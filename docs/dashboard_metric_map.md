# Dashboard Metric Map

Phase 1 inventory for the repository-native dashboard rebuild.

This document maps dashboard requirements to authoritative Python outputs before frontend work begins. It covers the metrics named in `docs/research-agents-dashboard-plan-2.md` and the fields currently used by `webapp.py`. It is a data contract planning document, not a second simulation specification.

## Authority and rules

- `DairyFarmModel` and its `SimulationContext` are the only scientific source of truth.
- `dairy_abm/reports.py::REPORT_CONTRACT` defines official report fields and units.
- `dairy_abm/dashboard.py` will be the only adapter between context data and dashboard JSON.
- The browser may format, sort, filter, and chart serialized values. It must not simulate or recreate model equations.
- `None` means unavailable. It must not be changed to `0` for display.
- A latest packet is a snapshot, not a time series. Historical series must use records or state histories.
- Existing per-day `report_confidence` and packet quality/confidence must be preserved.

## Status definitions

| Status | Meaning |
|---|---|
| `EXISTING` | The metric already exists in an authoritative record or official report field and can be consumed directly. |
| `BACKEND_AGGREGATE` | The required value is a reporting aggregate or ratio of authoritative outputs. The calculation belongs in Python, not JavaScript. |
| `BACKEND_EXPOSE` | The value already exists in a packet, state history, calibration inventory, or analysis module but is not in the current web response/report contract. |
| `MODEL_CHANGE` | The requested value needs historical state or a new authoritative output that the current model does not retain. |
| `UNSUPPORTED` | The current model does not represent the requested metric. Show `N/A`, disabled, or omit it. |

## Current authoritative output inventory

| Context source | Current contents | Dashboard use |
|---|---|---|
| `ctx.daily_records` | One flattened row per simulated day. Includes production, feed, manure, energy, water, environment, disease, processor, management, and confidence fields. | Primary daily series and run-level aggregates. |
| `ctx.monthly_records` | Calendar-month rows with `report` values of `environment` or `farm_manager`. | Existing monthly environment/economic reports. Preserve the `report` discriminator. |
| `ctx.annual_records` | Genetics trend rows and farm-manager genetics review rows. | Existing annual genetics/model outputs. Most other annual series need backend aggregation. |
| `ctx.schedule_records` | Date, phase, and executed agent names. | Scheduler/model-details page and schedule export. |
| `ctx.packets` | Latest packet for each packet name, including metadata and payload. | Latest-state cards, loop topology, current cow records, and packet provenance only. |
| `ctx.state` | Histories for environment, water, feed, manure, market, policy, sensors, genetics, and final per-cow state. | Backend-only exposure where the flattened report is incomplete. |
| `ctx.events.events` | Structured event records with date, source, level, message, and fields. | Warnings, event count, and audit details. |
| `REPORT_CONTRACT` | Official daily, monthly, annual, and experiment-level fields and units. | Contract metadata and export validation. |
| `calibration_inventory(ctx.calibration)` | Dotted key, agent, default, unit, source, assumption, description, and valid range. | Parameters page and calibration export. |
| `dairy_abm.analysis.npv` | NPV calculation and equipment cash-flow analysis from official outputs. | Equipment ROI/NPV page; do not reimplement in JavaScript. |

## Current web exposure

The Python dashboard adapter (`dairy_abm.dashboard`) exposes run metadata, the summary metric wrappers, and the chart series contract. Its daily display fields include:

`day`, `milk_l`, `dmi_kg`, `purchased_feed_kg_dm`, `irrigation_l`, `net_kwh`, `feedstock_tons`, `electricity_generated_kwh`, `biogas_volume_m3`, `biogas_gross_kwh`, `heat_generated_mj`, `energy_self_sufficiency_pct`, `freshwater_withdrawal_l`, `recycled_irrigation_l`, `recycled_irrigation_fraction`, `gross_kg_co2e`, `avoided_kg_co2e`, `net_kg_co2e`, `kg_co2e_per_l_milk`, `input_circularity`, `output_circularity`, `circularity_score`, `environment_nue`, `soil_carbon_delta_kg`, `synthetic_fertilizer_saved_kg`, `sustainability_score_0_100`, `new_disease_cases`, `active_disease_cases`, `disease_economic_cost`, `cow_count`, `total_revenue`, `total_cost`, `profit`, and `report_confidence`.

`series.monthly` and `series.annual` are backend-produced period rows. They use Python-owned sums, means, latest values, and ratios, then overlay authoritative monthly/annual report fields where those records exist. The compatibility workbench may still roll daily rows for its legacy Ledger / Graphs tabs; the full Charts page consumes these backend period series directly.
The compatibility workbench still rolls daily rows into monthly/yearly rows and derives intensity for its legacy tables. The full Charts route does not perform those roll-ups; it consumes the Python-produced `series` records.

# Metric map

## 1. Run metadata and model details

