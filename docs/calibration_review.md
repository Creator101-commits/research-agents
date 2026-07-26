# Calibration Review Checklist

This file records the values that must be reviewed or replaced before the model is used for scientific or financial decisions.

The authoritative machine-readable list is generated on every run as `calibration_inventory.json`. Each row includes `key`, `default`, `unit`, `valid_range`, `source`, and `assumption`.

Generate the full checklist:

```sh
python3 -m dairy_abm list-calibrations --output out/calibration_inventory.json
```

## Values Requiring Later Calibration

These groups are currently marked `assumption: true` in `configs/calibration.json`.

- Cow physiology: `cow.base_milk_l_per_cow_day`, `cow.base_dmi_kg_per_cow_day`, `cow.base_manure_kg_per_cow_day`, `cow.enteric_ch4_kg_per_cow_day`, `cow.heat_stress_milk_loss_fraction`, `cow.mortality_rate_annual`, `cow.pregnancy_rate_monthly`.
- Feed and crop: `feed_crop.ration_cost_per_kg_dm`, `feed_crop.crop_yield_kg_dm_per_ha_day`, `feed_crop.fertilizer_n_kg_per_ha_month`, `feed_crop.nutrient_return_efficiency`, `feed_crop.irrigation_l_per_ha_day`.
- Manure routing and emissions: `manure.digester_route_fraction`, `manure.compost_route_fraction`, `manure.storage_route_fraction`, `manure.biochemical_methane_potential_m3_per_kg_vs`, `manure.volatile_solids_fraction`, `manure.storage_ch4_kg_per_kg_manure`, `manure.compost_n2o_kg_per_kg_manure`.
- Energy economics and offsets: `energy.electricity_price_per_kwh`, `energy.heat_value_per_kwh`, `energy.parasitic_load_fraction`, `energy.grid_offset_kg_co2e_per_kwh`.
- Disease and treatment: `disease.mastitis_daily_probability`, `disease.lameness_daily_probability`, `disease.milk_loss_sick_fraction`, `disease.treatment_cost_per_case`, `disease.recovery_daily_probability`.
- Environment reporting: `environment.ch4_gwp100`, `environment.n2o_gwp100`, `environment.fertilizer_n_kg_co2e_per_kg_n`, `environment.circularity_weight_energy`, `environment.circularity_weight_nutrients`, `environment.circularity_weight_water`, `environment.circularity_weight_products`.
- Farm management economics: `farm_manager.labor_cost_per_cow_day`, `farm_manager.fixed_cost_per_day`, `farm_manager.discount_rate_annual`, `farm_manager.carbon_credit_price_per_tonne_co2e`.
- Sensors: `sensors.milk_sensor_noise_fraction`, `sensors.dmi_sensor_noise_fraction`, `sensors.alert_sensitivity`, `sensors.missing_reading_probability`.
- Water: `water.drinking_l_per_cow_day`, `water.parlor_l_per_cow_day`, `water.treatment_recovery_fraction`, `water.water_cost_per_l`.
- Dairy processing assumptions: `dairy_processor.processing_energy_kwh_per_l_milk`, `dairy_processor.whey_l_per_l_processed_milk`, `dairy_processor.whey_liquid_price_per_l`.
- Market and conversion assumptions: `market.milk_price_per_l`, `market.feed_cost_per_kg_dm`, `market.cull_cow_price`, `market.price_shock_stddev_fraction`, `market.class_cwt_to_l_conversion`. Observed wholesale and class-price series are retained with their source units and are not converted to per-litre product prices without an explicit conversion convention.
- Genetics implementation choices: `genetics.selection_intensity`, `genetics.trait_weights.milk_yield`, `genetics.trait_weights.feed_efficiency`, `genetics.trait_weights.fertility`, `genetics.trait_weights.health`, `genetics.trait_weights.survivability`.
- Land scenario defaults: `land.cropland_ha`, `land.pasture_ha`.
- Runtime conventions: `runtime.daily_tick_hours`, `runtime.monthly_report_day`, `runtime.annual_genetics_day`.

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
