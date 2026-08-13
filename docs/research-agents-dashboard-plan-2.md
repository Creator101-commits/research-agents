# Dairy Bioeconomy Dashboard — Repository-Native Rebuild Plan

## Purpose

This plan upgrades the existing `Creator101-commits/research-agents` repository into the full interactive dairy-bioeconomy dashboard.

It does **not** create a second simulation, replace `DairyFarmModel`, or port the old dashboard's JavaScript model.

The old `dairy-bioeconomy-dashboard-v2.html` is used only as a UI/UX reference. The existing Python model, rewritten equations, calibration system, reports, scenarios, and simulation behavior in `research-agents` remain authoritative.

---

# 1. Non-Negotiable Architecture Rule

## Source of truth

```text
research-agents Python model
        ↓
SimulationContext
        ↓
dashboard/report serialization
        ↓
HTTP API
        ↓
browser state
        ↓
UI
```

Never:

```text
Python model
        ↓
browser
        ↓
recalculate milk/feed/water/GHG/economics/etc. in JavaScript
```

The browser may format numbers, sort/filter rows, select series, switch views, and convert values to SVG coordinates.

The browser may **not** independently simulate cows, disease, feed, water, manure, GHG, markets, circular loops, economics, or ROI.

If the UI needs a number the backend does not expose, add it to the Python output contract first.

---

# 2. Existing Repository Is the Foundation

This plan is written specifically for the current `research-agents` repository.

Existing foundation:

```text
research-agents/
├── dairy_abm/
│   ├── agents/
│   ├── analysis/
│   │   └── npv.py
│   ├── config.py
│   ├── core.py
│   ├── model.py
│   └── reports.py
├── configs/
│   └── calibration.json
├── scenarios/
├── tests/
├── webapp.py
└── package.json
```

Existing behavior to preserve:

- `webapp.py` already uses Python stdlib `ThreadingHTTPServer`.
- `webapp.py` already calls the real `DairyFarmModel`.
- The web simulation follows the same model path as the CLI.
- `RUN_CACHE` already stores recent `SimulationContext` objects.
- `POST /api/run` already exists.
- `GET /api/scenario` already exists.
- `GET /api/export/<run_id>` already exists.
- `write_reports()` already produces official JSON/CSV outputs.
- `calibration_inventory()` already exposes parameter metadata.
- `dairy_abm/analysis/npv.py` already contains NPV analysis.
- `tests/test_webapp.py` already covers the existing web run desk.

This rebuild is therefore an **extension and refactor of the existing app**, not a replacement project.

---

# 3. What to Reuse from the Old Dashboard

Use the old HTML only for:

- page organization;
- sidebar navigation;
- KPI cards;
- chart layouts;
- circular-loop cards;
- flow-visualization ideas;
- scenario-comparison UX;
- equipment ROI card presentation;
- cow-performance tables;
- parameter-editing UX;
- tooltips;
- export UX;
- responsive layout ideas.

Do not copy:

- `simulateDay()`;
- `HerdModel`;
- JavaScript PRNG/model state;
- old scientific equations;
- old economics;
- old GHG equations;
- old sustainability calculations;
- old land calculations;
- old ROI assumptions;
- unsupported constants;
- unused sliders.

---

# 4. Frontend Technology Decision

Keep the project lightweight.

Use:

- plain HTML;
- CSS;
- ES modules;
- Fetch API;
- browser-native SVG charts;
- current Python stdlib server.

Do **not** introduce React, Vue, Vite, Webpack, Flask, FastAPI, or Chart.js during this rebuild unless a real limitation appears later.

The application should remain runnable with:

```bash
python3 webapp.py
```

---

# 5. Keep and Refactor `webapp.py`

Do not replace `webapp.py`.

Its final responsibilities should be:

- HTTP routing;
- request parsing;
- validation entry;
- safe static-file serving;
- scenario selection;
- run-cache access;
- calling `DairyFarmModel`;
- calling dashboard serializers;
- serving exports.

