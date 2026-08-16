import { state } from "./state.js";
import { aggregate, esc, fmt, periodLabel } from "./format.js";
import { CH, CHART_REGISTRY, buildCharts, svgChart } from "./charts.js";
import { compareScenarios, downloadRun, loadCalibration, loadDefaults, runSimulation } from "./api.js";
import { DEFAULT_PAGE, initRouter, navigate, pageFromHash, PAGES } from "./router.js";

"use strict";
const $ = (id) => document.getElementById(id);
const PERIODS = [["daily","Daily"],["monthly","Monthly"],["yearly","Yearly"]];
const CHART_PERIODS = [["daily","Daily"],["monthly","Monthly"],["annual","Annual"]];
const TABS = [["ledger","Ledger"],["graphs","Graphs"]];

const pageDefinition = (id) => PAGES.find(page => page.id === id) || PAGES.find(page => page.id === DEFAULT_PAGE);

function updateRailToggle() {
  const app = $("app-shell");
  const toggle = $("rail-toggle");
  if (!app || !toggle) return;
  app.classList.toggle("is-rail-collapsed", state.railCollapsed);
  toggle.setAttribute("aria-expanded", String(!state.railCollapsed));
  toggle.textContent = state.railCollapsed ? "Show navigation" : "Hide navigation";
}

function toggleRail() {
  state.railCollapsed = !state.railCollapsed;
  updateRailToggle();
  if (!state.railCollapsed) $("rail-toggle").focus();
}

function renderShell(page) {
  const current = pageDefinition(page);
  state.activePage = current.id;
  PAGES.forEach(({id}) => {
    const panel = $("page-" + id);
    if (panel) panel.hidden = id !== current.id;
    const nav = $("nav-" + id);
    if (nav) {
      nav.className = id === current.id ? "active" : "";
      if (id === current.id) nav.setAttribute("aria-current", "page");
      else nav.removeAttribute("aria-current");
    }
  });
  $("page-kicker").textContent = current.label.toUpperCase();
  $("page-title").textContent = current.label;
  $("page-description").textContent = current.description;
  updateRailToggle();
  if (current.id === "simulation") render();
  else if (current.id === "overview") renderOverview();
  else if (current.id === "charts") renderCharts();
  else if (current.id === "loops") renderLoops();
  else if (current.id === "comparison") renderComparison();
  else if (current.id === "cows") renderCows();
  else if (current.id === "environment") renderEnvironment();
  else if (current.id === "economics") renderEconomics();
  else if (current.id === "roi") renderEquipment();
  else if (current.id === "parameters") renderParameters();
  else if (current.id === "model-details") renderModelDetails();
  else if (current.id === "exports") renderExports();
}

function setLoading(loading) {
  state.loading = loading;
  $("loading-state").hidden = !loading;
  $("app-shell").className = `app${loading ? " is-loading" : ""}${state.railCollapsed ? " is-rail-collapsed" : ""}`;
  $("app-shell").setAttribute("aria-busy", String(loading));
  $("rail-status").textContent = loading ? "Running model" : "Ready for a run";
}

function setError(message) {
  state.error = message || null;
  $("error-banner").hidden = !message;
  $("error-text").textContent = message || "";
}

function setWarnings(warnings) {
  state.warnings = Array.isArray(warnings) ? warnings : [];
  $("warning-banner").hidden = state.warnings.length === 0;
  $("warning-text").textContent = state.warnings
    .map(warning => warning.message || warning.detail || "Model warning")
    .join(" ");
}

function updateScenarioLabel(name) {
  const label = name || "baseline";
  $("scenario-label").textContent = `${label} / calibrated`;
  $("header-scenario").textContent = label;
}

function updateRunMeta(data) {
  if (!data) {
    $("active-run-meta").textContent = "No run selected";
    return;
  }
  const meta = data.meta || data;
  const id = data.run_id || data.id || "unknown";
  const startDate = meta.start_date || data.start_date || (data.daily && data.daily[0] && data.daily[0].day) || "-";
  $("active-run-meta").textContent = `Run ${id} · ${meta.scenario_name || data.name || "unnamed"} · start ${startDate} · ${meta.days ?? data.days} days · herd ${meta.herd_size ?? data.herd_size ?? "-"} · seed ${meta.seed ?? data.seed ?? "-"}`;
}


const TOGGLE_KEYS = [
  ["l1_nutrient_loop_enabled", "L1 nutrient loop"],
  ["l2_water_loop_enabled", "L2 water loop"],
  ["l3_energy_loop_enabled", "L3 energy loop"],
  ["l4_byproduct_loop_enabled", "L4 byproduct loop"],
  ["enable_processor", "Processor"],
  ["enable_whey_processing", "Whey processing"],
  ["enable_land_agent", "Land agent"],
];

const COLUMNS = [
  ["day", "Date"],
  ["milk_l", "Milk (L)"],
  ["profit", "Profit (currency)"],
  ["net_kg_co2e", "Net CO2e (kg CO2e)"],
  ["kg_co2e_per_l_milk", "CO2e/L (kg CO2e/L)"],
  ["energy_self_sufficiency_pct", "Self-sufficiency (%)"],
  ["input_circularity", "Input circularity (fraction)"],
  ["output_circularity", "Output circularity (fraction)"],
  ["freshwater_withdrawal_l", "Freshwater (L)"],
  ["cow_count", "Cows"],
  ["active_disease_cases", "Cases"],
  ["sustainability_score_0_100", "Sustainability (score / 100)"],
];

async function initialize() {
  try {
    const data = await loadDefaults();
    state.config = data;
    const def = data.defaults;
    updateScenarioLabel(def.name || "baseline");
    $("scenario").innerHTML = data.scenarios
      .map(s => `<option value="${esc(s)}">${esc(s.replace(/\.json$/, ""))}</option>`).join("");
    $("scenario").value = data.scenarios.includes("baseline.json") ? "baseline.json" : data.scenarios[0];
    $("days").value = def.days;
    $("start-date").value = def.start_date || "";
    $("seed").value = def.seed; $("herd").value = def.herd_size;
    $("switches").innerHTML = TOGGLE_KEYS.map(([key,label]) =>
      `<label class="switch"><span>${label}</span>
        <input type="checkbox" data-k="${key}" ${def[key] ? "checked" : ""}></label>`).join("");
    setError("");
  } catch (error) {
    setError(error.message || "Unable to load dashboard configuration");
  }
}

function dashboardMetric(data, key) {
  const metric = data && data.summary && data.summary[key];
  if (metric && typeof metric === "object") return metric;
  const value = data && data.metrics ? data.metrics[key] : null;
  return {value, available: value !== null && value !== undefined, unit: ""};
}

function metricDisplay(data, key, decimals = 0, unit = "", scale = 1) {
  const metric = dashboardMetric(data, key);
  if (metric.available === false || metric.value === null || metric.value === undefined || Number.isNaN(Number(metric.value))) return "N/A";
  const label = unit || metric.unit || "";
  return `${fmt(Number(metric.value) * scale, decimals)}${label ? ` ${label}` : ""}`;
}

function overviewChart(rows, title, subtitle, series, options = {}) {
  const availableSeries = series.filter(item => rows.some(row => row[item.key] !== null && row[item.key] !== undefined));
  const chart = availableSeries.length
    ? svgChart(Object.assign({rows, period: "daily", title, kind: "area", series: availableSeries}, options))
    : `<div class="overview-unavailable">N/A<br><span>No reported data for this chart.</span></div>`;
  return `<article class="overview-chart"><div class="overview-charthead"><b>${esc(title)}</b><span>${esc(subtitle)}</span></div>${chart}</article>`;
}

function renderOverview() {
  const target = $("overview-content");
  if (!target) return;
  const d = state.data;
  if (!d) {
    target.innerHTML = `<div class="empty-state"><span class="eyebrow">OVERVIEW</span><h2>Farm outcomes at a glance.</h2><p>Run a simulation to populate the overview with authoritative model outputs.</p></div>`;
    return;
  }

  const cards = [
    ["Total milk", "milk", 0, "L"],
    ["Average milk / cow / day", "average_milk_per_cow", 2, "L/cow/day"],
    ["Net profit", "profit", 0, "currency"],
    ["Total revenue", "total_revenue", 0, "currency"],
    ["Total cost", "total_cost", 0, "currency"],
    ["Net GHG", "net_co2e", 0, "kg CO2e"],
    ["GHG intensity", "ghg_intensity", 3, "kg CO2e/L"],
    ["Feed conversion ratio", "fcr", 2, "kg DM/L"],
    ["Freshwater withdrawal", "freshwater", 0, "L"],
    ["Energy self-sufficiency", "energy_avg", 1, "%"],
    ["Circularity", "circularity", 1, "%", 100],
    ["Sustainability", "sustainability_avg", 1, "/ 100"],
    ["Active disease cases", "disease_cases", 0, "cases"],
    ["Ending herd", "herd_size", 0, "cows"],
  ];
  const kpis = cards.map(([label, key, decimals, unit, scale]) => {
    const metric = dashboardMetric(d, key);
    const unavailable = metric.available === false || metric.value === null || metric.value === undefined;
    return `<article class="overview-kpi${unavailable ? " is-unavailable" : ""}"><span>${esc(label)}</span><strong>${metricDisplay(d, key, decimals, unit, scale)}</strong></article>`;
  }).join("");

  const rows = d.series && Array.isArray(d.series.daily) ? d.series.daily : (Array.isArray(d.daily) ? d.daily : []);
  const charts = [
    overviewChart(rows, "Milk production", "Daily litres", [{key: "milk_l", color: "#b42318", label: "Milk"}], {unit: "L", dec: 0, ydec: 0}),
    overviewChart(rows, "Economics", "Reported daily currency", [
      {key: "total_revenue", color: "#3f6b4f", label: "Revenue"},
      {key: "total_cost", color: "#b7791f", label: "Cost"},
      {key: "profit", color: "#b42318", label: "Profit"},
    ], {unit: "currency", dec: 0, ydec: 0, floor: false}),
    overviewChart(rows, "Environmental performance", "Daily CO2e streams", [
      {key: "gross_kg_co2e", color: "#b7791f", label: "Gross"},
      {key: "avoided_kg_co2e", color: "#3f6b4f", label: "Avoided"},
      {key: "net_kg_co2e", color: "#b42318", label: "Net"},
    ], {unit: "kg CO2e", dec: 1, ydec: 1, floor: false}),
    overviewChart(rows, "Resource use", "Daily freshwater withdrawal", [{key: "freshwater_withdrawal_l", color: "#527a61", label: "Freshwater"}], {unit: "L", dec: 0, ydec: 0}),
  ].join("");

  const meta = d.meta || d;
  target.innerHTML = `<div class="overview-head"><div><span class="eyebrow">RUN SUMMARY</span><h2>${esc(meta.scenario_name || d.name || "unnamed")}</h2><p>Authoritative values from ${esc(String(meta.days ?? d.days))} simulated days beginning ${esc(meta.start_date || d.start_date || "-")}.</p></div><span class="overview-source">Python dashboard contract</span></div><div class="overview-kpis">${kpis}</div><div class="overview-charts">${charts}</div>`;
}

function chartCard(config, rows, period) {
  const available = rows.some(row => row[config.field] !== null && row[config.field] !== undefined);
  const chart = available
    ? svgChart({rows, period, title: config.title, kind: config.kind, unit: config.unit, dec: config.dec, ydec: config.ydec, floor: config.floor, series: [{key: config.field, color: config.color, label: config.title}]})
    : `<div class="chart-unavailable">N/A<br><span>No reported data for this series.</span></div>`;
  return `<article class="chart-card" data-chart-id="${esc(config.id)}"><div class="chart-cardhead"><div><b>${esc(config.title)}</b><span>${esc(config.unit)}</span></div><span>${esc(config.group)}</span></div>${chart}</article>`;
}

