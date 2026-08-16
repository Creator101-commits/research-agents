"""Serialize simulation contexts into the dashboard data contract.

The simulation and official reports remain authoritative. This module only
selects and aggregates their existing outputs for the web client.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from dairy_abm.analysis.npv import DEFAULT_DISCOUNT_RATE, npv
from dairy_abm.config import calibration_inventory
from dairy_abm.core import SimulationContext
from dairy_abm.reports import REPORT_CONTRACT


DASHBOARD_DAILY_FIELDS = (
    "day",
    "milk_l",
    "dmi_kg",
    "purchased_feed_kg_dm",
    "irrigation_l",
    "net_kwh",
    "feedstock_tons",
    "electricity_generated_kwh",
    "biogas_volume_m3",
    "biogas_gross_kwh",
    "heat_generated_mj",
    "energy_self_sufficiency_pct",
    "freshwater_withdrawal_l",
    "recycled_irrigation_l",
    "recycled_irrigation_fraction",
    "gross_kg_co2e",
    "avoided_kg_co2e",
    "net_kg_co2e",
    "kg_co2e_per_l_milk",
    "input_circularity",
    "output_circularity",
    "circularity_score",
    "environment_nue",
    "soil_carbon_delta_kg",
    "synthetic_fertilizer_saved_kg",
    "sustainability_score_0_100",
    "new_disease_cases",
    "active_disease_cases",
    "disease_economic_cost",
    "cow_count",
    "total_revenue",
    "total_cost",
    "profit",
    "report_confidence",
)

DASHBOARD_COW_FIELDS = (
    "id",
    "milk_l",
    "dmi_kg",
    "fcr_kg_dm_per_l",
    "days_in_milk",
    "parity",
    "body_weight_kg",
    "body_condition_score",
    "health_status",
    "infection_state",
    "disease",
    "alive",
    "quarantine_flag",
    "rumen_ph",
    "sara_active",
    "pregnant",
    "days_pregnant",
    "observed_dmi_kg",
    "actual_dmi_kg_dm",
    "expected_dmi_eq2_1_kg_dm",
    "estrus_detected",
    "feed_efficiency_trait",
    "trait_vector",
    "enteric_ch4_kg",
    "methane_intensity_kg_ch4_per_l",
)

DASHBOARD_ENVIRONMENT_FIELDS = (
    "day",
    "gross_kg_co2e",
    "avoided_kg_co2e",
    "net_kg_co2e",
    "milk_l",
    "milk_protein_kg",
    "kg_co2e_per_l_milk",
    "kg_co2e_per_kg_milk_protein",
    "energy_offset_kg_co2e",
    "fertilizer_offset_kg_co2e",
    "soil_carbon_offset_kg_co2e",
    "soil_carbon_delta_kg",
    "soil_organic_carbon_pct",
    "synthetic_fertilizer_saved_kg",
    "NUE",
    "circularity_score",
    "ICirc",
    "OCirc",
    "sustainability_score_0_100",
    "carbon_credit_value",
    "carbon_credit_price_per_tonne_co2e",
    "soil_biodiversity_index",
    "use_count",
    "cycle_count",
)

_ENVIRONMENT_METRICS: dict[str, tuple[Any, str, str]] = {
    "gross_kg_co2e": ("gross_kg_co2e", "kg CO2e", "sum"),
    "avoided_kg_co2e": ("avoided_kg_co2e", "kg CO2e", "sum"),
    "net_kg_co2e": ("net_kg_co2e", "kg CO2e", "sum"),
    "ghg_intensity": (("net_kg_co2e", "milk_l"), "kg CO2e/L milk", "ratio_of_sums"),
    "ghg_intensity_protein": (("net_kg_co2e", "milk_protein_kg"), "kg CO2e/kg milk protein", "ratio_of_sums"),
    "soil_carbon_delta_kg": ("soil_carbon_delta_kg", "kg C", "sum"),
    "synthetic_fertilizer_saved_kg": ("synthetic_fertilizer_saved_kg", "kg N", "sum"),
    "nue": ("NUE", "fraction", "mean"),
    "circularity_score": ("circularity_score", "fraction", "mean"),
    "input_circularity": ("ICirc", "fraction", "mean"),
    "output_circularity": ("OCirc", "fraction", "mean"),
    "sustainability_score_0_100": ("sustainability_score_0_100", "score 0-100", "mean"),
    "carbon_credit_value": ("carbon_credit_value", "currency", "sum"),
    "soil_organic_carbon_pct": ("soil_organic_carbon_pct", "%", "latest"),
    "soil_biodiversity_index": ("soil_biodiversity_index", "index", "latest"),
}

DASHBOARD_ECONOMICS_FIELDS = (
    "day",
    "milk_revenue",
    "processor_revenue",
    "byproduct_revenue",
    "energy_value",
    "carbon_credit_value",
    "total_revenue",
    "feed_cost",
    "water_cost",
    "treatment_cost",
    "disease_economic_cost",
    "cooling_cost",
    "processing_energy_cost",
    "labor_cost",
    "fixed_cost",
    "total_cost",
    "profit",
    "cumulative_profit",
    "cash_balance",
)

_ECONOMICS_METRICS: dict[str, tuple[str, str, str]] = {
    "milk_revenue": ("milk_revenue", "currency", "sum"),
    "processor_revenue": ("processor_revenue", "currency", "sum"),
    "byproduct_revenue": ("byproduct_revenue", "currency", "sum"),
    "energy_value": ("energy_value", "currency", "sum"),
    "carbon_credit_value": ("carbon_credit_value", "currency", "sum"),
    "total_revenue": ("total_revenue", "currency", "sum"),
    "feed_cost": ("feed_cost", "currency", "sum"),
    "water_cost": ("water_cost", "currency", "sum"),
    "treatment_cost": ("treatment_cost", "currency", "sum"),
    "disease_economic_cost": ("disease_economic_cost", "currency", "sum"),
    "cooling_cost": ("cooling_cost", "currency", "sum"),
    "processing_energy_cost": ("processing_energy_cost", "currency", "sum"),
    "labor_cost": ("labor_cost", "currency", "sum"),
    "fixed_cost": ("fixed_cost", "currency", "sum"),
    "total_cost": ("total_cost", "currency", "sum"),
    "profit": ("profit", "currency", "sum"),
    "cumulative_profit": ("cumulative_profit", "currency", "latest"),
    "cash_balance": ("cash_balance", "currency", "latest"),
}

_ECONOMICS_LATEST_FIELDS = (
    "milk_revenue",
    "raw_milk_revenue",
    "processor_revenue",
    "byproduct_revenue",
    "energy_value",
    "carbon_credit_value",
    "feed_cost",
    "water_cost",
    "treatment_cost",
    "disease_cost",
    "cooling_cost",
    "processing_energy_cost",
    "labor_cost",
    "fixed_cost",
    "total_revenue",
    "total_cost",
    "profit",
    "cash_balance",
    "annual_circular_benefit",
    "investment_cost_basis",
    "roi_circular_investment",
    "payback_period_years",
    "recommendation",
    "ranked_recommendations",
    "actionable_recommendations",
    "policy_change_triggers",
    "policy_conflicts",
    "automatic_policy_actions",
    "operating_point",
    "objective_weights",
    "effective_policy",
)
DASHBOARD_EQUIPMENT_FIELDS = (
    "id",
    "label",
    "capex",
    "annual_benefit",
    "roi",
    "payback_years",
    "npv",
    "status",
)
DASHBOARD_MODEL_DETAILS_FIELDS = (
    "scenario",
    "start_date",
    "days",
    "seed",
    "herd_size",
    "enabled_systems",
    "loop_states",
    "run_duration_s",
    "calibration_override_count",
    "assumption_count",
    "warnings",
    "policy_summary",
    "event_count",
    "report_contract",
    "scheduler",
)
DASHBOARD_EXPORT_FIELDS = (
    "id",
    "label",
    "filename",
    "content_type",
    "endpoint",
)
_EXPORT_ARTIFACT_DEFINITIONS = (
    ("summary", "Summary JSON", "summary.json", "application/json"),
    ("daily", "Daily CSV", "daily.csv", "text/csv"),
    ("schedule", "Schedule CSV", "schedule.csv", "text/csv"),
    ("monthly", "Monthly CSV", "monthly.csv", "text/csv"),
    ("annual", "Annual CSV", "annual.csv", "text/csv"),
    ("calibration", "Calibration Inventory", "calibration_inventory.json", "application/json"),
)


_EQUIPMENT_LABELS = {
    "milking_parlour_bulk_tank": "Milking parlour / bulk tank",
    "dairy_processor": "Dairy processor",
    "whey_processor": "Whey processor",
    "manure_system": "Manure system",
}




_SUMMARY_DEFINITIONS: dict[str, tuple[Any, str, str]] = {
    "milk": ("milk_l", "L", "sum"),
    "average_milk_per_cow": (("milk_l", "cow_count"), "L/cow/day", "mean_ratio"),
    "net_co2e": ("net_kg_co2e", "kg CO2e", "sum"),
    "ghg_intensity": (("net_kg_co2e", "milk_l"), "kg CO2e/L milk", "ratio_of_sums"),
    "fcr": (("dmi_kg", "milk_l"), "kg DM/L milk", "ratio_of_sums"),
    "profit": ("profit", "currency", "sum"),
    "total_revenue": ("total_revenue", "currency", "sum"),
    "total_cost": ("total_cost", "currency", "sum"),
    "energy_avg": ("energy_self_sufficiency_pct", "%", "mean"),
    "freshwater": ("freshwater_withdrawal_l", "L", "sum"),
    "circularity": ("circularity_score", "fraction", "mean"),
    "sustainability_avg": ("sustainability_score_0_100", "score 0-100", "mean"),
    "disease_cases": ("active_disease_cases", "cases", "latest"),
    "herd_size": ("cow_count", "cows", "latest"),
}
_SERIES_AGGREGATIONS: dict[str, tuple[Any, str]] = {
    "milk_l": ("milk_l", "sum"),
    "dmi_kg": ("dmi_kg", "sum"),
    "purchased_feed_kg_dm": ("purchased_feed_kg_dm", "sum"),
    "irrigation_l": ("irrigation_l", "sum"),
    "net_kwh": ("net_kwh", "sum"),
    "feedstock_tons": ("feedstock_tons", "sum"),
    "electricity_generated_kwh": ("electricity_generated_kwh", "sum"),
    "biogas_volume_m3": ("biogas_volume_m3", "sum"),
    "biogas_gross_kwh": ("biogas_gross_kwh", "sum"),
    "heat_generated_mj": ("heat_generated_mj", "sum"),
    "energy_self_sufficiency_pct": ("energy_self_sufficiency_pct", "mean"),
    "freshwater_withdrawal_l": ("freshwater_withdrawal_l", "sum"),
    "recycled_irrigation_l": ("recycled_irrigation_l", "sum"),
    "recycled_irrigation_fraction": (("recycled_irrigation_l", "irrigation_l"), "ratio_of_sums"),
    "gross_kg_co2e": ("gross_kg_co2e", "sum"),
    "avoided_kg_co2e": ("avoided_kg_co2e", "sum"),
    "net_kg_co2e": ("net_kg_co2e", "sum"),
    "kg_co2e_per_l_milk": (("net_kg_co2e", "milk_l"), "ratio_of_sums"),
    "input_circularity": ("input_circularity", "mean"),
    "output_circularity": ("output_circularity", "mean"),
    "circularity_score": ("circularity_score", "mean"),
    "environment_nue": ("environment_nue", "mean"),
    "soil_carbon_delta_kg": ("soil_carbon_delta_kg", "sum"),
    "synthetic_fertilizer_saved_kg": ("synthetic_fertilizer_saved_kg", "sum"),
    "sustainability_score_0_100": ("sustainability_score_0_100", "mean"),
    "new_disease_cases": ("new_disease_cases", "sum"),
    "active_disease_cases": ("active_disease_cases", "latest"),
    "disease_economic_cost": ("disease_economic_cost", "sum"),
    "cow_count": ("cow_count", "latest"),
    "total_revenue": ("total_revenue", "sum"),
    "total_cost": ("total_cost", "sum"),
    "profit": ("profit", "sum"),
}

_PERIOD_REPORT_FIELD_ALIASES = {
    "mean_circularity_score": "circularity_score",
    "mean_sustainability_score_0_100": "sustainability_score_0_100",
}

_FEATURE_DEFINITIONS = {
    "enable_processor": ("enable_processor", "dairy_processor.enabled"),
    "enable_whey_processing": (
        "enable_whey_processing",
        "dairy_processor.whey_processing_enabled",
    ),
    "enable_land_agent": ("enable_land_agent", "land.enabled"),
    "l1_nutrient_loop_enabled": (
        "l1_nutrient_loop_enabled",
        "manure.l1_nutrient_loop_enabled",
    ),
    "l2_water_loop_enabled": (
        "l2_water_loop_enabled",
        "water.l2_water_loop_enabled",
    ),
    "l3_energy_loop_enabled": (
        "l3_energy_loop_enabled",
        "energy.l3_energy_loop_enabled",
    ),
    "l4_byproduct_loop_enabled": (
        "l4_byproduct_loop_enabled",
        "dairy_processor.l4_byproduct_loop_enabled",
    ),
}


def _calibration_value_from_mapping(
    calibration: dict[str, Any], dotted_key: str, default: Any = None
) -> Any:
    node: Any = calibration
    try:
        for part in dotted_key.split("."):
            node = node[part]
    except (KeyError, TypeError):
        return default
    return node.get("value", default) if isinstance(node, dict) else node




def _feature_flags_for(
    scenario: dict[str, Any], calibration: dict[str, Any]
) -> dict[str, bool]:
    return {
        name: bool(scenario.get(scenario_key, _calibration_value_from_mapping(calibration, calibration_key, False)))
        for name, (scenario_key, calibration_key) in _FEATURE_DEFINITIONS.items()
    }


def _feature_flags(ctx: SimulationContext) -> dict[str, bool]:
    return _feature_flags_for(ctx.scenario, ctx.calibration)


def serialize_dashboard_config(
    default_scenario: dict[str, Any],
    calibration: dict[str, Any],
    scenario_names: list[str],
    report_contract: dict[str, Any],
) -> dict[str, Any]:
    """Build UI-safe configuration without exposing nested calibration values."""
    return {
        "default_scenario": deepcopy(default_scenario),
        "scenarios": list(scenario_names),
        "feature_flags": _feature_flags_for(default_scenario, calibration),
        "limits": {"min_days": 1, "max_days": 3650, "max_cached_runs": 10},
        "report_contract": deepcopy(report_contract),
        "ui_capabilities": {
            "run": True,
            "comparison": True,
            "calibration_inventory": True,
            "export": True,
        },
    }


def _comparison_value(payload: dict[str, Any], key: str) -> Any:
    summary = payload.get("summary", {})
    metric = summary.get(key)
    if isinstance(metric, dict):
        return metric.get("value")
    return payload.get("metrics", {}).get(key)


def serialize_comparison(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Return complete cached run payloads plus display-safe metric deltas."""
    if len(runs) < 2:
        raise ValueError("comparison requires at least two runs")

    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(runs):
        payload = item.get("result") if isinstance(item.get("result"), dict) else item
        if not isinstance(payload, dict):
            raise ValueError("comparison runs must be dashboard payloads")
        entry = deepcopy(payload)
        entry["label"] = item.get("label") or entry.get("label") or f"Run {index + 1}"
        normalized.append(entry)

    baseline = normalized[0]
    deltas: list[dict[str, Any]] = []
    for candidate in normalized[1:]:
        metrics: dict[str, dict[str, Any]] = {}
        for key, (_field, unit, _operation) in _SUMMARY_DEFINITIONS.items():
            baseline_value = _comparison_value(baseline, key)
            candidate_value = _comparison_value(candidate, key)
            numeric = all(
                isinstance(value_, (int, float)) and not isinstance(value_, bool)
                for value_ in (baseline_value, candidate_value)
            )
            absolute = candidate_value - baseline_value if numeric else None
            percentage = (
                absolute / baseline_value * 100.0
                if numeric and baseline_value != 0
                else None
            )
            metrics[key] = {
                "unit": unit,
                "baseline": baseline_value,
                "value": candidate_value,
                "absolute": absolute,
                "percentage": percentage,
            }
        deltas.append(
            {
                "baseline_run_id": baseline.get("run_id", baseline.get("id")),
                "run_id": candidate.get("run_id", candidate.get("id")),
                "metrics": metrics,
            }
        )

    return {
        "runs": normalized,
        "baseline_run_id": baseline.get("run_id", baseline.get("id")),
        "deltas": deltas,
    }