| UI Metric | Python Source | Field / Packet | Period | Unit | Aggregation | Status | Notes |
|---|---|---|---|---|---|---|---|
| Run ID | web/API run layer | generated `run_id` | run | identifier | none | `EXISTING` | Current web layer already generates an 8-character id. |
| Scenario name | `ctx.scenario` | `name` | run | text | none | `EXISTING` | Use `unnamed` only when the scenario has no name. |
| Start date | `ctx.scenario` | `start_date` | run | ISO date | none | `EXISTING` | The model clock uses this value. |
| Duration | `ctx.scenario` | `days` | run | days | none | `EXISTING` | Validate before model construction. |
| Seed | `ctx.scenario` | `seed` | run | integer | none | `EXISTING` | Required for deterministic replay. |
| Initial herd size | `ctx.scenario` | `len(herd)` when explicit, otherwise `herd_size` | run | cows | none | `EXISTING` | Explicit herd definitions take precedence over the numeric fallback. |
| Active herd count | `ctx.daily_records` | `cow_count` | daily | cows | latest/mean as labelled | `EXISTING` | Do not confuse active count with initial herd size. |
| Agent count | `ctx.daily_records` | `agent_count` | daily | count | latest | `EXISTING` | Derive enabled-agent status from actual records; do not hard-code 13. |
| Enabled systems | `ctx.scenario` and `ctx.state["policy"]` | processor, whey, land, L1-L4 and policy flags | run/daily | boolean | none | `EXISTING` | Feature flags must come from scenario/calibration capability. |
| Run duration | web/API run layer | `duration_s` | run | seconds | none | `EXISTING` | Wall-clock measurement, not a scientific result. |
| Event count | `ctx.events.events` | list length | run | count | count | `EXISTING` | The event list remains available for the detail view. |
| Warnings | `ctx.events.events` | `level` plus event fields | run/daily | structured text | filter warnings | `BACKEND_EXPOSE` | Serializer should produce readable warning objects without changing event data. |
| Scheduler execution order | `ctx.daily_records`, `ctx.schedule_records` | `execution_order`, `phase`, `agents` | daily/weekly/monthly/annual | text | none | `EXISTING` | Preserve the established scheduler order. |
| Policy summary | `ctx.state["policy"]`, `ctx.state["policy_history"]`, `manager_packet` | effective policy and actions | daily/run | structured text | latest/history | `BACKEND_EXPOSE` | Include automatic actions and policy conflicts. |
| Report-contract metadata | `REPORT_CONTRACT` | full contract | run | structured JSON | none | `EXISTING` | Expose contract metadata through the backend config/details response. |
| Calibration assumption count | `calibration_inventory(ctx.calibration)` | `assumption` | run | count | count true values | `BACKEND_AGGREGATE` | Count metadata only; do not infer scientific confidence. |
| Calibration override count | cached-run request metadata | override keys | run | count | count | `BACKEND_EXPOSE` | Store request metadata in the cached-run wrapper when overrides are added; no scientific model change is needed. |

## 2. Overview and core KPIs

| UI Metric | Python Source | Field / Packet | Period | Unit | Aggregation | Status | Notes |
|---|---|---|---|---|---|---|---|
| Total milk | `ctx.daily_records` | `milk_l` | daily/run | L | sum | `BACKEND_AGGREGATE` | Run total is a Python aggregate of daily model output. |
| Average milk per cow per day | `ctx.daily_records` | `milk_l`, `cow_count` | daily/run | L/cow/day | mean of `milk_l / cow_count` for positive counts | `BACKEND_AGGREGATE` | Label the denominator clearly. |
| Total purchased feed | `ctx.daily_records` | `purchased_feed_kg_dm` | daily/run | kg dry matter | sum | `BACKEND_AGGREGATE` | Use the report field, not a browser reconstruction. |
| Feed cost | `ctx.daily_records` | `feed_cost` | daily/run | currency | sum | `BACKEND_AGGREGATE` | Daily field is already reported by the manager path. |
| Total revenue | `ctx.daily_records` | `total_revenue` | daily/monthly/run | currency | sum | `BACKEND_AGGREGATE` | Monthly manager rows also contain this field. |
| Total cost | `ctx.daily_records` | `total_cost` | daily/monthly/run | currency | sum | `BACKEND_AGGREGATE` | Monthly manager rows also contain this field. |
| Net profit | `ctx.daily_records` | `profit` | daily/monthly/run | currency | sum | `BACKEND_AGGREGATE` | Do not infer profit from partial revenue categories. |
| Ending cash balance | `ctx.daily_records` | `cash_balance` | daily/run | currency | latest | `EXISTING` | Use the last simulated day for the run card. |
| Net GHG | `ctx.daily_records` or monthly environment rows | `net_kg_co2e` | daily/monthly/run | kg CO2e | sum | `BACKEND_AGGREGATE` | Preserve signed values. |
| Gross GHG | `ctx.daily_records` or monthly environment rows | `gross_kg_co2e` | daily/monthly/run | kg CO2e | sum | `BACKEND_AGGREGATE` | Source is the environment ledger result. |
| Avoided GHG | `ctx.daily_records` or monthly environment rows | `avoided_kg_co2e` | daily/monthly/run | kg CO2e | sum | `BACKEND_AGGREGATE` | Do not estimate avoided streams from net totals. |
| GHG intensity per litre | `ctx.daily_records` or environment report | `kg_co2e_per_l_milk` | daily/monthly/run | kg CO2e/L milk | ratio of total net GHG to total milk for aggregates | `BACKEND_AGGREGATE` | The ratio must be calculated in Python and be `None` when milk is zero. |
| GHG intensity per kg milk protein | `ctx.daily_records` or environment report | `kg_co2e_per_kg_milk_protein` | daily/monthly/run | kg CO2e/kg milk protein | ratio of totals for aggregates | `BACKEND_AGGREGATE` | Use the environment-produced protein denominator. |
| Feed conversion ratio | `cow_daily_packet`, `ctx.daily_records` | `feed_conversion_ratio_kg_dm_per_l` or `dmi_kg / milk_l` | daily/run | kg DM/L milk | ratio of total DMI to total milk | `BACKEND_AGGREGATE` | Do not use the old arbitrary efficiency score. |
| Freshwater withdrawal | `ctx.daily_records` | `freshwater_withdrawal_l` | daily/run | L | sum | `BACKEND_AGGREGATE` | Distinct from gross water use and net freshwater use. |
| Energy self-sufficiency | `ctx.daily_records` | `energy_self_sufficiency_pct` | daily/run | % | mean for a run | `BACKEND_AGGREGATE` | Preserve the model's percentage convention. |
| Overall circularity | `ctx.daily_records` | `circularity_score` | daily/run | fraction | mean/latest as labelled | `BACKEND_AGGREGATE` | Keep this distinct from input and output circularity. |
| Input circularity | `ctx.daily_records` | `input_circularity` | daily/run | fraction | mean | `BACKEND_AGGREGATE` | Direct environment output. |
| Output circularity | `ctx.daily_records` | `output_circularity` | daily/run | fraction | mean | `BACKEND_AGGREGATE` | Direct environment output. |
| Sustainability score | `ctx.daily_records` | `sustainability_score_0_100` | daily/run | score 0-100 | mean/latest as labelled | `BACKEND_AGGREGATE` | Preserve the model score; do not create another sustainability index. |
| Active disease cases | `ctx.daily_records` | `active_disease_cases` | daily/run | cows/cases | latest or peak, never an unlabelled sum | `BACKEND_AGGREGATE` | A sum of active cases is not a case count. |
| New disease cases | `ctx.daily_records` | `new_disease_cases` | daily/run | cases | sum | `BACKEND_AGGREGATE` | Separate incident cases from active prevalence. |
| Disease economic cost | `ctx.daily_records` | `disease_economic_cost` | daily/run | currency | sum | `BACKEND_AGGREGATE` | Use this label unless a separate treatment-cost history is exposed. |
| Herd size at end of run | `ctx.daily_records` | `cow_count` | daily/run | cows | latest | `EXISTING` | Births and mortality can make this differ from initial herd size. |

