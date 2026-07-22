from __future__ import annotations

from datetime import date

from dairy_abm.config import value
from dairy_abm.core import BaseAgent, ConfigError, Packet, require_fraction, require_nonnegative


class ManureAgent(BaseAgent):
    name = "manure"

    def tick(self, day: date) -> None:
        cow_packet = self.ctx.get_packet("cow_daily_packet")
        manure_kg = float(cow_packet.payload["manure_kg"]) if cow_packet is not None else 0.0
        digester_fraction = require_fraction(
            "manure.digester_route_fraction",
            float(value(self.ctx.calibration, "manure.digester_route_fraction")),
        )
        compost_fraction = require_fraction(
            "manure.compost_route_fraction",
            float(value(self.ctx.calibration, "manure.compost_route_fraction")),
        )
        storage_fraction = require_fraction(
            "manure.storage_route_fraction",
            float(value(self.ctx.calibration, "manure.storage_route_fraction")),
        )
        route_total = digester_fraction + compost_fraction + storage_fraction
        if abs(route_total - 1.0) > 0.000001:
            raise ConfigError(f"manure route fractions must sum to 1.0, got {route_total}")

        digester_kg = manure_kg * digester_fraction
        compost_kg = manure_kg * compost_fraction
        storage_kg = manure_kg * storage_fraction
        volatile_solids = digester_kg * float(value(self.ctx.calibration, "manure.volatile_solids_fraction"))
        biogas_ch4_m3 = volatile_solids * float(
            value(self.ctx.calibration, "manure.biochemical_methane_potential_m3_per_kg_vs")
        )
        storage_ch4_kg = storage_kg * float(value(self.ctx.calibration, "manure.storage_ch4_kg_per_kg_manure"))
        compost_n2o_kg = compost_kg * float(value(self.ctx.calibration, "manure.compost_n2o_kg_per_kg_manure"))
        nutrient_return_kg = manure_kg * float(value(self.ctx.calibration, "feed_crop.nutrient_return_efficiency"))

        self.ctx.publish(
            Packet(
                source=self.name,
                name="manure_packet",
                day=day,
                payload={
                    "manure_kg": require_nonnegative("manure_kg", manure_kg),
                    "digester_kg": require_nonnegative("digester_kg", digester_kg),
                    "compost_kg": require_nonnegative("compost_kg", compost_kg),
                    "storage_kg": require_nonnegative("storage_kg", storage_kg),
                    "biogas_ch4_m3": require_nonnegative("biogas_ch4_m3", biogas_ch4_m3),
                    "storage_ch4_kg": require_nonnegative("storage_ch4_kg", storage_ch4_kg),
                    "compost_n2o_kg": require_nonnegative("compost_n2o_kg", compost_n2o_kg),
                    "nutrient_return_kg": require_nonnegative("nutrient_return_kg", nutrient_return_kg),
                },
            )
        )
        self.ctx.state.setdefault("execution_order", []).append(self.name)