def _initial_herd_size(ctx: SimulationContext) -> int | None:
    herd = ctx.scenario.get("herd")
    if isinstance(herd, list):
        return len(herd)
    herd_size = ctx.scenario.get("herd_size")
    return herd_size if isinstance(herd_size, int) and not isinstance(herd_size, bool) else herd_size


def _aggregate(rows: list[dict[str, Any]], field: Any, operation: str) -> Any:
    if operation == "latest":
        key = field
        return next((row.get(key) for row in reversed(rows) if row.get(key) is not None), None)

    if operation in {"mean_ratio", "ratio_of_sums"}:
        numerator_key, denominator_key = field
        pairs = [
            (row.get(numerator_key), row.get(denominator_key))
            for row in rows
            if row.get(numerator_key) is not None
            and row.get(denominator_key) is not None
            and row.get(denominator_key) > 0
        ]
        if not pairs:
            return None
        if operation == "mean_ratio":
            return sum(numerator / denominator for numerator, denominator in pairs) / len(pairs)
        denominator = sum(denominator for _, denominator in pairs)
        return sum(numerator for numerator, _ in pairs) / denominator if denominator else None

    values = [row.get(field) for row in rows if row.get(field) is not None]
    if not values:
        return None
    if operation == "sum":
        return sum(values)
    return sum(values) / len(values)


