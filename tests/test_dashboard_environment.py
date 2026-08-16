"""Contract tests for the authoritative environment dashboard audit."""

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


class DashboardEnvironmentTests(unittest.TestCase):
    def _run(self, **overrides):
        scenario = {
            "name": "environment-audit",
            "start_date": "2026-01-01",
            "days": 35,
            "seed": 23,
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

    def test_environment_contract_preserves_metrics_history_months_and_ledger_metadata(self) -> None:
        ctx = self._run()
        environment = serialize_dashboard_run(ctx, "env01", 0.2)["environment"]
        history = ctx.state["environment_history"]

        self.assertTrue(environment["available"])
        self.assertEqual(environment["period"], "run")
        self.assertEqual(len(environment["daily"]), len(history))
        self.assertEqual(
            environment["metrics"]["gross_kg_co2e"]["value"],
            sum(row["gross_kg_co2e"] for row in history),
        )
        self.assertEqual(
            environment["metrics"]["net_kg_co2e"]["value"],
            sum(row["net_kg_co2e"] for row in history),
        )
        self.assertEqual(
            len(environment["ledger"]),
            len(ctx.state["environment_ledger"]),
        )
        self.assertTrue(environment["ledger"])
        first = environment["ledger"][0]
        self.assertTrue(
            {"date", "source", "stream_id", "period", "unit", "quality", "confidence", "direction", "value"} <= set(first)
        )
        self.assertIn("environment_packet", environment["provenance"]["packet"]["name"])
        self.assertTrue(environment["monthly"])
        self.assertTrue(all(row["report"] == "environment" for row in environment["monthly"]))
        self.assertIsNotNone(environment["monthly"][0]["circularity_score"])
        self.assertIsNotNone(environment["monthly"][0]["sustainability_score_0_100"])

    def test_environment_contract_keeps_zero_denominator_and_missing_context_unavailable(self) -> None:
        zero = self._run(days=1, herd_size=0)
        environment = serialize_dashboard_run(zero, "env02", 0.0)["environment"]
        self.assertFalse(environment["metrics"]["ghg_intensity"]["available"])
        self.assertIsNone(environment["metrics"]["ghg_intensity"]["value"])

        missing = SimulationContext(
            scenario={"name": "missing-environment", "days": 1},
            calibration={},
            rng=Random(1),
            events=EventLog(),
        )
        environment = serialize_dashboard_run(missing, "env03", 0.0)["environment"]
        self.assertFalse(environment["available"])
        self.assertEqual(environment["ledger"], [])
        self.assertTrue(all(not metric["available"] for metric in environment["metrics"].values()))

    def test_environment_page_renders_serialized_values_without_browser_aggregation(self) -> None:
        self.assertIn('id="environment-content"', INDEX)
        self.assertIn("renderEnvironment", APP)
        start = APP.index("function renderEnvironment")
        end = APP.index("function toolbar", start)
        environment_page = APP[start:end]
        self.assertIn("data.environment", environment_page)
        self.assertIn("audit.ledger", environment_page)
        self.assertNotIn("aggregate(", environment_page)
        self.assertNotIn("gross_kg_co2e -", environment_page)
        self.assertIn("environment-audit", CSS)
        self.assertIn("environment-ledger", CSS)


if __name__ == "__main__":
    unittest.main()
