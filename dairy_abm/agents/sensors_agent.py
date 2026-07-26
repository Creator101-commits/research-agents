from __future__ import annotations

from datetime import date

from dairy_abm.config import value
from dairy_abm.core import BaseAgent, Packet, require_fraction


class SensorsAgent(BaseAgent):
    name = "sensors"

    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        ctx.state.setdefault("sensor_fleet_history", [])

    def _thi(self) -> float | None:
        temperature_raw = self.ctx.scenario.get("ambient_temperature_c", value(self.ctx.calibration, "sensors.ambient_temperature_c"))
        humidity_raw = self.ctx.scenario.get("relative_humidity_pct", value(self.ctx.calibration, "sensors.relative_humidity_pct"))
        if not isinstance(temperature_raw, (int, float)) or not isinstance(humidity_raw, (int, float)):
            return None
        temperature = float(temperature_raw)
        humidity = float(humidity_raw)
        fahrenheit = 1.8 * temperature + 32.0
        return fahrenheit - (0.55 - 0.0055 * humidity) * (fahrenheit - 26.0)

    @staticmethod
    def _season_label(day: date) -> str:
        month = day.month
        if month in (12, 1, 2):
            return "winter"
        if month in (3, 4, 5):
            return "spring"
        if month in (6, 7, 8):
            return "summer"
        return "fall"

    def tick(self, day: date) -> None:
        cows = self.ctx.state.get("cows", [])
        missing_probability = require_fraction(
            "sensors.missing_reading_probability",
            float(value(self.ctx.calibration, "sensors.missing_reading_probability")),
        )
        dmi_noise = require_fraction(
            "sensors.dmi_sensor_noise_fraction",
            float(value(self.ctx.calibration, "sensors.dmi_sensor_noise_fraction")),
        )
        low_ph_threshold = float(value(self.ctx.calibration, "cow.sara_rumen_ph_threshold"))
        sara_ticks_required = int(value(self.ctx.calibration, "sensors.sara_consecutive_ticks"))
        bolus_replacement_ticks = int(value(self.ctx.calibration, "sensors.bolus_replacement_ticks"))
        fusion_mode = str(self.ctx.scenario.get("sensor_fusion_mode", "fused"))
        estrus_reliability = float(
            value(
                self.ctx.calibration,
                "sensors.estrus_fused_sensor_reliability"
                if fusion_mode == "fused"
                else "sensors.estrus_single_sensor_reliability",
            )
        )
        thermal_ids = set(self.ctx.scenario.get("sensor_thermal_mastitis_cow_ids", []))
        ambient_source = self.ctx.scenario.get(
            "ambient_temperature_c", value(self.ctx.calibration, "sensors.ambient_temperature_c")
        )
        humidity_source = self.ctx.scenario.get(
            "relative_humidity_pct", value(self.ctx.calibration, "sensors.relative_humidity_pct")
        )
        weather_available = isinstance(ambient_source, (int, float)) and isinstance(humidity_source, (int, float))
        ambient_temp = float(ambient_source) if weather_available else 0.0
        humidity = float(humidity_source) if weather_available else 0.0
        season = self._season_label(day)
        nir_seasonality = float(value(self.ctx.calibration, "sensors.nir_seasonality_modifier_fraction"))
        rumination_baseline = float(value(self.ctx.calibration, "sensors.rumination_baseline_minutes_per_day"))
        missing = 0
        observed_dmi: dict[str, float] = {}
        dmi_confidence: dict[str, float] = {}
        rumen_ph: dict[str, float] = {}
        sara_risk: dict[str, bool] = {}
        bolus_status: dict[str, str] = {}
        replacement_due_cow_ids: list[str] = []
        replacement_actions: list[str] = []
        estrus: dict[str, bool] = {}
        estrus_single: dict[str, bool] = {}
        estrus_fused: dict[str, bool] = {}
        estrus_candidates: dict[str, bool] = {}
        reproduction_signals: dict[str, dict[str, object]] = {}
        mastitis_alerts: list[dict[str, object]] = []
        filtered_alerts: list[dict[str, object]] = []
        observed_bcs: dict[str, float] = {}
        observed_bw: dict[str, float] = {}
        rumination_minutes: dict[str, float] = {}

        for cow in cows:
            cow_id = str(cow["id"])
            if bool(self.ctx.scenario.get("auto_replace_bolus", False)) and int(cow.get("rumen_bolus_age_ticks", 0)) >= bolus_replacement_ticks:
                cow["rumen_bolus_age_ticks"] = 0
                cow["low_ph_sensor_ticks"] = 0
                cow["rumen_bolus_replacement_reported"] = False
                replacement_actions.append(cow_id)
                self.ctx.events.add(day, self.name, "info", "rumen bolus replaced", cow_id=cow_id)
            if self.ctx.rng.random() < missing_probability:
                missing += 1
                dmi_confidence[cow_id] = 0.0
                continue
            true_dmi = float(cow.get("last_dmi_kg", value(self.ctx.calibration, "cow.base_dmi_kg_per_cow_day")))
            age = int(cow.get("rumen_bolus_age_ticks", 0))
            degradation = max(0.0, (age - int(bolus_replacement_ticks * 0.8)) / max(1, bolus_replacement_ticks))
            effective_dmi_noise = dmi_noise * (1.0 + degradation)
            observed_dmi[cow_id] = max(0.0, true_dmi * (1.0 + self.ctx.rng.gauss(0.0, effective_dmi_noise)))
            dmi_confidence[cow_id] = max(0.0, (1.0 - missing_probability) * (1.0 - 0.5 * degradation))
            bcs = float(cow.get("body_condition_score", value(self.ctx.calibration, "cow.initial_body_condition_score")))
            observed_bcs[cow_id] = max(0.0, bcs + self.ctx.rng.gauss(0.0, 0.1))
            bw = float(cow.get("body_weight_kg", value(self.ctx.calibration, "cow.initial_body_weight_kg")))
            observed_bw[cow_id] = max(0.0, bw + self.ctx.rng.gauss(0.0, 5.0))
            rumination_minutes[cow_id] = max(0.0, rumination_baseline + self.ctx.rng.gauss(0.0, 30.0))
            measured_ph = float(
                cow.get(
                    "rumen_ph_sensor",
                    cow.get("rumen_ph")
                    if cow.get("rumen_ph") is not None
                    else value(self.ctx.calibration, "sensors.rumen_ph_baseline"),
                )
            )
            rumen_ph[cow_id] = measured_ph
            cow["rumen_bolus_age_ticks"] = int(cow.get("rumen_bolus_age_ticks", 0)) + 1
            cow["low_ph_sensor_ticks"] = (
                int(cow.get("low_ph_sensor_ticks", 0)) + 1 if measured_ph < low_ph_threshold else 0
            )
            sara_risk[cow_id] = int(cow["low_ph_sensor_ticks"]) >= sara_ticks_required
            bolus_status[cow_id] = (
                "replacement_due"
                if int(cow["rumen_bolus_age_ticks"]) >= bolus_replacement_ticks
                else "healthy"
            )
            if bolus_status[cow_id] == "replacement_due":
                replacement_due_cow_ids.append(cow_id)
                if not cow.get("rumen_bolus_replacement_reported", False):
                    self.ctx.events.add(day, self.name, "warning", "rumen bolus replacement due", cow_id=cow_id)
                    cow["rumen_bolus_replacement_reported"] = True
            estrus_candidate = (
                float(cow.get("activity_signal", 0.0))
                >= float(value(self.ctx.calibration, "sensors.estrus_activity_threshold"))
                and float(cow.get("rumination_change_pct", 0.0))
                <= float(value(self.ctx.calibration, "sensors.estrus_rumination_change_threshold"))
            )
            estrus_single[cow_id] = bool(estrus_candidate and self.ctx.rng.random() <= float(value(self.ctx.calibration, "sensors.estrus_single_sensor_reliability")))
            fused_inputs_available = "activity_signal" in cow and "rumination_change_pct" in cow
            estrus_fused[cow_id] = bool(estrus_candidate and fused_inputs_available and self.ctx.rng.random() <= float(value(self.ctx.calibration, "sensors.estrus_fused_sensor_reliability")))
            estrus[cow_id] = estrus_fused[cow_id] if fusion_mode == "fused" and fused_inputs_available else estrus_single[cow_id]
            estrus_candidates[cow_id] = bool(estrus_candidate)
            cow["estrus_detected"] = estrus[cow_id]
            reproduction_signals[cow_id] = {"estrus_candidate_flag": estrus_candidates[cow_id], "estrus_flag_single": estrus_single[cow_id], "estrus_flag_fused": estrus_fused[cow_id], "estrus_detected": estrus[cow_id], "reliability": estrus_reliability if fusion_mode == "fused" and fused_inputs_available else float(value(self.ctx.calibration, "sensors.estrus_single_sensor_reliability"))}
            if cow_id in thermal_ids:
                alert = {
                    "cow_id": cow_id,
                    "type": "thermal_mastitis",
                    "severity": "warning",
                    "confidence": float(value(self.ctx.calibration, "sensors.thermal_mastitis_alert_confidence")),
                }
                mastitis_alerts.append(alert)
                filtered_alerts.append(alert)
            if sara_risk[cow_id]:
                filtered_alerts.append(
                    {"cow_id": cow_id, "type": "sara_risk", "severity": "warning", "confidence": 1.0}
                )

        season_adjusted_cp = require_fraction(
            "sensors.nir_crude_protein_fraction",
            float(value(self.ctx.calibration, "sensors.nir_crude_protein_fraction")) * (1.0 + nir_seasonality),
        )
        thi = self._thi() if weather_available else None
        quality = "ok" if missing == 0 and weather_available else "partial"
        fleet_health = {
            "total_boluses": len(cows),
            "replacement_due": len(replacement_due_cow_ids),
            "degraded": sum(1 for status in bolus_status.values() if status == "replacement_due"),
            "operational_fraction": (len(cows) - missing) / len(cows) if cows else 1.0,
        }
        self.ctx.publish(
            Packet(
                source=self.name,
                name="sensor_observation_packet",
                day=day,
                quality=quality,
                payload={
                    "observed_cows": len(cows) - missing,
                    "missing_readings": missing,
                    "thi": thi,
                    "heat_stress_flag": thi >= float(value(self.ctx.calibration, "cow.mild_heat_stress_thi")) if thi is not None else None,
                    "observed_dmi_kg_by_cow": observed_dmi,
                    "dmi_measurement_confidence_by_cow": dmi_confidence,
                    "rumen_ph_by_cow": rumen_ph,
                    "sara_risk_by_cow": sara_risk,
                    "bolus_status_by_cow": bolus_status,
                    "replacement_due_cow_ids": replacement_due_cow_ids,
                    "estrus_by_cow": estrus,
                    "estrus_candidate_flag": estrus_candidates,
                    "estrus_flag_single": estrus_single,
                    "estrus_flag_fused": estrus_fused,
                    "reproduction_signal_packet": reproduction_signals,
                    "fusion_mode": fusion_mode,
                    "estrus_reliability": estrus_reliability,
                    "nir_feed_profile": {
                        "crude_protein_fraction": season_adjusted_cp,
                        "valid": bool(self.ctx.scenario.get("nir_profile_available", True)),
                        "freshness_days": int(self.ctx.scenario.get("nir_profile_age_days", 0)),
                    },
                    "mastitis_alerts": mastitis_alerts,
                    "filtered_alerts": filtered_alerts,
                    "health_alerts": filtered_alerts,
                    "milk_noise_fraction": float(value(self.ctx.calibration, "sensors.milk_sensor_noise_fraction")),
                    "dmi_noise_fraction": dmi_noise,
                    "season": season,
                    "ambient_temperature_c": ambient_temp if weather_available else None,
                    "relative_humidity_pct": humidity if weather_available else None,
                    "weather_tick": {
                        "temperature_c": ambient_temp,
                        "humidity_pct": humidity,
                        "thi": thi,
                        "season": season,
                    },
                    "mean_body_condition_score_by_cow": observed_bcs,
                    "mean_body_weight_kg_by_cow": observed_bw,
                    "rumination_minutes_by_cow": rumination_minutes,
                    "nir_seasonality_modifier": nir_seasonality,
                    "fleet_health": fleet_health,
                    "weather_confidence": "estimated" if weather_available else "low",
                },
            )
        )
        self.ctx.state["sensor_fleet_history"].append(
            {
                "day": day.isoformat(),
                "fleet_health": fleet_health,
                "replacement_actions": replacement_actions,
                "missing_readings": missing,
            }
        )
        self.ctx.publish(
            Packet(
                source=self.name,
                name="sensor_maintenance_packet",
                day=day,
                payload={
                    "replacement_actions": replacement_actions,
                    "replacement_due_cow_ids": replacement_due_cow_ids,
                    "fleet_history_days": len(self.ctx.state["sensor_fleet_history"]),
                    "fleet_health": fleet_health,
                },
                confidence="estimated",
            )
        )
        self.ctx.state.setdefault("execution_order", []).append(self.name)
