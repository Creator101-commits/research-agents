const DEFAULTS = {
  number_of_cows: 100,
  simulation_years: 5,
  days_per_year: 365,
  enable_random_daily_variation: true,
  random_seed: 42,
  daily_variation_std_fraction: 0.08,
  daily_variation_min_multiplier: 0.70,
  daily_variation_max_multiplier: 1.30,
  milk_manure_correlation: 0.65,
  enable_seasonal_profile: true,
  seasonal_amplitude_fraction: 0.12,
  seasonal_peak_day_of_year: 120,
  enable_dynamic_loop_feedback: true,
  nutrient_pool_daily_use_fraction: 0.03,
  nutrient_pool_max_kg: 250000,
  // ── Herd-average baselines (used as reference/fallback) ──
  feed_intake_kg_per_cow_per_day: 22.0,
  water_use_L_per_cow_per_day: 120.0,
  milk_yield_L_per_cow_per_day: 28.0,
  manure_output_kg_per_cow_per_day: 55.0,
  fraction_forage_silage_of_feed: 0.70,
  fraction_alternative_byproduct_feed: 0.15,
  smart_tech_feed_efficiency_factor: 1.0,
  smart_tech_water_efficiency_factor: 1.0,
  smart_tech_milk_yield_factor: 1.0,
  health_feed_efficiency_factor: 1.0,
  health_milk_yield_factor: 1.0,
  methane_reduction_factor: 1.0,
  manure_to_treatment_fraction: 1.0,
  separator_solid_fraction: 0.35,
  separator_liquid_fraction: 0.65,
  biogas_m3_per_kg_manure_to_digester: 0.025,
  electricity_kWh_per_m3_biogas: 2.0,
  heat_kWh_per_m3_biogas: 2.5,
  digestate_kg_per_kg_manure_to_digester: 0.90,
  compost_kg_per_kg_manure_to_compost: 0.40,
  nitrogen_kg_per_kg_manure_to_compost: 0.005,
  phosphorus_kg_per_kg_manure_to_compost: 0.002,
  potassium_kg_per_kg_manure_to_compost: 0.006,
  fraction_milk_to_processor: 1.0,
  fraction_dairy_products_of_milk: 0.85,
  fraction_whey_of_milk: 0.10,
  fraction_whey_to_animal_feed_loop: 0.50,
  fraction_whey_to_functional_foods_bioproducts: 0.50,
  whey_volume_L_per_L_cheese_milk: 0.85,
  whey_volume_L_per_L_yogurt_milk: 0.75,
  fraction_sludge_of_milk: 0.02,
  fraction_waste_milk_of_milk: 0.03,
  fraction_waste_milk_to_animal_feed_loop: 0.70,
  fraction_waste_milk_to_biogas: 0.30,
  fraction_sludge_to_biogas: 0.50,
  fraction_sludge_to_fertilizer: 0.50,
  fraction_water_to_wastewater: 0.80,
  fraction_wastewater_recycled_to_irrigation: 0.70,
  wastewater_n_recovery_kg_per_L: 0.0001,
  wastewater_p_recovery_kg_per_L: 0.00005,
  wastewater_k_recovery_kg_per_L: 0.00008,
  nutrient_loop_feed_substitution_fraction: 0.10,
  water_loop_fresh_water_offset_fraction: 0.70,
  energy_loop_external_energy_offset_fraction: 0.20,
  byproduct_loop_feed_substitution_kg_per_kg: 0.80,
  land_cropland_ha: 80.0,
  land_pasture_ha: 40.0,
  land_silvopastoral_tree_cover_fraction: 0.05,
  soil_carbon_sequestration_index: 1.0,
  solar_electricity_kWh_per_cow_per_day: 0.5,
  enteric_methane_kg_co2e_per_cow_per_day: 5.0,
  manure_n2o_kg_co2e_per_kg_manure: 0.008,
  grid_avoided_kg_co2e_per_kWh: 0.40,
  biogas_methane_displacement_kg_co2e_per_m3: 1.5,
  milk_price_currency_per_L: 0.45,
  // ── Milk Market Allocation (contracts to different buyers/uses) ──
  fraction_milk_to_cheese:      0.40,
  fraction_milk_to_butter:      0.20,
  fraction_milk_to_yogurt:      0.15,
  fraction_milk_to_fresh:       0.15,
  fraction_milk_to_functional:  0.10,
  price_per_L_milk_cheese:      0.90,
  price_per_L_milk_butter:      0.60,
  price_per_L_milk_yogurt:      0.75,
  price_per_L_milk_fresh:       0.45,
  price_per_L_milk_functional:  1.20,
  electricity_price_currency_per_kWh: 0.16,
  heat_value_currency_per_kWh: 0.06,
  compost_value_currency_per_kg: 0.05,
  feed_cost_per_kg: 0.22,
  water_cost_per_L: 0.0008,
  milk_density_kg_per_L: 1.03,
  // ── Individual Cow Biology (cow_herd_model.py) ──
  wood_b: 0.20,
  wood_c: 0.0055,
  peak_milk_L_first_parity: 38.0,
  peak_milk_L_mature: 50.0,
  mature_parity: 3,
  lactation_length_days: 305,
  dry_period_days: 60,
  gestation_days: 283,
  cow_peak_std_fraction: 0.12,
  peak_floor_fraction: 0.4,
  daily_illness_probability: 0.004,
  illness_duration_days_mean: 4.0,
  illness_milk_penalty_fraction: 0.35,
  illness_feed_penalty_fraction: 0.15,
  max_parity: 6,
  annual_involuntary_cull_fraction: 0.12,
  bodyweight_first_parity_kg: 540.0,
  bodyweight_mature_kg: 680.0,
  maintenance_dmi_fraction_of_bw: 0.020,
  dmi_kg_per_L_milk: 0.30,
  water_base_L: 15.0,
  water_L_per_kg_dmi: 3.5,
  water_L_per_L_milk: 1.0,
  water_seasonal_amplitude: 0.15,
  water_peak_day_of_year: 200,
  manure_kg_per_kg_dmi: 2.0,
};

let cfg = {...DEFAULTS};

let activeFarmType = 'conventional';
const FARM_PRESETS = {conventional:{key:'conventional',label:'Conventional',color:'#01696f',overrides:{}}};
let lastResult = null;
let supportedParams = new Set();
let backendDefaults = {};
function defaultActiveLoops() {
  return { l1: true, l2: true, l3: true, l4: true };
}

/** Which loops are ON for a comparison scenario key (baseline / l1 / l1l3 / all4 …). */
function getActiveLoops(scenarioKey) {
  if (!scenarioKey || scenarioKey === 'all4') return defaultActiveLoops();
  if (scenarioKey === 'baseline') return { l1: false, l2: false, l3: false, l4: false };
  return {
    l1: scenarioKey.includes('l1'),
    l2: scenarioKey.includes('l2'),
    l3: scenarioKey.includes('l3'),
    l4: scenarioKey.includes('l4'),
  };
}

const PARAM_GROUPS = [
  {
    title: "Herd & Simulation Setup", icon: "",
    params: [
      {key:"number_of_cows", label:"Number of Cows", type:"number", min:1, max:5000, step:10, hint:"Total herd size"},
      {key:"simulation_years", label:"Simulation Years", type:"number", min:1, max:30, step:1, hint:"Length of simulation"},
      {key:"random_seed", label:"Random Seed", type:"number", min:0, max:99999, step:1, hint:"For reproducibility"},
      {key:"enable_random_daily_variation", label:"Random Daily Variation", type:"toggle", hint:"Add day-to-day noise"},
      {key:"enable_seasonal_profile", label:"Seasonal Profile", type:"toggle", hint:"Peak production in spring"},
      {key:"enable_dynamic_loop_feedback", label:"Dynamic Loop Feedback", type:"toggle", hint:"Circular economy credits"},
    ]
  },
  {
    title: "Per-Cow Daily Rates", icon: "",
    params: [
      {key:"milk_yield_L_per_cow_per_day", label:"Milk Yield (L/cow/day) ▸ Reference", hint:"Herd reference value only. Actual yield comes from the Woods curve model (Animal Biology → peak_milk_L params). This slider does not drive simulation output directly.", type:"slider", min:10, max:80, step:1},
      {key:"feed_intake_kg_per_cow_per_day", label:"Feed Intake (kg/cow/day) ▸ Reference", type:"slider", min:10, max:50, step:0.5},
      {key:"water_use_L_per_cow_per_day", label:"Water Use (L/cow/day) ▸ Reference", type:"slider", min:50, max:250, step:5},
      {key:"manure_output_kg_per_cow_per_day", label:"Manure Output (kg/cow/day) ▸ Reference", type:"slider", min:20, max:100, step:1},
    ]
  },
  {
    title: "Smart Technology", icon: "",
    params: [
      {key:"smart_tech_feed_efficiency_factor", label:"Feed Efficiency Factor", type:"slider", min:0.5, max:2.0, step:0.05, hint:">1 = less feed needed"},
      {key:"smart_tech_water_efficiency_factor", label:"Water Efficiency Factor", type:"slider", min:0.5, max:2.0, step:0.05},
      {key:"smart_tech_milk_yield_factor", label:"Milk Yield Factor", type:"slider", min:0.5, max:2.0, step:0.05},
      {key:"health_feed_efficiency_factor", label:"Health Feed Factor", type:"slider", min:0.5, max:2.0, step:0.05},
      {key:"health_milk_yield_factor", label:"Health Milk Factor", type:"slider", min:0.5, max:2.0, step:0.05},
      {key:"methane_reduction_factor", label:"Methane Reduction Factor", type:"slider", min:0.1, max:1.5, step:0.05, hint:"<1 = interventions reduce CH₄"},
    ]
  },
  {
    title: "Manure Management", icon: "",
    params: [
      {key:"manure_to_treatment_fraction", label:"Fraction to Treatment", type:"slider", min:0, max:1, step:0.05},
      {key:"separator_solid_fraction", label:"Solid Fraction (→ Compost)", type:"slider", min:0.1, max:0.9, step:0.05, hint:"Liquid = 1 − solid → Digester"},
      {key:"biogas_m3_per_kg_manure_to_digester", label:"Biogas Yield (m³/kg manure)", type:"slider", min:0.005, max:0.08, step:0.005},
      {key:"compost_kg_per_kg_manure_to_compost", label:"Compost Yield (kg/kg manure)", type:"slider", min:0.1, max:0.8, step:0.05},
    ]
  },
  {
    title: "Energy", icon: "",
    params: [
      {key:"electricity_kWh_per_m3_biogas", label:"Electricity (kWh/m³ biogas)", type:"slider", min:0.5, max:4, step:0.1},
      {key:"heat_kWh_per_m3_biogas", label:"Heat (kWh/m³ biogas)", type:"slider", min:0.5, max:5, step:0.1},
      {key:"solar_electricity_kWh_per_cow_per_day", label:"Solar Electricity (kWh/cow/day)", type:"slider", min:0, max:5, step:0.1},
    ]
  },  {
    title: "Milk Processing", icon: "",
    params: [
      {key:"fraction_milk_to_processor",      label:"Fraction to Processor",      type:"slider", min:0, max:1,   step:0.05, hint:"What fraction of total milk output enters the processing/value-add chain (1.0 = 100%)"},
      {key:"fraction_dairy_products_of_milk", label:"Dairy Products Fraction",    type:"slider", min:0.5, max:1, step:0.05, hint:"Governs whey/sludge/waste allocation fractions. Product-stream revenues are in Milk Market & Pricing below."},
      {key:"fraction_whey_of_milk",           label:"Whey Fraction (Legacy)",     type:"slider", min:0, max:0.3, step:0.01, hint:"Legacy fallback for whey volume. Actual whey volumes are product-mix weighted (see Milk Market & Pricing)."},
      {key:"fraction_whey_to_animal_feed_loop", label:"Whey → Feed Loop",        type:"slider", min:0, max:1,   step:0.05, hint:"Fraction of generated whey redirected as animal feed (Loop 4) — reduces purchased feed cost"},
    ]
  },
  {
    title: "Milk Market & Pricing", icon: "",
    params: [
      {key:"fraction_milk_to_cheese",     label:"→ Cheese Contracts (%)",           type:"slider", min:0, max:1,   step:0.05, hint:"Share of milk sold to cheese manufacturers (~$0.90/L)"},
      {key:"fraction_milk_to_butter",     label:"→ Butter/Cream Contracts (%)",     type:"slider", min:0, max:1,   step:0.05, hint:"Share of milk sold for butter & cream production (~$0.60/L)"},
      {key:"fraction_milk_to_yogurt",     label:"→ Yogurt/Fermented Contracts (%)", type:"slider", min:0, max:1,   step:0.05, hint:"Share sold to yogurt & fermented dairy buyers (~$0.75/L)"},
      {key:"fraction_milk_to_fresh",      label:"→ Fresh/Pasteurised Sales (%)",    type:"slider", min:0, max:1,   step:0.05, hint:"Share sold as fresh farm-gate milk at base price (~$0.45/L)"},
      {key:"fraction_milk_to_functional", label:"→ Functional/Protein Contracts (%)", type:"slider", min:0, max:1, step:0.05, hint:"Share contracted for protein concentrate & functional food manufacturers (~$1.20/L)"},
      {key:"price_per_L_milk_cheese",     label:"Cheese Contract Price ($/L)",      type:"number", min:0.1, max:5,  step:0.05, hint:"Price received per litre of milk under cheese contracts"},
      {key:"price_per_L_milk_butter",     label:"Butter Contract Price ($/L)",      type:"number", min:0.1, max:5,  step:0.05, hint:"Price received per litre of milk under butter/cream contracts"},
      {key:"price_per_L_milk_yogurt",     label:"Yogurt Contract Price ($/L)",      type:"number", min:0.1, max:5,  step:0.05, hint:"Price received per litre of milk under yogurt contracts"},
      {key:"price_per_L_milk_fresh",      label:"Fresh Milk Price ($/L)",           type:"number", min:0.1, max:3,  step:0.05, hint:"Farm-gate price for fresh/pasteurised milk sales"},
      {key:"price_per_L_milk_functional", label:"Functional Contract Price ($/L)",  type:"number", min:0.1, max:10, step:0.10, hint:"Price received per litre for functional/protein concentrate contracts"},
    ]
  },
  {
    title: "Economics", icon: "",
    params: [
      {key:"feed_cost_per_kg", label:"Feed Cost ($/kg)", type:"slider", min:0.05, max:0.80, step:0.01, hint:"Purchased feed cost per kg — loops that reduce netFeed reduce this cost"},
      {key:"water_cost_per_L", label:"Water Cost ($/L)", type:"slider", min:0.0001, max:0.005, step:0.0001, hint:"Fresh water cost per litre — loops that reduce netWater reduce this cost"},
      {key:"milk_price_currency_per_L", label:"Milk Price ($/L)", type:"slider", min:0.1, max:3.0, step:0.01, hint:"Farm-gate price including cooperative uplift. Conventional ~$0.78, Organic ~$0.72, Raw milk ~$2.10"},
      {key:"electricity_price_currency_per_kWh", label:"Electricity Price ($/kWh)", type:"slider", min:0.01, max:0.5, step:0.01},
      {key:"compost_value_currency_per_kg", label:"Compost Value ($/kg)", type:"slider", min:0, max:0.2, step:0.005},
      {key:"heat_value_currency_per_kWh", label:"Heat Value ($/kWh)", type:"slider", min:0, max:0.2, step:0.005},
    ]
  },
  {
    title: "GHG & Climate", icon: "",
    params: [
      {key:"enteric_methane_kg_co2e_per_cow_per_day", label:"Enteric CH₄ (kgCO₂e/cow/day)", type:"slider", min:1, max:15, step:0.5},
      {key:"manure_n2o_kg_co2e_per_kg_manure", label:"Manure N₂O (kgCO₂e/kg manure)", type:"slider", min:0, max:0.05, step:0.001},
      {key:"grid_avoided_kg_co2e_per_kWh", label:"Grid Emission Factor (kgCO₂e/kWh)", type:"slider", min:0.1, max:1.0, step:0.05},
      {key:"biogas_methane_displacement_kg_co2e_per_m3", label:"Biogas Displacement (kgCO₂e/m³)", type:"slider", min:0.5, max:3.0, step:0.1},
    ]
  },
  {
    title: "Land Resources", icon: "",
    params: [
      {key:"land_cropland_ha", label:"Cropland (ha)", type:"slider", min:0, max:500, step:5},
      {key:"land_pasture_ha", label:"Pasture (ha)", type:"slider", min:0, max:500, step:5},
      {key:"soil_carbon_sequestration_index", label:"Soil Carbon Index", type:"slider", min:0.5, max:2.0, step:0.1},
      {key:"land_silvopastoral_tree_cover_fraction", label:"Tree Cover Fraction", type:"slider", min:0, max:0.5, step:0.01},
    ]
  },
  {
    title: "Variability", icon: "",
    params: [
      {key:"daily_variation_std_fraction", label:"Daily Variation Std Dev", type:"slider", min:0, max:0.3, step:0.01},
      {key:"seasonal_amplitude_fraction", label:"Seasonal Amplitude", type:"slider", min:0, max:0.4, step:0.01},
      {key:"milk_manure_correlation", label:"Milk–Manure Correlation", type:"slider", min:0, max:1, step:0.05},
    ]
  },
  {
    title: "Animal Biology (Wood's Curve)", icon: "",
    params: [
      {key:"wood_b",                    label:"Wood's b coefficient",             type:"slider", min:0.05, max:0.5, step:0.01, hint:"Controls rise to peak (default 0.20)"},
      {key:"wood_c",                    label:"Wood's c coefficient",             type:"slider", min:0.001, max:0.02, step:0.0005, hint:"Controls post-peak decline (default 0.0055)"},
      {key:"mature_parity",             label:"Mature Parity",                    type:"number", min:2, max:6, step:1,     hint:"Parity at which cow reaches full peak potential"},
      {key:"cow_peak_std_fraction",     label:"Cow-to-Cow Peak Variation (σ)",   type:"slider", min:0, max:0.3, step:0.01, hint:"Individual heterogeneity in peak yield"},
    ]
  },
  {
    title: "Health & Culling", icon: "",
    params: [
      {key:"illness_duration_days_mean",     label:"Mean Illness Duration (days)",     type:"slider", min:1, max:14, step:0.5,    hint:"Exponential distribution mean"},
      {key:"illness_feed_penalty_fraction",  label:"Feed Penalty when Sick",          type:"slider", min:0, max:0.5, step:0.05,  hint:"Fraction of feed reduction during illness"},
    ]
  },
  {
    title: "Body Weight & Intake", icon: "",
    params: [
      {key:"maintenance_dmi_fraction_of_bw", label:"Maintenance DMI (fraction of BW)", type:"slider", min:0.01, max:0.04, step:0.001, hint:"NRC: ~2% of body weight"},
      {key:"dmi_kg_per_L_milk",             label:"Production DMI (kg/L milk)",       type:"slider", min:0.1, max:0.6, step:0.01,   hint:"Extra dry matter per litre of milk"},
      {key:"manure_kg_per_kg_dmi",          label:"Manure Output (kg/kg DMI)",        type:"slider", min:0.5, max:4, step:0.1,      hint:"~2x DMI is typical"},
      {key:"water_base_L",                  label:"Base Water Intake (L/day)",        type:"slider", min:5, max:40, step:1},
      {key:"water_L_per_kg_dmi",            label:"Water per kg DMI (L/kg)",          type:"slider", min:1, max:8, step:0.5},
      {key:"water_L_per_L_milk",            label:"Water per L Milk (L/L)",           type:"slider", min:0.2, max:3, step:0.1},
      {key:"water_seasonal_amplitude",      label:"Seasonal Water Amplitude",         type:"slider", min:0, max:0.4, step:0.01,    hint:"Extra water demand in hot season"},
    ]
  },
];

