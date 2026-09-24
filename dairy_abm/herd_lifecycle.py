"""Herd life-cycle submodel: reproduction, dry-off, calving, replacement, culling, clinical mastitis.

The rules and coefficients follow the Cdairy workbook's herd program inputs
(``herdInputs`` sheet) wherever the workbook states them, and are otherwise
calibrated to the workbook's AIRAND year-15 herd statistics (``Stats_MAST``).
Every coefficient lives in the ``herd`` calibration group with its source.

The submodel also accumulates, per calendar year, the herd statistics that the
workbook's economics layer consumes (``dairy_abm.analysis.cdairy_economics``),
so model output can be priced with exactly the workbook's formulas.
"""

from __future__ import annotations

from datetime import date
from math import exp, log, pow
from typing import Any, Callable

from dairy_abm.analysis.cdairy_economics import INPUT_REFS
from dairy_abm.config import value

REPRO_VWP = "vwp"
REPRO_OPEN = "open"
REPRO_PREGNANT = "pregnant"
REPRO_DNB = "dnb"


def _param(ctx, key: str) -> Any:
    return value(ctx.calibration, f"herd.{key}")


class HerdLifecycle:
    """Stateful daily herd dynamics operating on the shared ``ctx.state['cows']`` list."""

    def __init__(self, ctx) -> None:
        self.ctx = ctx
        c = lambda key: _param(ctx, key)  # noqa: E731
        self.vwp_cows = int(c("vwp_cows_days"))
        self.ov_low = float(c("ovulation_interval_low_days"))
        self.ov_mean = float(c("ovulation_interval_mean_days"))
        self.ov_high = float(c("ovulation_interval_high_days"))
        self.ov_std = float(c("ovulation_interval_std_days"))
        self.p_insem_cows = float(c("pr_insemination_at_estrus_cows"))
        self.p_insem_heifers = float(c("pr_insemination_at_estrus_heifers"))
        self.p_concept_cows = float(c("pr_conception_estrus_cows")) * float(c("conception_genetic_multiplier_cows"))
        self.p_concept_heifers = float(c("pr_conception_estrus_heifers")) * float(c("conception_genetic_multiplier_heifers"))
        self.p_estrus_expression = float(c("estrus_expression_probability"))
        self.p_first_service = float(c("first_service_submission_probability"))
        self.rate_eligibility_dim = int(c("reproduction_rate_eligibility_start_dim"))
        self.pregchecks = [int(c("pregcheck_2_days")), int(c("pregcheck_3_days")), int(c("pregcheck_4_days"))]
        self.gestation = int(ctx.scenario.get("gestation_days", c("gestation_days")))
        self.dry_period = int(c("dry_period_days"))
        self.dry_dmi = float(c("dry_cow_dmi_kg_per_day"))
        self.cull_milk_kg = float(c("cull_milk_threshold_kg_per_day"))
        self.dnb_dim = int(c("do_not_breed_after_dim_days"))
        self.max_parity = int(c("max_parity"))
        self.loss_cows = float(c("pregnancy_loss_probability_cows"))
        self.loss_heifers = float(c("pregnancy_loss_probability_heifers"))
        self.h_death_cows = self._daily(float(c("cow_death_rate_annual")))
        self.h_cull_cows = self._daily(float(c("cow_involuntary_cull_rate_annual")))
        self.h_death_heifers = self._daily(float(c("heifer_death_rate_annual")))
        self.h_cull_heifers = self._daily(float(c("heifer_involuntary_cull_rate_annual")))
        self.heifer_breeding_age = int(c("heifer_breeding_age_days"))
        self.barren_heifer_age = int(c("barren_heifer_cull_age_days"))
        self.calf_sale_age = int(c("female_calf_sale_age_days"))
        self.calf_sale_fraction = float(c("female_calf_sale_fraction"))
        self.stillbirth = float(c("stillbirth_fraction"))
        self.male_fraction = float(c("male_calf_fraction"))
        self.heifer_bw_birth = float(c("heifer_birth_weight_kg"))
        self.heifer_growth = float(c("heifer_growth_kg_per_day"))
        self.mastitis_rates = [
            float(c("clinical_mastitis_incidence_parity1")),
            float(c("clinical_mastitis_incidence_parity2")),
            float(c("clinical_mastitis_incidence_parity3")),
            float(c("clinical_mastitis_incidence_parity4plus")),
        ]
        self.gram_pos_share = float(c("mastitis_gram_positive_share"))
        self.gram_neg_share = float(c("mastitis_gram_negative_share"))
        self.add_per_gram_pos = float(c("antibiotic_daily_doses_per_gram_positive_case"))
        self.scs = float(c("average_scs"))
        self.fat_fraction = float(c("milk_fat_fraction"))
        self.protein_fraction = float(c("milk_protein_fraction"))
        self.profit_dev_cows = float(c("profit_deviation_cows_per_cow_year"))
        self.profit_dev_heifers = float(c("profit_deviation_heifers_per_cow_year"))
        self.purchase_threshold = float(c("replacement_purchase_threshold_fraction"))
        self.density = float(value(ctx.calibration, "cow.milk_density_kg_per_l")) if self._has("cow.milk_density_kg_per_l") else 1.03
        self.capacity = int(ctx.scenario.get("herd_capacity", ctx.scenario.get("herd_size", 0)) or 0)
        ctx.state.setdefault("herd_year_stats", {})
        ctx.state.setdefault("herd_removals", {"cows_died": 0, "cows_culled_live": 0, "cows_culled_rebalance": 0, "heifers_died": 0, "heifers_culled": 0, "calves_sold": 0, "bull_calves_sold": 0})
        ctx.state.setdefault("animal_serial", 0)
        self.today: dict[str, float] = {}
        self.conception_multiplier_today = 1.0

    # ----------------------------------------------------------------- helpers
    def _has(self, key: str) -> bool:
        try:
            value(self.ctx.calibration, key)
            return True
        except (KeyError, TypeError):
            return False

    @staticmethod
    def _daily(annual: float) -> float:
        if annual >= 1.0:
            return 1.0
        return 1.0 - pow(1.0 - max(annual, 0.0), 1.0 / 365.0)

    def _ovulation_interval(self) -> int:
        """Truncated normal ovulation interval (herdInputs ov_low/mean/high/std)."""
        rng = self.ctx.rng
        for _ in range(20):
            draw = rng.gauss(self.ov_mean, self.ov_std)
            if self.ov_low <= draw <= self.ov_high:
                return max(1, int(round(draw)))
        return int(round(self.ov_mean))

    def _stat(self, name: str, amount: float = 1.0) -> None:
        self.today[name] = self.today.get(name, 0.0) + amount

    def next_id(self, prefix: str) -> str:
        self.ctx.state["animal_serial"] = int(self.ctx.state["animal_serial"]) + 1
        return f"{prefix}-{self.ctx.state['animal_serial']}"

    # ------------------------------------------------------------ initial herd
    def initialize_animal(self, animal: dict[str, Any], steady_state: bool) -> None:
        """Add life-cycle fields; ``steady_state`` samples a representative stage."""
        rng = self.ctx.rng
        parity = int(animal.get("parity", 0))
        animal.setdefault("peak_factor", max(0.4, rng.gauss(1.0, float(_param(self.ctx, "cow_peak_std_fraction")))))
        animal.setdefault("days_to_ovulation", rng.randint(1, max(1, self._ovulation_interval())))
        animal.setdefault("inseminations", 0)
        animal.setdefault("days_since_insemination", None)
        animal.setdefault("conceived_dim", None)
        animal.setdefault("mastitis_cases", 0)
        animal.setdefault("removal_reason", None)
        if parity <= 0:
            animal.setdefault("category", "heifer")
            animal.setdefault("lactating", False)
            animal.setdefault("dry", False)
            animal.setdefault("repro_state", REPRO_VWP)
            if animal.get("pregnant"):
                animal["repro_state"] = REPRO_PREGNANT
            animal.setdefault("sale_decided", True)
            return
        animal.setdefault("category", "cow")
        pregnant = bool(animal.get("pregnant", False))
        days_pregnant = int(animal.get("days_pregnant", 0))
        dim = int(animal.get("days_in_milk", 0))
        if steady_state and "days_in_milk" not in animal.get("_explicit", ()):
            # Position in a calving interval of (typical days open + gestation).
            typical_open = self.vwp_cows + 40
            interval = typical_open + self.gestation
            t = rng.randint(1, interval)
            if t <= typical_open:
                dim, pregnant, days_pregnant = t, False, 0
            else:
                dim, pregnant, days_pregnant = t, True, t - typical_open
            animal["days_in_milk"] = dim
            animal["pregnant"] = pregnant
            animal["days_pregnant"] = days_pregnant
        dry = pregnant and days_pregnant >= self.gestation - self.dry_period
        animal.setdefault("dry", dry)
        animal.setdefault("lactating", not animal["dry"])
        if pregnant:
            animal.setdefault("repro_state", REPRO_PREGNANT)
            animal.setdefault("conceived_dim", max(1, dim - days_pregnant))
        elif dim < self.vwp_cows:
            animal.setdefault("repro_state", REPRO_VWP)
        elif dim > self.dnb_dim:
            animal.setdefault("repro_state", REPRO_DNB)
        else:
            animal.setdefault("repro_state", REPRO_OPEN)

    def initial_heifers(self, cow_count: int) -> list[dict[str, Any]]:
        """Replacement heifers present at the start, spread over rearing ages."""
        ratio = float(_param(self.ctx, "initial_heifers_per_cow"))
        count = int(round(cow_count * ratio))
        rng = self.ctx.rng
        rearing_days = self.heifer_breeding_age + 60 + self.gestation
        heifers = []
        for _ in range(count):
            age = rng.randint(self.calf_sale_age + 1, rearing_days)
            heifer = {
                "id": self.next_id("heifer"),
                "sex": "female",
                "parity": 0,
                "days_in_milk": 0,
                "age_days": age,
                "body_weight_kg": self.heifer_bw_birth + self.heifer_growth * age,
                "pregnant": False,
                "days_pregnant": 0,
            }
            conception_age = self.heifer_breeding_age + 55
            if age > conception_age:
                heifer["pregnant"] = True
                heifer["days_pregnant"] = min(self.gestation - 1, age - conception_age)
            heifers.append(heifer)
        return heifers

    # ------------------------------------------------------------- day driver
    def begin_day(self) -> None:
        self.today = {}
        self.calvings: list[dict[str, Any]] = []

    def heifer_day(self, heifer: dict[str, Any], day: date) -> None:
        """Rearing, breeding, sale, and removal of one female calf or heifer."""
        rng = self.ctx.rng
        heifer["age_days"] = int(heifer.get("age_days", 0)) + 1
        age = heifer["age_days"]
        heifer["body_weight_kg"] = self.heifer_bw_birth + self.heifer_growth * age
        if not heifer.get("sale_decided", True) and age >= self.calf_sale_age:
            heifer["sale_decided"] = True
            if rng.random() < self.calf_sale_fraction:
                self._remove(heifer, "female_calf_sold")
                self._stat("heifers_sold")
                return
        self._stat("present_heifer_days")
        if rng.random() < self.h_death_heifers:
            self._remove(heifer, "heifer_died")
            return
        if rng.random() < self.h_cull_heifers:
            self._stat("heifers_culled_death_and_rebalance", float(heifer["body_weight_kg"]))
            self._remove(heifer, "heifer_culled")
            return
        if heifer.get("pregnant"):
            self._pregnancy_day(heifer, is_heifer=True)
            return
        heifer["_ovulated_today"] = self.advance_cycle(heifer)
        if age < self.heifer_breeding_age:
            return
        if age >= self.barren_heifer_age:
            self._stat("heifers_culled_live")
            self._remove(heifer, "barren_heifer_culled")
            return
        self._stat("heat_detection_eligible_days_heifers")
        self._estrus_day(heifer, is_heifer=True)

    def cow_day(self, cow: dict[str, Any], milk_kg: float, dmi_kg: float, day: date) -> None:
        """Account one adult cow-day and advance reproduction, dry-off, and culling."""
        rng = self.ctx.rng
        self._stat("present_cow_days")
        parity_index = min(max(int(cow.get("parity", 1)), 1), 4) - 1
        if cow.get("lactating"):
            self._stat("milking_cow_days")
            self._stat("milk_kg", milk_kg)
            self._stat("fat_kg", milk_kg * self.fat_fraction)
            self._stat("protein_kg", milk_kg * self.protein_fraction)
            self._stat("dmi_wet_kg", dmi_kg)
            self._stat("days_in_milk_sum", float(cow.get("days_in_milk", 0)))
            if cow.get("pregnant"):
                self._stat("pregnant_wet_days")
            if rng.random() < self.mastitis_rates[parity_index] / 365.0:
                self._mastitis_case(cow, parity_index)
            self._stat(f"_milking_days_par{parity_index + 1}")
        else:
            self._stat("dry_cow_days")
            self._stat("dmi_dry_kg", dmi_kg)
        self._stat("pregnant_cow_days" if cow.get("pregnant") else "open_cow_days")
        if rng.random() < self.h_death_cows:
            self._remove(cow, "cow_died")
            self._stat("cows_died")
            return
        if rng.random() < self.h_cull_cows:
            self._remove(cow, "cow_culled_involuntary")
            self._stat("cows_culled_live")
            return
        state = cow.get("repro_state", REPRO_OPEN)
        dim = int(cow.get("days_in_milk", 0))
        if state in (REPRO_VWP, REPRO_OPEN):
            cow["_ovulated_today"] = self.advance_cycle(cow)
            if dim >= self.rate_eligibility_dim and state == REPRO_VWP:
                # Workbook 21-day rate statistics start before the VWP ends.
                self._stat("eligible_days35_cows")
                if cow["_ovulated_today"]:
                    self._stat("estrus_cycles_cows")
        if state == REPRO_VWP:
            self._stat("vwp_days")
            if dim >= self.vwp_cows:
                cow["repro_state"] = state = REPRO_OPEN
        if state == REPRO_OPEN:
            if dim > self.dnb_dim:
                cow["repro_state"] = state = REPRO_DNB
            else:
                self._stat("eligible_days")
                self._stat("eligible_days35_cows")
                self._stat("heat_detection_eligible_days_cows")
                self._estrus_day(cow, is_heifer=False)
        elif state == REPRO_PREGNANT:
            if int(cow.get("days_pregnant", 0)) <= self.pregchecks[0]:
                self._stat("heat_detection_eligible_days_cows")
            self._pregnancy_day(cow, is_heifer=False)
        if state == REPRO_DNB:
            self._stat("dnb_days")
            if cow.get("lactating") and milk_kg < self.cull_milk_kg:
                self._remove(cow, "cow_culled_end_of_lactation")
                self._stat("cows_culled_live")
                return
        if cow.get("lactating") and cow.get("pregnant") and int(cow.get("days_pregnant", 0)) >= self.gestation - self.dry_period:
            if int(cow.get("parity", 1)) >= self.max_parity:
                self._remove(cow, "cow_culled_last_parity")
                self._stat("cows_culled_live")
                return
            cow["lactating"] = False
            cow["dry"] = True

    # ---------------------------------------------------------- reproduction
    def advance_cycle(self, animal: dict[str, Any]) -> bool:
        """Advance the ovarian cycle one day; return True on an ovulation day.

        Cycles run continuously for open animals (including the VWP) so the
        first eligible estrus after the VWP falls at a random cycle phase.
        """
        animal["days_to_ovulation"] = int(animal.get("days_to_ovulation", 1)) - 1
        if animal["days_to_ovulation"] > 0:
            return False
        animal["days_to_ovulation"] = self._ovulation_interval()
        return True

    def _estrus_day(self, animal: dict[str, Any], is_heifer: bool) -> None:
        rng = self.ctx.rng
        if not animal.pop("_ovulated_today", False):
            return
        if not is_heifer:
            self._stat("estrus_cycles_cows")
        first = int(animal.get("inseminations", 0)) == 0
        if first and not is_heifer:
            # First service after the VWP (calibrated submission rate).
            if rng.random() >= self.p_first_service:
                return
        else:
            if rng.random() >= self.p_estrus_expression:
                return
            if rng.random() >= (self.p_insem_heifers if is_heifer else self.p_insem_cows):
                return
        # Insemination with conventional semen (AIRAND strategy).
        animal["inseminations"] = int(animal.get("inseminations", 0)) + 1
        if is_heifer:
            self._stat("conventional_inseminations_heifers")
        else:
            self._stat("conventional_inseminations_cows")
            self._stat("estrus_inseminations_cows")
            self._stat("inseminations35_cows")
            dim = int(animal.get("days_in_milk", 0))
            if first:
                self._stat("first_inseminations_cows")
                self._stat("days_first_insemination_sum", float(dim))
            else:
                last = animal.get("last_insemination_dim")
                if isinstance(last, int):
                    self._stat("reinseminations_cows")
                    self._stat("days_between_reinseminations_sum", float(dim - last))
            animal["last_insemination_dim"] = dim
        if rng.random() < (self.p_concept_heifers if is_heifer else self.p_concept_cows) * self.conception_multiplier_today:
            animal["pregnant"] = True
            animal["days_pregnant"] = 0
            animal["repro_state"] = REPRO_PREGNANT
            animal["reproduction_event_flag"] = "conception"
            history = animal.setdefault("reproduction_history", [])
            history.append({"event": "conception"})
            self._stat("_dam_age_at_conception_sum", float(animal.get("age_days", 0)))
            self._stat("_dam_conceptions", 1.0)
            if not is_heifer:
                dim = int(animal.get("days_in_milk", 0))
                animal["conceived_dim"] = dim
                self._stat("conceptions0_cows")
                self._stat("conceptions35_cows")
                self._stat("days_open_sum", float(dim))
            self._stat("_conceptions_total")

    def _pregnancy_day(self, animal: dict[str, Any], is_heifer: bool) -> None:
        rng = self.ctx.rng
        animal["days_pregnant"] = int(animal.get("days_pregnant", 0)) + 1
        dp = animal["days_pregnant"]
        for index, check_day in enumerate(self.pregchecks):
            if dp == check_day:
                self._stat(f"pregchecks_{index + 2}")
        # Pregnancy loss spread evenly between the first and last check.
        span = max(1, self.pregchecks[-1] - self.pregchecks[0])
        loss = self.loss_heifers if is_heifer else self.loss_cows
        if self.pregchecks[0] < dp <= self.pregchecks[-1] and rng.random() < 1.0 - pow(1.0 - loss, 1.0 / span):
            animal["pregnant"] = False
            animal["days_pregnant"] = 0
            animal["repro_state"] = REPRO_OPEN
            animal["days_to_ovulation"] = self._ovulation_interval()
            self._stat("_abortions")
            return
        if dp >= self.gestation:
            self.calvings.append(animal)

    def _mastitis_case(self, cow: dict[str, Any], parity_index: int) -> None:
        rng = self.ctx.rng
        cow["mastitis_cases"] = int(cow.get("mastitis_cases", 0)) + 1
        self._stat(f"_mastitis_cases_par{parity_index + 1}")
        draw = rng.random()
        if draw < self.gram_pos_share:
            self._stat("mastitis_gram_positive_cases")
            self._stat("antibiotic_daily_doses", self.add_per_gram_pos)
            kind = "gram_positive"
        elif draw < self.gram_pos_share + self.gram_neg_share:
            self._stat("mastitis_gram_negative_cases")
            kind = "gram_negative"
        else:
            self._stat("mastitis_other_cases")
            kind = "other"
        cow["clinical_mastitis_today"] = kind
        if cow.get("infection_state", "S") != "I":
            # Hand the case to the Disease agent's compartment state so the
            # daily milk-loss and recovery rules apply.
            cow["infection_state"] = "I"
            cow["health_status"] = "sick"
            cow["disease"] = "mastitis"
            cow["days_infected"] = 0

    # --------------------------------------------------------------- calving
    def process_calvings(
        self, day: date, make_calf: Callable[[dict[str, Any], str], dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Calve every animal that reached term today and return retained female calves."""
        rng = self.ctx.rng
        calves: list[dict[str, Any]] = []
        for dam in self.calvings:
            if not dam.get("alive", True):
                continue
            first_calving = int(dam.get("parity", 0)) == 0
            self._stat("_calvings_heifers" if first_calving else "_calvings_cows")
            if first_calving:
                self._stat("_age_at_first_calving_sum", float(dam.get("age_days", 0)))
            dam["pregnant"] = False
            dam["days_pregnant"] = 0
            dam["parity"] = int(dam.get("parity", 0)) + 1
            dam["days_in_milk"] = 0
            dam["lactating"] = True
            dam["dry"] = False
            dam["category"] = "cow"
            dam["repro_state"] = REPRO_VWP
            dam["inseminations"] = 0
            dam["last_insemination_dim"] = None
            dam["conceived_dim"] = None
            dam["calving_interval_days"] = 0
            dam["days_to_ovulation"] = self._ovulation_interval()
            dam["reproduction_event_flag"] = "first_calving" if first_calving else "calving"
            dam.setdefault("reproduction_history", []).append({"day": day.isoformat(), "event": dam["reproduction_event_flag"]})
            if rng.random() < self.stillbirth:
                continue
            if rng.random() < self.male_fraction:
                self._stat("male_calves_born")
                continue
            self._stat("female_calves_born")
            calf = make_calf(dam, "female")
            calf["sale_decided"] = False
            calves.append(calf)
        self.calvings = []
        return calves

    # ------------------------------------------------------------ rebalance
    def rebalance(self, cows: list[dict[str, Any]]) -> int:
        """Cull surplus adult cows above capacity (workbook 'culling to rebalance')."""
        if self.capacity <= 0:
            return 0
        adults = [cow for cow in cows if cow.get("alive", True) and int(cow.get("parity", 0)) >= 1]
        surplus = len(adults) - self.capacity
        if surplus <= 0:
            return 0
        # The AIRAND strategy culls on parent-average NM$ EBV, which is not
        # related to parity in a herd without a genetic trend, so surplus cows
        # are drawn at random: do-not-breed cows first, then open cows, then
        # pregnant lactating cows (dry cows are kept to calve).
        rng = self.ctx.rng
        dnb = [cow for cow in adults if cow.get("repro_state") == REPRO_DNB]
        open_cows = [cow for cow in adults if cow.get("repro_state") in (REPRO_VWP, REPRO_OPEN)]
        pregnant = [cow for cow in adults if cow.get("repro_state") == REPRO_PREGNANT and cow.get("lactating")]
        rng.shuffle(open_cows)
        rng.shuffle(pregnant)
        for cow in (dnb + open_cows + pregnant)[:surplus]:
            self._remove(cow, "cow_culled_rebalance")
            self._stat("cows_culled_to_rebalance")
        return surplus

    def needs_purchase(self, cows: list[dict[str, Any]]) -> int:
        """Number of replacement heifers to buy when the herd falls below the threshold."""
        if self.capacity <= 0:
            return 0
        adults = sum(1 for cow in cows if cow.get("alive", True) and int(cow.get("parity", 0)) >= 1)
        floor = int(self.capacity * self.purchase_threshold)
        return max(0, floor - adults)

    def record_purchase(self, count: int) -> None:
        self._stat("new_animals_purchased", float(count))

    # -------------------------------------------------------------- removal
    def _remove(self, animal: dict[str, Any], reason: str) -> None:
        animal["alive"] = False
        animal["lactating"] = False
        animal["removal_reason"] = reason
        removals = self.ctx.state["herd_removals"]
        key = {
            "cow_died": "cows_died",
            "cow_culled_involuntary": "cows_culled_live",
            "cow_culled_end_of_lactation": "cows_culled_live",
            "cow_culled_last_parity": "cows_culled_live",
            "cow_culled_rebalance": "cows_culled_rebalance",
            "heifer_died": "heifers_died",
            "heifer_culled": "heifers_culled",
            "barren_heifer_culled": "heifers_culled",
            "female_calf_sold": "calves_sold",
        }.get(reason)
        if key:
            removals[key] = removals.get(key, 0) + 1

    # ---------------------------------------------------------- accumulation
    def end_day(self, day: date) -> dict[str, float]:
        """Fold today's statistics into the calendar-year accumulator and return them."""
        year_stats = self.ctx.state["herd_year_stats"].setdefault(str(day.year), {"days": 0})
        year_stats["days"] += 1
        for name, amount in self.today.items():
            year_stats[name] = year_stats.get(name, 0.0) + amount
        return dict(self.today)


def annual_workbook_inputs(ctx, year_stats: dict[str, float]) -> dict[str, float]:
    """Map one year's accumulated statistics onto the workbook's economics inputs."""
    inputs = {name: float(year_stats.get(name, 0.0)) for name in INPUT_REFS}
    present = inputs["present_cow_days"]
    herd = lambda key: float(value(ctx.calibration, f"herd.{key}"))  # noqa: E731
    inputs["avg_weighted_scs"] = herd("average_scs")
    inputs["profit_deviation_cows"] = herd("profit_deviation_cows_per_cow_year") * present / 365.0
    inputs["profit_deviation_heifers"] = herd("profit_deviation_heifers_per_cow_year") * present / 365.0
    # Mean dam age when each embryo is created (conception), herd-program raw row 809.
    conceptions = float(year_stats.get("_dam_conceptions", 0.0))
    inputs["age_of_dam_at_creation_days"] = (
        float(year_stats.get("_dam_age_at_conception_sum", 0.0)) / conceptions if conceptions else 0.0
    )
    # Workbook agg row 585: average over parities of cases / (milking cow-days / 365).
    incidences = []
    for parity in range(1, 5):
        days = float(year_stats.get(f"_milking_days_par{parity}", 0.0))
        cases = float(year_stats.get(f"_mastitis_cases_par{parity}", 0.0))
        if days > 0:
            incidences.append(cases / (days / 365.0))
    inputs["mastitis_incidence"] = sum(incidences) / len(incidences) if incidences else 0.0
    return inputs


def wood_shape(dim: int, b: float, c: float) -> float:
    """Wood's lactation curve normalised to 1 at its peak (dim = b / c)."""
    d = max(1.0, float(dim))
    if b <= 0.0 or c <= 0.0:
        return 1.0
    return exp(b * log(d) - c * d - (b * log(b / c) - b))
