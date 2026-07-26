from __future__ import annotations

from datetime import date

from dairy_abm.config import value
from dairy_abm.core import BaseAgent, ConfigError, Packet, require_fraction, require_nonnegative


class ManureAgent(BaseAgent):
    name = "manure"

    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        ctx.state.setdefault("stored_manure_inventory_kg", 0.0)
        ctx.state.setdefault("manure_flow_history", [])

    def _route_fractions(self) -> tuple[float, float, float]:
        policy_routes = self.ctx.state["policy"].get("manure_route_policy", {})
        if not isinstance(policy_routes, dict):
            policy_routes = {}
        digester = require_fraction(
            "manure.digester_route_fraction",
            float(policy_routes.get("digester", value(self.ctx.calibration, "manure.digester_route_fraction"))),
        )
        compost = require_fraction(
            "manure.compost_route_fraction",
            float(policy_routes.get("compost", value(self.ctx.calibration, "manure.compost_route_fraction"))),
        )
        storage = require_fraction(
            "manure.storage_route_fraction",
            float(policy_routes.get("storage", value(self.ctx.calibration, "manure.storage_route_fraction"))),
        )
        if abs(digester + compost + storage - 1.0) > 0.000001:
            raise ConfigError("manure route fractions must sum to 1.0")
        return digester, compost, storage

    def _cofeed_assembly(self, digester_kg: float) -> tuple[float, float, bool, str | None]:
        grass_available = max(0.0, float(self.ctx.scenario.get("grass_cofeed_kg", 0.0)))
        food_available = max(0.0, float(self.ctx.scenario.get("food_waste_cofeed_kg", 0.0)))
        cofeed_requested = grass_available > 0.0 or food_available > 0.0
        if cofeed_requested and not bool(self.ctx.state["policy"]["cofeed_safety_approved"]):
            return 0.0, 0.0, False, "cofeed_safety_rejected"
        if digester_kg <= 0.0:
            return 0.0, 0.0, False, None
        manure_fraction = float(value(self.ctx.calibration, "manure.digester_feedstock_manure_fraction"))
        grass_fraction = float(value(self.ctx.calibration, "manure.digester_feedstock_grass_fraction"))
        food_fraction = float(value(self.ctx.calibration, "manure.digester_feedstock_food_waste_fraction"))
        if abs(manure_fraction + grass_fraction + food_fraction - 1.0) > 0.000001:
            raise ConfigError("manure digester feedstock fractions must sum to 1.0")
        target_total = digester_kg / manure_fraction
        target_grass = target_total * grass_fraction
        target_food = target_total * food_fraction
        grass = min(grass_available, target_grass)
        food = min(food_available, target_food)
        feasible = grass == target_grass and food == target_food
        return grass, food, feasible, None

    def tick(self, day: date) -> None:
        cow_packet = self.ctx.get_packet("cow_daily_packet")
        feed_context = self.ctx.get_packet("feed_nitrogen_context_packet")
        processor_residual = self.ctx.get_packet("processor_residual_packet")
        manure_kg = require_nonnegative(
            "manure_kg", float(cow_packet.payload["manure_kg"]) if cow_packet is not None else 0.0
        )
        ration_crude_protein = (
            require_nonnegative("ration_crude_protein_kg", float(feed_context.payload["ration_crude_protein_kg"]))
            if feed_context is not None
            else 0.0
        )
        ration_metabolizable_protein = (
            require_nonnegative(
                "ration_metabolizable_protein_kg",
                float(feed_context.payload["ration_metabolizable_protein_kg"]),
            )
            if feed_context is not None
            else 0.0
        )
        ration_nitrogen = (
            require_nonnegative("ration_nitrogen_kg", float(feed_context.payload["ration_nitrogen_kg"]))
            if feed_context is not None
            else 0.0
        )
        collection_efficiency = require_fraction(
            "manure.collection_efficiency", float(value(self.ctx.calibration, "manure.collection_efficiency"))
        )
        collected_kg = manure_kg * collection_efficiency
        uncollected_kg = manure_kg - collected_kg
        digester_fraction, compost_fraction, storage_fraction = self._route_fractions()
        capacity_fraction = require_fraction(
            "scenario.digester_capacity_pct",
            float(self.ctx.scenario.get("digester_capacity_pct", 100.0)) / 100.0,
        )
        requested_digester_kg = collected_kg * digester_fraction
        capacity_limited_digester_kg = requested_digester_kg * capacity_fraction
        configured_capacity = self.ctx.state["policy"].get("digester_capacity_kg_day")
        if configured_capacity is not None:
            capacity_limited_digester_kg = min(capacity_limited_digester_kg, max(0.0, float(configured_capacity)))
        capacity_residual_kg = requested_digester_kg - capacity_limited_digester_kg
        thermochemical_active = bool(self.ctx.state["policy"]["thermochemical_route_active"])
        thermochemical_fraction = require_fraction(
            "manure.thermochemical_route_fraction",
            float(value(self.ctx.calibration, "manure.thermochemical_route_fraction")),
        )
        thermochemical_kg = capacity_limited_digester_kg * thermochemical_fraction if thermochemical_active else 0.0
        digester_kg = capacity_limited_digester_kg - thermochemical_kg
        compost_kg = collected_kg * compost_fraction
        storage_input_kg = collected_kg * storage_fraction + capacity_residual_kg

        release_fraction = require_fraction(
            "manure.storage_release_fraction", float(value(self.ctx.calibration, "manure.storage_release_fraction"))
        )
        opening_storage_kg = require_nonnegative(
            "stored_manure_inventory_kg", float(self.ctx.state["stored_manure_inventory_kg"])
        )
        released_storage_kg = opening_storage_kg * release_fraction
        storage_capacity_kg = require_nonnegative(
            "manure.storage_capacity_kg", float(value(self.ctx.calibration, "manure.storage_capacity_kg"))
        )
        storage_before_overflow = opening_storage_kg - released_storage_kg + storage_input_kg
        storage_overflow_kg = max(0.0, storage_before_overflow - storage_capacity_kg)
        stored_inventory_kg = storage_before_overflow - storage_overflow_kg
        self.ctx.state["stored_manure_inventory_kg"] = stored_inventory_kg

        nitrogen_fraction = require_fraction(
            "feed_crop.nitrogen_fraction_of_crude_protein",
            float(value(self.ctx.calibration, "feed_crop.nitrogen_fraction_of_crude_protein")),
        )
        excess_protein_kg = max(0.0, ration_crude_protein - ration_metabolizable_protein)
        urinary_n_kg = min(
            ration_nitrogen,
            excess_protein_kg
            * nitrogen_fraction
            * require_fraction(
                "manure.urinary_n_excess_fraction",
                float(value(self.ctx.calibration, "manure.urinary_n_excess_fraction")),
            ),
        )
        fecal_n_kg = ration_nitrogen - urinary_n_kg
        collected_n_kg = ration_nitrogen * collection_efficiency
        digestate_n_kg = (
            collected_n_kg
            * (digester_kg / collected_kg if collected_kg else 0.0)
            * require_fraction(
                "manure.digestate_n_retention_fraction",
                float(value(self.ctx.calibration, "manure.digestate_n_retention_fraction")),
            )
        )
        compost_n_kg = (
            collected_n_kg
            * (compost_kg / collected_kg if collected_kg else 0.0)
            * require_fraction(
                "manure.compost_n_retention_fraction",
                float(value(self.ctx.calibration, "manure.compost_n_retention_fraction")),
            )
        )
        phosphorus_to_nitrogen = require_nonnegative(
            "manure.phosphorus_to_nitrogen_fraction",
            float(value(self.ctx.calibration, "manure.phosphorus_to_nitrogen_fraction")),
        )
        potassium_to_nitrogen = require_nonnegative(
            "manure.potassium_to_nitrogen_fraction",
            float(value(self.ctx.calibration, "manure.potassium_to_nitrogen_fraction")),
        )
        digestate_p_kg = digestate_n_kg * phosphorus_to_nitrogen
        digestate_k_kg = digestate_n_kg * potassium_to_nitrogen
        compost_p_kg = compost_n_kg * phosphorus_to_nitrogen
        compost_k_kg = compost_n_kg * potassium_to_nitrogen
        field_n2o_precursor = urinary_n_kg * collection_efficiency

        volatile_solids = digester_kg * float(value(self.ctx.calibration, "manure.volatile_solids_fraction"))
        biogas_ch4_m3 = volatile_solids * float(
            value(self.ctx.calibration, "manure.biochemical_methane_potential_m3_per_kg_vs")
        )
        storage_ch4_kg = stored_inventory_kg * float(
            value(self.ctx.calibration, "manure.storage_ch4_kg_per_kg_manure")
        )
        unmanaged_ch4_kg = (uncollected_kg + storage_overflow_kg) * float(
            value(self.ctx.calibration, "manure.uncollected_ch4_kg_per_kg_manure")
        )
        compost_n2o_kg = compost_kg * float(value(self.ctx.calibration, "manure.compost_n2o_kg_per_kg_manure"))
        nutrient_return_kg = digestate_n_kg + compost_n_kg
        soil_organic_carbon_delta_kg = compost_kg * float(self.ctx.scenario.get("compost_soil_carbon_fraction", 0.12)) + digestate_n_kg * float(self.ctx.scenario.get("digestate_soil_carbon_kg_per_kg_n", 0.25))
        self.ctx.state["soil_organic_carbon"] = float(self.ctx.state.get("soil_organic_carbon", 0.0)) + soil_organic_carbon_delta_kg
        l1_enabled = bool(
            self.ctx.scenario.get("l1_nutrient_loop_enabled", value(self.ctx.calibration, "manure.l1_nutrient_loop_enabled"))
        )
        if l1_enabled:
            self.ctx.state["loop_credits"]["feed_offset_kg"] += compost_kg * float(
                value(self.ctx.calibration, "feed_crop.nutrient_loop_feed_substitution_fraction")
            )

        grass_cofeed_kg, food_waste_cofeed_kg, cofeed_feasible, route_alert = self._cofeed_assembly(digester_kg)
        processor_residual_energy_kg = (
            require_nonnegative(
                "processor_residual_energy_kg",
                float(processor_residual.payload.get("energy_feedstock_kg", 0.0)),
            )
            if processor_residual is not None
            else 0.0
        )
        digester_feedstock_kg = digester_kg + grass_cofeed_kg + food_waste_cofeed_kg + processor_residual_energy_kg
        payload = {
            "manure_kg": manure_kg,
            "collected_manure_kg": collected_kg,
            "uncollected_manure_kg": uncollected_kg,
            "digester_kg": digester_kg,
            "thermochemical_manure_kg": thermochemical_kg,
            "compost_kg": compost_kg,
            "storage_kg": storage_input_kg,
            "storage_input_kg": storage_input_kg,
            "opening_storage_inventory_kg": opening_storage_kg,
            "released_storage_kg": released_storage_kg,
            "stored_manure_inventory_kg": stored_inventory_kg,
            "storage_capacity_kg": storage_capacity_kg,
            "storage_overflow_kg": storage_overflow_kg,
            "storage_overflow_flag": storage_overflow_kg > 0.0,
            "biogas_ch4_m3": biogas_ch4_m3,
            "biogas_volume_to_energy_m3": biogas_ch4_m3,
            "storage_ch4_kg": storage_ch4_kg,
            "unmanaged_ch4_kg": unmanaged_ch4_kg,
            "compost_n2o_kg": compost_n2o_kg,
            "nutrient_return_kg": nutrient_return_kg,
            "soil_organic_carbon_delta_kg": soil_organic_carbon_delta_kg,
            "manure_n_total_kg": ration_nitrogen,
            "urinary_n_kg": urinary_n_kg,
            "fecal_n_kg": fecal_n_kg,
            "field_n2o_precursor_kg_n": field_n2o_precursor,
            "digestate_n_kg": digestate_n_kg,
            "digestate_p_kg": digestate_p_kg,
            "digestate_k_kg": digestate_k_kg,
            "compost_n_kg": compost_n_kg,
            "compost_p_kg": compost_p_kg,
            "compost_k_kg": compost_k_kg,
            "feed_ration_crude_protein_kg": ration_crude_protein,
            "feed_ration_nitrogen_kg": ration_nitrogen,
            "grass_cofeed_kg": grass_cofeed_kg,
            "food_waste_cofeed_kg": food_waste_cofeed_kg,
            "processor_residual_energy_kg": processor_residual_energy_kg,
            "digester_feedstock_kg": digester_feedstock_kg,
            "digester_feedstock_feasible": cofeed_feasible,
            "manure_route_alert": route_alert,
        }
        self.ctx.state["manure_flow_history"].append({"day": day.isoformat(), **payload})
        self.ctx.publish(Packet(source=self.name, name="manure_packet", day=day, payload=payload))
        self.ctx.publish(
            Packet(
                source=self.name,
                name="manure_resource_packet",
                day=day,
                payload={
                    "digestate": {"n_kg": digestate_n_kg, "p_kg": digestate_p_kg, "k_kg": digestate_k_kg},
                    "compost": {"n_kg": compost_n_kg, "p_kg": compost_p_kg, "k_kg": compost_k_kg},
                    "soil_organic_carbon_delta_kg": soil_organic_carbon_delta_kg,
                    "biogas_volume_to_energy_m3": biogas_ch4_m3,
                    "field_n2o_precursor_kg_n": field_n2o_precursor,
                },
            )
        )
        if thermochemical_kg > 0.0:
            self.ctx.publish(
                Packet(
                    source=self.name,
                    name="thermochemical_manure_packet",
                    day=day,
                    payload={
                        "thermochemical_manure_kg": thermochemical_kg,
                        "biochar_kg": thermochemical_kg
                        * float(value(self.ctx.calibration, "manure.thermochemical_biochar_yield_fraction")),
                        "syngas_energy_kwh": thermochemical_kg
                        * float(value(self.ctx.calibration, "manure.thermochemical_syngas_kwh_per_kg")),
                    },
                    confidence="low",
                )
            )
        self.ctx.state.setdefault("execution_order", []).append(self.name)