## 3. Chart series

The chart registry should reference these backend fields. The frontend may convert values to SVG coordinates, but all period grouping and scientific/reporting aggregation belongs in Python.

| Chart series | Python Source | Field / Packet | Period | Unit | Aggregation | Status | Notes |
|---|---|---|---|---|---|---|---|
| Milk production | `ctx.daily_records` | `milk_l` | daily/monthly/annual | L | daily direct; monthly report or backend roll-up; annual backend roll-up | `EXISTING` | Primary production series. |
| Purchased feed | `ctx.daily_records` | `purchased_feed_kg_dm` | daily/monthly/annual | kg DM | sum | `EXISTING` | Use purchased feed, not total DMI, for this series. |
| Irrigation | `ctx.daily_records` | `irrigation_l` | daily/monthly/annual | L | sum | `EXISTING` | Distinguish irrigation demand from delivered irrigation. |
| Net energy | `ctx.daily_records` | `net_kwh` | daily/monthly/annual | kWh | sum | `EXISTING` | Reported energy packet output. |
| Feedstock | `ctx.daily_records` | `feedstock_tons` | daily/monthly/annual | tonnes | sum | `EXISTING` | Convert only for presentation; backend unit is tonnes/day. |
| Electricity generated | `ctx.daily_records` | `electricity_generated_kwh` | daily/monthly/annual | kWh | sum | `EXISTING` | Include solar and conversion output only as represented by the energy agent. |
| Biogas volume | `ctx.daily_records` | `biogas_volume_m3` | daily/monthly/annual | m3 | sum | `EXISTING` | Direct energy output. |
| Biogas gross energy | `ctx.daily_records` | `biogas_gross_kwh` | daily/monthly/annual | kWh | sum | `EXISTING` | Direct energy output. |
| Heat generated | `ctx.daily_records` | `heat_generated_mj` | daily/monthly/annual | MJ | sum over available values | `EXISTING` | Values can be `None` for inactive conversion modes. |
| Energy self-sufficiency | `ctx.daily_records` | `energy_self_sufficiency_pct` | daily/monthly/annual | % | mean | `EXISTING` | Do not sum percentages. |
| Freshwater withdrawal | `ctx.daily_records` | `freshwater_withdrawal_l` | daily/monthly/annual | L | sum | `EXISTING` | Direct water output. |
| Recycled irrigation | `ctx.daily_records` | `recycled_irrigation_l` | daily/monthly/annual | L | sum | `EXISTING` | Direct water output. |
| Recycled irrigation fraction | `ctx.daily_records` | `recycled_irrigation_fraction` | daily/monthly/annual | fraction | mean or ratio of totals, labelled | `EXISTING` | Prefer the model's fraction for daily values and a documented ratio for aggregates. |
| Gross GHG | `ctx.daily_records` | `gross_kg_co2e` | daily/monthly/annual | kg CO2e | sum | `EXISTING` | Environment output. |
| Avoided GHG | `ctx.daily_records` | `avoided_kg_co2e` | daily/monthly/annual | kg CO2e | sum | `EXISTING` | Environment output. |
| Net GHG | `ctx.daily_records` | `net_kg_co2e` | daily/monthly/annual | kg CO2e | sum | `EXISTING` | Environment output. |
| GHG intensity | `ctx.daily_records` | `kg_co2e_per_l_milk` | daily/monthly/annual | kg CO2e/L milk | ratio of totals for roll-ups | `EXISTING` | Backend must own monthly/yearly calculation. |
| Input circularity | `ctx.daily_records` | `input_circularity` | daily/monthly/annual | fraction | mean | `EXISTING` | Environment output. |
| Output circularity | `ctx.daily_records` | `output_circularity` | daily/monthly/annual | fraction | mean | `EXISTING` | Environment output. |
| Circularity score | `ctx.daily_records` | `circularity_score` | daily/monthly/annual | fraction | mean | `EXISTING` | Environment output. |
| Nitrogen-use efficiency | `ctx.daily_records` | `environment_nue` or `nitrogen_use_efficiency` | daily/monthly/annual | fraction | mean or ratio of totals | `EXISTING` | Use one clearly named canonical field in the dashboard contract. |
| Soil carbon change | `ctx.daily_records` | `soil_carbon_delta_kg` | daily/monthly/annual | kg C/day or period | sum | `EXISTING` | This is change, not an absolute soil-carbon stock. |
| Synthetic fertilizer saved | `ctx.daily_records` or environment report | `synthetic_fertilizer_saved_kg` | daily/monthly/annual | kg N | sum | `EXISTING` | Preserve the report unit. |
| Sustainability score | `ctx.daily_records` | `sustainability_score_0_100` | daily/monthly/annual | score 0-100 | mean | `EXISTING` | Direct environment output. |
| Disease economic cost | `ctx.daily_records` | `disease_economic_cost` | daily/monthly/annual | currency | sum | `EXISTING` | Do not present active cases as cost. |
| Profit | `ctx.daily_records` | `profit` | daily/monthly/annual | currency | sum | `EXISTING` | Direct manager output. |

