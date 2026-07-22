from __future__ import annotations

from datetime import date

from dairy_abm.config import value
from dairy_abm.core import BaseAgent, Packet, require_fraction, require_nonnegative


class LandManagementAgent(BaseAgent):
    name = "land"

    def tick(self, day: date) -> None:
        cropland_ha = require_nonnegative(
            "land.cropland_ha",
            float(self.ctx.scenario.get("land_cropland_ha", value(self.ctx.calibration, "land.cropland_ha"))),
        )
        pasture_ha = require_nonnegative(
            "land.pasture_ha",
            float(self.ctx.scenario.get("land_pasture_ha", value(self.ctx.calibration, "land.pasture_ha"))),
        )
        tree_cover = require_fraction(
            "land.silvopastoral_tree_cover_fraction",
            float(
                self.ctx.scenario.get(
                    "land_silvopastoral_tree_cover_fraction",
                    value(self.ctx.calibration, "land.silvopastoral_tree_cover_fraction"),
                )
            ),
        )
        soil_index = require_nonnegative(
            "land.soil_carbon_sequestration_index",
            float(
                self.ctx.scenario.get(
                    "soil_carbon_sequestration_index",
                    value(self.ctx.calibration, "land.soil_carbon_sequestration_index"),
                )
            ),
        )
        self.ctx.publish(
            Packet(
                source=self.name,
                name="land_packet",
                day=day,
                payload={
                    "land_owner": "land",
                    "cropland_ha": cropland_ha,
                    "pasture_ha": pasture_ha,
                    "silvopastoral_tree_cover_fraction": tree_cover,
                    "soil_carbon_sequestration_index": soil_index,
                },
            )
        )
        self.ctx.state["land_owner"] = "land"
        self.ctx.state.setdefault("execution_order", []).append(self.name)
