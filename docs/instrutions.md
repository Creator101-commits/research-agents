## TASK 1 (highest priority) — Energy Agent uses the wrong electricity formula

**File:** `dairy_abm/agents/energy_agent.py`

**Problem:** The blueprint's approved formula is `electricity_generated_kwh = 85.73 × digester_feedstock_total_t`. The code computes this correctly as `feedstock_gross_kwh`, then throws it away in favor of a biogas-volumetric calculation whenever `biogas_m3 > 0` — which is true in nearly every run. Line 39:

```python
conversion_kwh = biogas_gross_kwh if biogas_m3 > 0.0 else feedstock_gross_kwh
```

**Decide the approach first, then implement — this is a modeling decision, not just a bug fix:**

- **Option A (follow the blueprint literally):** Use `feedstock_gross_kwh` as the primary electricity output always. Keep `biogas_gross_kwh` computed and published as a secondary/diagnostic field (`biogas_derived_kwh_estimate`) so you don't lose that calculation, but it no longer drives the headline number.
- **Option B (keep the current biogas-volumetric model, but stop calling it the "approved FAN calibration"):** Rename `energy.kwh_per_ton_feedstock` in `calibration.json` so its description and `assumption` flag reflect that it's an unused/fallback-only coefficient, and update the paper text to describe the biogas-CHP path as the actual mechanism, not the FAN formula.

Pick Option A unless you have a specific reason (e.g. CHP-efficiency realism) to defend Option B in the paper — Option A is what the blueprint calls "approved," and it's a one-line change:

```python
conversion_kwh = feedstock_gross_kwh
biogas_derived_kwh_estimate = biogas_gross_kwh  # diagnostic only, not used in gross_kwh
```

Add `biogas_derived_kwh_estimate` to the published `energy_packet` payload dict alongside the existing fields so the diagnostic isn't lost.

**Verify:** Run a scenario with nonzero manure and confirm `electricity_generated_kwh` in the output now equals `feedstock_tons * 85.73` (within the parasitic-load subtraction). Add a unit test in `tests/` asserting this identity directly — there almost certainly isn't one today, since the bug shipped.

---

## TASK 2 — Enteric CH₄ ME constant is wrong (10.0 instead of 10.5)

**File:** `dairy_abm/agents/cow_agent.py`, line 306

**Current:**
```python
cow_ch4_kg = base_enteric * (cow_dmi_kg / max(base_dmi, 0.001)) * (10.0 / max(1.0, ration_me))
```

**Fix:** change `10.0` to `10.5` to match the blueprint's Herrero-derived approximation `ch4_per_litre = base_ch4 × (10.5 / me_concentration)`.

```python
cow_ch4_kg = base_enteric * (cow_dmi_kg / max(base_dmi, 0.001)) * (10.5 / max(1.0, ration_me))
```

Also pull this `10.5` out as a named calibration constant instead of a magic number, so it's auditable the same way everything else is:

In `configs/calibration.json`, under `"cow"`, add:
```json
"ch4_me_reference_constant": {
  "value": 10.5,
  "unit": "MJ/kg DM",
  "valid_range": "0..",
  "source": "abm_blueprint.html",
  "assumption": false,
  "description": "Herrero-derived ME reference constant in the enteric CH4 intensity approximation (ch4_per_litre = base_ch4 x (10.5 / ME))."
}
```

Then in `cow_agent.py`:
```python
ch4_me_reference = float(value(self.ctx.calibration, "cow.ch4_me_reference_constant"))
cow_ch4_kg = base_enteric * (cow_dmi_kg / max(base_dmi, 0.001)) * (ch4_me_reference / max(1.0, ration_me))
```

**Verify:** existing CH4 tests will shift slightly (5% higher CH4 output at a given ME) — re-run and update any hardcoded expected values in `tests/` that assumed the old constant.

---

## TASK 3 — Amino-acid CP reduction uses the wrong operation

**File:** `dairy_abm/agents/feed_crop_agent.py`, lines 159–165

**Problem:** Blueprint requires `dietary_cp_pct` to drop by **1.5–2.5 percentage points** (absolute) when amino-acid balancing is active. Code does a relative multiplicative cut instead (`× (1 - 0.06)`), which is a different operation and, on a typical ration, under-delivers versus the required range. The default value also isn't in `calibration.json` — it's a bare scenario default with no provenance tag.

