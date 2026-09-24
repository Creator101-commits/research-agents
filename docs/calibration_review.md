# Calibration Review Checklist

This file records the values that must be reviewed or replaced before the model is used for scientific or financial decisions.

The AIRAND herd lifecycle and `cdairy_economics` groups were calibrated against the supplied workbook's year-15 summary. `docs/parity/parity_report.md` gives the eight-seed comparison: 25 of 31 measures are within 2%, 4 within 5%, and 2 (age of dam, breeding cost) differ by more than 5%. The workbook's external Java simulator is unavailable, so agreement of aggregated outputs does not verify identical event rules. The old one-point milk calibration file was deleted; the canonical parameters are in `configs/calibration.json`.

The authoritative machine-readable list is generated on every run as `calibration_inventory.json`. Each row includes `key`, `default`, `unit`, `valid_range`, `source`, and `assumption`.

Generate the full checklist:

```sh
python3 -m dairy_abm list-calibrations --output out/calibration_inventory.json
```

## Audit fixes, 2026-09-23: coefficient and rule decisions

Precedence is workbook, then Blueprint (`docs/parity/blueprint_extracted.txt`); dashboard values are used only where the owner chose them to fill a gap. Every value below is in `configs/calibration.json` with its source.

| Item | Decision | Source |
|---|---|---|
| Feed cost | The ledger charges all intake: lactating DMI x `cdairy_economics.dmi_wet_price_per_kg` (0.30) plus dry DMI x `cdairy_economics.dmi_dry_price_per_kg` (0.20). Home-grown feed carries the same price. Loop feed offsets (L4 only, see below) reduce the charged kilograms, split pro rata between lactating and dry intake. Ledger and parity path share `dairy_abm.analysis.cdairy_economics.feed_cost_rows`. | Workbook Stats_MAST!BV19, BV20; rows 28-29 |
| Farm profit | Workbook herd economics (every Table 4 line) plus an itemized loop layer: electricity value, heat value, carbon credits, compost revenue, by-product revenue, loop feed saving, minus water, cooling and disease cost. | Workbook Tables Table 4; Blueprint for loop items |
| Processor (2026-09-24 decision) | The processor is treated as a separate business. Its product sales (`processor_revenue_not_in_profit`) and its processing energy (`processor_energy_cost_not_in_profit`, processing_energy_kwh x electricity price) are both reported, in the daily export and the model-details card, and neither is in farm profit. Farm revenue keeps the workbook milk component sales. Milk cooling stays in farm costs because it is a farm-side cost. No product-side costs are added because neither the workbook nor the Blueprint gives them. The processor still runs with L4 so whey and waste milk exist. | Workbook precedence; owner decision |
| Manure routing | `manure.digester_route_fraction` 0.65, `compost_route_fraction` 0.35, `storage_route_fraction` 0.0. With L3 off the digester share goes to storage and the digester does not run (no biogas, digestate or processor residue feedstock); with L1 off the compost share goes to storage. The dashboard adapter turns off the Farm Manager's emissions-triggered reroute (an implementation rule not in the Blueprint), which otherwise sends all manure to the digester. | Target dashboard separator_solid_fraction 0.35 (owner decision); Blueprint Manure 4.2 (routing is policy-driven), Energy 2.6 (biogas_investment_active) |
| Heat value | Not monetized. Heat is generated and reported, but no farm heat demand is configured, so `heat_value` is 0 and the UI says so. `energy.heat_value_per_kwh` (0.04, implementation) applies only if a scenario sets `farm_heat_demand_mj_per_day`. | Blueprint Energy 8.5, 2.7, 8.7 (no heat demand, recovery fraction or price); owner decision |
| Farm electricity demand | `energy.farm_energy_demand_kwh_per_day` = 100 kWh/day stays an unsourced implementation assumption and is labelled as such. Only displaced demand is valued; surplus (about 226 kWh/day for the default farm) is reported as `surplus_energy_kwh`. | Blueprint Energy 8.2, 9, 10 (demand needs external calibration; monetize displaced share only); owner decision |
| Solar | No capacity configured (0). The ROI card and the Total Electricity KPI say so. | Neither the Blueprint nor the workbook gives a solar assumption |
| Carbon-credit price | 0 unless a scenario sets `carbon_credit_price_per_tonne_co2e`; the ROI page uses the model price, so carbon credits are 0 by default. | Blueprint Energy 8.4 (price not specified) |
| Body weight | Baseline by parity: `cow.bodyweight_first_parity_kg` 540 kg rising linearly to `cow.bodyweight_mature_kg` 680 kg at `herd.mature_parity`. Within a lactation, weight moves by 0.8 x the daily intake residual e (actual intake without RFI divided by expected intake, minus 1), capped at 1 kg/day, and resets to the baseline at calving. Heat-stress and supply limits no longer drive weight loss because they already cut milk and intake together. BCS uses the same residual. | Target dashboard Animal Biology defaults (owner decision); no Blueprint or workbook BW equation; plausibility band from Blueprint Cow 8.1 (NASEM Eq 2-1 support, 624 +/- 80.2 kg) |
| Per-cow water | Kept as the herd-average allocation (`water.drinking_l_per_cow_day`) and labelled in the Cow Ranking table. | Blueprint Water 2.6 (no per-cow drinking equation) |

