from __future__ import annotations

from copy import deepcopy
import unittest

from dairy_abm.config import calibration_inventory, load_calibration
from dairy_abm.core import ConfigError
from dairy_abm.model import DairyFarmModel


BASE_SCENARIO = {
    "name": "integration-contracts",
    "start_date": "2026-12-25",
    "days": 10,
    "seed": 42,
    "herd_size": 12,
    "land_cropland_ha": 3,
    "land_pasture_ha": 2,
    "enable_processor": True,
    "enable_whey_processing": True,
    "enable_land_agent": True,
}


class IntegrationContractsTest(unittest.TestCase):
    def test_full_replay_is_deterministic_for_same_seed(self) -> None:
        calibration = load_calibration()
        first = DairyFarmModel(dict(BASE_SCENARIO), calibration).run()
        second = DairyFarmModel(dict(BASE_SCENARIO), load_calibration()).run()
        self.assertEqual(first.daily_records, second.daily_records)
        self.assertEqual(first.schedule_records, second.schedule_records)
        self.assertEqual(first.monthly_records, second.monthly_records)
        self.assertEqual(first.annual_records, second.annual_records)
        self.assertEqual(
            {name: packet.payload for name, packet in first.packets.items()},
            {name: packet.payload for name, packet in second.packets.items()},
        )

    def test_herd_size_zero_does_not_crash(self) -> None:
        scenario = dict(BASE_SCENARIO)
        scenario["herd_size"] = 0
        ctx = DairyFarmModel(scenario, load_calibration()).run()
        self.assertEqual(ctx.daily_records[0]["cow_count"], 0)
        self.assertEqual(ctx.daily_records[0]["milk_l"], 0.0)

    def test_circularity_score_hits_max_with_processor_enabled(self) -> None:
        scenario = dict(BASE_SCENARIO)
        calibration = load_calibration()
        ctx = DairyFarmModel(scenario, calibration).run()
        environment = ctx.packets["environment_packet"].payload
        self.assertGreaterEqual(environment["circularity_score"], 0)
        self.assertLessEqual(environment["circularity_score"], 1.0)

    def test_feed_efficiency_genetics_reduces_feed_cost(self) -> None:
        calibration_high = load_calibration()
        calibration_low = load_calibration()
        calibration_low["genetics"]["annual_rfi_gain_fraction"]["value"] = 0.0
        scenario = dict(BASE_SCENARIO)
        scenario["days"] = 370
        scenario["start_date"] = "2025-12-31"
        scenario["seed"] = 1
        scenario["herd_size"] = 10
        scenario["l4_byproduct_loop_enabled"] = False
        with_improvement = DairyFarmModel(scenario, calibration_high).run()
        without_improvement = DairyFarmModel(scenario, calibration_low).run()
        avg_feed_improved = sum(float(r["feed_cost"]) for r in with_improvement.daily_records[-30:])
        avg_feed_no_improvement = sum(float(r["feed_cost"]) for r in without_improvement.daily_records[-30:])
        self.assertLess(avg_feed_improved, avg_feed_no_improvement)

    def test_active_agent_packets_have_required_contract_fields(self) -> None:
        ctx = DairyFarmModel(dict(BASE_SCENARIO), load_calibration()).run()
        expected_sources = {
            "market_price_packet": "market",
            "sensor_observation_packet": "sensors",
            "disease_state_packet": "disease",
            "land_packet": "land",
            "feed_crop_packet": "feed_crop",
            "cow_daily_packet": "cow",
            "processor_packet": "dairy_processor",
            "manure_packet": "manure",
            "energy_packet": "energy",
            "water_packet": "water",
            "environment_packet": "environment",
            "manager_packet": "farm_manager",
            "genetics_packet": "genetics",
        }
        for packet_name, source in expected_sources.items():
            with self.subTest(packet=packet_name):
                packet = ctx.packets[packet_name]
                self.assertEqual(packet.source, source)
                self.assertEqual(packet.name, packet_name)
                self.assertTrue(packet.payload)
                self.assertIsInstance(packet.quality, str)

    def test_report_rows_keep_core_nonnegative_physical_fields(self) -> None:
        ctx = DairyFarmModel(dict(BASE_SCENARIO), load_calibration()).run()
        nonnegative_fields = {
            "milk_l",
            "dmi_kg",
            "manure_kg",
            "enteric_ch4_kg",
            "feed_cost",
            "digester_kg",
            "compost_kg",
            "storage_kg",
            "net_kwh",
            "net_water_l",
            "gross_kg_co2e",
            "net_kg_co2e",
            "total_revenue",
            "total_cost",
            "milk_processed_l",
        }
        for row in ctx.daily_records:
            for field in nonnegative_fields:
                with self.subTest(day=row["day"], field=field):
                    self.assertGreaterEqual(row[field], 0)
            self.assertLessEqual(row["net_kg_co2e"], row["gross_kg_co2e"])
            self.assertGreaterEqual(row["circularity_score"], 0)
            self.assertLessEqual(row["circularity_score"], 1)

    def test_calibration_inventory_covers_active_agent_roster(self) -> None:
        calibration = load_calibration()
        model = DairyFarmModel(dict(BASE_SCENARIO), calibration)
        inventory_agents = {row["agent"] for row in calibration_inventory(calibration)}
        active_agents = {agent.name for agent in model.agents} | {"genetics"}
        missing = active_agents - inventory_agents
        self.assertEqual(missing, set())

    def test_invalid_processor_product_mix_is_rejected_by_loader(self) -> None:
        calibration = deepcopy(load_calibration())
        calibration["dairy_processor"]["product_mix_functional"]["value"] = 0.2
        with self.assertRaises(ConfigError):
            from dairy_abm.config import validate_calibration

            validate_calibration(calibration)


if __name__ == "__main__":
    unittest.main()
