from __future__ import annotations

from datetime import date

from dairy_abm.config import value
from dairy_abm.core import BaseAgent, Packet, require_fraction, require_nonnegative


class EnergyAgent(BaseAgent):
    name = "energy"

    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        ctx.state.setdefault("energy_history", [])

    def tick(self, day: date) -> None:
        manure_packet = self.ctx.get_packet("manure_packet")
        thermochemical_packet = self.ctx.get_packet("thermochemical_manure_packet")
        market_packet = self.ctx.get_packet("market_price_packet")
        feedstock_kg = (
            float(manure_packet.payload.get("digester_feedstock_kg", manure_packet.payload["digester_kg"]))
            if manure_packet is not None
            else 0.0
        )
        feedstock_tons = require_nonnegative("feedstock_tons", feedstock_kg / 1000.0)
        feedstock_gross_kwh = feedstock_tons * float(value(self.ctx.calibration, "energy.kwh_per_ton_feedstock"))
        thermochemical_input_kwh = (
            require_nonnegative(
                "thermochemical_input_kwh",
                float(thermochemical_packet.payload.get("syngas_energy_kwh", 0.0)),
            )
            if thermochemical_packet is not None
            else 0.0
        )
        l3_enabled = bool(
            self.ctx.scenario.get("l3_energy_loop_enabled", value(self.ctx.calibration, "energy.l3_energy_loop_enabled"))
        )
        biogas_m3 = float(manure_packet.payload.get("biogas_volume_to_energy_m3", manure_packet.payload.get("biogas_ch4_m3", 0.0))) if manure_packet else 0.0
        methane_fraction = max(0.0, min(1.0, float(self.ctx.scenario.get("biogas_methane_fraction", 0.6))))
        conversion_mode = str(self.ctx.state["policy"].get("energy_conversion_mode", "chp")).lower()
        mode_efficiency = {"chp": 0.38, "electricity": 0.34, "boiler": 0.0}.get(conversion_mode, 0.38)
        biogas_gross_kwh = biogas_m3 * methane_fraction * 9.97 * mode_efficiency
        solar_capacity_kw = max(0.0, float(self.ctx.state["policy"].get("solar_capacity_kw", 0.0)))
        solar_kwh = solar_capacity_kw * max(0.0, float(self.ctx.scenario.get("solar_capacity_factor", 0.2))) * 24.0
        conversion_kwh = biogas_gross_kwh if biogas_m3 > 0.0 else feedstock_gross_kwh
        gross_kwh = conversion_kwh + thermochemical_input_kwh + solar_kwh if l3_enabled else 0.0
        parasitic = gross_kwh * require_fraction(
            "energy.parasitic_load_fraction", float(value(self.ctx.calibration, "energy.parasitic_load_fraction"))
        )
        net_kwh = max(0.0, gross_kwh - parasitic)
        farm_demand_kwh = require_nonnegative(
            "farm_energy_demand_kwh_per_day",
            float(
                self.ctx.scenario.get(
                    "farm_energy_demand_kwh_per_day",
                    value(self.ctx.calibration, "energy.farm_energy_demand_kwh_per_day"),
                )
            ),
        )
        displaced_grid_energy = min(net_kwh, farm_demand_kwh)
        surplus_energy = max(0.0, net_kwh - farm_demand_kwh)
        self_sufficiency = (
            100.0 * displaced_grid_energy / farm_demand_kwh if farm_demand_kwh > 0.0 else None
        )
        electricity_price = (
            float(market_packet.payload["electricity_price_per_kwh"])
            if market_packet is not None
            else float(value(self.ctx.calibration, "energy.electricity_price_per_kwh"))
        )
        grid_offset_factor = float(value(self.ctx.calibration, "energy.grid_offset_kg_co2e_per_kwh"))
        heat_mj_per_kwh = require_nonnegative(
            "energy.heat_mj_per_kwh", float(value(self.ctx.calibration, "energy.heat_mj_per_kwh"))
        )
        heat_generated_mj = net_kwh * heat_mj_per_kwh if heat_mj_per_kwh > 0.0 else None
        heat_value = float(market_packet.payload.get("heat_value_per_kwh", 0.0)) if market_packet is not None else 0.0
        heat_demand_mj = max(0.0, float(self.ctx.scenario.get("farm_heat_demand_mj_per_day", 0.0)))
        heat_displaced_mj = min(heat_generated_mj or 0.0, heat_demand_mj)
        heat_cost_saved = heat_displaced_mj / 3.6 * heat_value
        energy_cost_saved = displaced_grid_energy * electricity_price
        carbon_credit_price = float(market_packet.payload.get("carbon_credit_price_per_tonne_co2e", 0.0)) if market_packet is not None else 0.0
        grid_offset = displaced_grid_energy * grid_offset_factor
        carbon_credits_earned = max(0.0, grid_offset / 1000.0 * carbon_credit_price)
        conversion_confidence = "low" if thermochemical_input_kwh > 0.0 else "calibrated"
        packet_confidence = "low" if heat_generated_mj is None or conversion_confidence == "low" else "calibrated"
        payload = {
            "feedstock_tons": feedstock_tons,
            "feedstock_gross_kwh": require_nonnegative("feedstock_gross_kwh", feedstock_gross_kwh),
            "biogas_volume_m3": biogas_m3,
            "biogas_methane_fraction": methane_fraction,
            "conversion_mode": conversion_mode,
            "biogas_gross_kwh": biogas_gross_kwh,
            "solar_capacity_kw": solar_capacity_kw,
            "solar_generated_kwh": solar_kwh,
            "thermochemical_input_kwh": thermochemical_input_kwh,
            "gross_kwh": require_nonnegative("gross_kwh", gross_kwh),
            "parasitic_kwh": require_nonnegative("parasitic_kwh", parasitic),
            "net_kwh": require_nonnegative("net_kwh", net_kwh),
            "farm_energy_demand_kwh": farm_demand_kwh,
            "displaced_grid_energy_kwh": displaced_grid_energy,
            "surplus_energy_kwh": surplus_energy,
            "energy_self_sufficiency_pct": self_sufficiency,
            "heat_generated_mj": heat_generated_mj,
            "heat_demand_mj": heat_demand_mj,
            "heat_displaced_mj": heat_displaced_mj,
            "heat_value": heat_cost_saved,
            "electricity_generated_kwh": require_nonnegative("electricity_generated_kwh", net_kwh),
            "electricity_price_per_kwh": require_nonnegative("electricity_price_per_kwh", electricity_price),
            "energy_value": require_nonnegative("energy_value", energy_cost_saved + heat_cost_saved),
            "energy_cost_saved_day": require_nonnegative("energy_cost_saved_day", energy_cost_saved),
            "carbon_credits_earned": carbon_credits_earned,
            "grid_offset_kg_co2e_per_kwh": require_nonnegative("grid_offset_kg_co2e_per_kwh", grid_offset_factor),
            "grid_offset_kg_co2e": require_nonnegative(
                "grid_offset_kg_co2e", grid_offset
            ),
            "renewable_displacement_flag": displaced_grid_energy > 0.0,
            "conversion_confidence": conversion_confidence,
        }
        self.ctx.state["energy_history"].append({"day": day.isoformat(), **payload})
        self.ctx.publish(
            Packet(
                source=self.name,
                name="energy_packet",
                day=day,
                payload=payload,
                confidence=packet_confidence,
            )
        )
        self.ctx.publish(
            Packet(
                source=self.name,
                name="energy_offset_packet",
                day=day,
                payload={"ghg_offset_reported_kg_co2e": grid_offset, "carbon_credits_earned": carbon_credits_earned, "confidence": packet_confidence},
                confidence=packet_confidence,
                stream_id="grid_offset",
            )
        )
        self.ctx.state.setdefault("execution_order", []).append(self.name)
