# ABM Dairy Farm — Agent Design Blueprint

Implementation-focused blueprint for the dairy ABM. For this circular-bioeconomy project, the base runtime scope is Agents **1-12** (including the Water, Dairy Processor, and Market layers); Agent **13** remains an optional land extension that should only be enabled when the project is treated as needing standalone land-state ownership *(implementation assumption)*.

    No-hallucination audit rule: prose statements in this document should be treated as implementation assumption unless they are traceable to the provided resources or already marked as not clearly specified in provided resources.
    
> **Note:** 
>       **Default runtime roster for this project:** Agents **1-12** form the base implementation so the economy layer and the by-product circular loop remain active.
>       Agent **11** stays in the base roster for interface stability, but Dairy Processing / Whey Processing CapEx and product-mix routes activate only when opted in (dashboard ROI toggles; default off). Without opt-in, milk follows milking + bulk-tank cooling and farm-gate sales.
>       Agent **12** provides the economic/price layer, and Agent **13** remains the only disabled-by-default land extension.
>       If a scenario does not use stochastic price shocks or a specific processor route, keep those agents instantiated in static or zero-flow mode rather than removing them from runtime.
>     
    Provenance note: this blueprint consolidates the available HTML, PDF, and mindmap material into a concise implementation reference. Circular-bioeconomy indicator framing, co-product routing, and food-safety constraints are additionally aligned to FAO LEAP (2025), The role of livestock in circular bioeconomy systems (DOI 10.4060/cd6765en), with chapter-level citations at the agent sections where they apply. It is strongest where the sources describe ownership and interactions; unsupported coefficients or exact submodels are intentionally left configurable or external, and any untagged certainty is an implementation assumption.

## Table of Contents

- [Agent 1 — Genetics Agent](#agent-1)
- [Agent 2 — Cow Agent](#agent-2)
- [Agent 3 — Feed / Crop Agent](#agent-3)
- [Agent 4 — Manure Agent](#agent-4)
- [Agent 5 — Energy Agent](#agent-5)
- [Agent 6 — Disease Agent](#agent-6)
- [Agent 7 — Environment Agent](#agent-7)
- [Agent 8 — Farm Manager Agent](#agent-8)
- [Agent 9 — Sensors Agent](#agent-9)
- [Agent 10 — Water Agent](#agent-10)
- [Agent 11 — Dairy Processor Agent](#agent-11)
- [Agent 12 — Market Agent](#agent-12)
- [Agent 13 — Land Management Agent](#agent-13)

---

## Agent 1 — 🧬 Genetics Agent

*Tag: Biological*

### 1. Agent Purpose

The Genetics Agent owns **breeding-state, inherited trait-state, and generation-to-generation genetic improvement** for the herd.


Its role is to:


* rank breeding candidates,
* maintain one inherited trait vector per animal,
* translate market and management priorities into selection weights,
* inject offspring trait vectors at birth/breeding events,
* propagate long-run improvement in feed efficiency, survivability, fertility, and health,
* and expose herd-level genetic progress to the Farm Manager Agent and dashboard.

The agent exists because the original HTML architecture lists a Genetics Agent as a priority component; using a dedicated breeding controller instead of embedding all genetics logic inside the Cow Agent is treated here as an *implementation assumption* informed by the genetics PDF and Basarab-derived analysis.


It solves three modeling problems that other agents do not solve:


1. **Inheritance problem**: Cow-level productivity, feed efficiency, health resilience, and calving performance must persist across generations rather than reset each birth.
2. **Selection problem**: breeding decisions must respond to farm context through market scenario, feed cost, disease frequency, and cull-value signals.
3. **Compounding improvement problem**: long-run herd performance must improve through annual breeding cycles, not only through daily management.

Subsystem ownership:


* Biological inheritance layer
* Annual breeding decision layer
* Herd genetic trend reporting layer

Optimization goal:


* maximize **scenario-weighted lifetime herd value** using a multi-trait index centered on `net_merit_score` / NM$ and trait components represented in the provided materials *(implementation assumption)*.

Primary objectives:


* improve profitability across generations,
* reduce feed cost pressure through low RFI / RFI_fat selection,
* improve livability when mortality or cull economics justify it,
* improve fertility under grazing/pasture scenarios,
* improve health composite weighting under high disease pressure,
* indirectly reduce enteric CH₄ through the modeled `RFI_fat → DMI → CH₄` chain *(exact coefficient/form not provided in sources)*.

Dependencies:


* `Feed / Crop Agent`: `feed_cost_signal`
* `Disease Agent`: `disease_frequency_signal`
* `Farm Manager Agent`: `market_scenario`, breeding priority, cull price context
* `Cow Agent`: performance records, DMI records, survival, reproduction outcomes
* `Environment Agent`: downstream consumer of herd genetic effects on CH₄
* `Sensors Agent`: indirectly, via improved DMI observation quality that feeds Cow records

Constraints:


* direct CH₄ phenotype selection is treated as an implementation assumption and not clearly specified in provided resources
* reliable RFI_fat assignment requires at least **35 continuous days/ticks** of intake records
* cross-diet RFI expression is only moderately stable (`0.33–0.67` repeatability across diets)
* the updated USDA `NM$9 (01-25)` document (revised `Feb 2026`) is the active source for economic values and relative emphasis for `NM$`, `FM$`, `CM$`, and `GM$`; any reduced-trait internal proxy must be labeled separately from the official full published index.

Expected outputs:


* `trait_vector` for each offspring/new calf
* `genetic_gain_per_generation`
* `breeding_recommendation`
* `herd_nm_trend`
* updated herd mean `RFI_fat_EBV` distribution

Contribution to global system behavior:


* shifts long-run feed efficiency,
* shifts disease resilience and survivability,
* changes replacement herd quality,
* changes feed demand indirectly,
* changes enteric CH₄ indirectly,
* changes farm economics indirectly through trait composition rather than daily control.

### 2. Agent State Variables

#### 2.1 Core inherited trait variables

| Variable | Meaning | Units | Type | Valid range | Initialization | Update frequency | Dependencies | Persistence | Class |
|---|---|---|---|---|---|---|---|---|---|
| `net_merit_score` | master breeding rank proxy aligned to official `NM$` | dollars relative to 2020 breed-base cows; official TTA SD is about `$228` for `NM$`, `CM$`, and `FM$`, and `GM$` is rescaled to the same SD (USDA `NM$9` revised `Feb 2026`) | float | exact simulated range not clearly specified | initialize from the published `NM$9 (01-25)` table values (revised `Feb 2026`) plus local signal adjustment | annual / on re-ranking | published trait values, scenario, local signals | persists per animal | dynamic, inherited |
| `butterfat_ebv` | inherited butterfat breeding value | pounds PTA | float | not clearly specified | seed from initial herd distribution or parent average | annual / birth | parent traits, scenario weights | persists per animal | dynamic, inherited |
| `protein_ebv` | inherited protein breeding value | pounds PTA | float | not clearly specified | same as above | annual / birth | parent traits | persists per animal | dynamic, inherited |
| `rfi_fat_ebv` | inherited residual feed intake adjusted for fatness; core efficiency trait | official `RFI` is in pounds DMI/lactation; if the ABM keeps daily-residual logic, explicit conversion is required before applying official index values | float | biologically bounded by herd calibration, exact global min/max not clearly specified | initialize from herd distribution centered around mean efficiency | annual / birth | parent traits, RFI observation support | persists per animal | dynamic, inherited |
| `body_weight_composite` | penalty trait for high maintenance cost | composite units | float | not clearly specified | initialize from parent average or herd baseline | annual / birth | parent traits | persists per animal | dynamic, inherited |
| `livability_score` | survival-related inherited trait for cow and heifer livability | probability-like score | float | `0–1` if implemented probabilistically; exact standardized range not clearly specified | initialize from parent mean or herd baseline | annual / birth | parent traits, mortality history weighting | persists per animal | dynamic, inherited |
| `fertility_score` | inherited conception / reproductive performance trait | probability-like score | float | `0–1` if implemented as conception probability; exact standardized range not clearly specified | initialize from parent mean or herd baseline | annual / birth | parent traits, scenario weights | persists per animal | dynamic, inherited |
| `health_composite_score` | inherited resistance to common health events | dollars if mapped to `HTH$`; otherwise explicit conversion is required | float | not clearly specified | initialize from parent mean or herd baseline | annual / birth | parent traits, disease signal | persists per animal | dynamic, inherited |
| `calving_ease_score` | inherited calving performance trait | dollars if mapped to `CA$`; otherwise explicit conversion is required | float | not clearly specified | initialize from parent mean or herd baseline | annual / birth | parent traits | persists per animal | dynamic, inherited |

#### 2.2 Decision and policy variables

| Variable | Meaning | Units | Type | Valid range | Initialization | Update frequency | Dependencies | Persistence | Class |
|---|---|---|---|---|---|---|---|---|---|
| `market_scenario` | active breeding context | enum | enum | `{NM, CM, FM, GM}` | set by the Farm Manager Agent or the user at simulation start | event-driven or annual | Farm Manager Agent | persists until changed | static between changes |
| `user_breeding_priority` | management intent | enum | enum | supported values in resources: `profit`, `sustainability`, `disease resistance` | set by the Farm Manager Agent or the user | event-driven | Farm Manager Agent | persists until changed | static between changes |
| `feed_cost_signal` | feed-cost stress input for reweighting RFI and BWC | categorical or numeric upstream signal | enum/float | threshold not clearly specified in resources | ingest from Feed / Crop Agent | weekly / annual decision point | Feed / Crop Agent | not persistent beyond decision windows unless explicitly stored | dynamic |
| `disease_frequency_signal` | disease-pressure signal for health reweighting | count or categorical pressure signal | int/enum | threshold not clearly specified | ingest from Disease Agent | outbreak-driven / annual decision point | Disease Agent | can be stored in rolling history | dynamic |
| `cull_cow_price` | economic context that changes livability emphasis | currency | float | not clearly specified | ingest from Farm Manager Agent or Market Agent | monthly / annual decision point | Farm Manager Agent, optional Market Agent | rolling current value | dynamic |
| `selection_weights` | current active trait weight vector used for ranking | normalized mapping | dict[str,float] | should sum to 1 after normalization | initialize from `market_scenario` base template | annual and on signal updates | scenario + feed/disease/cull signals | persists for generation | adaptive |

#### 2.3 Record-quality and observation variables

| Variable | Meaning | Units | Type | Valid range | Initialization | Update frequency | Dependencies | Persistence | Class |
|---|---|---|---|---|---|---|---|---|---|
| `recorded_dmi_days` | number of valid individual intake observation days per candidate | days/ticks | int | `0+` | start at `0` for new calves | daily | Cow Agent and Sensors Agent intake records | persists per candidate | dynamic |
| `ebv_confidence` | confidence / reliability of RFI_fat assignment | proportion or score | float | `0–1` | initialize low before 35-day window | daily, then annual use | `recorded_dmi_days` | persists per candidate | dynamic |
| `candidate_record_complete` | whether minimum breeding-record set exists | bool | bool | `{true,false}` | false until required fields exist | daily / annual | cow performance records | persists | dynamic |
| `cross_diet_repeatability_modifier` | factor applied when diet regime changes | float | float | `0.33–0.67` supported; midpoint `0.50` recommended in integrated analysis if a single default is required | initialize as `1.0` before diet-switch logic or from configured default | event-driven on diet change | Feed / Crop Agent diet-state | persists until restabilization | dynamic |

#### 2.4 Breeding-cycle and trend variables

| Variable | Meaning | Units | Type | Valid range | Initialization | Update frequency | Dependencies | Persistence | Class |
|---|---|---|---|---|---|---|---|---|---|
| `candidate_pool` | current list of eligible breeding animals | ids/list | list | herd-dependent | initialize from herd | annual breeding cycle | Cow herd state | transient per cycle | dynamic |
| `selected_parents` | subset chosen for breeding | ids/list | list | `0..N` | empty before ranking | annual | ranking results | transient per cycle | dynamic |
| `offspring_trait_vector` | output trait package for newborn calf | structured record | dict | trait-dependent | generated at breeding event | birth / breeding event | parent traits + random variation | persists into calf state | inherited |
| `genetic_gain_per_generation` | realized trait improvement summary | score or vector delta | float/dict | not clearly specified as single metric; annual gain for RFI-supported traits `0.75–1.0%/year` | initialize at `0` | annual | selected vs base herd means | persists in trend history | dynamic |
| `herd_nm_trend` | time series of herd mean net merit score | time series | list[float] | not bounded in resources | initialize with baseline herd mean | annual | current herd scores | persists across run | historical |
| `herd_mean_rfi_fat` | mean herd efficiency trait state | trait units | float | herd-calibrated | initialize from herd distribution | annual | all cows’ `rfi_fat_ebv` | persists in trend history | dynamic |
| `breeding_recommendation` | human-readable recommendation for next breeding cycle | string/structured message | str/dict | not applicable | initialize null | annual / on signal changes | scenario + trait-pressure changes | latest only or full history | dynamic |

#### 2.5 Calibration variables

| Variable | Meaning | Units | Type | Supported value | Initialization | Update frequency | Dependencies | Persistence | Class |
|---|---|---|---|---|---|---|---|---|---|
| `heritability_h2_rfi_fat` | heritability for RFI_fat | proportion | float | `0.26–0.43`; integrated midpoint `0.35` if single default required | configure from calibration | static or scenario-level | Basarab calibration | persists | static |
| `selection_intensity_i` | selection-intensity term in breeder’s equation | unitless | float | not clearly specified numerically | derive from proportion selected | annual | candidate selection fraction | persists per generation | dynamic |
| `phenotypic_sd_sigma_p` | phenotypic SD of RFI_fat | trait units | float | not clearly specified | external calibration required | static or periodically recalculated | observed herd records | persists | calibration |
| `generation_interval_L` | generation interval in breeder’s equation | years | float | not clearly specified | external calibration required | static or scenario-level | herd demography | persists | calibration |
| `ch4_advantage_range` | uncertainty range mapping low-RFI animals to CH₄ reduction | proportion | tuple[float,float] | `0.15–0.25` | initialize from Basarab-derived range | static | CH₄ mapping logic | persists | calibration/uncertainty |

#### 2.6 Variables treated as unsupported as active Genetics state

These should **not** be active Genetics Agent state variables unless later described in additional sources:


* direct `ch4_phenotype_score`
* residual methane selection metric
* genomic marker arrays
* mutation rate
* explicit crossover rate
* direct milk-yield penalty from low RFI

### 3. Agent Behaviors and Actions

| Behavior | Trigger | Inputs | State transitions | Outputs | Recovery / termination |
|---|---|---|---|---|---|
| `initialize_base_weight_vector()` | simulation start or scenario change | `market_scenario` | loads scenario-specific trait priority template | `selection_weights` | ends once weights loaded |
| `ingest_management_signals()` | weekly or annual decision window | `feed_cost_signal`, `disease_frequency_signal`, `cull_cow_price`, `user_breeding_priority` | updates current decision context | refreshed signal state | ends each cycle |
| `reweight_selection_index()` | after signal ingestion | active weights + signals | increases RFI weight under high feed cost; increases health weight under high disease frequency; increases livability weight under high cull price / mortality pressure; increases fertility weight under grazing scenario | updated normalized `selection_weights` | ends after normalization |
| `update_candidate_record_quality()` | daily | DMI records, performance records | increments `recorded_dmi_days`; recomputes `ebv_confidence` | updated record-quality state | continuous until annual breeding |
| `validate_rfi_observation_window()` | before annual ranking | `recorded_dmi_days` | marks candidate as fully observed only at `>=35` days/ticks | `candidate_record_complete`, `ebv_confidence` | ends at ranking |
| `score_breeding_candidates()` | annual breeding cycle | trait vector + current weights | computes current `net_merit_score` proxy | ranked candidate list | ends after ranking |
| `select_top_parents()` | after ranking | ranked candidates, selection fraction | fills `selected_parents` | selected parent ids | ends when breeding list locked |
| `generate_offspring_trait_vector()` | each breeding/birth event | parent trait vectors | assigns offspring trait values as parent average + small random variation | `offspring_trait_vector` | ends once calf initialized |
| `apply_breeders_equation()` | annual generation update | `h²`, `i`, `σP`, `L` | updates expected herd mean improvement trajectory | `genetic_gain_per_generation`, updated herd mean expectation | ends once annual trend recorded |
| `apply_cross_diet_rfi_modifier()` | feed regime changes | `cross_diet_repeatability_modifier`, current `rfi_fat_ebv` | tempers expressed RFI under new diet | effective RFI passed downstream | ends after diet restabilization logic |
| `publish_genetic_outputs()` | end of breeding cycle | trend and recommendation state | none | `trait_vector`, `herd_nm_trend`, `genetic_gain_per_generation`, `breeding_recommendation` | ends after message dispatch |

#### Behavior details

##### initialize_base_weight_vector()
Base scenario logic inferred from the genetics PDF and integrated notes *(implementation assumption where exact mapping is not clearly provided in supplied resources)*:


* `NM$`: official all-around lifetime-profit index from the updated `NM$9` document (revised `Feb 2026`) with strongest positive emphasis on fat (`31.8%`), then protein and PL (`13.0%` each), plus negative maintenance/feed pressure through BWC (`-11.0%`) and RFI (`-6.8%`).
* `CM$`: cheese-oriented index from the same updated source with strong fat (`30.0%`) and protein (`17.4%`) emphasis, negative milk-volume emphasis (`-2.7%`), and similar PL / health structure to `NM$`.
* `FM$`: fluid-oriented index from the same updated source with the highest milk-volume emphasis (`17.6%`), strong fat emphasis (`31.7%`), zero direct protein emphasis, and the same PL / BWC / RFI structure as the published table.
* `GM$`: grazing-oriented index from the same updated source with strong fat emphasis (`30.3%`), materially higher fertility emphasis (`DPR 5.6%`, `CCR 5.2%`, `HCR 0.9%`), lower PL emphasis (`6.9%`), and stronger negative BWC/RFI pressure (`-13.0%` and `-7.6%`).

The official scenario coefficients and relative emphases are specified by `NM$9 (01-25)` in the updated USDA revision (`Feb 2026`). Implementation should still keep them versioned/configurable so breed-specific overrides or reduced-trait proxy mappings do not get confused with the published full index.


##### reweight_selection_index()
Signal rules treated as implementation assumptions aligned with the provided resources:


* if feed cost becomes high: increase `rfi_fat_ebv` weight and increase `body_weight_composite` penalty
* if disease frequency increases: increase `health_composite_score` weight
* if cull cow prices rise or herd mortality spikes: increase `livability_score` weight
* if pasture/grazing scenario is active: increase `fertility_score` weight

Exact increment size for each weight adjustment is **not clearly specified in provided resources**.


##### validate_rfi_observation_window()
Rule used for implementation:


* fewer than `35` intake-record days/ticks: EBV confidence remains low; do not finalize observation-based RFI assignment
* at `>=35` days/ticks: RFI observation window is valid for reliable assignment

##### generate_offspring_trait_vector()
Inheritance rule used for implementation:


* offspring traits are assigned from **parent average + small random variation**

Distribution, variance scale, and correlation structure of that random variation are **not clearly specified in provided resources**.


##### apply_cross_diet_rfi_modifier()
Rule used for implementation:


* when the Feed / Crop Agent changes diet type, effective RFI expression is only partially stable across diets
* phenotypic repeatability range inferred from provided materials: `0.33–0.67`
* integrated analysis recommends midpoint `0.50` if a single deterministic default is needed

##### Behaviors that should not exist

* direct methane selection behavior
* mutation-driven adaptive search
* reinforcement-learning reward updates
* self-evolving objective function beyond signal reweighting inferred from provided materials

These are not clearly specified in provided resources.


### 4. Decision-Making Logic

#### 4.1 Decision architecture

The Genetics Agent uses a **two-stage weighted ranking system**.


##### Stage 1 — base scenario selection
Choose one base trait-priority template from:


* `NM$`
* `CM$`
* `FM$`
* `GM$`

This determines the default breeding objective (implementation assumption).


##### Stage 2 — dynamic signal adjustment
Modify the base weight vector using current farm conditions:


* feed-cost pressure
* disease frequency pressure
* cull-value / survival pressure
* user breeding priority

#### 4.2 Decision rule (implementation assumption)

A conservative ranking logic consistent with the provided materials is:


1. start with a base weight vector from `market_scenario`
2. adjust weights using active signals
3. compute per-candidate composite score
4. rank all candidates
5. select top `N%`
6. generate offspring trait vectors from selected parents
7. record generation gain

#### 4.3 Utility / scoring logic

A generic implementation form used in this blueprint is:


$$net\_merit\_score_i = \sum_j w_j \cdot trait_{i,j}$$
**Source:** USDA/ARR Net Merit report `NM$9 (01-25)`, revised `Feb 2026` (`net-merit.pdf`), for trait/economic weighting context; exact coefficient/form not provided in sources.

**Why used:** Ranks breeding candidates each annual cycle so Genetics can select parents and publish genetic-gain outputs under the active NM$/scenario weights.


Where:


* `w_j` = current scenario-and-signal-adjusted trait weights
* `trait_{i,j}` = candidate i’s breeding value or inherited trait score for trait j

Supported trait dimensions:


* butterfat
* protein
* RFI / RFI_fat
* body weight composite penalty
* livability
* fertility
* health composite
* calving ease

Published official values and relative emphasis from the updated USDA `NM$9 (01-25)` revision (`Feb 2026`) are:


| Trait | Unit | NM$ value($/PTA unit) | FM$ value | CM$ value | GM$ value | NM$ emphasis(%) | FM$ emphasis | CM$ emphasis | GM$ emphasis |
|---|---|---|---|---|---|---|---|---|---|
| Milk | pounds | 0.022 | 0.122 | -0.02 | 0.022 | 3.2 | 17.6 | -2.7 | 3.0 |
| Fat | pounds | 5.01 | 5.01 | 5.01 | 5.11 | 31.8 | 31.7 | 30.0 | 30.3 |
| Protein | pounds | 3.33 | 0 | 4.73 | 3.39 | 13.0 | 0 | 17.4 | 12.3 |
| PL | months | 30 | 30 | 30 | 17 | 13.0 | 13.0 | 12.3 | 6.9 |
| SCS | log | -74 | -42 | -95 | -75 | -2.6 | -1.5 | -3.2 | -2.5 |
| BWC | composite | -57 | -57 | -57 | -72 | -11.0 | -11.0 | -10.4 | -13.0 |
| UDC | composite | 8 | 8 | 8 | 10 | 1.3 | 1.3 | 1.3 | 1.5 |
| FLC | composite | 3 | 3 | 3 | 3 | 0.4 | 0.4 | 0.4 | 0.4 |
| DPR | percent | 6 | 6 | 6 | 17.3 | 2.1 | 2.1 | 2.0 | 5.6 |
| CA$ | dollars | 1 | 1 | 1 | 1.1 | 3.3 | 3.3 | 3.2 | 3.4 |
| HCR | percent | 1.5 | 1.5 | 1.5 | 3 | 0.5 | 0.5 | 0.5 | 0.9 |
| CCR | percent | 4.3 | 4.3 | 4.3 | 13.3 | 1.8 | 1.8 | 1.7 | 5.2 |
| LIV | percent | 14.3 | 14.3 | 14.3 | 11.4 | 5.9 | 5.9 | 5.6 | 4.4 |
| HTH$ | dollars | 1 | 1 | 1 | 1.1 | 1.5 | 1.5 | 1.4 | 1.5 |
| RFI | pounds DMI/lactation | -0.35 | -0.35 | -0.35 | -0.42 | -6.8 | -6.8 | -6.4 | -7.6 |
| EFC | days | 2 | 2 | 2 | 1.7 | 1.0 | 1.0 | 1.0 | 0.8 |
| HLIV | percent | 8.2 | 8.2 | 8.2 | 6.6 | 0.8 | 0.7 | 0.7 | 0.6 |

Important equivalence note: exact replication of the official index requires the **full published trait table** in the official units above, plus the official index mechanics where applicable. For Holsteins, the official feed-saved combination is `PTA FSAV = -1(PTA RFI) - 162.7(PTA BWC)` with `REL FSAV = 0.617(REL RFI) + 0.383(REL BWC)`. If this blueprint uses a reduced overlap trait vector such as butterfat/protein/RFI/BWC/livability/fertility/health/calving only, that remains a scenario-aligned ABM proxy and must not be presented as automatically identical to official `NM$`, `CM$`, `FM$`, or `GM$`.


Therefore:


* the updated scenario tables from `net-merit.pdf` (USDA `NM$9` revised `Feb 2026`) are represented in the blueprint,
* the score structure used here is an implementation assumption aligned to those materials,
* the full official trait set remains the required basis for exact replication,
* any reduced-trait implementation in this ABM should be treated as a documented proxy mapping rather than the official index itself.

#### 4.4 Conflict resolution logic

Supported conflict pattern:


* scenario establishes the base objective
* active stress signals locally increase priority on specific traits

Safe implementation rule:


* apply configured signal adjustments described in the provided materials
* renormalize the weight vector after adjustment
* log the final active weight vector for transparency and dashboard output

Exact precedence ordering when multiple stressors occur simultaneously is not clearly specified in provided resources.


#### 4.5 Optimization logic

Supported optimization targets:


* lifetime profitability through NM$
* feed-cost reduction through low RFI
* disease resilience through health composite
* survival through livability
* reproductive stability through fertility
* indirect CH₄ reduction through RFI_fat

Unsupported optimization targets:


* direct methane phenotype minimization
* explicit genomic optimization
* learned reward functions
* Pareto-front breeding solver with exact numeric penalties

These are not clearly specified in provided resources.


### 5. Agent Interactions

| Interaction | Direction | Timing | Exchanged information | Impact |
|---|---|---|---|---|
| Feed / Crop Agent → Genetics | incoming | weekly / annual | `feed_cost_signal` | raises RFI weight and BWC penalty when feed costs are high |
| Disease → Genetics | incoming | outbreak-driven / annual | `disease_frequency_signal` | raises health composite weight |
| Farm Manager Agent → Genetics | incoming | start + annual + event | `market_scenario`, `user_breeding_priority`, `cull_cow_price`, breeding policy | sets base objective and context |
| Cow → Genetics | incoming | daily records, annual ranking | performance records, feed intake history, survival, reproduction outcomes | candidate scoring and EBV confidence |
| Sensors Agent → Cow → Genetics | indirect incoming | daily | improved DMI record quality | raises reliability of RFI-based decisions |
| Genetics → Cow | outgoing | birth / breeding event | `trait_vector` | sets inherited productivity, efficiency, fertility, health traits |
| Genetics → Farm Manager Agent | outgoing | annual | `genetic_gain_per_generation`, `breeding_recommendation`, `herd_nm_trend` | informs policy and reporting |
| Genetics → Environment | indirect outgoing | annual via herd mean traits | herd efficiency shift | changes herd-level CH₄ trajectory through RFI_fat |

#### Synchronization rules

* daily: update record quality only
* annual: perform ranking, selection, offspring generation, genetic gain update
* event-driven: reweight when market scenario or major signal changes
* no daily breeding decisions

#### Shared variables

* with Cow: trait vector, DMI observation count, fertility-related inherited fields
* with Farm Manager Agent: scenario, breeding priority, cull price, recommendation outputs
* with Feed / Crop Agent: feed-cost pressure, diet regime state
* with Environment: herd mean RFI_fat trajectory affecting CH₄ trend

#### Failure-handling logic

* if DMI records are insufficient, fall back to parent-based inheritance and low-confidence ranking
* if scenario weights are missing, do not run breeding optimization; raise configuration error
* if Feed / Crop Agent changes diet regime, use cross-diet modifier before downstream use of RFI expression
* if direct CH₄ phenotype is requested as a selection trait, reject the request as unsupported

### 6. Environmental Integration

The Genetics Agent is not a direct resource producer or consumer. Its environmental effect is **indirect and delayed**.


#### Environmental inputs

* none as primary physical inputs
* indirect environmental context arrives through:
* feed regime changes from the Feed / Crop Agent
* grazing/pasture scenario (`GM$`)
* disease pressure that may reflect environmental stress

#### Environmental outputs

* long-run reduction in enteric CH₄ through lower RFI_fat animals
* indirect change in herd feed demand through lower intake at equal production
* indirect effect on manure volume and nutrient output through changed intake

#### Supported environmental coupling

1. `RFI_fat → DMI → enteric CH₄`
2. diet change → partial re-expression of effective RFI_fat (`0.33–0.67`)
3. herd mean genetic shift → annual trend in CH₄ reduction (`0.75–1.0%/year` reported as an expected range in integrated analysis, *exact coefficient/form not provided in sources*)

#### Spatial effects
Spatial genetics effects are not clearly specified in the provided resources and remain configurable as an implementation assumption until a direct source is added; the architecture is farm-scale, not landscape-grid based.


#### Carrying-capacity / environmental constraints
No explicit carrying-capacity logic is assigned to the Genetics Agent in the provided resources.


### 7. Genetic / Evolutionary Logic

This section applies.


#### 7.1 Genome representation

Supported representation:


* **continuous trait vector**, not discrete genotype markers

Supported trait vector fields:


* `butterfat_ebv`
* `protein_ebv`
* `rfi_fat_ebv`
* `body_weight_composite`
* `livability_score`
* `fertility_score`
* `health_composite_score`
* `calving_ease_score`

Explicit genome-marker structure is not clearly specified in the provided resources and remains configurable as an implementation assumption until a direct source is added.


#### 7.2 Inheritance logic

Supported rule:


* offspring trait = parent average + small random variation

That is the only inheritance mechanism clearly described across the accessible resources; broader inheritance mechanics are *not clearly specified in the provided resources and remain configurable as an implementation assumption until a direct source is added*.


#### 7.3 Selection logic

Supported selection criterion:


* rank candidates by weighted `net_merit_score`
* select top `N%` as parents

Exact `N%` is not clearly specified in the provided resources and the shown form is an implementation assumption used to keep interfaces and accounting constraints executable.


#### 7.4 Fitness logic

Supported breeding fitness proxy:


* weighted profitability and resilience score under the active market scenario and active farm stressors

#### 7.5 Evolution rate

Supported annual improvement:


* `0.75–1.0% per year` under RFI-based multi-trait selection

#### 7.6 Mutation / crossover

Variation mechanism used as an implementation assumption from available materials:


* parental averaging + small random variation

Treated as implementation assumptions (not clearly specified in provided resources):


* explicit mutation rate
* crossover operator
* recombination map
* genomic selection matrix

#### 7.7 Evolutionary safeguards

Supported safeguards:


* no direct CH₄ selection
* do not trust RFI observation before 35-day window
* do not assume RFI expression is identical across diets
* do not collapse breeding to a single-trait methane objective

### 8. Equations / Algorithms / Thresholds

#### 8.1 Breeder’s equation

Supported from integrated Basarab analysis:


$$\Delta G_{annual} = \frac{h^2 \cdot i \cdot \sigma_P}{L}$$
**Source:** breeder-equation convention referenced in integrated genetics discussion; explicit citation not clearly specified in provided resources.

**Why used:** Updates expected annual herd genetic gain for RFI_fat so Genetics can report genetic_gain_per_generation and herd efficiency trends.


Variables:


* `h²`: heritability of RFI_fat, inferred range from provided materials `0.26–0.43`
* `i`: selection intensity, derived from proportion selected
* `σP`: phenotypic SD of RFI_fat
* `L`: generation interval in years

Use:


* annual update of expected herd genetic improvement
* should feed `genetic_gain_per_generation` and `herd_mean_rfi_fat`

Calibration dependencies:


* `i`, `σP`, `L` need external herd calibration
* exact herd demography for translating annual gain into calf-level updates is not clearly specified

#### 8.2 RFI_fat definition

Supported form:


$$RFI\_fat = actual\_DMI - expected\_DMI$$
**Source:** dairy RFI framing from genetics/project-analysis extracts; exact herd-specific coefficientization requires external calibration.

**Why used:** Defines the cow-level efficiency residual Genetics inherits and Cow expresses around NASEM expected intake.


For dairy cows, expected-DMI interpretation and dairy RFI context must account for:


* body weight
* fat mobilization
* milk fat
* milk protein
* milk yield

This is described in Basarab-derived analysis, but exact one-to-one citation mapping is not clearly specified in provided resources.


The added DMI source now provides a published lactating-Holstein expected-DMI equation (NASEM Equation 2-1). That physiological predictor should be owned by the `Cow Agent` as the expected-intake layer, while postpartum fat mobilization remains a retained dairy-RFI context / diagnostic / fallback signal rather than an extra published coefficient inside Equation 2-1 itself; the Genetics Agent continues to own inherited `RFI_fat`-related deviation around expected intake rather than the full cow-physiology intake model.


#### 8.3 CH₄ linkage

Supported chain:


$$actual\_DMI = expected\_DMI + RFI\_fat$$
**Source:** genetics–Cow DMI residual identity (expected DMI plus inherited `RFI_fat`); not an enteric-CH₄ emission equation.

**Why used:** Links inherited intake deviation to realized DMI before enteric-CH₄ scaling in the Genetics–Cow–Environment chain.


$$enteric\_CH4 = k \cdot actual\_DMI$$
**Source:** DMI-to-enteric-CH4 directional linkage in integrated analysis; scalar `k` requires external calibration and is not a fixed universal constant.

**Why used:** Provides a simple calibrated bridge from realized DMI to enteric CH₄ so Genetics can pass inherited intake effects downstream without owning diet/emission coefficients.


Where:


* `k` is diet-dependent and belongs operationally to Cow/Environment/Feed coupling
* Genetics Agent should not own `k`
* Genetics Agent owns the inherited component that shifts DMI

#### 8.4 CH₄ differential range

Supported range:


* low-RFI_fat animals produce `15–25%` less enteric CH₄ than high-RFI_fat animals

Safe implementation:


* keep as a bounded uncertainty range
* do not hard-code a universal fixed 20% unless using the integrated midpoint as a documented default

#### 8.5 Cross-diet modifier

Supported form:


$$effective\_RFI\_fat = RFI\_fat\_EBV \cdot r_{cross\_diet}$$
**Source:** integrated genetics notes in `project-analysis.pdf`; numeric cross-diet transfer range mapping to this exact implementation form is not clearly specified in provided resources.

**Why used:** Applies cross-diet transfer so Cow daily intake uses diet-adjusted inherited efficiency rather than raw EBV.


Supported range:


* `r_cross_diet = 0.33–0.67`

If a single default is required:


* integrated paper-analysis output recommends midpoint `0.50`

#### 8.6 EBV confidence threshold

Supported threshold:


* reliable RFI measurement requires at least **35 days/ticks**

Safe implementation:


* before 35 ticks: candidate remains low-confidence, parent-based prior dominates
* after 35 ticks: observation-based RFI can be used for ranking

Exact confidence-ramp formula is not clearly specified in the provided resources and the shown form is treated as an implementation assumption to keep interfaces and accounting constraints executable.


#### 8.7 Unsupported thresholds / coefficients

The following are not clearly specified:


* exact signal threshold for “feed cost HIGH”
* exact signal threshold for “disease frequency HIGH”
* exact offspring random-variation variance
* exact tie-break rule among equal candidate scores

### 9. Data Requirements

#### Required internal datasets
| Dataset | Needed fields | Resolution | Use |
|---|---|---|---|
| `cow_performance_records` | milk yield, milk fat, milk protein, feed intake, health events, survival, reproduction | daily with annual rollups | candidate scoring |
| `parent_trait_records` | all inherited trait variables per parent | per breeding event / annual snapshot | offspring generation |
| `dmi_record_series` | observed DMI by day/tick | daily; minimum 35 contiguous observations | RFI_fat confidence and EBV validity |
| `disease_history` | outbreak counts / frequency | event + rolling window | health-weight adjustment |
| `feed_cost_history` | current and recent feed-cost signal | weekly / monthly | RFI-weight adjustment |
| `cull_price_history` | cull cow economic context | monthly / annual | livability-weight adjustment |
| `market_scenario_config` | active scenario and base weights | static or event-driven | scenario switching |

#### External calibration requirements
These require real-world calibration or externally provided config:


* breed-specific overrides or reduced-trait remapping beyond the published USDA `NM$9 (01-25)` values (revised `Feb 2026`) for `NM$`, `CM$`, `FM$`, `GM$`
* `σP` for RFI_fat
* generation interval `L`
* herd-specific intake recording quality
* initial herd trait distributions

#### Variables that can be simulated internally

* annual candidate ranking
* parent selection
* offspring trait vector generation
* trend history
* weight adjustment state
* EBV confidence tracking
* scenario switching

#### Missing-data handling

* missing DMI records: use parent-based inheritance only; do not finalize RFI observation-based ranking
* missing feed-cost signal: retain prior weight vector
* missing disease signal: retain prior health weighting
* missing cull price: do not apply livability economic boost
* missing scenario weight table: halt breeding decision and raise configuration error

### 10. Edge Cases / Failure Conditions

| Issue | Detection | Prevention | Fallback / recovery |
|---|---|---|---|
| insufficient DMI window | `recorded_dmi_days < 35` | enforce observation gate | use parent-trait prior only |
| diet switch instability | Feed changes diet class | apply cross-diet modifier `0.33–0.67` | restabilize after observation window |
| direct CH₄ selection requested | presence of methane phenotype in breeding objective | explicit validation rule | reject and log unsupported objective |
| missing scenario coefficients | no weight table for active scenario | config validation before run | stop annual breeding cycle safely |
| unrealistic annual gain | annual gain outside supported `0.75–1.0%` expectation under calibrated selection | calibration audit | flag for review; do not silently continue |
| overconfidence in early records | EBV confidence high before 35 days | confidence gate | clamp confidence low |
| unsupported dairy-specific precision | use of beef-derived RFI parameters as exact dairy constants | label as approximate for dairy | retain range-based calibration |
| identical candidate scores | exact tie in ranking | tie-break rule must be configured | not clearly specified in provided resources |
| no eligible parents | empty candidate pool | validate herd demography before breeding cycle | skip breeding event and log system warning |
| stale signal state | outdated feed/disease/cull signals | timestamp signals | use last valid state or skip reweighting |

### 11. Direct Coding Guidance

#### 11.1 Module structure

Recommended module:


* `agents/genetics_agent.py`

Recommended class:


* `class GeneticsAgent:`

Recommended internal substructures:


* `ScenarioWeightConfig`
* `TraitVector`
* `CandidateRecord`
* `BreedingCycleResult`

#### 11.2 Core class responsibilities

```python
class GeneticsAgent:
    def __init__(self, config, rng):
        ...
    def ingest_signals(self, feed_cost_signal, disease_frequency_signal, market_scenario, user_breeding_priority, cull_cow_price):
        ...
    def update_candidate_records(self, cow_records):
        ...
    def compute_ebv_confidence(self, cow_id):
        ...
    def build_active_weight_vector(self):
        ...
    def score_candidates(self, candidate_ids):
        ...
    def select_parents(self, ranked_candidates):
        ...
    def generate_offspring_trait_vector(self, dam_traits, sire_traits):
        ...
    def apply_genetic_gain_update(self):
        ...
    def publish_outputs(self):
        ...```

#### 11.3 State-management logic

* keep per-cow inherited traits in a persistent trait registry keyed by `cow_id`
* keep per-cow observation quality separately from trait values
* do not overwrite inherited values with noisy daily observations
* maintain annual trend histories independently from daily herd state

#### 11.4 Update-loop order

##### Daily

1. ingest updated cow intake/performance records
2. increment `recorded_dmi_days`
3. refresh `ebv_confidence`
4. if Feed changed diet class, update effective RFI modifier state

##### Annual breeding cycle

1. ingest latest Farm Manager Agent, Feed / Crop Agent, Disease signals
2. build active weight vector from scenario + signal adjustments
3. validate candidate record quality
4. score candidates
5. select parents
6. generate offspring trait vectors
7. apply breeder’s equation update
8. publish annual outputs to Farm Manager Agent and dashboard

#### 11.5 Scheduling logic

* daily record maintenance
* annual breeding and selection
* immediate reweight only when a signal changes, but actual parent selection still occurs on breeding cadence

#### 11.6 Interaction APIs

Incoming interfaces:


* `FeedAgent.get_feed_cost_signal()`
* `DiseaseAgent.get_disease_frequency_signal()`
* `FarmManager.get_market_scenario()`
* `CowRegistry.get_candidate_performance_records()`

Outgoing interfaces:


* `CowRegistry.assign_trait_vector(calf_id, trait_vector)`
* `FarmManager.receive_breeding_report(report)`
* `Dashboard.receive_genetic_trend(genetic_gain, herd_nm_trend)`
* `EnvironmentAgent.receive_herd_rfi_distribution(summary)` or equivalent trend handoff

#### 11.7 Persistence logic
Persist across simulation years:


* inherited trait vectors
* herd NM$ trend
* herd mean RFI_fat trend
* breeding recommendations history
* scenario-weight history if dashboarding is required

Do not persist as authoritative biological state:


* transient ranking lists
* temporary annual candidate pools
* unvalidated short-window RFI observations

#### 11.8 Stochastic handling
Use RNG only for:


* offspring trait variation around parental mean
* optional uncertainty draw within CH₄ advantage range inferred from provided materials

Do not use RNG for:


* official scenario weight tables
* EBV validity threshold
* direct CH₄ selection

#### 11.9 Extensibility
Safe extension points:


* externalized breed-specific overrides or reduced-trait proxy remaps layered on top of the published USDA `NM$9 (01-25)` tables (revised `Feb 2026`)
* optional RG / RIG scenario variants
* richer pedigree or sire-selection logic
* tighter Cow–Genetics linkage for lactation-stage corrected expected DMI

Unsafe extension points unless new sources are added:


* genomic marker modeling
* direct methane breeding phenotype
* unsupported mutation/recombination models
* unsupported exact fertility or calving hazard equations

---

## Agent 2 — 🐄 Cow Agent

*Tag: Core*

### 1. Agent Purpose

The Cow Agent is the **primary biological unit** of the system.


The original HTML architecture defines it as the agent that models:


* health status,
* lactation stage,
* daily milk yield,
* feed consumption,
* body condition,
* reproduction events,
* mortality,
* manure produced,
* methane emitted,
* feed conversion ratio,
* and health/mortality signaling.

Its responsibilities are to:


* receive inherited trait vectors from the Genetics Agent,
* receive daily ration quality and quantity from the Feed / Crop Agent,
* receive disease-state updates from the Disease Agent,
* receive water availability and environmental conditions,
* convert those inputs into biological outputs each tick,
* and pass those outputs to the Manure Agent, Environment Agent, Farm Manager Agent, and genetics-linked reproduction workflows.

Subsystem ownership:


* individual-animal physiological state,
* production state,
* intake state,
* disease-affected productivity state,
* reproduction state,
* and biological output generation.

Objectives:


* represent realistic per-cow variation,
* transmit feed quality into milk output, manure output, and CH₄ output,
* preserve inherited genetic effects without collapsing them into deterministic herd averages,
* expose daily biological outputs that drive the rest of the ABM.

Optimization goal:


* The Cow Agent does **not** own a farm-level optimizer.
* Its role is state evolution under constraints, not strategic optimization.
* It expresses inherited and environmental efficiency through mechanistically grounded updates.

Dependencies:


* Genetics Agent: trait vector
* Feed / Crop Agent: ration quality/quantity, `me_concentration`, `dietary_cp_pct`, `mp_supply`, grain:fiber structure
* Disease Agent: infection state, quarantine, productivity penalties
* Water Agent: water availability and water-demand feedback context
* Sensors Agent: DMI observations, BCS estimate, rumination/activity state, rumen pH, THI-derived heat stress inputs
* Farm Manager Agent: indirectly through management policy that changes feed and disease context

Constraints:


* direct CH₄ phenotype selection is not clearly specified in provided resources; CH₄ is expressed through intake and diet quality, not owned as a direct inherited optimization target
* daily DMI must be stochastic, not fixed
* dairy RFI interpretation must account for lactation stage and fat mobilization as postpartum-context / diagnostic support rather than as an extra Equation 2-1 coefficient
* for lactating Holstein cows, published NASEM Equation 2-1 is described as the primary expected-DMI predictor using parity, MilkE, BW, BCS, and DIM
* heat-stress and SARA penalties must only be applied where they are described in provided materials
* exact milk-output / lactation-curve equations, and expected-DMI extensions outside the lactating-Holstein use case described in provided materials, are **not clearly specified in the provided resources and the shown form is retained as an implementation assumption so agent interfaces and mass/energy/accounting constraints stay executable**

Expected outputs:


* `daily_milk_yield_l`
* `actual_dmi_kg_dm`
* `manure_kg_day`
* `enteric_ch4`
* `feed_conversion_ratio`
* `reproduction_event_flag`
* `health_mortality_signal`
* optionally `nitrogen_use_efficiency`
* optionally `estrus_state` / `estrus_detected_flag` for downstream breeding logic

Contribution to global system behavior:


* drives milk revenue,
* drives manure inflow to nutrient and energy loops,
* drives enteric CH₄,
* carries disease burden at individual level,
* transmits genetic improvement into observable herd performance,
* creates heterogeneity required for a realistic ABM.

Why this agent exists:


* The HTML architecture appears to position the Cow Agent as the simulation’s primary biological unit.
* Herrero-derived analysis is interpreted here as placing the cow at the point where diet quality links to productivity and CH₄.
* Basarab-derived analysis is interpreted here as linking cow-level `RFI_fat` to actual DMI and therefore CH₄.
* Zhang/Tedeschi-derived analysis is interpreted here as supporting cow-level heat-stress, rumen-pH, rumination, and sensor-informed state estimation logic.

### 2. Agent State Variables

Variables below prioritize what is described in the provided resources; any extensions should be treated as *implementation assumption*.


#### 2.1 Identity and lifecycle variables

| Variable | Meaning | Units | Data type | Valid range | Initialization | Update frequency | Dependencies | Persistence | Class |
|---|---|---|---|---|---|---|---|---|---|
| `cow_id` | unique cow identifier | none | string/int | unique | assigned at herd initialization or birth | never | simulation kernel | persistent | static |
| `age` | cow age | days or ticks | int | `>=0` | initialized from herd setup or calf birth | daily | time progression | persistent | dynamic |
| `lactation_stage` | current lactation status used in intake and yield logic | categorical or day-in-lactation counter | enum/int | exact categories not clearly specified | initialized from herd setup or calving event | daily | reproduction history | persistent | dynamic |
| `days_in_milk` | DIM counter used directly by the supported lactating-Holstein expected-DMI equation | days | int | `>=0`; Equation 2-1 support data covered roughly `1–368` DIM | initialized from last calving event or herd setup | daily | reproduction history | persistent | dynamic |
| `parity` | count of completed calving cycles; map to `0` for primiparous and `1` for multiparous when applying Equation 2-1 | count | int | `>=0` | initialized from herd state | event-driven | calving events | persistent | dynamic |
| `alive_flag` | whether the cow remains active in simulation | boolean | bool | `{true,false}` | true at initialization | event-driven | mortality logic | persistent | dynamic |
| `mortality_flag` | terminal mortality output flag | boolean | bool | `{true,false}` | false at initialization | event-driven | disease and survival outcomes | terminal | dynamic |

#### 2.2 Inherited trait variables

These are injected by the Genetics Agent and persist on the cow.


| Variable | Meaning | Units | Data type | Valid range | Initialization | Update frequency | Dependencies | Persistence | Class |
|---|---|---|---|---|---|---|---|---|---|
| `butterfat_ebv` | inherited butterfat potential | pounds PTA | float | not clearly specified | from Genetics trait vector | at birth only | Genetics Agent | persistent | inherited |
| `protein_ebv` | inherited protein potential | pounds PTA | float | not clearly specified | from Genetics trait vector | at birth only | Genetics Agent | persistent | inherited |
| `rfi_fat_ebv` | inherited residual feed intake adjusted for fatness | official `RFI` is in pounds DMI/lactation; if Cow uses a daily residual form, explicit conversion is required | float | not clearly specified; herd-calibrated | from Genetics trait vector | at birth only | Genetics Agent | persistent | inherited |
| `body_weight_composite` | inherited body maintenance-cost tendency | composite units | float | not clearly specified | from Genetics trait vector | at birth only | Genetics Agent | persistent | inherited |
| `livability_score` | inherited survival tendency | probability-like/index | float | exact scaling not clearly specified | from Genetics trait vector | at birth only | Genetics Agent | persistent | inherited |
| `fertility_score` | inherited fertility tendency | probability-like/index | float | exact scaling not clearly specified | from Genetics trait vector | at birth only | Genetics Agent | persistent | inherited |
| `health_composite_score` | inherited disease resilience | dollars if mapped to `HTH$`; otherwise explicit conversion is required | float | exact scaling not clearly specified | from Genetics trait vector | at birth only | Genetics Agent | persistent | inherited |
| `calving_ease_score` | inherited calving difficulty resistance | dollars if mapped to `CA$`; otherwise explicit conversion is required | float | exact scaling not clearly specified | from Genetics trait vector | at birth only | Genetics Agent | persistent | inherited |

#### 2.3 Intake, production, and body-state variables

| Variable | Meaning | Units | Data type | Valid range | Initialization | Update frequency | Dependencies | Persistence | Class |
|---|---|---|---|---|---|---|---|---|---|
| `expected_dmi_kg_dm` | expected dry matter intake before stochastic and RFI adjustments; for lactating Holsteins this is supported by Equation 2-1 | kg DM/day | float | `>=0` | initialized from baseline physiological state | daily | parity, `days_in_milk`, `body_weight`, `body_condition_score`, `milk_energy_mcal_d` | transient + persisted if needed for diagnostics | dynamic |
| `actual_dmi_kg_dm` | realized intake after RFI expression and stochastic variation | kg DM/day | float | `>=0` | initialize from first valid daily ration | daily | expected DMI, effective RFI, stochastic term, heat stress | persistent daily history | dynamic, stochastic |
| `observed_dmi_kg_dm` | sensor-observed DMI received from Sensors Agent | kg DM/day | float | `>=0` | null until first observation | daily | Sensors Agent | persistent daily history | dynamic |
| `daily_milk_yield_l` | realized milk output | litres/day | float | `>=0` | initialized from herd baseline | daily | feed, genetics, disease, heat stress, SARA | persistent daily history | dynamic |
| `milk_energy_mcal_d` | MilkE input required by the supported Equation 2-1 expected-DMI predictor | Mcal/day | float | `>=0` | initialized from baseline milk state or computed from starting milk output/composition data | daily | milk yield and milk-energy calculation pipeline | persistent daily history | dynamic |
| `milk_volume_trait` | inherited milk-volume tendency if modeled separately from observed milk | pounds PTA if modeled as the official milk trait; otherwise explicit conversion is required from daily milk-volume units | float | not clearly specified | from genetic structure if implemented | persistent | Genetics | persistent | inherited |
| `feed_conversion_ratio` | feed-to-output efficiency indicator | ratio | float | `>=0` | compute after first valid milk and DMI values | daily | DMI, milk yield, digestibility state | persistent daily history | dynamic |
| `body_condition_score` | cow body condition state | BCS score | float | `1–5` when used in Equation 2-1 | initialized from herd baseline or sensor estimate | daily or sensor update | Sensors Agent / internal energy state | persistent | dynamic |
| `body_weight` | live body weight state | kg | float | `>0` | initialized from herd baseline or sensor estimate | daily or sensor update | Sensors Agent / life stage | persistent | dynamic |
| `fat_mobilization_flag` | indicates postpartum reserve-mobilization context retained for dairy RFI interpretation, fallback handling, and early-lactation diagnostics; not an extra published Equation 2-1 coefficient | boolean | bool | `{true,false}` | initialized from lactation state | daily | lactation stage | persistent short-term | dynamic |

#### 2.4 Health, disease, and stress variables

| Variable | Meaning | Units | Data type | Valid range | Initialization | Update frequency | Dependencies | Persistence | Class |
|---|---|---|---|---|---|---|---|---|---|
| `infection_status` | Disease Agent state on cow | enum | enum | supported by HTML: disease/infection state; exact disease-state set may be `SIR` or `SEIR` depending Disease Agent | initialized susceptible/healthy | daily | Disease Agent | persistent | dynamic |
| `quarantine_flag` | whether cow is isolated | boolean | bool | `{true,false}` | false | daily/event | Disease Agent | persistent while active | dynamic |
| `health_status` | broad physiological health state | enum/index | enum/float | not clearly specified | initialized healthy | daily | Disease, rumen pH, heat stress, inherited health composite | persistent | dynamic |
| `vet_cost_event_flag` | whether current tick should emit a vet/treatment cost event | boolean | bool | `{true,false}` | false | event-driven | disease, calving difficulty | transient/event history | dynamic |
| `heat_stress_index` | THI-like environmental stress input affecting production | THI | float | integrated analysis gives threshold bands at 68 and 72 | from Sensors/environment | daily | Sensors Agent / environment | daily history | dynamic |
| `rumen_ph` | rumen acidity state | pH units | float | biological range not fully specified; SARA threshold supported at `=0` | `0` | daily | rumen pH | persistent short-term | dynamic |
| `sara_flag` | subacute ruminal acidosis state | boolean | bool | `{true,false}` | false | daily | rumen pH threshold + duration | persistent while active | dynamic |
| `digestibility_penalty_active` | whether digestibility penalty is currently applied | boolean | bool | `{true,false}` | false | daily | SARA logic | dynamic | dynamic |

#### 2.5 Reproduction and behavior variables

| Variable | Meaning | Units | Data type | Valid range | Initialization | Update frequency | Dependencies | Persistence | Class |
|---|---|---|---|---|---|---|---|---|---|
| `reproduction_event_flag` | HTML-required reproduction output | boolean | bool | `{true,false}` | false | event-driven | estrus, conception, calving outcome | event history | dynamic |
| `estrus_state` | latent biological estrus state | boolean/enum | bool/enum | not clearly specified beyond event occurrence | initialized not-in-estrus | daily | reproductive cycle | persistent | dynamic |
| `estrus_detected_flag` | whether estrus is detected by sensor pipeline | boolean | bool | `{true,false}` | false | event-driven | Sensors fusion rule | event history | dynamic |
| `calving_interval` | days between calvings | days | float | `>0` | initialized from prior history or null | event-driven | conception and calving events | persistent | dynamic |
| `rumination_time_pct_baseline` | rumination relative to cow baseline | proportion | float | `>=0` | initialize at `1.0` baseline | daily | Sensors Agent | persistent daily history | dynamic |
| `activity_multiplier_baseline` | activity relative to normal baseline | ratio | float | `>=0` | initialize at `1.0` | daily | Sensors Agent | persistent daily history | dynamic |

#### 2.6 Nitrogen and environmental-output variables

| Variable | Meaning | Units | Data type | Valid range | Initialization | Update frequency | Dependencies | Persistence | Class |
|---|---|---|---|---|---|---|---|---|---|
| `manure_kg_day` | manure mass output | kg/day | float | `>=0` | initialized after first intake tick | daily | DMI, diet composition | persistent daily history | dynamic |
| `enteric_ch4` | enteric methane output | mass/day or CO₂e/day depending downstream implementation | float | `>=0` | initialize after first intake tick | daily | DMI, ME concentration, RFI expression | persistent daily history | dynamic |
| `ch4_intensity_per_litre` | methane intensity per unit milk | mass/litre | float | `>=0` | computed when both CH₄ and milk are available | daily | CH₄, milk yield, ME concentration | persistent | dynamic |
| `nitrogen_use_efficiency` | milk N / dietary N | ratio | float | theoretical `0–1`; observed range `0.20–0.32`; theoretical ceiling `0.40–0.45` | null until N inputs available | daily/weekly | Feed dietary N, milk N | persistent | dynamic |
| `health_mortality_signal` | consolidated output signal for Farm Manager and Disease handling | categorical/boolean | enum/bool | not clearly specified | initialize normal | daily/event | health, mortality, disease | transient + history | dynamic |

#### 2.7 Environmental / interaction input variables

| Variable | Meaning | Units | Data type | Valid range | Initialization | Update frequency | Dependencies | Persistence | Class |
|---|---|---|---|---|---|---|---|---|---|
| `ration_quality` | quality component of feed ration | structured record | dict | includes ME/CP/etc. where supplied | from Feed / Crop Agent | daily | Feed / Crop Agent | daily history | dynamic |
| `ration_quantity` | quantity component of feed ration | kg DM/day or ration units | float | `>=0` | from Feed / Crop Agent | daily | Feed / Crop Agent | daily history | dynamic |
| `me_concentration` | metabolizable energy concentration of diet | MJ/kg DM | float | supported system ranges: `8.0–9.5`, `9.5–12.5`, `>10.5` by system class | from Feed / Crop Agent | daily | Feed / Crop Agent | daily history | dynamic |
| `dietary_cp_pct` | crude protein concentration | % DM | float | integrated protein-analysis examples `16–18%` standard, `14–15%` optimized | from Feed / Crop Agent | daily | Feed / Crop Agent | daily history | dynamic |
| `mp_supply` | metabolizable protein supply | g/day | float | exact cow-specific bounds not clearly specified | from Feed / Crop Agent | daily | Feed / Crop Agent | daily history | dynamic |
| `water_availability` | water access input from environment/water loop | litres/day or adequacy flag | float/bool | not clearly specified | from Water Agent or environment | daily | Water Agent | daily history | dynamic |

### 3. Agent Behaviors and Actions

#### 3.1 Daily behavior inventory

| Behavior | Trigger conditions | Required inputs | State transitions | Outputs | Cooldown / termination |
|---|---|---|---|---|---|
| `ingest_daily_inputs()` | start of daily tick | ration, genetics state, disease state, water availability, sensor updates | refreshes all incoming states | none directly | ends same tick |
| `compute_expected_dmi()` | after input ingest | `parity`, `days_in_milk`, `body_weight`, `body_condition_score`, `milk_energy_mcal_d` | updates `expected_dmi_kg_dm` using Equation 2-1 for lactating Holsteins | expected intake | daily recomputed |
| `apply_rfi_expression()` | after expected DMI | `rfi_fat_ebv`, cross-diet modifier | adjusts intake tendency | modified intake state | daily |
| `apply_stochastic_dmi_variation()` | after RFI adjustment | expected intake, CV range | updates `actual_dmi_kg_dm` | realized intake | daily |
| `apply_heat_stress_response()` | THI available | `heat_stress_index` | reduces DMI, milk yield, reproductive success as supported | modified DMI/yield/reproduction | ends when THI returns below threshold band |
| `update_rumen_ph()` | feed composition available | grain:fiber, feeding frequency proxy if available, sensor value | updates `rumen_ph` | pH state | daily |
| `evaluate_sara()` | after rumen pH update | `rumen_ph` history | sets `sara_flag` and digestibility penalty after threshold duration | penalty flags | ends after pH recovers and counter resets |
| `update_milk_production()` | after intake/stress/health update | DMI, ME, disease penalties, heat stress, SARA | updates `daily_milk_yield_l` | milk output | daily |
| `update_manure_output()` | after intake and feed composition update | DMI, diet quality, CP context | updates `manure_kg_day` | manure output | daily |
| `update_enteric_ch4()` | after DMI and diet quality update | actual DMI, ME concentration | updates `enteric_ch4` and `ch4_intensity_per_litre` | CH₄ output | daily |
| `update_nue()` | if N data available | dietary N, milk N | updates `nitrogen_use_efficiency` | NUE output | daily/weekly |
| `update_disease_state_effects()` | after Disease signal | infection/quarantine/health penalties | modifies production and mortality risk outputs | `health_mortality_signal` | daily |
| `update_reproduction_state()` | daily cycle with estrus inputs | fertility, estrus state, detection flags, heat stress | updates conception/calving interval/reproduction event flag | reproduction events | event-driven |
| `publish_outputs()` | end of daily tick | full updated state | none | milk, manure, CH₄, FCR, reproduction flag, mortality signal | ends each tick |

#### 3.2 Supported adaptive / emergency behaviors

##### Heat-stress response
Integrated Zhang analysis supports:


* `THI 72`: severe stress, reduce DMI by `10–15%`, milk yield by `10–20%`, increase reproductive failure probability

The added DMI source provides consistent observational support around those bands: acute heat stress at average `THI 72` reduced DMI by `11.5%` versus thermoneutral `THI 57`, extreme cases can exceed `50%` DMI depression, and West et al. reported about `-0.85 kg/d` DMI per degree C increase in mean air temperature over `25–32°C` with a roughly two-day lag.


However, the DMI source does **not** provide a validated universal temperature/humidity modifier to embed inside Equation 2-1, so heat stress should remain an external adjustment layer on top of the expected-intake prediction described in provided materials.


This behavior terminates when THI falls back below the active band.


##### SARA response
Tedeschi-derived analysis supports:


* if `rumen_ph =3` consecutive ticks:
* feed digestibility `−10%`
* milk yield `−5–8%`
* FCR worsens

Termination:


* when rumen pH recovers above threshold and low-pH counter resets

##### Disease-response behavior
Supported by original HTML:


* Disease Agent sets infection status per cow
* infected cows receive milk-yield reduction, quarantine flag, mortality effects
* Cow emits health and mortality signal to Farm Manager Agent

Exact infection-to-mortality hazard equation is not clearly specified in the provided resources and the shown form is an implementation assumption used to keep interfaces and accounting constraints executable.


##### Estrus / reproduction behavior
Supported by Tedeschi-derived analysis:


* rumination drop `10–30%` from baseline can signal estrus
* activity + rumination fusion yields higher detection accuracy than single-sensor mode
* missed detections delay conception and extend calving interval

The Cow Agent owns the latent reproductive state and the realized event flag; detection reliability is supplied by the Sensors Agent.


#### 3.3 Maintenance behaviors

* increment age
* maintain reproductive history
* maintain rumen pH low-tick counter
* maintain daily histories for DMI, milk, CH₄, and manure
* maintain state continuity across ticks

#### 3.4 Failure-state behaviors

* if ration missing: hold or zero production logic must be handled as an implementation assumption; exact fallback is not clearly specified in resources
* if rumen pH sensor absent or degraded: use observed noisy pH if available, else mark SARA detection confidence low
* if water unavailable: input exists in HTML, but exact production penalty is not clearly specified in provided resources

### 4. Decision-Making Logic

The Cow Agent is a **state-transition and physiology-expression agent**, not a farm optimizer. Its “decision-making” is therefore internal prioritization of biological responses.


#### 4.1 Update priority stack

Daily priority order treated as an implementation assumption aligned with provided resources:


1. ingest feed, disease, water, sensor, and inherited trait inputs
2. compute intake state
3. apply environmental stress modifiers
4. apply digestive penalty logic
5. compute production outputs
6. compute emissions and manure outputs
7. update reproduction and health outputs
8. publish outputs

#### 4.2 Internal decision architecture

##### Intake realization
The Cow Agent determines realized intake from (implementation assumption):


* physiological expected DMI,
* inherited efficiency (`rfi_fat_ebv`),
* daily stochastic variation,
* heat-stress penalties,
* possibly diet-switch modifier passed through genetics/feed interaction.

Intake-control framing inferred from provided resources:


* DMI is affected by both physical fill/distension and metabolic control
* the added DMI source discusses the hepatic oxidation theory as a metabolic control mechanism
* these mechanisms motivate the expected-intake and ration-effect layers but do not replace the residual `RFI_fat` structure

For lactating Holstein cows, use the published Equation 2-1 as the primary expected-intake layer:

$$expected\_DMI_{Eq2-1} = \left[3.7 + 5.7 \times Parity + 0.305 \times MilkE + 0.022 \times BW + (-0.689 - 1.87 \times Parity) \times BCS\right] \times \left[1 - (0.212 + 0.136 \times Parity) \times e^{-0.053 \times DIM}\right]$$
**Source:** NASEM dairy DMI equation (Eq. 2-1) from `Dry Matter Intake.pdf`.

**Why used:** Provides the Cow Agent’s expected-intake baseline so inherited RFI and daily noise can be layered consistently into realized DMI.


where `Parity = 0` for primiparous cows and `1` for multiparous cows, `BCS` is scaled `1–5`, `DIM` is days in milk, and `MilkE` is milk net energy in `Mcal/d`.


Support context for Equation 2-1:


* developed from `31,635` weekly observations, `3,143` lactations, `2,791` cows, and `11` U.S. research stations spanning `2007–2016`
* support data covered cows between roughly `1` and `368` DIM with means +/- SD of `24.3 +/- 4.55` kg DMI, `29.9 +/- 6.23` Mcal/d MilkE, `624 +/- 80.2` kg BW, `3.03 +/- 0.459` BCS, `0.021 +/- 1.22` kg/d BW change, and `149 +/- 5.28` cm height
* cross-validation performance: `RMSEP = 2.61` kg, mean bias `0.008` kg, and `CCC = 0.80`
* within Equation 2-1 interpretation, increasing BCS reduces DMI by about `0.70 kg/d` per BCS unit for primiparous cows and `2.6 kg/d` per BCS unit for multiparous cows

Realized-intake form used for implementation (inferred from combined source context):

$$actual\_DMI_t = expected\_DMI_t + effective\_RFI\_fat + \epsilon_t$$
**Source:** combined implementation form synthesized in `project analysis.pdf` from NASEM Eq. 2-1 intake layer plus inherited-RFI residual/noise layering; exact stochastic convention remains an implementation assumption.

**Why used:** Realizes daily DMI from Eq. 2-1, inherited RFI, and noise so Cow can drive CH₄, NUE, and manure mass flows.


With:


* `\epsilon_t ~ N(0, CV × expected_DMI_t)`
* `CV = 0.11–0.22`

If a single default CV is needed, integrated analysis recommended `0.15`.


##### Production realization
Production logic treated as an implementation assumption from architecture context:


* higher `me_concentration` improves milk productivity and lowers CH₄ intensity
* disease reduces productivity
* SARA reduces digestibility and milk yield
* heat stress reduces DMI and milk yield

Exact lactation-curve form is not clearly specified in the provided resources and the shown form is treated as an implementation assumption to keep interfaces and accounting constraints executable.


##### Reproductive logic
Reproductive influences inferred from provided resources:


* higher inherited fertility improves success
* heat stress increases reproductive failure probability
* estrus detection quality affects timing of breeding events
* missed detections extend calving interval

Exact conception-probability equation is not clearly specified in the provided resources and the shown form is retained as an implementation assumption so interfaces and accounting constraints stay executable.


#### 4.3 Conflict resolution
If multiple penalties occur in one tick:


* apply them sequentially in biologically causal order:

1. feed/intake computation
2. heat stress penalty
3. disease penalty
4. SARA penalty
5. output recomputation

The exact interaction rule among simultaneous disease + heat stress + SARA beyond this ordering is not clearly specified in the provided resources and the shown form is an implementation assumption used to keep interfaces and accounting constraints executable.


#### 4.4 Objective/reward systems
A reward function is not clearly specified in the provided resources and the shown form is treated as an implementation assumption to keep interfaces and accounting constraints executable for the Cow Agent.


Unsupported:


* reinforcement learning,
* utility maximization,
* strategic self-optimization.

### 5. Agent Interactions

| Interaction | Direction | Trigger | Exchanged information | Timing / frequency | Impact |
|---|---|---|---|---|---|
| Genetics → Cow | incoming | birth / breeding event | trait vector | event-driven | sets inherited performance, fertility, health, efficiency state |
| Feed / Crop Agent → Cow | incoming | daily ration update | quantity, ME, CP, MP, grain:fiber composition | daily | drives intake, milk, CH₄, rumen pH, manure |
| Disease → Cow | incoming | daily disease update | infection status, quarantine, productivity penalty | daily | alters health, milk, mortality signal |
| Sensors Agent → Cow | incoming | start of daily tick | observed DMI, BCS, BW, rumen pH, rumination/activity, THI | daily | improves state estimation and event detection |
| Water Agent → Cow | incoming | daily water update | water availability | daily | required input from HTML; exact penalty if insufficient not clearly specified |
| Cow → Manure | outgoing | daily output publish | manure kg/day, upstream nutrient context | daily | feeds nutrient and energy loops |
| Cow → Environment | outgoing | daily output publish | enteric CH₄, milk output for intensity calculations | daily | environmental accounting |
| Cow → Farm Manager Agent | outgoing | daily output publish | milk yield, reproduction flag, health/mortality signal | daily | management dashboard and economics |
| Cow → Genetics | outgoing | record collection | performance records, DMI history, survival, fertility outcomes | daily / annual use | future breeding decisions |

#### Synchronization rules

* Cow update must occur **after** Sensors Agent and Feed / Crop Agent inputs are ready
* Cow output must occur **before** Manure and Environment aggregate daily outputs
* Genetics should read Cow records continuously but rank candidates only on annual breeding cadence

#### Shared variables

* `actual_dmi_kg_dm`
* `daily_milk_yield_l`
* `infection_status`
* `reproduction_event_flag`
* `rumen_ph`
* `body_condition_score`
* `nitrogen_use_efficiency`

#### Failure-handling logic

* if sensor-derived states are missing, use last valid value or biologically computed internal estimate if one exists
* if feed composition fields are incomplete, CH₄ and rumen pH precision degrade
* if reproduction detection is uncertain, keep latent estrus separate from detected estrus

### 6. Environmental Integration

#### Environmental inputs

* `heat_stress_index` / THI
* water availability
* feed quality as environmental resource quality proxy
* disease pressure indirectly affected by environment through Disease Agent

#### Environmental outputs

* enteric CH₄
* manure mass
* indirectly nutrient-loading signal through manure
* milk output used in emission-intensity denominators
* if Water Agent active, water-demand implication may be passed indirectly

#### Climate/resource dependencies
Resource effects inferred from provided materials:


* heat stress reduces DMI, milk yield, reproductive performance
* diet quality increases productivity and lowers CH₄ intensity
* high-grain feeding can lower rumen pH and trigger SARA
* dietary CP and MP context affect N efficiency and downstream excretion, though N₂O is accounted for downstream rather than as a clearly specified direct Cow-layer equation in provided resources

#### Temporal effects

* daily physiological updates
* multi-day SARA threshold memory (`>=3` consecutive low-pH ticks)
* lactation-stage dependency on expected DMI
* early-lactation fat mobilization informs postpartum RFI interpretation and diagnostic safeguards

#### Spatial effects
The Cow Agent is farm-local (not clearly specified in the provided resources and remains configurable as an implementation assumption until a direct source is added).

Explicit movement across parcels, barns, or spatial grids is not clearly specified in the provided resources and remains configurable as an implementation assumption until a direct source is added.


#### Resource consumption / production
Consumes:


* feed ration
* water

Produces:


* milk
* manure
* enteric CH₄
* reproduction and health signals

#### Environmental feedback loops

1. Feed quality → Cow productivity → manure / CH₄ → Environment
2. Heat stress → lower intake / milk → changed economics and feeding strategy
3. High-grain feeding → rumen pH decline → SARA → poorer FCR and lower milk

### 7. Genetic / Evolutionary Logic (If Applicable)

This section applies only to **genetic expression**, not breeding decisions.


#### 7.1 Genetic expression owned by Cow Agent
The Cow Agent receives and stores the inherited trait vector and expresses it through daily physiology:


* `rfi_fat_ebv` affects intake tendency
* `fertility_score` affects reproduction outcomes
* `health_composite_score` affects disease resilience
* `livability_score` affects survival tendency
* butterfat/protein EBV affect production composition potential

#### 7.2 Not owned by Cow Agent
The Cow Agent does **not** own:


* parent selection,
* mutation,
* crossover,
* fitness evaluation,
* breeder’s equation updates.

Those belong to the Genetics Agent.


#### 7.3 Inheritance dependency (inferred)
Cow performance is partly inherited and partly environmental:


* inherited trait vector at birth
* environmental expression via feed, disease, heat, rumen pH, water, and sensor-informed state

Exact gene-by-environment interaction functions beyond the RFI cross-diet moderation described in provided materials are not clearly specified in the provided resources and the shown form is retained as an implementation assumption so interfaces and accounting constraints stay executable.


### 8. Equations / Algorithms / Thresholds

#### 8.1 Intake realization

Supported combined form:


$$actual\_DMI_t = expected\_DMI_t + effective\_RFI\_fat + \epsilon_t$$
**Source:** combined implementation form synthesized in `project analysis.pdf` from NASEM Eq. 2-1 intake layer plus inherited-RFI residual/noise layering; exact stochastic convention remains an implementation assumption.

**Why used:** Realizes daily DMI from Eq. 2-1, inherited RFI, and noise so Cow can drive CH₄, NUE, and manure mass flows.


Where:


* for lactating Holsteins, `expected_DMI_t` should follow Equation 2-1 inputs and coefficients (`Parity`, `MilkE`, `BW`, `BCS`, `DIM`)
* `fat_mobilization_flag` remains a postpartum-context safeguard for dairy RFI interpretation, diagnostics, and fallback handling rather than a separate Equation 2-1 coefficient
* `effective_RFI_fat` reflects inherited efficiency under current diet context
* `\epsilon_t ~ N(0, CV × expected_DMI_t)`

Supported values:


* `CV = 0.11–0.22`
* integrated midpoint default if needed: `0.15`

#### 8.2 CH₄ logic

Supported mechanistic relationship:

$$enteric\_CH4_t = k_{diet} \cdot actual\_DMI_t$$
**Source:** directional DMI-to-enteric-CH4 coupling from `project analysis.pdf`; explicit universal scalar form with fixed `k_diet` is an implementation assumption.

**Why used:** Links inherited intake deviation to realized DMI before enteric-CH₄ scaling in the Genetics–Cow–Environment chain.


with:


* `k_diet` decreasing as `me_concentration` increases

Supported integrated approximation from the Herrero analysis:

$$ch4\_per\_litre = base\_ch4 \times \left(\frac{10.5}{me\_concentration}\right)$$
**Source:** approximation proposed in `project analysis.pdf` (Herrero-derived synthesis) using ME-linked CH4-intensity scaling; not a verbatim primary-paper equation.

**Why used:** Scales CH₄ per litre of milk with diet ME so Cow can report milk-normalized intensity alongside DMI-based CH₄.


And:

$$enteric\_CH4_t = daily\_milk\_yield_l \times ch4\_per\_litre$$
**Source:** identity implied by the same `project analysis.pdf` CH4-intensity approximation when milk-linked output reporting is enabled; implementation convention.

**Why used:** Reconciles milk-yield reporting with CH₄-per-litre when the milk-intensity pathway is enabled.


Use notes:


* exact `base_ch4` is not clearly specified in the provided resources and the shown form is an implementation assumption used to keep interfaces and accounting constraints executable
* exact preference between DMI-based vs milk-intensity-based implementation must be chosen consistently across Cow and Environment modules
* both reflect the same directional mechanism inferred from provided materials: higher ME → lower CH₄ intensity

#### 8.3 NUE

Supported definition:

$$NUE = \frac{milk\_N}{dietary\_N}$$
**Source:** nitrogen-use-efficiency definition used in protein/N-efficiency discussion in `project-analysis.pdf`; farm-specific partition factors require external calibration.

**Why used:** Computes cow-level nitrogen-use efficiency for Feed protein policy and downstream urinary-N pressure.


Supported range:


* on-farm baseline: `20–32%`
* theoretical ceiling: `40–45%`

Cow-level NUE should be emitted if dietary N and milk N are available.


#### 8.4 Heat stress thresholds

Integrated paper-analysis output supports:


* `THI  72`: severe stress
* DMI `−10–15%`
* milk yield `−10–20%`
* reproductive failure probability increases

#### 8.5 SARA threshold

SARA threshold behavior inferred from integrated analysis:


* if `rumen_ph =3` consecutive ticks:
* digestibility `−10%`
* milk yield `−5–8%`
* FCR worsens

#### 8.6 Estrus detection-linked state

Supported biological signal:


* rumination reduction `10–30%` below baseline
* sensor-detection accuracy:
* single modality `85%`
* fused activity + rumination `95%`

Cow Agent use:


* maintain latent estrus state
* receive observed detection from the Sensors Agent
* generate reproduction event flag accordingly

#### 8.7 Quantities not clearly specified

* exact lactation equation
* exact manure-mass equation
* exact milk-protein conversion
* exact mortality hazard equation
* exact water insufficiency penalty
* exact body-condition update equation
* exact feeding-frequency contribution to rumen pH

### 9. Data Requirements

#### Required datasets / structures

| Dataset | Required fields | Temporal resolution | Use |
|---|---|---|---|
| `daily_feed_input` | ration quantity, ME, CP, MP, grain:fiber ratio | daily | intake and productivity update |
| `genetic_trait_vector` | RFI_fat, butterfat/protein EBV, fertility, health, livability, calving ease | at birth + persistent | inherited state |
| `daily_disease_state` | infection status, quarantine, productivity penalty | daily | health and milk adjustment |
| `sensor_state_vector` | observed DMI, rumination, activity, BCS, BW, rumen pH, THI | daily | state estimation and event detection |
| `reproduction_history` | calving dates, conception events, parity | event-driven | lactation stage, DIM, parity, and calving interval |
| `milk_output_history` | daily milk yield plus milk fat/protein or computed `MilkE` | daily | economics, FCR, Equation 2-1 input support, genetic records |
| `dmi_history` | actual and observed DMI | daily | Genetics observation window |
| `n_balance_inputs` | dietary N, milk N | daily/weekly | NUE |

#### Calibration requirements
Need real-world or configured calibration for:


* baseline herd body weight and BCS distributions
* lactation-stage mapping
* MilkE calculation pipeline and verified Equation 2-1 implementation for lactating Holsteins
* fallback expected-DMI logic for non-lactating cows, non-Holstein breeds, or cases outside the Equation 2-1 envelope described in provided materials
* milk-output function
* manure-output function
* `base_ch4` or `k_diet`
* reproductive-cycle timing
* disease penalty magnitudes if not already specified in Disease module

#### Internal simulation-only values
Can be simulated internally:


* daily stochastic intake noise
* SARA low-pH counters
* heat-stress penalty application
* reproduction event flags
* daily output histories

#### Missing-data handling

* missing DMI observation: keep internal `actual_dmi_kg_dm`; mark `observed_dmi_kg_dm` missing
* missing rumen pH: disable confident SARA detection unless an internal proxy is modeled as an implementation assumption
* missing THI: do not apply heat-stress penalty
* missing dietary N: NUE not computed
* missing milk data: FCR and CH₄ intensity per litre not computed

### 10. Edge Cases / Failure Conditions

| Issue | Detection mechanism | Prevention logic | Fallback / recovery |
|---|---|---|---|
| negative or impossible DMI | `actual_dmi_kg_dm  0` while prolonged near-zero DMI | consistency check | cap milk or flag biologically invalid state |
| missing water input | no water availability value | require explicit null-handling path | exact production fallback not clearly specified |
| runaway daily variability | repeated extreme DMI draws | bounded stochastic sampling | truncate at biologically valid lower bound |
| dead cow still producing outputs | `alive_flag == false` but update executes | early exit in daily update | no outputs except terminal events |

### 11. Direct Coding Guidance

#### 11.1 Module structure

Recommended module:


* `agents/cow_agent.py`

Recommended class:


* `class CowAgent:`

Recommended internal data groups:


* `IdentityState`
* `TraitState`
* `PhysiologyState`
* `ProductionState`
* `HealthState`
* `ReproductionState`
* `SensorState`
* `DailyOutputState`

#### 11.2 Core class layout

```python
class CowAgent:
    def __init__(self, cow_id, trait_vector, initial_state, rng):
        ...
    def ingest_inputs(self, feed_input, disease_input, water_input, sensor_input):
        ...
    def compute_expected_dmi(self):
        ...
    def compute_actual_dmi(self):
        ...
    def apply_heat_stress(self):
        ...
    def update_rumen_ph(self):
        ...
    def evaluate_sara(self):
        ...
    def update_milk_output(self):
        ...
    def update_manure_output(self):
        ...
    def update_enteric_ch4(self):
        ...
    def update_nue(self):
        ...
    def update_reproduction(self):
        ...
    def publish_outputs(self):
        ...```

#### 11.3 Update-loop order

Recommended daily order:


1. `ingest_inputs()`
2. if `alive_flag == False`: exit early
3. `compute_expected_dmi()`
4. `compute_actual_dmi()`
5. `apply_heat_stress()`
6. `update_rumen_ph()`
7. `evaluate_sara()`
8. `update_milk_output()`
9. `update_manure_output()`
10. `update_enteric_ch4()`
11. `update_nue()`
12. `update_reproduction()`
13. `publish_outputs()`

This ordering preserves a causal chain inferred from provided materials:

feed composition / physiology → intake → stress / digestion penalties → milk → manure / CH₄ → reproduction output.


#### 11.4 State-management logic

* inherited traits are immutable after birth except if overwritten by a genetics event treated as an implementation assumption, which should not happen in normal lifecycle
* daily biological states are mutable and history-tracked
* sensor-observed values must remain separate from internal “true” states where measurement error is modeled
* latent reproductive state should remain separate from detected reproductive event state

#### 11.5 Execution priority
The Cow Agent should run:


* after Sensors Agent and Feed / Crop Agent,
* after Disease state update,
* before Manure and Environment aggregation,
* before Farm Manager Agent daily economics rollup,
* continuously feeding records back to Genetics.

#### 11.6 Interaction APIs

Incoming:


* `FeedAgent.get_ration_for_cow(cow_id)`
* `DiseaseAgent.get_cow_health_state(cow_id)`
* `SensorsAgent.get_cow_sensor_packet(cow_id)`
* `WaterAgent.get_water_status(cow_id)`

Outgoing:


* `ManureAgent.receive_cow_outputs(cow_id, manure_kg_day, nitrogen_context)`
* `EnvironmentAgent.receive_cow_emissions(cow_id, enteric_ch4, milk_output)`
* `FarmManager.receive_cow_outputs(cow_id, milk_yield, reproduction_event_flag, health_mortality_signal)`
* `GeneticsAgent.receive_cow_record(cow_id, performance_record)`

#### 11.7 Persistence logic
Persist:


* inherited trait vector
* daily output history
* disease history
* reproduction history
* DMI history
* rumen pH history / low-pH counter
* NUE history if computed

Transient per tick:


* current penalties
* latest input packet
* event flags that are emitted and reset

#### 11.8 Stochastic handling
Use RNG only where inferred from provided materials:


* daily DMI stochastic variation (`CV 0.11–0.22`)
* optional observation-noise separation between actual and observed DMI if handled partly inside Cow

Do not add unsupported random mortality, random milk shocks, or random disease logic here unless owned by Disease Agent or another sourced module.


#### 11.9 Extensibility
Safe future extensions:


* explicit lactation-curve parameterization once sourced
* explicit milk fat/protein outputs if downstream processor requires them
* richer reproductive state machine
* more detailed water-demand coupling

Unsafe without new sources:


* full digestion submodel
* unsupported water-penalty thresholds
* unsupported body-condition energy-balance equations
* unsupported movement/grazing spatial logic

#### 11.10 Integration mapping for existing CVDS Cow base
If the project uses the existing CVDS-based cow code as the implementation base, keep the internal equations and add an adapter layer that maps CVDS fields to the ABM contract.


Field mapping (CVDS base -> ABM contract):

| CVDS field / variable | ABM field | Role | Notes |
|---|---|---|---|
| `AnimalID` | `cow_id` | identity input | stable unique key |
| `PenID` | `pen_id` | context input | used for Feed/Crop ration lookup |
| `Sex` | `sex` / parity context | identity input | normalize to enum at adapter boundary |
| `Age` or `AgeHipHeight*30` | `age_days` | state input | keep one canonical age field in published packet |
| `HipHeight` | `hip_height` | state input | used by frame-score logic |
| `BCS` | `body_condition_score` | state input/output | keep existing scale and validate range on ingest |
| `iBW`, `IsiBWShrunk` | `full_body_weight`, `sbw` | initialization input | retain existing SBW conversion behavior |
| `Implants`, `Holstein` | `using_implants`, `holstein_breeding` | policy/breed modifiers | retain as boolean modifiers |
| `NEm_diet`, `NEg_diet` (pen properties) | `diet_nem_mcal_kg`, `diet_neg_mcal_kg` | Feed->Cow input packet | publish as explicit daily ration-energy fields |
| `Shrunk_Body_Weight` | `sbw` | primary cow state | main growth state variable |
| `Equivalent_Shrunk_Body_Weight` | `eq_sbw` | internal physiology state | keep internal; optionally publish for diagnostics |
| `dmi` | `actual_dmi_kg_dm` | core Cow output | required downstream by Feed, Environment, Manure |
| `NEm_req`, `Feed_Required` | `nem_requirement`, `feed_required_kg_dm` | diagnostic output | useful for feed adequacy/debug traces |
| `Retained_Energy` | `retained_energy_mcal_d` | growth-energy output | supports performance explainability |
| `Shrunken_Weight_Gain` | `swg_day` | daily growth output | used by Farm Manager trend summaries |
| `Empty_Body_Fat` (`EBF`) | `ebf_pct` | body-composition output | support market readiness and condition tracking |
| `Carcass_Weight`, `Carcass_Weight_Gain` | `carcass_weight`, `carcass_weight_gain` | market/processor bridge outputs | optional for scenarios that include carcass economics |

Minimum adapter packet contracts:

```python
# Feed / Crop -> Cow
{
  "cow_id": int,
  "date": "YYYY-MM-DD",
  "diet_nem_mcal_kg": float,
  "diet_neg_mcal_kg": float
}

# Cow -> Environment
{
  "cow_id": int,
  "date": "YYYY-MM-DD",
  "actual_dmi_kg_dm": float,
  "enteric_ch4_g_day": float,
  "ebf_pct": float
}

# Cow -> Manure
{
  "cow_id": int,
  "date": "YYYY-MM-DD",
  "actual_dmi_kg_dm": float,
  "manure_kg_day": float
}```

Derived-output guidance for project integration:


* derive `enteric_ch4` from the Cow engine DMI via the active emissions function used in the project scenario configuration
* derive `manure_kg_day` from DMI/body-weight context using configurable coefficients
* publish both raw CVDS states and mapped ABM fields so downstream agents can remain stable while formulas evolve

Unit-handling rule:


* if CVDS internals stay in legacy units, convert units at the adapter boundary and publish one canonical unit system to all other agents to prevent cross-agent drift

---

## Agent 3 — 🌾 Feed / Crop Agent

*Tag: Resource*

### 1. Agent Purpose

The Feed / Crop Agent owns the **nutritional supply loop** and the **on-farm crop/feed production loop**.


The original HTML architecture defines it as the agent that:


* tracks crop growth on farm land,
* manages feed supply,
* receives digestate/compost back into soil,
* sends daily feed rations to the Cow Agent,
* outputs synthetic fertilizer requirement,
* tracks feed cost,
* tracks crop yield,
* and supports amino acid balancing.

Its responsibilities are to:


* convert land, season, soil fertility, and recycling inputs into crop/feed availability,
* build per-cow or herd feeding plans,
* control the main upstream variables that drive milk productivity, CH₄ intensity, manure N, urinary N, and N₂O,
* compute feed sourcing priority,
* expose feed costs and nutrition quality to Farm Manager Agent and Genetics,
* and support the E5 amino-acid-balancing experiment with mechanistically grounded state changes.

Subsystem ownership:


* crop/feed production,
* ration composition,
* feed-quality state,
* precision nutrition control,
* protein optimization control,
* feed sourcing hierarchy,
* and part of nutrient circularity through soil fertility response.

Optimization goals:


* provide biologically adequate ration supply,
* minimize feed cost subject to nutritional adequacy,
* minimize urinary N / downstream N₂O burden,
* reduce GHG intensity through diet quality,
* improve local feed autonomy,
* and maintain Cow productivity under seasonal and heat-stress conditions.

Primary objectives described in provided resources:


1. manage `me_concentration` as the master upstream diet-quality variable,
2. manage `dietary_cp_pct` and `mp_supply` for protein efficiency,
3. shift from herd-average static feeding toward per-cow PAN-style feeding,
4. implement amino-acid balancing as a multi-output policy,
5. apply crop-soil feedbacks from digestate/compost,
6. apply feed sourcing priority: `own-farm → local → market import`,
7. apply catch-crop logic to N leaching reduction,
8. emit feed-cost pressure to Genetics and cost streams to Farm Manager Agent.

Dependencies:


* Manure Agent: digestate, compost, soil organic carbon / nutrient return
* Cow Agent: lactation stage, BCS, health state, actual intake, NUE-linked outputs
* Sensors Agent: feed nutrient profile, real-time feed intake, seasonal/environmental measurement context
* Farm Manager Agent: policy weights, protein-optimization toggle, economic/environmental priority
* Environment Agent: downstream consumer of N₂O, GHG intensity, fertilizer displacement effects
* Water Agent: irrigation feedback and water-demand effects under low-CP/RP-AA diets
* Market Agent: feed-price context for static or dynamic pricing mode

Constraints:


* exact crop-growth equations are not clearly specified in the provided resources
* exact nutrient requirement equations per cow are not clearly specified
* exact ML model structure for HIMM or MP prediction is not clearly specified
* exact transport-radius FAN exchange system is explicitly **out of scope**
* exact local-exchange pricing structure is not clearly specified
* exact synthetic fertilizer substitution coefficients are not clearly specified

Expected outputs:


* per-cow or herd `daily_feed_ration`
* `feed_cost_day`
* `crop_yield_t_ha`
* `synthetic_fertiliser_requirement`
* `feed_cost_signal`
* `nitrogen_excretion_reduced_flag`
* `local_feed_autonomy`
* nutrient-quality variables for Cow and Environment modules

Contribution to global system behavior:


* sets the main causal driver for Cow productivity and CH₄ intensity,
* sets the main causal driver for urinary N and downstream N₂O,
* governs on-farm feed autonomy and part of circularity,
* controls part of E4 and E5 economic outcomes,
* and transmits economic stress to Genetics through feed-cost signaling.

Why this agent exists:


* the HTML architecture clearly presents it as essential,
* Herrero-derived analysis identifies diet quality as the dominant upstream driver for milk, CH₄, and manure N,
* the protein-nutrition analysis identifies protein formulation as the main upstream lever for N₂O,
* Zhang-derived analysis identifies individual-level dynamic feeding and multi-objective formulation as the core PAN mechanism,
* the approved plan restricts FAN use to five calibration/mechanism insertions, two of which belong here by implementation assumption: catch crops and sourcing hierarchy.
* FAO LEAP positions feed formulation as the main lever for food–feed competition and NUE: most human-edible biomass entering livestock systems does not return as human food, so plant and processing co-products should be prioritized over grains where biologically adequate **(Source:** FAO, 2025, Ch. 1 §1.2; Ch. 3 §3.1**)**.

### 2. Agent State Variables

Only variables described in provided resources or clearly included in the approved plan are included.


#### 2.1 Structural and spatial variables

| Variable | Meaning | Units | Type | Valid range | Initialization | Update frequency | Dependencies | Persistence | Class |
|---|---|---|---|---|---|---|---|---|---|
| `land_area_ha` | farm land available for crop/feed production | ha | float | `>0` | user initialization | static or scenario-level | user input | persistent | static |
| `production_system_type` | production context used to initialize feed-quality baseline | enum | enum | supported classes from integrated Herrero summary: arid grazing, humid/temperate mixed, high-intensity developed | simulation setup | rarely changed | user/scenario | persistent | static |
| `season_tick` | seasonal progression affecting crop/feed quality | tick/season enum | int/enum | not clearly specified | initialized from calendar | weekly/daily depending sim design | time | persistent | dynamic |
| `weather_tick` | weather/season input used in HTML crop logic | structured input | dict/enum | not clearly specified | from environment setup | daily/weekly | environment | persistent history | dynamic |
| `catch_crop_active` | whether catch crop mitigation is active | bool | bool | `{true,false}` | false unless policy/scenario activates it | seasonal/policy | Farm Manager policy | persistent | dynamic |

#### 2.2 Crop and soil variables

| Variable | Meaning | Units | Type | Valid range | Initialization | Update frequency | Dependencies | Persistence | Class |
|---|---|---|---|---|---|---|---|---|---|
| `soil_fertility_score` | aggregate soil fertility state used by original HTML | score/index | float | not clearly specified | initialized from baseline soil state | weekly | digestate/compost, crop use | persistent | dynamic |
| `soil_organic_carbon_delta` | change in soil carbon due to amendments | delta score or mass-equivalent | float | not clearly specified | 0 at start | weekly/seasonal | Manure Agent returns | persistent history | dynamic |
| `crop_yield_t_ha` | crop production output | tonnes/ha | float | `>=0` | initialized from baseline production scenario | seasonal/weekly | soil fertility, land area, weather/season | persistent history | dynamic |
| `digestate_applied` | digestate quantity applied to land | quantity units not clearly specified | float | `>=0` | 0 | weekly | Manure Agent | transient + history | dynamic |
| `compost_applied` | compost quantity applied to land | quantity units not clearly specified | float | `>=0` | 0 | weekly | Manure Agent | transient + history | dynamic |
| `synthetic_fertiliser_requirement` | remaining fertilizer need after recycled nutrient inputs | kg or equivalent nutrient demand | float | `>=0` | baseline demand at initialization | weekly/seasonal | crop demand, digestate/compost returns | persistent history | dynamic |
| `n_leaching` | nitrogen lost from crop/soil side | mass/time | float | `>=0` | baseline from scenario | weekly/seasonal | soil N state, catch crop flag | persistent history | dynamic |

#### 2.3 Feed inventory and sourcing variables

| Variable | Meaning | Units | Type | Valid range | Initialization | Update frequency | Dependencies | Persistence | Class |
|---|---|---|---|---|---|---|---|---|---|
| `on_farm_feed_available` | feed available from own farm production | kg DM or feed units | float | `>=0` | computed from crop yield | weekly/daily allocation | crop yield, reserves | persistent history | dynamic |
| `local_feed_available` | feed available from local off-farm source in single-farm abstraction | kg DM or feed units | float | `>=0` | scenario input if local sourcing exists | daily/weekly | local procurement setting | persistent history | dynamic |
| `market_import_feed_available` | feed available via market import | kg DM or feed units | float | `>=0` | assumed available unless supply-constrained scenario | daily/weekly | market/import setting | persistent history | dynamic |
| `feed_sourcing_state` | active sourcing tier | enum | enum | `{own_farm, local, market_import}` | initialize by availability priority | daily/weekly | feed availability levels | persistent | dynamic |
| `local_feed_autonomy` | fraction of demand met before market import | ratio | float | `0–1` | initialize from first demand/supply evaluation | daily/weekly | own-farm + local supply vs demand | persistent history | dynamic |
| `feed_inventory_reserve` | stored feed carried across ticks | kg DM or feed units | float | `>=0` | initialized from scenario | daily/weekly | previous production and use | persistent | dynamic |
| `feed_cost_day` | total daily feed cost | currency/day | float | `>=0` | compute after first ration allocation | daily | sourcing state, ration composition, supplement usage | persistent history | dynamic |
| `feed_cost_signal` | compressed signal to Genetics | enum/float | exact categories not specified | derived from feed cost context | weekly/annual | feed cost history | transient + history | dynamic |  |

#### 2.4 Ration-composition variables

| Variable | Meaning | Units | Type | Valid range | Initialization | Update frequency | Dependencies | Persistence | Class |
|---|---|---|---|---|---|---|---|---|---|
| `daily_feed_ration` | ration sent to Cow Agent | structured record | dict | per-cow or herd ration object | baseline ration at start | daily | all feed-quality and requirement logic | transient + history | dynamic |
| `ration_quantity` | offered ration quantity | kg DM/day | float | `>=0` | initial baseline | daily | cow requirements, inventory | transient + history | dynamic |
| `feed_nutrient_profile` | nutrient composition from NIR or internal estimate, including ME, CP, `fNDF`, `ADF/NDF`, `fNDFD`, and other fiber/starch predictors needed for Equation 2-2 when used | structured record | dict | includes ME/CP plus explicit ration-effect fiber inputs when Equation 2-2 is active | initialized from baseline feed | daily/weekly | Sensors or internal seasonal estimate | persistent history | dynamic |
| `me_concentration` | metabolizable energy concentration | MJ/kg DM | float | supported ranges: `8.0–9.5` arid grazing; `9.5–12.5` humid/temperate mixed; `>10.5` high-intensity systems | initialize from `production_system_type` | daily/weekly | feed composition, season | persistent history | dynamic |
| `dietary_cp_pct` | crude protein concentration of ration | % DM | float | supported examples: `16–18%` standard, `14–15%` optimized | initialize from baseline diet | daily | protein policy and ration formulation | persistent history | dynamic |
| `mp_supply` | metabolizable protein supplied | g/day | float | `>=0`; exact cow-specific limits not clearly specified | initialized from baseline nutrition model | daily | ration composition | persistent history | dynamic |
| `grain_fraction` | proportion of ration from grain/concentrates | ratio | float | `0–1` | initialized from baseline diet | daily | ration formulation | persistent history | dynamic |
| `fibrous_fraction` | proportion of ration from grass/silage/fibrous feeds | ratio | float | `0–1` | initialized from baseline diet | daily | ration formulation | persistent history | dynamic |
| `grain_vs_fibrous_feed_ratio` | compact diet-structure variable from integrated Herrero/protein analysis | ratio | float | `>=0` | computed from fractions | daily | ration formulation | persistent history | dynamic |
| `energy_protein_synchrony` | synchronization of fermentable energy and degradable protein | binary/graded | bool/float | supported as high/low or graded modifier; exact continuous bounds not specified | initialize neutral | daily | grain:fiber structure, protein formulation | persistent history | dynamic |
| `amino_acid_balancing` | E5 / protein optimization switch | bool | bool | `{true,false}` | false by default unless experiment or policy active | daily/policy | Farm Manager | persistent | dynamic |
| `rp_lys_flag` | rumen-protected lysine supplementation active | bool | bool | `{true,false}` | false | daily | amino acid balancing policy | persistent | dynamic |
| `rp_met_flag` | rumen-protected methionine supplementation active | bool | bool | `{true,false}` | false | daily | amino acid balancing policy | persistent | dynamic |

#### 2.5 Nitrogen and precision-feeding variables

| Variable | Meaning | Units | Type | Valid range | Initialization | Update frequency | Dependencies | Persistence | Class |
|---|---|---|---|---|---|---|---|---|---|
| `nitrogen_excretion_reduced_flag` | HTML-required flag indicating lower N loss state | bool | bool | `{true,false}` | false | daily | protein optimization logic | transient + history | dynamic |
| `excess_n` | N supplied above MP requirement proxy | mass/day or equivalent formula output | float | can be negative or zero before clamping; practical emission use should clamp at `>=0` | initialize null | daily | `dietary_cp_pct`, `mp_requirement_pct`, DMI | transient + history | dynamic |
| `urinary_n_pressure_signal` | upstream signal for downstream urinary N formation | mass/day or index | float | `>=0` | null until first computation | daily | excess N, synchrony | transient + history | dynamic |
| `nue_support_signal` | feed-side contribution to Cow NUE state | structured | dict/float | not directly bounded | initialize null | daily | CP, MP, AA balancing, synchrony | transient | dynamic |
| `mp_requirement_pct` | MP requirement proxy used in excess-N calculation | % or equivalent normalized target | float | exact ranges not specified | from nutritional requirement model | daily | cow nutritional status vector | transient | dynamic |

#### 2.6 Precision-feeding control variables

| Variable | Meaning | Units | Type | Valid range | Initialization | Update frequency | Dependencies | Persistence | Class |
|---|---|---|---|---|---|---|---|---|---|
| `cow_nutritional_status_vector` | per-cow PAN input assembled from the Cow Agent and Sensors Agent | structured record | dict | contains lactation stage, BCS, health status, activity, intake state | empty at init | daily | Cow + Sensors Agent | transient | dynamic |
| `individual_ration_mode` | whether per-cow tailored rationing is active | bool | bool | `{true,false}` | false unless PAN mode active | daily/policy | Farm Manager Agent or architecture mode | persistent | dynamic |
| `multi_objective_policy_weights` | policy weights for ration optimization | dict | dict[str,float] | should normalize; exact values not specified | initialize from Farm Manager Agent priorities | daily/weekly | Farm Manager Agent | persistent | dynamic |
| `ghg_intensity_target` | internal target signal for GHG-aware feeding | kg CO₂eq/litre milk | float | not clearly specified numerically | null unless policy active | daily/weekly | Farm Manager Agent / Environment feedback | transient | dynamic |

#### 2.7 Variables not described as explicit Feed / Crop Agent state

Do not add unless new sources are provided:


* full crop-growth differential equations,
* exact NIR predictor coefficients,
* exact GA/PSO hyperparameters,
* transport-radius network matching variables from FAN,
* district-level circularity score,
* oscillating CP schedule optimization,
* exact supplement prices for RP-AA.

### 3. Agent Behaviors and Actions

#### 3.1 Core behaviors

| Behavior | Trigger conditions | Required inputs | State transitions | Action outputs | Cooldown / termination |
|---|---|---|---|---|---|
| `initialize_feed_quality_baseline()` | simulation start | `production_system_type` | loads baseline ME band and feed-quality context | initial `me_concentration`, feed-quality state | one-time unless scenario reset |
| `update_crop_soil_state()` | weekly/seasonal tick | soil fertility, digestate, compost, weather, land area | updates crop yield and fertilizer requirement | `crop_yield_t_ha`, `synthetic_fertiliser_requirement`, on-farm feed availability | seasonal / weekly |
| `build_feed_inventory()` | after crop update or supply refresh | crop yield, reserves, local/market availability | updates available feed pools | inventory states | daily/weekly |
| `apply_sourcing_hierarchy()` | when feed demand must be met | own-farm, local, market availability | sets sourcing tier in priority order | `feed_sourcing_state`, `local_feed_autonomy`, cost basis | recomputed whenever demand/supply changes |
| `assemble_cow_status_vector()` | start of feeding decision | Cow state + Sensors state | creates per-cow nutritional input bundle | `cow_nutritional_status_vector` | daily |
| `formulate_daily_ration()` | daily | nutrient status vector, inventory, policy weights | updates ration composition and quantity | `daily_feed_ration` | daily |
| `apply_amino_acid_balancing()` | if protein optimization or E5 active | CP baseline, MP context, RP-AA flags | lowers CP, enables RP supplements, updates N-pressure signals | reduced CP, updated MP, `nitrogen_excretion_reduced_flag` | remains active while policy true |
| `update_energy_protein_synchrony()` | after ration composition | grain:fiber and protein structure | updates synchrony modifier | `energy_protein_synchrony` | daily |
| `compute_feed_cost()` | after sourcing and formulation | ration composition, sourcing state, supplement use | updates cost variables | `feed_cost_day`, `feed_cost_signal` | daily |
| `publish_ration_to_cow()` | end of daily formulation | ration state | none | `daily_feed_ration` to Cow | daily |
| `publish_environmental_precursors()` | after formulation | CP/MP/excess N states, catch crop status, fertilizer demand | none | N-leaching, excess N, fertilizer requirement, nutrient-loss signals | daily/weekly |
| `emit_management_signals()` | after daily/weekly rollup | cost and feed-autonomy state | none | feed cost signal to Genetics, cost and autonomy to Farm Manager | weekly/daily |

#### 3.2 Supported adaptive behaviors

##### Per-cow PAN ration adjustment
Described in Zhang-derived analysis:


* each tick, Feed reads Cow/Sensors state vector
* ration can differ by cow on the same tick
* variables mentioned as drivers in provided resources:
* lactation stage
* BCS
* health status
* activity level
* RFI_fat_EBV through Cow state or integrated logic

This is the core precision-feeding behavior described in provided resources (source: Zhang-derived analysis).


##### Amino acid balancing
Supported simultaneous effects:


* reduce `dietary_cp_pct` by `1.5–2.5` percentage points
* activate `rp_lys_flag`
* activate `rp_met_flag`
* reduce urinary N by `10–20%`
* maintain milk yield
* reduce water demand by `~21 L/cow/day`
* improve NUE by `+5–6` percentage points
* may improve or maintain IOFC depending on RP-AA pricing

Exact cost equation is not clearly specified.


##### Catch crop mitigation
Approved FAN integration supports:


* if `catch_crop_active = true`
* multiply N leaching by `0.5`

No new agent or loop is required (source: approved FAN integration plan).


##### Seasonal feed-quality adaptation
Heat-stress compensation response treated as an implementation assumption:


* `me_concentration` should not remain fixed for all time
* NIR-derived feed-quality variation can change seasonally
* higher summer forage quality / lower winter silage quality is mentioned in integrated analysis as a realism improvement

Exact seasonal function is not clearly specified.


#### 3.3 Emergency / failure behaviors

##### Feed shortage handling
Supported sourcing order:


1. own-farm feed
2. local sourcing
3. market import

If none are sufficient, the exact ration-shortfall fallback rule is not clearly specified in the provided resources and the shown form is treated as an implementation assumption to keep agent interfaces and mass/energy/accounting constraints executable.


##### Heat-stress compensation support
Supported:


* when heat stress is detected, the Feed / Crop Agent should respond by increasing energy density and electrolyte supplementation as compensatory PAN response

Exact electrolyte dose or energy-density increment is not clearly specified in the provided resources and the shown form is retained as an implementation assumption so agent interfaces and mass/energy/accounting constraints stay executable.


#### 3.4 Maintenance behaviors

* maintain feed inventory,
* roll forward seasonal crop state,
* maintain cost history,
* maintain autonomy ratio history,
* maintain CP/MP/N synchrony histories,
* maintain current sourcing tier.

### 4. Decision-Making Logic

#### 4.1 Decision architecture

The Feed / Crop Agent uses a **hierarchical multi-objective decision process** (implementation assumption).


##### Layer 1 — satisfy nutritional adequacy
Supported objective:


* avoid deviation from individual nutrient requirements

##### Layer 2 — minimize cost and environmental burden jointly
Supported objectives from Zhang:


1. minimize feed cost
2. minimize nitrogen excretion / urinary N pressure
3. minimize GHG intensity
4. minimize deviation from individual nutrient requirements

##### Layer 3 — maximize on-farm/local sourcing before market import
Supported by approved FAN integration:


* priority rule, not market-matching network logic

#### 4.2 Multi-objective formulation logic

Supported structure:


* replace cost-only LP-equivalent logic
* use a multi-objective optimizer or weighted-sum approximation
* final operating point selected by Farm Manager policy weights

Supported objective set:


* `feed_cost_day`
* `urinary_n_pressure_signal`
* `ghg_intensity_target` / predicted GHG burden
* nutrient adequacy deviation

Exact optimizer, objective scaling, and convergence logic are not clearly specified in the provided resources and the shown form is an implementation assumption used to keep agent interfaces and mass/energy/accounting constraints executable.


#### 4.3 Supported decision rules

##### Sourcing hierarchy
Supported hard ordering:


1. `own_farm`
2. `local`
3. `market_import`

This is a priority rule, not a scored multi-farm exchange broker.


##### Protein optimization logic
Supported rule:


* if `amino_acid_balancing = true`
* decrease CP by `1.5–2.5` percentage points
* maintain milk yield
* reduce urinary N by `10–20%`
* improve NUE
* reduce water demand

##### Synchrony logic
Supported rule:


* if rumen degradable energy and protein are synchronized, NUE improves
* if imbalanced, NH₃ waste rises and urinary-N pressure rises

Exact synchrony formula is not clearly specified.


#### 4.4 Supported equations / algorithmic forms

##### Excess N
Integrated protein-analysis output gives:


$$excess\_N = (dietary\_cp\_pct - mp\_requirement\_pct) \times DMI$$
**Source:** `Dry Matter Intake.pdf` CP/MP framing plus project-analysis nitrogen-routing context; exact coefficient/form not provided in sources.

**Why used:** Quantifies CP above MP needs to drive urinary-N and field-N₂O precursors in Feed–Manure–Environment routing.


Use:


* upstream driver for urinary-N formation
* should be clamped at zero for downstream excretion logic if negative

##### Feed-quality influence
Supported directional rule:


* higher `me_concentration` improves production and lowers CH₄ intensity
* higher grain fraction raises ME but can increase acidosis risk and feed cost trade-offs

##### Ration-effect DMI evaluator
Once diet composition is known, the added DMI source supports using Equation 2-2 to evaluate ration effects on DMI for lactating Holstein cows:


$$DMI_{Eq2-2} = 12.0 - 0.107 \times fNDF + 8.17 \times \frac{ADF}{NDF} + 0.0253 \times fNDFD - 0.328 \times \left(\frac{ADF}{NDF} - 0.602\right) \times (fNDFD - 48.3) + 0.225 \times MY + 0.00390 \times (fNDFD - 48.3) \times (MY - 33.1)$$
**Source:** NASEM ration-effect DMI equation (Eq. 2-2) from `Dry Matter Intake.pdf`.

**Why used:** Evaluates ration-composition effects on DMI so Feed / Crop recommendations remain consistent with Cow-side intake dynamics.


Required inputs:


* `fNDF`: forage NDF as percent of diet DM
* `ADF/NDF`: ADF as a fraction of diet NDF
* `fNDFD`: forage NDF digestibility (%)
* `MY`: milk yield (kg/d)

Interface rule: if the Cow Agent publishes milk as `daily_milk_yield_l`, the Feed / Crop Agent must convert that output into Equation-2-2-compatible `MY` in `kg/d` using one consistent implementation-wide convention before invoking the ration-effect DMI evaluator; the cited sources do not provide a milk-density constant to hard-code here.


Use limits:


* limit to cows past `60` days postpartum / DIM
* support data were from Holstein cows only
* Equation 2-1 in the Cow Agent remains the primary expected-DMI predictor; Equation 2-2 is for evaluating ration effects once diet proportions are known
* do not use for large `NFFS` changes
* ground, pelleted, or very finely chopped forages should not be treated as forage for this equation
* for multiple forages, use a weighted-average `fNDFD`; if unavailable, the source allows fallback to dataset mean `52.0%`

##### Forage fill and digestibility rules
Supported directional rules from the added DMI source:


* for ration filling effects, `forage NDF` is more important than total NDF
* `NFFS` generally have much less filling effect than forage NDF
* within forage type, a one-unit increase in forage NDF digestibility corresponds to about `+0.17 kg/d` DMI and `+0.25 kg/d` fat-corrected milk

##### Unsaturated-fat intake penalty
Additional supported ration-effect note:


* unsaturated-fat additions depressed DMI by about `0.41 kg` per `1%` added fat

##### Local autonomy
Supported metric logic:

$$local\_feed\_autonomy = \frac{own\_farm\_feed + local\_feed}{total\_feed\_demand}$$
**Source:** hierarchical sourcing policy (own-farm → local → market) from FAN integration notes in `project-analysis.pdf`; exact KPI normal form is an implementation assumption.

**Why used:** Tracks own-farm plus local feed share against demand for Farm Manager autonomy KPIs and sourcing policy checks.

bounded to `0–1`


Exact formula text is not given verbatim, but this is directly derivable from the approved sourcing rule and autonomy metric.


#### 4.5 Unsupported decision logic
Do not implement without new sources:


* full district exchange optimization,
* exact transport-distance scoring,
* exact GA/PSO parameterization,
* oscillating protein strategy,
* exact crop-growth optimizer.

### 5. Agent Interactions

| Interaction | Direction | Trigger | Exchanged information | Timing / frequency | Impact |
|---|---|---|---|---|---|
| Manure → Feed / Crop Agent | incoming | weekly recycling | digestate, compost, soil nutrient return | weekly | raises soil fertility, reduces fertilizer need |
| Cow → Feed / Crop Agent | incoming | daily | lactation stage, `days_in_milk`, BCS, health status, `daily_milk_yield_l` plus a consistently converted Equation-2-2-compatible `MY` (`kg/d`) view for ration-effect DMI evaluation, DMI/NUE-linked state | daily | drives per-cow rationing and ration-effect DMI evaluation |
| Sensors Agent → Feed / Crop Agent | incoming | daily | NIR nutrient profile, observed intake, environmental state | daily | enables PAN and dynamic feed quality |
| Farm Manager Agent → Feed / Crop Agent | incoming | policy/event | economic vs environmental priority, protein optimization toggle | daily/weekly | changes objective weighting |
| Market Agent → Feed / Crop Agent | incoming | daily/weekly | import feed price | daily/weekly | changes feed-cost calculation |
| Feed / Crop Agent → Cow | outgoing | daily | daily ration, ME, CP, MP, grain:fiber composition | daily | drives production, CH₄, rumen pH, manure |
| Feed / Crop Agent → Genetics | outgoing | weekly/annual | feed cost signal | weekly/annual | reweights RFI/BWC emphasis |
| Feed / Crop Agent → Environment | outgoing | daily/weekly | fertilizer requirement, N leaching, excess-N pressure | daily/weekly | downstream GHG and sustainability accounting |
| Feed / Crop Agent → Farm Manager Agent | outgoing | daily/weekly | feed cost, local autonomy, protein status, optimization context | daily/weekly | management decisions |
| Feed / Crop Agent → Water Agent | outgoing indirect | daily | amino acid balancing / low-CP diet state | daily | reduced water demand under RP-AA/low CP |
| Feed / Crop Agent → Manure | outgoing indirect | daily | diet CP and digestibility context | daily | affects fecal vs urinary N split downstream |

#### Synchronization rules

* Feed / Crop Agent must run after Sensors Agent and before Cow daily state update
* weekly crop-soil update should occur after manure-return events
* cost and sourcing state should be available before Farm Manager Agent daily or weekly economic rollup
* feed-cost signal should be aggregated before Genetics annual ranking

#### Shared variables

* `me_concentration`
* `dietary_cp_pct`
* `mp_supply`
* `grain_fraction`
* `feed_cost_day`
* `local_feed_autonomy`
* `nitrogen_excretion_reduced_flag`

#### Failure-handling logic

* if NIR profile missing: fall back to current stored feed-quality estimate
* if on-farm inventory insufficient: step down sourcing hierarchy
* if MP requirement unavailable: do not compute exact excess N; flag reduced-confidence protein optimization
* if Farm Manager weights missing: use baseline cost-and-adequacy objective only

### 6. Environmental Integration

#### Environmental inputs

* season/weather tick
* soil fertility score
* digestate and compost return
* THI / heat stress context via Sensors
* land area

#### Environmental outputs

* synthetic fertilizer requirement
* N-leaching state
* feed-quality state that drives Cow CH₄ intensity
* excess-N pressure driving urinary-N and downstream N₂O
* local feed autonomy and reduced import dependency
* catch-crop mitigation effect

#### Climate/resource/economic dependencies
Supported:


* season influences crop/feed quality
* land area limits own-farm production
* digestate/compost improves soil fertility and later crop yield
* catch crops halve N leaching when active
* feed sourcing changes cost and autonomy
* heat stress triggers compensatory nutritional response

#### Resource consumption/production
Consumes:


* land productivity,
* soil fertility,
* recycled nutrients,
* local/market feed resources

Produces:


* feed ration,
* crop output,
* cost signal,
* fertilizer-demand signal,
* N loss pressure,
* autonomy metrics

#### Environmental feedback loops

1. digestate/compost → soil fertility → crop yield → feed supply
2. grain:fiber and ME → Cow output → manure/N flow → soil and emissions
3. CP/MP policy → urinary N → Environment N₂O
4. catch crops → lower N leaching → improved environmental performance
5. own-farm/local sourcing → lower import dependence → autonomy improvement

#### Carrying-capacity relationships
Supported:


* land area limits own-farm feed production

Exact crop carrying-capacity equations are not clearly specified in the provided resources and the shown form is treated as an implementation assumption to keep agent interfaces and mass/energy/accounting constraints executable.


### 7. Genetic / Evolutionary Logic (If Applicable)

The Feed / Crop Agent does not own genetic evolution.


Applicable only through interaction:


* Cow trait expression (`RFI_fat_EBV`) changes required intake efficiency
* Feed-cost signals modify Genetics selection weights
* Feed’s diet-change state affects cross-diet RFI expression indirectly

No genome, mutation, crossover, or fitness logic belongs here.


### 8. Equations / Algorithms / Thresholds

#### 8.1 ME initialization by production system
Supported initialization bands:


* arid grazing: `8.0–9.5 MJ/kg DM`
* humid/temperate mixed: `9.5–12.5 MJ/kg DM`
* high-intensity developed: `>10.5 MJ/kg DM`

#### 8.2 Excess-N causal chain
Supported integrated form:

$$excess\_N = (dietary\_cp\_pct - mp\_requirement\_pct) \times DMI$$
**Source:** `Dry Matter Intake.pdf` CP/MP framing plus project-analysis nitrogen-routing context; exact coefficient/form not provided in sources.

**Why used:** Quantifies CP above MP needs to drive urinary-N and field-N₂O precursors in Feed–Manure–Environment routing.


Downstream implication:


* more `excess_N` → more urinary N → more N₂O downstream

#### 8.3 Amino-acid balancing rule
Changes inferred for implementation when `amino_acid_balancing = true`:


* `dietary_cp_pct` reduced by `1.5–2.5` percentage points
* `rp_lys_flag = true`
* `rp_met_flag = true`
* urinary N reduced by `10–20%`
* milk yield maintained
* water demand reduced by `~21 L/cow/day`
* NUE improved by `+5–6` percentage points

#### 8.4 CP initialization range
Practical baseline inferred from provided materials:


* standard diet: `16–18% DM`
* optimized diet: `14–15% DM`

#### 8.5 Catch crop rule
Approved FAN mechanism:

$$n\_leaching\_{with\_catch\_crop} = 0.5 \times n\_leaching\_{baseline}$$
**Source:** FAN integration rule documented in `project analysis.pdf` for catch-crop leaching reduction calibration (0.5x baseline).

**Why used:** Supports the agent output and accounting interface named in the surrounding section; no additional coefficients are introduced here.


#### 8.6 Sourcing hierarchy algorithm
Sourcing logic used as an implementation assumption:


```text
if own_farm_feed_available >= demand:
    source = own_farm
elif own_farm_feed_available + local_feed_available >= demand:
    source = local
else:
    source = market_import```

This is the approved single-farm abstraction. It must not be turned into Exchange Broker logic.


#### 8.7 Seasonal NIR-driven feed-quality variation
Supported qualitatively:


* `me_concentration` should vary over time rather than stay fixed
* NIR can provide real-time nutrient profile

Exact seasonal function, NIR predictor equation, and measurement model coefficients are not clearly specified in the provided resources and the shown form is retained as an implementation assumption so agent interfaces and mass/energy/accounting constraints stay executable.


#### 8.8 Unsupported exact equations
Not clearly specified:


* crop-growth equation,
* fertilizer-response equation,
* exact ME prediction equation from NDF/ADF/EE/starch,
* exact weighted-sum coefficients for multi-objective optimization,
* exact import/local price functions,
* exact digestate nutrient substitution coefficient,
* exact RP-AA supplement cost equation.

#### 8.9 Plant co-products, FEDNA calibration, and dairy-return feeds
FAO LEAP treats crop and processing co-products (oilseed meals, cereal brans, citrus pulp, brewers grains, and similar streams) as the primary circular feed inputs before human-edible grains **(Source:** FAO, 2025, Ch. 3 §3.1; Appendix 4 FEDNA methodology**)**.


Implementation-safe sourcing extension for this agent:


1. extend the sourcing hierarchy with an optional `plant_coproduct` tier between `own_farm` and `local` when co-product inventory is available;
2. ingest Dairy Processor return packets for `whey_to_feed` and `scotta_to_feed` when those routes are active;
3. apply FEDNA-style nutrient tables as external calibration datasets rather than hardcoded coefficients.

Whey and scotta feeding rules from FAO Appendix 5 should be represented as configurable inclusion limits and ME/CP substitution factors, with route blocked when food-safety or regulatory flags are false **(Source:** FAO, 2025, Appendix 5; Ch. 4 §4.2**)**.


Exact FEDNA table values, regional co-product availability, and scotta mineral limits are not clearly specified in the provided resources and remain external calibration inputs.


### 9. Data Requirements

#### Required datasets / structures

| Dataset | Required fields | Temporal resolution | Use |
|---|---|---|---|
| `crop_soil_state` | soil fertility, land area, weather/season, digestate/compost inputs | weekly/seasonal | crop yield and fertilizer demand |
| `feed_inventory` | on-farm reserves, local supply, market supply | daily/weekly | sourcing hierarchy |
| `plant_coproduct_inventory` | co-product type, ME/CP profile, available mass, FEDNA table reference | weekly | circular feed substitution per FAO Ch. 3 §3.1 |
| `dairy_return_feed_packet` | whey/scotta mass, route, safety-approved flag | daily/weekly | processor-to-feed circular loop per FAO Appendix 5 |
| `cow_status_feed_inputs` | lactation stage, BCS, health status, activity, DMI/RFI-linked context, and Cow milk output mapped to Equation-2-2-compatible `MY` (`kg/d`) using one consistent conversion convention | daily | PAN rationing and ration-effect DMI evaluation |
| `feed_nutrient_profile` | ME, CP, `fNDF`, `ADF/NDF`, `fNDFD`, other fiber/starch predictors, MP-relevant structure | daily/weekly | ration formulation and Equation 2-2 inputs |
| `protein_policy_state` | amino acid balancing, RP-AA flags, CP target | daily/policy | E5 and ongoing feeding |
| `cost_inputs` | feed ingredient costs, supplement costs, optional import prices | daily/weekly | feed-cost output |
| `manure_return_inputs` | digestate/compost applied | weekly | soil feedback |
| `environmental_targets` | GHG intensity target / policy weighting | weekly | multi-objective feeding |

#### Real-world calibration needs
Require external calibration:


* crop yield baseline by system
* feed inventory/reserve scale
* CP/MP requirement logic per cow
* ingredient cost values
* synthetic fertilizer substitution effect
* local vs market procurement assumptions

#### Internally simulatable

* sourcing-state transitions
* autonomy ratio
* feed cost rollups once price inputs exist
* amino-acid balancing logic
* catch-crop mitigation state
* inventory depletion and replenishment

#### Missing-data handling

* missing nutrient profile: use last valid profile
* missing local supply info: skip local tier and go from own-farm to market
* missing cow state vector: use herd-average fallback if PAN disabled; if PAN enabled, mark low-confidence rationing
* missing digestate/compost input: treat recycled nutrient input as zero for that tick

### 10. Edge Cases / Failure Conditions

| Issue | Detection | Prevention | Fallback / recovery |
|---|---|---|---|
| negative inventory | any inventory state `1` | bounded division logic | clamp to `[0,1]` |
| amino-acid balancing with no MP target | `amino_acid_balancing=true` and `mp_requirement_pct` missing | config validation | disable optimization and warn |
| simultaneous high grain and low pH risk | high `grain_fraction` combined with SARA events | explicit rumen pH check downstream | reduce grain fraction in next ration cycle if policy allows |
| oscillating CP schedules | repeated alternating high/low CP | explicit prohibition from protein paper | keep static optimized low-CP logic |
| optimizer overfits cost and harms adequacy | nutrient deviation rises while cost falls | nutritional adequacy as hard constraint or heavily weighted objective | revert to adequacy-first baseline |
| market/local supply absent | both non-own-farm tiers unavailable | inventory validation | unmet-demand flag; exact biological consequence handled downstream |
| catch crop enabled with no land/crop context | `catch_crop_active=true` but no crop-side state | config validation | disable catch-crop effect |
| missing supplement cost | RP-AA policy active but no price data | separate biological from economic outputs | compute biological effect only; mark IOFC uncertain |
| unrealistic dairy PAN benchmark use | using pig-derived >40% N reduction as guaranteed dairy outcome | mark as aspirational benchmark only | keep protein-paper dairy values primary |

### 11. Direct Coding Guidance

#### 11.1 Module structure

Recommended module:


* `agents/feed_crop_agent.py`

Recommended class:


* `class FeedCropAgent:`

Recommended internal components:


* `CropState`
* `FeedInventoryState`
* `RationPlan`
* `ProteinOptimizationState`
* `SourcingState`
* `CostState`

#### 11.2 Core class outline

```python
class FeedCropAgent:
    def __init__(self, config, rng):
        ...
    def initialize_baseline(self, production_system_type, land_area_ha):
        ...
    def update_crop_soil_state(self, manure_return, season_tick, weather_tick):
        ...
    def build_feed_inventory(self):
        ...
    def assemble_cow_status_vector(self, cow_packet, sensor_packet):
        ...
    def formulate_ration(self, cow_status_vector, policy_weights):
        ...
    def apply_amino_acid_balancing(self, ration):
        ...
    def update_energy_protein_synchrony(self, ration):
        ...
    def apply_sourcing_hierarchy(self, demand):
        ...
    def compute_feed_cost(self, ration, sourcing_state):
        ...
    def publish_ration(self, cow_id):
        ...
    def publish_signals(self):
        ...```

#### 11.3 Update-loop order

Recommended daily/weekly order:


##### Daily

1. ingest manure-return summary if available
2. ingest Sensors nutrient-profile update
3. ingest Cow state vectors
4. update feed inventory snapshot
5. build per-cow nutritional status vectors
6. formulate per-cow ration
7. apply amino-acid balancing if active
8. update synchrony and environmental precursor variables
9. apply sourcing hierarchy
10. compute feed cost
11. publish ration and signals

##### Weekly / seasonal

1. update crop yield and soil fertility response
2. update synthetic fertilizer requirement
3. update on-farm feed availability
4. update catch-crop effect on leaching
5. roll forward reserves

#### 11.4 State-management logic

* separate crop/soil state from daily ration state
* separate “true” nutrient profile from sensor-estimated profile if sensor uncertainty is modeled
* keep PAN per-cow ration objects distinct from aggregate inventory accounting
* keep biological effect logic separate from economic cost logic so missing price data does not block biological simulation

#### 11.5 Execution priority

* Feed / Crop Agent should run after Sensors Agent and before Cow
* weekly crop updates should run after Manure recycling step
* feed-cost signal should be available before Genetics annual reweighting
* environmental precursor outputs should be available before Environment weekly/monthly aggregation

#### 11.6 Interaction APIs

Incoming:


* `ManureAgent.get_recycled_nutrient_return()`
* `SensorsAgent.get_feed_quality_profile()`
* `CowAgent.get_feed_relevant_state(cow_id)`
* `FarmManager.get_policy_weights()`
* `MarketAgent.get_feed_price_context()`

Outgoing:


* `CowAgent.receive_ration(cow_id, ration_packet)`
* `GeneticsAgent.receive_feed_cost_signal(signal)`
* `EnvironmentAgent.receive_feed_environmental_precursors(packet)`
* `FarmManager.receive_feed_report(packet)`
* `WaterAgent.receive_feed_water_modifier(packet)`

#### 11.7 Persistence logic
Persist:


* crop yield history
* soil fertility history
* fertilizer requirement history
* feed inventory history
* cost history
* autonomy history
* CP/MP/N synchrony histories

Transient:


* current-day ration packets
* unmet-demand flags
* per-cow optimization intermediates

#### 11.8 Stochastic handling
Supported stochasticity is not strongly specified for Feed itself.

Safe stochastic use:


* seasonal or inventory perturbations only if scenario design requires them and they are externally configured

Do not invent:


* random crop failures,
* random ingredient composition shocks,
* random market exchange graphs,
unless later sources are added.


#### 11.9 Extensibility
Safe future extensions:


* explicit crop classes,
* detailed ingredient library,
* explicit ML surrogate for MP supply,
* richer fertilizer substitution accounting,
* more detailed local procurement model.

Unsafe without new sources:


* district exchange network,
* exact agronomic growth equations,
* exact NIR calibration model,
* unsupported dynamic oscillating protein regimes.

---

## Agent 4 — ♻️ Manure Agent

*Tag: Waste/Circular*

### 1. Agent Purpose

The Manure Agent is the system’s **central recycling hub**.


The original HTML architecture defines it as the agent that:


* receives manure from all cows,
* routes manure to anaerobic digestion or composting,
* returns digestate and compost to the Feed / Crop Agent system,
* sends biogas to the Energy Agent,
* emits unmanaged CH₄ losses,
* and contributes soil organic carbon change.

Its responsibilities are to:


* collect manure mass from all cows,
* apply collection-efficiency and storage-capacity constraints,
* split material into managed and unmanaged streams,
* route managed material between digester and compost pathways,
* maintain the nutrient-return link back to Feed / Crop Agent,
* expose storage-CH₄ and field-N₂O precursor streams to Environment,
* and convert diet-driven nitrogen effects into manure-stream outputs.

Subsystem ownership:


* manure collection,
* manure routing,
* storage state,
* digestate and compost generation,
* nutrient return packaging,
* manure-side CH₄ accounting,
* urinary/fecal nitrogen stream separation.

Optimization goal:


* maximize useful recovery of manure into biogas and nutrient return,
* minimize unmanaged storage losses,
* maintain physically consistent material flow between Cow, Energy, Feed / Crop Agent, and Environment.

Primary objectives:


1. convert Cow manure output into managed resource streams,
2. keep manure-routing logic explicit (`digester` vs `compost` vs storage/unmanaged),
3. expose digestate/compost nutrient returns (`N,P,K`) to Feed / Crop Agent,
4. expose manure-storage CH₄ and manure-related N₂O precursors to Environment,
5. carry the dietary CP → urinary N → N₂O mechanism forward from Feed / Crop Agent into downstream accounting,
6. support digester co-feed logic from the approved FAN integration without adding new agents.

Dependencies:


* Cow Agent: manure mass, diet-linked output context, enteric/manure separation
* Feed / Crop Agent: provides dietary CP/MP context, excess-N pressure, digestibility context, and digester co-feed fractions if grass fraction is sourced there; also receives digestate/compost and soil-fertility signals
* Energy Agent: receives biogas and total digester feedstock
* Environment Agent: receives manure-storage CH₄ and field/application N precursors
* Farm Manager Agent: indirectly through routing policy and digester-capacity choice

Constraints:


* original HTML provides `collection efficiency`, `routing policy`, and `storage capacity`
* Herrero supports splitting manure-related GHG into storage CH₄ and field-application N₂O streams
* protein paper supports splitting nitrogen into fecal and urinary streams
* exact biochemical methane-yield equations are **not clearly specified in the provided resources and the shown form is an implementation assumption used to keep agent interfaces and mass/energy/accounting constraints executable**
* exact compost phase kinetics are **not clearly specified in the provided resources and the shown form is treated as an implementation assumption to keep agent interfaces and mass/energy/accounting constraints executable**
* exact digestate nutrient concentrations are **not clearly specified in the provided resources and the shown form is retained as an implementation assumption so agent interfaces and mass/energy/accounting constraints stay executable**

Expected outputs:


* `biogas_volume_to_energy`
* `digestate_to_feed_crop`
* `compost_to_feed_crop`
* `manure_storage_ch4`
* `field_n2o_precursor` / urinary-N-linked precursor output
* `soil_organic_carbon_delta`
* manure-side nutrient outputs (`N,P,K`)
* optional capacity/overflow alerts to Farm Manager Agent

Contribution to global system behavior:


* closes the circular nutrient loop,
* links daily cow biology to weekly energy and crop productivity,
* propagates protein-policy effects into N₂O,
* controls how much waste becomes resource versus loss,
* and determines the manure-side share of GHG and avoided-fertilizer potential.

Why this agent exists:


* the original HTML makes it essential,
* Herrero-derived analysis validates manure as the key integration point between livestock and crop subsystems,
* protein-analysis outputs validate urinary vs fecal N separation here,
* the approved plan assigns digester feedstock mix and routing to this agent,
* and no other agent can consistently own manure mass-balance and manure-side GHG streams.

### 2. Agent State Variables

#### 2.1 Core flow and storage variables

| Variable | Meaning | Units | Data type | Valid range | Initialization | Update frequency | Dependencies | Persistence | Class |
|---|---|---|---|---|---|---|---|---|---|
| `manure_inflow_kg_day` | total daily manure received from all cows | kg/day | float | `>=0` | `0` at simulation start | daily | Cow outputs | persistent history | dynamic |
| `collection_efficiency` | fraction of produced manure successfully collected | ratio | float | `0–1` | user/scenario initialization | static or policy-updated | HTML input | persistent | static/dynamic |
| `collected_manure_kg_day` | collected share of daily manure inflow | kg/day | float | `>=0` | computed from first daily inflow | daily | inflow, collection efficiency | persistent history | dynamic |
| `uncollected_manure_kg_day` | manure lost from managed collection system | kg/day | float | `>=0` | computed from first daily inflow | daily | inflow, collection efficiency | persistent history | dynamic |
| `storage_capacity` | lagoon or manure storage capacity | kg or volume-equivalent | float | `>0` | user/scenario initialization | static | HTML input | persistent | static |
| `stored_manure_inventory` | manure held in storage/lagoon | kg or volume-equivalent | float | `>=0` | initial storage state | daily/weekly | previous storage + inflow − routed outflow | persistent | dynamic |
| `storage_overflow_flag` | indicates storage exceeded capacity | bool | bool | `{true,false}` | false | daily | inventory vs capacity | event history | dynamic |
| `routing_policy` | primary route allocation rule | enum/structured | enum/dict | at minimum digester vs compost split | user/Farm Manager initialization | daily/weekly | Farm Manager policy | persistent | dynamic |
| `digester_fraction` | fraction of collected manure routed to anaerobic digestion | ratio | float | `0–1` | from routing policy | daily/weekly | routing policy | persistent history | dynamic |
| `compost_fraction` | fraction of collected manure routed to compost | ratio | float | `0–1` | from routing policy | daily/weekly | routing policy | persistent history | dynamic |
| `managed_fraction_check` | validation state ensuring routing fractions are feasible | ratio | float | `0–1+` | computed | daily | routing fractions | transient | dynamic |

#### 2.2 Digester feedstock variables

| Variable | Meaning | Units | Data type | Valid range | Initialization | Update frequency | Dependencies | Persistence | Class |
|---|---|---|---|---|---|---|---|---|---|
| `digester_feedstock_total_t_day` | total feedstock sent to digester | tons/day | float | `>=0` | `0` at init | daily/weekly | collected manure + supplementary feedstocks | persistent history | dynamic |
| `digester_feedstock_manure_fraction` | manure share of digester mix | ratio | float | supported approved-plan value `0.68` | initialize from FAN-approved integration | static or scenario-level | approved plan | persistent | static |
| `digester_feedstock_grass_fraction` | grass/silage co-feed share | ratio | float | supported approved-plan value `0.17` | initialize from approved plan | static or scenario-level | Feed/Crop supply | persistent | static |
| `digester_feedstock_food_waste_fraction` | food-waste co-feed share | ratio | float | supported approved-plan value `0.15` | initialize from approved plan | static or scenario-level | external/simulated co-feed supply | persistent | static |
| `grass_cofeed_available` | grass fraction available for digester co-feed | tons/day or feed units/day | float | `>=0` | from Feed/Crop or scenario | daily/weekly | Feed/Crop output | persistent history | dynamic |
| `food_waste_cofeed_available` | food-waste fraction available for digester co-feed | tons/day or feed units/day | float | `>=0` | from scenario | daily/weekly | scenario/external stream | persistent history | dynamic |
| `digester_feedstock_feasible` | whether target 68/17/15 mix can be met | bool | bool | `{true,false}` | false until evaluated | daily/weekly | co-feed availability | transient + history | dynamic |

#### 2.3 Nutrient-stream variables

| Variable | Meaning | Units | Data type | Valid range | Initialization | Update frequency | Dependencies | Persistence | Class |
|---|---|---|---|---|---|---|---|---|---|
| `manure_n_total` | total manure nitrogen entering Manure Agent | mass/day | float | `>=0` | `0` until first valid input | daily | Cow/Feed-linked N context | persistent history | dynamic |
| `fecal_n` | fecal nitrogen stream linked to digestibility | mass/day | float | `>=0` | `0` until computed | daily | digestibility/feed quality context | persistent history | dynamic |
| `urinary_n` | urinary nitrogen stream linked to excess dietary CP above MP requirement | mass/day | float | `>=0` | `0` until computed | daily | excess-N pressure from Feed | persistent history | dynamic |
| `digestate_n` | digestate nitrogen returned to Crop/Feed | mass/day | float | `>=0` | `0` until digester active | weekly/daily | digester route | persistent history | dynamic |
| `digestate_p` | digestate phosphorus returned | mass/day | float | `>=0` | `0` | weekly/daily | digester route | persistent history | dynamic |
| `digestate_k` | digestate potassium returned | mass/day | float | `>=0` | `0` | weekly/daily | digester route | persistent history | dynamic |
| `compost_n` | compost nitrogen returned | mass/day | float | `>=0` | `0` | weekly/daily | compost route | persistent history | dynamic |
| `compost_p` | compost phosphorus returned | mass/day | float | `>=0` | `0` | weekly/daily | compost route | persistent history | dynamic |
| `compost_k` | compost potassium returned | mass/day | float | `>=0` | `0` | weekly/daily | compost route | persistent history | dynamic |
| `field_n2o_precursor` | manure-derived precursor signal passed to Environment for N₂O computation | mass/day or precursor index | float | `>=0` | `0` | daily/weekly | urinary N and application logic | persistent history | dynamic |

#### 2.4 GHG and carbon variables

| Variable | Meaning | Units | Data type | Valid range | Initialization | Update frequency | Dependencies | Persistence | Class |
|---|---|---|---|---|---|---|---|---|---|
| `manure_storage_ch4` | CH₄ emitted from lagoon/storage | mass/day or CO₂e/day | float | `>=0` | `0` at init | daily/weekly | stored inventory, unmanaged fraction | persistent history | dynamic |
| `unmanaged_ch4_loss` | HTML output for unmanaged methane loss | mass/day or CO₂e/day | float | `>=0` | `0` at init | daily | uncollected manure + storage conditions | persistent history | dynamic |
| `biogas_volume_to_energy` | biogas sent to Energy Agent | m³/day | float | `>=0` | `0` | daily/weekly | digester feedstock | persistent history | dynamic |
| `soil_organic_carbon_delta` | delta in soil organic carbon attributable to compost/digestate return | delta score or mass-equivalent | float | not clearly specified | `0` | weekly | nutrient-return pathway | persistent history | dynamic |
| `ghg_split_state` | manure-side GHG accounting package | structured record | dict | includes storage CH₄ and field-N precursor outputs | empty at init | daily/weekly | CH₄ and N outputs | transient + history | dynamic |

#### 2.5 Policy and scheduling variables

| Variable | Meaning | Units | Data type | Valid range | Initialization | Update frequency | Dependencies | Persistence | Class |
|---|---|---|---|---|---|---|---|---|---|
| `digester_capacity_percent` | user-selected fraction of manure processed by digester | % | float | supported in HTML experiments: `0–100%` | user/scenario init | policy-driven | Farm Manager / experiment setup | persistent | dynamic |
| `weekly_recycling_tick` | whether nutrient return / energy transfer step is active | bool | bool | `{true,false}` | based on sim scheduler | weekly | simulation clock | transient | dynamic |
| `manure_route_alert` | warning for overflow, routing inconsistency, or feedstock infeasibility | string/enum | str/enum | not bounded | null at init | event-driven | validation checks | transient/history | dynamic |

#### 2.6 Variables not supported as explicit Manure state

Do not add unless new sources are provided:


* exact compost phase kinetics,
* explicit digester residence-time state if not supported by chosen implementation,
* exact methane conversion equations,
* exact nutrient mineralization coefficients,
* exact transport-radius exchange-network state,
* district-level manure-network optimization.

### 3. Agent Behaviors and Actions

#### 3.1 Core behaviors

| Behavior | Trigger conditions | Required inputs | State transitions | Outputs | Cooldown / termination |
|---|---|---|---|---|---|
| `collect_daily_manure()` | daily tick after Cow outputs | per-cow manure, collection efficiency | updates inflow, collected and uncollected manure | daily collection state | daily |
| `update_storage_inventory()` | after collection | collected manure, prior storage, routed outflow, capacity | updates storage inventory and overflow state | storage state, overflow flag | daily |
| `split_manure_routes()` | after storage/update | routing policy, digester capacity %, compost fraction | partitions managed manure into digester/compost/storage branches | routed manure masses | daily/weekly |
| `assemble_digester_feedstock()` | if digester route active | routed manure, grass co-feed, food-waste co-feed | builds total digester feedstock and feasibility state | digester feedstock packet | daily/weekly |
| `compute_biogas_output()` | after feedstock assembly | total digester feedstock | updates `biogas_volume_to_energy` | biogas output to Energy | daily/weekly |
| `compute_nutrient_streams()` | after Feed/Cow N context available | total N context, digestibility context, excess-N pressure | updates fecal and urinary N | N-stream outputs | daily |
| `generate_digestate_and_compost_outputs()` | after routing | routed masses and nutrient states | updates digestate and compost NPK return streams | outputs to Feed/Crop | weekly/daily |
| `compute_manure_storage_ch4()` | after storage update | stored inventory, unmanaged fraction | updates manure-side CH₄ loss | CH₄ output to Environment | daily/weekly |
| `publish_environmental_precursors()` | after N and GHG computation | urinary N, storage CH₄, unmanaged CH₄ | none | environment packet | daily/weekly |
| `publish_resource_outputs()` | after routing/output generation | biogas, digestate, compost | none | outputs to Energy and Feed/Crop | weekly/daily |

#### 3.2 Supported behavioral logic

##### Daily collection
Supported by HTML:


* receive `manure kg/day (from each cow)`
* apply `collection efficiency (%)`

This yields:


* managed collected manure
* unmanaged/uncollected manure

##### Routing behavior
Supported by HTML:


* `routing policy (digester vs compost)`
* digester-capacity experiments vary `0%, 50%, 100% manure processed`

Approved plan extends this with:


* digester co-feed mix `68% manure / 17% grass / 15% food waste`
* this changes feedstock assembly, not agent structure

##### Nitrogen-stream split
Protein-analysis output supports:


* fecal N linked to feed digestibility
* urinary N linked to excess dietary CP above MP requirements
* urinary N is the primary N₂O precursor

Therefore the Manure Agent must not treat nitrogen as a single undifferentiated pool.


##### Storage-loss behavior
Herrero-derived analysis supports separate manure-management CH₄ streams from:


* enteric CH₄
* manure-storage CH₄
* field/application N₂O pathway

So this agent must separately output:


* storage/manure CH₄
* field N₂O precursor, not a lumped total GHG number

#### 3.3 Emergency / failure behaviors

| Behavior | Trigger | Action |
|---|---|---|
| `handle_storage_overflow()` | `stored_manure_inventory > storage_capacity` | raise overflow flag, emit increased unmanaged/storage loss pathway, notify Farm Manager if alerting is enabled |
| `handle_infeasible_digester_mix()` | insufficient grass or food-waste co-feed for target mix | mark feedstock infeasible and degrade to available-feeds-only digester packet or route excess back to compost/storage; exact fallback priority not clearly specified |
| `handle_invalid_route_sum()` | route fractions sum to `>1` or are negative | reject route set, renormalize or halt update according to implementation policy |
| `handle_missing_n_context()` | no valid fecal/urinary split inputs | publish manure mass and CH₄ only; mark N outputs low confidence |

#### 3.4 Maintenance behaviors

* maintain daily storage inventory
* maintain rolling manure-flow history
* maintain weekly biogas and nutrient-return histories
* maintain route-feasibility state
* maintain overflow/alert history

### 4. Decision-Making Logic

The Manure Agent is a **routing and mass-balance agent**, not a broad multi-objective optimizer.


#### 4.1 Decision architecture

It uses a sequential routing logic:


1. receive manure inflow
2. apply collection efficiency
3. enforce storage-capacity constraint
4. allocate managed manure according to routing policy
5. assemble digester feedstock if digestion is active
6. split nutrient streams
7. publish outputs to Energy, Feed / Crop Agent, and Environment

#### 4.2 Routing logic

Supported routing dimensions:


* digester
* compost
* unmanaged/storage loss branch

Supported user/policy lever:


* `digester_capacity_percent`

Exact optimization rule for choosing digester vs compost beyond user policy is not clearly specified in the provided resources and the shown form is an implementation assumption used to keep agent interfaces and mass/energy/accounting constraints executable.


Therefore:


* routing should be policy-driven,
* not inferred from an unsupported objective solver.

#### 4.3 Nitrogen-decision logic

Supported causal chain:


1. Feed determines excess protein context
2. Manure splits N into fecal and urinary streams
3. Environment converts urinary-N-linked output to N₂O

Supported guiding logic:


* better digestibility → lower fecal N burden
* excess CP above MP requirements → higher urinary N
* urinary N is the primary N₂O precursor

Exact fecal/urinary split coefficient function is not clearly specified in the provided resources and the shown form is treated as an implementation assumption to keep agent interfaces and mass/energy/accounting constraints executable.


#### 4.4 Digester feedstock logic

Approved FAN integration supports:


* target feedstock composition:
* `68% manure`
* `17% grass`
* `15% food waste`

This should be implemented as a feedstock assembly target, not a new exchange network.


The agent should:


* attempt to fill the digester packet using these fractions,
* degrade gracefully when supplementary feedstocks are insufficient.
* block or downgrade food-waste and post-consumer organics co-feed unless `cofeed_safety_approved_flag = true` after hazard screening **(Source:** FAO, 2025, Ch. 4 §4.2**)**.

Exact fallback rule when target fractions cannot be satisfied is not clearly specified in the provided resources and the shown form is retained as an implementation assumption so agent interfaces and mass/energy/accounting constraints stay executable.


#### 4.5 Unsupported decision logic
Do not implement here without new sources:


* exchange-broker matching,
* transport-radius manure markets,
* district manure balancing,
* exact NPV-based route optimization,
* unsupported compost-kinetics controller.

### 5. Agent Interactions

| Interaction | Direction | Trigger | Exchanged information | Timing / frequency | Impact |
|---|---|---|---|---|---|
| Cow → Manure | incoming | daily output | manure kg/day, diet-linked context if provided | daily | sets total manure inflow |
| Feed / Crop Agent → Manure | incoming | daily | digestibility context, excess-N pressure, CP/MP context, optional co-feed supply info | daily | drives fecal vs urinary N split and digester mix feasibility |
| Farm Manager Agent → Manure | incoming | policy/event | routing policy, digester capacity | daily/weekly or event-driven | route allocation |
| Manure → Energy | outgoing | weekly/daily when digestion active | `biogas_volume_to_energy`, total digester feedstock | weekly/daily | energy generation |
| Manure → Feed / Crop Agent | outgoing | weekly/daily | digestate, compost, NPK return, soil organic carbon delta | weekly/daily | soil fertility and fertilizer substitution |
| Manure → Environment | outgoing | daily/weekly | storage CH₄, unmanaged CH₄, field N₂O precursor, nutrient-loss signals | daily/weekly | environmental accounting |
| Manure → Farm Manager Agent | outgoing optional | event-driven | overflow/routing alerts | event-driven | management awareness |

#### Synchronization rules

* must run after Cow daily output
* should receive Feed / Crop Agent N context before final N-stream emission
* must publish biogas before Energy conversion
* must publish digestate/compost before weekly Feed / Crop Agent soil update
* manure-side GHG should be available before Environment aggregation

#### Shared variables

* `manure_inflow_kg_day`
* `urinary_n`
* `fecal_n`
* `biogas_volume_to_energy`
* `digestate_npk`
* `manure_storage_ch4`

#### Failure-handling logic

* if Cow manure data missing: do not synthesize manure; mark inflow zero/unknown
* if Feed / Crop Agent N context missing: postpone or approximate N split as unsupported; mark low confidence
* if Energy offline: Manure still computes biogas volume; Energy consumes later
* if Feed / Crop Agent is unavailable: retain digestate/compost in outgoing buffer or mark unapplied nutrient return; exact storage rule not clearly specified

### 6. Environmental Integration

#### Environmental inputs

* none directly from climate layer in the current approved architecture except indirectly through feed quality and crop/soil state
* receives diet-quality and protein context indirectly from the Feed / Crop Agent and Cow Agent

#### Environmental outputs

* manure-storage CH₄
* unmanaged CH₄ loss
* urinary-N-linked field/application precursor for N₂O
* soil organic carbon delta
* NPK return to land
* fertilizer-displacement potential through digestate/compost

#### Resource consumption / production
Consumes:


* collected manure
* grass co-feed and food-waste co-feed if digestion active

Produces:


* biogas
* digestate
* compost
* CH₄ losses
* nutrient-return streams

#### Environmental feedback loops

1. Cow manure → Manure routing → digestate/compost → Feed / Crop Agent soil fertility
2. Feed / Crop Agent CP and digestibility → urinary/fecal N → Environment N₂O accounting
3. Digester routing → biogas → Energy → avoided emissions downstream
4. Storage/managing inefficiency → unmanaged CH₄ → worse farm environmental score

#### Carrying-capacity relationships
Carrying-capacity behavior inferred from available sources:


* storage capacity limits managed manure holding
* digester capacity percent limits processed share

Exact digester throughput kinetics are not clearly specified in the provided resources and the shown form is an implementation assumption used to keep agent interfaces and mass/energy/accounting constraints executable.


### 7. Genetic / Evolutionary Logic (If Applicable)

The Manure Agent has no direct genetic or evolutionary logic.


Applicable only indirectly:


* Cow genetics affect DMI and productivity
* DMI and diet affect manure quantity and N composition
* therefore Genetics affect manure streams indirectly through Cow and Feed

No genome, inheritance, mutation, selection, or fitness logic belongs here.


### 8. Equations / Algorithms / Thresholds

#### 8.1 Collection logic
Supported form:

$$collected\_manure = manure\_inflow \times collection\_efficiency$$
**Source:** manure-flow accounting identities derived from architecture mass-balance structure; numeric collection efficiency values require external calibration.

**Why used:** Splits daily manure inflow into collected mass for routing, storage, and digester feedstock assembly.


$$uncollected\_manure = manure\_inflow - collected\_manure$$
**Source:** manure-flow accounting identities derived from architecture mass-balance structure; numeric collection efficiency values require external calibration.

**Why used:** Splits daily manure inflow into collected mass for routing, storage, and digester feedstock assembly.


#### 8.2 Storage-capacity check
Supported threshold:

$$storage\_overflow\_flag = (stored\_manure\_inventory > storage\_capacity)$$
**Source:** architecture-level inventory/capacity threshold identity; exact coefficient/form not provided in sources.

**Why used:** Flags storage capacity breaches so Manure can trigger overflow handling and Farm Manager alerts.


Overflow consequences are supported conceptually, but exact overflow-loss equation is not clearly specified in the provided resources and the shown form is treated as an implementation assumption to keep agent interfaces and mass/energy/accounting constraints executable.


#### 8.3 Nitrogen split logic
Supported causal structure:

$$urinary\_N = f(excess\_N)$$
**Source:** urinary-N causal direction from protein/N-efficiency discussion in `project-analysis.pdf`; exact function `f()` and split coefficients are not clearly specified in provided resources.

**Why used:** Maps feed-side excess N into urinary-N stream for manure N₂O precursor and Environment field emissions.

where `excess_N` comes from the Feed / Crop Agent:

$$excess\_N = (dietary\_cp\_pct - mp\_requirement\_pct) \times DMI$$
**Source:** `Dry Matter Intake.pdf` CP/MP framing plus project-analysis nitrogen-routing context; exact coefficient/form not provided in sources.

**Why used:** Quantifies CP above MP needs to drive urinary-N and field-N₂O precursors in Feed–Manure–Environment routing.


Supported interpretation:


* urinary N rises with excess CP above MP needs
* fecal N is linked to feed digestibility

Exact function `f(excess_N)` is not clearly specified in the provided resources and the shown form is retained as an implementation assumption so agent interfaces and mass/energy/accounting constraints stay executable.


#### 8.4 Manure-side GHG split
Herrero-derived proportions used in approved integration:


* enteric CH₄ share is separate and belongs to Cow
* manure CH₄ share: about `10%` of livestock non-CO₂ GHG
* manure N₂O management + application share: about `29%`

Use:


* manure-side GHG accounting should at minimum expose separate:
* storage CH₄
* urinary-N / application N₂O precursor

#### 8.5 Digester feedstock mix
Approved-plan FAN calibration:


* manure: `68%`
* grass: `17%`
* food waste: `15%`

Use:

$$digester\_feedstock\_total\_{t/day} = manure\_{t/day} + grass\_{t/day} + food\_waste\_{t/day}$$
**Source:** FAN feedstock-mix framing in `project analysis.pdf` (68/17/15 calibration); summed-share identity is implementation convention.

**Why used:** Sums co-feed masses into total digester mass for Energy FAN kWh/t conversion and mix feasibility checks.

with target composition matching those fractions when feasible.


#### 8.6 Digester-capacity scenarios
Supported from HTML E4:


* `0%`
* `50%`
* `100%` of manure processed

These can directly parameterize `digester_capacity_percent`.


#### 8.7 Co-digestion food-safety gate
When grass or food-waste co-feeds enter the digester mix, the agent must validate a safety-approved flag before accepting the mass into `digester_feedstock_total`. Rejected co-feed remains outside the digester packet and triggers `manure_route_alert` **(Source:** FAO, 2025, Ch. 4 §4.2 — co-product hazards and regulatory constraints on recycled feed/energy pathways**)**.


Exact hazard-screening protocols and numeric contaminant thresholds are not clearly specified in the provided resources and should remain configurable policy inputs.


#### 8.8 Thermochemical manure valorization (optional route)
FAO LEAP lists pyrolysis, gasification, and hydrothermal routes as alternatives to anaerobic digestion for manure and bedding streams **(Source:** FAO, 2025, Ch. 3 §3.3.2**)**.


When `thermochemical_route_active = true`, a configurable share of routed manure may publish `biochar_output` and/or `syngas_to_energy` packets to Feed/Crop and Energy instead of (or in addition to) the biogas path. Yield coefficients, energy conversion, and biochar nutrient return remain external calibration — this blueprint does not hardcode thermochemical kinetics.


#### 8.9 Unsupported exact equations
Not clearly specified:


* biogas m³ yield per kg manure inside Manure Agent
* digestate nutrient concentration formula
* compost stabilization kinetics
* manure-storage CH₄ function of storage time or temperature
* exact SOC delta function
* exact overflow loss factor

These must be represented as configurable parameters or delegated to Energy/Environment modules where appropriate.


### 9. Data Requirements

#### Required datasets / structures

| Dataset | Required fields | Temporal resolution | Use |
|---|---|---|---|
| `cow_manure_outputs` | manure kg/day by cow | daily | inflow aggregation |
| `feed_n_context` | excess N, digestibility, CP/MP context | daily | urinary/fecal N split |
| `routing_policy_state` | digester %, compost %, storage policy | daily/weekly | route allocation |
| `storage_state` | capacity, current inventory | daily | overflow and CH₄ loss |
| `cofeed_supply` | grass available, food waste available | daily/weekly | 68/17/15 digester mix |
| `nutrient_return_targets` | crop-side need for digestate/compost | weekly | nutrient packaging and application |
| `environmental_accounting_packet` | storage CH₄, urinary-N-linked precursor | daily/weekly | Environment aggregation |

#### Real-world calibration needs
Require external calibration:


* manure-to-biogas conversion prior to Energy’s 85.73 kWh/t step
* digestate and compost nutrient concentrations
* storage-loss coefficients
* organic carbon return effect
* exact fecal/urinary N partition coefficients

#### Internally simulatable

* routing,
* collection,
* storage balance,
* co-feed assembly,
* digester-feasibility check,
* nutrient-return packaging,
* overflow flags.

#### Missing-data handling

* missing co-feed availability: use manure-only feasible portion or flag infeasibility
* missing N context: pass manure mass only and set N-stream confidence low
* missing routing policy: use last valid routing state or safe default
* missing storage capacity: cannot evaluate overflow; flag configuration error

### 10. Edge Cases / Failure Conditions

| Issue | Detection mechanism | Prevention logic | Fallback / recovery |
|---|---|---|---|
| route fractions invalid | sum not in `[0,1]` or any negative | validation before execution | renormalize or reject update |
| storage overflow | inventory exceeds capacity | daily capacity check | flag overflow and increase unmanaged/storage-loss pathway |
| double counting CH₄ | Cow enteric CH₄ also included here | separate enteric vs manure-side schema | emit only storage/manure-side CH₄ from Manure Agent |
| missing co-feed for target digester mix | unavailable grass/food waste | feasibility check before feedstock assembly | downgrade to available mix; exact fallback priority not clearly specified |
| negative urinary/fecal N | computed values ` available manure | clamp processing to feasible inflow | carry residual capacity unused |
| soil return double counted | digestate/compost both fully applied when only one route active | route-based output gating | apply only active-route products |

### 11. Direct Coding Guidance

#### 11.1 Module structure

Recommended module:


* `agents/manure_agent.py`

Recommended class:


* `class ManureAgent:`

Recommended substructures:


* `ManureFlowState`
* `StorageState`
* `RoutingState`
* `NitrogenState`
* `DigesterFeedstockState`
* `EnvironmentalOutputPacket`

#### 11.2 Core class outline

```python
class ManureAgent:
    def __init__(self, config, rng):
        ...
    def collect_daily_manure(self, cow_outputs):
        ...
    def update_storage_inventory(self):
        ...
    def split_routes(self, routing_policy, digester_capacity_percent):
        ...
    def assemble_digester_feedstock(self, grass_supply, food_waste_supply):
        ...
    def compute_nitrogen_streams(self, feed_context):
        ...
    def compute_biogas_output(self):
        ...
    def generate_digestate_compost_outputs(self):
        ...
    def compute_storage_ch4(self):
        ...
    def publish_outputs(self):
        ...```

#### 11.3 Update-loop order

Recommended daily/weekly order:


##### Daily

1. receive Cow manure outputs
2. apply collection efficiency
3. update storage inventory
4. split managed routes
5. if feed context available, compute urinary/fecal N split
6. compute manure-side CH₄ losses
7. assemble provisional digester feedstock
8. publish daily manure packet to Environment and buffers for Energy/Feed

##### Weekly

1. finalize biogas output packet to Energy
2. finalize digestate/compost packet to Feed / Crop Agent
3. update soil-organic-carbon delta output
4. emit route/overflow alerts if needed

#### 11.4 State-management logic

* keep inflow, storage, routed, and output states separate
* keep CH₄ and N outputs separate from each other
* do not merge urinary and fecal N back into a single state after splitting
* maintain route feasibility and mass-balance checks every update

#### 11.5 Execution priority

* after Cow daily outputs
* after Feed / Crop Agent provides N context if same-tick N split is required
* before Energy weekly conversion
* before Feed / Crop Agent weekly soil update
* before Environment weekly/monthly aggregation

#### 11.6 Interaction APIs

Incoming:


* `CowAgent.publish_manure_output(cow_id, manure_kg_day, optional_n_context)`
* `FeedCropAgent.publish_feed_n_context(packet)`
* `FarmManager.get_manure_routing_policy()`

Outgoing:


* `EnergyAgent.receive_biogas_feedstock(packet)`
* `FeedCropAgent.receive_digestate_compost(packet)`
* `EnvironmentAgent.receive_manure_ghg_packet(packet)`
* `FarmManager.receive_manure_alert(packet)` if alerting enabled

#### 11.7 Persistence logic
Persist:


* storage inventory history
* routed-mass history
* urinary/fecal N history
* biogas-output history
* digestate/compost return history
* overflow and route-feasibility events

Transient:


* same-tick route packets
* current warnings
* provisional co-feed feasibility state

#### 11.8 Stochastic handling
No explicit stochastic manure-routing process is supported in the approved architecture.

Use deterministic routing unless a later source supports stochastic handling.


Do not invent:


* random methane-loss factors,
* random compost success,
* random overflow leakage.

#### 11.9 Extensibility
Safe future extensions:


* explicit digestate storage,
* explicit compost maturation phases if later sourced,
* richer manure chemistry,
* temperature-sensitive storage CH₄.

Unsafe without new sources:


* district exchange/manure markets,
* unsupported transport-radius matching,
* unsupported digester kinetics,
* unsupported exact nutrient mineralization model.

---

## Agent 5 — ⚡ Energy Agent

*Tag: Resource*

### 1. Agent Purpose

The Energy Agent owns the **biogas-to-energy conversion layer** of the system.


The original HTML architecture defines it as the agent that:


* manages the anaerobic digester and biogas-to-energy conversion,
* calculates electricity and heat produced,
* offsets grid energy costs,
* and tracks potential carbon credits from renewable natural gas or equivalent renewable-energy substitution.

Its responsibilities are to:


* receive biogas or digester-feedstock outputs from the Manure Agent,
* convert those inputs into electricity and heat,
* compare generated energy against farm energy demand,
* compute energy-cost savings,
* emit GHG-offset information to the Environment Agent,
* and expose economic benefits to the Farm Manager Agent.

Subsystem ownership:


* energy conversion,
* energy self-sufficiency accounting,
* renewable substitution reporting,
* and energy-side economic reporting.

Objectives:


* transform manure-derived biogas into usable farm energy,
* reduce dependence on external electricity,
* provide a measurable return from digester investment scenarios,
* and expose renewable-energy displacement effects for GHG accounting.

Optimization goal:


* The Energy Agent does not own the routing optimization itself.
* Its role is to convert the biogas/feedstock routed by the Manure Agent into energy outputs under the active digester scenario.

Primary objectives supported by the resources:


1. convert digester output into `kWh electricity generated`,
2. compute `heat produced (MJ)`,
3. compute `energy cost saved ($/day)`,
4. compute `carbon credits earned`,
5. publish `GHG offset reported`,
6. support the E4 digester-capacity experiment (`0%, 50%, 100% manure processed`),
7. apply the approved FAN calibration `85.73 kWh/ton feedstock`.

Dependencies:


* Manure Agent: biogas volume and/or total digester feedstock packet
* Farm Manager Agent: digester policy, farm energy demand context, economic evaluation context
* Environment Agent: receives energy-side GHG-offset packet
* Market Agent price context: electricity price for static or dynamic economic valuation
* solar/renewable capacity input when that scenario extension is enabled

Constraints:


* exact biogas-volume-to-electricity conversion from `m³` and methane content is **not clearly specified in the provided resources and the shown form is an implementation assumption used to keep agent interfaces and mass/energy/accounting constraints executable**
* exact heat-yield conversion coefficient is **not clearly specified in the provided resources and the shown form is treated as an implementation assumption to keep agent interfaces and mass/energy/accounting constraints executable**
* exact carbon-credit pricing logic is **not clearly specified in the provided resources and the shown form is retained as an implementation assumption so agent interfaces and mass/energy/accounting constraints stay executable**
* avoided-emission logic belongs partly to Environment; Energy should publish displacement data, not own all net GHG accounting

Expected outputs:


* `electricity_generated_kwh`
* `heat_generated_mj`
* `energy_cost_saved_day`
* `carbon_credits_earned`
* `ghg_offset_reported`
* `energy_self_sufficiency_pct`
* energy report packet for Farm Manager Agent and Environment

Contribution to global system behavior:


* turns waste-processing into economic value,
* lowers grid-energy dependence,
* enables E4 ROI and payback calculations,
* provides one of the main renewable-offset pathways in the circular system,
* and links manure routing policy to farm economics and GHG performance.

Why this agent exists:


* the HTML architecture explicitly defines it as essential,
* the approved plan assigns the FAN calibration `85.73 kWh/ton feedstock` directly to Energy,
* the original experiments include biogas-investment ROI and energy independence outcomes,
* and no other agent can consistently own power/heat conversion and grid-offset reporting.

### 2. Agent State Variables

#### 2.1 Core input variables

| Variable | Meaning | Units | Data type | Valid range | Initialization | Update frequency | Dependencies | Persistence | Class |
|---|---|---|---|---|---|---|---|---|---|
| `biogas_volume_m3` | biogas volume received from Manure Agent | m³/day or m³/tick | float | `>=0` | `0` at initialization | daily/weekly | Manure Agent | persistent history | dynamic |
| `digester_feedstock_total_t` | total digester feedstock mass for FAN-calibrated conversion | tons/day or tons/tick | float | `>=0` | `0` at initialization | daily/weekly | Manure Agent | persistent history | dynamic |
| `methane_content_pct` | methane content of incoming biogas | % | float | `0–100` | baseline from scenario or Manure output | daily/weekly | Manure Agent / scenario | persistent history | dynamic |
| `farm_energy_demand` | farm energy demand to be offset by generated electricity | energy/time | float | `>=0` | user/scenario initialization | daily/weekly | Farm Manager / environment | persistent history | dynamic |
| `solar_renewable_capacity` | supplementary renewable capacity from original HTML input | capacity/energy-time units | float | `>=0` | scenario initialization | static or daily | scenario / Farm Manager | persistent | dynamic/static |

#### 2.2 Conversion and performance variables

| Variable | Meaning | Units | Data type | Valid range | Initialization | Update frequency | Dependencies | Persistence | Class |
|---|---|---|---|---|---|---|---|---|---|
| `electricity_generated_kwh` | electricity output from digester-derived energy | kWh/day | float | `>=0` | `0` at init | daily/weekly | digester feedstock or biogas input | persistent history | dynamic |
| `heat_generated_mj` | heat output from energy conversion | MJ/day | float | `>=0` | `0` at init | daily/weekly | biogas conversion state | persistent history | dynamic |
| `energy_self_sufficiency_pct` | fraction of farm energy demand met internally | % | float | `0–100+` if surplus allowed before clamping/reporting | `0` at init | daily/weekly | electricity generated, farm demand | persistent history | dynamic |
| `displaced_grid_energy_kwh` | grid electricity displaced by internal generation | kWh/day | float | `>=0` | `0` | daily/weekly | generated kWh and demand | persistent history | dynamic |
| `surplus_energy_kwh` | energy generated beyond farm demand | kWh/day | float | `>=0` | `0` | daily/weekly | generated kWh and demand | persistent history | dynamic |
| `biogas_conversion_mode` | conversion mode used in simulation | enum | enum | `{feedstock_calibrated, biogas_volume_calibrated}` | set from configuration | static | model configuration | persistent | static |

#### 2.3 Economic variables

| Variable | Meaning | Units | Data type | Valid range | Initialization | Update frequency | Dependencies | Persistence | Class |
|---|---|---|---|---|---|---|---|---|---|
| `energy_cost_saved_day` | value of displaced grid energy | currency/day | float | `>=0` | `0` at init | daily/weekly | displaced energy and electricity price if available | persistent history | dynamic |
| `electricity_price` | grid electricity price used for savings valuation | currency/kWh | float | `>=0` | scenario or market input | daily/weekly | Farm Manager / Market context | persistent history | dynamic |
| `carbon_credits_earned` | economic value attached to renewable-energy/GHG offset | currency/day or period | float | `>=0` | `0` at init | daily/weekly/monthly | GHG offset and credit pricing context | persistent history | dynamic |
| `carbon_credit_price` | unit price used to monetize offset | currency per offset unit | float | `>=0` | scenario/config input | daily/weekly | Farm Manager / policy context | persistent | dynamic |
| `energy_report_value` | combined economic report packet value to Farm Manager | structured | dict | not bounded | empty at init | daily/weekly | savings + credit outputs | transient + history | dynamic |

#### 2.4 GHG / offset variables

| Variable | Meaning | Units | Data type | Valid range | Initialization | Update frequency | Dependencies | Persistence | Class |
|---|---|---|---|---|---|---|---|---|---|
| `ghg_offset_reported` | offset amount communicated to Environment | mass CO₂e/time or structured offset packet | float/dict | `>=0` | `0` or empty at init | daily/weekly | displaced grid energy and accounting context | persistent history | dynamic |
| `renewable_displacement_flag` | indicates that fossil/grid displacement occurred this tick | bool | bool | `{true,false}` | false | daily/weekly | displaced energy > 0 | persistent history | dynamic |
| `offset_packet_valid` | whether enough data exists to publish offset reliably | bool | bool | `{true,false}` | false | daily/weekly | conversion inputs + valuation context | transient + history | dynamic |

#### 2.5 Calibration variables

| Variable | Meaning | Units | Data type | Valid range | Initialization | Update frequency | Dependencies | Persistence | Class |
|---|---|---|---|---|---|---|---|---|---|
| `feedstock_to_electricity_coeff` | approved FAN electricity coefficient | kWh/ton feedstock | float | approved value `85.73` | initialize from approved plan | static | configuration | persistent | static |
| `heat_conversion_coeff` | coefficient converting biogas/feedstock energy into heat | MJ per input unit | float | not clearly specified | optional external calibration only; no supported default | static | external calibration | persistent | calibration |
| `biogas_volume_to_energy_coeff` | direct m³→kWh conversion if used instead of feedstock route | kWh/m³ | float | not clearly specified | optional external calibration only; no supported default | static | external calibration | persistent | calibration |

#### 2.6 Policy and experiment variables

| Variable | Meaning | Units | Data type | Valid range | Initialization | Update frequency | Dependencies | Persistence | Class |
|---|---|---|---|---|---|---|---|---|---|
| `digester_capacity_percent` | share of manure/feedstock processed under active scenario | % | float | supported experiment values include `0`, `50`, `100` | user/scenario initialization | policy-driven | Farm Manager / experiment state | persistent | dynamic |
| `biogas_investment_active` | whether digester system is active | bool | bool | `{true,false}` | scenario initialization | policy-driven | Farm Manager | persistent | dynamic |
| `energy_generation_active` | whether enough input exists to run conversion | bool | bool | `{true,false}` | false at init | daily/weekly | biogas/feedstock input > 0 | transient + history | dynamic |

#### 2.7 Variables not supported as explicit Energy state

Do not add unless new sources are provided:


* exact digester residence-time dynamics,
* CHP efficiency curve,
* RNG pipeline-sales model,
* exact OPEX/CAPEX amortization terms,
* exact heat-recovery fraction,
* dynamic emissions factor for grid electricity.

### 3. Agent Behaviors and Actions

#### 3.1 Core behaviors

| Behavior | Trigger conditions | Required inputs | State transitions | Outputs | Cooldown / termination |
|---|---|---|---|---|---|
| `ingest_energy_inputs()` | start of energy update | biogas volume, feedstock total, methane content, energy demand | refreshes input state | none directly | each update |
| `validate_conversion_mode()` | after input ingest | conversion mode + available data | selects feasible conversion path | conversion-ready state | each update |
| `compute_electricity_generated()` | if conversion-ready | feedstock total and/or biogas input | updates `electricity_generated_kwh` | electricity output | daily/weekly |
| `compute_heat_generated()` | after electricity conversion | available conversion state | updates `heat_generated_mj` | heat output | daily/weekly |
| `compute_energy_balance()` | after generation | electricity generated, farm demand, optional solar/renewables | updates displaced grid energy, surplus, self-sufficiency | energy-balance state | daily/weekly |
| `compute_energy_cost_saved()` | after balance | displaced grid energy, electricity price | updates `energy_cost_saved_day` | economic output | daily/weekly |
| `compute_ghg_offset_packet()` | after balance | displaced grid energy and offset context | updates `ghg_offset_reported` | offset packet to Environment | daily/weekly |
| `compute_carbon_credits()` | if credit logic active | offset packet, carbon-credit context | updates `carbon_credits_earned` | economic output | daily/weekly |
| `publish_energy_outputs()` | end of update | full energy state | none | packets to Farm Manager and Environment | each update |

#### 3.2 Supported behavioral logic

##### Feedstock-calibrated electricity generation
Approved plan supports:


* replace unspecified/default conversion with:
$$electricity\_generated\_kwh = 85.73 \times digester\_feedstock\_total\_t$$
**Source:** FAN integration calibration in `project-analysis.pdf`.

**Why used:** Converts digester feedstock tonnes to kWh using the approved FAN calibration for Energy and E4 scenarios.


This is the most directly supported conversion in the final architecture.


##### Demand-offset behavior
Supported by the original HTML purpose:


* generated electricity offsets farm grid-energy cost

So the Energy Agent should compute:


* how much internal generation is used against farm demand,
* how much demand remains,
* and whether surplus exists.

##### Carbon-credit / offset behavior
Supported by HTML outputs:


* `carbon credits earned`
* `GHG offset reported`

Supported by approved plan:


* Energy should publish renewable displacement information
* full avoided-emission accounting is finalized in Environment

Therefore Energy should:


* compute displacement packet,
* not own the entire net-farm GHG balance.

#### 3.3 Emergency / failure behaviors

| Behavior | Trigger | Action |
|---|---|---|
| `handle_missing_feedstock()` | no digester feedstock / no biogas input | publish zero generation |
| `handle_invalid_price_context()` | electricity price unavailable | compute physical outputs only; mark economic outputs low confidence |
| `handle_invalid_conversion_path()` | selected conversion mode lacks required data | fall back to supported feedstock-based coefficient if feedstock total exists; otherwise hold output at zero |
| `handle_zero_demand_case()` | farm demand is zero | set self-sufficiency handling explicitly; surplus equals full generation |

#### 3.4 Maintenance behaviors

* maintain generation history,
* maintain self-sufficiency history,
* maintain cost-savings history,
* maintain offset history,
* maintain scenario-level capacity state.

### 4. Decision-Making Logic

The Energy Agent is a **conversion and accounting agent**, not a strategic optimizer.


#### 4.1 Decision architecture

It uses a sequential deterministic decision flow:


1. read available energy input
2. choose feasible conversion path
3. convert to electricity
4. compute heat
5. compare against farm demand
6. compute economic and GHG offset outputs
7. publish packets

#### 4.2 Conversion-path logic

Preferred path under approved architecture:


* use `digester_feedstock_total_t` with FAN coefficient `85.73 kWh/t`

Fallback path:


* if only `biogas_volume_m3` is available, a direct m³→kWh coefficient would be needed, but that coefficient is not clearly specified in the provided resources and the shown form is an implementation assumption used to keep agent interfaces and mass/energy/accounting constraints executable.

Therefore the implementation should prefer the feedstock-based conversion if the Manure Agent publishes total digester feedstock.


#### 4.3 Energy-balance logic

Supported derivation:

$$displaced\_grid\_energy = \min(electricity\_generated\_kwh,\ farm\_energy\_demand)$$
**Source:** architecture-level energy-offset and cost accounting identities; tariff and demand inputs require external calibration.

**Why used:** Caps on-farm renewable use against demand so self-sufficiency and cost-savings KPIs stay internally consistent.


$$surplus\_energy = \max(0,\ electricity\_generated\_kwh - farm\_energy\_demand)$$
**Source:** architecture-level energy-offset and cost accounting identities; tariff and demand inputs require external calibration.

**Why used:** Records generation above farm demand for reporting surplus without double-counting grid offset.


$$energy\_self\_sufficiency\_pct = 100 \times \frac{displaced\_grid\_energy}{farm\_energy\_demand}$$
**Source:** architecture-level energy-offset and cost accounting identities; tariff and demand inputs require external calibration.

**Why used:** Normalizes displaced grid energy to farm demand for dashboard energy-independence metrics.

if demand > 0.


This is directly derivable from:


* HTML inputs/outputs,
* dashboard metric `energy self-sufficiency (%)`,
* and the stated role of offsetting grid energy cost.

#### 4.4 Economic logic

Supported derivation:

$$energy\_cost\_saved\_day = displaced\_grid\_energy \times electricity\_price$$
**Source:** architecture-level energy-offset and cost accounting identities; tariff and demand inputs require external calibration.

**Why used:** Monetizes displaced kWh for Farm Manager economics and circular-investment ROI inputs.


The structure is directly derivable from “offsets grid energy costs.”

The value of `electricity_price` is not clearly specified in the provided resources and this item remains configurable and should be treated as an implementation assumption until a direct source is added.


#### 4.5 GHG-offset logic

Supported derivation:


* renewable generation displaces external grid electricity
* the Energy Agent should publish displacement magnitude
* the Environment Agent should convert this into final avoided-emission accounting

Exact emissions factor for displaced grid electricity is not clearly specified in the provided resources and the shown form is treated as an implementation assumption to keep agent interfaces and mass/energy/accounting constraints executable.


#### 4.6 Unsupported decision logic
Do not implement here without new sources:


* NPV or payback optimization inside Energy Agent,
* real-time electricity arbitrage,
* exact RNG market dispatch,
* storage/battery scheduling,
* detailed CHP dispatch optimization.

Those belong to the Farm Manager Agent or require additional literature.


### 5. Agent Interactions

| Interaction | Direction | Trigger | Exchanged information | Timing / frequency | Impact |
|---|---|---|---|---|---|
| Manure → Energy | incoming | when digestion active | biogas volume, digester feedstock total, methane content | daily/weekly | drives generation |
| Farm Manager Agent → Energy | incoming | scenario/policy changes | digester capacity, investment state, optional economic context | event-driven / weekly | turns energy pathway on/off and contextualizes outputs |
| Market Agent or Farm Manager Agent price context → Energy | incoming | price update | electricity price, credit-price context | daily/weekly/monthly | monetizes energy and offsets |
| Energy → Farm Manager Agent | outgoing | after energy update | kWh generated, heat produced, cost saved, carbon credits, self-sufficiency | daily/weekly | economics and ROI |
| Energy → Environment | outgoing | after energy update | renewable displacement packet, GHG offset report | daily/weekly | avoided-emission accounting |
| optional Energy → Dashboard | outgoing | reporting step | energy KPI packet | daily/weekly | visualization |

#### Synchronization rules

* Energy must run after Manure publishes digester outputs
* Energy must run before Environment finalizes offset accounting
* Farm Manager can consume Energy outputs on weekly or monthly aggregation cadence
* if solar/renewable capacity is included, combined balance should be computed before publishing self-sufficiency

#### Shared variables

* `biogas_volume_m3`
* `digester_feedstock_total_t`
* `electricity_generated_kwh`
* `energy_cost_saved_day`
* `carbon_credits_earned`
* `ghg_offset_reported`

#### Failure-handling logic

* if Manure sends zero feedstock, Energy publishes zero-generation packet
* if price context missing, keep physical outputs and suppress valuation
* if Environment unavailable, persist offset packet for next aggregation step
* if farm demand missing, self-sufficiency and displaced-grid calculations are low confidence

### 6. Environmental Integration

#### Environmental inputs

* none directly from ecology/climate in the current approved architecture
* receives renewable-energy precursor via manure digestion pathway
* may receive exogenous solar/renewable capacity from scenario inputs

#### Environmental outputs

* renewable displacement / GHG-offset packet
* reported internal renewable energy generation
* indirect avoided fossil-energy burden

#### Resource consumption / production
Consumes:


* digester biogas / feedstock-derived energy potential

Produces:


* electricity
* heat
* offset signal to Environment
* economic savings signal to Farm Manager Agent

#### Environmental feedback loops

1. Cow manure → Manure routing → Energy generation → grid displacement → Environment offset
2. Higher digester-capacity scenario → more electricity generation → higher self-sufficiency and carbon-credit potential
3. Energy generation supports E4 biogas-investment scenario and feeds back into Farm Manager Agent policy evaluation

#### Carrying-capacity / system constraints
Energy-conversion behavior inferred from available sources:


* digester-capacity scenario percent constrains available feedstock processing upstream

Exact digester throughput, thermal loss, and conversion efficiency constraints are not clearly specified in the provided resources and the shown form is retained as an implementation assumption so agent interfaces and mass/energy/accounting constraints stay executable.


### 7. Genetic / Evolutionary Logic (If Applicable)

The Energy Agent has no direct genetic or evolutionary logic.


Applicable only indirectly:


* Genetics affects Cow efficiency,
* Cow efficiency affects manure/feedstock quantity and possibly CH₄ profile,
* that changes digester input magnitude,
* but no genetic state is owned here.

### 8. Equations / Algorithms / Thresholds

#### 8.1 Approved FAN conversion coefficient

Supported by the approved plan:

$$electricity\_generated\_kwh = 85.73 \times digester\_feedstock\_total\_t$$
**Source:** FAN integration calibration in `project-analysis.pdf` (85.73 kWh per tonne feedstock).

**Why used:** Converts digester feedstock tonnes to kWh using the approved FAN calibration for Energy and E4 scenarios.


Where:


* `85.73` is the approved FAN-derived calibration coefficient
* `digester_feedstock_total_t` is the total feedstock mass entering the digester

#### 8.2 Energy-balance equations

Supported derived equations:

$$displaced\_grid\_energy = \min(electricity\_generated\_kwh,\ farm\_energy\_demand)$$
**Source:** architecture-level energy-offset and cost accounting identities; tariff and demand inputs require external calibration.

**Why used:** Caps on-farm renewable use against demand so self-sufficiency and cost-savings KPIs stay internally consistent.


$$surplus\_energy = \max(0,\ electricity\_generated\_kwh - farm\_energy\_demand)$$
**Source:** architecture-level energy-offset and cost accounting identities; tariff and demand inputs require external calibration.

**Why used:** Records generation above farm demand for reporting surplus without double-counting grid offset.


If `farm_energy_demand > 0`:

$$energy\_self\_sufficiency\_pct = 100 \times \frac{displaced\_grid\_energy}{farm\_energy\_demand}$$
**Source:** architecture-level energy-offset and cost accounting identities; tariff and demand inputs require external calibration.

**Why used:** Normalizes displaced grid energy to farm demand for dashboard energy-independence metrics.


#### 8.3 Cost-savings equation

Directly derivable from HTML role:

$$energy\_cost\_saved\_day = displaced\_grid\_energy \times electricity\_price$$
**Source:** architecture-level energy-offset and cost accounting identities; tariff and demand inputs require external calibration.

**Why used:** Monetizes displaced kWh for Farm Manager economics and circular-investment ROI inputs.


`electricity_price` numeric value is not clearly specified in the provided resources and this remains configurable and should be treated as an implementation assumption until a direct source is added.


#### 8.4 Carbon-credit logic

Supported structure:

$$carbon\_credits\_earned = ghg\_offset\_reported \times carbon\_credit\_price$$
**Source:** architecture/accounting-layer identity; credit protocol and pricing basis are not clearly specified in provided resources.

**Why used:** Translates reported GHG offset into credit revenue when Energy publishes economic packets to Farm Manager.


However, the exact offset unit, exact carbon-credit price, and exact eligibility rules are not clearly specified in the provided resources and the shown form is an implementation assumption used to keep agent interfaces and mass/energy/accounting constraints executable.


#### 8.5 Heat-output logic

`heat_generated_mj` is an explicit HTML output, but the conversion coefficient is not clearly specified in the provided resources and the shown form is treated as an implementation assumption to keep agent interfaces and mass/energy/accounting constraints executable.


Therefore:


* keep `heat_generated_mj` as an output field,
* compute it only if a calibrated coefficient is supplied,
* otherwise mark it as configured but unavailable.

#### 8.6 Thermochemical energy path (optional)
When Manure publishes a `syngas_to_energy` or pyrolysis-gas packet under the thermochemical route, Energy should treat it as a separate generation source alongside biogas-CHP, using externally calibrated conversion coefficients **(Source:** FAO, 2025, Ch. 3 §3.3.2**)**. If no coefficient is configured, publish the physical packet only and mark economic outputs low-confidence — same rule as `heat_generated_mj`.


#### 8.7 Unsupported exact thresholds
Not clearly specified:


* minimum methane content for feasible generation,
* biogas compression/loss fractions,
* CHP split between electricity and heat,
* grid-emissions factor for offset accounting,
* exact payback and ROI formula terms inside Energy Agent.

### 9. Data Requirements

#### Required datasets / structures

| Dataset | Required fields | Temporal resolution | Use |
|---|---|---|---|
| `manure_energy_packet` | biogas volume, digester feedstock total, methane content | daily/weekly | conversion |
| `farm_energy_context` | farm demand, renewable capacity | daily/weekly | self-sufficiency and displacement |
| `price_context` | electricity price, optional carbon-credit price | daily/weekly/monthly | economic outputs |
| `policy_context` | digester active flag, digester-capacity scenario | event-driven | activation and scenario control |
| `offset_context` | emissions-accounting interface schema | weekly/monthly | Environment packet |

#### External calibration requirements
Need external calibration for:


* heat conversion coefficient,
* direct biogas-volume-to-kWh coefficient if that path is used,
* carbon-credit pricing,
* exact offset factor for displaced electricity.

#### Internally simulatable

* electricity generation from feedstock coefficient,
* self-sufficiency percent,
* displaced-grid energy,
* surplus energy,
* energy-cost savings once price context exists.

#### Missing-data handling

* missing feedstock total: cannot use 85.73 kWh/t conversion
* missing demand: generation can still be computed, but not displacement or self-sufficiency
* missing electricity price: physical outputs only
* missing methane content: retain as informational input unless a methane-content-specific conversion path is used

### 10. Edge Cases / Failure Conditions

| Issue | Detection mechanism | Prevention logic | Fallback / recovery |
|---|---|---|---|
| zero feedstock but positive generation | feedstock/generation inconsistency check | require valid input before conversion | set generation to zero and log error |
| positive demand with missing price | no electricity price | separate physical from economic logic | compute kWh only |
| demand zero causing divide-by-zero self-sufficiency | `farm_energy_demand == 0` | guarded division | self-sufficiency undefined or set via explicit convention |
| double counting offsets | Energy and Environment both finalize same offset | Energy publishes packet only; Environment owns net accounting | schema separation |
| unsupported m³→kWh conversion used accidentally | no coefficient configured | config validation | switch to feedstock-based conversion only |
| negative savings or credits | computed output `<0` | clamp at zero after validation | log anomaly |
| surplus handled as cost savings without demand | surplus exists | separate `surplus_energy_kwh` from displaced-grid energy | only monetize displaced share unless explicit export pricing exists |
| missing carbon-credit price | no price context | physical offset only | publish zero-valued credits and keep offset packet |
| solar/renewable capacity double counted | both digester kWh and solar kWh added without schema | separate source fields | aggregate only in explicit balance function |

### 11. Direct Coding Guidance

#### 11.1 Module structure

Recommended module:


* `agents/energy_agent.py`

Recommended class:


* `class EnergyAgent:`

Recommended substructures:


* `EnergyInputPacket`
* `GenerationState`
* `DemandBalanceState`
* `EconomicState`
* `OffsetPacket`

#### 11.2 Core class outline

```python
class EnergyAgent:
    def __init__(self, config):
        ...
    def ingest_inputs(self, manure_packet, demand_context, price_context=None):
        ...
    def validate_conversion_mode(self):
        ...
    def compute_electricity_generated(self):
        ...
    def compute_heat_generated(self):
        ...
    def compute_energy_balance(self):
        ...
    def compute_cost_savings(self):
        ...
    def compute_offset_packet(self):
        ...
    def compute_carbon_credits(self):
        ...
    def publish_outputs(self):
        ...```

#### 11.3 Update-loop order

Recommended daily/weekly order:


1. ingest Manure digester packet
2. ingest energy-demand and price context
3. validate conversion path
4. compute electricity generated
5. compute heat generated if configured
6. compute displaced demand and surplus
7. compute cost savings
8. compute GHG-offset packet
9. compute carbon credits if pricing exists
10. publish outputs to Farm Manager Agent and Environment

#### 11.4 State-management logic

* keep physical generation separate from economic valuation
* keep offset packet separate from final net-GHG calculation
* keep input-source fields (`feedstock`, `biogas volume`, `methane content`) separate for auditability
* store both generated and displaced energy to avoid over-crediting surplus generation

#### 11.5 Execution priority

* after Manure
* before Environment monthly net-GHG rollup
* before Farm Manager ROI/payback summary
* in weekly cadence if following original architecture recycling step

#### 11.6 Interaction APIs

Incoming:


* `ManureAgent.publish_energy_packet()`
* `FarmManager.get_energy_policy_context()`
* `MarketAgent.get_energy_price_context()`

Outgoing:


* `FarmManager.receive_energy_report(packet)`
* `EnvironmentAgent.receive_energy_offset_packet(packet)`

#### 11.7 Persistence logic
Persist:


* kWh generation history
* heat generation history
* self-sufficiency history
* cost-savings history
* carbon-credit history
* offset packet history

Transient:


* same-tick validation flags
* current anomaly flags
* unpublished offset packet

#### 11.8 Stochastic handling
No explicit stochastic Energy behavior is supported by the provided resources.

Use deterministic conversion unless later sources justify random process losses or uptime variability.


#### 11.9 Extensibility
Safe future extensions:


* explicit heat-use pathway,
* export-to-grid pricing,
* CHP efficiency split,
* storage/battery coupling,
* stronger integration with solar/renewable capacity.

Unsafe without new sources:


* exact CHP thermodynamics,
* detailed RNG market modeling,
* exact capex/opex financing inside Energy Agent,
* dynamic grid-emissions factors.

---

## Agent 6 — 🦠 Disease Agent

*Tag: Health*

### 1. Agent Purpose

The Disease Agent owns **within-herd disease-state evolution**.


The original HTML architecture defines it as an essential agent that:


* simulates disease dynamics using a simplified **SIR** model,
* tracks disease spread across the herd,
* applies productivity penalties,
* tracks mortality,
* and connects health shocks to economic loss.

Its responsibilities are to:


* maintain each cow’s infection compartment,
* update herd-level `S`, `I`, and `R` counts each tick,
* apply disease-driven milk-yield penalties to the Cow Agent,
* generate vet-cost and mortality signals for Farm Manager accounting,
* enforce quarantine flags,
* consume disease-resistance input from the Genetics Agent,
* consume management controls `biosecurity_level` and `vaccination_policy_flag`,
* and optionally consume sensor-triggered disease alerts when the Sensors Agent is active.

Objectives:


* represent outbreak dynamics at herd scale without introducing unsupported pathogen-specific submodels,
* expose disease costs and milk-loss consequences,
* connect genetics, management, and stress into disease outcomes,
* support the HTML E3 shock experiment: `introduce mastitis/FMD at tick 100; vary biosecurity levels (0–100%)`.

Subsystem ownership:


* epidemiological state,
* outbreak injection and persistence,
* quarantine control flags,
* disease-related yield penalties,
* disease-related vet-cost and mortality accounting.

Dependencies:


* Genetics Agent for disease-resistance trait / resistance index,
* Cow Agent or shared health/feed context for stress signal,
* Farm Manager for `biosecurity_level` and `vaccination_policy_flag`,
* optional Sensors Agent for thermal mastitis alert,
* scenario controller for outbreak shock timing and disease label.

Constraints:


* the HTML architecture specifies a **simplified SIR** model; pathogen-specific clinical progression is not specified,
* the tree view mentions `SIR/SEIR`, but the detailed agent card specifies simplified `SIR`; use `SIR` as the default implementation,
* exact transmission, recovery, mortality, quarantine-effect, and vaccination-effect coefficients are **not clearly specified in the provided resources and the shown form is retained as an implementation assumption so interfaces and accounting constraints stay executable**,
* disease-specific differences between `mastitis` and `FMD` beyond scenario labeling and outbreak injection are **not clearly specified in the provided resources and remain configurable as an implementation assumption until a direct source is added**.

Expected outputs:


* `infection_status_per_cow`
* `milk_yield_reduction_pct`
* `vet_cost_per_event`
* `quarantine_flag`
* `herd_immunity_status`
* `mortality_rate`
* herd epidemiology dashboard metrics:
* `susceptible_count`
* `infected_count`
* `recovered_count`
* `days_to_herd_immunity`
* `outbreak_economic_cost`

Contribution to global system behavior:


* creates the disease-economics-biosecurity loop from the HTML workflow,
* propagates health shocks into Cow productivity and mortality,
* provides Farm Manager with health-risk information for policy response,
* sends outbreak frequency context back to Genetics so annual selection can reweight health traits.

### 2. Agent State Variables

#### 2.1 Core herd epidemiology state


* `infection_state[cow_id]`: per-cow disease compartment; units none; enum; valid range `{S, I, R}`; initialize all cows to `S` unless shock seeding is active; update daily; depends on outbreak logic; persistent; dynamic.
* `susceptible_count`: current count of susceptible cows; units cows; integer; valid range `0..herd_size`; initialize to herd size; update daily; derived from `infection_state`; persistent history; dynamic.
* `infected_count`: current count of infected cows; units cows; integer; valid range `0..herd_size`; initialize `0`; update daily; derived from `infection_state`; persistent history; dynamic.
* `recovered_count`: current count of recovered cows; units cows; integer; valid range `0..herd_size`; initialize `0`; update daily; derived from `infection_state`; persistent history; dynamic.
* `mortality_count`: cumulative deaths attributed to disease; units cows; integer; valid range `>=0`; initialize `0`; update daily; depends on infected-state transitions; persistent; dynamic.
* `mortality_rate`: disease-attributed mortality rate; units `%` or fraction per reporting period; float; valid range `0–100%`; initialize `0`; update daily/weekly; depends on `mortality_count` and herd denominator; persistent history; dynamic.

#### 2.2 Per-cow progression and penalty state


* `days_infected[cow_id]`: duration since infection started; units days/ticks; integer; valid range `>=0`; initialize `0`; update daily for infected cows; persistent; dynamic.
* `quarantine_flag[cow_id]`: whether the cow is isolated or movement-restricted; bool; valid range `{true,false}`; initialize `false`; update daily; depends on infection state and policy rules; persistent history; dynamic.
* `yield_penalty_pct[cow_id]`: disease-imposed milk reduction to be sent to Cow Agent; units `%`; float; valid range `0–100%`; initialize `0`; update daily; depends on infection state and disease severity mapping; persistent history; dynamic.
* `vet_cost_event[cow_id]`: cost accrued when the cow experiences a disease event; units currency/event; float; valid range `>=0`; initialize `0`; update on event; depends on infection transitions and treatment policy; persistent history; dynamic.
* `disease_death_flag[cow_id]`: terminal mortality outcome this tick; bool; initialize `false`; update daily; depends on infected-state mortality logic; transient + history; dynamic.

#### 2.3 Incoming management and host-condition state


* `disease_resistance_index[cow_id]`: inherited resistance signal received from Genetics; units not clearly specified; numeric; valid range not clearly specified; initialize from Genetics output; update annually or when new animals enter; persistent; inherited/dynamic.
* `biosecurity_level_pct`: user-controlled transmission-rate modifier; units `%`; float; valid range `0–100%`; initialize from scenario/user input; update when policy changes; persistent; dynamic.
* `vaccination_policy_flag`: disease-control policy flag from management; bool; valid range `{true,false}`; initialize from scenario/user input; update on policy changes; persistent; dynamic.
* `stress_level[cow_id]`: feed/health stress signal used as disease-risk modifier; units not clearly specified; numeric; valid range not clearly specified; initialize from Cow/shared state; update daily; persistent history; dynamic.
* `herd_density`: crowding/contact-pressure input; units not clearly specified in the provided resources; numeric; valid range `>=0`; initialize from herd-size and farm-space context; update when herd size or housing context changes; persistent; dynamic.
* `thermal_mastitis_signal[cow_id]`: optional event-level sensor alert from Sensors Agent; bool or score; valid range depends on sensor schema; initialize null/false; update on event; transient + history; dynamic.

#### 2.4 Outbreak scenario state


* `outbreak_shock_active`: whether an exogenous outbreak experiment is enabled; bool; initialize from experiment config; persistent; dynamic.
* `outbreak_tick`: scheduled tick for shock introduction; units tick index; integer; supported value explicitly shown in HTML experiment `100`; initialize from experiment config; persistent; static/dynamic.
* `outbreak_disease_label`: disease label used by E3 scenario; enum; valid supported labels `{mastitis, FMD}` from the HTML experiment text; initialize from scenario; persistent; dynamic.
* `seed_infection_count`: number of cows infected at outbreak start; units cows; integer; valid range `>=0`; initialization required by scenario; exact default not clearly specified in the provided resources; persistent; dynamic.
* `outbreak_active_flag`: whether infection is currently present in herd; bool; initialize `false`; update daily; derived from `infected_count > 0`; persistent history; dynamic.
* `outbreak_start_tick`: tick when current outbreak began; integer or null; initialize null; update on first nonzero infection event; persistent; dynamic.
* `outbreak_end_tick`: tick when outbreak resolves; integer or null; initialize null; update when `infected_count` returns to `0`; persistent; dynamic.
* `outbreak_duration_ticks`: duration from start to resolution; units ticks; integer; valid range `>=0`; initialize `0`; update on resolution; persistent history; dynamic.

#### 2.5 Economic and reporting state


* `outbreak_economic_cost`: cumulative disease-related cost; units currency; float; valid range `>=0`; initialize `0`; update daily/weekly; depends on vet costs, mortality losses, and milk-loss valuation if implemented; persistent; dynamic.
* `milk_loss_due_to_disease_pct`: herd-level productivity loss metric; units `%`; float; valid range `0–100%`; initialize `0`; update daily/weekly; derived from cow penalties; persistent history; dynamic.
* `herd_immunity_status`: reporting field required by HTML outputs; structured or nullable categorical; exact threshold logic not clearly specified in the provided resources; initialize null/unknown; update daily/weekly; persistent history; dynamic.
* `days_to_herd_immunity`: dashboard metric in HTML; integer or null; initialize null; update only if a herd-immunity threshold is configured; persistent history; dynamic.
* `vaccination_coverage_needed_pct`: dashboard metric listed in HTML; float or null; exact formula not clearly specified in the provided resources; initialize null; update when epidemiological threshold model exists; persistent history; derived placeholder.

#### 2.6 Calibration and control parameters


* `base_transmission_rate`: baseline infection-spread parameter for simplified SIR; units per tick; float; valid range `>=0`; must be externally calibrated; initialize from config; persistent; calibration.
* `recovery_rate`: infected-to-recovered transition parameter; units per tick; float; valid range `>=0`; externally calibrated; initialize from config; persistent; calibration.
* `disease_mortality_rate`: infected-to-death transition parameter; units per tick; float; valid range `>=0`; externally calibrated; initialize from config; persistent; calibration.
* `biosecurity_modifier_function`: function or lookup that converts `biosecurity_level_pct` into a transmission modifier; exact formula not clearly specified; initialize from config; persistent; calibration.
* `vaccination_modifier_function`: function that reduces susceptibility or transmission when `vaccination_policy_flag=true`; exact formula not clearly specified; initialize from config; persistent; calibration.
* `stress_modifier_function`: function mapping stress to increased disease risk; exact formula not clearly specified; initialize from config; persistent; calibration.
* `resistance_modifier_function`: function mapping inherited disease resistance to reduced disease risk and/or mortality; exact formula not clearly specified; initialize from config; persistent; calibration.
* `quarantine_effect_function`: function reducing effective contact when `quarantine_flag=true`; exact value not clearly specified; initialize from config; persistent; calibration.

### 3. Agent Behaviors and Actions

#### 3.1 Normal behaviors


* `initialize_herd_epidemiology()`
* Trigger: simulation start or herd reset.
* Inputs: herd roster.
* Action: assigns all cows to `S`, clears infection histories, zeroes costs and mortality.
* Output: clean disease-state store.


* `ingest_management_controls()`
* Trigger: start of daily disease update.
* Inputs: `biosecurity_level_pct`, `vaccination_policy_flag`.
* Action: refreshes policy modifiers for this tick.
* Output: updated transmission context.


* `ingest_host_signals()`
* Trigger: daily.
* Inputs: `disease_resistance_index`, `stress_level`, `herd_density`, optional `thermal_mastitis_signal`.
* Action: assembles risk inputs before state transition.
* Output: per-cow risk context.


* `update_transmission_pressure()`
* Trigger: daily after ingest.
* Inputs: infected prevalence, density, biosecurity, vaccination, stress, resistance, quarantine effect.
* Action: computes effective infection pressure for susceptible cows.
* Output: transmission context for S→I transitions.


* `advance_SIR_state()`
* Trigger: daily.
* Inputs: current compartment state plus calibrated transition logic.
* Action: executes `S→I`, `I→R`, and infected-to-death removal.
* Output: new per-cow compartment states and herd counts.


* `apply_quarantine_rules()`
* Trigger: after infection-state update.
* Inputs: current infection state, management policy.
* Action: sets `quarantine_flag` for infected cows under the active rule set.
* Output: per-cow quarantine flags.


* `apply_productivity_penalties()`
* Trigger: after disease-state update.
* Inputs: infection state, disease severity mapping if configured.
* Action: computes `yield_penalty_pct[cow_id]`.
* Output: penalty packet to Cow Agent.


* `accumulate_disease_costs()`
* Trigger: after state and penalties update.
* Inputs: new infections, treatment events, mortality events.
* Action: computes per-event and cumulative disease cost.
* Output: `vet_cost_event`, `outbreak_economic_cost`.


* `publish_outputs()`
* Trigger: end of daily update.
* Outputs:
* to Cow: infection status, yield penalty, quarantine, mortality signal
* to Farm Manager Agent: outbreak size, milk loss, vet cost, mortality rate
* to Genetics: outbreak-frequency signal for annual breeding reweighting
* to dashboard/reporting: S/I/R counts, outbreak duration, herd-immunity tracking

#### 3.2 Adaptive / event-driven behaviors


* `inject_outbreak_shock()`
* Trigger: if E3 scenario active and current tick equals `outbreak_tick`.
* Inputs: `outbreak_disease_label`, `seed_infection_count`.
* Action: infects a scenario-defined initial set of cows.
* Output: outbreak start.
* Supported detail: HTML specifies `tick 100` and scenario labels `mastitis/FMD`.
* Unsupported detail: exact seeding count and cow-selection rule are not clearly specified.


* `sensor_assisted_case_flagging()`
* Trigger: when `thermal_mastitis_signal` arrives from Sensors Agent.
* Inputs: sensor alert, current cow state.
* Action: marks cow as high-risk or candidate case for Disease evaluation.
* Output: event log / optional escalation.
* Constraint: sensor alert should not silently overwrite infection state unless the user explicitly chooses that integration rule, because the exact fusion rule is not clearly specified.


* `notify_outbreak_severity()`
* Trigger: outbreak active and severity crosses reporting threshold.
* Inputs: infected prevalence, cost, duration.
* Action: publishes `disease_frequency_signal` to Genetics and policy alert to Farm Manager Agent.
* Output: cross-agent adaptation.
* Threshold values are not clearly specified.

#### 3.3 Failure-state behaviors


* `handle_empty_herd()`: if herd size is zero, skip disease transitions and publish zero counts.
* `handle_invalid_compartment_state()`: if any cow has state outside `{S,I,R}`, reset that cow to last valid state and log error.
* `handle_duplicate_shock_injection()`: prevent repeated seeding at the same outbreak tick.
* `handle_missing_resistance_signal()`: if Genetics data missing, use neutral modifier and mark low-confidence disease update.
* `handle_missing_stress_signal()`: default to neutral stress effect and log warning.
* `handle_unresolved_outbreak()`: if outbreak never resolves within simulation horizon, preserve active outbreak state and keep `days_to_herd_immunity = null`.

### 4. Decision-Making Logic

The Disease Agent uses a **deterministic/stochastic compartment update architecture** centered on simplified SIR logic.


#### 4.1 Priority order


1. read management controls
2. read host susceptibility and stress signals
3. inject exogenous outbreak if scenario requires
4. compute effective transmission pressure
5. update per-cow infection state
6. apply quarantine
7. apply yield penalties and mortality
8. accumulate economic losses
9. publish herd metrics and cross-agent signals

#### 4.2 Core decision factors

Transmission risk is allowed to depend on the exact inputs defined by the HTML card:


* disease resistance trait
* herd density
* biosecurity level
* vaccination policy flag
* stress level

This means the decision architecture should treat disease spread as a base transmission process modulated by:


* contact pressure from currently infected animals,
* crowding,
* management protection,
* host susceptibility,
* and stress.

#### 4.3 Constraint handling


* `biosecurity_level_pct` is the only management control explicitly defined as a transmission-rate modifier in the HTML parameter table.
* `vaccination_policy_flag` is explicitly an input, but the exact functional impact is not specified; implement as a configurable modifier, not a hardcoded coefficient.
* `disease_resistance_index` is an inherited host modifier, but the exact mapping from Genetics score to infection susceptibility is not specified; implement as a configurable multiplier.
* `stress_level` increases disease risk conceptually through the provided inputs, but no exact formula is provided; implement as a configurable risk multiplier.

#### 4.4 Conflict-resolution logic

If multiple protective and harmful signals are present simultaneously:


* apply all as ordered modifiers to effective transmission risk,
* keep modifier order explicit in code,
* and record each modifier in the daily disease log for auditability.

Recommended order:


1. base transmission
2. herd-density effect
3. biosecurity reduction
4. vaccination reduction
5. stress increase
6. genetic-resistance reduction
7. quarantine contact reduction

The exact numerical composition rule is not clearly specified; multiplication is a safe default implementation pattern, but it remains a calibration choice.


### 5. Agent Interactions

#### Incoming dependencies


* Genetics → Disease
* Frequency: annual and at animal entry.
* Data: disease-resistance index.
* Impact: modifies susceptibility and possibly recovery/mortality.
* Supported by HTML and approved interaction map.


* Farm Manager → Disease
* Frequency: policy change / scenario setup.
* Data: `biosecurity_level_pct`, `vaccination_policy_flag`.
* Impact: transmission-rate modifier and prevention policy context.


* Cow / shared health-feed context → Disease
* Frequency: daily.
* Data: stress level.
* Impact: raises or lowers disease risk.
* Exact ownership of stress signal is not fully specified; treat it as an incoming shared state.


* Sensors → Disease
* Frequency: on event.
* Data: thermal mastitis signal.
* Impact: optional case flagging or alerting.
* Supported by the approved plan; exact fusion rule not clearly specified.


* Scenario controller → Disease
* Frequency: event-based.
* Data: outbreak shock activation, `tick 100`, disease label.
* Impact: seeds exogenous outbreak for E3.

#### Outgoing dependencies


* Disease → Cow
* Frequency: daily.
* Data: infection state, yield penalty, quarantine flag, mortality signal.
* Impact: changes milk output and cow health status.


* Disease → Farm Manager
* Frequency: daily/weekly.
* Data: vet cost, outbreak size, milk loss, mortality rate, outbreak duration.
* Impact: economic loss calculation and policy response.


* Disease → Genetics
* Frequency: on outbreak / periodic summary.
* Data: disease-frequency signal.
* Impact: annual breeding reweight toward health traits.

#### Synchronization rules


* Disease must run before final Cow milk-output calculation for the tick, because disease determines yield penalties (implementation assumption).
* Disease should run after policy updates from Farm Manager Agent are available (implementation assumption).
* Genetics resistance values can be cached for the year and refreshed on annual breeding/update events (implementation assumption).
* Sensor alerts can be processed before or during daily disease update, but should be timestamped and not applied retroactively (implementation assumption).

#### Feedback loops


* Disease → Cow → Farm Manager → biosecurity policy → Disease
* Disease → Farm Manager → Genetics weighting → future resistance → Disease
* Sensors → Disease → Cow/Farm Manager

### 6. Environmental Integration

The Disease Agent has **no primary environmental ownership** in the provided resources.


Environmental coupling is indirect:


* disease lowers milk output,
* reduced milk output can worsen environmental intensity per litre,
* mortality changes herd structure and resource use,
* outbreak-related stress may affect overall farm efficiency.

Direct environmental outputs such as CH4, N2O, water use, or land effects are not assigned to Disease in the provided resources.


Implementation rule:


* Disease should publish milk-loss and mortality signals,
* Environment may consume those signals indirectly when normalizing emissions intensity,
* but Disease should not calculate GHG directly.

Climate-driven disease effects, pathogen survival in environment, or spatial pathogen spread are **not clearly specified in the provided resources and remain configurable as an implementation assumption until a direct source is added**.


### 7. Genetic / Evolutionary Logic (If Applicable)

The Disease Agent does not own breeding, mutation, crossover, or generational genetics.


Supported genetic logic is limited to:


* receiving inherited disease-resistance signal from Genetics,
* using that signal as a host modifier in infection outcomes,
* publishing outbreak-frequency information back to Genetics so breeding priorities can shift toward health.

The following are not clearly specified and should not be invented:


* exact genomic architecture of disease resistance,
* mutation rules,
* multi-locus disease genetics,
* explicit inheritance equations inside Disease.

### 8. Equations / Algorithms / Thresholds

#### 8.1 Herd-level simplified SIR update

The minimal compartment update consistent with the HTML architecture is:


$$S_{t+1} = S_t - new\_infections_t$$
**Source:** SIR-style compartment structure for disease module; explicit coefficientized model in project files is an implementation assumption.

**Why used:** Supports the agent output and accounting interface named in the surrounding section; no additional coefficients are introduced here.


$$I_{t+1} = I_t + new\_infections_t - recoveries_t - deaths_t$$
**Source:** SIR-style compartment structure for disease module; explicit coefficientized model in project files is an implementation assumption.

**Why used:** Supports the agent output and accounting interface named in the surrounding section; no additional coefficients are introduced here.


$$R_{t+1} = R_t + recoveries_t$$
**Source:** SIR-style compartment structure for disease module; explicit coefficientized model in project files is an implementation assumption.

**Why used:** Supports the agent output and accounting interface named in the surrounding section; no additional coefficients are introduced here.


Where:


* `deaths_t` removes animals from active herd state,
* `new_infections_t`, `recoveries_t`, and `deaths_t` are generated from per-cow transition logic.

#### 8.2 Effective transmission structure

A supported implementation form is:


$$transmission\_pressure_t = f(I_t/N_t,\ herd\_density,\ biosecurity,\ vaccination,\ stress,\ resistance,\ quarantine)$$
**Source:** architecture input-set synthesis for disease pressure; exact coefficient/form not provided in sources.

**Why used:** Combines infection prevalence and control inputs into daily new-infection pressure for the SIR update.


Because the HTML explicitly states:


* biosecurity modifies transmission rate,
* disease resistance is an input,
* herd density is an input,
* vaccination is an input,
* stress level is an input.

Exact functional form and coefficient values are **not clearly specified in the provided resources and the shown form is an implementation assumption used to keep interfaces and accounting constraints executable**.


#### 8.3 Per-cow infection decision

For each susceptible cow:


* evaluate current exposure context,
* compute infection probability or deterministic threshold from `transmission_pressure_t`,
* transition `S→I` if the infection event occurs.

The exact stochastic draw rule is not clearly specified. A Bernoulli process is the standard ABM implementation, but that remains a modeling choice rather than a resource-defined requirement.


#### 8.4 Recovery and mortality

For each infected cow:


* increment `days_infected`,
* evaluate recovery event,
* evaluate mortality event,
* otherwise remain infected.

Exact values for:


* recovery probability,
* disease mortality probability,
* disease-duration threshold

are **not clearly specified in the provided resources and remain configurable as an implementation assumption until a direct source is added**.


#### 8.5 Quarantine logic

Supported by the architecture:


* quarantine rules exist,
* quarantine flag is an output.

Implementation-safe rule:


* infected cows may receive `quarantine_flag=true`,
* quarantine reduces effective contact or exposure pressure.

Exact quarantine effectiveness is **not clearly specified in the provided resources and the shown form is treated as an implementation assumption to keep interfaces and accounting constraints executable**.


#### 8.6 Yield-penalty logic

Supported by HTML:


* Disease outputs `milk yield reduction (%)`.

Implementation-safe rule:


* infected cows receive a nonzero `yield_penalty_pct`,
* susceptible and recovered cows default to zero unless a persistent penalty is explicitly configured.

Exact penalty magnitude by disease or day-in-state is **not clearly specified in the provided resources and the shown form is retained as an implementation assumption so interfaces and accounting constraints stay executable**.


#### 8.7 Experiment-specific threshold

The only explicit numerical disease experiment threshold provided is:


* E3 outbreak introduced at `tick 100`.

Use that directly for the outbreak-shock scenario.


#### 8.8 Validation benchmark

The HTML experiment table states:


* high biosecurity + genetically resistant herd reduces outbreak duration and financial loss by `>40%`.

This is a **validation expectation**, not a hardcoded equation.


### 9. Data Requirements

Required data structures:


* herd roster with persistent cow IDs
* per-cow infection compartment store
* per-cow disease-resistance index from Genetics
* per-cow stress signal from Cow/shared state
* herd-density context
* management policy context: `biosecurity_level_pct`, `vaccination_policy_flag`
* scenario context for outbreak shock: active flag, tick, disease label, seed count
* optional sensor event stream for mastitis alerts
* valuation context for vet costs and milk-loss monetization

Temporal resolution:


* daily tick for disease-state update is supported by the approved architecture.
* weekly/monthly aggregation for dashboard KPIs and Farm Manager reporting.

Spatial resolution:


* herd-level mixing structure is supported.
* pen-level, barn-level, or distance-based contact networks are not clearly specified.

Calibration datasets needed from real data or scenario assumptions:


* base transmission rate,
* recovery rate,
* mortality rate,
* disease-specific milk-loss curve,
* quarantine effectiveness,
* vaccination effect size,
* biosecurity effect size,
* vet cost per event.

Internally simulatable without external calibration:


* compartment bookkeeping,
* outbreak timing,
* S/I/R counts,
* cost accumulation logic,
* reporting structure.

Missing-data handling:


* if resistance data missing, use neutral modifier and flag confidence issue,
* if stress missing, use neutral modifier,
* if herd-density missing, use neutral mixing assumption,
* if cost data missing, keep epidemiology active and output physical-health metrics only.

### 10. Edge Cases / Failure Conditions


* `herd_size = 0`
* Detection: no cows in roster.
* Prevention: skip transition loop.
* Recovery: publish zero counts and zero costs.


* invalid compartment totals
* Detection: `S + I + R + deaths_this_tick` inconsistent with live herd count.
* Prevention: recompute counts from per-cow state after each update.
* Recovery: overwrite aggregate counts from per-cow truth.


* outbreak shock fires twice
* Detection: `current_tick == outbreak_tick` and `shock_already_applied=true`.
* Prevention: one-shot scenario flag.
* Recovery: reject duplicate seeding.


* all cows quarantined but transmission still rises
* Detection: infected prevalence increasing despite full quarantine.
* Prevention: verify quarantine effect path.
* Recovery: log calibration issue; maintain simulation but mark outbreak dynamics for review.


* mortality without infected state
* Detection: death event on cow not in `I`.
* Prevention: guard transition order.
* Recovery: reject event and log error.


* sensor false positive
* Detection: mastitis alert on cow remaining clinically negative.
* Prevention: treat sensor input as alert, not automatic compartment overwrite.
* Recovery: expire alert after configurable review period.


* herd immunity status undefined
* Detection: no configured immunity threshold.
* Prevention: separate `recovered_count` from threshold-based immunity metric.
* Recovery: publish `herd_immunity_status = null/unknown`.


* vaccination KPI requested but no formula available
* Detection: dashboard asks for `vaccination_coverage_needed_pct`.
* Prevention: require configured epidemic threshold method.
* Recovery: publish null and label as not clearly specified.


* computational bottleneck at large herd size
* Detection: disease loop runtime dominates daily tick.
* Prevention: vectorize state arrays or pre-group by compartment.
* Recovery: switch from object-per-cow transitions to indexed arrays while preserving per-cow IDs.

### 11. Direct Coding Guidance

Recommended module:


* `agents/disease_agent.py`

Recommended class structure:


* `DiseaseAgent`
* `DiseaseStateStore`
* `DiseasePolicyContext`
* `DiseaseReportPacket`

Recommended internal state layout:


* per-cow arrays or dictionaries for:
* `infection_state`
* `days_infected`
* `quarantine_flag`
* `yield_penalty_pct`
* herd-level cached summaries for:
* `S`, `I`, `R`
* outbreak timing
* cumulative costs
* mortality

Recommended update-loop order per daily tick:


1. receive Farm Manager disease policy context
2. receive Genetics resistance values
3. receive Cow/shared stress values
4. receive optional sensor alerts
5. inject scheduled outbreak if E3 active
6. compute effective transmission context
7. update `S→I`
8. update infected progression `I→R` and `I→death`
9. apply quarantine flags
10. compute yield penalties and mortality outputs
11. accumulate vet cost and outbreak economic cost
12. refresh herd-level metrics
13. publish packets to Cow, Farm Manager, Genetics, and dashboard layer

Recommended APIs:


* `receive_policy_context(biosecurity_level_pct, vaccination_policy_flag)`
* `receive_host_signals(resistance_map, stress_map, herd_density)`
* `receive_sensor_alerts(alert_packet)`
* `seed_outbreak(outbreak_disease_label, seed_infection_count)`
* `step(current_tick)`
* `publish_cow_health_packet()`
* `publish_manager_report()`
* `publish_genetics_feedback()`

Execution priority:


* after Farm Manager Agent policy refresh,
* before Cow milk-output finalization,
* before Farm Manager Agent daily economic rollup,
* before annual Genetics reweighting summary is compiled.

Persistence logic:


* persist per-cow state across ticks,
* persist outbreak history for experiment analysis,
* persist daily `S/I/R` counts for dashboard plots,
* persist cumulative cost and mortality histories for E3 comparison.

Stochastic handling:


* use a seeded random generator if per-cow infection transitions are probabilistic,
* store the run seed with experiment metadata so outbreak trajectories are reproducible.

Extensibility-safe additions:


* pathogen-specific parameter sets,
* pen-level contact networks,
* recovery-with-loss states,
* sensor-confirmed subclinical disease states.

Do not add without new sources:


* pathogen-environment survival,
* explicit SEIR latent period,
* treatment-protocol optimization,
* antimicrobial-resistance modeling,
* detailed vaccination coverage optimization,
* pathogen-specific clinical thresholds.

---

## Agent 7 — 🌍 Environment Agent

*Tag: System*

### 1. Agent Purpose

The Environment Agent owns the farm’s **environmental accounting layer**.


The original HTML architecture defines it as the agent that:


* aggregates environmental outputs across agents,
* tracks total GHG emissions `(CH₄, N₂O, CO₂)`,
* tracks soil carbon sequestration,
* tracks water use,
* and produces the farm’s net environmental impact score and progress toward net-zero targets.

Its responsibilities are to:


* receive environmental sub-streams from operational agents,
* keep a global GHG ledger,
* separate major emission pathways instead of lumping them,
* compute farm-level environmental KPIs,
* apply avoided-emission corrections from biogas and digestate substitution,
* normalize total impact by milk output,
* and publish monthly sustainability results to the Farm Manager Agent and dashboard.

Subsystem ownership:


* environmental aggregation,
* GHG sub-accounting,
* net carbon balance,
* emission intensity metrics,
* carbon-credit-ready offset accounting,
* sustainability KPI publication.

Objectives:


1. aggregate positive emission streams without double counting,
2. apply negative avoided-emission terms required by the approved FAN integration,
3. compute `GHG intensity (kg CO₂e/litre milk)`,
4. compute `net carbon balance`,
5. publish `carbon credits` and `sustainability score`,
6. keep soil carbon and optional water-use accounting tied to the same reporting layer.

Dependencies:


* Cow Agent: enteric CH₄ and milk-output denominator context
* Manure Agent: storage CH₄ and field N₂O precursor / manure-related emission packet
* Feed / Crop Agent: soil carbon delta, synthetic fertilizer requirement or savings context
* Energy Agent: GHG offset / renewable-displacement packet
* Water Agent: water-use packet if active
* Farm Manager Agent: consumes monthly KPIs, may provide policy/reporting thresholds
* optional Genetics Agent signal: annual CH₄ attribution factor via `RFI_fat`, for reporting alignment only

Constraints supported by the resources:


* the plan explicitly says Environment remains the aggregator and should gain **sub-accounts, not child agents**
* the paper-derived plan explicitly requires splitting the lumped GHG bucket into at least:
* enteric CH₄,
* manure-storage CH₄,
* manure-related N₂O / field-application N₂O
* the approved plan marks **avoided-emission GHG terms** as an urgent correctness fix:
* biogas displacing grid electricity,
* digestate displacing synthetic fertilizer
* exact emission-factor coefficients for these avoided terms are **not clearly specified in the provided resources and the shown form is an implementation assumption used to keep interfaces and accounting constraints executable**
* the exact formula for `sustainability score (0–100)` is **not clearly specified in the provided resources and the shown form is treated as an implementation assumption to keep interfaces and accounting constraints executable**
* the exact formula for `soil biodiversity index` is **not clearly specified in the provided resources and the shown form is retained as an implementation assumption so interfaces and accounting constraints stay executable**
* direct CO₂ source accounting is named in the HTML, but source-specific CO₂ mechanisms are **not clearly specified in the provided resources and remain configurable as an implementation assumption until a direct source is added**

Expected outputs:


* `total_ghg_score_co2e_per_litre_milk`
* `net_carbon_balance`
* `soil_biodiversity_index`
* `carbon_credits`
* `sustainability_score_0_100`
* optional `emission_intensity_kg_co2e_per_kg_protein`
* optional `water_use_l_per_litre_milk`
* monthly environmental report packet to Farm Manager and dashboard

Contribution to global system behavior:


* closes the farm-level environmental ledger,
* prevents manure, feed, and energy benefits from being misreported,
* makes E1, E4, and E5 experiments comparable on a common KPI layer,
* and converts mechanistic chains from other agents into whole-farm sustainability outputs.

Why this agent exists:


* it is explicitly essential in the original HTML architecture,
* the approved plan assigns the global GHG ledger to Environment,
* Herrero-derived analysis justifies sub-stream separation and emission-intensity tracking,
* and the approved FAN integration assigns avoided-emission corrections directly to Environment.

### 2. Agent State Variables

#### 2.1 Core GHG ledger variables


* `enteric_ch4_co2e`: enteric CH₄ contribution received from Cow; units `kg CO₂e / tick` or `kg CO₂e / month`; type `float`; valid range `>=0`; initialize `0`; update daily then aggregate monthly; depends on Cow outputs and milk-production state; interacts with `gross_ghg_co2e`; persists in source ledger; dynamic.
* `manure_storage_ch4_co2e`: CH₄ from manure storage / lagoon; units `kg CO₂e / tick`; type `float`; valid range `>=0`; initialize `0`; update daily from Manure; interacts with `gross_ghg_co2e`; persistent; dynamic.
* `field_n2o_co2e`: N₂O from manure application / field-emission pathway; units `kg CO₂e / tick`; type `float`; valid range `>=0`; initialize `0`; update daily or weekly from Manure and/or Feed/Crop environmental packet; interacts with `gross_ghg_co2e`; persistent; dynamic.
* `other_positive_ghg_co2e`: optional positive emission bucket for any additional explicitly supplied stream; units `kg CO₂e / tick`; type `float`; valid range `>=0`; initialize `0`; update only if another agent provides a supported packet; persistent; dynamic.
* `gross_ghg_co2e`: sum of positive GHG streams before avoided-emission subtraction; units `kg CO₂e / month`; type `float`; valid range `>=0`; initialize `0`; update monthly; depends on all positive subaccounts; persistent history; dynamic.
* `global_ghg_ledger`: source-tagged ledger keyed by stream and period; units structured packet; type `dict/list`; valid range not bounded; initialize empty; update daily/monthly; depends on all incoming packets; persists for auditability; dynamic.

#### 2.2 Avoided-emission and offset variables


* `avoided_grid_emissions_co2e`: negative GHG term from biogas displacing grid electricity; units `kg CO₂e / period`; type `float`; valid range `>=0`; initialize `0`; update weekly/monthly; depends on Energy displacement packet and configured emissions factor; persistent; dynamic.
* `avoided_synthetic_fertilizer_co2e`: negative GHG term from digestate substituting synthetic fertilizer; units `kg CO₂e / period`; type `float`; valid range `>=0`; initialize `0`; update weekly/monthly; depends on digestate use / fertilizer-saved packet and configured substitution factor; persistent; dynamic.
* `total_avoided_ghg_co2e`: sum of all validated negative terms; units `kg CO₂e / period`; type `float`; valid range `>=0`; initialize `0`; update monthly; depends on avoided-emission subaccounts; persistent; dynamic.
* `energy_offset_packet`: raw packet from Energy Agent containing renewable-displacement context; units structured; type `dict`; initialize empty; update weekly; persists for audit trail; dynamic.
* `fertilizer_substitution_packet`: raw packet from Feed/Crop or Manure/Crop interface describing digestate-driven fertilizer displacement; units structured; type `dict`; initialize empty; update weekly/monthly; persists; dynamic.
* `offset_validation_flag`: whether enough information exists to convert raw offset packets into valid negative GHG terms; type `bool`; initialize `false`; update when packets arrive; transient + history; dynamic.

#### 2.3 Carbon balance and intensity variables


* `net_ghg_co2e`: net GHG after subtracting avoided terms; units `kg CO₂e / period`; type `float`; valid range can be positive, zero, or negative; initialize `0`; update monthly; depends on `gross_ghg_co2e` and `total_avoided_ghg_co2e`; persistent history; dynamic.
* `net_carbon_balance`: farm-level net carbon result reported by HTML output; units `kg CO₂e / period`; type `float`; valid range not bounded above or below; initialize `0`; update monthly; operationally same ledger result as `net_ghg_co2e` unless a wider carbon-stock method is later configured; persistent history; dynamic.
* `milk_output_litres`: milk denominator used for normalization; units `L / period`; type `float`; valid range `>=0`; initialize `0`; update daily then aggregate monthly; depends on Cow outputs; persistent history; dynamic.
* `ghg_intensity_kg_co2e_per_litre`: environmental KPI listed in HTML dashboard; units `kg CO₂e / litre milk`; type `float`; valid range `>=0` if defined; initialize `0` or `null` when denominator absent; update monthly; depends on `net_ghg_co2e` or `gross_ghg_co2e` and `milk_output_litres`; persistent history; dynamic.
* `emission_intensity_kg_co2e_per_kg_protein`: Herrero-derived benchmark metric retained by the approved plan; units `kg CO₂e / kg edible protein`; type `float`; valid range `>=0`; initialize `null`; update monthly if protein denominator exists; depends on milk-protein output or an explicit protein conversion layer; persistent history; dynamic.
* `synthetic_fertilizer_saved_kg`: HTML dashboard environmental KPI; units `kg`; type `float`; valid range `>=0`; initialize `0`; update weekly/monthly; depends on digestate substitution packet; persistent; dynamic.

#### 2.4 Soil and ecological variables


* `soil_carbon_delta`: soil carbon change received from Feed/Crop; units not clearly specified in the provided resources; type `float`; valid range positive or negative; initialize `0`; update weekly/monthly; depends on crop and digestate state; persistent history; dynamic.
* `soil_organic_carbon_pct`: dashboard KPI listed in HTML; units `%`; type `float`; valid range `0–100`; initialize from scenario or `null`; update monthly if Feed/Crop supplies the level, or if the optional Land extension is explicitly enabled; persistent history; dynamic.
* `soil_biodiversity_index`: output required by HTML; units index; type `float`; valid range not clearly specified; initialize `null` or configured baseline; update monthly if a scoring function exists; persistent history; dynamic.
* `sustainability_score_0_100`: whole-farm composite sustainability score; units score; type `float`; valid range `0–100`; initialize `null` or configured baseline; update monthly; depends on environmental KPIs and score function; persistent history; dynamic.

#### 2.5 Optional water variables


* `water_use_total_l`: total farm water use if Water Agent active; units `L / period`; type `float`; valid range `>=0`; initialize `0`; update daily/monthly when Water packet exists; persistent history; dynamic.
* `water_use_l_per_litre_milk`: dashboard KPI from HTML; units `L / litre milk`; type `float`; valid range `>=0`; initialize `null`; update monthly if both water use and milk are available; persistent history; dynamic.
* `water_agent_active`: whether water metrics should be included; type `bool`; initialize from scenario; update on configuration; persistent; static/dynamic.

#### 2.6 Credit and reporting variables


* `carbon_credits_value`: environmental carbon-credit value sent to Farm Manager Agent; units currency / period; type `float`; valid range `>=0`; initialize `0`; update monthly; depends on validated net offsets and a configured credit price; persistent history; dynamic.
* `carbon_credit_price`: monetization input for offsets; units currency per offset unit; type `float`; valid range `>=0`; initialize from scenario/config if available; update monthly; persistent; dynamic.
* `environment_report_packet`: structured monthly packet sent to Farm Manager Agent/dashboard; type `dict`; initialize empty; update monthly; persistent snapshots; dynamic.
* `reporting_period_index`: current aggregation period; units integer; type `int`; valid range `>=0`; initialize `0`; update monthly; persistent; dynamic.

#### 2.7 Validation / reference variables


* `herrero_enteric_share_ref`: reference share for enteric CH₄ in environmental breakdown; units fraction; type `float`; initialize `0.65`; static; calibration/validation only.
* `herrero_manure_ch4_share_ref`: reference share for manure CH₄; units fraction; type `float`; initialize `0.10`; static; validation only.
* `herrero_manure_n2o_share_ref`: reference share for manure-related N₂O; units fraction; type `float`; initialize `0.29`; static; validation only.
* `stream_consistency_flag`: whether incoming sub-streams are unit-consistent and non-duplicated; type `bool`; initialize `true`; update each aggregation cycle; transient + history; dynamic.

#### 2.8 Unsupported or partially specified variables

These may exist as placeholders but their numeric rules are not grounded enough for hardcoded values:


* direct `co2_nonbiogenic_streams`
* exact grid-emission factor
* exact synthetic-fertilizer substitution factor
* exact biodiversity-score formula
* exact sustainability-score formula
* exact carbon-credit eligibility rules

### 3. Agent Behaviors and Actions

#### 3.1 Normal behaviors


* `ingest_daily_emission_packets()`
* Trigger: daily after Cow and Manure updates.
* Inputs: Cow enteric CH₄ packet, Manure storage CH₄ packet, Manure field-N₂O packet, optional Feed/Crop fertilizer-emission packet.
* Action: append source-tagged entries to `global_ghg_ledger`.
* Outputs: updated ledger only.


* `ingest_weekly_offset_packets()`
* Trigger: weekly after Energy and recycling updates.
* Inputs: Energy displacement packet, digestate/fertilizer substitution packet.
* Action: stores raw negative-term packets without applying them until validation.
* Outputs: updated offset buffers.


* `ingest_monthly_context()`
* Trigger: monthly aggregation phase.
* Inputs: milk output, soil carbon delta, optional water use, optional protein denominator.
* Action: refreshes normalization and ecological context.
* Outputs: reporting-ready state.


* `validate_stream_integrity()`
* Trigger: before monthly aggregation.
* Inputs: full ledger and buffered packets.
* Action: checks for duplicate source submission, negative positive-stream values, missing denominator, and incompatible periodicity.
* Outputs: `stream_consistency_flag`, anomaly list.


* `aggregate_positive_ghg()`
* Trigger: monthly after validation.
* Inputs: daily/weekly ledger entries.
* Action: sums positive subaccounts into `gross_ghg_co2e`.
* Outputs: gross GHG total and stream-level breakdown.


* `compute_avoided_emissions()`
* Trigger: monthly after positive aggregation.
* Inputs: Energy offset packet, digestate substitution packet, configured emission-factor context if available.
* Action: computes `avoided_grid_emissions_co2e`, `avoided_synthetic_fertilizer_co2e`, and `total_avoided_ghg_co2e`.
* Outputs: validated negative subaccounts.
* Constraint: exact conversion factors are not clearly specified, so they must remain configuration inputs rather than hardcoded constants.


* `compute_net_carbon_balance()`
* Trigger: after avoided-emission calculation.
* Inputs: gross and avoided totals, soil carbon delta if included in configured balance logic.
* Action: computes `net_ghg_co2e` and `net_carbon_balance`.
* Outputs: final farm-level carbon result for the period.


* `compute_intensity_metrics()`
* Trigger: after net balance.
* Inputs: `net_ghg_co2e`, `gross_ghg_co2e`, `milk_output_litres`, optional protein denominator.
* Action: computes `ghg_intensity_kg_co2e_per_litre` and optional protein-normalized intensity.
* Outputs: KPI values.


* `compute_optional_scores()`
* Trigger: after intensity metrics.
* Inputs: GHG, soil, water, fertilizer-saved, optional biodiversity inputs.
* Action: computes `sustainability_score_0_100`, `soil_biodiversity_index`, and `carbon_credits_value` only if score/price functions are configured.
* Outputs: composite scores and economic environmental values.


* `publish_environment_report()`
* Trigger: end of monthly cycle.
* Outputs:
* to Farm Manager Agent: sustainability score, net carbon balance, emission intensity, carbon credits
* to dashboard: full environmental KPI packet
* to analysis/validation layer: source-broken GHG breakdown

#### 3.2 Adaptive / corrective behaviors


* `apply_avoided_emission_correction()`
* Trigger: whenever Energy and digestate packets are both active.
* Action: ensures net GHG reflects both renewable-electricity displacement and fertilizer substitution.
* Modeling purpose: fixes the under-reporting of biogas scenarios identified in the approved FAN integration.


* `switch_report_mode_gross_vs_net()`
* Trigger: when user or Farm Manager requests diagnostic detail.
* Action: publishes both gross emissions and net-after-offset emissions.
* Purpose: avoids confusion where mitigation scenarios appear unchanged because only gross emissions were shown.


* `benchmark_against_reference_shares()`
* Trigger: monthly or experiment-end validation.
* Action: compares current stream decomposition against reference shares `65/10/29`.
* Purpose: diagnostic only; it must not overwrite actual stream totals.

#### 3.3 Failure-state behaviors


* `handle_missing_offset_factors()`: if offset packets exist but no factor is configured, publish gross GHG and store offsets as pending/unvalued.
* `handle_zero_milk_denominator()`: if milk output is zero, suppress per-litre intensity and keep absolute totals only.
* `handle_duplicate_credit_sources()`: if Energy sends credit value and Environment also computes credits, Environment becomes final authority and ignores provisional duplicates.
* `handle_optional_agent_absence()`: if Water or the optional Land extension is absent, publish environmental KPIs without those fields.
* `handle_negative_positive_stream()`: clamp erroneous positive-stream inputs below zero to zero and log validation error.

### 4. Decision-Making Logic

The Environment Agent is a **deterministic aggregation and normalization agent**. It does not optimize production; it consolidates and validates environmental consequences from other agents.


#### 4.1 Decision sequence


1. receive raw positive-emission packets
2. receive raw avoided-emission packets
3. validate units, ownership, and duplicate submissions
4. aggregate positive streams into gross GHG
5. compute negative avoided-emission terms
6. compute net carbon balance
7. normalize by milk output
8. compute composite scores and credit values if configured
9. publish monthly results

#### 4.2 Prioritization logic

Priority order for trustworthy reporting:


1. source-traceable physical streams
2. validated avoided-emission terms
3. denominator-aware intensity metrics
4. optional composite scores

This prevents the agent from reporting a polished score when the underlying stream accounting is incomplete.


#### 4.3 Double-count prevention logic


* Cow owns enteric CH₄ generation.
* Manure owns manure-storage CH₄ and field-N₂O precursor publication.
* Energy owns renewable-displacement precursor publication.
* Environment owns **final aggregation and netting**, not upstream generation.

If the same stream arrives twice from different agents, the source-tagged ledger must reject or quarantine the duplicate entry.


#### 4.4 Credit finalization logic

Because the HTML architecture lists carbon credits under both Energy and Environment outputs:


* Energy may produce a provisional energy-credit estimate,
* Environment should finalize the carbon-credit figure sent to Farm Manager Agent after checking net offsets and avoiding duplicate crediting.

Exact carbon-credit pricing and eligibility logic are not clearly specified in the provided resources and the shown form is an implementation assumption used to keep agent interfaces and mass/energy/accounting constraints executable.


#### 4.5 Composite-score logic

The Environment Agent must expose `sustainability score (0–100)` because it is an explicit HTML output, but the exact weighting and normalization function are not clearly specified in the provided resources and the shown form is treated as an implementation assumption to keep agent interfaces and mass/energy/accounting constraints executable.


Implementation-safe rule:


* treat score computation as a configurable scoring function,
* do not hardcode arbitrary weights.

### 5. Agent Interactions

#### Incoming dependencies


* Cow → Environment
* Frequency: daily.
* Data: enteric CH₄; monthly milk-output denominator.
* Impact: supplies dominant emission stream and normalization basis.


* Manure → Environment
* Frequency: daily.
* Data: storage CH₄, field N₂O precursors or already converted manure-related N₂O packet.
* Impact: supplies secondary emission streams.


* Energy → Environment
* Frequency: weekly.
* Data: GHG offset / renewable displacement.
* Impact: activates avoided-grid-emission term.


* Feed/Crop → Environment
* Frequency: weekly/monthly.
* Data: soil carbon delta, synthetic fertilizer requirement/saved, optional fertilizer-application emissions.
* Impact: supports soil-carbon accounting and digestate-substitution offset.


* Water Agent → Environment
* Frequency: monthly when active.
* Data: water use.
* Impact: enables `L/litre milk` water KPI.


* Genetics → Environment
* Frequency: annual, per interaction map.
* Data: CH₄ factor via `RFI_fat`.
* Impact: should be used for attribution/diagnostics only unless explicitly wired as a Cow-calculation input upstream; do not add it as a separate emission stream.

#### Outgoing dependencies


* Environment → Farm Manager Agent
* Frequency: monthly.
* Data: sustainability score, net carbon balance, emission intensity, carbon credits.
* Impact: policy evaluation and recommendation logic.


* Environment → Dashboard / reporting layer
* Frequency: monthly and experiment-end.
* Data: environmental KPI packet, sub-stream breakdown, gross vs net comparison.
* Impact: visualization and scenario comparison.

#### Synchronization rules


* Environment runs after daily Cow and Manure emissions are available.
* Monthly environmental rollup runs after weekly Energy and recycling updates are posted.
* Farm Manager Agent should consume Environment after netting is complete, not from raw sub-stream packets.
* If Water Agent is off, its fields remain absent, not zero by assumption.

#### Feedback loops


* Feed → Cow → Environment: diet quality alters enteric CH₄ intensity through Cow outputs.
* Feed → Manure → Environment: dietary CP and amino-acid balancing alter urinary N and then N₂O.
* Manure → Energy → Environment: manure-to-biogas creates avoided fossil-energy emissions.
* Manure → Feed/Crop → Environment: digestate substitution reduces synthetic-fertilizer burden.
* Environment → Farm Manager → Feed/Manure/Energy policies: sustainability KPIs influence management policy.

### 6. Environmental Integration

This is the system’s primary environmental integrator (source: approved architecture and integration plan).


#### Environmental inputs

* enteric CH₄ from Cow
* manure-storage CH₄ from Manure
* field/manure N₂O from Manure and/or Feed/Crop environmental packet
* GHG offset from Energy
* soil carbon delta from crops
* optional water use from Water Agent
* optional annual CH₄ attribution factor from Genetics

#### Environmental outputs

* gross GHG ledger
* net carbon balance
* GHG intensity per litre milk
* optional protein-normalized emission intensity
* synthetic fertilizer saved
* soil organic carbon / biodiversity outputs when supported
* sustainability score
* carbon credits
* optional FAO-aligned circularity metrics: `NUE`, `ICirc`, `OCirc`, `use_count`, `cycle_count`
* indicator-type tags on each published KPI: `target`, `practice`, `result`, or `outcome`

#### Resource/environmental dependencies

* milk output for normalization
* digestate use for fertilizer-displacement logic
* energy displacement for avoided-grid-emission logic
* crop/soil signals for soil carbon outcomes
* optional water metrics

#### Carrying-capacity and environmental constraints
Not clearly specified in the provided resources:


* ecosystem carrying-capacity thresholds,
* biodiversity threshold responses,
* net-zero target threshold definitions,
* soil-carbon saturation functions.

#### Environmental feedback handling
Environment itself does not alter Cow, Feed, or Energy directly (implementation assumption).

Its effect is indirect through Farm Manager decisions based on published KPIs (implementation assumption).


### 7. Genetic / Evolutionary Logic (If Applicable)

The Environment Agent has no direct genome, inheritance, crossover, or mutation logic (not clearly specified in the provided resources and this item remains configurable and should be treated as an implementation assumption until a direct source is added).


Supported indirect genetic linkage:


* Genetics influences `RFI_fat`,
* `RFI_fat` changes Cow DMI and enteric CH₄,
* Environment records the resulting CH₄ pathway,
* annual Genetics-to-Environment attribution can be stored for reporting alignment.

Do not implement inside Environment:


* direct breeding optimization,
* methane EBV selection logic,
* evolutionary state transitions.

### 8. Equations / Algorithms / Thresholds

#### 8.1 Minimum supported gross-GHG aggregation

A directly supported minimum decomposition is:


$$gross\_ghg\_co2e =
enteric\_ch4\_co2e +
manure\_storage\_ch4\_co2e +
field\_n2o\_co2e$$
**Source:** emissions-bucket decomposition aligned to Herrero-derived shares and project-analysis aggregation logic; exact factorization constants require external calibration.

**Why used:** Aggregates enteric, manure-storage, and field N₂O buckets before FAN avoided-emission netting in Environment.


This reflects the approved split of the previously lumped GHG bucket.


#### 8.2 Herrero-derived reference proportions

Use as validation references, not as replacement formulas:


* enteric CH₄ share: `~65%`
* manure CH₄ share: `~10%`
* manure-related N₂O share: `~29%`

These come from the project-analysis extraction of Herrero and justify the sub-account structure.


#### 8.3 Net-GHG aggregation with FAN avoided-emission correction

$$net\_ghg\_co2e =
gross\_ghg\_co2e -
avoided\_grid\_emissions\_co2e -
avoided\_synthetic\_fertilizer\_co2e$$
**Source:** FAN avoided-emission framing in `project-analysis.pdf`; project-specific grid/fertilizer emission factors require external calibration.

**Why used:** Subtracts grid and fertilizer avoided emissions from gross farm GHG for net carbon-balance KPIs.


This is the urgent correctness fix required by the approved plan.


#### 8.4 GHG intensity per litre milk

$$ghg\_intensity\_kg\_co2e\_per\_litre =
\frac{net\_ghg\_co2e}{milk\_output\_litres}$$
**Source:** KPI denominator identity (emissions per milk litre); emission buckets are aggregated separately upstream.

**Why used:** Divides net GHG by milk output for per-litre sustainability benchmarking on the Environment dashboard.


if `milk_output_litres > 0`.


If strict Herrero-style gross non-CO₂ benchmarking is desired, also compute:


$$gross\_emission\_intensity =
\frac{gross\_ghg\_co2e}{milk\_output\_litres}$$
**Source:** KPI denominator identity (emissions per milk litre); emission buckets are aggregated separately upstream.

**Why used:** Provides gross per-litre intensity for Herrero-style non-CO₂ benchmarking alongside net metrics.


#### 8.5 Protein-normalized intensity

$$emission\_intensity\_kg\_co2e\_per\_kg\_protein =
\frac{gross\_ghg\_co2e \text{ or } net\_ghg\_co2e}{protein\_output\_kg}\]
**Source:** KPI denominator identity (emissions per kg protein); chooses gross or net numerator per reporting mode.

**Why used:** Normalizes emissions to protein output for protein-footprint KPIs when protein mass is available.


The approved plan keeps this KPI, but exact protein-denominator derivation is not clearly specified in the provided resources and the shown form is retained as an implementation assumption so agent interfaces and mass/energy/accounting constraints stay executable.


#### 8.6 Carbon-credit calculation

Implementation form:


$$carbon\_credits\_value =
validated\_creditable\_offset \times carbon\_credit\_price$$
**Source:** Herrero-derived emissions split + FAN avoided-emission framing from `project-analysis.pdf`; exact conversion/credit protocols are not clearly specified in provided resources.

**Why used:** Monetizes validated offset mass for Farm Manager revenue when credit price and eligibility context are configured.


The exact definition of `validated_creditable_offset` and the required price inputs are not clearly specified in the provided resources and the shown form is an implementation assumption used to keep agent interfaces and mass/energy/accounting constraints executable.


#### 8.7 Unsupported exact factors

Do not hardcode without external calibration:


* grid-emissions factor for displaced electricity
* synthetic-fertilizer substitution factor
* direct N₂O emission factor numeric
* soil biodiversity score weights
* sustainability-score weights
* net-zero threshold

#### 8.8 FAO LEAP circularity indicators and LCA reporting layer
FAO LEAP distinguishes **target** (policy goals), **practice** (adopted circular actions), **result** (measurable flows), and **outcome** (system-level effects) indicators. Every Environment KPI published to Farm Manager should carry one of these tags **(Source:** FAO, 2025, Ch. 2 §2.1.1**)**.


Supported circularity metrics (configurable numerators/denominators):


* `NUE` — nitrogen retained in products relative to nitrogen intake; align with Feed urinary-N outputs when cow-level intake is available **(Source:** FAO, 2025, Ch. 2 §2.2**)**
* `ICirc` — share of feed or nutrient inputs sourced from recycled/co-product streams rather than virgin human-edible inputs **(Source:** FAO, 2025, Ch. 2 §2.3**)**
* `OCirc` — share of manure, whey, wastewater, or crop residues valorized in feed, fertilizer, or energy routes rather than unmanaged loss **(Source:** FAO, 2025, Ch. 2 §2.3**)**
* `use_count` — number of productive uses a material stream undergoes before leaving the farm system boundary **(Source:** FAO, 2025, Ch. 5**)**
* `cycle_count` — number of completed circular loops (e.g., manure → digestate → crop → feed → milk) observed in the reporting window **(Source:** FAO, 2025, Ch. 5**)**

LCA alignment note: when scenario comparisons require attributional footprints, document whether co-product credits use allocation or system expansion; this agent aggregates flows for ABM KPIs and does not replace a full consequential LCA engine **(Source:** FAO, 2025, Ch. 2 §2.4**)**.


Exact ICirc/OCirc boundary definitions, use-count attribution rules, and SDG mapping weights are not clearly specified in the provided resources and remain configurable reporting metadata.


### 9. Data Requirements

Required internal/external packets:


* `cow_environment_packet`
* fields: enteric CH₄, milk output
* frequency: daily
* `manure_environment_packet`
* fields: storage CH₄, field-N₂O precursor or converted N₂O
* frequency: daily/weekly
* `energy_offset_packet`
* fields: displaced energy or already-converted offset value
* frequency: weekly
* `crop_environment_packet`
* fields: soil carbon delta, synthetic fertilizer saved/required, optional fertilizer-application emissions
* frequency: weekly/monthly
* `water_packet`
* fields: total water use
* frequency: monthly when active
* `price_context`
* fields: carbon-credit price if credits are monetized
* frequency: monthly

Temporal resolution:


* daily ingestion for raw emission flows
* weekly ingestion for offset and recycling packets
* monthly aggregation for KPI publication
* experiment-end summaries for scenario comparison

Spatial resolution:


* farm-level aggregate environmental accounting
* no field-level spatial heterogeneity is clearly specified for Environment beyond receiving soil-level summaries from Feed/Crop

Preprocessing requirements:


* convert all upstream packets to common `CO₂e / period` units before aggregation
* preserve source tags for every ledger entry
* store gross and avoided terms separately

Validation datasets / anchors:


* Herrero-derived stream-share diagnostics `65/10/29`
* experiment comparison metrics from the HTML dashboard:
* `GHG intensity`
* `net carbon balance`
* `synthetic fertiliser saved`
* `sustainability score`

Variables requiring real-world calibration:


* avoided-grid-emission factor
* avoided-fertilizer-emission factor
* carbon-credit price
* biodiversity-score formula
* sustainability-score formula

Variables simulatable internally:


* source-stream aggregation
* gross GHG
* net GHG
* per-litre intensity
* source-share diagnostics
* monthly report assembly

Missing-data handling:


* if milk denominator missing, publish absolute GHG only
* if offset factors missing, keep raw offset packets and publish gross GHG with “offset pending”
* if water packet missing and Water Agent off, omit water KPI
* if soil carbon delta missing, publish GHG metrics without soil-carbon update

### 10. Edge Cases / Failure Conditions


* double counting the same emission stream
* Detection: duplicate source+stream+period key in ledger.
* Prevention: source-tagged ingestion with unique keys.
* Recovery: reject duplicate or move to anomaly queue.


* positive stream submitted as negative
* Detection: sign check on all “positive” emission packet types.
* Prevention: validate packet schema on ingest.
* Recovery: clamp to zero and log error.


* offset larger than gross emissions
* Detection: `total_avoided_ghg_co2e > gross_ghg_co2e`.
* Prevention: none required; net-negative farms are possible conceptually.
* Recovery: allow negative `net_carbon_balance`, but do not coerce KPI sign.


* zero milk output denominator
* Detection: `milk_output_litres == 0`.
* Prevention: guarded division.
* Recovery: set per-litre metrics to `null` and publish absolute totals only.


* Energy credit duplicated by Environment credit
* Detection: both packets contain monetized credit values.
* Prevention: Environment finalizes only one credit figure.
* Recovery: ignore provisional duplicate and log reconciliation note.


* missing avoided-emission factor
* Detection: raw offset packet present but factor absent.
* Prevention: configuration validation at simulation start.
* Recovery: report gross emissions plus unconverted offset packet.


* sustainability score requested without formula
* Detection: no score function configured.
* Prevention: check configuration before reporting.
* Recovery: publish `null` or “not configured,” not an invented score.


* inconsistent period units
* Detection: mix of daily and monthly values without aggregation tag.
* Prevention: require `period_type` in every packet.
* Recovery: reject packet until normalized.


* optional Water or biodiversity context absent
* Detection: no packet and feature inactive.
* Prevention: feature flags.
* Recovery: omit those KPIs from final report instead of assuming zero.

### 11. Direct Coding Guidance

Recommended module:


* `agents/environment_agent.py`

Recommended classes:


* `EnvironmentAgent`
* `GHGLedgerEntry`
* `EnvironmentalOffsetPacket`
* `EnvironmentReportPacket`

Recommended internal structure:


* `positive_streams_by_period`
* `offset_streams_by_period`
* `kpi_history`
* `anomaly_log`

Recommended method layout:


```python
class EnvironmentAgent:
    def __init__(self, config):
        ...
    def receive_cow_packet(self, packet):
        ...
    def receive_manure_packet(self, packet):
        ...
    def receive_energy_offset_packet(self, packet):
        ...
    def receive_crop_packet(self, packet):
        ...
    def receive_water_packet(self, packet):
        ...
    def validate_stream_integrity(self, period):
        ...
    def aggregate_positive_ghg(self, period):
        ...
    def compute_avoided_emissions(self, period):
        ...
    def compute_net_balance(self, period):
        ...
    def compute_intensity_metrics(self, period):
        ...
    def compute_optional_scores(self, period):
        ...
    def publish_report(self, period):
        ...```

Recommended update-loop order:


1. daily: ingest Cow and Manure environmental packets
2. weekly: ingest Energy and digestate/fertilizer substitution packets
3. monthly:

* ingest milk, soil, and optional water totals
* validate streams
* aggregate gross GHG
* apply avoided-emission corrections
* compute net balance
* compute intensities
* compute optional score/credits
* publish report to Farm Manager Agent and dashboard

Execution priority:


* after Cow, Manure, Feed/Crop, and Energy have posted their current-period packets
* before Farm Manager monthly recommendations are generated

State-management rules:


* keep gross emissions separate from offsets
* keep physical offsets separate from monetized credits
* keep source-traceable entries for every stream
* store both monthly totals and experiment-end cumulative totals

Persistence rules:


* persist all period ledgers for scenario comparison
* persist anomaly log for debugging and audit
* persist gross vs net KPIs separately

Stochastic handling:


* none required by the provided resources
* all supported Environment logic is deterministic aggregation and normalization

Extensibility-safe additions:


* explicit soil-carbon stock model
* richer biodiversity module
* additional water-accounting detail
* field-level environmental subledgers

Do not add without new sources:


* hardcoded IPCC factors
* net-zero threshold policies
* arbitrary sustainability weights
* direct CO₂ source breakdown beyond supplied packets
* ecosystem carrying-capacity equations

---

## Agent 8 — 🧑‍🌾 Farm Manager Agent

*Tag: Control*

### 1. Agent Purpose

The Farm Manager Agent is the system’s **top-level decision orchestrator**.


The original HTML architecture defines it as the agent that:


* responds to user-set policies,
* calculates whole-farm profitability,
* issues recommendations,
* and acts as the simulation’s “brain.”

Its core responsibilities are to:


* hold the active farm policy state,
* aggregate economic and sustainability information coming from other agents,
* arbitrate trade-offs among profit, disease control, genetics, and environmental performance,
* issue policy change triggers,
* publish dashboard summary statistics,
* and send only the allowed control signals downstream.

In the approved architecture, it is the **L1 policy layer** above:


* Feed optimization,
* Genetics selection weighting,
* Disease biosecurity control,
* Manure/Energy routing scenarios.

The plan explicitly assigns it:


* user policy weighting across economic, environmental, disease, and genetics goals,
* filtered recommendation generation,
* and alert prioritization with tiers `Critical / Important / Advisory` derived from the Tedeschi integration.

It does **not** own:


* raw sensor acquisition,
* direct ration optimization,
* direct breeding computations,
* direct disease progression,
* or final environmental accounting.

Those remain with:


* Sensors,
* Feed,
* Genetics,
* Disease,
* Environment.

Why this agent exists:


* it is explicitly essential in the HTML architecture,
* the workflow sends profit and sustainability results into Farm Manager before dashboard output,
* the approved plan uses it as the policy/control node,
* and it is the only agent that can consistently arbitrate conflicting goals across subsystems.

Subsystem ownership:


* policy state,
* farm-level economics,
* recommendation generation,
* dashboard summary assembly,
* cross-agent control dispatch,
* farm cash balance.

Objectives:


1. compute whole-farm profitability from incoming revenue and cost streams,
2. track ROI/payback for circular investments when enough data exists,
3. issue policy changes for breeding priority, biosecurity, digester deployment, and related management toggles,
4. surface filtered recommendations rather than raw subsystem noise,
5. convert monthly technical KPIs into user-facing decision support.

Dependencies:


* Cow for milk output / milk revenue packet,
* Feed / Crop Agent for feed-cost and feed-sourcing outcomes,
* Disease for outbreak alerts, milk-loss, vet costs,
* Energy for cost savings and carbon-credit packet,
* Environment for sustainability score and emission intensity,
* Genetics for annual breeding progress and breeding recommendation,
* Market Agent for price context or price shocks,
* Dairy Processor Agent for by-product revenue and valorization packets,
* Sensors Agent for filtered alerts only.

Constraints:


* exact optimization algorithm for Farm Manager Agent is **not clearly specified in the provided resources**
* exact recommendation thresholds for `Critical / Important / Advisory` are **not clearly specified in the provided resources**
* exact milk price functions, carbon-credit prices, investment-cost schedules, and payback parameters are **not clearly specified in the provided resources**
* raw sensor-stream interpretation must remain outside Farm Manager Agent; the plan explicitly offloads that to the Sensors Agent.

Expected outputs:


* `net_farm_profit`
* `roi_circular_investment`
* `payback_period_years`
* `actionable_recommendations`
* `policy_change_triggers`
* `dashboard_summary_stats`
* downstream policy packet for Genetics, Disease, Feed / Crop Agent, Manure, and Energy

Contribution to global system behavior:


* closes the economic and decision loop,
* turns technical subsystem outputs into management actions,
* governs the trade-off surface for experiments E1–E6 and related scenario toggles,
* and provides the user-facing interpretation layer for the whole ABM.

### 2. Agent State Variables

#### 2.1 Policy and user-control variables


* `breeding_priority_mode`: active breeding emphasis; enum; valid supported values from HTML/user table are `milk`, `disease`, `CH4`; initialize from user input; update on policy events; passed to Genetics as breeding-priority context; persistent; dynamic.
* `market_scenario_index`: annual genetics market scenario selector; enum; valid supported values now grounded by `net-merit.pdf` / USDA `NM$9 (01-25)` revised `Feb 2026` are `NM$`, `CM$`, `FM$`, `GM$`; initialize from user or scenario; update annually or on user override; passed to Genetics as the official four-scenario choice; persistent; dynamic.
* `biosecurity_level_pct`: herd biosecurity control; float `%`; valid range `0–100`; initialize from user input; update when policy changes; passed to Disease; persistent; dynamic.
* `digester_capacity_pct`: manure-to-energy policy level; float `%`; valid range `0–100`; initialize from user input; update on policy change; passed to Manure/Energy pathway; persistent; dynamic.
* `feed_policy_mode`: feed policy selector; enum; supported value distinction from HTML is `standard` vs `amino_balanced`; initialize from user input or default; update on policy change; passed to Feed; persistent; dynamic.
* `land_area_ha`: farm land area retained for management context; float `ha`; valid range `>=0`; initialize from user input; usually static; consumed mainly by Feed/Crop; persistent; static.
* `herd_size_target`: desired herd size or current initialized herd count; integer cows; valid range `>=0`; initialize from user input; update only if herd-scaling scenario changes; persistent; dynamic.
* `budget_available`: management budget context named in HTML workflow; currency; valid range `>=0`; initialize from user/scenario; update monthly/yearly; used for policy feasibility screening; persistent; dynamic.
* `simulation_horizon_years`: run horizon; integer/float years; valid range `>0`; initialize from user input; static for a run; persistent; static.

#### 2.2 Objective-weight and decision-state variables


* `economic_weight`: weight assigned to profit/cost performance in policy arbitration; float; valid range not clearly specified; initialize from scenario or equal-weight default; update when user changes priorities; persistent; dynamic.
* `environmental_weight`: weight assigned to GHG/sustainability goals; float; valid range not clearly specified; initialize from scenario; update on policy change; persistent; dynamic.
* `disease_weight`: weight assigned to health and outbreak resilience; float; valid range not clearly specified; initialize from scenario; update on policy change; persistent; dynamic.
* `genetics_weight`: weight assigned to long-run breeding improvement; float; valid range not clearly specified; initialize from scenario; update on policy change; persistent; dynamic.
* `policy_conflict_state`: structured record of currently competing objectives; type `dict`; initialize empty; update whenever economics and environmental/health signals diverge; persistent history; dynamic.
* `selected_operating_point`: current management choice after arbitration; structured state; initialize from initial user settings; update weekly/monthly; persistent history; dynamic.

#### 2.3 Economic ledger variables


* `milk_revenue`: revenue from milk sales; currency per day/week/month; float; valid range `>=0`; initialize `0`; update daily from Cow volume × farm-gate price when Dairy Processing Unit is not opted in, or from Dairy Processor product-mix revenue when that unit (and Loop 4) is active — matching dashboard `milkRev = loops.l4 ? dairyProductRev : rawMilkRev`; persistent history; dynamic.
* `byproduct_revenue`: revenue or feed-cost offsets from Dairy Processor Agent *only when* opted-in processor/whey routes generate sellable or credited outputs; currency per period; float; valid range `>=0`; initialize `0`; update weekly; persistent history; dynamic.
* `milk_cooling_cost`: bulk-tank cooling opex from dashboard identity `milk × milk_cooling_kWh_per_L_milk × electricity_price`; applies in the default milking path (with or without processing); currency per period; float `>=0`; dynamic.
* `feed_cost_total`: farm feed cost; currency per period; float; valid range `>=0`; initialize `0`; update daily/weekly from Feed / Crop Agent; persistent history; dynamic.
* `vet_cost_total`: disease-related treatment cost; currency per period; float; valid range `>=0`; initialize `0`; update daily/weekly from Disease; persistent history; dynamic.
* `energy_cost_saved`: avoided energy cost from Energy; currency per period; float; valid range `>=0`; initialize `0`; update weekly; persistent history; dynamic.
* `carbon_credits_value`: monetized carbon-credit or offset value from Energy/Environment reconciliation; currency per period; float; valid range `>=0`; initialize `0`; update weekly/monthly; persistent history; dynamic.
* `other_operating_costs`: optional explicit additional cost bucket; currency; initialize `0`; use only if another supported stream provides it; persistent; dynamic.
* `net_farm_profit`: headline economic output; currency per year or period; float; valid range positive or negative; initialize `0`; update monthly/yearly; depends on revenue and cost ledgers; persistent history; dynamic.
* `farm_cash_balance`: shared state explicitly owned by Farm Manager Agent in the approved plan; currency; valid range can be negative if debt is represented; initialize from scenario or `0`; update daily/monthly as `revenue - costs`; persistent; dynamic.

#### 2.4 Investment and circular-economy variables


* `roi_circular_investment`: ROI of circular investments, explicitly required by HTML; float; valid range not clearly specified; initialize `null` or `0`; update monthly/yearly if investment-cost context exists; persistent history; dynamic.
* `payback_period_years`: payback metric explicitly required by HTML dashboard; float years; valid range `>=0` when defined; initialize `null`; update when investment cost and annualized benefit exist; persistent history; dynamic.
* `circular_investment_active`: bool flag indicating digester or similar circular investment pathway is active; initialize from scenario; update on policy change; persistent; dynamic.
* `annual_circular_benefit`: aggregated annual benefit attributable to circular loop; currency/year; initialize `0`; update yearly; depends on energy savings, fertilizer savings, credits, and other supported benefits; persistent; dynamic.
* `investment_cost_basis`: capex or implementation cost used in ROI/payback; currency; valid range `>=0`; initialize from scenario if available; exact default not clearly specified in the provided resources; persistent; calibration.

#### 2.5 KPI intake variables


* `sustainability_score_0_100`: monthly composite from Environment; float `0–100`; initialize `null`; update monthly; persistent history; dynamic.
* `emission_intensity_kg_co2e_per_litre`: monthly environmental KPI from Environment; float `>=0`; initialize `null`; update monthly; persistent history; dynamic.
* `disease_alert_state`: structured disease status from Disease; initialize empty; update daily/weekly; includes outbreak state, mortality, milk-loss; persistent history; dynamic.
* `milk_output_total`: milk production volume used for revenue and summary stats; litres per period; initialize `0`; update daily and aggregate; persistent history; dynamic.
* `feed_autonomy_metric`: supported by approved plan as `local_feed_autonomy`; float or fraction; initialize `null`; update from Feed / Crop Agent; persistent history; dynamic.
* `genetic_gain_per_generation`: annual genetics KPI from Genetics; numeric; initialize `null`; update annually; persistent history; dynamic.
* `herd_nm_trend`: annual breeding-value trend summary from Genetics; initialize empty or `null`; update annually; persistent history; dynamic.
* `sensor_alert_queue`: filtered alerts only from Sensors Agent; structured queue; initialize empty; update on event; transient + history; dynamic.

#### 2.6 Recommendation and control-output variables


* `recommendation_queue`: ordered list of management recommendations; type `list`; initialize empty; update daily/weekly/monthly; persistent snapshots; dynamic.
* `policy_change_triggers`: current trigger set sent to downstream agents; type `dict`; initialize empty; update when decision state changes; persistent history; dynamic.
* `dashboard_summary_stats`: final display packet; type `dict`; initialize empty; update monthly; persistent snapshots; dynamic.
* `alert_priority_tier`: enum for a given recommendation or alert; valid values `Critical`, `Important`, `Advisory`; initialize null; update whenever recommendation queue is rebuilt; dynamic.
* `recommendation_explanation`: textual rationale/XAI-style explanation for a policy suggestion; string or structured list; initialize empty; update with each recommendation; persistent snapshots; dynamic.

#### 2.7 Unsupported exact-state details

Do not hardcode without new sources:


* explicit utility coefficients,
* exact recommendation thresholds,
* exact debt/interest model,
* exact milk-price function,
* exact capex schedules for digester deployment,
* exact dashboard scoring weights.

### 3. Agent Behaviors and Actions

#### 3.1 Core behaviors


* `ingest_user_policy_inputs()`
* Trigger: simulation start and any user policy change.
* Inputs: herd size, land area, budget, breeding priority, biosecurity level, energy investment, simulation horizon, feed policy if used.
* Action: updates master policy state.
* Outputs: initial or revised control packet.


* `ingest_operational_kpis()`
* Trigger: daily/weekly/monthly depending on source.
* Inputs:
* Cow milk output/revenue,
* Feed / Crop Agent cost summary,
* Disease alerts and vet costs,
* Energy savings/credits,
* Environment sustainability KPIs,
* Genetics progress metrics,
* Market Agent price context or price shocks,
* Dairy Processor Agent revenue/value packet,
* filtered Sensors Agent alerts.
* Action: refreshes farm-level ledgers and KPI buffers.


* `update_cash_balance()`
* Trigger: daily and monthly close.
* Inputs: revenues and costs.
* Action: updates `farm_cash_balance`.
* Outputs: economic ledger state.


* `compute_profitability()`
* Trigger: monthly and annual reporting.
* Inputs: current revenue/cost totals.
* Action: computes `net_farm_profit`.
* Outputs: profitability packet.


* `evaluate_circular_investment_performance()`
* Trigger: weekly/monthly/yearly when digester pathway active.
* Inputs: energy savings, credits, fertilizer savings if available, investment cost basis.
* Action: computes ROI/payback if supported data exists.
* Outputs: circular-investment report.


* `rank_management_issues()`
* Trigger: after KPI ingestion.
* Inputs: outbreak status, profit trend, emission intensity, feed autonomy, sensor alerts, genetics signals.
* Action: classifies active issues into `Critical / Important / Advisory`.
* Outputs: prioritized issue list.


* `generate_recommendations()`
* Trigger: after ranking issues.
* Inputs: issue list plus current policy state.
* Action: creates filtered management recommendations only.
* Outputs: recommendation queue with explanations.


* `dispatch_policy_updates()`
* Trigger: when policy change is accepted or simulation auto-policy mode is active.
* Inputs: selected recommendations.
* Action: publishes downstream control settings.
* Outputs:
* to Disease: `biosecurity_level_pct`
* to Manure/Energy: `digester_capacity_pct`
* to Genetics: breeding priority / market scenario
* to Feed: feed policy mode and possibly target operating priority
* to dashboard: summary stats and explanations


* `publish_dashboard_summary()`
* Trigger: monthly close and experiment-end.
* Action: compiles user-facing summary stats and reasons.
* Outputs: dashboard packet.

#### 3.2 Adaptive behaviors


* `respond_to_outbreak()`
* Trigger: Disease reports active outbreak or severe alert.
* Action: escalate disease-related recommendations and/or increase biosecurity policy.
* Supported by HTML disease-economic-biosecurity loop.
* Exact threshold for escalation is not clearly specified.


* `respond_to_high_feed_cost_or_low_feed_autonomy()`
* Trigger: Feed cost rises or `local_feed_autonomy` degrades.
* Action: prioritize feed-purchase scrutiny, amino-acid balancing / sourcing recommendations, and possibly signal genetics context through breeding priorities.
* Supported by approved Feed hierarchy and Farm Manager policy role.
* Exact threshold not clearly specified.


* `respond_to_poor_environmental_performance()`
* Trigger: Environment reports high emission intensity or low sustainability performance.
* Action: elevate environmental recommendations, especially circular-loop or feed-related policy suggestions.
* Supported by monthly Environment → Farm Manager flow.


* `respond_to_circular_roi_signal()`
* Trigger: Energy/Environment show favorable digester performance.
* Action: reinforce or maintain digester investment recommendation.
* Supported by HTML E4 and Energy/FAN integration.


* `annual_breeding_review()`
* Trigger: annual cycle.
* Inputs: genetics trend, outbreak history, feed-cost history, current breeding priority.
* Action: update Genetics-facing scenario index or breeding emphasis.
* Supported by Genetics ← Farm Manager annual interaction.

#### 3.3 Maintenance behaviors


* maintain rolling revenue and cost ledgers
* maintain recommendation history
* maintain policy-change history
* maintain dashboard history by reporting period
* maintain issue-tier counts for explainability and audit

#### 3.4 Failure-state behaviors


* `handle_missing_environment_kpis()`: publish economic summary only and suppress sustainability recommendation confidence.
* `handle_missing_price_context()`: compute physical/operational advice but mark profit estimates low confidence.
* `handle_conflicting_recommendations()`: resolve using objective weights and tier ordering.
* `handle_sensor_noise_overload()`: accept filtered alerts only; reject raw high-frequency sensor streams.

### 4. Decision-Making Logic

The Farm Manager Agent is the **policy arbitration layer**, not a low-level optimizer.


#### 4.1 Decision architecture

Supported architecture from the approved plan:


* `Strategic`: user parameters and top-level weights
* `Tactical`: Farm Manager filtered recommendations and policy triggers
* `Operational`: Feed, Manure, Disease, Genetics execute within their own domain logic

So Farm Manager decision-making should follow this order:


1. read current policy state
2. aggregate subsystem KPIs
3. assess objective conflicts
4. prioritize issues
5. choose or recommend a policy response
6. dispatch policy updates
7. publish dashboard explanations

#### 4.2 Multi-objective arbitration

The approved plan explicitly gives Farm Manager authority to weight:


* economic goals,
* environmental goals,
* disease-control goals,
* genetics goals.

Therefore the agent should maintain a **weighted policy context**, but the exact numeric utility function is not clearly specified in the provided resources.


Implementation-safe rule:


* use configurable objective weights,
* keep recommendation scoring transparent,
* do not hardcode a black-box optimizer.

#### 4.3 Conflict-resolution logic

The plan explicitly states:


* Farm Manager policy weights arbitrate Feed multi-objective vs profit.
* Feed optimization can produce different Pareto-feasible operating points.
* Farm Manager selects the operating preference, not the internal Feed algorithm.

So conflict resolution should prioritize:


1. `Critical` alerts first,
2. then weighted policy objectives,
3. then stability / minimal policy churn.

#### 4.4 Recommendation tiers

The approved plan supports priority tiers:


* `Critical`
* `Important`
* `Advisory`

Implementation-safe interpretation:


* `Critical`: immediate threat to herd viability, outbreak, or severe financial/environmental failure
* `Important`: meaningful but non-catastrophic drift in cost, emissions, or feed autonomy
* `Advisory`: long-horizon improvement opportunities such as breeding reweight or circular investment tuning

Exact thresholds for assignment are not clearly specified in the provided resources.


#### 4.5 Policy outputs supported by sources

Farm Manager is allowed to control:


* `biosecurity_level_pct`
* `digester_capacity_pct`
* `breeding_priority_mode`
* `market_scenario_index`
* dashboard/recommendation outputs
* feed-policy mode where supported by scenario design

Farm Manager should not be treated as directly setting under the provided materials:


* per-cow rations,
* per-cow disease state,
* genetic equations,
* environmental-factor values.

### 5. Agent Interactions

#### Incoming dependencies


* Cow → Farm Manager
* Frequency: daily.
* Data: milk litres / milk revenue.
* Impact: feeds revenue ledger.


* Feed/Crop → Farm Manager
* Frequency: daily/weekly.
* Data: feed cost, feed policy outcomes, local feed autonomy, possibly fertilizer-cost implications.
* Impact: drives feed-purchase decisions and cost accounting.


* Disease → Farm Manager
* Frequency: daily/weekly.
* Data: disease alerts, vet cost, milk-loss, mortality/outbreak state.
* Impact: triggers biosecurity and health-priority recommendations.


* Energy → Farm Manager
* Frequency: weekly.
* Data: cost savings, credits.
* Impact: circular investment assessment.


* Environment → Farm Manager
* Frequency: monthly.
* Data: sustainability score, emission intensity, net carbon balance, carbon credits.
* Impact: environmental trade-off evaluation and dashboard summary.


* Genetics → Farm Manager
* Frequency: annual.
* Data: breeding recommendation, genetic gain, herd trend.
* Impact: breeding-policy review.


* Sensors Agent → Farm Manager Agent
* Frequency: on filtered alert.
* Data: filtered alerts only.
* Impact: issue prioritization.
* Constraint: no raw sensor streams.


* Market Agent → Farm Manager Agent
* Frequency: monthly baseline packet, with optional stochastic shock overlay.
* Data: milk and input price context plus shock signals when enabled.
* Impact: profitability accounting and economic stress testing.


* Dairy Processor Agent → Farm Manager Agent
* Frequency: weekly/monthly packet aligned to processor accounting window.
* Data: by-product stream quantities and revenue.
* Impact: base-runtime revenue diversification and circular-loop valuation.

#### Outgoing dependencies


* Farm Manager → Genetics
* Frequency: annual.
* Data: breeding priority and market-scenario index.
* Impact: selection-weight context.


* Farm Manager → Disease
* Frequency: policy event.
* Data: biosecurity level.
* Impact: transmission-rate control.


* Farm Manager → Manure / Energy
* Frequency: policy event.
* Data: digester-capacity target / investment activation.
* Impact: circular-loop scale.


* Farm Manager → Feed
* Frequency: policy event.
* Data: feed policy mode and high-level management priorities.
* Impact: ration strategy objective emphasis.


* Farm Manager → Dashboard
* Frequency: monthly / experiment-end.
* Data: summary stats, recommendations, XAI-style explanations.
* Impact: user-facing interpretation.

#### Synchronization rules


* Daily: receive Cow output and disease state impacts.
* Weekly: receive Energy and recycling economics.
* Monthly: receive Environment KPIs and compute whole-farm summary.
* Annual: review genetics scenario and breeding orientation.

#### Feedback loops


* Feed → Cow → revenue → Farm Manager → feed-purchase / feed-policy response
* Disease → loss/cost → Farm Manager → biosecurity → Disease
* Genetics → herd trend → Farm Manager → breeding priority → Genetics
* Energy/Environment → savings/sustainability → Farm Manager → digester policy → Manure/Energy

### 6. Environmental Integration

Farm Manager is not the primary environmental accountant, but it is the **primary environmental decision consumer**.


Environmental inputs:


* sustainability score
* emission intensity
* net carbon balance
* carbon credits
* fertilizer-saving implications
* optional water KPI

Environmental outputs:


* policy choices that affect:
* feed strategy,
* biosecurity,
* digester capacity,
* breeding priority

Environmental-response logic:


* if environmental KPIs worsen, Farm Manager can raise the weight of environmental objectives and promote mitigation recommendations.
* if avoided-emission benefits improve circular ROI, Farm Manager can strengthen digester recommendations.

Environmental constraints:


* all environmental accounting remains in Environment.
* Farm Manager must not recompute GHG from raw subsystem data.
* when Environment publishes FAO indicator-type tags, Farm Manager should surface `practice` vs `outcome` separately in recommendations so policy levers are not confused with system effects **(Source:** FAO, 2025, Ch. 2 §2.1.1**)**.

Policy and regulatory constraints from FAO LEAP that Farm Manager should expose as user-configurable gates (not compute internally):


* food-safety approval for co-product feed and co-digestion routes **(Source:** FAO, 2025, Ch. 4 §4.2**)**
* One Health / biosecurity level already mapped to Disease Agent; escalate when recycled streams cross species boundaries **(Source:** FAO, 2025, Ch. 4 §4.3**)**
* optional SDG reporting flags for scenario narratives (e.g., SDG 2 food security, SDG 12 responsible production) without hardcoded SDG scores **(Source:** FAO, 2025, Ch. 1 §1.1**)**

Spatial effects:


* farm-scale only.
* field/parcel policy logic is not part of the base Phase 1 model unless the optional Land extension is specifically enabled later.

### 7. Genetic / Evolutionary Logic (If Applicable)

Farm Manager does not own inheritance or evolution.


Genetics-related logic inferred from provided materials is limited to:


* choosing breeding priority mode,
* selecting annual genetics market scenario (`NM$`, `CM$`, `FM$`, `GM$`),
* reacting to feed-cost and disease context through high-level breeding policy emphasis,
* consuming annual breeding recommendations from Genetics.

Unsupported within Farm Manager:


* trait inheritance,
* EBV calculation,
* breeder’s equation,
* mutation/crossover,
* direct selection-index formula.

### 8. Equations / Algorithms / Thresholds

#### 8.1 Net farm profit

Accounting identity inferred from provided materials:


$$net\_farm\_profit = total\_revenue - total\_costs$$
**Source:** management-accounting identity used in architecture design; line-item inclusion conventions are configurable and partially not clearly specified in provided resources.

**Why used:** Rolls agent revenue and cost packets into Farm Manager profit for scenario comparison.


Where `total_revenue` may include:


* milk revenue,
* by-product revenue,
* carbon-credit value

and `total_costs` may include:


* feed cost,
* vet cost,
* net energy cost or energy cost net of savings,
* other operating costs inferred from provided materials.

Exact accounting convention for handling `energy_cost_saved` as revenue-equivalent versus negative cost is **not clearly specified in the provided resources**.


#### 8.2 Farm cash balance update

Supported structure from approved shared-state table:


$$farm\_cash\_balance_{t+1} = farm\_cash\_balance_t + revenue_t - costs_t$$
**Source:** architecture-level management cashflow convention; exact canonical source formula is not clearly specified in provided resources.

**Why used:** Supports the agent output and accounting interface named in the surrounding section; no additional coefficients are introduced here.


#### 8.3 ROI and payback

These are required HTML outputs, but the exact formulas are not specified.


Implementation-safe derived forms, only if investment-cost data exists:


$$roi\_circular\_investment = \frac{annual\_circular\_benefit}{investment\_cost\_basis}$$
**Source:** accounting/decision identities used by management layer; exact formula conventions are not clearly specified in provided resources.

**Why used:** Compares annual circular benefits to investment basis for digester and circular-policy ROI reporting.


$$payback\_period\_years = \frac{investment\_cost\_basis}{annual\_circular\_benefit}$$
**Source:** accounting/decision identities used by management layer; exact formula conventions are not clearly specified in provided resources.

**Why used:** Estimates years to recover circular capital from annual benefits for E4-style investment screens.


when `annual_circular_benefit > 0`.


These are reasonable accounting structures, but because the resources do not give the exact formula conventions, they should remain configurable.


#### 8.4 Recommendation ranking

Supported structure:


* classify issues into `Critical / Important / Advisory`
* rank by tier first, then by weighted objective importance

A general rule is:


$$recommendation\_score = f(severity,\ objective\_weights,\ persistence,\ expected\_benefit)$$
**Source:** accounting/decision identities used by management layer; exact formula conventions are not clearly specified in provided resources.

**Why used:** Ranks management alerts by severity and objective weights for Farm Manager advisory output.


The exact functional form is not clearly specified in the provided resources.


#### 8.5 Explicit thresholds from sources

Supported explicit control ranges:


* `biosecurity_level_pct`: `0–100%`
* `digester_capacity_pct`: `0–100%`
* breeding priority categories: `milk / disease / CH4`
* feed policy categories: `standard / amino-balanced`
* genetics market scenarios: `NM$ / CM$ / FM$ / GM$`

Exact thresholds for:


* switching recommendation tiers,
* auto-changing policies,
* declaring investment attractive,
* declaring profit unacceptable

are **not clearly specified in the provided resources**.


#### 8.6 Regulatory and circular-route policy gates
Farm Manager owns boolean policy switches that downstream agents must respect before activating circular routes:


* `cofeed_safety_approved` → Manure co-digestion and Dairy Processor feed-return routes
* `coproduct_feed_allowed` → Feed acceptance of whey/scotta and plant co-products
* `dairy_processor_unit_enabled` → maps to ROI `eqToggle_dairyprocessor`; default false
* `whey_processor_unit_enabled` → maps to ROI `eqToggle_whey`; default false
* `thermochemical_route_active` → Manure/Energy thermochemical path
* `sdg_reporting_mode` → optional narrative tags on dashboard summary only
**Source:** FAO (2025), Ch. 4 §§4.2–4.3; Ch. 1 §1.1 (SDG framing).


### 9. Data Requirements

Required input datasets / streams:


* user policy configuration
* daily milk output / milk revenue stream from Cow
* feed-cost stream from Feed
* disease alert and vet-cost stream from Disease
* weekly energy savings/credit stream from Energy
* monthly environmental KPI stream from Environment
* annual breeding recommendation stream from Genetics
* market-price stream
* by-product revenue stream
* filtered sensor-alert stream

Temporal resolution:


* daily for production and disease economics
* weekly for energy and recycling economics
* monthly for environmental and whole-farm reporting
* annual for breeding-policy review

Spatial resolution:


* farm-level management node
* no finer spatial decision layer is clearly specified

Preprocessing requirements:


* align all incoming streams to common reporting periods
* preserve source IDs for explanations
* store both current-period and cumulative values

Calibration requirements:


* milk price if revenue is not directly supplied
* investment cost basis for ROI/payback
* carbon-credit prices if monetized by Farm Manager
* recommendation-threshold settings
* objective weights

Internally simulatable:


* cash-balance tracking
* profit aggregation
* recommendation queueing
* alert prioritization
* policy packet dispatch

Missing-data handling:


* if price data missing, accept direct revenue packets where available
* if ROI inputs missing, keep `roi_circular_investment = null`
* if environmental KPIs missing, issue economics-only recommendations
* if Genetics annual review missing, retain prior breeding policy state

### 10. Edge Cases / Failure Conditions


* conflicting subsystem recommendations
* Detection: more than one recommended policy update targets the same control in opposite directions.
* Prevention: rank by tier and objective weights.
* Recovery: keep current policy if conflict unresolved; log for dashboard explanation.


* negative or undefined profit due to missing prices
* Detection: incomplete revenue/cost packet.
* Prevention: validate required accounting fields before monthly close.
* Recovery: publish low-confidence profitability state instead of fabricated values.


* double counting carbon credits
* Detection: Energy and Environment both supply monetized credits.
* Prevention: choose one final credit source in accounting layer.
* Recovery: reconcile and log.


* sensor alert overload
* Detection: high-frequency raw alerts arriving at Farm Manager Agent.
* Prevention: reject non-filtered sensor packets.
* Recovery: accept only filtered alert summary from the Sensors Agent.


* unstable policy oscillation
* Detection: same control flips repeatedly across adjacent periods.
* Prevention: add minimum persistence / hysteresis window.
* Recovery: freeze control until next review cycle.
* Exact hysteresis rule is not clearly specified in the provided resources.


* ROI requested with no investment-cost basis
* Detection: `investment_cost_basis` missing.
* Prevention: require scenario input.
* Recovery: publish ROI/payback as `null`.


* outbreak active but biosecurity unchanged
* Detection: active Disease alert with no policy review event.
* Prevention: forced recommendation generation on outbreak.
* Recovery: mark `Critical` issue and queue biosecurity recommendation.


* missing economy-layer packet
* Detection: Market Agent or Dairy Processor Agent fails to publish the current-period packet.
* Prevention: keep both agents instantiated in the base runtime, even when they are running in static-price or zero-flow mode.
* Recovery: mark the economic summary low-confidence for that period and continue with the available revenue/cost streams.

### 11. Direct Coding Guidance

Recommended module:


* `agents/farm_manager_agent.py`

Recommended class structure:


* `FarmManagerAgent`
* `FarmPolicyState`
* `EconomicLedger`
* `RecommendationItem`
* `DashboardSummaryPacket`

Recommended internal organization:


* policy state store
* revenue/cost ledgers by period
* KPI buffers by source
* prioritized recommendation queue
* downstream control packet builder

Recommended method layout:


```python
class FarmManagerAgent:
    def __init__(self, config):
        ...
    def receive_user_policy(self, policy_packet):
        ...
    def receive_cow_packet(self, packet):
        ...
    def receive_feed_packet(self, packet):
        ...
    def receive_disease_packet(self, packet):
        ...
    def receive_energy_packet(self, packet):
        ...
    def receive_environment_packet(self, packet):
        ...
    def receive_genetics_packet(self, packet):
        ...
    def receive_sensor_alerts(self, alert_packet):
        ...
    def receive_market_packet(self, packet):
        ...
    def update_cash_balance(self, period):
        ...
    def compute_profitability(self, period):
        ...
    def evaluate_circular_investment(self, period):
        ...
    def rank_management_issues(self, period):
        ...
    def generate_recommendations(self, period):
        ...
    def build_policy_change_triggers(self):
        ...
    def dispatch_policy_updates(self):
        ...
    def publish_dashboard_summary(self, period):
        ...```

Recommended update-loop order:


1. read user policy state
2. ingest current-period packets from Cow, Feed / Crop Agent, Disease, Energy, Environment, Market Agent, Dairy Processor Agent, Genetics, Sensors Agent
3. update revenue/cost ledgers
4. update farm cash balance
5. compute monthly/annual profit metrics
6. evaluate circular-investment metrics if enough inputs exist
7. rank issues by tier
8. generate filtered recommendations with explanation text
9. build downstream policy packet
10. publish dashboard summary

Execution priority:


* after operational agents publish current-period outputs
* after Environment publishes monthly KPIs
* before next-period policy-controlled agents step with revised settings

State-management rules:


* keep raw KPIs separate from interpreted recommendations
* keep accounting values separate from explanation text
* keep current policy separate from proposed policy
* store recommendation history for experiment comparison

Stochastic handling:


* none required by the provided resources
* Farm Manager Agent logic should remain deterministic unless optional price shocks from Market Agent are introduced upstream

Extensibility-safe additions:


* configurable recommendation rules
* richer scenario-comparison dashboards
* user approval workflow for policy changes
* optional sensitivity analysis over objective weights

Do not add without new sources:


* reinforcement learning controller
* black-box economic optimizer
* detailed financing/debt model
* raw PLF data fusion
* arbitrary score weights or recommendation thresholds

---

## Agent 9 — 📡 Sensors Agent

*Tag: Data/IoT*

### 1. Agent Purpose

The Sensors Agent is the system’s **precision-livestock measurement layer**.


It is a **new required agent** in the approved architecture because:


* the mindmap includes **Smart Technologies** as a farm input,
* the paper-analysis extracts from Zhang and Tedeschi require a distinct **PLF data pipeline**,
* and no existing HTML agent owns per-tick sensor acquisition, measurement noise, multi-sensor fusion, degradation, or THI computation.

Its role is to:


* run at **tick 0** before the daily operational update,
* acquire environmental and animal-linked sensor signals,
* convert raw signals into filtered measured states,
* compute `heat_stress_index (THI)` from temperature and relative humidity,
* overlay measurement error on observed DMI,
* track rumen-bolus degradation and replacement timing,
* detect or flag sensor-supported states such as estrus, SARA risk, and optional thermal mastitis alerts,
* and publish only the appropriate processed outputs to downstream agents.

Subsystem ownership:


* PLF sensing and measurement quality,
* multi-sensor fusion,
* sensor-health and degradation tracking,
* filtered alert generation,
* shared `heat_stress_index` production.

The approved architecture explicitly keeps this agent as a **measurement layer only; no resource transformation**.


It exists to solve a modeling gap:


* Feed, Cow, Disease, and Farm Manager need sensor-enhanced inputs,
* but the original HTML architecture does not provide a dedicated owner for data acquisition and filtering.

Supported outputs and interactions from the approved plan:


* to Cow: `DMI measured`, `BCS`, `rumen_pH`, `THI`, `estrus flag`
* to Feed: `NIR profile`, `heat stress flag`
* to Disease: `thermal mastitis signal` (optional)
* to Genetics: estrus/reproduction scheduling support
* to Farm Manager: **filtered alerts only**

Constraints:


* the Sensors Agent must not replace Cow, Feed, Disease, or Farm Manager logic,
* it should publish measured or inferred states, not final biological penalties or policy decisions,
* exact sensor hardware specifications, error distributions, and fusion-model formulas are **not clearly specified in the provided resources**.

### 2. Agent State Variables

#### 2.1 Environmental sensing state


* `ambient_temperature`: environmental temperature used for THI computation; units not clearly specified in the provided resources; type `float`; valid range not clearly specified; initialized from scenario/weather feed; updated at tick 0 daily; depends on external weather input; persistent history; dynamic.
* `relative_humidity_pct`: environmental humidity used for THI computation; units `%`; type `float`; valid range `0–100`; initialized from weather input; updated at tick 0 daily; persistent history; dynamic.
* `heat_stress_index_thi`: computed THI shared variable; units THI index; type `float`; valid range not clearly specified; initialized `null` or baseline; updated daily at tick 0; depends on temperature and humidity; persistent history; dynamic.
* `heat_stress_flag`: categorical or boolean heat-stress signal sent to Cow and Feed; valid range `{false,true}` or banded categories if configured; initialized `false`; updated daily; depends on THI thresholding; persistent history; dynamic.
* `season`: seasonal context used for NIR seasonality and shared environmental propagation; type `enum/string`; initialized from scenario; updated daily/weekly; externally owned but cached locally; persistent; dynamic.
* `weather_tick`: current weather-step identifier; type `int`; initialized from simulation kernel; updated daily/weekly; persistent; dynamic.

#### 2.2 Per-cow wearable / feeder measurement state


* `activity_signal[cow_id]`: wearable-derived activity measure; units not clearly specified; type `float`; valid range not clearly specified; initialized from baseline or empty signal; updated daily or sub-daily then aggregated to tick 0 output; persistent history; dynamic.
* `rumination_signal[cow_id]`: wearable-derived rumination measure; units not clearly specified; type `float`; valid range not clearly specified; initialized from baseline; updated daily; persistent history; dynamic.
* `rumination_change_pct[cow_id]`: percent deviation from baseline rumination; units `%`; type `float`; initialized `0`; updated daily; depends on current vs baseline rumination; persistent history; dynamic.
* `dmi_measured[cow_id]`: measured dry matter intake; units `kg DM/day`; type `float`; valid range `>=0`; initialized from first available reading; updated daily; depends on feeder measurement plus error overlay; persistent history; dynamic.
* `dmi_measurement_error[cow_id]`: sensor error applied to measured DMI; units `kg DM/day` or fraction depending on implementation; type `float`; valid range not clearly specified; initialized `0`; updated daily; depends on configured error model; persistent history; stochastic/calibration.
* `dmi_measurement_confidence[cow_id]`: confidence score for DMI measurement; type `float`; valid range not clearly specified; initialized baseline confidence; updated daily; depends on device health and missingness; persistent history; dynamic.
* `body_condition_score_measured[cow_id]`: CV-derived BCS estimate; units score; type `float`; valid range not clearly specified in the provided resources; initialized `null`; updated daily or when image inference runs; persistent history; dynamic.
* `body_weight_measured[cow_id]`: measured or CV-estimated body weight; units `kg`; type `float`; valid range `>=0`; initialized `null`; updated daily; persistent history; dynamic.

#### 2.3 Rumen bolus and pH state


* `rumen_ph_measured[cow_id]`: rumen pH measurement from bolus sensor; units `pH`; type `float`; valid range not explicitly specified for the ABM, but used with threshold logic below; initialized `null`; updated daily; persistent history; dynamic.
* `rumen_ph_noise_level[cow_id]`: measurement-noise intensity applied to rumen pH reading; type `float`; valid range not clearly specified; initialized low/baseline; updated daily; depends on bolus age; persistent history; dynamic.
* `rumen_bolus_age_ticks[cow_id]`: age of pH bolus sensor in ticks; units ticks; type `int`; valid range `>=0`; initialized `0` on installation/replacement; updated daily; persistent; dynamic.
* `rumen_bolus_health_state[cow_id]`: bolus status enum; valid values `{healthy, degrading, replacement_due}`; initialized `healthy`; updated daily; depends on age and replacement rule; persistent; dynamic.
* `sensor_replacement_due_flag[cow_id]`: whether a bolus replacement event should be triggered; type `bool`; initialized `false`; updated daily; becomes relevant at approximately `tick >= 80–90`; persistent history; dynamic.
* `low_ph_consecutive_ticks[cow_id]`: counter of consecutive ticks with `rumen_pH = 3 ticks`; persistent history; dynamic.

#### 2.4 Fusion and reproductive signal state


* `estrus_candidate_flag[cow_id]`: preliminary estrus candidate based on sensor evidence; type `bool`; initialized `false`; updated daily; depends on rumination change and available sensor inputs; transient + history; dynamic.
* `estrus_flag_single[cow_id]`: estrus output when using single-sensor logic; type `bool`; initialized `false`; updated daily; persistent history; dynamic.
* `estrus_flag_fused[cow_id]`: estrus output when fused-sensor logic is enabled; type `bool`; initialized `false`; updated daily; persistent history; dynamic.
* `estrus_reliability[cow_id]`: reliability/confidence of estrus detection; type `float`; supported anchor values are `0.85` for single-sensor mode and `0.95` for fused mode; initialized based on configured mode; updated daily; persistent history; dynamic.
* `fusion_mode`: sensor-fusion mode selector; enum; valid range `{single, fused}`; initialized from configuration; updated on configuration change; persistent; static/dynamic.
* `reproduction_signal_packet[cow_id]`: structured output for Genetics/Cow scheduling; type `dict`; initialized empty; updated when estrus is detected; transient + history; dynamic.

#### 2.5 Feed-quality sensing state


* `nir_feed_profile`: NIR-derived feed quality packet; type `dict`; initialized empty; updated daily or whenever feed batch changes; depends on available inline feed sensing; persistent history; dynamic.
* `nir_profile_valid_flag`: whether the NIR profile is usable for downstream Feed logic; type `bool`; initialized `false`; updated with each profile refresh; persistent history; dynamic.
* `nir_seasonality_context`: seasonality tag associated with the NIR profile; type `string/enum`; initialized from `season`; updated daily/weekly; persistent; dynamic.

#### 2.6 Disease-support sensing state


* `thermal_mastitis_signal[cow_id]`: optional thermal alert sent to Disease; type `bool` or scored event packet; initialized `false`; updated on event; transient + history; dynamic.
* `thermal_mastitis_confidence[cow_id]`: confidence score for mastitis alert; type `float`; supported as an optional high-accuracy alert channel with `>87%` accuracy; initialized `null`; updated on event; persistent history; dynamic.
* `disease_alert_packet[cow_id]`: structured alert packet sent to Disease; initialized empty; updated on event; transient + history; dynamic.

#### 2.7 Fleet-health and alert state


* `sensor_fleet_status`: whole-fleet health summary explicitly supported in the approved plan; type `dict`; initialized empty; updated daily; persistent history; dynamic.
* `filtered_alert_queue`: processed alert queue for downstream consumption; type `list`; initialized empty; updated daily/event-driven; persistent snapshots; dynamic.
* `farm_manager_alert_packet`: filtered alert packet sent to Farm Manager; type `dict`; initialized empty; updated on event/daily; transient + history; dynamic.
* `alert_count_total`: count of generated alerts in current period; type `int`; initialized `0`; updated daily/weekly; persistent history; dynamic.
* `bolus_age_summary`: fleet summary of bolus ages for dashboard/sensor-health reporting; type `dict`; initialized empty; updated daily; persistent history; dynamic.

#### 2.8 Variables with unsupported exact numeric definitions

The following exist conceptually but their exact ranges or formulas are **not clearly specified in the provided resources**:


* exact THI formula,
* exact THI-to-DMI/yield response coefficients,
* exact DMI error distribution,
* exact rumen pH noise-growth function after degradation starts,
* exact estrus fusion rule,
* exact mastitis thermal threshold,
* exact alert-priority scoring formula.

### 3. Agent Behaviors and Actions

#### 3.1 Core behaviors


* `ingest_environmental_inputs()`
* Trigger: start of tick 0 each day.
* Inputs: environmental temperature, relative humidity, season/weather context.
* Action: caches weather state for THI and NIR seasonality.
* Outputs: updated environmental sensor state.


* `compute_thi()`
* Trigger: after environmental input ingest.
* Inputs: temperature and humidity.
* Action: computes `heat_stress_index_thi`.
* Outputs: `heat_stress_index_thi`, `heat_stress_flag`.
* Constraint: exact THI formula is not clearly specified in the provided resources.


* `ingest_animal_sensor_channels()`
* Trigger: tick 0 each day.
* Inputs: wearable activity, rumination, feeder DMI observation, CV BCS/BW, rumen bolus pH.
* Action: records current raw measurements for each cow.
* Outputs: raw measurement cache.


* `overlay_dmi_measurement_error()`
* Trigger: after DMI ingest.
* Inputs: feeder DMI observation and configured error model.
* Action: publishes `dmi_measured` as an observed, potentially noisy quantity rather than a perfect latent state.
* Outputs: `dmi_measured`, confidence score.


* `update_bolus_age_and_health()`
* Trigger: daily.
* Inputs: current bolus ages.
* Action: increments bolus age, updates health state, begins degradation once age approaches `80–90` ticks.
* Outputs: `rumen_bolus_health_state`, `sensor_replacement_due_flag`, updated pH-noise level.


* `measure_rumen_ph_and_flag_sara()`
* Trigger: daily after bolus update.
* Inputs: pH reading and noise state.
* Action: updates `rumen_ph_measured`, increments/reset `low_ph_consecutive_ticks`, and flags SARA when the threshold is met.
* Outputs: `rumen_ph_measured`, `sara_risk_flag`.
* Supported threshold: `rumen_pH =3 ticks`.


* `update_nir_feed_profile()`
* Trigger: daily or feed-batch change.
* Inputs: NIR sensing and seasonal context.
* Action: refreshes `nir_feed_profile`.
* Outputs: feed-quality packet to Feed.


* `detect_estrus()`
* Trigger: daily after wearable input update.
* Inputs: rumination change and available sensor channels.
* Action: creates estrus candidate and final estrus flag in single or fused mode.
* Outputs: estrus packet to Cow and Genetics.
* Supported anchors:
* rumination drop `10–30%`
* `85%` single-sensor detection accuracy
* `95%` fused-sensor detection accuracy


* `detect_thermal_mastitis_optional()`
* Trigger: on thermal anomaly event if this feature is active.
* Inputs: thermal sensing stream.
* Action: creates optional mastitis alert.
* Outputs: disease alert packet.
* Supported anchor: optional accuracy `>87%`.


* `filter_and_publish_alerts()`
* Trigger: end of tick 0.
* Inputs: all derived sensor events.
* Action: sends measured states to biological/operational agents and filtered alerts to Farm Manager.
* Outputs:
* to Cow: measured DMI, BCS/BW, pH, THI, estrus flag, SARA risk
* to Feed: NIR profile, heat stress flag
* to Disease: thermal mastitis signal
* to Genetics: estrus/reproduction scheduling packet
* to Farm Manager: filtered alerts only

#### 3.2 Adaptive behaviors


* `increase_ph_noise_after_degradation()`
* Trigger: bolus age reaches degradation window `>=80–90 ticks`.
* Action: raises pH measurement noise until replacement occurs.
* Output: lower confidence pH signal and replacement event.


* `switch_single_to_fused_mode()`
* Trigger: multiple sensor channels available and fusion mode enabled.
* Action: updates estrus reliability from single-mode assumption to fused-mode assumption.
* Output: higher-confidence estrus flag.
* Exact fusion rule is not clearly specified.


* `emit_replacement_event()`
* Trigger: `sensor_replacement_due_flag=true`.
* Action: publishes maintenance/replacement event.
* Output: sensor-health update and optional replacement-cost event for management.
* Exact cost is not clearly specified.

#### 3.3 Failure-state behaviors


* `handle_missing_weather_inputs()`: suppress THI computation and publish null/low-confidence heat-stress state.
* `handle_missing_bolus_signal()`: do not infer SARA from absent pH data; preserve missing-state marker.
* `handle_partial_fusion_inputs()`: downgrade fused estrus request to single-sensor logic when only one stream is present.
* `handle_sensor_disagreement()`: preserve both raw evidence and lowered confidence rather than forcing a false certainty.
* `handle_alert_overproduction()`: keep only filtered alerts for Farm Manager Agent; raw stream remains inside the Sensors Agent.

### 4. Decision-Making Logic

The Sensors Agent is a **measurement, filtering, and inference layer**, not a policy optimizer.


#### 4.1 Decision architecture

The approved architecture supports this sequence:


1. acquire environment and raw device inputs
2. compute THI
3. age and degrade sensors
4. construct measured states with error/quality overlays
5. apply threshold or fusion logic
6. produce filtered outputs for downstream agents

#### 4.2 THI logic

THI behavior inferred from available sources:


* compute `THI` from temperature and relative humidity
* use THI thresholds to drive heat-stress signaling to Cow and Feed

Not fully specified:


* exact THI formula
* exact threshold bands in the extracted paper text
* exact THI-to-DMI/yield penalty coefficients

The approved plan allows implementation with **cited bands `68/72` or calibrated thresholds**, but the extracted paper text did not fully quantify the full response function.


#### 4.3 SARA logic

Supported deterministic rule:


* if `rumen_pH =3 ticks`, publish a SARA-risk flag

The Sensors Agent does not apply the milk/FCR penalty itself.

It only publishes the state signal so Cow/Feed can react.


#### 4.4 Estrus fusion logic

Estrus-fusion behavior inferred from available sources:


* estrus-related signal can be derived from rumination change
* rumination decrease of `10–30%` is the supported behavioral indicator
* single-sensor detection accuracy anchor: `85%`
* fused-sensor detection accuracy anchor: `95%`

Not clearly specified:


* exact mathematical classifier,
* exact combination of channels in fused mode,
* exact false-positive and false-negative rates by farm context.

Implementation-safe rule:


* use a configurable fusion pipeline,
* keep `estrus_reliability` explicit,
* and never treat fused mode as perfect.

#### 4.5 Mastitis alert logic

Supported:


* optional thermal mastitis signal to Disease
* supported accuracy anchor `>87%`

Not clearly specified:


* exact temperature threshold,
* exact persistence rule,
* exact handling of false positives.

#### 4.6 DMI measurement-error logic

Supported:


* DMI should be measured through the Sensors layer with an explicit **measurement error overlay**

Not clearly specified:


* exact error distribution,
* whether error is additive or multiplicative,
* whether error depends on sensor age or cow behavior.

Implementation-safe rule:


* store both measured value and confidence,
* keep latent biological state outside Sensors,
* and treat sensor DMI as an observed estimate.

### 5. Agent Interactions

#### Incoming dependencies


* weather/scenario context → Sensors
* Frequency: daily/seasonal
* Data: temperature, relative humidity, season/weather tick
* Impact: THI and NIR seasonality


* simulated device channels / raw sensing layer → Sensors
* Frequency: tick 0 daily
* Data: activity, rumination, feeder DMI, CV BCS/BW, rumen bolus pH, optional thermal signal
* Impact: measured-state construction


* feed-batch context → Sensors
* Frequency: daily or batch change
* Data: feed material available for NIR profiling
* Impact: NIR packet validity

#### Outgoing dependencies


* Sensors → Cow
* Frequency: daily
* Data: `DMI measured`, `BCS`, `rumen_pH`, `THI`, `estrus flag`, `SARA risk`
* Impact: better state estimation and physiology-context updates


* Sensors → Feed
* Frequency: daily
* Data: `NIR profile`, `heat stress flag`
* Impact: PAN adjustment and heat-stress compensatory diet response


* Sensors → Disease
* Frequency: event-driven
* Data: `thermal mastitis signal`
* Impact: early disease-support alerting


* Sensors → Genetics
* Frequency: event-driven / reproductive schedule
* Data: estrus/reproduction scheduling flag
* Impact: breeding/reproduction timing support


* Sensors → Farm Manager
* Frequency: event-driven / daily summary
* Data: filtered alerts only, plus fleet-health summaries if desired
* Impact: management awareness without raw sensor overload


* Sensors → shared environment
* Frequency: daily
* Data: `heat_stress_index`
* Impact: Cow and Feed use the same shared heat-stress state

#### Synchronization rules


* Sensors runs at **tick 0**, before the daily feed-health-cow sequence.
* Cow and Feed should consume sensor outputs in the same day’s update.
* Disease event alerts can be consumed immediately or at next daily health update.
* Farm Manager receives filtered summaries, not raw measurement streams.

#### Failure-handling logic


* if sensor confidence is low, publish degraded-confidence measurements rather than fabricated clean data
* if bolus replacement is overdue, keep pH available only if configuration allows degraded readings
* if thermal mastitis sensing is disabled, publish no disease alert rather than a null classifier result

### 6. Environmental Integration

The Sensors Agent is environmentally coupled through **heat stress and seasonal sensing**, not through direct emissions.


Environmental inputs:


* temperature
* relative humidity
* season/weather tick

Environmental outputs:


* `heat_stress_index (THI)` to shared environment
* heat-stress flags to Cow and Feed

Environmental feedback loops:


* higher THI changes Cow DMI/yield behavior through Cow
* Feed receives heat-stress context and can increase energy density or otherwise adjust ration logic
* seasonal conditions influence NIR feed-profile interpretation

Resource production/consumption:


* none directly
* Sensors does not create or transform feed, manure, energy, or emissions

Carrying-capacity or climate-threshold relationships:


* not clearly specified beyond the existence of THI thresholds and seasonal variation

### 7. Genetic / Evolutionary Logic (If Applicable)

The Sensors Agent has no direct genetic or evolutionary mechanism (not clearly specified in the provided resources).


Indirect supported role:


* estrus/reproduction scheduling signals can be sent to Genetics or reproduction scheduling logic
* this affects when breeding events are recognized, not how inheritance works

Not supported here:


* genome representation
* mutation
* crossover
* selection
* breeding-value computation

### 8. Equations / Algorithms / Thresholds

#### 8.1 THI computation

Supported structure:

$$heat\_stress\_index = f(temperature,\ relative\_humidity)$$
**Source:** sensor/PLF thresholds and degradation notes from project-analysis extracts; exact coefficient/form not provided in sources.

**Why used:** Derives THI from temperature and humidity so Cow can apply documented heat-stress intake and milk penalties.


The exact formula is not clearly specified in the provided resources.


Supported implementation note from the approved plan:


* use cited threshold bands `68/72` if adopted,
* otherwise treat THI thresholds as calibrated inputs.

#### 8.2 DMI measurement model

Supported structure:

$$dmi\_measured = dmi\_observed + error$$
**Source:** sensor/PLF thresholds and degradation notes from project-analysis extracts; exact coefficient/form not provided in sources.

**Why used:** Adds observation error to true DMI for Sensors→Cow state estimation and Genetics record quality.


or an equivalent configurable observation model.


The exact error distribution is not clearly specified in the provided resources.


#### 8.3 Rumen-bolus degradation

Supported rule:


* after approximately `80–90 ticks`, rumen-bolus pH noise increases until replacement event

Implementation form:

$$rumen\_ph\_noise\_level = g(bolus\_age)$$
**Source:** sensor/PLF thresholds and degradation notes from project-analysis extracts; exact coefficient/form not provided in sources.

**Why used:** Models bolus-age degradation so low-pH SARA flags reflect sensor confidence, not raw readings alone.


for `bolus_age >= degradation_threshold`.


The exact function `g()` is not clearly specified in the provided resources.


#### 8.4 SARA threshold

Supported deterministic threshold:

$$\text{if } rumen\_pH 87%`

Exact thermal threshold and window are not clearly specified in the provided resources.


### 9. Data Requirements

Required inputs:


* daily environmental temperature
* daily relative humidity
* daily/near-daily activity signal
* daily/near-daily rumination signal
* daily feeder DMI observations
* daily CV or image-derived BCS/BW estimates
* daily rumen bolus pH readings
* feed-batch NIR sensing input
* optional thermal mastitis stream
* season/weather index

Temporal resolution:


* **tick 0 daily** for all sensor acquisition
* event-driven for mastitis alerts and replacement events
* daily/weekly summaries for fleet-health reporting

Spatial resolution:


* per cow for wearable, feeder, CV, pH, estrus, mastitis
* farm-environment level for temperature/humidity

Requires external calibration:


* THI formula if not predefined elsewhere
* THI thresholds if not using the cited `68/72` bands
* DMI error model
* pH-noise degradation curve
* mastitis classifier threshold
* estrus fusion rule
* alert filtering rules

Can be simulated internally:


* bolus age tracking
* replacement timing window
* SARA threshold logic
* estrus confidence mode switching
* filtered alert routing

Missing-data handling:


* missing weather: suppress THI
* missing pH: suppress SARA detection
* missing second signal in fused mode: downgrade to single-sensor mode
* missing NIR: keep prior feed profile only if staleness handling is configured; otherwise mark invalid

### 10. Edge Cases / Failure Conditions


* missing temperature or humidity
* Detection: null weather fields at tick 0
* Prevention: schema validation
* Recovery: publish `heat_stress_index = null` and low-confidence heat-stress state


* bolus age exceeds replacement window but still used as clean data
* Detection: `rumen_bolus_age_ticks >= degradation_threshold`
* Prevention: mandatory degradation-state update before pH publish
* Recovery: increase noise, lower confidence, emit replacement event


* false SARA due to noisy degraded pH signal
* Detection: repeated low pH only after degradation onset with low confidence
* Prevention: carry confidence alongside pH
* Recovery: publish `sara_risk_flag` with degraded-confidence marker


* fused estrus requested with only one usable signal
* Detection: missing second channel
* Prevention: fusion-input validation
* Recovery: downgrade to single-mode reliability `0.85`


* contradictory sensor signals
* Detection: estrus candidate from one channel but not others
* Prevention: explicit fusion mode and confidence output
* Recovery: keep candidate state without hard flag if rule requires corroboration


* mastitis classifier enabled without thermal stream
* Detection: feature on, no thermal input
* Prevention: feature-availability check
* Recovery: disable mastitis alert for that period


* Farm Manager alert overload
* Detection: too many raw events in a short period
* Prevention: publish filtered alerts only
* Recovery: batch and summarize alerts before dispatch


* stale NIR profile
* Detection: profile age exceeds freshness window
* Prevention: timestamp every profile
* Recovery: mark `nir_profile_valid_flag=false`

### 11. Direct Coding Guidance

Recommended module:


* `agents/sensors_agent.py`

Recommended class structure:


* `SensorsAgent`
* `SensorFleetState`
* `CowSensorSnapshot`
* `FilteredAlert`
* `ReproductionSignalPacket`

Recommended internal state split:


* environmental sensing state
* per-cow measurement cache
* bolus-health registry
* fusion/alert state
* fleet-health summary

Recommended update-loop order:


1. ingest weather and season context
2. compute THI
3. ingest raw wearable / feeder / CV / pH / thermal streams
4. increment bolus ages and update degradation state
5. overlay DMI measurement error
6. compute rumen pH outputs and SARA-risk flags
7. update NIR feed profile
8. detect estrus in single or fused mode
9. emit optional thermal mastitis alerts
10. build filtered outputs for Cow, Feed, Disease, Genetics, and Farm Manager
11. update fleet-health summary and replacement events

Recommended APIs:


```python
class SensorsAgent:
    def receive_weather(self, temperature, relative_humidity, season, weather_tick): ...
    def receive_raw_cow_signals(self, cow_signal_packet): ...
    def receive_feed_sensing(self, nir_packet): ...
    def step_tick0(self, current_tick): ...
    def publish_cow_measurements(self): ...
    def publish_feed_measurements(self): ...
    def publish_disease_alerts(self): ...
    def publish_genetics_signals(self): ...
    def publish_manager_alerts(self): ...```

Execution priority:


* before Feed and Cow daily logic
* before Disease uses sensor-driven mastitis signals
* before Farm Manager receives alert summaries

State-management rules:


* keep raw sensor readings separate from filtered downstream packets
* keep measured states separate from latent biological truth
* keep confidence attached to any inferred state
* store sensor-health variables independently from animal states

Persistence rules:


* persist per-cow sensor histories
* persist bolus age and replacement history
* persist alert history and confidence
* persist THI time series

Stochastic handling:


* allowed only for observation error or classifier uncertainty if explicitly configured
* do not add unsupported random sensor behaviors beyond the measurement-error layer already justified by the approved plan

Extensibility-safe additions:


* additional wearable channels
* richer confidence scoring
* barn-level microclimate inputs
* more formal sensor-fleet maintenance scheduling

Do not add without new sources:


* proprietary ML classifier structures
* detailed image-model architectures
* exact thermal mastitis decision boundaries
* raw-behavior time-budget ontologies as a replacement for this PLF layer
* direct autonomous management decisions from sensors alone

---

## Agent 10 — 💧 Water Agent

*Tag: Resource*

### 1. Agent Purpose

The Water Agent is a **base-runtime circular-resource agent** that owns the farm’s **water-use and water-recycling loop**.


The original HTML architecture defines it as the agent that:


* tracks drinking, cleaning, and irrigation water use,
* models treatment-plant recycling,
* models nutrient recovery,
* and adds the water circularity loop.

The mindmap reinforces the same loop:


* clean water is used for **drinking, milking, and cleaning**,
* dirty water is collected and treated on-farm,
* treated water is recycled for irrigation,
* and nutrients are recovered during treatment.

Its responsibilities are to:


* track farm water demand by use type,
* collect wastewater from farm operations,
* treat wastewater,
* recycle treated water back to cropland irrigation,
* publish water-footprint metrics to Environment,
* and expose optional nutrient-recovery flows to Feed / Crop Agent.

Why this agent exists:


* the source architecture includes this water-loop module,
* the mindmap includes a full water-recycling loop,
* and the approved plan keeps it as the owner of drinking, cleaning, irrigation, and treatment recycle in the project runtime.

Modeling problem solved:


* without this agent, the model can report overall environmental KPIs, but cannot close the explicit **water circularity loop** shown in the source architecture.

Subsystem ownership:


* water demand accounting,
* wastewater collection,
* treatment and recycle state,
* irrigation reuse,
* water-footprint reporting.

Dependencies:


* Cow Agent for drinking-water demand and wastewater source context,
* Feed / Crop Agent for irrigation demand,
* Environment Agent for water-footprint reporting,
* Farm Manager Agent policy and Feed / Crop Agent diet policy for the optional amino-acid-balancing water effect.

Constraints:


* exact drinking-water equations,
* exact wastewater-return fractions,
* exact treatment efficiency,
* exact nutrient-recovery composition,
* and exact water-cost economics

are **not clearly specified in the provided resources**.


The only paper-backed quantitative enhancement routed through the approved plan is:


* under amino-acid-balancing policy, water use decreases by **21 L/day**,
* but the exact scaling basis is **not clearly specified in the provided resources**.

Expected outputs:


* `total_water_use_l`
* `drinking_water_l`
* `cleaning_water_l`
* `irrigation_water_l`
* `wastewater_volume_l`
* `treated_water_l`
* `recycled_irrigation_l`
* `water_use_l_per_litre_milk`
* optional `nutrient_recovery_packet`

Contribution to global system behavior:


* closes the optional water loop,
* reduces net freshwater withdrawal when recycling is active,
* provides the Environment Agent with the water-use KPI listed in the HTML dashboard,
* and gives Feed / Crop Agent an irrigation-reuse channel.

### 2. Agent State Variables

#### 2.1 Demand-side water variables


* `drinking_water_l`: water allocated to cow drinking; units `L/day`; type `float`; valid range `>=0`; initialize `0`; update daily; depends on Cow population and Cow demand packet; persistent history; dynamic.
* `cleaning_water_l`: water allocated to milking-parlor and barn cleaning; units `L/day`; type `float`; valid range `>=0`; initialize `0`; update daily; depends on farm operational cleaning demand; persistent history; dynamic.
* `irrigation_water_demand_l`: crop irrigation demand; units `L/day` or `L/tick`; type `float`; valid range `>=0`; initialize `0`; update daily/weekly; depends on Feed / Crop Agent irrigation request; persistent history; dynamic.
* `total_water_use_l`: total water used across drinking, cleaning, and irrigation before netting recycled reuse; units `L/day`; type `float`; valid range `>=0`; initialize `0`; update daily; persistent history; dynamic.
* `freshwater_withdrawal_l`: new incoming water drawn before treatment/reuse accounting; units `L/day`; type `float`; valid range `>=0`; initialize `0`; update daily; depends on unmet demand after reuse allocation; persistent history; dynamic.

#### 2.2 Wastewater and treatment variables


* `wastewater_volume_l`: total wastewater collected on-farm; units `L/day`; type `float`; valid range `>=0`; initialize `0`; update daily; depends on drinking/cleaning use and any return-flow assumptions; persistent history; dynamic.
* `treatment_active_flag`: whether the treatment/recycling pathway is active; type `bool`; initialize from scenario/config; update on policy/config change; persistent; dynamic.
* `treated_water_l`: treated water available after wastewater processing; units `L/day`; type `float`; valid range `>=0`; initialize `0`; update daily/weekly; depends on wastewater volume and treatment process; persistent history; dynamic.
* `treatment_recovery_fraction`: fraction of wastewater converted to reusable treated water; units fraction; type `float`; valid range `0–1`; initialize from configuration; update only if recalibrated; persistent; calibration.
* `wastewater_storage_l`: buffered untreated wastewater volume if treatment is not immediate; units `L`; valid range `>=0`; initialize `0`; update daily; persistent; dynamic.

#### 2.3 Reuse and crop-support variables


* `recycled_irrigation_l`: treated water sent back to cropland irrigation; units `L/day`; type `float`; valid range `>=0`; initialize `0`; update daily/weekly; depends on treated-water availability and irrigation demand; persistent history; dynamic.
* `recycled_irrigation_fraction`: share of irrigation demand met by treated water; units fraction; type `float`; valid range `0–1`; initialize `0`; update daily/weekly; depends on `recycled_irrigation_l` and irrigation demand; persistent history; dynamic.
* `nutrient_recovery_packet`: optional recovered-nutrient packet from treated water; type `dict`; initialize empty; update daily/weekly if enabled; depends on treatment outputs; persistent history; dynamic.
* `crop_irrigation_delivery_packet`: structured output to Feed / Crop Agent containing recycled water supplied; type `dict`; initialize empty; update daily/weekly; transient + history; dynamic.

#### 2.4 Environmental-reporting variables


* `water_use_l_per_litre_milk`: environmental KPI explicitly listed in HTML; units `L/litre milk`; type `float`; valid range `>=0`; initialize `null` or `0`; update daily/monthly; depends on total water use and milk output denominator; persistent history; dynamic.
* `milk_output_litres`: denominator used for water-intensity calculation; units `L/day` or `L/month`; type `float`; valid range `>=0`; initialize `0`; update daily/monthly; depends on Cow output packet; persistent history; dynamic.
* `water_environment_packet`: structured output to Environment; type `dict`; initialize empty; update daily/monthly; persistent snapshots; dynamic.
* `net_freshwater_use_l`: freshwater withdrawal after reuse credit; units `L/day`; type `float`; valid range `>=0`; initialize `0`; update daily; depends on reuse allocation; persistent history; dynamic.

#### 2.5 Policy-linked variables


* `amino_acid_policy_active`: whether the amino-acid-balancing policy is active; type `bool`; initialize from Feed / Crop Agent or Farm Manager Agent policy; update on policy changes; persistent; dynamic.
* `water_saving_from_aa_l_per_day`: supported water-reduction anchor from the approved plan; units `L/day`; type `float`; initialize `21`; static calibration constant; persistent; calibration.
* `aa_water_adjustment_applied`: whether the current tick’s water-use adjustment has been applied; type `bool`; initialize `false`; update daily; transient + history; dynamic.

#### 2.6 Variables not numerically specified enough for hardcoding


* exact drinking-water demand per cow,
* exact cleaning-water demand formula,
* exact wastewater-return ratio,
* exact nutrient recovery mass,
* exact treatment efficiency,
* exact irrigation demand model,
* exact water-cost model

are **not clearly specified in the provided resources** and should remain configurable.


### 3. Agent Behaviors and Actions

#### 3.1 Core behaviors


* `ingest_cow_water_demand()`
* Trigger: daily.
* Inputs: cow drinking-water demand or herd drinking-water packet.
* Action: updates `drinking_water_l`.
* Outputs: demand-side water state.


* `ingest_cleaning_demand()`
* Trigger: daily.
* Inputs: milking and cleaning demand context.
* Action: updates `cleaning_water_l`.
* Outputs: cleaning-water state.


* `ingest_irrigation_demand()`
* Trigger: daily/weekly.
* Inputs: Feed / Crop Agent irrigation request.
* Action: updates `irrigation_water_demand_l`.
* Outputs: irrigation-demand state.


* `apply_policy_water_adjustment()`
* Trigger: daily after demand ingest.
* Inputs: `amino_acid_policy_active`.
* Action: if active, applies the paper-backed water reduction anchor.
* Outputs: adjusted water-demand total.
* Constraint: exact scaling basis of the `21 L/day` reduction is not clearly specified.


* `compute_total_water_use()`
* Trigger: daily.
* Inputs: drinking, cleaning, irrigation demands.
* Action: computes aggregate water use.
* Outputs: `total_water_use_l`.


* `collect_wastewater()`
* Trigger: daily after use accounting.
* Inputs: water-use categories and wastewater assumptions.
* Action: computes wastewater available for treatment.
* Outputs: `wastewater_volume_l`.


* `treat_wastewater()`
* Trigger: daily/weekly when treatment active.
* Inputs: `wastewater_volume_l`, treatment parameters.
* Action: converts wastewater into treated reusable water.
* Outputs: `treated_water_l`, optional nutrient-recovery packet.


* `allocate_recycled_water_to_irrigation()`
* Trigger: after treatment.
* Inputs: treated water and irrigation demand.
* Action: sends reused water to Feed / Crop Agent irrigation.
* Outputs: `recycled_irrigation_l`, crop delivery packet.


* `compute_water_intensity()`
* Trigger: daily/monthly reporting.
* Inputs: `total_water_use_l`, `milk_output_litres`.
* Action: computes `water_use_l_per_litre_milk`.
* Outputs: environmental KPI.


* `publish_environment_packet()`
* Trigger: end of reporting cycle.
* Outputs: water footprint and reuse metrics to Environment.

#### 3.2 Adaptive behaviors


* `prioritize_recycled_water_for_irrigation()`
* Trigger: treated water available and irrigation demand > 0.
* Action: allocates recycled water to crop irrigation before new freshwater is assigned.
* Support: directly grounded in the mindmap statement “recycled for irrigation.”


* `activate_treatment_recycle_loop()`
* Trigger: Water Agent enabled and treatment active.
* Action: closes the water loop from wastewater to irrigation.
* Support: source architecture water-loop purpose and mindmap loop.


* `publish_nutrient_recovery_if_enabled()`
* Trigger: treatment run completes.
* Action: sends recovered nutrient signal to Feed / Crop Agent if the model enables that packet.
* Constraint: exact nutrient composition is not clearly specified.

#### 3.3 Failure-state behaviors


* `handle_missing_irrigation_request()`: if no Crop demand exists, treated water is held or reported as unused treated water.
* `handle_missing_milk_output()`: suppress `L/litre milk` KPI and publish absolute water totals only.
* `handle_treatment_inactive()`: wastewater is accumulated or discarded from loop accounting; no recycled irrigation is sent.
* `handle_negative_water_balance()`: clamp negative reuse or withdrawal values to zero and log anomaly.

### 4. Decision-Making Logic

The Water Agent is a **deterministic water-balance and recycle-allocation agent**.


#### 4.1 Decision architecture


1. read drinking, cleaning, and irrigation demand
2. apply amino-acid-policy water adjustment if active
3. compute total water use
4. collect wastewater
5. treat wastewater if treatment loop active
6. allocate treated water to irrigation
7. compute net freshwater use and water intensity
8. publish environmental and crop-support outputs

#### 4.2 Allocation logic

The strongest supported reuse rule is:


* treated water goes back to **irrigate cropland**

So the agent should prioritize:


1. treatment output generation
2. irrigation reuse allocation
3. remaining unmet irrigation demand from freshwater sources

No alternative reuse routing hierarchy is specified in the provided resources.


#### 4.3 Policy-linked logic

The approved plan links amino-acid balancing to:


* lower CP,
* reduced urinary N,
* and a **21 L/day water-use calibration anchor**

Therefore Water may apply a configurable policy-linked water-use adjustment when that flag is active.


The exact placement of that reduction across:


* drinking,
* cleaning,
* or irrigation

is **not clearly specified in the provided resources**.

Implementation-safe choice:


* apply it to a dedicated `policy_water_adjustment` term before final total reporting.

#### 4.4 Constraint handling

If treatment data is incomplete:


* keep physical water-use accounting active,
* suppress recycled-water and nutrient-recovery outputs,
* and continue publishing water footprint.

### 5. Agent Interactions

#### Incoming dependencies


* Cow → Water
* Frequency: daily
* Data: drinking-water demand and/or wastewater source context
* Impact: sets animal-side water use


* Feed/Crop → Water
* Frequency: daily/weekly
* Data: irrigation demand
* Impact: sets crop-side water need


* Feed/Farm Manager → Water
* Frequency: policy event
* Data: amino-acid-balancing flag
* Impact: passes through the supported `21 L/day` calibration anchor under configured scaling


* simulation/environment context → Water
* Frequency: daily/weekly
* Data: optional operational cleaning demand context
* Impact: sets cleaning-water use

#### Outgoing dependencies


* Water → Crop/Feed
* Frequency: daily/weekly
* Data: recycled irrigation water, optional nutrient-recovery packet
* Impact: supports irrigation loop and optional nutrient feedback


* Water → Environment
* Frequency: daily/monthly
* Data: total water use, net freshwater use, `L/litre milk`, recycled-water metrics
* Impact: water-footprint KPI


* Water → Cow
* Frequency: daily if modeled as explicit supply
* Data: delivered drinking water
* Impact: optional direct supply confirmation

#### Synchronization rules


* Water should run after Cow and Crop/Feed publish current demand packets.
* Water should publish to Environment before monthly environmental aggregation.
* Recycled irrigation should be available before or during the next Crop/Feed irrigation update, depending on simulation scheduling.

#### Failure-handling logic


* if Crop/Feed is inactive, Water still publishes footprint to Environment
* if Water Agent is disabled, Environment omits water KPI instead of inventing zero use

### 6. Environmental Integration

This agent’s main environmental role is to support the KPI:


* `Water use (L/litre milk)`

Environmental inputs:


* milk output denominator from Cow
* irrigation demand context from Crop/Feed

Environmental outputs:


* total water use
* net freshwater use
* treated/recycled water volume
* `water_use_l_per_litre_milk`

Environmental feedback loops:


* Cow → Water → treatment → irrigation → Crop/Feed
* Feed amino-acid policy → Water demand reduction
* Water → Environment footprint accounting

Resource consumption/production:


* consumes freshwater and wastewater treatment capacity
* produces treated water for irrigation reuse
* optionally produces nutrient-recovery packet

Carrying-capacity or water-scarcity thresholds:


* **Not clearly specified in the provided resources.**

### 7. Genetic / Evolutionary Logic (If Applicable)

The Water Agent has no direct genetic or evolutionary logic.


Indirectly:


* feed policy and cow productivity affect water intensity,
* but no inherited trait, mutation, crossover, or selection rule belongs here.

### 8. Equations / Algorithms / Thresholds

#### 8.1 Total water-use accounting

Supported structure:

$$total\_water\_use_l = drinking\_water_l + cleaning\_water_l + irrigation\_water_l$$
**Source:** architecture/mindmap water-loop accounting; numeric treatment/scaling coefficients require external calibration.

**Why used:** Sums farm water demand streams for Water Agent balance and Environment water-intensity denominators.


#### 8.2 Wastewater treatment structure

Supported loop structure:

$$treated\_water_l = wastewater\_volume_l \times treatment\_recovery\_fraction$$
**Source:** architecture/mindmap water-loop accounting; numeric treatment/scaling coefficients require external calibration.

**Why used:** Converts wastewater volume to recoverable treated water for the reuse loop.


The existence of treatment and recycle is supported.

The exact numeric `treatment_recovery_fraction` is **not clearly specified in the provided resources**.


#### 8.3 Recycled irrigation allocation

Supported structure:

$$recycled\_irrigation_l = \min(treated\_water_l,\ irrigation\_water\_demand_l)$$
**Source:** architecture/mindmap water-loop accounting; numeric treatment/scaling coefficients require external calibration.

**Why used:** Allocates treated water to irrigation demand without exceeding available recovery.


$$net\_freshwater\_use_l = total\_water\_use_l - recycled\_irrigation_l$$
**Source:** architecture/mindmap water-loop accounting; numeric treatment/scaling coefficients require external calibration.

**Why used:** Reports freshwater draw after on-farm reuse for net water-footprint KPIs.


#### 8.4 Water-intensity KPI

Supported directly by HTML dashboard metric:

$$water\_use\_l\_per\_litre\_milk = \frac{total\_water\_use_l}{milk\_output\_litres}$$
**Source:** architecture/mindmap water-loop accounting; numeric treatment/scaling coefficients require external calibration.

**Why used:** Computes litres of water per litre of milk for dashboard water-intensity reporting.


if `milk_output_litres > 0`.


#### 8.5 Amino-acid-policy adjustment

Supported anchor from approved plan:


* `21 L/day` is the cited water-use calibration anchor associated with the amino-acid-balancing policy.
* The provided resources do not specify whether that anchor applies per cow, per herd, per ration change, or under another scaling basis.

Implementation should therefore keep `21 L/day` as a configurable calibration input tied to the amino-acid policy flag and require an explicit scaling mode before translating it into an operational adjustment.


#### 8.6 Unsupported exact thresholds

Do not invent:


* minimum treatment efficiency,
* wastewater nutrient concentrations,
* irrigation sufficiency thresholds,
* water-scarcity stress thresholds,
* water pricing formulas.

These are **not clearly specified in the provided resources**.


### 9. Data Requirements

Required input datasets / packets:


* herd drinking-water demand or per-cow drinking-water totals
* farm cleaning-water demand
* Crop/Feed irrigation-demand packet
* milk-output denominator from Cow
* amino-acid-policy flag from Feed/Farm Manager
* treatment system on/off state
* optional nutrient-recovery schema

Temporal resolution:


* daily for drinking, cleaning, wastewater, and water-use accounting
* daily/weekly for irrigation demand and recycled irrigation delivery
* monthly for water-intensity reporting to Environment

Spatial resolution:


* farm-level water loop
* no field-level irrigation parcel geometry is clearly specified

Variables requiring external calibration:


* treatment recovery fraction
* wastewater-return fraction
* nutrient recovery amounts
* allocation of the `21 L/day` amino-acid-policy effect

Variables simulatable internally:


* water-balance bookkeeping
* treatment/reuse routing
* recycled-irrigation allocation
* `L/litre milk` metric

Missing-data handling:


* missing milk output → absolute water totals only
* missing irrigation demand → no recycled-water dispatch
* missing treatment parameters → no recycle loop, but still track use
* missing policy flag → no amino-acid water adjustment

### 10. Edge Cases / Failure Conditions


* zero milk output denominator
* Detection: `milk_output_litres == 0`
* Prevention: guarded division
* Recovery: publish absolute water totals only


* treated water exceeds irrigation demand
* Detection: `treated_water_l > irrigation_water_demand_l`
* Prevention: `min()` allocation
* Recovery: store/report surplus treated water


* negative freshwater use after reuse
* Detection: `net_freshwater_use_l < 0`
* Prevention: bounded allocation
* Recovery: clamp to zero and log anomaly


* treatment inactive but recycle requested
* Detection: `treatment_active_flag = false` with irrigation reuse call
* Prevention: feature flag check
* Recovery: set `recycled_irrigation_l = 0`


* amino-acid policy active but scaling ambiguous
* Detection: policy flag on and no scaling mode configured
* Prevention: require explicit configuration of how `21 L/day` is applied
* Recovery: hold adjustment in a separate report field or apply at farm level with warning


* missing wastewater-return assumptions
* Detection: no rule for converting use to wastewater
* Prevention: configuration validation
* Recovery: treat wastewater as externally supplied packet or disable treatment loop

### 11. Direct Coding Guidance

Recommended module:


* `agents/water_agent.py`

Recommended class structure:


* `WaterAgent`
* `WaterDemandPacket`
* `WastewaterTreatmentState`
* `WaterEnvironmentPacket`

Recommended internal state split:


* use-side demand accounting
* treatment/recycle state
* irrigation-reuse state
* environmental reporting state

Recommended update-loop order:


1. receive cow drinking-water demand
2. receive cleaning-water demand
3. receive crop irrigation demand
4. receive milk-output denominator
5. apply amino-acid-policy adjustment if active
6. compute total water use
7. collect wastewater
8. treat wastewater if enabled
9. allocate treated water to irrigation
10. compute net freshwater use and `L/litre milk`
11. publish to Crop/Feed and Environment

Recommended APIs:


```python
class WaterAgent:
    def receive_cow_water_packet(self, packet): ...
    def receive_irrigation_demand(self, packet): ...
    def receive_policy_context(self, amino_acid_policy_active): ...
    def receive_milk_output(self, milk_litres): ...
    def step(self): ...
    def publish_crop_irrigation_packet(self): ...
    def publish_environment_packet(self): ...```

Execution priority:


* after Cow and Crop/Feed demand generation
* before Environment monthly footprint rollup

State-management rules:


* keep gross water use separate from net freshwater use
* keep treated water separate from recycled irrigation actually delivered
* keep policy-driven adjustment separate from physical wastewater treatment logic

Stochastic handling:


* none required by the provided resources

Extensibility-safe additions:


* explicit water-cost accounting
* field-level irrigation scheduling
* richer nutrient-recovery schema
* water-scarcity scenarios

Do not add without new sources:


* physiological cow water-intake equations,
* wastewater chemistry model,
* treatment-plant kinetics,
* precise nutrient-recovery factors,
* water-market pricing or scarcity economics.

---

## Agent 11 — 🏭 Dairy Processor Agent

*Tag: Routing / Valorization*

This base runtime module keeps the by-product circular loop inside the project scope and now uses market-facing dairy product series from `dairy-situation-glance.csv` for valuation, plus solids/conversion anchors from the USDA ERS dairy sector model documentation.


> **Note:** **Dashboard ROI opt-in rule (do not invent differently):** In the dairy bioeconomy dashboard Equipment ROI section, `Dairy Processing Unit` (`eqToggle_dairyprocessor`) and `Whey Processing Unit` (`eqToggle_whey`) are `optional: true` with `defaultEnabled: false`. They enter the CapEx/ROI portfolio only when the user checks those boxes. Foundational milk handling is always the non-optional `Milking Parlour + Bulk Tank` package (`milking_infrastructure`) plus daily bulk-tank cooling opex (`milk_cooling_kWh_per_L_milk`). Agent 11 processing routes must follow the same opt-in gate.

### 1. Agent Purpose

The Dairy Processor Agent has **two operating modes** aligned to the dashboard:


1. **Default / not opted (processing off):** milk is only milked, cooled in the bulk tank, and sold at farm-gate. No cheese/butter/yogurt/functional split, no whey/sludge valorization CapEx. Agent 11 stays instantiated but in zero-flow / pass-through mode; Farm Manager books `rawMilkRev` and cooling cost.
2. **Opted-in processing:** user enables Dairy Processing Unit and/or Whey Processing Unit (ROI toggles) and Loop 4 / `processing_active_flag`. Then Agent 11 owns product-mix valuation and residual routing.

When processing is opted in, responsibilities are to:


* ingest raw milk from the Cow Agent,
* apply Farm Manager route policy and Loop 4 / equipment opt-in flags,
* split milk into product streams when the Dairy Processing Unit is enabled,
* generate whey, sludge, and waste-milk residual streams,
* route residuals to feed, fertilizer, biogas, or disposal when the Whey Processing Unit (and related routes) are enabled,
* value product and by-product streams using Market Agent prices when available,
* publish physical and revenue packets to Farm Manager, Feed / Crop, Manure, and Energy.

When processing is **not** opted in, responsibilities shrink to coordination only:


* acknowledge Cow milk volume,
* publish a zero processor packet (or omit product/residual ledgers),
* leave milk revenue at farm-gate and leave cooling Cost with Farm Manager / Energy context,
* do not allocate CapEx for dairyprocessor or whey units in ROI.

Why this agent exists:


* the dashboard separates foundational milking+cooling CapEx from optional L4 processing units,
* without opt-in processing, milk must be valued only at farm-gate and residuals cannot close circular routes,
* FAO LEAP places milk co-products on a cascading value pyramid (food → feed → energy/materials → disposal) when those routes are active **(Source:** FAO, 2025, Ch. 1 Fig. 4; Ch. 3 §3.2.2**)**.

Dependencies:


* Cow Agent: milk supply (`L/day` or mass-equivalent)
* Market Agent: synchronized wholesale / class price packet when dynamic pricing is enabled
* Farm Manager Agent: route policy, Loop 4 on/off, food-safety / co-product feed gates
* Feed / Crop Agent: consumer of whey/scotta feed-return packet
* Manure / Energy Agents: optional sludge and waste-milk biogas / fertilizer routes
* Environment Agent: OCirc / use-count increments for valorized residuals (optional reporting)

Constraints (do not hardcode without calibration):


* plant-specific milk-to-product yield coefficients,
* exact whey/sludge/waste-milk split factors beyond dashboard defaults,
* processor capacity and operating-cost functions,
* route-specific losses, quality downgrades, and compliance penalties,
* whey/scotta inclusion limits for herd feeding **(Source:** FAO, 2025, Appendix 5; thresholds *not clearly specified in provided resources***)**.

Expected outputs:


* default mode: zero / empty processor product packets; farm-gate milk path left to Farm Manager
* when dairy processor opted in: `processor_report_packet`, product revenues, residual generation
* when whey unit opted in: `dairy_return_feed_packet` / whey-route benefits as configured
* `byproduct_revenue_usd_period` only for active opted-in streams

### 2. Agent State Variables

#### 2.1 Control / policy (ROI-aligned opt-in)


* `processing_active_flag` / Loop 4 on — enables product-mix simulation path; bool; Farm Manager / scenario; dynamic.
* `dairy_processor_unit_enabled` — maps to dashboard ROI toggle `eqToggle_dairyprocessor`; `optional`; **default false**; only when true may CapEx and processing-uplift ROI for the Dairy Processing Unit be counted.
* `whey_processor_unit_enabled` — maps to dashboard ROI toggle `eqToggle_whey`; `optional`; **default false**; only when true may CapEx and whey-to-feed ROI for the Whey Processing Unit be counted.
* `milking_parlour_bulk_tank_active` — foundational package (`milking_infrastructure`); not optional in dashboard ROI catalogue; origin of milk handling capacity for farm-gate sales.
* `route_mode` — active routing map; used only when processing units are enabled.
* `fraction_milk_to_processor` — share of milk entering processing when L4 and dairy-processor unit are active; fraction `0–1`; dashboard default `1.0`.
* `coproduct_feed_allowed` — gate for whey/scotta return-to-feed; requires whey unit / Loop 4 residual routes as configured.

Implementation rule from dashboard: if an optional equipment toggle is unchecked, exclude that unit from portfolio CapEx/benefit totals (greyed “Not included”); do not invent active processor revenue for a disabled unit.


#### 2.2 Physical milk and residual streams


* `raw_milk_input_l` — ingested milk; `L/period`; float `>=0`; daily/weekly; from Cow.
* Product-mix fractions (dashboard Loop 4 defaults, configurable): `fraction_milk_to_cheese` `0.40`, `fraction_milk_to_butter` `0.20`, `fraction_milk_to_yogurt` `0.15`, `fraction_milk_to_fresh` `0.15`, `fraction_milk_to_functional` `0.10`. Fractions should sum to `1` when used as exclusive splits *(implementation assumption from dashboard defaults)*.
* `whey_output` — generated whey; dashboard derives by product-specific `whey_yield_*` (e.g. cheese `0.88` L whey / L milk); float `>=0`.
* `sludge_output` — `proc × fraction_sludge_of_milk`; dashboard default sludge fraction `0.02`.
* `waste_milk_output` — `proc × fraction_waste_milk_of_milk`; dashboard default `0.03`.
* `scotta_output_l` — optional FAO Appendix 5 residual stream when modeled; otherwise omit.
* `route_tier` per residual stream: `food`, `feed`, `energy`, `materials`, or `disposal` for value-pyramid ordering **(Source:** FAO, 2025, Ch. 1 Fig. 4**)**.

#### 2.3 Component-balance variables (USDA ERS path)


* `milk_fat_input_lb`, `skim_solids_input_lb`, `residual_fat_lb`, `residual_snf_lb` — used when solids mass-balance routing is enabled (USDA ERS TB-1961 anchors in §8).
* Exact milk composition used to convert `raw_milk_input_l` into fat/SNF pounds is **not clearly specified in the provided resources** and remains configurable.

#### 2.4 Price and revenue variables


* Dashboard farm-gate / contract prices (`$/L` milk-equivalent): `price_per_L_milk_cheese`, `price_per_L_milk_butter`, `price_per_L_milk_yogurt`, `price_per_L_milk_fresh`, `price_per_L_milk_functional`, plus farm-gate `milk_price_currency_per_L` when L4 is off.
* Optional Market-Agent wholesale fields when CSV path is enabled: `wholesale_cheddar_price_usd_lb`, `wholesale_whey_price_usd_lb`, `wholesale_butter_price_usd_lb`, `wholesale_nonfat_dry_milk_price_usd_lb`.
* `byproduct_revenue_usd_period`, stream revenues, `processor_report_packet`.

#### 2.5 Residual routing fractions (dashboard defaults)


* `fraction_whey_to_animal_feed_loop` default `0.50`
* `fraction_waste_milk_to_animal_feed_loop` default `0.70`; `fraction_waste_milk_to_biogas` default `0.30`
* `fraction_sludge_to_biogas` default `0.50`; `fraction_sludge_to_fertilizer` default `0.50`
* `byproduct_loop_feed_substitution_kg_per_kg` — converts whey/waste-milk returned mass to feed credit; exact numeric value is scenario-configured in dashboard.

These defaults come from the dairy bioeconomy dashboard Loop 4 configuration and are **calibration starting points**, not universal constants.


### 3. Agent Behaviors and Actions


* `ingest_milk_batch()` — daily/weekly; Cow milk volume (always).
* `ingest_price_context()` — Market Agent packet or static dashboard farm-gate / product prices.
* `apply_equipment_opt_in_gates()` — read `dairy_processor_unit_enabled` and `whey_processor_unit_enabled` (ROI toggles) plus Loop 4 / `processing_active_flag`.
* `apply_default_milking_cooling_path()` — when dairy processor not opted in: zero product/residual flows; Farm Manager uses farm-gate milk price; cooling opex uses `milk_cooling_kWh_per_L_milk` (dashboard bulk-tank cooling).
* `split_product_streams()` — only if dairy processor unit enabled and Loop 4 on.
* `compute_whey_and_residuals()` — only if dairy processing path produced whey/sludge/waste streams.
* `route_residuals()` — whey-to-feed / waste / sludge routes only if whey processor unit enabled (and safety gates allow).
* `value_streams()` — quantity × price for active streams only.
* `publish_processor_packet()` — Farm Manager + optional Feed/Manure/Energy packets; publish zeros when units not opted in.

### 4. Decision-Making Logic


1. **Default path (no dairy/whey unit selected):** milk handled as milking + bulk-tank cooling only. `proc = 0` for product mix. Farm Manager: `milkRev = rawMilkRev = milk × milk_price_currency_per_L`. Cooling cost always applies in dashboard economics: `coolingCost = milk × milk_cooling_kWh_per_L_milk × electricity_price`. ROI portfolio includes `Milking Parlour + Bulk Tank`, not dairyprocessor/whey CapEx.
2. **Dairy Processing Unit opted in + Loop 4 on:** `proc = milk × fraction_milk_to_processor`; split into product streams; `milkRev = dairyProductRev`. ROI benefit for dairyprocessor uses processing uplift vs raw-milk baseline (dashboard: `max(0, dairyProductRev − rawMilkRev)` plus liquid whey stream value at `whey_liquid_price_per_L` when that unit is active).
3. **Whey Processing Unit opted in:** only then count whey-to-feed / waste-diversion CapEx and ROI benefits (feed substitution and disposal savings as in dashboard `whey` equipment card). Do not enable whey CapEx solely because cheese made whey unless the whey toggle is also on.
4. Prefer higher value-pyramid tiers when multiple residual options exist and safety flags allow **(Source:** FAO, 2025, Ch. 1 Fig. 4**)**.
5. Block whey/scotta feed return when `coproduct_feed_allowed=false` **(Source:** FAO, 2025, Ch. 4 §4.2; Appendix 5**)**.
6. Exact multi-objective residual optimizer is **not clearly specified**; keep policy-driven fractions. Keep unused routes at weight zero rather than deleting the agent.

### 5. Agent Interactions

| Interaction | Direction | Trigger | Exchanged information | Timing | Impact |
|---|---|---|---|---|---|
| Cow → Dairy Processor | incoming | daily milk output | milk litres / solids if available | daily | sets `raw_milk_input_l` |
| Market → Dairy Processor | incoming | price tick | wholesale / class / product prices | monthly preferred | stream valuation |
| Farm Manager → Dairy Processor | incoming | policy | Loop 4 flag, route fractions, safety gates | event / weekly | enables routes |
| Dairy Processor → Farm Manager | outgoing | after valuation | `byproduct_revenue`, processor packet | daily/weekly | profit ledger |
| Dairy Processor → Feed / Crop | outgoing | feed-return route | `dairy_return_feed_packet` | daily/weekly | feed credit / OCirc |
| Dairy Processor → Manure / Energy | outgoing | biogas/fertilizer routes | sludge / waste-milk mass | daily/weekly | extra digester feedstock / fertilizer |

Synchronization: run after Cow milk publish and after Market price packet when dynamic pricing is used; publish before Farm Manager profitability close.


### 6. Environmental Integration


* does not own GHG accounting,
* may emit residual-fate tags so Environment can update `OCirc` / `use_count` when residuals are valorized,
* internal feed loops carry zero external revenue but still count as circular uses **(Source:** FAO, 2025, Ch. 5; Appendix 5**)**.

### 7. Genetic / Evolutionary Logic (If Applicable)

None. Butterfat/protein genetics affect Cow solids output upstream; this agent consumes resulting milk composition if provided and does not evolve traits.


### 8. Equations / Algorithms / Thresholds

#### 8.1 Default milking + bulk-tank path (no processor opt-in)

Dashboard economics when Loop 4 / dairy processor is off:

$$rawMilkRev = milk \times milk\_price\_currency\_per\_L$$
$$milkRev = rawMilkRev$$
$$coolingCost = milk \times milk\_cooling\_kWh\_per\_L\_milk \times electricity\_price$$
**Source:** dairy bioeconomy dashboard `simulateDay` and Economics params (`milk_cooling_kWh_per_L_milk` hint: bulk tank cooling electricity).

**Why used:** Matches farms that milk and cool only — no on-farm dairy plant.


Foundational CapEx (always in ROI catalogue, not checkbox-gated): `Milking Parlour + Bulk Tank` (`milking_infrastructure`) — “origin of all milk revenue”; dashboard combines parlour and bulk tank because bulk tanks are virtually never installed separately from the parlour.


#### 8.2 Opt-in Dairy Processing Unit + Loop 4 product valuation

Only when dairy processor unit is enabled and Loop 4 is active:

$$proc = milk \times fraction\_milk\_to\_processor$$
$$dairyProductRev = \sum_{p \in \{cheese,butter,yogurt,fresh,functional\}} (proc \times fraction\_milk\_to\_p) \times price\_per\_L\_milk\_p$$
$$milkRev = dairyProductRev$$
**Source:** dairy bioeconomy dashboard Loop 4 implementation.


ROI card benefit for `dairyprocessor` (dashboard):

$$processingUplift = \max(0,\ dairyProductRev - rawMilkRev)$$
plus liquid whey stream value at configured `whey_liquid_price_per_L` when included on that card. CapEx formula in dashboard: `max(60000, n × 550)` plus install % — treat as dashboard calibration, not a universal constant.


When dairy processor is **not** opted in: do not run the product-mix equations above; leave `proc = 0` and use §8.1.


#### 8.3 Opt-in Whey Processing Unit

Whey mass exists as a physical by-product of dairy processing when product mix is active. The separate `whey` ROI unit is still **opt-in** (`defaultEnabled: false`). When enabled, dashboard benefits include feed substitution value from `feedReturn`, disposal savings on diverted whey/waste milk, and an optional functional whey premium term using `fraction_whey_to_functional_foods_bioproducts`. CapEx: `max(40000, n × 280)` plus install % (dashboard).


When whey unit is not opted in: do not add whey-unit CapEx or its ROI benefit to the portfolio; residual physical whey may still be tracked at zero processing CapEx if the dairy unit produced it — detailed off-farm whey fate beyond dashboard toggles is **not clearly specified**.


#### 8.2 Whey generation (dashboard product-specific yields)

$$whey = \sum_p (milk_p \times whey\_yield\_p)$$
with dashboard defaults `whey_yield_cheese=0.88`, `yogurt=0.05`, `functional=0.10`, butter/fresh `0`.


#### 8.3 Generic stream revenue (Market / CSV path)

$$revenue_{stream,t} = quantity_{stream,t} \times price_{stream,t}$$
$$byproduct\_revenue_t = \sum_{stream} revenue_{stream,t}$$
**Source:** accounting identity with prices from Market Agent / `dairy-situation-glance.csv`.


Convert volumes to lb before applying `$/lb` wholesale series when using CSV wholesale fields.


#### 8.4 USDA ERS solids conversion anchors

Optional mass-balance path when component ledgers are enabled (`Byproduct.pdf` / USDA ERS TB-1961):


* `fat_required_butter = 0.8050 × butter_output_lb`; `snf_required_butter = 0.0185 × butter_output_lb`
* `fat_required_american_cheese = 0.3282 × ...`; `snf_required_american_cheese = 0.8510 × ...`
* `fat_required_other_cheese = 0.2488 × ...`; `snf_required_other_cheese = 0.8590 × ...`
* `fat_required_dry_whey = 0.0100 × ...`; `snf_required_dry_whey = 0.9400 × ...`
* `residual_fat_lb` / `residual_snf_lb` = inputs minus sum of product draws
**Source:** USDA ERS TB-1961 conversion factors (`Byproduct.pdf`, 2023).


Interpretation note already in blueprint: cheese conversion percentages above 100% solids-required equivalents represent solids required for production, not final product composition.


#### 8.5 Unsupported exact equations


* exact plant OpEx / capacity curves,
* exact scotta mineral limits,
* exact bioplastics/protein-isolate yields,
* mapping from dairy-situation wholesale $/$lb series onto dashboard $/L milk-equivalent contract prices without an explicit conversion convention.
Mark these as configurable or omitted.


### 9. Data Requirements


* Cow milk volume (daily)
* Loop 4 / product-mix configuration
* price context: static dashboard prices or Market CSV packet
* optional milk fat/SNF composition for USDA solids path
* safety-approval flags for feed-return

Missing-data handling: if Market prices absent → use last valid price or dashboard static defaults and set low-confidence revenue flag; if safety flag false → keep physical whey ledger but block feed return.


### 10. Edge Cases / Failure Conditions

| Issue | Detection | Prevention | Fallback |
|---|---|---|---|
| Dairy/whey CapEx counted while toggle off | ROI portfolio includes disabled unit | `isEquipEnabled` / opt-in gate | exclude from totals; grey “Not included” |
| Product-mix revenue with dairy unit off | `dairyProductRev > 0` while unit disabled | gate before valuation | force farm-gate `rawMilkRev` only |
| Whey ROI on with no dairy processing | whey toggle on, dairy toggle off / L4 off | config validation | disable whey benefits or require dairy path first (dashboard allows independent toggles — keep flags independent but document zero whey volume if L4 off) |
| Loop 4 on but product fractions do not sum to 1 | sum check | config validation | renormalize or reject |
| Negative residual after solids debit | `residual_* < 0` | component capacity check | clamp and flag infeasibility |
| Feed return without safety approval | flag false | gate before publish | reroute to energy/disposal per policy |
| Price packet missing | null prices | schema check | physical outputs only / static farm-gate defaults |
| Zero milk with nonzero processor outputs | mass balance | require milk ingest | zero outputs and log |

### 11. Direct Coding Guidance


* Module: `agents/dairy_processor_agent.py`; class `DairyProcessorAgent`.
* Preferred loop: receive milk → apply ROI opt-in gates → if neither dairy nor whey unit enabled, publish zero process flows and exit to farm-gate + cooling path → else split products / residuals → apply prices → publish.
* Keep the agent instantiated when unused; set unit flags false and route weights to zero (dashboard keeps toggles; unchecked units are excluded from portfolio, not deleted from the catalogue).
* Support two valuation modes without mixing units silently: (A) dashboard $/L milk-equivalent product mix when dairy unit on; (B) Market wholesale $/lb with explicit unit conversion.
* Align ROI CapEx inclusion with `optional`/`defaultEnabled: false` for `dairyprocessor` and `whey`; always allow foundational `milking_infrastructure` CapEx consideration at Farm Manager / ROI layer.

```python
class DairyProcessorAgent:
    def ingest_milk(self, cow_milk_packet): ...
    def ingest_prices(self, market_packet=None, static_prices=None): ...
    def apply_equipment_opt_in(self, dairy_unit_on, whey_unit_on, loop4_on): ...
    def apply_default_milking_cooling_path(self): ...  # farm-gate; no product mix
    def apply_loop4_and_split(self, policy): ...       # only if dairy unit on
    def compute_residuals(self): ...
    def route_residuals(self, policy): ...             # whey-unit gated
    def value_streams(self): ...
    def publish(self): ...```

---

## Agent 12 — 📈 Market Agent

*Tag: Economic Layer*

This base runtime module provides the economy layer through exogenous market packets grounded in `dairy-situation-glance.csv` (monthly + annual dairy market indicators), `dymclassprices.pdf` (class/component pricing formulas), and Dong-Du-Gould volatility evidence for risk-state dynamics.


### 1. Agent Purpose

The Market Agent owns **synchronized exogenous price context** for milk, dairy products, and (when configured) feed/energy linkages used by Farm Manager, Feed / Crop, Energy, and Dairy Processor.


Its responsibilities are to:


* load period-matched market observations,
* publish one price packet per market tick to all consumers,
* optionally compute volatility / regime labels,
* apply scenario overlays (static, observed, or observed-plus-shock),
* flag missing values instead of inventing structural market-clearing.

Why this agent exists:


* Farm Manager milk and by-product revenue need a common price basis,
* Dairy Processor wholesale valuation needs synchronized product prices,
* dashboard scenarios today use static sliders; this agent is the upgrade path to dataset-backed prices without embedding markets inside Farm Manager.

Constraints:


* do not add endogenous market-clearing or trade-network dynamics without additional sources,
* do not invent unsupported structural supply–demand equations,
* exact mapping from Class III $/cwt to dashboard `milk_price_currency_per_L` requires an explicit conversion convention and is **not clearly specified** as a single project formula.

Expected outputs:


* `market_state_packet`
* `market_packet_quality_flag`
* optional `market_regime_label` / volatility fields

### 2. Agent State Variables

#### 2.1 Milk class and all-milk prices (CSV)


* `all_milk_price_usd_cwt`, `class_iii_price_usd_cwt`, `class_iv_price_usd_cwt` from `Category=Milk prices`.
* `class_ii_price_usd_cwt` and component fields from `dymclassprices.pdf`: butterfat, skim, protein, other solids, somatic-cell adjustment rate.

#### 2.2 Wholesale dairy products (CSV)


* `butter_price_usd_lb`, `cheddar_blocks_price_usd_lb`, `cheddar_barrels_price_usd_lb`, `dry_whey_price_usd_lb`, `nonfat_dry_milk_price_usd_lb` from `Category=Wholesale dairy product prices`.

#### 2.3 Macro / export / volatility context


* CPI YoY fields from `Category=Consumer Price Indexes`.
* Oceania export butter / SMP prices when present.
* Dong-Du-Gould style fields when high-frequency inputs exist: `realized_volatility_class_iii`, first-20-day log-return variance, cheese-use/supply ratio, USDX return, VIX, corn volatility proxy, speculation index.
* `market_state_packet`, `market_packet_quality_flag`, `market_regime_label`.

#### 2.4 Dashboard-static fallback prices


* When CSV mode is off, Market may publish (or Farm Manager may hold) dashboard static fields: `milk_price_currency_per_L`, product `price_per_L_milk_*`, `feed_cost_per_kg`, `electricity_price_currency_per_kWh`, `heat_value_currency_per_kWh`.
* These are simulation configuration values, not derived market observations.

### 3. Agent Behaviors and Actions


* `load_period_rows()` — CSV by Year/Period/Frequency.
* `build_price_packet()` — tagged units and source IDs.
* `compute_volatility_state()` — preferred realized-vol path; fallback first-20-day variance.
* `apply_scenario_overlay()` — static / observed / observed+shock.
* `publish_synchronized_packet()` — identical packet to Farm Manager, Feed, Energy, Dairy Processor.

### 4. Decision-Making Logic


1. Prefer monthly CSV values; fall back to annual when monthly missing.
2. If `Value=NA`, carry forward last valid value and set quality warning.
3. Never publish negative prices; clamp and log.
4. If high-frequency data unavailable, disable realized-volatility branch.
5. Shock overlays are scenario tools, not structural laws.

### 5. Agent Interactions

| Interaction | Direction | Trigger | Exchanged information | Timing | Impact |
|---|---|---|---|---|---|
| Market → Farm Manager | outgoing | price tick | milk / product / optional carbon prices | monthly preferred | revenue and ROI valuation |
| Market → Dairy Processor | outgoing | price tick | wholesale product prices | monthly | by-product valuation |
| Market → Feed / Crop | outgoing | price tick | feed-price context if supplied | monthly/weekly | feed-cost rollups |
| Market → Energy | outgoing | price tick | electricity / heat tariff context if supplied | monthly/weekly | energy-cost savings |
| External CSV / config → Market | incoming | load | observed series or static defaults | init + monthly | fills packet |

Synchronization: publish **before** Farm Manager profitability close and before Feed/Energy/Processor pricing-dependent calculations.


### 6. Environmental Integration

Market does not compute GHG. It may optionally carry carbon-credit price context if Environment/Energy monetization is enabled; the credit price source must be configured — exact project default is **not clearly specified**.


### 7. Genetic / Evolutionary Logic (If Applicable)

None.


### 8. Equations / Algorithms / Thresholds

#### 8.1 Normalization / returns (implementation transforms)

$$price\_index_{x,t} = \frac{price_{x,t}}{price_{x,t0}}$$
$$\Delta p_{x,t} = \frac{price_{x,t} - price_{x,t-1}}{price_{x,t-1}}$$
**Source:** implementation-derived transforms; not named source formulas.


#### 8.2 Volatility (Dong-Du-Gould, 2011)

$$r_{t,j}=\log(p_{t,j})-\log(p_{t,j-1}), \qquad RV_t=\sum_{j=1}^{m} r_{t,j}^2$$
$$mvol_t = \mathrm{Var}\left(\Delta \log P_{d}\right),\quad d \in \text{first 20 trading days of month } t$$
**Source:** Dong, Du, Gould (2011), “Milk Price Volatility and its Determinants”.


Optional regime overlay (reported signs/magnitudes; calibrate locally; scenario overlay only):

$$\widehat{mvol}_t = c + S_t + 0.54\cdot cheese\_use\_supply_t + 0.62\cdot usdx\_return_t + 0.18\cdot corn\_vol_t + 0.11\cdot vix_t + 0.027\cdot speculation_t$$
**Source:** same paper regression outputs.


#### 8.3 USDA class / component formulas (dymclassprices.pdf)

$$Butterfat\ Price = (Butter\ Price - 0.2272)\times 1.211$$
$$Nonfat\ Solids\ Price = (NFDM\ Price - 0.2393)\times 0.99$$
$$Other\ Solids\ Price = (Dry\ Whey\ Price - 0.2668)\times 1.03$$
$$Class\ III\ Price = (Class\ III\ Skim\ Price \times 0.965) + (Butterfat\ Price \times 3.5)$$
$$Class\ IV\ Price = (Class\ IV\ Skim\ Price \times 0.965) + (Butterfat\ Price \times 3.5)$$
**Source:** USDA class/component formulas in `dymclassprices.pdf`. Monthly commodity inputs are weighted averages over the previous four or five NDPSR weeks (same source).


#### 8.4 Milk revenue handoff (coordination, not Market-owned volume)

Market publishes price; Farm Manager / Processor compute revenue:


* Loop 4 off: `milk_revenue ≈ milk_L × milk_price_currency_per_L` (dashboard).
* Loop 4 on: product-mix revenue via Dairy Processor (§ Agent 11).
* Class $/cwt → $/L conversion must be documented at implementation time; do not silently assume a conversion.

#### 8.5 Unsupported


* endogenous equilibrium price formation,
* futures-options Greek models,
* universal Class→$/L constant without project convention.

### 9. Data Requirements


* `dairy-situation-glance.csv` with Category/Data_item mappings
* optional `dymclassprices.pdf` component inputs
* optional high-frequency Class III series for Dong-Du-Gould volatility
* scenario mode flag (static vs observed)

Missing-data handling: carry-forward + `market_packet_quality_flag=low_confidence`; if CSV absent, emit static dashboard price packet and tag provenance `static_config`.


### 10. Edge Cases / Failure Conditions

| Issue | Detection | Prevention | Fallback |
|---|---|---|---|
| CSV row missing for period | lookup fail | schema calendar check | annual fallback or carry-forward |
| Unit mismatch $/cwt vs $/L | unit tag conflict | require conversion function | refuse mixed arithmetic; publish both fields |
| Negative computed class price | <0 | formula domain checks | clamp and flag anomaly |
| Consumers use different price ticks | packet ID mismatch | single publish per tick | force resync / reject stale packets |

### 11. Direct Coding Guidance


* Module: `agents/market_agent.py`; class `MarketAgent`.
* Map CSV `Category`/`Data_item` to internal names explicitly.
* Persist raw values and normalized indices.
* In dashboard-parity mode, Market can act as a thin publisher of static config prices so Agent 11/8 interfaces stay identical.

```python
class MarketAgent:
    def load_csv(self, path): ...
    def select_period(self, year, period, frequency="Monthly"): ...
    def build_packet(self): ...
    def compute_volatility(self): ...
    def apply_overlay(self, mode): ...
    def publish(self): ...```

---

## Agent 13 — 🗺️ Land Management Agent

*Tag: Land Extension*

> **Note:** Disabled by default. Only enable Agent 13 when the project adds explicit land-allocation, rotational-grazing, or silvopastoral scenarios with supporting inputs. Exact land-growth, grazing-intake, and sequestration kinetics are **not clearly specified in the provided resources** beyond dashboard Land Resources parameters and Feed/Crop land ownership in base mode.

### 1. Agent Purpose

The Land Management Agent is an **optional extension** that owns standalone land-allocation, pasture-availability, and coarse soil-carbon reporting when those cannot remain inside Feed / Crop Agent.


Base-mode rule (already approved): if Agent 13 remains off, keep crop/pasture land logic inside `Feed / Crop Agent` and land-linked environmental accounting inside `Environment Agent`.


Dashboard Land Resources parameters already exposed without a separate agent:


* `land_cropland_ha`
* `land_pasture_ha`
* `soil_carbon_sequestration_index`
* `land_silvopastoral_tree_cover_fraction`
These may initialize Feed/Crop or, if Agent 13 is enabled, Land Agent state. Exact functional use of tree-cover fraction and soil-carbon index in equations is **not clearly specified** beyond being configurable scenario inputs.


### 2. Agent State Variables (when enabled)


* `land_cropland_ha`, `land_pasture_ha` — ha; float `>=0`; scenario init; static or rare policy update.
* `land_silvopastoral_tree_cover_fraction` — fraction `0–0.5` in dashboard range; scenario init.
* `soil_carbon_sequestration_index` — index; dashboard range about `0.5–2.0`; exact physical mapping not clearly specified.
* `land_allocation_packet` — structured area availability for Feed/Crop.
* `grazing_access_packet` — optional Cow grazing access if grazing is explicitly modeled.
* `soil_carbon_packet` — coarse sequestration signal for Environment.

Do not invent parcel GIS layers, plot-level hydrology, or endogenous land markets without new sources.


### 3. Agent Behaviors and Actions (when enabled)


* `initialize_land_state()` from scenario.
* `update_seasonal_availability()` only if seasonal land rules are configured (exact rule **not clearly specified**).
* `publish_feed_land_packet()` to Feed/Crop.
* `publish_grazing_packet()` to Cow if grazing mode on.
* `publish_soil_carbon_packet()` to Environment.

### 4. Decision-Making Logic

Policy-driven allocation only. Exact optimization of cropland vs pasture shares is **not clearly specified**; use scenario presets.


### 5. Agent Interactions

| Interaction | Direction | Exchanged information | Timing |
|---|---|---|---|
| Config → Land | incoming | ha, tree cover, soil-carbon index, grazing flags | init / rare |
| Land → Feed / Crop | outgoing | land-allocation / pasture availability | seasonal/weekly |
| Land → Cow | outgoing optional | grazing access | daily/seasonal |
| Land → Environment | outgoing | coarse soil-carbon / sequestration packet | monthly/seasonal |

### 6. Environmental Integration

May forward a coarse soil-carbon index or delta packet. Environment remains owner of final GHG/soil KPI aggregation. Exact sequestration (tCO₂e/ha) conversion is **not clearly specified**.


### 7. Genetic / Evolutionary Logic (If Applicable)

None.


### 8. Equations / Algorithms / Thresholds

No sourced land-production equation is locked in this blueprint beyond Feed/Crop crop/land variables already owned in base mode. When Agent 13 is enabled:


* pass through configured ha and indices,
* do not invent yield = f(tree_cover) or SOC differential equations without a cited source,
* any derived sequestration must cite an external factor and remain configurable.

### 9. Data Requirements


* scenario land areas and silvopastoral / grazing flags
* optional seasonal calendar if availability varies
* Environment reporting schema for soil-carbon packet

### 10. Edge Cases / Failure Conditions


* Agent 13 enabled but Feed/Crop still mutates the same land ha → double ownership; prevent by exclusive ownership flag.
* Negative land area → reject config.
* Grazing packet published while Cow grazing mode off → treat as unused.

### 11. Direct Coding Guidance


* Module: `agents/land_agent.py`; class `LandManagementAgent`.
* Instantiate only when `enable_land_agent=true`.
* Default runtime: omit agent; Feed/Crop reads dashboard Land Resources params directly.

```python
class LandManagementAgent:
    def __init__(self, config): ...
    def initialize(self): ...
    def publish_packets(self): ...```

---
