from __future__ import annotations

from datetime import date

from dairy_abm.config import value
from dairy_abm.core import BaseAgent, Packet, require_fraction, require_nonnegative


class DairyProcessorAgent(BaseAgent):
    name = "dairy_processor"

    def tick(self, day: date) -> None:
        policy = self.ctx.state["policy"]
        l4_enabled = bool(
            self.ctx.scenario.get(
                "l4_byproduct_loop_enabled",
                value(self.ctx.calibration, "dairy_processor.l4_byproduct_loop_enabled"),
            )
        )
        quality_approved = bool(self.ctx.scenario.get("processor_quality_approved", True))
        enabled = bool(policy["dairy_processor_unit_enabled"]) and l4_enabled and quality_approved
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
        product_prices = {
            name: require_nonnegative(
                f"price_per_l_milk_{name}",
                float(
                    market_packet.payload.get(
                        f"price_per_l_milk_{name}",
                        value(self.ctx.calibration, f"dairy_processor.price_per_l_milk_{name}"),
                    )
                )
                if market_packet is not None
                else float(value(self.ctx.calibration, f"dairy_processor.price_per_l_milk_{name}")),
            )
            for name in product_mix
        }

        if not enabled:
            packet = Packet(
                source=self.name,
                name="processor_packet",
                day=day,
                quality="inactive",
                payload={
                    "enabled": False,
                    "raw_milk_input_l": milk_l,
                    "milk_processed_l": 0.0,
                    "farm_gate_milk_l": milk_l,
                    "raw_milk_revenue": milk_l * milk_price,
                    "processor_revenue": 0.0,
                    "processing_energy_kwh": 0.0,
                    "byproduct_revenue": 0.0,
                    "whey_l": 0.0,
                    "scotta_output_l": 0.0,
                    "sludge_l": 0.0,
                    "waste_milk_l": 0.0,
                    "product_streams_l": {name: 0.0 for name in product_mix},
                    "product_revenue": 0.0,
                    "product_mix": product_mix,
                    "product_prices_per_l": product_prices,
                    "component_balance": {"fat_kg": 0.0, "snf_kg": 0.0, "protein_kg": 0.0},
                    "valorized_residual_l": 0.0,
                },
            )
            self.ctx.publish(packet)
            self.ctx.state.setdefault("execution_order", []).append(self.name)
            return

        processor_fraction = float(value(self.ctx.calibration, "dairy_processor.fraction_milk_to_processor"))
        require_fraction("dairy_processor.fraction_milk_to_processor", processor_fraction)
        processing_capacity_l = max(0.0, float(self.ctx.scenario.get("processor_capacity_l_per_day", milk_l)))
        processed_milk_l = min(milk_l * processor_fraction, processing_capacity_l)
        farm_gate_milk_l = milk_l - processed_milk_l
        product_streams_l = {
            name: processed_milk_l * share for name, share in product_mix.items()
        }
        product_revenue = sum(
            product_streams_l[name] * product_prices[name] for name in product_streams_l
        )
        processing_energy = processed_milk_l * float(value(self.ctx.calibration, "dairy_processor.processing_energy_kwh_per_l_milk"))
        whey_enabled = bool(policy["whey_processor_unit_enabled"])
        whey_l = (
            product_streams_l["cheese"] * float(value(self.ctx.calibration, "dairy_processor.whey_yield_cheese"))
            + product_streams_l["yogurt"] * float(value(self.ctx.calibration, "dairy_processor.whey_yield_yogurt"))
            + product_streams_l["functional"] * float(value(self.ctx.calibration, "dairy_processor.whey_yield_functional"))
        )
        scotta_l = whey_l * max(0.0, min(1.0, float(self.ctx.scenario.get("scotta_yield_fraction", 0.0)))) if whey_enabled else 0.0
        sludge_l = processed_milk_l * float(value(self.ctx.calibration, "dairy_processor.fraction_sludge_of_milk"))
        waste_milk_l = processed_milk_l * float(value(self.ctx.calibration, "dairy_processor.fraction_waste_milk_of_milk"))
        feed_allowed = whey_enabled and bool(policy["coproduct_feed_allowed"])
        whey_feed_l = whey_l * require_fraction(
            "dairy_processor.fraction_whey_to_feed",
            float(value(self.ctx.calibration, "dairy_processor.fraction_whey_to_feed")),
        ) if feed_allowed else 0.0
        whey_disposal_l = whey_l - whey_feed_l
        sludge_energy_l = sludge_l * require_fraction(
            "dairy_processor.fraction_sludge_to_energy",
            float(value(self.ctx.calibration, "dairy_processor.fraction_sludge_to_energy")),
        ) if whey_enabled else 0.0
        sludge_fertilizer_l = sludge_l - sludge_energy_l
        waste_milk_feed_l = waste_milk_l * require_fraction(
            "dairy_processor.fraction_waste_milk_to_feed",
            float(value(self.ctx.calibration, "dairy_processor.fraction_waste_milk_to_feed")),
        ) if feed_allowed else 0.0
        waste_milk_energy_l = waste_milk_l - waste_milk_feed_l
        scotta_feed_l = scotta_l if feed_allowed else 0.0
        feed_return_whey_l = whey_feed_l + waste_milk_feed_l + scotta_feed_l
        if whey_l > 0.0 and feed_allowed:
            substitution_kg = float(
                value(self.ctx.calibration, "dairy_processor.byproduct_loop_feed_substitution_kg_per_kg")
            )
            self.ctx.state["loop_credits"]["feed_offset_kg"] += whey_feed_l * substitution_kg
        processor_revenue = product_revenue + farm_gate_milk_l * milk_price
        feed_return_total_l = whey_feed_l + waste_milk_feed_l + scotta_feed_l
        byproduct_revenue = feed_return_total_l * require_nonnegative(
            "dairy_processor.whey_liquid_price_per_l",
            float(value(self.ctx.calibration, "dairy_processor.whey_liquid_price_per_l")),
        )
        self.ctx.publish(
            Packet(
                source=self.name,
                name="processor_packet",
                day=day,
                payload={
                    "enabled": True,
                    "raw_milk_input_l": require_nonnegative("raw_milk_input_l", milk_l),
                    "milk_processed_l": require_nonnegative("milk_processed_l", processed_milk_l),
                    "processor_capacity_l_per_day": processing_capacity_l,
                    "quality_approved": quality_approved,
                    "farm_gate_milk_l": require_nonnegative("farm_gate_milk_l", farm_gate_milk_l),
                    "raw_milk_revenue": require_nonnegative("raw_milk_revenue", milk_l * milk_price),
                    "processor_revenue": require_nonnegative("processor_revenue", processor_revenue),
                    "processing_energy_kwh": require_nonnegative("processing_energy_kwh", processing_energy),
                    "byproduct_revenue": byproduct_revenue,
                    "whey_l": require_nonnegative("whey_l", whey_l),
                    "scotta_output_l": scotta_l,
                    "feed_return_whey_l": require_nonnegative("feed_return_whey_l", feed_return_whey_l),
                    "sludge_l": require_nonnegative("sludge_l", sludge_l),
                    "waste_milk_l": require_nonnegative("waste_milk_l", waste_milk_l),
                    "product_streams_l": product_streams_l,
                    "product_revenue": require_nonnegative("product_revenue", product_revenue),
                    "product_mix": product_mix,
                    "product_prices_per_l": product_prices,
                    "component_balance": {
                        "fat_kg": processed_milk_l * float(self.ctx.scenario.get("milk_fat_fraction", 0.039)),
                        "snf_kg": processed_milk_l * float(self.ctx.scenario.get("milk_snf_fraction", 0.087)),
                        "protein_kg": processed_milk_l * float(self.ctx.scenario.get("milk_protein_fraction", 0.032)),
                    },
                    "route_tiers": {"whey": "feed" if feed_allowed else "disposal", "scotta": "feed" if scotta_feed_l else "disposal", "sludge": "energy" if sludge_energy_l else "materials", "waste_milk": "feed" if waste_milk_feed_l else "energy"},
                    "valorized_residual_l": feed_return_total_l + sludge_energy_l,
                },
            )
        )
        self.ctx.publish(
            Packet(
                source=self.name,
                name="processor_residual_packet",
                day=day,
                payload={
                    "whey_feed_l": whey_feed_l,
                    "whey_disposal_l": whey_disposal_l,
                    "sludge_energy_l": sludge_energy_l,
                    "sludge_fertilizer_l": sludge_fertilizer_l,
                    "waste_milk_feed_l": waste_milk_feed_l,
                    "waste_milk_energy_l": waste_milk_energy_l,
                    "scotta_feed_l": scotta_feed_l,
                    "energy_feedstock_kg": sludge_energy_l + waste_milk_energy_l,
                    "fertilizer_residual_kg": sludge_fertilizer_l,
                },
            )
        )
        self.ctx.publish(
            Packet(
                source=self.name,
                name="dairy_return_feed_packet",
                day=day,
                payload={
                    "whey_to_feed_l": whey_feed_l,
                    "scotta_to_feed_l": scotta_feed_l,
                    "waste_milk_to_feed_l": waste_milk_feed_l,
                    "feed_eligible_kg_dm": feed_return_total_l * float(self.ctx.scenario.get("dairy_return_kg_dm_per_l", 0.08)),
                    "crude_protein_fraction": float(self.ctx.scenario.get("dairy_return_crude_protein_fraction", 0.18)),
                    "food_safety_approved": feed_allowed,
                },
                quality="ok" if feed_allowed else "blocked",
            )
        )
        self.ctx.state.setdefault("execution_order", []).append(self.name)
