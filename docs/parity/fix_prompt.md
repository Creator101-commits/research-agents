# Task: fix the audit findings in research-agents (model economics, dashboard values, UI gaps)

## 0. Context and ground rules

- Repo: `/Users/sreeharshak/Dev/research-agents`, branch `feat/blueprint-excel-dashboard-parity`. Nothing on this branch is committed yet. `main` is untouched; my old WIP is saved at `refs/backup/wip-before-parity`.
- Read first: `AGENTS.md`, then `docs/parity/research-agents_parity_plan.md`, `docs/parity/parity_report.md`, `docs/parity/blueprint_formulas.md`, `docs/parity/dashboard_ui_spec.md`. The target UI is `docs/parity/conventional_dashboard_target.html`. The Blueprint text is `docs/parity/blueprint_extracted.txt`. The workbook is `Cdairy_mc_kk_current_PS_CM_Strategies.xlsm` in the repo root; its extracted data is `configs/reference_targets/cdairy_stats_mast.json`.
- Where sources disagree, the Excel workbook wins, then the Blueprint. The target dashboard's JavaScript formulas only fill gaps and set layout.
- No emojis anywhere: code, comments, UI text, docs, commits. Where the target shows an emoji icon, use a small inline SVG in the same box, the way the Circular Loops cards already do.
- Python standard library only. Do not add dependencies. Playwright may be used locally for screenshots if it is already installed, but it must not become a project dependency.
- Never invent data or coefficients. Every new or changed coefficient goes in `configs/calibration.json` with `value`, `unit`, `valid_range`, `source`, `assumption`, and `description`, and the source must be the workbook (cell reference) or the Blueprint (section). If neither gives a value, stop and ask me rather than guessing.
- Do the work yourself; do not hand it to subagents. Do not commit until I have reviewed the result.

## 1. What an audit found (reproduce these first)

Numbers below are from the current branch: default dashboard run (100 cows, 5 years, seed 42) and the same run with all four loops off. Money is per cow per year.

| Finding | Evidence |
|---|---|
| Dashboard profit is far above the workbook | Default run $5,103 profit; all loops off $3,698. Applying the workbook formulas to the herd statistics of that same loops-off run (`dairy_abm.analysis.excel_parity.annual_excel_economics`) gives $1,296 to $1,732 per year, about $1,530 on average. |
| Feed cost is $0 for the whole run | `feed_crop_agent.py`: 80 ha x `feed_crop.crop_yield_kg_dm_per_ha_day` (2,800 kg DM/day) plus an opening inventory of about 707 t covers the whole herd's intake, so `purchased_feed` is 0, and `feed_cost_total = purchased_feed * feed_cost` (around line 259). Home-grown feed is never charged. The workbook charges all intake: lactating DMI x `cdairy_economics` lactating price ($0.30/kg) plus dry DMI x dry price ($0.20/kg), about $2,600/cow/yr. The ledger's other herd costs ($1,608) already match the workbook's non-feed costs (about $1,600), so feed is the whole gap. |
| Loop 4 adds processor revenue | `dashboard_conventional.resolve_inputs` sets `enable_processor = loops["l4"]`. With the processor on, `herd_revenue` uses `processor_revenue` ($6,506/cow/yr of dairy product sales) instead of workbook milk component sales ($5,030). That is where the "L4 +36.8% profit" in the comparison comes from. It is product-sales uplift with no product costs, not a byproduct effect. |
| Heat Value is always $0 | `energy_agent.py`: heat is only valued up to `scenario.farm_heat_demand_mj_per_day`, which the baseline scenario does not set, so displaced heat is 0 while 1.19 million kWh of heat is generated. |
| Energy revenue is flat at $12/day | Only electricity up to `energy.farm_energy_demand_kwh_per_day` (100 kWh) is credited; about 469 kWh/day of surplus is not. This matches the Blueprint ("only monetize displaced share unless explicit export pricing exists"), so do not change the math. Label it in the UI (see 3.3) and confirm the farm demand value has a documented source. |
| Loop 1 is essentially empty | With L3 on, almost all manure goes to the digester: compost 0.6 kg/day, $51 compost revenue over 5 years, nitrogen recovered 11 kg in 5 years, Loop 1 feed offset 0.1 kg/day. Also, biogas (230,365 m3) and digestate are identical with L3 off and on; the L3 toggle only switches electricity conversion. |
| Solar is 0 | Baseline solar capacity is 0, so the Solar PV ROI card and the solar part of Total Electricity are always 0. |
| Cow Ranking data gaps | `herd_summary` gives every cow the same 95 L of water; `calvings` counts only `event == "calving"` and skips `first_calving`; `peakFactor` reads `milk_trait` instead of `peak_factor`; body weights drift down to 420-650 kg over the run. |
| UI differences from the target | Extra 9th page "Formulas & Values"; equipment ROI cards show empty coloured squares where icons were; the Cow Ranking summary cards lost their coloured values and units; the "Running simulation / Simulation complete" badge in the farm summary card is gone; only 19 target parameters are connected, so most controls are disabled, including Feed Cost. |
| ROI page mixes in fixed numbers | `buildEquipROI` uses target constants the model does not use (for example `feed_cost_per_kg` 0.22 while the model charges 0.30, `grid_avoided_kg_co2e_per_kWh` 0.40, `biogas_m3_per_kg_manure_to_digester` 0.025 used to back-calculate manure). The Manure Separator's benefit is mostly digestate value (`organicFert x 0.015`), which gives +2,241% lifetime ROI on a loop that makes 0.6 kg of compost a day. |
| Housekeeping | `configs/reference_targets/cdairy_airand_milk_calibration.json` is obsolete and still present. `parity_report.md` says re-extraction differed by up to 2.9e-11, but an independent re-extraction matched the fixture exactly (Python `==`). `tmp/_audit_snapshot.tgz` is audit scratch. |