It should not remain a giant HTML/CSS/JS string or become a large calculation/reporting layer.

The small totals/means currently created inside `_run_simulation()` should move into the dashboard/report layer.

---

# 6. Add `dairy_abm/dashboard.py`

Add:

```text
dairy_abm/dashboard.py
```

This becomes the single adapter between `SimulationContext` and the dashboard.

Suggested functions:

```python
serialize_dashboard_run(ctx, run_id, duration_s) -> dict
serialize_dashboard_config(...) -> dict
serialize_comparison(runs) -> dict
build_dashboard_warnings(ctx) -> list[dict]
```

Possible helpers:

```python
_build_summary(...)
_build_timeseries(...)
_build_loop_sections(...)
_build_cow_table(...)
_build_environment_section(...)
_build_economics_section(...)
_build_equipment_section(...)
_build_model_details(...)
```

Allowed:

- select fields;
- rename fields;
- attach units;
- group outputs;
- map packet/state values into UI sections;
- perform approved reporting aggregates;
- calculate display comparison deltas;
- expose missing values as `None`.

Not allowed:

- inventing scientific equations;
- inventing economic equations;
- creating a second sustainability model;
- creating a second ROI model.

---

# 7. Create a Dashboard Metric Map Before UI Coding

Add:

```text
docs/dashboard_metric_map.md
```

For every desired UI metric, record:

| UI Metric | Python Source | Field / Packet | Period | Unit | Aggregation | Status | Notes |
|---|---|---|---|---|---|---|---|

Status must be one of:

- `EXISTING`
- `BACKEND_AGGREGATE`
- `BACKEND_EXPOSE`
- `MODEL_CHANGE`
- `UNSUPPORTED`

Inspect:

- `ctx.daily_records`
- `ctx.monthly_records`
- `ctx.annual_records`
- `ctx.schedule_records`
- `ctx.state`
- `ctx.packets`
- `ctx.events`
- `REPORT_CONTRACT`
- calibration inventory
- per-cow state/records

Do not build a card just because the old HTML had one.

---

# 8. Stable Dashboard Response Contract

Frontend code should not depend directly on arbitrary packet structures or CSV field names.

Recommended response:

```json
{
  "run_id": "abc12345",
  "meta": {
    "scenario_name": "baseline",
    "seed": 1,
    "days": 365,
    "herd_size": 100,
    "duration_s": 0.0
  },
  "features": {},
  "summary": {},
  "series": {
    "daily": [],
    "monthly": [],
    "annual": []
  },
  "loops": {
    "l1": {},
    "l2": {},
    "l3": {},
    "l4": {}
  },
  "cows": [],
  "environment": {},
  "economics": {},
  "equipment": {},
  "model_details": {},
  "warnings": []
}
```

For major metrics, prefer:

```json
{
  "value": 123.4,
  "unit": "kg CO2e",
  "available": true,
  "confidence": "high",
  "source": "environment_packet"
}
```

Unsupported:

```json
{
  "value": null,
  "available": false,
  "reason": "not produced by current model"
}
```

Never substitute `0` for "not available."

---

# 9. API Migration Strategy

## Keep current routes during migration

```text
GET  /api/scenario
POST /api/run
GET  /api/export/<run_id>
```

## Add

```text
GET  /api/config
GET  /api/calibration
GET  /api/run/<run_id>
POST /api/compare
```

`GET /api/scenario` should remain temporarily as a compatibility route.

Remove it only after:

1. the new frontend no longer uses it;
2. tests are updated;
3. no documented workflow depends on it.

---

# 10. `GET /api/config`

Return UI-safe runtime configuration:

```json
{
  "default_scenario": {},
  "scenarios": [],
  "feature_flags": {},
  "limits": {},
  "report_contract": {},
  "ui_capabilities": {}
}
```

Feature controls must come from actual backend scenario/config capability, not from the old HTML.

Known existing top-level flags include:

- `enable_processor`
- `enable_whey_processing`
- `enable_land_agent`
- `l1_nutrient_loop_enabled`
- `l2_water_loop_enabled`
- `l3_energy_loop_enabled`
- `l4_byproduct_loop_enabled`

