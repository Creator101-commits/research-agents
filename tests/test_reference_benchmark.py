from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from dairy_abm.analysis.excel_parity import (
    aggregate_seed_runs,
    annual_excel_economics,
    compare_year,
    run_parity,
    workbook_reference,
)
from dairy_abm.analysis.reference_benchmark import evaluate_reference_benchmark
from dairy_abm.config import load_calibration
from dairy_abm.core import ConfigError
from dairy_abm.dashboard import serialize_dashboard_run
from dairy_abm.model import DairyFarmModel
from dairy_abm.reports import write_reports


def _scenario(**overrides):
    base = {"name": "parity", "start_date": "2026-01-01", "days": 30, "seed": 3, "herd_size": 40}
    base.update(overrides)
    return base


class ReferenceBenchmarkTest(unittest.TestCase):
    def test_workbook_reference_is_the_airand_year15_result(self) -> None:
        reference = workbook_reference("AIRAND")
        self.assertEqual(reference["year"], 15)
        self.assertAlmostEqual(reference["technical"]["milk_yield_kg_per_cow_year"], 12668.710786630883, places=6)
        self.assertAlmostEqual(reference["table4"]["profit"], 1541.3954411278155, places=6)
        self.assertAlmostEqual(reference["technical"]["antibiotic_daily_doses"], 284.3 / reference["present_cows"])

    def test_identical_inputs_compare_as_exact_match(self) -> None:
        reference = workbook_reference("AIRAND")
        comparison = compare_year({"technical": reference["technical"], "table4": reference["table4"]}, reference)
        self.assertTrue(all(row["status"] == "match" for row in comparison["rows"]))
        self.assertTrue(all(row["absolute_gap"] == 0.0 for row in comparison["rows"]))

    def test_every_run_is_priced_with_the_workbook_formulas(self) -> None:
        ctx = DairyFarmModel(_scenario(), load_calibration()).run()
        annual = annual_excel_economics(ctx)
        self.assertEqual(len(annual), 1)
        row = annual[0]
        self.assertEqual(row["days"], 30)
        self.assertFalse(row["complete_year"])
        self.assertGreater(row["technical"]["milk_yield_kg_per_cow_year"], 0.0)
        daily_milk_revenue = sum(record["milk_revenue"] for record in ctx.daily_records)
        workbook_milk = row["economics"]["milk_sales"] + row["economics"]["fat_sales"] + row["economics"]["protein_sales"] + row["economics"]["scs_deviation"]
        # Daily herd-total accounting adds up to the workbook's annual per-cow rows.
        self.assertAlmostEqual(daily_milk_revenue, workbook_milk / row["economics"]["multiplier"], places=6)

    def test_run_parity_reports_status_for_all_rows(self) -> None:
        ctx = DairyFarmModel(_scenario(), load_calibration()).run()
        parity = run_parity(ctx)
        assert parity is not None
        self.assertEqual(parity["source"]["strategy"], "AIRAND")
        counts = parity["comparison"]["status_counts"]
        self.assertEqual(sum(counts.values()), len(parity["comparison"]["rows"]))

    def test_seed_aggregate_averages_compared_years(self) -> None:
        runs = [run_parity(DairyFarmModel(_scenario(seed=seed), load_calibration()).run()) for seed in (1, 2)]
        aggregate = aggregate_seed_runs(runs)
        self.assertEqual(aggregate["seeds"], 2)
        milk = next(row for row in aggregate["comparison"]["rows"] if row["key"] == "milk_yield_kg_per_cow_year")
        self.assertIsNotNone(milk["standard_error"])

    def test_unknown_reference_is_rejected(self) -> None:
        ctx = DairyFarmModel(_scenario(days=1, herd_size=2), load_calibration()).run()
        with self.assertRaisesRegex(ConfigError, "unknown reference_benchmark"):
            evaluate_reference_benchmark("not-a-reference", ctx)

    def test_report_persists_reference_comparison_and_excel_parity(self) -> None:
        ctx = DairyFarmModel(_scenario(days=2, herd_size=4, reference_benchmark="cdairy_airand_year15"), load_calibration()).run()
        with TemporaryDirectory() as tmp:
            write_reports(Path(tmp), ctx)
            summary = json.loads((Path(tmp) / "summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["reference_benchmark"]["id"], "cdairy_airand_year15")
        self.assertEqual(summary["excel_parity"]["source"]["strategy"], "AIRAND")

    def test_dashboard_includes_reference_comparison(self) -> None:
        ctx = DairyFarmModel(_scenario(days=1, herd_size=2, reference_benchmark="cdairy_airand_year15"), load_calibration()).run()
        payload = serialize_dashboard_run(ctx, "reference", 0.0)
        self.assertEqual(payload["reference_benchmark"]["id"], "cdairy_airand_year15")
        self.assertIn("comparison", payload["reference_benchmark"])


if __name__ == "__main__":
    unittest.main()
