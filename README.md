# Dairy ABM

> Agent-based model of a dairy farm for simulating milk production, emissions, energy, water, and economic performance.

![GitHub last commit](https://img.shields.io/github/last-commit/Creator101-commits/research-agents)
![GitHub](https://img.shields.io/github/license/Creator101-commits/research-agents)
![GitHub issues](https://img.shields.io/github/issues-raw/Creator101-commits/research-agents)

A zero-dependency Python simulation of a dairy farm using 13 agent-based model (ABM) components. Each day, agents for cows, feed crops, manure, energy, disease, water, market, and more interact through a packet-based messaging system to produce detailed physical, environmental, and economic outputs. Designed for research, policy analysis, and education — no external packages required.

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
| `summary.json` | Simulation metadata, scenario flags, latest packets |
| `calibration_inventory.json` | All 70+ calibration parameters with metadata |
| `daily.csv` | Per-day agent outputs (milk, DMI, manure, revenue, emissions) |
| `schedule.csv` | Phase execution log (daily, weekly, monthly, annual) |
| `monthly.csv` | Monthly aggregates (environment, farm manager) |
| `annual.csv` | Annual genetics summary |

```sh
ls output/
# annual.csv  calibration_inventory.json  daily.csv  monthly.csv  schedule.csv  summary.json
```

## Installation
[(Back to top)](#table-of-contents)

**Requirements:** Python 3.10+ — no third-party packages.

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
  --enable-land-agent
```

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

### Calibration system

All model parameters live in `configs/calibration.json`. Each parameter includes:

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

Parameters marked `assumption: true` are implementation placeholders that require calibration before scientific use. Blueprint-anchored values (`assumption: false`) come from the `abm_blueprint.html` reference design.

### Agent roster

| # | Agent | File | Responsibility |
|---|-------|------|----------------|
| 1 | Genetics | `genetics_agent.py` | Annual breeding cycle, genetic trend |
| 2 | Cow | `cow_agent.py` | Milk, DMI, manure, enteric CH4, revenue |
| 3 | Feed/Crop | `feed_crop_agent.py` | Crop supply, purchased feed, irrigation |
| 4 | Manure | `manure_agent.py` | Digester/compost/storage routing, biogas, N2O |
| 5 | Energy | `energy_agent.py` | Digester kWh, parasitic load, grid offset |
| 6 | Disease | `disease_agent.py` | Mastitis/lameness transitions, milk loss |
| 7 | Environment | `environment_agent.py` | GHG accounting, circularity score |
| 8 | Farm Manager | `farm_manager_agent.py` | P&L, recommendations |
| 9 | Sensors | `sensors_agent.py` | Missing readings, health alerts |
| 10 | Water | `water_agent.py` | Drinking/parlor/irrigation, treatment recovery |
| 11 | Dairy Processor | `dairy_processor_agent.py` | Product mix, processing energy, whey |
| 12 | Market | `market_agent.py` | Milk price, feed cost, price shocks |
| 13 | Land Management | `land_agent.py` | Cropland/pasture, silvopastoral, soil carbon |

## Architecture
[(Back to top)](#table-of-contents)

```
dairy_abm/
├── __init__.py          # Package entry, exports DairyFarmModel
├── __main__.py          # python3 -m dairy_abm entry
├── cli.py               # argparse CLI (run, validate-config, list-calibrations)
├── config.py            # Calibration loading, validation, inventory
├── core.py              # Packet, EventLog, SimulationContext, SimulationClock, BaseAgent
├── model.py             # DairyFarmModel — daily loop, phase scheduling
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

All 46 tests cover deterministic replay, agent contracts, calibration inventory, CLI integration, phase scheduling, mass/energy conservation, and error rejection.

### Project conventions

- **No external dependencies** — standard library only
- **Packet-based agent communication** — agents publish and consume data through `SimulationContext.packets`
- **Calibration-first** — every parameter has metadata (source, range, assumption flag)
- **Deterministic** — same seed always produces identical output
- **Test-first** — new agents or parameters require corresponding tests

## Contributing
[(Back to top)](#table-of-contents)

Contributions are welcome. To propose a change:

1. Fork it (<https://github.com/Creator101-commits/research-agents/fork>)
2. Create your feature branch (`git checkout -b feature/fooBar`)
3. Commit your changes (`git commit -am 'Add some fooBar'`)
4. Push to the branch (`git push origin feature/fooBar`)
5. Open a new Pull Request

Please make sure all 46 tests pass before opening a PR.

## License
[(Back to top)](#table-of-contents)

Distributed under the MIT License. See [`LICENSE`](./LICENSE) for more information.