Any additional toggle must be verified before adding it.

---

# 11. `GET /api/calibration`

Use:

```python
calibration_inventory(CALIBRATION)
```

Do not make the browser parse the raw nested calibration file.

The existing inventory already provides:

- key;
- group/agent;
- default;
- unit;
- source;
- assumption;
- description;
- valid range.

If UI-only metadata is needed, keep it separate from the scientific calibration values.

---

# 12. Safe Per-Run Calibration Overrides

The full Parameters page requires real backend overrides.

Do not mutate global `CALIBRATION`.

Recommended request:

```json
{
  "scenario": "baseline.json",
  "scenario_overrides": {
    "days": 365,
    "seed": 42
  },
  "calibration_overrides": {
    "environment.some_parameter": 0.0
  }
}
```

Backend:

```text
base calibration
      ↓
deep copy
      ↓
apply allowed overrides
      ↓
validate_calibration()
      ↓
DairyFarmModel(scenario, run_calibration)
```

Each run must have isolated calibration state.

---

# 13. Validation

Backend is authoritative.

Validate:

- scenario path containment;
- days;
- seed;
- herd size;
- boolean feature flags;
- calibration key existence;
- calibration type;
- valid range;
- fraction constraints;
- sum-to-one groups;
- incompatible feature combinations if defined.

Invalid client configuration should normally return HTTP `400`, not `500`.

---

# 14. Run Cache

Keep the existing in-memory approach initially.

Possible structure:

```python
@dataclass
class CachedRun:
    ctx: SimulationContext
    duration_s: float
    serialized: dict | None = None
```

Required behavior:

- `POST /api/run` creates the run;
- `GET /api/run/<id>` returns the normalized dashboard payload;
- `GET /api/export/<id>` creates official reports from the same cached `SimulationContext`.

This guarantees the UI and exports refer to the exact same simulation.

---

# 15. Extract the Frontend from Inline `PAGE`

Create:

```text
web/
├── index.html
├── styles/
│   ├── tokens.css
│   ├── base.css
│   ├── layout.css
│   ├── components.css
│   └── pages.css
└── js/
    ├── app.js
    ├── api.js
    ├── state.js
    ├── router.js
    ├── format.js
    ├── charts.js
    ├── components/
    │   ├── kpi-card.js
    │   ├── metric-table.js
    │   ├── chart-card.js
    │   ├── status-badge.js
    │   ├── warning-panel.js
    │   ├── parameter-control.js
    │   └── loop-card.js
    └── pages/
        ├── overview.js
        ├── simulation.js
        ├── charts.js
        ├── loops.js
        ├── comparison.js
        ├── cows.js
        ├── environment.js
        ├── economics.js
        ├── roi.js
        ├── parameters.js
        ├── model-details.js
        └── exports.js
```

`webapp.py` should safely serve:

```text
/           → web/index.html
/assets/... → files under web/
```

Prevent static-file path traversal.

---

# 16. Safe Migration of Current UI

Do not delete the current `PAGE` immediately.

Order:

1. freeze current tests;
2. add `dashboard.py`;
3. add new API routes;
4. add static-file serving;
5. reproduce current basic run functionality from `web/`;
6. migrate tests;
7. remove the giant inline page.

The final state should contain one dashboard only.

---

# 17. Native SVG Chart System

Create one reusable chart engine in:

```text
web/js/charts.js
```

Support:

- line;
- multi-line;
- bar;
- stacked bar;
- scatter.

Chart code handles:

- axes;
- scales;
- ticks;
- legends;
- tooltips;
- SVG export;
- PNG export via SVG-to-canvas if needed.

Chart code must only convert backend values into visual coordinates.

It must not calculate scientific values.

---

# 18. Final Navigation

Sidebar:

1. Overview
2. Simulation
3. Charts
4. Circular Loops
5. Scenario Comparison
6. Cow Performance
7. Environment
8. Economics
9. Equipment ROI
10. Parameters
11. Model Details
12. Export

