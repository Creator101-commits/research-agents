import { state } from "./state.js";
import { aggregate, esc, fmt, periodLabel } from "./format.js";
import { CH, CHART_REGISTRY, buildCharts, svgChart } from "./charts.js";
import { downloadRun, loadDefaults, runSimulation } from "./api.js";
import { DEFAULT_PAGE, initRouter, navigate, pageFromHash, PAGES } from "./router.js";

"use strict";
const $ = (id) => document.getElementById(id);
const PERIODS = [["daily","Daily"],["monthly","Monthly"],["yearly","Yearly"]];
const CHART_PERIODS = [["daily","Daily"],["monthly","Monthly"],["annual","Annual"]];
const TABS = [["ledger","Ledger"],["graphs","Graphs"]];

const pageDefinition = (id) => PAGES.find(page => page.id === id) || PAGES.find(page => page.id === DEFAULT_PAGE);

function renderShell(page) {
  const current = pageDefinition(page);
  state.activePage = current.id;
  PAGES.forEach(({id}) => {
    const panel = $("page-" + id);
    if (panel) panel.hidden = id !== current.id;
    const nav = $("nav-" + id);
    if (nav) nav.className = id === current.id ? "active" : "";
  });
  $("page-kicker").textContent = current.label.toUpperCase();
  $("page-title").textContent = current.label;
  $("page-description").textContent = current.description;
  if (current.id === "simulation") render();
  else if (current.id === "overview") renderOverview();
  else if (current.id === "charts") renderCharts();
}

function setLoading(loading) {
  state.loading = loading;
  $("loading-state").hidden = !loading;
  $("app-shell").className = loading ? "app is-loading" : "app";
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
  ["profit", "Profit"],
  ["net_kg_co2e", "Net CO2e (kg)"],
  ["kg_co2e_per_l_milk", "CO2e/L"],
  ["energy_self_sufficiency_pct", "Self-suff %"],
  ["input_circularity", "In circ"],
  ["output_circularity", "Out circ"],
  ["freshwater_withdrawal_l", "Freshwater (L)"],
  ["cow_count", "Cows"],
  ["active_disease_cases", "Cases"],
  ["sustainability_score_0_100", "Sust."],
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
  const head = COLUMNS.map(([,lab]) => `<th>${lab}</th>`).join("");
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
  const go = $("go");
  go.disabled = true;
  go.innerHTML = `<span class="spinner"></span>Running...`;
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
  if (b.dataset.page) navigate(b.dataset.page);
  else if (b.dataset.chartPeriod) { state.selectedPeriod = b.dataset.chartPeriod; renderCharts(); }
  else if (b.dataset.view) { state.view = b.dataset.view; render(); }
  else if (b.dataset.period) { state.period = b.dataset.period; state.selectedPeriod = b.dataset.period; render(); }
  else if (b.dataset.d) { $("days").value = b.dataset.d; }
  else if (b.id === "download") download();
  else if (b.id === "dlgraphs") downloadGraphsPNG();
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
