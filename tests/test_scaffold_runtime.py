from __future__ import annotations

from datetime import date
from pathlib import Path
from random import Random
from tempfile import TemporaryDirectory
import json
import unittest

from dairy_abm.cli import main
from dairy_abm.config import calibration_inventory, load_calibration, value
from dairy_abm.core import (
    ConfigError,
    EventLog,
    Packet,
    SimulationClock,
    SimulationContext,
    require_fraction,
    require_nonnegative,
)
from dairy_abm.model import DairyFarmModel


class ScaffoldRuntimeTest(unittest.TestCase):
    def test_package_model_runs_deterministic_daily_schedule(self) -> None:
        calibration = load_calibration()
        scenario = {"name": "test", "start_date": "2026-01-01", "days": 3, "seed": 11}
        first = DairyFarmModel(scenario, calibration).run()
        second = DairyFarmModel(scenario, calibration).run()
        self.assertEqual(first.daily_records, second.daily_records)
        self.assertEqual([row["day"] for row in first.daily_records], ["2026-01-01", "2026-01-02", "2026-01-03"])
        self.assertEqual(first.daily_records[0]["agent_count"], 11)
        self.assertIn("milk_l", first.daily_records[0])

    def test_clock_boundaries(self) -> None:
        clock = SimulationClock(start=date(2026, 1, 30), days=3)
        self.assertEqual(clock.dates(), [date(2026, 1, 30), date(2026, 1, 31), date(2026, 2, 1)])
        self.assertTrue(SimulationClock.is_month_end(date(2026, 1, 31)))
        self.assertTrue(SimulationClock.is_year_end(date(2026, 12, 31)))
        self.assertTrue(SimulationClock.is_week_end(date(2026, 1, 4)))

    def test_packet_event_and_validation_helpers(self) -> None:
        ctx = SimulationContext(
            scenario={},
            calibration={},
            rng=Random(1),
            events=EventLog(),
        )
        packet = Packet(source="test", name="test_packet", day=date(2026, 1, 1), payload={"x": 1})
        ctx.publish(packet)
        ctx.events.add(date(2026, 1, 1), "test", "info", "created")
        self.assertIs(ctx.get_packet("test_packet"), packet)
        self.assertEqual(ctx.events.events[0]["message"], "created")
        self.assertEqual(require_nonnegative("x", 0), 0)
        self.assertEqual(require_fraction("f", 1), 1)
        with self.assertRaises(ConfigError):
            require_nonnegative("x", -0.1)
        with self.assertRaises(ConfigError):
            require_fraction("f", 1.1)

    def test_calibration_inventory_exposes_assumption_flags(self) -> None:
        calibration = load_calibration()
        rows = calibration_inventory(calibration)
        keys = {row["key"] for row in rows}
        self.assertIn("genetics.heritability_h2_rfi_fat", keys)
        self.assertIn("runtime.daily_tick_hours", keys)
        self.assertEqual(value(calibration, "genetics.heritability_h2_rfi_fat"), 0.35)
        self.assertTrue(any(row["assumption"] for row in rows))

    def test_cli_run_and_inventory_outputs(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            scenario_path = root / "scenario.json"
            scenario_path.write_text(
                json.dumps({"name": "cli", "start_date": "2026-01-01", "days": 2, "seed": 5}),
                encoding="utf-8",
            )
            output_dir = root / "out"
            self.assertEqual(main(["run", "--scenario", str(scenario_path), "--output", str(output_dir)]), 0)
            summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["scenario_name"], "cli")
            self.assertEqual(summary["daily_records"], 2)
            self.assertIn("cow_daily_packet", summary["latest_packets"])
            self.assertTrue((output_dir / "daily.csv").exists())
            inventory_path = root / "inventory.json"
            self.assertEqual(main(["list-calibrations", "--output", str(inventory_path)]), 0)
            self.assertGreater(len(json.loads(inventory_path.read_text(encoding="utf-8"))), 0)


if __name__ == "__main__":
    unittest.main()
