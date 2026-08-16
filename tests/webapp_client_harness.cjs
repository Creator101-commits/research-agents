"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const webRoot = process.argv[2];
const loaded = new Set();
function loadModule(filePath) {
  const absolute = path.resolve(filePath);
  if (loaded.has(absolute)) return "";
  loaded.add(absolute);
  let source = fs.readFileSync(absolute, "utf8");
  source = source.replace(/^import\s+\{[^}]+\}\s+from\s+["'](\.\/[^"']+)["'];?\s*$/gm,
    (_, dependency) => loadModule(path.resolve(path.dirname(absolute), dependency)));
  source = source.replace(/^export\s+(?=(?:const|function|async function|class)\b)/gm, "");
  return source;
}
const script = loadModule(path.join(webRoot, "js", "app.js"));

const elements = new Map();
const documentListeners = {};
const downloads = [];
const switches = [];

function makeElement(id) {
  const element = {
    id,
    value: "",
    innerHTML: "",
    textContent: "",
    disabled: false,
    hidden: false,
    className: "",
    attributes: {},
    classList: {
      toggle(name, force) {
        const has = element.className.split(" ").includes(name);
        const next = force === undefined ? !has : force;
        element.className = next ? [...new Set(`${element.className} ${name}`.trim().split(" "))].join(" ") : element.className.split(" ").filter(value => value && value !== name).join(" ");
        return next;
      },
    },
    setAttribute(name, value) { element.attributes[name] = String(value); },
    removeAttribute(name) { delete element.attributes[name]; },
    focus() {},
    dataset: {},
    addEventListener(type, listener) {
      element["on" + type] = listener;
    },
    closest() {
      return element;
    },
  };
  elements.set(id, element);
  return element;
}

["scenario", "days", "start-date", "seed", "herd", "switches", "go", "stamp", "results", "run", "rail-toggle", "loops-content", "comparison-content", "environment-content", "economics-content", "equipment-content", "parameters-content", "model-details-content", "exports-content"]
  .forEach(makeElement);

const document = {
  body: { appendChild() {} },
  getElementById(id) {
    return elements.get(id) || makeElement(id);
  },
  querySelectorAll(selector) {
    return selector === "#switches input" ? switches : [];
  },
  addEventListener(type, listener) {
    documentListeners[type] = listener;
  },
  createElement(tag) {
    if (tag === "a") {
      const anchor = {
        href: "",
        download: "",
        click() {
          downloads.push({name: anchor.download, href: anchor.href});
        },
        remove() {},
      };
      return anchor;
    }
    if (tag === "canvas") {
      return {
        width: 0,
        height: 0,
        getContext() {
          return {fillStyle: "", fillRect() {}, drawImage() {}};
        },
        toBlob(callback) {
          callback({type: "image/png"});
        },
      };
    }
    return makeElement("created-" + tag);
  },
};

globalThis.alert = message => { globalThis.lastAlert = message; };
let imageMode = "normal";
globalThis.Image = class {
  set src(value) {
    this._src = value;
    queueMicrotask(() => imageMode === "error" ? this.onerror && this.onerror() : this.onload && this.onload());
  }
};
globalThis.URL = {
  createObjectURL() { return "blob:test"; },
  revokeObjectURL() {},
};