## 4. Circular loops

### L1: Nutrient loop

| UI Metric | Python Source | Field / Packet | Period | Unit | Aggregation | Status | Notes |
|---|---|---|---|---|---|---|---|
| L1 enabled | `ctx.scenario` / calibration | `l1_nutrient_loop_enabled` | run | boolean | none | `EXISTING` | Use scenario override first, then calibration default. |
| Manure produced | `ctx.daily_records` | `manure_kg` | daily/run | kg | sum | `EXISTING` | Cow output. |
| Digester route | `ctx.daily_records` | `digester_kg` | daily/run | kg | sum | `EXISTING` | Manure route output. |
| Compost route | `ctx.daily_records` | `compost_kg` | daily/run | kg | sum | `EXISTING` | Manure route output. |
| Storage route | `ctx.daily_records` | `storage_kg` | daily/run | kg | sum | `EXISTING` | Manure route output. |
| Digestate N/P/K | `ctx.packets["manure_packet"]` or `ctx.state["manure_flow_history"]` | `digestate_n_kg`, `digestate_p_kg`, `digestate_k_kg` | latest/daily | kg | sum for history | `BACKEND_EXPOSE` | Not flattened into `daily_records`; expose from the manure history. |
| Compost N/P/K | `ctx.packets["manure_packet"]` or manure history | `compost_n_kg`, `compost_p_kg`, `compost_k_kg` | latest/daily | kg | sum for history | `BACKEND_EXPOSE` | Preserve route identity. |
| Nutrient return | manure history/packet | `nutrient_return_kg` | daily/run | kg | sum | `BACKEND_EXPOSE` | Do not infer it from fertilizer savings. |
| Feed loop offset | `ctx.daily_records` | `feed_loop_offset_kg` | daily/run | kg | sum | `EXISTING` | This is a loop credit, not purchased feed. |
| Synthetic fertilizer saved | `ctx.daily_records` | `synthetic_fertilizer_saved_kg` | daily/run | kg N | sum | `EXISTING` | Environment-produced result. |
| L1 route alert | manure packet/history | `manure_route_alert` | daily | text | latest/list | `BACKEND_EXPOSE` | Show only when the model reports an alert. |

### L2: Water loop

| UI Metric | Python Source | Field / Packet | Period | Unit | Aggregation | Status | Notes |
|---|---|---|---|---|---|---|---|
| L2 enabled | `ctx.scenario` / calibration | `l2_water_loop_enabled` | run | boolean | none | `EXISTING` | Use the actual active flag. |
| Total water use | water packet/history | `total_water_use_l` | daily/run | L | sum | `BACKEND_EXPOSE` | Not the same as net freshwater use. |
| Net water use | `ctx.daily_records` | `net_water_l` | daily/run | L | sum | `EXISTING` | Direct daily report field. |
| Freshwater withdrawal | `ctx.daily_records` | `freshwater_withdrawal_l` | daily/run | L | sum | `EXISTING` | Direct daily report field. |
| Recycled irrigation | `ctx.daily_records` | `recycled_irrigation_l` | daily/run | L | sum | `EXISTING` | Direct daily report field. |
| Recycled irrigation fraction | `ctx.daily_records` | `recycled_irrigation_fraction` | daily/run | fraction | mean/ratio of totals | `EXISTING` | Keep the aggregation definition visible. |
| Water saving | water packet/history | `water_saving_l` | daily/run | L | sum | `BACKEND_EXPOSE` | Available in water history, not the flattened daily row. |
| Treatment active/capacity | water packet/history | `treatment_active`, `treatment_capacity_l_per_day` | daily | boolean/L/day | latest/series | `BACKEND_EXPOSE` | Supports an auditable water-treatment card. |
| Wastewater storage | water packet/history | `wastewater_storage_l` | daily | L | latest/series | `BACKEND_EXPOSE` | Do not use recycled irrigation as a storage proxy. |
| Recovered N/P/K | water packet/history | `recovered_n_kg`, `recovered_p_kg`, `recovered_k_kg` | daily/run | kg | sum | `BACKEND_EXPOSE` | Nutrient recovery is part of L2 and may feed L1 accounting. |
| Water use intensity | water packet/history | `water_use_l_per_litre_milk` | daily/run | L/L milk | ratio of totals for aggregates | `BACKEND_EXPOSE` | Use the model's water-environment field. |

### L3: Energy loop

