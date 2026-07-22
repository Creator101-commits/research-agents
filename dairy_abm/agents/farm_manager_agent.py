from __future__ import annotations

from datetime import date

from dairy_abm.config import value
from dairy_abm.core import BaseAgent, Packet, require_nonnegative


class FarmManagerAgent(BaseAgent):
    name = "farm_manager"

    def tick(self, day: date) -> None:
        cow = self.ctx.get_packet("cow_daily_packet")
        feed = self.ctx.get_packet("feed_crop_packet")
        water = self.ctx.get_packet("water_packet")
        energy = self.ctx.get_packet("energy_packet")
        disease = self.ctx.get_packet("disease_state_packet")
        environment = self.ctx.get_packet("environment_packet")
        cow_count = int(cow.payload["cow_count"]) if cow is not None else 0
        milk_revenue = float(cow.payload["milk_revenue"]) if cow is not None else 0.0
        feed_cost = float(feed.payload["feed_cost"]) if feed is not None else 0.0
        water_cost = float(water.payload["water_cost"]) if water is not None else 0.0
        energy_value = float(energy.payload["energy_value"]) if energy is not None else 0.0
        treatment_cost = float(disease.payload["treatment_cost"]) if disease is not None else 0.0
        labor_cost = cow_count * float(value(self.ctx.calibration, "farm_manager.labor_cost_per_cow_day"))
        fixed_cost = float(value(self.ctx.calibration, "farm_manager.fixed_cost_per_day"))
        carbon_credit_value = (
            float(environment.payload["energy_offset_kg_co2e"])
            / 1000.0
            * float(value(self.ctx.calibration, "farm_manager.carbon_credit_price_per_tonne_co2e"))
            if environment is not None
            else 0.0
        )
        total_revenue = milk_revenue + energy_value + carbon_credit_value
        total_cost = feed_cost + water_cost + treatment_cost + labor_cost + fixed_cost
        profit = total_revenue - total_cost
        self.ctx.publish(
            Packet(
                source=self.name,
                name="manager_packet",
                day=day,
                payload={
                    "milk_revenue": require_nonnegative("milk_revenue", milk_revenue),
                    "energy_value": require_nonnegative("energy_value", energy_value),
                    "carbon_credit_value": require_nonnegative("carbon_credit_value", carbon_credit_value),
                    "feed_cost": require_nonnegative("feed_cost", feed_cost),
                    "water_cost": require_nonnegative("water_cost", water_cost),
                    "treatment_cost": require_nonnegative("treatment_cost", treatment_cost),
                    "labor_cost": require_nonnegative("labor_cost", labor_cost),
                    "fixed_cost": require_nonnegative("fixed_cost", fixed_cost),
                    "total_revenue": require_nonnegative("total_revenue", total_revenue),
                    "total_cost": require_nonnegative("total_cost", total_cost),
                    "profit": profit,
                    "recommendation": self._recommendation(profit, feed_cost, treatment_cost),
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
                "report": "farm_manager",
                "milk_revenue": sum(float(row.get("milk_revenue", 0.0)) for row in rows),
                "total_revenue": sum(float(row.get("total_revenue", 0.0)) for row in rows),
                "total_cost": sum(float(row.get("total_cost", 0.0)) for row in rows),
                "profit": sum(float(row.get("profit", 0.0)) for row in rows),
            }
        )

    @staticmethod
    def _recommendation(profit: float, feed_cost: float, treatment_cost: float) -> str:
        if treatment_cost > feed_cost:
            return "review_health_protocol"
        if profit < 0:
            return "review_cost_structure"
        return "maintain_current_policy"
