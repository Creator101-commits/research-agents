"""Adapter from the Python model ledger to the Conventional Farm dashboard."""

from __future__ import annotations

from copy import deepcopy
from itertools import combinations
from statistics import mean

from dairy_abm.config import apply_calibration_overrides, value
from dairy_abm.core import ConfigError
from dairy_abm.model import DairyFarmModel


LOOPS = ("l1", "l2", "l3", "l4")
LOOP_SCENARIO_KEYS = {
    "l1": "l1_nutrient_loop_enabled",
    "l2": "l2_water_loop_enabled",
    "l3": "l3_energy_loop_enabled",
    "l4": "l4_byproduct_loop_enabled",
}

PRODUCT_MIX = ("cheese", "butter", "yogurt", "fresh", "functional")

# Pasture and heat value stay disabled: the land agent is off in the dashboard
# scenario, and no farm heat demand is configured, so neither changes a run.
# Target controls with a direct model equivalent. A calibration target may be a
# tuple when one control sets keys that must stay equal (the workbook feed price
# is stored for the ledger, the market packet and the feed agent's fallback).
PARAMETERS = {
    "number_of_cows": ("scenario", "herd_size"),
    "simulation_years": ("scenario", "days"),
    "random_seed": ("scenario", "seed"),
    "land_cropland_ha": ("scenario", "land_cropland_ha"),
    "wood_b": ("calibration", "herd.wood_b"),
    "wood_c": ("calibration", "herd.wood_c"),
    "peak_milk_L_first_parity": ("calibration", "herd.peak_milk_l_first_parity"),
    "peak_milk_L_mature": ("calibration", "herd.peak_milk_l_mature"),
    "mature_parity": ("calibration", "herd.mature_parity"),
    "cow_peak_std_fraction": ("calibration", "herd.cow_peak_std_fraction"),
    "dry_period_days": ("calibration", "herd.dry_period_days"),
    "max_parity": ("calibration", "herd.max_parity"),
    "annual_involuntary_cull_fraction": ("calibration", "herd.cow_involuntary_cull_rate_annual"),
    "bodyweight_first_parity_kg": ("calibration", "cow.bodyweight_first_parity_kg"),
    "bodyweight_mature_kg": ("calibration", "cow.bodyweight_mature_kg"),
    "illness_milk_penalty_fraction": ("calibration", "disease.milk_loss_sick_fraction"),
    "feed_cost_per_kg": (
        "calibration",
        ("cdairy_economics.dmi_wet_price_per_kg", "market.feed_cost_per_kg_dm", "feed_crop.ration_cost_per_kg_dm"),
    ),
    "water_cost_per_L": ("calibration", "water.water_cost_per_l"),
    "electricity_price_currency_per_kWh": ("calibration", "energy.electricity_price_per_kwh"),
    "compost_value_currency_per_kg": ("calibration", "manure.compost_value_per_kg"),
    "compost_kg_per_kg_manure_to_compost": ("calibration", "manure.compost_product_yield_fraction"),
    "grid_avoided_kg_co2e_per_kWh": ("calibration", "energy.grid_offset_kg_co2e_per_kwh"),
    "water_loop_fresh_water_offset_fraction": ("calibration", "water.water_loop_fresh_water_offset_fraction"),
    "fraction_milk_to_processor": ("calibration", "dairy_processor.fraction_milk_to_processor"),
    "fraction_whey_to_animal_feed_loop": ("calibration", "dairy_processor.fraction_whey_to_feed"),
    **{
        f"fraction_milk_to_{name}": ("calibration", f"dairy_processor.product_mix_{name}")
        for name in PRODUCT_MIX
    },
    **{
        f"price_per_L_milk_{name}": ("calibration", f"dairy_processor.price_per_l_milk_{name}")
        for name in PRODUCT_MIX
    },
}


def _solar_capacity_factor(scenario: dict) -> float:
    return float(scenario.get("solar_capacity_factor", 0.2))


