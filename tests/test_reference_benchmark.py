from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from dairy_abm.analysis.reference_benchmark import evaluate_reference_benchmark
from dairy_abm.config import load_calibration
from dairy_abm.core import ConfigError, read_json
from dairy_abm.dashboard import serialize_dashboard_run
from dairy_abm.model import DairyFarmModel
from dairy_abm.reports import write_reports


class ReferenceBenchmarkTest(unittest.TestCase):
    def test_cdairy_reference_compares_only_identical_measure(self) -> None:
        result = evaluate_reference_benchmark(
            "cdairy_airand_year15",
            [
                {"cow_count": 2, "milk_l": 20.0},
                {"cow_count": 2, "milk_l": 22.0},
            ],
            1.03,
        )
        assert result is not None
        milk = next(row for row in result["metrics"] if row["name"] == "milk_kg_per_cow_year")
        self.assertAlmostEqual(milk["observed"], 42.0 * 1.03 * 365.0 / 4.0)
        self.assertIsNotNone(milk["absolute_gap"])

        cull = next(row for row in result["metrics"] if row["name"] == "annual_cull_rate_pct")
        self.assertEqual(cull["comparison"], "not_modeled")
        self.assertIsNone(cull["observed"])
        self.assertIsNone(cull["absolute_gap"])

    def test_unknown_reference_is_rejected(self) -> None:
        with self.assertRaisesRegex(ConfigError, "unknown reference_benchmark"):
            evaluate_reference_benchmark("not-a-reference", [], 1.03)

    def test_report_persists_reference_comparison(self) -> None:
        scenario = {
            "name": "reference-report",
            "start_date": "2026-01-01",
            "days": 2,
            "seed": 1,
            "herd_size": 4,
            "reference_benchmark": "cdairy_airand_year15",
        }
        context = DairyFarmModel(scenario, load_calibration()).run()
        with TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_reports(output, context)
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["reference_benchmark"]["id"], "cdairy_airand_year15")
        self.assertEqual(summary["reference_benchmark"]["source"]["strategy"], "AIRAND")

    def test_cdairy_milk_calibration_matches_the_unit_equivalent_target(self) -> None:
        root = Path(__file__).resolve().parent.parent
        scenario = read_json(root / "scenarios" / "cdairy_airand_reference.json")
        context = DairyFarmModel(
            scenario,
            load_calibration(root / "configs" / "reference_targets" / "cdairy_airand_milk_calibration.json"),
        ).run()
        with TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_reports(output, context)
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
        milk = next(
            row
            for row in summary["reference_benchmark"]["metrics"]
            if row["name"] == "milk_kg_per_cow_year"
        )
        self.assertLess(abs(milk["absolute_gap"]), 0.01)

    def test_dashboard_includes_reference_comparison(self) -> None:
        scenario = {
            "name": "reference-dashboard",
            "start_date": "2026-01-01",
            "days": 1,
            "seed": 1,
            "herd_size": 1,
            "reference_benchmark": "cdairy_airand_year15",
        }
        context = DairyFarmModel(scenario, load_calibration()).run()
        payload = serialize_dashboard_run(context, "reference", 0.0)
        self.assertEqual(payload["reference_benchmark"]["id"], "cdairy_airand_year15")
        self.assertEqual(
            payload["reference_benchmark"]["metrics"][0]["comparison"], "comparable"
        )


if __name__ == "__main__":
    unittest.main()
