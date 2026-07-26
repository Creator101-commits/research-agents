from __future__ import annotations

from datetime import date
from typing import Any

from dairy_abm.config import value
from dairy_abm.core import BaseAgent, ConfigError, Packet, require_fraction, require_nonnegative


class LandManagementAgent(BaseAgent):
    name = "land"

    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        ctx.state.setdefault("pasture_paddock_condition", {})

    def _seasonal_availability(self, day: date) -> tuple[float, str]:
        rules = self.ctx.scenario.get("land_seasonal_availability")
        if rules is None:
            return 1.0, "not_configured"
        if not isinstance(rules, dict):
            raise ConfigError("land_seasonal_availability must be a month-to-fraction mapping")
        raw_fraction: Any = rules.get(str(day.month), rules.get(f"{day.month:02d}", 1.0))
        return require_fraction("land seasonal availability", float(raw_fraction)), "scenario"

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
        allocation = self.ctx.scenario.get("land_allocation", {})
        if isinstance(allocation, dict):
            requested_crop_share = float(allocation.get("cropland_share", cropland_ha / max(0.001, cropland_ha + pasture_ha)))
            requested_crop_share = min(1.0, max(0.0, requested_crop_share))
            total_ha = cropland_ha + pasture_ha
            cropland_ha = total_ha * requested_crop_share
            pasture_ha = total_ha - cropland_ha
        availability_fraction, availability_source = self._seasonal_availability(day)
        cropland_available_ha = cropland_ha * availability_fraction
        pasture_available_ha = pasture_ha * availability_fraction
        grazing_enabled = bool(self.ctx.scenario.get("land_grazing_enabled", False))
        rotation_days = max(1, int(self.ctx.scenario.get("rotational_grazing_rotation_days", 1)))
        paddock_count = max(1, int(self.ctx.scenario.get("rotational_grazing_paddocks", 1)))
        paddock_phase = (day.toordinal() // rotation_days) % paddock_count
        conditions: dict[str, float] = self.ctx.state["pasture_paddock_condition"]
        recovery_fraction = min(1.0, max(0.0, float(self.ctx.scenario.get("pasture_daily_recovery_fraction", 0.03))))
        utilization_fraction = min(1.0, max(0.0, float(self.ctx.scenario.get("pasture_grazing_utilization_fraction", 0.08))))
        for index in range(paddock_count):
            key = str(index)
            prior = min(1.0, max(0.0, float(conditions.get(key, 1.0))))
            conditions[key] = max(0.0, prior * (1.0 - utilization_fraction)) if grazing_enabled and index == paddock_phase else min(1.0, prior + recovery_fraction)
        active_paddock_condition = conditions[str(paddock_phase)]
        grazable_pasture_ha = pasture_available_ha * active_paddock_condition / paddock_count
        soil_carbon_delta = (
            pasture_available_ha * float(self.ctx.scenario.get("pasture_soil_carbon_kg_co2e_per_ha_day", 0.0))
            + tree_cover * (cropland_available_ha + pasture_available_ha) * float(self.ctx.scenario.get("tree_soil_carbon_kg_co2e_per_ha_day", 0.0))
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
                    "cropland_available_ha": cropland_available_ha,
                    "pasture_available_ha": pasture_available_ha,
                    "grazable_pasture_ha": grazable_pasture_ha,
                    "seasonal_availability_fraction": availability_fraction,
                    "seasonal_availability_source": availability_source,
                    "silvopastoral_tree_cover_fraction": tree_cover,
                    "soil_carbon_sequestration_index": soil_index,
                    "land_allocation": {"cropland_share": cropland_ha / max(0.001, cropland_ha + pasture_ha), "pasture_share": pasture_ha / max(0.001, cropland_ha + pasture_ha)},
                },
                confidence="scenario",
            )
        )
        self.ctx.publish(
            Packet(
                source=self.name,
                name="grazing_access_packet",
                day=day,
                payload={
                    "enabled": grazing_enabled,
                    "pasture_available_ha": pasture_available_ha,
                    "grazable_pasture_ha": grazable_pasture_ha,
                    "seasonal_availability_fraction": availability_fraction,
                    "rotational_grazing_active": grazing_enabled and int(self.ctx.scenario.get("rotational_grazing_paddocks", 1)) > 1,
                    "active_paddock": paddock_phase,
                    "active_paddock_condition": active_paddock_condition,
                    "paddock_conditions": dict(conditions),
                },
                quality="inactive" if not grazing_enabled else "scenario",
                confidence="scenario",
            )
        )
        self.ctx.publish(
            Packet(
                source=self.name,
                name="soil_carbon_packet",
                day=day,
                payload={
                    "soil_carbon_sequestration_index": soil_index,
                    "silvopastoral_tree_cover_fraction": tree_cover,
                    "seasonal_availability_fraction": availability_fraction,
                    "soil_carbon_delta_kg_co2e": soil_carbon_delta,
                },
                quality="context_only",
                confidence="scenario",
            )
        )
        self.ctx.state["land_owner"] = "land"
        self.ctx.state.setdefault("execution_order", []).append(self.name)