def _metric(
    value_: Any,
    unit: str,
    source: str,
    aggregation: str,
    *,
    confidence: str | None = None,
    quality: str | None = None,
) -> dict[str, Any]:
    available = value_ is not None
    result: dict[str, Any] = {
        "value": value_,
        "unit": unit,
        "available": available,
        "source": source,
        "aggregation": aggregation,
    }
    if confidence is not None:
        result["confidence"] = confidence
    if quality is not None:
        result["quality"] = quality
    if not available:
        result["reason"] = "no data for selected run"
    return result


def _packet_provenance(packet: Any) -> dict[str, Any] | None:
    if packet is None:
        return None
    day = packet.day.isoformat() if hasattr(packet.day, "isoformat") else packet.day
    return {
        "source": packet.source,
        "name": packet.name,
        "day": day,
        "date": day,
        "period": packet.period,
        "quality": packet.quality,
        "confidence": packet.confidence,
        "stream_id": packet.stream_id,
    }


def _history_provenance(
    history_name: str, rows: list[dict[str, Any]], packet: Any = None
) -> dict[str, Any] | None:
    provenance = _packet_provenance(packet)
    if not rows and provenance is None:
        return None
    if provenance is None:
        days = [row.get("day") for row in rows if row.get("day") is not None]
        provenance = {
            "source": f'ctx.state["{history_name}"]',
            "name": history_name,
            "day": days[-1] if days else None,
            "date": days[-1] if days else None,
            "period": "daily",
            "quality": "history",
            "confidence": _period_confidence(rows),
            "stream_id": None,
        }
    provenance["history_source"] = f'ctx.state["{history_name}"]'
    provenance["coverage"] = {
        "rows": len(rows),
        "start": rows[0].get("day") if rows else None,
        "end": rows[-1].get("day") if rows else None,
    }
    return provenance


def _metric_from_provenance(
    value_: Any,
    unit: str,
    source: str,
    aggregation: str,
    provenance: dict[str, Any] | None,
) -> dict[str, Any]:
    return _metric(
        value_,
        unit,
        source,
        aggregation,
        confidence=provenance.get("confidence") if provenance else None,
        quality=provenance.get("quality") if provenance else None,
    )


def _history_metric(
    history_name: str,
    rows: list[dict[str, Any]],
    field: Any,
    unit: str,
    aggregation: str,
    packet: Any = None,
) -> dict[str, Any]:
    provenance = _history_provenance(history_name, rows, packet)
    return _metric_from_provenance(
        _aggregate(rows, field, aggregation),
        unit,
        f'ctx.state["{history_name}"]',
        aggregation,
        provenance,
    )


def _daily_loop_metric(
    ctx: SimulationContext,
    field: Any,
    unit: str,
    aggregation: str,
    packet_name: str | None = None,
) -> dict[str, Any]:
    packet = ctx.get_packet(packet_name) if packet_name else None
    provenance = _history_provenance("daily_records", ctx.daily_records, packet)
    return _metric_from_provenance(
        _aggregate(ctx.daily_records, field, aggregation),
        unit,
        "ctx.daily_records",
        aggregation,
        provenance,
    )


def _packet_metric(
    ctx: SimulationContext,
    packet_name: str,
    field: str,
    unit: str,
    aggregation: str = "latest",
) -> dict[str, Any]:
    packet = ctx.get_packet(packet_name)
    provenance = _packet_provenance(packet)
    value_ = packet.payload.get(field) if packet is not None else None
    return _metric_from_provenance(
        deepcopy(value_),
        unit,
        f'ctx.packets["{packet_name}"].payload.{field}',
        aggregation,
        provenance,
    )


