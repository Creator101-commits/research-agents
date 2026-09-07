from __future__ import annotations

import unittest

from dairy_abm.analysis.dmc import (
    annual_premium,
    dmc_feed_cost,
    dmc_margin,
    monthly_indemnity,
    tiered_monthly_indemnity,
)
from dairy_abm.analysis.farm_system_comparison import assess_farm_systems
from dairy_abm.analysis.investment import analyze_investments, estimate_loop_capex
from dairy_abm.config import load_calibration
from dairy_abm.farm_systems import list_farm_systems, resolve_farm_system
from dairy_abm.model import DairyFarmModel


class AbstractAlignmentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.calibration = load_calibration()

    def test_five_named_system_profiles_exist_and_explicit_values_win(self) -> None:
        self.assertEqual(
            list_farm_systems(),
            ("conventional", "robotic", "certified_organic", "raw_milk", "beef_on_dairy"),
        )
        scenario, _, profile = resolve_farm_system(
            {
                "farm_system": "certified-organic",
                "production_system": "arid_grazing",
                "enable_land_agent": True,
            },
            self.calibration,
        )
        self.assertEqual(scenario["farm_system"], "certified_organic")
        self.assertEqual(scenario["production_system"], "arid_grazing")
        self.assertEqual(profile["constraints"]["minimum_grazing_days"], 120)
        self.assertEqual(profile["constraints"]["minimum_pasture_dmi_fraction"], 0.30)

    def test_capex_is_sized_and_can_be_replaced_by_farm_specific_quotes(self) -> None:
        scenario = {
            "herd_size": 100,
            "land_cropland_ha": 80,
            "enable_processor": True,
            "l1_nutrient_loop_enabled": True,
            "l2_water_loop_enabled": True,
            "l3_energy_loop_enabled": True,
            "l4_byproduct_loop_enabled": True,
        }
        estimates = estimate_loop_capex(scenario, self.calibration)
        self.assertAlmostEqual(
            estimates["l1_nutrient"]["capex"],
            2712.96 + 80 * 2.47105381 * 14.99,
        )
        self.assertAlmostEqual(estimates["l3_energy"]["capex"], 12602.22 + 100 * 372.58)
        self.assertAlmostEqual(estimates["l4_byproduct"]["capex"], 100 * 944.095238)

        scenario["investment_capex_overrides"] = {"l3_energy": 250000.0}
        overridden = estimate_loop_capex(scenario, self.calibration)
        self.assertEqual(overridden["l3_energy"]["capex"], 250000.0)
        self.assertEqual(overridden["l3_energy"]["capex_method"], "scenario_override")

    def test_fifteen_year_roi_uses_initial_capital_and_fifteen_annual_flows(self) -> None:
        scenario = {
            "herd_size": 10,
            "land_cropland_ha": 0,
            "enable_processor": False,
            "l1_nutrient_loop_enabled": False,
            "l2_water_loop_enabled": False,
            "l3_energy_loop_enabled": True,
            "l4_byproduct_loop_enabled": False,
            "investment_capex_overrides": {"l3_energy": 1000.0},
        }
        records = [{"energy_value": 100.0, "carbon_credit_value": 0.0}]
        result = analyze_investments(scenario, self.calibration, records)
        energy = result["technologies"]["l3_energy"]
        self.assertEqual(len(energy["cash_flows"]), 16)
        self.assertEqual(energy["cash_flows"][0], -1000.0)
        self.assertEqual(energy["annual_net_benefit"], 36500.0)
        self.assertAlmostEqual(energy["simple_payback_years"], 1000.0 / 36500.0)
        self.assertAlmostEqual(energy["fifteen_year_roi"], (15 * 36500.0 - 1000.0) / 1000.0)

    def test_usda_dmc_formula_premium_and_payment_examples(self) -> None:
        self.assertAlmostEqual(dmc_feed_cost(3.56, 314.92, 201.0), 8.88753)
        self.assertAlmostEqual(dmc_margin(16.60, 3.56, 314.92, 201.0), 7.71247)
        self.assertAlmostEqual(monthly_indemnity(7.71, 8.0, 4_400_000, 0.95), 1010.1666667, places=2)
        premium = annual_premium(4_400_000, 0.95, 8.0)
        self.assertAlmostEqual(premium["premium_after_discount"], 4180.0)
        self.assertAlmostEqual(premium["total_annual_cost"], 4280.0)

    def test_dmc_tier_one_limit_and_separate_tier_two_election(self) -> None:
        tier1_only = annual_premium(10_000_000, 0.95, 9.5)
        self.assertEqual(tier1_only["tier1_covered_lb"], 5_700_000.0)
        self.assertEqual(tier1_only["tier2_covered_lb"], 0.0)
        self.assertEqual(tier1_only["uncovered_production_lb"], 4_300_000.0)

        split = annual_premium(
            10_000_000,
            0.95,
            9.5,
            tier2_coverage_level=8.0,
        )
        self.assertEqual(split["tier1_covered_lb"], 5_700_000.0)
        self.assertEqual(split["tier2_covered_lb"], 3_800_000.0)
        self.assertEqual(split["tier2_coverage_level_usd_cwt"], 8.0)
        payments = tiered_monthly_indemnity(7.0, split)
        self.assertAlmostEqual(payments["tier1"], 11875.0)
        self.assertAlmostEqual(payments["tier2"], 3166.6666667, places=4)
        self.assertAlmostEqual(payments["total"], 15041.6666667, places=4)

    def test_model_publishes_investment_and_dmc_analysis_without_conflating_margin_types(self) -> None:
        ctx = DairyFarmModel(
            {
                "days": 2,
                "herd_size": 4,
                "farm_system": "robotic",
                "l3_energy_loop_enabled": True,
                "dmc_market_inputs": {
                    "all_milk_usd_cwt": 20.0,
                    "corn_usd_bu": 4.0,
                    "soybean_meal_usd_ton": 300.0,
                    "alfalfa_usd_ton": 220.0,
                },
            },
            self.calibration,
        ).run()
        investment = ctx.packets["investment_analysis_packet"].payload
        dmc = ctx.packets["dmc_analysis_packet"].payload
        self.assertEqual(investment["analysis_horizon_years"], 15)
        self.assertIn("fifteen_year_roi", investment["technologies"]["l3_energy"])
        self.assertEqual(dmc["official_status"], "computed")
        self.assertFalse(dmc["simulated_iofc_is_official_dmc_margin"])
        self.assertIn("investment_analysis", ctx.packets["manager_packet"].payload)

    def test_loop_switches_control_the_physical_recovery_they_name(self) -> None:
        disabled = DairyFarmModel(
            {
                "days": 2,
                "herd_size": 4,
                "land_cropland_ha": 1,
                "l1_nutrient_loop_enabled": False,
                "l2_water_loop_enabled": False,
                "amino_acid_policy_active": False,
            },
            self.calibration,
        ).run()
        enabled = DairyFarmModel(
            {
                "days": 2,
                "herd_size": 4,
                "land_cropland_ha": 1,
                "l1_nutrient_loop_enabled": True,
                "l2_water_loop_enabled": True,
                "amino_acid_policy_active": False,
            },
            self.calibration,
        ).run()
        self.assertEqual(disabled.packets["manure_packet"].payload["nutrient_return_kg"], 0.0)
        self.assertEqual(disabled.packets["water_packet"].payload["treated_water_l"], 0.0)
        self.assertGreater(enabled.packets["manure_packet"].payload["nutrient_return_kg"], 0.0)
        self.assertGreater(enabled.packets["water_packet"].payload["treated_water_l"], 0.0)

    def test_assessment_executes_all_five_systems_and_each_loop(self) -> None:
        assessment = assess_farm_systems(
            {
                "name": "abstract-alignment",
                "start_date": "2026-01-01",
                "days": 1,
                "herd_size": 2,
                "land_cropland_ha": 1,
                "land_pasture_ha": 1,
                "enable_land_agent": False,
            },
            self.calibration,
            seeds=(3,),
        )
        self.assertEqual(assessment["run_count"], 30)
        self.assertEqual({row["farm_system"] for row in assessment["runs"]}, set(list_farm_systems()))
        self.assertEqual(
            {row["configuration"] for row in assessment["runs"]},
            {"none", "l1_nutrient", "l2_water", "l3_energy", "l4_byproduct", "all"},
        )
        self.assertTrue(all("portfolio_fifteen_year_roi" in row for row in assessment["runs"]))
        self.assertTrue(all("counterfactual_annual_net_benefit" in row for row in assessment["runs"]))
        self.assertTrue(all(row["dmc_premium_change_attributable_to_loop"] == 0.0 for row in assessment["runs"]))


if __name__ == "__main__":
    unittest.main()
