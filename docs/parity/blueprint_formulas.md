# ABM Dairy Farm Blueprint: formula inventory and code conformance check

- **Blueprint:** `1a2e6259-Blueprint.html` (about 364k characters of text). I read the full text, all 88 KaTeX `math-block` elements and all `<pre>` code blocks. The `<script>` blocks contain only UI code: theme switching, copy buttons, search and the KaTeX fallback. They hold no model content.
- **Codebase:** `$HOME/mnt/research-agents` on the user's Mac. I only read files there and changed nothing.
- **Status labels:** **MATCH** means the code implements the formula as written. **PARTIAL** means the form is right but some part is missing or changed. **DIFFERENT** means the code uses a different coefficient, form or unit. **MISSING** means I found no implementation. **N/S** means the blueprint marks the item "not clearly specified", so any code there is an implementation assumption and cannot be matched.
- **File references:** `ga`=agents/genetics_agent.py, `ca`=cow_agent.py, `fa`=feed_crop_agent.py, `ma`=manure_agent.py, `ea`=energy_agent.py, `da`=disease_agent.py, `ev`=environment_agent.py, `fm`=farm_manager_agent.py, `sa`=sensors_agent.py, `wa`=water_agent.py, `pa`=dairy_processor_agent.py, `mk`=market_agent.py, `la`=land_agent.py, `cal`=configs/calibration.json.

---

## Agent 1: Genetics (G)

| # | Blueprint formula / rule (section) | Parameters and defaults | Status | Code evidence and difference |
|---|---|---|---|---|
| G-1 | `net_merit_score_i = Σ_j w_j · trait_{i,j}` (§4.3) | w = scenario and signal weights after renormalisation | PARTIAL | `ga:_full_merit` has the right Σw·trait form, and it flips the sign of RFI only. The weights are not NM$9 (see G-2). **BWC gets a positive weight**, so a higher BWC ranks better. NM$9 gives BWC a negative weight. |
| G-2 | USDA NM$9 (01-25, rev. Feb 2026) table (§4.3). NM $/PTA: Milk 0.022, Fat 5.01, Protein 3.33, PL 30, SCS −74, BWC −57, UDC 8, FLC 3, DPR 6, CA$ 1, HCR 1.5, CCR 4.3, LIV 14.3, HTH$ 1, RFI −0.35, EFC 2, HLIV 8.2. FM/CM/GM columns as tabled. NM emphasis %: 3.2/31.8/13.0/13.0/−2.6/−11.0/1.3/0.4/2.1/3.3/0.5/1.8/5.9/1.5/−6.8/1.0/0.8. CM: fat 30.0, protein 17.4, milk −2.7. FM: milk 17.6, fat 31.7, protein 0. GM: fat 30.3, DPR 5.6, CCR 5.2, HCR 0.9, PL 6.9, BWC −13.0, RFI −7.6 | Official values, to be kept versioned and configurable | DIFFERENT | `ga:_SCENARIO_TEMPLATES` holds invented weights over 9 traits. For NM they are milk_yield 0.25, butterfat 0.16, protein 0.16, rfi 0.14, BWC +0.06, livability 0.08, fertility 0.07, health 0.06, calving 0.02, against NM$9 emphasis of milk 3.2%, fat 31.8%, protein 13.0%, BWC −11.0%, RFI −6.8%. The PL, SCS, UDC, FLC, DPR/HCR/CCR split, EFC and HLIV traits are absent. `cal genetics.trait_weights` (milk 0.35, feed_eff 0.30, fertility 0.15, health 0.10, surv 0.10) is a second, separate weight set that is used only for `herd_net_merit_score`. |
| G-3 | Feed Saved: `PTA FSAV = −1·PTA RFI − 162.7·PTA BWC`; `REL FSAV = 0.617·REL RFI + 0.383·REL BWC` (§4.3) | Holstein | MISSING | Not found. |
| G-4 | Breeder's equation `ΔG_annual = h²·i·σP / L` (§8.1) | h² 0.26–0.43, default 0.35. i is derived from the proportion selected. σP and L need external calibration | MATCH (formula) | `ga:annual` lines 229–234. i = φ(z)/p (`_selection_intensity_i`). cal: h² 0.35, p 0.2, σP 0.054, L 3.0; the last three are implementation values. ΔG is reported but never applied to herd traits (see G-14). |
| G-5 | `RFI_fat = actual_DMI − expected_DMI` (§8.2) | none | MATCH | `ga:record_daily_intake` line 72 computes sensor-observed DMI − Eq 2-1 expected DMI and averages it into `rfi_fat_phenotype`. |
| G-6 | `actual_DMI = expected_DMI + RFI_fat` (§8.3) | none | PARTIAL | See C-2. |
| G-7 | `enteric_CH4 = k · actual_DMI`, where k is diet-dependent and owned outside Genetics (§8.3) | k is calibrated externally | MATCH | Implemented in Cow (C-6). Genetics does not own k. |
| G-8 | Low-RFI animals emit 15–25% less CH₄. Keep this as a bounded range and do not hard-code 20% unless it is documented (§8.4) | `ch4_advantage_range` (0.15, 0.25) | MISSING | No such parameter or logic. |
| G-9 | `effective_RFI_fat = RFI_fat_EBV · r_cross_diet` (§8.5) | r 0.33–0.67, default 0.50 | DIFFERENT | cal 0.5 is correct. The code multiplies **`ebv_confidence`** by 0.5 after a detected diet change (`ga` line 81) instead of scaling the RFI that is passed on. The diet-change detector (ΔME > 0.5 or ΔNDF > 0.03) is an implementation choice. `ca` line 284 adds the raw `rfi_fat_ebv`. |
| G-10 | RFI observation gate: fewer than 35 days/ticks gives low confidence and parent prior; 35 or more is valid (§3, §8.6) | 35 | MATCH | `ga` lines 61–79. The counter resets on a missed observation, so it requires a contiguous window. Confidence = min(1, days/35); the ramp is N/S in the blueprint. |
| G-11 | Offspring trait = parent average + small random variation (§7.2) | Variance N/S | PARTIAL | `ga:_offspring_trait_vector` uses mean + N(0, 0.02·\|mean\|) (cal 0.02). It then clamps each trait at ≥ 0 with `max(0.0, …)`, which **forces rfi_fat_ebv to be non-negative**, so efficient negative-RFI values are lost. It produces only one calf per year, whose "dam" and "sire" are the top two ranked cows. Ordinary calvings in `ca` lines 364–379 copy the dam's trait vector with no averaging and no variation. The code also adds `genome_markers`, which the blueprint lists as unsupported (§2.6, §7.1). |
| G-12 | Rank by weighted score and select top N% (§7.3) | N% N/S | MATCH | `ga:annual` line 240 uses cal `selection_intensity` 0.2, which is the top 20%. |
| G-13 | Signal reweighting (§3, §4.4). High feed cost raises the RFI weight and the BWC penalty. Disease raises health. High cull price or mortality raises livability. Grazing raises fertility. Renormalise afterwards. Increments N/S | Thresholds N/S | DIFFERENT | Ranking uses `full_weights`: GM ×1.1 fertility, grazing ×1.1 fertility, mortality ×1.25 livability, any disease ×1.25 health, "sustainability" ×1.15 RFI, then renormalisation. **Feed-cost stress (×1.25) is applied only to `selection_weights`**, which feed reporting and not ranking, and there is no BWC change. **The cull-price rule is reversed**: a LOW cull price (< 700) raises survivability ×1.15 (cal `low_cull_price_threshold`), and only in `selection_weights`. |
| G-14 | Annual improvement of 0.75–1.0%/yr under RFI selection. An out-of-range gain should be flagged (§7.5, §10) | none | PARTIAL | cal `annual_rfi_gain_fraction` 0.00875 (the midpoint) is applied by multiplying the **selected adult cows'** `feed_efficiency_trait` by (1 − 0.00875) (`ga` line 244). That mutates inherited state after birth, which Cow §11.4 forbids. No range audit flag. |
| G-15 | `herd_mean_rfi_fat` = mean of the cows' `rfi_fat_ebv` (§2.4) | none | DIFFERENT | `ga` line 239 averages `feed_efficiency_trait` over eligible cows. |
| G-16 | Missing scenario weight table: halt breeding and raise a config error (§9) | none | MATCH | `ga` line 197 raises `ConfigError`. |
| — | RFI units: official RFI is lb DMI/lactation and needs explicit conversion before daily use (§2.1) | none | MISSING | `rfi_fat_ebv` is added directly as kg/day (`ca` line 284). |

