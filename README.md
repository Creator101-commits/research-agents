# Dairy ABM

> Agent-based model of a dairy farm for simulating milk production, emissions, energy, water, and economic performance.

A zero-dependency Python simulation of a dairy farm using 13 agent-based model (ABM) components. Each day, agents for cows, feed crops, manure, energy, disease, water, market, and more interact through a packet-based messaging system to produce detailed physical, environmental, and economic outputs. Designed for research, policy analysis, and education, no external packages required.

## Table of Contents

- [Dairy ABM](#dairy-abm)
- [Quickstart / Demo](#quickstart--demo)
- [Installation](#installation)
- [Usage](#usage)
- [Architecture](#architecture)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Quickstart / Demo
[(Back to top)](#table-of-contents)

Run a 10-day baseline simulation and inspect the outputs:

```sh
python3 -m dairy_abm run \
  --scenario scenarios/baseline.json \
  --output output/
```

This produces six output files:

| File | Contents |
|------|----------|
| `summary.json` | Simulation metadata, scenario flags, policy state, report contract, events, latest packets |
| `calibration_inventory.json` | All 200+ calibration parameters with metadata (source, range, assumption flag) |
| `daily.csv` | Per-day agent outputs (milk, DMI, manure, enteric CH4, biogas, kWh, heat, water, GHG streams, circularity, profit, disease economics, processor metrics, NUE, sustainability score, policy conflicts) |
| `schedule.csv` | Phase execution log (daily, weekly, monthly, annual) |
| `monthly.csv` | Monthly aggregates (milk, emissions, profit, soil carbon, fertiliser saved) |
| `annual.csv` | Annual genetics summary (genetic gain, net merit, breeding candidates, selection details) |

`summary.json` also includes a `report_contract` section describing the period, units, and confidence semantics for the principal daily, monthly, annual, and experiment-level KPIs. Each `daily.csv` row includes `report_confidence`, a pipe-delimited `source:quality/confidence` summary for the packets used to produce that row.

```sh
ls output/
# annual.csv  calibration_inventory.json  daily.csv  monthly.csv  schedule.csv  summary.json
```

## Installation
[(Back to top)](#table-of-contents)

**Requirements:** Python 3.10+ - no third-party packages.

```sh
git clone https://github.com/Creator101-commits/research-agents.git
cd research-agents
```

That is it. The project uses only the Python standard library (`datetime`, `random`, `json`, `csv`, `argparse`, `pathlib`, `typing`, `unittest`).

## Usage
[(Back to top)](#table-of-contents)

### Run a simulation

```sh
python3 -m dairy_abm run --scenario scenarios/baseline.json --output output/
```

Override scenario parameters at the command line:

```sh
python3 -m dairy_abm run \
  --scenario scenarios/baseline.json \
  --output output/ \
  --days 365 \
  --seed 42 \
  --enable-processor \
  --enable-whey-processing \
  --enable-land-agent \
  --disable-l1-loop
```

Use `--enable-l1-loop` / `--disable-l1-loop`, `--enable-l2-loop` / `--disable-l2-loop`, `--enable-l3-loop` / `--disable-l3-loop`, or `--enable-l4-loop` / `--disable-l4-loop` to override a loop setting in a scenario file for a single run.

### Validate calibration config

```sh
python3 -m dairy_abm validate-config
```

### List calibration parameters

```sh
python3 -m dairy_abm list-calibrations
```

Export to JSON:

```sh
python3 -m dairy_abm list-calibrations --output inventory.json
```

### Scenario format

Scenarios are JSON files with these supported keys:

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `name` | string | `"unnamed"` | Scenario label |
| `start_date` | string | `"2026-01-01"` | First simulation day (ISO format) |
| `days` | int | `1` | Number of simulation days |
| `seed` | int | `1` | RNG seed for deterministic replay |
| `herd_size` | int | `100` | Initial number of cows |
| `land_cropland_ha` | float | calibration default | Cropland hectares |
| `land_pasture_ha` | float | calibration default | Pasture hectares |
| `enable_processor` | bool | `false` | Enable dairy processor agent |
| `enable_whey_processing` | bool | `false` | Enable whey processing route |
| `enable_land_agent` | bool | `false` | Enable land management agent |
| `l1_nutrient_loop_enabled` | bool | calibration default (`true`) | Enable compost-derived feed credits for the following day |
| `l2_water_loop_enabled` | bool | calibration default (`true`) | Enable recovered-water credits for the following day's irrigation demand |
| `l3_energy_loop_enabled` | bool | calibration default (`true`) | Enable biogas energy generation without a cross-agent mass credit |
| `l4_byproduct_loop_enabled` | bool | calibration default (`true`) | Enable whey-derived feed credits for the following day when processing is active |
| `market_mode` | string | `"static"` | `"static"`, `"observed"`, or `"observed_plus_shock"` pricing mode |
| `market_data_csv` | string | none | Optional observed-price CSV used by observed market modes |
| `market_scenario` | string | `"NM"` | Genetics breeding objective: `NM` (net merit), `CM` (cheese), `FM` (fluid), `GM` (grazing) |
| `land_seasonal_availability` | object | none | Optional month-to-availability-fraction mapping when Land is enabled |
| `land_grazing_enabled` | bool | `false` | Publish optional grazing-access context when Land is enabled |
| `land_allocation` | object | none | Optional cropland/pasture share split |
| `policy_updates` | object | none | Dated policy override map keyed by ISO date or `"default"` |
| `biosecurity_level_pct` | float | `0.0` | Biosecurity level (0-100) reducing disease transmission |
| `vaccination_policy_active` | bool | `false` | Enable vaccination rollout |
| `vaccination_target_coverage` | float | `1.0` | Target fraction of herd to vaccinate |
| `catch_crop_active` | bool | `false` | Enable catch-crop N leaching reduction |
| `amino_acid_policy_active` | bool | calibration default | Enable amino-acid balancing for CP reduction |
| `amino_acid_cp_reduction_fraction` | float | `0.06` | Crude protein reduction via amino acid balancing (max 0.15) |
| `energy_conversion_mode` | string | `"chp"` | Conversion mode: `"chp"`, `"electricity"`, or `"boiler"` |
| `solar_capacity_kw` | float | `0.0` | Installed solar PV capacity |
| `herd` | array | none | Optional explicit cow definitions with trait overrides |
| `estrus_required_for_conception` | bool | `true` | Whether estrus detection is needed for conception |
| `milk_density_kg_per_l` | float | `1.03` | Milk density for class-price per-L conversion |
| `use_usda_component_pricing` | bool | `false` | Use USDA component-based milk pricing |
| `enable_disease_outbreak` | bool | `false` | Enable scheduled disease outbreak |
| `disease_outbreak_tick` | int | `100` | Tick at which outbreak is seeded |
| `disease_outbreak_label` | string | `"mastitis"` | Disease label for outbreak |
| `disease_outbreak_seed_count` | int | `1` | Number of initially infected cows |
| `initial_cash_balance` | float | `0.0` | Opening farm cash balance |
| `circular_investment_schedule` | array | none | List of dated investment costs |
| `equipment_capex` | object | none | Equipment capex map for ROI calculations |

`enable_whey_processing` requires `enable_processor`. Land-specific overrides (`land_seasonal_availability`, `land_grazing_enabled`) require `enable_land_agent`. Invalid combinations fail during model construction rather than being ignored.

Observed market CSVs can provide a `date` column for daily selection, `year` plus `month`/`period` for monthly selection, or `year,frequency=annual` for annual fallback. Missing numeric values carry forward the last valid value for that field and set a low-confidence packet flag. Product fields named `price_per_l_milk_<product>` are consumed by the processor. Class-price observations are also exposed in `$ / L` using the configurable scenario milk-density convention.

## Model Boundaries
[(Back to top)](#table-of-contents)

- **Execution order is enforced.** Market and sensor observations are published first, followed by land context, feed rations, and management policy dispatch, then disease, water delivery, cow production, processor, manure, energy, water balance, environment accounting, and farm manager reporting. Genetics intake recording runs last. This ensures all downstream agents see the upstream state they depend on.
- **Land is optional**, but when enabled it supplies seasonal allocation, rotational grazing with paddock recovery, silvopastoral tree cover, and scenario-calibrated soil-carbon context. Land-specific scenario overrides require `enable_land_agent` or configuration will be rejected.
- **Environment retains a full stream-level GHG ledger**, tracking each emission and offset source (enteric CH4, storage CH4, unmanaged CH4, compost N2O, field N2O, energy grid displacement, fertiliser substitution, soil carbon) with direction (positive/avoided), period, and confidence. It reports signed net-carbon results, sustainability score (0-100), circularity indicators (Icirc/Ocirc), and cumulative KPIs across the run. Factors marked as assumptions still require scientific calibration.
- **Per-cow lifecycle** tracks age, parity, days in milk, body condition, body weight, rumen pH, SARA, pregnancy, calving, mortality, and per-cow trait vectors inherited from genetics. Heat stress (THI bands at 68 and 72) and SARA (sustained low rumen pH) reduce DMI and milk yield.
- **Disease uses a full SIR model** with outbreak seeding, transmission pressure (density-modulated), biosecurity, quarantine, vaccination rollout, inherited genetic resistance, and stress-susceptibility amplification. Herd immunity and cumulative outbreak economics are tracked.
- **Manure management** includes collection efficiency, storage inventory with overflow, NPK accounting per route (digester/compost/storage), digester co-feed assembly (manure + grass + food waste), thermochemical valorisation, and processor residue integration.
- **Energy** supports biogas (CHP/electricity/boiler conversion modes), solar PV, thermochemical syngas, parasitic load, farm demand capping, self-sufficiency reporting, heat recovery, and carbon credit valuation.
- **Market** supports three pricing modes: `static` (calibration defaults), `observed` (CSV-sourced daily/monthly/annual prices with forward-fill on missing values), and `observed_plus_shock` (CSV plus stochastic shocks). USDA class pricing and component pricing formulas are available.
- **Circular loops** (L1-L4) remain explicit, carrying feed, water, nutrient, and byproduct credits between days where the source packet is finalized after production.

### Calibration system

All model parameters live in `configs/calibration.json` (200+ parameters across all 13 agents). Each parameter includes:

```json
{
  "value": 0.35,
  "unit": "fraction",
  "valid_range": "0.26..0.43",
  "source": "abm_blueprint.html",
  "assumption": false,
  "description": "Midpoint default for RFI_fat heritability."
}
```

Parameters are organised per agent:

| Agent section | Key parameters |
|---------------|----------------|
| `cow` | Lactation parameters, DMI, heat stress (THI thresholds), SARA (pH threshold + consecutive ticks), reproduction (pregnancy rate, gestation, eligibility), mortality, BCS dynamics, grazing intake, milk protein, replacement maturity, wood-curve peak |
| `feed_crop` | Crop yield, irrigation, ration cost, crude protein fractions, metabolizable protein, NDF, ME, N leaching, seasonal yield modifier |
| `manure` | Route fractions (digester/compost/storage), collection efficiency, storage capacity, CH4/N2O emission factors, NPK ratios, digester feedstock fractions, thermochemical yields |
| `energy` | Feedstock kWh conversion, parasitic load, grid offset factor, farm demand, heat conversion, electricity price |
| `disease` | Mastitis/lameness probabilities, recovery, mortality, treatment cost, quarantine/vaccination/biosecurity effectiveness, transmission, stress multiplier, herd density modifier |
| `environment` | GWP100 factors, field N2O conversion, fertiliser offset, circularity weights |
| `farm_manager` | Labor/fixed cost, carbon credit price, objective weights (profit/environment/welfare/circularity), policy flags |
| `sensors` | Missing reading probability, DMI/milk noise fractions, THI calculation, estrus reliability (single/fused), rumen pH baseline, bolus replacement interval, NIR seasonality |
| `water` | Drinking/parlor rates, treatment recovery, water savings, wastewater return, nutrient recovery coefficient |
| `dairy_processor` | Product mix, whey yields by stream, sludge/waste fractions, product prices, residual route fractions (whey/sludge/waste milk to feed/energy) |
| `market` | Milk/feed/cull/electricity prices, shock stddev |
| `land` | Cropland/pasture hectares, tree cover, soil carbon index |
| `genetics` | Trait weights, heritability, selection intensity, phenotypic SD, generation interval, minimum intake record days, stress thresholds and multipliers |

Parameters marked `assumption: true` are implementation placeholders that require calibration before scientific use. Blueprint-anchored values (`assumption: false`) come from the `abm_blueprint.html` reference design.

Processor residual route fractions (`fraction_whey_to_feed`, `fraction_sludge_to_energy`, `fraction_waste_milk_to_feed`) are validated in the inclusive range `0.0..1.0`, including when calibration is modified in memory before a run. Manure route fractions (digester + compost + storage) are validated to sum to 1.0.

### Agent roster

| # | Agent | File | Responsibility |
|---|-------|------|----------------|
| 1 | Genetics | `genetics_agent.py` | Multi-trait selection (NM$/CM$/FM$/GM$), breeder's equation, offspring inheritance, EBV confidence, herd net-merit trend |
| 2 | Cow | `cow_agent.py` | Per-cow lifecycle (age, parity, DIM, BCS), NASEM expected-DMI, Wood lactation curve, heat stress (THI), SARA, reproduction (estrus/conception/calving), mortality, grazing, NUE |
| 3 | Feed/Crop | `feed_crop_agent.py` | Multi-source feed hierarchy (farm -> coproduct -> local -> import), inventory, soil N dynamics, amino-acid balancing, NIR profiling, seasonal yield modifiers |
| 4 | Manure | `manure_agent.py` | Collection efficiency, storage with overflow, NPK per route, digester co-feed (manure + grass + food waste), thermochemical route, processor residue |
| 5 | Energy | `energy_agent.py` | Biogas (CHP/electricity/boiler), solar, thermochemical syngas, grid displacement, self-sufficiency, heat recovery, carbon credits |
| 6 | Disease | `disease_agent.py` | SIR model, outbreak seeding, transmission, biosecurity, quarantine, vaccination, inherited resistance, stress susceptibility, herd immunity, economic costing |
| 7 | Environment | `environment_agent.py` | Stream-level GHG ledger, soil carbon, fertilizer offset, circularity (Icirc/Ocirc), sustainability score, carbon credits, cumulative KPIs |
| 8 | Farm Manager | `farm_manager_agent.py` | Policy dispatch (pre-production), multi-objective optimisation, automatic trigger responses, cash balance, circular investment ROI, equipment ROI, policy conflict detection |
| 9 | Sensors | `sensors_agent.py` | THI, DMI obs with bolus degradation, rumen pH/SARA, estrus detection (single/fused), thermal mastitis alerts, NIR profiling, fleet health |
| 10 | Water | `water_agent.py` | Pre-production drinking-water delivery, wastewater treatment with storage, recycled irrigation, nutrient recovery, amino-acid savings |
| 11 | Dairy Processor | `dairy_processor_agent.py` | Product stream routing (cheese/butter/yogurt/fresh/functional), whey/scotta/sludge valorisation, byproduct revenue, capacity limits, component balance |
| 12 | Market | `market_agent.py` | Static/observed/observed+shock pricing, USDA class pricing, component pricing, CSV forward-fill, volatility tracking |
| 13 | Land Management | `land_agent.py` | Seasonal availability, rotational grazing with paddock recovery, silvopastoral tree cover, soil carbon context |

## Architecture
[(Back to top)](#table-of-contents)

```
dairy_abm/
├── __init__.py          # Package entry, exports DairyFarmModel
├── __main__.py          # python3 -m dairy_abm entry
├── cli.py               # argparse CLI (run, validate-config, list-calibrations)
├── config.py            # Calibration loading, validation, inventory
├── core.py              # Packet, EventLog, SimulationContext, SimulationClock, BaseAgent
├── model.py             # DairyFarmModel - daily loop, phase scheduling
├── reports.py           # Output writer (summary, CSV, inventory)
└── agents/              # 13 agent implementations
    ├── cow_agent.py
    ├── dairy_processor_agent.py
    ├── disease_agent.py
    ├── energy_agent.py
    ├── environment_agent.py
    ├── farm_manager_agent.py
    ├── feed_crop_agent.py
    ├── genetics_agent.py
    ├── land_agent.py
    ├── manure_agent.py
    ├── market_agent.py
    ├── sensors_agent.py
    └── water_agent.py
```

Agents communicate through **packets** published to `SimulationContext`, not direct method calls. The simulation clock drives daily, weekly (Sunday), monthly (calendar end), and annual (Dec 31) phases with a deterministic, seeded RNG.

### Daily execution order

Each day follows a fixed phase order that respects biological and operational dependencies:

```
market.tick()          -> price and cost signals available
sensors.tick()         -> environmental observations (THI, DMI, pH, estrus)
[land.tick()]          -> seasonal availability, grazing context (if enabled)
feed_crop.tick()       -> rations prepared before cow production
farm_manager.dispatch_policy() -> policy actions applied before disease/cow
disease.tick()         -> infection state updated before cow tick
water.prepare_delivery() -> drinking-water constraint published
cow.tick()             -> milk, DMI, manure, CH4, reproduction, mortality
processor.tick()       -> milk processed into product streams
manure.tick()          -> manure routed, biogas generated, nutrients accounted
energy.tick()          -> biogas/solar converted to kWh, grid offset
water.tick()           -> water balance, treatment, recycled irrigation
environment.tick()     -> GHG ledger, circularity, sustainability score
farm_manager.tick()    -> P&L, ROI, recommendations, operating point
genetics.record_daily_intake() -> DMI observation quality for breeding candidates
```

This ordering ensures that management policy reaches disease before cows are affected, rations are ready before cow production, and water delivery is published before cows consume it.

## Development
[(Back to top)](#table-of-contents)

```sh
git clone https://github.com/Creator101-commits/research-agents.git
cd research-agents
```

### Run tests

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
```

Or via Bun (if installed):

```sh
bun test
```

Tests cover deterministic replay, agent contracts, calibration inventory, CLI integration, phase scheduling, loop timing, market replay, report contracts, energy balances, environment ledger, manure pathways, market-land integration, sensors-disease integration, water treatment, blueprint conformance, and mass/energy/economic conservation.

### Project conventions

- **No external dependencies** - standard library only
- **Packet-based agent communication** - agents publish and consume data through `SimulationContext.packets`
- **Calibration-first** - every parameter has metadata (source, range, assumption flag)
- **Deterministic** - same seed always produces identical output
- **Test-first** - new agents or parameters require corresponding tests

## Contributing
[(Back to top)](#table-of-contents)

Contributions are welcome. To propose a change:

1. Fork it (<https://github.com/Creator101-commits/research-agents/fork>)
2. Create your feature branch (`git checkout -b feature/fooBar`)
3. Commit your changes (`git commit -am 'Add some fooBar'`)
4. Push to the branch (`git push origin feature/fooBar`)
5. Open a new Pull Request

Please make sure the full test suite passes before opening a PR.

## License
[(Back to top)](#table-of-contents)

Distributed under the MIT License. See [`LICENSE`](./LICENSE) for more information.