| L4 feed credit (2026-09-24) | The credit is the dry matter returned: whey sent to feed x 1.03 kg/L x `dairy_processor.dry_whey_yield_kg_per_kg_whey` (0.065), plus waste milk sent to feed x 1.03 kg/L x (`herd.milk_fat_fraction` 0.0375 + `dairy_processor.milk_snf_fraction` 0.087), valued at the workbook dry-matter feed prices. It replaces `dairy_processor.byproduct_loop_feed_substitution_kg_per_kg` (0.8 kg feed per litre of liquid whey, implementation), which was removed. Default-farm L4 feed saving: $529 to $55 per cow per year. | Owner decision. Note: the calibration file lists the dry whey yield and SNF fraction as "implementation"; the USDA ERS coefficients in the processor (TB-1961) are component draws per lb of product, not the liquid-whey solids yield. |
| L1 feed credit (2026-09-24) | Removed, with `feed_crop.nutrient_loop_feed_substitution_fraction` (0.1, implementation). The Blueprint's nutrient loop returns compost and digestate N/P/K to cropland and lowers the synthetic fertilizer requirement; it defines no feed offset. L1's money value is compost revenue. Avoided synthetic fertilizer is reported as kg N (`synthetic_fertilizer_saved_kg`) and kg CO2e (Blueprint ENV-11, `environment.fertilizer_n_kg_co2e_per_kg_n`) but not monetized, because neither the workbook nor the Blueprint gives a fertilizer price. | Blueprint Feed/Crop (synthetic_fertiliser_requirement) and Manure (compost_to_feed_crop) sections; owner decision |
| Ration coverage (2026-09-24) | Each cow now receives the herd's coverage fraction of its own need (previously its target times cow count over the target sum, which under-fed below-average cows). | Bug fix |
| `herd.milk_yield_scale` (2026-09-24) | Recalibrated 1.368 to 1.3016 after the coverage fix raised 8-seed milk to +5.1%. | Stats_MAST!BQ12 (AIRAND year-15 milk) |
| `cow.dmi_level_calibration_factor` (2026-09-24) | Recalibrated 1.19 to 1.1169 after the coverage fix raised lactating intake to 27.92 kg per milking cow-day (feeding cost +8.1%, profit -8.6% after the milk refit). | Stats_MAST AT73 / AT21 (26.21 kg per milking cow-day); owner approval |
| Disease loop line (2026-09-24) | Excludes the lost-milk value, which lower milk sales already reflect. The default farm's lost-milk value is 0 (`disease_milk_loss_value_per_cow_day` is scenario-only), so the default line ($4.42 per cow per year of lameness treatment) is unchanged. | Double-count fix |

Findings that need review but were not changed:

- The Farm Manager's automatic feed response compares purchased-feed cash (`feed_crop_packet.feed_cost`, normally 0 because home-grown feed covers intake) with a fixed $500/day trigger; it was left on purchased cash so its behaviour did not change.
- The processor's `dairy_return_feed_packet` still offers `feed_eligible_kg_dm` = 0.08 kg DM per litre (scenario default) as a separate supply to Feed/Crop. It is used only when own-farm feed runs short, which does not happen in the default farm, but it is a second valuation of the same whey.

## Values Requiring Later Calibration

These groups are currently marked `assumption: true` in `configs/calibration.json`.

For the current status of any specific key, use the generated inventory; the examples below are a review checklist and can change as Blueprint and workbook values are added.

