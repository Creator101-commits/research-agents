from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from dairy_abm.cli import main
from dairy_abm.config import load_calibration
from dairy_abm.core import ConfigError
from dairy_abm.model import DairyFarmModel


def baseline_scenario(**overrides):
    scenario = {
        "name": "daily-flow",
        "start_date": "2026-01-01",
        "days": 1,
        "seed": 7,
        "herd_size": 10,
        "land_cropland_ha": 0,
    }
    scenario.update(overrides)
    return scenario


class DailyFlowAgentsTest(unittest.TestCase):
    def test_scheduler_order_matches_daily_flow(self) -> None:
        ctx = DairyFarmModel(baseline_scenario(), load_calibration()).run()
        self.assertEqual(
            ctx.daily_records[0]["execution_order"],
            "market,sensors,feed_crop,farm_manager_policy,disease,water_delivery,cow,dairy_processor,manure,energy,water,environment,farm_manager",
        )
        self.assertTrue({
            "market_price_packet",
            "sensor_observation_packet",
            "disease_state_packet",
            "feed_crop_packet",
            "cow_daily_packet",
        }.issubset(set(ctx.packets)))

    def test_daily_mass_and_economics_are_nonnegative_and_coherent(self) -> None:
        ctx = DairyFarmModel(baseline_scenario(herd_size=2), load_calibration()).run()
        row = ctx.daily_records[0]
        self.assertEqual(row["cow_count"], 2)
        self.assertGreater(row["milk_l"], 0)
        self.assertGreater(row["dmi_kg"], 0.0)
        self.assertGreater(row["manure_kg"], 0.0)
        self.assertGreater(row["enteric_ch4_kg"], 0)
        self.assertGreaterEqual(row["feed_cost"], 0.0)
        self.assertEqual(row["milk_revenue"], row["milk_l"] * row["milk_price_per_l"])

    def test_disease_state_reduces_milk_when_probability_forces_cases(self) -> None:
        healthy = DairyFarmModel(baseline_scenario(herd_size=5), load_calibration()).run()
        calibration = deepcopy(load_calibration())
        calibration["disease"]["mastitis_daily_probability"]["value"] = 1.0
        calibration["disease"]["lameness_daily_probability"]["value"] = 0.0
        calibration["disease"]["recovery_daily_probability"]["value"] = 0.0
        sick = DairyFarmModel(baseline_scenario(herd_size=5), calibration).run()
        self.assertEqual(sick.daily_records[0]["new_disease_cases"], 5)
        self.assertLess(sick.daily_records[0]["milk_l"], healthy.daily_records[0]["milk_l"])
        self.assertEqual(sick.packets["cow_daily_packet"].payload["sick_cows"], 5)

    def test_sensor_packet_flags_missing_readings(self) -> None:
        calibration = deepcopy(load_calibration())
        calibration["sensors"]["missing_reading_probability"]["value"] = 1.0
        ctx = DairyFarmModel(baseline_scenario(herd_size=4), calibration).run()
        packet = ctx.packets["sensor_observation_packet"]
        self.assertEqual(packet.quality, "partial")
        self.assertEqual(packet.payload["observed_cows"], 0)
        self.assertEqual(packet.payload["missing_readings"], 4)

    def test_negative_market_price_is_rejected(self) -> None:
        calibration = deepcopy(load_calibration())
        calibration["market"]["milk_price_per_l"]["value"] = -1.0
        with self.assertRaises(ConfigError):
            DairyFarmModel(baseline_scenario(), calibration).run()

    def test_cli_daily_csv_contains_agent_outputs(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            scenario_path = root / "scenario.json"
            scenario_path.write_text(json.dumps(baseline_scenario(days=2, herd_size=3)), encoding="utf-8")
            output_dir = root / "out"
            self.assertEqual(main(["run", "--scenario", str(scenario_path), "--output", str(output_dir)]), 0)
            daily_csv = (output_dir / "daily.csv").read_text(encoding="utf-8")
            self.assertIn("execution_order", daily_csv)
            self.assertIn("milk_l", daily_csv)
            self.assertIn("active_disease_cases", daily_csv)


if __name__ == "__main__":
    unittest.main()