function renderCharts() {
  const target = $("charts-content");
  if (!target) return;
  const d = state.data;
  if (!d) {
    target.innerHTML = `<div class="empty-state"><span class="eyebrow">CHARTS</span><h2>No series selected.</h2><p>Run a simulation first. The charts page will use the model's daily, monthly, and annual records without re-simulating or rolling them up in the browser.</p></div>`;
    return;
  }

  const period = CHART_PERIODS.some(([key]) => key === state.selectedPeriod) ? state.selectedPeriod : "daily";
  state.selectedPeriod = period;
  const rows = d.series && Array.isArray(d.series[period]) ? d.series[period] : [];
  const groups = [...new Set(CHART_REGISTRY.map(config => config.group))].map(group => {
    const cards = CHART_REGISTRY
      .filter(config => config.group === group && config.periods.includes(period))
      .map(config => chartCard(config, rows, period))
      .join("");
    return `<section class="chart-group"><div class="chart-grouphead"><span class="eyebrow">${esc(group)}</span><span>${rows.length} ${period} points</span></div><div class="chart-grid">${cards}</div></section>`;
  }).join("");
  const periodButtons = CHART_PERIODS.map(([key, label]) =>
    `<button type="button" data-chart-period="${key}" class="${key === period ? "on" : ""}">${label}</button>`).join("");
  target.innerHTML = `<div class="charts-workspace"><div class="charts-toolbar"><div><span class="eyebrow">SERIES WORKSPACE</span><h2>Backend-produced trends.</h2><p>Period values come from the Python dashboard contract; unavailable fields remain unavailable.</p></div><div class="chart-periods">${periodButtons}</div></div><div class="chart-note">Selected period: <b>${esc(period)}</b>. No monthly or annual aggregation is performed in the browser.</div><div class="chart-registry">${groups}</div></div>`;
}
function loopStateClass(value) {
  return value === "active" ? "is-active" : value === "inactive" ? "is-inactive" : "is-unavailable";
}

function loopMetricDisplay(metric) {
  if (!metric || metric.available === false || metric.value === null || metric.value === undefined) return "N/A";
  return `${fmt(metric.value, 2)}${metric.unit ? ` ${esc(metric.unit)}` : ""}`;
}

function renderLoopMetric(label, metric) {
  return `<div class="loop-metric"><span>${esc(label)}</span><strong>${loopMetricDisplay(metric)}</strong></div>`;
}

function renderLoopSection(key, section, title, description) {
  const metricRows = Object.entries(section.metrics || {})
    .map(([label, metric]) => renderLoopMetric(label.replaceAll("_", " "), metric)).join("");
  const detailRows = Object.entries(section.details || {})
    .filter(([, value]) => value !== null && value !== undefined && value !== "")
    .map(([label, value]) => `<div class="loop-detail"><span>${esc(label.replaceAll("_", " "))}</span><b>${esc(typeof value === "object" ? JSON.stringify(value) : String(value))}</b></div>`).join("");
  const provenance = (section.provenance || []).map(item => `<span class="loop-provenance">${esc(item.source || item.name || "source")} · ${esc(item.confidence || "unavailable")}</span>`).join("");
  return `<article class="loop-section ${loopStateClass(section.state)}"><header class="loop-sectionhead"><div><span class="eyebrow">${esc(key.toUpperCase())}</span><h2>${esc(title)}</h2><p>${esc(description)}</p></div><b class="loop-state">${esc(section.state)}</b></header><div class="loop-metrics">${metricRows || `<div class="loop-empty">N/A<br><span>No authoritative loop data was retained.</span></div>`}</div>${detailRows ? `<div class="loop-details">${detailRows}</div>` : ""}<footer class="loop-sectionfoot">${section.enabled ? "Enabled" : "Disabled or unavailable"} ${provenance}</footer></article>`;
}

function renderLoopFlow(flow) {
  if (!flow || !Array.isArray(flow.nodes) || !Array.isArray(flow.edges)) return `<div class="loop-empty">N/A<br><span>No flow data was retained.</span></div>`;
  const nodes = flow.nodes.map(node => `<span class="loop-node ${loopStateClass(node.state)}"><b>${esc(node.label)}</b><small>${esc(node.state)}</small></span>`).join("");
  const edges = flow.edges.map(edge => `<li class="${loopStateClass(edge.state)}"><b>${esc(edge.label)}</b><span>${esc(edge.source)} → ${esc(edge.target)} · ${esc(edge.unit || "")}</span></li>`).join("");
  return `<div class="loop-flow"><div class="loop-nodes">${nodes}</div><ol class="loop-edges">${edges}</ol></div>`;
}

function renderLoops() {
  const target = $("loops-content");
  if (!target) return;
  const data = state.data;
  if (!data || !data.loops) {
    target.innerHTML = `<div class="empty-state"><span class="eyebrow">CIRCULAR LOOPS</span><h2>Trace the farm's loops.</h2><p>Run a simulation to inspect authoritative nutrient, water, energy, and byproduct pathways.</p></div>`;
    return;
  }
  const loops = data.loops;
  target.innerHTML = `<div class="loops-workspace"><div class="loops-head"><div><span class="eyebrow">CIRCULARITY WORKSPACE</span><h2>Material pathways from the model.</h2><p>Values and connection states come from serialized histories and packets. Units remain attached to each stream.</p></div><span class="overview-source">Python dashboard contract</span></div><div class="loop-sections">${renderLoopSection("l1", loops.l1, "Nutrient loop", "Manure routes, nutrient return, and fertilizer substitution.")}${renderLoopSection("l2", loops.l2, "Water loop", "Water use, treatment, recovery, and recycled irrigation.")}${renderLoopSection("l3", loops.l3, "Energy loop", "Feedstock, biogas, electricity, heat, and energy value.")}${renderLoopSection("l4", loops.l4, "Byproduct loop", "Processor outputs, residual routes, and approved feed returns.")}</div><section class="loop-flow-section"><header class="loop-sectionhead"><div><span class="eyebrow">FLOW TOPOLOGY</span><h2>Farm material flow</h2><p>Fixed topology with backend-driven active, inactive, and unavailable states.</p></div></header>${renderLoopFlow(loops.flow)}</section></div>`;
}

const COMPARISON_MODES = [
  ["baseline", "Baseline vs Current"],
  ["loop", "Individual Loop"],
  ["scenarios", "User-selected scenarios"],
  ["matrix", "Full L1-L4 matrix"],
];
const COMPARISON_METRIC_META = {
  milk: ["Milk", "higher"],
  average_milk_per_cow: ["Average milk / cow / day", "higher"],
  net_co2e: ["Net GHG", "lower"],
  ghg_intensity: ["GHG intensity", "lower"],
  fcr: ["Feed conversion ratio", "lower"],
  profit: ["Profit", "higher"],
  total_revenue: ["Total revenue", "higher"],
  total_cost: ["Total cost", "lower"],
  energy_avg: ["Energy self-sufficiency", "higher"],
  freshwater: ["Freshwater withdrawal", "lower"],
  circularity: ["Circularity", "higher"],
  sustainability_avg: ["Sustainability", "higher"],
  disease_cases: ["Disease cases", "lower"],
  herd_size: ["Ending herd", "higher"],
};
const COMPARISON_LOOP_KEYS = TOGGLE_KEYS.filter(([key]) => key.startsWith("l"));
const COMPARISON_DECIMALS = {
  milk: 0, average_milk_per_cow: 2, net_co2e: 0, ghg_intensity: 3, fcr: 3,
  profit: 0, total_revenue: 0, total_cost: 0, energy_avg: 1, freshwater: 0,
  circularity: 3, sustainability_avg: 1, disease_cases: 0, herd_size: 0,
};

function comparisonScenarioNames() {
  const names = state.config && Array.isArray(state.config.scenarios) ? state.config.scenarios : ["baseline.json"];
  return names.length ? names : ["baseline.json"];
}

function comparisonScenarioFile(name) {
  const names = comparisonScenarioNames();
  const clean = String(name || "baseline").replace(/\.json$/, "");
  return names.find(item => item === name || String(item).replace(/\.json$/, "") === clean) || `${clean}.json`;
}

function comparisonControl(id, fallback) {
  const element = $(id);
  return element && element.value !== "" && element.value !== undefined ? element.value : fallback;
}

function comparisonNumber(value, fallback) {
  if (value === "" || value === null || value === undefined || !Number.isFinite(Number(value))) return fallback;
  return Math.trunc(Number(value));
}

function comparisonMeta(run) {
  const payload = run && typeof run === "object" ? run : {};
  const meta = payload.meta && typeof payload.meta === "object" ? payload.meta : payload;
  const daily = Array.isArray(payload.daily) && payload.daily.length ? payload.daily[0] : null;
  return {
    scenario: meta.scenario_name || payload.name || "unnamed",
    start_date: meta.start_date || payload.start_date || (daily && daily.day) || null,
    days: meta.days ?? payload.days ?? null,
    herd_size: meta.herd_size ?? payload.herd_size ?? null,
    seed: meta.seed ?? payload.seed ?? null,
    calibration_overrides: meta.calibration_overrides && typeof meta.calibration_overrides === "object" ? meta.calibration_overrides : {},
  };
}

function comparisonBaseSettings() {
  const defaults = state.config && (state.config.defaults || state.config.default_scenario) || {};
  const current = comparisonMeta(state.data);
  return {
    days: comparisonNumber(current.days, comparisonNumber(defaults.days, 10)),
    start_date: current.start_date || defaults.start_date || "",
    seed: comparisonNumber(current.seed, comparisonNumber(defaults.seed, 1)),
    herd_size: comparisonNumber(current.herd_size, comparisonNumber(defaults.herd_size, 100)),
  };
}

function comparisonFeatureSettings(source, fallback = {}) {
  return TOGGLE_KEYS.reduce((features, [key]) => {
    features[key] = source && Object.prototype.hasOwnProperty.call(source, key)
      ? Boolean(source[key]) : Boolean(fallback[key]);
    return features;
  }, {});
}

function comparisonDefaultFeatures() {
  const defaults = state.config && (state.config.feature_flags || state.config.defaults || state.config.default_scenario) || {};
  return comparisonFeatureSettings(defaults);
}

function comparisonCurrentFeatures() {
  return comparisonFeatureSettings(state.data && state.data.features, comparisonDefaultFeatures());
}

function comparisonSettings() {
  const base = comparisonBaseSettings();
  return {
    days: comparisonNumber(comparisonControl("comparison-days", base.days), base.days),
    start_date: comparisonControl("comparison-start-date", base.start_date),
    seed: comparisonNumber(comparisonControl("comparison-seed", base.seed), base.seed),
    herd_size: comparisonNumber(comparisonControl("comparison-herd", base.herd_size), base.herd_size),
  };
}

function comparisonOverrides(settings, features) {
  const overrides = {
    days: settings.days,
    seed: settings.seed,
    herd_size: settings.herd_size,
    ...features,
  };
  if (settings.start_date) overrides.start_date = settings.start_date;
  return overrides;
}

function comparisonRunSpec(label, scenario, settings, features, calibration_overrides = {}) {
  return {
    label,
    scenario: comparisonScenarioFile(scenario),
    scenario_overrides: comparisonOverrides(settings, features),
    calibration_overrides,
  };
}

function comparisonRequests() {
  const mode = COMPARISON_MODES.some(([key]) => key === state.comparisonMode) ? state.comparisonMode : "baseline";
  const settings = comparisonSettings();
  const defaultScenario = comparisonScenarioFile("baseline");
  const defaultFeatures = comparisonDefaultFeatures();
  const current = comparisonMeta(state.data);
  if (mode === "loop") {
    const loopKey = comparisonControl("comparison-loop", COMPARISON_LOOP_KEYS[0][0]);
    const loop = COMPARISON_LOOP_KEYS.find(([key]) => key === loopKey) || COMPARISON_LOOP_KEYS[0];
    const changed = {...defaultFeatures, [loop[0]]: false};
    return [
      comparisonRunSpec("Scenario defaults", defaultScenario, settings, defaultFeatures),
      comparisonRunSpec(`${loop[1]} off`, defaultScenario, settings, changed),
    ];
  }
  if (mode === "scenarios") {
    const names = comparisonScenarioNames();
    const first = comparisonControl("comparison-scenario-a", defaultScenario);
    const second = comparisonControl("comparison-scenario-b", names[1] || defaultScenario);
    const firstLabel = comparisonControl("comparison-label-a", "Scenario A");
    const secondLabel = comparisonControl("comparison-label-b", "Scenario B");
    return [
      comparisonRunSpec(firstLabel, first, settings, defaultFeatures),
      comparisonRunSpec(secondLabel, second, settings, defaultFeatures),
    ];
  }
  if (mode === "matrix") {
    return Array.from({length: 16}, (_, mask) => {
      const features = {...defaultFeatures};
      const states = COMPARISON_LOOP_KEYS.map(([key, label], index) => {
        features[key] = Boolean(mask & (1 << index));
        return `${label.replace(/ loop$/, "")}: ${features[key] ? "on" : "off"}`;
      });
      return comparisonRunSpec(states.join(" · "), defaultScenario, settings, features);
    });
  }
  const currentScenario = state.data ? comparisonScenarioFile(current.scenario) : defaultScenario;
  const currentOverrides = current.calibration_overrides;
  return [
    comparisonRunSpec("Baseline", defaultScenario, settings, defaultFeatures),
    comparisonRunSpec("Current", currentScenario, settings, comparisonCurrentFeatures(), currentOverrides),
  ];
}

