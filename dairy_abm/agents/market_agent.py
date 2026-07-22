from __future__ import annotations

from datetime import date

from dairy_abm.config import value
from dairy_abm.core import BaseAgent, Packet, require_nonnegative


class MarketAgent(BaseAgent):
    name = "market"

    def tick(self, day: date) -> None:
        shock_stddev = float(value(self.ctx.calibration, "market.price_shock_stddev_fraction"))
        shock = self.ctx.rng.gauss(0.0, shock_stddev) if shock_stddev else 0.0
        milk_price = float(value(self.ctx.calibration, "market.milk_price_per_l")) * (1.0 + shock)
        feed_cost = float(value(self.ctx.calibration, "market.feed_cost_per_kg_dm")) * (1.0 + shock)
        milk_price = require_nonnegative("milk_price_per_l", milk_price)
        feed_cost = require_nonnegative("feed_cost_per_kg_dm", feed_cost)
        packet = Packet(
            source=self.name,
            name="market_price_packet",
            day=day,
            quality="static_config",
            payload={
                "milk_price_per_l": milk_price,
                "feed_cost_per_kg_dm": feed_cost,
                "cull_cow_price": float(value(self.ctx.calibration, "market.cull_cow_price")),
                "electricity_price_per_kwh": float(value(self.ctx.calibration, "energy.electricity_price_per_kwh")),
                "heat_value_per_kwh": float(value(self.ctx.calibration, "energy.heat_value_per_kwh")),
                "source": "static_config",
            },
        )
        self.ctx.publish(packet)
        self.ctx.state.setdefault("execution_order", []).append(self.name)
