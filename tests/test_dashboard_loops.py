"""Contract tests for authoritative circular-loop dashboard data."""

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


class DashboardLoopsTests(unittest.TestCase):
    def _run(self, **overrides):
        scenario = {
            "name": "loops",
            "start_date": "2026-01-01",
            "days": 2,
            "seed": 12,
            "herd_size": 3,
            "enable_processor": True,
            "enable_whey_processing": True,
            "l1_nutrient_loop_enabled": True,
            "l2_water_loop_enabled": True,
            "l3_energy_loop_enabled": True,
            "l4_byproduct_loop_enabled": True,
        }
        scenario.update(overrides)
        return DairyFarmModel(scenario, load_calibration()).run()

    def test_loop_sections_use_histories_and_packet_provenance(self) -> None:
        ctx = self._run()
        result = serialize_dashboard_run(ctx, "loops01", 0.1)
        loops = result["loops"]

        for key in ("l1", "l2", "l3", "l4"):
            with self.subTest(loop=key):
                self.assertIn(loops[key]["state"], {"active", "inactive", "unavailable"})
                self.assertTrue(loops[key]["enabled"])
                self.assertIn("metrics", loops[key])
                self.assertTrue(loops[key]["provenance"])
                self.assertIn("confidence", loops[key]["provenance"][0])

        l1 = loops["l1"]["metrics"]
        manure_history = ctx.state["manure_flow_history"]
        self.assertAlmostEqual(
            l1["manure_kg"]["value"],
            sum(row["manure_kg"] for row in manure_history),
        )
        self.assertAlmostEqual(
            l1["digestate_n_kg"]["value"],
            sum(row["digestate_n_kg"] for row in manure_history),
        )

        l2 = loops["l2"]["metrics"]
        water_history = ctx.state["water_history"]
        self.assertAlmostEqual(
            l2["total_water_use_l"]["value"],
            sum(row["total_water_use_l"] for row in water_history),
        )
        self.assertAlmostEqual(
            l2["recycled_irrigation_l"]["value"],
            sum(row["recycled_irrigation_l"] for row in water_history),
        )

        l3 = loops["l3"]["metrics"]
        energy_history = ctx.state["energy_history"]
        self.assertAlmostEqual(
            l3["feedstock_tons"]["value"],
            sum(row["feedstock_tons"] for row in energy_history),
        )
        self.assertAlmostEqual(
            l3["net_kwh"]["value"],
            sum(row["net_kwh"] for row in energy_history),
        )

        l4 = loops["l4"]
        processor = ctx.get_packet("processor_packet")
        self.assertEqual(l4["state"], "active")
        self.assertEqual(l4["details"]["product_streams_l"], processor.payload["product_streams_l"])
        self.assertEqual(l4["details"]["route_tiers"], processor.payload["route_tiers"])
        self.assertTrue(l4["metrics"]["milk_processed_l"]["available"])

        flow = loops["flow"]
        self.assertTrue({node["id"] for node in flow["nodes"]} >= {"cow", "milk", "manure", "energy"})
        self.assertTrue(flow["edges"])
        self.assertTrue(all(edge["state"] in {"active", "inactive", "unavailable"} for edge in flow["edges"]))

    def test_disabled_and_missing_loop_data_are_not_reported_as_active(self) -> None:
        ctx = self._run(
            enable_processor=False,
            enable_whey_processing=False,
            l1_nutrient_loop_enabled=False,
            l2_water_loop_enabled=False,
            l3_energy_loop_enabled=False,
            l4_byproduct_loop_enabled=False,
        )
        loops = serialize_dashboard_run(ctx, "loops02", 0.0)["loops"]
        for key in ("l1", "l2", "l3", "l4"):
            with self.subTest(loop=key):
                self.assertEqual(loops[key]["state"], "inactive")

        missing = SimulationContext(
            scenario={"name": "missing-loops", "days": 1},
            calibration={},
            rng=Random(1),
            events=EventLog(),
        )
        loops = serialize_dashboard_run(missing, "loops03", 0.0)["loops"]
        for key in ("l1", "l2", "l3", "l4"):
            with self.subTest(loop=key):
                self.assertEqual(loops[key]["state"], "unavailable")
                self.assertFalse(loops[key]["enabled"])

    def test_loops_page_renders_backend_state_without_browser_aggregation(self) -> None:
        self.assertIn('id="loops-content"', INDEX)
        self.assertIn("renderLoops", APP)
        self.assertIn("data.loops", APP)
        start = APP.index("function renderLoops")
        end = APP.index("function toolbar", start)
        loops_page = APP[start:end]
        self.assertNotIn("aggregate(", loops_page)
        self.assertIn("active", loops_page)
        self.assertIn("inactive", loops_page)
        self.assertIn("unavailable", loops_page)
        self.assertIn("loop-flow", CSS)
        self.assertIn("loop-section", CSS)


if __name__ == "__main__":
    unittest.main()