## Agent 2: Cow (C)

| # | Blueprint formula / rule | Parameters | Status | Code evidence and difference |
|---|---|---|---|---|
| C-1 | NASEM Eq 2-1: `DMI = [3.7 + 5.7·P + 0.305·MilkE + 0.022·BW + (−0.689 − 1.87·P)·BCS] × [1 − (0.212 + 0.136·P)·e^(−0.053·DIM)]` (§4.2) | P = 0 primiparous, 1 multiparous. BCS 1–5. MilkE in Mcal/d. BW in kg | MATCH | `ca:_expected_dmi`. Parity ≤ 1 maps to 0. DIM is floored at 1. Clamp ≥ 0. |
| C-2 | `actual_DMI_t = expected_DMI_t + effective_RFI_fat + ε_t` (§4.2, §8.1) | ε ~ N(0, CV·expected) | PARTIAL | `ca` line 284 is correct except that it uses the raw EBV (G-9). Line 304 then multiplies the result by `feed_efficiency_trait`, the heat loss, ration coverage and water availability, and SARA applies a further ×0.9. The realised DMI is therefore not the published formula. |
| C-3 | CV = 0.11–0.22, default 0.15 (§8.1) | none | MATCH | `ca` line 283 clamps to [0.11, 0.22] with default 0.15. The default is hard-coded as a scenario default and is not in cal. |
| C-4 | Heat stress (§3.2, §8.4). THI < 68: no effect. 68–72: DMI −5%, milk −3%. > 72: DMI −10–15%, milk −10–20% | cal: 68, 72, 0.05/0.03, 0.12/0.15 | MATCH | `ca` lines 195–220. Values are inside the ranges. |
| C-5 | THI > 72 raises reproductive-failure probability (§8.4) | Magnitude N/S | MISSING | Conception probability (`ca` line 384) does not use THI. |
| C-6 | `enteric_CH4_t = k_diet · actual_DMI_t`, with k_diet falling as ME rises (§8.2) | k_diet external | MATCH | `ca` line 312 computes 0.42·(DMI/22)·(10.5/ME), so k_diet = 0.42/22·10.5/ME. cal `ch4_me_reference_constant` = 10.5. |
| C-7 | `ch4_per_litre = base_ch4 × (10.5/ME)` and `enteric_CH4 = milk_l × ch4_per_litre` (§8.2). One path must be chosen consistently | base_ch4 N/S | PARTIAL | The 10.5/ME scaling is applied inside the DMI path. The milk-intensity path is not implemented; intensity is output as CH₄/milk. The result is consistent but a hybrid of the two paths. |
| C-8 | `NUE = milk_N / dietary_N`. Range 20–32%, ceiling 40–45% (§8.3) | none | MATCH | `ca` lines 405–412 at herd level: milk N = L × 0.033 × 0.16, with litres treated as kg. No range check. |
| C-9 | SARA trigger: rumen pH < 5.8 for ≥ 3 consecutive ticks (§8.5) | 5.8, 3 | MATCH | `ca` lines 264–271 with cal 5.8 and 3. |
| C-10 | SARA effects: digestibility −10%, milk −5–8%, FCR worsens (§8.5) | none | DIFFERENT | Milk −6% is correct. "Digestibility −10%" is implemented as **DMI −10%** (cal `sara_dmi_loss_fraction` 0.10, which is labelled as a blueprint value). That lowers DMI/milk by about 4%, so **FCR improves instead of worsening**. |
| C-11 | Estrus: 10–30% rumination drop; detection 85% single, 95% fused; latent and detected states kept separate (§8.6) | none | PARTIAL | Detection happens in `sa` (S-6). `ca` line 384 multiplies conception by `estrus_reliability` again, even though detection was already sampled at that reliability, so reliability counts twice. There is no latent estrus state. See also S-6: by default no estrus is ever detected. |
| C-12 | Penalty order: intake → heat → disease → SARA (§4.3) | none | MATCH | Penalties are multiplicative, so order does not change the result. |
| C-13 | FCR is null when milk = 0 (§10) | none | PARTIAL | Returns 0.0, at herd level only. |
| C-14 | Clamp DMI ≥ 0 (§10) | none | MATCH | `max(0.0, …)`. |
| C-15 | A dead cow exits early (§10, §11.3) | none | MATCH | `ca` line 242. |
| C-16 | No unsupported random mortality inside Cow (§11.8) | none | DIFFERENT | `ca` lines 394–396 apply 4%/yr random mortality (cal `mortality_rate_annual`). |
| C-17 | `update_rumen_ph()` from grain:fiber, feeding frequency and sensor (§3.1). Function N/S | none | MISSING | No endogenous pH model. pH comes only from the sensors, which pass through `cow.rumen_ph` or the baseline 6.2, so SARA cannot trigger unless a scenario injects `rumen_ph_sensor`. |
| C-18 | Eq 2-1 envelope: lactating Holstein, about 1–368 DIM. A fallback is needed outside it (§9) | none | PARTIAL | Applied to every cow with DIM > 0 and no DIM cap. No fallback. |
| N/S | MilkE pipeline, lactation curve, manure mass, BCS/BW update, water penalty, mortality hazard | none | N/S | Code uses MilkE = kg·(0.0929·fat% + 0.0547·prot% + 0.0395·lact%) with fat% = 3.9·butterfat_ebv, which multiplies a lb-PTA EBV into a percentage. It uses a Wood-style lactation factor, manure = 60·DMI/22, ±0.02 BCS/day, and milk and DMI × water fraction. All are assumptions. |

