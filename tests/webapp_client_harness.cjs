"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const sourcePath = process.argv[2];
const page = fs.readFileSync(sourcePath, "utf8");
const script = page.split("<script>", 2)[1].split("</script>", 1)[0];

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

["scenario", "days", "seed", "herd", "switches", "go", "stamp", "results", "run"]
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

let fetchMode = "normal";
globalThis.fetch = async (url, options = {}) => {
  if (url === "/api/scenario") {
    return {ok: true, async json() { return {defaults, scenarios: ["baseline.json"]}; }};
  }
  if (url === "/api/run") {
    if (fetchMode === "error") {
      return {ok: false, async json() { return {error: "bad <run>"}; }};
    }
    assert.equal(options.method, "POST");
    const body = JSON.parse(options.body);
    assert.equal(body.scenario, "baseline.json");
    assert.equal(body.days, 2);
    assert.equal(body.seed, 9);
    assert.equal(body.herd_size, 4);
    assert.equal(body.enable_processor, true);
    return {ok: true, async json() { return runData; }};
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
  globalThis.webapp = {aggregate, periodLabel, svgChart, buildCharts, render, ledger,
    onRun, download, downloadGraphsPNG, state};
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
  assert.match(elements.get("scenario").innerHTML, /baseline/);
  assert.equal(elements.get("days").value, 10);
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
  const yearly = api.aggregate(rows, "yearly");
  assert.equal(yearly.length, 1);
  assert.equal(yearly[0].milk_l, 35);
  assert.equal(yearly[0].energy_self_sufficiency_pct, 70);
  assert.equal(api.periodLabel("2026-02-01", "daily"), "02-01");
  assert.equal(api.periodLabel("2026-02", "monthly"), "26-02");
  assert.equal(api.periodLabel("2026", "yearly"), "2026");

  const svg = api.svgChart({rows, period: "daily", title: "Test", kind: "bar", unit: "L",
    series: [{key: "milk_l", color: "#b42318", label: "Milk"}]});
  assert.match(svg, /viewBox="0 0 520 244"/);
  assert.match(svg, /class="ttl"/);
  assert.match(svg, /class="axislabel"/);
  assert.match(svg, /<rect/);
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
  elements.get("seed").value = "9";
  elements.get("herd").value = "4";
  fetchMode = "normal";
  await api.onRun({preventDefault() {}});
  assert.equal(api.state.view, "graphs");
  assert.equal(api.state.period, "daily");
  assert.equal(elements.get("stamp").textContent, "SIMULATED");
  assert.equal(api.state.data.id, "abc12345");
  assert.match(elements.get("results").innerHTML, /Milk produced/);

  fetchMode = "error";
  await api.onRun({preventDefault() {}});
  assert.equal(elements.get("stamp").textContent, "ERROR");
  assert.match(elements.get("results").innerHTML, /bad &lt;run&gt;/);

  fetchMode = "normal";
  api.state.data = runData;
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