What already passes and must keep passing: all 262 tests; the workbook economics port (exact for 5 strategies x 20 years); the 8-seed parity result (21 match, 4 close, 6 differ; milk -0.3%, profit -1.0%); all 45 dashboard charts rendering in both themes with no JavaScript errors; the page layout.

## 2. Model and ledger fixes (do these first)

2.1 Feed cost follows the workbook
- Charge feed in the farm ledger with the workbook rule: lactating DMI x lactating price + dry DMI x dry price, using the existing `cdairy_economics` prices (`CdairyPrices`). Home-grown feed is charged at the same price, because the workbook has no own-feed discount.
- Circular-loop feed offsets (L1 nutrient offset, L4 byproduct return) reduce the charged kilograms at the same price, so a loop saving shows up as a lower feed cost.
- Keep `purchased_feed_kg_dm` and inventory as physical flows; only the cost rule changes. Make sure the parity path and the ledger use one shared function so they cannot drift apart.

2.2 One profit definition, reconciled to the workbook
- Farm profit = workbook herd economics (every Table 4 line, including feeding cost) + circular-loop layer (loop revenues - loop costs, including water, cooling and processing energy), with the loop layer listed line by line.
- Add a regression test: for an all-loops-off run, the ledger's herd revenue, herd cost and herd profit for each complete calendar year must equal `annual_excel_economics(ctx)` for the same run to within 0.5% (they come from the same inputs). Water and other Blueprint-only costs are reported as separate loop-layer lines, not hidden inside herd costs.

2.3 Processor and Loop 4
- In the dashboard adapter, stop tying `enable_processor` to L4 for revenue. The processor may still run so whey and waste milk exist for the L4 byproduct loop, but farm revenue keeps the workbook milk component sales. Report processor product revenue separately (for example `processor_revenue_not_in_profit`) or leave it out of the dashboard payload, and document the choice.
- After the fix, the L4 comparison column must show only byproduct effects: feed return, lower feed cost, whey and waste-milk flows.

2.4 Heat, surplus electricity, compost and solar
- Heat: find the Blueprint's farm heat demand, or its rule for valuing recovered heat (search `blueprint_extracted.txt` for heat demand and heat value). If a value exists, add it as a calibration entry and use it in the dashboard scenario. If not, ask me before choosing one. Either way Heat Value must not silently stay at $0.
- Surplus electricity: keep the Blueprint rule (only displaced demand is monetized). Report `surplus_energy_kwh` in the payload so the UI can show it (see 3.3).
- Manure routing: check the Blueprint's manure routing and separator split and compare it with `manure_agent._route_fractions()`. If the Blueprint defines a solid/liquid separation when L1 is on (the target uses 35% solids to compost), implement it so L1 produces compost and N/P/K. Make the L3 toggle control whether the digester runs at all, so biogas and digestate are 0 with L3 off, unless the Blueprint says otherwise. Cite the Blueprint section in the code comment and in `docs/calibration_review.md`.
- Solar: if the Blueprint or workbook gives a solar assumption, use it; if not, leave solar at 0 and have the Solar PV ROI card say that no solar capacity is configured, instead of showing a negative ROI with no explanation.

2.5 Cow Ranking data (`dairy_abm/dashboard_conventional.py::herd_summary`)
- `calvings`: count both `calving` and `first_calving` events.
- `peakFactor`: use `cow["peak_factor"]`.
- Water: if the Blueprint has a per-cow water intake equation (for example as a function of DMI, milk and temperature), use it in the water agent and record per-cow water. If it does not, keep the herd value but label the column in the UI as the herd-average allocation.
- Body weight drift: find why body weight trends down (`cow_agent.py` energy-balance update around lines 421-430: actual DMI averages below expected because of heat and ration losses). Check the Blueprint's body weight and BCS equations and fix it to match. Mature cows must stay in a plausible range across a 5-year run; add a test for it.

Record every coefficient decision and its source in `docs/calibration_review.md`.

## 3. Dashboard fixes (after section 2)