const defaults = {
  name: "baseline",
  start_date: "2026-12-25",
  days: 10,
  seed: 1,
  herd_size: 100,
  l1_nutrient_loop_enabled: true,
  l2_water_loop_enabled: true,
  l3_energy_loop_enabled: true,
  l4_byproduct_loop_enabled: true,
  enable_processor: false,
  enable_whey_processing: false,
  enable_land_agent: false,
};
const parameterData = {
  parameters: [
    {key: "demo.rate", agent: "demo", default: 0.5, unit: "fraction", source: "test", assumption: true, description: "Demo rate", valid_range: "0..1"},
    {key: "demo.enabled", agent: "demo", default: true, unit: "boolean", source: "test", assumption: false, description: "Demo switch", valid_range: "true,false"},
  ],
};
const runData = {
  id: "abc12345",
  name: "baseline",
  seed: 9,
  days: 2,
  herd_size: 4,
  duration_s: 0.01,
  events: 3,
  metrics: {milk: 30, net_co2e: 5, profit: 7, energy_avg: 60, freshwater: 9, sustainability_avg: 50},
  daily: [
    {day: "2026-01-01", milk_l: 10, profit: 2, net_kg_co2e: 3, kg_co2e_per_l_milk: .3,
      energy_self_sufficiency_pct: 50, input_circularity: .1, output_circularity: .2,
      freshwater_withdrawal_l: 4, cow_count: 4, active_disease_cases: 0, sustainability_score_0_100: 40},
    {day: "2026-01-02", milk_l: 20, profit: 5, net_kg_co2e: 2, kg_co2e_per_l_milk: .1,
      energy_self_sufficiency_pct: 70, input_circularity: .3, output_circularity: .4,
      freshwater_withdrawal_l: 5, cow_count: 4, active_disease_cases: 1, sustainability_score_0_100: 60},
  ],
};
runData.series = {
  daily: runData.daily,
  monthly: [{day: "2026-01", milk_l: 30, profit: 7, net_kg_co2e: 5, kg_co2e_per_l_milk: 5 / 30}],
  annual: [{day: "2026", milk_l: 30, profit: 7, net_kg_co2e: 5, kg_co2e_per_l_milk: 5 / 30}],
};
runData.loops = {
  l1: {state: "active", enabled: true, metrics: {manure_kg: {value: 20, unit: "kg", available: true}}, details: {}, provenance: []},
  l2: {state: "inactive", enabled: false, metrics: {}, details: {}, provenance: []},
  l3: {state: "active", enabled: true, metrics: {net_kwh: {value: 4, unit: "kWh", available: true}}, details: {}, provenance: []},
  l4: {state: "unavailable", enabled: false, metrics: {}, details: {}, provenance: []},
  flow: {nodes: [{id: "cow", label: "Cow", state: "active"}], edges: []},
};
runData.environment = {
  available: true,
  period: "run",
  source: 'ctx.state["environment_history"]',
  metrics: {
    gross_kg_co2e: {value: 9, unit: "kg CO2e", available: true},
    avoided_kg_co2e: {value: 2, unit: "kg CO2e", available: true},
    net_kg_co2e: {value: 7, unit: "kg CO2e", available: true},
    ghg_intensity: {value: .23, unit: "kg CO2e/L milk", available: true},
    soil_carbon_delta_kg: {value: 1, unit: "kg C", available: true},
    synthetic_fertilizer_saved_kg: {value: 3, unit: "kg N", available: true},
    nue: {value: .4, unit: "fraction", available: true},
    circularity_score: {value: .5, unit: "fraction", available: true},
    sustainability_score_0_100: {value: 60, unit: "score 0-100", available: true},
    carbon_credit_value: {value: 4, unit: "currency", available: true},
    soil_organic_carbon_pct: {value: 2, unit: "%", available: true},
    soil_biodiversity_index: {value: 1, unit: "index", available: true},
  },
  daily: [{day: "2026-01-01", gross_kg_co2e: 9, avoided_kg_co2e: 2, net_kg_co2e: 7, kg_co2e_per_l_milk: .23, circularity_score: .5, sustainability_score_0_100: 60}],
  monthly: [{month: "2026-01", report: "environment", gross_kg_co2e: 9, avoided_kg_co2e: 2, net_kg_co2e: 7, kg_co2e_per_l_milk: .23, circularity_score: .5, sustainability_score_0_100: 60}],
  ledger: [{date: "2026-01-01", source: "energy", stream_id: "grid", value: 2, unit: "kg CO2e", direction: "avoided", quality: "ok", confidence: "estimated"}],
  warnings: [],
  provenance: {packet: {source: "environment", name: "environment_packet", confidence: "estimated"}},
};
runData.economics = {
  available: true,
  source: "ctx.daily_records",
  metrics: {
    total_revenue: {value: 90, unit: "currency", available: true},
    total_cost: {value: 60, unit: "currency", available: true},
    profit: {value: 30, unit: "currency", available: true},
    cumulative_profit: {value: 30, unit: "currency", available: true},
    cash_balance: {value: 130, unit: "currency", available: true},
    farm_npv: {value: 29, unit: "currency", available: true},
  },
  daily: [
    {day: "2026-01-01", total_revenue: 90, total_cost: 60, profit: 30},
  ],
  monthly: [{month: "2026-01", report: "farm_manager", total_revenue: 90, total_cost: 60, profit: 30}],
  latest: {recommendation: "maintain_current_policy", policy_conflicts: [], milk_revenue: 90, total_cost: 60},
  market: {milk_price_per_l: .4, market_mode: "static", market_regime_label: "stable"},
  discount_rate: .06,
  warnings: [],
};
runData.equipment = {
  available: true,
  assets: [
    {id: "dairy_processor", label: "Dairy processor", capex: 100, annual_benefit: 30, roi: .3, payback_years: 3.33, npv: 30, status: "configured"},
  ],
  equipment_npvs: {dairy_processor: 30},
  discount_rate: .06,
  warnings: [],
  provenance: {npv: {source: "dairy_abm.analysis.npv"}},
};
runData.model_details = {
  available: true,
  source: "Python dashboard contract",
  scenario: "baseline",
  start_date: "2026-01-01",
  days: 2,
  seed: 9,
  herd_size: 4,
  enabled_systems: {enable_processor: false, enable_whey_processing: false, enable_land_agent: false, l1_nutrient_loop_enabled: true},
  loop_states: {l1: "active", l2: "inactive", l3: "active", l4: "unavailable"},
  run_duration_s: .01,
  calibration_override_count: 0,
  assumption_count: 5,
  active_agent_count: 11,
  event_count: 3,
  warnings: [{source: "model", message: "check packet"}],
  policy_summary: {recommendation: "maintain_current_policy", history_count: 2, automatic_policy_actions: [], policy_conflicts: [], policy_change_triggers: ["routine_review"], effective_policy: {feed_mode: "balanced"}},
  scheduler: {latest_execution_order: ["market", "cow", "environment"], records: [{day: "2026-01-02", phase: "daily", agents: "market,cow,environment"}], record_count: 1},
  report_contract: {daily: {period: "daily", confidence: "packet", fields: {milk_l: "L"}}, monthly: {period: "calendar month", confidence: "report", fields: {profit: "currency"}}},
};
runData.exports = {
  available: true,
  source: "dairy_abm.reports.write_reports",
  artifacts: [
    {id: "summary", label: "Summary JSON", filename: "summary.json", content_type: "application/json", endpoint: "/api/export/abc12345/summary.json"},
    {id: "daily", label: "Daily CSV", filename: "daily.csv", content_type: "text/csv", endpoint: "/api/export/abc12345/daily.csv"},
    {id: "zip", label: "Full ZIP", filename: "abc12345-output.zip", content_type: "application/zip", endpoint: "/api/export/abc12345"},
  ],
  contract: {official_files: ["summary.json", "daily.csv"]},
};