def _set(overrides: dict, key: str, raw: float) -> None:
    overrides[key] = raw


# Controls that map to a model quantity through a unit conversion:
# name -> (default from scenario/calibration, apply to scenario/overrides).
DERIVED_PARAMETERS = {
    # Separator solids go to compost, liquids to the digester (Manure routing).
    "separator_solid_fraction": (
        lambda sc, cal: value(cal, "manure.compost_route_fraction"),
        lambda raw, sc, cal, ov: ov.update({
            "manure.compost_route_fraction": raw,
            "manure.digester_route_fraction": round(1.0 - raw, 12),
            "manure.storage_route_fraction": 0.0,
        }),
    ),
    # The model publishes methane volume per kg manure as VS fraction x BMP.
    "biogas_m3_per_kg_manure_to_digester": (
        lambda sc, cal: value(cal, "manure.volatile_solids_fraction")
        * value(cal, "manure.biochemical_methane_potential_m3_per_kg_vs"),
        lambda raw, sc, cal, ov: _set(
            ov, "manure.biochemical_methane_potential_m3_per_kg_vs", raw / value(cal, "manure.volatile_solids_fraction")
        ),
    ),
    # Solar kWh/cow/day = kW per cow x capacity factor x 24 h (Energy agent).
    "solar_electricity_kWh_per_cow_per_day": (
        lambda sc, cal: (
            value(cal, "energy.solar_kw_per_cow") * _solar_capacity_factor(sc) * 24.0
            if sc.get("solar_sized_per_cow")
            else 0.0
        ),
        lambda raw, sc, cal, ov: (
            sc.update({"solar_sized_per_cow": raw > 0}),
            _set(ov, "energy.solar_kw_per_cow", raw / (24.0 * _solar_capacity_factor(sc))),
        ),
    ),
    # A multiplier on the enteric CH4 coefficient (1 = no intervention).
    "methane_reduction_factor": (
        lambda sc, cal: 1.0,
        lambda raw, sc, cal, ov: _set(ov, "cow.enteric_ch4_kg_per_cow_day", value(cal, "cow.enteric_ch4_kg_per_cow_day") * raw),
    ),
    # Manure scales with intake from the base manure / base DMI ratio (Cow agent).
    "manure_kg_per_kg_dmi": (
        lambda sc, cal: value(cal, "cow.base_manure_kg_per_cow_day") / value(cal, "cow.base_dmi_kg_per_cow_day"),
        lambda raw, sc, cal, ov: _set(ov, "cow.base_manure_kg_per_cow_day", raw * value(cal, "cow.base_dmi_kg_per_cow_day")),
    ),
    # Mean illness duration of a daily recovery probability p is 1 / p.
    "illness_duration_days_mean": (
        lambda sc, cal: 1.0 / value(cal, "disease.recovery_daily_probability"),
        lambda raw, sc, cal, ov: _set(ov, "disease.recovery_daily_probability", 1.0 / raw),
    ),
}

SUPPORTED_PARAMETERS = (*PARAMETERS, *DERIVED_PARAMETERS)


def default_config(scenario: dict, calibration: dict) -> dict:
    """Expose only controls that have a model equivalent."""
    result = {}
    for name, (kind, target) in PARAMETERS.items():
        key = target[0] if isinstance(target, tuple) else target
        raw = scenario.get(key) if kind == "scenario" else value(calibration, key)
        result[name] = raw / 365 if name == "simulation_years" else raw
    for name, (default, _apply) in DERIVED_PARAMETERS.items():
        result[name] = default(scenario, calibration)
    return result