function comparisonModeControls() {
  return `<div class="comparison-mode" role="group" aria-label="Comparison mode">${COMPARISON_MODES.map(([key, label]) => `<button type="button" data-comparison-mode="${key}" class="${state.comparisonMode === key ? "on" : ""}">${esc(label)}</button>`).join("")}</div>`;
}

function comparisonScenarioOptions(selected) {
  return comparisonScenarioNames().map(name => `<option value="${esc(name)}" ${name === selected ? "selected" : ""}>${esc(name.replace(/\.json$/, ""))}</option>`).join("");
}

function comparisonForm() {
  const settings = comparisonBaseSettings();
  const mode = COMPARISON_MODES.find(([key]) => key === state.comparisonMode) || COMPARISON_MODES[0];
  const names = comparisonScenarioNames();
  const specific = state.comparisonMode === "loop"
    ? `<label>Loop<select id="comparison-loop">${COMPARISON_LOOP_KEYS.map(([key, label]) => `<option value="${key}">${esc(label)}</option>`).join("")}</select></label>`
    : state.comparisonMode === "scenarios"
      ? `<div class="comparison-scenario-grid"><label>First scenario<select id="comparison-scenario-a">${comparisonScenarioOptions(names[0])}</select></label><label>First label<input id="comparison-label-a" value="Scenario A"></label><label>Second scenario<select id="comparison-scenario-b">${comparisonScenarioOptions(names[1] || names[0])}</select></label><label>Second label<input id="comparison-label-b" value="Scenario B"></label></div>`
      : state.comparisonMode === "matrix"
        ? `<p class="comparison-matrix-note"><b>16 actual model runs.</b> Each L1-L4 on/off combination is sent to the Python model; no matrix values are inferred in the browser.</p>`
        : `<p class="comparison-mode-note">Baseline uses the selected scenario defaults. Current replays the latest run settings and retained feature flags.</p>`;
  const runLabel = state.comparisonMode === "matrix" ? "Run 16 model runs" : "Run comparison";
  return `<section class="comparison-controls"><header><div><span class="eyebrow">COMPARISON DESIGN</span><h2>${esc(mode[1])}</h2><p>Independent runs, one shared comparison contract.</p></div>${comparisonModeControls()}</header><div class="comparison-settings"><label>Duration<input id="comparison-days" type="number" min="1" max="3650" step="1" value="${esc(settings.days)}"><small>days</small></label><label>Start date<input id="comparison-start-date" type="date" value="${esc(settings.start_date)}"></label><label>Seed<input id="comparison-seed" type="number" step="1" value="${esc(settings.seed)}"></label><label>Herd size<input id="comparison-herd" type="number" min="0" step="1" value="${esc(settings.herd_size)}"></label></div><div class="comparison-specific">${specific}</div><button id="comparison-run" type="button">${runLabel}</button></section>`;
}

function comparisonWarnings(result) {
  const runs = Array.isArray(result && result.runs) ? result.runs : [];
  if (runs.length < 2) return ["At least two completed runs are required for a comparison."];
  const warnings = [];
  const metas = runs.map(comparisonMeta);
  const settings = [["seed", "Seeds"], ["days", "Durations"], ["herd_size", "Herd sizes"], ["start_date", "Start dates"]];
  settings.forEach(([key, label]) => {
    const values = new Set(metas.map(meta => String(meta[key] ?? "unavailable")));
    if (values.size > 1) warnings.push(`${label} differ across runs.`);
  });
  const featureKeys = [...new Set(runs.flatMap(run => Object.keys(run.features || {})))];
  featureKeys.forEach(key => {
    const values = new Set(runs.map(run => String(Boolean((run.features || {})[key]))));
    if (values.size > 1) {
      const label = (TOGGLE_KEYS.find(([name]) => name === key) || [key, key])[1];
      warnings.push(`${label} settings differ.`);
    }
  });
  const calibration = new Set(metas.map(meta => JSON.stringify(meta.calibration_overrides || {})));
  if (calibration.size > 1) warnings.push("Calibration overrides differ across runs.");
  runs.forEach(run => (Array.isArray(run.warnings) ? run.warnings : []).forEach(warning => {
    const text = typeof warning === "string" ? warning : warning.message || warning.detail;
    if (text) warnings.push(`${run.label || "Run"}: ${text}`);
  }));
  return [...new Set(warnings)];
}

function comparisonFeatureSummary(run) {
  const entries = Object.entries(run.features || {});
  if (!entries.length) return "Feature state unavailable";
  return entries.filter(([, enabled]) => enabled).map(([key]) => (TOGGLE_KEYS.find(([name]) => name === key) || [key, key])[1]).join(", ") || "No optional systems enabled";
}

function comparisonRunCards(runs) {
  return runs.map(run => {
    const meta = comparisonMeta(run);
    const runId = run.run_id || run.id || "unavailable";
    return `<article class="comparison-run-card"><header><b>${esc(run.label || "Run")}</b><span>${esc(runId)}</span></header><dl><div><dt>Scenario</dt><dd>${esc(meta.scenario)}</dd></div><div><dt>Seed</dt><dd>${esc(meta.seed ?? "N/A")}</dd></div><div><dt>Duration</dt><dd>${esc(meta.days ?? "N/A")} days</dd></div><div><dt>Herd</dt><dd>${esc(meta.herd_size ?? "N/A")}</dd></div><div><dt>Features</dt><dd>${esc(comparisonFeatureSummary(run))}</dd></div></dl></article>`;
  }).join("");
}

function comparisonMetricKeys(result) {
  const keys = [];
  (result && result.deltas || []).forEach(delta => Object.keys(delta.metrics || {}).forEach(key => {
    if (!keys.includes(key)) keys.push(key);
  }));
  return keys;
}

function comparisonMetricLabel(key) {
  return COMPARISON_METRIC_META[key] ? COMPARISON_METRIC_META[key][0] : key.replaceAll("_", " ");
}

function comparisonMetricDirection(key) {
  return COMPARISON_METRIC_META[key] ? COMPARISON_METRIC_META[key][1] : "neutral";
}

function comparisonAssessment(key, absolute) {
  if (!Number.isFinite(Number(absolute)) || Number(absolute) === 0) return "is-neutral";
  const direction = comparisonMetricDirection(key);
  if (direction === "higher") return Number(absolute) > 0 ? "is-favorable" : "is-unfavorable";
  if (direction === "lower") return Number(absolute) < 0 ? "is-favorable" : "is-unfavorable";
  return "is-neutral";
}

function comparisonValue(value, key, unit = "") {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return `<span class="comparison-na">N/A</span>`;
  const decimals = COMPARISON_DECIMALS[key] ?? 2;
  return `${esc(fmt(Number(value), decimals))}${unit ? ` <small>${esc(unit)}</small>` : ""}`;
}

function comparisonDeltaValue(value, key, unit = "") {
  return comparisonValue(value, key, unit);
}

function comparisonPercentage(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return `<span class="comparison-na">N/A</span>`;
  return `${esc(fmt(Number(value), 1))}%`;
}

function comparisonTable(result, metricKeys) {
  const runs = Array.isArray(result.runs) ? result.runs : [];
  const labels = new Map(runs.map(run => [String(run.run_id || run.id), run.label || "Run"]));
  const rows = (result.deltas || []).flatMap(delta => Object.entries(delta.metrics || {}).map(([key, metric]) => {
    const assessment = comparisonAssessment(key, metric.absolute);
    const candidateId = String(delta.run_id || "");
    return `<tr class="${assessment}"><th scope="row">${esc(comparisonMetricLabel(key))}<small>${esc(key)}</small></th><td>${comparisonValue(metric.baseline, key, metric.unit)}</td><td>${esc(labels.get(candidateId) || "Candidate")}<br>${comparisonValue(metric.value, key, metric.unit)}</td><td class="comparison-delta ${assessment}">${comparisonDeltaValue(metric.absolute, key, metric.unit)}</td><td class="comparison-delta ${assessment}">${comparisonPercentage(metric.percentage)}</td></tr>`;
  })).join("");
  if (!rows) return `<div class="comparison-unavailable">N/A<br><span>The comparison returned no safe metric deltas.</span></div>`;
  return `<div class="comparison-table-wrap"><table class="comparison-table"><thead><tr><th scope="col">Metric</th><th scope="col">${esc(runs[0] && runs[0].label || "Baseline")}</th><th scope="col">Candidate</th><th scope="col">Absolute delta</th><th scope="col">Percentage delta</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

function comparisonChart(result, key) {
  const runs = Array.isArray(result.runs) ? result.runs : [];
  const runLabels = new Map(runs.map(run => [String(run.run_id || run.id), run.label || "Run"]));
  const points = (result.deltas || []).map(delta => {
    const metric = delta.metrics && delta.metrics[key];
    return metric && Number.isFinite(Number(metric.absolute)) ? {label: runLabels.get(String(delta.run_id)) || "Candidate", value: Number(metric.absolute), unit: metric.unit || "", assessment: comparisonAssessment(key, metric.absolute)} : null;
  }).filter(Boolean);
  if (!points.length) return `<div class="comparison-unavailable">N/A<br><span>No numeric delta is available for ${esc(comparisonMetricLabel(key))}.</span></div>`;
  const width = 680;
  const height = 250;
  const left = 38;
  const right = 18;
  const top = 26;
  const bottom = 48;
  const zero = top + (height - top - bottom) / 2;
  const max = Math.max(1, ...points.map(point => Math.abs(point.value)));
  const slot = (width - left - right) / points.length;
  const barWidth = Math.min(76, slot * .64);
  const bars = points.map((point, index) => {
    const barHeight = Math.max(2, Math.abs(point.value) / max * ((height - top - bottom) / 2 - 8));
    const x = left + index * slot + (slot - barWidth) / 2;
    const y = point.value >= 0 ? zero - barHeight : zero;
    return `<rect class="comparison-bar ${point.assessment}" x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${barWidth.toFixed(1)}" height="${barHeight.toFixed(1)}" rx="1"><title>${esc(point.label)} · ${esc(fmt(point.value, COMPARISON_DECIMALS[key] ?? 2))} ${esc(point.unit)}</title></rect><text class="comparison-axis-label" x="${(x + barWidth / 2).toFixed(1)}" y="${height - 19}" text-anchor="middle">${esc(point.label.slice(0, 13))}</text>`;
  }).join("");
  const direction = comparisonMetricDirection(key);
  return `<svg class="comparison-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(comparisonMetricLabel(key))} delta chart"><line class="comparison-zero" x1="${left}" y1="${zero}" x2="${width - right}" y2="${zero}"/><text class="comparison-chart-title" x="${left}" y="16">${esc(comparisonMetricLabel(key))} · ${esc(direction === "neutral" ? "direction neutral" : `${direction} is favorable`)}</text>${bars}</svg>`;
}