const comparisonData = {
  runs: [
    {
      run_id: "base1111",
      label: "Baseline",
      meta: {scenario_name: "baseline", start_date: "2026-01-01", days: 2, herd_size: 4, seed: 9, calibration_overrides: {}},
      features: {l1_nutrient_loop_enabled: true, l2_water_loop_enabled: true, l3_energy_loop_enabled: true, l4_byproduct_loop_enabled: true},
      warnings: [],
    },
    {
      run_id: "alt2222",
      label: "Alternative",
      meta: {scenario_name: "baseline", start_date: "2026-01-01", days: 2, herd_size: 4, seed: 10, calibration_overrides: {}},
      features: {l1_nutrient_loop_enabled: true, l2_water_loop_enabled: true, l3_energy_loop_enabled: false, l4_byproduct_loop_enabled: true},
      warnings: [],
    },
  ],
  deltas: [{
    baseline_run_id: "base1111",
    run_id: "alt2222",
    metrics: {
      milk: {unit: "L", baseline: 30, value: 32, absolute: 2, percentage: 6.6667},
      net_co2e: {unit: "kg CO2e", baseline: 5, value: 3, absolute: -2, percentage: -40},
      profit: {unit: "currency", baseline: 7, value: 6, absolute: -1, percentage: -14.2857},
    },
  }],
};

