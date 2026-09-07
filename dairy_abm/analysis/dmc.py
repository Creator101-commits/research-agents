from __future__ import annotations

from typing import Any

from dairy_abm.core import ConfigError


DMC_PREMIUM_RATES_2026: dict[float, tuple[float, float | None]] = {
    4.0: (0.0, 0.0),
    4.5: (0.0025, 0.0025),
    5.0: (0.005, 0.005),
    5.5: (0.030, 0.100),
    6.0: (0.050, 0.310),
    6.5: (0.070, 0.650),
    7.0: (0.080, 1.107),
    7.5: (0.090, 1.413),
    8.0: (0.100, 1.813),
    8.5: (0.105, None),
    9.0: (0.110, None),
    9.5: (0.150, None),
}


def dmc_feed_cost(corn_usd_bu: float, soybean_meal_usd_ton: float, alfalfa_usd_ton: float) -> float:
    for name, amount in {
        "corn_usd_bu": corn_usd_bu,
        "soybean_meal_usd_ton": soybean_meal_usd_ton,
        "alfalfa_usd_ton": alfalfa_usd_ton,
    }.items():
        if amount < 0.0:
            raise ConfigError(f"{name} must be nonnegative")
    return 1.0728 * corn_usd_bu + 0.00735 * soybean_meal_usd_ton + 0.0137 * alfalfa_usd_ton


def dmc_margin(all_milk_usd_cwt: float, corn_usd_bu: float, soybean_meal_usd_ton: float, alfalfa_usd_ton: float) -> float:
    if all_milk_usd_cwt < 0.0:
        raise ConfigError("all_milk_usd_cwt must be nonnegative")
    return all_milk_usd_cwt - dmc_feed_cost(corn_usd_bu, soybean_meal_usd_ton, alfalfa_usd_ton)


def annual_premium(
    production_history_lb: float,
    coverage_fraction: float,
    coverage_level: float,
    *,
    tier2_coverage_level: float | None = None,
    lock_in_discount: bool = False,
    administrative_fee: float = 100.0,
) -> dict[str, float | None]:
    if production_history_lb < 0.0:
        raise ConfigError("production_history_lb must be nonnegative")
    if not 0.05 <= coverage_fraction <= 0.95 or abs(coverage_fraction * 20 - round(coverage_fraction * 20)) > 1e-9:
        raise ConfigError("DMC coverage_fraction must be 0.05..0.95 in 0.05 increments")
    level = round(float(coverage_level), 2)
    if level not in DMC_PREMIUM_RATES_2026:
        raise ConfigError("DMC coverage_level must be 4.00..9.50 in 0.50 increments")

    tier1_rate, same_level_tier2_rate = DMC_PREMIUM_RATES_2026[level]
    tier1_history_lb = min(production_history_lb, 6_000_000.0)
    tier2_history_lb = max(0.0, production_history_lb - 6_000_000.0)
    tier1_lb = tier1_history_lb * coverage_fraction

    selected_tier2_level: float | None
    if tier2_history_lb <= 0.0:
        selected_tier2_level = None
    elif tier2_coverage_level is not None:
        selected_tier2_level = round(float(tier2_coverage_level), 2)
        if selected_tier2_level not in DMC_PREMIUM_RATES_2026:
            raise ConfigError("DMC tier2_coverage_level must be 4.00..8.00 in 0.50 increments")
        if DMC_PREMIUM_RATES_2026[selected_tier2_level][1] is None:
            raise ConfigError("DMC Tier 2 coverage is unavailable above $8.00")
    elif same_level_tier2_rate is not None:
        selected_tier2_level = level
    else:
        selected_tier2_level = None

    tier2_lb = tier2_history_lb * coverage_fraction if selected_tier2_level is not None else 0.0
    tier2_rate = (
        DMC_PREMIUM_RATES_2026[selected_tier2_level][1]
        if selected_tier2_level is not None
        else None
    )
    premium_before_discount = (
        tier1_lb / 100.0 * tier1_rate
        + tier2_lb / 100.0 * float(tier2_rate or 0.0)
    )
    discount = 0.25 if lock_in_discount else 0.0
    premium = premium_before_discount * (1.0 - discount)
    return {
        "eligible_production_history_lb": production_history_lb,
        "covered_production_lb": tier1_lb + tier2_lb,
        "uncovered_production_lb": production_history_lb - tier1_lb - tier2_lb,
        "tier1_covered_lb": tier1_lb,
        "tier2_covered_lb": tier2_lb,
        "tier1_coverage_level_usd_cwt": level,
        "tier2_coverage_level_usd_cwt": selected_tier2_level,
        "premium_before_discount": premium_before_discount,
        "premium_discount": premium_before_discount * discount,
        "premium_after_discount": premium,
        "administrative_fee": administrative_fee,
        "total_annual_cost": premium + administrative_fee,
    }


def monthly_indemnity(
    official_margin_usd_cwt: float,
    coverage_level: float,
    production_history_lb: float,
    coverage_fraction: float,
    producer_share: float = 1.0,
) -> float:
    if not 0.0 <= producer_share <= 1.0:
        raise ConfigError("DMC producer_share must be between 0 and 1")
    covered_monthly_cwt = production_history_lb * coverage_fraction / 100.0 / 12.0
    return max(0.0, coverage_level - official_margin_usd_cwt) * covered_monthly_cwt * producer_share