## Agent 3: Feed / Crop (F)

| # | Blueprint | Params | Status | Code evidence and difference |
|---|---|---|---|---|
| F-1 | ME by system: arid 8.0–9.5, humid/temperate 9.5–12.5, high-intensity > 10.5 MJ/kg DM (§8.1) | none | MATCH | cal 8.75, 11.0, 11.5. `fa` adds a ±5% cosine seasonal swing; the seasonal function is N/S. |
| F-2 | CP 16–18% standard, 14–15% optimised (§8.4) | none | PARTIAL | cal local 0.18 and import 0.16 fit the standard band. There is no explicit optimised target; AA balancing gives CP − 2 pp. |
| F-3 | `excess_N = (dietary_cp_pct − mp_requirement_pct) × DMI`, clamped ≥ 0 (§4.4, §8.2) | none | DIFFERENT | Feed does not compute it. `ma` line 132 uses max(0, CP_kg − **MP supply**_kg), with MP = 0.64·CP. There is no `mp_requirement_pct` anywhere, so "requirement" is replaced by supply. |
| F-4 | NASEM Eq 2-2: `12.0 − 0.107·fNDF + 8.17·ADF/NDF + 0.0253·fNDFD − 0.328·(ADF/NDF − 0.602)·(fNDFD − 48.3) + 0.225·MY + 0.00390·(fNDFD − 48.3)·(MY − 33.1)` (§4.4) | none | MISSING | No fNDF, ADF/NDF or fNDFD inputs. Only a constant NDF of 0.38. |
| F-5 | MY must be in kg/d with one consistent L→kg convention (§4.4) | none | MISSING | Not applicable because Eq 2-2 is absent. Elsewhere the code uses a density of 1.03, but not for this. |
| F-6 | Eq 2-2 limits: DIM > 60, Holstein, no large NFFS changes, fNDFD fallback 52.0% (§4.4) | none | MISSING | none |
| F-7 | +1 unit forage NDFD gives +0.17 kg/d DMI and +0.25 kg/d FCM (§4.4) | none | MISSING | none |
| F-8 | Unsaturated fat: −0.41 kg DMI per 1% added fat (§4.4) | none | MISSING | none |
| F-9 | `local_feed_autonomy = (own_farm + local)/total_feed_demand`, bounded 0–1 (§4.4) | none | DIFFERENT | `fa` line 235: numerator = own-farm (inventory + crop) + grazing only, which **excludes the local tier**. Denominator = total feed supplied, not demand. |
| F-10 | Sourcing: own_farm → local → market, with an optional plant_coproduct tier between own_farm and local (§8.6, §8.9) | none | MATCH | `fa` lines 130–138: own → plant_coproduct → dairy_return → local → market. The loop feed offset is used first. The code does not keep an enum `feed_sourcing_state`. |
| F-11 | Amino-acid balancing (§8.3): CP −1.5–2.5 pp, rp_lys/rp_met true, urinary N −10–20%, milk maintained, water −21 L/cow/day, NUE +5–6 pp | none | PARTIAL | `fa` lines 179–195. CP −0.02 (2 pp) with a 0.025 cap but **no 1.5 pp floor**. The flags are correct. Water is handled in `wa`. The urinary-N reduction is not applied or bounded; it emerges only through the manure formula. NUE +5–6 pp is not enforced. |
| F-12 | Catch crop: `n_leaching = 0.5 × baseline` (§8.5) | none | MATCH | `fa` line 225 (the 0.5 is hard-coded). The baseline rate is cal 0.02/day of soil N, which is an assumption. |
| F-13 | Heat stress leads to higher energy density and electrolytes (§3.3). Magnitude N/S | none | MISSING | Feed never reads THI or the heat flag. |
| F-14 | Whey/scotta/co-product feed gated by safety flags (§8.9) | none | MATCH | `coproduct_feed_allowed` gating. |
| F-15 | `feed_cost_day` from ration composition, sourcing and supplements (§3.1) | none | PARTIAL | Only purchased feed is priced (`fa` line 228). Own-farm, local and co-product feed cost nothing. There is no RP-AA supplement cost; the blueprint says that cost is not specified. |
| F-16 | `feed_cost_signal` to Genetics; threshold N/S (§2.3) | none | PARTIAL | Genetics reads the market `feed_cost_per_kg_dm` against cal 0.40, which is an implementation value. |

