# AIRAND year-15 parity: eight seeded model runs

The comparison used `python3 -m dairy_abm parity --seeds 1,2,3,4,5,6,7,8` on 2026-09-24 (Python 3.14.7, macOS), after two rounds of fixes: the workbook feed charge in the ledger, parity-based body weight, manure routing gated by L1 and L3, deterministic trait inheritance, and per-cow ration coverage measured against each cow's own need, followed by a recalibration of `herd.milk_yield_scale` and `cow.dmi_level_calibration_factor` (see below). The source is the live `Stats_MAST` formulas in `Cdairy_mc_kk_current_PS_CM_Strategies.xlsm`, extracted to `configs/reference_targets/cdairy_stats_mast.json`. The model figure is the arithmetic mean of eight seeded runs. Standard error measures variation among those eight runs; it does not measure uncertainty in the workbook target. Full per-seed data and unrounded results are in `parity_results_8_seeds.json`.

Classification: **25 within 2%**, **4 more within 5%**, and **2 over 5%**. An exact-zero target is compared by absolute equality. These tolerances assess calibration agreement, not scientific validation.

Earlier results, for the record: the report before the fixes listed 21 / 4 / 6, but re-running that command on the pre-fix code on this machine gave 18 / 7 / 6 (milk -0.3%, profit -0.7%), so that table was not reproducible. After the first round of fixes the result was 22 / 7 / 2 (milk +0.1%, profit +1.7%).

## Recalibration after the ration-coverage fix

The feed agent gave each cow a coverage of `target_i x cow_count / sum(targets)`, so cows with below-average intake targets were treated as under-fed even when the herd was fully supplied, and lost milk and intake. Each cow now receives the herd's coverage fraction of its own need. That raised milk to +5.1% and feeding cost to +8.1% against the workbook (8 seeds, 12 / 12 / 7), because both coefficients had been fitted with the bug in place. They were refitted to their existing, documented workbook targets:

| Coefficient | Old | New | Target |
|---|---:|---:|---|
| `herd.milk_yield_scale` | 1.368 | 1.3016 | Stats_MAST!BQ12, AIRAND year-15 milk 12,668.71 kg/cow/year (new = old x 12,668.71 / 13,315.13) |
| `cow.dmi_level_calibration_factor` | 1.19 | 1.1169 | Stats_MAST AT73 / AT21, AIRAND year-15 lactating DMI 26.2076 kg per milking cow-day (model was 27.9228; 8-seed mean now 26.2075) |

The intake refit was approved by the owner on 2026-09-24, because with only the milk refit profit was -8.6%.

## Results

| Measure | Unit | Workbook | Model mean | Model SE | Difference | Status |
|---|---|---:|---:|---:|---:|---|
| Milk yield/cow/yr (kg) | kg/cow/year | 12,668.71 | 12,679.49 | 33.48 | +0.1% | match |
| Cow pregnancy rate (%) | fraction | 0.3650 | 0.3627 | 0.0063 | -0.6% | match |
| Cow conception rate | fraction | 0.6431 | 0.6365 | 0.0073 | -1.0% | match |
| 21-day service rate | fraction | 0.5675 | 0.5696 | 0.0049 | +0.4% | match |
| Cow days open (d) | days | 110.84 | 111.90 | 0.9019 | +1.0% | match |
| Days to first service | days | 79.51 | 82.63 | 0.0598 | +3.9% | close |
| Average days in milk | days | 162.88 | 164.99 | 0.6717 | +1.3% | match |
| Annual cull rate (%) | fraction | 0.3673 | 0.3683 | 0.0096 | +0.3% | match |
| Surplus female calves (%) | fraction | 0.2416 | 0.2370 | 0.0121 | -1.9% | match |
| Age of dam at creation (d) | days | 1,057.17 | 1,193.25 | 7.5856 | +12.9% | differs |
| Mastitis incidence (%) | cases/milking cow-year | 0.1733 | 0.1713 | 0.0062 | -1.1% | match |
| Yearly antibiotic daily doses (per cow) | doses/cow/year | 0.2455 | 0.2369 | 0.0172 | -3.5% | close |
| Milking cows (%) | fraction | 0.8596 | 0.8621 | 0.0011 | +0.3% | match |
| Pregnant cows (%) | fraction | 0.6711 | 0.6939 | 0.0024 | +3.4% | close |
| Milk component sales | currency/cow/year | 5,068.14 | 5,072.43 | 13.39 | +0.1% | match |
| Cow sales | currency/cow/year | 304.41 | 298.72 | 9.2118 | -1.9% | match |
| Calf sales | currency/cow/year | 154.21 | 152.84 | 4.3102 | -0.9% | match |
| Profit deviation | currency/cow/year | 231.43 | 231.43 | 0.0000 | -0.0% | match |
| Total revenues | currency/cow/year | 5,758.18 | 5,755.42 | 13.01 | -0.0% | match |
| Feeding cost | currency/cow/year | 2,599.15 | 2,599.79 | 3.7662 | +0.0% | match |
| Breeding cost | currency/cow/year | 34.62 | 32.35 | 0.2513 | -6.6% | differs |
| Pregnancy diagnosis and heat detection | currency/cow/year | 26.26 | 25.84 | 0.1627 | -1.6% | match |
| Other variable cost | currency/cow/year | 182.50 | 182.50 | 0.0000 | +0.0% | match |
| Heifer raised cost | currency/cow/year | 619.97 | 590.56 | 6.6963 | -4.7% | close |
| Genomic testing cost | currency/cow/year | 0.0000 | 0.0000 | 0.0000 | +0.0% | match |
| Clinical mastitis treatment | currency/cow/year | 7.6320 | 7.4802 | 0.2414 | -2.0% | match |
| Dry cow therapy | currency/cow/year | 16.65 | 16.36 | 0.1363 | -1.8% | match |
| Fixed costs | currency/cow/year | 730.00 | 730.00 | 0.0000 | +0.0% | match |
| Total costs | currency/cow/year | 4,216.79 | 4,184.88 | 7.4297 | -0.8% | match |
| Profit | currency/cow/year | 1,541.40 | 1,570.54 | 15.92 | +1.9% | match |
| Net present value of profit | currency/cow/year | 739.87 | 753.86 | 15.92 | +1.9% | match |

