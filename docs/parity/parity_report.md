# AIRAND year-15 parity: eight seeded model runs

The comparison used `python3 -m dairy_abm parity --seeds 1,2,3,4,5,6,7,8` on 2026-09-23. The source is the live `Stats_MAST` formulas in `Cdairy_mc_kk_current_PS_CM_Strategies.xlsm`, extracted to `configs/reference_targets/cdairy_stats_mast.json`. The model figure is the arithmetic mean of eight seeded runs. Standard error measures variation among those eight runs; it does not measure uncertainty in the workbook target. Full per-seed data and unrounded results are in `parity_results_8_seeds.json`.

Classification: **21 within 2%**, **4 more within 5%**, and **6 over 5%**. An exact-zero target is compared by absolute equality. These tolerances assess calibration agreement, not scientific validation.

## Results

| Measure | Unit | Workbook | Model mean | Model SE | Difference | Status |
|---|---|---:|---:|---:|---:|---|
| Milk yield/cow/yr (kg) | kg/cow/year | 12,668.71 | 12,630.21 | 43.83 | -0.3% | match |
| Cow pregnancy rate (%) | fraction | 0.3650 | 0.3439 | 0.0024 | -5.8% | differs |
| Cow conception rate | fraction | 0.6431 | 0.6184 | 0.0052 | -3.8% | close |
| 21-day service rate | fraction | 0.5675 | 0.5562 | 0.0025 | -2.0% | match |
| Cow days open (d) | days | 110.84 | 111.82 | 0.5560 | +0.9% | match |
| Days to first service | days | 79.51 | 82.60 | 0.0665 | +3.9% | close |
| Average days in milk | days | 162.88 | 164.56 | 0.5280 | +1.0% | match |
| Annual cull rate (%) | fraction | 0.3673 | 0.3745 | 0.0124 | +1.9% | match |
| Surplus female calves (%) | fraction | 0.2416 | 0.2321 | 0.0100 | -4.0% | close |
| Age of dam at creation (d) | days | 1,057.17 | 1,171.94 | 6.13 | +10.9% | differs |
| Mastitis incidence (%) | cases/milking cow-year | 0.1733 | 0.1603 | 0.0067 | -7.5% | differs |
| Yearly antibiotic daily doses (per cow) | doses/cow/year | 0.2455 | 0.2181 | 0.0223 | -11.2% | differs |
| Milking cows (%) | fraction | 0.8596 | 0.8621 | 0.0008 | +0.3% | match |
| Pregnant cows (%) | fraction | 0.6711 | 0.6882 | 0.0017 | +2.5% | close |
| Milk component sales | currency/cow/year | 5,068.14 | 5,052.72 | 17.53 | -0.3% | match |
| Cow sales | currency/cow/year | 304.41 | 299.39 | 9.60 | -1.6% | match |
| Calf sales | currency/cow/year | 154.21 | 151.58 | 3.15 | -1.7% | match |
| Profit deviation | currency/cow/year | 231.43 | 231.43 | 0.0000 | -0.0% | match |
| Total revenues | currency/cow/year | 5,758.18 | 5,735.12 | 17.74 | -0.4% | match |
| Feeding cost | currency/cow/year | 2,599.15 | 2,606.39 | 6.21 | +0.3% | match |
| Breeding cost | currency/cow/year | 34.62 | 32.51 | 0.4263 | -6.1% | differs |
| Pregnancy diagnosis and heat detection | currency/cow/year | 26.26 | 25.81 | 0.2137 | -1.7% | match |
| Other variable cost | currency/cow/year | 182.50 | 182.50 | 0.0000 | +0.0% | match |
| Heifer raised cost | currency/cow/year | 619.97 | 608.12 | 8.97 | -1.9% | match |
| Genomic testing cost | currency/cow/year | 0.0000 | 0.0000 | 0.0000 | +0.0% | match |
| Clinical mastitis treatment | currency/cow/year | 7.63 | 7.13 | 0.3022 | -6.6% | differs |
| Dry cow therapy | currency/cow/year | 16.65 | 16.35 | 0.0992 | -1.8% | match |
| Fixed costs | currency/cow/year | 730.00 | 730.00 | 0.0000 | +0.0% | match |
| Total costs | currency/cow/year | 4,216.79 | 4,208.81 | 12.12 | -0.2% | match |
| Profit | currency/cow/year | 1,541.40 | 1,526.31 | 14.40 | -1.0% | match |
| Net present value of profit | currency/cow/year | 739.87 | 732.63 | 14.40 | -1.0% | match |

