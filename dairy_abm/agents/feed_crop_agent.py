from __future__ import annotations

from datetime import date

from dairy_abm.config import value
from dairy_abm.core import BaseAgent, Packet, require_nonnegative


class FeedCropAgent(BaseAgent):
    name = "feed_crop"

    def tick(self, day: date) -> None:
        credits = self.ctx.state.get("loop_credits", {"feed_offset_kg": 0.0, "water_offset_l": 0.0})
        feed_offset = float(credits["feed_offset_kg"])
        water_offset = float(credits["water_offset_l"])
        self.ctx.state["loop_credits"] = {"feed_offset_kg": 0.0, "water_offset_l": 0.0}

        cow_packet = self.ctx.get_packet("cow_daily_packet")
        cow_count = int(cow_packet.payload["cow_count"]) if cow_packet is not None else 0
        total_dmi = float(cow_packet.payload["dmi_kg"]) if cow_packet is not None else 0.0
        total_dmi = require_nonnegative("total_dmi_kg", total_dmi)
        market = self.ctx.get_packet("market_price_packet")
        feed_cost = (
            float(market.payload["feed_cost_per_kg_dm"])
            if market is not None
            else float(value(self.ctx.calibration, "feed_crop.ration_cost_per_kg_dm"))
        )
        land_packet = self.ctx.get_packet("land_packet")
        if land_packet is not None:
            cropland_ha = float(land_packet.payload["cropland_ha"])
            land_owner = "land"
        else:
            cropland_ha = float(self.ctx.scenario.get("land_cropland_ha", value(self.ctx.calibration, "land.cropland_ha")))
            land_owner = "feed_crop"
            self.ctx.state.setdefault("land_owner", "feed_crop")
        crop_supply = cropland_ha * float(value(self.ctx.calibration, "feed_crop.crop_yield_kg_dm_per_ha_day"))
        purchased_feed = max(0.0, total_dmi - crop_supply - feed_offset)
        feed_cost_total = purchased_feed * feed_cost
        irrigation_l = max(
            0.0,
            cropland_ha * float(value(self.ctx.calibration, "feed_crop.irrigation_l_per_ha_day")) - water_offset,
        )
        packet = Packet(
            source=self.name,
            name="feed_crop_packet",
            day=day,
            payload={
                "cow_count": cow_count,
                "dmi_demand_kg": total_dmi,
                "crop_supply_kg_dm": crop_supply,
                "purchased_feed_kg_dm": purchased_feed,
                "feed_cost": feed_cost_total,
                "feed_cost_per_kg_dm": feed_cost,
                "irrigation_l": irrigation_l,
                "feed_offset_kg": feed_offset,
                "water_offset_l": water_offset,
                "land_owner": land_owner,
            },
        )
        self.ctx.publish(packet)
        self.ctx.state.setdefault("execution_order", []).append(self.name)