def resolve_inputs(params: dict, base_scenario: dict, base_calibration: dict) -> tuple[dict, dict, dict]:
    if not isinstance(params, dict):
        raise ValueError("request body must be a JSON object")
    cfg = params.get("cfg", {})
    if not isinstance(cfg, dict):
        raise ValueError("cfg must be an object")
    unsupported = set(cfg) - set(SUPPORTED_PARAMETERS)
    if unsupported:
        raise ValueError(f"unsupported parameter: {sorted(unsupported)[0]}")
    scenario = deepcopy(base_scenario)
    scenario.update({"days": 5 * 365, "herd_size": 100, "seed": 42})
    overrides = {}
    derived = []
    for key, raw in cfg.items():
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ValueError(f"{key} must be numeric")
        if key in DERIVED_PARAMETERS:
            derived.append((key, raw))
            continue
        kind, target = PARAMETERS[key]
        if kind == "scenario":
            scenario[target] = round(raw * 365) if key == "simulation_years" else raw
        else:
            for item in target if isinstance(target, tuple) else (target,):
                overrides[item] = raw
    for key, raw in derived:
        if raw <= 0 and key in ("illness_duration_days_mean",):
            raise ValueError(f"{key} must be positive")
        DERIVED_PARAMETERS[key][1](raw, scenario, base_calibration, overrides)
    days = scenario["days"]
    if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 10950:
        raise ValueError("simulation_years must yield 1 to 10950 days")
    for key in ("herd_size", "seed"):
        raw = scenario[key]
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise ValueError(f"{key} must be a whole number")
    if not 1 <= scenario["herd_size"] <= 5000:
        raise ValueError("number_of_cows must be between 1 and 5000")
    loops = params.get("loops", {key: True for key in LOOPS})
    if not isinstance(loops, dict) or set(loops) != set(LOOPS) or any(type(x) is not bool for x in loops.values()):
        raise ValueError("loops must contain four boolean values")
    for key, field in LOOP_SCENARIO_KEYS.items():
        scenario[field] = loops[key]
    # The processor runs with L4 only so whey and waste milk exist for the
    # by-product feed loop; its product sales stay out of farm profit, which
    # keeps the workbook's milk component sales (reported as
    # processorRevenueNotInProfit).
    scenario["enable_processor"] = loops["l4"]
    scenario["enable_whey_processing"] = loops["l4"]
    # The emissions-triggered reroute (an implementation rule, not in the
    # Blueprint) would send all manure to the digester and override the
    # separator split the dashboard runs with.
    scenario["auto_environment_response"] = False
    mix_keys = [f"dairy_processor.product_mix_{name}" for name in PRODUCT_MIX]
    if any(key in overrides for key in mix_keys):
        # Contract shares are normalized to sum to 1, as the target's normalizeProductMix does.
        shares = {key: float(overrides.get(key, value(base_calibration, key))) for key in mix_keys}
        total = sum(shares.values())
        if total <= 0.0 or any(share < 0.0 for share in shares.values()):
            raise ValueError("milk contract shares must be nonnegative with a positive total")
        overrides.update({key: share / total for key, share in shares.items()})
    try:
        calibration = apply_calibration_overrides(base_calibration, overrides)
    except ConfigError as exc:
        raise ValueError(str(exc)) from exc
    return scenario, calibration, default_config(scenario, calibration)