## Gaps requiring investigation

- **Age of dam at creation (+10.9%)** uses a cohort definition that may differ from the workbook Java simulator. Align the population and event timing before changing biology coefficients.
- **Pregnancy (−5.8%) and conception (−3.8%)** indicate remaining reproductive-timing differences. The workbook contains aggregated Monte Carlo output; the external Java simulator that produced it is unavailable, so event-level equivalence has not been established.
- **Mastitis incidence (−7.5%), antibiotic daily doses (−11.2%), and treatment cost (−6.6%)** move together. Investigate case detection, episode duration, treatment eligibility, and denominator definitions before further calibration.
- **Breeding cost (−6.1%)** follows simulated insemination counts. The workbook formula near `Stats_MAST!AA471` also merits direct review: its cell references appear inconsistent with adjacent strategies. This is a suspected workbook issue, not a confirmed correction.
- **Days to first service (+3.9%), surplus female calves (−4.0%), and pregnant cows (+2.5%)** are close but still outside the 2% band.

## Economics and provenance

The spreadsheet economics formula port was checked separately against all five MAST strategies for every available year. This eight-seed comparison tests model-generated AIRAND year-15 inputs to that formula layer. Model milk yield is 12,630.21 against 12,668.71 kg/cow/year (−0.3%). Model revenue is $5,735.12 against $5,758.18 (−0.4%), total cost is $4,208.81 against $4,216.79 (−0.2%), and profit is $1,526.31 against $1,541.40 (−1.0%). These monetary values are per cow per year.

The pasted published `Tables!P63` profit is $1,517, while the live `Stats_MAST` formula produces $1,541.40. This report uses the live formula consistently; the pasted value remains an independent presentation value. The workbook stores summary output from an external Java Monte Carlo model whose source is not available here. Agreement of eight model seeds with those summaries does not demonstrate event-level identity or predict real farm performance.

## Reference extraction

On this Mac, `python3 scripts/extract_cdairy_reference.py Cdairy_mc_kk_current_PS_CM_Strategies.xlsm /tmp/fixture.json` produced the same schema, keys, arrays, strings, integers, and other nonnumeric values as `configs/reference_targets/cdairy_stats_mast.json`. A recursive comparison found 243 floating point values that differ at most `2.9103830456733704e-11`; bytewise `cmp` therefore fails. This is numerical reproduction, not byte-for-byte reproduction. The handoff fixture was retained to avoid hiding this platform-level difference.

## Dashboard visual review

The Conventional Farm layout was captured for Overview, Time Series Charts, Circular Loops, Comparison, ROI Justification, Cow Ranking, Parameters, and Animal Biology in both light and dark mode. Target, app, and side-by-side screenshots are in `docs/parity/screenshots/` with `target-*`, `app-*`, and `comparison-*` prefixes. All eight pages loaded in both themes without app browser errors. The top viewport of every page was visually compared. Layout, color tokens, typography, cards, and chart placement follow the target. The visible differences are numerical plots and table rows from the Python model, the requested Export and Excel parity UI, disabled controls without Python equivalents, and omission of target emojis. The eight-equipment ROI catalogue remains a scenario estimate with fixed assumptions, not a farm quote.

## Remaining validation limits

The four loop combinations are simulated from the Python model; no claim is made that their outputs reproduce the dashboard's former JavaScript engine. The workbook cannot establish Blueprint-only energy, water, or nutrient equations. Those formulas are covered by implementation tests and the Blueprint notes in this directory. Calibration assumptions listed in `docs/calibration_review.md` require domain review before scientific or financial use.