function renderComparisonResult(result) {
  const runs = Array.isArray(result && result.runs) ? result.runs : [];
  if (runs.length < 2) return `<div class="empty-state"><h2>No comparison result.</h2><p>Run at least two independent model configurations.</p></div>`;
  const keys = comparisonMetricKeys(result);
  const selected = keys.includes(state.comparisonMetric) ? state.comparisonMetric : keys[0];
  state.comparisonMetric = selected || "milk";
  const warnings = comparisonWarnings(result);
  const warningHtml = warnings.length
    ? `<div class="comparison-warnings"><b>Interpretation checks</b><ul>${warnings.map(warning => `<li>${esc(warning)}</li>`).join("")}</ul></div>`
    : `<div class="comparison-consistent">Shared seed and run settings are aligned; deltas are easier to attribute.</div>`;
  const metricButtons = keys.map(key => `<button type="button" data-comparison-metric="${esc(key)}" class="${key === selected ? "on" : ""}">${esc(comparisonMetricLabel(key))}</button>`).join("");
  return `<section class="comparison-result"><div class="comparison-result-head"><div><span class="eyebrow">RESULTS</span><h2>Baseline-ledger deltas.</h2><p>Absolute and percentage changes are supplied by the Python comparison contract.</p></div><span class="overview-source">${runs.length} independent runs</span></div>${warningHtml}<section class="comparison-runs"><header><div><span class="eyebrow">RUN METADATA</span><h3>Keep the settings in view.</h3></div></header><div class="comparison-run-grid">${comparisonRunCards(runs)}</div></section><section class="comparison-chart-panel"><header><div><span class="eyebrow">SELECTABLE METRIC</span><h3>Which delta deserves attention?</h3></div><div class="comparison-metric-buttons">${metricButtons}</div></header>${selected ? comparisonChart(result, selected) : `<div class="comparison-unavailable">N/A</div>`}</section><section class="comparison-table-panel"><header><div><span class="eyebrow">COMPARISON TABLE</span><h3>Trace every safe metric.</h3><p>Green means favorable for the selected metric direction; red means unfavorable; neutral means no directional rule was assigned.</p></div></header>${comparisonTable(result, keys)}</section></section>`;
}

function renderComparison() {
  const target = $("comparison-content");
  if (!target) return;
  target.innerHTML = `<div class="comparison-workspace"><header class="comparison-head"><div><span class="eyebrow">SCENARIO COMPARISON</span><h2>Compare independent model runs.</h2><p>Use the same seed and settings for controlled attribution, or make differences explicit in the warning rail.</p></div><span class="overview-source">Python comparison contract</span></header>${comparisonForm()}${state.comparison ? renderComparisonResult(state.comparison) : `<div class="comparison-empty"><b>No comparison has been run.</b><span>Choose a mode, review the settings, and send the configurations to the authoritative model.</span></div>`}</div>`;
}

async function runComparison() {
  setError("");
  setWarnings([]);
  setLoading(true);
  try {
    const data = await compareScenarios({runs: comparisonRequests()});
    state.comparison = data;
    const runs = Array.isArray(data.runs) ? data.runs : [];
    const keys = comparisonMetricKeys(data);
    if (!keys.includes(state.comparisonMetric)) state.comparisonMetric = keys[0] || "milk";
    $("stamp").textContent = "COMPARED";
    $("active-run-meta").textContent = `${runs.length} independent model runs compared`;
    navigate("comparison");
    renderShell("comparison");
  } catch (error) {
    setError(error.message || "The comparison failed");
    renderShell("comparison");
  } finally {
    setLoading(false);
  }
}


const COW_SORTS = [
  ["milk_l", "Milk/day: high to low"],
  ["fcr_kg_dm_per_l", "FCR: low to high"],
  ["dmi_kg", "DMI: high to low"],
  ["methane_intensity_kg_ch4_per_l", "Methane intensity: low to high"],
];
const COW_COLUMNS = [
  ["id", "Cow ID"],
  ["milk_l", "Milk/day (L)"],
  ["dmi_kg", "DMI (kg DM/day)"],
  ["fcr_kg_dm_per_l", "FCR (kg DM/L)"],
  ["days_in_milk", "DIM (days)"],
  ["health_status", "Health state"],
  ["rumen_ph", "Rumen pH"],
  ["sara_active", "SARA"],
  ["body_condition_score", "BCS (score)"],
  ["body_weight_kg", "Weight (kg)"],
  ["pregnant", "Pregnant"],
];

function cowCell(value, decimals = 0, unit = "") {
  if (value === null || value === undefined) return `<span class="cow-na">N/A</span>`;
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return `${esc(fmt(value, decimals))}${unit ? ` ${esc(unit)}` : ""}`;
  return esc(value);
}

function cowScatter(rows, xKey, yKey, xLabel, yLabel) {
  const points = rows.filter(row => typeof row[xKey] === "number" && typeof row[yKey] === "number");
  if (!points.length) return `<div class="cow-chart-unavailable">N/A<br><span>No paired values are available.</span></div>`;
  const width = 520;
  const height = 230;
  const pad = 34;
  const xValues = points.map(row => row[xKey]);
  const yValues = points.map(row => row[yKey]);
  const xMin = Math.min(...xValues);
  const xMax = Math.max(...xValues);
  const yMin = Math.min(...yValues);
  const yMax = Math.max(...yValues);
  const xRange = xMax === xMin ? 1 : xMax - xMin;
  const yRange = yMax === yMin ? 1 : yMax - yMin;
  const x = value => pad + ((value - xMin) / xRange) * (width - pad * 2);
  const y = value => height - pad - ((value - yMin) / yRange) * (height - pad * 2);
  const dots = points.map(row => `<circle cx="${x(row[xKey]).toFixed(1)}" cy="${y(row[yKey]).toFixed(1)}" r="5" class="cow-dot"><title>${esc(row.id)} · ${esc(fmt(row[xKey], 2))} ${esc(xLabel)} · ${esc(fmt(row[yKey], 2))} ${esc(yLabel)}</title></circle>`).join("");
  return `<svg class="cow-scatter" viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(xLabel)} versus ${esc(yLabel)}"><line x1="${pad}" y1="${height - pad}" x2="${width - pad}" y2="${height - pad}"/><line x1="${pad}" y1="${pad}" x2="${pad}" y2="${height - pad}"/>${dots}<text x="${width / 2}" y="${height - 6}" text-anchor="middle">${esc(xLabel)}</text><text x="12" y="${height / 2}" text-anchor="middle" transform="rotate(-90 12 ${height / 2})">${esc(yLabel)}</text></svg>`;
}

function renderCowHealth(cows) {
  const counts = Object.entries(cows.health_counts || {});
  if (!counts.length) return `<div class="cow-chart-unavailable">N/A<br><span>No health states were reported.</span></div>`;
  const maximum = Math.max(1, ...counts.map(([, count]) => Number(count)));
  return counts.map(([name, count]) => `<div class="cow-health"><div><b>${esc(name)}</b><span>${fmt(count)} cows</span></div><i><em style="width:${Math.round(Number(count) / maximum * 100)}%"></em></i></div>`).join("");
}

function renderCowTraits(cows) {
  const traits = Object.entries(cows.trait_distributions || {});
  if (!traits.length) return `<div class="cow-chart-unavailable">N/A<br><span>No genetic trait values were retained.</span></div>`;
  return traits.map(([name, distribution]) => {
    const range = Number(distribution.max) - Number(distribution.min);
    const values = (distribution.values || []).map(item => {
      const width = range > 0 ? ((Number(item.value) - Number(distribution.min)) / range) * 100 : 100;
      return `<div class="cow-trait"><span>${esc(item.id)}</span><i><em style="width:${Math.max(0, Math.min(100, width))}%"></em></i><b>${esc(fmt(item.value, 3))}</b></div>`;
    }).join("");
    return `<article class="cow-trait-group"><header><b>${esc(name)}</b><span>mean ${esc(fmt(distribution.mean, 3))}</span></header>${values}</article>`;
  }).join("");
}

function renderCows() {
  const target = $("cows-content");
  if (!target) return;
  const data = state.data;
  const cows = data && data.cows;
  if (!cows || !cows.available || !Array.isArray(cows.records) || !cows.records.length) {
    target.innerHTML = `<div class="empty-state"><span class="eyebrow">COW PERFORMANCE</span><h2>No latest-day cow records.</h2><p>Run a simulation with an active herd to populate the traceable cow explorer.</p></div>`;
    return;
  }
  const sortKey = COW_SORTS.some(([key]) => key === state.cowSort) ? state.cowSort : "milk_l";
  state.cowSort = sortKey;
  const ranking = cows.rankings && Array.isArray(cows.rankings[sortKey]) ? cows.rankings[sortKey] : [];
  const byId = new Map(cows.records.map(row => [String(row.id), row]));
  const ordered = ranking.map(id => byId.get(String(id))).filter(Boolean);
  const rankedIds = new Set(ordered.map(row => String(row.id)));
  const rows = ordered.concat(cows.records.filter(row => !rankedIds.has(String(row.id))));
  const sortButtons = COW_SORTS.map(([key, label]) => `<button type="button" data-cow-sort="${key}" class="${key === sortKey ? "on" : ""}">${esc(label)}</button>`).join("");
  const headers = COW_COLUMNS.map(([, label]) => `<th scope="col">${esc(label)}</th>`).join("");
  const body = rows.map(row => `<tr>${COW_COLUMNS.map(([key]) => `<td>${cowCell(row[key], key === "milk_l" || key === "dmi_kg" || key === "body_weight_kg" ? 1 : key === "fcr_kg_dm_per_l" || key === "body_condition_score" || key === "rumen_ph" ? 2 : 0, key === "milk_l" ? "L" : key === "dmi_kg" ? "kg" : key === "body_weight_kg" ? "kg" : "")}</td>`).join("")}</tr>`).join("");
  const meta = cows.provenance ? `${cows.date || "latest day"} · ${cows.provenance.confidence || "unavailable confidence"}` : (cows.date || "latest day");
  target.innerHTML = `<div class="cows-workspace"><header class="cows-head"><div><span class="eyebrow">COW PERFORMANCE</span><h2>Trace the latest herd snapshot.</h2><p>${esc(cows.history_note || "Per-cow values come from the authoritative model records.")}</p></div><span class="overview-source">${esc(meta)}</span></header><section class="cow-health-panel"><header><div><span class="eyebrow">HEALTH STATES</span><h3>Current herd signals</h3></div><span>${fmt(rows.length)} records</span></header><div class="cow-health-grid">${renderCowHealth(cows)}</div></section><section class="cow-explorer-panel"><header class="cow-panel-head"><div><span class="eyebrow">LATEST-DAY TABLE</span><h3>Per-cow records</h3><p>Sort uses direct reported metrics; unavailable values remain N/A.</p></div><div class="cow-sort">${sortButtons}</div></header><div class="cow-table-wrap"><table class="cow-table"><thead><tr>${headers}</tr></thead><tbody>${body}</tbody></table></div></section><section class="cow-analytics"><article class="cow-chart-card"><header><b>Milk vs FCR</b><span>Direct cow metrics</span></header>${cowScatter(rows, "milk_l", "fcr_kg_dm_per_l", "L/day", "kg DM/L")}</article><article class="cow-chart-card"><header><b>DMI vs milk</b><span>Direct cow metrics</span></header>${cowScatter(rows, "dmi_kg", "milk_l", "kg DM/day", "L/day")}</article></section><section class="cow-traits"><header><span class="eyebrow">GENETIC TRAITS</span><h3>Retained trait distributions</h3></header>${renderCowTraits(cows)}</section></div>`;
}

function environmentMetricDisplay(metric, decimals = 2) {
  if (!metric || metric.available === false || metric.value === null || metric.value === undefined || Number.isNaN(Number(metric.value))) return "N/A";
  return `${fmt(Number(metric.value), decimals)}${metric.unit ? ` ${esc(metric.unit)}` : ""}`;
}

function environmentMetricCard(label, key, metric, decimals = 2) {
  const unavailable = !metric || metric.available === false || metric.value === null || metric.value === undefined;
  return `<article class="environment-kpi${unavailable ? " is-unavailable" : ""}"><span>${esc(label)}</span><strong>${environmentMetricDisplay(metric, decimals)}</strong><small>${esc(key)}</small></article>`;
}

function environmentCell(row, key, decimals = 2) {
  const value = row && row[key];
  return value === null || value === undefined || Number.isNaN(Number(value)) ? "N/A" : fmt(Number(value), decimals);
}