FIELD_MAP = {
    "milk": "milk_l", "manure": "manure_kg", "feedDemand": "dmi_kg",
    "waterBase": "total_water_use_l",
    "netWater": "net_water_l", "whey": "whey_l", "wheyGenerated": "whey_l",
    "wastewater": "wastewater_l", "compost": "compost_product_kg",
    "nRec": "compost_n_kg", "pRec": "compost_p_kg", "kRec": "compost_k_kg",
    "wN": "water_recovered_n_kg", "wP": "water_recovered_p_kg", "wK": "water_recovered_k_kg",
    "biogasM3": "biogas_volume_m3", "elec": "electricity_generated_kwh",
    "solar": "solar_generated_kwh", "recycledIrrig": "recycled_irrigation_l",
    "freshOffset": "l2_water_offset_l", "waterCredit": "water_loop_offset_l",
    "digestate": "digestate_kg", "feedOffset": "l1_feed_offset_kg",
    "l4FeedOffset": "l4_feed_offset_kg", "wheyToFeed": "whey_to_feed_l",
    "wasteToFeed": "waste_milk_to_feed_l", "feedReturn": "l4_feed_offset_kg",
    "grossGHG": "gross_kg_co2e", "netGHG": "net_kg_co2e",
    "avoidedGrid": "energy_offset_kg_co2e", "biogasDispl": "fertilizer_offset_kg_co2e",
    "milkRev": "milk_revenue", "heatVal": "heat_value",
    "compostRev": "compost_revenue", "totalRevenue": "total_revenue",
    "feedCost": "feed_cost", "waterCost": "water_cost", "profit": "profit",
    "sludgeFertilizer": "sludge_fertilizer_l", "nutrientPool": "soil_n_kg",
    "workbookFeedCost": "workbook_feed_cost", "loopFeedSaving": "loop_feed_saving",
    "purchasedFeedCost": "purchased_feed_cost", "herdRevenue": "herd_revenue",
    "herdCost": "herd_cost", "herdProfit": "herd_profit", "loopNet": "loop_net",
    "coolingCost": "cooling_cost", "processorEnergyCostNotInProfit": "processor_energy_cost_not_in_profit",
    "diseaseCost": "disease_cost", "carbonCredits": "carbon_credit_value",
    "processorRevenueNotInProfit": "processor_revenue_not_in_profit",
    "digesterManure": "digester_kg", "compostManure": "compost_kg",
    "fertilizerNSaved": "synthetic_fertilizer_saved_kg", "fertilizerOffsetCO2e": "fertilizer_offset_kg_co2e",
    "digestateN": "digestate_n_kg", "digestateP": "digestate_p_kg", "digestateK": "digestate_k_kg",
    "surplusElec": "surplus_energy_kwh", "displacedElec": "displaced_grid_energy_kwh",
    "farmElecDemand": "farm_energy_demand_kwh", "heatDemand": "heat_demand_mj",
    "byproductFeedCredit": "pending_feed_credit_kg",
    "waterRecycleCredit": "pending_water_credit_l",
}
ALIAS = {"feed": "netFeed", "biogas": "biogasM3", "fcr": "netFCR", "profitability": "profit", "water": "netWater"}