// ════════════════════════════════════════════════════════════════════
//  CHART MANAGEMENT
// ════════════════════════════════════════════════════════════════════
const chartInstances = {};

function getChartColors() {
  const d = document.documentElement.getAttribute('data-theme')==='dark';
  return {
    grid: d ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
    tick: d ? '#797876' : '#7a7974',
    primary: d ? '#4f98a3' : '#01696f',
    success: d ? '#6daa45' : '#437a22',
    gold: d ? '#e8af34' : '#d19900',
    blue: d ? '#5591c7' : '#006494',
    orange: d ? '#fdab43' : '#da7101',
    error: d ? '#d163a7' : '#a12c7b',
    bg: d ? '#1c1b19' : '#f9f8f5',
    text: d ? '#cdccca' : '#28251d',
  };
}

function chartDefaults() {
  const co = getChartColors();
  return {
    responsive: true, maintainAspectRatio: false,
    plugins: {legend:{display:true, labels:{color:co.tick, font:{size:11}, boxWidth:10, padding:12}}, tooltip:{backgroundColor:co.bg, titleColor:co.text, bodyColor:co.tick, borderColor:co.grid, borderWidth:1}},
    scales: {x:{grid:{color:co.grid}, ticks:{color:co.tick, font:{size:10}, maxTicksLimit:8}}, y:{grid:{color:co.grid}, ticks:{color:co.tick, font:{size:10}}}},
  };
}

function destroyChart(id) { if (chartInstances[id]) { chartInstances[id].destroy(); delete chartInstances[id]; } }

function makeChart(id, type, labels, datasets, extraOptions={}) {
  destroyChart(id);
  const el = document.getElementById(id);
  if (!el) return;
  const opts = Object.assign({}, chartDefaults(), extraOptions);
  // Deep-merge scales if both exist
  if (extraOptions.scales && chartDefaults().scales) {
    opts.scales = Object.assign({}, chartDefaults().scales, extraOptions.scales);
  }
  chartInstances[id] = new Chart(el, {type, data:{labels, datasets}, options: opts});
}

function dayLabels(days) { return days.map(d => `Day ${d}`); }

function buildOverviewCharts(res) {
  const L = dayLabels(res.series.day); const co = getChartColors();
  requestAnimationFrame(() => {
    makeChart('chartMilk','line', L, [{label:'Milk (L/day)', data:res.series.milk, borderColor:co.primary, backgroundColor:co.primary+'22', fill:true, pointRadius:0, tension:.3}]);
    makeChart('chartRevenue','line', L, [
      {label:'Milk Revenue ($/day)', data:res.series.milkRev, borderColor:co.primary, backgroundColor:co.primary+'18', fill:false, pointRadius:0, tension:.3},
      {label:'Energy Revenue ($/day)', data:res.series.energyVal, borderColor:co.orange, fill:false, pointRadius:0, tension:.3},
      {label:'Heat Value ($/day)', data:res.series.heatVal, borderColor:co.gold, fill:false, pointRadius:0, tension:.3},
      {label:'Compost Revenue ($/day)', data:res.series.compostRev, borderColor:co.success, fill:false, pointRadius:0, tension:.3},
    ]);
    makeChart('chartGHG','line', L, [
      {label:'Gross GHG (kgCO₂e)', data:res.series.grossGHG, borderColor:co.error, pointRadius:0, tension:.3},
      {label:'Net GHG (kgCO₂e)', data:res.series.netGHG, borderColor:co.success, backgroundColor:co.success+'22', fill:true, pointRadius:0, tension:.3},
    ]);
    makeChart('chartEnergy','line', L, [{label:'Total Electricity (kWh/day)', data:res.series.totalElec, borderColor:co.orange, backgroundColor:co.orange+'22', fill:true, pointRadius:0, tension:.3}]);
  });
}

function buildAllCharts(res) {
  const grid = document.getElementById('allChartsGrid');
  const L = dayLabels(res.series.day); const co = getChartColors();
  const charts = [
    {id:'ts_milk', title:'Milk Production (L/day)', key:'milk', color:co.primary},
    {id:'ts_feed', title:'Net Feed Consumed (kg/day)', key:'feed', color:co.gold},
    {id:'ts_water', title:'Net Water Use (L/day)', key:'water', color:co.blue},
    {id:'ts_manure', title:'Manure Output (kg/day)', key:'manure', color:co.orange},
    {id:'ts_biogas', title:'Biogas Production (m³/day)', key:'biogas', color:co.success},
    {id:'ts_elec', title:'Total Electricity (kWh/day)', key:'totalElec', color:co.orange},
    {id:'ts_heat', title:'Heat Recovered (kWh/day)', key:'heat', color:co.error},
    {id:'ts_compost', title:'Compost Produced (kg/day)', key:'compost', color:co.success},
    {id:'ts_nrec', title:'Nitrogen Recovered (kg/day)', key:'nRec', color:co.primary},
    {id:'ts_ghg', title:'Net GHG (kgCO₂e/day)', key:'netGHG', color:co.error},
    {id:'ts_rev_milk', title:'Milk Revenue ($/day)', key:'milkRev', color:co.primary},
    {id:'ts_rev_energy', title:'Energy Revenue ($/day)', key:'energyVal', color:co.orange},
    {id:'ts_rev_heat', title:'Heat Value ($/day)', key:'heatVal', color:co.gold},
    {id:'ts_rev_compost', title:'Compost Revenue ($/day)', key:'compostRev', color:co.success},
    {id:'ts_fcr', title:'Feed Conversion Ratio (kg/kg)', key:'fcr', color:co.blue},
  ];
  grid.innerHTML = charts.map(c => `<div class="card"><div class="card-header"><div class="card-title">${c.title}</div></div><div class="card-body"><div class="chart-wrap"><canvas id="${c.id}"></canvas></div></div></div>`).join('');
  // rAF ensures canvases are painted in DOM before Chart.js measures dimensions
  requestAnimationFrame(() => {
    charts.forEach(c => {
      makeChart(c.id,'line',L,[{label:c.title, data:res.series[c.key], borderColor:c.color, backgroundColor:c.color+'22', fill:true, pointRadius:0, tension:.3}]);
    });
  });
}

function buildLoops(res) {
  const avg = res.avg;
  const n1 = v => (v ?? 0).toFixed(1);
  const n2 = v => (v ?? 0).toFixed(2);
  const n0 = v => Math.round(v ?? 0).toLocaleString();

  const totalOrganic = (avg.compost||0) + (avg.digestate||0) + (avg.sludgeFertilizer||0);
  const wwTreated    = avg.wastewater || 0;
  const freshOffsetL = avg.freshOffset || 0;

  const loopDefs = [
    {
      cls: 'lhc-l1', icon: '<svg viewBox="0 0 24 24" width="21" height="21" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 18c1-8 7-12 16-12-1 9-5 15-13 14"/><path d="M5 20c3-6 6-9 12-11"/></svg>', badge: 'Loop 1', title: 'Manure Separator',
      subtitle: 'Solid fraction → compost + N/P/K → cropland → feed offset',
      heroVal: n1(totalOrganic), heroUnit: 'kg/day', heroLabel: 'Total organic fertilizer to cropland',
      metrics: [
        ['Feed offset from nutrients', n1(avg.feedOffset) + ' kg/day'],
        ['Nitrogen recovered', n2(avg.nRec) + ' kg/day'],
        ['Phosphorus recovered', n2(avg.pRec) + ' kg/day'],
        ['Potassium recovered', n2(avg.kRec) + ' kg/day'],
        ['Digestate applied', n1(avg.digestate) + ' kg/day'],
      ]
    },
    {
      cls: 'lhc-l2', icon: '<svg viewBox="0 0 24 24" width="21" height="21" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2c-3 5-7 9-7 14a7 7 0 0 0 14 0c0-5-4-9-7-14Z"/></svg>', badge: 'Loop 2', title: 'Water Cycle',
      subtitle: 'Wastewater treatment → irrigation → fresh-water offset',
      heroVal: n0(avg.recycledIrrig), heroUnit: 'L/day', heroLabel: 'Recycled irrigation water',
      metrics: [
        ['Wastewater treated', n0(wwTreated) + ' L/day'],
        ['Fresh water offset', n0(freshOffsetL) + ' L/day'],
        ['Net water draw', n0(avg.netWater) + ' L/day'],
      ]
    },
    {
      cls: 'lhc-l3', icon: '<svg viewBox="0 0 24 24" width="21" height="21" fill="none" stroke="currentColor" stroke-width="2"><path d="m13 2-9 12h7l-1 8 10-13h-7V2Z"/></svg>', badge: 'Loop 3', title: 'Energy / Biogas',
      subtitle: 'Manure → anaerobic digester → electricity + heat',
      heroVal: n1(avg.totalElec), heroUnit: 'kWh/day', heroLabel: 'Total electricity (biogas + solar)',
      metrics: [
        ['Biogas produced', n1(avg.biogas) + ' m³/day'],
        ['Heat recovered', n1(avg.heat) + ' kWh/day'],
        ['Digestate → fertilizer', n1(avg.digestate) + ' kg/day'],
      ]
    },
    {
      cls: 'lhc-l4', icon: '<svg viewBox="0 0 24 24" width="21" height="21" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 6h16v12H4zM4 10h16M8 6v12M16 6v12"/></svg>', badge: 'Loop 4', title: 'Dairy Byproduct',
      subtitle: 'Whey + waste milk → animal feed + functional foods',
      heroVal: n1(avg.feedReturn), heroUnit: 'kg/day', heroLabel: 'Feed return from byproducts',
      metrics: [
        ['Whey → functional foods', avg.wheyFoods == null ? 'N/A' : n1(avg.wheyFoods) + ' L/day'],
        ['Sludge → fertilizer', n1(avg.sludgeFertilizer) + ' L/day'],
      ]
    },
  ];

  const grid = document.getElementById('loopGrid');
  grid.innerHTML = loopDefs.map(ld => `
    <div class="lhc ${ld.cls}">
      <div class="lhc-header">
        <div class="lhc-icon">${ld.icon}</div>
        <div class="lhc-meta">
          <div class="lhc-loop-badge">${ld.badge}</div>
          <div class="lhc-title">${ld.title}</div>
          <div class="lhc-subtitle">${ld.subtitle}</div>
        </div>
      </div>
      <div class="lhc-accent-bar"></div>
      <div class="lhc-hero-stat">
        <div>
          <div style="display:flex;align-items:baseline;gap:6px">
            <span class="lhc-hero-val">${ld.heroVal}</span>
            <span class="lhc-hero-unit">${ld.heroUnit}</span>
          </div>
          <div class="lhc-hero-label">${ld.heroLabel}</div>
        </div>
      </div>
      <div class="lhc-metrics">
        ${ld.metrics.map(([name, val]) => `
          <div class="lhc-row">
            <span class="lhc-row-name">${name}</span>
            <span class="lhc-row-val">${val}</span>
          </div>`).join('')}
      </div>
    </div>
  `).join('');

  const L = dayLabels(res.series.day);
  const co = getChartColors();
  // Build clean year-based labels (Year 1, Year 2 … only at Jan 1 of each year)
  const totalDays = res.series.day.length;
  const daysPerYear = 365;
  // Downsample: one point per week to keep chart smooth but not overwhelming
  const step = 7;
  const poolData   = [];
  const inputData  = [];
  const offsetData = [];
  const xLabels    = [];
  for (let i = 0; i < totalDays; i += step) {
    const dayNum = res.series.day[i];
    const yr = Math.floor((dayNum - 1) / daysPerYear) + 1;
    const doy = ((dayNum - 1) % daysPerYear) + 1;
    // Label: show "Yr N" at start of each year, blank otherwise
    const isYearStart = doy <= step;
    xLabels.push(isYearStart ? `Yr ${yr}` : '');
    poolData.push(res.series.nutrientPool[i] ?? 0);
    inputData.push(res.series.organicFert[i] ?? 0);
    offsetData.push(res.series.feedOffset[i] ?? 0);
  }

  destroyChart('chartNutrient');
  const elN = document.getElementById('chartNutrient');
  if (elN) {
    chartInstances['chartNutrient'] = new Chart(elN, {
      type: 'line',
      data: {
        labels: xLabels,
        datasets: [
          {
            label: 'Soil Nutrient Pool (kg)',
            data: poolData,
            borderColor: co.success,
            backgroundColor: co.success + '28',
            fill: true, pointRadius: 0, tension: 0.4,
            borderWidth: 2,
            yAxisID: 'y',
          },
          {
            label: 'Daily Organic Input (kg)',
            data: inputData,
            borderColor: co.orange || '#da7101',
            backgroundColor: 'transparent',
            fill: false, pointRadius: 0, tension: 0.3,
            borderDash: [5, 4], borderWidth: 1.5,
            yAxisID: 'y1',
          },
          {
            label: 'Feed Offset / day (kg)',
            data: offsetData,
            borderColor: co.primary,
            backgroundColor: 'transparent',
            fill: false, pointRadius: 0, tension: 0.3,
            borderDash: [2, 3], borderWidth: 1.5,
            yAxisID: 'y1',
          },
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { labels: { color: co.text, font: { size: 10 }, boxWidth: 14, padding: 12 } },
          tooltip: {
            callbacks: {
              title: ctx => {
                // Find the actual day number for this index
                const i = ctx[0].dataIndex * step;
                const dayNum = res.series.day[Math.min(i, totalDays - 1)];
                const yr = Math.floor((dayNum - 1) / daysPerYear) + 1;
                const doy = ((dayNum - 1) % daysPerYear) + 1;
                const month = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][Math.floor((doy-1)/30.44)];
                return `Year ${yr}, ~${month} (Day ${dayNum})`;
              },
              label: ctx => {
                const v = ctx.raw;
                return ` ${ctx.dataset.label}: ${v >= 1000 ? (v/1000).toFixed(1)+'k' : v.toFixed(1)} kg`;
              }
            }
          }
        },
        scales: {
          x: {
            ticks: {
              color: co.muted, font: { size: 9 }, maxRotation: 0,
              // Only show non-empty labels (year markers)
              callback: function(val, idx) { return this.getLabelForValue(val) || null; }
            },
            grid: { color: co.grid }
          },
          y: {
            position: 'left',
            title: { display: true, text: 'Nutrient Pool (kg)', color: co.muted, font: { size: 10 } },
            ticks: { color: co.muted, font: { size: 9 },
              callback: v => v >= 1000 ? (v/1000).toFixed(0)+'k' : v
            },
            grid: { color: co.grid }
          },
          y1: {
            position: 'right',
            title: { display: true, text: 'Daily kg', color: co.muted, font: { size: 10 } },
            ticks: { color: co.muted, font: { size: 9 },
              callback: v => v >= 1000 ? (v/1000).toFixed(1)+'k' : v.toFixed(1)
            },
            grid: { drawOnChartArea: false }
          }
        }
      }
    });
  }
}