let fetchMode = "normal";
globalThis.fetch = async (url, options = {}) => {
  if (url === "/api/scenario") {
    return {ok: true, async json() { return {defaults, scenarios: ["baseline.json"]}; }};
  }
  if (url === "/api/calibration") {
    return {ok: true, async json() { return parameterData; }};
  }
  if (url === "/api/run") {
    if (fetchMode === "error") {
      return {ok: false, async json() { return {error: "bad <run>"}; }};
    }
    assert.equal(options.method, "POST");
    const body = JSON.parse(options.body);
    assert.equal(body.scenario, "baseline.json");
    assert.equal(body.days, 2);
    assert.equal(body.start_date, "2026-01-15");
    assert.equal(body.seed, 9);
    assert.equal(body.herd_size, 4);
    assert.equal(body.enable_processor, true);
    if (Object.keys(body.calibration_overrides || {}).length) assert.deepEqual(body.calibration_overrides, {"demo.rate": 0.75});
    return {ok: true, async json() { return runData; }};
  }
  if (url === "/api/compare") {
    assert.equal(options.method, "POST");
    const body = JSON.parse(options.body);
    assert.equal(body.runs.length, 2);
    assert.equal(body.runs[0].scenario, "baseline.json");
    assert.equal(body.runs[1].scenario, "baseline.json");
    assert.equal(body.runs[0].scenario_overrides.seed, 9);
    return {ok: true, async json() { return comparisonData; }};
  }
  if (url === "/api/export/abc12345") {
    return {ok: true, async blob() { return {type: "application/zip"}; }};
  }
  throw new Error("unexpected fetch: " + url);
};

const context = vm.createContext({
  console: {log: (...args) => console.log(...args), error() {}},
  document,
  fetch: globalThis.fetch,
  Image: globalThis.Image,
  URL: globalThis.URL,
  alert: globalThis.alert,
  setTimeout,
  clearTimeout,
  encodeURIComponent,
  Promise,
  Number,
  String,
  Math,
  Object,
  Map,
  Array,
  isNaN,
});

const exportCode = `
  globalThis.webapp = {aggregate, periodLabel, svgChart, buildCharts, CHART_REGISTRY, render, ledger, renderOverview,
    renderCharts, renderLoops, renderCows, renderEnvironment, renderEconomics, renderEquipment, renderParameters, renderModelDetails, renderExports, renderComparison, runComparison, onRun, download, downloadGraphsPNG, renderShell, setLoading, setError, setWarnings, loadCalibration,
    pageFromHash, navigate, state};
`;
vm.runInContext(script + exportCode, context);
const api = context.webapp;

function click(button) {
  documentListeners.click({target: {closest: () => button}});
}
function button(dataset = {}, id = "") {
  return {id, dataset};
}
function tick() {
  return new Promise(resolve => setImmediate(resolve));
}

