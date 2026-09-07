from __future__ import annotations

from datetime import date

from dairy_abm.config import value
from dairy_abm.core import BaseAgent, Packet, require_fraction, require_nonnegative


class WaterAgent(BaseAgent):
    name = "water"

    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        ctx.state.setdefault("wastewater_storage_l", 0.0)
        ctx.state.setdefault("water_history", [])

    def prepare_delivery(self, day: date) -> None:
        """Make the current-day drinking-water constraint available to Cow."""
        cows = [cow for cow in self.ctx.state.get("cows", []) if cow.get("alive", True)]
        requested = len(cows) * float(value(self.ctx.calibration, "water.drinking_l_per_cow_day"))
        source_capacity = float(self.ctx.scenario.get("freshwater_supply_l_per_day", requested))
        availability_fraction = min(1.0, source_capacity / requested) if requested > 0.0 else 1.0
        availability_fraction *= float(self.ctx.scenario.get("water_delivery_fraction", 1.0))
        availability_fraction = max(0.0, min(1.0, availability_fraction))
        self.ctx.publish(
            Packet(
                source=self.name,
                name="water_delivery_packet",
                day=day,
                payload={
                    "drinking_water_requested_l": requested,
                    "drinking_water_delivered_l": requested * availability_fraction,
                    "water_availability_fraction": availability_fraction,
                    "quality_flag": "ok" if availability_fraction >= 1.0 else "constrained",
                    "source_capacity_l": source_capacity,
                },
                quality="ok" if availability_fraction >= 1.0 else "partial",
            )
        )
        self.ctx.state.setdefault("execution_order", []).append("water_delivery")

    def tick(self, day: date) -> None:
        cow_packet = self.ctx.get_packet("cow_daily_packet")
        feed_packet = self.ctx.get_packet("feed_crop_packet")
        cow_count = int(cow_packet.payload["cow_count"]) if cow_packet is not None else 0
        milk_l = float(cow_packet.payload["milk_l"]) if cow_packet is not None else 0.0
        drinking_l = cow_count * float(value(self.ctx.calibration, "water.drinking_l_per_cow_day"))
        parlor_l = cow_count * float(value(self.ctx.calibration, "water.parlor_l_per_cow_day"))
        irrigation_l = float(feed_packet.payload["irrigation_l"]) if feed_packet is not None else 0.0
        irrigation_demand_l = (
            float(feed_packet.payload.get("irrigation_demand_l", irrigation_l))
            if feed_packet is not None
            else 0.0
        )
        amino_acid_policy_active = bool(
            feed_packet is not None
            and feed_packet.payload.get("amino_acid_balancing_active", False)
            and float(feed_packet.payload.get("amino_acid_cp_reduction_points", 0.0)) > 0.0
        )
        amino_acid_adjustment_l = (
            cow_count * float(value(self.ctx.calibration, "water.water_saving_l_per_cow_day"))
            if amino_acid_policy_active
            else 0.0
        )
        gross_l = drinking_l + parlor_l + irrigation_l
        total_water_use_l = max(0.0, gross_l - amino_acid_adjustment_l)
        wastewater_l = parlor_l * require_fraction(
            "water.wastewater_return_fraction",
            float(value(self.ctx.calibration, "water.wastewater_return_fraction")),
        )
        l2_enabled = bool(
            self.ctx.scenario.get("l2_water_loop_enabled", value(self.ctx.calibration, "water.l2_water_loop_enabled"))
        )
        treatment_configured = bool(
            self.ctx.scenario.get("water_treatment_active", value(self.ctx.calibration, "water.treatment_active"))
        )
        treatment_active = treatment_configured and (
            l2_enabled or bool(self.ctx.scenario.get("water_treatment_independent_of_l2", False))
        )
        opening_wastewater_storage_l = require_nonnegative(
            "wastewater_storage_l", float(self.ctx.state["wastewater_storage_l"])
        )
        wastewater_available_l = opening_wastewater_storage_l + wastewater_l
        treatment_capacity_l = max(0.0, float(self.ctx.scenario.get("water_treatment_capacity_l_per_day", wastewater_available_l)))
        treatment_input_l = min(wastewater_available_l, treatment_capacity_l)
        if treatment_active:
            treated_water_l = treatment_input_l * require_fraction(
                "water.treatment_recovery_fraction",
                float(value(self.ctx.calibration, "water.treatment_recovery_fraction")),
            )
            wastewater_storage_l = wastewater_available_l - treatment_input_l
        else:
            treated_water_l = 0.0
            wastewater_storage_l = wastewater_available_l
        self.ctx.state["wastewater_storage_l"] = wastewater_storage_l
        recycled_irrigation_l = min(treated_water_l, irrigation_demand_l)
        treated_water_surplus_l = treated_water_l - recycled_irrigation_l
        net_freshwater_use_l = max(0.0, total_water_use_l - recycled_irrigation_l)
        water_intensity = total_water_use_l / milk_l if milk_l > 0.0 else None

        if l2_enabled:
            credit = treated_water_l * require_nonnegative(
                "water.water_loop_fresh_water_offset_fraction",
                float(value(self.ctx.calibration, "water.water_loop_fresh_water_offset_fraction")),
            )
            self.ctx.state["loop_credits"]["water_offset_l"] += credit
            self.ctx.state["loop_credit_sources"]["l2_water_offset_l"] += credit
        nutrient_recovery_enabled = bool(value(self.ctx.calibration, "water.nutrient_recovery_enabled"))
        recovered_n_kg = (
            treated_water_l * require_nonnegative(
                "water.nutrient_recovery_kg_n_per_l",
                float(value(self.ctx.calibration, "water.nutrient_recovery_kg_n_per_l")),
            )
            if nutrient_recovery_enabled
            else 0.0
        )
        phosphorus_to_nitrogen = float(value(self.ctx.calibration, "manure.phosphorus_to_nitrogen_fraction"))
        potassium_to_nitrogen = float(value(self.ctx.calibration, "manure.potassium_to_nitrogen_fraction"))
        recovered_p_kg = recovered_n_kg * phosphorus_to_nitrogen
        recovered_k_kg = recovered_n_kg * potassium_to_nitrogen
        if nutrient_recovery_enabled:
            self.ctx.state["nutrient_credits"]["recovered_water_n_kg"] += recovered_n_kg
        payload = {
            "cow_count": cow_count,
            "drinking_l": require_nonnegative("drinking_l", drinking_l),
            "parlor_l": require_nonnegative("parlor_l", parlor_l),
            "cleaning_water_l": require_nonnegative("cleaning_water_l", parlor_l),
            "irrigation_l": require_nonnegative("irrigation_l", irrigation_l),
            "irrigation_demand_l": require_nonnegative("irrigation_demand_l", irrigation_demand_l),
            "gross_water_l": require_nonnegative("gross_water_l", gross_l),
            "total_water_use_l": require_nonnegative("total_water_use_l", total_water_use_l),
            "water_saving_l": require_nonnegative("water_saving_l", amino_acid_adjustment_l),
            "amino_acid_water_adjustment_l": require_nonnegative(
                "amino_acid_water_adjustment_l", amino_acid_adjustment_l
            ),
            "wastewater_volume_l": require_nonnegative("wastewater_volume_l", wastewater_l),
            "opening_wastewater_storage_l": opening_wastewater_storage_l,
            "wastewater_storage_l": wastewater_storage_l,
            "treatment_active": treatment_active,
            "treatment_capacity_l_per_day": treatment_capacity_l,
            "treatment_input_l": treatment_input_l,
            "treated_water_l": require_nonnegative("treated_water_l", treated_water_l),
            "recovered_n_kg": require_nonnegative("recovered_n_kg", recovered_n_kg),
            "recovered_p_kg": require_nonnegative("recovered_p_kg", recovered_p_kg),
            "recovered_k_kg": require_nonnegative("recovered_k_kg", recovered_k_kg),
            "recovered_water_l": require_nonnegative("recovered_water_l", treated_water_l),
            "recycled_irrigation_l": require_nonnegative("recycled_irrigation_l", recycled_irrigation_l),
            "treated_water_surplus_l": require_nonnegative("treated_water_surplus_l", treated_water_surplus_l),
            "water_use_l_per_litre_milk": water_intensity,
            "net_freshwater_use_l": require_nonnegative("net_freshwater_use_l", net_freshwater_use_l),
            "freshwater_withdrawal_l": require_nonnegative("freshwater_withdrawal_l", net_freshwater_use_l),
            "recycled_irrigation_fraction": recycled_irrigation_l / irrigation_demand_l if irrigation_demand_l > 0.0 else 0.0,
            "net_water_l": require_nonnegative("net_water_l", net_freshwater_use_l),
            "water_cost": require_nonnegative(
                "water_cost", net_freshwater_use_l * float(value(self.ctx.calibration, "water.water_cost_per_l"))
            ),
            "input_confidence": "estimated" if cow_packet is not None and feed_packet is not None else "low",
        }
        self.ctx.state["water_history"].append({"day": day.isoformat(), **payload})
        self.ctx.publish(Packet(source=self.name, name="water_packet", day=day, payload=payload))
        self.ctx.publish(
            Packet(
                source=self.name,
                name="water_environment_packet",
                day=day,
                payload={
                    "total_water_use_l": payload["total_water_use_l"],
                    "net_freshwater_use_l": payload["net_freshwater_use_l"],
                    "water_use_l_per_litre_milk": payload["water_use_l_per_litre_milk"],
                    "recycled_irrigation_l": payload["recycled_irrigation_l"],
                    "confidence": "estimated",
                },
                confidence="estimated",
            )
        )
        if nutrient_recovery_enabled:
            self.ctx.publish(
                Packet(
                    source=self.name,
                    name="water_nutrient_recovery_packet",
                    day=day,
                    payload={
                        "recovered_n_kg": recovered_n_kg,
                        "recovered_p_kg": recovered_p_kg,
                        "recovered_k_kg": recovered_k_kg,
                        "treated_water_l": treated_water_l,
                    },
                    confidence="low",
                )
            )
        self.ctx.state.setdefault("execution_order", []).append(self.name)
