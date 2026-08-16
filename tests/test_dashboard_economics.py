"""Contract tests for the authoritative economics dashboard data."""

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


class DashboardEconomicsTests(unittest.TestCase):
    def _run(self, **overrides):
        scenario = {
            "name": "economics-audit",
            "start_date": "2026-01-01",
            "days": 35,
            "seed": 31,
            "herd_size": 4,
            "enable_processor": True,
            "enable_whey_processing": True,
            "l1_nutrient_loop_enabled": True,
            "l2_water_loop_enabled": True,
            "l3_energy_loop_enabled": True,
            "l4_byproduct_loop_enabled": True,
        }
        scenario.update(overrides)
        return DairyFarmModel(scenario, load_calibration()).run()

    def test_economics_contract_uses_daily_manager_outputs_and_reports(self) -> None:
        ctx = self._run()
        economics = serialize_dashboard_run(ctx, "econ01", 0.2)["economics"]
        daily = ctx.daily_records

        self.assertTrue(economics["available"])
        self.assertEqual(len(economics["daily"]), len(daily))
        self.assertEqual(
            economics["metrics"]["milk_revenue"]["value"],
            sum(row["milk_revenue"] for row in daily),
        )
        self.assertEqual(
            economics["metrics"]["total_revenue"]["value"],
            sum(row["total_revenue"] for row in daily),
        )
        self.assertEqual(
            economics["metrics"]["total_cost"]["value"],
            sum(row["total_cost"] for row in daily),
        )
        self.assertEqual(
            economics["metrics"]["profit"]["value"],
            sum(row["profit"] for row in daily),
        )
        self.assertEqual(
            economics["metrics"]["cumulative_profit"]["value"],
            sum(row["profit"] for row in daily),
        )
        self.assertTrue(economics["metrics"]["farm_npv"]["available"])
        self.assertEqual(
            economics["latest"]["byproduct_revenue"],
            ctx.packets["manager_packet"].payload["byproduct_revenue"],
        )
        self.assertEqual(
            economics["latest"]["labor_cost"],
            ctx.packets["manager_packet"].payload["labor_cost"],
        )
        self.assertTrue(economics["monthly"])
        self.assertTrue(all(row["report"] == "farm_manager" for row in economics["monthly"]))
        self.assertEqual(
            economics["market"]["milk_price_per_l"],
            ctx.state["market_history"][-1]["milk_price_per_l"],
        )
        self.assertIn("recommendation", economics["latest"])
        self.assertIn("policy_conflicts", economics["latest"])

    def test_economics_contract_keeps_unretained_historical_categories_unavailable(self) -> None:
        ctx = self._run(enable_processor=True)
        economics = serialize_dashboard_run(ctx, "econ02", 0.0)["economics"]

        self.assertTrue(all(row["byproduct_revenue"] is None for row in economics["daily"]))
        self.assertTrue(all(row["labor_cost"] is None for row in economics["daily"]))
        self.assertTrue(all(row["fixed_cost"] is None for row in economics["daily"]))
        self.assertTrue(all(row["treatment_cost"] is not None for row in economics["daily"]))
        self.assertFalse(economics["metrics"]["byproduct_revenue"]["available"])

        missing = SimulationContext(
            scenario={"name": "missing-economics", "days": 1},
            calibration={},
            rng=Random(1),
            events=EventLog(),
        )
        economics = serialize_dashboard_run(missing, "econ03", 0.0)["economics"]
        self.assertFalse(economics["available"])
        self.assertEqual(economics["daily"], [])
        self.assertTrue(all(not metric["available"] for metric in economics["metrics"].values()))

    def test_economics_page_renders_serialized_values_without_browser_aggregation(self) -> None:
        self.assertIn('id="economics-content"', INDEX)
        self.assertIn("renderEconomics", APP)
        start = APP.index("function renderEconomics")
        end = APP.index("function toolbar", start)
        economics_page = APP[start:end]
        self.assertIn("data.economics", economics_page)
        self.assertIn("audit.daily", economics_page)
        self.assertNotIn("aggregate(", economics_page)
        self.assertNotIn("profit /", economics_page)
        self.assertIn("economics-audit", CSS)
        self.assertIn("economics-breakdown", CSS)


if __name__ == "__main__":
    unittest.main()
