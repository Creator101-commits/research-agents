from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from dairy_abm.cli import main


ROOT = Path(__file__).resolve().parent.parent


class CliOutputsAndReadmeTest(unittest.TestCase):
    def test_baseline_cli_writes_all_documented_outputs(self) -> None:
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "baseline"
            self.assertEqual(
                main(["run", "--scenario", str(ROOT / "scenarios" / "baseline.json"), "--output", str(output)]),
                0,
            )
            expected = {
                "summary.json",
                "calibration_inventory.json",
                "daily.csv",
                "schedule.csv",
                "monthly.csv",
                "annual.csv",
            }
            self.assertEqual(expected, {path.name for path in output.iterdir()})
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["scenario_name"], "baseline")
            self.assertEqual(set(summary["output_files"]), expected)
            self.assertEqual(summary["daily_records"], 10)
            self.assertGreaterEqual(summary["monthly_records"], 2)
            self.assertEqual(summary["annual_records"], 1)
            self.assertFalse(summary["scenario_flags"]["enable_processor"])
            self.assertFalse(summary["scenario_flags"]["enable_land_agent"])

    def test_cli_feature_flags_override_scenario_defaults(self) -> None:
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "flags"
            self.assertEqual(
                main(
                    [
                        "run",
                        "--scenario",
                        str(ROOT / "scenarios" / "baseline.json"),
                        "--output",
                        str(output),
                        "--days",
                        "1",
                        "--enable-processor",
                        "--enable-whey-processing",
                        "--enable-land-agent",
                    ]
                ),
                0,
            )
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            self.assertTrue(summary["scenario_flags"]["enable_processor"])
            self.assertTrue(summary["scenario_flags"]["enable_whey_processing"])
            self.assertTrue(summary["scenario_flags"]["enable_land_agent"])
            self.assertTrue(summary["latest_packets"]["processor_packet"]["payload"]["enabled"])
            self.assertEqual(summary["latest_packets"]["land_packet"]["payload"]["land_owner"], "land")

    def test_readme_mentions_python_cli_and_test_command(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("python3 -m dairy_abm run", readme)
        self.assertIn("python3 -m unittest discover -s tests -p 'test_*.py'", readme)
        self.assertIn("calibration_inventory.json", readme)


if __name__ == "__main__":
    unittest.main()