**Current:**
```python
cp_reduction_fraction = min(0.15, max(0.0, float(self.ctx.scenario.get("amino_acid_cp_reduction_fraction", 0.06)))) if amino_acid_balancing_active else 0.0
ration_crude_protein *= 1.0 - cp_reduction_fraction
```

**Fix:** Change to an absolute percentage-point subtraction on the CP fraction, not a relative multiply. `ration_crude_protein` is a mass (kg), not a percentage, so the points need to be converted at the point where CP fraction is applied to DM intake — do this upstream, on the `local_cp_fraction`/`imported_cp_fraction`/`coproduct_cp` inputs before they're multiplied by mass, or equivalently subtract `cp_reduction_points × total_dmi` from the summed `ration_crude_protein` mass. The second is simpler given the current structure:

```python
cp_reduction_points = min(0.025, max(0.0, float(self.ctx.scenario.get(
    "amino_acid_cp_reduction_points",
    value(self.ctx.calibration, "feed_crop.amino_acid_cp_reduction_points"),
)))) if amino_acid_balancing_active else 0.0
ration_crude_protein = max(0.0, ration_crude_protein - cp_reduction_points * total_dmi)
```

(`total_dmi` should already be in scope earlier in `tick()` — confirm the variable name matches what's used elsewhere in the function.)

Add to `configs/calibration.json` under `"feed_crop"`:
```json
"amino_acid_cp_reduction_points": {
  "value": 0.02,
  "unit": "percentage points of dietary CP",
  "valid_range": "0.015..0.025",
  "source": "abm_blueprint.html",
  "assumption": false,
  "description": "Absolute reduction in dietary crude-protein percentage when amino-acid balancing is active (1.5-2.5pp band, 2.0pp midpoint)."
}
```

Everywhere else `cp_reduction_fraction` was used downstream (e.g. the `ration_metabolizable_protein` calculation a few lines below, and anywhere reporting `amino_acid_cp_reduction_fraction` in the published payload) needs to be updated to use the new points-based value or removed if it no longer makes sense as a "fraction." Search the file for `cp_reduction_fraction` and update every usage consistently — don't leave a mix of the old fractional variable and the new points-based one.

**Verify:** with amino-acid balancing on and a baseline CP of e.g. 17%, confirm the resulting ration CP is roughly 15% (17 − 2pp), not ~16% (17 × 0.94, the old relative-cut result).

---

## TASK 4 — Missing `nitrogen_excretion_reduced_flag`

**File:** `dairy_abm/agents/feed_crop_agent.py`

**Problem:** Blueprint marks this an "HTML-required" output flag. It doesn't exist anywhere in the code.

**Fix:** In the `tick()` method, once `amino_acid_balancing_active` and the CP reduction (Task 3) are computed, derive the flag directly from whether a reduction was actually applied this tick:

```python
nitrogen_excretion_reduced_flag = amino_acid_balancing_active and cp_reduction_points > 0.0
```

Add `"nitrogen_excretion_reduced_flag": nitrogen_excretion_reduced_flag,` to the published `feed_crop_packet` payload dict, next to the existing `amino_acid_balancing_active` field.

**Verify:** grep the payload for the new key with amino-acid balancing toggled on vs off in a scenario run; confirm it flips accordingly.

---

## TASK 5 — Missing `rp_lys_flag` / `rp_met_flag`

**File:** `dairy_abm/agents/feed_crop_agent.py`

**Problem:** Blueprint requires these two specific booleans. Code has `lysine_adequacy` / `methionine_adequacy` (floats) instead — a different signal.

**Fix:** Don't remove the adequacy floats — they're useful — but add the required booleans alongside them, since the blueprint explicitly asks for both a flag and (implicitly, via "supplementation") an underlying rate:

```python
rp_lys_flag = bool(amino_acid_balancing_active)
rp_met_flag = bool(amino_acid_balancing_active)
```

These are meant to signal that rumen-protected lysine/methionine supplementation is active as the mechanism that makes the CP reduction (Task 3) work without losing milk yield — per the blueprint they're tied to the policy being on, not to the adequacy ratio. Add both to the payload dict:

```python
"rp_lys_flag": rp_lys_flag,
"rp_met_flag": rp_met_flag,
"lysine_adequacy": lysine_adequacy,
"methionine_adequacy": methionine_adequacy,
```

**Verify:** confirm both new keys appear in the packet payload and toggle with the amino-acid policy flag.

---

## TASK 6 — ME never varies by production system or season

**File:** `dairy_abm/agents/feed_crop_agent.py`, plus `configs/calibration.json`

**Problem:** `ration_me_mj_per_kg_dm` is a single flat constant (`11.5`) for the whole simulation. Blueprint requires production-system-based initialization (arid grazing 8.0–9.5, humid/temperate 9.5–12.5, high-intensity >10.5) and says ME "should vary over time rather than stay fixed."

**Fix, in two parts:**

**6a — Production-system initialization.** Add a `feed_crop.production_system` scenario setting (`"arid_grazing"`, `"humid_temperate"`, `"high_intensity"`) and three calibration bands instead of one flat value:

In `configs/calibration.json` under `"feed_crop"`, replace the single `metabolizable_energy_mj_per_kg_dm` entry with:
```json
"metabolizable_energy_mj_per_kg_dm_arid_grazing": {
  "value": 8.75, "unit": "MJ/kg DM", "valid_range": "8.0..9.5",
  "source": "abm_blueprint.html", "assumption": false,
  "description": "ME initialization midpoint for arid grazing systems."
},
"metabolizable_energy_mj_per_kg_dm_humid_temperate": {
  "value": 11.0, "unit": "MJ/kg DM", "valid_range": "9.5..12.5",
  "source": "abm_blueprint.html", "assumption": false,
  "description": "ME initialization midpoint for humid/temperate mixed systems."
},
"metabolizable_energy_mj_per_kg_dm_high_intensity": {
  "value": 11.5, "unit": "MJ/kg DM", "valid_range": "10.5..",
  "source": "abm_blueprint.html", "assumption": false,
  "description": "ME initialization floor for high-intensity developed systems (>10.5)."
}
```

In `feed_crop_agent.py`, replace the flat lookup:
```python
ration_me_mj_per_kg_dm = float(
    value(self.ctx.calibration, "feed_crop.metabolizable_energy_mj_per_kg_dm")
)
```
with a production-system dispatch, computed once in `__init__` or at the top of `tick()`:
```python
production_system = str(self.ctx.scenario.get("production_system", "high_intensity"))
me_key = {
    "arid_grazing": "feed_crop.metabolizable_energy_mj_per_kg_dm_arid_grazing",
    "humid_temperate": "feed_crop.metabolizable_energy_mj_per_kg_dm_humid_temperate",
    "high_intensity": "feed_crop.metabolizable_energy_mj_per_kg_dm_high_intensity",
}.get(production_system, "feed_crop.metabolizable_energy_mj_per_kg_dm_high_intensity")
base_me_mj_per_kg_dm = float(value(self.ctx.calibration, me_key))
```

**6b — Seasonal variation.** The blueprint leaves the exact function unspecified ("implementation assumption"), so pick a simple, documented sinusoidal modifier rather than inventing something elaborate — reuse the existing seasonal-modifier pattern already in the file (search for `feed_seasonal_yield_modifier` and mirror its structure/day-of-year math) so there's one consistent seasonal mechanism in the agent, not two different ones:
```python
day_of_year = day.timetuple().tm_yday
seasonal_me_amplitude = float(value(self.ctx.calibration, "feed_crop.seasonal_me_amplitude_fraction"))
seasonal_me_modifier = 1.0 + seasonal_me_amplitude * cos(2 * pi * (day_of_year - 200) / 365.0)
ration_me_mj_per_kg_dm = base_me_mj_per_kg_dm * seasonal_me_modifier
```
(`cos`/`pi` need importing from `math` if not already imported in this file — check the top of `feed_crop_agent.py` first.) Add `seasonal_me_amplitude_fraction` to calibration.json (`assumption: true`, since the blueprint doesn't give an exact function — document that clearly in the `description` field, e.g. "Peak-to-baseline seasonal ME swing; exact form not specified in blueprint §8.7, implementation choice.").

**Verify:** run the same scenario with `production_system` set to each of the three values and confirm `ration_me_mj_per_kg_dm` differs accordingly; run a full-year scenario and confirm ME oscillates across months rather than staying constant.

---

## TASK 7 — No phosphorus/potassium recovery from water effluent

**File:** `dairy_abm/agents/water_agent.py`, `configs/calibration.json`

**Problem:** Only nitrogen effluent recovery exists, and it's disabled by default (coefficient `0.0`). No P/K path exists at all from water.

**Fix:** Mirror the pattern already used for manure's N→P→K derivation (fixed ratios off of N) rather than inventing new absolute coefficients — check `manure.phosphorus_to_nitrogen_fraction` / `manure.potassium_to_nitrogen_fraction` in `calibration.json` and reuse the same ratios for consistency, since the blueprint doesn't give separate water-specific P/K coefficients:

In `water_agent.py`, wherever `recovered_n_kg` is computed, add:
```python
phosphorus_to_nitrogen = float(value(self.ctx.calibration, "manure.phosphorus_to_nitrogen_fraction"))
potassium_to_nitrogen = float(value(self.ctx.calibration, "manure.potassium_to_nitrogen_fraction"))
recovered_p_kg = recovered_n_kg * phosphorus_to_nitrogen
recovered_k_kg = recovered_n_kg * potassium_to_nitrogen
```
Add both to the published `water_packet` payload. Also reconsider whether `water.nutrient_recovery_enabled` should default to `true` now that this is a real, complete pathway — that's a scenario-design decision for you and Dr. Kaniyamattam, not something to flip silently; leave the default as-is unless you decide otherwise, but note the option.

**Verify:** with `nutrient_recovery_enabled: true` and a nonzero `nutrient_recovery_kg_n_per_l`, confirm `recovered_p_kg` and `recovered_k_kg` appear in the payload and scale with `recovered_n_kg`.

---

## TASK 8 — L4 sludge-to-fertilizer is a dead end

**File:** `dairy_abm/agents/manure_agent.py`

**Problem:** `dairy_processor_agent.py` publishes `fertilizer_residual_kg` on `processor_residual_packet`, but `manure_agent.py` only reads `energy_feedstock_kg` from that packet (line 196) — `fertilizer_residual_kg` is never consumed.

**Fix:** Treat processor fertilizer residual the same way compost nitrogen is treated — feed it into the same N/P/K nutrient-return ledger that already exists (see `nutrient_return_kg = digestate_n_kg + compost_n_kg` around line 181). You'll need a mass→N conversion; reuse `manure.compost_n_retention_fraction`-style logic or, more directly, treat the processor fertilizer residual as an addition to the compost pool before N is derived from it (since it's already a solid/sludge byproduct conceptually similar to compost feedstock):

```python
processor_fertilizer_residual_kg = (
    require_nonnegative(
        "processor_fertilizer_residual_kg",
        float(processor_residual.payload.get("fertilizer_residual_kg", 0.0)),
    )
    if processor_residual is not None
    else 0.0
)
```
Add this near the existing `processor_residual_energy_kg` line. Then fold it into the nutrient ledger — the simplest correct approach is to add its nitrogen-equivalent contribution using the same retention fraction already used for compost:
```python
processor_residual_n_kg = processor_fertilizer_residual_kg * float(
    value(self.ctx.calibration, "manure.compost_n_retention_fraction")
) * float(value(self.ctx.calibration, "manure.residual_sludge_n_fraction"))
nutrient_return_kg = digestate_n_kg + compost_n_kg + processor_residual_n_kg
```
Add `manure.residual_sludge_n_fraction` to `calibration.json` (nitrogen content per kg of processor sludge residual — this needs a real number from Dr. Kaniyamattam or a labeled `assumption: true` placeholder; don't invent a precise-looking value without flagging it as unsupported).

Also feed `processor_residual_n_kg` into the L1 feed-offset credit alongside compost, if you want the L4→L1 handoff to be a genuine closed loop rather than just a bigger N number:
```python
if l1_enabled:
    self.ctx.state["loop_credits"]["feed_offset_kg"] += (compost_kg + processor_fertilizer_residual_kg) * float(
        value(self.ctx.calibration, "feed_crop.nutrient_loop_feed_substitution_fraction")
    )
```

Add `"processor_fertilizer_residual_kg"` and `"processor_residual_n_kg"` to the published `manure_packet` payload for traceability.

**Verify:** enable the processor and whey unit in a scenario, confirm `processor_residual_n_kg` is nonzero and that `nutrient_return_kg` increases relative to a run with the processor off.

---

## TASK 9 — Environment KPIs aren't tagged target/practice/result/outcome

**File:** `dairy_abm/agents/environment_agent.py`

**Problem:** Blueprint (FAO LEAP alignment, §8.8): "Every Environment KPI published to Farm Manager should carry one of these tags." None do.

**Fix:** Add a small tagging dict alongside the existing KPI computations and publish it as its own payload field rather than restructuring every existing key (minimizes downstream breakage for Farm Manager and any dashboard code consuming the flat payload today):

```python
kpi_leap_tags = {
    "gross_ghg_co2e": "result",
    "net_ghg_co2e": "result",
    "ghg_intensity_kg_co2e_per_l": "result",
    "emission_intensity_kg_co2e_per_kg_protein": "result",
    "carbon_credits_value": "outcome",
    "ICirc": "practice",
    "OCirc": "practice",
    "use_count": "result",
    "cycle_count": "outcome",
}
```
Add `"kpi_leap_tags": kpi_leap_tags` to the published `environment_packet` payload. Confirm the key names in the dict exactly match the actual payload keys already in the file (grep the file for each before finalizing — don't guess at spelling).

**Verify:** payload now contains a `kpi_leap_tags` dict; spot-check a couple of tag assignments against the FAO LEAP definitions quoted in the blueprint (target = policy goal, practice = adopted action, result = measured flow, outcome = system-level effect) to make sure the categorization is defensible, not just present.

---

## TASK 10 — No NPV calculation

**File:** new file, e.g. `dairy_abm/analysis/npv.py`, or a post-processing script — **not** inside the running agents.

**Why not in the model itself:** NPV needs a discount rate and a cash-flow horizon, which are analysis-time choices, not simulation state. Bolting it into `FarmManagerAgent` would conflate the running simulation with a downstream financial-analysis step. Keep it separate.

**Fix:** Write a small script that reads the `daily.csv`/`annual.csv` outputs (or the `annual_records` list already accumulated in `ctx`) and computes discounted cash flow:

```python
def npv(cash_flows: list[float], discount_rate: float) -> float:
    return sum(cf / (1.0 + discount_rate) ** year for year, cf in enumerate(cash_flows))
```

Apply it to the annual `net_farm_profit` series and, separately, to each equipment asset's `annual_benefit` series from `_equipment_roi()`, so you get both a whole-farm NPV and per-asset NPVs. Pick a discount rate defensible for this context (typical agricultural capital projects: 5-8%) and state it explicitly in the paper rather than hardcoding it silently — expose it as a script argument or config value, not a buried constant.

**Verify:** run against a completed scenario's annual output and sanity-check the NPV sign/magnitude against the already-computed ROI — a strongly positive-ROI investment should also show positive NPV at a reasonable discount rate.

---

## TASK 11 — Equipment catalogue only covers 4 assets

**File:** `dairy_abm/agents/farm_manager_agent.py`, `_equipment_roi()`

**Problem:** Only `milking_parlour_bulk_tank`, `dairy_processor`, `whey_processor`, `manure_system` are tracked. Blueprint's fuller list (biodigester, CHP, separator, water system, solar) isn't broken out.

**Fix:** Decide first whether this is worth doing for the paper's scope, or whether you'd rather scope the paper's economic-module claim down to the four assets that exist — extending this is real modeling work, not a quick patch, since each new asset needs its own `annual_benefit` formula (e.g. biodigester's benefit ≈ energy_value + carbon_credit_value already computed by Energy/Environment; CHP's benefit needs to be split out from biodigester if tracked separately; solar's benefit ≈ its own displaced-grid share, which currently isn't separated from biogas-driven displacement). If you proceed:

1. Add capex entries to a scenario `equipment_capex` dict: `"biodigester"`, `"chp_unit"`, `"solids_separator"`, `"water_treatment_system"`, `"solar_array"`.
2. For each, write a matching `annual_benefit` expression in `_equipment_roi()` using fields already available on the Energy/Water/Environment packets (e.g. `solar_array` benefit = `solar_kwh_generated × electricity_price`, which requires Energy to publish `solar_kwh` separately from `biogas_gross_kwh` — check whether it already does before assuming it).
3. Extend the returned equipment-ROI dict with the new keys, keeping the existing four untouched so nothing downstream breaks.

**Verify:** with capex set for a new asset, confirm its ROI/payback appear in the payload and are `null` (not a crash) when capex is `$0`, matching the existing behavior for the original four.

---

## TASK 12 — Solar isn't scaled per cow

**File:** `dairy_abm/agents/energy_agent.py`, `configs/calibration.json`

**Problem:** `solar_capacity_kw` is a flat farm-level policy value with no herd-size linkage.

**Fix:** Add an optional per-cow sizing mode. Keep the existing flat-capacity path as the default (don't break existing scenarios) and add an opt-in scenario flag:

```python
if bool(self.ctx.scenario.get("solar_sized_per_cow", False)):
    herd_size = int(self.ctx.state.get("herd_size", len(self.ctx.state.get("cows", []))))
    kw_per_cow = float(value(self.ctx.calibration, "energy.solar_kw_per_cow"))
    solar_capacity_kw = herd_size * kw_per_cow
else:
    solar_capacity_kw = max(0.0, float(self.ctx.state["policy"].get("solar_capacity_kw", 0.0)))
```
Add `energy.solar_kw_per_cow` to `calibration.json` with `assumption: true` (blueprint doesn't give a number for this — say so plainly in the description).

**Verify:** toggle `solar_sized_per_cow` on/off in an otherwise-identical scenario and confirm `solar_capacity_kw` scales with herd size only in the "on" case.

---

## TASK 13 — USDA ERS TB-1961 solids mass-balance ledger is unbuilt (optional per blueprint)

**File:** `dairy_abm/agents/dairy_processor_agent.py`

This is the lowest priority — the blueprint marks it explicitly optional ("Optional mass-balance path when component ledgers are enabled"). Only do this if the paper specifically claims component-level mass-balance validation of the processor. If so:

Add the eight named coefficients to `calibration.json` under a new `dairy_processor.usda_ers` sub-block (or flat keys prefixed `usda_ers_`), sourced directly to the blueprint (`assumption: false`, since these are named USDA figures, not modeling choices):
```json
"usda_ers_fat_required_butter": {"value": 0.8050, ...},
"usda_ers_snf_required_butter": {"value": 0.0185, ...},
"usda_ers_fat_required_american_cheese": {"value": 0.3282, ...},
"usda_ers_snf_required_american_cheese": {"value": 0.8510, ...},
"usda_ers_fat_required_other_cheese": {"value": 0.2488, ...},
"usda_ers_snf_required_other_cheese": {"value": 0.8590, ...},
"usda_ers_fat_required_dry_whey": {"value": 0.0100, ...},
"usda_ers_snf_required_dry_whey": {"value": 0.9400, ...}
```
Then add a new optional method, gated by a scenario flag (e.g. `processor_component_ledger_enabled`), that computes `fat_required_lb`/`snf_required_lb` per product line from `product_mix` output volumes, sums them, and reports `residual_fat_lb`/`residual_snf_lb` as `input_fat_lb - sum(fat_required)` and similarly for SNF. Publish these as new fields on `processor_residual_packet` rather than replacing the existing yield-fraction logic — this should be an additive diagnostic ledger, not a replacement for the working product-mix model.

**Verify:** with the flag on, confirm `residual_fat_lb`/`residual_snf_lb` appear and are sanity-checked against known milk composition (residuals shouldn't be wildly negative, which would indicate the product mix is infeasible given input solids).

---

## After all tasks: re-run the full suite and regenerate the paper sections

```bash
pytest -q
```

Then re-read `paper_sections_3.4_3.5.md` from earlier and update every place it described a gap as still-open — Tasks 1, 3, 4, 5, 7, 8, and 9 each remove one of the caveats currently written into that draft. Don't just delete the caveat sentences; replace them with a short accurate description of the new behavior, the same way the rest of that document is written.