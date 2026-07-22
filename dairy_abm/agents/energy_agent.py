from __future__ import annotations

from datetime import date

from dairy_abm.config import value
from dairy_abm.core import BaseAgent, Packet, require_nonnegative


class EnergyAgent(BaseAgent):
    name = "energy"

    def tick(self, day: date) -> None:
        manure_packet = self.ctx.get_packet("manure_packet")
        market_packet = self.ctx.get_packet("market_price_packet")
        feedstock_tons = (
            float(manure_packet.payload["digester_kg"]) / 1000.0 if manure_packet is not None else 0.0
        )
        gross_kwh = feedstock_tons * float(value(self.ctx.calibration, "energy.kwh_per_ton_feedstock"))
        parasitic = gross_kwh * float(value(self.ctx.calibration, "energy.parasitic_load_fraction"))
        net_kwh = max(0.0, gross_kwh - parasitic)
        electricity_price = (
            float(market_packet.payload["electricity_price_per_kwh"])
            if market_packet is not None
            else float(value(self.ctx.calibration, "energy.electricity_price_per_kwh"))
        )
        offset_kg_co2e = net_kwh * float(value(self.ctx.calibration, "energy.grid_offset_kg_co2e_per_kwh"))
        self.ctx.publish(
            Packet(
                source=self.name,
                name="energy_packet",
                day=day,
                payload={
                    "feedstock_tons": require_nonnegative("feedstock_tons", feedstock_tons),
                    "gross_kwh": require_nonnegative("gross_kwh", gross_kwh),
                    "parasitic_kwh": require_nonnegative("parasitic_kwh", parasitic),
                    "net_kwh": require_nonnegative("net_kwh", net_kwh),
                    "energy_value": require_nonnegative("energy_value", net_kwh * electricity_price),
                    "grid_offset_kg_co2e": require_nonnegative("grid_offset_kg_co2e", offset_kg_co2e),
                },
            )
        )
        self.ctx.state.setdefault("execution_order", []).append(self.name)