function renderEnvironmentPeriodTable(rows, label, dateKey) {
  if (!Array.isArray(rows) || !rows.length) return `<div class="environment-unavailable">N/A<br><span>No ${esc(label.toLowerCase())} environment records were retained.</span></div>`;
  const body = rows.map(row => `<tr><th scope="row">${esc(row[dateKey] || "N/A")}</th><td>${environmentCell(row, "gross_kg_co2e", 1)}</td><td>${environmentCell(row, "avoided_kg_co2e", 1)}</td><td>${environmentCell(row, "net_kg_co2e", 1)}</td><td>${environmentCell(row, "kg_co2e_per_l_milk", 3)}</td><td>${environmentCell(row, "circularity_score", 3)}</td><td>${environmentCell(row, "sustainability_score_0_100", 1)}</td></tr>`).join("");
  return `<div class="environment-table-wrap"><table class="environment-table"><thead><tr><th scope="col">${esc(label)}</th><th scope="col">Gross GHG (kg CO2e)</th><th scope="col">Avoided GHG (kg CO2e)</th><th scope="col">Net GHG (kg CO2e)</th><th scope="col">GHG/L (kg CO2e/L)</th><th scope="col">Circularity (fraction)</th><th scope="col">Sustainability (score / 100)</th></tr></thead><tbody>${body}</tbody></table></div>`;
}

function renderEnvironmentLedger(rows) {
  if (!Array.isArray(rows) || !rows.length) return `<div class="environment-unavailable">N/A<br><span>No recorded environmental source streams are available.</span></div>`;
  const body = rows.map(row => `<tr><td>${esc(row.date || "N/A")}</td><td>${esc(row.source || "N/A")}</td><td>${esc(row.stream_id || "N/A")}</td><td>${row.value === null || row.value === undefined ? "N/A" : `${esc(fmt(Number(row.value), 2))} ${esc(row.unit || "")}`}</td><td>${esc(row.direction || "N/A")}</td><td>${esc(row.quality || "N/A")}</td><td>${esc(row.confidence || "N/A")}</td></tr>`).join("");
  return `<div class="environment-ledger-wrap"><table class="environment-ledger"><thead><tr><th scope="col">Date</th><th scope="col">Source</th><th scope="col">Stream</th><th scope="col">Value</th><th scope="col">Direction</th><th scope="col">Quality</th><th scope="col">Confidence</th></tr></thead><tbody>${body}</tbody></table></div>`;
}

function renderEnvironment() {
  const target = $("environment-content");
  if (!target) return;
  const data = state.data;
  const audit = data && data.environment;
  if (!audit || !audit.available) {
    target.innerHTML = `<div class="empty-state"><span class="eyebrow">ENVIRONMENT AUDIT</span><h2>No environment records.</h2><p>Run a simulation to inspect authoritative emissions, soil, circularity, and source-stream ledger values.</p></div>`;
    return;
  }
  const metrics = audit.metrics || {};
  const cards = [
    ["Gross GHG", "gross_kg_co2e", 1], ["Avoided GHG", "avoided_kg_co2e", 1], ["Net GHG", "net_kg_co2e", 1],
    ["GHG intensity", "ghg_intensity", 3], ["Soil carbon change", "soil_carbon_delta_kg", 2], ["Fertilizer saved", "synthetic_fertilizer_saved_kg", 2],
    ["NUE", "nue", 3], ["Circularity", "circularity_score", 3], ["Sustainability", "sustainability_score_0_100", 1],
    ["Carbon credit value", "carbon_credit_value", 2], ["Soil carbon stock", "soil_organic_carbon_pct", 2], ["Soil biodiversity", "soil_biodiversity_index", 2],
  ].map(([label, key, decimals]) => environmentMetricCard(label, key, metrics[key], decimals)).join("");
  const daily = Array.isArray(audit.daily) ? audit.daily : [];
  const chart = daily.length
    ? svgChart({rows: daily, period: "daily", title: "Daily environmental ledger", kind: "area", unit: "kg CO2e", dec: 1, ydec: 1, floor: false, series: [{key: "gross_kg_co2e", color: "#b7791f", label: "Gross"}, {key: "avoided_kg_co2e", color: "#3f6b4f", label: "Avoided"}, {key: "net_kg_co2e", color: "#b42318", label: "Net"}]})
    : `<div class="environment-unavailable">N/A<br><span>No daily environment series is available.</span></div>`;
  const warnings = (audit.warnings || []).map(warning => `<li>${esc(warning.message || warning.detail || "Environment warning")}</li>`).join("");
  const packet = audit.provenance && audit.provenance.packet;
  const provenance = packet ? `${packet.source || "environment"} · ${packet.name || "packet"} · ${packet.confidence || "unavailable confidence"}` : (audit.source || "environment history");
  target.innerHTML = `<div class="environment-audit"><header class="environment-head"><div><span class="eyebrow">ENVIRONMENT AUDIT</span><h2>Recorded outcomes, not reconstructed totals.</h2><p>Emissions, soil, circularity, and sustainability values are serialized from environment history and packets. Source streams retain their ledger metadata.</p></div><span class="overview-source">${esc(provenance)}</span></header>${warnings ? `<div class="environment-warnings"><b>Model warnings</b><ul>${warnings}</ul></div>` : ""}<section class="environment-kpis">${cards}</section><section class="environment-chart-panel"><header><div><span class="eyebrow">DAILY SERIES</span><h3>Gross, avoided, and net GHG</h3><p>Daily values come directly from the backend environment history.</p></div></header>${chart}</section><section class="environment-period-panel"><header><div><span class="eyebrow">MONTHLY REPORTS</span><h3>Calendar-month environment records</h3><p>Monthly rows are official environment report outputs; the browser does not roll them up.</p></div></header>${renderEnvironmentPeriodTable(audit.monthly, "Month", "month")}</section><section class="environment-ledger-panel"><header><div><span class="eyebrow">SOURCE STREAM LEDGER</span><h3>Audit every recorded stream.</h3><p>Only streams exposed by the model are shown. Positive and avoided directions remain distinct.</p></div></header>${renderEnvironmentLedger(audit.ledger)}</section></div>`;
}

function economicsValue(value, decimals = 2, unit = "") {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "N/A";
  return `${fmt(Number(value), decimals)}${unit ? ` ${esc(unit)}` : ""}`;
}

function economicsMetricCard(label, key, metric, decimals = 2) {
  const unavailable = !metric || metric.available === false || metric.value === null || metric.value === undefined;
  return `<article class="economics-kpi${unavailable ? " is-unavailable" : ""}"><span>${esc(label)}</span><strong>${unavailable ? "N/A" : economicsValue(metric.value, decimals, metric.unit)}</strong><small>${esc(key)}</small></article>`;
}

function economicsSeriesTable(rows, dateKey, columns) {
  if (!Array.isArray(rows) || !rows.length) return `<div class="economics-unavailable">N/A<br><span>No authoritative economics records were retained.</span></div>`;
  const body = rows.map(row => `<tr><th scope="row">${esc(row[dateKey] || "N/A")}</th>${columns.map(([key, label, decimals = 2]) => `<td>${economicsValue(row[key], decimals)}</td>`).join("")}</tr>`).join("");
  const headers = columns.map(([key, label]) => `<th scope="col">${esc(label || key.replaceAll("_", " "))}</th>`).join("");
  return `<div class="economics-table-wrap"><table class="economics-table"><thead><tr><th scope="col">${esc(dateKey)}</th>${headers}</tr></thead><tbody>${body}</tbody></table></div>`;
}

function economicsLatestTable(latest, rows) {
  if (!latest) return `<div class="economics-unavailable">N/A<br><span>No manager packet was retained for this run.</span></div>`;
  const body = rows.map(([label, key, decimals]) => `<tr><th scope="row">${esc(label)}</th><td>${economicsValue(latest[key], decimals)}</td></tr>`).join("");
  return `<div class="economics-table-wrap"><table class="economics-table economics-latest"><thead><tr><th scope="col">Latest manager field</th><th scope="col">Value (currency)</th></tr></thead><tbody>${body}</tbody></table></div>`;
}

function renderEconomics() {
  const target = $("economics-content");
  if (!target) return;
  const data = state.data;
  const audit = data && data.economics;
  if (!audit || !audit.available) {
    target.innerHTML = `<div class="empty-state"><span class="eyebrow">ECONOMICS</span><h2>No economics records.</h2><p>Run a simulation to inspect authoritative revenue, cost, profit, cash, market, and NPV outputs.</p></div>`;
    return;
  }
  const metrics = audit.metrics || {};
  const cards = [
    ["Total revenue", "total_revenue", 2], ["Total cost", "total_cost", 2], ["Profit", "profit", 2],
    ["Cumulative profit", "cumulative_profit", 2], ["Ending cash", "cash_balance", 2], ["Farm NPV", "farm_npv", 2],
  ].map(([label, key, decimals]) => economicsMetricCard(label, key, metrics[key], decimals)).join("");
  const daily = Array.isArray(audit.daily) ? audit.daily : [];
  const chart = daily.length
    ? svgChart({rows: daily, period: "daily", title: "Daily revenue, cost, and profit", kind: "area", unit: "currency", dec: 2, ydec: 2, floor: false, series: [{key: "total_revenue", color: "#3f6b4f", label: "Revenue"}, {key: "total_cost", color: "#b7791f", label: "Cost"}, {key: "profit", color: "#b42318", label: "Profit"}]})
    : `<div class="economics-unavailable">N/A<br><span>No daily economics series is available.</span></div>`;
  const latest = audit.latest;
  const revenueFields = [["Raw milk revenue", "raw_milk_revenue", 2], ["Processor revenue", "processor_revenue", 2], ["Byproduct revenue", "byproduct_revenue", 2], ["Energy value", "energy_value", 2], ["Carbon credit value", "carbon_credit_value", 2], ["Total revenue", "total_revenue", 2]];
  const costFields = [["Feed cost", "feed_cost", 2], ["Water cost", "water_cost", 2], ["Treatment cost", "treatment_cost", 2], ["Disease economic cost", "disease_cost", 2], ["Cooling cost", "cooling_cost", 2], ["Processing energy cost", "processing_energy_cost", 2], ["Labor cost", "labor_cost", 2], ["Fixed cost", "fixed_cost", 2], ["Total cost", "total_cost", 2]];
  const monthly = Array.isArray(audit.monthly) ? audit.monthly : [];
  const market = audit.market || {};
  const marketRows = [["Milk price", "milk_price_per_l", 4, "currency/L"], ["Feed price", "feed_cost_per_kg_dm", 4, "currency/kg DM"], ["Electricity price", "electricity_price_per_kwh", 4, "currency/kWh"], ["Carbon credit price", "carbon_credit_price_per_tonne_co2e", 2, "currency/t CO2e"], ["Market mode", "market_mode", 0, ""], ["Regime", "market_regime_label", 0, ""]];
  const marketMarkup = marketRows.map(([label, key, decimals, unit]) => `<div class="economics-market-row"><span>${esc(label)}</span><b>${typeof market[key] === "string" ? esc(market[key]) : economicsValue(market[key], decimals, unit)}</b></div>`).join("");
  const warnings = (audit.warnings || []).map(warning => `<li>${esc(warning.message || warning.detail || "Economics warning")}</li>`).join("");
  const recommendation = latest && latest.recommendation ? `<p><b>Recommendation:</b> ${esc(latest.recommendation)}</p>` : `<p><b>Recommendation:</b> N/A</p>`;
  const conflicts = latest && Array.isArray(latest.policy_conflicts) && latest.policy_conflicts.length ? `<p><b>Policy conflicts:</b> ${esc(JSON.stringify(latest.policy_conflicts))}</p>` : `<p><b>Policy conflicts:</b> none reported</p>`;
  target.innerHTML = `<div class="economics-audit"><header class="economics-head"><div><span class="eyebrow">ECONOMICS</span><h2>Trace reported money flows.</h2><p>Revenue, cost, cash, market, and NPV values come from manager, daily report, market, disease, and existing analysis outputs. Unretained categories remain N/A.</p></div><span class="overview-source">${esc(audit.source || "ctx.daily_records")}</span></header>${warnings ? `<div class="economics-warnings"><b>Model warnings</b><ul>${warnings}</ul></div>` : ""}<section class="economics-kpis">${cards}</section><section class="economics-chart-panel"><header><div><span class="eyebrow">DAILY SERIES</span><h3>Revenue, cost, and profit</h3><p>Daily rows are serialized by Python; the browser does not roll them up.</p></div></header>${chart}</section><section class="economics-breakdown"><article><header><span class="eyebrow">REVENUE</span><h3>Latest manager revenue fields</h3></header>${economicsLatestTable(latest, revenueFields)}</article><article><header><span class="eyebrow">COSTS</span><h3>Latest manager cost fields</h3></header>${economicsLatestTable(latest, costFields)}</article></section><section class="economics-period-panel"><header><div><span class="eyebrow">MONTHLY REPORTS</span><h3>Farm-manager calendar records</h3><p>Monthly values are official manager rows, not frontend aggregates.</p></div></header>${economicsSeriesTable(monthly, "month", [["total_revenue", "Total revenue"], ["total_cost", "Total cost"], ["profit", "Profit"]])}</section><section class="economics-lower"><article class="economics-market"><header><span class="eyebrow">MARKET SNAPSHOT</span><h3>Latest price context</h3></header>${marketMarkup || `<div class="economics-unavailable">N/A</div>`}</article><article class="economics-decisions"><header><span class="eyebrow">MANAGER OUTPUT</span><h3>Policy context</h3></header>${recommendation}${conflicts}<p><b>NPV discount rate:</b> ${economicsValue(audit.discount_rate, 3)}</p></article></section></div>`;
}