## Agent 4: Manure (M)

| # | Blueprint | Status | Code evidence and difference |
|---|---|---|---|
| M-1 | `collected = manure_inflow × collection_efficiency` (§8.1) | MATCH | `ma` line 90. cal eff = 1.0, an implementation value. |
| M-2 | `uncollected = inflow − collected` (§8.1) | MATCH | `ma` line 91. |
| M-3 | `storage_overflow_flag = stored_inventory > storage_capacity` (§8.2) | MATCH | `ma` lines 123–125 and 235. The overflow mass is added to unmanaged CH₄; the overflow-loss equation is N/S. |
| M-4 | `urinary_N = f(excess_N)`; f is N/S (§8.3) | PARTIAL | f is linear: 0.75 × excess protein × 0.16, capped at ration N. Excess is measured against MP supply (see F-3). |
| M-5 | Fecal N is linked to digestibility and kept separate from urinary N (§4.3) | DIFFERENT | `fecal_N = ration_N − urinary_N` with no digestibility term. **Manure N total = dietary N**: milk N is never subtracted, so the N balance counts milk N twice. |
| M-6 | `digester_feedstock_total = manure + grass + food_waste`, target 68/17/15 (§8.5) | MATCH | `ma:_cofeed_assembly` sets target_total = manure/0.68, with the feasibility flag and cal 0.68/0.17/0.15. The code also adds processor residual kg, which is an extension. |
| M-7 | Co-feed safety gate (§8.7) | MATCH | `ma` line 44 raises the alert `cofeed_safety_rejected`. |
| M-8 | `digester_capacity_percent` 0/50/100 (§8.6) | PARTIAL | Read from `scenario.digester_capacity_pct`. Farm Manager never dispatches it. |
| M-9 | Herrero shares: manure CH₄ about 10%, manure N₂O about 29% (§8.4) | MISSING | No validation reference. |
| M-10 | Route fractions must be feasible: renormalise or reject (§3.3, §10) | MATCH | `ma` line 36 raises `ConfigError` if the sum ≠ 1. |
| N/S | Biogas yield, storage CH₄, SOC delta, digestate concentrations | N/S | VS 0.08 × BMP 0.24 m³ CH₄/kg VS, published as "biogas volume". SOC uses 0.12 and 0.25, hard-coded scenario defaults that are not in cal. |

## Agent 5: Energy (EN)

| # | Blueprint | Status | Code evidence and difference |
|---|---|---|---|
| EN-1 | `electricity_generated_kwh = 85.73 × digester_feedstock_total_t` (§3.2, §8.1) | DIFFERENT | `feedstock_gross_kwh = 85.73·t` is correct (cal 85.73). The **published** `electricity_generated_kwh = net_kwh = (85.73·t + solar + syngas) × (1 − 0.12 parasitic)` (`ea` lines 53–57, 114). Feedstock also includes processor residuals. The blueprint wants separate source fields that are combined only in the balance (§10). |
| EN-2 | `displaced = min(E, demand)` (§8.2) | MATCH | `ea` line 67, using net_kwh. |
| EN-3 | `surplus = max(0, E − demand)` | MATCH | `ea` line 68. |
| EN-4 | `self_sufficiency_pct = 100·displaced/demand` if demand > 0 | MATCH | `ea` lines 69–71. Returns None when demand is 0. |
| EN-5 | `energy_cost_saved_day = displaced × electricity_price` | MATCH | `ea` line 86. cal price 0.12 is an implementation value. |
| EN-6 | `carbon_credits_earned = ghg_offset_reported × carbon_credit_price` | MATCH | `ea` line 89: kg/1000 × $/t. The price defaults to 0. Farm Manager uses the Environment credit, not this one, so credits are not counted twice. |
| EN-7 | Compute heat only if a calibrated coefficient is supplied (§8.5) | PARTIAL | heat = net_kwh × 4.74 MJ/kWh (cal, EPA-derived, marked as an assumption). It is derived from electricity rather than from biogas. |
| EN-8 | E4 scenarios at 0/50/100% (§2.6) | MATCH | Implemented through M-8. |
| N/S | m³→kWh fallback coefficient not specified (§4.2) | N/S (flag) | The diagnostic `biogas_gross_kwh = m³ × 0.6 × 9.97 × 0.38` is hard-coded and not in cal. Manure's value is already **CH₄** m³ (VS×BMP), so the 0.6 methane fraction is applied twice. It is diagnostic only. |

## Agent 6: Disease (D)