// ════════════════════════════════════════════════════════════════════
//  KPI CARDS
// ════════════════════════════════════════════════════════════════════
const KPI_DEFS = [
  {id:'kpi_milk', label:'Avg. Daily Milk', key:'milk', unit:'L/day', icon:'green', iconSvg:'<path d="M3 3h18M3 9h18"/><circle cx="12" cy="16" r="3"/>'},
  {id:'kpi_milk_rev', label:'Milk Revenue', key:'milkRev', unit:'$/day', icon:'teal', iconSvg:'<path d="M3 3h18M3 9h18"/><circle cx="12" cy="16" r="3"/>'},
  {id:'kpi_energy_rev', label:'Energy Revenue', key:'energyVal', unit:'$/day', icon:'orange', iconSvg:'<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>'},
  {id:'kpi_heat_rev', label:'Heat Value', key:'heatVal', unit:'$/day', icon:'gold', iconSvg:'<path d="M12 2v6M12 16v6M4.93 4.93l4.24 4.24M14.83 14.83l4.24 4.24M2 12h6M16 12h6"/>'},
  {id:'kpi_compost_rev', label:'Compost Revenue', key:'compostRev', unit:'$/day', icon:'green', iconSvg:'<circle cx="12" cy="12" r="10"/><path d="M8 12h8M12 8v8"/>'},
  {id:'kpi_ghg', label:'Net GHG/day', key:'netGHG', unit:'kgCO₂e', icon:'teal', iconSvg:'<path d="M12 2a10 10 0 0 1 10 10"/><path d="M12 22a10 10 0 0 1-10-10"/><path d="M9 12h6M12 9v6"/>'},
  {id:'kpi_elec', label:'Daily Electricity', key:'totalElec', unit:'kWh/day', icon:'orange', iconSvg:'<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>'},
  {id:'kpi_biogas', label:'Daily Biogas', key:'biogas', unit:'m³/day', icon:'blue', iconSvg:'<path d="M12 2a10 10 0 1 0 0 20"/><path d="M12 8v4l3 3"/>'},
  {id:'kpi_feed', label:'Net Feed/day', key:'feed', unit:'kg/day', icon:'teal', iconSvg:'<path d="M12 2l3 6h6l-5 4 2 6-6-4-6 4 2-6-5-4h6z"/>'},
  {id:'kpi_compost', label:'Daily Compost', key:'compost', unit:'kg/day', icon:'green', iconSvg:'<circle cx="12" cy="12" r="10"/><path d="M8 12h8M12 8v8"/>'},
  {id:'kpi_fcr', label:'Feed Conv. Ratio', key:'fcr', unit:'kg/kg', icon:'blue', iconSvg:'<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>'},
];

function fmt(v, key) {
  if (key==='fcr') return v.toFixed(3);
  const isCurrency = ['milkRev','energyVal','heatVal','compostRev','profitability'].includes(key);
  if (isCurrency) {
    if (v >= 1e6) return '$'+(v/1e6).toFixed(2)+'M';
    if (v >= 1e3) return '$'+(v/1000).toFixed(1)+'K';
    return '$'+v.toFixed(2);
  }
  if (v >= 1e6) return (v/1e6).toFixed(2)+'M';
  if (v >= 1e4) return (v/1000).toFixed(1)+'K';
  return v.toFixed(1);
}

function fmtCurrency(v) {
  if (v >= 1e6) return '$'+(v/1e6).toFixed(3)+'M';
  if (v >= 1e3) return '$'+(v/1000).toFixed(1)+'K';
  return '$'+v.toFixed(2);
}

function renderKPIs(avg) {
  const grid = document.getElementById('kpiGrid');
  grid.innerHTML = KPI_DEFS.map(k => `
    <div class="kpi-card">
      <div class="kpi-icon ${k.icon}"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${k.iconSvg}</svg></div>
      <div class="kpi-label">${k.label}</div>
      <div class="kpi-value" id="${k.id}">${fmt(avg[k.key]||0, k.key)}<span class="kpi-unit">${k.unit}</span></div>
    </div>
  `).join('');
}

function animateKPIs() {
  document.querySelectorAll('.kpi-value').forEach(el => {
    el.classList.remove('updated');
    requestAnimationFrame(() => el.classList.add('updated'));
  });
}

function updateRevSummary(res) {
  const t   = res.totals;
  const d   = res.days;
  const simYears = d / 365;

  // Real simulation revenue fields only
  const rMilk    = t.milkRev    || 0;
  const rEnergy  = t.energyVal  || 0;
  const rHeat    = t.heatVal    || 0;
  const rCompost = t.compostRev || 0;
  const grossRev = t.totalRevenue || 0;
  const otherRevenue = Math.max(0, grossRev - rMilk - rEnergy - rHeat - rCompost);

  const totalFeedCost  = t.feedCost  || 0;
  const totalWaterCost = t.waterCost || 0;
  const netProfit = t.profit ?? 0;

  // Helpers
  const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  const pct = v => grossRev > 0 ? (v / grossRev * 100).toFixed(1) + '%' : '—';
  const perDay = v => fmtCurrency(v / d) + '/day avg';

  // ── Header ──
  set('revPeriodLabel',      res.n + ' cows · ' + simYears.toFixed(1) + ' yr (' + d.toLocaleString() + ' days)');
  set('revGrossTotalHeader', fmtCurrency(grossRev));
  set('revGrandTotal',       fmtCurrency(netProfit));

  // ── 4 Revenue streams ──
  set('revTotalMilk',    fmtCurrency(rMilk));
  set('revPctMilk',      pct(rMilk) + ' of gross');
  set('revDailyMilk',    perDay(rMilk));

  set('revTotalEnergy',  fmtCurrency(rEnergy));
  set('revPctEnergy',    pct(rEnergy) + ' of gross');
  set('revDailyEnergy',  perDay(rEnergy));

  set('revTotalHeat',    fmtCurrency(rHeat));
  set('revPctHeat',      pct(rHeat) + ' of gross');
  set('revDailyHeat',    perDay(rHeat));

  set('revTotalCompost', fmtCurrency(rCompost));
  set('revPctCompost',   pct(rCompost) + ' of gross');
  set('revDailyCompost', perDay(rCompost));

  // ── Input costs ──
  set('revTotalFeedCost',  '−' + fmtCurrency(totalFeedCost));
  set('revDailyFeedCost',  '−' + fmtCurrency(totalFeedCost / d) + '/day avg');
  set('revTotalWaterCost', '−' + fmtCurrency(totalWaterCost));
  set('revDailyWaterCost', '−' + fmtCurrency(totalWaterCost / d) + '/day avg');
  set('revOtherHerdNet', (t.otherHerdNet >= 0 ? '+' : '−') + fmtCurrency(Math.abs(t.otherHerdNet)));

  // ── Donut legend % ──
  set('legendPctMilk',    pct(rMilk));
  set('legendPctEnergy',  pct(rEnergy));
  set('legendPctHeat',    pct(rHeat));
  set('legendPctCompost', pct(rCompost));
  set('legendPctOther', pct(otherRevenue));

  document.getElementById('revSummaryWrap').style.display = 'block';

  // ── Donut chart — 4 segments matching the 4 stream cards ──
  const co = getChartColors();
  destroyChart('chartRevDonut');
  requestAnimationFrame(() => {
    const el = document.getElementById('chartRevDonut');
    if (!el) return;
    const bgStyle = s => getComputedStyle(document.documentElement).getPropertyValue(s).trim() || '';
    chartInstances['chartRevDonut'] = new Chart(el, {
      type: 'doughnut',
      data: {
        labels: ['Milk Revenue', 'Energy Value', 'Heat Value', 'Compost Revenue', 'Other Revenue'],
        datasets: [{
          data: [rMilk, rEnergy, rHeat, rCompost, otherRevenue],
          backgroundColor: [co.primary + 'cc', co.orange + 'cc', co.gold + 'cc', co.success + 'cc', co.blue + 'cc'],
          borderColor:      [co.primary,         co.orange,        co.gold,        co.success,        co.blue],
          borderWidth: 2,
          hoverOffset: 10,
        }]
      },
      options: {
        responsive: false,
        cutout: '65%',
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: bgStyle('--color-surface') || '#fff',
            titleColor:      bgStyle('--color-text')    || '#222',
            bodyColor:       bgStyle('--color-text')    || '#222',
            borderColor:     bgStyle('--color-border')  || '#ccc',
            borderWidth: 1,
            padding: 10,
            callbacks: {
              title: ctx => ctx[0].label,
              label: ctx => '  ' + fmtCurrency(ctx.raw) +
                            '  (' + (grossRev > 0 ? (ctx.raw / grossRev * 100).toFixed(1) : 0) + '%)'
            }
          }
        }
      }
    });
  });
}


function setStatus(s) {
  const badge = document.getElementById('statusBadge');
  badge.className = 'status-badge '+s;
  badge.textContent = s.charAt(0).toUpperCase()+s.slice(1);
}

let lcCharts = {};

const LC_SCENARIOS = [
  { key:'baseline', label:'Baseline',   group:'Reference',    chips:[],                    cls:'col-baseline', desc:'No circular loops' },
  { key:'l1',  label:'Loop 1',     group:'Individual',   chips:['L1'],                cls:'col-l1',     desc:'Manure Separator' },
  { key:'l2',  label:'Loop 2',     group:'Individual',   chips:['L2'],                cls:'col-l2',     desc:'Water Cycle' },
  { key:'l3',  label:'Loop 3',     group:'Individual',   chips:['L3'],                cls:'col-l3',     desc:'Energy/Biogas' },
  { key:'l4',  label:'Loop 4',     group:'Individual',   chips:['L4'],                cls:'col-l4',     desc:'Dairy Processing' },
  { key:'l1l2', label:'L1+L2',    group:'2-Loop Combo',  chips:['L1','L2'],           cls:'col-combo2', desc:'Nutrient+Water' },
  { key:'l1l3', label:'L1+L3',    group:'2-Loop Combo',  chips:['L1','L3'],           cls:'col-combo2', desc:'Nutrient+Energy' },
  { key:'l1l4', label:'L1+L4',    group:'2-Loop Combo',  chips:['L1','L4'],           cls:'col-combo2', desc:'Nutrient+Byproduct' },
  { key:'l2l3', label:'L2+L3',    group:'2-Loop Combo',  chips:['L2','L3'],           cls:'col-combo2', desc:'Water+Energy' },
  { key:'l2l4', label:'L2+L4',    group:'2-Loop Combo',  chips:['L2','L4'],           cls:'col-combo2', desc:'Water+Byproduct' },
  { key:'l3l4', label:'L3+L4',    group:'2-Loop Combo',  chips:['L3','L4'],           cls:'col-combo2', desc:'Energy+Byproduct' },
  { key:'l1l2l3', label:'L1+L2+L3', group:'3-Loop Combo', chips:['L1','L2','L3'],    cls:'col-combo3', desc:'Nutrient+Water+Energy' },
  { key:'l1l2l4', label:'L1+L2+L4', group:'3-Loop Combo', chips:['L1','L2','L4'],    cls:'col-combo3', desc:'Nutrient+Water+Byproduct' },
  { key:'l1l3l4', label:'L1+L3+L4', group:'3-Loop Combo', chips:['L1','L3','L4'],    cls:'col-combo3', desc:'Nutrient+Energy+Byproduct' },
  { key:'l2l3l4', label:'L2+L3+L4', group:'3-Loop Combo', chips:['L2','L3','L4'],    cls:'col-combo3', desc:'Water+Energy+Byproduct' },
  { key:'all4', label:'All 4',     group:'All 4 Loops',  chips:['L1','L2','L3','L4'], cls:'col-all4',   desc:'Full circular economy' },
];

const CHIP_COLORS = {
  L1: { bg: 'var(--color-success-highlight)', fg: 'var(--color-success)' },
  L2: { bg: 'var(--color-blue-highlight)',    fg: 'var(--color-blue)' },
  L3: { bg: 'var(--color-orange-highlight)',  fg: 'var(--color-orange)' },
  L4: { bg: '#dacfde',                        fg: 'var(--color-purple,#7a39bb)' },
};

function makeChip(code) {
  const c = CHIP_COLORS[code] || {};
  return `<span class="loop-chip" style="background:${c.bg};color:${c.fg}">${code}</span>`;
}

// ─── Metric definitions for the table ───────────────────────────────
const LC_METRICS = [
  { section: 'REVENUE' },
  { key: 'milkRev',      label: 'Milk Revenue ($)',           fmt: '$', sign: 'higher-good', period: true },
  { key: 'energyVal',    label: 'Energy Revenue ($)',         fmt: '$', sign: 'higher-good', period: true },
  { key: 'heatVal',      label: 'Heat Revenue ($)',           fmt: '$', sign: 'higher-good', period: true },
  { key: 'compostRev',   label: 'Compost Revenue ($)',        fmt: '$', sign: 'higher-good', period: true },
  { key: 'totalRevenue', label: 'Total Revenue ($)',          fmt: '$', sign: 'higher-good', period: true, bold: true },
  { key: 'feedCost',     label: 'Feed Cost ($)',              fmt: '$', sign: 'lower-good',  period: true },
  { key: 'waterCost',    label: 'Water Cost ($)',             fmt: '$', sign: 'lower-good',  period: true },
  { key: 'profit',       label: 'Net Profit ($)',             fmt: '$', sign: 'higher-good', period: true, bold: true },
  { section: 'LOOP 2 — WATER CYCLE' },
  { key: 'waterCredit',  label: 'Water Credit Applied (L)',   fmt: 'L', sign: 'higher-good', period: true },
  { key: 'freshOffset',  label: 'Fresh-Water Offset Queued (L)', fmt: 'L', sign: 'higher-good', period: true },
  { key: 'recycledIrrig',label:'Recycled Irrigation (L)',    fmt: 'L', sign: 'higher-good', period: true },
  { key: 'netWater',     label: 'Net Water Draw (L)',         fmt: 'L', sign: 'lower-good',  period: true },
  { section: 'LOOP 1 & 4 — FEED SAVINGS' },
  { key: 'netFeed',      label: 'Net Feed Input (kg)',        fmt: 'kg', sign: 'lower-good',  period: true },
  { key: 'feedOffset',   label: 'Nutrient Feed Offset (kg)',  fmt: 'kg', sign: 'higher-good', period: true },
  { key: 'feedReturn',   label: 'Byproduct Feed Return (kg)', fmt: 'kg', sign: 'higher-good', period: true },
  { section: 'CIRCULAR LOOP OUTPUT' },
  { key: 'organicFert',label: 'Organic Fertilizer (kg)',  fmt: 'kg', sign: 'higher-good', period: true },
  { key: 'compost',    label: 'Compost Produced (kg)',    fmt: 'kg', sign: 'higher-good', period: true },
  { key: 'biogasM3',   label: 'Biogas Produced (m³)',     fmt: 'm³', sign: 'higher-good', period: true },
  { key: 'totalElec',  label: 'Total Electricity (kWh)',    fmt:'kWh', sign: 'higher-good', period: true },
  { key: 'heat',       label: 'Heat Generated (kWh)',     fmt: 'kWh', sign: 'higher-good', period: true },
  { section: 'WASTE & NUTRIENT RECOVERY' },
  { key: 'nRecTotal',  label: 'Nitrogen Recovered (kg)',  fmt: 'kg', sign: 'higher-good', period: true },
  { key: 'pRecTotal',  label: 'Phosphorus Recovered (kg)',fmt: 'kg', sign: 'higher-good', period: true },
  { key: 'kRecTotal',  label: 'Potassium Recovered (kg)', fmt: 'kg', sign: 'higher-good', period: true },
  { section: 'ENVIRONMENTAL' },
  { key: 'netGHG',     label: 'Net GHG (kg CO₂e)',        fmt: 'kg', sign: 'lower-good',  period: true },
  { key: 'grossGHG',   label: 'Gross GHG (kg CO₂e)',      fmt: 'kg', sign: 'lower-good',  period: true },
  { key: 'avoidedGrid',label: 'Grid GHG Avoided (kg CO₂e)',fmt:'kg', sign: 'higher-good', period: true },
  { section: 'DAILY AVERAGES' },
  { key: 'milk',       label: 'Avg Daily Milk (L)',       fmt: 'L',  sign: 'higher-good', period: false },
  { key: 'netFCR',     label: 'Avg Net FCR (kg/kg)',      fmt: 'r3', sign: 'lower-good',  period: false },
  { key: 'grossFCR',   label: 'Avg Gross FCR (kg/kg)',    fmt: 'r3', sign: 'lower-good',  period: false },
];

function lcFmt(val, fmt) {
  if (val === undefined || val === null || isNaN(val)) return '—';
  if (fmt === '$')   return '$' + val.toLocaleString('en', {maximumFractionDigits: 0});
  if (fmt === 'r3')  return val.toFixed(3);
  if (fmt === 'r2')  return val.toFixed(2);
  // kg, L, m³, kWh
  return val.toLocaleString('en', {maximumFractionDigits: 0});
}

