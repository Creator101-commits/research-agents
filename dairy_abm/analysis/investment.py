from __future__ import annotations

from typing import Any

from dairy_abm.config import value
from dairy_abm.core import ConfigError


LOOP_LABELS = {
    "l1_nutrient": "L1 nutrient recovery",
    "l2_water": "L2 water recycling",
    "l3_energy": "L3 energy recovery",
    "l4_byproduct": "L4 processing and byproduct recovery",
}


def _annualize(total: float, observed_days: int) -> float:
    return total * 365.0 / observed_days if observed_days > 0 else 0.0


def _npv(cash_flows: list[float], discount_rate: float) -> float:
    if discount_rate <= -1.0:
        raise ConfigError("investment discount rate must be greater than -1")
    return sum(amount / (1.0 + discount_rate) ** year for year, amount in enumerate(cash_flows))


def _discounted_payback(capex: float, annual_net_benefit: float, rate: float, horizon: int) -> float | None:
    if capex <= 0.0 or annual_net_benefit <= 0.0:
        return None
    remaining = capex
    for year in range(1, horizon + 1):
        discounted = annual_net_benefit / (1.0 + rate) ** year
        if discounted >= remaining:
            return (year - 1) + remaining / discounted
        remaining -= discounted
    return None


def estimate_loop_capex(
    scenario: dict[str, Any], calibration: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    herd_size = max(0, int(scenario.get("herd_size", len(scenario.get("herd", [])) or 100)))
    cropland_ha = max(0.0, float(scenario.get("land_cropland_ha", value(calibration, "land.cropland_ha"))))
    cropland_acres = cropland_ha * 2.47105381
    estimates = {
        "l1_nutrient": (
            float(value(calibration, "farm_manager.investment.l1_nutrient_base_capex"))
            + cropland_acres * float(value(calibration, "farm_manager.investment.l1_nutrient_capex_per_acre"))
        ),
        "l2_water": float(value(calibration, "farm_manager.investment.l2_water_base_capex")),
        "l3_energy": (
            float(value(calibration, "farm_manager.investment.l3_energy_base_capex"))
            + herd_size * float(value(calibration, "farm_manager.investment.l3_energy_capex_per_animal_unit"))
        ),
        "l4_byproduct": herd_size * float(
            value(calibration, "farm_manager.investment.l4_processing_capex_per_cow")
        ),
    }
    enabled = {
        "l1_nutrient": bool(scenario.get("l1_nutrient_loop_enabled", value(calibration, "manure.l1_nutrient_loop_enabled"))),
        "l2_water": bool(scenario.get("l2_water_loop_enabled", value(calibration, "water.l2_water_loop_enabled"))),
        "l3_energy": bool(scenario.get("l3_energy_loop_enabled", value(calibration, "energy.l3_energy_loop_enabled"))),
        "l4_byproduct": bool(scenario.get("l4_byproduct_loop_enabled", value(calibration, "dairy_processor.l4_byproduct_loop_enabled")))
        and bool(scenario.get("enable_processor", value(calibration, "dairy_processor.enabled"))),
    }
    overrides = scenario.get("investment_capex_overrides", {})
    if not isinstance(overrides, dict):
        raise ConfigError("investment_capex_overrides must be an object")
    unknown = set(overrides) - set(LOOP_LABELS)
    if unknown:
        raise ConfigError(f"unknown investment capex override(s): {', '.join(sorted(unknown))}")

    sources = {
        "l1_nutrient": "USDA NRCS FY2026 EQIP payment schedule, nutrient-management design base plus per-acre implementation cost",
        "l2_water": "USDA NRCS FY2026 EQIP payment schedule, wastewater screw-pump base cost",
        "l3_energy": "USDA NRCS FY2026 EQIP payment schedule, modular biodigester plus covered-lagoon animal-unit cost",
        "l4_byproduct": "USDA SARE SW14-015 equipment cost divided by the documented 210-cow herd",
    }
    result: dict[str, dict[str, Any]] = {}
    for loop_id, estimate in estimates.items():
        if not enabled[loop_id]:
            result[loop_id] = {
                "enabled": False,
                "capex": 0.0,
                "capex_method": "disabled",
                "source": sources[loop_id],
            }
            continue
        if loop_id in overrides:
            capex = float(overrides[loop_id])
            if capex < 0.0:
                raise ConfigError(f"investment_capex_overrides.{loop_id} must be nonnegative")
            method = "scenario_override"
        else:
            capex = max(0.0, estimate)
            method = "screening_estimate"
        result[loop_id] = {
            "enabled": True,
            "capex": capex,
            "capex_method": method,
            "source": sources[loop_id],
        }
    return result


def analyze_investments(
    scenario: dict[str, Any], calibration: dict[str, Any], daily_records: list[dict[str, Any]]
) -> dict[str, Any]:
    """Calculate transparent loop-level and portfolio investment screening metrics."""
    observed_days = len(daily_records)
    horizon = int(scenario.get("investment_horizon_years", value(calibration, "farm_manager.investment.analysis_horizon_years")))
    if horizon <= 0:
        raise ConfigError("investment_horizon_years must be positive")
    discount_rate = float(scenario.get("investment_discount_rate", value(calibration, "farm_manager.discount_rate_annual")))
    if not 0.0 <= discount_rate <= 1.0:
        raise ConfigError("investment_discount_rate must be between 0 and 1")

    feed_price = float(value(calibration, "market.feed_cost_per_kg_dm"))
    water_price = float(value(calibration, "water.water_cost_per_l"))
    totals = {
        "l1_nutrient": sum(float(row.get("l1_feed_offset_kg", row.get("feed_loop_offset_kg", 0.0))) * float(row.get("feed_cost_per_kg_dm", feed_price)) for row in daily_records),
        "l2_water": sum(float(row.get("l2_water_offset_l", row.get("water_loop_offset_l", 0.0))) * water_price for row in daily_records),
        "l3_energy": sum(float(row.get("energy_value", 0.0)) + float(row.get("carbon_credit_value", 0.0)) for row in daily_records),
        "l4_byproduct": sum(
            max(0.0, float(row.get("processor_revenue", 0.0)) - float(row.get("raw_milk_revenue", row.get("milk_revenue", 0.0))))
            + float(row.get("byproduct_revenue", 0.0))
            - float(row.get("processing_energy_cost", 0.0))
            for row in daily_records
        ),
    }
    annual_om_overrides = scenario.get("investment_annual_om_overrides", {})
    if not isinstance(annual_om_overrides, dict):
        raise ConfigError("investment_annual_om_overrides must be an object")
    unknown_om = set(annual_om_overrides) - set(LOOP_LABELS)
    if unknown_om:
        raise ConfigError(f"unknown investment O&M override(s): {', '.join(sorted(unknown_om))}")

    capex = estimate_loop_capex(scenario, calibration)
    technologies: dict[str, dict[str, Any]] = {}
    for loop_id, label in LOOP_LABELS.items():
        annual_gross_benefit = _annualize(totals[loop_id], observed_days)
        annual_om = float(annual_om_overrides.get(loop_id, 0.0))
        if annual_om < 0.0:
            raise ConfigError(f"investment_annual_om_overrides.{loop_id} must be nonnegative")
        annual_net_benefit = annual_gross_benefit - annual_om
        basis = capex[loop_id]
        capital = float(basis["capex"])
        cash_flows = [-capital] + [annual_net_benefit] * horizon
        cumulative_net_return = sum(cash_flows)
        fifteen_year_roi = cumulative_net_return / capital if capital > 0.0 else None
        discounted_roi = (
            (_npv(cash_flows, discount_rate) / capital) if capital > 0.0 else None
        )
        technologies[loop_id] = {
            "label": label,
            **basis,
            "observed_days": observed_days,
            "annual_gross_benefit": annual_gross_benefit,
            "annual_operating_cost": annual_om,
            "annual_net_benefit": annual_net_benefit,
            "simple_annual_roi": annual_net_benefit / capital if capital > 0.0 else None,
            "simple_payback_years": capital / annual_net_benefit if capital > 0.0 and annual_net_benefit > 0.0 else None,
            "analysis_horizon_years": horizon,
            "cumulative_net_return": cumulative_net_return,
            "fifteen_year_roi": fifteen_year_roi if horizon == 15 else None,
            "horizon_roi": fifteen_year_roi,
            "npv": _npv(cash_flows, discount_rate),
            "discounted_roi": discounted_roi,
            "discounted_payback_years": _discounted_payback(capital, annual_net_benefit, discount_rate, horizon),
            "cash_flows": cash_flows,
            "quality": "scenario_override" if basis["capex_method"] == "scenario_override" else "screening_estimate",
        }

    portfolio_capex = sum(float(item["capex"]) for item in technologies.values())
    portfolio_annual_net = sum(float(item["annual_net_benefit"]) for item in technologies.values())
    portfolio_cash_flows = [-portfolio_capex] + [portfolio_annual_net] * horizon
    portfolio = {
        "capex": portfolio_capex,
        "annual_net_benefit": portfolio_annual_net,
        "simple_payback_years": portfolio_capex / portfolio_annual_net if portfolio_capex > 0.0 and portfolio_annual_net > 0.0 else None,
        "simple_annual_roi": portfolio_annual_net / portfolio_capex if portfolio_capex > 0.0 else None,
        "cumulative_net_return": sum(portfolio_cash_flows),
        "fifteen_year_roi": sum(portfolio_cash_flows) / portfolio_capex if portfolio_capex > 0.0 and horizon == 15 else None,
        "horizon_roi": sum(portfolio_cash_flows) / portfolio_capex if portfolio_capex > 0.0 else None,
        "npv": _npv(portfolio_cash_flows, discount_rate),
        "discounted_roi": _npv(portfolio_cash_flows, discount_rate) / portfolio_capex if portfolio_capex > 0.0 else None,
        "discounted_payback_years": _discounted_payback(portfolio_capex, portfolio_annual_net, discount_rate, horizon),
        "cash_flows": portfolio_cash_flows,
    }
    return {
        "method": "farm-scale screening estimate",
        "currency_year": 2026,
        "observed_days": observed_days,
        "annualization_days": 365,
        "analysis_horizon_years": horizon,
        "discount_rate": discount_rate,
        "technologies": technologies,
        "portfolio": portfolio,
        "limitations": [
            "Capital estimates are screening bases, not vendor quotes or engineering bids.",
            "Annual operating costs include simulated stream-specific costs plus any explicit O&M overrides; unconfigured maintenance, financing, taxes, depreciation, and grants are excluded.",
            "Fifteen-year ROI is cumulative undiscounted net return divided by initial capital; NPV and discounted ROI are reported separately.",
        ],
    }