function parameterFilters() {
  if (!state.filters || typeof state.filters !== "object") state.filters = {};
  if (!state.filters.parameters) state.filters.parameters = {search: "", group: "all", assumption: "all", changed: false};
  return state.filters.parameters;
}

function parameterRow(key) {
  return (Array.isArray(state.calibration) ? state.calibration : []).find(row => row.key === key);
}

function parameterChanged(row) {
  return Object.prototype.hasOwnProperty.call(state.parameterDraft, row.key);
}

function parameterCurrent(row) {
  return parameterChanged(row) ? state.parameterDraft[row.key] : row.default;
}

function parameterControlId(key) {
  return `parameter-control-${String(key).replace(/[^A-Za-z0-9_-]/g, "-")}`;
}

function parameterNumericRange(row) {
  const range = String(row.valid_range || "");
  if (typeof row.default === "boolean" || typeof row.default === "string" || !range || range === "true,false") return {min: null, max: null};
  const parts = range.includes("..") ? range.split("..", 2) : [range, range];
  const min = parts[0] === "" ? null : Number(parts[0]);
  const max = parts[1] === "" ? null : Number(parts[1]);
  return {min: Number.isFinite(min) ? min : null, max: Number.isFinite(max) ? max : null};
}

function parameterValidation(row, value) {
  const defaultValue = row.default;
  if (typeof defaultValue === "boolean") return typeof value === "boolean" ? "" : "Value must be boolean";
  if (typeof defaultValue === "number") {
    if (value === "" || value === null || !Number.isFinite(Number(value))) return "Value must be numeric";
    if (Number.isInteger(defaultValue) && !Number.isInteger(Number(value))) return "Value must be an integer";
    const {min, max} = parameterNumericRange(row);
    if (min !== null && Number(value) < min || max !== null && Number(value) > max) return `Value must be within ${row.valid_range}`;
    return "";
  }
  if (typeof defaultValue === "string") {
    const range = String(row.valid_range || "");
    const choices = range.split(",").map(value_ => value_.trim()).filter(Boolean);
    if (choices.length > 1 && !choices.includes(String(value)) || choices.length === 1 && choices[0] !== String(value)) return `Value must equal ${row.valid_range}`;
  }
  return "";
}

function parameterCandidate(input, row) {
  if (typeof row.default === "boolean") return Boolean(input.checked);
  if (typeof row.default === "number") return input.value === "" ? "" : Number(input.value);
  return String(input.value);
}

function syncParameterInput(input, rerender = false) {
  const row = parameterRow(input.dataset.parameterKey);
  if (!row) return;
  const value = parameterCandidate(input, row);
  const error = parameterValidation(row, value);
  if (error) {
    state.parameterErrors[row.key] = error;
    delete state.parameterDraft[row.key];
  } else {
    delete state.parameterErrors[row.key];
    if (value === row.default) delete state.parameterDraft[row.key];
    else state.parameterDraft[row.key] = value;
  }
  if (rerender) renderParameters();
}

function parameterInput(row) {
  const current = parameterCurrent(row);
  const id = parameterControlId(row.key);
  const attrs = `id="${id}" data-parameter-key="${esc(row.key)}" data-parameter-input`;
  if (typeof row.default === "boolean") {
    return `<label class="parameter-toggle"><input type="checkbox" ${attrs} ${current ? "checked" : ""}><span>Enabled</span></label>`;
  }
  if (row.unit === "enum") {
    const choices = [...new Set([String(current), ...String(row.valid_range || "").split(",").map(value => value.trim()).filter(Boolean)])];
    return `<select ${attrs}>${choices.map(choice => `<option value="${esc(choice)}" ${String(current) === choice ? "selected" : ""}>${esc(choice)}</option>`).join("")}</select>`;
  }
  if (typeof row.default === "number") {
    const range = parameterNumericRange(row);
    const min = range.min === null ? "" : ` min="${range.min}"`;
    const max = range.max === null ? "" : ` max="${range.max}"`;
    const step = Number.isInteger(row.default) ? "1" : "any";
    return `<input type="number" ${attrs} value="${esc(String(current))}" step="${step}"${min}${max}>`;
  }
  return `<input type="text" ${attrs} value="${esc(String(current))}">`;
}

function parameterValueText(value) {
  if (value === null || value === undefined) return "N/A";
  return typeof value === "boolean" ? (value ? "true" : "false") : String(value);
}

function parameterCard(row) {
  const changed = parameterChanged(row);
  const error = state.parameterErrors[row.key] || "";
  const assumption = row.assumption ? "assumption" : "anchored";
  return `<article class="parameter-row${changed ? " is-changed" : ""}"><header><div><code>${esc(row.key)}</code><span class="parameter-unit">${esc(row.unit || "")}</span></div><div class="parameter-badges"><span class="parameter-source">${esc(row.source || "source unavailable")}</span><span class="parameter-assumption ${assumption}">${esc(assumption)}</span>${changed ? `<span class="parameter-changed">changed</span>` : ""}</div></header><div class="parameter-control"><label for="${parameterControlId(row.key)}">${esc(row.key.split(".").slice(-1)[0].replaceAll("_", " "))}</label>${parameterInput(row)}<button type="button" class="parameter-reset" data-parameter-reset="${esc(row.key)}"${changed ? "" : " disabled"}>Reset field</button></div><p class="parameter-description">${esc(row.description || "No description provided.")}</p><dl class="parameter-meta"><div><dt>Default</dt><dd>${esc(parameterValueText(row.default))}</dd></div><div><dt>Valid range</dt><dd><code>${esc(row.valid_range || "not specified")}</code></dd></div></dl>${error ? `<p class="parameter-error" role="alert">${esc(error)}</p>` : ""}</article>`;
}

function renderParameters() {
  const target = $("parameters-content");
  if (!target) return;
  if (!Array.isArray(state.calibration)) {
    target.innerHTML = `<div class="empty-state"><span class="eyebrow">PARAMETERS</span><h2>Loading calibration inventory.</h2><p>Fetching parameter metadata from <code>/api/calibration</code>.</p></div>`;
    if (!state.parameterLoading) {
      state.parameterLoading = true;
      loadCalibration().then(data => {
        state.calibration = Array.isArray(data.parameters) ? data.parameters : [];
        state.parameterLoading = false;
        renderParameters();
      }).catch(error => {
        state.parameterLoading = false;
        setError(error.message || "Unable to load calibration inventory");
        target.innerHTML = `<div class="empty-state"><span class="eyebrow">PARAMETERS</span><h2>Calibration unavailable.</h2><p>${esc(error.message || "Unable to load calibration inventory")}</p></div>`;
      });
    }
    return;
  }
  const filters = parameterFilters();
  const search = String(filters.search || "").trim().toLowerCase();
  const rows = state.calibration.filter(row => {
    const haystack = [row.key, row.agent, row.unit, row.source, row.description, row.default].join(" ").toLowerCase();
    if (search && !haystack.includes(search)) return false;
    if (filters.group !== "all" && row.agent !== filters.group) return false;
    if (filters.assumption === "assumption" && !row.assumption || filters.assumption === "anchored" && row.assumption) return false;
    return !filters.changed || parameterChanged(row);
  });
  const groups = [...new Set(rows.map(row => row.agent))].sort();
  const groupOptions = [...new Set(state.calibration.map(row => row.agent))].sort().map(group => `<option value="${esc(group)}" ${filters.group === group ? "selected" : ""}>${esc(group)}</option>`).join("");
  const changedCount = Object.keys(state.parameterDraft).length;
  const errorCount = Object.keys(state.parameterErrors).length;
  const groupMarkup = groups.length ? groups.map(group => `<section class="parameter-group"><header><div><span class="eyebrow">${esc(group)}</span><h3>${rows.filter(row => row.agent === group).length} visible parameters</h3></div><button type="button" class="ghost" data-parameter-reset-group="${esc(group)}">Reset group</button></header><div class="parameter-list">${rows.filter(row => row.agent === group).map(parameterCard).join("")}</div></section>`).join("") : `<div class="parameter-empty">N/A<br><span>No parameters match the current filters.</span></div>`;
  target.innerHTML = `<div class="parameter-editor"><header class="parameter-head"><div><span class="eyebrow">CALIBRATION INVENTORY</span><h2>Edit validated model parameters.</h2><p>Values are generated from the Python calibration inventory. Changes become isolated per-run overrides and are validated again by the backend before simulation.</p></div><span class="overview-source">${state.calibration.length} parameters</span></header><section class="parameter-toolbar"><label class="parameter-search"><span>Search</span><input id="parameter-search" data-parameter-filter="search" type="search" value="${esc(filters.search || "")}" placeholder="key, source, description"></label><label><span>Group</span><select data-parameter-filter="group"><option value="all">All groups</option>${groupOptions}</select></label><label><span>Assumption</span><select data-parameter-filter="assumption"><option value="all" ${filters.assumption === "all" ? "selected" : ""}>All</option><option value="assumption" ${filters.assumption === "assumption" ? "selected" : ""}>Assumptions</option><option value="anchored" ${filters.assumption === "anchored" ? "selected" : ""}>Anchored</option></select></label><label class="parameter-checkbox"><input type="checkbox" data-parameter-filter="changed" ${filters.changed ? "checked" : ""}><span>Changed only</span></label><button type="button" class="ghost" id="parameter-reset-all">Reset all</button></section><div class="parameter-summary"><b>${changedCount} override${changedCount === 1 ? "" : "s"}</b> will be sent with the next run. ${errorCount ? `<strong>${errorCount} validation error${errorCount === 1 ? "" : "s"}:</strong> Fix calibration values before running.` : "Backend validation remains authoritative."}<button type="button" data-page="simulation">Go to simulation</button></div>${groupMarkup}</div>`;
}

function modelDetailsText(value) {
  if (value === null || value === undefined || value === "") return "N/A";
  return typeof value === "object" ? JSON.stringify(value) : String(value);
}

function modelDetailsState(value) {
  return value === "active" ? "is-active" : value === "inactive" ? "is-inactive" : "is-unavailable";
}