def serialize_run(ctx, cfg: dict, *, include_series: bool = True) -> dict:
    records = ctx.daily_records
    days = len(records)
    if not days:
        raise ValueError("model returned no daily records")
    series = {key: [float(row.get(source) or 0.0) for row in records] for key, source in FIELD_MAP.items()}
    series["netFeed"] = [
        max(0.0, feed - float(row.get("feed_loop_offset_kg") or 0.0))
        for feed, row in zip(series["feedDemand"], records)
    ]
    # The energy packet's total already includes heat; split the two display streams.
    # Electricity is valued only up to the farm demand (Blueprint Energy 8.2, 10).
    series["energyVal"] = [
        max(0.0, float(row.get("energy_value") or 0.0) - float(row.get("heat_value") or 0.0))
        for row in records
    ]
    # Split the ledger's loop feed saving between L1 and L4 by offset kilograms.
    series["l1FeedSaving"], series["l4FeedSaving"] = [], []
    for row in records:
        l1, l4 = float(row.get("l1_feed_offset_kg") or 0.0), float(row.get("l4_feed_offset_kg") or 0.0)
        saving = float(row.get("loop_feed_saving") or 0.0)
        series["l1FeedSaving"].append(saving * l1 / (l1 + l4) if l1 + l4 > 0 else 0.0)
        series["l4FeedSaving"].append(saving * l4 / (l1 + l4) if l1 + l4 > 0 else 0.0)
    series["day"] = list(range(1, days + 1))
    series["heat"] = [float(row.get("heat_generated_mj") or 0.0) / 3.6 for row in records]
    series["totalElec"] = [a + b for a, b in zip(series["elec"], series["solar"])]
    # Sludge is recorded in liters without a density; do not add it to kilogram flows.
    series["organicFert"] = [
        float(row.get("compost_product_kg") or 0.0) + float(row.get("digestate_kg") or 0.0)
        for row in records
    ]
    for nutrient in ("n", "p", "k"):
        series[nutrient + "RecTotal"] = [a + b for a, b in zip(series[nutrient + "Rec"], series["w" + nutrient.upper()])]
    series["energyCredit"] = [0.0] * days
    milk_mass = [float(row.get("milk_kg") or 0.0) for row in records]
    for key, feed_key in (("netFCR", "netFeed"), ("grossFCR", "feedDemand")):
        series[key] = [feed / milk if milk > 0 else None for feed, milk in zip(series[feed_key], milk_mass)]
    totals = {key: sum(v for v in values if v is not None) for key, values in series.items() if key != "day"}
    avg = {key: total / days for key, total in totals.items()}
    for key in ("netFCR", "grossFCR"):
        valid = [item for item in series[key] if item is not None]
        avg[key] = mean(valid) if valid else None
    for alias, source in ALIAS.items():
        series[alias] = series[source]
        totals[alias] = totals[source]
        avg[alias] = avg[source]
    totals["feedCostTotal"] = totals["feedCost"]
    totals["waterCostTotal"] = totals["waterCost"]
    totals["circularOutput"] = sum(totals[k] for k in ("compost", "recycledIrrig", "feedReturn", "totalElec"))
    avg["wheyFoods"] = None
    series["wheyFoods"] = [None] * days
    totals["otherHerdNet"] = totals["profit"] - (totals["totalRevenue"] - totals["feedCost"] - totals["waterCost"])
    # Workbook herd costs other than feed; the loop layer is listed line by line.
    totals["otherHerdCost"] = totals["herdCost"] - totals["workbookFeedCost"]
    totals["loopLines"] = {
        "electricityValue": totals["energyVal"], "heatValue": totals["heatVal"],
        "carbonCredits": totals["carbonCredits"], "compostRevenue": totals["compostRev"],
        "loopFeedSaving": totals["loopFeedSaving"], "waterCost": -totals["waterCost"],
        "coolingCost": -totals["coolingCost"],
        "diseaseCost": -totals["diseaseCost"],
    }
    notes = {}
    if totals["heat"] > 0 and totals["heatVal"] == 0 and totals["heatDemand"] == 0:
        notes["heatVal"] = "Heat is generated but not valued: no farm heat demand is configured (Blueprint Energy 8.5)."
    if totals["solar"] == 0:
        notes["solar"] = "No solar capacity is configured; the Blueprint and workbook give no solar assumption."
    if totals["surplusElec"] > 0:
        notes["energyVal"] = (
            "Electricity is valued only up to the farm demand of "
            f"{avg['farmElecDemand']:.0f} kWh/day (implementation assumption); "
            f"{avg['surplusElec']:.0f} kWh/day of surplus is reported but not monetized (Blueprint Energy 10)."
        )
    # Model prices and factors for the ROI page, so it does not fall back to the
    # target's catalogue constants where the model has a value.
    last = records[-1]
    cfg = {
        **cfg,
        "dry_feed_cost_per_kg": value(ctx.calibration, "cdairy_economics.dmi_dry_price_per_kg"),
        "carbon_credit_price_per_tonne_co2e": float(last.get("carbon_credit_price_per_tonne_co2e") or 0.0),
        "heat_value_effective_per_kWh": totals["heatVal"] / totals["heat"] if totals["heat"] > 0 else 0.0,
        "farm_energy_demand_kwh_per_day": avg["farmElecDemand"],
    }
    if totals["carbonCredits"] == 0:
        notes["carbon"] = "No carbon-credit price is configured, so avoided emissions earn no credit revenue (Blueprint Energy 8.4)."
    result = {
        "series": series if include_series else {}, "avg": avg, "totals": totals,
        "days": days, "n": int(ctx.scenario.get("herd_size", 0)), "cfg": cfg,
        "herdSummary": herd_summary(ctx) if include_series else [],
        "notes": notes,
        "modelDetails": {
            "name": ctx.scenario.get("name", "baseline"),
            "seed": ctx.scenario.get("seed"),
            "days": days,
            "source": "DairyFarmModel",
            "loops": {key: bool(ctx.scenario.get(field)) for key, field in LOOP_SCENARIO_KEYS.items()},
            # The processor is a separate business: both figures are reported, neither is in profit.
            "processorRevenueNotInProfit": totals["processorRevenueNotInProfit"],
            "processorEnergyCostNotInProfit": totals["processorEnergyCostNotInProfit"],
        },
    }
    return result