function lcDelta(val, baseVal, fmt, sign) {
  const diff = val - baseVal;
  if (Math.abs(diff) < 0.0001) return `<span class="delta-neutral">—</span>`;
  const pct = baseVal !== 0 ? (diff / Math.abs(baseVal) * 100) : 0;
  const pos  = diff > 0;
  const good = (sign === 'higher-good') ? pos : !pos;
  const cls  = good ? 'delta-pos' : 'delta-neg';
  const sign2 = pos ? '+' : '';
  const fmtDiff = fmt === 'r3' || fmt === 'r2'
    ? sign2 + diff.toFixed(fmt === 'r3' ? 3 : 2)
    : (pos ? '+' : '') + lcFmt(diff, fmt);
  const pctStr = pct !== 0 ? ` (${pct > 0 ? '+' : ''}${pct.toFixed(1)}%)` : '';
  return `<span class="${cls}">${fmtDiff}${pctStr}</span>`;
}

let _lcCurrentHighlight = 'all';

let cmpMode       = 'A';           // 'A' or 'D'
let cmpResults    = null;          // cached after runLoopComparison
let modeASelected = new Set(['l1','l2','l3','l4']); // default 4 individual loops
let hlMode        = 'all';         // highlight filter

function switchCmpMode(mode) {
  cmpMode = mode;
  document.getElementById('modePanelA').style.display = mode === 'A' ? 'block' : 'none';
  document.getElementById('modePanelB').style.display = mode === 'B' ? 'block' : 'none';
  document.getElementById('modeTabA').classList.toggle('active-mode-tab', mode === 'A');
  document.getElementById('modeTabB').classList.toggle('active-mode-tab', mode === 'B');
  if (!cmpResults) return;
  if (mode === 'A') renderModeATable();
  else              renderModeDTable();
}

// ── BUILD MODE A CHECKBOXES ──────────────────────────────────────────────────
function buildModeACheckboxes() {
  const wrap = document.getElementById('modeACheckboxes');
  if (!wrap) return;
  wrap.innerHTML = '';
  LC_SCENARIOS.slice(1).forEach(sc => {
    const pill = document.createElement('span');
    pill.className = 'sc-pill' + (modeASelected.has(sc.key) ? ' selected' : '');
    pill.dataset.key = sc.key;
    pill.innerHTML = sc.chips.map(makeChip).join('') + ' <span style="margin-left:2px">' + sc.label + '</span>';
    pill.title = sc.desc;
    pill.addEventListener('click', () => {
      if (modeASelected.has(sc.key)) {
        modeASelected.delete(sc.key);
        pill.classList.remove('selected');
      } else {
          modeASelected.add(sc.key);
        pill.classList.add('selected');
      }
      if (cmpResults) renderModeATable();
    });
    wrap.appendChild(pill);
  });
}

// ── BUILD MODE D DROPDOWNS ───────────────────────────────────────────────────
function buildModeDDropdowns() {
  ['pairPickerA','pairPickerB'].forEach((id, idx) => {
    const sel = document.getElementById(id);
    if (!sel) return;
    sel.innerHTML = '';
    // group options
    const groups = ['Reference','Individual','2-Loop Combo','3-Loop Combo','All 4 Loops'];
    groups.forEach(g => {
      const scs = LC_SCENARIOS.filter(s => s.group === g || (g === 'Reference' && s.key === 'baseline'));
      if (!scs.length) return;
      const og = document.createElement('optgroup');
      og.label = g;
      scs.forEach(sc => {
        const o = document.createElement('option');
        o.value = sc.key;
        o.textContent = sc.label + ' — ' + sc.desc;
        og.appendChild(o);
      });
      sel.appendChild(og);
    });
    // defaults: A = baseline, B = all4
    sel.value = idx === 0 ? 'baseline' : 'all4';
  });
}

// ── RENDER MODE A TABLE (baseline pinned + selected scenarios) ───────────────
function renderModeATable() {
  const results = cmpResults;
  const base    = results.baseline;
  const selected = Array.from(modeASelected);
  const selScenarios = LC_SCENARIOS.filter(s => selected.includes(s.key));

  document.getElementById('cmpTableTitle').textContent    = 'Baseline + Selected Scenarios';
  document.getElementById('cmpTableSubtitle').textContent = 'Baseline always pinned · Δ = change vs Baseline · tick scenarios above to add/remove';

  const tbl = document.getElementById('loopCmpTable');
  tbl.innerHTML = '';

  const thead = tbl.createTHead();
  const hr1 = thead.insertRow();

  // Group header row
  const metricTh0 = document.createElement('th');
  metricTh0.textContent = 'Metric'; metricTh0.rowSpan = 1;
  hr1.appendChild(metricTh0);

  const baseTh0 = document.createElement('th');
  baseTh0.textContent = 'Baseline'; baseTh0.className = 'col-baseline';
  baseTh0.style.cssText = 'text-align:center;padding:var(--space-2) var(--space-3)';
  hr1.appendChild(baseTh0);

  selScenarios.forEach(sc => {
    const th = document.createElement('th');
    th.className = sc.cls;
    th.style.cssText = 'text-align:center;padding:var(--space-2) var(--space-3)';
    const chips = sc.chips.map(makeChip).join('');
    th.innerHTML = `<div style="display:flex;gap:2px;justify-content:center;margin-bottom:2px">${chips}</div><div style="font-weight:700;font-size:var(--text-xs)">${sc.label}</div><div style="font-size:10px;color:var(--color-text-faint)">${sc.desc}</div>`;
    hr1.appendChild(th);
  });

  const tbody = tbl.createTBody();
  const totalCols = 1 + 1 + selScenarios.length;

  LC_METRICS.forEach(m => {
    if (m.section) {
      const tr = tbody.insertRow();
      tr.className = 'section-row';
      const td = tr.insertCell(); td.colSpan = totalCols; td.textContent = m.section;
      return;
    }
    const tr = tbody.insertRow();
    const td0 = tr.insertCell();
    td0.className = 'metric-label'; td0.textContent = m.label;
    if (m.bold) td0.style.fontWeight = '700';

    const baseVal = m.period ? (base.totals[m.key] || 0) : (base.avg[m.key] || 0);

    // Baseline column
    const tdBase = tr.insertCell();
    tdBase.className = 'val-cell col-baseline';
    tdBase.innerHTML = `<span>${lcFmt(baseVal, m.fmt)}</span><div style="font-size:10px;color:var(--color-text-faint)">— reference</div>`;

    // Selected scenarios
    selScenarios.forEach(sc => {
      const td = tr.insertCell();
      const res = results[sc.key];
      if (!res) { td.textContent = '—'; return; }
      const val = m.period ? (res.totals[m.key] || 0) : (res.avg[m.key] || 0);
      td.className = 'val-cell' + (sc.key === 'all4' ? ' col-all4' : '');
      td.innerHTML = `<span>${lcFmt(val, m.fmt)}</span>${lcDelta(val, baseVal, m.fmt, m.sign)}`;
    });
  });

  applyHlMode();
  updateChartsForMode();
}

// ── RENDER MODE B TABLE (pairwise A vs B with Δ column) ──────────────────────
function renderPairTable() {
  if (!cmpResults) return;
  renderModeDTable();
}

function renderModeDTable() {
  const results = cmpResults;
  const keyA = document.getElementById('pairPickerA')?.value || 'baseline';
  const keyB = document.getElementById('pairPickerB')?.value || 'all4';
  const scA  = LC_SCENARIOS.find(s => s.key === keyA);
  const scB  = LC_SCENARIOS.find(s => s.key === keyB);
  if (!scA || !scB) return;

  document.getElementById('cmpTableTitle').textContent    = scA.label + ' vs ' + scB.label;
  document.getElementById('cmpTableSubtitle').textContent = 'Side-by-side · Δ = B minus A (absolute + %)';

  const tbl = document.getElementById('loopCmpTable');
  tbl.innerHTML = '';

  const resA = results[keyA];
  const resB = results[keyB];

  const thead = tbl.createTHead();
  const hr = thead.insertRow();
  ['Metric', scA.label, scB.label, 'Δ  (B − A)'].forEach((label, i) => {
    const th = document.createElement('th');
    th.style.cssText = 'text-align:center;padding:var(--space-2) var(--space-3)';
    if (i === 0) { th.textContent = label; th.style.textAlign = 'left'; }
    else if (i === 1) {
      const chips = scA.chips.map(makeChip).join('');
      th.innerHTML = `<div style="display:flex;gap:2px;justify-content:center;margin-bottom:2px">${chips || '<span style="font-size:10px;padding:2px 6px;border-radius:99px;background:var(--color-surface-offset);color:var(--color-text-muted);font-weight:700">0</span>'}</div><div style="font-weight:700;font-size:var(--text-xs)">${scA.label}</div><div style="font-size:10px;color:var(--color-text-faint)">${scA.desc}</div>`;
      th.className = scA.cls || 'col-baseline';
    } else if (i === 2) {
      const chips = scB.chips.map(makeChip).join('');
      th.innerHTML = `<div style="display:flex;gap:2px;justify-content:center;margin-bottom:2px">${chips || '<span style="font-size:10px;padding:2px 6px;border-radius:99px;background:var(--color-surface-offset);color:var(--color-text-muted);font-weight:700">0</span>'}</div><div style="font-weight:700;font-size:var(--text-xs)">${scB.label}</div><div style="font-size:10px;color:var(--color-text-faint)">${scB.desc}</div>`;
      th.className = scB.cls || '';
    } else {
      th.textContent = label; th.className = 'col-diff'; th.style.fontStyle = 'italic';
    }
    hr.appendChild(th);
  });

  const tbody = tbl.createTBody();
  LC_METRICS.forEach(m => {
    if (m.section) {
      const tr = tbody.insertRow();
      tr.className = 'section-row';
      const td = tr.insertCell(); td.colSpan = 4; td.textContent = m.section;
      return;
    }
    const tr = tbody.insertRow();
    const td0 = tr.insertCell();
    td0.className = 'metric-label'; td0.textContent = m.label;
    if (m.bold) td0.style.fontWeight = '700';

    const valA = m.period ? (resA.totals[m.key]||0) : (resA.avg[m.key]||0);
    const valB = m.period ? (resB.totals[m.key]||0) : (resB.avg[m.key]||0);
    const diff = valB - valA;
    const pct  = valA !== 0 ? (diff / Math.abs(valA) * 100) : 0;

    const tdA = tr.insertCell();
    tdA.className = 'val-cell ' + (scA.cls||'col-baseline');
    tdA.innerHTML = `<span>${lcFmt(valA, m.fmt)}</span>`;

    const tdB = tr.insertCell();
    tdB.className = 'val-cell ' + (scB.cls||'');
    tdB.innerHTML = `<span>${lcFmt(valB, m.fmt)}</span>`;

    const tdD = tr.insertCell();
    tdD.className = 'val-cell col-diff';
    const goodDiff = m.sign === 'lower-good' ? -diff : diff;
    const cls = goodDiff > 0.001 ? 'delta-pos' : goodDiff < -0.001 ? 'delta-neg' : 'delta-neutral';
    const sign = diff >= 0 ? '+' : '';
    tdD.innerHTML = `<span class="${cls}">${sign}${lcFmt(diff, m.fmt)}</span><div style="font-size:10px;color:var(--color-text-faint)">${sign}${pct.toFixed(1)}%</div>`;
  });
  updateChartsForMode();
}

