from __future__ import annotations

from datetime import date

from dairy_abm.config import value
from dairy_abm.core import BaseAgent, Packet, require_fraction, require_nonnegative


class DiseaseAgent(BaseAgent):
    name = "disease"

    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        ctx.state.setdefault("disease_outbreak_history", [])
        ctx.state.setdefault("disease_history", [])
        ctx.state.setdefault("disease_tick", 0)
        ctx.state.setdefault("outbreak_state", {"active": False, "start_day": None, "end_day": None, "cumulative_economic_cost": 0.0})
        for cow in ctx.state.get("cows", []):
            cow.setdefault(
                "infection_state",
                "I" if cow.get("health_status") != "healthy" else "S",
            )
            cow.setdefault("days_infected", 0)
            cow.setdefault("quarantine_flag", False)
            cow.setdefault("vaccinated", False)

    def _seed_outbreak(self, day: date, cows: list[dict[str, object]]) -> int:
        if not bool(self.ctx.scenario.get("enable_disease_outbreak", False)):
            return 0
        target_tick = int(self.ctx.scenario.get("disease_outbreak_tick", 100))
        configured_start = self.ctx.scenario.get("disease_outbreak_start_date")
        starts_today = str(configured_start) == day.isoformat() if configured_start else self.ctx.state["disease_tick"] == target_tick
        if not starts_today or self.ctx.state["disease_outbreak_history"]:
            return 0
        seed_count = max(0, int(self.ctx.scenario.get("disease_outbreak_seed_count", 1)))
        label = str(self.ctx.scenario.get("disease_outbreak_label", "mastitis"))
        seeded = 0
        for cow in cows:
            if seeded >= seed_count:
                break
            if cow.get("alive", True) and cow.get("infection_state") == "S":
                cow["infection_state"] = "I"
                cow["health_status"] = "sick"
                cow["disease"] = label
                cow["days_infected"] = 0
                seeded += 1
        self.ctx.state["disease_outbreak_history"].append(
            {"day": day.isoformat(), "tick": self.ctx.state["disease_tick"], "label": label, "seeded": seeded}
        )
        return seeded

    def tick(self, day: date) -> None:
        cows = self.ctx.state.get("cows", [])
        for cow in cows:
            cow.setdefault(
                "infection_state",
                "I" if cow.get("health_status") != "healthy" else "S",
            )
            cow.setdefault("days_infected", 0)
            cow.setdefault("quarantine_flag", False)
        self.ctx.state["disease_tick"] = int(self.ctx.state["disease_tick"]) + 1
        mastitis_probability = require_fraction(
            "disease.mastitis_daily_probability",
            float(value(self.ctx.calibration, "disease.mastitis_daily_probability")),
        )
        lameness_probability = require_fraction(
            "disease.lameness_daily_probability",
            float(value(self.ctx.calibration, "disease.lameness_daily_probability")),
        )
        recovery_probability = require_fraction(
            "disease.recovery_daily_probability",
            float(value(self.ctx.calibration, "disease.recovery_daily_probability")),
        )
        mortality_probability = require_fraction(
            "disease.disease_mortality_daily_probability",
            float(value(self.ctx.calibration, "disease.disease_mortality_daily_probability")),
        )
        sensor_packet = self.ctx.get_packet("sensor_observation_packet")
        sensor_alerts = (
            list(sensor_packet.payload.get("mastitis_alerts", [])) if sensor_packet is not None else []
        )
        outbreak_seeded = self._seed_outbreak(day, cows)
        infected_cows = [
            cow for cow in cows if cow.get("alive", True) and cow.get("infection_state") == "I"
        ]
        quarantine_enabled = bool(value(self.ctx.calibration, "disease.quarantine_enabled"))
        for cow in infected_cows:
            cow["quarantine_flag"] = quarantine_enabled
        quarantine_effectiveness = require_fraction(
            "disease.quarantine_effectiveness_fraction",
            float(value(self.ctx.calibration, "disease.quarantine_effectiveness_fraction")),
        )
        infectious_equivalent = sum(
            1.0 - quarantine_effectiveness if cow.get("quarantine_flag", False) else 1.0
            for cow in infected_cows
        )
        live_count = sum(1 for cow in cows if cow.get("alive", True))
        policy = self.ctx.state["policy"]
        raw_biosecurity = float(policy.get("biosecurity_level_pct", self.ctx.scenario.get("biosecurity_level_pct", 0.0)))
        biosecurity_level = require_fraction("policy.biosecurity_level", raw_biosecurity / 100.0 if raw_biosecurity > 1.0 else raw_biosecurity)
        biosecurity_effectiveness = require_fraction(
            "disease.biosecurity_effectiveness_fraction",
            float(value(self.ctx.calibration, "disease.biosecurity_effectiveness_fraction")),
        )
        transmission_probability = require_fraction(
            "disease.transmission_daily_probability",
            float(value(self.ctx.calibration, "disease.transmission_daily_probability")),
        )
        herd_density_modifier = require_nonnegative(
            "disease.herd_density_transmission_multiplier",
            float(value(self.ctx.calibration, "disease.herd_density_transmission_multiplier")),
        )
        transmission_pressure_base = (
            transmission_probability
            * infectious_equivalent
            / live_count
            * (1.0 - biosecurity_level * biosecurity_effectiveness)
            if live_count
            else 0.0
        )
        transmission_pressure = transmission_pressure_base * herd_density_modifier

        vaccination_effectiveness = require_fraction(
            "disease.vaccination_effectiveness_fraction",
            float(value(self.ctx.calibration, "disease.vaccination_effectiveness_fraction")),
        )
        vaccinated_today = 0
        if bool(policy.get("vaccination_policy_active", False)):
            target_coverage = require_fraction(
                "vaccination_target_coverage",
                float(self.ctx.scenario.get("vaccination_target_coverage", 1.0)),
            )
            target_count = round(live_count * target_coverage)
            daily_capacity = max(0, int(self.ctx.scenario.get("vaccination_rollout_per_day", live_count)))
            already_vaccinated = sum(1 for cow in cows if cow.get("alive", True) and cow.get("vaccinated", False))
            for cow in cows:
                if vaccinated_today >= min(daily_capacity, max(0, target_count - already_vaccinated)):
                    break
                if cow.get("alive", True) and not cow.get("vaccinated", False):
                    cow["vaccinated"] = True
                    vaccinated_today += 1
        inherited_resistance_effectiveness = require_fraction(
            "disease.inherited_resistance_effectiveness_fraction",
            float(value(self.ctx.calibration, "disease.inherited_resistance_effectiveness_fraction")),
        )
        stress_multiplier = require_nonnegative(
            "disease.stress_susceptibility_multiplier",
            float(value(self.ctx.calibration, "disease.stress_susceptibility_multiplier")),
        )

        sensor_payload = sensor_packet.payload if sensor_packet is not None else {}
        thi = sensor_payload.get("thi")
        heat_stress_active = isinstance(thi, (int, float)) and thi >= float(
            value(self.ctx.calibration, "cow.mild_heat_stress_thi")
        )
        sara_risk_by_cow = sensor_payload.get("sara_risk_by_cow", {})
        if not isinstance(sara_risk_by_cow, dict):
            sara_risk_by_cow = {}

        new_cases = outbreak_seeded
        recovered = 0
        deaths = 0
        for cow in cows:
            if not cow.get("alive", True):
                continue
            if cow.get("infection_state") == "I":
                cow["days_infected"] = int(cow.get("days_infected", 0)) + 1
                if self.ctx.rng.random() < mortality_probability:
                    cow["alive"] = False
                    cow["quarantine_flag"] = False
                    deaths += 1
                elif self.ctx.rng.random() < recovery_probability:
                    cow["infection_state"] = "R"
                    cow["health_status"] = "healthy"
                    cow["disease"] = None
                    cow["quarantine_flag"] = False
                    recovered += 1
                continue
            if cow.get("infection_state") != "S":
                continue
            cow_stress = heat_stress_active or bool(sara_risk_by_cow.get(cow["id"], False))
            cow_vaccinated = bool(cow.get("vaccinated", False))
            health_trait = 1.0
            trait_vector = cow.get("trait_vector")
            if isinstance(trait_vector, dict):
                health_trait = float(trait_vector.get("health", 1.0))
            resistance_modifier = 1.0
            if cow_vaccinated:
                resistance_modifier *= 1.0 - vaccination_effectiveness
            if health_trait > 1.0:
                resistance_modifier *= 1.0 - (health_trait - 1.0) * inherited_resistance_effectiveness
            infection_probability = (
                min(1.0, mastitis_probability + lameness_probability + transmission_pressure)
                * (stress_multiplier if cow_stress else 1.0)
                * max(0.0, resistance_modifier)
            )
            if self.ctx.rng.random() < infection_probability:
                cow["infection_state"] = "I"
                cow["health_status"] = "sick"
                cow["disease"] = "mastitis" if self.ctx.rng.random() < mastitis_probability else "lameness"
                cow["days_infected"] = 0
                cow["quarantine_flag"] = quarantine_enabled
                new_cases += 1

        susceptible_count = sum(
            1 for cow in cows if cow.get("alive", True) and cow.get("infection_state") == "S"
        )
        infected_count = sum(
            1 for cow in cows if cow.get("alive", True) and cow.get("infection_state") == "I"
        )
        recovered_count = sum(
            1 for cow in cows if cow.get("alive", True) and cow.get("infection_state") == "R"
        )
        quarantined_count = sum(
            1 for cow in cows if cow.get("alive", True) and cow.get("quarantine_flag", False)
        )
        immunity_status = "full" if live_count and recovered_count == live_count else "partial" if recovered_count else "none"
        treatment_cost = new_cases * float(value(self.ctx.calibration, "disease.treatment_cost_per_case"))
        milk_loss_cost = infected_count * float(value(self.ctx.calibration, "disease.milk_loss_sick_fraction")) * float(self.ctx.scenario.get("disease_milk_loss_value_per_cow_day", 0.0))
        quarantine_cost = quarantined_count * float(self.ctx.scenario.get("quarantine_cost_per_cow_day", 0.0))
        mortality_cost = deaths * float(self.ctx.scenario.get("disease_mortality_cost_per_cow", 0.0))
        outbreak_state = self.ctx.state["outbreak_state"]
        if infected_count and not outbreak_state["active"]:
            outbreak_state.update({"active": True, "start_day": day.isoformat(), "end_day": None})
        if outbreak_state["active"] and not infected_count:
            outbreak_state.update({"active": False, "end_day": day.isoformat()})
        outbreak_day_cost = treatment_cost + milk_loss_cost + quarantine_cost + mortality_cost
        outbreak_state["cumulative_economic_cost"] = float(outbreak_state["cumulative_economic_cost"]) + outbreak_day_cost
        vaccination_coverage = sum(1 for cow in cows if cow.get("alive", True) and cow.get("vaccinated", False)) / live_count if live_count else 0.0
        if immunity_status == "full" and outbreak_state.get("herd_immunity_day") is None:
            outbreak_state["herd_immunity_day"] = day.isoformat()
        start_text = outbreak_state.get("start_day")
        start_date = date.fromisoformat(start_text) if start_text else None
        duration_days = (day - start_date).days + 1 if outbreak_state["active"] and start_date else 0
        immunity_text = outbreak_state.get("herd_immunity_day")
        immunity_date = date.fromisoformat(immunity_text) if immunity_text else None
        days_to_herd_immunity = (immunity_date - start_date).days + 1 if immunity_date and start_date else None
        per_cow_penalties = {
            str(cow["id"]): {
                "milk_yield_penalty_fraction": float(value(self.ctx.calibration, "disease.milk_loss_sick_fraction")) if cow.get("infection_state") == "I" else 0.0,
                "mortality_signal": bool(not cow.get("alive", True)),
            }
            for cow in cows
        }
        report = {
            "new_cases": new_cases,
            "recovered": recovered,
            "deaths": deaths,
            "active_cases": infected_count,
            "susceptible_count": susceptible_count,
            "infected_count": infected_count,
            "recovered_count": recovered_count,
            "quarantined_count": quarantined_count,
            "herd_immunity_status": immunity_status,
            "outbreak_seeded_count": outbreak_seeded,
            "sensor_alert_count": len(sensor_alerts),
            "transmission_pressure": transmission_pressure,
            "herd_density_modifier": herd_density_modifier,
            "vaccination_effectiveness_applied": vaccination_effectiveness,
            "inherited_resistance_effectiveness": inherited_resistance_effectiveness,
            "stress_susceptibility_multiplier": stress_multiplier,
            "milk_loss_sick_fraction": float(value(self.ctx.calibration, "disease.milk_loss_sick_fraction")),
            "treatment_cost": treatment_cost,
            "milk_loss_cost": milk_loss_cost,
            "quarantine_cost": quarantine_cost,
            "mortality_cost": mortality_cost,
            "outbreak_economic_cost": outbreak_day_cost,
            "outbreak_active_flag": bool(outbreak_state["active"]),
            "outbreak_start_day": outbreak_state["start_day"],
            "outbreak_end_day": outbreak_state["end_day"],
            "outbreak_duration_days": duration_days,
            "vaccination_coverage": vaccination_coverage,
            "vaccinated_today": vaccinated_today,
            "vaccination_target_coverage": float(self.ctx.scenario.get("vaccination_target_coverage", 1.0)),
            "days_to_herd_immunity": days_to_herd_immunity,
            "cumulative_outbreak_economic_cost": outbreak_state["cumulative_economic_cost"],
            "per_cow_health_signal": per_cow_penalties,
            "disease_frequency_signal": infected_count,
        }
        self.ctx.state["disease_history"].append({"day": day.isoformat(), **report})
        self.ctx.publish(Packet(source=self.name, name="disease_state_packet", day=day, payload=report))
        self.ctx.state.setdefault("execution_order", []).append(self.name)
