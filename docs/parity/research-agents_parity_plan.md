# research-agents: plan to match the Dashboard UI, the Blueprint formulas and the Cdairy Excel outputs

Status: historical plan. Implementation results and remaining gaps are in `parity_report.md`. The baseline and code descriptions below describe the repository before this parity branch; they are retained as planning context.

## 1. What is in the codebase today

- `dairy_abm/` is a Python standard-library ABM with 13 agents. It runs on a packet-based daily scheduler and uses `configs/calibration.json` (209 keys) as its parameter registry.
- `webapp.py` and `web/` are a custom-SVG dashboard with 12 flat pages and a white/red theme. There is no dark mode and no Chart.js.
- `dairy_abm/analysis/reference_benchmark.py` already compares the model with the workbook, but only on one measure: AIRAND year-15 milk, 12,668 kg/cow/yr. That comparison is made to pass by forcing `cow.base_milk_l_per_cow_day = 50.82`, a single-point fit. The other 13 targets are marked `not_modeled` or `not_equivalent`.
- Uncommitted work sits in `webapp.py`, `web/js/*`, `web/styles/pages.css` and two tests. It adds scenario-aware Parameters and cleans up the Economics and ROI warnings. It must be kept.

## 2. What each of the three sources actually is

### Dairy bioeconomy dashboard.html (UI target: Conventional Farm only)

- **Layout:** a 56 px top bar holding the Run Simulation button, a status chip and a theme toggle. The 260 px sidebar has two groups:
  - DASHBOARD: Overview, Time Series Charts, Circular Loops, Comparison, ROI Justification, Cow Ranking.
  - SETTINGS: Parameters, Animal Biology.
