from __future__ import annotations

from datetime import date
from math import cos, pi

from dairy_abm.config import value
from dairy_abm.core import BaseAgent, Packet, require_fraction, require_nonnegative


class FeedCropAgent(BaseAgent):
    name = "feed_crop"

    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        ctx.state.setdefault(
            "feed_inventory_kg_dm",
            float(
                ctx.scenario.get(
                    "initial_feed_inventory_kg_dm",
                    value(ctx.calibration, "feed_crop.initial_feed_inventory_kg_dm"),
                )
            ),
        )
        ctx.state.setdefault(
            "soil_n_kg",
            float(
                ctx.scenario.get(
                    "initial_soil_n_kg", value(ctx.calibration, "feed_crop.initial_soil_n_kg")
                )
            ),
        )
        ctx.state.setdefault("feed_history", [])
        ctx.state.setdefault("local_feed_inventory_kg_dm", float(ctx.scenario.get("local_feed_inventory_kg_dm", 0.0)))
        ctx.state.setdefault("plant_coproduct_inventory_kg_dm", float(ctx.scenario.get("plant_coproduct_inventory_kg_dm", 0.0)))

    def tick(self, day: date) -> None:
        credits = self.ctx.state.get("loop_credits", {"feed_offset_kg": 0.0, "water_offset_l": 0.0})
        feed_offset = float(credits["feed_offset_kg"])
        water_offset = float(credits["water_offset_l"])
        self.ctx.state["loop_credits"] = {"feed_offset_kg": 0.0, "water_offset_l": 0.0}
        nutrient_credits = self.ctx.state["nutrient_credits"]
        recovered_water_n_credit = require_nonnegative(
            "recovered_water_n_kg", float(nutrient_credits["recovered_water_n_kg"])
        )
        self.ctx.state["nutrient_credits"] = {"recovered_water_n_kg": 0.0}

        cow_packet = self.ctx.get_packet("cow_daily_packet")
        active_cows = [
            cow
            for cow in self.ctx.state.get("cows", [])
            if cow.get("alive", True)
            and cow.get("sex", "female") == "female"
            and int(cow.get("days_in_milk", 0)) > 0
        ]
        cow_count = len(active_cows)
        total_dmi = (
            float(cow_packet.payload["dmi_kg"])
            if cow_packet is not None
            else sum(float(cow.get("expected_dmi_kg", value(self.ctx.calibration, "cow.base_dmi_kg_per_cow_day"))) for cow in active_cows)
        )
        total_dmi = require_nonnegative("total_dmi_kg", total_dmi)
        grazing_packet = self.ctx.get_packet("grazing_access_packet")
        grazing_intake_kg = float(cow_packet.payload.get("grazing_intake_kg", 0.0)) if cow_packet is not None else 0.0
        if grazing_packet is not None and bool(grazing_packet.payload.get("enabled", False)):
            available_grazing = (
                float(
                    grazing_packet.payload.get(
                        "grazable_pasture_ha",
                        grazing_packet.payload.get("pasture_available_ha", 0.0),
                    )
                )
                * float(value(self.ctx.calibration, "cow.grazing_intake_kg_dm_per_ha_day"))
            )
            grazing_intake_kg = min(total_dmi, available_grazing)
        grazing_intake_kg = require_nonnegative("grazing_intake_kg", grazing_intake_kg)
        market = self.ctx.get_packet("market_price_packet")
        sensor_packet = self.ctx.get_packet("sensor_observation_packet")
        feed_cost = (
            float(market.payload["feed_cost_per_kg_dm"])
            if market is not None
            else float(value(self.ctx.calibration, "feed_crop.ration_cost_per_kg_dm"))
        )
        land_packet = self.ctx.get_packet("land_packet")
        prior_manure = self.ctx.get_packet("manure_packet")
        prior_manure_resources = self.ctx.get_packet("manure_resource_packet")
        if land_packet is not None:
            cropland_ha = float(
                land_packet.payload.get("cropland_available_ha", land_packet.payload["cropland_ha"])
            )
            land_owner = "land"
        else:
            cropland_ha = float(self.ctx.scenario.get("land_cropland_ha", value(self.ctx.calibration, "land.cropland_ha")))
            land_owner = "feed_crop"
            self.ctx.state.setdefault("land_owner", "feed_crop")
        season_yield_mod = float(
            self.ctx.scenario.get(
                "feed_seasonal_yield_modifier",
                value(self.ctx.calibration, "feed_crop.seasonal_yield_modifier"),
            )
        )
        monthly_mod = self.ctx.scenario.get("feed_seasonal_yield_by_month", {})
        if isinstance(monthly_mod, dict):
            month_key = f"{day.month:02d}"
            season_yield_mod = float(monthly_mod.get(month_key, monthly_mod.get(str(day.month), season_yield_mod)))
        soil_organic_carbon = float(self.ctx.state.get("soil_organic_carbon", 0.0))
        soil_yield_modifier = max(0.5, min(1.5, 1.0 + soil_organic_carbon / max(1.0, cropland_ha * 1000.0)))
        crop_supply = cropland_ha * float(value(self.ctx.calibration, "feed_crop.crop_yield_kg_dm_per_ha_day")) * season_yield_mod * soil_yield_modifier
        opening_inventory = require_nonnegative(
            "feed_inventory_kg_dm", float(self.ctx.state["feed_inventory_kg_dm"])
        )
        feed_demand = max(0.0, total_dmi - grazing_intake_kg)
        plant_coproduct_inventory = max(0.0, float(self.ctx.state["plant_coproduct_inventory_kg_dm"]))
        dairy_return = self.ctx.get_packet("dairy_return_feed_packet")
        dairy_return_kg = float(dairy_return.payload.get("feed_eligible_kg_dm", 0.0)) if dairy_return else 0.0
        local_import_inventory = max(0.0, float(self.ctx.state["local_feed_inventory_kg_dm"]))
        local_feed_available = opening_inventory + crop_supply
        local_feed_used = min(feed_demand, local_feed_available)
        remaining_demand = max(0.0, feed_demand - local_feed_used - feed_offset)
        plant_coproduct_used = min(remaining_demand, plant_coproduct_inventory) if bool(self.ctx.state["policy"].get("coproduct_feed_allowed", True)) else 0.0
        remaining_demand -= plant_coproduct_used
        dairy_return_used = min(remaining_demand, dairy_return_kg) if bool(self.ctx.state["policy"].get("coproduct_feed_allowed", True)) else 0.0
        remaining_demand -= dairy_return_used
        local_import_used = min(remaining_demand, local_import_inventory)
        purchased_feed = max(0.0, remaining_demand - local_import_used)
        self.ctx.state["plant_coproduct_inventory_kg_dm"] = plant_coproduct_inventory - plant_coproduct_used
        self.ctx.state["local_feed_inventory_kg_dm"] = local_import_inventory - local_import_used
        ending_inventory = local_feed_available - local_feed_used
        self.ctx.state["feed_inventory_kg_dm"] = ending_inventory
        local_cp_fraction = require_fraction(
            "feed_crop.local_feed_crude_protein_fraction",
            float(value(self.ctx.calibration, "feed_crop.local_feed_crude_protein_fraction")),
        )
        nir_profile = sensor_packet.payload.get("nir_feed_profile", {}) if sensor_packet is not None else {}
        nir_freshness_days = int(nir_profile.get("freshness_days", 0)) if isinstance(nir_profile, dict) else 0
        if isinstance(nir_profile, dict) and nir_profile.get("valid", False) and nir_freshness_days <= int(self.ctx.scenario.get("nir_max_freshness_days", 7)):
            local_cp_fraction = require_fraction(
                "sensors.nir_feed_profile.crude_protein_fraction",
                float(nir_profile.get("crude_protein_fraction", local_cp_fraction)),
            )
        imported_cp_fraction = require_fraction(
            "feed_crop.imported_feed_crude_protein_fraction",
            float(value(self.ctx.calibration, "feed_crop.imported_feed_crude_protein_fraction")),
        )
        metabolizable_protein_fraction = require_fraction(
            "feed_crop.metabolizable_protein_fraction_of_crude_protein",
            float(value(self.ctx.calibration, "feed_crop.metabolizable_protein_fraction_of_crude_protein")),
        )
        nitrogen_fraction = require_fraction(
            "feed_crop.nitrogen_fraction_of_crude_protein",
            float(value(self.ctx.calibration, "feed_crop.nitrogen_fraction_of_crude_protein")),
        )
        coproduct_cp = float(self.ctx.scenario.get("plant_coproduct_crude_protein_fraction", imported_cp_fraction))
        dairy_return_cp = float(dairy_return.payload.get("crude_protein_fraction", imported_cp_fraction)) if dairy_return else imported_cp_fraction
        ration_crude_protein = (
            local_feed_used * local_cp_fraction
            + (local_import_used + purchased_feed) * imported_cp_fraction
            + plant_coproduct_used * coproduct_cp
            + dairy_return_used * dairy_return_cp
        )
        amino_acid_balancing_active = bool(self.ctx.state["policy"].get("amino_acid_policy_active", False))
        protein_target_fraction = float(self.ctx.scenario.get("protein_target_fraction", local_cp_fraction))
        baseline_protein = total_dmi * protein_target_fraction
        # Amino acid balancing permits a lower crude-protein ration while retaining the
        # metabolizable-protein target through lysine/methionine supplementation.
        cp_reduction_points = min(
            0.025,
            max(
                0.0,
                float(
                    self.ctx.scenario.get(
                        "amino_acid_cp_reduction_points",
                        value(self.ctx.calibration, "feed_crop.amino_acid_cp_reduction_points"),
                    )
                ),
            ),
        ) if amino_acid_balancing_active else 0.0
        ration_crude_protein = max(0.0, ration_crude_protein - cp_reduction_points * total_dmi)
        ration_metabolizable_protein = max(
            ration_crude_protein * metabolizable_protein_fraction,
            max(0.0, baseline_protein - cp_reduction_points * total_dmi) * metabolizable_protein_fraction,
        )
        ration_nitrogen = ration_crude_protein * nitrogen_fraction
        opening_soil_n = require_nonnegative("soil_n_kg", float(self.ctx.state["soil_n_kg"]))
        if prior_manure_resources is not None:
            digestate = prior_manure_resources.payload.get("digestate", {})
            compost = prior_manure_resources.payload.get("compost", {})
            manure_n_return = require_nonnegative(
                "route_specific_nutrient_return_kg",
                float(digestate.get("n_kg", 0.0)) + float(compost.get("n_kg", 0.0)),
            )
        else:
            manure_n_return = (
                require_nonnegative("nutrient_return_kg", float(prior_manure.payload["nutrient_return_kg"]))
                if prior_manure is not None
                else 0.0
            )
        soil_n_available = opening_soil_n + manure_n_return + recovered_water_n_credit
        daily_n_requirement = (
            cropland_ha
            * float(value(self.ctx.calibration, "feed_crop.fertilizer_n_kg_per_ha_month"))
            / 30.0
        )
        organic_n_used = min(soil_n_available, daily_n_requirement)
        recycled_n_used = min(manure_n_return, organic_n_used)
        fertilizer_n_required = daily_n_requirement - organic_n_used
        catch_crop_leaching_fraction = require_fraction(
            "feed_crop.catch_crop_n_leaching_fraction",
            float(value(self.ctx.calibration, "feed_crop.catch_crop_n_leaching_fraction")),
        )
        catch_crop_active = bool(self.ctx.state["policy"].get("catch_crop_active", False))
        catch_crop_n_leaching_kg = soil_n_available * catch_crop_leaching_fraction * (0.5 if catch_crop_active else 1.0)
        ending_soil_n = max(0.0, soil_n_available - organic_n_used - catch_crop_n_leaching_kg)
        self.ctx.state["soil_n_kg"] = ending_soil_n
        feed_cost_total = purchased_feed * feed_cost
        total_feed_supplied = local_feed_used + local_import_used + purchased_feed + plant_coproduct_used + dairy_return_used + feed_offset + grazing_intake_kg
        ration_coverage_fraction = 1.0 if total_dmi <= 0.0 else min(
            1.0, total_feed_supplied / total_dmi
        )
        total_feed_from_farm = local_feed_used + grazing_intake_kg
        total_feed_all = total_feed_from_farm + local_import_used + purchased_feed + plant_coproduct_used + dairy_return_used
        local_feed_autonomy = total_feed_from_farm / total_feed_all if total_feed_all > 0.0 else 1.0
        production_system = str(
            self.ctx.scenario.get(
                "production_system",
                self.ctx.scenario.get("feed_crop", {}).get("production_system", "high_intensity"),
            )
        )
        me_key = {
            "arid_grazing": "feed_crop.metabolizable_energy_mj_per_kg_dm_arid_grazing",
            "humid_temperate": "feed_crop.metabolizable_energy_mj_per_kg_dm_humid_temperate",
            "high_intensity": "feed_crop.metabolizable_energy_mj_per_kg_dm_high_intensity",
        }.get(production_system, "feed_crop.metabolizable_energy_mj_per_kg_dm_high_intensity")
        base_me_mj_per_kg_dm = float(value(self.ctx.calibration, me_key))
        day_of_year = day.timetuple().tm_yday
        seasonal_me_amplitude = float(value(self.ctx.calibration, "feed_crop.seasonal_me_amplitude_fraction"))
        seasonal_me_modifier = 1.0 + seasonal_me_amplitude * cos(2 * pi * (day_of_year - 200) / 365.0)
        ration_me_mj_per_kg_dm = base_me_mj_per_kg_dm * seasonal_me_modifier
        ration_ndf_fraction = require_fraction(
            "feed_crop.neutral_detergent_fiber_fraction",
            float(value(self.ctx.calibration, "feed_crop.neutral_detergent_fiber_fraction")),
        )
        irrigation_demand_l = cropland_ha * float(
            value(self.ctx.calibration, "feed_crop.irrigation_l_per_ha_day")
        )
        recovered_water_applied_l = min(irrigation_demand_l, water_offset)
        irrigation_l = irrigation_demand_l - recovered_water_applied_l
        lysine_adequacy = min(1.0, ration_crude_protein / max(0.001, total_feed_supplied * protein_target_fraction)) if amino_acid_balancing_active else None
        methionine_adequacy = lysine_adequacy if amino_acid_balancing_active else None
        nitrogen_excretion_reduced_flag = amino_acid_balancing_active and cp_reduction_points > 0.0
        rp_lys_flag = bool(amino_acid_balancing_active)
        rp_met_flag = bool(amino_acid_balancing_active)
        raw_ration_targets = {
            str(cow["id"]): max(
                0.1,
                float(cow.get("expected_dmi_kg", value(self.ctx.calibration, "cow.base_dmi_kg_per_cow_day")))
                * (1.0 + 0.08 * max(0, int(cow.get("parity", 1)) - 1))
                * (1.0 + 0.05 * max(0.0, 3.0 - float(cow.get("body_condition_score", 3.0))))
                * (1.0 + max(0.0, float(cow.get("trait_vector", {}).get("rfi_fat_ebv", 0.0))) / 20.0),
            )
            for cow in active_cows
        }
        target_total = sum(raw_ration_targets.values())
        per_cow_rations = {
            str(cow["id"]): {
                "dmi_target_kg": raw_ration_targets[str(cow["id"])],
                "me_mj_per_kg_dm": ration_me_mj_per_kg_dm,
                "crude_protein_fraction": ration_crude_protein / total_feed_supplied if total_feed_supplied else 0.0,
                "ndf_fraction": ration_ndf_fraction,
                "coverage_fraction": min(
                    1.0,
                    ration_coverage_fraction
                    * total_dmi / max(0.001, target_total)
                    * raw_ration_targets[str(cow["id"])] / max(0.001, total_dmi / max(1, cow_count)),
                ),
                "lysine_adequacy": lysine_adequacy,
                "methionine_adequacy": methionine_adequacy,
            }
            for cow in active_cows
        }
        packet = Packet(
            source=self.name,
            name="feed_crop_packet",
            day=day,
            payload={
                "cow_count": cow_count,
                "cropland_ha": cropland_ha,
                "dmi_demand_kg": total_dmi,
                "crop_supply_kg_dm": crop_supply,
                "opening_feed_inventory_kg_dm": opening_inventory,
                "local_feed_used_kg_dm": local_feed_used,
                "ending_feed_inventory_kg_dm": ending_inventory,
                "ration_crude_protein_kg": ration_crude_protein,
                "nir_crude_protein_fraction": local_cp_fraction,
                "nir_profile_fresh": bool(isinstance(nir_profile, dict) and nir_profile.get("valid", False) and nir_freshness_days <= int(self.ctx.scenario.get("nir_max_freshness_days", 7))),
                "ration_metabolizable_protein_kg": ration_metabolizable_protein,
                "ration_nitrogen_kg": ration_nitrogen,
                "opening_soil_n_kg": opening_soil_n,
                "manure_n_return_kg": manure_n_return,
                "manure_resource_packet_used": prior_manure_resources is not None,
                "recovered_water_n_credit_kg": recovered_water_n_credit,
                "organic_n_used_kg": organic_n_used,
                "recycled_n_used_kg": recycled_n_used,
                "fertilizer_n_required_kg": fertilizer_n_required,
                "ending_soil_n_kg": ending_soil_n,
                "purchased_feed_kg_dm": purchased_feed,
                "local_import_feed_kg_dm": local_import_used,
                "plant_coproduct_feed_kg_dm": plant_coproduct_used,
                "dairy_return_feed_kg_dm": dairy_return_used,
                "feed_sourcing_hierarchy": ["own_farm", "plant_coproduct", "local", "market_import"],
                "ration_coverage_fraction": ration_coverage_fraction,
                "local_feed_autonomy": local_feed_autonomy,
                "seasonal_yield_modifier": season_yield_mod,
                "catch_crop_n_leaching_kg": catch_crop_n_leaching_kg,
                "catch_crop_active": catch_crop_active,
                "soil_organic_carbon_delta_kg": float(prior_manure.payload.get("soil_organic_carbon_delta_kg", 0.0)) if prior_manure else 0.0,
                "ration_me_mj_per_kg_dm": ration_me_mj_per_kg_dm,
                "ration_ndf_fraction": ration_ndf_fraction,
                "grazing_intake_kg": grazing_intake_kg,
                "feed_demand_after_grazing_kg": feed_demand,
                "feed_cost": feed_cost_total,
                "feed_cost_per_kg_dm": feed_cost,
                "irrigation_l": irrigation_l,
                "irrigation_demand_l": irrigation_demand_l,
                "freshwater_irrigation_l": irrigation_l,
                "recovered_water_applied_l": recovered_water_applied_l,
                "feed_offset_kg": feed_offset,
                "water_offset_l": water_offset,
                "land_owner": land_owner,
                "per_cow_rations": per_cow_rations,
                "precision_feeding_active": True,
                "amino_acid_balancing_active": amino_acid_balancing_active,
                "amino_acid_cp_reduction_points": cp_reduction_points,
                "nitrogen_excretion_reduced_flag": nitrogen_excretion_reduced_flag,
                "rp_lys_flag": rp_lys_flag,
                "rp_met_flag": rp_met_flag,
                "lysine_adequacy": lysine_adequacy,
                "methionine_adequacy": methionine_adequacy,
                "energy_protein_synchrony": min(1.0, ration_metabolizable_protein / max(0.001, total_feed_supplied * protein_target_fraction)),
                "ration_optimizer_objectives": {"cost": feed_cost_total, "nitrogen": ration_nitrogen, "coverage": ration_coverage_fraction},
            },
        )
        self.ctx.publish(packet)
        self.ctx.state["feed_history"].append({"day": day.isoformat(), **packet.payload})
        self.ctx.publish(
            Packet(
                source=self.name,
                name="feed_nitrogen_context_packet",
                day=day,
                payload={
                    "ration_crude_protein_kg": ration_crude_protein,
                    "ration_metabolizable_protein_kg": ration_metabolizable_protein,
                    "ration_nitrogen_kg": ration_nitrogen,
                    "dmi_demand_kg": total_dmi,
                },
            )
        )
        self.ctx.state.setdefault("execution_order", []).append(self.name)
