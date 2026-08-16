"""Contract tests for the read-only model details dashboard page."""

from __future__ import annotations

from pathlib import Path
from random import Random
import unittest

from dairy_abm.config import calibration_inventory, load_calibration
from dairy_abm.core import EventLog, SimulationContext
from dairy_abm.dashboard import serialize_dashboard_run
from dairy_abm.model import DairyFarmModel
from dairy_abm.reports import REPORT_CONTRACT


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
INDEX = (WEB / "index.html").read_text(encoding="utf-8")
APP = (WEB / "js" / "app.js").read_text(encoding="utf-8")
CSS = "\n".join(path.read_text(encoding="utf-8") for path in (WEB / "styles").glob("*.css"))


class DashboardModelDetailsTests(unittest.TestCase):
    @staticmethod
    def run_model(**overrides):
        scenario = {
            "name": "details-audit",
            "start_date": "2026-01-01",
            "days": 1,
            "seed": 23,
            "herd_size": 3,
            "enable_processor": False,
            "enable_whey_processing": False,
            "enable_land_agent": False,
            "l1_nutrient_loop_enabled": True,
            "l2_water_loop_enabled": True,
            "l3_energy_loop_enabled": True,
            "l4_byproduct_loop_enabled": True,
        }
        scenario.update(overrides)
        return DairyFarmModel(scenario, load_calibration()).run()

    def test_details_use_actual_run_configuration_and_authoritative_records(self) -> None:
        ctx = self.run_model()
        details = serialize_dashboard_run(
            ctx,
            "details01",
            0.37,
            calibration_overrides={"genetics.selection_intensity": 0.4},
        )["model_details"]

        self.assertTrue(details["available"])
        self.assertEqual(details["scenario"], "details-audit")
        self.assertEqual(details["days"], 1)
        self.assertEqual(details["seed"], 23)
        self.assertEqual(details["herd_size"], 3)
        self.assertEqual(details["run_duration_s"], 0.37)
        self.assertEqual(details["calibration_override_count"], 1)
        self.assertEqual(
            details["assumption_count"],
            sum(row["assumption"] for row in calibration_inventory(ctx.calibration)),
        )
        self.assertEqual(details["event_count"], len(ctx.events.events))
        self.assertEqual(details["report_contract"], REPORT_CONTRACT)
        self.assertEqual(details["active_agent_count"], ctx.daily_records[-1]["agent_count"])
        self.assertEqual(
            details["scheduler"]["latest_execution_order"],
            ctx.daily_records[-1]["execution_order"].split(","),
        )
        self.assertFalse(details["enabled_systems"]["enable_processor"])
        self.assertFalse(details["enabled_systems"]["enable_land_agent"])
        self.assertEqual(details["loop_states"]["l1"], "active")
        self.assertEqual(
            details["policy_summary"]["effective_policy"],
            ctx.packets["manager_packet"].payload["effective_policy"],
        )

    def test_details_remain_safe_when_context_has_no_run_records(self) -> None:
        ctx = SimulationContext(
            scenario={"name": "empty", "days": 0, "seed": 1},
            calibration={},
            rng=Random(1),
            events=EventLog(),
        )
        details = serialize_dashboard_run(ctx, "details02", 0.0)["model_details"]

        self.assertFalse(details["available"])
        self.assertIsNone(details["active_agent_count"])
        self.assertEqual(details["scheduler"]["records"], [])
        self.assertEqual(details["assumption_count"], 0)
        self.assertEqual(details["event_count"], 0)

    def test_model_details_page_is_read_only_and_uses_serialized_fields(self) -> None:
        self.assertIn('id="model-details-content"', INDEX)
        self.assertIn("renderModelDetails", APP)
        self.assertIn("model_details", APP)
        self.assertIn("policy_summary", APP)
        self.assertIn("report_contract", APP)
        self.assertIn("model-details", CSS)
        self.assertNotIn("13 active agents", APP.lower())


if __name__ == "__main__":
    unittest.main()