(async () => {
  await tick();
  assert.equal(api.pageFromHash("#/overview"), "overview");
  assert.equal(api.pageFromHash("#/not-a-page"), "simulation");
  api.renderShell("overview");
  assert.equal(api.state.activePage, "overview");
  assert.equal(elements.get("page-overview").hidden, false);
  click(button({}, "rail-toggle"));
  assert.equal(api.state.railCollapsed, true);
  assert.equal(elements.get("rail-toggle").attributes["aria-expanded"], "false");
  click(button({}, "rail-toggle"));
  assert.equal(api.state.railCollapsed, false);
  assert.equal(elements.get("page-simulation").hidden, true);
  api.setLoading(true);
  assert.equal(elements.get("loading-state").hidden, false);
  assert.match(elements.get("app-shell").className, /is-loading/);
  api.setError("bad <run>");
  assert.equal(elements.get("error-banner").hidden, false);
  assert.equal(elements.get("error-text").textContent, "bad <run>");
  api.setWarnings([{message: "check packet"}]);
  assert.equal(elements.get("warning-banner").hidden, false);
  assert.equal(elements.get("warning-text").textContent, "check packet");
  api.setError("");
  api.setWarnings([]);
  api.setLoading(false);
  api.renderShell("simulation");
  assert.equal(api.state.activePage, "simulation");
  assert.equal(elements.get("page-simulation").hidden, false);
  assert.equal(elements.get("page-overview").hidden, true);
  assert.match(elements.get("scenario").innerHTML, /baseline/);
  assert.equal(elements.get("days").value, 10);
  assert.equal(elements.get("start-date").value, "2026-12-25");
  assert.match(elements.get("switches").innerHTML, /l1_nutrient_loop_enabled/);
  assert.match(elements.get("switches").innerHTML, /enable_land_agent/);
  assert.equal(switches.length, 0);

  const rows = [
    {day: "2026-01-01", milk_l: 10, profit: 2, energy_self_sufficiency_pct: 50, cow_count: 10},
    {day: "2026-01-02", milk_l: 20, profit: -1, energy_self_sufficiency_pct: 70, cow_count: 12},
    {day: "2026-02-01", milk_l: 5, profit: 4, energy_self_sufficiency_pct: 90, cow_count: 20},
  ];
  assert.deepEqual(api.aggregate(rows, "daily"), rows);
  const monthly = api.aggregate(rows, "monthly");
  assert.deepEqual(monthly.map(r => r.day), ["2026-01", "2026-02"]);
  assert.equal(monthly[0].milk_l, 30);
  assert.equal(monthly[0].profit, 1);
  assert.equal(monthly[0].energy_self_sufficiency_pct, 60);
  assert.equal(monthly[0].cow_count, 11);
  const intensity = api.aggregate([
    {day: "2026-03-01", milk_l: 10, net_kg_co2e: 1},
    {day: "2026-03-02", milk_l: 30, net_kg_co2e: 9},
  ], "monthly");
  assert.equal(intensity[0].kg_co2e_per_l_milk, 0.25);
  const yearly = api.aggregate(rows, "yearly");
  assert.equal(yearly.length, 1);
  assert.equal(yearly[0].milk_l, 35);
  assert.equal(yearly[0].energy_self_sufficiency_pct, 70);
  assert.equal(api.periodLabel("2026-02-01", "daily"), "02-01");
  assert.equal(api.periodLabel("2026-02", "monthly"), "26-02");
  assert.equal(api.periodLabel("2026", "yearly"), "2026");
  assert.equal(api.periodLabel("2026", "annual"), "2026");

  const svg = api.svgChart({rows, period: "daily", title: "Test", kind: "bar", unit: "L",
    series: [{key: "milk_l", color: "#b42318", label: "Milk"}]});
  assert.match(svg, /viewBox="0 0 520 244"/);
  assert.match(svg, /class="ttl"/);
  assert.match(svg, /class="axislabel"/);
  assert.match(svg, /<rect/);
  const missingSvg = api.svgChart({rows: [{day: "2026-01-01", milk_l: null}, {day: "2026-01-02", milk_l: 10}], period: "daily", title: "Missing", kind: "bar", unit: "L", series: [{key: "milk_l", color: "#b42318", label: "Milk"}]});
  assert.doesNotMatch(missingSvg, /2026-01-01 - 0/);
  assert.match(svg, /<style>/);
  assert.match(svg, /\.gsv \.ttl/);
  assert.match(svg, /<title>2026-01-01/);
  assert.doesNotMatch(svg, /undefined|null/);
  assert.equal(api.buildCharts(runData.daily, "daily").length, 8);
  assert.match(api.buildCharts(runData.daily, "daily")[0].s, /#b42318/);
  assert.match(api.buildCharts(runData.daily, "daily")[2].s, /#3f6b4f/);

  api.state.data = runData;
  api.state.view = "ledger";
  api.state.period = "daily";
  api.render();
  assert.match(elements.get("results").innerHTML, /Daily ledger/);
  assert.match(elements.get("results").innerHTML, /2026-01-02/);
  api.state.view = "graphs";
  api.render();
  assert.equal((elements.get("results").innerHTML.match(/<svg /g) || []).length, 8);
  assert.match(elements.get("results").innerHTML, /Download graphs \(PNG\)/);
  assert.match(elements.get("results").innerHTML, /class="graph-lead"/);

  click(button({d: "30"}));
  assert.equal(elements.get("days").value, "30");
  click(button({view: "ledger"}));
  assert.equal(api.state.view, "ledger");
  click(button({period: "monthly"}));
  assert.equal(api.state.period, "monthly");
  assert.match(elements.get("results").innerHTML, /Rolled-up ledger/);

  switches.push({checked: true, dataset: {k: "enable_processor"}});
  elements.get("scenario").value = "baseline.json";
  elements.get("days").value = "2";
  elements.get("start-date").value = "2026-01-15";
  elements.get("seed").value = "9";
  elements.get("herd").value = "4";
  fetchMode = "normal";
  await api.onRun({preventDefault() {}});
  assert.equal(api.state.view, "graphs");
  assert.equal(api.state.period, "daily");
  assert.equal(elements.get("stamp").textContent, "SIMULATED");
  assert.equal(api.state.data.id, "abc12345");
  assert.match(elements.get("active-run-meta").textContent, /start 2026-01-01/);
  api.renderShell("overview");
  assert.match(elements.get("overview-content").innerHTML, /Total milk/);
  assert.match(elements.get("overview-content").innerHTML, /Milk production/);
  assert.match(elements.get("overview-content").innerHTML, /N\/A/);
  api.renderShell("simulation");
  assert.match(elements.get("results").innerHTML, /Milk produced/);
  api.renderShell("charts");
  assert.equal(api.state.activePage, "charts");
  assert.match(elements.get("charts-content").innerHTML, /Milk production/);
  assert.match(elements.get("charts-content").innerHTML, /daily points/);
  assert.match(elements.get("charts-content").innerHTML, /<svg /);
  click(button({chartPeriod: "monthly"}));
  assert.equal(api.state.selectedPeriod, "monthly");
  assert.match(elements.get("charts-content").innerHTML, /monthly points/);
  click(button({chartPeriod: "annual"}));
  assert.equal(api.state.selectedPeriod, "annual");
  assert.match(elements.get("charts-content").innerHTML, /annual points/);
  api.renderShell("simulation");
  api.renderShell("loops");
  assert.equal(api.state.activePage, "loops");
  assert.match(elements.get("loops-content").innerHTML, /Nutrient loop/);
  assert.match(elements.get("loops-content").innerHTML, /active/);
  assert.match(elements.get("loops-content").innerHTML, /unavailable/);
  api.renderShell("environment");
  assert.equal(api.state.activePage, "environment");
  assert.match(elements.get("environment-content").innerHTML, /Gross GHG/);
  assert.match(elements.get("environment-content").innerHTML, /SOURCE STREAM LEDGER/);
  assert.match(elements.get("environment-content").innerHTML, /energy/);
  assert.match(elements.get("environment-content").innerHTML, /Calendar-month environment records/);
  api.renderShell("economics");
  assert.equal(api.state.activePage, "economics");
  assert.match(elements.get("economics-content").innerHTML, /Trace reported money flows/);
  assert.match(elements.get("economics-content").innerHTML, /Farm NPV/);
  assert.match(elements.get("economics-content").innerHTML, /Latest price context/);
  api.renderShell("roi");
  assert.equal(api.state.activePage, "roi");
  assert.match(elements.get("equipment-content").innerHTML, /Inspect reported equipment returns/);
  assert.match(elements.get("equipment-content").innerHTML, /Existing analysis outputs/);
  const loadedParameters = await api.loadCalibration();
  assert.equal(loadedParameters.parameters.length, 2);
  api.state.calibration = parameterData.parameters;
  api.renderShell("parameters");
  assert.equal(api.state.activePage, "parameters");
  assert.match(elements.get("parameters-content").innerHTML, /Edit validated model parameters/);
  assert.match(elements.get("parameters-content").innerHTML, /demo.rate/);
  assert.match(elements.get("parameters-content").innerHTML, /assumption/);
  api.state.parameterDraft = {"demo.rate": 0.75};
  api.renderParameters();
  assert.match(elements.get("parameters-content").innerHTML, /1 override/);
  api.renderShell("model-details");
  assert.equal(api.state.activePage, "model-details");
  assert.match(elements.get("model-details-content").innerHTML, /READ-ONLY RUN DESCRIPTION/);
  assert.match(elements.get("model-details-content").innerHTML, /Actual run capabilities/);
  assert.match(elements.get("model-details-content").innerHTML, /Latest daily execution order/);
  assert.match(elements.get("model-details-content").innerHTML, /Official report metadata/);
  api.renderShell("exports");
  assert.equal(api.state.activePage, "exports");
  assert.match(elements.get("exports-content").innerHTML, /OFFICIAL REPORT EXPORTS/);
  assert.match(elements.get("exports-content").innerHTML, /Summary JSON/);
  assert.match(elements.get("exports-content").innerHTML, /Full ZIP/);
  assert.match(elements.get("exports-content").innerHTML, /Chart PNG/);
  api.state.comparison = null;
  api.state.comparisonMode = "baseline";
  api.renderShell("comparison");
  assert.match(elements.get("comparison-content").innerHTML, /Baseline vs Current/);
  click(button({comparisonMode: "matrix"}));
  assert.match(elements.get("comparison-content").innerHTML, /16 actual model runs/);
  click(button({comparisonMode: "loop"}));
  assert.match(elements.get("comparison-content").innerHTML, /Individual Loop/);
  click(button({comparisonMode: "scenarios"}));
  assert.match(elements.get("comparison-content").innerHTML, /User-selected scenarios/);
  click(button({comparisonMode: "baseline"}));
  fetchMode = "comparison";
  await api.runComparison();
  assert.equal(api.state.comparison.runs.length, 2);
  assert.match(elements.get("comparison-content").innerHTML, /Net GHG/);
  assert.match(elements.get("comparison-content").innerHTML, /Seeds differ/);
  assert.match(elements.get("comparison-content").innerHTML, /is-favorable/);
  assert.match(elements.get("comparison-content").innerHTML, /is-unfavorable/);
  click(button({comparisonMetric: "profit"}));
  assert.equal(api.state.comparisonMetric, "profit");

  api.renderShell("simulation");

  fetchMode = "error";
  await api.onRun({preventDefault() {}});
  assert.equal(elements.get("stamp").textContent, "ERROR");
  assert.match(elements.get("results").innerHTML, /bad &lt;run&gt;/);
  assert.equal(api.state.data, null);
  await api.download();
  assert.equal(downloads.length, 0);

  fetchMode = "normal";
  await api.onRun({preventDefault() {}});
  api.state.view = "graphs";
  api.state.period = "daily";
  await api.downloadGraphsPNG();
  assert.ok(globalThis.lastAlert === undefined);
  assert.ok(downloads.some(d => d.name === "graphs-daily.png"));
  imageMode = "error";
  await api.downloadGraphsPNG();
  assert.equal(globalThis.lastAlert, "Graph download failed. Please try again.");
  imageMode = "normal";
  await api.download();
  assert.ok(downloads.some(d => d.name === "dairy-abc12345-output.zip"));

  console.log("webapp client tests passed");
})().catch(error => {
  console.error(error.stack || error);
  process.exitCode = 1;
});
