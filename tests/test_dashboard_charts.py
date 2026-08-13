"""Contract tests for backend-produced chart series and the charts page."""

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
CHARTS = (WEB / "js" / "charts.js").read_text(encoding="utf-8")
CSS = "\n".join(path.read_text(encoding="utf-8") for path in (WEB / "styles").glob("*.css"))


class DashboardChartsTests(unittest.TestCase):
    def test_serializer_exposes_backend_daily_monthly_and_annual_series(self) -> None:
        ctx = DairyFarmModel(
            {
                "name": "charts",
                "start_date": "2026-01-01",
                "days": 35,
                "seed": 12,
                "herd_size": 3,
            },
            load_calibration(),
        ).run()
        result = serialize_dashboard_run(ctx, "charts01", 0.1)

        self.assertEqual(len(result["series"]["daily"]), 35)
        self.assertEqual([row["day"] for row in result["series"]["monthly"]], ["2026-01", "2026-02"])
        self.assertEqual([row["day"] for row in result["series"]["annual"]], ["2026"])
        january = [row for row in ctx.daily_records if row["day"].startswith("2026-01")]
        monthly = result["series"]["monthly"][0]
        self.assertAlmostEqual(monthly["milk_l"], sum(row["milk_l"] for row in january))
        self.assertAlmostEqual(monthly["profit"], sum(row["profit"] for row in january))
        self.assertAlmostEqual(
            monthly["kg_co2e_per_l_milk"],
            sum(row["net_kg_co2e"] for row in january) / sum(row["milk_l"] for row in january),
        )
        self.assertIn("purchased_feed_kg_dm", monthly)
        self.assertIn("freshwater_withdrawal_l", monthly)
        self.assertIn("report_confidence", monthly)

    def test_missing_period_values_remain_unavailable(self) -> None:
        ctx = SimulationContext(
            scenario={"name": "missing-charts", "start_date": "2026-01-01", "days": 1},
            calibration={},
            rng=Random(1),
            events=EventLog(),
        )
        ctx.daily_records.append({"day": "2026-01-01", "milk_l": None})
        result = serialize_dashboard_run(ctx, "missing01", 0.0)
        for period in ("daily", "monthly", "annual"):
            with self.subTest(period=period):
                self.assertIsNone(result["series"][period][0]["milk_l"])
                self.assertIsNone(result["series"][period][0]["net_kg_co2e"])

    def test_charts_page_uses_registry_and_backend_period_series(self) -> None:
        self.assertIn('id="charts-content"', INDEX)
        self.assertIn("renderCharts", APP)
        self.assertIn("CHART_REGISTRY", APP)
        self.assertIn("d.series", APP)
        start = APP.index("function renderCharts")
        end = APP.index("function toolbar", start)
        charts_page = APP[start:end]
        self.assertNotIn("aggregate(", charts_page)
        for field in (
            "milk_l",
            "purchased_feed_kg_dm",
            "irrigation_l",
            "net_kwh",
            "electricity_generated_kwh",
            "biogas_volume_m3",
            "freshwater_withdrawal_l",
            "gross_kg_co2e",
            "avoided_kg_co2e",
            "net_kg_co2e",
            "kg_co2e_per_l_milk",
            "soil_carbon_delta_kg",
            "synthetic_fertilizer_saved_kg",
            "disease_economic_cost",
            "profit",
        ):
            self.assertIn(field, CHARTS)
        self.assertIn('"annual"', CHARTS)
        self.assertIn("charts-workspace", CSS)
        self.assertIn("chart-registry", CSS)


if __name__ == "__main__":
    unittest.main()