function renderModelDetails() {
  const target = $("model-details-content");
  if (!target) return;
  const data = state.data;
  const details = data && data.model_details;
  if (!details || !details.available) {
    target.innerHTML = `<div class="empty-state"><span class="eyebrow">MODEL DETAILS</span><h2>No run details yet.</h2><p>Run a simulation to inspect the actual scenario, enabled systems, scheduler, policy, warnings, and report contract.</p></div>`;
    return;
  }
  const meta = [
    ["Scenario", details.scenario], ["Start date", details.start_date], ["Duration", details.days, "days"],
    ["Seed", details.seed], ["Initial herd", details.herd_size, "cows"], ["Run duration", details.run_duration_s, "s"],
    ["Calibration overrides", details.calibration_override_count], ["Assumptions", details.assumption_count],
    ["Events", details.event_count], ["Active agents", details.active_agent_count],
  ].map(([label, value, unit]) => `<div class="model-detail-metric"><span>${esc(label)}</span><strong>${esc(modelDetailsText(value))}${unit && value !== null && value !== undefined ? ` ${esc(unit)}` : ""}</strong></div>`).join("");
  const systems = Object.entries(details.enabled_systems || {})
    .filter(([key]) => key.startsWith("enable_"))
    .map(([key, enabled]) => `<span class="model-detail-status ${enabled ? "is-active" : "is-inactive"}"><b>${esc(key.replace(/^enable_/, "").replaceAll("_", " "))}</b><small>${enabled ? "enabled" : "disabled"}</small></span>`)
    .join("");
  const loops = Object.entries(details.loop_states || {})
    .map(([key, value]) => `<article class="model-loop-state ${modelDetailsState(value)}"><span class="eyebrow">${esc(key.toUpperCase())}</span><b>${esc(String(value || "unavailable"))}</b></article>`)
    .join("");
  const order = (details.scheduler && Array.isArray(details.scheduler.latest_execution_order)) ? details.scheduler.latest_execution_order : [];
  const orderMarkup = order.length ? order.map((item, index) => `<li><span>${index + 1}</span><b>${esc(item)}</b></li>`).join("") : `<li class="model-detail-na">N/A</li>`;
  const scheduleRecords = details.scheduler && Array.isArray(details.scheduler.records) ? details.scheduler.records : [];
  const scheduleRows = scheduleRecords.slice(-16).map(row => `<tr><td>${esc(row.day)}</td><td>${esc(row.phase)}</td><td>${esc(row.agents)}</td></tr>`).join("");
  const policy = details.policy_summary || {};
  const policyFields = [["Recommendation", policy.recommendation], ["History records", policy.history_count], ["Automatic actions", policy.automatic_policy_actions], ["Conflicts", policy.policy_conflicts], ["Triggers", policy.policy_change_triggers]].map(([label, value]) => `<div class="model-policy-field"><span>${esc(label)}</span><b>${esc(modelDetailsText(value))}</b></div>`).join("");
  const effectivePolicy = Object.entries(policy.effective_policy || {}).map(([key, value]) => `<div class="model-policy-value"><span>${esc(key.replaceAll("_", " "))}</span><b>${esc(modelDetailsText(value))}</b></div>`).join("");
  const warnings = Array.isArray(details.warnings) ? details.warnings : [];
  const warningMarkup = warnings.length ? `<ul>${warnings.map(warning => `<li><b>${esc(warning.source || "model")}</b><span>${esc(warning.message || warning.detail || "Warning")}</span></li>`).join("")}</ul>` : `<div class="model-detail-na">No warning events recorded.</div>`;
  const contract = details.report_contract && typeof details.report_contract === "object" ? details.report_contract : {};
  const contractMarkup = Object.entries(contract).map(([period, definition]) => {
    const fields = definition && typeof definition.fields === "object" ? Object.keys(definition.fields) : [];
    return `<article class="model-contract-card"><header><b>${esc(period)}</b><span>${fields.length} fields</span></header><p>${esc(definition && definition.period || "No period metadata")}</p><small>${esc(definition && definition.confidence || "No confidence metadata")}</small></article>`;
  }).join("");
  target.innerHTML = `<div class="model-details"><header class="model-details-head"><div><span class="eyebrow">READ-ONLY RUN DESCRIPTION</span><h2>${esc(details.scenario || "Unnamed run")}</h2><p>Configuration, scheduler execution, policy outputs, warnings, and report metadata are serialized by Python from the completed run. This page performs no model calculations.</p></div><span class="overview-source">${esc(details.source || "Python dashboard contract")}</span></header><section class="model-detail-metrics">${meta}</section><section class="model-detail-section"><header><div><span class="eyebrow">ENABLED SYSTEMS</span><h3>Actual run capabilities</h3></div></header><div class="model-system-grid">${systems || `<div class="model-detail-na">N/A</div>`}</div></section><section class="model-detail-section"><header><div><span class="eyebrow">LOOP STATES</span><h3>Configured circular pathways</h3></div></header><div class="model-loop-grid">${loops || `<div class="model-detail-na">N/A</div>`}</div></section><section class="model-detail-two"><article class="model-detail-section"><header><div><span class="eyebrow">SCHEDULER</span><h3>Latest daily execution order</h3><p>${scheduleRecords.length} recorded schedule rows; showing the latest ${Math.min(16, scheduleRecords.length)}.</p></div></header><ol class="model-order">${orderMarkup}</ol><div class="model-schedule-table"><table><thead><tr><th>Date</th><th>Phase</th><th>Agents/stages</th></tr></thead><tbody>${scheduleRows || `<tr><td colspan="3">N/A</td></tr>`}</tbody></table></div></article><article class="model-detail-section"><header><div><span class="eyebrow">POLICY SUMMARY</span><h3>Manager decisions</h3></div></header><div class="model-policy-fields">${policyFields}</div><h4>Effective policy</h4><div class="model-policy-values">${effectivePolicy || `<div class="model-detail-na">N/A</div>`}</div></article></section><section class="model-detail-section"><header><div><span class="eyebrow">WARNINGS</span><h3>Recorded model warnings</h3></div></header><div class="model-warning-list">${warningMarkup}</div></section><section class="model-detail-section"><header><div><span class="eyebrow">REPORT CONTRACT</span><h3>Official report metadata</h3><p>Source: <code>dairy_abm.reports.REPORT_CONTRACT</code>.</p></div></header><div class="model-contract-grid">${contractMarkup || `<div class="model-detail-na">N/A</div>`}</div></section></div>`;
}

function renderExports() {
  const target = $("exports-content");
  if (!target) return;
  const data = state.data;
  const manifest = data && data.exports;
  if (!manifest || !manifest.available) {
    target.innerHTML = `<div class="empty-state"><span class="eyebrow">EXPORT CENTER</span><h2>No completed run to export.</h2><p>Run a simulation first. Official files are generated by <code>dairy_abm.reports.write_reports</code> from the cached simulation context.</p></div>`;
    return;
  }
  const artifacts = Array.isArray(manifest.artifacts) ? manifest.artifacts : [];
  const files = artifacts.map(artifact => `<a class="export-artifact${artifact.id === "zip" ? " is-primary" : ""}" href="${esc(artifact.endpoint)}" download="${esc(artifact.filename)}"><span class="export-artifact-icon">${artifact.id === "zip" ? "ZIP" : esc(artifact.filename.split(".").pop().toUpperCase())}</span><span><b>${esc(artifact.label)}</b><small>${esc(artifact.filename)} · ${esc(artifact.content_type || "download")}</small></span><strong>Download</strong></a>`).join("");
  const graphButton = data.daily && data.daily.length ? `<button type="button" class="export-presentation" id="export-graphs"><b>Chart PNG</b><span>Presentation image from the current chart registry</span></button>` : `<div class="export-presentation is-unavailable"><b>Chart PNG</b><span>N/A until a chartable run is selected.</span></div>`;
  target.innerHTML = `<div class="export-center"><header class="export-center-head"><div><span class="eyebrow">OFFICIAL REPORT EXPORTS</span><h2>Download the run ledger.</h2><p>These files are generated by <code>dairy_abm.reports.write_reports</code>; the browser does not rebuild reports or scientific calculations.</p></div><span class="overview-source">${esc(manifest.source || "official report writer")}</span></header><section class="export-file-grid">${files || `<div class="export-empty">N/A</div>`}</section><section class="export-presentation-panel"><header><div><span class="eyebrow">PRESENTATION OUTPUTS</span><h3>Optional visual exports</h3><p>Presentation files are separate from the official JSON and CSV report contract.</p></div></header><div class="export-presentation-grid">${graphButton}<div class="export-presentation is-unavailable"><b>Scenario comparison CSV</b><span>N/A unless a comparison export contract is added by Python.</span></div></div></section></div>`;
}

function equipmentValue(value, decimals = 2, unit = "") {
  if (value === null || value === undefined || value === "" || Number.isNaN(Number(value))) return "N/A";
  return `${fmt(Number(value), decimals)}${unit ? ` ${esc(unit)}` : ""}`;
}

function equipmentCard(asset) {
  const status = asset.status === "zero_capex" ? "ROI and payback unavailable: zero CapEx" : asset.status || "reported";
  return `<article class="equipment-card${asset.status === "zero_capex" ? " is-unavailable" : ""}"><header><div><span class="eyebrow">EQUIPMENT</span><h3>${esc(asset.label || asset.id)}</h3></div><span class="equipment-status">${esc(status)}</span></header><dl><div><dt>CapEx</dt><dd>${equipmentValue(asset.capex, 2, "currency")}</dd></div><div><dt>Annual benefit</dt><dd>${equipmentValue(asset.annual_benefit, 2, "currency/year")}</dd></div><div><dt>ROI</dt><dd>${equipmentValue(asset.roi, 3, "fraction")}</dd></div><div><dt>Payback</dt><dd>${equipmentValue(asset.payback_years, 2, "years")}</dd></div><div><dt>NPV</dt><dd>${equipmentValue(asset.npv, 2, "currency")}</dd></div></dl><small class="equipment-id">${esc(asset.id)}</small></article>`;
}

function renderEquipment() {
  const target = $("equipment-content");
  if (!target) return;
  const data = state.data;
  const equipment = data && data.equipment;
  if (!equipment || !equipment.available) {
    target.innerHTML = `<div class="empty-state"><span class="eyebrow">EQUIPMENT ROI</span><h2>No equipment analysis.</h2><p>Run a simulation with manager equipment outputs to inspect CapEx, benefit, ROI, payback, and NPV values.</p></div>`;
    return;
  }
  const assets = Array.isArray(equipment.assets) ? equipment.assets : [];
  const warnings = (equipment.warnings || []).map(warning => `<li>${esc(warning.message || "Equipment warning")}</li>`).join("");
  const cards = assets.length ? assets.map(equipmentCard).join("") : `<div class="equipment-unavailable">N/A<br><span>No represented equipment assets were retained.</span></div>`;
  const npvRows = Object.entries(equipment.equipment_npvs || {}).map(([id, value]) => `<tr><th scope="row">${esc(id)}</th><td>${equipmentValue(value, 2, "currency")}</td></tr>`).join("");
  const npvTable = npvRows ? `<div class="equipment-table-wrap"><table class="equipment-table"><thead><tr><th scope="col">Asset</th><th scope="col">NPV (currency)</th></tr></thead><tbody>${npvRows}</tbody></table></div>` : `<div class="equipment-unavailable">N/A</div>`;
  const npvSource = equipment.provenance && equipment.provenance.npv && equipment.provenance.npv.source;
  target.innerHTML = `<div class="equipment-roi"><header class="equipment-head"><div><span class="eyebrow">EQUIPMENT ROI</span><h2>Inspect reported equipment returns.</h2><p>Cards use manager-produced CapEx and annual benefits. ROI and payback are retained as unavailable when the model has no positive CapEx basis; NPV uses the existing Python analysis function.</p></div><span class="overview-source">${esc(npvSource || "dairy_abm.analysis.npv")}</span></header>${warnings ? `<div class="equipment-warnings"><b>Analysis notes</b><ul>${warnings}</ul></div>` : ""}<section class="equipment-grid">${cards}</section><section class="equipment-npv-panel"><header><div><span class="eyebrow">NPV</span><h3>Existing analysis outputs</h3><p>Discount rate: ${equipmentValue(equipment.discount_rate, 3)}. No NPV calculation is performed in the browser.</p></div></header>${npvTable}</section></div>`;
}

function toolbar() {
  const seg = (list, tok, cur) => `<div class="seg">` +
    list.map(([v,lab]) => `<button type="button" data-${tok}="${v}" class="${v===cur?"on":""}">${lab}</button>`).join("") +
    `</div>`;
  const dl = state.view==="graphs" && state.data ? `<button id="dlgraphs" class="btn">Download graphs (PNG)</button>` : "";
  return `<div class="tb">
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      ${seg(TABS,"view",state.view)}
      ${seg(PERIODS,"period",state.period)}
    </div>
    ${dl}
  </div>`;
}