| UI Metric | Python Source | Field / Packet | Period | Unit | Aggregation | Status | Notes |
|---|---|---|---|---|---|---|---|
| L3 enabled | `ctx.scenario` / calibration | `l3_energy_loop_enabled` | run | boolean | none | `EXISTING` | Use the actual active flag. |
| Feedstock | `ctx.daily_records` | `feedstock_tons` | daily/run | tonnes | sum | `EXISTING` | Direct energy output. |
| Biogas volume | `ctx.daily_records` | `biogas_volume_m3` | daily/run | m3 | sum | `EXISTING` | Direct energy output. |
| Biogas gross energy | `ctx.daily_records` | `biogas_gross_kwh` | daily/run | kWh | sum | `EXISTING` | Direct energy output. |
| Electricity generated | `ctx.daily_records` | `electricity_generated_kwh` | daily/run | kWh | sum | `EXISTING` | Direct energy output. |
| Net energy | `ctx.daily_records` | `net_kwh` | daily/run | kWh | sum | `EXISTING` | Direct energy output. |
| Heat generated | `ctx.daily_records` | `heat_generated_mj` | daily/run | MJ | sum available values | `EXISTING` | `None` is valid for inactive modes. |
| Energy self-sufficiency | `ctx.daily_records` | `energy_self_sufficiency_pct` | daily/run | % | mean | `EXISTING` | Direct report field. |
| Energy value | `ctx.daily_records` | `energy_value` | daily/run | currency | sum | `EXISTING` | Manager accounting input. |
| Energy GHG offset | `ctx.daily_records` or environment history | `energy_offset_kg_co2e` | daily/run | kg CO2e | sum | `EXISTING` | Environment ledger output. |
| Solar/thermochemical details | energy packet/history | `solar_generated_kwh`, `thermochemical_input_kwh`, conversion fields | daily | kWh/metadata | series | `BACKEND_EXPOSE` | Show only when represented by the active energy configuration. |

### L4: Byproduct loop

| UI Metric | Python Source | Field / Packet | Period | Unit | Aggregation | Status | Notes |
|---|---|---|---|---|---|---|---|
| L4 enabled | `ctx.scenario` / calibration | `l4_byproduct_loop_enabled` | run | boolean | none | `EXISTING` | Processor output is still disabled unless processor is enabled. |
| Processor enabled | `ctx.daily_records` / processor packet | `processor_enabled`, `enabled` | daily/latest | boolean | latest/series | `EXISTING` | Respect inactive packet quality. |
| Milk processed | `ctx.daily_records` | `milk_processed_l` | daily/run | L | sum | `EXISTING` | Direct daily report field. |
| Product streams | processor packet/history | `product_streams_l` | latest/daily | L | sum for history | `BACKEND_EXPOSE` | Current daily rows do not retain the product-stream map. |
| Whey | `ctx.daily_records` / processor packet | `whey_l` | daily/run | L | sum | `EXISTING` | Direct daily field when processor is active. |
| Scotta | `ctx.daily_records` / processor packet | `scotta_l` / `scotta_output_l` | daily/run | L | sum | `EXISTING` | Preserve the field name distinction in the adapter. |
| Sludge and waste milk | processor packet/history | `sludge_l`, `waste_milk_l` | latest/daily | L | sum for history | `BACKEND_EXPOSE` | Current flattened rows do not include both fields. |
| Valorized residuals | processor packet/history | `valorized_residual_l` | latest/daily | L | sum for history | `BACKEND_EXPOSE` | Use actual route output. |
| Byproduct route state | processor packet | `route_tiers`, processor residual packet | latest | structured text | none | `BACKEND_EXPOSE` | Needed for active/inactive/unavailable flow states. |
| Byproduct feed return | processor residual/return packet | `whey_feed_l`, `scotta_feed_l`, `waste_milk_feed_l`, `feed_eligible_kg_dm` | latest/daily | L/kg DM | sum for history | `BACKEND_EXPOSE` | Preserve food-safety approval and blocked states. |
| Byproduct revenue | processor packet/manager packet | `byproduct_revenue` | latest/daily | currency | sum for history | `MODEL_CHANGE` | The model computes it daily but does not retain a historical flattened series. |

## 5. Cow performance

The current authoritative per-cow record is `ctx.packets["cow_daily_packet"].payload["cow_records"]`. It is a latest-day snapshot. `ctx.state["cows"]` contains final lifecycle state and per-cow histories, but those histories are not date-labelled records.

