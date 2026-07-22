from __future__ import annotations

import unittest

from dairy_abm.config import load_calibration
from dairy_abm.core import ConfigError
from dairy_abm.model import DairyFarmModel


def scenario(**overrides):
    base = {
        "name": "genetics-processor-land",
        "start_date": "2026-01-01",
        "days": 1,
        "seed": 3,
        "herd_size": 8,
        "land_cropland_ha": 0,
        "enable_land_agent": False,
    }
    base.update(overrides)
    return base


class GeneticsProcessorLandAgentsTest(unittest.TestCase):
    def test_processor_agent_is_present_but_zero_flow_by_default(self) -> None:
        ctx = DairyFarmModel(scenario(), load_calibration()).run()
        packet = ctx.packets["processor_packet"]
        cow = ctx.packets["cow_daily_packet"].payload
        self.assertEqual(packet.quality, "inactive")
        self.assertFalse(packet.payload["enabled"])
        self.assertEqual(packet.payload["milk_processed_l"], 0.0)
        self.assertEqual(packet.payload["farm_gate_milk_l"], cow["milk_l"])
        self.assertNotIn("land_packet", ctx.packets)

    def test_processor_opt_in_processes_milk_and_optional_whey(self) -> None:
        ctx = DairyFarmModel(
            scenario(enable_processor=True, enable_whey_processing=True, herd_size=2),
            load_calibration(),
        ).run()
        packet = ctx.packets["processor_packet"].payload
        cow = ctx.packets["cow_daily_packet"].payload
        self.assertTrue(packet["enabled"])
        self.assertEqual(packet["milk_processed_l"], cow["milk_l"])
        self.assertGreater(packet["processor_revenue"], cow["milk_revenue"])
        self.assertGreater(packet["processing_energy_kwh"], 0)
        self.assertGreater(packet["whey_l"], 0)
        self.assertAlmostEqual(sum(packet["product_mix"].values()), 1.0)

    def test_land_agent_disabled_keeps_feed_crop_land_ownership(self) -> None:
        ctx = DairyFarmModel(scenario(land_cropland_ha=4), load_calibration()).run()
        self.assertEqual(ctx.daily_records[0]["land_owner"], "feed_crop")
        self.assertEqual(ctx.packets["feed_crop_packet"].payload["land_owner"], "feed_crop")
        self.assertNotIn("land_packet", ctx.packets)

    def test_land_agent_opt_in_transfers_land_ownership(self) -> None:
        ctx = DairyFarmModel(scenario(enable_land_agent=True, land_cropland_ha=4), load_calibration()).run()
        self.assertEqual(ctx.daily_records[0]["land_owner"], "land")
        self.assertEqual(ctx.packets["land_packet"].payload["land_owner"], "land")
        self.assertEqual(ctx.packets["feed_crop_packet"].payload["land_owner"], "land")
        self.assertIn("land", ctx.daily_records[0]["execution_order"])

    def test_invalid_land_area_is_rejected_when_land_agent_enabled(self) -> None:
        with self.assertRaises(ConfigError):
            DairyFarmModel(scenario(enable_land_agent=True, land_cropland_ha=-1), load_calibration()).run()

    def test_annual_genetics_runs_on_calendar_year_end(self) -> None:
        ctx = DairyFarmModel(
            scenario(start_date="2026-12-31", days=1, herd_size=10),
            load_calibration(),
        ).run()
        packet = ctx.packets["genetics_packet"].payload
        self.assertEqual(packet["year"], 2026)
        self.assertEqual(packet["minimum_intake_record_days"], 35)
        self.assertGreater(packet["selected_parent_count"], 0)
        self.assertEqual(ctx.annual_records[0]["report"], "genetics")


if __name__ == "__main__":
    unittest.main()
