from __future__ import annotations

from datetime import date

from dairy_abm.config import value
from dairy_abm.core import BaseAgent, Packet, require_fraction, require_nonnegative


class DairyProcessorAgent(BaseAgent):
    name = "dairy_processor"

    def tick(self, day: date) -> None:
        enabled = bool(value(self.ctx.calibration, "dairy_processor.enabled")) or bool(
            self.ctx.scenario.get("enable_processor", False)
        )
        cow_packet = self.ctx.get_packet("cow_daily_packet")
        market_packet = self.ctx.get_packet("market_price_packet")
        milk_l = float(cow_packet.payload["milk_l"]) if cow_packet is not None else 0.0
        milk_price = (
            float(market_packet.payload["milk_price_per_l"])
            if market_packet is not None
            else float(value(self.ctx.calibration, "market.milk_price_per_l"))
        )
        product_mix = {
            "cheese": float(value(self.ctx.calibration, "dairy_processor.product_mix_cheese")),
            "butter": float(value(self.ctx.calibration, "dairy_processor.product_mix_butter")),
            "yogurt": float(value(self.ctx.calibration, "dairy_processor.product_mix_yogurt")),
            "fresh": float(value(self.ctx.calibration, "dairy_processor.product_mix_fresh")),
            "functional": float(value(self.ctx.calibration, "dairy_processor.product_mix_functional")),
        }
        for name, share in product_mix.items():
            require_fraction(f"dairy_processor.product_mix_{name}", share)

        if not enabled:
            packet = Packet(
                source=self.name,
                name="processor_packet",
                day=day,
                quality="inactive",
                payload={
                    "enabled": False,
                    "milk_processed_l": 0.0,
                    "farm_gate_milk_l": milk_l,
                    "processor_revenue": 0.0,
                    "processing_energy_kwh": 0.0,
                    "whey_l": 0.0,
                    "product_mix": product_mix,
                },
            )
            self.ctx.publish(packet)
            self.ctx.state.setdefault("execution_order", []).append(self.name)
            return

        processing_energy = milk_l * float(value(self.ctx.calibration, "dairy_processor.processing_energy_kwh_per_l_milk"))
        whey_enabled = bool(value(self.ctx.calibration, "dairy_processor.whey_processing_enabled")) or bool(
            self.ctx.scenario.get("enable_whey_processing", False)
        )
        whey_l = milk_l * float(value(self.ctx.calibration, "dairy_processor.whey_l_per_l_processed_milk")) if whey_enabled else 0.0
        processor_revenue = milk_l * milk_price * 1.15
        self.ctx.publish(
            Packet(
                source=self.name,
                name="processor_packet",
                day=day,
                payload={
                    "enabled": True,
                    "milk_processed_l": require_nonnegative("milk_processed_l", milk_l),
                    "farm_gate_milk_l": 0.0,
                    "processor_revenue": require_nonnegative("processor_revenue", processor_revenue),
                    "processing_energy_kwh": require_nonnegative("processing_energy_kwh", processing_energy),
                    "whey_l": require_nonnegative("whey_l", whey_l),
                    "product_mix": product_mix,
                },
            )
        )
        self.ctx.state.setdefault("execution_order", []).append(self.name)