Use client-side page switching.

---

# 19. Frontend State

Use a small state module:

```javascript
{
  activePage,
  config,
  calibration,
  currentRun,
  currentRunId,
  comparison,
  selectedPeriod,
  parameterDraft,
  filters
}
```

Do not create independent scientific state in JavaScript.

---

# 20. PHASE 0 — Baseline Lock

Before changing UI code:

1. run current test suite;
2. record current route behavior;
3. record CLI behavior;
4. run one deterministic baseline scenario;
5. preserve expected results as fixtures where useful;
6. confirm same-seed determinism.

Deliverable: known-good starting point.

---

# 21. PHASE 1 — Metric Inventory

Create `docs/dashboard_metric_map.md`.

Map all desired old-dashboard UI metrics to existing Python outputs.

No visual page implementation starts until its metrics are mapped.

Deliverable: no ambiguous metrics.

---

# 22. PHASE 2 — Add `dairy_abm/dashboard.py`

Start by reproducing current webapp output:

- run ID;
- scenario;
- seed;
- days;
- herd size;
- duration;
- existing summary metrics;
- current daily rows;
- event count.

Then extend section by section.

Add:

```text
tests/test_dashboard_serializer.py
```

Test:

- deterministic serialization;
- missing values;
- units;
- no context mutation;
- no calibration mutation.

Deliverable: stable Python-to-dashboard adapter.

---

# 23. PHASE 3 — Expand API

Add:

```text
GET /api/config
GET /api/calibration
GET /api/run/<id>
POST /api/compare
```

Keep old routes working.

Update `POST /api/run` to use the new serializer.

Deliverable: complete backend API foundation.

---

# 24. PHASE 4 — Calibration Overrides

Implement safe per-run calibration overrides.

Test:

- valid key;
- invalid key;
- invalid type;
- invalid range;
- invalid sum-to-one groups;
- independent runs do not contaminate each other.

Deliverable: backend support for a real Parameters page.

---

# 25. PHASE 5 — Static Frontend Extraction

Create `web/`.

Move UI out of `webapp.py`.

Update tests to inspect real static files rather than exact strings inside `PAGE`.

Do not weaken tests; migrate them.

Deliverable: modular frontend.

---

# 26. PHASE 6 — Dashboard Shell

Build:

- sidebar;
- top header;
- run status;
- scenario label;
- active-run metadata;
- page router;
- error banner;
- warning banner;
- loading state;
- responsive content area.

Deliverable: all final pages reachable.

---

# 27. PHASE 7 — Simulation Page

Core controls:

- scenario;
- duration;
- start date;
- seed;
- herd size;
- Run Simulation.

Feature switches:

- only verified backend-supported flags.

Do not port old dashboard controls automatically.

Deliverable: new UI can run the real Python model end-to-end.

---

# 28. PHASE 8 — Overview

Candidate KPI cards:

- total milk;
- average milk per cow;
- net profit;
- total revenue;
- total cost;
- net GHG;
- GHG intensity;
- FCR;
- freshwater withdrawal;
- energy self-sufficiency;
- circularity;
- sustainability;
- disease cases;
- herd size.

These are candidates until verified in `dashboard_metric_map.md`.

If unavailable:

- show `N/A`; or
- omit until supported.

Candidate overview charts:

1. Milk Production
2. Economics
3. Environmental Performance
4. Resource Use

Deliverable: immediate run summary.

---

# 29. PHASE 9 — Full Charts Page

Use a presentation-only chart registry.

Example:

```javascript
{
  id: "milk",
  title: "Milk Production",
  field: "milk_l",
  unit: "L",
  periods: ["daily", "monthly"]
}
```

Potential existing report series include:

- milk;
- purchased feed;
- irrigation;
- net energy;
- feedstock;
- electricity generation;
- biogas;
- heat;
- energy self-sufficiency;
- freshwater withdrawal;
- recycled irrigation;
- gross GHG;
- avoided GHG;
- net GHG;
- GHG intensity;
- circularity;
- NUE;
- soil carbon;
- fertilizer saved;
- sustainability;
- disease economic cost;
- profit.

