"""Price model output with the Cdairy workbook formulas and compare it to the workbook.

Every run accumulates herd statistics per calendar year (``herd_lifecycle``).
This module turns each year into the workbook's per-cow/year economics,
technical-performance rows, and 'Table 4' lines, and compares the final
simulated year with the workbook's AIRAND year-15 results.

The workbook result is the mean of 1,000 stochastic replications of a 15-year
herd program; a single seeded run is one draw, so ``run_parity`` averages
several seeds before comparing.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

from dairy_abm.analysis.cdairy_economics import CdairyPrices, evaluate_year
from dairy_abm.core import read_json
from dairy_abm.herd_lifecycle import annual_workbook_inputs

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = ROOT / "configs" / "reference_targets" / "cdairy_stats_mast.json"
PUBLISHED_PATH = ROOT / "configs" / "reference_targets" / "cdairy_airand_year15.json"

# Absolute herd counts in the workbook refer to its ~1,158-cow herd, so they
# are compared per average present cow.
PER_COW_COUNTS = {"antibiotic_daily_doses"}

TECHNICAL_ROWS = (
    ("milk_yield_kg_per_cow_year", "Milk yield/cow/yr (kg)", "kg/cow/year"),
    ("pregnancy_rate_35", "Cow pregnancy rate (%)", "fraction"),
    ("conception_rate_35", "Cow conception rate", "fraction"),
    ("service_rate_21d_35", "21-day service rate", "fraction"),
    ("days_open", "Cow days open (d)", "days"),
    ("days_to_first_service", "Days to first service", "days"),
    ("days_in_milk", "Average days in milk", "days"),
    ("annual_cull_rate", "Annual cull rate (%)", "fraction"),
    ("surplus_female_calves_sold", "Surplus female calves (%)", "fraction"),
    ("age_of_dam_at_creation_days", "Age of dam at creation (d)", "days"),
    ("mastitis_incidence", "Mastitis incidence (%)", "cases/milking cow-year"),
    ("antibiotic_daily_doses", "Yearly antibiotic daily doses (per cow)", "doses/cow/year"),
    ("pct_milking_cows", "Milking cows (%)", "fraction"),
    ("pct_pregnant_cows", "Pregnant cows (%)", "fraction"),
)
TABLE4_ROWS = (
    ("milk_component_sales", "Milk component sales"),
    ("cow_sales", "Cow sales"),
    ("calf_sales", "Calf sales"),
    ("profit_deviation", "Profit deviation"),
    ("total_revenues", "Total revenues"),
    ("feeding_cost", "Feeding cost"),
    ("breeding_cost", "Breeding cost"),
    ("pregnancy_diagnosis_and_heat_detection_cost", "Pregnancy diagnosis and heat detection"),
    ("other_variable_cost", "Other variable cost"),
    ("heifer_raised_cost", "Heifer raised cost"),
    ("genomic_testing_cost", "Genomic testing cost"),
    ("clinical_mastitis_treatment_cost", "Clinical mastitis treatment"),
    ("dry_cow_therapy_cost", "Dry cow therapy"),
    ("fixed_costs", "Fixed costs"),
    ("total_costs", "Total costs"),
    ("profit", "Profit"),
    ("net_present_value", "Net present value of profit"),
)


def _fixture() -> dict[str, Any]:
    return read_json(FIXTURE_PATH)


def workbook_reference(strategy: str = "AIRAND") -> dict[str, Any]:
    """Return the workbook's year-15 economics, technical rows, and Table 4 for a strategy."""
    fixture = _fixture()
    block = fixture["strategies"][strategy]
    final = block["years"][-1]
    result = evaluate_year(final["inputs"], CdairyPrices(block["prices"]), True)
    present_cows = final["inputs"]["present_cow_days"] / 365.0
    technical = dict(result["technical"])
    technical["antibiotic_daily_doses"] = technical["antibiotic_daily_doses"] / present_cows
    return {
        "strategy": strategy,
        "experiment": block["experiment"],
        "year": final["year"],
        "present_cows": present_cows,
        "technical": technical,
        "table4": result["table4"],
        "economics": result["economics"],
    }


def annual_excel_economics(ctx) -> list[dict[str, Any]]:
    """Workbook-priced results for every simulated calendar year of a run."""
    prices = CdairyPrices.from_calibration(ctx.calibration)
    rows: list[dict[str, Any]] = []
    for year, stats in sorted(ctx.state.get("herd_year_stats", {}).items()):
        inputs = annual_workbook_inputs(ctx, stats)
        if inputs["present_cow_days"] <= 0.0:
            continue
        result = evaluate_year(inputs, prices, year15=False)
        present_cows = inputs["present_cow_days"] / float(stats.get("days", 365) or 365)
        technical = dict(result["technical"])
        technical["antibiotic_daily_doses"] = technical["antibiotic_daily_doses"] / (inputs["present_cow_days"] / 365.0)
        rows.append(
            {
                "year": int(year),
                "days": int(stats.get("days", 0)),
                "complete_year": int(stats.get("days", 0)) >= 365,
                "average_present_cows": present_cows,
                "technical": technical,
                "economics": result["economics"],
                "table4": result["table4"],
                "inputs": inputs,
            }
        )
    return rows