def herd_summary(ctx) -> list[dict]:
    cows = ctx.state.get("cows", [])
    milk_revenue = sum(float(r.get("milk_revenue") or 0) for r in ctx.daily_records)
    milk_volume = sum(float(r.get("milk_l") or 0) for r in ctx.daily_records)
    milk_mass = sum(float(r.get("milk_kg") or 0) for r in ctx.daily_records)
    density = milk_mass / milk_volume if milk_volume else 1.03
    price = milk_revenue / milk_volume if milk_volume else 0.0
    # The Blueprint gives no per-cow drinking equation (Water agent 2.6), so each
    # cow gets the herd-average allocation; the UI labels the column that way.
    water = float(value(ctx.calibration, "water.drinking_l_per_cow_day"))
    gwp = float(value(ctx.calibration, "environment.ch4_gwp100"))
    result = []
    for cow in cows:
        if int(cow.get("parity", 0)) < 1:
            continue
        milk_hist = cow.get("milk_history", [])
        if not milk_hist:
            continue
        milk_days = sum(v > 0 for v in milk_hist)
        duration = len(milk_hist)
        avg_milk = sum(milk_hist) / milk_days if milk_days else 0.0
        avg_feed = mean(cow.get("dmi_history", [0.0]))
        model_id = str(cow.get("id", ""))
        result.append({
            "id": f"C{len(result) + 1:05d}", "modelId": model_id,
            "parity": int(cow.get("parity", 0)),
            "bw": round(float(cow.get("body_weight_kg", 0.0))),
            "peakFactor": float(cow.get("peak_factor", 1.0)),
            "milk": avg_milk, "feed": avg_feed, "water": water,
            "manure": mean(cow.get("manure_history", [0.0])),
            "fcr": sum(cow.get("dmi_history", [])) / (sum(milk_hist) * density) if sum(milk_hist) > 0 else None,
            "milkRev": avg_milk * price, "ghg": mean(cow.get("ch4_history", [0.0])) * gwp,
            "daysActive": duration, "daysMilking": milk_days,
            "sickDays": sum(h != "healthy" for h in cow.get("health_history", [])),
            "calvings": sum(e.get("event") in ("calving", "first_calving") for e in cow.get("reproduction_history", [])),
            "cullReason": "active" if cow.get("alive", True) else str(cow.get("removal_reason") or "removed"),
            "isFounder": model_id.startswith("cow-"),
        })
    return result


def run_model(params: dict, base_scenario: dict, base_calibration: dict, *, include_series: bool = True):
    scenario, calibration, cfg = resolve_inputs(params, base_scenario, base_calibration)
    ctx = DairyFarmModel(scenario, calibration).run()
    return serialize_run(ctx, cfg, include_series=include_series), ctx


def compare_one(job):
    key, params, base_scenario, base_calibration = job
    loops = {loop: key == "all4" or loop in key for loop in LOOPS}
    if key == "baseline":
        loops = {loop: False for loop in LOOPS}
    params = {**params, "loops": loops}
    result, _ = run_model(params, base_scenario, base_calibration, include_series=False)
    result["herdSummary"] = []
    return key, result


def comparison_keys() -> list[str]:
    return ["baseline"] + ["".join(group) for size in range(1, 4) for group in combinations(LOOPS, size)] + ["all4"]
