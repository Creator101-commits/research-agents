from __future__ import annotations

from datetime import date

from dairy_abm.config import value
from dairy_abm.core import BaseAgent, Packet, require_nonnegative


class WaterAgent(BaseAgent):
    name = "water"

    def tick(self, day: date) -> None:
        cow_packet = self.ctx.get_packet("cow_daily_packet")
        feed_packet = self.ctx.get_packet("feed_crop_packet")
        cow_count = int(cow_packet.payload["cow_count"]) if cow_packet is not None else 0
        drinking_l = cow_count * float(value(self.ctx.calibration, "water.drinking_l_per_cow_day"))
        parlor_l = cow_count * float(value(self.ctx.calibration, "water.parlor_l_per_cow_day"))
        irrigation_l = float(feed_packet.payload["irrigation_l"]) if feed_packet is not None else 0.0
        gross_l = drinking_l + parlor_l + irrigation_l
        saving_l = cow_count * float(value(self.ctx.calibration, "water.water_saving_l_per_cow_day"))
        recoverable_l = max(0.0, parlor_l - saving_l)
        recovered_l = recoverable_l * float(value(self.ctx.calibration, "water.treatment_recovery_fraction"))
        l2_enabled = bool(
            self.ctx.scenario.get(
                "l2_water_loop_enabled",
                value(self.ctx.calibration, "water.l2_water_loop_enabled"),
            )
        )
        if l2_enabled:
            offset_fraction = float(value(self.ctx.calibration, "water.water_loop_fresh_water_offset_fraction"))
            self.ctx.state["loop_credits"]["water_offset_l"] += recovered_l * offset_fraction
        net_l = max(0.0, gross_l - saving_l - recovered_l)
        cost = net_l * float(value(self.ctx.calibration, "water.water_cost_per_l"))
        self.ctx.publish(
            Packet(
                source=self.name,
                name="water_packet",
                day=day,
                payload={
                    "cow_count": cow_count,
                    "drinking_l": require_nonnegative("drinking_l", drinking_l),
                    "parlor_l": require_nonnegative("parlor_l", parlor_l),
                    "irrigation_l": require_nonnegative("irrigation_l", irrigation_l),
                    "gross_water_l": require_nonnegative("gross_water_l", gross_l),
                    "water_saving_l": require_nonnegative("water_saving_l", saving_l),
                    "recovered_water_l": require_nonnegative("recovered_water_l", recovered_l),
                    "net_water_l": require_nonnegative("net_water_l", net_l),
                    "water_cost": require_nonnegative("water_cost", cost),
                },
            )
        )
        self.ctx.state.setdefault("execution_order", []).append(self.name)