- **Styling:** Chart.js 4.4.2, Inter and JetBrains Mono fonts, a teal primary (`#01696f`) on warm neutrals, loop colours L1–L4, and a full dark theme.
- **Built-in maths:** the page has its own JS formulas (Wood's curve, 90-day nutrient pool, compost revenue, an 8-item equipment ROI catalogue). These disagree with the Blueprint and the Excel in places.

### Blueprint.html (formula authority)

The Blueprint audit covers 13 agents plus the scheduler and interfaces: about 78 MATCH, 42 PARTIAL, 21 DIFFERENT and 34 MISSING. The largest gaps are listed below.

- **Genetics:** the index weights are not NM$9, a positive body-weight weight should be −11 %, the cull-price rule is reversed, and offspring RFI is clamped at ≥ 0.
- **Cow:** conception never fires without scenario-supplied estrus signals. The SARA modifier is applied to intake instead of digestibility. There is an extra random mortality term.
- **Sensors:** the THI formula uses `(F − 26)` where the standard form uses `(F − 58)`. This is confirmed in `sensors_agent.py:26`.
- **Nitrogen:** excess N is computed against MP supply rather than MP requirement, and manure N double-counts milk N.
- **Energy:** the published electricity figure includes an extra parasitic load and additions on top of `85.73·t`.
- **Environment:** the soil-carbon offset is hard-coded, and the sustainability and biodiversity scores are invented. The Blueprint says to publish null.
- **Processor and Market:** the USDA solids coefficients, the Class III/IV and component price formulas, and the volatility regression are missing.
- **Water:** the recycled-irrigation credit may be double-counted.
- **Not specified in the Blueprint:** a list of items the Blueprint marks "not clearly specified" cannot be matched to it exactly. Examples are the lactation, manure and mortality equations, the disease effect sizes and the biogas kWh coefficients.

### Cdairy_mc_kk_current_PS_CM_Strategies.xlsm (output target)

- **Not a model itself:** the VBA only imports text files written by an external Java Monte Carlo program (DeVries lab, "IVF_Program"). The Java source is not in the workbook.
- **Stats_MAST:** holds the Java output for 5 strategies (AIRAND, AINM$, AIMAST, SSNM$, ETNM$), 1,000 replications and years −4 to 15. It also holds about 140 Excel formulas that turn herd counts into per-cow/year economics. Examples: milk/fat/protein sales, SCS penalty, cow and calf sales, wet and dry feed cost, breeding, heat detection, pregnancy diagnosis, dry-cow therapy, mastitis treatment, heifer raising, fixed costs, profit, and NPV at 5 %.
- **Tables / Updated_Tables:** hold the published results, which are the numbers to match. Year-15 AIRAND examples: milk 12,668 kg/cow/yr, pregnancy rate 36.5 %, days open 111, cull rate 36.7 %, mastitis 17.3 %, 284 antibiotic doses, revenue $5,734, cost $4,217, profit $1,517, NPV $728.
- **herd / herdInputs:** hold the reproduction inputs: VWP 70 d, P(insemination at estrus) 0.61, conception 0.40, pregnancy checks at 42/60/220 d, dry-cow DMI 12.5 kg.
- **Tables_METR:** holds a second set of strategies (BT-BDCT, PST-SDCT, ABU-Banned and others).

## 3. What can be matched, and how exactly

| Target | Achievable | How it is proved |
|---|---|---|
| Excel economics layer (Stats_MAST formulas → Tables P46–P64) | Exact, to the workbook's rounding | Feed the workbook's own year aggregates into a Python port and assert Tables values for all 5 strategies |
| Excel technical measures (pregnancy rate, days open, cull, mastitis, doses, milk, fat, protein) produced by our ABM | Calibrated within a stated tolerance, not identical | Multi-seed runs (mean ± SE) compared with the Excel means and SEM |
| Blueprint formulas | Exact where the Blueprint gives an equation; labelled assumption where it says "not specified" | One conformance test per numbered formula (G-1, C-3, …) |
| Conventional dashboard UI | Visually matching | Side-by-side screenshots of all 8 pages, light and dark |

The Excel outputs cannot be made identical without the Java program. If you have its source, the herd submodel could be ported instead of calibrated, and the technical measures could then match much more closely.

## 4. Phased plan

**Phase 0 – Safety**
- Work on a new branch, `feat/blueprint-excel-dashboard-parity`. `main` is never touched.
- Commit or stash your current uncommitted work first (your call).
- Snapshot the baseline outputs and the 245 passing tests.

**Phase 1 – Excel economics, exact**
- Add `dairy_abm/analysis/cdairy_economics.py` as a line-by-line port of the Stats_MAST AW-column formulas.
- Move the Excel prices into `calibration.json` with source cells (Tables!C7:C32).
- Add a fixture `configs/reference_targets/cdairy_stats_mast.json`, extracted once from the workbook. It is not stored under `output/`.
- Add tests reproducing Tables!O46:T64 and C67:H74 for all 5 strategies.

**Phase 2 – Blueprint formula parity**
- Fix every DIFFERENT and MISSING item, in order of impact: THI, Cow reproduction and SARA, NM$9 genetics, N balance, energy, environment nulls, processor and market formulas, the water double-count.
- Where the Blueprint is silent, use the Excel `herd` inputs if one exists. Otherwise keep a labelled assumption.
- Add one test per numbered formula.

**Phase 3 – Herd submodel that produces Excel-equivalent measures**
- Add parity classes, VWP, estrus detection, insemination/conception, pregnancy checks, dry-off, involuntary and voluntary culling with replacement, clinical mastitis with Gram+/Gram−/other treatment, antibiotic doses, and fat/protein/SCS yields.
- Wire the Phase-1 economics to the model's output.
- Replace the 50.82 L single-point hack with a real calibration against AIRAND year 15, and optionally all 5 strategies.
- Add a multi-replicate runner.

**Phase 4 – UI rebuild to the Conventional dashboard**
- Adopt the target's tokens, fonts, top bar, sidebar and 8 pages, with dark mode.
- Serialize the 6 series the model already computes but does not expose: heat $, manure and compost kg, net water, feed offset, N recovered, solar kWh.
- Elements the model cannot back (compost revenue, the 90-day nutrient pool, the 8-equipment catalogue) are either built in Python as labelled assumptions or shown as N/A.

**Phase 5 – Verification**
- Full test suite and conservation checks.
- A generated parity report: Excel vs Python table and Blueprint conformance matrix.
- UI screenshot comparison.
- README and docs updated per AGENTS.md.

## 5. Decisions (answered 2026-09-23)

- **Precedence:** Excel wins everything. Where the Excel has a formula or value, it overrides the Blueprint. The Blueprint fills only the gaps the Excel does not cover (energy, water, manure, loops and so on). The dashboard supplies layout only.
- **Excel scope:** AIRAND first, end to end. The other strategies come later.
- **Charts:** vendor Chart.js 4.4.2 locally under `web/vendor/`.
- **Extra pages:** fold them into the 8 target pages. Export moves to the top bar, and the Excel parity check goes under Comparison.

Original questions, kept for the record:

1. **Precedence when sources conflict**, for example milk price: $0.78/L (dashboard), $0.07/kg milk + $4.30/kg fat + $5.47/kg protein (Excel), or USDA component formulas (Blueprint). Proposed: Blueprint for equations, Excel for parameter values, economics and targets, and the dashboard for layout only.
2. **Excel scope:** AIRAND only, all 5 MAST strategies (this needs sexed semen, embryo transfer and genomic testing), or also the METR mastitis-treatment strategies.
3. **Chart.js:** add it as a new dependency (vendored locally) to match the look exactly, or keep the zero-dependency SVG charts restyled.
4. **Existing pages with no dashboard counterpart** (Simulation, Environment, Economics, Model Details, Export): remove them, or fold them into the 8 pages and the top bar.
5. **Java simulator source:** is it available?

Side effects of the survey so far:
- Git-ignored `__pycache__/` folders were created in `dairy_abm/`.
- `oletools` was installed in the workspace VM's Python, not the project, to read the VBA.