| UI Metric | Python Source | Field / Packet | Period | Unit | Aggregation | Status | Notes |
|---|---|---|---|---|---|---|---|
| Cow ID | cow daily packet | `cow_records[*].id` | latest day | text | none | `EXISTING` | Stable identifier. |
| Milk/day | cow daily packet | `cow_records[*].milk_l` | latest day | L/day | none | `EXISTING` | Direct per-cow output. |
| DMI | cow daily packet | `cow_records[*].dmi_kg` | latest day | kg DM/day | none | `EXISTING` | Direct per-cow output. |
| Per-cow FCR | cow daily packet | `dmi_kg / milk_l` | latest day | kg DM/L | ratio | `BACKEND_AGGREGATE` | Only calculate when milk is positive. |
| Days in milk | cow daily packet | `cow_records[*].days_in_milk` | latest day | days | none | `EXISTING` | Direct per-cow output. |
| Parity | cow daily packet | `cow_records[*].parity` | latest day | count | none | `EXISTING` | Direct per-cow output. |
| Body weight | `ctx.state["cows"]` | `body_weight_kg` | final state | kg | none | `BACKEND_EXPOSE` | Not currently in `cow_records`. |
| Body condition score | `ctx.state["cows"]` | `body_condition_score` | final state | score | none | `BACKEND_EXPOSE` | Not currently in `cow_records`. |
| Health state | cow daily packet/state | `health_status` | latest/final | text | none | `EXISTING` | Direct daily record plus lifecycle state. |
| Rumen pH | cow daily packet | `cow_records[*].rumen_ph` | latest day | pH | none | `EXISTING` | Preserve missing readings as unavailable. |
| SARA state | cow daily packet | `cow_records[*].sara_active` | latest day | boolean | none | `EXISTING` | Direct per-cow output. |
| Pregnancy state | `ctx.state["cows"]` | `pregnant`, `days_pregnant` | final state | boolean/days | none | `BACKEND_EXPOSE` | Only aggregate pregnant count is currently in the cow packet. |
| Observed DMI | cow daily packet | `observed_dmi_kg` | latest day | kg DM/day | none | `EXISTING` | May be `None` when the sensor reading is missing. |
| Actual/expected DMI | cow daily packet | `actual_dmi_kg_dm`, `expected_dmi_eq2_1_kg_dm` | latest day | kg DM/day | none | `EXISTING` | Useful for traceable feed-efficiency views. |
| Estrus detected | cow daily packet | `estrus_detected` | latest day | boolean | none | `EXISTING` | Sensor-derived observation. |
| Feed-efficiency trait | `ctx.state["cows"]` | `feed_efficiency_trait` / `trait_vector` | final state | trait score | none | `BACKEND_EXPOSE` | Use the actual genetic trait, not a dashboard score. |
| Genetic traits | `ctx.state["cows"]` | `trait_vector` | final state | trait values | none | `BACKEND_EXPOSE` | Preserve trait names and values. |
| Methane intensity per cow | per-cow state histories | `ch4_history` and `milk_history` | final/latest | kg CH4/L milk | latest ratio | `BACKEND_EXPOSE` | Historical date alignment is not retained in the current state shape. |
| Cow ranking | cow records | direct milk, DMI, FCR, health fields | latest day | presentation | sort | `BACKEND_AGGREGATE` | Sort only by selected real metrics. Do not restore the old 1-99 formula. |
| Health-state counts | disease/cow packets | `active_cases`, `healthy_cows`, `sick_cows` | daily/latest | cows/cases | count | `EXISTING` | Keep disease counts distinct from cow health states. |
| Trait distributions | final cow state | `trait_vector` | final state | trait values | distribution | `BACKEND_EXPOSE` | Current model supplies the values; frontend only charts them. |
| Historical per-cow table | no dated per-cow record collection | — | run | — | — | `MODEL_CHANGE` | Add dated per-cow records only if historical cow exploration is required. |

## 6. Environment and audit ledger

| UI Metric | Python Source | Field / Packet | Period | Unit | Aggregation | Status | Notes |
|---|---|---|---|---|---|---|---|
| Gross GHG | environment packet/history | `gross_kg_co2e` | daily/monthly/run | kg CO2e | sum | `EXISTING` | Environment output. |
| Avoided GHG | environment packet/history | `avoided_kg_co2e` | daily/monthly/run | kg CO2e | sum | `EXISTING` | Environment output. |
| Net GHG | environment packet/history | `net_kg_co2e` | daily/monthly/run | kg CO2e | sum | `EXISTING` | Signed result. |
| GHG intensity | environment packet/history | `kg_co2e_per_l_milk`, `kg_co2e_per_kg_milk_protein` | daily/monthly/run | kg CO2e per product unit | ratio of totals for aggregates | `EXISTING` | Preserve `None` for zero denominators. |
| Soil carbon change | environment packet/history | `soil_carbon_delta_kg` | daily/monthly/run | kg C | sum | `EXISTING` | This is change, not stock. |
| Soil organic carbon stock | `ctx.state` | `soil_organic_carbon` | final state | model-specific | latest | `BACKEND_EXPOSE` | Expose only with the model's declared unit. |
| Fertilizer saved | environment packet/history | `synthetic_fertilizer_saved_kg` | daily/monthly/run | kg N | sum | `EXISTING` | Environment output. |
| NUE | environment packet/history | `NUE` | daily | fraction | mean/ratio of totals | `EXISTING` | Canonical dashboard name should be selected in serializer. |
| Circularity | environment packet/history | `circularity_score`, `ICirc`, `OCirc` | daily/monthly/run | fraction | mean | `EXISTING` | Use actual environment values. |
| Sustainability | environment packet/history | `sustainability_score_0_100` | daily/monthly/run | score 0-100 | mean | `EXISTING` | No second sustainability model. |
| Carbon credit value | environment packet/history | `carbon_credit_value` | daily/run | currency | sum | `BACKEND_EXPOSE` | Present in environment history but not current daily flattening. |
| Environmental stream ledger | `ctx.state["environment_history"]` and `ctx.state["environment_ledger"]` | `environmental_streams`; packet source, stream id, quality, confidence | daily/run | kg CO2e | preserve rows | `BACKEND_EXPOSE` | Use recorded streams. Never reverse-engineer source emissions from totals. |
| Ledger source metadata | environment ledger packets | `source`, `stream_id`, `period`, `quality`, `confidence` | daily | text | none | `BACKEND_EXPOSE` | Packet metadata is authoritative. |

## 7. Economics

