from __future__ import annotations

from pathlib import Path
from typing import Any

from dairy_abm.config import calibration_inventory, value
from dairy_abm.core import SimulationContext, write_csv, write_json


def write_reports(output_dir: Path, ctx: SimulationContext) -> None:
    summary: dict[str, Any] = {
        "scenario_name": ctx.scenario.get("name", "unnamed"),
        "daily_records": len(ctx.daily_records),
        "schedule_records": len(ctx.schedule_records),
        "monthly_records": len(ctx.monthly_records),
        "annual_records": len(ctx.annual_records),
        "output_files": [
            "summary.json",
            "calibration_inventory.json",
            "daily.csv",
            "schedule.csv",
            "monthly.csv",
            "annual.csv",
        ],
        "scenario_flags": {
            "enable_processor": bool(ctx.scenario.get("enable_processor", False)),
            "enable_whey_processing": bool(ctx.scenario.get("enable_whey_processing", False)),
            "enable_land_agent": bool(ctx.scenario.get("enable_land_agent", False)),
            "l1_nutrient_loop_enabled": bool(
                ctx.scenario.get(
                    "l1_nutrient_loop_enabled",
                    value(ctx.calibration, "manure.l1_nutrient_loop_enabled"),
                )
            ),
            "l2_water_loop_enabled": bool(
                ctx.scenario.get(
                    "l2_water_loop_enabled",
                    value(ctx.calibration, "water.l2_water_loop_enabled"),
                )
            ),
            "l3_energy_loop_enabled": bool(
                ctx.scenario.get(
                    "l3_energy_loop_enabled",
                    value(ctx.calibration, "energy.l3_energy_loop_enabled"),
                )
            ),
            "l4_byproduct_loop_enabled": bool(
                ctx.scenario.get(
                    "l4_byproduct_loop_enabled",
                    value(ctx.calibration, "dairy_processor.l4_byproduct_loop_enabled"),
                )
            ),
        },
        "events": ctx.events.events,
        "latest_packets": {
            name: {
                "source": packet.source,
                "day": packet.day.isoformat(),
                "quality": packet.quality,
                "payload": packet.payload,
            }
            for name, packet in sorted(ctx.packets.items())
        },
    }
    write_json(output_dir / "summary.json", summary)
    write_json(output_dir / "calibration_inventory.json", calibration_inventory(ctx.calibration))
    write_csv(output_dir / "daily.csv", ctx.daily_records)
    write_csv(output_dir / "schedule.csv", ctx.schedule_records)
    write_csv(output_dir / "monthly.csv", ctx.monthly_records)
    write_csv(output_dir / "annual.csv", ctx.annual_records)
