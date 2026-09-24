"""Extract the Cdairy workbook reference fixture used by the economics parity tests.

Usage (standard library only):

    python3 scripts/extract_cdairy_reference.py Cdairy_mc_kk_current_PS_CM_Strategies.xlsm \
        configs/reference_targets/cdairy_stats_mast.json

The script streams ``Stats_MAST`` (about 400 MB of XML) without loading it
whole, keeps only the cells the economics port reads, and records for every
strategy block and simulated year:

* ``inputs``   - herd statistics named as in ``dairy_abm.analysis.cdairy_economics.INPUT_REFS``
* ``expected`` - the workbook's cached per-cow/year results (column AW rows)
* ``prices``   - the block's unit prices (column BV)

The workbook itself is not modified.
"""

from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dairy_abm.analysis.cdairy_economics import INPUT_REFS, PRICE_CELLS  # noqa: E402

SHEET_PATH = "xl/worksheets/sheet4.xml"  # Stats_MAST (workbook rId4)
BLOCK_WIDTH = 78
STRATEGIES = ["AIRAND", "AINM$", "AIMAST", "SSNM$", "ETNM$"]
YEARS = list(range(-4, 16))  # Stats_MAST row 10: C=-4 .. V=15
MAX_ROW = 1300
MAX_COL = 400

# Workbook result rows (column AW labels) checked by the parity test.
EXPECTED_ROWS: dict[str, int] = {
    "multiplier": 9, "milk_yield_kg": 12, "fat_yield_kg": 13, "protein_yield_kg": 14,
    "scc_deviation_thousands": 15, "milk_sales": 16, "fat_sales": 17, "protein_sales": 18,
    "scs_deviation": 19, "cow_sales": 20, "bull_calf_sales": 21, "female_calf_sales": 22,
    "profit_deviation_cows": 23, "other_heifer_sales": 24, "profit_deviation_heifers": 25,
    "extra_embryo_sales": 26, "revenues": 27, "wet_feed_cost": 28, "dry_feed_cost": 29,
    "open_pregnant_wet_cost": 30, "milking_dry_cost": 31, "embryo_donor_cost": 32,
    "breeding_cost_cows": 33, "heat_detection_cost_cows": 34, "pregnancy_diagnosis_cost": 35,
    "presynch_cost_cows": 36, "dry_cow_therapy_cost": 37, "mastitis_treatment_cost": 38,
    "heifer_raised_cost": 39, "heifer_purchased_cost": 40, "genomic_testing_cost": 41,
    "breeding_cost_heifers": 42, "presynch_cost_heifers": 43, "firstsynch_cost_heifers": 44,
    "resynch_cost_heifers": 45, "heat_detection_cost_heifers": 46, "variable_costs": 47,
    "fixed_costs": 48, "profit": 49, "milking_cows_ratio": 50, "dry_cows_ratio": 51,
    "total_cows_ratio": 52,
    # technical performance
    "pct_milking_cows": 53, "pct_dry_cows": 54, "pct_open_cows": 55, "pct_pregnant_cows": 56,
    "service_rate_21d_35": 57, "service_rate_21d": 58, "conception_rate_35": 65,
    "pregnancy_rate_35": 70, "pregnancy_rate": 71, "annual_cull_rate": 72,
    "days_to_first_service": 73, "days_open": 74, "days_between_inseminations": 75,
    "days_in_milk": 76, "conception_rate_0": 79, "surplus_female_calves_sold": 99,
}


# Stats_MAST "Table 4" summary (BN labels): year-15 value per strategy in
# BP..BT, year-0 DEFAULT in BO. These feed the published Tables sheet.
TABLE4_ROWS: dict[str, int] = {
    "milk_component_sales": 516, "cow_sales": 517, "calf_sales": 518, "profit_deviation": 519,
    "total_revenues": 520, "feeding_cost": 522, "breeding_cost": 523,
    "pregnancy_diagnosis_and_heat_detection_cost": 524, "other_variable_cost": 525,
    "heifer_raised_cost": 526, "genomic_testing_cost": 527, "clinical_mastitis_treatment_cost": 528,
    "dry_cow_therapy_cost": 529, "fixed_costs": 530, "total_costs": 531, "profit": 533,
    "net_present_value": 534,
}
TABLE4_YEAR15_COLUMNS = ["BP", "BQ", "BR", "BS", "BT"]


def col_num(letters: str) -> int:
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n


def col_letters(n: int) -> str:
    out = ""
    while n:
        n, rem = divmod(n - 1, 26)
        out = chr(65 + rem) + out
    return out