function render() {
  const d = state.data;
  let html = toolbar();
  if (!d) {
    html += `<p class="note">No run yet. Pick a scenario, choose a run length (Day / Month / Year or a custom day count), then press <b>Run simulation</b>. After a run, the Ledger / Graphs tabs and Daily / Monthly / Yearly views work on the same simulation.</p>`;
  } else {
    const rows = aggregate(d.daily, state.period);
    html += `<div class="recordline">
      <span class="runname">${esc(d.name)}</span>
      <span>${d.days} days</span><span>herd ${fmt(d.herd_size)}</span>
      <span>seed ${d.seed}</span><span>${d.events} events</span>
      <span class="dur">ran in ${d.duration_s}s</span>
      <button id="download" class="dl" title="daily, monthly, annual and schedule CSV plus summary.json">Download output (.zip)</button>
    </div>`;
    html += stats(d);
    if (state.view === "graphs") {
      html += `<p class="muted">${rows.length} ${state.period} rows, rolled up from a ${d.days}-day daily run. The monthly and yearly views group the daily simulation, they do not re-simulate.</p>`;
      html += graphs(rows);
    } else {
      html += ledger(rows);
    }
  }
  $("results").innerHTML = html;
}

function stats(d) {
  const m = d.metrics;
  const figs = [
    ["Total milk", fmt(m.milk,0)+" L", ""],
    ["Net CO2e", fmt(m.net_co2e,0)+" kg", "emiss"],
    ["Profit", fmt(m.profit,0), "money"],
    ["Energy self-suff", fmt(m.energy_avg,1)+" %", ""],
    ["Freshwater drawn", fmt(m.freshwater,0)+" L", ""],
    ["Avg sustainability", fmt(m.sustainability_avg,1)+" / 100", ""],
  ].map(([lab,v,cls]) => `<div class="figure ${cls}"><b>${v}</b><span>${lab}</span></div>`).join("");
  return `<div class="totals">${figs}</div>`;
}

function ledger(rows) {
  const rowsRev = rows.slice().reverse();  // newest first, like a farm ledger
  const head = COLUMNS.map(([,lab]) => `<th scope="col">${lab}</th>`).join("");
  const body = rowsRev.map(r => `<tr>${COLUMNS.map(([k]) =>
    k==="day" ? `<td>${esc(r.day)}</td>` : `<td>${fmt(r[k],2)}</td>`).join("")}</tr>`).join("");
  return `<div class="ledger"><h3>${state.period==="daily"?"Daily":"Rolled-up"} ledger</h3><div class="tablewrap">
    <table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div></div>`;
}

function graphs(rows) {
  const g = buildCharts(rows, state.period);
  const lead = g[0] ? `<section class="graph-lead"><div class="graph-leadhead"><b>Production overview</b><span class="graph-badge">${rows.length} ${state.period} points</span></div>${g[0].s}</section>` : "";
  const support = g.slice(1).map(c => `<div class="gwrap">${c.s}</div>`).join("");
  return `${lead}<div class="ggrid">${support}</div>`;
}

// ---- interactions ----
async function onRun(ev) {
  ev.preventDefault();
  if (Object.keys(state.parameterErrors || {}).length) {
    setError("Fix calibration values before running.");
    navigate("parameters");
    renderShell("parameters");
    return;
  }
  const go = $("go");
  go.disabled = true;
  go.innerHTML = `<span class="spinner" aria-hidden="true"></span><span>Running...</span>`;
  $("stamp").textContent = "RUNNING";
  setError("");
  setWarnings([]);
  setLoading(true);
  const body = {
    scenario: $("scenario").value,
    days: parseInt($("days").value, 10),
    start_date: $("start-date").value,
    seed: $("seed").value === "" ? null : parseInt($("seed").value, 10),
    herd_size: $("herd").value === "" ? null : parseInt($("herd").value, 10),
    calibration_overrides: Object.assign({}, state.parameterDraft),
  };
  if (!body.start_date) delete body.start_date;
  document.querySelectorAll("#switches input").forEach(inp => body[inp.dataset.k] = inp.checked);
  try {
    const data = await runSimulation(body);
    state.currentRunId = data.id;
    state.currentRun = data;
    state.data = data;
    state.view = "graphs";
    state.period = "daily";
    state.selectedPeriod = "daily";
    updateScenarioLabel(data.name);
    updateRunMeta(data);
    setWarnings(data.warnings);
    navigate("simulation");
    renderShell("simulation");
    $("stamp").textContent = "SIMULATED";
  } catch (err) {
    state.currentRunId = null;
    state.currentRun = null;
    state.data = null;
    updateRunMeta(null);
    setWarnings([]);
    setError(err.message || "The model run failed");
    $("report-meta").textContent = "READY FOR A RUN";
    $("report-content").innerHTML = '<div class="empty-state"><h2>No report yet.</h2><p>Run a simulation first, then export the research report from the workbench.</p></div>';
    $("stamp").textContent = "ERROR";
    navigate("simulation");
    renderShell("simulation");
    $("results").innerHTML = '<div class="err"><b>Run failed:</b> ' + esc(err.message) + '</div>';
  } finally {
    setLoading(false);
    go.disabled = false;
    go.textContent = "Run simulation";
  }
}

async function download() {
  if (!state.currentRunId) return;
  const blob = await downloadRun(state.currentRunId);
  if (blob) saveBlob(blob, "dairy-" + state.currentRunId + "-output.zip");
}

function saveBlob(blob, name) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
}

// Rasterize the current SVG charts into a single tall PNG and download it.
async function downloadGraphsPNG() {
  const rows = aggregate((state.data && state.data.daily) || [], state.period);
  if (!rows.length) return;
  const charts = buildCharts(rows, state.period);
  const S = 2, PAD = 20, W = CH.W, H = CH.H;
  const canvas = document.createElement("canvas");
  canvas.width = W * S;
  canvas.height = (H + PAD) * charts.length * S;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#ffffff"; ctx.fillRect(0, 0, canvas.width, canvas.height);
  try {
    const images = await Promise.all(charts.map(ch => new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = reject;
      img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(ch.s);
    })));
    images.forEach((img, i) => ctx.drawImage(img, 0, (PAD + i*(H + PAD))*S, W*S, H*S));
    canvas.toBlob(blob => {
      if (blob) saveBlob(blob, "graphs-" + state.period + ".png");
      else alert("Graph download failed. Please try again.");
    }, "image/png");
  } catch (err) {
    console.error("Graph download failed", err);
    alert("Graph download failed. Please try again.");
  }
}

document.addEventListener("click", (e) => {
  const b = e.target.closest("button"); if (!b) return;
  if (b.id === "rail-toggle") toggleRail();
  else if (b.dataset.page) navigate(b.dataset.page);
  else if (b.dataset.chartPeriod) { state.selectedPeriod = b.dataset.chartPeriod; renderCharts(); }
  else if (b.dataset.cowSort) { state.cowSort = b.dataset.cowSort; renderCows(); }
  else if (b.dataset.comparisonMode) { state.comparisonMode = b.dataset.comparisonMode; renderComparison(); }
  else if (b.dataset.comparisonMetric) { state.comparisonMetric = b.dataset.comparisonMetric; renderComparison(); }
  else if (b.dataset.view) { state.view = b.dataset.view; render(); }
  else if (b.dataset.period) { state.period = b.dataset.period; state.selectedPeriod = b.dataset.period; render(); }
  else if (b.dataset.d) { $("days").value = b.dataset.d; }
  else if (b.id === "comparison-run") runComparison();
  else if (b.id === "download") download();
  else if (b.id === "export-graphs") downloadGraphsPNG();
  else if (b.dataset.parameterReset) {
    delete state.parameterDraft[b.dataset.parameterReset];
    delete state.parameterErrors[b.dataset.parameterReset];
    renderParameters();
  }
  else if (b.dataset.parameterResetGroup) {
    (state.calibration || []).filter(row => row.agent === b.dataset.parameterResetGroup).forEach(row => {
      delete state.parameterDraft[row.key];
      delete state.parameterErrors[row.key];
    });
    renderParameters();
  }
  else if (b.id === "parameter-reset-all") {
    state.parameterDraft = {};
    state.parameterErrors = {};
    renderParameters();
  }
  else if (b.id === "dlgraphs") downloadGraphsPNG();
});

function syncParameterFilter(filter, preserveFocus = false) {
  const name = filter.dataset.parameterFilter;
  const filters = parameterFilters();
  const cursor = name === "search" && typeof filter.selectionStart === "number" ? filter.selectionStart : null;
  filters[name] = name === "changed" ? Boolean(filter.checked) : filter.value;
  renderParameters();
  if (preserveFocus && name === "search") {
    const next = $("parameter-search");
    if (next && typeof next.focus === "function") {
      next.focus();
      if (cursor !== null && typeof next.setSelectionRange === "function") next.setSelectionRange(cursor, cursor);
    }
  }
}

document.addEventListener("input", (e) => {
  const target = e.target;
  const input = target && target.closest ? target.closest("[data-parameter-key]") : null;
  if (input) {
    syncParameterInput(input);
    return;
  }
  const filter = target && target.closest ? target.closest("[data-parameter-filter]") : null;
  if (filter) {
    syncParameterFilter(filter, true);
  }
});

document.addEventListener("change", (e) => {
  const target = e.target;
  const input = target && target.closest ? target.closest("[data-parameter-key]") : null;
  if (input) {
    syncParameterInput(input, true);
    return;
  }
  const filter = target && target.closest ? target.closest("[data-parameter-filter]") : null;
  if (filter) {
    syncParameterFilter(filter);
  }
});

function renderReport(d) {
  const m = d.metrics;
  const svg = svgChart({rows: d.daily, period: "daily", title: "Production trajectory", kind: "area", unit: "L", dec: 0, ydec: 0, series: [{key: "milk_l", color: "#b42318", label: "Milk"}]});
  const rows = [
    ["Milk produced", fmt(m.milk, 0) + " L", "model total", ""],
    ["Net CO2e", fmt(m.net_co2e, 0) + " kg", "model total", ""],
    ["Profit", fmt(m.profit, 0), "model total", "green"],
    ["Energy self-sufficiency", fmt(m.energy_avg, 1) + " %", "daily mean", ""],
    ["Freshwater drawn", fmt(m.freshwater, 0) + " L", "model total", ""],
    ["Sustainability score", fmt(m.sustainability_avg, 1) + " / 100", "daily mean", "green"],
  ].map(([label, value, note, cls]) => `<div class="reportrow"><b>${label}</b><strong class="${cls}">${value}</strong><span>${note}</span><span>reported</span></div>`).join("");
  $("report-meta").textContent = `${String(d.name).toUpperCase()} · SEED ${d.seed} · ${d.days} DAYS`;
  $("report-content").innerHTML = `<div class="reportintro"><h3>One farm.<br>${d.days} days<br>in evidence.</h3><div class="finding"><b class="green">${fmt(m.sustainability_avg, 1)} / 100</b><span>mean sustainability score<br>from the selected simulation run</span></div></div><div class="reportchart"><div class="reportcharthead"><b>Production trajectory</b><span>Milk output · litres / day</span></div>${svg}</div><div class="reportfoot"><div>${rows}</div><p class="interpretation"><b>Run summary</b><br>This report summarizes the selected scenario using the same daily records shown in the workbench. Monthly and yearly views are roll-ups of this simulation, not separate runs.</p></div>`;
}
function showReport() {
  if (state.data) renderReport(state.data);
  $("workspace").style.display = "none";
  $("report").classList.add("open");
  window.scrollTo(0, 0);
}
function hideReport() {
  $("report").classList.remove("open");
  $("workspace").style.display = "block";
  window.scrollTo(0, 0);
}
initRouter(renderShell);
initialize();
$("run").addEventListener("submit", onRun);
$("open-report").addEventListener("click", showReport);
$("scenario").addEventListener("change", () => updateScenarioLabel($("scenario").value.replace(/\.json$/, "")));
$("back-workspace").addEventListener("click", hideReport);