| UI Metric | Python Source | Field / Packet | Period | Unit | Aggregation | Status | Notes |
|---|---|---|---|---|---|---|---|
| Raw milk revenue | `ctx.daily_records` | `milk_revenue` | daily/run | currency | sum | `EXISTING` | Cow-side raw milk revenue. |
| Processor revenue | `ctx.daily_records` | `processor_revenue` | daily/run | currency | sum | `EXISTING` | Includes the processor output defined by the processor agent. |
| Energy revenue/value | `ctx.daily_records` | `energy_value` | daily/run | currency | sum | `EXISTING` | Manager accounting output. |
| Total revenue | `ctx.daily_records` | `total_revenue` | daily/monthly/run | currency | sum | `EXISTING` | Direct manager output. |
| Feed cost | `ctx.daily_records` | `feed_cost` | daily/run | currency | sum | `EXISTING` | Direct manager output. |
| Water cost | `ctx.daily_records` | `water_cost` | daily/run | currency | sum | `EXISTING` | Direct manager output. |
| Disease economic cost | `ctx.daily_records` | `disease_economic_cost` | daily/run | currency | sum | `EXISTING` | Use this available category. |
| Cooling cost | `ctx.daily_records` | `cooling_cost` | daily/run | currency | sum | `EXISTING` | Direct manager output. |
| Processing energy cost | `ctx.daily_records` | `processing_energy_cost` | daily/run | currency | sum | `EXISTING` | Direct manager output. |
| Byproduct revenue history | processor/manager packet | `byproduct_revenue` | daily/run | currency | sum | `MODEL_CHANGE` | Computed by the model but not retained in historical flattened records. |
| Labor and fixed cost history | manager packet/calibration | `labor_cost`, `fixed_cost` | daily/run | currency | sum | `MODEL_CHANGE` | Only the latest manager packet has these categories. Do not reconstruct them in the dashboard. |
| Treatment-cost history | `ctx.state["disease_history"]` | `treatment_cost` | daily/run | currency | sum | `BACKEND_EXPOSE` | Disease history retains this category; keep it distinct from total disease economic cost. |
| Total cost | `ctx.daily_records` | `total_cost` | daily/monthly/run | currency | sum | `EXISTING` | Direct manager output. |
| Profit | `ctx.daily_records` | `profit` | daily/monthly/run | currency | sum | `EXISTING` | Direct manager output. |
| Cumulative profit | `ctx.daily_records` | `profit` | run | currency | cumulative sum | `BACKEND_AGGREGATE` | Python display aggregate. |
| Cash balance | `ctx.daily_records` | `cash_balance` | daily/run | currency | latest/series | `EXISTING` | Direct manager output. |
| Profit per litre | total profit and total milk | `profit`, `milk_l` | run | currency/L | ratio | `UNSUPPORTED` | Do not add until this unit and interpretation are explicitly defined in the report contract. |
| Manager recommendation | `ctx.daily_records` / manager packet | `manager_recommendation`, `recommendation` | daily/latest | text | latest/history | `EXISTING` | Preserve the actual policy recommendation. |
| Policy conflicts | manager packet/history | `policy_conflicts`, conflict count | daily/latest | structured text/count | preserve | `BACKEND_EXPOSE` | Conflicts are not the same as warnings or disease cases. |
| Farm NPV | `dairy_abm.analysis.npv` plus official outputs | `npv()` / annual profit cash flows | run | currency | discounted cash flow | `BACKEND_AGGREGATE` | Integrate the existing analysis module in Python. |
| NPV discount rate | `dairy_abm.analysis.npv` | `DEFAULT_DISCOUNT_RATE` or explicit backend input | run | fraction | none | `BACKEND_EXPOSE` | Surface the assumption; do not hide it in frontend code. |
| Unavailable revenue/cost categories | current model output | no retained historical field | run | currency | — | `UNSUPPORTED` | Show `N/A` until the category is added to an authoritative report. |

## 8. Equipment ROI

The current manager output represents four equipment assets. The dashboard may show these assets only when their backend data is available. Zero CapEx produces `None` ROI/payback and must not be displayed as zero.

| UI Metric | Python Source | Field / Packet | Period | Unit | Aggregation | Status | Notes |
|---|---|---|---|---|---|---|---|
| Milking parlour / bulk tank CapEx | `manager_packet` | `equipment_roi.milking_parlour_bulk_tank.capex` | latest/run | currency | none | `BACKEND_EXPOSE` | Current model asset name. |
| Milking parlour / bulk tank benefit, ROI, payback | `manager_packet` | corresponding `annual_benefit`, `roi`, `payback_years` | latest/run | currency/fraction/years | none | `BACKEND_EXPOSE` | Backend-produced values. |
| Dairy processor CapEx, benefit, ROI, payback | `manager_packet` | `equipment_roi.dairy_processor.*` | latest/run | mixed | none | `BACKEND_EXPOSE` | Show only when processor capability/configuration supports it. |
| Whey processor CapEx, benefit, ROI, payback | `manager_packet` | `equipment_roi.whey_processor.*` | latest/run | mixed | none | `BACKEND_EXPOSE` | Show only when whey processing is represented. |
| Manure system CapEx, benefit, ROI, payback | `manager_packet` | `equipment_roi.manure_system.*` | latest/run | mixed | none | `BACKEND_EXPOSE` | Uses energy/carbon benefits defined by the manager agent. |
| Equipment NPV | `dairy_abm.analysis.npv` | equipment cash flows / `equipment_npvs` | run | currency | discounted cash flow | `BACKEND_AGGREGATE` | Reuse `npv.py`; no JavaScript ROI engine. |
| Anaerobic digester card | current equipment map | no separate asset key | run | — | — | `UNSUPPORTED` | Do not silently substitute `manure_system` without a documented mapping. |
| CHP card | current equipment map | no separate asset key | run | — | — | `UNSUPPORTED` | Energy conversion is modeled, but separate CHP ROI is not. |
| Separator card | current equipment map | no separate asset key | run | — | — | `UNSUPPORTED` | No authoritative ROI output. |
| Water recycling card | current equipment map | no separate asset key | run | — | — | `UNSUPPORTED` | Water recycling metrics exist, but separate CapEx/ROI does not. |
| Solar card | current equipment map | no separate asset key | run | — | — | `UNSUPPORTED` | Solar generation exists when configured; solar ROI does not. |
| Sensors card | current equipment map | no separate asset key | run | — | — | `UNSUPPORTED` | Sensor maintenance exists; sensor ROI does not. |