| # | Blueprint | Status | Code evidence and difference |
|---|---|---|---|
| D-1 to D-3 | `S' = S − new_inf`; `I' = I + new_inf − recov − deaths`; `R' = R + recov` (§8.1) | MATCH | Per-cow transitions in `da:tick`. Counts are recomputed from per-cow state. |
| D-4 | `transmission_pressure = f(I/N, density, biosecurity, vaccination, stress, resistance, quarantine)`; form N/S (§8.2) | PARTIAL | β·I_eff/N·(1 − bio·0.8)·density is multiplicative, which is fine. The code also adds **background sporadic infections** (mastitis 0.0008 + lameness 0.0005 per day) that are outside SIR. Resistance uses the legacy `trait_vector['health']`, and only when it exceeds 1, instead of `health_composite_score`. Stress = THI ≥ 68 or SARA. |
| D-5 | Modifier order: base → density → biosecurity → vaccination → stress → resistance → quarantine (§4.4) | MATCH | The modifiers are multiplicative, so order does not matter. Each modifier is published in the packet. |
| D-6 | Per-cow Bernoulli draws (§8.3) | MATCH | none |
| D-7 | Recovery and mortality probabilities are configurable (§8.4) | MATCH | cal 0.18/day and 0.0/day. |
| D-8 | Quarantine reduces contact (§8.5) | MATCH | Infected cows count ×(1 − 0.7). |
| D-9 | Infected cows get yield_penalty > 0; S and R get 0 (§8.6) | MATCH | 0.18 (cal). |
| D-10 | E3 outbreak at tick 100 with mastitis/FMD labels (§8.7) | MATCH | `da:_seed_outbreak`, default tick 100. Seed count defaults to 1; the blueprint does not specify it. |
| D-11 | Validation: high biosecurity plus resistance reduces outbreak duration and loss by > 40% (§8.8) | MISSING | No check or test found. |
| D-12 | `herd_immunity_status` threshold N/S; publish null/unknown if none is configured (§10) | DIFFERENT | "full" when every live cow is R. `days_to_herd_immunity` is derived from that. |
| D-13 | biosecurity 0–100% (§2.3) | PARTIAL | Unit ambiguity: values ≤ 1 are read as a fraction and values > 1 as %. The FM auto-response `max(level, 0.75)` means 75% only when the level is stored as a fraction. |
| D-14 | `disease_frequency_signal` to Genetics | MATCH | infected_count. |

## Agent 7: Environment (ENV)

| # | Blueprint | Status | Code evidence and difference |
|---|---|---|---|
| ENV-1 | `gross = enteric_CH4 + manure_storage_CH4 + field_N2O` (CO₂e) (§8.1) | PARTIAL | `ev` line 98 also adds unmanaged CH₄ and compost N₂O. The blueprint allows extra positive streams. |
| ENV-2 | `net = gross − avoided_grid − avoided_synthetic_fertilizer` (§8.3) | DIFFERENT | The code also subtracts a **soil-carbon offset** of SOC_kg × 3.67 (hard-coded) plus the land delta (`ev` line 81). The blueprint's minimal net has only the two avoided terms. |
| ENV-3 | `intensity_per_litre = net/milk` if milk > 0 (§8.4) | MATCH | `ev:_intensity`. |
| ENV-4 | `gross_emission_intensity = gross/milk` (§8.4) | MISSING | none |
| ENV-5 | `per_kg_protein = (gross or net)/protein_kg` (§8.5) | PARTIAL | net/(milk_L × 0.033) only. |
| ENV-6 | `carbon_credits_value = validated_creditable_offset × price` (§8.6) | PARTIAL | Uses **all avoided CO₂e, including soil**, with no validation step. |
| ENV-7 | Herrero reference shares 65/10/29, for diagnostics only (§8.2) | MISSING | none |
| ENV-8 | Sustainability score 0–100 must be a configurable function with no hard-coded weights; publish null if none is configured (§4.5, §10) | DIFFERENT | `60·circularity + 40·avoided_fraction` is hard-coded (`ev` line 135). |
| ENV-9 | Soil biodiversity index N/S; publish null or a configured value (§2.4) | DIFFERENT | Invented as `soil_index × (1 + tree_cover)`. |
| ENV-10 | Avoided grid = displaced energy × factor, where the factor is external (§8.7) | MATCH | cal 0.38 kg/kWh, marked as an assumption. |
| ENV-11 | Avoided fertilizer = digestate substitution × factor (§8.3) | PARTIAL | recycled_n_used (compost, digestate and water N) × cal 5.0. |
| ENV-12 | Daily ingest, weekly offsets, monthly netting (§11) | PARTIAL | Nets daily and aggregates monthly. |
| ENV-13 | FAO NUE/ICirc/OCirc/use_count/cycle_count plus target/practice/result/outcome tags (§8.8) | PARTIAL | Present, with ad hoc definitions. |
| ENV-14 | Zero milk gives null intensity (§10) | MATCH | none |
| ENV-15 | Negative net is allowed (§10) | MATCH | none |
| N/S | Field N₂O EF, GWPs | N/S (flag) | field N₂O = precursor N × 0.01 "kg N₂O/kg N". If that is meant to be IPCC EF1, which is in N₂O-N, the 44/28 factor is missing; I am not sure which is intended. GWP 27.2/273 are config values; the blueprint warns against hard-coded IPCC factors. `rfi_attributed_ch4_delta` uses a hard-coded ×0.01. |

## Agent 8: Farm Manager (FM)

| # | Blueprint | Status | Code evidence and difference |
|---|---|---|---|
| FM-1 | `net_farm_profit = total_revenue − total_costs` (§8.1) | MATCH | `fm` line 148. Revenue = milk + by-product + energy_value (electricity + heat) + Environment credits. Costs = feed, water, cooling, processing energy, disease, labour (3.5/cow/day), fixed (250/day). The blueprint does not specify the energy-saving convention. |
| FM-2 | `cash_{t+1} = cash_t + revenue_t − costs_t` (§8.2) | MATCH | `fm` lines 171–176, daily. |
| FM-3 | `ROI = annual_circular_benefit / investment_cost_basis` (§8.3) | MATCH | The benefit is **one day's value × 365**. Returns null when there is no investment. |
| FM-4 | `payback = investment / annual_benefit` if the benefit > 0 | MATCH | none |
| FM-5 | `recommendation_score = f(severity, objective_weights, persistence, expected_benefit)` (§8.4) | MISSING | Sorts by tier only. The triggers are invented, for example treatment cost > feed cost. |
| FM-6 | Tiers Critical/Important/Advisory. An outbreak must force a Critical biosecurity recommendation (§4.4, §10) | PARTIAL | Tiers exist. An outbreak does not force a Critical recommendation; it only auto-raises biosecurity in `dispatch_policy`. |
| FM-7 | Controls: biosecurity 0–100, digester 0–100, breeding priority {milk, disease, CH4}, feed policy {standard, amino_balanced}, scenario {NM, CM, FM, GM} (§8.5) | PARTIAL | NM/CM/FM/GM are correct. Breeding priority uses {profit, sustainability, beef_on_dairy}. feed_mode uses {balanced, precision} plus an AA flag. digester_capacity is not dispatched by FM. |
| FM-8 | Objective weights: economic, environmental, disease, genetics (§2.2, §4.2); no arbitrary weights (§11) | DIFFERENT | profit 0.5, environment 0.2, animal_welfare 0.2, circularity 0.1, with hard-coded normalisations (profit/1000, net/5000) and auto triggers (1000 kg CO₂e, 500 feed cost, 30% energy). |
| FM-9 | Policy gates: cofeed_safety_approved, coproduct_feed_allowed, thermochemical_route_active, sdg_reporting_mode (§8.6) | MATCH | `model._initialize_policy_state`. |
| FM-10 | A single final carbon-credit source (§10) | MATCH | Uses the Environment credit only. |