def tiered_monthly_indemnity(
    official_margin_usd_cwt: float,
    premium_election: dict[str, float | None],
    producer_share: float = 1.0,
) -> dict[str, float]:
    """Calculate Tier 1 and Tier 2 monthly indemnities from an enrolled election."""
    if not 0.0 <= producer_share <= 1.0:
        raise ConfigError("DMC producer_share must be between 0 and 1")
    tier1_level = float(premium_election["tier1_coverage_level_usd_cwt"] or 0.0)
    tier2_level = premium_election.get("tier2_coverage_level_usd_cwt")
    tier1_payment = (
        max(0.0, tier1_level - official_margin_usd_cwt)
        * float(premium_election["tier1_covered_lb"] or 0.0)
        / 100.0
        / 12.0
        * producer_share
    )
    tier2_payment = (
        max(0.0, float(tier2_level) - official_margin_usd_cwt)
        * float(premium_election["tier2_covered_lb"] or 0.0)
        / 100.0
        / 12.0
        * producer_share
        if tier2_level is not None
        else 0.0
    )
    return {
        "tier1": tier1_payment,
        "tier2": tier2_payment,
        "total": tier1_payment + tier2_payment,
    }


def analyze_dmc(
    scenario: dict[str, Any], daily_records: list[dict[str, Any]]
) -> dict[str, Any]:
    observed_days = len(daily_records)
    milk_l = sum(float(row.get("milk_l", 0.0)) for row in daily_records)
    milk_revenue = sum(float(row.get("raw_milk_revenue", row.get("milk_revenue", 0.0))) for row in daily_records)
    feed_cost = sum(float(row.get("feed_cost", 0.0)) for row in daily_records)
    density = max(0.1, float(scenario.get("milk_density_kg_per_l", 1.03)))
    milk_cwt = milk_l * density / 45.359237
    simulated_iofc = (milk_revenue - feed_cost) / milk_cwt if milk_cwt > 0.0 else None
    annualized_milk_lb = milk_l * density * 2.20462262 * (365.0 / observed_days if observed_days else 0.0)
    production_history = float(scenario.get("dmc_production_history_lb", annualized_milk_lb))
    coverage_level = float(scenario.get("dmc_coverage_level", 8.0))
    tier2_coverage_level = scenario.get("dmc_tier2_coverage_level")
    coverage_fraction = float(scenario.get("dmc_coverage_fraction", 0.95))
    lock_in = bool(scenario.get("dmc_lock_in_discount", False))
    premium = annual_premium(
        production_history,
        coverage_fraction,
        coverage_level,
        tier2_coverage_level=(
            float(tier2_coverage_level) if tier2_coverage_level is not None else None
        ),
        lock_in_discount=lock_in,
    )

    inputs = scenario.get("dmc_market_inputs", {})
    if inputs and not isinstance(inputs, dict):
        raise ConfigError("dmc_market_inputs must be an object")
    required = {"all_milk_usd_cwt", "corn_usd_bu", "soybean_meal_usd_ton", "alfalfa_usd_ton"}
    official_margin = None
    official_feed_cost = None
    indemnity = None
    indemnity_by_tier = None
    if isinstance(inputs, dict) and required <= set(inputs):
        official_feed_cost = dmc_feed_cost(
            float(inputs["corn_usd_bu"]),
            float(inputs["soybean_meal_usd_ton"]),
            float(inputs["alfalfa_usd_ton"]),
        )
        official_margin = float(inputs["all_milk_usd_cwt"]) - official_feed_cost
        indemnity_by_tier = tiered_monthly_indemnity(
            official_margin,
            premium,
            float(scenario.get("dmc_producer_share", 1.0)),
        )
        indemnity = indemnity_by_tier["total"]

    return {
        "program_year": 2026,
        "official_formula_source": "USDA FSA 1-DMC paragraph 85 and January 2026 DMC fact sheet",
        "official_formula_source_url": "https://www.fsa.usda.gov/Internet/FSA_File/1-dmc_r00_a01.pdf",
        "premium_source_url": "https://www.fsa.usda.gov/sites/default/files/2026-01/FSA_DMC_012026.pdf",
        "simulated_iofc_margin_usd_cwt": simulated_iofc,
        "simulated_iofc_is_official_dmc_margin": False,
        "coverage_level_usd_cwt": coverage_level,
        "simulated_iofc_above_selected_threshold": simulated_iofc >= coverage_level if simulated_iofc is not None else None,
        "production_history_lb": production_history,
        "production_history_method": "scenario_override" if "dmc_production_history_lb" in scenario else "annualized simulated milk proxy",
        "coverage_fraction": coverage_fraction,
        "premium": premium,
        "official_market_inputs": dict(inputs) if isinstance(inputs, dict) else {},
        "official_feed_cost_usd_cwt": official_feed_cost,
        "official_dmc_margin_usd_cwt": official_margin,
        "estimated_monthly_indemnity": indemnity,
        "estimated_monthly_indemnity_by_tier": indemnity_by_tier,
        "official_status": "computed" if official_margin is not None else "unavailable_without_dmc_market_inputs",
        "limitations": [
            "The simulated farm IOFC margin is not the official national DMC margin.",
            "Official DMC screening requires monthly USDA all-milk, corn, soybean-meal, and alfalfa prices.",
            "Eligibility, production history, sequestration, and payment determinations remain FSA decisions.",
        ],
    }