def _loop_section(
    enabled: bool,
    has_data: bool,
    metrics: dict[str, dict[str, Any]],
    provenance: list[dict[str, Any]],
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = "active" if enabled and has_data else "inactive" if has_data else "unavailable"
    return {
        "state": state,
        "enabled": bool(enabled),
        "metrics": metrics,
        "details": deepcopy(details or {}),
        "provenance": deepcopy(provenance),
    }


def _combined_loop_state(*sections: dict[str, Any]) -> str:
    states = {section["state"] for section in sections}
    if "unavailable" in states:
        return "unavailable"
    if "active" in states:
        return "active"
    return "inactive"


def _build_loop_flow(
    ctx: SimulationContext,
    l1: dict[str, Any],
    l2: dict[str, Any],
    l3: dict[str, Any],
    l4: dict[str, Any],
) -> dict[str, Any]:
    data = bool(ctx.daily_records)
    processor = ctx.get_packet("processor_packet")
    processor_has_data = processor is not None
    whey_value = processor.payload.get("whey_l") if processor is not None else None
    combined_l1_l3 = _combined_loop_state(l1, l3)
    combined_l1_l2 = _combined_loop_state(l1, l2)
    nodes = [
        {"id": "cow", "label": "Cow", "state": "active" if data else "unavailable"},
        {"id": "milk", "label": "Milk", "state": "active" if data else "unavailable", "unit": "L/day"},
        {"id": "processor", "label": "Processor", "state": l4["state"]},
        {
            "id": "whey",
            "label": "Whey",
            "state": l4["state"] if whey_value is not None else "unavailable",
            "unit": "L/day",
        },
        {"id": "feed", "label": "Feed", "state": "active" if data else "unavailable", "unit": "kg DM/day"},
        {"id": "manure", "label": "Manure", "state": l1["state"], "unit": "kg/day"},
        {"id": "digester", "label": "Digester", "state": combined_l1_l3, "unit": "kg / m3"},
        {"id": "energy", "label": "Energy", "state": l3["state"], "unit": "kWh/day"},
        {"id": "water-treatment", "label": "Water Treatment", "state": l2["state"], "unit": "L/day"},
        {"id": "crops", "label": "Crops", "state": combined_l1_l2, "unit": "kg N / L"},
    ]
    edges = [
        {"source": "cow", "target": "milk", "label": "milk output", "unit": "L/day", "state": "active" if data else "unavailable"},
        {"source": "cow", "target": "manure", "label": "manure", "unit": "kg/day", "state": l1["state"]},
        {"source": "milk", "target": "processor", "label": "raw milk", "unit": "L/day", "state": l4["state"]},
        {"source": "manure", "target": "digester", "label": "digester route", "unit": "kg/day", "state": l1["state"]},
        {"source": "manure", "target": "crops", "label": "nutrient return", "unit": "kg N/day", "state": l1["state"]},
        {"source": "digester", "target": "energy", "label": "biogas", "unit": "m3/day", "state": combined_l1_l3},
        {"source": "water-treatment", "target": "crops", "label": "recycled irrigation", "unit": "L/day", "state": l2["state"]},
        {"source": "energy", "target": "feed", "label": "energy return", "unit": "kWh/day", "state": l3["state"]},
        {"source": "processor", "target": "whey", "label": "whey", "unit": "L/day", "state": l4["state"] if processor_has_data else "unavailable"},
        {"source": "whey", "target": "feed", "label": "feed return", "unit": "L / kg DM", "state": l4["state"] if whey_value is not None else "unavailable"},
    ]
    return {"nodes": nodes, "edges": edges}


def _build_loop_sections(ctx: SimulationContext) -> dict[str, Any]:
    features = _feature_flags(ctx)
    daily = ctx.daily_records
    manure_rows = ctx.state.get("manure_flow_history", [])
    water_rows = ctx.state.get("water_history", [])
    energy_rows = ctx.state.get("energy_history", [])
    manure_rows = manure_rows if isinstance(manure_rows, list) else []
    water_rows = water_rows if isinstance(water_rows, list) else []
    energy_rows = energy_rows if isinstance(energy_rows, list) else []
    manure_packet = ctx.get_packet("manure_packet")
    water_packet = ctx.get_packet("water_packet")
    energy_packet = ctx.get_packet("energy_packet")
    processor_packet = ctx.get_packet("processor_packet")
    residual_packet = ctx.get_packet("processor_residual_packet")
    return_packet = ctx.get_packet("dairy_return_feed_packet")

    l1 = _loop_section(
        features["l1_nutrient_loop_enabled"],
        bool(manure_rows or manure_packet),
        {
            "manure_kg": _history_metric("manure_flow_history", manure_rows, "manure_kg", "kg", "sum", manure_packet),
            "digester_kg": _history_metric("manure_flow_history", manure_rows, "digester_kg", "kg", "sum", manure_packet),
            "compost_kg": _history_metric("manure_flow_history", manure_rows, "compost_kg", "kg", "sum", manure_packet),
            "storage_kg": _history_metric("manure_flow_history", manure_rows, "storage_kg", "kg", "sum", manure_packet),
            "digestate_n_kg": _history_metric("manure_flow_history", manure_rows, "digestate_n_kg", "kg N", "sum", manure_packet),
            "digestate_p_kg": _history_metric("manure_flow_history", manure_rows, "digestate_p_kg", "kg P", "sum", manure_packet),
            "digestate_k_kg": _history_metric("manure_flow_history", manure_rows, "digestate_k_kg", "kg K", "sum", manure_packet),
            "compost_n_kg": _history_metric("manure_flow_history", manure_rows, "compost_n_kg", "kg N", "sum", manure_packet),
            "compost_p_kg": _history_metric("manure_flow_history", manure_rows, "compost_p_kg", "kg P", "sum", manure_packet),
            "compost_k_kg": _history_metric("manure_flow_history", manure_rows, "compost_k_kg", "kg K", "sum", manure_packet),
            "nutrient_return_kg": _history_metric("manure_flow_history", manure_rows, "nutrient_return_kg", "kg N", "sum", manure_packet),
            "feed_loop_offset_kg": _daily_loop_metric(ctx, "feed_loop_offset_kg", "kg DM", "sum", "feed_crop_packet"),
            "synthetic_fertilizer_saved_kg": _daily_loop_metric(ctx, "synthetic_fertilizer_saved_kg", "kg N", "sum", "environment_packet"),
        },
        [item for item in (_packet_provenance(manure_packet),) if item is not None],
        {
            "route_alerts": [row["manure_route_alert"] for row in manure_rows if row.get("manure_route_alert")],
            "digester_feedstock_feasible": [row.get("digester_feedstock_feasible") for row in manure_rows],
        },
    )

    l2 = _loop_section(
        features["l2_water_loop_enabled"],
        bool(water_rows or water_packet),
        {
            "total_water_use_l": _history_metric("water_history", water_rows, "total_water_use_l", "L", "sum", water_packet),
            "net_water_l": _daily_loop_metric(ctx, "net_water_l", "L", "sum", "water_packet"),
            "freshwater_withdrawal_l": _daily_loop_metric(ctx, "freshwater_withdrawal_l", "L", "sum", "water_packet"),
            "recycled_irrigation_l": _history_metric("water_history", water_rows, "recycled_irrigation_l", "L", "sum", water_packet),
            "recycled_irrigation_fraction": _history_metric("water_history", water_rows, ("recycled_irrigation_l", "irrigation_demand_l"), "fraction", "ratio_of_sums", water_packet),
            "water_saving_l": _history_metric("water_history", water_rows, "water_saving_l", "L", "sum", water_packet),
            "recovered_n_kg": _history_metric("water_history", water_rows, "recovered_n_kg", "kg N", "sum", water_packet),
            "recovered_p_kg": _history_metric("water_history", water_rows, "recovered_p_kg", "kg P", "sum", water_packet),
            "recovered_k_kg": _history_metric("water_history", water_rows, "recovered_k_kg", "kg K", "sum", water_packet),
            "water_use_l_per_litre_milk": _history_metric("water_history", water_rows, ("total_water_use_l", "milk_l"), "L/L milk", "ratio_of_sums", water_packet),
        },
        [item for item in (_packet_provenance(water_packet),) if item is not None],
        {
            "treatment_active": water_rows[-1].get("treatment_active") if water_rows else None,
            "treatment_capacity_l_per_day": water_rows[-1].get("treatment_capacity_l_per_day") if water_rows else None,
            "wastewater_storage_l": water_rows[-1].get("wastewater_storage_l") if water_rows else None,
        },
    )

    l3 = _loop_section(
        features["l3_energy_loop_enabled"],
        bool(energy_rows or energy_packet),
        {
            "feedstock_tons": _history_metric("energy_history", energy_rows, "feedstock_tons", "tonnes", "sum", energy_packet),
            "biogas_volume_m3": _history_metric("energy_history", energy_rows, "biogas_volume_m3", "m3", "sum", energy_packet),
            "biogas_gross_kwh": _history_metric("energy_history", energy_rows, "biogas_gross_kwh", "kWh", "sum", energy_packet),
            "electricity_generated_kwh": _history_metric("energy_history", energy_rows, "electricity_generated_kwh", "kWh", "sum", energy_packet),
            "net_kwh": _history_metric("energy_history", energy_rows, "net_kwh", "kWh", "sum", energy_packet),
            "heat_generated_mj": _history_metric("energy_history", energy_rows, "heat_generated_mj", "MJ", "sum", energy_packet),
            "energy_self_sufficiency_pct": _history_metric("energy_history", energy_rows, "energy_self_sufficiency_pct", "%", "mean", energy_packet),
            "energy_value": _history_metric("energy_history", energy_rows, "energy_value", "currency", "sum", energy_packet),
            "energy_offset_kg_co2e": _daily_loop_metric(ctx, "energy_offset_kg_co2e", "kg CO2e", "sum", "energy_offset_packet"),
        },
        [item for item in (_packet_provenance(energy_packet),) if item is not None],
        {
            "conversion_mode": energy_rows[-1].get("conversion_mode") if energy_rows else None,
            "solar_generated_kwh": _aggregate(energy_rows, "solar_generated_kwh", "sum"),
            "thermochemical_input_kwh": _aggregate(energy_rows, "thermochemical_input_kwh", "sum"),
            "gross_kwh": _aggregate(energy_rows, "gross_kwh", "sum"),
        },
    )

    l4_enabled = features["l4_byproduct_loop_enabled"] and features["enable_processor"]
    l4 = _loop_section(
        l4_enabled,
        processor_packet is not None,
        {
            "milk_processed_l": _daily_loop_metric(ctx, "milk_processed_l", "L", "sum", "processor_packet"),
            "whey_l": _daily_loop_metric(ctx, "whey_l", "L", "sum", "processor_packet"),
            "scotta_l": _packet_metric(ctx, "processor_packet", "scotta_output_l", "L", "latest"),
            "sludge_l": _packet_metric(ctx, "processor_packet", "sludge_l", "L", "latest"),
            "waste_milk_l": _packet_metric(ctx, "processor_packet", "waste_milk_l", "L", "latest"),
            "valorized_residual_l": _packet_metric(ctx, "processor_packet", "valorized_residual_l", "L", "latest"),
            "byproduct_revenue": _packet_metric(ctx, "processor_packet", "byproduct_revenue", "currency", "latest"),
            "whey_feed_l": _packet_metric(ctx, "processor_residual_packet", "whey_feed_l", "L", "latest"),
            "scotta_feed_l": _packet_metric(ctx, "processor_residual_packet", "scotta_feed_l", "L", "latest"),
            "waste_milk_feed_l": _packet_metric(ctx, "processor_residual_packet", "waste_milk_feed_l", "L", "latest"),
            "feed_eligible_kg_dm": _packet_metric(ctx, "dairy_return_feed_packet", "feed_eligible_kg_dm", "kg DM", "latest"),
        },
        [item for item in (_packet_provenance(processor_packet), _packet_provenance(residual_packet), _packet_provenance(return_packet)) if item is not None],
        {
            "processor_quality": processor_packet.quality if processor_packet else None,
            "quality_approved": processor_packet.payload.get("quality_approved") if processor_packet else None,
            "product_streams_l": deepcopy(processor_packet.payload.get("product_streams_l")) if processor_packet else None,
            "route_tiers": deepcopy(processor_packet.payload.get("route_tiers")) if processor_packet else None,
            "food_safety_approved": return_packet.payload.get("food_safety_approved") if return_packet else None,
        },
    )
    loops = {"l1": l1, "l2": l2, "l3": l3, "l4": l4}
    loops["flow"] = _build_loop_flow(ctx, l1, l2, l3, l4)
    return loops

def _environment_daily_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {field: deepcopy(row.get(field)) for field in DASHBOARD_ENVIRONMENT_FIELDS}
        for row in rows
    ]


