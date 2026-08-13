"""Contract tests for the authoritative dashboard overview."""

from __future__ import annotations

from pathlib import Path
from random import Random
import unittest

from dairy_abm.config import load_calibration
from dairy_abm.core import EventLog, SimulationContext
from dairy_abm.dashboard import serialize_dashboard_run
from dairy_abm.model import DairyFarmModel


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
INDEX = (WEB / "index.html").read_text(encoding="utf-8")
APP = (WEB / "js" / "app.js").read_text(encoding="utf-8")
CSS = "\n".join(path.read_text(encoding="utf-8") for path in (WEB / "styles").glob("*.css"))


class DashboardOverviewTests(unittest.TestCase):
    def test_overview_contract_contains_verified_run_kpis(self) -> None:
        ctx = DairyFarmModel(
            {
                "name": "overview",
                "start_date": "2026-01-01",
                "days": 2,
                "seed": 12,
                "herd_size": 3,
            },
            load_calibration(),
        ).run()
        result = serialize_dashboard_run(ctx, "overview1", 0.1)
        for key in (
            "milk",
            "average_milk_per_cow",
            "profit",
            "total_revenue",
            "total_cost",
            "net_co2e",
            "ghg_intensity",
            "fcr",
            "freshwater",
            "energy_avg",
            "circularity",
            "sustainability_avg",
            "disease_cases",
            "herd_size",
        ):
            with self.subTest(key=key):
                self.assertIn(key, result["summary"])
                self.assertIn("available", result["summary"][key])

        rows = ctx.daily_records
        positive_cow_rows = [row for row in rows if row["cow_count"] > 0]
        expected_average = sum(row["milk_l"] / row["cow_count"] for row in positive_cow_rows) / len(positive_cow_rows)
        expected_intensity = sum(row["net_kg_co2e"] for row in rows) / sum(row["milk_l"] for row in rows)
        expected_fcr = sum(row["dmi_kg"] for row in rows) / sum(row["milk_l"] for row in rows)
        self.assertAlmostEqual(result["summary"]["average_milk_per_cow"]["value"], expected_average)
        self.assertAlmostEqual(result["summary"]["ghg_intensity"]["value"], expected_intensity)
        self.assertAlmostEqual(result["summary"]["fcr"]["value"], expected_fcr)
        self.assertEqual(result["summary"]["herd_size"]["value"], rows[-1]["cow_count"])
        self.assertEqual(result["summary"]["disease_cases"]["value"], rows[-1]["active_disease_cases"])

    def test_overview_marks_missing_kpis_unavailable(self) -> None:
        ctx = SimulationContext(
            scenario={"name": "missing-overview", "days": 1},
            calibration={},
            rng=Random(1),
            events=EventLog(),
        )
        ctx.daily_records.append({"day": "2026-01-01"})
        result = serialize_dashboard_run(ctx, "missing01", 0.0)
        for key in ("average_milk_per_cow", "ghg_intensity", "fcr", "circularity", "disease_cases", "herd_size"):
            with self.subTest(key=key):
                self.assertIsNone(result["summary"][key]["value"])
                self.assertFalse(result["summary"][key]["available"])

    def test_overview_is_a_run_summary_and_preserves_unavailable_values(self) -> None:
        self.assertIn('id="overview-content"', INDEX)
        self.assertIn("renderOverview", APP)
        self.assertIn("average_milk_per_cow", APP)
        self.assertIn("Total milk", APP)
        self.assertIn("Milk production", APP)
        self.assertIn("Environmental performance", APP)
        self.assertIn("Resource use", APP)
        self.assertIn('available === false', APP)
        self.assertIn("N/A", APP)
        self.assertIn("overview-charts", CSS)
        self.assertIn("overview-kpis", CSS)

    def test_overview_uses_backend_series_without_period_rollups(self) -> None:
        start = APP.index("function renderOverview")
        end = APP.index("function toolbar", start)
        overview = APP[start:end]
        self.assertIn("d.series", overview)
        self.assertIn("overviewChart", overview)
        self.assertIn("svgChart(", APP)
        self.assertNotIn("aggregate(", overview)


if __name__ == "__main__":
    unittest.main()
