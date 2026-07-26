from __future__ import annotations

import unittest

from dairy_abm.config import load_calibration
from dairy_abm.model import DairyFarmModel


def scenario(**overrides):
    base = {
        "name": "sensors-disease",
        "start_date": "2026-01-01",
        "days": 1,
        "seed": 17,
        "herd_size": 1,
        "land_cropland_ha": 0,
        "enable_land_agent": False,
    }
    base.update(overrides)
    return base


class SensorsDiseaseIntegrationTest(unittest.TestCase):
    def test_sensors_publish_thi_observed_dmi_sara_bolus_and_filtered_alerts(self) -> None:
        calibration = load_calibration()
        calibration["sensors"]["bolus_replacement_ticks"]["value"] = 2
        ctx = DairyFarmModel(
            scenario(
                days=3,
                ambient_temperature_c=30.0,
                relative_humidity_pct=70.0,
                herd=[
                    {
                        "id": "cow-1",
                        "rumen_ph_sensor": 5.6,
                        "activity_signal": 1.3,
                        "rumination_change_pct": -0.3,
                    }
                ],
            ),
            calibration,
        ).run()
        sensors = ctx.packets["sensor_observation_packet"].payload
        cow = ctx.packets["cow_daily_packet"].payload
        feed = ctx.packets["feed_crop_packet"].payload

        self.assertGreater(sensors["thi"], 72.0)
        self.assertIn("cow-1", sensors["observed_dmi_kg_by_cow"])
        self.assertEqual(sensors["rumen_ph_by_cow"]["cow-1"], 5.6)
        self.assertTrue(sensors["sara_risk_by_cow"]["cow-1"])
        self.assertEqual(sensors["bolus_status_by_cow"]["cow-1"], "replacement_due")
        self.assertTrue(sensors["estrus_by_cow"]["cow-1"])
        self.assertTrue(all("confidence" in alert for alert in sensors["filtered_alerts"]))
        self.assertIn("observed_dmi_kg", cow["cow_records"][0])
        self.assertTrue(cow["cow_records"][0]["estrus_detected"])
        self.assertEqual(feed["nir_crude_protein_fraction"], 0.16)

    def test_sensor_mastitis_alert_does_not_create_a_disease_case(self) -> None:
        calibration = load_calibration()
        calibration["disease"]["mastitis_daily_probability"]["value"] = 0.0
        calibration["disease"]["lameness_daily_probability"]["value"] = 0.0
        calibration["disease"]["transmission_daily_probability"]["value"] = 0.0
        ctx = DairyFarmModel(
            scenario(sensor_thermal_mastitis_cow_ids=["cow-1"], herd=[{"id": "cow-1"}]),
            calibration,
        ).run()
        sensors = ctx.packets["sensor_observation_packet"].payload
        disease = ctx.packets["disease_state_packet"].payload
        manager = ctx.packets["manager_packet"].payload

        self.assertEqual(len(sensors["mastitis_alerts"]), 1)
        self.assertEqual(disease["sensor_alert_count"], 1)
        self.assertEqual(disease["infected_count"], 0)
        self.assertEqual(disease["susceptible_count"], 1)
        self.assertEqual(manager["sensor_alert_count"], 1)

    def test_disease_outbreak_is_one_shot_and_compartments_are_conserved(self) -> None:
        calibration = load_calibration()
        calibration["disease"]["recovery_daily_probability"]["value"] = 0.0
        ctx = DairyFarmModel(
            scenario(
                days=2,
                herd_size=3,
                enable_disease_outbreak=True,
                disease_outbreak_tick=1,
                disease_outbreak_seed_count=2,
                disease_outbreak_label="mastitis",
            ),
            calibration,
        ).run()
        disease = ctx.packets["disease_state_packet"].payload

        self.assertEqual(len(ctx.state["disease_outbreak_history"]), 1)
        self.assertEqual(disease["infected_count"], 2)
        self.assertEqual(disease["quarantined_count"], 2)
        self.assertEqual(
            disease["susceptible_count"] + disease["infected_count"] + disease["recovered_count"],
            3,
        )

    def test_recovery_moves_cow_to_immune_compartment(self) -> None:
        calibration = load_calibration()
        calibration["disease"]["recovery_daily_probability"]["value"] = 1.0
        ctx = DairyFarmModel(
            scenario(herd=[{"id": "cow-1", "infection_state": "I"}]), calibration
        ).run()
        disease = ctx.packets["disease_state_packet"].payload

        self.assertEqual(disease["recovered"], 1)
        self.assertEqual(disease["recovered_count"], 1)
        self.assertEqual(disease["herd_immunity_status"], "full")
        self.assertEqual(ctx.state["cows"][0]["infection_state"], "R")

    def test_biosecurity_reduces_reported_transmission_pressure(self) -> None:
        calibration = load_calibration()
        calibration["disease"]["recovery_daily_probability"]["value"] = 0.0
        baseline = DairyFarmModel(
            scenario(
                herd_size=2,
                enable_disease_outbreak=True,
                disease_outbreak_tick=1,
                disease_outbreak_seed_count=1,
            ),
            calibration,
        ).run()
        protected = DairyFarmModel(
            scenario(
                herd_size=2,
                enable_disease_outbreak=True,
                disease_outbreak_tick=1,
                disease_outbreak_seed_count=1,
                biosecurity_level_pct=100.0,
            ),
            load_calibration(),
        ).run()

        self.assertGreater(
            baseline.packets["disease_state_packet"].payload["transmission_pressure"],
            protected.packets["disease_state_packet"].payload["transmission_pressure"],
        )


if __name__ == "__main__":
    unittest.main()
