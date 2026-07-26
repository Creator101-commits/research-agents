from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from dairy_abm.cli import main
from dairy_abm.config import load_calibration
from dairy_abm.model import DairyFarmModel


def scenario(**overrides):
    base = {
        "name": "scheduler",
        "start_date": "2026-01-01",
        "days": 1,
        "seed": 4,
        "herd_size": 3,
        "land_cropland_ha": 0,
        "enable_land_agent": False,
    }
    base.update(overrides)
    return base


class SchedulerPhasesTest(unittest.TestCase):
    def test_daily_phase_records_order_for_every_day(self) -> None:
        ctx = DairyFarmModel(scenario(days=3), load_calibration()).run()
        daily = [row for row in ctx.schedule_records if row["phase"] == "daily"]
        self.assertEqual(len(daily), 3)
        self.assertEqual(daily[0]["day"], "2026-01-01")
        self.assertEqual(
            daily[0]["agents"],
            "market,sensors,feed_crop,farm_manager_policy,disease,water_delivery,cow,dairy_processor,manure,energy,water,environment,farm_manager",
        )

    def test_weekly_phase_runs_on_sunday_only(self) -> None:
        ctx = DairyFarmModel(scenario(start_date="2026-01-01", days=7), load_calibration()).run()
        weekly = [row for row in ctx.schedule_records if row["phase"] == "weekly"]
        self.assertEqual(weekly, [
            {
                "day": "2026-01-04",
                "phase": "weekly",
                "agents": "market,sensors,feed_crop,disease,cow,dairy_processor,manure,energy,water,environment,farm_manager",
            }
        ])

    def test_monthly_phase_runs_after_daily_record_on_month_end(self) -> None:
        ctx = DairyFarmModel(scenario(start_date="2026-01-30", days=2), load_calibration()).run()
        phases = [(row["day"], row["phase"]) for row in ctx.schedule_records]
        self.assertEqual(phases, [
            ("2026-01-30", "daily"),
            ("2026-01-31", "daily"),
            ("2026-01-31", "monthly"),
        ])
        self.assertEqual({row["report"] for row in ctx.monthly_records}, {"environment", "farm_manager"})

    def test_annual_phase_runs_after_monthly_on_year_end(self) -> None:
        ctx = DairyFarmModel(scenario(start_date="2026-12-31", days=1), load_calibration()).run()
        phases = [(row["day"], row["phase"]) for row in ctx.schedule_records]
        self.assertEqual(phases, [
            ("2026-12-31", "daily"),
            ("2026-12-31", "monthly"),
            ("2026-12-31", "annual"),
        ])
        annual = [row for row in ctx.schedule_records if row["phase"] == "annual"]
        self.assertEqual(annual[0]["agents"], "genetics,farm_manager")
        self.assertEqual(ctx.annual_records[0]["report"], "genetics")

    def test_land_enabled_schedule_includes_land_before_feed_crop(self) -> None:
        ctx = DairyFarmModel(scenario(enable_land_agent=True), load_calibration()).run()
        daily_agents = ctx.schedule_records[0]["agents"].split(",")
        self.assertLess(daily_agents.index("land"), daily_agents.index("feed_crop"))
        self.assertEqual(ctx.daily_records[0]["land_owner"], "land")

    def test_cli_writes_schedule_csv(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            scenario_path = root / "scenario.json"
            scenario_path.write_text(json.dumps(scenario(days=2)), encoding="utf-8")
            output_dir = root / "out"
            self.assertEqual(main(["run", "--scenario", str(scenario_path), "--output", str(output_dir)]), 0)
            schedule_csv = (output_dir / "schedule.csv").read_text(encoding="utf-8")
            self.assertIn("phase", schedule_csv)
            self.assertIn("daily", schedule_csv)
            summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["schedule_records"], 2)


if __name__ == "__main__":
    unittest.main()
