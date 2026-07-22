from __future__ import annotations

from datetime import date

from dairy_abm.config import value
from dairy_abm.core import BaseAgent, Packet, require_fraction


class SensorsAgent(BaseAgent):
    name = "sensors"

    def tick(self, day: date) -> None:
        cows = self.ctx.state.get("cows", [])
        missing_probability = require_fraction(
            "sensors.missing_reading_probability",
            float(value(self.ctx.calibration, "sensors.missing_reading_probability")),
        )
        alert_sensitivity = float(value(self.ctx.calibration, "sensors.alert_sensitivity"))
        missing = 0
        alerts: list[dict[str, object]] = []
        for cow in cows:
            if self.ctx.rng.random() < missing_probability:
                missing += 1
                continue
            if cow.get("health_status") != "healthy" and self.ctx.rng.random() < alert_sensitivity:
                alerts.append({"cow_id": cow["id"], "type": "health", "severity": "warning"})

        quality = "ok" if missing == 0 else "partial"
        self.ctx.publish(
            Packet(
                source=self.name,
                name="sensor_observation_packet",
                day=day,
                quality=quality,
                payload={
                    "observed_cows": len(cows) - missing,
                    "missing_readings": missing,
                    "health_alerts": alerts,
                    "milk_noise_fraction": float(value(self.ctx.calibration, "sensors.milk_sensor_noise_fraction")),
                    "dmi_noise_fraction": float(value(self.ctx.calibration, "sensors.dmi_sensor_noise_fraction")),
                },
            )
        )
        self.ctx.state.setdefault("execution_order", []).append(self.name)
