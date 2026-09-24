"""Line-by-line port of the Cdairy workbook's per-cow economics layer.

Source: ``Cdairy_mc_kk_current_PS_CM_Strategies.xlsm``, sheet ``Stats_MAST``.
In that sheet each strategy block turns yearly herd statistics (produced by an
external Monte Carlo herd program) into per-cow/year economics in the column
labelled ``AW`` (formulas in ``AX``..``BQ``, one column per simulated year) with
unit prices in column ``BV``. Row numbers below refer to strategy block 1
(``MAST_AIRAND``); the other blocks repeat the same layout 78 columns to the
right.

Nothing in this module invents a coefficient. Every formula mirrors one
workbook cell so that feeding the workbook's own herd statistics reproduces the
workbook's outputs exactly (see ``tests/test_cdairy_economics.py``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from dairy_abm.config import value
from dairy_abm.core import ConfigError

# Herd-statistic inputs. Each entry is (column kind, rows summed). "agg" means
# the block's aggregated statistics columns (AA..AT), "raw" means the imported
# herd-program columns (C..V). Both columns hold one value per simulated year.
INPUT_REFS: dict[str, tuple[str, tuple[int, ...]]] = {
    "milk_kg": ("agg", (15,)),
    "fat_kg": ("agg", (16,)),
    "protein_kg": ("agg", (17,)),
    "avg_weighted_scs": ("agg", (19,)),
    "present_cow_days": ("agg", (20,)),
    "milking_cow_days": ("agg", (21,)),
    "dry_cow_days": ("agg", (22,)),
    "open_cow_days": ("agg", (23,)),
    "pregnant_cow_days": ("agg", (24,)),
    "conceptions35_cows": ("agg", (27,)),
    "heat_detection_eligible_days_cows": ("agg", (28, 29, 30, 31, 32, 33)),
    "heat_detection_eligible_days_heifers": ("agg", (34, 35, 36, 37, 38, 39)),
    "conventional_inseminations_cows": ("agg", (41, 42)),
    "estrus_inseminations_cows": ("agg", (41,)),
    "sexed_inseminations_cows": ("agg", (43,)),
    "conventional_inseminations_heifers": ("agg", (44, 45)),
    "sexed_inseminations_heifers": ("agg", (46,)),
    "presynch_cows": ("agg", (48,)),
    "presynch_heifers": ("agg", (53,)),
    "firstsynch_heifers": ("agg", (54,)),
    "resynch_f_heifers": ("agg", (55,)),
    "resynch_s_heifers": ("agg", (56,)),
    "pregchecks_1": ("agg", (57,)),
    "pregchecks_2": ("agg", (58,)),
    "pregchecks_3": ("agg", (59,)),
    "pregchecks_4": ("agg", (60,)),
    "cows_died": ("agg", (65,)),
    "cows_culled_live": ("agg", (66, 67, 68)),
    "heifers_culled_death_and_rebalance": ("agg", (70, 72)),
    "heifers_culled_live": ("agg", (71,)),
    "dmi_wet_kg": ("agg", (73,)),
    "dmi_dry_kg": ("agg", (74,)),
    "days_open_sum": ("agg", (75,)),
    "days_first_insemination_sum": ("agg", (76,)),
    "first_inseminations_cows": ("agg", (77,)),
    "days_between_reinseminations_sum": ("agg", (78,)),
    "reinseminations_cows": ("agg", (79,)),
    "days_in_milk_sum": ("agg", (80,)),
    "eligible_days35_cows": ("agg", (81,)),
    "inseminations35_cows": ("agg", (82,)),
    "vwp_days": ("agg", (84,)),
    "eligible_days": ("agg", (85,)),
    "dnb_days": ("agg", (86,)),
    "pregnant_wet_days": ("agg", (88,)),
    "estrus_cycles_cows": ("agg", (89,)),
    "cows_culled_to_rebalance": ("agg", (90,)),
    "new_animals_purchased": ("agg", (91,)),
    "conceptions0_cows": ("agg", (92,)),
    "frozen_embryo_transfers_cows": ("agg", (471,)),
    "embryo_donor_heifers": ("agg", (537,)),
    "embryo_donor_cows": ("agg", (542,)),
    "fresh_embryo_transfers_heifers": ("agg", (556,)),
    "frozen_embryo_transfers_heifers": ("agg", (559,)),
    "fresh_embryo_transfers_cows": ("agg", (568,)),
    "embryos_left_inventory": ("agg", (572,)),
    "mastitis_incidence": ("agg", (585,)),
    "antibiotic_daily_doses": ("agg", (587,)),
    "present_heifer_days": ("raw", (20,)),
    "male_calves_born": ("raw", (50,)),
    "female_calves_born": ("raw", (51,)),
    "genomic_tests": ("raw", (519,)),
    "profit_deviation_heifers": ("raw", (531,)),
    "profit_deviation_cows": ("raw", (532, 533, 534, 535)),
    "heifers_sold": ("raw", (363,)),
    "age_of_dam_at_creation_days": ("raw", (809,)),
    "mastitis_gram_positive_cases": ("raw", (1017, 1018, 1019, 1020, 1021)),
    "mastitis_gram_negative_cases": ("raw", (1022, 1023, 1024, 1025, 1026)),
    "mastitis_other_cases": ("raw", (1027, 1028, 1029, 1030, 1031)),
}

# Unit prices: calibration key suffix -> workbook price cell (column BV).
PRICE_CELLS: dict[str, int] = {
    "profit_deviation_adjustment": 10,
    "milk_price_per_kg": 12,
    "fat_price_per_kg": 13,
    "protein_price_per_kg": 14,
    "scs_penalty": 15,
    "cull_cow_value": 16,
    "bull_calf_value": 17,
    "female_calf_value": 18,
    "dmi_wet_price_per_kg": 19,
    "dmi_dry_price_per_kg": 20,
    "presynch_cost": 21,
    "firstsynch_cost": 22,
    "resynch_f_cost": 23,
    "resynch_s_cost": 24,
    "pregnancy_diagnosis_1_cost": 25,
    "pregnancy_diagnosis_2_cost": 26,
    "pregnancy_diagnosis_3_cost": 27,
    "pregnancy_diagnosis_4_cost": 28,
    "ai_cost": 29,
    "sexed_semen_cost": 30,
    "donor_cow_cost": 31,
    "donor_heifer_cost": 32,
    "fresh_embryo_cost": 33,
    "frozen_embryo_cost": 34,
    "vwp_cow_day_cost": 35,
    "eligible_cow_day_cost": 36,
    "dnb_cow_day_cost": 37,
    "pregnant_wet_cow_day_cost": 38,
    "milking_cow_day_cost": 39,
    "dry_cow_day_cost": 40,
    "replacement_heifer_cost": 41,
    "fixed_cost_per_cow_day": 42,
    "genomic_testing_cost": 43,
    "heifer_raising_cost_per_day": 44,
    "cull_price_per_kg": 45,
    "heat_detection_cost_per_cow_day": 46,
    "heat_detection_cost_per_heifer_day": 47,
    "extra_embryo_sale_price": 48,
    "gram_positive_mastitis_cost": 49,
    "gram_negative_mastitis_cost": 50,
    "other_mastitis_cost": 51,
    "dry_cow_therapy_cost": 52,
}

# Tables!P64 multiplies year-15 profit by this literal to report NPV.
YEAR15_NPV_FACTOR = 0.48


@dataclass(frozen=True)
class CdairyPrices:
    """Workbook unit prices keyed by the names in ``PRICE_CELLS``."""

    values: Mapping[str, float]

    def __getitem__(self, name: str) -> float:
        return float(self.values[name])

    @classmethod
    def from_calibration(cls, calibration: dict[str, Any]) -> "CdairyPrices":
        """Read every workbook price from the ``cdairy_economics`` calibration group."""
        return cls({name: float(value(calibration, f"cdairy_economics.{name}")) for name in PRICE_CELLS})


def _require(inputs: Mapping[str, float], name: str) -> float:
    if name not in inputs:
        raise ConfigError(f"cdairy economics input missing: {name}")
    return float(inputs[name])


def per_cow_year_economics(inputs: Mapping[str, float], prices: CdairyPrices) -> dict[str, float]:
    """Return the Stats_MAST AW rows 12-52 for one simulated year.

    ``inputs`` holds herd totals for that year under the names in ``INPUT_REFS``.
    Monetary rows are per average present cow per year, as in the workbook
    ("per cow/year" measure, Stats_MAST!AV1).
    """
    present = _require(inputs, "present_cow_days")
    if present <= 0.0:
        raise ConfigError("present_cow_days must be positive")
    # Row 1 / row 9: per cow/year multiplier.
    return _economics(inputs, prices, 1.0 / present * 365.0)


def herd_total_economics(inputs: Mapping[str, float], prices: CdairyPrices) -> dict[str, float]:
    """Return the same rows as herd totals (multiplier 1) for any accounting period.

    Every workbook row is linear in the herd counts once the average SCS is
    fixed, so daily herd totals computed here add up exactly to the annual
    per-cow result multiplied by the average number of present cows.
    """
    return _economics(inputs, prices, 1.0)


def _economics(inputs: Mapping[str, float], prices: CdairyPrices, mult: float) -> dict[str, float]:
    get = lambda name: _require(inputs, name)  # noqa: E731
    out: dict[str, float] = {"multiplier": mult}
    out["milk_yield_kg"] = get("milk_kg") * mult  # row 12
    out["fat_yield_kg"] = get("fat_kg") * mult  # row 13
    out["protein_yield_kg"] = get("protein_kg") * mult  # row 14
    out["scc_deviation_thousands"] = ((2 ** (get("avg_weighted_scs") - 3) * 100000) - 200000) / 1000  # row 15
    out["milk_sales"] = out["milk_yield_kg"] * prices["milk_price_per_kg"]  # row 16
    out["fat_sales"] = out["fat_yield_kg"] * prices["fat_price_per_kg"]  # row 17
    out["protein_sales"] = out["protein_yield_kg"] * prices["protein_price_per_kg"]  # row 18
    out["scs_deviation"] = (out["scc_deviation_thousands"] * prices["scs_penalty"]) * out["milk_yield_kg"]  # row 19
    out["cow_sales"] = (get("cows_culled_live") + get("cows_culled_to_rebalance")) * prices["cull_cow_value"] * mult  # row 20
    out["bull_calf_sales"] = get("male_calves_born") * prices["bull_calf_value"] * mult  # row 21
    out["female_calf_sales"] = get("heifers_sold") * prices["female_calf_value"] * mult  # row 22
    out["profit_deviation_cows"] = get("profit_deviation_cows") * mult  # row 23
    out["other_heifer_sales"] = (  # row 24
        get("heifers_culled_death_and_rebalance") * prices["cull_price_per_kg"]
        + get("heifers_culled_live") * prices["cull_cow_value"]
    ) * mult
    out["profit_deviation_heifers"] = get("profit_deviation_heifers") * mult  # row 25
    out["extra_embryo_sales"] = (get("embryos_left_inventory") * prices["extra_embryo_sale_price"]) * mult  # row 26
    out["revenues"] = (  # row 27
        out["milk_sales"] + out["fat_sales"] + out["protein_sales"] + out["scs_deviation"]
        + out["cow_sales"] + out["bull_calf_sales"]
        + (out["female_calf_sales"] + out["profit_deviation_cows"] + out["other_heifer_sales"]
           + out["profit_deviation_heifers"] + out["extra_embryo_sales"]) * prices["profit_deviation_adjustment"]
    )
    out["wet_feed_cost"] = get("dmi_wet_kg") * prices["dmi_wet_price_per_kg"] * mult  # row 28
    out["dry_feed_cost"] = get("dmi_dry_kg") * prices["dmi_dry_price_per_kg"] * mult  # row 29
    out["open_pregnant_wet_cost"] = (  # row 30
        get("vwp_days") * prices["vwp_cow_day_cost"]
        + get("eligible_days") * prices["eligible_cow_day_cost"]
        + get("dnb_days") * prices["dnb_cow_day_cost"]
        + get("pregnant_wet_days") * prices["pregnant_wet_cow_day_cost"]
    ) * mult
    out["milking_dry_cost"] = (  # row 31
        get("milking_cow_days") * prices["milking_cow_day_cost"] + get("dry_cow_days") * prices["dry_cow_day_cost"]
    ) * mult
    out["embryo_donor_cost"] = (  # row 32
        get("embryo_donor_heifers") * prices["donor_heifer_cost"] + get("embryo_donor_cows") * prices["donor_cow_cost"]
    ) * mult
    out["breeding_cost_cows"] = (  # row 33
        get("conventional_inseminations_cows") * prices["ai_cost"]
        + get("sexed_inseminations_cows") * prices["sexed_semen_cost"]
        + (get("fresh_embryo_transfers_cows") * prices["fresh_embryo_cost"]
           + get("frozen_embryo_transfers_cows") * prices["frozen_embryo_cost"])
    ) * mult
    out["heat_detection_cost_cows"] = get("heat_detection_eligible_days_cows") * prices["heat_detection_cost_per_cow_day"] * mult  # row 34
    out["pregnancy_diagnosis_cost"] = (  # row 35
        get("pregchecks_1") * prices["pregnancy_diagnosis_1_cost"]
        + get("pregchecks_2") * prices["pregnancy_diagnosis_2_cost"]
        + get("pregchecks_3") * prices["pregnancy_diagnosis_3_cost"]
        + get("pregchecks_4") * prices["pregnancy_diagnosis_4_cost"]
    ) * mult
    out["presynch_cost_cows"] = get("presynch_cows") * prices["presynch_cost"] * mult  # row 36
    out["dry_cow_therapy_cost"] = (get("dry_cow_days") / 60) * mult * prices["dry_cow_therapy_cost"]  # row 37
    out["mastitis_treatment_cost"] = (  # row 38
        get("mastitis_gram_positive_cases") * prices["gram_positive_mastitis_cost"]
        + get("mastitis_gram_negative_cases") * prices["gram_negative_mastitis_cost"]
        + get("mastitis_other_cases") * prices["other_mastitis_cost"]
    ) * mult
    out["heifer_raised_cost"] = get("present_heifer_days") * mult * prices["heifer_raising_cost_per_day"]  # row 39
    out["heifer_purchased_cost"] = get("new_animals_purchased") * prices["replacement_heifer_cost"] * mult  # row 40
    out["genomic_testing_cost"] = get("genomic_tests") * prices["genomic_testing_cost"] * mult  # row 41
    out["breeding_cost_heifers"] = (  # row 42
        get("conventional_inseminations_heifers") * prices["ai_cost"]
        + get("sexed_inseminations_heifers") * prices["sexed_semen_cost"]
        + (get("fresh_embryo_transfers_heifers") * prices["fresh_embryo_cost"]
           + get("frozen_embryo_transfers_heifers") * prices["frozen_embryo_cost"])
    ) * mult
    out["presynch_cost_heifers"] = get("presynch_heifers") * prices["presynch_cost"] * mult  # row 43
    out["firstsynch_cost_heifers"] = get("firstsynch_heifers") * prices["firstsynch_cost"] * mult  # row 44
    out["resynch_cost_heifers"] = (  # row 45
        get("resynch_f_heifers") * prices["resynch_f_cost"] + get("resynch_s_heifers") * prices["resynch_s_cost"]
    ) * mult
    out["heat_detection_cost_heifers"] = get("heat_detection_eligible_days_heifers") * mult * prices["heat_detection_cost_per_heifer_day"]  # row 46
    variable_rows = (
        "wet_feed_cost", "dry_feed_cost", "open_pregnant_wet_cost", "milking_dry_cost", "embryo_donor_cost",
        "breeding_cost_cows", "heat_detection_cost_cows", "pregnancy_diagnosis_cost", "presynch_cost_cows",
        "dry_cow_therapy_cost", "mastitis_treatment_cost", "heifer_raised_cost", "heifer_purchased_cost",
        "genomic_testing_cost", "breeding_cost_heifers", "presynch_cost_heifers", "firstsynch_cost_heifers",
        "resynch_cost_heifers", "heat_detection_cost_heifers",
    )
    out["variable_costs"] = sum(out[name] for name in variable_rows)  # row 47
    out["milking_cows_ratio"] = (get("milking_cow_days") * mult) / 365  # row 50
    out["dry_cows_ratio"] = (get("dry_cow_days") * mult) / 365  # row 51
    out["total_cows_ratio"] = out["milking_cows_ratio"] + out["dry_cows_ratio"]  # row 52
    out["fixed_costs"] = out["total_cows_ratio"] * prices["fixed_cost_per_cow_day"] * 365  # row 48
    out["profit"] = out["revenues"] - out["variable_costs"] - out["fixed_costs"]  # row 49
    return out


def technical_performance(inputs: Mapping[str, float]) -> dict[str, float | None]:
    """Return the workbook's technical-performance rows (Stats_MAST AW 53-99 subset).

    These feed ``Tables`` rows 67-74 (Table 3, technical performance).
    """
    get = lambda name: _require(inputs, name)  # noqa: E731
    present = get("present_cow_days")
    mult = 365.0 / present if present > 0 else 0.0

    def ratio(num: float, den: float) -> float | None:
        return num / den if den else None

    return {
        "milk_yield_kg_per_cow_year": get("milk_kg") * mult,  # row 12
        "pct_milking_cows": ratio(get("milking_cow_days"), present),  # row 53
        "pct_dry_cows": ratio(get("dry_cow_days"), present),  # row 54
        "pct_open_cows": ratio(get("open_cow_days"), present),  # row 55
        "pct_pregnant_cows": ratio(get("pregnant_cow_days"), present),  # row 56
        "service_rate_21d_35": ratio(get("inseminations35_cows"), get("eligible_days35_cows") / 21),  # row 57
        "service_rate_21d": ratio(get("conventional_inseminations_cows"), get("estrus_cycles_cows")),  # row 58
        "conception_rate_35": ratio(get("conceptions35_cows"), get("inseminations35_cows")),  # row 65
        "pregnancy_rate_35": ratio(get("conceptions35_cows"), get("eligible_days35_cows") / 21),  # row 70
        "pregnancy_rate": ratio(get("conceptions35_cows"), get("estrus_cycles_cows")),  # row 71
        "annual_cull_rate": (get("cows_died") + get("cows_culled_live")) * mult + get("cows_culled_to_rebalance") * mult,  # row 72
        "days_to_first_service": ratio(get("days_first_insemination_sum"), get("first_inseminations_cows")),  # row 73
        "days_open": ratio(get("days_open_sum"), get("conceptions35_cows")),  # row 74
        "days_between_inseminations": ratio(get("days_between_reinseminations_sum"), get("reinseminations_cows")),  # row 75
        "days_in_milk": ratio(get("days_in_milk_sum"), get("milking_cow_days")),  # row 76
        "conception_rate_0": ratio(get("conceptions0_cows"), get("estrus_inseminations_cows")),  # row 79
        "surplus_female_calves_sold": ratio(get("heifers_sold"), get("female_calves_born")),  # row 99
        "age_of_dam_at_creation_days": get("age_of_dam_at_creation_days"),  # raw row 809
        "mastitis_incidence": get("mastitis_incidence"),  # agg row 585
        "antibiotic_daily_doses": get("antibiotic_daily_doses"),  # agg row 587
    }


def table4_summary(econ: Mapping[str, float], year15: bool) -> dict[str, float]:
    """Return Tables 'Table 4' (average revenues and costs) lines, Stats_MAST BN516-BN534."""
    revenue_lines = {
        "milk_component_sales": econ["milk_sales"] + econ["fat_sales"] + econ["protein_sales"] + econ["scs_deviation"],
        "cow_sales": econ["cow_sales"] + econ["other_heifer_sales"],
        # The ETNM$ column (BT518) also adds extra embryo sales (row 26); the
        # other strategy columns omit it, but it is zero for them.
        "calf_sales": econ["bull_calf_sales"] + econ["female_calf_sales"] + econ["extra_embryo_sales"],
        "profit_deviation": econ["profit_deviation_cows"] + econ["profit_deviation_heifers"],
    }
    cost_lines = {
        "feeding_cost": econ["wet_feed_cost"] + econ["dry_feed_cost"],
        "breeding_cost": econ["embryo_donor_cost"] + econ["breeding_cost_cows"] + econ["breeding_cost_heifers"],
        "pregnancy_diagnosis_and_heat_detection_cost": econ["heat_detection_cost_cows"] + econ["pregnancy_diagnosis_cost"] + econ["heat_detection_cost_heifers"],
        "other_variable_cost": econ["open_pregnant_wet_cost"] + econ["milking_dry_cost"],
        "heifer_raised_cost": econ["heifer_raised_cost"],
        "genomic_testing_cost": econ["genomic_testing_cost"],
        "clinical_mastitis_treatment_cost": econ["mastitis_treatment_cost"],
        "dry_cow_therapy_cost": econ["dry_cow_therapy_cost"],
        "fixed_costs": econ["fixed_costs"],
    }
    total_revenues = sum(revenue_lines.values())
    total_costs = sum(cost_lines.values())
    profit = total_revenues - total_costs
    return {
        **revenue_lines,
        "total_revenues": total_revenues,
        **cost_lines,
        "total_costs": total_costs,
        "profit": profit,
        # BO534 uses *1 for year 0 and BP534.. use *0.48 for year 15.
        "net_present_value": profit * (YEAR15_NPV_FACTOR if year15 else 1.0),
    }


def evaluate_year(inputs: Mapping[str, float], prices: CdairyPrices, year15: bool = False) -> dict[str, Any]:
    """Convenience wrapper returning economics, technical measures, and the Table 4 view."""
    econ = per_cow_year_economics(inputs, prices)
    return {
        "economics": econ,
        "technical": technical_performance(inputs),
        "table4": table4_summary(econ, year15),
    }