## Agent 9: Sensors (S)

| # | Blueprint | Status | Code evidence and difference |
|---|---|---|---|
| S-1 | `THI = f(T, RH)`; formula N/S (§8.1) | N/S, likely bug | `sa:_thi` computes `F − (0.55 − 0.0055·RH)·(F − 26)`. The standard NRC (1971) form is `(1.8T + 32) − (0.55 − 0.0055·RH)·(1.8T − 26)`, which is the same as `(F − 58)`. The code's version gives a THI that is **32·(0.55 − 0.0055·RH) lower**, about 7 THI points at 60% RH. At 30 °C and 60% RH the code gives about 72.8, against 79.8 for the standard form. |
| S-2 | Heat flag bands 68/72 (§4.2, §8.1) | PARTIAL | Boolean flag at ≥ 68 only. |
| S-3 | `dmi_measured = dmi_observed + error`; error model N/S (§8.2) | PARTIAL | Multiplicative N(0, 0.04·(1 + degradation)). The degradation is tied to bolus age, which the blueprint links to pH noise, not DMI. |
| S-4 | `rumen_ph_noise = g(bolus_age)`; noise rises from about 80–90 ticks until replacement (§8.3) | DIFFERENT | **No pH noise at all**; pH passes through unchanged. Degradation starts at 0.8×90 = 72 ticks and inflates DMI noise instead. Replacement falls due at 90 (cal). |
| S-5 | SARA flag: pH < 5.8 for ≥ 3 ticks (§8.4) | MATCH | `sa` lines 128–131. |
| S-6 | Estrus: rumination −10% to −30%; accuracy 85% single, 95% fused; downgrade to single if an input is missing (§8.5) | PARTIAL | Logic and anchors are correct: activity ≥ 1.2 AND rumination change ≤ −0.2, then a reliability draw. **No code generates `activity_signal` or `rumination_change_pct`**, so by default no estrus is detected. With `estrus_required_for_conception` = True, conceptions never happen unless the scenario herd supplies those fields. |
| S-7 | Thermal mastitis alert with accuracy > 87% (§8.6) | PARTIAL | A constant 0.87 confidence, applied only to cow IDs the scenario lists. There is no detector. |
| S-8 | Farm Manager receives filtered alerts only (§4) | MATCH | none |
| S-9 | Missing weather gives THI = null (§10) | MATCH | none |
| S-10 | A fused-mode request with missing inputs is downgraded to single (§10) | MATCH | none |

## Agent 10: Water (W)

| # | Blueprint | Status | Code evidence and difference |
|---|---|---|---|
| W-1 | `total = drinking + cleaning + irrigation` (§8.1) | PARTIAL | `wa` line 213, minus the AA adjustment, which is allowed as a separate term. The irrigation term is freshwater irrigation already net of the previous day's loop credit (see W-4). |
| W-2 | `treated = wastewater × treatment_recovery_fraction` (§8.2) | MATCH | cal 0.35, an implementation value. |
| W-3 | `recycled_irrigation = min(treated, irrigation_demand)` (§8.3) | MATCH | none |
| W-4 | `net_freshwater = total − recycled_irrigation` (§8.3) | PARTIAL | Possible **double credit**. `fa` already subtracts `water_offset` (treated × 0.7 from the previous day) from irrigation, and `wa` then subtracts recycled_irrigation again. |
| W-5 | `L water per L milk = total/milk` (§8.4) | MATCH | none |
| W-6 | 21 L/day AA anchor; scaling basis N/S and must be configured explicitly (§8.5) | PARTIAL | 21 L × cow_count, which is a hard-coded per-cow basis, applied only when the CP reduction is > 0. |
| W-7 | Recycled water goes to irrigation before freshwater (§4.2) | MATCH | none |
| W-8 | Clamp negative values (§10) | MATCH | none |

## Agent 11: Dairy Processor (P)

| # | Blueprint | Status | Code evidence and difference |
|---|---|---|---|
| P-1 | `revenue_stream = quantity × price_stream`, with $/lb prices from the dairy-situation CSV and conversion to lb (§4) | DIFFERENT | Products are valued as L milk-equivalent × cal $/L (0.55/0.55/0.50/0.42/0.65). No CSV wholesale $/lb prices and no lb conversion. |
| P-2 | `byproduct_revenue = Σ revenue_stream`; revenue for internal feed loops is 0 (§4) | DIFFERENT | `pa` line 134: by-product revenue = feed-return litres × 0.03 $/L, so internal feed loops earn revenue. |
| P-3 to P-9 | USDA ERS TB-1961. fat_butter 0.8050, snf_butter 0.0185, fat_AmCheese 0.3282, snf_AmCheese 0.8510, fat_otherCheese 0.2488, snf_otherCheese 0.8590, fat_dryWhey 0.0100, snf_dryWhey 0.9400 (× lb output) | MISSING | None of these coefficients appear in code or cal. |
| P-10, P-11 | `residual_fat = fat_in − Σ fat_required`; `residual_snf = skim_solids_in − Σ snf_required` | MISSING | `component_balance` is just litres × 0.039/0.087/0.032. |
| P-12 | Value pyramid: food → feed → energy/materials → disposal (§1) | PARTIAL | Whey goes 50% to feed and the rest to disposal, skipping energy. Waste milk goes 70% to feed, then energy. Sludge goes 50% to energy, then fertilizer. |
| P-13 | Keep the agent instantiated with zero flows when unused (§7) | MATCH | When disabled it publishes an inactive zero-flow packet. |
| P-14 | Missing price gives physical outputs with low-confidence revenue (§3) | PARTIAL | Falls back silently to cal prices. |

