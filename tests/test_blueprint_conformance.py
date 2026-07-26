from __future__ import annotations

from copy import deepcopy
import unittest

from dairy_abm.config import load_calibration
from dairy_abm.core import ConfigError
from dairy_abm.model import DairyFarmModel


def scenario(**overrides):
    base = {
        "name": "blueprint-conformance",
        "start_date": "2026-01-01",
        "days": 2,
        "seed": 47,
        "herd_size": 4,
        "land_cropland_ha": 1.0,
    }
    base.update(overrides)
    return base


class BlueprintConformanceTest(unittest.TestCase):
    def test_water_nutrient_recovery_is_a_one_day_soil_n_credit(self) -> None:
        calibration = load_calibration()
        calibration["water"]["nutrient_recovery_enabled"]["value"] = True
        calibration["water"]["nutrient_recovery_kg_n_per_l"]["value"] = 0.01
        ctx = DairyFarmModel(scenario(amino_acid_policy_active=False), calibration).run()

        first_water = ctx.state["water_history"][0]
        first_feed, second_feed = [
            row for row in ctx.state["feed_history"]
        ]
        expected_credit = first_water["treated_water_l"] * 0.01
        self.assertGreater(expected_credit, 0.0)
        self.assertEqual(first_feed["recovered_water_n_credit_kg"], 0.0)
        self.assertAlmostEqual(second_feed["recovered_water_n_credit_kg"], expected_credit)
        self.assertGreaterEqual(second_feed["fertilizer_n_required_kg"], 0.0)

    def test_environment_records_field_n2o_precursor_once(self) -> None:
        calibration = deepcopy(load_calibration())
        calibration["environment"]["field_n2o_kg_n2o_per_kg_n"]["value"] = 0.02
        ctx = DairyFarmModel(scenario(days=1), calibration).run()
        manure = ctx.packets["manure_packet"].payload
        environment = ctx.packets["environment_packet"].payload
        streams = {
            stream["stream_id"]: stream
            for stream in environment["environmental_streams"]
        }

        self.assertIn("field_n2o", streams)
        self.assertAlmostEqual(
            streams["field_n2o"]["kg_co2e"],
            manure["field_n2o_precursor_kg_n"] * 0.02 * calibration["environment"]["n2o_gwp100"]["value"],
        )

    def test_processor_residuals_are_conserved_and_reach_energy_and_manager(self) -> None:
        ctx = DairyFarmModel(
            scenario(days=1, enable_processor=True, enable_whey_processing=True), load_calibration()
        ).run()
        processor = ctx.packets["processor_packet"].payload
        residual = ctx.packets["processor_residual_packet"].payload
        manure = ctx.packets["manure_packet"].payload
        manager = ctx.packets["manager_packet"].payload

        self.assertAlmostEqual(
            residual["whey_feed_l"] + residual["whey_disposal_l"], processor["whey_l"]
        )
        self.assertAlmostEqual(
            residual["sludge_energy_l"] + residual["sludge_fertilizer_l"], processor["sludge_l"]
        )
        self.assertAlmostEqual(
            residual["waste_milk_feed_l"] + residual["waste_milk_energy_l"], processor["waste_milk_l"]
        )
        self.assertGreater(manure["processor_residual_energy_kg"], 0.0)
        self.assertGreaterEqual(processor["byproduct_revenue"], 0.0)
        self.assertEqual(manager["byproduct_revenue"], processor["byproduct_revenue"])

    def test_environment_monthly_report_flows_to_manager_with_policy_and_credit_kpis(self) -> None:
        calibration = load_calibration()
        calibration["farm_manager"]["carbon_credit_price_per_tonne_co2e"]["value"] = 50.0
        ctx = DairyFarmModel(
            scenario(
                start_date="2026-01-31",
                days=1,
                enable_land_agent=True,
                soil_carbon_sequestration_index=1.2,
                circular_investment_schedule=[{"name": "digester", "cost": 1000.0}],
            ),
            calibration,
        ).run()
        environment = ctx.packets["environment_packet"].payload
        manager = ctx.packets["manager_packet"].payload
        monthly_manager = next(row for row in ctx.monthly_records if row["report"] == "farm_manager")

        self.assertGreaterEqual(environment["soil_biodiversity_index"], 0.0)
        self.assertGreaterEqual(environment["sustainability_score_0_100"], 0.0)
        self.assertLessEqual(environment["sustainability_score_0_100"], 100.0)
        self.assertEqual(manager["carbon_credit_value"], environment["carbon_credit_value"])
        self.assertEqual(manager["investment_cost_basis"], 1000.0)
        self.assertTrue(manager["ranked_recommendations"])
        self.assertEqual(monthly_manager["environment_net_kg_co2e"], environment["net_kg_co2e"])

    def test_market_regime_sensor_replacement_and_grazing_genetics_context(self) -> None:
        calibration = load_calibration()
        calibration["sensors"]["bolus_replacement_ticks"]["value"] = 1
        ctx = DairyFarmModel(
            scenario(
                start_date="2026-12-31",
                days=1,
                enable_land_agent=True,
                land_grazing_enabled=True,
                market_scenario="GM",
                user_breeding_priority="sustainability",
                herd_size=2,
            ),
            calibration,
        ).run()
        market = ctx.packets["market_price_packet"].payload
        sensors = ctx.packets["sensor_observation_packet"].payload
        genetics = ctx.packets["genetics_packet"].payload

        self.assertIn(market["market_regime_label"], {"stable", "volatile"})
        self.assertEqual(market["realized_volatility"], 0.0)
        self.assertTrue(sensors["replacement_due_cow_ids"])
        self.assertTrue(any(event["message"] == "rumen bolus replacement due" for event in ctx.events.events))
        self.assertEqual(genetics["market_scenario"], "GM")
        self.assertEqual(genetics["user_breeding_priority"], "sustainability")
        self.assertTrue(genetics["grazing_context_active"])

    def test_scenario_dependencies_and_daily_confidence_contract(self) -> None:
        with self.assertRaises(ConfigError):
            DairyFarmModel(scenario(enable_whey_processing=True), load_calibration())
        with self.assertRaises(ConfigError):
            DairyFarmModel(
                scenario(land_seasonal_availability={"1": 0.5}), load_calibration()
            )

        ctx = DairyFarmModel(scenario(days=1), load_calibration()).run()
        self.assertIn("report_confidence", ctx.daily_records[0])
        self.assertIn("market", ctx.daily_records[0]["report_confidence"])

    def test_processor_residual_route_fractions_must_be_valid(self) -> None:
        calibration = deepcopy(load_calibration())
        calibration["dairy_processor"]["fraction_whey_to_feed"]["value"] = 1.01

        with self.assertRaises(ConfigError):
            DairyFarmModel(scenario(), calibration)


if __name__ == "__main__":
    unittest.main()
