from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


DEFAULT_DISCOUNT_RATE = 0.06


def npv(cash_flows: list[float], discount_rate: float) -> float:
    """Return the net present value of annual cash flows starting at year zero."""
    if discount_rate <= -1.0:
        raise ValueError("discount_rate must be greater than -1")
    return sum(cf / (1.0 + discount_rate) ** year for year, cf in enumerate(cash_flows))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _float(row: dict[str, Any], key: str) -> float | None:
    value = row.get(key)
    if value in (None, "", "None", "null"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _annual_profit(daily_rows: list[dict[str, str]], annual_rows: list[dict[str, str]]) -> list[float]:
    annual_profit = [
        _float(row, "net_farm_profit")
        if _float(row, "net_farm_profit") is not None
        else _float(row, "profit")
        for row in annual_rows
    ]
    if annual_profit and all(value is not None for value in annual_profit):
        return [float(value) for value in annual_profit]

    by_year: defaultdict[str, float] = defaultdict(float)
    for row in daily_rows:
        day = row.get("day", "")
        profit = _float(row, "profit")
        if day and profit is not None:
            by_year[day[:4]] += profit
    return [by_year[year] for year in sorted(by_year)]


def _equipment_cash_flows(summary: dict[str, Any]) -> dict[str, list[float]]:
    manager = summary.get("latest_packets", {}).get("manager_packet", {})
    equipment = manager.get("payload", {}).get("equipment_roi", {})
    if not isinstance(equipment, dict):
        return {}
    return {
        name: [float(details["annual_benefit"])]
        for name, details in equipment.items()
        if isinstance(details, dict) and details.get("annual_benefit") is not None
    }


def analyze_outputs(
    daily_path: Path,
    annual_path: Path | None = None,
    summary_path: Path | None = None,
    discount_rate: float = DEFAULT_DISCOUNT_RATE,
) -> dict[str, Any]:
    daily_rows = _read_csv(daily_path)
    annual_rows = _read_csv(annual_path) if annual_path is not None and annual_path.exists() else []
    farm_cash_flows = _annual_profit(daily_rows, annual_rows)
    result: dict[str, Any] = {
        "discount_rate": discount_rate,
        "farm_cash_flows": farm_cash_flows,
        "farm_npv": npv(farm_cash_flows, discount_rate),
        "equipment_npvs": {},
    }
    if summary_path is not None and summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        result["equipment_cash_flows"] = _equipment_cash_flows(summary)
        result["equipment_npvs"] = {
            name: npv(cash_flows, discount_rate)
            for name, cash_flows in result["equipment_cash_flows"].items()
        }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compute farm and equipment NPV from simulation outputs.")
    parser.add_argument("--daily", type=Path, required=True)
    parser.add_argument("--annual", type=Path)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--discount-rate", type=float, default=DEFAULT_DISCOUNT_RATE)
    args = parser.parse_args(argv)
    print(json.dumps(analyze_outputs(args.daily, args.annual, args.summary, args.discount_rate), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