## Agent 12: Market (MK)

| # | Blueprint | Status | Code evidence and difference |
|---|---|---|---|
| MK-1 | `price_index = p_t / p_t0` | MISSING | none |
| MK-2 | `Δp = (p_t − p_{t−1}) / p_{t−1}` | PARTIAL | Only \|Δp\| for milk, labelled `realized_volatility`. |
| MK-3 | `r = log p_j − log p_{j−1}`; `RV_t = Σ r²` within the month (Dong-Du-Gould) | MISSING | No RV sum. |
| MK-4 | `mvol_t = Var(Δlog P_d)` over the first 20 trading days of month t | DIFFERENT | `mk` line 238: population **stdev** of the **last 20** simulated daily log returns × √252, which is a rolling, annualised figure. |
| MK-5 | `Butterfat = (Butter − 0.2272) × 1.211` | MISSING | none |
| MK-6 | `Nonfat solids = (NFDM − 0.2393) × 0.99` | MISSING | none |
| MK-7 | `Other solids = (DryWhey − 0.2668) × 1.03` | MISSING | none |
| MK-8 | `Class III = ClassIII_skim × 0.965 + Butterfat × 3.5` | MISSING | none |
| MK-9 | `Class IV = ClassIV_skim × 0.965 + Butterfat × 3.5` | MISSING | The code's component price is fat/protein/solids fractions × raw butter/cheddar/NFDM prices, which is not the USDA formula. |
| MK-10 | `mvol_hat = c + S_t + 0.54·cheese_use_supply + 0.62·usdx_return + 0.18·corn_vol + 0.11·vix + 0.027·speculation` | MISSING | Only `macro_context` pass-through. |
| MK-11 | NA values are carried forward with a quality warning | MATCH | `mk:_observed_prices`. |
| MK-12 | Clamp negative prices | MATCH | none |
| MK-13 | Monthly keyed by Year + Period + Frequency, with annual fallback | MATCH | `mk:_select_observation`. |
| MK-14 | Modes: static, observed, observed_plus_shock | PARTIAL | The shock is also applied in static mode; its stddev is 0 by default. |
| MK-15 | One synchronised packet per tick | MATCH | none |
| note | cwt→L | not in the blueprint | cal `market.class_cwt_to_l_conversion` 43.97 is **unused**. The code uses 45.359/1.03 = 44.04. |

## Agent 13: Land (L, optional)

| # | Blueprint | Status | Code evidence and difference |
|---|---|---|---|
| L-1 | Disabled by default | MATCH | cal `land.enabled` = false. |
| L-2 | When off, land logic stays in Feed/Crop | MATCH | `fa` uses `land.cropland_ha` and sets `land_owner` = feed_crop. |

## Scheduler order (SCH) and numeric interface rules (IF)

The code's daily order is set in `model._run_daily`:

Market → Sensors → (Land) → Feed/Crop → FM.dispatch_policy → Disease → Water.prepare_delivery → Cow → Processor → Manure → Energy → Water → Environment → FM.tick → Genetics.record_daily_intake

After the daily run come the weekly, monthly and annual hooks. Annual order is Genetics.annual, then FM.annual.

| # | Blueprint rule | Status | Code evidence and difference |
|---|---|---|---|
| SCH-1 | Sensors runs at tick 0, before Feed and Cow | MATCH | none |
| SCH-2 | Market runs before FM profit and Feed/Energy pricing | MATCH | none |
| SCH-3 | Feed runs after Sensors and before Cow | MATCH | none |
| SCH-4 | FM policy refresh runs before Disease | MATCH | none |
| SCH-5 | Disease runs before Cow milk | MATCH | none |
| SCH-6 | Cow runs before Manure and Environment | MATCH | none |
| SCH-7 | Manure → Energy → Environment | MATCH | none |
| SCH-8 | Water runs after Cow and Feed, before Environment | MATCH | none |
| SCH-9 | Environment runs before FM | MATCH | none |
| SCH-10 | Genetics records daily and ranks annually | MATCH | none |
| SCH-11 | Weekly crop/soil, digestate return and energy/offset steps; monthly environmental netting | PARTIAL | `BaseAgent.weekly` is a no-op everywhere, so every step runs daily. |
| SCH-12 | Feed consumes the same-day Cow state | PARTIAL | Feed runs before Cow and uses the previous day's `cow_daily_packet` DMI, a one-tick lag. |
| SCH-13 | Cow internal order: expected DMI → actual DMI → heat → rumen pH → SARA → milk → manure → CH₄ → NUE → reproduction | PARTIAL | The rumen-pH update step is missing. The rest follows this order. |
| IF-1 | Cow → Env packet: `actual_dmi_kg_dm`, `enteric_ch4_g_day`, `ebf_pct` | DIFFERENT | Herd-total `enteric_ch4_kg` in kg, not g. No `ebf_pct`. |
| IF-2 | Cow → Manure per cow: `actual_dmi_kg_dm`, `manure_kg_day` | PARTIAL | Herd totals, plus per-cow records without manure. |
| IF-3 | Feed → Cow: `diet_nem_mcal_kg`, `diet_neg_mcal_kg` | DIFFERENT | Publishes ME in MJ/kg DM instead. |
| IF-4 | Eq 2-2 MY in kg/d | MISSING | none |
| IF-5 | Conversion of official RFI/PTA units (lb/lactation) to daily units | MISSING | none |
| IF-6 | All environment packets converted to common CO₂e/period units, with period_type on each | PARTIAL | Streams are tagged "daily". |
| IF-7 | One synchronised market packet | MATCH | none |

