from __future__ import annotations

from datetime import date

from dairy_abm.config import value
from dairy_abm.core import BaseAgent, Packet, require_fraction


class GeneticsAgent(BaseAgent):
    name = "genetics"

    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        ctx.state.setdefault("genetic_trend", [])

    def annual(self, day: date) -> None:
        cows = self.ctx.state.get("cows", [])
        if not cows:
            herd_mean_rfi = 0.0
            selected = []
        else:
            herd_mean_rfi = sum(float(cow.get("feed_efficiency_trait", 1.0)) for cow in cows) / len(cows)
            selection_intensity = require_fraction(
                "genetics.selection_intensity",
                float(value(self.ctx.calibration, "genetics.selection_intensity")),
            )
            selected_count = max(1, int(round(len(cows) * selection_intensity)))
            selected = sorted(cows, key=lambda cow: float(cow.get("feed_efficiency_trait", 1.0)))[:selected_count]
            annual_gain = float(value(self.ctx.calibration, "genetics.annual_rfi_gain_fraction"))
            for cow in selected:
                cow["feed_efficiency_trait"] = max(0.5, float(cow.get("feed_efficiency_trait", 1.0)) * (1.0 - annual_gain))

        trend = {
            "year": day.year,
            "herd_mean_rfi_fat": herd_mean_rfi,
            "selected_parent_count": len(selected),
            "minimum_intake_record_days": int(value(self.ctx.calibration, "genetics.minimum_intake_record_days")),
            "cross_diet_repeatability_modifier": float(
                value(self.ctx.calibration, "genetics.cross_diet_repeatability_modifier")
            ),
        }
        self.ctx.state["genetic_trend"].append(trend)
        self.ctx.publish(
            Packet(
                source=self.name,
                name="genetics_packet",
                day=day,
                payload={
                    **trend,
                    "breeding_recommendation": "select_low_rfi_candidates" if selected else "no_candidates",
                },
            )
        )
        self.ctx.annual_records.append({"year": day.year, "report": "genetics", **trend})