def read_cells(xlsm: Path) -> dict[str, Any]:
    """Stream Stats_MAST and return cached cell values for rows <= MAX_ROW."""
    zf = zipfile.ZipFile(xlsm)
    shared = zf.read("xl/sharedStrings.xml").decode("utf-8")
    strings = [re.sub(r"<[^>]+>", "", s) for s in re.findall(r"<si>(.*?)</si>", shared, flags=re.S)]
    row_re = re.compile(r'<row [^>]*r="(\d+)"[^>]*>(.*?)</row>', re.S)
    cell_re = re.compile(r'<c r="([A-Z]+)(\d+)"([^>]*?)(?:/>|>(.*?)</c>)', re.S)
    cells: dict[str, Any] = {}
    buf = ""
    with zf.open(SHEET_PATH) as handle:
        while True:
            chunk = handle.read(8_000_000)
            if not chunk:
                break
            buf += chunk.decode("utf-8", "replace")
            cut = buf.rfind("</row>")
            if cut < 0:
                continue
            part, buf = buf[: cut + 6], buf[cut + 6 :]
            for row_number, body in row_re.findall(part):
                if int(row_number) > MAX_ROW:
                    return cells
                for col, row, attrs, inner in cell_re.findall(body):
                    if col_num(col) > MAX_COL:
                        continue
                    match = re.search(r"<v>(.*?)</v>", inner or "")
                    if match is None:
                        continue
                    raw = match.group(1)
                    if 't="s"' in attrs:
                        cells[col + row] = strings[int(raw)]
                    elif 't="str"' in attrs or 't="e"' in attrs:
                        cells[col + row] = raw
                    else:
                        try:
                            cells[col + row] = float(raw)
                        except ValueError:
                            cells[col + row] = raw
    return cells


def build_fixture(cells: dict[str, Any], workbook_name: str) -> dict[str, Any]:
    def num(ref: str) -> float:
        value = cells.get(ref, 0.0)
        return float(value) if isinstance(value, (int, float)) else 0.0

    strategies: dict[str, Any] = {}
    for block, strategy in enumerate(STRATEGIES):
        offset = block * BLOCK_WIDTH
        experiment = cells.get(f"{col_letters(col_num('C') + offset)}2")
        # Every block references the shared price column with absolute $BV refs.
        prices = {name: num(f"BV{row}") for name, row in PRICE_CELLS.items()}
        years: list[dict[str, Any]] = []
        for index, year in enumerate(YEARS):
            # Burn-in years (<= 0) of blocks 2-5 are formula copies of block 1
            # (e.g. Stats_MAST!DX12 = AX12), so their inputs come from block 1.
            source_offset = 0 if year <= 0 else offset
            columns = {
                "agg": col_letters(col_num("AA") + source_offset + index),
                "raw": col_letters(col_num("C") + source_offset + index),
            }
            econ_col = col_letters(col_num("AX") + offset + index)
            inputs = {
                name: sum(num(f"{columns[kind]}{row}") for row in rows)
                for name, (kind, rows) in INPUT_REFS.items()
            }
            expected = {}
            for name, row in EXPECTED_ROWS.items():
                value = cells.get(f"{econ_col}{row}")
                expected[name] = float(value) if isinstance(value, (int, float)) else None
            years.append({"year": year, "inputs": inputs, "expected": expected})
        table4 = {
            name: cells.get(f"{TABLE4_YEAR15_COLUMNS[block]}{row}") for name, row in TABLE4_ROWS.items()
        }
        strategies[strategy] = {
            "experiment": experiment,
            "prices": prices,
            "years": years,
            "table4_year15": table4,
        }
    return {
        "id": "cdairy_stats_mast",
        "source": {
            "workbook": workbook_name,
            "sheet": "Stats_MAST",
            "layout": "strategy blocks every 78 columns; inputs from AA..AT (aggregated) and C..V (raw); results in AX..BQ; prices in BV",
            "note": "Cached workbook values. Herd statistics come from an external Monte Carlo herd program imported by the workbook's macros.",
        },
        "years": YEARS,
        "table4_year0_default": {name: cells.get(f"BO{row}") for name, row in TABLE4_ROWS.items()},
        "strategies": strategies,
    }


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    xlsm, target = Path(argv[1]), Path(argv[2])
    fixture = build_fixture(read_cells(xlsm), xlsm.name)
    target.write_text(json.dumps(fixture, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {target} ({len(fixture['strategies'])} strategies x {len(YEARS)} years)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