Use backend daily/monthly/annual records.

Do not rebuild monthly/yearly scientific aggregates in JavaScript.

Deliverable: reusable chart workspace.

---

# 30. PHASE 10 — Circular Loops

Four sections:

## L1 — Nutrient
Use actual mapped manure/nutrient/fertilizer outputs.

## L2 — Water
Use actual mapped water/recycling/freshwater outputs.

## L3 — Energy
Use actual mapped feedstock/biogas/electricity/heat/energy outputs.

## L4 — Byproduct
Use actual mapped processor/whey/sludge/feed/energy outputs.

## Flow diagram

Fixed topology, backend-driven state.

Possible nodes:

```text
Cow
Milk
Processor
Whey
Feed
Manure
Digester
Energy
Water Treatment
Crops
```

Connection state:

- active;
- inactive;
- unavailable.

Do not visually compare incompatible units as though they are the same stream magnitude.

Deliverable: old dashboard loop UX using Python output.

---

# 31. PHASE 11 — Cow Performance

First define the exact current per-cow record contract.

Candidate columns:

- Cow ID
- Milk/day
- DMI
- FCR
- Days in Milk
- Parity
- Body Weight
- BCS
- Health State
- Rumen pH
- SARA
- Pregnancy State
- Feed-Efficiency Trait
- Genetic Traits
- Methane Intensity

Only include fields that exist.

Ranking must use direct real metrics.

Do not restore the old arbitrary 1–99 efficiency-score formula.

Candidate charts:

- Milk vs FCR;
- DMI vs Milk;
- health-state counts;
- trait distributions.

Deliverable: traceable cow explorer.

---

# 32. PHASE 12 — Scenario Comparison Backend

`POST /api/compare` should perform real Python reruns.

Request:

```json
{
  "runs": [
    {
      "label": "Baseline",
      "scenario": "baseline.json",
      "scenario_overrides": {},
      "calibration_overrides": {}
    },
    {
      "label": "Alternative",
      "scenario": "baseline.json",
      "scenario_overrides": {},
      "calibration_overrides": {}
    }
  ]
}
```

Backend:

1. validates each config;
2. runs each model independently;
3. serializes each result;
4. selects comparison-safe metrics;
5. computes display deltas;
6. returns all results.

Use the same seed by default for controlled comparisons unless explicitly changed.

Deliverable: correct model-to-model comparison.

---

# 33. PHASE 13 — Scenario Comparison UI

Modes:

1. Baseline vs Current
2. Individual Loop Comparison
3. User-Selected Scenarios
4. Optional Full L1-L4 Matrix

The full loop matrix means 16 actual model runs.

UI:

- table;
- absolute delta;
- percentage delta;
- selectable metric chart;
- run metadata;
- warnings when seeds/settings differ.

Directional coloring must be metric-aware.

For example:

- lower GHG may be favorable;
- higher profit may be favorable;
- higher disease burden is unfavorable.

Deliverable: old comparison UX with correct semantics.

---

# 34. PHASE 14 — Environment Page

Use actual environment ledger/packets/report fields.

Candidates:

- gross GHG;
- avoided GHG;
- net GHG;
- GHG intensity;
- soil carbon;
- fertilizer saved;
- NUE;
- circularity;
- sustainability.

Show individual source streams only when the model exposes them.

Do not reverse-engineer source emissions from totals.

Optional ledger:

| Date | Source | Stream | Value | Unit | Quality | Confidence |

Deliverable: auditable environmental page.

---

# 35. PHASE 15 — Economics Page

Use model/report/manager outputs only.

Candidate sections:

Revenue:
- milk;
- processing;
- energy;
- other actual backend categories.

Costs:
- feed;
- water;
- disease/treatment;
- processing;
- energy;
- other backend categories.

Outputs:
- profit;
- cumulative profit if backend-supported;
- per-unit metrics only if explicitly defined.