def _environment_ledger_rows(
    ctx: SimulationContext, history: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    ledger = ctx.state.get("environment_ledger", {})
    packets = ledger.values() if isinstance(ledger, dict) else []
    for packet in packets:
        payload = packet.payload if isinstance(getattr(packet, "payload", None), dict) else {}
        day = packet.day.isoformat() if hasattr(packet.day, "isoformat") else packet.day
        rows.append(
            {
                "date": day,
                "source": packet.source,
                "stream_id": packet.stream_id or payload.get("stream_id"),
                "direction": payload.get("direction"),
                "value": deepcopy(payload.get("kg_co2e")),
                "unit": payload.get("unit", "kg CO2e"),
                "period": packet.period,
                "quality": packet.quality,
                "confidence": packet.confidence,
                "name": packet.name,
            }
        )
    if not rows:
        for history_row in history:
            for stream in history_row.get("environmental_streams", []):
                if not isinstance(stream, dict):
                    continue
                rows.append(
                    {
                        "date": history_row.get("day"),
                        "source": stream.get("source"),
                        "stream_id": stream.get("stream_id"),
                        "direction": stream.get("direction"),
                        "value": deepcopy(stream.get("kg_co2e")),
                        "unit": stream.get("unit", "kg CO2e"),
                        "period": stream.get("period", "daily"),
                        "quality": "history",
                        "confidence": "estimated",
                        "name": "environment_stream",
                    }
                )
    rows.sort(key=lambda row: (str(row.get("date") or ""), str(row.get("source") or ""), str(row.get("stream_id") or "")))
    return rows


def _build_environment_audit(ctx: SimulationContext) -> dict[str, Any]:
    history = ctx.state.get("environment_history", [])
    history = history if isinstance(history, list) else []
    environment_packet = ctx.get_packet("environment_packet")
    report_packet = ctx.get_packet("environment_report_packet")
    monthly: list[dict[str, Any]] = []
    for row in ctx.monthly_records:
        if not isinstance(row, dict) or row.get("report") != "environment":
            continue
        normalized = deepcopy(row)
        for source, target in _PERIOD_REPORT_FIELD_ALIASES.items():
            if source in normalized:
                normalized[target] = deepcopy(normalized[source])
        monthly.append(normalized)
    daily = _environment_daily_rows(history)
    ledger = _environment_ledger_rows(ctx, history)
    metrics = {
        name: _history_metric("environment_history", history, field, unit, operation, environment_packet)
        for name, (field, unit, operation) in _ENVIRONMENT_METRICS.items()
    }
    history_provenance = _history_provenance("environment_history", history, environment_packet)
    monthly_provenance = _history_provenance("monthly_records", monthly, report_packet)
    warnings = [
        deepcopy(event)
        for event in getattr(getattr(ctx, "events", None), "events", [])
        if event.get("source") == "environment" and str(event.get("level", "")).lower() == "warning"
    ]
    available = bool(history or monthly or ledger or environment_packet)
    return {
        "available": available,
        "period": "run",
        "source": 'ctx.state["environment_history"]',
        "metrics": metrics,
        "daily": daily,
        "monthly": monthly,
        "ledger": ledger,
        "latest": deepcopy(daily[-1]) if daily else None,
        "warnings": warnings,
        "provenance": {
            "packet": _packet_provenance(environment_packet),
            "history": history_provenance,
            "monthly": monthly_provenance,
        },
        "contract": {
            "fields": list(DASHBOARD_ENVIRONMENT_FIELDS),
            "metric_keys": list(_ENVIRONMENT_METRICS),
            "ledger_fields": [
                "date", "source", "stream_id", "direction", "value", "unit",
                "period", "quality", "confidence", "name",
            ],
        },
    }

def _economics_daily_rows(ctx: SimulationContext) -> list[dict[str, Any]]:
    source_rows = ctx.daily_records if isinstance(ctx.daily_records, list) else []
    environment_rows = ctx.state.get("environment_history", [])
    environment_by_day = {
        str(row.get("day")): row
        for row in environment_rows
        if isinstance(row, dict) and row.get("day") is not None
    }
    disease_rows = ctx.state.get("disease_history", [])
    disease_by_day = {
        str(row.get("day")): row
        for row in disease_rows
        if isinstance(row, dict) and row.get("day") is not None
    }
    result: list[dict[str, Any]] = []
    cumulative_profit: float | None = 0.0
    for source in source_rows:
        day = source.get("day")
        environment = environment_by_day.get(str(day), {})
        disease = disease_by_day.get(str(day), {})
        profit = source.get("profit")
        if cumulative_profit is not None and _is_number(profit):
            cumulative_profit += float(profit)
        else:
            cumulative_profit = None
        result.append(
            {
                "day": deepcopy(day),
                "milk_revenue": deepcopy(source.get("milk_revenue")),
                "processor_revenue": deepcopy(source.get("processor_revenue")),
                # The model does not retain a dated byproduct revenue series.
                "byproduct_revenue": None,
                "energy_value": deepcopy(source.get("energy_value")),
                "carbon_credit_value": deepcopy(environment.get("carbon_credit_value")),
                "total_revenue": deepcopy(source.get("total_revenue")),
                "feed_cost": deepcopy(source.get("feed_cost")),
                "water_cost": deepcopy(source.get("water_cost")),
                "treatment_cost": deepcopy(disease.get("treatment_cost")),
                "disease_economic_cost": deepcopy(source.get("disease_economic_cost")),
                "cooling_cost": deepcopy(source.get("cooling_cost")),
                "processing_energy_cost": deepcopy(source.get("processing_energy_cost")),
                # These manager categories exist only on the latest packet.
                "labor_cost": None,
                "fixed_cost": None,
                "total_cost": deepcopy(source.get("total_cost")),
                "profit": deepcopy(profit),
                "cumulative_profit": cumulative_profit,
                "cash_balance": deepcopy(source.get("cash_balance")),
            }
        )
    return result


def _economics_metric(
    rows: list[dict[str, Any]],
    field: str,
    unit: str,
    operation: str,
    source: str,
    packet: Any = None,
) -> dict[str, Any]:
    provenance = _history_provenance("daily_records", rows, packet)
    return _metric_from_provenance(
        _aggregate(rows, field, operation),
        unit,
        source,
        operation,
        provenance,
    )


def _farm_npv_metric(ctx: SimulationContext) -> tuple[dict[str, Any], list[float]]:
    annual_profit: dict[str, float] = {}
    for row in ctx.daily_records:
        day = row.get("day")
        profit = row.get("profit")
        if day is not None and _is_number(profit):
            annual_profit.setdefault(str(day)[:4], 0.0)
            annual_profit[str(day)[:4]] += float(profit)
    cash_flows = [annual_profit[year] for year in sorted(annual_profit)]
    value_ = npv(cash_flows, DEFAULT_DISCOUNT_RATE) if cash_flows else None
    return (
        _metric(
            value_,
            "currency",
            "dairy_abm.analysis.npv",
            "discounted cash flow",
        ),
        cash_flows,
    )


def _build_economics(ctx: SimulationContext) -> dict[str, Any]:
    daily = _economics_daily_rows(ctx)
    manager_packet = ctx.get_packet("manager_packet")
    market_packet = ctx.get_packet("market_price_packet")
    monthly = [
        deepcopy(row)
        for row in ctx.monthly_records
        if isinstance(row, dict) and row.get("report") == "farm_manager"
    ]
    disease_rows = ctx.state.get("disease_history", [])
    metrics = {
        name: _economics_metric(
            daily,
            field,
            unit,
            operation,
            'ctx.daily_records',
            manager_packet,
        )
        for name, (field, unit, operation) in _ECONOMICS_METRICS.items()
    }
    npv_metric, cash_flows = _farm_npv_metric(ctx)
    metrics["farm_npv"] = npv_metric
    latest = None
    if manager_packet is not None and isinstance(manager_packet.payload, dict):
        latest = {
            field: deepcopy(manager_packet.payload.get(field))
            for field in _ECONOMICS_LATEST_FIELDS
        }
        latest["date"] = manager_packet.day.isoformat() if hasattr(manager_packet.day, "isoformat") else manager_packet.day
    market: dict[str, Any] = {}
    if market_packet is not None and isinstance(market_packet.payload, dict):
        market_fields = (
            "milk_price_per_l",
            "feed_cost_per_kg_dm",
            "electricity_price_per_kwh",
            "carbon_credit_price_per_tonne_co2e",
            "market_mode",
            "source",
            "period_selection",
            "market_packet_quality_flag",
            "realized_volatility",
            "market_regime_label",
        )
        market = {field: deepcopy(market_packet.payload.get(field)) for field in market_fields}
        market["provenance"] = _packet_provenance(market_packet)
    warnings = [
        deepcopy(event)
        for event in getattr(getattr(ctx, "events", None), "events", [])
        if event.get("source") in {"farm_manager", "market", "disease"}
        and str(event.get("level", "")).lower() == "warning"
    ]
    available = bool(daily or monthly or manager_packet)
    return {
        "available": available,
        "period": "run",
        "source": 'ctx.daily_records',
        "metrics": metrics,
        "daily": daily,
        "monthly": monthly,
        "latest": latest,
        "market": market,
        "farm_cash_flows": cash_flows,
        "discount_rate": DEFAULT_DISCOUNT_RATE,
        "warnings": warnings,
        "provenance": {
            "manager_packet": _packet_provenance(manager_packet),
            "daily": _history_provenance("daily_records", daily, manager_packet),
            "monthly": _history_provenance("monthly_records", monthly),
            "disease_history": _history_provenance("disease_history", list(disease_rows)) if isinstance(disease_rows, list) else None,
        },
        "contract": {
            "fields": list(DASHBOARD_ECONOMICS_FIELDS),
            "metric_keys": [*list(_ECONOMICS_METRICS), "farm_npv"],
            "latest_fields": list(_ECONOMICS_LATEST_FIELDS),
        },
    }

def _build_equipment_roi(ctx: SimulationContext) -> dict[str, Any]:
    manager_packet = ctx.get_packet("manager_packet")
    manager_payload = manager_packet.payload if manager_packet is not None else {}
    raw_assets = manager_payload.get("equipment_roi") if isinstance(manager_payload, dict) else None
    assets: list[dict[str, Any]] = []
    equipment_npvs: dict[str, float] = {}
    warnings: list[dict[str, str]] = []
    if isinstance(raw_assets, dict):
        for asset_id, raw_asset in raw_assets.items():
            if not isinstance(raw_asset, dict):
                continue
            capex = deepcopy(raw_asset.get("capex"))
            annual_benefit = deepcopy(raw_asset.get("annual_benefit"))
            npv_value = (
                npv([float(annual_benefit)], DEFAULT_DISCOUNT_RATE)
                if _is_number(annual_benefit)
                else None
            )
            if npv_value is not None:
                equipment_npvs[str(asset_id)] = npv_value
            if capex is None:
                status = "unavailable_capex"
            elif _is_number(capex) and float(capex) == 0.0:
                status = "zero_capex"
                warnings.append(
                    {
                        "asset": str(asset_id),
                        "message": "CapEx is zero; ROI and payback are unavailable.",
                    }
                )
            else:
                status = "configured"
            assets.append(
                {
                    "id": str(asset_id),
                    "label": _EQUIPMENT_LABELS.get(
                        str(asset_id), str(asset_id).replace("_", " ").title()
                    ),
                    "capex": capex,
                    "annual_benefit": annual_benefit,
                    "roi": deepcopy(raw_asset.get("roi")),
                    "payback_years": deepcopy(raw_asset.get("payback_years")),
                    "npv": npv_value,
                    "status": status,
                }
            )
    return {
        "available": bool(assets),
        "period": "run",
        "assets": assets,
        "equipment_npvs": equipment_npvs,
        "discount_rate": DEFAULT_DISCOUNT_RATE,
        "warnings": warnings,
        "provenance": {
            "manager_packet": _packet_provenance(manager_packet),
            "npv": {
                "source": "dairy_abm.analysis.npv",
                "name": "npv",
                "period": "annual benefit",
                "discount_rate": DEFAULT_DISCOUNT_RATE,
            },
        },
        "contract": {
            "fields": list(DASHBOARD_EQUIPMENT_FIELDS),
            "asset_ids": [asset["id"] for asset in assets],
        },
    }


def _split_execution_order(value_: Any) -> list[str]:
    if isinstance(value_, str):
        return [item for item in value_.split(",") if item]
    if isinstance(value_, list):
        return [str(item) for item in value_ if item is not None]
    return []


def _build_model_details(
    ctx: SimulationContext,
    duration_s: float,
    calibration_overrides: dict[str, Any] | None,
) -> dict[str, Any]:
    daily = [row for row in ctx.daily_records if isinstance(row, dict)]
    latest_daily = daily[-1] if daily else None
    schedule_records = [row for row in ctx.schedule_records if isinstance(row, dict)]
    latest_daily_schedule = next(
        (row for row in reversed(schedule_records) if row.get("phase") == "daily"),
        None,
    )
    execution_order = _split_execution_order(
        latest_daily.get("execution_order") if latest_daily else None
    )
    if not execution_order and latest_daily_schedule:
        execution_order = _split_execution_order(latest_daily_schedule.get("agents"))

    features = _feature_flags(ctx)
    enabled_systems = {name: bool(enabled) for name, enabled in features.items()}
    enabled_systems.update(
        {
            "processor": enabled_systems.get("enable_processor", False),
            "whey_processing": enabled_systems.get("enable_whey_processing", False),
            "land": enabled_systems.get("enable_land_agent", False),
        }
    )
    loops = _build_loop_sections(ctx)
    loop_states = {
        key: section.get("state")
        for key, section in loops.items()
        if key in {"l1", "l2", "l3", "l4"}
    }

    manager_packet = ctx.get_packet("manager_packet")
    manager_payload = manager_packet.payload if manager_packet is not None else {}
    manager_payload = manager_payload if isinstance(manager_payload, dict) else {}
    policy_history = ctx.state.get("policy_history", [])
    policy_history = policy_history if isinstance(policy_history, list) else []
    effective_policy = manager_payload.get("effective_policy", ctx.state.get("policy"))
    automatic_actions = manager_payload.get(
        "automatic_policy_actions", ctx.state.get("last_automatic_policy_actions", [])
    )
    policy_summary = {
        "effective_policy": deepcopy(effective_policy),
        "recommendation": deepcopy(manager_payload.get("recommendation")),
        "ranked_recommendations": deepcopy(manager_payload.get("ranked_recommendations", [])),
        "actionable_recommendations": deepcopy(manager_payload.get("actionable_recommendations", [])),
        "policy_change_triggers": deepcopy(manager_payload.get("policy_change_triggers", [])),
        "automatic_policy_actions": deepcopy(automatic_actions),
        "policy_conflicts": deepcopy(manager_payload.get("policy_conflicts", [])),
        "history_count": len(policy_history),
        "latest_history": deepcopy(policy_history[-1]) if policy_history else None,
    }
    overrides = deepcopy(calibration_overrides or {})
    warnings = build_dashboard_warnings(ctx)
    details = {
        "available": bool(daily or schedule_records),
        "source": "ctx.scenario, ctx.state, ctx.schedule_records, and ctx.events",
        "scenario": ctx.scenario.get("name", "unnamed"),
        "start_date": ctx.scenario.get("start_date"),
        "days": ctx.scenario.get("days", len(daily)),
        "seed": ctx.scenario.get("seed"),
        "herd_size": _initial_herd_size(ctx),
        "enabled_systems": enabled_systems,
        "loop_states": loop_states,
        "run_duration_s": round(float(duration_s), 2),
        "calibration_override_count": len(overrides),
        "assumption_count": sum(
            1 for row in calibration_inventory(ctx.calibration) if row.get("assumption") is True
        ),
        "active_agent_count": latest_daily.get("agent_count") if latest_daily else None,
        "warnings": warnings,
        "policy_summary": policy_summary,
        "event_count": len(getattr(getattr(ctx, "events", None), "events", [])),
        "report_contract": deepcopy(REPORT_CONTRACT),
        "scheduler": {
            "latest_execution_order": execution_order,
            "records": deepcopy(schedule_records),
            "record_count": len(schedule_records),
        },
        "contract": {"fields": list(DASHBOARD_MODEL_DETAILS_FIELDS)},
    }
    return details

def _build_export_manifest(run_id: str, available: bool) -> dict[str, Any]:
    artifacts = []
    if available:
        artifacts = [
            {
                "id": artifact_id,
                "label": label,
                "filename": filename,
                "content_type": content_type,
                "endpoint": f"/api/export/{run_id}/{filename}",
            }
            for artifact_id, label, filename, content_type in _EXPORT_ARTIFACT_DEFINITIONS
        ]
        artifacts.append(
            {
                "id": "zip",
                "label": "Full ZIP",
                "filename": f"{run_id}-output.zip",
                "content_type": "application/zip",
                "endpoint": f"/api/export/{run_id}",
            }
        )
    return {
        "available": bool(available),
        "source": "dairy_abm.reports.write_reports",
        "artifacts": artifacts,
        "contract": {
            "fields": list(DASHBOARD_EXPORT_FIELDS),
            "official_files": [filename for _, _, filename, _ in _EXPORT_ARTIFACT_DEFINITIONS],
            "zip": True,
        },
    }



def _is_number(value_: Any) -> bool:
    return isinstance(value_, (int, float)) and not isinstance(value_, bool)


def _safe_ratio(numerator: Any, denominator: Any) -> float | None:
    if not _is_number(numerator) or not _is_number(denominator) or denominator <= 0:
        return None
    return float(numerator) / float(denominator)


def _last_number(values: Any) -> float | None:
    if not isinstance(values, list):
        return None
    return next((float(item) for item in reversed(values) if _is_number(item)), None)


def _ranked_ids(rows: list[dict[str, Any]], field: str, reverse: bool = False) -> list[Any]:
    ranked = [row for row in rows if _is_number(row.get(field))]
    ranked.sort(key=lambda row: row[field], reverse=reverse)
    return [row["id"] for row in ranked]


def _trait_distributions(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    values: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        traits = row.get("trait_vector")
        if not isinstance(traits, dict):
            continue
        for name, value_ in traits.items():
            if _is_number(value_):
                values.setdefault(str(name), []).append({"id": row["id"], "value": value_})
    return {
        name: {
            "values": items,
            "min": min(item["value"] for item in items),
            "max": max(item["value"] for item in items),
            "mean": sum(item["value"] for item in items) / len(items),
        }
        for name, items in values.items()
    }


def _build_cow_explorer(ctx: SimulationContext) -> dict[str, Any]:
    packet = ctx.get_packet("cow_daily_packet")
    payload = packet.payload if packet is not None and isinstance(packet.payload, dict) else {}
    raw_records = payload.get("cow_records", [])
    raw_records = raw_records if isinstance(raw_records, list) else []
    state_by_id = {
        str(cow.get("id")): cow
        for cow in ctx.state.get("cows", [])
        if isinstance(cow, dict) and cow.get("id") is not None
    }
    records: list[dict[str, Any]] = []
    for source_record in raw_records:
        if not isinstance(source_record, dict) or source_record.get("id") is None:
            continue
        cow_id = source_record["id"]
        state = state_by_id.get(str(cow_id), {})
        traits = state.get("trait_vector") if isinstance(state.get("trait_vector"), dict) else None
        milk_l = source_record.get("milk_l")
        dmi_kg = source_record.get("dmi_kg")
        enteric_ch4_kg = _last_number(state.get("ch4_history"))
        row = {
            "id": deepcopy(cow_id),
            "milk_l": deepcopy(milk_l),
            "dmi_kg": deepcopy(dmi_kg),
            "fcr_kg_dm_per_l": _safe_ratio(dmi_kg, milk_l),
            "days_in_milk": deepcopy(source_record.get("days_in_milk")),
            "parity": deepcopy(source_record.get("parity")),
            "body_weight_kg": deepcopy(state.get("body_weight_kg")),
            "body_condition_score": deepcopy(state.get("body_condition_score")),
            "health_status": deepcopy(source_record.get("health_status", state.get("health_status"))),
            "infection_state": deepcopy(state.get("infection_state")),
            "disease": deepcopy(state.get("disease")),
            "alive": deepcopy(state.get("alive")),
            "quarantine_flag": deepcopy(state.get("quarantine_flag")),
            "rumen_ph": deepcopy(source_record.get("rumen_ph")),
            "sara_active": deepcopy(source_record.get("sara_active")),
            "pregnant": deepcopy(state.get("pregnant")),
            "days_pregnant": deepcopy(state.get("days_pregnant")),
            "observed_dmi_kg": deepcopy(source_record.get("observed_dmi_kg")),
            "actual_dmi_kg_dm": deepcopy(source_record.get("actual_dmi_kg_dm")),
            "expected_dmi_eq2_1_kg_dm": deepcopy(source_record.get("expected_dmi_eq2_1_kg_dm")),
            "estrus_detected": deepcopy(source_record.get("estrus_detected")),
            "feed_efficiency_trait": deepcopy(
                state.get("feed_efficiency_trait", traits.get("feed_efficiency") if traits else None)
            ),
            "trait_vector": deepcopy(traits),
            "enteric_ch4_kg": enteric_ch4_kg,
            "methane_intensity_kg_ch4_per_l": _safe_ratio(enteric_ch4_kg, milk_l),
        }
        records.append(row)

    health_counts: dict[str, int] = {}
    infection_state_counts: dict[str, int] = {}
    for row in records:
        health = str(row["health_status"] or "unavailable")
        health_counts[health] = health_counts.get(health, 0) + 1
        infection = row["infection_state"]
        if infection is not None:
            infection_key = str(infection)
            infection_state_counts[infection_key] = infection_state_counts.get(infection_key, 0) + 1

    packet_date = packet.day.isoformat() if packet is not None and hasattr(packet.day, "isoformat") else None
    return {
        "available": bool(records),
        "period": "latest-day",
        "date": packet_date,
        "source": 'ctx.packets["cow_daily_packet"].payload["cow_records"]',
        "state_source": 'ctx.state["cows"]',
        "historical": False,
        "history_note": "The current model retains undated per-cow histories; this explorer shows the latest-day snapshot.",
        "contract": {"fields": list(DASHBOARD_COW_FIELDS), "period": "latest-day"},
        "provenance": _packet_provenance(packet),
        "records": records,
        "health_counts": health_counts,
        "infection_state_counts": infection_state_counts,
        "disease_summary": {
            key: deepcopy(payload.get(key))
            for key in ("cow_count", "healthy_cows", "sick_cows", "sara_affected_cows", "pregnant_cows")
        },
        "rankings": {
            "milk_l": _ranked_ids(records, "milk_l", reverse=True),
            "fcr_kg_dm_per_l": _ranked_ids(records, "fcr_kg_dm_per_l"),
            "dmi_kg": _ranked_ids(records, "dmi_kg", reverse=True),
            "methane_intensity_kg_ch4_per_l": _ranked_ids(records, "methane_intensity_kg_ch4_per_l"),
        },
        "trait_distributions": _trait_distributions(records),
    }


def _daily_rows(ctx: SimulationContext) -> list[dict[str, Any]]:
    return [
        {field: deepcopy(record.get(field)) for field in DASHBOARD_DAILY_FIELDS}
        for record in ctx.daily_records
    ]

def _period_key(record: dict[str, Any], period: str) -> str | None:
    day = record.get("day")
    if day is None:
        return None
    text = str(day)
    return text[:7] if period == "monthly" else text[:4]


def _period_confidence(rows: list[dict[str, Any]]) -> str | None:
    values = [str(row["report_confidence"]) for row in rows if row.get("report_confidence")]
    return "|".join(dict.fromkeys(values)) if values else None


def _rollup_period_rows(rows: list[dict[str, Any]], period: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        key = _period_key(row, period)
        if key is not None:
            groups.setdefault(key, []).append(row)

    result: list[dict[str, Any]] = []
    for key in sorted(groups):
        group = groups[key]
        output = {"day": key}
        for field, (source, operation) in _SERIES_AGGREGATIONS.items():
            output[field] = _aggregate(group, source, operation)
        output["report_confidence"] = _period_confidence(group)
        result.append(output)
    return result


def _overlay_period_reports(
    rows: list[dict[str, Any]], reports: list[dict[str, Any]], period: str
) -> None:
    by_period = {row["day"]: row for row in rows}
    period_field = "month" if period == "monthly" else "year"
    for report in reports:
        key = report.get(period_field)
        if key is None or str(key) not in by_period:
            continue
        output = by_period[str(key)]
        for source, value_ in report.items():
            field = _PERIOD_REPORT_FIELD_ALIASES.get(source, source)
            if field in _SERIES_AGGREGATIONS and value_ is not None:
                output[field] = deepcopy(value_)


def _period_rows(ctx: SimulationContext, period: str) -> list[dict[str, Any]]:
    rows = _rollup_period_rows(ctx.daily_records, period)
    reports = ctx.monthly_records if period == "monthly" else ctx.annual_records
    _overlay_period_reports(rows, reports, period)
    return rows


def build_dashboard_warnings(ctx: SimulationContext) -> list[dict[str, Any]]:
    """Return warning events without exposing mutable context objects."""
    events = getattr(getattr(ctx, "events", None), "events", [])
    return [
        deepcopy(event)
        for event in events
        if str(event.get("level", "")).lower() == "warning"
    ]


def serialize_dashboard_run(
    ctx: SimulationContext,
    run_id: str,
    duration_s: float,
    *,
    calibration_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the stable dashboard payload for one completed simulation."""
    daily = _daily_rows(ctx)
    monthly = _period_rows(ctx, "monthly")
    annual = _period_rows(ctx, "annual")
    metrics = {
        name: _aggregate(ctx.daily_records, field, operation)
        for name, (field, _unit, operation) in _SUMMARY_DEFINITIONS.items()
    }
    summary = {
        name: _metric(value_, unit, "ctx.daily_records", operation)
        for name, value_ in metrics.items()
        for _field, unit, operation in [_SUMMARY_DEFINITIONS[name]]
    }
    event_count = len(getattr(getattr(ctx, "events", None), "events", []))
    days = ctx.scenario.get("days", len(ctx.daily_records))
    overrides = deepcopy(calibration_overrides or {})
    meta = {
        "scenario_name": ctx.scenario.get("name", "unnamed"),
        "start_date": ctx.scenario.get("start_date"),
        "seed": ctx.scenario.get("seed"),
        "days": days,
        "herd_size": _initial_herd_size(ctx),
        "duration_s": round(float(duration_s), 2),
        "event_count": event_count,
        "calibration_override_count": len(overrides),
        "calibration_overrides": overrides,
    }
    features = _feature_flags(ctx)
    warnings = build_dashboard_warnings(ctx)

    return {
        "run_id": run_id,
        "meta": meta,
        "features": features,
        "summary": summary,
        "series": {"daily": daily, "monthly": monthly, "annual": annual},
        "loops": _build_loop_sections(ctx),
        "cows": _build_cow_explorer(ctx),
        "environment": _build_environment_audit(ctx),
        "economics": _build_economics(ctx),
        "equipment": _build_equipment_roi(ctx),
        "model_details": _build_model_details(ctx, duration_s, overrides),
        "exports": _build_export_manifest(run_id, bool(ctx.daily_records or ctx.schedule_records)),
        "warnings": warnings,
        # Compatibility fields for the current run-desk response.
        "id": run_id,
        "name": meta["scenario_name"],
        "start_date": meta["start_date"],
        "seed": meta["seed"],
        "days": meta["days"],
        "herd_size": meta["herd_size"],
        "duration_s": meta["duration_s"],
        "metrics": metrics,
        "daily": daily,
        "events": event_count,
    }


__all__ = [
    "DASHBOARD_DAILY_FIELDS",
    "DASHBOARD_COW_FIELDS",
    "DASHBOARD_ENVIRONMENT_FIELDS",
    "DASHBOARD_ECONOMICS_FIELDS",
    "DASHBOARD_EQUIPMENT_FIELDS",
    "DASHBOARD_MODEL_DETAILS_FIELDS",
    "DASHBOARD_EXPORT_FIELDS",
    "build_dashboard_warnings",
    "serialize_comparison",
    "serialize_dashboard_config",
    "serialize_dashboard_run",
]
