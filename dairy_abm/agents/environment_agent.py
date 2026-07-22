from __future__ import annotations

from datetime import date

from dairy_abm.config import value
from dairy_abm.core import BaseAgent, Packet, require_nonnegative


class EnvironmentAgent(BaseAgent):
    name = "environment"

    def tick(self, day: date) -> None:
        cow = self.ctx.get_packet("cow_daily_packet")
        manure = self.ctx.get_packet("manure_packet")
        energy = self.ctx.get_packet("energy_packet")
        water = self.ctx.get_packet("water_packet")
        enteric_ch4 = float(cow.payload["enteric_ch4_kg"]) if cow is not None else 0.0
        manure_ch4 = float(manure.payload["storage_ch4_kg"]) if manure is not None else 0.0
        manure_n2o = float(manure.payload["compost_n2o_kg"]) if manure is not None else 0.0
        gross_co2e = (
            (enteric_ch4 + manure_ch4) * float(value(self.ctx.calibration, "environment.ch4_gwp100"))
            + manure_n2o * float(value(self.ctx.calibration, "environment.n2o_gwp100"))
        )
        energy_offset = float(energy.payload["grid_offset_kg_co2e"]) if energy is not None else 0.0
        net_co2e = max(0.0, gross_co2e - energy_offset)
        nutrient_return = float(manure.payload["nutrient_return_kg"]) if manure is not None else 0.0
        net_water = float(water.payload["net_water_l"]) if water is not None else 0.0
        processor = self.ctx.get_packet("processor_packet")
        products_score = 1.0 if (processor is not None and processor.payload.get("enabled", False)) else 0.0
        circularity_score = min(
            1.0,
            (
                float(value(self.ctx.calibration, "environment.circularity_weight_energy")) * (1.0 if energy_offset > 0 else 0.0)
                + float(value(self.ctx.calibration, "environment.circularity_weight_nutrients"))
                * min(1.0, nutrient_return / 1000.0)
                + float(value(self.ctx.calibration, "environment.circularity_weight_water"))
                * (1.0 if net_water > 0 else 0.0)
                + float(value(self.ctx.calibration, "environment.circularity_weight_products"))
                * products_score
            ),
        )
        self.ctx.publish(
            Packet(
                source=self.name,
                name="environment_packet",
                day=day,
                payload={
                    "enteric_ch4_kg": require_nonnegative("enteric_ch4_kg", enteric_ch4),
                    "manure_ch4_kg": require_nonnegative("manure_ch4_kg", manure_ch4),
                    "manure_n2o_kg": require_nonnegative("manure_n2o_kg", manure_n2o),
                    "gross_kg_co2e": require_nonnegative("gross_kg_co2e", gross_co2e),
                    "energy_offset_kg_co2e": require_nonnegative("energy_offset_kg_co2e", energy_offset),
                    "net_kg_co2e": require_nonnegative("net_kg_co2e", net_co2e),
                    "circularity_score": circularity_score,
                },
            )
        )
        self.ctx.state.setdefault("execution_order", []).append(self.name)

    def monthly(self, day: date) -> None:
        if not self.ctx.daily_records:
            return
        month = day.strftime("%Y-%m")
        rows = [row for row in self.ctx.daily_records if row["day"].startswith(month)]
        self.ctx.monthly_records.append(
            {
                "month": month,
                "report": "environment",
                "milk_l": sum(float(row.get("milk_l", 0.0)) for row in rows),
                "net_kg_co2e": sum(float(row.get("net_kg_co2e", 0.0)) for row in rows),
                "net_water_l": sum(float(row.get("net_water_l", 0.0)) for row in rows),
            }
        )
