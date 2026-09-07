from __future__ import annotations

import csv
import json
from itertools import product
from pathlib import Path
from statistics import mean

from dairy_abm.config import load_calibration
from dairy_abm.model import DairyFarmModel


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(__file__).resolve().parent / "data"
LOOP_KEYS = (
    "l1_nutrient_loop_enabled",
    "l2_water_loop_enabled",
    "l3_energy_loop_enabled",
    "l4_byproduct_loop_enabled",
)


def scenario(seed: int, loops: tuple[bool, bool, bool, bool]) -> dict[str, object]:
    return {
        "name": "poster_loop_factorial",
        "start_date": "2026-01-01",
        "days": 365,
        "seed": seed,
        "herd_size": 100,
        "land_cropland_ha": 80,
        "land_pasture_ha": 40,
        "production_system": "high_intensity",
        "amino_acid_policy_active": False,
        "auto_biosecurity_response": False,
        "auto_environment_response": False,
        "auto_feed_response": False,
        "auto_energy_response": False,
        "enable_processor": True,
        "enable_whey_processing": True,
        "enable_land_agent": True,
        **dict(zip(LOOP_KEYS, loops, strict=True)),
    }


def summarize(seed: int, loops: tuple[bool, bool, bool, bool]) -> tuple[dict[str, object], list[dict[str, object]]]:
    ctx = DairyFarmModel(scenario(seed, loops), load_calibration()).run()
    rows = ctx.daily_records
    total_milk = sum(float(row["milk_l"]) for row in rows)
    total_net_ghg = sum(float(row["net_kg_co2e"]) for row in rows)
    summary: dict[str, object] = {
        "seed": seed,
        "configuration": "".join("1" if enabled else "0" for enabled in loops),
        **{key: enabled for key, enabled in zip(LOOP_KEYS, loops, strict=True)},
        "days": len(rows),
        "agent_count": int(rows[-1]["agent_count"]),
        "milk_l": total_milk,
        "operating_profit": sum(float(row["profit"]) for row in rows),
        "net_kg_co2e": total_net_ghg,
        "avoided_kg_co2e": sum(float(row["avoided_kg_co2e"]) for row in rows),
        "kg_co2e_per_l_milk": total_net_ghg / total_milk if total_milk else None,
        "freshwater_withdrawal_l": sum(float(row["freshwater_withdrawal_l"]) for row in rows),
        "recycled_irrigation_l": sum(float(row["recycled_irrigation_l"]) for row in rows),
        "electricity_generated_kwh": sum(float(row["electricity_generated_kwh"]) for row in rows),
        "feed_loop_offset_kg": sum(float(row["feed_loop_offset_kg"]) for row in rows),
        "water_loop_offset_l": sum(float(row["water_loop_offset_l"]) for row in rows),
        "synthetic_fertilizer_saved_kg": sum(float(row["synthetic_fertilizer_saved_kg"]) for row in rows),
        "mean_circularity_score": mean(float(row["circularity_score"]) for row in rows),
        "mean_sustainability_score": mean(float(row["sustainability_score_0_100"]) for row in rows),
        "whey_l": sum(float(row["whey_l"]) for row in rows),
        "roi_reported": rows[-1]["roi_circular_investment"],
        "payback_reported": rows[-1]["payback_period_years"],
    }
    return summary, rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    factorial: list[dict[str, object]] = []
    full_daily: list[dict[str, object]] = []
    for loops in product((False, True), repeat=4):
        summary, daily = summarize(42, loops)
        factorial.append(summary)
        if loops == (True, True, True, True):
            full_daily = daily

    selected = {
        "No loops": (False, False, False, False),
        "Nutrient + water": (True, True, False, False),
        "Energy": (False, False, True, False),
        "Products": (False, False, False, True),
        "All loops": (True, True, True, True),
    }
    robustness: list[dict[str, object]] = []
    for label, loops in selected.items():
        for seed in range(1, 13):
            summary, _ = summarize(seed, loops)
            summary["label"] = label
            robustness.append(summary)

    write_csv(DATA_DIR / "factorial_seed42.csv", factorial)
    write_csv(DATA_DIR / "robustness_12seeds.csv", robustness)
    write_csv(DATA_DIR / "full_loop_daily_seed42.csv", full_daily)
    metadata = {
        "experiment": "Full 2^4 factorial at seed 42 plus five selected configurations over seeds 1-12",
        "scenario": scenario(42, (True, True, True, True)),
        "loop_order": list(LOOP_KEYS),
        "limitations": [
            "Computational outputs are model-derived, not field measurements.",
            "No capital investment cost is supplied, so ROI and payback are intentionally not reported.",
            "The abstract's five proposed farm systems are not implemented as five directly comparable scenarios in this repository revision.",
        ],
    }
    (DATA_DIR / "experiment_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
