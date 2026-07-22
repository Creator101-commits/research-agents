from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from dairy_abm.cli import main
from dairy_abm.config import calibration_inventory, load_calibration, value
from dairy_abm.core import ConfigError


EXPECTED_AGENTS = {
    "cow",
    "dairy_processor",
    "disease",
    "energy",
    "environment",
    "farm_manager",
    "feed_crop",
    "genetics",
    "land",
    "manure",
    "market",
    "runtime",
    "sensors",
    "water",
}


class CalibrationInventoryTest(unittest.TestCase):
    def test_inventory_covers_all_agent_families(self) -> None:
        rows = calibration_inventory(load_calibration())
        agents = {row["agent"] for row in rows}
        self.assertEqual(EXPECTED_AGENTS, agents)
        self.assertGreaterEqual(len(rows), 70)

    def test_inventory_rows_are_review_ready(self) -> None:
        rows = calibration_inventory(load_calibration())
        for row in rows:
            with self.subTest(row=row["key"]):
                self.assertTrue(row["key"])
                self.assertTrue(row["agent"])
                self.assertIn("default", row)
                self.assertTrue(row["unit"])
                self.assertTrue(row["source"])
                self.assertIsInstance(row["assumption"], bool)
                self.assertTrue(row["description"])
                self.assertTrue(row["valid_range"])
        self.assertTrue(any(row["assumption"] for row in rows))
        self.assertTrue(any(not row["assumption"] for row in rows))

    def test_blueprint_anchors_are_preserved(self) -> None:
        calibration = load_calibration()
        self.assertEqual(value(calibration, "genetics.minimum_intake_record_days"), 35)
        self.assertEqual(value(calibration, "energy.kwh_per_ton_feedstock"), 85.73)
        self.assertEqual(value(calibration, "water.water_saving_l_per_cow_day"), 21.0)
        self.assertFalse(value(calibration, "dairy_processor.enabled"))
        self.assertFalse(value(calibration, "land.enabled"))

    def test_invalid_weight_override_is_rejected(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text(
                json.dumps({"manure": {"digester_route_fraction": {"value": 0.9}}}),
                encoding="utf-8",
            )
            with self.assertRaises(ConfigError):
                load_calibration(str(path))

    def test_cli_writes_full_inventory(self) -> None:
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "inventory.json"
            self.assertEqual(main(["list-calibrations", "--output", str(output)]), 0)
            rows = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(EXPECTED_AGENTS, {row["agent"] for row in rows})
            self.assertIn("market.class_cwt_to_l_conversion", {row["key"] for row in rows})


if __name__ == "__main__":
    unittest.main()