3.1 Match the target exactly, without emojis
- Equipment ROI cards: put an inline SVG icon in each `.equip-icon` box (digester, CHP, separator, solar, whey, water, sensors, beef), in the same style as the loop-card SVGs.
- Parameter group headers and Animal Biology group headers: add matching small SVG icons or keep them empty consistently; do not use emojis.
- Cow Ranking summary cards: restore the target markup (coloured values with `font-size:var(--text-lg)`, `font-weight:800`, the target colours, and a muted sub line with units, for example "0.467 kg/kg" and "10% of all cows").
- Farm summary card: restore the status pill ("Running simulation..." then "Simulation complete"), in plain text without emojis.
- Keep the agreed additions: the Export button, the Excel parity card on Comparison, the "Other herd costs/revenue (workbook)" row, the model-details card.

3.2 The 9th page
- The agreed layout has 8 pages. Ask me whether to keep "Formulas & Values". If I say fold it in, move it into a collapsible section on the Parameters page and remove the extra sidebar item.

3.3 Honest labels for model-driven values
- Energy Revenue card and KPI tooltip: say it covers displaced farm demand only, and show surplus kWh.
- Any series that is legitimately zero for the default farm (for example solar, if no source exists) gets a short note in the card instead of an unexplained flat line.

3.4 Parameters
- Go through every control in the target's `PARAM_GROUPS` and Animal Biology groups and connect each one that has a real model equivalent: at minimum Feed Cost (the workbook lactating DMI price), and wherever they exist, solar, methane factor, grid emission factor, biogas yield, compost yield, separator solid fraction, lactation length, dry period, cull rate. Changing a connected control must change the run output; add a test that proves this for each connected key.
- Leave the rest disabled with the tooltip "Not used by the Python model", and list both groups in `docs/dashboard_metric_map.md`.

3.5 ROI page uses model values
- Keep the target's card structure and formulas, but take every price or factor the model has from the run (`res.cfg` from the backend): feed price, electricity price, heat value, grid factor, carbon price, and the actual kg of manure sent to the digester instead of back-calculating from 0.025.
- The Manure Separator benefit uses separator and compost outputs only; digestate value belongs to the Anaerobic Biodigester card. Any remaining catalogue constant (capital cost per cow, disposal cost per tonne, and so on) is labelled as a scenario estimate in the methodology note.

## 4. Housekeeping
- Delete `configs/reference_targets/cdairy_airand_milk_calibration.json` and `tmp/_audit_snapshot.tgz` (ask me for delete permission if needed).
- Fix the extraction paragraph in `docs/parity/parity_report.md`: re-run `python3 scripts/extract_cdairy_reference.py Cdairy_mc_kk_current_PS_CM_Strategies.xlsm /tmp/fixture.json`, compare with Python `==`, and report what you actually get.
- Emojis in `docs/parity/`: the target HTML copy, `dashboard_ui_spec.md` and `blueprint_extracted.txt` contain emojis. Strip them from the files we wrote (`dashboard_ui_spec.md`, `blueprint_formulas.md`). For the two source copies (target HTML, Blueprint text), ask me whether to keep them out of git or keep them as-is, since they are reference material.
- Keep the README and docs (`docs/explanation.md`, `docs/calibration_review.md`, `docs/dashboard_metric_map.md`) in sync with every change.

## 5. Verification (all required before you report back)

1. `python3 -B -m unittest discover -s tests -p 'test_*.py'`: all pass, including the new tests from 2.2, 2.5 and 3.4.
2. `python3 -m dairy_abm parity --seeds 1,2,3,4,5,6,7,8`: must still show at least 21 within 2%, milk and profit within 2%. Update `parity_report.md` and `parity_results_8_seeds.json` with the new run.
3. Default dashboard run and all-loops-off run: print per-cow-year revenue, feed cost, other herd costs, loop-layer lines and profit, next to `annual_excel_economics` for the same run. All-loops-off herd profit must be within 0.5% of the workbook-formula profit, and the default run's profit must differ from it only by the listed loop-layer lines.
4. Run the 16-loop comparison and show a table of profit vs baseline per scenario, with the reason for each loop's effect.
5. UI audit: start `python3 webapp.py`, then run `docs/parity/tools/ui_audit.py` for the target and the app (both themes, all 8 pages). Required: the same chart ids per page as the target, no page errors, and no dataset that is all zero unless 3.3 explains it on screen. Build side-by-side screenshots and review every page yourself.
6. Emoji scan over `dairy_abm`, `web`, `tests`, `scripts`, `configs`, `docs`, `README.md`: no emoji or pictograph characters (U+1F000-1FAFF, U+2600-27BF, U+FE0F) outside the reference copies I approved.

## 6. Report back

Give a short report: what changed and why (with Blueprint section or workbook cell for each coefficient), the before and after numbers from 5.3 and 5.4, the parity table, anything you could not match and why, and the questions from 2.4, 3.2 and 4 that need my decision. Then propose conventional commits split by area (economics ledger, manure and energy, herd summary, UI, docs). Do not commit until I say so.
