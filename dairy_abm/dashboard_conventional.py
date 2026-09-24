"""Adapter from the Python model ledger to the Conventional Farm dashboard."""

from __future__ import annotations

from copy import deepcopy
from itertools import combinations
from statistics import mean

from dairy_abm.config import apply_calibration_overrides, value
from dairy_abm.model import DairyFarmModel


LOOPS = ("l1", "l2", "l3", "l4")
LOOP_SCENARIO_KEYS = {
    "l1": "l1_nutrient_loop_enabled",
    "l2": "l2_water_loop_enabled",
    "l3": "l3_energy_loop_enabled",
    "l4": "l4_byproduct_loop_enabled",
}

PARAMETERS = {
    "number_of_cows": ("scenario", "herd_size"),
    "simulation_years": ("scenario", "days"),
    "random_seed": ("scenario", "seed"),
    "land_cropland_ha": ("scenario", "land_cropland_ha"),
    "land_pasture_ha": ("scenario", "land_pasture_ha"),
    "wood_b": ("calibration", "herd.wood_b"),
    "wood_c": ("calibration", "herd.wood_c"),
    "peak_milk_L_first_parity": ("calibration", "herd.peak_milk_l_first_parity"),
    "peak_milk_L_mature": ("calibration", "herd.peak_milk_l_mature"),
    "mature_parity": ("calibration", "herd.mature_parity"),
    "cow_peak_std_fraction": ("calibration", "herd.cow_peak_std_fraction"),
    "dry_period_days": ("calibration", "herd.dry_period_days"),
    "max_parity": ("calibration", "herd.max_parity"),
    "water_cost_per_L": ("calibration", "water.water_cost_per_l"),
    "electricity_price_currency_per_kWh": ("calibration", "energy.electricity_price_per_kwh"),
    "heat_value_currency_per_kWh": ("calibration", "energy.heat_value_per_kwh"),
    "compost_value_currency_per_kg": ("calibration", "manure.compost_value_per_kg"),
    "water_loop_fresh_water_offset_fraction": ("calibration", "water.water_loop_fresh_water_offset_fraction"),
    "nutrient_loop_feed_substitution_fraction": ("calibration", "feed_crop.nutrient_loop_feed_substitution_fraction"),
}


def default_config(scenario: dict, calibration: dict) -> dict:
    """Expose only controls that have a direct model equivalent."""
    result = {}
    for name, (kind, target) in PARAMETERS.items():
        raw = scenario.get(target) if kind == "scenario" else value(calibration, target)
        result[name] = raw / 365 if name == "simulation_years" else raw
    return result


def resolve_inputs(params: dict, base_scenario: dict, base_calibration: dict) -> tuple[dict, dict, dict]:
    if not isinstance(params, dict):
        raise ValueError("request body must be a JSON object")
    cfg = params.get("cfg", {})
    if not isinstance(cfg, dict):
        raise ValueError("cfg must be an object")
    unsupported = set(cfg) - set(PARAMETERS)
    if unsupported:
        raise ValueError(f"unsupported parameter: {sorted(unsupported)[0]}")
    scenario = deepcopy(base_scenario)
    scenario.update({"days": 5 * 365, "herd_size": 100, "seed": 42})
    overrides = {}
    for key, raw in cfg.items():
        kind, target = PARAMETERS[key]
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ValueError(f"{key} must be numeric")
        if kind == "scenario":
            scenario[target] = round(raw * 365) if key == "simulation_years" else raw
        else:
            overrides[target] = raw
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
    scenario["enable_processor"] = loops["l4"]
    scenario["enable_whey_processing"] = loops["l4"]
    calibration = apply_calibration_overrides(base_calibration, overrides)
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
    series["energyVal"] = [
        max(0.0, float(row.get("energy_value") or 0.0) - float(row.get("heat_value") or 0.0))
        for row in records
    ]
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
    result = {
        "series": series if include_series else {}, "avg": avg, "totals": totals,
        "days": days, "n": int(ctx.scenario.get("herd_size", 0)), "cfg": cfg,
        "herdSummary": herd_summary(ctx) if include_series else [],
        "modelDetails": {
            "name": ctx.scenario.get("name", "baseline"),
            "seed": ctx.scenario.get("seed"),
            "days": days,
            "source": "DairyFarmModel",
            "loops": {key: bool(ctx.scenario.get(field)) for key, field in LOOP_SCENARIO_KEYS.items()},
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
            "peakFactor": float(cow.get("milk_trait", 1.0)),
            "milk": avg_milk, "feed": avg_feed, "water": water,
            "manure": mean(cow.get("manure_history", [0.0])),
            "fcr": sum(cow.get("dmi_history", [])) / (sum(milk_hist) * density) if sum(milk_hist) > 0 else None,
            "milkRev": avg_milk * price, "ghg": mean(cow.get("ch4_history", [0.0])) * gwp,
            "daysActive": duration, "daysMilking": milk_days,
            "sickDays": sum(h != "healthy" for h in cow.get("health_history", [])),
            "calvings": sum(e.get("event") == "calving" for e in cow.get("reproduction_history", [])),
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
