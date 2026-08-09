from __future__ import annotations

from datetime import date
from math import exp, pow
from typing import Any

from dairy_abm.config import value
from dairy_abm.core import BaseAgent, Packet, require_fraction, require_nonnegative


class CowAgent(BaseAgent):
    name = "cow"

    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        ctx.state.setdefault("cows", self._build_initial_herd())

    def _build_initial_herd(self) -> list[dict[str, Any]]:
        herd = self.ctx.scenario.get("herd")
        if isinstance(herd, list):
            return [self._normalize_cow(cow, index) for index, cow in enumerate(herd)]
        herd_size = int(self.ctx.scenario.get("herd_size", 100))
        return [
            self._normalize_cow({"id": f"cow-{index + 1}"}, index)
            for index in range(herd_size)
        ]

    def _normalize_cow(self, cow: dict[str, Any], index: int) -> dict[str, Any]:
        normalized = dict(cow)
        milk_trait = float(normalized.get("milk_trait", 1.0))
        feed_efficiency_trait = float(normalized.get("feed_efficiency_trait", 1.0))
        normalized.setdefault("id", f"cow-{index + 1}")
        normalized.setdefault("health_status", "healthy")
        normalized.setdefault("disease", None)
        normalized["milk_trait"] = milk_trait
        normalized["feed_efficiency_trait"] = feed_efficiency_trait
        normalized.setdefault(
            "inherited_traits",
            {"milk": milk_trait, "feed_efficiency": feed_efficiency_trait},
        )
        normalized.setdefault(
            "trait_vector",
            {
                "milk_yield": milk_trait,
                "feed_efficiency": 1.0 / feed_efficiency_trait if feed_efficiency_trait > 0.0 else 0.0,
                "butterfat_ebv": float(normalized.get("butterfat_ebv", 1.0)),
                "protein_ebv": float(normalized.get("protein_ebv", 1.0)),
                "rfi_fat_ebv": float(normalized.get("rfi_fat_ebv", 0.0)),
                "body_weight_composite": float(normalized.get("body_weight_composite", 1.0)),
                "livability_score": float(normalized.get("livability_score", normalized.get("survivability_trait", 1.0))),
                "fertility_score": float(normalized.get("fertility_score", normalized.get("fertility_trait", 1.0))),
                "health_composite_score": float(normalized.get("health_composite_score", normalized.get("health_trait", 1.0))),
                "calving_ease_score": float(normalized.get("calving_ease_score", 1.0)),
                "fertility": float(normalized.get("fertility_trait", 1.0)),
                "health": float(normalized.get("health_trait", 1.0)),
                "survivability": float(normalized.get("survivability_trait", 1.0)),
            },
        )
        normalized.setdefault("alive", True)
        normalized.setdefault("sex", "female")
        normalized.setdefault(
            "age_days", int(value(self.ctx.calibration, "cow.initial_age_days"))
        )
        normalized.setdefault(
            "days_in_milk", int(value(self.ctx.calibration, "cow.initial_days_in_milk"))
        )
        normalized.setdefault("parity", int(value(self.ctx.calibration, "cow.initial_parity")))
        normalized.setdefault(
            "body_weight_kg", float(value(self.ctx.calibration, "cow.initial_body_weight_kg"))
        )
        normalized.setdefault(
            "body_condition_score",
            float(value(self.ctx.calibration, "cow.initial_body_condition_score")),
        )
        normalized.setdefault("pregnant", False)
        normalized.setdefault("days_pregnant", 0)
        normalized.setdefault("rumen_ph", None)
        normalized.setdefault("sara_ticks", 0)
        normalized.setdefault(
            "genome_markers",
            {
                trait: float(normalized["trait_vector"].get(trait, 0.0))
                for trait in ("butterfat_ebv", "protein_ebv", "rfi_fat_ebv", "fertility_score", "health_composite_score")
            },
        )
        normalized.setdefault("calving_interval_days", 0)
        normalized.setdefault("reproduction_history", [])
        normalized.setdefault("dmi_history", [])
        normalized.setdefault("milk_history", [])
        normalized.setdefault("ch4_history", [])
        normalized.setdefault("manure_history", [])
        normalized.setdefault("health_history", [])
        normalized.setdefault("body_weight_history", [])
        normalized.setdefault("bcs_history", [])
        return normalized

    @staticmethod
    def _expected_dmi(cow: dict[str, Any], milk_e_mcal: float) -> float:
        parity = 0.0 if int(cow.get("parity", 1)) <= 1 else 1.0
        body_weight = float(cow.get("body_weight_kg", 650.0))
        bcs = float(cow.get("body_condition_score", 3.0))
        dim = max(1.0, float(cow.get("days_in_milk", 1)))
        expected = (
            3.7 + 5.7 * parity + 0.305 * milk_e_mcal + 0.022 * body_weight
            + (-0.689 - 1.87 * parity) * bcs
        ) * (1.0 - (0.212 + 0.136 * parity) * exp(-0.053 * dim))
        return max(0.0, expected)

    @staticmethod
    def _milk_energy_mcal(milk_l: float, traits: dict[str, Any]) -> float:
        """Calculate MilkE from milk mass and configurable component proxies."""
        density = float(traits.get("milk_density_kg_per_l", 1.03))
        fat = max(0.0, 0.039 * float(traits.get("butterfat_ebv", 1.0)))
        protein = max(0.0, 0.032 * float(traits.get("protein_ebv", 1.0)))
        lactose = float(traits.get("lactose_fraction", 0.048))
        milk_kg = max(0.0, milk_l * density)
        return milk_kg * (0.0929 * fat * 100.0 + 0.0547 * protein * 100.0 + 0.0395 * lactose * 100.0)

    @staticmethod
    def _lactation_factor(days_in_milk: int, peak_days: float = 60.0) -> float:
        """A normalized Wood-style curve keeps production tied to lactation stage."""
        dim = max(1.0, float(days_in_milk))
        peak = max(1.0, peak_days)
        return max(0.25, (dim / peak) ** 0.2 * exp(0.2 * (1.0 - dim / peak)))

    def tick(self, day: date) -> None:
        cows = self.ctx.state.get("cows", [])
        disease_packet = self.ctx.get_packet("disease_state_packet")
        market_packet = self.ctx.get_packet("market_price_packet")
        prior_ration = self.ctx.get_packet("feed_crop_packet")
        water_delivery = self.ctx.get_packet("water_delivery_packet")
        sensor_packet = self.ctx.get_packet("sensor_observation_packet")
        grazing_packet = self.ctx.get_packet("grazing_access_packet")
        ration_coverage_fraction = (
            float(prior_ration.payload["ration_coverage_fraction"])
            if prior_ration is not None
            else 1.0
        )
        ration_coverage_fraction = min(1.0, max(0.0, ration_coverage_fraction))
        ration_shortfall_milk_loss = require_fraction(
            "cow.ration_shortfall_milk_loss_fraction",
            float(value(self.ctx.calibration, "cow.ration_shortfall_milk_loss_fraction")),
        )
        sensor_payload = sensor_packet.payload if sensor_packet is not None else {}
        prior_ration_nitrogen = (
            float(prior_ration.payload.get("ration_nitrogen_kg", 0.0))
            if prior_ration is not None
            else 0.0
        )
        thi = sensor_payload.get("thi")
        rumen_ph_by_cow = sensor_payload.get("rumen_ph_by_cow", {})
        observed_dmi_by_cow = sensor_payload.get("observed_dmi_kg_by_cow", {})
        estrus_by_cow = sensor_payload.get("estrus_by_cow", {})
        if not isinstance(rumen_ph_by_cow, dict):
            rumen_ph_by_cow = {}
        if not isinstance(observed_dmi_by_cow, dict):
            observed_dmi_by_cow = {}
        if not isinstance(estrus_by_cow, dict):
            estrus_by_cow = {}
        per_cow_rations = prior_ration.payload.get("per_cow_rations", {}) if prior_ration else {}
        if not isinstance(per_cow_rations, dict):
            per_cow_rations = {}
        water_availability = float(water_delivery.payload.get("water_availability_fraction", 1.0)) if water_delivery else 1.0
        water_availability = min(1.0, max(0.0, water_availability))

        base_milk = float(value(self.ctx.calibration, "cow.base_milk_l_per_cow_day"))
        base_dmi = float(value(self.ctx.calibration, "cow.base_dmi_kg_per_cow_day"))
        base_manure = float(value(self.ctx.calibration, "cow.base_manure_kg_per_cow_day"))
        base_enteric = float(value(self.ctx.calibration, "cow.enteric_ch4_kg_per_cow_day"))
        ch4_me_reference = float(value(self.ctx.calibration, "cow.ch4_me_reference_constant"))
        sick_loss = (
            float(disease_packet.payload["milk_loss_sick_fraction"])
            if disease_packet is not None
            else float(value(self.ctx.calibration, "disease.milk_loss_sick_fraction"))
        )
        per_cow_health_signal = disease_packet.payload.get("per_cow_health_signal", {}) if disease_packet else {}
        milk_l = 0.0
        dmi_kg = 0.0
        manure_kg = 0.0
        enteric_ch4_kg = 0.0
        sick_cows = 0
        sara_affected_cows = 0
        conceptions = 0
        deaths = 0
        newborns: list[dict[str, Any]] = []
        active_cows: list[dict[str, Any]] = []
        total_days_in_milk = 0.0
        total_body_condition_score = 0.0
        cow_records: list[dict[str, Any]] = []
        heat_stress_active = isinstance(thi, (int, float)) and thi >= float(
            value(self.ctx.calibration, "cow.mild_heat_stress_thi")
        )
        severe_heat_stress = isinstance(thi, (int, float)) and thi > float(
            value(self.ctx.calibration, "cow.severe_heat_stress_thi")
        )
        heat_dmi_loss = 0.0
        heat_milk_loss = 0.0
        if severe_heat_stress:
            heat_dmi_loss = require_fraction(
                "cow.severe_heat_stress_dmi_loss_fraction",
                float(value(self.ctx.calibration, "cow.severe_heat_stress_dmi_loss_fraction")),
            )
            heat_milk_loss = require_fraction(
                "cow.severe_heat_stress_milk_loss_fraction",
                float(value(self.ctx.calibration, "cow.severe_heat_stress_milk_loss_fraction")),
            )
        elif heat_stress_active:
            heat_dmi_loss = require_fraction(
                "cow.mild_heat_stress_dmi_loss_fraction",
                float(value(self.ctx.calibration, "cow.mild_heat_stress_dmi_loss_fraction")),
            )
            heat_milk_loss = require_fraction(
                "cow.mild_heat_stress_milk_loss_fraction",
                float(value(self.ctx.calibration, "cow.mild_heat_stress_milk_loss_fraction")),
            )
        sara_ph_threshold = float(value(self.ctx.calibration, "cow.sara_rumen_ph_threshold"))
        sara_required_ticks = int(value(self.ctx.calibration, "cow.sara_consecutive_ticks"))
        sara_dmi_loss = require_fraction(
            "cow.sara_dmi_loss_fraction", float(value(self.ctx.calibration, "cow.sara_dmi_loss_fraction"))
        )
        sara_milk_loss = require_fraction(
            "cow.sara_milk_loss_fraction", float(value(self.ctx.calibration, "cow.sara_milk_loss_fraction"))
        )
        pregnancy_rate_monthly = require_fraction(
            "cow.pregnancy_rate_monthly", float(value(self.ctx.calibration, "cow.pregnancy_rate_monthly"))
        )
        pregnancy_rate_daily = 1.0 - pow(1.0 - pregnancy_rate_monthly, 1.0 / 30.0)
        mortality_rate_annual = require_fraction(
            "cow.mortality_rate_annual", float(value(self.ctx.calibration, "cow.mortality_rate_annual"))
        )
        mortality_rate_daily = 1.0 - pow(1.0 - mortality_rate_annual, 1.0 / 365.0)
        reproduction_eligibility_days = int(
            value(self.ctx.calibration, "cow.reproduction_eligibility_days_in_milk")
        )

        for cow in cows:
            if not cow.get("alive", True):
                continue
            cow["reproduction_event_flag"] = None
            if str(cow.get("sex", "female")) != "female" or int(cow.get("days_in_milk", 0)) <= 0:
                cow["age_days"] = int(cow.get("age_days", 0)) + 1
                maturity_days = int(
                    self.ctx.scenario.get(
                        "replacement_maturity_days",
                        value(self.ctx.calibration, "cow.replacement_maturity_days"),
                    )
                )
                if (
                    str(cow.get("sex", "female")) == "female"
                    and int(cow.get("parity", 0)) == 0
                    and int(cow["age_days"]) >= maturity_days
                ):
                    cow["parity"] = 1
                    cow["days_in_milk"] = 1
                    cow["calving_interval_days"] = 0
                    cow["reproduction_event_flag"] = "first_calving"
                    cow["reproduction_history"].append({"day": day.isoformat(), "event": "first_calving"})
                continue
            rumen_ph = rumen_ph_by_cow.get(cow["id"])
            if isinstance(rumen_ph, (int, float)):
                cow["rumen_ph"] = float(rumen_ph)
                cow["sara_ticks"] = (
                    int(cow["sara_ticks"]) + 1 if rumen_ph < sara_ph_threshold else 0
                )
            sara_active = int(cow["sara_ticks"]) >= sara_required_ticks
            if sara_active:
                sara_affected_cows += 1
            milk_modifier = float(cow.get("milk_trait", 1.0))
            efficiency_modifier = float(cow.get("feed_efficiency_trait", 1.0))
            trait_vector = cow.get("trait_vector", {})
            rfi_fat = float(trait_vector.get("rfi_fat_ebv", 0.0)) if isinstance(trait_vector, dict) else 0.0
            ration = per_cow_rations.get(str(cow["id"]), {})
            cow_ration_coverage = min(1.0, max(0.0, float(ration.get("coverage_fraction", ration_coverage_fraction))))
            ration_me = float(ration.get("me_mj_per_kg_dm", prior_ration.payload.get("ration_me_mj_per_kg_dm", 10.0) if prior_ration else 10.0))
            milk_e_mcal = self._milk_energy_mcal(float(cow.get("last_milk_l", base_milk)), trait_vector if isinstance(trait_vector, dict) else {})
            expected_dmi = self._expected_dmi(cow, milk_e_mcal)
            cow["expected_dmi_kg"] = expected_dmi
            dmi_cv = min(0.22, max(0.11, float(self.ctx.scenario.get("dmi_stochastic_cv", 0.15))))
            actual_dmi = max(0.0, expected_dmi + rfi_fat + self.ctx.rng.gauss(0.0, dmi_cv * expected_dmi))
            if cow.get("health_status") != "healthy":
                health_signal = per_cow_health_signal.get(str(cow["id"]), {}) if isinstance(per_cow_health_signal, dict) else {}
                milk_modifier *= 1.0 - float(health_signal.get("milk_yield_penalty_fraction", sick_loss))
                sick_cows += 1
            cow_milk_l = (
                base_milk
                * milk_modifier
                * self._lactation_factor(
                    int(cow["days_in_milk"]),
                    float(
                        self.ctx.scenario.get(
                            "lactation_peak_days", value(self.ctx.calibration, "cow.lactation_peak_days")
                        )
                    ),
                )
                * (1.0 - heat_milk_loss)
                * (1.0 - (1.0 - cow_ration_coverage) * ration_shortfall_milk_loss)
                * water_availability
            )
            cow_dmi_kg = actual_dmi * efficiency_modifier * (1.0 - heat_dmi_loss) * cow_ration_coverage * water_availability
            if sara_active:
                cow_milk_l *= 1.0 - sara_milk_loss
                cow_dmi_kg *= 1.0 - sara_dmi_loss
            milk_l += cow_milk_l
            dmi_kg += cow_dmi_kg
            cow["last_dmi_kg"] = cow_dmi_kg
            cow_manure_kg = base_manure * (cow_dmi_kg / max(base_dmi, 0.001))
            cow_ch4_kg = base_enteric * (cow_dmi_kg / max(base_dmi, 0.001)) * (ch4_me_reference / max(1.0, ration_me))
            manure_kg += cow_manure_kg
            enteric_ch4_kg += cow_ch4_kg
            cow["last_milk_l"] = cow_milk_l
            energy_balance_fraction = cow_dmi_kg / max(expected_dmi, 0.001) - 1.0
            cow["body_weight_kg"] = max(
                300.0,
                float(cow["body_weight_kg"]) + max(-1.0, min(1.0, energy_balance_fraction * 0.8)),
            )
            cow["body_condition_score"] = min(
                5.0,
                max(1.0, float(cow["body_condition_score"]) + max(-0.02, min(0.02, energy_balance_fraction * 0.02))),
            )
            cow["dmi_history"].append(cow_dmi_kg)
            cow["milk_history"].append(cow_milk_l)
            cow["ch4_history"].append(cow_ch4_kg)
            cow["manure_history"].append(cow_manure_kg)
            cow["health_history"].append(cow.get("health_status", "healthy"))
            cow["body_weight_history"].append(float(cow["body_weight_kg"]))
            cow["bcs_history"].append(float(cow["body_condition_score"]))
            total_days_in_milk += float(cow["days_in_milk"])
            total_body_condition_score += float(cow["body_condition_score"])
            cow_records.append(
                {
                    "id": cow["id"],
                    "milk_l": cow_milk_l,
                    "dmi_kg": cow_dmi_kg,
                    "days_in_milk": cow["days_in_milk"],
                    "parity": cow["parity"],
                    "health_status": cow["health_status"],
                    "rumen_ph": cow["rumen_ph"],
                    "observed_dmi_kg": observed_dmi_by_cow.get(cow["id"]),
                    "actual_dmi_kg_dm": cow_dmi_kg,
                    "expected_dmi_eq2_1_kg_dm": expected_dmi,
                    "milk_e_mcal": milk_e_mcal,
                    "estrus_detected": bool(estrus_by_cow.get(cow["id"], False)),
                    "sara_active": sara_active,
                }
            )
            active_cows.append(cow)

        for cow in active_cows:
            if cow["pregnant"]:
                cow["days_pregnant"] = int(cow["days_pregnant"]) + 1
                if int(cow["days_pregnant"]) >= int(self.ctx.scenario.get("gestation_days", 280)):
                    cow["pregnant"] = False
                    cow["days_pregnant"] = 0
                    cow["days_in_milk"] = 0
                    cow["parity"] = int(cow["parity"]) + 1
                    cow["calving_interval_days"] = 0
                    cow["reproduction_history"].append({"day": day.isoformat(), "event": "calving"})
                    cow["reproduction_event_flag"] = "calving"
                    dam_traits = cow.get("trait_vector", {})
                    newborns.append(
                        self._normalize_cow(
                            {
                                "id": f"calf-{cow['id']}-{day.isoformat()}",
                                "age_days": 0,
                                "days_in_milk": 0,
                                "parity": 0,
                                "body_weight_kg": 40.0,
                                "sex": "female" if self.ctx.rng.random() < 0.5 else "male",
                                "trait_vector": dict(dam_traits) if isinstance(dam_traits, dict) else {},
                                "parent_ids": [cow["id"]],
                            },
                            len(cows) + len(newborns),
                        )
                    )
            elif int(cow["days_in_milk"]) >= reproduction_eligibility_days:
                estrus_detected = bool(estrus_by_cow.get(cow["id"], False))
                estrus_required = bool(self.ctx.scenario.get("estrus_required_for_conception", True))
                sensor_reliability = float(sensor_payload.get("estrus_reliability", 1.0))
                conception_probability = pregnancy_rate_daily * float(cow.get("trait_vector", {}).get("fertility_score", 1.0)) * sensor_reliability
                if (not estrus_required or estrus_detected) and self.ctx.rng.random() < min(1.0, conception_probability):
                    cow["pregnant"] = True
                    cow["days_pregnant"] = 0
                    cow["reproduction_history"].append({"day": day.isoformat(), "event": "conception"})
                    cow["reproduction_event_flag"] = "conception"
                    conceptions += 1
            cow["age_days"] = int(cow["age_days"]) + 1
            cow["days_in_milk"] = int(cow["days_in_milk"]) + 1
            cow["calving_interval_days"] = int(cow.get("calving_interval_days", 0)) + 1
            if self.ctx.rng.random() < mortality_rate_daily:
                cow["alive"] = False
                deaths += 1

        if newborns:
            self.ctx.state["cows"].extend(newborns)

        active_cow_count = len(active_cows)
        pregnant_cows = sum(1 for cow in active_cows if cow["pregnant"])
        feed_conversion_ratio = dmi_kg / milk_l if milk_l > 0.0 else 0.0
        enteric_ch4_intensity = enteric_ch4_kg / milk_l if milk_l > 0.0 else 0.0
        milk_protein_nitrogen = (
            milk_l
            * float(value(self.ctx.calibration, "cow.milk_protein_fraction"))
            * float(value(self.ctx.calibration, "feed_crop.nitrogen_fraction_of_crude_protein"))
        )
        nitrogen_use_efficiency = (
            milk_protein_nitrogen / prior_ration_nitrogen if prior_ration_nitrogen > 0.0 else None
        )

        grazing_intake_kg = 0.0
        if grazing_packet is not None and bool(grazing_packet.payload.get("enabled", False)):
            pasture_ha = float(grazing_packet.payload.get("pasture_available_ha", 0.0))
            seasonal_frac = float(grazing_packet.payload.get("seasonal_availability_fraction", 1.0))
            total_grazing_available = (
                pasture_ha
                * seasonal_frac
                * float(value(self.ctx.calibration, "cow.grazing_intake_kg_dm_per_ha_day"))
            )
            grazing_intake_kg = min(total_grazing_available, dmi_kg)

        milk_price = (
            float(market_packet.payload["milk_price_per_l"])
            if market_packet is not None
            else float(value(self.ctx.calibration, "market.milk_price_per_l"))
        )
        milk_revenue = milk_l * milk_price
        packet = Packet(
            source=self.name,
            name="cow_daily_packet",
            day=day,
            payload={
                "cow_count": active_cow_count,
                "healthy_cows": active_cow_count - sick_cows,
                "sick_cows": sick_cows,
                "milk_l": require_nonnegative("milk_l", milk_l),
                "daily_milk_yield_l": require_nonnegative("daily_milk_yield_l", milk_l),
                "dmi_kg": require_nonnegative("dmi_kg", dmi_kg),
                "actual_dmi_kg_dm": require_nonnegative("actual_dmi_kg_dm", dmi_kg),
                "manure_kg": require_nonnegative("manure_kg", manure_kg),
                "enteric_ch4_kg": require_nonnegative("enteric_ch4_kg", enteric_ch4_kg),
                "milk_revenue": require_nonnegative("milk_revenue", milk_revenue),
                "ration_coverage_fraction": ration_coverage_fraction,
                "thi": float(thi) if isinstance(thi, (int, float)) else None,
                "heat_stress_active": heat_stress_active,
                "sara_affected_cows": sara_affected_cows,
                "pregnant_cows": pregnant_cows,
                "conceptions": conceptions,
                "deaths": deaths,
                "mean_days_in_milk": total_days_in_milk / active_cow_count if active_cow_count else 0.0,
                "mean_body_condition_score": (
                    total_body_condition_score / active_cow_count if active_cow_count else 0.0
                ),
                "feed_conversion_ratio_kg_dm_per_l": feed_conversion_ratio,
                "enteric_ch4_intensity_kg_per_l": enteric_ch4_intensity,
                "milk_protein_nitrogen_kg": milk_protein_nitrogen,
                "nitrogen_use_efficiency": nitrogen_use_efficiency,
                "grazing_intake_kg": grazing_intake_kg,
                "grazing_enabled": bool(grazing_packet.payload.get("enabled", False)) if grazing_packet else False,
                "water_availability_fraction": water_availability,
                "health_mortality_signal": {"deaths": deaths, "sick_cows": sick_cows},
                "reproduction_event_count": sum(1 for cow in active_cows if cow.get("reproduction_event_flag")),
                "cow_records": cow_records,
            },
        )
        self.ctx.publish(packet)
        self.ctx.state.setdefault("execution_order", []).append(self.name)
