from __future__ import annotations

from datetime import date
from math import exp, pi, sqrt
from statistics import NormalDist

from dairy_abm.config import value
from dairy_abm.core import BaseAgent, ConfigError, Packet, require_fraction


class GeneticsAgent(BaseAgent):
    name = "genetics"
    _TRAITS = ("milk_yield", "feed_efficiency", "fertility", "health", "survivability")
    _INHERITED_TRAITS = (
        "milk_yield", "butterfat_ebv", "protein_ebv", "rfi_fat_ebv",
        "body_weight_composite", "livability_score", "fertility_score",
        "health_composite_score", "calving_ease_score",
    )
    _SCENARIO_TEMPLATES = {
        "NM": {"milk_yield": 0.25, "butterfat_ebv": 0.16, "protein_ebv": 0.16, "rfi_fat_ebv": 0.14, "body_weight_composite": 0.06, "livability_score": 0.08, "fertility_score": 0.07, "health_composite_score": 0.06, "calving_ease_score": 0.02},
        "CM": {"milk_yield": 0.31, "butterfat_ebv": 0.19, "protein_ebv": 0.16, "rfi_fat_ebv": 0.11, "body_weight_composite": 0.05, "livability_score": 0.07, "fertility_score": 0.05, "health_composite_score": 0.04, "calving_ease_score": 0.02},
        "FM": {"milk_yield": 0.20, "butterfat_ebv": 0.14, "protein_ebv": 0.14, "rfi_fat_ebv": 0.16, "body_weight_composite": 0.08, "livability_score": 0.10, "fertility_score": 0.09, "health_composite_score": 0.07, "calving_ease_score": 0.02},
        "GM": {"milk_yield": 0.18, "butterfat_ebv": 0.12, "protein_ebv": 0.12, "rfi_fat_ebv": 0.17, "body_weight_composite": 0.08, "livability_score": 0.10, "fertility_score": 0.11, "health_composite_score": 0.09, "calving_ease_score": 0.03},
    }

    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        ctx.state.setdefault("genetic_trend", [])
        ctx.state.setdefault("herd_nm_trend", [])

    def record_daily_intake(self, day: date) -> None:
        cow_packet = self.ctx.get_packet("cow_daily_packet")
        if cow_packet is None:
            return
        feed_packet = self.ctx.get_packet("feed_crop_packet")
        cross_diet_modifier = float(value(self.ctx.calibration, "genetics.cross_diet_repeatability_modifier"))
        ration_me = float(feed_packet.payload.get("ration_me_mj_per_kg_dm", 0.0)) if feed_packet else 0.0
        ration_ndf = float(feed_packet.payload.get("ration_ndf_fraction", 0.0)) if feed_packet else 0.0
        last_me = float(self.ctx.state.setdefault("last_ration_me_mj", ration_me))
        last_ndf = float(self.ctx.state.setdefault("last_ration_ndf_fraction", ration_ndf))
        diet_changed = (
            abs(ration_me - last_me) > 0.5 if last_me > 0.0 else False
        ) or (
            abs(ration_ndf - last_ndf) > 0.03 if last_ndf > 0.0 else False
        )
        if diet_changed:
            self.ctx.state["last_diet_change_day"] = day.isoformat()
            self.ctx.state["diet_change_recorded"] = True
            self.ctx.state["stable_diet_days"] = 0
        else:
            self.ctx.state["stable_diet_days"] = int(self.ctx.state.get("stable_diet_days", 0)) + 1
        if int(self.ctx.state.get("stable_diet_days", 0)) >= int(
            value(self.ctx.calibration, "genetics.minimum_intake_record_days")
        ):
            self.ctx.state["diet_change_recorded"] = False
        self.ctx.state["last_ration_me_mj"] = ration_me
        self.ctx.state["last_ration_ndf_fraction"] = ration_ndf

        minimum_days = int(value(self.ctx.calibration, "genetics.minimum_intake_record_days"))
        records = {record["id"]: record for record in cow_packet.payload["cow_records"]}
        for cow in self.ctx.state.get("cows", []):
            cow.setdefault("recorded_dmi_days", 0)
            cow.setdefault("candidate_record_complete", False)
            cow.setdefault("dmi_record_series", [])
            record = records.get(cow["id"])
            observed = record.get("observed_dmi_kg") if record else None
            if cow.get("alive", True) and record is not None and isinstance(observed, (int, float)):
                cow["recorded_dmi_days"] += 1
                expected = float(record.get("expected_dmi_eq2_1_kg_dm", cow.get("expected_dmi_kg", 0.0)))
                rfi = float(observed) - expected
                cow["dmi_record_series"].append({"day": day.isoformat(), "observed_dmi_kg": float(observed), "expected_dmi_kg": expected, "rfi_fat": rfi})
                cow["rfi_fat_phenotype"] = sum(item["rfi_fat"] for item in cow["dmi_record_series"]) / len(cow["dmi_record_series"])
            elif cow.get("alive", True):
                # RFI eligibility requires a contiguous observed record window.
                cow["recorded_dmi_days"] = 0
            cow["candidate_record_complete"] = cow["recorded_dmi_days"] >= minimum_days
            cow["ebv_confidence"] = min(1.0, cow["recorded_dmi_days"] / minimum_days)
            if bool(self.ctx.state.get("diet_change_recorded", False)):
                cow["ebv_confidence"] *= cross_diet_modifier

    def _selection_weights(
        self,
        feed_cost_signal: float | None,
        active_disease_cases: int,
        cull_cow_price: float | None,
    ) -> dict[str, float]:
        weights = {
            trait: float(value(self.ctx.calibration, f"genetics.trait_weights.{trait}"))
            for trait in self._TRAITS
        }
        if feed_cost_signal is not None and feed_cost_signal > float(
            value(self.ctx.calibration, "genetics.feed_cost_stress_threshold_per_kg_dm")
        ):
            weights["feed_efficiency"] *= float(
                value(
                    self.ctx.calibration,
                    "genetics.feed_efficiency_weight_multiplier_under_feed_stress",
                )
            )
        if active_disease_cases >= int(value(self.ctx.calibration, "genetics.disease_frequency_stress_threshold")):
            weights["health"] *= float(
                value(self.ctx.calibration, "genetics.health_weight_multiplier_under_disease_stress")
            )
        if cull_cow_price is not None and cull_cow_price < float(
            value(self.ctx.calibration, "genetics.low_cull_price_threshold")
        ):
            weights["survivability"] *= float(
                value(
                    self.ctx.calibration,
                    "genetics.survivability_weight_multiplier_under_low_cull_price",
                )
            )
        total = sum(weights.values())
        if total <= 0.0:
            raise ConfigError("genetics trait weights must have a positive total")
        return {trait: weight / total for trait, weight in weights.items()}

    def _selection_intensity_i(self, selection_fraction: float) -> float:
        if selection_fraction >= 1.0:
            return 0.0
        z_score = NormalDist().inv_cdf(1.0 - selection_fraction)
        normal_density = exp(-(z_score**2) / 2.0) / sqrt(2.0 * pi)
        return normal_density / selection_fraction

    def _trait_merit(self, cow: dict[str, object], weights: dict[str, float]) -> float:
        trait_vector = cow["trait_vector"]
        if not isinstance(trait_vector, dict):
            raise ConfigError(f"cow {cow['id']} has an invalid trait vector")
        return sum(weights[trait] * float(trait_vector.get(trait, 0.0)) for trait in self._TRAITS)

    @staticmethod
    def _full_merit(cow: dict[str, object], weights: dict[str, float]) -> float:
        traits = cow.get("trait_vector", {})
        if not isinstance(traits, dict):
            return 0.0
        score = 0.0
        for trait, weight in weights.items():
            trait_value = float(traits.get(trait, 1.0 if trait != "rfi_fat_ebv" else 0.0))
            # Lower RFI improves the breeding index; all other EBVs increase it.
            score += weight * (-trait_value if trait == "rfi_fat_ebv" else trait_value)
        return score

    def _offspring_trait_vector(self, selected: list[dict[str, object]]) -> tuple[list[str], dict[str, float] | None, dict[str, float] | None]:
        if not selected:
            return [], None, None
        dam = selected[0]
        sire = selected[1] if len(selected) > 1 else selected[0]
        dam_traits = dam["trait_vector"]
        sire_traits = sire["trait_vector"]
        if not isinstance(dam_traits, dict) or not isinstance(sire_traits, dict):
            raise ConfigError("selected parent has an invalid trait vector")
        variation_fraction = float(value(self.ctx.calibration, "genetics.offspring_trait_variation_fraction"))
        offspring = {}
        dam_markers = dam.get("genome_markers", {})
        sire_markers = sire.get("genome_markers", {})
        offspring_markers: dict[str, float] = {}
        for trait in self._INHERITED_TRAITS:
            parental_mean = (float(dam_traits.get(trait, 0.0)) + float(sire_traits.get(trait, 0.0))) / 2.0
            variation = self.ctx.rng.gauss(0.0, abs(parental_mean) * variation_fraction) if variation_fraction else 0.0
            offspring[trait] = max(0.0, parental_mean + variation)
            if isinstance(dam_markers, dict) and isinstance(sire_markers, dict):
                inherited_marker = float(dam_markers.get(trait, offspring[trait])) if self.ctx.rng.random() < 0.5 else float(sire_markers.get(trait, offspring[trait]))
                offspring_markers[trait] = inherited_marker + self.ctx.rng.gauss(0.0, abs(inherited_marker) * variation_fraction)
        return [str(dam["id"]), str(sire["id"])], offspring, offspring_markers

    def annual(self, day: date) -> None:
        cows = self.ctx.state.get("cows", [])
        feed_packet = self.ctx.get_packet("feed_crop_packet")
        feed_cost_signal = (
            float(feed_packet.payload["feed_cost_per_kg_dm"]) if feed_packet is not None else None
        )
        ration_me = float(feed_packet.payload.get("ration_me_mj_per_kg_dm", 0.0)) if feed_packet else self.ctx.state.get("last_ration_me_mj", 0.0)
        ration_ndf = float(feed_packet.payload.get("ration_ndf_fraction", 0.0)) if feed_packet else self.ctx.state.get("last_ration_ndf_fraction", 0.0)
        disease_packet = self.ctx.get_packet("disease_state_packet")
        active_disease_cases = int(disease_packet.payload["active_cases"]) if disease_packet is not None else 0
        market_packet = self.ctx.get_packet("market_price_packet")
        cull_cow_price = (
            float(market_packet.payload["cull_cow_price"]) if market_packet is not None else None
        )
        eligible_cows = [cow for cow in cows if cow.get("candidate_record_complete", False)]
        selection_weights = self._selection_weights(
            feed_cost_signal,
            active_disease_cases,
            cull_cow_price,
        )
        policy = self.ctx.state["policy"]
        market_scenario = str(policy.get("market_scenario", "NM")).upper()
        user_breeding_priority = str(policy.get("user_breeding_priority", "profit"))
        if market_scenario not in self._SCENARIO_TEMPLATES:
            raise ConfigError(f"unsupported market scenario {market_scenario!r}; expected NM, CM, FM, or GM")
        full_weights = dict(self._SCENARIO_TEMPLATES[market_scenario])
        grazing_packet = self.ctx.get_packet("grazing_access_packet")
        grazing_context_active = bool(grazing_packet.payload.get("enabled", False)) if grazing_packet else False
        if market_scenario == "GM":
            selection_weights["fertility"] *= 1.1
            full_weights["fertility_score"] *= 1.1
        if user_breeding_priority == "sustainability":
            selection_weights["feed_efficiency"] *= 1.1
            full_weights["rfi_fat_ebv"] *= 1.15
        if grazing_context_active:
            selection_weights["fertility"] *= 1.1
            full_weights["fertility_score"] *= 1.1
        mortality_signal = sum(1 for cow in cows if not cow.get("alive", True))
        if mortality_signal:
            full_weights["livability_score"] *= 1.25
        if active_disease_cases:
            full_weights["health_composite_score"] *= 1.25
        full_weight_total = sum(full_weights.values())
        full_weights = {trait: trait_weight / full_weight_total for trait, trait_weight in full_weights.items()}
        weight_total = sum(selection_weights.values())
        selection_weights = {trait: weight / weight_total for trait, weight in selection_weights.items()}
        selection_fraction = require_fraction(
            "genetics.selection_intensity",
            float(value(self.ctx.calibration, "genetics.selection_intensity")),
        )
        selection_intensity_i = self._selection_intensity_i(selection_fraction)
        phenotypic_sd = float(value(self.ctx.calibration, "genetics.phenotypic_sd_rfi_fat"))
        generation_interval = float(value(self.ctx.calibration, "genetics.generation_interval_years"))
        if generation_interval <= 0.0:
            raise ConfigError("genetics.generation_interval_years must be positive")
        genetic_gain = (
            float(value(self.ctx.calibration, "genetics.heritability_h2_rfi_fat"))
            * selection_intensity_i
            * phenotypic_sd
            / generation_interval
        )
        if not eligible_cows:
            herd_mean_rfi = 0.0
            selected = []
        else:
            herd_mean_rfi = sum(float(cow.get("feed_efficiency_trait", 1.0)) for cow in eligible_cows) / len(eligible_cows)
            selected_count = max(1, int(round(len(eligible_cows) * selection_fraction)))
            selected = sorted(eligible_cows, key=lambda cow: self._full_merit(cow, full_weights), reverse=True)[:selected_count]
            annual_gain = float(value(self.ctx.calibration, "genetics.annual_rfi_gain_fraction"))
            for cow in selected:
                cow["feed_efficiency_trait"] = max(0.5, float(cow.get("feed_efficiency_trait", 1.0)) * (1.0 - annual_gain))

        offspring_parent_ids, offspring_trait_vector, offspring_markers = self._offspring_trait_vector(selected)
        offspring_id = None
        if offspring_trait_vector is not None:
            offspring_id = f"calf-{day.year}-{len(cows) + 1}"
            self.ctx.state["cows"].append({
                "id": offspring_id,
                "alive": True,
                "health_status": "healthy",
                "disease": None,
                "age_days": 0,
                "days_in_milk": 0,
                "parity": 0,
                "pregnant": False,
                "days_pregnant": 0,
                "body_weight_kg": 40.0,
                "body_condition_score": 3.0,
                "rumen_ph": None,
                "sara_ticks": 0,
                "dmi_history": [],
                "milk_history": [],
                "ch4_history": [],
                "manure_history": [],
                "health_history": [],
                "body_weight_history": [],
                "bcs_history": [],
                "reproduction_history": [],
                "recorded_dmi_days": 0,
                "candidate_record_complete": False,
                "ebv_confidence": 0.0,
                "dmi_record_series": [],
                "milk_trait": float(offspring_trait_vector["milk_yield"]),
                "feed_efficiency_trait": max(0.5, 1.0 + float(offspring_trait_vector["rfi_fat_ebv"]) / 10.0),
                "trait_vector": offspring_trait_vector,
                "genome_markers": offspring_markers or {},
                "parent_ids": offspring_parent_ids,
            })
        herd_net_merit = (
            sum(self._trait_merit(cow, selection_weights) for cow in eligible_cows) / len(eligible_cows)
            if eligible_cows
            else 0.0
        )
        self.ctx.state["herd_nm_trend"].append({"year": day.year, "net_merit_score": herd_net_merit})

        trend = {
            "year": day.year,
            "herd_mean_rfi_fat": herd_mean_rfi,
            "selected_parent_count": len(selected),
            "minimum_intake_record_days": int(value(self.ctx.calibration, "genetics.minimum_intake_record_days")),
            "feed_cost_signal_per_kg_dm": feed_cost_signal,
            "eligible_candidate_count": len(eligible_cows),
            "selection_weights": selection_weights,
            "net_merit_template": market_scenario,
            "net_merit_weights": full_weights,
            "candidate_pool": [
                {"id": cow["id"], "ebv_confidence": cow.get("ebv_confidence", 0.0), "rfi_fat": cow.get("rfi_fat_phenotype"), "net_merit_score": self._full_merit(cow, full_weights)}
                for cow in eligible_cows
            ],
            "selected_parents": [
                {"id": cow["id"], "net_merit_score": self._full_merit(cow, full_weights)} for cow in selected
            ],
            "selected_parent_ids": [cow["id"] for cow in selected],
            "offspring_parent_ids": offspring_parent_ids,
            "offspring_trait_vector": offspring_trait_vector,
            "offspring_genome_markers": offspring_markers,
            "offspring_id": offspring_id,
            "genetic_gain_per_generation": genetic_gain,
            "selection_intensity_i": selection_intensity_i,
            "phenotypic_sd_rfi_fat": phenotypic_sd,
            "generation_interval_years": generation_interval,
            "heritability_h2_rfi_fat": float(value(self.ctx.calibration, "genetics.heritability_h2_rfi_fat")),
            "herd_net_merit_score": herd_net_merit,
            "herd_nm_trend": list(self.ctx.state["herd_nm_trend"]),
            "active_disease_cases": active_disease_cases,
            "disease_frequency_signal": active_disease_cases,
            "mortality_signal": mortality_signal,
            "cull_cow_price": cull_cow_price,
            "market_scenario": market_scenario,
            "user_breeding_priority": user_breeding_priority,
            "grazing_context_active": grazing_context_active,
            "diet_change_recorded": bool(self.ctx.state.get("diet_change_recorded", False)),
            "stable_diet_days": int(self.ctx.state.get("stable_diet_days", 0)),
            "last_diet_change_day": self.ctx.state.get("last_diet_change_day", None),
            "cross_diet_repeatability_modifier": float(
                value(self.ctx.calibration, "genetics.cross_diet_repeatability_modifier")
            ),
            "last_ration_me_mj_per_kg_dm": ration_me,
            "last_ration_ndf_fraction": ration_ndf,
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
