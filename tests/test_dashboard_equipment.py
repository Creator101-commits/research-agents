"""Contract tests for the repository-native equipment ROI dashboard data."""

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


class DashboardEquipmentTests(unittest.TestCase):
    def _run(self, **overrides):
        scenario = {
            "name": "equipment-audit",
            "start_date": "2026-01-01",
            "days": 35,
            "seed": 41,
            "herd_size": 4,
            "enable_processor": True,
            "enable_whey_processing": True,
            "l1_nutrient_loop_enabled": True,
            "l2_water_loop_enabled": True,
            "l3_energy_loop_enabled": True,
            "l4_byproduct_loop_enabled": True,
            "equipment_capex": {
                "milking_parlour_bulk_tank": 1000,
                "dairy_processor": 2000,
                "whey_processor": 500,
                "manure_system": 1500,
            },
        }
        scenario.update(overrides)
        return DairyFarmModel(scenario, load_calibration()).run()

    def test_equipment_contract_uses_manager_assets_and_existing_npv(self) -> None:
        ctx = self._run()
        equipment = serialize_dashboard_run(ctx, "roi01", 0.3)["equipment"]

        self.assertTrue(equipment["available"])
        self.assertEqual(
            {asset["id"] for asset in equipment["assets"]},
            {"milking_parlour_bulk_tank", "dairy_processor", "whey_processor", "manure_system"},
        )
        processor = next(asset for asset in equipment["assets"] if asset["id"] == "dairy_processor")
        manager = ctx.packets["manager_packet"].payload["equipment_roi"]["dairy_processor"]
        self.assertEqual(processor["capex"], manager["capex"])
        self.assertEqual(processor["annual_benefit"], manager["annual_benefit"])
        self.assertEqual(processor["roi"], manager["roi"])
        self.assertEqual(processor["payback_years"], manager["payback_years"])
        self.assertEqual(equipment["equipment_npvs"]["dairy_processor"], processor["npv"])
        self.assertEqual(equipment["discount_rate"], 0.06)
        self.assertEqual(equipment["provenance"]["manager_packet"]["name"], "manager_packet")

    def test_zero_capex_keeps_roi_and_payback_unavailable(self) -> None:
        ctx = self._run(equipment_capex={"dairy_processor": 0})
        equipment = serialize_dashboard_run(ctx, "roi02", 0.0)["equipment"]
        processor = next(asset for asset in equipment["assets"] if asset["id"] == "dairy_processor")

        self.assertEqual(processor["capex"], 0.0)
        self.assertIsNone(processor["roi"])
        self.assertIsNone(processor["payback_years"])
        self.assertIn("zero_capex", processor["status"])

        missing = SimulationContext(
            scenario={"name": "missing-equipment", "days": 1},
            calibration={},
            rng=Random(1),
            events=EventLog(),
        )
        equipment = serialize_dashboard_run(missing, "roi03", 0.0)["equipment"]
        self.assertFalse(equipment["available"])
        self.assertEqual(equipment["assets"], [])
        self.assertEqual(equipment["equipment_npvs"], {})

    def test_equipment_page_only_mentions_model_represented_assets(self) -> None:
        self.assertIn('id="equipment-content"', INDEX)
        self.assertIn("renderEquipment", APP)
        start = APP.index("function renderEquipment")
        end = APP.index("function toolbar", start)
        equipment_page = APP[start:end]
        self.assertIn("data.equipment", equipment_page)
        self.assertIn("equipment.assets", equipment_page)
        self.assertNotIn("function npv", equipment_page)
        self.assertNotIn("anaerobic digester", equipment_page.lower())
        self.assertIn("equipment-roi", CSS)
        self.assertIn("equipment-card", CSS)


if __name__ == "__main__":
    unittest.main()