If a needed category is not exposed, fix Python reporting first.

Deliverable: traceable economics page.

---

# 36. PHASE 16 — Equipment ROI

Reuse:

```text
dairy_abm/analysis/npv.py
```

Do not build an unrelated ROI engine in JavaScript.

Existing analysis already provides NPV logic and reads equipment benefit data.

Extend Python if needed with clearly defined functions such as:

```python
simple_payback(...)
roi_percent(...)
annualized_net_benefit(...)
equipment_analysis(...)
```

Equipment assumptions must come from backend configuration/calibration.

Never copy old dashboard CapEx/savings constants without explicit sourcing/configuration.

Candidate cards:

- Anaerobic Digester
- CHP
- Separator
- Water Recycling
- Solar
- Dairy Processor
- Whey Processing
- Sensors

Only show equipment represented by current model/configuration.

Deliverable: repository-native ROI analysis.

---

# 37. PHASE 17 — Parameter Editor

Generate from:

```text
GET /api/calibration
        ↓
calibration_inventory()
```

Do not hand-code hundreds of fields.

Each parameter shows:

- display name;
- dotted key;
- value;
- unit;
- source;
- assumption;
- description;
- valid range.

Controls:

- boolean → toggle;
- numeric → number input;
- enum → select if supported.

UX:

- search;
- group filter;
- assumption filter;
- changed-only filter;
- reset field;
- reset group;
- reset all;
- source badge;
- assumption badge;
- validation messages.

Deliverable: dynamic calibration editor.

---

# 38. PHASE 18 — Model Details

Read-only.

Show:

- scenario;
- start date;
- duration;
- seed;
- herd size;
- enabled systems;
- loop states;
- run duration;
- calibration override count;
- assumption count;
- warnings;
- policy summary;
- event count;
- report-contract information.

Do not hard-code "13 active agents."

Land is optional, so component status must be derived from actual configuration.

Deliverable: transparent run description.

---

# 39. PHASE 19 — Export Center

Reuse official `write_reports()` output.

Expose:

- Summary JSON
- Daily CSV
- Schedule CSV
- Monthly CSV
- Annual CSV
- Calibration Inventory
- Full ZIP

Optional presentation exports:

- Scenario Comparison CSV
- Chart SVG
- Chart PNG

Official model reports must never be rebuilt in JavaScript.

Deliverable: unified export page.

---

# 40. PHASE 20 — Responsive and Accessibility Polish

Requirements:

- collapsible sidebar;
- normal laptop-first layout;
- scrollable large tables;
- keyboard focus;
- readable chart labels;
- clear empty states;
- loading states;
- consistent units;
- accessible form labels;
- no unnecessary animation.

Deliverable: usable final UI.

---

# 41. Testing Strategy

## Preserve current tests

Do not delete good tests merely because code moved.

Migrate them.

## Add backend tests

- dashboard serializer;
- `/api/config`;
- `/api/calibration`;
- `/api/run/<id>`;
- `/api/compare`;
- calibration override validation;
- calibration isolation;
- missing values;
- unsupported values;
- run cache;
- export consistency.

## Add frontend tests

Keep the current lightweight Node approach where practical.

Test:

- API request building;
- navigation;
- run button;
- loading;
- errors;
- scenario selection;
- feature toggles;
- parameter overrides;
- chart registry;
- comparison;
- cow sorting;
- exports.

## Add static-serving tests

- root page;
- CSS;
- JS;
- missing asset;
- path-traversal rejection.

---

# 42. Required Regression Tests

## CLI/Web Scientific Equivalence

For identical:

- scenario;
- scenario overrides;
- calibration overrides;
- seed;
- days;
- herd size;

the Python results through CLI/model and web must match.

Frontend formatting may differ.

Scientific output may not.

## Export Consistency

For one cached run:

1. request dashboard JSON;
2. request ZIP export;
3. verify both map to the same `SimulationContext`.

## Comparison Consistency

`POST /api/compare(A,B)` must contain the same run outputs as running A and B separately.