## calibration.json values that disagree with the blueprint or cite it without support

1. **The `dairy_processor.*` source tags point at values the blueprint does not contain.** These entries are tagged `source: abm_blueprint.html, assumption: false`, but none of their numbers appear in the blueprint:
   - `product_mix` 0.4/0.2/0.15/0.15/0.1
   - `whey_yield` 0.88/0.05/0.1
   - `fraction_sludge_of_milk` 0.02 and `fraction_waste_milk_of_milk` 0.03
   - `fraction_whey_to_feed` 0.5, `fraction_sludge_to_energy` 0.5 and `fraction_waste_milk_to_feed` 0.7
   - `fraction_milk_to_processor` 1.0

   The same applies to `land.silvopastoral_tree_cover_fraction` 0.1 and `land.soil_carbon_sequestration_index` 1.0. They may come from an older blueprint version, but that is not verifiable.
2. **Genetics weights are not NM$9.** `genetics.trait_weights` does not match NM$9, and neither do the code-embedded scenario templates. The BWC sign is also wrong in ranking.
3. **The cull-price rule points the wrong way.** `genetics.low_cull_price_threshold` = 700 triggers on a LOW cull price; the blueprint triggers on a HIGH cull price or high mortality.
4. **`cow.sara_dmi_loss_fraction` 0.10** is tagged as a blueprint value, but the blueprint's −10% applies to digestibility, not DMI.
5. **`cow.heat_stress_milk_loss_fraction` 0.08** is unused (legacy).
6. **`feed_crop.amino_acid_cp_reduction_points` 0.02** has the unit label "percentage points", but the code treats the value as a fraction, so it equals 2.0 pp. That is consistent in number but the label is misleading. The valid range 0.015–0.025 in cal is not enforced below 0.015.
7. **`energy.parasitic_load_fraction` 0.12**, together with solar and syngas being added in, makes the published `electricity_generated_kwh` differ from 85.73·t.
8. **`sensors.bolus_replacement_ticks` 90** is correct, but degradation starts at a hard-coded 0.8×90 = 72 ticks instead of 80–90.
9. **`market.class_cwt_to_l_conversion` 43.97** is unused.
10. **Blueprint values that are missing from cal:**
    - DMI CV 0.15, which is hard-coded in `ca`
    - The CH₄ advantage range 0.15–0.25
    - Herrero shares 0.65/0.10/0.29
    - The NM$9 table and FSAV coefficients
    - The eight USDA ERS solids coefficients
    - The USDA class-price constants (0.2272, 1.211, 0.2393, 0.99, 0.2668, 1.03, 0.965, 3.5)
    - The Dong-Du-Gould coefficients
    - The catch-crop 0.5 and the CP cap 0.025, both hard-coded
11. **Values the blueprint says not to hard-code without calibration** are present in cal, all flagged as implementation values: GWP 27.2/273, field EF 0.01, grid 0.38, fertilizer 5.0 kg CO₂e/kg N, and circularity weights 0.3/0.3/0.2/0.2. The sustainability-score weights 60/40 are hard-coded in code, not cal.
12. **These cal values match the blueprint:** h² 0.35, cross-diet 0.5, 35 days, annual gain 0.00875, THI 68/72, heat losses 0.05/0.03/0.12/0.15, SARA 5.8/3 and milk loss 0.06, ME 8.75/11.0/11.5, CP 0.16/0.18, digester mix 0.68/0.17/0.15, 85.73 kWh/t, estrus 0.85/0.95 and −0.2, mastitis 0.87, water saving 21 L/cow/day, and land disabled.

## Blueprint items marked "not clearly specified" that cannot be matched exactly

- **Genetics:** thresholds for "high" feed cost or disease; weight increment sizes; precedence when several stressors occur; offspring variance and correlation; tie-break rule; N% selected; σP; L; exact EBV confidence ramp; reduced-trait proxy mapping.
- **Cow:** lactation curve; milk-protein conversion; MilkE pipeline; manure mass equation; mortality hazard; BCS/BW update; water-insufficiency penalty; rumen-pH feeding-frequency effect; base_ch4 or k_diet; conception probability; how disease, heat and SARA combine beyond their ordering; fallback DMI outside the Eq 2-1 envelope.
- **Feed:** crop-growth and fertilizer-response equations; ME prediction from NDF/ADF; optimizer and multi-objective weights; local and import price functions; digestate substitution coefficient; RP-AA cost; seasonal ME function; synchrony formula; electrolyte and energy-density increments; shortage fallback; FEDNA values.
- **Manure:** biogas yield per kg; digestate and compost nutrient concentrations; storage CH₄ as a function of time or temperature; SOC function; overflow loss factor; fecal/urinary split function f(); fallback when the co-feed mix is infeasible.
- **Energy:** m³→kWh coefficient; heat coefficient; CHP split; methane minimum; grid emissions factor; credit protocol and price; electricity price.
- **Disease:** β, recovery, mortality and quarantine/vaccination/biosecurity/stress/resistance effect sizes and functional form; seed count; herd-immunity threshold; vaccination-coverage formula; milk-loss magnitude; vet cost.
- **Environment:** grid and fertilizer factors; N₂O EF; sustainability-score and biodiversity formulas; credit eligibility; protein denominator; ICirc/OCirc boundaries; net-zero threshold.
- **Farm Manager:** utility function; tier thresholds; recommendation_score f(); convention for energy savings as revenue; milk price; capex; hysteresis.
- **Sensors:** THI formula; THI response coefficients; DMI error distribution; pH-noise function g(); fusion rule; mastitis threshold; alert scoring.
- **Water:** drinking and cleaning demand; wastewater-return fraction; treatment efficiency; nutrient recovery; scaling of the 21 L anchor; water cost.
- **Processor:** plant-specific yields; whey/sludge/waste split factors; capacity and operating cost; losses; whey/scotta inclusion limits and hazard thresholds.
- **Market:** the price_index and Δp forms are "implementation-derived", with no named source formula.
