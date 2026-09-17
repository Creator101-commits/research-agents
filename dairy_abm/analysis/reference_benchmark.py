"""Evaluate report outputs against source-defined reference targets."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dairy_abm.core import ConfigError, read_json


ROOT = Path(__file__).resolve().parents[2]
_REFERENCE_FILES = {
    "cdairy_airand_year15": ROOT / "configs" / "reference_targets" / "cdairy_airand_year15.json",
}


def evaluate_reference_benchmark(
    reference_id: str | None,
    daily_records: list[dict[str, Any]],
    milk_density_kg_per_l: float,
) -> dict[str, Any] | None:
    """Return comparable annualized outputs without converting unmatched metrics into proxies."""
    if reference_id is None:
        return None
    if reference_id not in _REFERENCE_FILES:
        raise ConfigError(f"unknown reference_benchmark: {reference_id}")
    if milk_density_kg_per_l <= 0.0:
        raise ConfigError("milk density must be positive for reference benchmarking")

    reference = read_json(_REFERENCE_FILES[reference_id])
    observed_days = len(daily_records)
    cow_days = sum(max(0.0, float(row.get("cow_count", 0.0))) for row in daily_records)

    observed = {
        "milk_kg_per_cow_year": _annual_per_cow(
            sum(float(row.get("milk_l", 0.0)) for row in daily_records) * milk_density_kg_per_l,
            cow_days,
        ),
    }
    metrics: list[dict[str, Any]] = []
    for name, target in reference["metrics"].items():
        comparison = str(target["comparison"])
        actual = observed.get(name) if comparison == "comparable" else None
        metrics.append(
            {
                "name": name,
                "target": float(target["target"]),
                "unit": target["unit"],
                "source_cell": target["source_cell"],
                "comparison": comparison,
                "observed": actual,
                "absolute_gap": actual - float(target["target"]) if actual is not None else None,
                "relative_gap_fraction": (
                    (actual - float(target["target"])) / float(target["target"])
                    if actual is not None and float(target["target"]) != 0.0
                    else None
                ),
            }
        )
    return {
        "id": reference["id"],
        "label": reference["label"],
        "source": reference["source"],
        "observed_days": observed_days,
        "cow_days": cow_days,
        "annualization_days": 365,
        "metrics": metrics,
        "limitations": [
            "Only identical measures are compared. Non-equivalent and unmodeled reference measures remain unavailable.",
            "The source is a 1,000-replication year-15 strategy result. A single deterministic run is not an equivalent uncertainty estimate.",
            "The reference workbook does not provide targets for this model's water, energy, manure, carbon, or circularity outputs.",
        ],
    }


def _annual_per_cow(total: float, cow_days: float) -> float | None:
    """Annualize a total against the observed cow-day denominator."""
    return total * 365.0 / cow_days if cow_days > 0.0 else None
