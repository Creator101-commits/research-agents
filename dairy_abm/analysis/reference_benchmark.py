"""Evaluate report outputs against the Cdairy workbook reference targets."""

from __future__ import annotations

from typing import Any

from dairy_abm.analysis.excel_parity import run_parity
from dairy_abm.core import ConfigError

_REFERENCES = {
    "cdairy_airand_year15": "Cdairy AIRAND year-15 reference (Stats_MAST, 1,000 replications)",
}


def evaluate_reference_benchmark(reference_id: str | None, ctx) -> dict[str, Any] | None:
    """Return the workbook comparison for a named reference, or None when not requested."""
    if reference_id is None:
        return None
    if reference_id not in _REFERENCES:
        raise ConfigError(f"unknown reference_benchmark: {reference_id}")
    parity = run_parity(ctx)
    return {
        "id": reference_id,
        "label": _REFERENCES[reference_id],
        **(parity or {"comparison": None}),
    }
