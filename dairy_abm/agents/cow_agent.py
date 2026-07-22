from __future__ import annotations

from datetime import date
from typing import Any

from dairy_abm.config import value
from dairy_abm.core import BaseAgent, Packet, require_nonnegative


class CowAgent(BaseAgent):
    name = "cow"

    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        ctx.state.setdefault("cows", self._build_initial_herd())

    def _build_initial_herd(self) -> list[dict[str, Any]]:
        herd = self.ctx.scenario.get("herd")
        if isinstance(herd, list):
            return [dict(cow) for cow in herd]
        herd_size = int(self.ctx.scenario.get("herd_size", 100))
        return [
            {
                "id": f"cow-{index + 1}",
                "health_status": "healthy",
                "disease": None,
                "milk_trait": 1.0,
                "feed_efficiency_trait": 1.0,
            }
            for index in range(herd_size)
        ]

    def tick(self, day: date) -> None:
        cows = self.ctx.state.get("cows", [])
        disease_packet = self.ctx.get_packet("disease_state_packet")
        market_packet = self.ctx.get_packet("market_price_packet")

        base_milk = float(value(self.ctx.calibration, "cow.base_milk_l_per_cow_day"))
        base_dmi = float(value(self.ctx.calibration, "cow.base_dmi_kg_per_cow_day"))
        base_manure = float(value(self.ctx.calibration, "cow.base_manure_kg_per_cow_day"))
        base_enteric = float(value(self.ctx.calibration, "cow.enteric_ch4_kg_per_cow_day"))
        sick_loss = (
            float(disease_packet.payload["milk_loss_sick_fraction"])
            if disease_packet is not None
            else float(value(self.ctx.calibration, "disease.milk_loss_sick_fraction"))
        )
        milk_l = 0.0
        dmi_kg = 0.0
        manure_kg = 0.0
        enteric_ch4_kg = 0.0
        sick_cows = 0

        for cow in cows:
            milk_modifier = float(cow.get("milk_trait", 1.0))
            efficiency_modifier = float(cow.get("feed_efficiency_trait", 1.0))
            if cow.get("health_status") != "healthy":
                milk_modifier *= 1.0 - sick_loss
                sick_cows += 1
            milk_l += base_milk * milk_modifier
            dmi_kg += base_dmi * efficiency_modifier
            manure_kg += base_manure
            enteric_ch4_kg += base_enteric * efficiency_modifier

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
                "cow_count": len(cows),
                "healthy_cows": len(cows) - sick_cows,
                "sick_cows": sick_cows,
                "milk_l": require_nonnegative("milk_l", milk_l),
                "dmi_kg": require_nonnegative("dmi_kg", dmi_kg),
                "manure_kg": require_nonnegative("manure_kg", manure_kg),
                "enteric_ch4_kg": require_nonnegative("enteric_ch4_kg", enteric_ch4_kg),
                "milk_revenue": require_nonnegative("milk_revenue", milk_revenue),
            },
        )
        self.ctx.publish(packet)
        self.ctx.state.setdefault("execution_order", []).append(self.name)