## Parameter Isolation

Run:

```text
A: parameter X = value 1
B: parameter X = value 2
C: default
```

Verify no run contaminates the next.

---

# 43. Unsupported Metric Policy

Never fill missing dashboard space with guessed values.

Use:

- `N/A`
- `Not available in current model`
- `Disabled`
- `No data for selected period`

Distinguish:

- zero;
- missing;
- disabled;
- unsupported.

---

# 44. Units, Source, and Confidence

Backend/report units are authoritative.

Browser may format but should not silently change scientific units.

Where available, preserve:

- source;
- assumption;
- quality;
- confidence.

Badges may include:

- Source
- Assumption
- Observed
- Estimated
- Disabled
- N/A

Do not infer confidence in JavaScript.

---

# 45. Performance

Initial target:

- local use;
- up to 3650 days;
- normal herd configurations;
- 10 cached runs.

Use:

- backend monthly/annual records;
- lazy chart creation;
- visual downsampling only;
- optional serialized-result caching;
- table virtualization only if needed.

Do not add background-job infrastructure until profiling proves it is necessary.

---

# 46. Error Handling

Use:

- `400` for invalid client configuration;
- `404` for missing run/assets;
- `500` for actual unexpected backend failures.

UI should present readable messages.

---

# 47. Security / Local Safety

Even locally:

- block scenario path traversal;
- block static-file path traversal;
- whitelist calibration keys;
- do not evaluate input strings;
- do not expose arbitrary repository files;
- cap request size;
- escape user/config-derived text.

---

# 48. Final Repository Layout

```text
research-agents/
├── configs/
│   └── calibration.json
│
├── dairy_abm/
│   ├── agents/
│   ├── analysis/
│   │   └── npv.py
│   ├── cli.py
│   ├── config.py
│   ├── core.py
│   ├── dashboard.py          # NEW
│   ├── model.py
│   └── reports.py
│
├── docs/
│   ├── dashboard_metric_map.md   # NEW
│   └── ...
│
├── scenarios/
│
├── tests/
│   ├── test_dashboard_serializer.py   # NEW
│   ├── test_webapp.py
│   └── ...
│
├── web/
│   ├── index.html
│   ├── styles/
│   └── js/
│       ├── components/
│       └── pages/
│
├── webapp.py                 # KEEP + REFACTOR
└── package.json
```

---

# 49. Files That Should Normally Stay Untouched During UI Work

Unless a genuine missing output or bug is discovered, avoid modifying:

```text
dairy_abm/agents/*
dairy_abm/model.py
```

If a page cannot display a value, first determine:

> Is this a dashboard exposure problem, or does the model truly not compute it?

Prefer fixing serialization/reporting before changing scientific model code.

---

# 50. Exact Implementation Order

```text
1. Run current test suite.
2. Freeze current web/CLI baseline.
3. Create dashboard metric inventory.
4. Add dairy_abm/dashboard.py.
5. Add serializer tests.
6. Expand API while preserving current routes.
7. Add per-run calibration overrides.
8. Add validation tests.
9. Add safe static-file serving.
10. Extract current inline PAGE into web/.
11. Reproduce current run desk from static frontend.
12. Migrate existing client/visual tests.
13. Build dashboard shell.
14. Build Simulation.
15. Build Overview.
16. Build Charts.
17. Build Circular Loops.
18. Build Cow Performance.
19. Build Scenario Comparison backend.
20. Build Scenario Comparison UI.
21. Build Environment.
22. Build Economics.
23. Extend/reuse NPV analysis for Equipment ROI.
24. Build Equipment ROI.
25. Build Parameter Editor.
26. Build Model Details.
27. Build Export center.
28. Responsive/accessibility polish.
29. Run full regression suite.
30. Verify CLI/web scientific equivalence.
```

Do not jump directly to visual pages before the data/API work is stable.

---

# 51. Milestones

## Milestone A — Architecture Complete