- Cow physiology: `cow.base_dmi_kg_per_cow_day`, `cow.base_manure_kg_per_cow_day`, `cow.enteric_ch4_kg_per_cow_day`, `cow.heat_stress_milk_loss_fraction`.
- Feed and crop: `feed_crop.ration_cost_per_kg_dm`, `feed_crop.crop_yield_kg_dm_per_ha_day`, `feed_crop.fertilizer_n_kg_per_ha_month`, `feed_crop.nutrient_return_efficiency`, `feed_crop.irrigation_l_per_ha_day`.
- Manure routing and emissions: `manure.digester_route_fraction`, `manure.compost_route_fraction`, `manure.storage_route_fraction` (target-dashboard values, owner decision), `manure.biochemical_methane_potential_m3_per_kg_vs`, `manure.volatile_solids_fraction`, `manure.storage_ch4_kg_per_kg_manure`, `manure.compost_n2o_kg_per_kg_manure`.
- Energy economics and offsets: `energy.electricity_price_per_kwh`, `energy.heat_value_per_kwh`, `energy.parasitic_load_fraction`, `energy.grid_offset_kg_co2e_per_kwh`, `energy.farm_energy_demand_kwh_per_day`.
- Body weight: `cow.bodyweight_first_parity_kg`, `cow.bodyweight_mature_kg`, `cow.initial_body_weight_kg`.
- Disease and treatment: `disease.lameness_daily_probability`, `disease.milk_loss_sick_fraction`, `disease.treatment_cost_per_case`, `disease.recovery_daily_probability`.
- Environment reporting: `environment.ch4_gwp100`, `environment.n2o_gwp100`, `environment.fertilizer_n_kg_co2e_per_kg_n`, `environment.circularity_weight_energy`, `environment.circularity_weight_nutrients`, `environment.circularity_weight_water`, `environment.circularity_weight_products`.
- Farm management economics: `farm_manager.discount_rate_annual`, `farm_manager.carbon_credit_price_per_tonne_co2e`. Herd fixed and variable costs come from the workbook (`cdairy_economics`).
- Sensors: `sensors.milk_sensor_noise_fraction`, `sensors.dmi_sensor_noise_fraction`, `sensors.alert_sensitivity`, `sensors.missing_reading_probability`.
- Water: `water.drinking_l_per_cow_day`, `water.parlor_l_per_cow_day`, `water.treatment_recovery_fraction`, `water.water_cost_per_l`.
- Dairy processing assumptions: `dairy_processor.processing_energy_kwh_per_l_milk`, `dairy_processor.whey_l_per_l_processed_milk`, `dairy_processor.whey_liquid_price_per_l`.
- Market and conversion assumptions: `market.milk_price_per_l`, `market.feed_cost_per_kg_dm`, `market.cull_cow_price`, `market.price_shock_stddev_fraction`, `market.class_cwt_to_l_conversion`. Observed wholesale and class-price series are retained with their source units and are not converted to per-litre product prices without an explicit conversion convention.
- Genetics implementation choices: `genetics.selection_intensity`, `genetics.trait_weights.milk_yield`, `genetics.trait_weights.feed_efficiency`, `genetics.trait_weights.fertility`, `genetics.trait_weights.health`, `genetics.trait_weights.survivability`.
- Land scenario defaults: `land.cropland_ha`, `land.pasture_ha`.
- Runtime conventions: `runtime.daily_tick_hours`, `runtime.monthly_report_day`, `runtime.annual_genetics_day`.
- Herd lifecycle: reproduction timing, parity transitions, replacement/culling, clinical mastitis episodes, treatment dosing, and the conversion of events to annual per-cow measures.
- Workbook economics: price and cost inputs in `cdairy_economics`; these reproduce formulas for workbook inputs but still depend on the model's simulated herd counts.

Processor residual route fractions must remain in `0.0..1.0`; model construction revalidates in-memory calibration overrides before agents are initialized.

## Blueprint-Anchored Defaults

These values are still configurable, but are not marked as assumptions because the blueprint explicitly supplied or constrained them:

- `genetics.heritability_h2_rfi_fat`
- `genetics.cross_diet_repeatability_modifier`
- `genetics.minimum_intake_record_days`
- `genetics.annual_rfi_gain_fraction`
- `energy.kwh_per_ton_feedstock`
- `water.water_saving_l_per_cow_day`
- `dairy_processor.enabled`
- `dairy_processor.whey_processing_enabled`
- `dairy_processor.product_mix_cheese`
- `dairy_processor.product_mix_butter`
- `dairy_processor.product_mix_yogurt`
- `dairy_processor.product_mix_fresh`
- `dairy_processor.product_mix_functional`
- `land.enabled`
- `land.silvopastoral_tree_cover_fraction`
- `land.soil_carbon_sequestration_index`

## Intentional Runtime Boundaries

- The daily scheduler retains `Cow -> Feed/Crop`. Nutrient, water, and dairy-byproduct loops use one-day credits rather than synchronous feedback.
- Land soil-carbon and grazing packets are scenario context only. They do not change GHG totals or cow intake without a supported equation and calibration.
- Optional water nutrient recovery reaches Feed/Crop as a one-day-lag soil-N credit. Processor sludge and waste-milk packets are not routed into same-day mass balances.
- Environmental net carbon can be negative. The fertilizer substitution factor is an implementation assumption and must be reviewed before scientific or financial use.