// ── HIGHLIGHT FILTER ─────────────────────────────────────────────────────────
function loopHighlight(mode, btn) {
  hlMode = mode;
  document.querySelectorAll('.rank-filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  applyHlMode();
}

function applyHlMode() {
  const tbl = document.getElementById('loopCmpTable');
  if (!tbl) return;
  tbl.querySelectorAll('tbody tr:not(.section-row)').forEach(tr => {
    if (hlMode === 'all') { tr.style.display = ''; return; }
    const hasDelta = tr.querySelector('.delta-pos, .delta-neg');
    const hasPos   = tr.querySelector('.delta-pos');
    const hasNeg   = tr.querySelector('.delta-neg');
    if (hlMode === 'gains')   tr.style.display = hasPos ? '' : 'none';
    if (hlMode === 'savings') tr.style.display = hasNeg ? '' : 'none';
  });
}

function renderLoopTable(results) {
  // legacy shim — Mode A is now the default
  renderModeATable();
}


function renderLoopKpiBanner(results) {
  // Replaced by compact summary strip — 3 key stats only
  const base  = results.baseline;
  const all4  = results.all4;
  const strip = document.getElementById('loopCmpSummaryStrip');
  if (!strip) return;

  const profitGain = all4.totals.profit - base.totals.profit;
  const ghgReduce  = base.totals.netGHG - all4.totals.netGHG;

  // Best profit scenario across all 15
  let bestName = '', bestVal = -Infinity;
  LC_SCENARIOS.slice(1).forEach(sc => {
    const v = results[sc.key]?.totals.profit - base.totals.profit;
    if (v > bestVal) { bestVal = v; bestName = sc.label; }
  });

  const fmt$  = v => (v >= 0 ? '+$' : '-$') + Math.abs(v).toLocaleString('en',{maximumFractionDigits:0});
  const fmtKg = v => (v >= 0 ? '−' : '+') + Math.abs(v).toLocaleString('en',{maximumFractionDigits:0}) + ' kg';

  strip.innerHTML = `
    <div class="cmp-stat">
      <div class="cmp-stat-label">All-4 Net Profit Change</div>
      <div class="cmp-stat-value" style="color:${profitGain>=0?'var(--color-success)':'var(--color-notification)'}">${fmt$(profitGain)}</div>
      <div class="cmp-stat-sub">vs Baseline over simulation period</div>
    </div>
    <div class="cmp-stat">
      <div class="cmp-stat-label">Best Profit Scenario</div>
      <div class="cmp-stat-value">${bestName}</div>
      <div class="cmp-stat-sub">${fmt$(bestVal)} vs Baseline</div>
    </div>
    <div class="cmp-stat">
      <div class="cmp-stat-label">All-4 GHG Change</div>
      <div class="cmp-stat-value" style="color:${ghgReduce>=0?'var(--color-success)':'var(--color-notification)'}">${fmtKg(ghgReduce)} CO₂e</div>
      <div class="cmp-stat-sub">net emissions over simulation period</div>
    </div>`;
}


// ── Active chart state ────────────────────────────────────────────────────────
let activeChartKey = 'profit';
const CHART_META = {
  profit:  { title:'Net Profit vs Baseline',      yFmt: v=>'$'+(v/1000).toFixed(0)+'k',  tip: ctx=>' $'+ctx.raw.toLocaleString(),          val: (r,b)=>r.totals.profit,       diff: (r,b)=>r.totals.profit - b.totals.profit },
  revenue: { title:'Total Revenue vs Baseline',   yFmt: v=>'$'+(v/1000).toFixed(0)+'k',  tip: ctx=>' $'+ctx.raw.toLocaleString(),          val: (r,b)=>r.totals.totalRevenue, diff: (r,b)=>r.totals.totalRevenue - b.totals.totalRevenue },
  feed:    { title:'Feed Cost Savings vs Baseline',yFmt:v=>'$'+Math.abs(v).toLocaleString(undefined,{maximumFractionDigits:0}), tip: ctx=>' $'+ctx.raw.toLocaleString(undefined,{maximumFractionDigits:0}), val: (r,b)=>b.totals.feedCost - r.totals.feedCost, diff:(r,b)=>b.totals.feedCost - r.totals.feedCost },
  water:   { title:'Water Cost Savings vs Baseline',yFmt:v=>'$'+v.toLocaleString(),       tip: ctx=>' $'+ctx.raw.toLocaleString(undefined,{maximumFractionDigits:0}), val:(r,b)=>b.totals.waterCost - r.totals.waterCost, diff:(r,b)=>b.totals.waterCost - r.totals.waterCost },
  ghg:     { title:'GHG Reduction vs Baseline',   yFmt: v=>(v/1000).toFixed(1)+'t',      tip: ctx=>' '+ctx.raw.toLocaleString()+' kg CO₂e', val:(r,b)=>b.totals.netGHG   - r.totals.netGHG,  diff:(r,b)=>b.totals.netGHG   - r.totals.netGHG },
};

function getComparisonRef(mode) {
  if (!cmpResults) return null;
  if (mode === 'B') {
    const keyA = document.getElementById('pairPickerA')?.value || 'baseline';
    return cmpResults[keyA] || cmpResults.baseline;
  }
  return cmpResults.baseline;
}

function switchChart(key, btn) {
  activeChartKey = key;
  document.querySelectorAll('.cmp-chart-tab').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  const titleEl = document.getElementById('cmpChartTitle');
  if (titleEl && CHART_META[key]) titleEl.textContent = CHART_META[key].title;
  if (cmpResults) setTimeout(() => drawActiveChart(), 20);
}

function renderLoopCharts(results) {
  updateChartsForMode();
}

function getChartScenarioKeys() {
  if (cmpMode === 'A') {
    return LC_SCENARIOS.slice(1).filter(s => modeASelected.has(s.key)).map(s => s.key);
  } else {
    const keyA = document.getElementById('pairPickerA')?.value || 'baseline';
    const keyB = document.getElementById('pairPickerB')?.value || 'all4';
    return keyA === keyB ? [keyA] : [keyA, keyB];
  }
}

function updateChartsForMode() {
  if (!cmpResults) return;
  // Small delay so DOM is painted and canvases have real dimensions
  setTimeout(() => {
    drawActiveChart();
    drawRadar();
    drawGroupAvg();
  }, 20);
}

function drawActiveChart() {
  const results = cmpResults;
  const co      = getChartColors();
  const base    = getComparisonRef(cmpMode);
  const meta    = CHART_META[activeChartKey];
  const activeKeys = getChartScenarioKeys();
  const displayScs = activeKeys.map(k => LC_SCENARIOS.find(s => s.key === k)).filter(Boolean);
  const labels     = displayScs.map(s => s.label);

  const scColor = k => {
    const sc = LC_SCENARIOS.find(s => s.key === k);
    if (!sc || k === 'baseline') return co.muted;
    if (sc.group === 'Individual')   return co.primary;
    if (sc.group === '2-Loop Combo') return co.gold || '#d19900';
    if (sc.group === '3-Loop Combo') return co.orange || '#da7101';
    if (sc.group === 'All 4 Loops')  return co.success;
    return co.muted;
  };
  const barColors = cmpMode === 'B' && activeKeys.length === 2
    ? [co.primary, co.orange || '#da7101']
    : activeKeys.map(scColor);

  if (lcCharts.active) { try { lcCharts.active.destroy(); } catch(e){} }

  const titleEl = document.getElementById('cmpChartTitle');
  if (titleEl) titleEl.textContent = meta.title;

  const data = displayScs.map(sc => meta.diff(results[sc.key], base));

  const baselineVal = 0;
  const datasets = [{ label: meta.title, data, backgroundColor: barColors, borderRadius: 4 }];

  // Full-width baseline rule drawn as a canvas plugin (not a dataset)
  // so it always spans the entire plot area — no gap at start/end
  const baselinePlugin = cmpMode === 'A' ? [{
    id: 'baselineLine',
    afterDraw(chart) {
      const { ctx, scales: { y }, chartArea: { left, right } } = chart;
      const yPos = y.getPixelForValue(baselineVal);
      const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
      ctx.save();
      ctx.beginPath();
      ctx.setLineDash([6, 4]);
      ctx.moveTo(left, yPos);
      ctx.lineTo(right, yPos);
      ctx.strokeStyle = isDark ? '#e5e5e5' : '#1a1a1a';
      ctx.lineWidth = 1.5;
      ctx.globalAlpha = 0.75;
      ctx.stroke();
      ctx.restore();
      // "Baseline" label at right edge
      ctx.save();
      ctx.font = '9px sans-serif';
      ctx.fillStyle = isDark ? '#aaa' : '#444';
      ctx.fillText(cmpMode === 'B' ? 'Reference' : 'Baseline', right + 5, yPos + 3);
      ctx.restore();
    }
  }] : [];

  const xAxis = { ticks:{ color:co.muted, font:{size:10}, maxRotation:0, minRotation:0 }, grid:{ color:co.grid } };
  const yAxis = { ticks:{ color:co.muted, font:{size:10}, callback: meta.yFmt }, grid:{ color:co.grid } };

  lcCharts.active = new Chart(document.getElementById('chartLcActive'), {
    type: 'bar',
    data: { labels, datasets },
    options: { responsive:true, maintainAspectRatio:false,
      layout: { padding: { right: cmpMode === 'A' ? 60 : 0 } },
      plugins: { legend:{ display:false }, tooltip:{ callbacks:{ label: meta.tip } } },
      scales: { x: xAxis, y: yAxis }
    },
    plugins: baselinePlugin
  });
}

function drawRadar() {
  const results = cmpResults;
  const co      = getChartColors();
  const base    = getComparisonRef(cmpMode);
  const activeKeys = getChartScenarioKeys();
  const displayScs = activeKeys.map(k => LC_SCENARIOS.find(s => s.key === k)).filter(Boolean);

  // Normalise across all 15 (so the scale stays stable)
  const allNB = LC_SCENARIOS.slice(1);
  const mx = {
    profit:  Math.max(1, ...allNB.map(s => results[s.key]?.totals.profit || 0)),
    revenue: Math.max(1, ...allNB.map(s => results[s.key]?.totals.totalRevenue || 0)),
    feed:    Math.max(1, ...allNB.map(s => base.totals.netFeed  - (results[s.key]?.totals.netFeed  || 0))),
    water:   Math.max(1, ...allNB.map(s => base.totals.waterCost- (results[s.key]?.totals.waterCost|| 0))),
    ghg:     Math.max(1, ...allNB.map(s => base.totals.netGHG   - (results[s.key]?.totals.netGHG   || 0))),
  };
  const norm = (v, mx) => Math.max(0, v/mx*100);

  if (lcCharts.radar) { try { lcCharts.radar.destroy(); } catch(e){} }
  const colors = ['#01696f','#da7101','#27ae60','#2980b9','#8e44ad','#c0392b','#e67e22','#16a085'];
  lcCharts.radar = new Chart(document.getElementById('chartLcRadar'), {
    type:'radar',
    data:{
      labels:['Net Profit','Revenue','Feed Savings','Water Savings','GHG Reduction'],
      datasets: displayScs.map((sc,i)=>{
        const r = results[sc.key]; const c = colors[i % colors.length];
        return { label:sc.label, data:[
          norm(r.totals.profit, mx.profit),
          norm(r.totals.totalRevenue, mx.revenue),
          norm(base.totals.netFeed  - r.totals.netFeed,  mx.feed),
          norm(base.totals.waterCost- r.totals.waterCost, mx.water),
          norm(base.totals.netGHG   - r.totals.netGHG,   mx.ghg),
        ], borderColor:c, backgroundColor:c+'20', borderWidth:2, pointRadius:3 };
      })
    },
    options:{ responsive:true, maintainAspectRatio:false,
      plugins:{ legend:{ labels:{ color:co.text, font:{size:9}, boxWidth:10 }, position:'right' } },
      scales:{ r:{ min:0, max:100, ticks:{ color:co.muted, font:{size:9}, stepSize:25, backdropColor:'transparent' }, grid:{ color:co.grid }, pointLabels:{ color:co.text, font:{size:10} } } }
    }
  });
}

function drawGroupAvg() {
  const results = cmpResults;
  const co = getChartColors();
  const base = getComparisonRef(cmpMode);
  if (lcCharts.groupRev) { try { lcCharts.groupRev.destroy(); } catch(e){} }
  const groups = ['Individual','2-Loop Combo','3-Loop Combo','All 4 Loops'];
  const avgs = groups.map(g => {
    const scs = LC_SCENARIOS.filter(s => s.group === g);
    return scs.reduce((sum,s)=>sum+((results[s.key]?.totals.profit||0)-base.totals.profit),0)/(scs.length||1);
  });
  lcCharts.groupRev = new Chart(document.getElementById('chartLcGroupRev'),{
    type:'bar', data:{ labels:groups, datasets:[{ label:'Avg Profit Gain ($)', data:avgs,
      backgroundColor:[co.primary, co.gold||'#d19900', co.orange||'#da7101', co.success], borderRadius:6 }] },
    options:{ responsive:true, maintainAspectRatio:false, indexAxis:'y',
      plugins:{ legend:{ display:false }, tooltip:{ callbacks:{ label:ctx=>' $'+ctx.raw.toLocaleString() } } },
      scales:{
        x:{ ticks:{ color:co.muted, font:{size:10}, callback:v=>'$'+(v/1000).toFixed(0)+'k' }, grid:{ color:co.grid } },
        y:{ ticks:{ color:co.text, font:{size:11} }, grid:{ display:false } }
      }
    }
  });
}


function buildParamForms() {
  const container = document.getElementById('paramGroups');
  container.innerHTML = PARAM_GROUPS.map(group => `
    <div class="param-group">
      <div class="param-group-header">${group.icon} ${group.title}</div>
      <div class="param-group-body">
        ${group.params.map(p => buildParamHTML(p)).join('')}
      </div>
    </div>
  `).join('');
  // Build quick-jump navigator
  const nav = document.getElementById('paramGroupNav');
  if (nav) {
    const pills = PARAM_GROUPS.map((g, i) => {
      const id = 'pg_' + i;
      return '<a href="#' + id + '" style="font-size:11px;padding:3px 9px;background:var(--color-surface);border:1px solid var(--color-divider);border-radius:12px;color:var(--color-text-muted);text-decoration:none;white-space:nowrap" onclick="document.getElementById(\'pg_'+i+'\').scrollIntoView({behavior:\'smooth\',block:\'start\'});return false">' + g.icon + ' ' + g.title + '</a>';
    });
    // keep the label span, replace rest
    nav.innerHTML = '<span style="font-size:11px;font-weight:700;color:var(--color-text-muted);width:100%;margin-bottom:4px;display:block">JUMP TO SECTION</span>' + pills.join('');
  }
  // Add id anchors to each param-group div
  container.querySelectorAll('.param-group').forEach((el, i) => { el.id = 'pg_' + i; });

  // Build animal params separately
  const animalContainer = document.getElementById('animalParamGroups');
  const animalGroups = [
    {title:"Lactation — Wood's Curve", icon:'', params:[
      {key:'peak_milk_L_first_parity',  label:'Peak Milk 1st Parity (L/day)',    type:'slider', min:15, max:70,    step:1,      hint:"Heifer peak yield"},
      {key:'peak_milk_L_mature',        label:'Peak Milk Mature Cow (L/day)',    type:'slider', min:20, max:80,    step:1,      hint:"Peak for parity ≥ mature_parity"},
      {key:'lactation_length_days',     label:'Lactation Length (days)',          type:'slider', min:200, max:400,  step:5,      hint:"Standard 305 days"},
      {key:'dry_period_days',           label:'Dry Period (days)',                type:'slider', min:30, max:120,   step:5,      hint:"Rest before next calving; typical 60 days"},
      {key:'wood_b',                    label:"Wood's b (rise to peak)",          type:'slider', min:0.05, max:0.5, step:0.01,   hint:"Controls rise speed (default 0.20)"},
      {key:'wood_c',                    label:"Wood's c (post-peak decline)",     type:'slider', min:0.001, max:0.02, step:0.0005, hint:"Controls decline rate (default 0.0055)"},
      {key:'mature_parity',             label:'Mature Parity',                    type:'number', min:2, max:6,      step:1,      hint:"Parity at which cow reaches full peak potential"},
      {key:'max_parity',                label:'Max Parity (cull threshold)',      type:'number', min:2, max:12,     step:1,      hint:"Cow culled when she would exceed this parity"},
      {key:'cow_peak_std_fraction',     label:'Cow-to-Cow Peak Variation (σ)',   type:'slider', min:0, max:0.3,    step:0.01,   hint:"Individual heterogeneity in peak yield"},
    ], isAnimal:true},
    {title:'Health & Disease', icon:'', params:[
      {key:'daily_illness_probability',      label:'Daily Illness Probability',   type:'slider', min:0, max:0.05, step:0.001, hint:"Chance/day a healthy cow falls ill"},
      {key:'illness_duration_days_mean',     label:'Mean Illness Duration (days)',type:'slider', min:1, max:14,   step:0.5,   hint:"Exponential distribution mean"},
      {key:'illness_milk_penalty_fraction',  label:'Milk Penalty when Sick',      type:'slider', min:0, max:0.8,  step:0.05,  hint:"Fraction of milk lost during illness"},
      {key:'illness_feed_penalty_fraction',  label:'Feed Penalty when Sick',      type:'slider', min:0, max:0.5,  step:0.05,  hint:"Fraction of feed reduction during illness"},
    ], isAnimal:true},
    {title:'Reproduction & Culling', icon:'', params:[
      {key:'annual_involuntary_cull_fraction', label:'Annual Involuntary Cull Rate', type:'slider', min:0.01, max:0.40, step:0.01, hint:"12% default; max-parity retirements are additional"},
    ], isAnimal:true},
    {title:'Body Weight & Intake', icon:'', params:[
      {key:'bodyweight_first_parity_kg',      label:'Heifer Body Weight (kg)',         type:'slider', min:300, max:800,  step:10},
      {key:'bodyweight_mature_kg',            label:'Mature Cow Body Weight (kg)',     type:'slider', min:400, max:1000, step:10},
      {key:'maintenance_dmi_fraction_of_bw',  label:'Maintenance DMI (fraction of BW)',type:'slider', min:0.01, max:0.04, step:0.001, hint:"NRC: ~2% of body weight"},
      {key:'dmi_kg_per_L_milk',               label:'Production DMI (kg/L milk)',      type:'slider', min:0.1, max:0.6,  step:0.01,  hint:"Extra dry matter per litre of milk"},
      {key:'manure_kg_per_kg_dmi',            label:'Manure Output (kg/kg DMI)',       type:'slider', min:0.5, max:4,    step:0.1,   hint:"~2x DMI is typical"},
      {key:'water_base_L',                    label:'Base Water Intake (L/day)',        type:'slider', min:5, max:40,    step:1},
      {key:'water_L_per_kg_dmi',              label:'Water per kg DMI (L/kg)',          type:'slider', min:1, max:8,    step:0.5},
      {key:'water_L_per_L_milk',              label:'Water per L Milk (L/L)',           type:'slider', min:0.2, max:3,  step:0.1},
      {key:'water_seasonal_amplitude',        label:'Seasonal Water Amplitude',         type:'slider', min:0, max:0.4,  step:0.01,  hint:"Extra water demand in hot season"},
    ], isAnimal:true},
  ];
  animalContainer.innerHTML = animalGroups.map(group => `
    <div class="param-group">
      <div class="param-group-header">${group.icon} ${group.title}</div>
      <div class="param-group-body">
        ${group.params.map(p => buildParamHTML(p, true)).join('')}
      </div>
    </div>
  `).join('');
}

function formatParamVal(key, val) {
  // Percentage keys — show as % with 0 decimals
  if (key.includes('fraction') || key.includes('cull') || key === 'manure_to_treatment_fraction'
      || key === 'methane_reduction_factor') {
    if (val <= 1 && val >= 0) return (val * 100).toFixed(0) + '%';
  }
  // Probability keys
  if (key.includes('probability')) return (val * 100).toFixed(2) + '%';
  // Integer-like keys
  if (Number.isInteger(val) || (val >= 1 && val % 1 === 0)) return String(Math.round(val));
  // Small decimals (< 1)
  if (Math.abs(val) < 0.01) return val.toFixed(4);
  if (Math.abs(val) < 0.1)  return val.toFixed(3);
  if (Math.abs(val) < 10)   return val.toFixed(2);
  return val.toFixed(1);
}

function buildParamHTML(p, isAnimal=false) {
  // Always read from cfg (live values) — cfg is initialised from DEFAULTS so this works for both normal and animal params
  const currentVal = cfg[p.key] ?? DEFAULTS[p.key] ?? DEFAULTS_ANIMAL[p.key] ?? 0;
  const disabled = !supportedParams.has(p.key);
  const disabledAttr = disabled ? 'disabled title="Not used by the Python model"' : '';
  if (p.type === 'toggle') {
    return `<div class="toggle-wrap">
      <label class="toggle">
        <input type="checkbox" ${disabledAttr} ${currentVal?'checked':''} onchange="updateParam('${p.key}', this.checked, ${isAnimal})" />
        <span class="toggle-track"></span>
        <span class="toggle-thumb"></span>
      </label>
      <span class="toggle-label">${p.label}</span>
    </div>`;
  }
  if (p.type === 'slider') {
    return `<div class="param-row">
      <label class="param-label">${p.label}<span class="param-value-display" id="pv_${p.key}">${formatParamVal(p.key, currentVal)}</span></label>
      <input type="range" class="param-slider" ${disabledAttr} min="${p.min}" max="${p.max}" step="${p.step}" value="${currentVal}"
        oninput="updateParam('${p.key}', +this.value, ${isAnimal}); this.closest('.param-row').querySelector('.param-value-display').textContent=formatParamVal('${p.key}', +this.value)" />
      ${p.hint ? `<span class="param-hint">${p.hint}</span>` : ''}
    </div>`;
  }
  // number input
  return `<div class="param-row">
    <label class="param-label">${p.label}</label>
    <input type="number" class="param-input" ${disabledAttr} min="${p.min}" max="${p.max}" step="${p.step||1}" value="${currentVal}"
      onchange="updateParam('${p.key}', +this.value, ${isAnimal})" />
    ${p.hint ? `<span class="param-hint">${p.hint}</span>` : ''}
  </div>`;
}

const DEFAULTS_ANIMAL = {
  peak_milk_L_first_parity: 38, peak_milk_L_mature: 50, lactation_length_days: 305,
  dry_period_days: 60, daily_illness_probability: 0.004, illness_milk_penalty_fraction: 0.35,
  max_parity: 6, annual_involuntary_cull_fraction: 0.12,
  bodyweight_first_parity_kg: 540, bodyweight_mature_kg: 680,
};

function updateParam(key, value, isAnimal=false) {
  if (key === 'separator_solid_fraction') {
    cfg.separator_solid_fraction = value;
    cfg.separator_liquid_fraction = +(1 - value).toFixed(4);
  } else {
    cfg[key] = value;
  }
  // Mark dashboard as stale — user must click Run to update charts
  markParamsDirty();
}

function markParamsDirty() {
  const btn = document.getElementById('runBtn');
  if (btn) {
    btn.classList.add('dirty');
    btn.title = 'Parameters changed — click to re-run simulation';
  }
  // Show stale banner on chart sections
  document.querySelectorAll('.stale-banner').forEach(b => b.style.display = 'flex');
}

function markParamsClean() {
  const btn = document.getElementById('runBtn');
  if (btn) {
    btn.classList.remove('dirty');
    btn.title = '';
  }
  document.querySelectorAll('.stale-banner').forEach(b => b.style.display = 'none');
}

function resetParams() {
  cfg = {...DEFAULTS, ...backendDefaults};
  buildParamForms();
  markParamsDirty();
}

// ════════════════════════════════════════════════════════════════════
//  NAVIGATION
// ════════════════════════════════════════════════════════════════════

// ════════════════════════════════════════════════════════════════════
//  EQUIPMENT ROI JUSTIFICATION
// ════════════════════════════════════════════════════════════════════
let equipROIChartPayback = null;
let equipROIChartBenefit = null;

// Equipment catalogue — cost formulae reference cfg / herd size
// annualBenefitFn(totals, simYears, cfg) → $/year
const EQUIPMENT_CATALOGUE = [
  {
    id: 'biodigester',
    loop: 'L3',
    loopClass: 'equip-l3',
    icon: '',
    name: 'Anaerobic Biodigester',
    desc: 'Processes the liquid manure fraction into biogas + digestate. Core of the energy loop — feeds the CHP engine. Produces digestate fertilizer (N+P) and eliminates liquid manure disposal costs. The solid fraction is handled separately by the Manure Separator (L1).',
    // Realistic: $500-800/cow for farm-scale AD vessel, mixing, gas storage
    capitalFn: (n) => n * 700,
    annualBenefitFn: (totals, simYears, cfg) => {
      // Digestate N fertilizer: use actual totals.digestate from simulation
      // (liquid × digestate_kg_per_kg_manure_to_digester)
      const digestate_kg   = totals.digestate / simYears;
      const digestateNVal  = digestate_kg * 0.005 * 1.20;   // 0.5% N @ $1.20/kg N
      const digestatePVal  = digestate_kg * 0.002 * 2.50;   // 0.2% P @ $2.50/kg P
      // Manure disposal saving: $3/tonne liquid manure processed
      const liquid_kg      = totals.biogasM3 / simYears / (cfg.biogas_m3_per_kg_manure_to_digester || 0.025);
      const disposalSaving = (liquid_kg / 1000) * 3.0;
      // Carbon credits: biogas methane displacement $30/tonne CO2e
      const carbonVal      = (totals.biogasM3 / simYears * 1.5) / 1000 * 30.0;
      // NOTE: compost revenue is NOT included here — that belongs entirely to the
      // Manure Separator card (L1) which owns the solid fraction.
      return digestateNVal + digestatePVal + disposalSaving + carbonVal;
    },
    metrics: (totals, simYears, cfg) => {
      const digestate_kg = totals.digestate / simYears;
      const liquid_kg    = totals.biogasM3 / simYears / (cfg.biogas_m3_per_kg_manure_to_digester || 0.025);
      return [
        { label: 'Biogas Produced/yr',          val: () => (totals.biogasM3/simYears).toLocaleString('en',{maximumFractionDigits:0})+' m³ (→ feeds CHP)' },
        { label: 'Avg Biogas Output',            val: () => (totals.biogasM3/simYears/365).toFixed(1)+' m³/day' },
        { label: 'Digestate N+P Value/yr',       val: () => '$'+((digestate_kg*0.005*1.20)+(digestate_kg*0.002*2.50)).toLocaleString('en',{maximumFractionDigits:0}) },
        { label: 'Digestate Produced/day',       val: () => (digestate_kg/365).toFixed(0)+' kg/day (liquid frac)' },
        { label: 'Manure Disposal Saved/yr',     val: () => '$'+(liquid_kg/1000*3).toLocaleString('en',{maximumFractionDigits:0}) },
        { label: 'Carbon Credits/yr',            val: () => '$'+(totals.biogasM3/simYears*1.5/1000*30).toLocaleString('en',{maximumFractionDigits:0}) },
      ];
    },
    verdict: (roi) => roi > 80 ? 'good' : roi > 20 ? 'warn' : 'bad',
    verdictLabel: (pb) => pb <= 6 ? `Excellent: ${pb.toFixed(1)}-yr payback — foundation of the bioeconomy loop` : pb <= 12 ? `Strong: ${pb.toFixed(1)}-yr payback, 20-yr design life` : `Good: ${pb.toFixed(1)} yrs — carbon incentives accelerate recovery`,
  },
  {
    id: 'chp',
    loop: 'L3',
    loopClass: 'equip-l3',
    icon: '',
    name: 'Biogas CHP Engine',
    desc: 'Combined Heat & Power engine converts biogas from the digester into on-farm electricity (~44% efficiency) and usable heat (~31% efficiency). Eliminates grid electricity bills and replaces natural gas for heating.',
    // Realistic: $2,500–4,000/kWe installed for farm-scale gas CHP
    capitalFn: (n) => {
      const dailyBiogas = n * 55 * 0.65 * 0.025; // m³/day from manure
      const kWe = dailyBiogas * 2.0 / 24;         // electrical capacity
      return Math.max(50000, kWe * 3500) * 1.15;  // $3,500/kWe + 15% install
    },
    annualBenefitFn: (totals, simYears, cfg) => {
      // Use configured electricity & heat prices — stays consistent with simulation revenue
      const elecPrice      = cfg.electricity_price_currency_per_kWh || 0.16;
      const heatPrice      = cfg.heat_value_currency_per_kWh || 0.06;
      const elecAvoided    = (totals.elec   / simYears) * elecPrice;
      // Heat: replaces natural gas at configured heat value
      const heatAvoided    = (totals.heat   / simYears) * heatPrice;
      // Demand charge savings (~25% of electricity rate for peak demand reduction)
      const demandSaving   = (totals.elec   / simYears) * elecPrice * 0.25;
      // Grid CO2e avoided carbon credits ($30/tonne)
      const carbonVal      = (totals.avoidedGrid / simYears) / 1000 * 30.0;
      // Energy independence premium (5% of avoided electricity)
      const energySecurity = elecAvoided * 0.05;
      return elecAvoided + heatAvoided + demandSaving + carbonVal + energySecurity;
    },
    metrics: (totals, simYears, cfg) => {
      const kWe = (totals.elec/simYears/365/24).toFixed(2);
      return [
        { label: 'Electricity Generated/yr',     val: () => (totals.elec/simYears).toLocaleString('en',{maximumFractionDigits:0})+' kWh' },
        { label: 'Heat Generated/yr',            val: () => (totals.heat/simYears).toLocaleString('en',{maximumFractionDigits:0})+' kWh thermal' },
        { label: 'Avg Electrical Capacity',      val: () => kWe+' kWe (continuous)' },
        { label: 'Avoided Grid Cost/yr',         val: () => '$'+((totals.elec/simYears)*(activeFarmType==='conventional'?(cfg.electricity_price_currency_per_kWh||0.16):0.18)).toLocaleString('en',{maximumFractionDigits:0}) },
        { label: 'Heat Value/yr (gas displace)', val: () => '$'+((totals.heat/simYears)*0.06).toLocaleString('en',{maximumFractionDigits:0}) },
        { label: 'Grid CO₂e Avoided/yr',         val: () => (totals.avoidedGrid/simYears).toFixed(0)+' kg CO₂e' },
        { label: 'Carbon Credits/yr',            val: () => '$'+(totals.avoidedGrid/simYears/1000*30).toLocaleString('en',{maximumFractionDigits:0}) },
        { label: 'Combined Efficiency',          val: () => '~75% (44% elec + 31% thermal)' },
      ];
    },
    verdict: (roi) => roi > 60 ? 'good' : roi > 15 ? 'warn' : 'bad',
    verdictLabel: (pb) => pb <= 4 ? `Exceptional: ${pb.toFixed(1)}-yr payback — on-farm energy self-sufficiency` : pb <= 8 ? `Excellent: ${pb.toFixed(1)}-yr payback, 15–20yr engine life` : `Strong: ${pb.toFixed(1)} yrs — pairs with digester for full biogas value`,
  },
  {
    id: 'separator',
    loop: 'L1',
    loopClass: 'equip-l1',
    icon: '',
    name: 'Manure Separator',
    desc: 'Mechanically separates manure into solid and liquid fractions. The solid fraction yields compost revenue and N/P/K fertilizer recovery. The liquid fraction feeds the Anaerobic Biodigester (L3). Enabling this loop (L1) represents the decision to capture value from the solid stream.',
    capitalFn: (n) => Math.max(15000, n * 180),
    annualBenefitFn: (totals, simYears, cfg) => {
      const compostRev  = totals.compostRev / simYears;
      const nutrientVal = (totals.nRecTotal + totals.pRecTotal + totals.kRecTotal) / simYears * 0.80;
      const feedOffset  = (totals.feedCost  / simYears) * 0.08;
      const orgFertVal  = (totals.organicFert / simYears) * 0.015;
      return compostRev + nutrientVal + feedOffset + orgFertVal;
    },
    metrics: (totals, simYears, cfg) => [
      { label: 'Compost Revenue/yr',          val: () => '$'+(totals.compostRev/simYears).toLocaleString('en',{maximumFractionDigits:0}) },
      { label: 'N+P+K Fertilizer Value/yr',   val: () => '$'+((totals.nRecTotal+totals.pRecTotal+totals.kRecTotal)/simYears*0.80).toLocaleString('en',{maximumFractionDigits:0}) },
      { label: 'Feed Cost Offset/yr (organic subst.)', val: () => '$'+((totals.feedCost/simYears)*0.08).toLocaleString('en',{maximumFractionDigits:0}) },
      { label: 'Compost Produced',            val: () => (totals.compost/simYears/365).toFixed(1)+' kg/day' },
      { label: 'N/P/K Recovered/yr',          val: () => ((totals.nRecTotal+totals.pRecTotal+totals.kRecTotal)/simYears).toFixed(0)+' kg/yr' },
    ],
    verdict: (roi) => roi > 150 ? 'good' : roi > 40 ? 'warn' : 'bad',
    verdictLabel: (pb) => pb <= 2 ? `Exceptional: ${pb.toFixed(1)}-yr payback — highest ROI in the system` : pb <= 8 ? `Excellent: ${pb.toFixed(1)}-yr payback — immediate revenue from compost` : `Good: ${pb.toFixed(1)}-yr payback`,
  },
  {
    id: 'solar',
    loop: 'L3',
    loopClass: 'equip-l3',
    icon: '',
    name: 'Solar PV Array',
    desc: 'On-farm solar electricity supplements CHP output during daylight hours. Valued at avoided retail electricity cost, not export tariff.',
    capitalFn: (n) => Math.max(30000, n * 350),
    annualBenefitFn: (totals, simYears, cfg) => {
      // Use configured electricity price — consistent with simulation
      const elecPrice      = cfg.electricity_price_currency_per_kWh || 0.16;
      const avoidedRetail  = (totals.solar / simYears) * elecPrice;
      const carbonVal      = (totals.solar / simYears) * (cfg.grid_avoided_kg_co2e_per_kWh || 0.40) / 1000 * 30.0;
      const energySecPrem  = avoidedRetail * 0.05;
      return avoidedRetail + carbonVal + energySecPrem;
    },
    metrics: (totals, simYears, cfg) => [
      { label: 'Solar kWh Generated/yr',       val: () => (totals.solar/simYears).toLocaleString('en',{maximumFractionDigits:0})+' kWh' },
      { label: 'Avoided Grid Cost/yr',         val: () => '$'+((totals.solar/simYears)*(activeFarmType==='conventional'?(cfg.electricity_price_currency_per_kWh||0.16):0.18)).toLocaleString('en',{maximumFractionDigits:0}) },
      { label: 'Carbon Credits/yr',            val: () => '$'+((totals.solar/simYears)*(cfg.grid_avoided_kg_co2e_per_kWh||0.40)/1000*30).toLocaleString('en',{maximumFractionDigits:0}) },
      { label: 'Grid CO₂e Avoided/yr',         val: () => ((totals.solar/simYears)*(cfg.grid_avoided_kg_co2e_per_kWh||0.40)).toFixed(0)+' kg' },
      { label: 'Avg Solar Output/day',          val: () => (totals.solar/simYears/365).toFixed(1)+' kWh/day' },
    ],
    verdict: (roi) => roi > 50 ? 'good' : roi > 10 ? 'warn' : 'bad',
    verdictLabel: (pb) => pb <= 8 ? `Excellent: ${pb.toFixed(1)}-yr payback with 25-yr panel life` : pb <= 15 ? `Good: ${pb.toFixed(1)}-yr payback — industry standard for farm solar` : `Fair: ${pb.toFixed(1)} yrs — increase panel area or check tariff incentives`,
  },

  {
    id: 'whey',
    loop: 'L4',
    loopClass: 'equip-l4',
    icon: '',
    name: 'Whey Processing Unit',
    desc: 'Converts whey and dairy byproducts into animal feed, reducing purchased feed costs and closing the dairy value loop.',
    capitalFn: (n) => Math.max(40000, n * 280),
    annualBenefitFn: (totals, simYears, cfg) => {
      // feedReturn = (wheyToFeed + wasteToFeed) × byproduct_substitution_kg_per_kg
      // This is the net feed demand reduction — the one correct metric to value.
      // wheyToFeed/wasteToFeed raw volumes are NOT added separately (that would double-count)
      // and byproductFeedCredit (the sim's cumulative queue total) is NOT added (already captured here).
      const feedCost       = cfg.feed_cost_per_kg || 0.22;
      const feedReturnVal  = (totals.feedReturn  / simYears) * feedCost;
      // Waste disposal cost avoided: $40/tonne of whey + waste milk diverted from disposal
      const wasteAvoided   = (totals.wheyToFeed + totals.wasteToFeed) / simYears / 1000 * 40.0;
      // Functional food / bioactive value premium on high-value whey fraction
      const functionalPrem = (totals.whey / simYears) * (cfg.fraction_whey_to_functional_foods_bioproducts || 0.5) * 0.08;
      return feedReturnVal + wasteAvoided + functionalPrem;
    },
    metrics: (totals, simYears, cfg) => activeFarmType === 'conventional' ? [
      { label: 'Feed Return Value/yr',         val: () => '$'+((totals.feedReturn/simYears)*(cfg.feed_cost_per_kg||0.22)).toLocaleString('en',{maximumFractionDigits:0}) },
      { label: 'Whey to Feed/yr',              val: () => (totals.wheyToFeed/simYears).toLocaleString('en',{maximumFractionDigits:0})+' L' },
      { label: 'Waste Milk to Feed/yr',        val: () => (totals.wasteToFeed/simYears).toLocaleString('en',{maximumFractionDigits:0})+' L' },
      { label: 'Waste Disposal Saved/yr',      val: () => '$'+((totals.wheyToFeed+totals.wasteToFeed)/simYears/1000*40).toLocaleString('en',{maximumFractionDigits:0}) },
      { label: 'Whey Processed/day',           val: () => (totals.whey/simYears/365).toFixed(1)+' L/day' },
    ] : [
      { label: 'Feed Replaced from Whey/yr',   val: () => '$'+((totals.wheyToFeed/simYears)*(cfg.feed_cost_per_kg||0.22)).toLocaleString('en',{maximumFractionDigits:0}) },
      { label: 'Feed Replaced from Waste/yr',  val: () => '$'+((totals.wasteToFeed/simYears)*(cfg.feed_cost_per_kg||0.22)).toLocaleString('en',{maximumFractionDigits:0}) },
      { label: 'Byproduct Feed Credit/yr',     val: () => '$'+(totals.byproductFeedCredit/simYears).toLocaleString('en',{maximumFractionDigits:0}) },
      { label: 'Waste Disposal Saved/yr',      val: () => '$'+((totals.wheyToFeed+totals.wasteToFeed)/simYears/1000*40).toLocaleString('en',{maximumFractionDigits:0}) },
      { label: 'Whey Processed/day',           val: () => (totals.wheyToFeed/simYears/365).toFixed(1)+' kg/day' },
    ],
    verdict: (roi) => roi > 60 ? 'good' : roi > 15 ? 'warn' : 'bad',
    verdictLabel: (pb) => pb <= 5 ? `Strong: ${pb.toFixed(1)}-yr payback from direct feed cost reduction` : pb <= 12 ? `Good: ${pb.toFixed(1)}-yr payback — premium whey products further improve this` : `Fair: ${pb.toFixed(1)} yrs — consider smaller unit or functional food upgrade`,
  },

  {
    id: 'wastewater',
    loop: 'L2',
    loopClass: 'equip-l2',
    icon: '',
    name: 'Water Recycling System',
    desc: 'Recycles dairy wastewater for crop irrigation, recovers dissolved N/P/K nutrients, and reduces municipal water purchase.',
    capitalFn: (n) => Math.max(25000, n * 220),
    annualBenefitFn: (totals, simYears, cfg) => {
      const waterIrrigVal  = (totals.recycledIrrig / simYears) * (cfg.water_cost_per_L || 0.0008) * 2.5;
      const freshAvoided   = (totals.freshOffset   / simYears) * (cfg.water_cost_per_L || 0.0008);
      const treatmentSaved = (totals.recycledIrrig / simYears) / 1000 * 0.50;
      const nutrientVal    = (totals.wN + totals.wP + totals.wK) / simYears * 0.80;
      return waterIrrigVal + freshAvoided + treatmentSaved + nutrientVal;
    },
    metrics: (totals, simYears, cfg) => [
      { label: 'Irrigation Water Value/yr',    val: () => '$'+((totals.recycledIrrig/simYears)*(cfg.water_cost_per_L||0.0008)*2.5).toLocaleString('en',{maximumFractionDigits:0}) },
      { label: 'Fresh Water Avoided/yr',       val: () => (totals.freshOffset/simYears).toLocaleString('en',{maximumFractionDigits:0})+' L' },
      { label: 'Treatment Cost Saved/yr',      val: () => '$'+((totals.recycledIrrig/simYears)/1000*0.50).toLocaleString('en',{maximumFractionDigits:0}) },
      { label: 'Nutrient Recovery Value/yr',   val: () => '$'+((totals.wN+totals.wP+totals.wK)/simYears*0.80).toLocaleString('en',{maximumFractionDigits:0}) },
      { label: 'Water Recycled/day',           val: () => (totals.recycledIrrig/simYears/365).toFixed(0)+' L/day' },
    ],
    verdict: (roi) => roi > 60 ? 'good' : roi > 10 ? 'warn' : 'bad',
    verdictLabel: (pb) => pb <= 6 ? `Strong: ${pb.toFixed(1)}-yr payback — excellent in water-stressed regions` : pb <= 12 ? `Good: ${pb.toFixed(1)}-yr payback — justified by water scarcity value` : `Long-term: ${pb.toFixed(1)} yrs — strong ESG case for water security`,
  },  {
    id: 'smartsensors',
    loop: 'L1',
    loopClass: 'equip-l1',
    icon: '',
    name: 'Smart Feed & Health Sensors',
    desc: 'Precision feeding and real-time health monitoring — improves milk yield ~3% and reduces feed waste ~5%. Highest ROI per dollar invested.',
    capitalFn: (n) => Math.max(20000, n * 120),
    annualBenefitFn: (totals, simYears, cfg) => {
      if (activeFarmType === 'conventional') {
        const milkFactor = (cfg.smart_tech_milk_yield_factor || 1) - 1;
        const feedFactor = 1 - (cfg.smart_tech_feed_efficiency_factor || 1);
        const milkUplift     = (totals.milkRev  / simYears) * Math.max(0, milkFactor);
        const feedSaving     = (totals.feedCost / simYears) * Math.max(0, feedFactor);
        const vetSaving      = (cfg.number_of_cows || 100) * 50;
        const cullingBenefit = (totals.milkRev  / simYears) * 0.015;
        return milkUplift + feedSaving + vetSaving + cullingBenefit;
      }
      const milkUplift     = (totals.milkRev  / simYears) * 0.03;
      const feedSaving     = (totals.feedCost / simYears) * 0.05;
      const vetSaving      = (cfg.number_of_cows || 100) * 50;
      const cullingBenefit = (totals.milkRev  / simYears) * 0.015;
      return milkUplift + feedSaving + vetSaving + cullingBenefit;
    },
    metrics: (totals, simYears, cfg) => {
      if (activeFarmType === 'conventional') {
        const milkFactor = (cfg.smart_tech_milk_yield_factor || 1) - 1;
        const feedFactor = 1 - (cfg.smart_tech_feed_efficiency_factor || 1);
        return [
          { label: 'Milk Uplift/yr',               val: () => '$'+((totals.milkRev/simYears)*Math.max(0,milkFactor)).toLocaleString('en',{maximumFractionDigits:0}) },
          { label: 'Feed Savings/yr',              val: () => '$'+((totals.feedCost/simYears)*Math.max(0,feedFactor)).toLocaleString('en',{maximumFractionDigits:0}) },
          { label: 'Vet Cost Savings/yr',          val: () => '$'+((cfg.number_of_cows||100)*50).toLocaleString('en',{maximumFractionDigits:0}) },
          { label: 'Reduced Culling Benefit/yr',   val: () => '$'+((totals.milkRev/simYears)*0.015).toLocaleString('en',{maximumFractionDigits:0}) },
          { label: 'Milk Revenue (simulated)',     val: () => '$'+(totals.milkRev/simYears).toLocaleString('en',{maximumFractionDigits:0})+'/yr' },
        ];
      }
      return [
        { label: 'Milk Uplift 3%/yr',           val: () => '$'+((totals.milkRev/simYears)*0.03).toLocaleString('en',{maximumFractionDigits:0}) },
        { label: 'Feed Savings 5%/yr',           val: () => '$'+((totals.feedCost/simYears)*0.05).toLocaleString('en',{maximumFractionDigits:0}) },
        { label: 'Vet Cost Savings/yr',          val: () => '$'+((cfg.number_of_cows||100)*50).toLocaleString('en',{maximumFractionDigits:0}) },
        { label: 'Reduced Culling Benefit/yr',   val: () => '$'+((totals.milkRev/simYears)*0.015).toLocaleString('en',{maximumFractionDigits:0}) },
        { label: 'Milk Revenue (simulated)',     val: () => '$'+(totals.milkRev/simYears).toLocaleString('en',{maximumFractionDigits:0})+'/yr' },
      ];
    },
    verdict: (roi) => roi > 150 ? 'good' : roi > 50 ? 'warn' : 'bad',
    verdictLabel: (pb) => pb <= 3 ? `Exceptional: ${pb.toFixed(1)}-yr payback — best ROI/$ in entire portfolio` : pb <= 6 ? `Excellent: ${pb.toFixed(1)}-yr payback — low cost, high-impact precision tech` : `Strong: ${pb.toFixed(1)} yrs — literature confirms 200–400% lifetime ROI`,
  },
  {
    id: 'beefcross', loop: 'L4', loopClass: 'equip-l4', icon: '',
    name: 'Beef-on-Dairy Program',
    desc: 'Beef-breed semen on 45% of cows. Bull calves sold as premium weaners ($420/head). Fully activated on Beef-on-Dairy farm type only.',
    capitalFn: (n) => Math.max(3000, n * 35),
    annualBenefitFn: (totals, simYears, cfg) => {
      const p = FARM_PRESETS[activeFarmType];
      if (!p || !p.beefOnDairy) return 0;
      const calves = (cfg.number_of_cows || 100) * (p.beefCrossBreedFraction || 0.45) * 0.5;
      return calves * (p.beefCalfValuePerHead || 420);
    },
    metrics: (totals, simYears, cfg) => {
      const p     = FARM_PRESETS[activeFarmType];
      const frac  = (p && p.beefCrossBreedFraction) || 0.45;
      const val   = (p && p.beefCalfValuePerHead)   || 420;
      const calves = (cfg.number_of_cows || 100) * frac * 0.5;
      return [
        { label: 'Cross-breed fraction', val: () => Math.round(frac * 100) + '% of herd' },
        { label: 'Bull calves sold/yr',  val: () => calves.toFixed(0) + ' head' },
        { label: 'Value per weaner',     val: () => '$' + val },
        { label: 'Gross calf revenue/yr',val: () => '$' + (calves * val).toLocaleString('en', {maximumFractionDigits:0}) },
        { label: 'Active on this farm',  val: () => (p && p.beefOnDairy) ? ' Beef-on-Dairy' : ' Switch to Beef-on-Dairy farm type' },
      ];
    },
    verdict:      (roi) => roi > 200 ? 'good' : roi > 50 ? 'warn' : 'bad',
    verdictLabel: (pb)  => pb < 1 ? 'Exceptional: <1 yr payback — pure revenue uplift, near-zero CapEx' : `Good: ${pb.toFixed(1)}-yr payback`,
  }

];

function getEquipROIInputs() {
  return {
    discRate:      Math.max(0, parseFloat(document.getElementById('roiDiscountRate')?.value) || 7) / 100,
    lifespan:      Math.max(1, Math.min(40, parseInt(document.getElementById('roiLifespan')?.value) || 15)),
    installPct:    Math.max(0, parseFloat(document.getElementById('roiInstallPct')?.value) || 15) / 100,
    maintPct:      Math.max(0, parseFloat(document.getElementById('roiMaintenancePct')?.value) || 2) / 100,
  };
}

function fmtMoney(v) {
  const a = Math.abs(v), s = v < 0 ? '-' : '';
  if (a >= 1e6) return s + '$' + (a/1e6).toFixed(2) + 'M';
  if (a >= 1e3) return s + '$' + (a/1e3).toFixed(1) + 'k';
  return s + '$' + a.toFixed(0);
}

function calcNPV(annualNet, capital, discRate, years) {
  let npv = -capital;
  for (let t = 1; t <= years; t++) npv += annualNet / Math.pow(1 + discRate, t);
  return npv;
}

function buildEquipROI(res) {
  if (!res) return;

  document.getElementById('roiEquipEmpty').style.display = 'none';
  document.getElementById('roiEquipBody').style.display  = 'block';

  const simCfg = (activeFarmType === 'conventional' && res.cfg) ? res.cfg : cfg;
  const { discRate, lifespan, installPct, maintPct } = getEquipROIInputs();
  const simYears = simCfg.simulation_years || 5;
  const n = simCfg.number_of_cows || 100;
  const totals = res.totals;

  const isDark    = document.documentElement.getAttribute('data-theme') === 'dark';
  const gridColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)';
  const textColor = isDark ? '#797876' : '#7a7974';

  // Compute each equipment
  const results = EQUIPMENT_CATALOGUE.map(eq => {
    const baseCapital    = eq.capitalFn(n);
    const totalCapital   = baseCapital * (1 + installPct);
    const annualBenefit  = activeFarmType === 'conventional'
      ? eq.annualBenefitFn(totals, simYears, simCfg)
      : eq.annualBenefitFn(totals, simYears, cfg);
    const annualMaint    = totalCapital * maintPct;
    const annualNet      = annualBenefit - annualMaint;
    const payback        = annualNet > 0 ? totalCapital / annualNet : 999;
    const npv            = calcNPV(annualNet, totalCapital, discRate, lifespan);
    const lifetimeBenefit = annualNet * lifespan;
    const roi            = ((lifetimeBenefit - totalCapital) / Math.max(1, totalCapital)) * 100;
    return { eq, baseCapital, totalCapital, annualBenefit, annualMaint, annualNet, payback, npv, roi, lifetimeBenefit };
  });

  // ── Portfolio summary ──
  const totalCapex   = results.reduce((a, r) => a + r.totalCapital, 0);
  const totalBenefit = results.reduce((a, r) => a + r.annualNet, 0);
  const portfolioNPV = results.reduce((a, r) => a + r.npv, 0);
  const blendedPB    = totalBenefit > 0 ? totalCapex / totalBenefit : 999;

  document.getElementById('roiTotalCapex').textContent    = fmtMoney(totalCapex);
  document.getElementById('roiTotalBenefit').textContent  = fmtMoney(totalBenefit) + '/yr';
  document.getElementById('roiBlendedPayback').textContent= blendedPB < 999 ? blendedPB.toFixed(1) + ' yrs' : 'N/A';
  document.getElementById('roiPortfolioNPV').textContent  = fmtMoney(portfolioNPV);
  document.getElementById('roiNPVSub').textContent        = `at ${(discRate*100).toFixed(1)}% · ${lifespan}yr`;
  document.getElementById('roiPortfolioDesc').textContent = `${results.length} equipment items · ${simYears}-year simulation · herd of ${n}`;

  // ── Portfolio Payback Chart ──
  const years = Array.from({length: lifespan + 1}, (_, i) => i);
  const paybackDatasets = results.map(r => ({
    label: r.eq.name,
    data: years.map(y => -r.totalCapital + r.annualNet * y),
    borderWidth: 2,
    pointRadius: 0,
    fill: false,
    tension: 0.3,
  }));
  const colors = ['#01696f','#437a22','#006494','#da7101','#7a39bb','#d19900'];
  paybackDatasets.forEach((ds, i) => {
    ds.borderColor = colors[i % colors.length];
    ds.backgroundColor = colors[i % colors.length] + '15';
  });

  if (equipROIChartPayback) equipROIChartPayback.destroy();
  equipROIChartPayback = new Chart(document.getElementById('chartEquipPayback'), {
    type: 'line',
    data: { labels: years.map(y => 'Y' + y), datasets: [
      ...paybackDatasets,
      { label: 'Break-even', data: years.map(() => 0), borderColor: isDark ? 'rgba(255,255,255,.2)' : 'rgba(0,0,0,.15)',
        borderWidth: 1, borderDash: [4,4], pointRadius: 0, fill: false }
    ]},
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { labels: { color: textColor, font: { size: 10 }, boxWidth: 10, padding: 8 } },
        tooltip: { callbacks: { label: ctx => ctx.dataset.label === 'Break-even' ? null : ` ${ctx.dataset.label}: ${fmtMoney(ctx.raw)}` } }
      },
      scales: {
        x: { grid: { color: gridColor }, ticks: { color: textColor, font: { size: 10 }, maxTicksLimit: 8 } },
        y: { grid: { color: gridColor }, ticks: { color: textColor, font: { size: 10 }, callback: v => fmtMoney(v) } }
      }
    }
  });

  // ── Benefit Bar Chart ──
  if (equipROIChartBenefit) equipROIChartBenefit.destroy();
  equipROIChartBenefit = new Chart(document.getElementById('chartEquipBenefit'), {
    type: 'bar',
    data: {
      labels: results.map(r => r.eq.name.split(' ').slice(0, 2).join(' ')),
      datasets: [
        { label: 'Annual Benefit', data: results.map(r => r.annualBenefit),
          backgroundColor: colors.map(c => c + 'bb'), borderRadius: 5, borderSkipped: false },
        { label: 'Annual Maint.', data: results.map(r => -r.annualMaint),
          backgroundColor: results.map(() => (isDark ? 'rgba(200,80,80,.5)' : 'rgba(161,44,123,.35)')),
          borderRadius: 5, borderSkipped: false }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: textColor, font: { size: 10 }, boxWidth: 10 } },
        tooltip: { callbacks: { label: ctx => ` ${ctx.dataset.label}: ${fmtMoney(ctx.raw)}` } }
      },
      scales: {
        x: { grid: { color: gridColor }, ticks: { color: textColor, font: { size: 10 }, maxRotation: 30 } },
        y: { grid: { color: gridColor }, stacked: false, ticks: { color: textColor, font: { size: 10 }, callback: v => fmtMoney(v) } }
      }
    }
  });

  // ── Equipment Cards ──
  const grid = document.getElementById('equipRoiGrid');
  grid.innerHTML = '';

  results.forEach((r, idx) => {
    const { eq, totalCapital, annualBenefit, annualNet, payback, npv, roi } = r;
    const verdictClass = eq.verdict(roi);
    const verdictText  = eq.verdictLabel(payback);
    const pbPct        = Math.min(100, (lifespan / Math.max(0.01, payback)) * 100);
    const annROI       = (annualNet / Math.max(1, totalCapital)) * 100;

    const metrics = activeFarmType === 'conventional'
      ? eq.metrics(totals, simYears, simCfg)
      : eq.metrics(totals, simYears, cfg);

    const card = document.createElement('div');
    card.className = `equip-card ${eq.loopClass}`;
    card.style.animationDelay = (idx * 0.05) + 's';
    card.innerHTML = `
      <div class="equip-card-header">
        <div class="equip-icon">${eq.icon}</div>
        <div class="equip-meta">
          <div class="equip-loop-badge">${eq.loop} — ${eq.id === 'smartsensors' ? 'Precision Tech' : eq.loop === 'L3' ? 'Energy Loop' : eq.loop === 'L2' ? 'Water Loop' : eq.loop === 'L4' ? 'Dairy Loop' : 'Nutrient Loop'}</div>
          <div class="equip-name">${eq.name}</div>
          <div class="equip-desc">${eq.desc}</div>
        </div>
      </div>
      <div class="equip-accent-bar"></div>
      <div class="equip-kpi-row">
        <div class="equip-kpi">
          <div class="equip-kpi-label">Total CapEx</div>
          <div class="equip-kpi-val">${fmtMoney(totalCapital)}</div>
        </div>
        <div class="equip-kpi">
          <div class="equip-kpi-label">Annual Net</div>
          <div class="equip-kpi-val ${annualNet >= 0 ? 'pos' : 'neg'}">${fmtMoney(annualNet)}</div>
        </div>
        <div class="equip-kpi">
          <div class="equip-kpi-label">${lifespan}yr NPV</div>
          <div class="equip-kpi-val ${npv >= 0 ? 'pos' : 'neg'}">${fmtMoney(npv)}</div>
        </div>
      </div>
      <div class="equip-metrics">
        ${metrics.map(m => `
          <div class="equip-metric-row">
            <span class="equip-metric-label">${m.label}</span>
            <span class="equip-metric-val">${m.val()}</span>
          </div>`).join('')}
        <div class="equip-metric-row">
          <span class="equip-metric-label">Annual ROI</span>
          <span class="equip-metric-val" style="color:${annROI >= 0 ? 'var(--color-success)' : 'var(--color-error)'}">${annROI >= 0 ? '+' : ''}${annROI.toFixed(1)}%</span>
        </div>
        <div class="equip-metric-row">
          <span class="equip-metric-label">Lifetime ROI (${lifespan}yr)</span>
          <span class="equip-metric-val" style="color:${roi >= 0 ? 'var(--color-success)' : 'var(--color-error)'}">${roi >= 0 ? '+' : ''}${roi.toFixed(0)}%</span>
        </div>
      </div>
      <div class="equip-payback-wrap">
        <div class="equip-pb-labels">
          <span>Payback: ${payback < 999 ? payback.toFixed(1) + ' yrs' : '> lifespan'}</span>
          <span>${lifespan}yr lifespan</span>
        </div>
        <div class="equip-pb-track">
          <div class="equip-pb-fill" id="pb-fill-${eq.id}" style="width:0%"></div>
        </div>
      </div>
      <div class="equip-verdict ${verdictClass}">
        ${verdictClass === 'good' ? '' : verdictClass === 'warn' ? '' : ''} ${verdictText}
      </div>`;
    grid.appendChild(card);

    // Animate payback bar
    requestAnimationFrame(() => {
      setTimeout(() => {
        const fill = document.getElementById('pb-fill-' + eq.id);
        if (fill) fill.style.width = pbPct.toFixed(1) + '%';
      }, idx * 60 + 100);
    });
  });

  // Resize charts
  requestAnimationFrame(() => {
    [equipROIChartPayback, equipROIChartBenefit].forEach(c => { try { c?.resize(); } catch(e){} });
  });
}

