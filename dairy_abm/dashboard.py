"""Serialize simulation contexts into the dashboard data contract.

The simulation and official reports remain authoritative. This module only
selects and aggregates their existing outputs for the web client.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from dairy_abm.core import SimulationContext


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


def _metric(value_: Any, unit: str, source: str, aggregation: str) -> dict[str, Any]:
    available = value_ is not None
    result: dict[str, Any] = {
        "value": value_,
        "unit": unit,
        "available": available,
        "source": source,
        "aggregation": aggregation,
    }
    if not available:
        result["reason"] = "no data for selected run"
    return result


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
        "loops": {},
        "cows": [],
        "environment": {},
        "economics": {},
        "equipment": {},
        "model_details": {},
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
    "build_dashboard_warnings",
    "serialize_comparison",
    "serialize_dashboard_config",
    "serialize_dashboard_run",
]