## Gaps requiring investigation

- **Age of dam at creation (+12.9%)** uses a cohort definition that may differ from the workbook Java simulator. Align the population and event timing before changing biology coefficients.
- **Breeding cost (-6.6%)** follows simulated insemination counts. The workbook formula near `Stats_MAST!AA471` also merits direct review: its cell references appear inconsistent with adjacent strategies. This is a suspected workbook issue, not a confirmed correction.
- **Heifer raised cost (-4.7%), days to first service (+3.9%), antibiotic daily doses (-3.5%) and pregnant cows (+3.4%)** are close but outside the 2% band. The workbook contains aggregated Monte Carlo output; the external Java simulator is unavailable, so event-level equivalence has not been established.

## Determinism fix

`GeneticsAgent.offspring_traits` iterated a Python `set` of trait names while drawing from the seeded RNG, so the draw order, and therefore the results, depended on the per-process string hash seed (`PYTHONHASHSEED`). The same seed did not replay identically across processes, on the pre-fix code as well. The loop now uses insertion order and `tests/test_deterministic_replay.py` checks two hash seeds. After this fix, the round-1 eight-seed results were produced twice with different hash seeds and were identical.

## Economics and provenance

The spreadsheet economics formula port was checked separately against all five MAST strategies for every available year. This eight-seed comparison tests model-generated AIRAND year-15 inputs to that formula layer. Model milk yield is 12,679.49 against 12,668.71 kg/cow/year (+0.1%). Model revenue is $5,755.42 against $5,758.18 (-0.0%), total cost is $4,184.88 against $4,216.79 (-0.8%), and profit is $1,570.54 against $1,541.40 (+1.9%). These monetary values are per cow per year.

The farm ledger now charges feed with the same workbook rows (`cdairy_economics.feed_cost_rows`, Stats_MAST rows 28-29) that this comparison uses, so for a run with every loop off the ledger's herd revenue, herd cost and herd profit equal `annual_excel_economics` for each complete calendar year (`tests/test_ledger_reconciliation.py`; the dashboard default farm matches to 0.000% in both the default and loops-off runs). Circular-loop items are a separate, itemized layer on top.

The pasted published `Tables!P63` profit is $1,517, while the live `Stats_MAST` formula produces $1,541.40. This report uses the live formula consistently; the pasted value remains an independent presentation value. The workbook stores summary output from an external Java Monte Carlo model whose source is not available here. Agreement of eight model seeds with those summaries does not demonstrate event-level identity or predict real farm performance.

## Reference extraction

Re-checked on 2026-09-23 on this Mac (Python 3.14.7): `python3 scripts/extract_cdairy_reference.py Cdairy_mc_kk_current_PS_CM_Strategies.xlsm /tmp/fixture.json` produced the same schema, keys, arrays, strings, integers, and other nonnumeric values as `configs/reference_targets/cdairy_stats_mast.json`, but Python `==` on the two loaded objects is `False`: 243 floating point leaves differ, at most `2.9103830456733704e-11` (`AIMAST` year index 11, `heat_detection_eligible_days_cows`), and bytewise comparison also fails. The differences are consistent with summation-order rounding in multi-row sums. The audit note that an independent re-extraction matched exactly with `==` was not reproduced here. The committed fixture was retained.

## Dashboard visual review

`docs/parity/tools/ui_audit.py` was run for the target and the app (1440 px, light and dark, all eight target pages). Every page has the same Chart.js canvas ids as the target, and neither page logged a page error or console error. The only all-zero datasets are Heat Value on the Overview revenue chart and the time-series Heat Value chart (both carry an on-screen note: no farm heat demand is configured, Blueprint Energy 8.5) and the ROI payback chart's Break-even reference line; the Solar PV item is excluded from the ROI charts and its card states that no solar capacity is configured. Target, app, and side-by-side screenshots are in `docs/parity/screenshots/` with `target-*`, `app-*`, and `comparison-*` prefixes, and every page was reviewed side by side.

Remaining visible differences are intended: numbers and table rows come from the Python model; the Export button, Excel parity card, "Other herd costs/revenue (workbook)" row and Model details card are agreed additions; the ninth page, Formulas & Values, is kept by owner decision; controls without a Python equivalent are disabled; target emojis are replaced by inline SVG icons in the ROI cards, revenue cards and parameter group headers, and dropped from inline text such as the farm title, tier filter and jump links.

## Remaining validation limits

The four loop combinations are simulated from the Python model; no claim is made that their outputs reproduce the dashboard's former JavaScript engine. The workbook cannot establish Blueprint-only energy, water, or nutrient equations. Those formulas are covered by implementation tests and the Blueprint notes in this directory. Calibration assumptions listed in `docs/calibration_review.md` require domain review before scientific or financial use.
