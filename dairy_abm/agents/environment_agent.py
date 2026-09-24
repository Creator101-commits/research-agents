from __future__ import annotations

from datetime import date
from typing import Any

from dairy_abm.config import value
from dairy_abm.core import BaseAgent, Packet, require_nonnegative


class EnvironmentAgent(BaseAgent):
    name = "environment"

    def __init__(self, ctx) -> None:
        """Initialize environmental history used by the emissions ledger and reports."""
        super().__init__(ctx)
        ctx.state.setdefault("environment_history", [])

    def _record_stream(
        self, day: date, source: str, stream_id: str, direction: str, kg_co2e: float
    ) -> dict[str, Any]:
        """Record one validated emissions or avoided-emissions stream in the ledger."""
        amount = require_nonnegative(f"{stream_id}_kg_co2e", kg_co2e)
        payload = {
            "source": source,
            "stream_id": stream_id,
            "direction": direction,
            "kg_co2e": amount,
            "unit": "kg CO2e",
            "period": "daily",
        }
        self.ctx.record_environment_stream(
            Packet(
                source=source,
                name="environment_stream",
                day=day,
                payload=payload,
                confidence="estimated",
                stream_id=stream_id,
            )
        )
        return payload

    @staticmethod
    def _intensity(total: float, denominator: float) -> float | None:
        """Return an emissions intensity when its denominator is positive."""
        return total / denominator if denominator > 0.0 else None

    def tick(self, day: date) -> None:
        """Combine daily agent packets into emissions, circularity, and sustainability KPIs."""
        cow = self.ctx.get_packet("cow_daily_packet")
        manure = self.ctx.get_packet("manure_packet")
        energy = self.ctx.get_packet("energy_packet")
        feed = self.ctx.get_packet("feed_crop_packet")
        water = self.ctx.get_packet("water_packet")
        processor = self.ctx.get_packet("processor_packet")
        market = self.ctx.get_packet("market_price_packet")
        soil_carbon = self.ctx.get_packet("soil_carbon_packet")
        water_environment = self.ctx.get_packet("water_environment_packet")
        energy_offset_packet = self.ctx.get_packet("energy_offset_packet")

        enteric_ch4 = float(cow.payload["enteric_ch4_kg"]) if cow is not None else 0.0
        manure_ch4 = float(manure.payload["storage_ch4_kg"]) if manure is not None else 0.0
        unmanaged_ch4 = float(manure.payload.get("unmanaged_ch4_kg", 0.0)) if manure is not None else 0.0
        manure_n2o = float(manure.payload["compost_n2o_kg"]) if manure is not None else 0.0
        field_n2o_precursor = float(manure.payload.get("field_n2o_precursor_kg_n", 0.0)) if manure is not None else 0.0
        milk_l = float(cow.payload["milk_l"]) if cow is not None else 0.0
        milk_protein_kg = (
            milk_l * float(value(self.ctx.calibration, "cow.milk_protein_fraction"))
            if cow is not None
            else 0.0
        )
        nutrient_return = float(manure.payload["nutrient_return_kg"]) if manure is not None else 0.0
        recycled_n_used = float(feed.payload.get("recycled_n_used_kg", 0.0)) if feed is not None else 0.0
        energy_offset = float(energy_offset_packet.payload.get("ghg_offset_reported_kg_co2e", 0.0)) if energy_offset_packet is not None else (float(energy.payload["grid_offset_kg_co2e"]) if energy is not None else 0.0)
        fertilizer_offset = recycled_n_used * float(
            value(self.ctx.calibration, "environment.fertilizer_n_kg_co2e_per_kg_n")
        )
        recycled_water = float(water.payload.get("recycled_irrigation_l", 0.0)) if water is not None else 0.0
        soil_carbon_delta_kg = float(manure.payload.get("soil_organic_carbon_delta_kg", 0.0)) if manure is not None else 0.0
        land_soil_delta = float(soil_carbon.payload.get("soil_carbon_delta_kg_co2e") or 0.0) if soil_carbon else 0.0
        # CO2 per kg C is the molecular-mass ratio 44/12; the soil-carbon change is
        # reported separately and is not part of the blueprint net balance.
        soil_carbon_offset = max(0.0, soil_carbon_delta_kg * 44.0 / 12.0 + land_soil_delta)

        ch4_gwp = float(value(self.ctx.calibration, "environment.ch4_gwp100"))
        n2o_gwp = float(value(self.ctx.calibration, "environment.n2o_gwp100"))
        field_n2o = field_n2o_precursor * float(
            value(self.ctx.calibration, "environment.field_n2o_kg_n2o_per_kg_n")
        )
        streams = [
            self._record_stream(day, "cow", "enteric_ch4", "positive", enteric_ch4 * ch4_gwp),
            self._record_stream(day, "manure", "storage_ch4", "positive", manure_ch4 * ch4_gwp),
            self._record_stream(day, "manure", "unmanaged_ch4", "positive", unmanaged_ch4 * ch4_gwp),
            self._record_stream(day, "manure", "compost_n2o", "positive", manure_n2o * n2o_gwp),
            self._record_stream(day, "manure", "field_n2o", "positive", field_n2o * n2o_gwp),
            self._record_stream(day, "energy", "energy_grid_displacement", "avoided", energy_offset),
            self._record_stream(day, "feed_crop", "fertilizer_substitution", "avoided", fertilizer_offset),
        ]
        gross_co2e = sum(stream["kg_co2e"] for stream in streams if stream["direction"] == "positive")
        avoided_co2e = sum(stream["kg_co2e"] for stream in streams if stream["direction"] == "avoided")
        net_co2e = gross_co2e - avoided_co2e
        products_score = 1.0 if (processor is not None and processor.payload.get("enabled", False)) else 0.0
        circularity_indicators = {
            "energy_recovery_active": energy_offset > 0.0,
            "nutrient_recycling_active": recycled_n_used > 0.0,
            "water_reuse_active": recycled_water > 0.0,
            "product_loop_active": products_score > 0.0,
        }
        circularity_score = min(
            1.0,
            (
                float(value(self.ctx.calibration, "environment.circularity_weight_energy"))
                * float(circularity_indicators["energy_recovery_active"])
                + float(value(self.ctx.calibration, "environment.circularity_weight_nutrients"))
                * min(1.0, nutrient_return / 1000.0)
                + float(value(self.ctx.calibration, "environment.circularity_weight_water"))
                * float(circularity_indicators["water_reuse_active"])
                + float(value(self.ctx.calibration, "environment.circularity_weight_products")) * products_score
            ),
        )
        input_circularity = min(1.0, (recycled_n_used + recycled_water / 1000.0) / max(1.0, nutrient_return + recycled_water / 1000.0))
        output_circularity = min(1.0, (float(processor.payload.get("valorized_residual_l", 0.0)) if processor else 0.0) / max(1.0, float(processor.payload.get("whey_l", 0.0)) if processor else 1.0))
        use_count = int((1 if energy_offset else 0) + (1 if recycled_n_used else 0) + (1 if recycled_water else 0) + (1 if products_score else 0))
        cycle_count = sum(1 for active in circularity_indicators.values() if active)
        rfi_attributed_ch4_delta = 0.0
        if cow is not None:
            rfi_attributed_ch4_delta = sum(
                float(record.get("actual_dmi_kg_dm", 0.0)) - float(record.get("expected_dmi_eq2_1_kg_dm", 0.0))
                for record in cow.payload.get("cow_records", [])
            ) * 0.01
        soil_context = dict(soil_carbon.payload) if soil_carbon is not None else None
        soil_index = float(soil_context.get("soil_carbon_sequestration_index", 0.0)) if soil_context else 0.0
        tree_cover = float(soil_context.get("silvopastoral_tree_cover_fraction", 0.0)) if soil_context else 0.0
        # Blueprint 2.4 / 4.5 / 10: these composite scores are published as null
        # unless the scenario configures a scoring function.
        biodiversity_config = self.ctx.scenario.get("soil_biodiversity_index_weights")
        soil_biodiversity_index = (
            float(biodiversity_config.get("soil_index", 0.0)) * soil_index
            + float(biodiversity_config.get("tree_cover", 0.0)) * tree_cover
            if isinstance(biodiversity_config, dict) and soil_context
            else None
        )
        avoided_fraction = avoided_co2e / gross_co2e if gross_co2e > 0.0 else 0.0
        score_config = self.ctx.scenario.get("sustainability_score_weights")
        sustainability_score = (
            min(
                100.0,
                100.0 * float(score_config.get("circularity", 0.0)) * circularity_score
                + 100.0 * float(score_config.get("avoided_fraction", 0.0)) * min(1.0, avoided_fraction),
            )
            if isinstance(score_config, dict)
            else None
        )
        herrero_reference_shares = {"enteric_ch4": 0.65, "manure_ch4": 0.10, "manure_n2o": 0.29}
        gross_shares = (
            {
                "enteric_ch4": enteric_ch4 * ch4_gwp / gross_co2e,
                "manure_ch4": (manure_ch4 + unmanaged_ch4) * ch4_gwp / gross_co2e,
                "manure_n2o": (manure_n2o + field_n2o) * n2o_gwp / gross_co2e,
            }
            if gross_co2e > 0.0
            else None
        )
        carbon_credit_price = float(market.payload.get("carbon_credit_price_per_tonne_co2e", 0.0)) if market else 0.0
        if carbon_credit_price <= 0.0:
            carbon_credit_price = float(value(self.ctx.calibration, "farm_manager.carbon_credit_price_per_tonne_co2e"))
        # Credits apply to validated avoided emissions only (grid and fertilizer).
        creditable_offset = energy_offset + fertilizer_offset
        carbon_credit_value = creditable_offset / 1000.0 * carbon_credit_price
        milk_intensity = self._intensity(net_co2e, milk_l)
        protein_intensity = self._intensity(net_co2e, milk_protein_kg)
        if milk_intensity is None or protein_intensity is None:
            self.ctx.events.add(
                day,
                self.name,
                "warning",
                "environment intensity denominator is zero",
                milk_l=milk_l,
                milk_protein_kg=milk_protein_kg,
            )
        outcome_tags = ["net_negative" if net_co2e < 0.0 else "net_positive"]
        if net_co2e < 0.0:
            self.ctx.events.add(
                day,
                self.name,
                "info",
                "net carbon balance is negative",
                gross_kg_co2e=gross_co2e,
                avoided_kg_co2e=avoided_co2e,
            )
        kpi_leap_tags = {
            "gross_kg_co2e": "result",
            "net_kg_co2e": "result",
            "kg_co2e_per_l_milk": "result",
            "kg_co2e_per_kg_milk_protein": "result",
            "carbon_credit_value": "outcome",
            "ICirc": "practice",
            "OCirc": "practice",
            "use_count": "result",
            "cycle_count": "outcome",
        }
        payload = {
            "enteric_ch4_kg": require_nonnegative("enteric_ch4_kg", enteric_ch4),
            "manure_ch4_kg": require_nonnegative("manure_ch4_kg", manure_ch4),
            "unmanaged_ch4_kg": require_nonnegative("unmanaged_ch4_kg", unmanaged_ch4),
            "manure_n2o_kg": require_nonnegative("manure_n2o_kg", manure_n2o),
            "field_n2o_kg": require_nonnegative("field_n2o_kg", field_n2o),
            "gross_kg_co2e": require_nonnegative("gross_kg_co2e", gross_co2e),
            "energy_offset_kg_co2e": require_nonnegative("energy_offset_kg_co2e", energy_offset),
            "fertilizer_offset_kg_co2e": require_nonnegative("fertilizer_offset_kg_co2e", fertilizer_offset),
            "soil_carbon_offset_kg_co2e": soil_carbon_offset,
            "soil_carbon_delta_kg": soil_carbon_delta_kg,
            "soil_organic_carbon_pct": float(self.ctx.state.get("soil_organic_carbon", 0.0)),
            "synthetic_fertilizer_saved_kg": recycled_n_used,
            "avoided_kg_co2e": require_nonnegative("avoided_kg_co2e", avoided_co2e),
            "net_kg_co2e": net_co2e,
            "milk_l": require_nonnegative("milk_l", milk_l),
            "milk_protein_kg": require_nonnegative("milk_protein_kg", milk_protein_kg),
            "kg_co2e_per_l_milk": milk_intensity,
            "gross_kg_co2e_per_l_milk": self._intensity(gross_co2e, milk_l),
            "herrero_reference_shares": herrero_reference_shares,
            "gross_stream_shares": gross_shares,
            "creditable_offset_kg_co2e": creditable_offset,
            "kg_co2e_per_kg_milk_protein": protein_intensity,
            "circularity_score": circularity_score,
            "circularity_indicators": circularity_indicators,
            "ICirc": input_circularity,
            "OCirc": output_circularity,
            "NUE": cow.payload.get("nitrogen_use_efficiency") if cow else None,
            "use_count": use_count,
            "cycle_count": cycle_count,
            "rfi_attributed_ch4_delta_kg": rfi_attributed_ch4_delta,
            "soil_biodiversity_index": soil_biodiversity_index,
            "sustainability_score_0_100": sustainability_score,
            "carbon_credit_value": carbon_credit_value,
            "carbon_credit_price_per_tonne_co2e": carbon_credit_price,
            "kpi_leap_tags": kpi_leap_tags,
            "result_tags": ["gross_emissions", "avoided_emissions", "intensity", "circularity"],
            "outcome_tags": outcome_tags,
            "environmental_streams": streams,
            "soil_carbon_context": soil_context,
            "water_environment": dict(water_environment.payload) if water_environment else None,
            "raw_offset_packet": {"energy_grid_kg_co2e": energy_offset, "fertilizer_kg_co2e": fertilizer_offset, "soil_carbon_kg_co2e": soil_carbon_offset},
            "final_offset_packet": {"avoided_kg_co2e": avoided_co2e, "confidence": "estimated", "pending": False},
        }
        self.ctx.state["environment_history"].append({"day": day.isoformat(), **payload})
        payload["cumulative_kpis"] = self._cumulative(payload)
        self.ctx.publish(Packet(source=self.name, name="environment_packet", day=day, payload=payload))
        self.ctx.state.setdefault("execution_order", []).append(self.name)

    def _cumulative(self, payload: dict[str, Any]) -> dict[str, float | None]:
        """Running cumulative KPIs (same definitions as _aggregate) updated in O(1) per day."""
        state = self.ctx.state.setdefault(
            "environment_cumulative",
            {"gross": 0.0, "avoided": 0.0, "net": 0.0, "milk": 0.0, "protein": 0.0, "water": 0.0, "score_sum": 0.0, "score_n": 0,
             "circularity_sum": 0.0, "days": 0, "soil_c": 0.0, "fert_saved": 0.0},
        )
        state["days"] += 1
        state["circularity_sum"] += float(payload.get("circularity_score", 0.0))
        state["soil_c"] += float(payload.get("soil_carbon_delta_kg", 0.0))
        state["fert_saved"] += float(payload.get("synthetic_fertilizer_saved_kg", 0.0))
        state["gross"] += float(payload["gross_kg_co2e"])
        state["avoided"] += float(payload["avoided_kg_co2e"])
        state["net"] += float(payload["net_kg_co2e"])
        state["milk"] += float(payload["milk_l"])
        state["protein"] += float(payload["milk_protein_kg"])
        water_env = payload.get("water_environment")
        if isinstance(water_env, dict):
            state["water"] += float(water_env.get("net_freshwater_use_l", 0.0))
        if payload.get("sustainability_score_0_100") is not None:
            state["score_sum"] += float(payload["sustainability_score_0_100"])
            state["score_n"] += 1
        return {
            "gross_kg_co2e": state["gross"],
            "avoided_kg_co2e": state["avoided"],
            "net_kg_co2e": state["net"],
            "milk_l": state["milk"],
            "milk_protein_kg": state["protein"],
            "kg_co2e_per_l_milk": self._intensity(state["net"], state["milk"]),
            "kg_co2e_per_kg_milk_protein": self._intensity(state["net"], state["protein"]),
            "water_l": state["water"],
            "mean_sustainability_score_0_100": state["score_sum"] / state["score_n"] if state["score_n"] else None,
            "mean_circularity_score": state["circularity_sum"] / state["days"],
            "soil_carbon_delta_kg": state["soil_c"],
            "synthetic_fertilizer_saved_kg": state["fert_saved"],
        }

    def _aggregate(self, rows: list[dict[str, Any]]) -> dict[str, float | None]:
        """Aggregate environmental history into cumulative totals and intensities."""
        gross = sum(float(row["gross_kg_co2e"]) for row in rows)
        avoided = sum(float(row["avoided_kg_co2e"]) for row in rows)
        net = sum(float(row["net_kg_co2e"]) for row in rows)
        milk = sum(float(row["milk_l"]) for row in rows)
        protein = sum(float(row["milk_protein_kg"]) for row in rows)
        return {
            "gross_kg_co2e": gross,
            "avoided_kg_co2e": avoided,
            "net_kg_co2e": net,
            "milk_l": milk,
            "milk_protein_kg": protein,
            "kg_co2e_per_l_milk": self._intensity(net, milk),
            "kg_co2e_per_kg_milk_protein": self._intensity(net, protein),
            "water_l": sum(float(row.get("water_environment", {}).get("net_freshwater_use_l", 0.0)) for row in rows if isinstance(row.get("water_environment"), dict)),
            "mean_sustainability_score_0_100": (
                sum(float(row["sustainability_score_0_100"]) for row in scored) / len(scored)
                if (scored := [row for row in rows if row.get("sustainability_score_0_100") is not None])
                else None
            ),
            "mean_circularity_score": sum(float(row.get("circularity_score", 0.0)) for row in rows) / len(rows),
            "soil_carbon_delta_kg": sum(float(row.get("soil_carbon_delta_kg", 0.0)) for row in rows),
            "synthetic_fertilizer_saved_kg": sum(float(row.get("synthetic_fertilizer_saved_kg", 0.0)) for row in rows),
        }

    def monthly(self, day: date) -> None:
        """Publish the current month's aggregated environmental report."""
        month = day.strftime("%Y-%m")
        rows = [row for row in self.ctx.state["environment_history"] if row["day"].startswith(month)]
        if not rows:
            return
        report = {"month": month, "report": "environment", **self._aggregate(rows)}
        self.ctx.monthly_records.append(report)
        self.ctx.publish(
            Packet(source=self.name, name="environment_report_packet", day=day, payload=report, period="monthly")
        )
