from __future__ import annotations

from datetime import date
from math import exp, pow
from typing import Any

from dairy_abm.analysis.cdairy_economics import CdairyPrices, herd_total_economics
from dairy_abm.config import value
from dairy_abm.core import BaseAgent, Packet, require_fraction, require_nonnegative
from dairy_abm.herd_lifecycle import HerdLifecycle, wood_shape


class CowAgent(BaseAgent):
    name = "cow"

    # Share of generated cows by parity (1, 2, 3, 4, 5, 6): workbook AIRAND
    # year-15 present cows by parity (Stats_MAST raw rows 21-24) with the 4+
    # group spread over parities 4-6.
    _GENERATED_PARITY_WEIGHTS = (0.337, 0.250, 0.176, 0.12, 0.075, 0.042)

    def __init__(self, ctx) -> None:
        """Initialize the agent and create the configured starting herd."""
        super().__init__(ctx)
        self.lifecycle = HerdLifecycle(ctx)
        self._cached_params: tuple | None = None
        self.prices = CdairyPrices.from_calibration(ctx.calibration)
        ctx.state.setdefault("cows", self._build_initial_herd())
        if self.lifecycle.capacity <= 0:
            self.lifecycle.capacity = sum(1 for cow in ctx.state["cows"] if int(cow.get("parity", 0)) >= 1)
        ctx.state["herd_capacity"] = self.lifecycle.capacity

    def _build_initial_herd(self) -> list[dict[str, Any]]:
        """Build the herd from scenario animals or the configured herd size."""
        herd = self.ctx.scenario.get("herd")
        if isinstance(herd, list):
            animals = []
            for index, cow in enumerate(herd):
                explicit = dict(cow)
                explicit["_explicit"] = tuple(cow.keys())
                animal = self._normalize_cow(explicit, index)
                self.lifecycle.initialize_animal(animal, steady_state=False)
                animals.append(animal)
            return animals
        herd_size = int(self.ctx.scenario.get("herd_size", 100))
        rng = self.ctx.rng
        animals = []
        for index in range(herd_size):
            parity = 1 + self._weighted_index(self._GENERATED_PARITY_WEIGHTS, rng.random())
            animal = self._normalize_cow({"id": f"cow-{index + 1}", "parity": parity}, index)
            self.lifecycle.initialize_animal(animal, steady_state=True)
            animal["age_days"] = 735 + (parity - 1) * 391 + int(animal.get("days_in_milk", 0))
            animals.append(animal)
        if bool(self.ctx.scenario.get("include_replacement_heifers", True)):
            for heifer in self.lifecycle.initial_heifers(herd_size):
                calf = self._normalize_cow(heifer, len(animals))
                self.lifecycle.initialize_animal(calf, steady_state=False)
                animals.append(calf)
        return animals

    @staticmethod
    def _weighted_index(weights: tuple[float, ...], draw: float) -> int:
        total = sum(weights)
        cumulative = 0.0
        for index, weight in enumerate(weights):
            cumulative += weight / total
            if draw < cumulative:
                return index
        return len(weights) - 1

    def _normalize_cow(self, cow: dict[str, Any], index: int) -> dict[str, Any]:
        """Fill missing cow state and normalize traits into the runtime schema."""
        normalized = dict(cow)
        milk_trait = float(normalized.get("milk_trait", 1.0))
        feed_efficiency_trait = float(normalized.get("feed_efficiency_trait", 1.0))
        normalized.setdefault("id", f"cow-{index + 1}")
        normalized.setdefault("health_status", "healthy")
        normalized.setdefault("disease", None)
        normalized["milk_trait"] = milk_trait
        normalized["feed_efficiency_trait"] = feed_efficiency_trait
        normalized.setdefault(
            "inherited_traits",
            {"milk": milk_trait, "feed_efficiency": feed_efficiency_trait},
        )
        normalized.setdefault(
            "trait_vector",
            {
                "milk_yield": milk_trait,
                "feed_efficiency": 1.0 / feed_efficiency_trait if feed_efficiency_trait > 0.0 else 0.0,
                "butterfat_ebv": float(normalized.get("butterfat_ebv", 1.0)),
                "protein_ebv": float(normalized.get("protein_ebv", 1.0)),
                "rfi_fat_ebv": float(normalized.get("rfi_fat_ebv", 0.0)),
                "body_weight_composite": float(normalized.get("body_weight_composite", 1.0)),
                "livability_score": float(normalized.get("livability_score", normalized.get("survivability_trait", 1.0))),
                "fertility_score": float(normalized.get("fertility_score", normalized.get("fertility_trait", 1.0))),
                "health_composite_score": float(normalized.get("health_composite_score", normalized.get("health_trait", 1.0))),
                "calving_ease_score": float(normalized.get("calving_ease_score", 1.0)),
                "fertility": float(normalized.get("fertility_trait", 1.0)),
                "health": float(normalized.get("health_trait", 1.0)),
                "survivability": float(normalized.get("survivability_trait", 1.0)),
            },
        )
        normalized.setdefault("alive", True)
        normalized.setdefault("sex", "female")
        normalized.setdefault(
            "age_days", int(value(self.ctx.calibration, "cow.initial_age_days"))
        )
        normalized.setdefault(
            "days_in_milk", int(value(self.ctx.calibration, "cow.initial_days_in_milk"))
        )
        normalized.setdefault("parity", int(value(self.ctx.calibration, "cow.initial_parity")))
        if int(normalized["parity"]) >= 1:
            # Adult body weight follows the parity baseline; an explicit starting
            # weight is kept as a fixed offset from that baseline.
            baseline = self._baseline_body_weight(int(normalized["parity"]))
            normalized.setdefault("body_weight_kg", baseline)
            normalized.setdefault("body_weight_offset_kg", float(normalized["body_weight_kg"]) - baseline)
        normalized.setdefault(
            "body_weight_kg", float(value(self.ctx.calibration, "cow.initial_body_weight_kg"))
        )
        normalized.setdefault(
            "body_condition_score",
            float(value(self.ctx.calibration, "cow.initial_body_condition_score")),
        )
        normalized.setdefault("pregnant", False)
        normalized.setdefault("days_pregnant", 0)
        normalized.setdefault("rumen_ph", None)
        normalized.setdefault("sara_ticks", 0)
        normalized.setdefault(
            "genome_markers",
            {
                trait: float(normalized["trait_vector"].get(trait, 0.0))
                for trait in ("butterfat_ebv", "protein_ebv", "rfi_fat_ebv", "fertility_score", "health_composite_score")
            },
        )
        normalized.setdefault("calving_interval_days", 0)
        normalized.setdefault("reproduction_history", [])
        normalized.setdefault("dmi_history", [])
        normalized.setdefault("milk_history", [])
        normalized.setdefault("ch4_history", [])
        normalized.setdefault("manure_history", [])
        normalized.setdefault("health_history", [])
        normalized.setdefault("body_weight_history", [])
        normalized.setdefault("bcs_history", [])
        return normalized

    @staticmethod
    def _expected_dmi(cow: dict[str, Any], milk_e_mcal: float) -> float:
        """Estimate dry-matter intake from parity, milk energy, body size, and condition."""
        parity = 0.0 if int(cow.get("parity", 1)) <= 1 else 1.0
        body_weight = float(cow.get("body_weight_kg", 650.0))
        bcs = float(cow.get("body_condition_score", 3.0))
        dim = max(1.0, float(cow.get("days_in_milk", 1)))
        # Outside the Eq 2-1 envelope the limit DIM is used as the fallback.
        dim = min(dim, float(cow.get("_eq2_1_max_dim", 368)))
        expected = (
            3.7 + 5.7 * parity + 0.305 * milk_e_mcal + 0.022 * body_weight
            + (-0.689 - 1.87 * parity) * bcs
        ) * (1.0 - (0.212 + 0.136 * parity) * exp(-0.053 * dim))
        return max(0.0, expected)

    def _milk_energy_mcal(self, milk_l: float, traits: dict[str, Any]) -> float:
        """Calculate MilkE from milk mass and the workbook milk fat and protein contents."""
        density = float(traits.get("milk_density_kg_per_l", 1.03))
        fat = max(0.0, self.lifecycle.fat_fraction * float(traits.get("butterfat_ebv", 1.0)))
        protein = max(0.0, self.lifecycle.protein_fraction * float(traits.get("protein_ebv", 1.0)))
        lactose = float(traits.get("lactose_fraction", 0.048))
        milk_kg = max(0.0, milk_l * density)
        return milk_kg * (0.0929 * fat * 100.0 + 0.0547 * protein * 100.0 + 0.0395 * lactose * 100.0)

    def _lactation_params(self) -> tuple[float, float, float, float, int, float]:
        cal = self.ctx.calibration
        return (
            float(value(cal, "herd.wood_b")),
            float(value(cal, "herd.wood_c")),
            float(value(cal, "herd.peak_milk_l_first_parity")),
            float(value(cal, "herd.peak_milk_l_mature")),
            max(2, int(value(cal, "herd.mature_parity"))),
            float(value(cal, "herd.milk_yield_scale")),
        )

    def _lactation_factor(self, days_in_milk: int) -> float:
        """Wood's lactation curve normalised to 1 at peak (dashboard Animal Biology b, c)."""
        b, c, *_ = self._cached_params or self._lactation_params()
        return wood_shape(days_in_milk, b, c)

    def _peak_milk_l(self, cow: dict[str, Any]) -> float:
        """Parity-specific Wood's peak, scaled so herd yield matches the workbook."""
        _b, _c, first, mature, mature_parity, scale = self._cached_params or self._lactation_params()
        parity = max(1, int(cow.get("parity", 1)))
        blend = min(1.0, max(0.0, (parity - 1) / (mature_parity - 1)))
        return (first + (mature - first) * blend) * scale * float(cow.get("peak_factor", 1.0))

    def _baseline_body_weight(self, parity: int) -> float:
        """Parity body-weight baseline: first-parity weight rising linearly to mature weight.

        Values come from the target dashboard's Animal Biology defaults (owner
        decision 2026-09-23); the Blueprint and the workbook give no BW rule.
        """
        cal = self.ctx.calibration
        first = float(value(cal, "cow.bodyweight_first_parity_kg"))
        mature = float(value(cal, "cow.bodyweight_mature_kg"))
        mature_parity = max(2, int(value(cal, "herd.mature_parity")))
        blend = min(1.0, max(0.0, (max(1, parity) - 1) / (mature_parity - 1)))
        return first + (mature - first) * blend

    def _make_calf(self, dam: dict[str, Any], sex: str) -> dict[str, Any]:
        """Create a retained calf; genetics supplies inherited traits when available."""
        inherit = self.ctx.state.get("offspring_traits_fn")
        dam_traits = dam.get("trait_vector", {})
        traits = inherit(dam) if callable(inherit) else (dict(dam_traits) if isinstance(dam_traits, dict) else {})
        calf = self._normalize_cow(
            {
                "id": self.lifecycle.next_id(f"calf-{dam['id']}"),
                "age_days": 0,
                "days_in_milk": 0,
                "parity": 0,
                "body_weight_kg": float(value(self.ctx.calibration, "herd.heifer_birth_weight_kg")),
                "sex": sex,
                "trait_vector": traits,
                "parent_ids": [dam["id"]],
            },
            len(self.ctx.state.get("cows", [])),
        )
        self.lifecycle.initialize_animal(calf, steady_state=False)
        return calf

    def _purchase_heifers(self, count: int) -> list[dict[str, Any]]:
        """Buy springing heifers to restore the herd (workbook new animals purchased)."""
        gestation = self.lifecycle.gestation
        bought = []
        for _ in range(count):
            heifer = self._normalize_cow(
                {
                    "id": self.lifecycle.next_id("purchased"),
                    "age_days": 700,
                    "days_in_milk": 0,
                    "parity": 0,
                    "pregnant": True,
                    "days_pregnant": gestation - 30,
                    "body_weight_kg": 520.0,
                },
                len(self.ctx.state.get("cows", [])),
            )
            self.lifecycle.initialize_animal(heifer, steady_state=False)
            bought.append(heifer)
        self.lifecycle.record_purchase(count)
        return bought

    def tick(self, day: date) -> None:
        """Advance each animal and publish daily production, health, and reproduction results."""
        cows = self.ctx.state.get("cows", [])
        lifecycle = self.lifecycle
        lifecycle.begin_day()
        self._cached_params = self._lactation_params()
        disease_packet = self.ctx.get_packet("disease_state_packet")
        prior_ration = self.ctx.get_packet("feed_crop_packet")
        water_delivery = self.ctx.get_packet("water_delivery_packet")
        sensor_packet = self.ctx.get_packet("sensor_observation_packet")
        grazing_packet = self.ctx.get_packet("grazing_access_packet")
        ration_coverage_fraction = (
            float(prior_ration.payload["ration_coverage_fraction"])
            if prior_ration is not None
            else 1.0
        )
        ration_coverage_fraction = min(1.0, max(0.0, ration_coverage_fraction))
        ration_shortfall_milk_loss = require_fraction(
            "cow.ration_shortfall_milk_loss_fraction",
            float(value(self.ctx.calibration, "cow.ration_shortfall_milk_loss_fraction")),
        )
        sensor_payload = sensor_packet.payload if sensor_packet is not None else {}
        prior_ration_nitrogen = (
            float(prior_ration.payload.get("ration_nitrogen_kg", 0.0))
            if prior_ration is not None
            else 0.0
        )
        thi = sensor_payload.get("thi")
        rumen_ph_by_cow = sensor_payload.get("rumen_ph_by_cow", {})
        observed_dmi_by_cow = sensor_payload.get("observed_dmi_kg_by_cow", {})
        estrus_by_cow = sensor_payload.get("estrus_by_cow", {})
        if not isinstance(rumen_ph_by_cow, dict):
            rumen_ph_by_cow = {}
        if not isinstance(observed_dmi_by_cow, dict):
            observed_dmi_by_cow = {}
        if not isinstance(estrus_by_cow, dict):
            estrus_by_cow = {}
        per_cow_rations = prior_ration.payload.get("per_cow_rations", {}) if prior_ration else {}
        if not isinstance(per_cow_rations, dict):
            per_cow_rations = {}
        water_availability = float(water_delivery.payload.get("water_availability_fraction", 1.0)) if water_delivery else 1.0
        water_availability = min(1.0, max(0.0, water_availability))

        base_dmi = float(value(self.ctx.calibration, "cow.base_dmi_kg_per_cow_day"))
        base_manure = float(value(self.ctx.calibration, "cow.base_manure_kg_per_cow_day"))
        base_enteric = float(value(self.ctx.calibration, "cow.enteric_ch4_kg_per_cow_day"))
        ch4_me_reference = float(value(self.ctx.calibration, "cow.ch4_me_reference_constant"))
        sick_loss = (
            float(disease_packet.payload["milk_loss_sick_fraction"])
            if disease_packet is not None
            else float(value(self.ctx.calibration, "disease.milk_loss_sick_fraction"))
        )
        per_cow_health_signal = disease_packet.payload.get("per_cow_health_signal", {}) if disease_packet else {}
        milk_l = 0.0
        dmi_kg = 0.0
        manure_kg = 0.0
        enteric_ch4_kg = 0.0
        sick_cows = 0
        sara_affected_cows = 0
        milking_cows = 0
        dry_cows = 0
        heifers = 0
        active_cows: list[dict[str, Any]] = []
        total_days_in_milk = 0.0
        total_body_condition_score = 0.0
        cow_records: list[dict[str, Any]] = []
        heat_stress_active = isinstance(thi, (int, float)) and thi >= float(
            value(self.ctx.calibration, "cow.mild_heat_stress_thi")
        )
        severe_heat_stress = isinstance(thi, (int, float)) and thi > float(
            value(self.ctx.calibration, "cow.severe_heat_stress_thi")
        )
        heat_dmi_loss = 0.0
        heat_milk_loss = 0.0
        if severe_heat_stress:
            heat_dmi_loss = require_fraction(
                "cow.severe_heat_stress_dmi_loss_fraction",
                float(value(self.ctx.calibration, "cow.severe_heat_stress_dmi_loss_fraction")),
            )
            heat_milk_loss = require_fraction(
                "cow.severe_heat_stress_milk_loss_fraction",
                float(value(self.ctx.calibration, "cow.severe_heat_stress_milk_loss_fraction")),
            )
        elif heat_stress_active:
            heat_dmi_loss = require_fraction(
                "cow.mild_heat_stress_dmi_loss_fraction",
                float(value(self.ctx.calibration, "cow.mild_heat_stress_dmi_loss_fraction")),
            )
            heat_milk_loss = require_fraction(
                "cow.mild_heat_stress_milk_loss_fraction",
                float(value(self.ctx.calibration, "cow.mild_heat_stress_milk_loss_fraction")),
            )
        sara_ph_threshold = float(value(self.ctx.calibration, "cow.sara_rumen_ph_threshold"))
        sara_required_ticks = int(value(self.ctx.calibration, "cow.sara_consecutive_ticks"))
        sara_digestibility_loss = require_fraction(
            "cow.sara_digestibility_loss_fraction",
            float(value(self.ctx.calibration, "cow.sara_digestibility_loss_fraction")),
        )
        sara_milk_loss = require_fraction(
            "cow.sara_milk_loss_fraction", float(value(self.ctx.calibration, "cow.sara_milk_loss_fraction"))
        )
        density = lifecycle.density
        lifecycle.conception_multiplier_today = (
            1.0 - float(value(self.ctx.calibration, "cow.heat_stress_conception_reduction_fraction"))
            if severe_heat_stress
            else 1.0
        )
        eq_dim_limit = int(value(self.ctx.calibration, "cow.eq2_1_max_dim_days"))

        for cow in list(cows):
            if not cow.get("alive", True):
                continue
            cow["reproduction_event_flag"] = None
            cow["clinical_mastitis_today"] = None
            if "category" not in cow:
                lifecycle.initialize_animal(cow, steady_state=False)
            if int(cow.get("parity", 0)) <= 0:
                if str(cow.get("sex", "female")) == "female":
                    heifers += 1
                    lifecycle.heifer_day(cow, day)
                else:
                    cow["age_days"] = int(cow.get("age_days", 0)) + 1
                continue
            lactating = bool(cow.get("lactating", True))
            if cow.get("_bw_parity") != int(cow["parity"]):
                # A new lactation starts from the parity baseline.
                cow["_bw_parity"] = int(cow["parity"])
                cow["body_weight_deviation_kg"] = 0.0
            energy_balance_fraction = 0.0
            cow_milk_l = 0.0
            expected_dmi = 0.0
            milk_e_mcal = 0.0
            sara_active = False
            trait_vector = cow.get("trait_vector", {})
            if lactating:
                milking_cows += 1
                rumen_ph = rumen_ph_by_cow.get(cow["id"])
                if isinstance(rumen_ph, (int, float)):
                    cow["rumen_ph"] = float(rumen_ph)
                    cow["sara_ticks"] = (
                        int(cow["sara_ticks"]) + 1 if rumen_ph < sara_ph_threshold else 0
                    )
                sara_active = int(cow["sara_ticks"]) >= sara_required_ticks
                if sara_active:
                    sara_affected_cows += 1
                milk_modifier = float(cow.get("milk_trait", 1.0))
                # Blueprint 8.5: the Genetics agent supplies the cross-diet adjusted RFI.
                rfi_fat = float(
                    cow.get(
                        "effective_rfi_fat",
                        trait_vector.get("rfi_fat_ebv", 0.0) if isinstance(trait_vector, dict) else 0.0,
                    )
                )
                ration = per_cow_rations.get(str(cow["id"]), {})
                cow_ration_coverage = min(1.0, max(0.0, float(ration.get("coverage_fraction", ration_coverage_fraction))))
                ration_me = float(ration.get("me_mj_per_kg_dm", prior_ration.payload.get("ration_me_mj_per_kg_dm", 10.0) if prior_ration else 10.0))
                peak_l = self._peak_milk_l(cow)
                cow["_eq2_1_max_dim"] = eq_dim_limit
                milk_e_mcal = self._milk_energy_mcal(float(cow.get("last_milk_l", peak_l * 0.7)), trait_vector if isinstance(trait_vector, dict) else {})
                expected_dmi = self._expected_dmi(cow, milk_e_mcal) * float(value(self.ctx.calibration, "cow.dmi_level_calibration_factor"))
                cow["expected_dmi_kg"] = expected_dmi
                dmi_cv = min(0.22, max(0.11, float(self.ctx.scenario.get("dmi_stochastic_cv", value(self.ctx.calibration, "cow.dmi_stochastic_cv")))))
                actual_dmi = max(0.0, expected_dmi + rfi_fat + self.ctx.rng.gauss(0.0, dmi_cv * expected_dmi))
                # Only the daily residual e moves body reserves: heat stress and supply
                # shortfalls cut milk and intake together (Blueprint Cow 8.1, 8.5), and
                # RFI is by definition intake not explained by energy use or BW change.
                energy_balance_fraction = (actual_dmi - rfi_fat) / max(expected_dmi, 0.001) - 1.0
                if cow.get("health_status") != "healthy":
                    health_signal = per_cow_health_signal.get(str(cow["id"]), {}) if isinstance(per_cow_health_signal, dict) else {}
                    milk_modifier *= 1.0 - float(health_signal.get("milk_yield_penalty_fraction", sick_loss))
                    sick_cows += 1
                cow_milk_l = (
                    peak_l
                    * milk_modifier
                    * self._lactation_factor(int(cow["days_in_milk"]))
                    * (1.0 - heat_milk_loss)
                    * (1.0 - (1.0 - cow_ration_coverage) * ration_shortfall_milk_loss)
                    * water_availability
                )
                # Blueprint 8.1: actual_DMI = expected_DMI + effective_RFI_fat + e, then
                # the heat-stress penalty and the supply constraints (ration, water).
                cow_dmi_kg = actual_dmi * (1.0 - heat_dmi_loss) * cow_ration_coverage * water_availability
                if sara_active:
                    # Blueprint 8.5: SARA lowers milk and diet digestibility, not intake.
                    cow_milk_l *= 1.0 - sara_milk_loss
                    ration_me *= 1.0 - sara_digestibility_loss
            else:
                dry_cows += 1
                ration_me = float(prior_ration.payload.get("ration_me_mj_per_kg_dm", 10.0)) if prior_ration else 10.0
                expected_dmi = lifecycle.dry_dmi
                cow["expected_dmi_kg"] = expected_dmi
                cow_dmi_kg = lifecycle.dry_dmi * water_availability
            milk_l += cow_milk_l
            dmi_kg += cow_dmi_kg
            cow["last_dmi_kg"] = cow_dmi_kg
            cow_manure_kg = base_manure * (cow_dmi_kg / max(base_dmi, 0.001))
            cow_ch4_kg = base_enteric * (cow_dmi_kg / max(base_dmi, 0.001)) * (ch4_me_reference / max(1.0, ration_me))
            manure_kg += cow_manure_kg
            enteric_ch4_kg += cow_ch4_kg
            cow["last_milk_l"] = cow_milk_l
            if lactating:
                cow["body_weight_deviation_kg"] = float(cow.get("body_weight_deviation_kg", 0.0)) + max(
                    -1.0, min(1.0, energy_balance_fraction * 0.8)
                )
                cow["body_condition_score"] = min(
                    5.0,
                    max(1.0, float(cow["body_condition_score"]) + max(-0.02, min(0.02, energy_balance_fraction * 0.02))),
                )
            cow["body_weight_kg"] = max(
                300.0,
                self._baseline_body_weight(int(cow["parity"]))
                + float(cow.get("body_weight_offset_kg", 0.0))
                + float(cow.get("body_weight_deviation_kg", 0.0)),
            )
            cow["dmi_history"].append(cow_dmi_kg)
            cow["milk_history"].append(cow_milk_l)
            cow["ch4_history"].append(cow_ch4_kg)
            cow["manure_history"].append(cow_manure_kg)
            cow["health_history"].append(cow.get("health_status", "healthy"))
            cow["body_weight_history"].append(float(cow["body_weight_kg"]))
            cow["bcs_history"].append(float(cow["body_condition_score"]))
            total_days_in_milk += float(cow["days_in_milk"])
            total_body_condition_score += float(cow["body_condition_score"])
            lifecycle.cow_day(cow, cow_milk_l * density, cow_dmi_kg, day)
            cow_records.append(
                {
                    "id": cow["id"],
                    "milk_l": cow_milk_l,
                    "dmi_kg": cow_dmi_kg,
                    "days_in_milk": cow["days_in_milk"],
                    "parity": cow["parity"],
                    "lactating": lactating,
                    "pregnant": bool(cow.get("pregnant", False)),
                    "repro_state": cow.get("repro_state"),
                    "health_status": cow["health_status"],
                    "rumen_ph": cow["rumen_ph"],
                    "observed_dmi_kg": observed_dmi_by_cow.get(cow["id"]),
                    "actual_dmi_kg_dm": cow_dmi_kg,
                    "expected_dmi_eq2_1_kg_dm": expected_dmi,
                    "milk_e_mcal": milk_e_mcal,
                    "estrus_detected": bool(estrus_by_cow.get(cow["id"], False)),
                    "sara_active": sara_active,
                    "clinical_mastitis": cow.get("clinical_mastitis_today"),
                }
            )
            if cow.get("alive", True):
                active_cows.append(cow)
                cow["age_days"] = int(cow["age_days"]) + 1
                if cow.get("lactating"):
                    cow["days_in_milk"] = int(cow["days_in_milk"]) + 1
                cow["calving_interval_days"] = int(cow.get("calving_interval_days", 0)) + 1

        newborns = lifecycle.process_calvings(day, self._make_calf)
        if newborns:
            self.ctx.state["cows"].extend(newborns)
        rebalanced = lifecycle.rebalance(self.ctx.state["cows"])
        purchase = lifecycle.needs_purchase(self.ctx.state["cows"])
        if purchase:
            springing = [a for a in self.ctx.state["cows"] if a.get("alive", True) and int(a.get("parity", 0)) == 0 and a.get("pregnant")]
            if not springing:
                self.ctx.state["cows"].extend(self._purchase_heifers(purchase))
        today = lifecycle.end_day(day)
        workbook_inputs = {name: float(today.get(name, 0.0)) for name in self._workbook_input_names()}
        workbook_inputs["avg_weighted_scs"] = lifecycle.scs
        workbook_inputs["profit_deviation_cows"] = lifecycle.profit_dev_cows * workbook_inputs["present_cow_days"] / 365.0
        workbook_inputs["profit_deviation_heifers"] = lifecycle.profit_dev_heifers * workbook_inputs["present_cow_days"] / 365.0
        daily_economics = herd_total_economics(workbook_inputs, self.prices)

        active_cows = [cow for cow in active_cows if cow.get("alive", True)]
        active_cow_count = len(active_cows)
        deaths = int(today.get("cows_died", 0))
        pregnant_cows = sum(1 for cow in active_cows if cow.get("pregnant"))
        # Blueprint 10: FCR is null when there is no milk.
        feed_conversion_ratio = dmi_kg / milk_l if milk_l > 0.0 else None
        enteric_ch4_intensity = enteric_ch4_kg / milk_l if milk_l > 0.0 else None
        milk_protein_nitrogen = (
            milk_l
            * float(value(self.ctx.calibration, "cow.milk_protein_fraction"))
            * float(value(self.ctx.calibration, "feed_crop.nitrogen_fraction_of_crude_protein"))
        )
        nitrogen_use_efficiency = (
            milk_protein_nitrogen / prior_ration_nitrogen if prior_ration_nitrogen > 0.0 else None
        )

        grazing_intake_kg = 0.0
        if grazing_packet is not None and bool(grazing_packet.payload.get("enabled", False)):
            pasture_ha = float(grazing_packet.payload.get("pasture_available_ha", 0.0))
            seasonal_frac = float(grazing_packet.payload.get("seasonal_availability_fraction", 1.0))
            total_grazing_available = (
                pasture_ha
                * seasonal_frac
                * float(value(self.ctx.calibration, "cow.grazing_intake_kg_dm_per_ha_day"))
            )
            grazing_intake_kg = min(total_grazing_available, dmi_kg)

        # Milk is priced with the workbook's component prices (Excel precedence).
        milk_revenue = (
            daily_economics["milk_sales"] + daily_economics["fat_sales"]
            + daily_economics["protein_sales"] + daily_economics["scs_deviation"]
        )
        packet = Packet(
            source=self.name,
            name="cow_daily_packet",
            day=day,
            payload={
                "cow_count": active_cow_count,
                "milking_cows": milking_cows,
                "dry_cows": dry_cows,
                "heifer_count": heifers,
                "healthy_cows": active_cow_count - sick_cows,
                "sick_cows": sick_cows,
                "milk_l": require_nonnegative("milk_l", milk_l),
                "milk_kg": milk_l * density,
                "milk_fat_kg": milk_l * density * lifecycle.fat_fraction,
                "milk_true_protein_kg": milk_l * density * lifecycle.protein_fraction,
                "daily_milk_yield_l": require_nonnegative("daily_milk_yield_l", milk_l),
                "dmi_kg": require_nonnegative("dmi_kg", dmi_kg),
                "dmi_lactating_kg": float(today.get("dmi_wet_kg", 0.0)),
                "dmi_dry_kg": float(today.get("dmi_dry_kg", 0.0)),
                "actual_dmi_kg_dm": require_nonnegative("actual_dmi_kg_dm", dmi_kg),
                "manure_kg": require_nonnegative("manure_kg", manure_kg),
                "enteric_ch4_kg": require_nonnegative("enteric_ch4_kg", enteric_ch4_kg),
                "milk_revenue": require_nonnegative("milk_revenue", max(0.0, milk_revenue)),
                "ration_coverage_fraction": ration_coverage_fraction,
                "thi": float(thi) if isinstance(thi, (int, float)) else None,
                "heat_stress_active": heat_stress_active,
                "sara_affected_cows": sara_affected_cows,
                "pregnant_cows": pregnant_cows,
                "conceptions": int(today.get("_conceptions_total", 0)),
                "calvings": int(today.get("_calvings_cows", 0) + today.get("_calvings_heifers", 0)),
                "deaths": deaths,
                "cows_culled": int(today.get("cows_culled_live", 0) + today.get("cows_culled_to_rebalance", 0)),
                "cows_culled_rebalance": rebalanced,
                "heifers_sold": int(today.get("heifers_sold", 0)),
                "bull_calves_sold": int(today.get("male_calves_born", 0)),
                "clinical_mastitis_cases": int(
                    today.get("mastitis_gram_positive_cases", 0)
                    + today.get("mastitis_gram_negative_cases", 0)
                    + today.get("mastitis_other_cases", 0)
                ),
                "antibiotic_daily_doses": float(today.get("antibiotic_daily_doses", 0.0)),
                "mean_days_in_milk": total_days_in_milk / active_cow_count if active_cow_count else 0.0,
                "mean_body_condition_score": (
                    total_body_condition_score / active_cow_count if active_cow_count else 0.0
                ),
                "feed_conversion_ratio_kg_dm_per_l": feed_conversion_ratio,
                "sara_digestibility_loss_fraction": sara_digestibility_loss if sara_affected_cows else 0.0,
                "heat_stress_conception_multiplier": lifecycle.conception_multiplier_today,
                "enteric_ch4_intensity_kg_per_l": enteric_ch4_intensity,
                "milk_protein_nitrogen_kg": milk_protein_nitrogen,
                "nitrogen_use_efficiency": nitrogen_use_efficiency,
                "grazing_intake_kg": grazing_intake_kg,
                "grazing_enabled": bool(grazing_packet.payload.get("enabled", False)) if grazing_packet else False,
                "water_availability_fraction": water_availability,
                "health_mortality_signal": {"deaths": deaths, "sick_cows": sick_cows},
                "reproduction_event_count": sum(1 for cow in active_cows if cow.get("reproduction_event_flag")),
                "workbook_daily_economics": daily_economics,
                "cow_records": cow_records,
            },
        )
        self.ctx.publish(packet)
        self.ctx.state.setdefault("execution_order", []).append(self.name)

    @staticmethod
    def _workbook_input_names() -> tuple[str, ...]:
        from dairy_abm.analysis.cdairy_economics import INPUT_REFS

        return tuple(INPUT_REFS)