## 9. Parameters and configuration

| UI Metric | Python Source | Field / Packet | Period | Unit | Aggregation | Status | Notes |
|---|---|---|---|---|---|---|---|
| Calibration key | `calibration_inventory(ctx.calibration)` | `key` | run | dotted key | none | `EXISTING` | Use inventory output; do not hand-code fields. |
| Calibration group/agent | calibration inventory | `agent` | run | text | none | `EXISTING` | Used for grouping/filtering. |
| Calibration default | calibration inventory | `default` | run | parameter unit | none | `EXISTING` | Scientific default. |
| Unit | calibration inventory | `unit` | run | text | none | `EXISTING` | Backend value is authoritative. |
| Source | calibration inventory | `source` | run | text | none | `EXISTING` | Display as provenance metadata. |
| Assumption flag | calibration inventory | `assumption` | run | boolean | none | `EXISTING` | Do not infer this flag from value type. |
| Description | calibration inventory | `description` | run | text | none | `EXISTING` | Display/help text. |
| Valid range | calibration inventory | `valid_range` | run | text | none | `EXISTING` | Backend validation remains authoritative. |
| Runtime feature flags | scenario/calibration | verified top-level flags | run | boolean | none | `BACKEND_EXPOSE` | Target `/api/config` must expose only supported flags. |
| Scenario list/defaults | scenario directory/default scenario | scenario JSON | run | JSON | none | `EXISTING` | Current `/api/scenario` is a compatibility route; target `/api/config` should be UI-safe. |
| Per-run parameter value | isolated calibration copy | dotted override key/value | run | calibration unit | none | `BACKEND_EXPOSE` | Phase 4 backend requirement; never mutate global `CALIBRATION`. |

## 10. Exports and comparisons

| UI Metric | Python Source | Field / Packet | Period | Unit | Aggregation | Status | Notes |
|---|---|---|---|---|---|---|---|
| Dashboard JSON | `dairy_abm.dashboard` target adapter | normalized dashboard contract | run | JSON | serialization only | `BACKEND_EXPOSE` | Phase 2 target; values must come from the cached context. |
| Summary JSON | `write_reports()` | `summary.json` | run | JSON | official export | `EXISTING` | Keep official report generation in `reports.py`. |
| Daily CSV | `write_reports()` | `ctx.daily_records` | daily | CSV | none | `EXISTING` | Official report. |
| Schedule CSV | `write_reports()` | `ctx.schedule_records` | schedule | CSV | none | `EXISTING` | Official report. |
| Monthly CSV | `write_reports()` | `ctx.monthly_records` | monthly | CSV | none | `EXISTING` | Preserve environment/manager report rows. |
| Annual CSV | `write_reports()` | `ctx.annual_records` | annual | CSV | none | `EXISTING` | Preserve genetics/review rows. |
| Calibration inventory export | `write_reports()` | `calibration_inventory.json` | run | JSON | none | `EXISTING` | Same calibration copy used for the run. |
| Full ZIP | web export layer | official report files | run | ZIP | packaging only | `EXISTING` | Dashboard JSON and ZIP must reference the same cached context. |
| Comparison metrics | comparison backend | selected serialized metrics | multiple runs | metric-specific | absolute/percentage deltas | `BACKEND_AGGREGATE` | Directional coloring is presentation logic; metric values come from Python. |
| Comparison warnings | comparison backend | run metadata and warnings | multiple runs | structured text | compare settings | `BACKEND_EXPOSE` | Warn when seeds, durations, herd sizes, or features differ. |
| Chart SVG/PNG | frontend chart layer | serialized chart values | presentation | image | coordinate conversion | `EXISTING` | Presentation export only; never an official scientific report replacement. |

# Phase 1 decisions and backlog

## Ready for serializer use

These can be implemented without changing scientific agents: daily report fields, monthly environment/manager rows, annual genetics/review rows, schedule rows, event records, calibration inventory, latest packet metadata, environment history, water/feed/manure histories, current per-cow state, and existing NPV/equipment output.

## Must be exposed by the backend adapter

1. Packet/state-backed loop details that are not flattened into `daily_records`.
2. Environment stream ledger rows with source, stream id, unit, quality, and confidence.
3. Current per-cow lifecycle/genetic fields that are not in `cow_records`.
4. Manager policy, conflicts, recommendations, and equipment ROI.
5. Configuration, report-contract, and calibration inventory metadata.
6. Backend-produced monthly/yearly series wherever the official model does not already provide a period record.

## Genuine model/report gaps

1. Historical manager revenue/cost categories for byproduct revenue, labor, and fixed cost are not retained. Do not reconstruct them in the serializer.
2. Historical per-cow rows are not date-labelled. The current cow packet supports a latest-day explorer; historical cow charts need an explicit model/report output.
3. The legacy dashboard's separate ROI cards for digester, CHP, separator, water recycling, solar, and sensors are not represented by current equipment ROI output.
4. Profit-per-litre is not yet an explicitly defined report metric and should remain unavailable until its contract semantics are approved.

## Unsupported-value policy

The frontend must distinguish zero, missing, disabled, unsupported, and no-data-for-period states. Unsupported metrics are not placeholders for guessed values. The safe display values are:

- `N/A` — no authoritative metric exists;
- `Not available in current model` — a requested concept is outside the current model;
- `Disabled` — the corresponding feature flag or packet is inactive;
- `No data for selected period` — the model produced no record for that period.

No dashboard page should be implemented until its requested fields are either `EXISTING`, `BACKEND_AGGREGATE`, or `BACKEND_EXPOSE`, with the `MODEL_CHANGE` and `UNSUPPORTED` rows explicitly handled.