- existing model preserved;
- `dashboard.py` exists;
- API contract stable;
- calibration overrides isolated;
- static frontend exists;
- old inline monolith removed or reduced to loader;
- old functionality preserved.

## Milestone B — Core Dashboard

- Simulation;
- Overview;
- Charts;
- Circular Loops;
- no duplicated formulas;
- missing values handled correctly.

## Milestone C — Analysis Dashboard

- Cow Performance;
- Scenario Comparison;
- Environment;
- Economics;
- Equipment ROI;
- Parameters.

## Milestone D — Final Local Dashboard

- Model Details;
- Exports;
- responsive layout;
- accessibility;
- all tests pass;
- CLI/web equivalence verified.

---

# 52. Definition of Done

The rebuild is complete only if:

1. `DairyFarmModel` remains the simulation authority.
2. Old `simulateDay()` logic is absent.
3. Old `HerdModel` logic is absent.
4. `webapp.py` remains the local server entrypoint.
5. `webapp.py` is no longer a giant UI/calculation file.
6. `dairy_abm/dashboard.py` owns dashboard serialization.
7. Official report generation remains in `reports.py`.
8. NPV/ROI reuses `dairy_abm/analysis/npv.py`.
9. Parameters come from `calibration_inventory()`.
10. Calibration overrides are per-run and validated.
11. Existing API behavior is migrated without needless breakage.
12. Charts use Python-produced values.
13. Scenario comparison runs the Python model.
14. Cow pages use actual cow records.
15. Circular-loop UI uses actual loop outputs.
16. Environment uses actual environment outputs.
17. Economics uses backend accounting.
18. Unsupported values are not fabricated.
19. Existing tests are migrated rather than discarded.
20. Identical inputs produce identical scientific results through CLI/model and web.

---

# 53. Final Architecture

```text
                           OLD DASHBOARD HTML
                         UI / UX REFERENCE ONLY
                                  │
                                  │ layout ideas
                                  ▼
┌───────────────────────────────────────────────────────────────┐
│                         web/                                  │
│                                                               │
│ Overview · Simulation · Charts · Loops · Comparison           │
│ Cows · Environment · Economics · ROI · Parameters · Export    │
│                                                               │
│ Plain HTML + CSS + ES modules + SVG                           │
└──────────────────────────────┬────────────────────────────────┘
                               │ JSON
                               ▼
┌───────────────────────────────────────────────────────────────┐
│                       webapp.py                               │
│                                                               │
│ stdlib ThreadingHTTPServer                                    │
│ routes · static files · validation · run cache · exports      │
└──────────────────────────────┬────────────────────────────────┘
                               │
                  ┌────────────┴────────────┐
                  ▼                         ▼
┌──────────────────────────┐    ┌──────────────────────────────┐
│ dairy_abm/dashboard.py   │    │ dairy_abm/reports.py         │
│                          │    │                              │
│ normalized UI contract   │    │ official JSON/CSV reports    │
│ warnings                 │    │ report contract              │
│ comparison presentation  │    │ calibration inventory export │
└────────────┬─────────────┘    └──────────────┬───────────────┘
             │                                  │
             └──────────────┬───────────────────┘
                            ▼
┌───────────────────────────────────────────────────────────────┐
│                     DairyFarmModel                            │
│                                                               │
│ existing rewritten model · packets · state · records          │
│ existing scientific formulas · existing scenario behavior     │
│ optional Land component when enabled                          │
└──────────────────────────────┬────────────────────────────────┘
                               │
                               ▼
┌───────────────────────────────────────────────────────────────┐
│                    SimulationContext                          │
│                                                               │
│ daily · monthly · annual · schedule · packets · events · state│
└───────────────────────────────────────────────────────────────┘
```

---

# 54. Rule That Overrides Everything Else

Keep the visual strengths of the old dashboard.

Keep the existing Python model and rewritten formulas from `research-agents`.

Do not merge two simulation engines.

There must be exactly **one** simulation truth:

```text
DairyFarmModel
```

Everything in the new dashboard is a view, control surface, comparison layer, or export layer over that model.