function recalcEquipROI() {
  if (lastResult) buildEquipROI(lastResult);
}

function navigate(id) {
  document.querySelectorAll('.page-section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('section-'+id)?.classList.add('active');
  document.getElementById('nav-'+id)?.classList.add('active');
  if (id === 'formulas') initFormulaPage();
  // Re-render charts after the section is visible so Chart.js can measure dimensions
  requestAnimationFrame(() => {
    if (id === 'charts'   && lastResult) buildAllCharts(lastResult);
    if (id === 'loops'    && lastResult) buildLoops(lastResult);
    if (id === 'overview' && lastResult) { buildOverviewCharts(lastResult); updateRevSummary(lastResult); }
    if (id === 'roi'      && lastResult) buildEquipROI(lastResult);
    // Resize ALL existing chart instances in case they were drawn while hidden
    requestAnimationFrame(() => {
      Object.values(chartInstances).forEach(c => { try { c.resize(); } catch(e){} });
    });
  });
}

// ════════════════════════════════════════════════════════════════════
//  COW RANKING
// ══════════════════════════════════════════════════════════════════
let rankData = [];
let rankSortKey = 'rank';
let rankSortAsc = true;
let rankFilterTier = 'all';

function tierLabel(t) {
  return {elite:' Elite', good:' Good', avg:' Average', poor:' Poor'}[t]||t;
}

function renderRankTable() {
  let data = rankFilterTier==='all' ? [...rankData]
           : rankData.filter(c=>c.tier===rankFilterTier);
  data.sort((a,b) => {
    const av=a[rankSortKey], bv=b[rankSortKey];
    if (typeof av==='string') return rankSortAsc ? av.localeCompare(bv) : bv.localeCompare(av);
    return rankSortAsc ? av-bv : bv-av;
  });
  document.querySelectorAll('.rank-table th').forEach(th => {
    th.classList.remove('sorted');
    const ic=th.querySelector('.sort-icon'); if(ic) ic.textContent='⇅';
  });
  const ath = document.getElementById('th-'+rankSortKey);
  if (ath) {
    ath.classList.add('sorted');
    const ic=ath.querySelector('.sort-icon'); if(ic) ic.textContent=rankSortAsc?'▲':'▼';
  }
  const tbody = document.getElementById('rankTbody');
  tbody.innerHTML = data.map(c => {
    const bc = c.rank===1?'rank-1':c.rank===2?'rank-2':c.rank===3?'rank-3':'rank-other';
    const barCls = c.efficiency>=80 ? '' : c.efficiency>=60 ? 'avg' : 'poor';
    const fcrCol = c.tier==='elite'?'var(--color-primary)':c.tier==='poor'?'var(--color-error)':'var(--color-text)';
    return `<tr>
      <td><span class="rank-badge ${bc}">${c.rank}</span></td>
      <td style="font-weight:700;color:var(--color-text)" title="Model cow ID: ${c.modelId}">${c.id}</td>
      <td style="text-align:center;color:var(--color-text-muted)">${c.parity}</td>
      <td style="color:var(--color-text-muted)">${c.bw}</td>
      <td style="font-weight:700;color:var(--color-primary)">${c.milk.toFixed(2)}</td>
      <td style="color:var(--color-text)">${c.feed.toFixed(2)}</td>
      <td style="color:var(--color-text)">${c.water.toFixed(1)}</td>
      <td style="color:var(--color-text)">${c.manure.toFixed(2)}</td>
      <td style="font-weight:800;color:${fcrCol}">${c.fcr != null ? c.fcr.toFixed(3) : "—"}</td>
      <td style="color:var(--color-success);font-weight:600">$${c.milkRev.toFixed(2)}</td>
      <td style="color:var(--color-text-muted)">${c.ghg.toFixed(2)}</td>
      <td>
        <div class="eff-bar-wrap">
          <div class="eff-bar ${barCls}" style="width:${c.efficiency ?? 0}%"></div>
          <span style="font-size:var(--text-xs);color:var(--color-text-muted);min-width:32px">${c.efficiency != null ? c.efficiency + '%' : '—'}</span>
        </div>
      </td>
      <td><span class="tier-chip tier-${c.tier}">${tierLabel(c.tier)}</span></td>
    </tr>`;
  }).join('');
}

function sortRank(key) {
  if (rankSortKey===key) rankSortAsc=!rankSortAsc;
  else { rankSortKey=key; rankSortAsc=(key==='rank'||key==='fcr'); }
  renderRankTable();
}

function filterRank(tier, btn) {
  rankFilterTier=tier;
  document.querySelectorAll('.rank-filter-btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  renderRankTable();
}

function renderRankCharts() {
  const co = getChartColors();
  const fcrUnit = activeFarmType === 'conventional' ? 'kg/kg' : 'kg/L';
  destroyChart('chartRankScatter'); destroyChart('chartRankBar');
  const tc = { elite:co.primary, good:co.success, avg:co.gold, poor:co.error };
  const elS = document.getElementById('chartRankScatter');
  if (elS) {
    chartInstances['chartRankScatter'] = new Chart(elS, {
      type:'scatter',
      data:{ datasets:[{
        label:'Cows (color = tier)',
        data: rankData.filter(c=>c.fcr!==null).map(c=>({x:c.milk, y:c.fcr, label:c.id, tier:c.tier})),
        backgroundColor: rankData.filter(c=>c.fcr!==null).map(c=>tc[c.tier]+'cc'),
        borderColor: rankData.filter(c=>c.fcr!==null).map(c=>tc[c.tier]),
        borderWidth: 1,
        pointRadius: Math.max(3, Math.min(7, Math.round(120/rankData.length))),
        pointHoverRadius: 9,
      }]},
      options:{
        responsive: true, maintainAspectRatio: false,
        plugins:{
          legend:{display:true, labels:{color:co.tick, font:{size:11}, generateLabels:()=>
            Object.entries(tc).map(([tier,color])=>({text:tierLabel(tier), fillStyle:color+'cc', strokeStyle:color, lineWidth:1}))
          }},
          tooltip:{
            backgroundColor:co.bg, titleColor:co.text, bodyColor:co.tick, borderColor:co.grid, borderWidth:1,
            callbacks:{
              title: ctx => ctx[0].raw.label + ' · ' + tierLabel(ctx[0].raw.tier),
              label: ctx => `  Milk: ${ctx.raw.x.toFixed(2)} L/day  |  FCR: ${ctx.raw.y.toFixed(3)} ${fcrUnit}`
            }
          }
        },
        scales:{
          x:{
            title:{display:true, text:'Avg Milk (L/milking day)', color:co.tick, font:{size:11}},
            grid:{color:co.grid}, ticks:{color:co.tick, font:{size:10}}
          },
          y:{
            title:{display:true, text:`Feed Conversion Ratio (${fcrUnit})`, color:co.tick, font:{size:11}},
            grid:{color:co.grid}, ticks:{color:co.tick, font:{size:10}}
          }
        }
      }
    });
  }
  const top20 = [...rankData].sort((a,b)=>b.milkRev-a.milkRev).slice(0,20);
  const elB = document.getElementById('chartRankBar');
  if (elB) {
    chartInstances['chartRankBar'] = new Chart(elB, {
      type:'bar',
      data:{
        labels: top20.map(c => c.id),
        datasets:[{
          label:'Milk Revenue ($/milking day)',
          data: top20.map(c => parseFloat(c.milkRev.toFixed(2))),
          backgroundColor: top20.map(c => tc[c.tier]+'cc'),
          borderColor: top20.map(c => tc[c.tier]),
          borderWidth:1, borderRadius:4,
        }]
      },
      options:{
        responsive:true, maintainAspectRatio:false,
        plugins:{
          legend:{display:false},
          tooltip:{
            backgroundColor:co.bg, titleColor:co.text, bodyColor:co.tick, borderColor:co.grid, borderWidth:1,
            callbacks:{
              title: ctx => ctx[0].label + ' · ' + tierLabel(top20[ctx[0].dataIndex].tier),
              label: ctx => `  Revenue: $${ctx.raw.toFixed(2)}/day  |  FCR: ${top20[ctx.dataIndex].fcr.toFixed(3)}`
            }
          }
        },
        scales:{
          x:{grid:{color:co.grid}, ticks:{color:co.tick, font:{size:9}, maxRotation:0, autoSkip:true}},
          y:{
            grid:{color:co.grid}, ticks:{color:co.tick, font:{size:10}},
            title:{display:true, text:'Milk Revenue ($/day)', color:co.tick, font:{size:11}}
          }
        }
      }
    });
  }
}

//  THEME TOGGLE
// ════════════════════════════════════════════════════════════════════
(function(){
  const t = document.querySelector('[data-theme-toggle]');
  const r = document.documentElement;
  let d = matchMedia('(prefers-color-scheme:dark)').matches ? 'dark' : 'light';
  r.setAttribute('data-theme', d);
  t && t.addEventListener('click', () => {
    d = d==='dark'?'light':'dark';
    r.setAttribute('data-theme', d);
    t.setAttribute('aria-label','Switch to '+(d==='dark'?'light':'dark')+' mode');
    t.innerHTML = d==='dark'
      ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>'
      : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
    // refresh chart colors
    if (lastResult) {
      buildOverviewCharts(lastResult);
      if (document.getElementById('section-charts').classList.contains('active')) buildAllCharts(lastResult);
      if (document.getElementById('section-loops').classList.contains('active')) buildLoops(lastResult);
    }
  });
})();

// ════════════════════════════════════════════════════════════════════

async function apiPost(path, body) {
  const response = await fetch(path, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || 'Request failed');
  return payload;
}
function modelConfig() {
  return Object.fromEntries([...supportedParams].map(key => [key,cfg[key]]));
}
async function runSimulation() {
  const btn = document.getElementById('runBtn');
  btn.disabled = true; btn.classList.add('running'); setStatus('running');
  try {
    const res = await apiPost('/api/conventional/run', {cfg:modelConfig(), loops:defaultActiveLoops()});
    res.cfg = {...cfg,...res.cfg};
    lastResult = res;
    renderKPIs(res.avg); animateKPIs(); updateRevSummary(res);
    document.getElementById('overviewCharts').style.display='block';
    buildOverviewCharts(res); buildAllCharts(res); buildLoops(res);
    if (document.getElementById('section-roi').classList.contains('active')) buildEquipROI(res);
    document.getElementById('chartsEmpty').style.display='none';
    document.getElementById('chartsContent').style.display='flex';
    document.getElementById('loopsEmpty').style.display='none';
    document.getElementById('loopsContent').style.display='flex';
    document.getElementById('exportBtn').disabled=false;
    const details = res.modelDetails;
    document.getElementById('modelDetailsContent').textContent =
      `${details.source} · ${details.name} · ${details.days.toLocaleString()} days · seed ${details.seed}. ` +
      'The Python farm model supplies every simulation result. Controls without a Python equivalent are disabled.';
    setStatus('ready'); markParamsClean();
    document.getElementById('statusBadge').title='Python farm model';
  } catch(error) {
    setStatus('error'); console.error(error);
    document.getElementById('statusBadge').title=error.message;
  } finally {btn.disabled=false;btn.classList.remove('running');}
}
async function runLoopComparison() {
  const btn=document.getElementById('loopCmpBtn');
  btn.disabled=true;btn.classList.add('running');
  try {
    const data=await apiPost('/api/conventional/compare',{cfg:modelConfig(),loops:defaultActiveLoops()});
    cmpResults=data.results;
    document.getElementById('loopCmpResults').style.display='flex';
    activeChartKey='profit';
    document.querySelectorAll('.cmp-chart-tab').forEach((b,i)=>b.classList.toggle('active',i===0));
    buildModeACheckboxes();buildModeDDropdowns();renderLoopKpiBanner(cmpResults);renderModeATable();
  } catch(error) {console.error(error);alert('Loop comparison error: '+error.message);}
  finally {btn.disabled=false;btn.classList.remove('running');}
}
function generateRanking() {
  if (!lastResult) return;
  const summaries=lastResult.herdSummary || [];
  const active=summaries.filter(c=>c.cullReason==='active' && c.daysMilking>0);
  const historical=summaries.filter(c=>c.cullReason!=='active' && c.daysMilking>0);
  const neverMilked=summaries.filter(c=>c.daysMilking===0).length;
  rankData=(document.getElementById('rankToggleAll').checked ? [...active,...historical] : active).map(c=>({...c}));
  rankData.sort((a,b)=>(a.fcr??Infinity)-(b.fcr??Infinity));
  rankData.forEach((c,i)=>c.rank=i+1);
  const valid=rankData.filter(c=>c.fcr!==null);
  const min=valid.length?valid[0].fcr:0,max=valid.length?valid[valid.length-1].fcr:1;
  rankData.forEach(c=>{
    c.efficiency=c.fcr===null?null:Math.min(99,Math.max(1,Math.round(97-(c.fcr-min)/Math.max(.0001,max-min)*94)));
    c.tier=c.efficiency===null?'poor':c.efficiency>=80?'elite':c.efficiency>=60?'good':c.efficiency>=35?'avg':'poor';
  });
  const n=lastResult.n,days=lastResult.days;
  document.getElementById('rankSubtitle').textContent=`${rankData.length} cows ranked (${historical.length} replaced cows ${document.getElementById('rankToggleAll').checked?'included':'hidden'} · ${neverMilked} never-milked excluded) · ${n} herd · ${days.toLocaleString()} days · Python model`;
  const fcrCows=rankData.filter(c=>c.fcr!==null);
  const avgFCR=fcrCows.length?fcrCows.reduce((a,c)=>a+c.fcr,0)/fcrCows.length:null;
  const avgMilk=rankData.length?rankData.reduce((a,c)=>a+c.milk,0)/rankData.length:0;
  const best=rankData[0];
  document.getElementById('rankKpiRow').innerHTML=[
    {label:'Best FCR Cow',val:best?.id??'—',sub:best?.fcr?.toFixed(3)??'—'},
    {label:'Herd Avg FCR',val:avgFCR?.toFixed(3)??'—',sub:'kg feed per kg milk'},
    {label:'Avg Milk / Cow',val:avgMilk.toFixed(1)+' L',sub:'per cow per milking day'},
    {label:'Elite Cows',val:rankData.filter(c=>c.tier==='elite').length,sub:'of ranked cows'}
  ].map(k=>`<div class="kpi-card"><div class="kpi-label">${k.label}</div><div class="kpi-value">${k.val}</div><div class="kpi-unit">${k.sub}</div></div>`).join('');
  rankSortKey='rank';rankSortAsc=true;rankFilterTier='all';
  renderRankTable();renderRankCharts();
  document.getElementById('rankResults').style.display='block';
}
function exportRun() {
  if (lastResult?.runId) document.getElementById('exportMenu').hidden = !document.getElementById('exportMenu').hidden;
}
function downloadRun(artifact) {
  if (!lastResult?.runId) return;
  document.getElementById('exportMenu').hidden=true;
  location.href='/api/export/'+encodeURIComponent(lastResult.runId)+'/'+artifact;
}
async function loadExcelParity() {
  const slot=document.getElementById('excelParitySummary');
  try {
    const response=await fetch('/api/conventional/parity');
    const result=await response.json();
    if (!response.ok) throw new Error(result.error || 'Parity data unavailable');
    const counts=result.status_counts;
    const milk=result.selected.milk_yield_kg_per_cow_year;
    const profit=result.selected.profit;
    slot.textContent=`${result.seeds} seeds against ${result.reference}: ${counts.match} within 2%, ${counts.close} within 5%, ${counts.differs} beyond 5%. Milk ${((milk.relative_gap_fraction||0)*100).toFixed(1)}%; profit ${((profit.relative_gap_fraction||0)*100).toFixed(1)}%.`;
  } catch(error) {slot.textContent='Excel parity report is unavailable.';}
}
async function initializeDashboard() {
  try {
    const response=await fetch('/api/conventional/params');
    const data=await response.json();
    if (!response.ok) throw new Error(data.error||'Parameters unavailable');
    supportedParams=new Set(data.supported);backendDefaults=data.cfg;
    cfg={...DEFAULTS,...data.cfg};
    buildParamForms();
    loadExcelParity();
    await runSimulation();
  } catch(error) {setStatus('error');console.error(error);}
}
initializeDashboard();
window.addEventListener('resize',()=>requestAnimationFrame(()=>Object.values(chartInstances).forEach(c=>{try{c.resize();}catch(error){}})));