def _status(gap_fraction: float | None) -> str:
    if gap_fraction is None:
        return "unavailable"
    size = abs(gap_fraction)
    if size <= 0.02:
        return "match"
    if size <= 0.05:
        return "close"
    return "differs"


def compare_year(observed: dict[str, Any], reference: dict[str, Any]) -> dict[str, Any]:
    """Compare one workbook-priced model year with the workbook reference."""
    rows = []
    for key, label, unit in TECHNICAL_ROWS:
        rows.append(_row("technical", key, label, unit, observed["technical"].get(key), reference["technical"].get(key)))
    for key, label in TABLE4_ROWS:
        # NPV uses the workbook's year-15 discount literal on both sides.
        obs = observed["table4"].get(key)
        if key == "net_present_value" and obs is not None:
            obs = observed["table4"]["profit"] * 0.48
        rows.append(_row("economics", key, label, "currency/cow/year", obs, reference["table4"].get(key)))
    counts = {"match": 0, "close": 0, "differs": 0, "unavailable": 0}
    for row in rows:
        counts[row["status"]] += 1
    return {"rows": rows, "status_counts": counts}


def _row(group: str, key: str, label: str, unit: str, observed: float | None, target: float | None) -> dict[str, Any]:
    gap = observed - target if observed is not None and target is not None else None
    fraction = gap / abs(target) if gap is not None and target else (0.0 if gap == 0 else None)
    return {
        "group": group,
        "key": key,
        "label": label,
        "unit": unit,
        "target": target,
        "observed": observed,
        "absolute_gap": gap,
        "relative_gap_fraction": fraction,
        "status": _status(fraction),
    }


def run_parity(ctx) -> dict[str, Any] | None:
    """Summary block for one run: annual workbook economics plus the AIRAND comparison."""
    annual = annual_excel_economics(ctx)
    if not annual:
        return None
    complete = [row for row in annual if row["complete_year"]]
    compared = complete[-1] if complete else annual[-1]
    reference = workbook_reference("AIRAND")
    published = read_json(PUBLISHED_PATH)
    return {
        "source": {
            "workbook": "Cdairy_mc_kk_current_PS_CM_Strategies.xlsm",
            "sheet": "Stats_MAST",
            "strategy": "AIRAND",
            "reference_year": reference["year"],
            "replications": 1000,
        },
        "annual": [
            {key: row[key] for key in ("year", "days", "complete_year", "average_present_cows", "technical", "table4")}
            for row in annual
        ],
        "compared_year": compared["year"],
        "comparison": compare_year(compared, reference),
        "published_tables_note": (
            "The workbook's Tables sheet holds pasted values; for AIRAND its milk component sales "
            f"({published['metrics']['milk_component_sales_per_cow_year']['target']}) differ from the live "
            f"Stats_MAST formula result ({round(reference['table4']['milk_component_sales'], 2)}). "
            "Comparisons use the live Stats_MAST results."
        ),
        "limitations": [
            "The workbook's herd statistics come from an external Monte Carlo herd program; this model reproduces them by calibration, not by porting that program.",
            "A single seeded run is one stochastic draw; use `python3 -m dairy_abm parity` to average several seeds.",
            "Genetic profit deviation and herd SCS are taken from the workbook (herd.* calibration) because the herd program's formulas for them are not available.",
        ],
    }


def aggregate_seed_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Average the compared year of several seeded runs and compare the mean."""
    reference = workbook_reference("AIRAND")
    years = []
    for parity in runs:
        compared = next(row for row in parity["annual"] if row["year"] == parity["compared_year"])
        years.append(compared)
    averaged = {"technical": {}, "table4": {}}
    spread = {"technical": {}, "table4": {}}
    for group in ("technical", "table4"):
        keys = set().union(*(row[group].keys() for row in years))
        for key in keys:
            values = [row[group][key] for row in years if row[group].get(key) is not None]
            if values:
                averaged[group][key] = mean(values)
                spread[group][key] = pstdev(values) / (len(values) ** 0.5) if len(values) > 1 else None
    comparison = compare_year(deepcopy(averaged), reference)
    for row in comparison["rows"]:
        group = "technical" if row["group"] == "technical" else "table4"
        row["standard_error"] = spread[group].get(row["key"])
    return {"seeds": len(runs), "comparison": comparison}
