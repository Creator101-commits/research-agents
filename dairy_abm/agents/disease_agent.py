from __future__ import annotations

from datetime import date

from dairy_abm.config import value
from dairy_abm.core import BaseAgent, Packet, require_fraction


class DiseaseAgent(BaseAgent):
    name = "disease"

    def tick(self, day: date) -> None:
        cows = self.ctx.state.get("cows", [])
        mastitis_probability = require_fraction(
            "disease.mastitis_daily_probability",
            float(value(self.ctx.calibration, "disease.mastitis_daily_probability")),
        )
        lameness_probability = require_fraction(
            "disease.lameness_daily_probability",
            float(value(self.ctx.calibration, "disease.lameness_daily_probability")),
        )
        recovery_probability = require_fraction(
            "disease.recovery_daily_probability",
            float(value(self.ctx.calibration, "disease.recovery_daily_probability")),
        )
        new_cases = 0
        recovered = 0
        active_cases = 0

        for cow in cows:
            if cow.get("health_status") != "healthy":
                if self.ctx.rng.random() < recovery_probability:
                    cow["health_status"] = "healthy"
                    cow["disease"] = None
                    recovered += 1
                else:
                    active_cases += 1
                continue
            draw = self.ctx.rng.random()
            if draw < mastitis_probability:
                cow["health_status"] = "sick"
                cow["disease"] = "mastitis"
                new_cases += 1
                active_cases += 1
            elif draw < mastitis_probability + lameness_probability:
                cow["health_status"] = "sick"
                cow["disease"] = "lameness"
                new_cases += 1
                active_cases += 1

        self.ctx.publish(
            Packet(
                source=self.name,
                name="disease_state_packet",
                day=day,
                payload={
                    "new_cases": new_cases,
                    "recovered": recovered,
                    "active_cases": active_cases,
                    "milk_loss_sick_fraction": float(value(self.ctx.calibration, "disease.milk_loss_sick_fraction")),
                    "treatment_cost": new_cases * float(value(self.ctx.calibration, "disease.treatment_cost_per_case")),
                },
            )
        )
        self.ctx.state.setdefault("execution_order", []).append(self.name)
