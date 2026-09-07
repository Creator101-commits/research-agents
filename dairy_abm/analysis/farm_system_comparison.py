from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from statistics import fmean
from typing import Any, Iterable

from dairy_abm.core import ConfigError, write_csv, write_json
from dairy_abm.farm_systems import list_farm_systems
from dairy_abm.model import DairyFarmModel


LOOP_CONFIGURATIONS: dict[str, tuple[bool, bool, bool, bool]] = {
    "none": (False, False, False, False),
    "l1_nutrient": (True, False, False, False),
    "l2_water": (False, True, False, False),
    "l3_energy": (False, False, True, False),
    "l4_byproduct": (False, False, False, True),
    "all": (True, True, True, True),
}


def _scenario_for_run(
    base: dict[str, Any], farm_system: str, configuration: str, seed: int
) -> dict[str, Any]:
    if configuration not in LOOP_CONFIGURATIONS:
        raise ConfigError(f"unknown loop configuration {configuration!r}")
    l1, l2, l3, l4 = LOOP_CONFIGURATIONS[configuration]
    scenario = deepcopy(base)
    for profile_key in (
        "production_system",
        "enable_land_agent",
        "land_grazing_enabled",
        "market_scenario",
        "milking_system",
        "precision_dairy_technology_count",
        "direct_raw_milk_sales",
        "beef_on_dairy_enabled",
        "user_breeding_priority",
    ):
        scenario.pop(profile_key, None)
    scenario.update(
        {
            "farm_system": farm_system,
            "seed": seed,
            "l1_nutrient_loop_enabled": l1,
            "l2_water_loop_enabled": l2,
            "l3_energy_loop_enabled": l3,
            "l4_byproduct_loop_enabled": l4,
            "enable_processor": l4,
            "enable_whey_processing": l4,
        }
    )
    return scenario


def assess_farm_systems(
    base_scenario: dict[str, Any],
    calibration: dict[str, Any],
    *,
    systems: Iterable[str] | None = None,
    configurations: Iterable[str] | None = None,
    seeds: Iterable[int] = (1,),
) -> dict[str, Any]:
    selected_systems = tuple(systems or list_farm_systems())
    selected_configs = tuple(configurations or LOOP_CONFIGURATIONS)
    selected_seeds = tuple(int(seed) for seed in seeds)
    if not selected_seeds:
        raise ConfigError("at least one seed is required")

    runs: list[dict[str, Any]] = []
    for system in selected_systems:
        for configuration in selected_configs:
            for seed in selected_seeds:
                scenario = _scenario_for_run(base_scenario, system, configuration, seed)
                ctx = DairyFarmModel(scenario, calibration).run()
                days = len(ctx.daily_records)
                annualizer = 365.0 / days if days else 0.0
                investment = ctx.state["investment_analysis"]
                dmc = ctx.state["dmc_analysis"]
                runs.append(
                    {
                        "farm_system": ctx.scenario["farm_system"],
                        "farm_system_label": ctx.scenario["farm_system_label"],
                        "configuration": configuration,
                        "seed": seed,
                        "days": days,
                        "annual_milk_l": sum(float(row.get("milk_l", 0.0)) for row in ctx.daily_records) * annualizer,
                        "annual_operating_profit": sum(float(row.get("profit", 0.0)) for row in ctx.daily_records) * annualizer,
                        "annual_net_kg_co2e": sum(float(row.get("net_kg_co2e", 0.0)) for row in ctx.daily_records) * annualizer,
                        "annual_freshwater_withdrawal_l": sum(float(row.get("freshwater_withdrawal_l", 0.0)) for row in ctx.daily_records) * annualizer,
                        "mean_circularity_score": fmean(float(row.get("circularity_score", 0.0)) for row in ctx.daily_records) if days else 0.0,
                        "portfolio_capex": investment["portfolio"]["capex"],
                        "portfolio_annual_net_benefit": investment["portfolio"]["annual_net_benefit"],
                        "portfolio_payback_years": investment["portfolio"]["simple_payback_years"],
                        "portfolio_fifteen_year_roi": investment["portfolio"]["fifteen_year_roi"],
                        "portfolio_npv": investment["portfolio"]["npv"],
                        "investment_discount_rate": investment["discount_rate"],
                        "simulated_iofc_margin_usd_cwt": dmc["simulated_iofc_margin_usd_cwt"],
                        "simulated_iofc_above_selected_threshold": dmc["simulated_iofc_above_selected_threshold"],
                        "dmc_selected_annual_cost": dmc["premium"]["total_annual_cost"],
                    }
                )
    baseline_by_system_seed = {
        (row["farm_system"], row["seed"]): row
        for row in runs
        if row["configuration"] == "none"
    }
    for row in runs:
        baseline = baseline_by_system_seed[(row["farm_system"], row["seed"])]
        annual_net_benefit = float(row["annual_operating_profit"]) - float(
            baseline["annual_operating_profit"]
        )
        capex = float(row["portfolio_capex"])
        rate = float(row["investment_discount_rate"])
        horizon = 15
        annuity_factor = sum(1.0 / (1.0 + rate) ** year for year in range(1, horizon + 1))
        row["counterfactual_annual_net_benefit"] = annual_net_benefit
        row["counterfactual_simple_payback_years"] = (
            capex / annual_net_benefit if capex > 0.0 and annual_net_benefit > 0.0 else None
        )
        row["counterfactual_fifteen_year_roi"] = (
            (horizon * annual_net_benefit - capex) / capex if capex > 0.0 else None
        )
        row["counterfactual_npv"] = -capex + annual_net_benefit * annuity_factor
        row["annual_net_benefit_method"] = (
            "annualized operating-profit difference versus same-system no-loop run"
        )
        row["simulated_iofc_change_vs_no_loops_usd_cwt"] = (
            float(row["simulated_iofc_margin_usd_cwt"])
            - float(baseline["simulated_iofc_margin_usd_cwt"])
        )
        row["raises_simulated_iofc_above_threshold"] = bool(
            not baseline["simulated_iofc_above_selected_threshold"]
            and row["simulated_iofc_above_selected_threshold"]
        )
        row["dmc_premium_change_attributable_to_loop"] = 0.0
        row["dmc_premium_change_reason"] = (
            "USDA DMC premiums depend on elected coverage and production history, not farm-simulated IOFC."
        )
    return {
        "assessment_type": "comparative simulation screening",
        "farm_systems": list(selected_systems),
        "loop_configurations": list(selected_configs),
        "seeds": list(selected_seeds),
        "run_count": len(runs),
        "runs": runs,
        "limitations": [
            "This is a model-output comparison, not empirical validation against measured farms.",
            "Profile defaults encode structural differences; price premiums, labor effects, and beef-calf revenue require observed or explicit scenario inputs.",
        ],
    }


def write_farm_system_assessment(output_dir: Path, assessment: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "farm_system_assessment.json", assessment)
    write_csv(output_dir / "farm_system_assessment.csv", assessment["runs"])
