#!/usr/bin/env python3
"""Web run-desk for the dairy farm agent-based model.

Zero-dependency local server (stdlib only). Serves a single web page that
runs the real DairyFarmModel and returns the daily ledger + summary figures
to the browser. Same code path as `python3 -m dairy_abm run`; simulation
results stay in memory and exports use temporary files outside the repository.

Usage:  python3 webapp.py   ->  open http://localhost:8765
"""

from __future__ import annotations

import io
import json
import tempfile
import time
import uuid
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from dairy_abm.config import load_calibration
from dairy_abm.core import read_json
from dairy_abm.model import DairyFarmModel
from dairy_abm.reports import write_reports

ROOT = Path(__file__).resolve().parent
SCENARIO_DIR = ROOT / "scenarios"
DEFAULT_SCENARIO = read_json(SCENARIO_DIR / "baseline.json")
CALIBRATION = load_calibration(None)

# Recent completed runs by id, so the browser can re-download output without a re-run.
RUN_CACHE: dict[str, object] = {}
# Columns shown in the browser ledger: (record key, ledger label).
DISPLAY_FIELDS = [
    ("day", "Date"),
    ("milk_l", "Milk (L)"),
    ("profit", "Profit"),
    ("net_kg_co2e", "Net CO2e (kg)"),
    ("kg_co2e_per_l_milk", "CO2e/L (kg)"),
    ("energy_self_sufficiency_pct", "Energy self-suff %"),
    ("input_circularity", "Input circ."),
    ("output_circularity", "Output circ."),
    ("freshwater_withdrawal_l", "Freshwater (L)"),
    ("cow_count", "Cows"),
    ("active_disease_cases", "Disease cases"),
    ("sustainability_score_0_100", "Sust. score"),
]


def _run_simulation(params: dict) -> dict:
    suspected = params.get("scenario")
    scenario = dict(DEFAULT_SCENARIO)
    if suspected:
        path = (SCENARIO_DIR / suspected).resolve()
        if path == SCENARIO_DIR.resolve() or str(path).startswith(str(SCENARIO_DIR.resolve())):
            scenario = read_json(path)
        else:
            raise ValueError(f"scenario file must live under {SCENARIO_DIR.name}/")

    for key in (
        "days",
        "seed",
        "herd_size",
        "start_date",
        "enable_processor",
        "enable_whey_processing",
        "enable_land_agent",
        "l1_nutrient_loop_enabled",
        "l2_water_loop_enabled",
        "l3_energy_loop_enabled",
        "l4_byproduct_loop_enabled",
    ):
        if key in params and params[key] is not None:
            scenario[key] = params[key]

    days = scenario.get("days", 10)
    if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 3650:
        raise ValueError("days must be a whole number between 1 and 3650")

    t0 = time.perf_counter()
    ctx = DairyFarmModel(scenario, CALIBRATION).run()
    duration_s = time.perf_counter() - t0

    run_id = uuid.uuid4().hex[:8]
    RUN_CACHE[run_id] = ctx
    while len(RUN_CACHE) > 10:  # keep the last ten runs downloadable
        RUN_CACHE.pop(next(iter(RUN_CACHE)))

    records = [
        {key: record.get(key) for key, _ in DISPLAY_FIELDS} for record in ctx.daily_records
    ]

    def total(key: str) -> float:
        return sum(record.get(key, 0.0) or 0.0 for record in ctx.daily_records)

    def mean(key: str) -> float:
        values = [record.get(key) for record in ctx.daily_records if record.get(key) is not None]
        return sum(values) / len(values) if values else 0.0

    metrics = {
        "milk": total("milk_l"),
        "net_co2e": total("net_kg_co2e"),
        "profit": total("profit"),
        "energy_avg": mean("energy_self_sufficiency_pct"),
        "freshwater": total("freshwater_withdrawal_l"),
        "sustainability_avg": mean("sustainability_score_0_100"),
    }

    return {
        "id": run_id,
        "name": scenario.get("name", "unnamed"),
        "seed": scenario.get("seed"),
        "days": days,
        "herd_size": scenario.get("herd_size"),
        "duration_s": round(duration_s, 2),
        "metrics": metrics,
        "daily": records,
        "events": len(ctx.events.events),
    }



def _export_zip(ctx: object) -> bytes:
    """All report files for a finished run, zipped in memory (same files the CLI writes)."""
    with tempfile.TemporaryDirectory() as tmp:
        write_reports(Path(tmp), ctx)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for file in sorted(Path(tmp).iterdir()):
                archive.write(file, file.name)
        return buffer.getvalue()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_: object) -> None:  # keep the console quiet
        pass

    def _send(self, code: int, payload: object, ctype: str = "application/json") -> None:
        if isinstance(payload, bytes):
            body = payload
        elif isinstance(payload, str):
            body = payload.encode()
        else:
            body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._send(200, PAGE, "text/html; charset=utf-8")
        elif path == "/api/scenario":
            names = sorted(p.name for p in SCENARIO_DIR.glob("*.json"))
            self._send(200, {"defaults": DEFAULT_SCENARIO, "scenarios": names})
        elif path.startswith("/api/export/"):
            run_id = path.removeprefix("/api/export/")
            ctx = RUN_CACHE.get(run_id)
            if ctx is None:
                self._send(404, {"error": "run not found or too old to export"})
                return
            zip_bytes = _export_zip(ctx)
            name = ctx.scenario.get("name", "run")
            self.send_response(200)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Disposition", f'attachment; filename="{name}-output.zip"')
            self.send_header("Content-Length", str(len(zip_bytes)))
            self.end_headers()
            self.wfile.write(zip_bytes)
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/run":
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
        except Exception as exc:  # malformed request body
            self._send(400, {"error": f"bad request: {exc}"})
            return
        try:
            result = _run_simulation(body)
            self._send(200, {"ok": True, **result})
        except Exception as exc:
            self._send(500, {"error": str(exc)})


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dairy Farm - Run Desk</title>
<style>
  :root {
    --paper:  #ffffff;
    --surface:#ffffff;
    --ink:    #111827;
    --muted:  #667085;
    --line:   #e5e7eb;
    --tin:    #cbd5e1;
    --accent: #b42318;
    --accent-ink: #c2412d;
    --sage:   #3f6b4f;
    --sage-soft: #f1f8f3;
    --quiet: #f7f8f9;
    --shadow: 0 -10px 28px rgba(17,24,39,.09);
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; min-height: 100%; }
  body { background: var(--paper); color: var(--ink); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; line-height: 1.45; }
  button, input, select { font: inherit; }
  button { cursor: pointer; }
  .mono { font-variant-numeric: tabular-nums; }

  .app { min-height: 100vh; display: grid; grid-template-columns: 238px minmax(0, 1fr); background: var(--paper); }
  .rail { display: flex; flex-direction: column; padding: 28px 18px; border-right: 1px solid var(--line); background: var(--paper); }
  .brand { display: flex; align-items: center; gap: 10px; padding: 0 10px; font-size: 16px; font-weight: 800; letter-spacing: -.02em; }
  .mark { width: 25px; height: 25px; border-radius: 50%; background: var(--accent); position: relative; }
  .mark:after { content: ""; position: absolute; width: 9px; height: 9px; left: 8px; top: 8px; border-radius: 50%; background: var(--paper); }
  .railnav { display: grid; gap: 5px; margin-top: 54px; }
  .railnav button { text-align: left; padding: 12px 13px; border: 0; border-left: 2px solid transparent; background: transparent; color: var(--muted); font-size: 13px; }
  .railnav button:hover, .railnav button.active { border-left-color: var(--accent); color: var(--ink); background: var(--quiet); font-weight: 700; }
  .railfoot { margin-top: auto; padding: 16px 12px 0; border-top: 1px solid var(--line); color: var(--muted); font-size: 11px; line-height: 1.6; }
  .green { color: var(--sage); }
  .red { color: var(--accent); }

  .workspace { min-width: 0; padding: 36px 44px 36px; }
  .topbar { display: flex; align-items: start; justify-content: space-between; gap: 32px; padding-bottom: 28px; border-bottom: 1px solid var(--line); }
  .topbar h1 { margin: 0; font-size: 29px; letter-spacing: -.045em; }
  .topbar p { margin: 7px 0 0; color: var(--muted); font-size: 13px; }
  .topactions { display: flex; gap: 11px; align-items: center; }
  .status { padding: 9px 12px; border: 1px solid #cde3d3; background: var(--sage-soft); color: var(--sage); font-size: 11px; font-weight: 800; }
  .ghost { padding: 9px 14px; border: 1px solid var(--line); background: var(--paper); color: var(--ink); font-size: 12px; }
  .ghost:hover { border-color: var(--accent); color: var(--accent); }
  .workbench { display: grid; grid-template-columns: 260px minmax(0, 1fr); gap: 30px; margin-top: 34px; align-items: start; }
  .result { min-width: 0; }

  .config { position: static; align-self: start; display: block; border: 1px solid var(--line); background: var(--paper); box-shadow: 0 8px 22px rgba(17,24,39,.05); }
  .confighead { display: block; padding: 18px 20px; border-right: 0; border-bottom: 1px solid var(--line); }
  .confighead h2 { margin: 0; font-size: 16px; letter-spacing: -.02em; }
  .confighead p { margin: 6px 0 0; color: var(--muted); font-size: 10px; line-height: 1.4; }
  form#run { display: block; padding: 18px 20px; }
  .field { min-width: 0; padding: 0 0 14px; margin: 0 0 14px; border-left: 0; border-bottom: 1px solid var(--line); }
  .field:first-child { padding-left: 0; border-left: 0; }
  .field:last-of-type { flex: none; padding-bottom: 0; margin-bottom: 0; border-bottom: 0; }
  .field label, .field .label { display: flex; justify-content: space-between; color: var(--muted); font-size: 10px; }
  .field .value { margin-top: 5px; font-size: 14px; font-weight: 700; }
  input[type=number], select { width: 100%; min-height: 34px; padding: 6px 8px; border: 1px solid var(--tin); border-radius: 2px; background: var(--paper); color: var(--ink); }
  input:focus, select:focus { outline: 2px solid var(--accent-ink); outline-offset: 1px; }
  .hint { margin-top: 3px; color: var(--muted); font-size: 10px; }
  .pills, .seg { display: inline-flex; border: 1px solid var(--tin); border-radius: 3px; overflow: hidden; }
  .pills { margin-top: 7px; }
  .pills button, .seg button { border: 0; border-right: 1px solid var(--tin); background: var(--paper); color: var(--muted); padding: 6px 9px; font-size: 10px; font-weight: 600; }
  .pills button:last-child, .seg button:last-child { border-right: 0; }
  .pills button:hover, .pills button.active, .seg button:hover { color: var(--accent); background: #fff4f2; }
  .seg button.on { background: var(--ink); color: var(--paper); }
  .switches { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 10px; row-gap: 3px; margin-top: 6px; }
  .switch { display: flex; align-items: center; justify-content: space-between; gap: 5px; font-size: 10px; white-space: nowrap; }
  .switch input { width: auto; accent-color: var(--sage); }
  button#go { width: 100%; margin-top: 14px; padding: 11px; border: 0; background: var(--accent); color: var(--paper); font-size: 12px; font-weight: 800; }
  button#go:disabled { opacity: .55; cursor: wait; }

  #results { min-height: 360px; }
  .empty-state p { max-width: 54ch; margin: 0; color: var(--muted); font-size: 14px; }
  .note { max-width: 620px; color: var(--muted); font-size: 14px; }
  .note b { color: var(--ink); }
  .muted { margin: 0 0 16px; color: var(--muted); font-size: 12px; }
  .empty-state { max-width: 620px; padding: 68px 0 100px; }
  .empty-state h2 { margin: 0 0 10px; font-size: 34px; letter-spacing: -.05em; }
  .empty-state p { max-width: 54ch; margin: 0; color: var(--muted); font-size: 14px; }
  .recordline { display: flex; flex-wrap: wrap; gap: 10px 22px; align-items: baseline; padding-bottom: 16px; margin-bottom: 22px; border-bottom: 1px dashed var(--tin); color: var(--muted); font-size: 12px; }
  .recordline .runname { color: var(--ink); font-size: 22px; font-weight: 800; }
  .recordline .dur { color: var(--accent); font-weight: 700; }
  .recordline .dl { margin-left: auto; padding: 9px 14px; border: 1px solid var(--tin); border-radius: 2px; background: var(--paper); color: var(--ink); font-size: 12px; font-weight: 600; }
  .recordline .dl:hover { border-color: var(--accent); color: var(--accent); }
  .totals { display: grid; grid-template-columns: repeat(auto-fit, minmax(155px, 1fr)); gap: 14px; margin-bottom: 28px; }
  .figure { padding: 8px 0 10px; border-top: 3px solid var(--line); }
  .figure b { display: block; font-size: 23px; font-weight: 800; letter-spacing: -.02em; }
  .figure span { color: var(--muted); font-size: 11px; }
  .figure.money b { color: var(--sage); }
  .figure.emiss b { color: var(--accent-ink); }
  .tb { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; justify-content: space-between; padding-bottom: 16px; margin-bottom: 20px; border-bottom: 1px dashed var(--tin); }
  .tb p { margin: 0; color: var(--muted); font-size: 12px; }
  .btn { padding: 9px 14px; border: 1px solid var(--tin); border-radius: 3px; background: var(--paper); color: var(--ink); font-size: 12px; font-weight: 600; }
  .btn:hover { border-color: var(--accent); color: var(--accent); }
  .graph-lead { padding: 20px 22px 14px; border: 1px solid var(--line); background: var(--paper); }
  .graph-leadhead { display: flex; justify-content: space-between; align-items: baseline; gap: 16px; padding-bottom: 10px; }
  .graph-leadhead b { font-size: 15px; }
  .graph-leadhead span { color: var(--muted); font-size: 11px; }
  .graph-lead .gsv { width: 100%; height: 300px; margin-top: 6px; }
  .graph-badge { padding: 5px 8px; border: 1px solid #cde3d3; background: var(--sage-soft); color: var(--sage); font-size: 10px; font-weight: 700; }
  .ggrid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; margin-top: 20px; }
  .gwrap { padding: 16px 16px 12px; border: 1px solid var(--line); background: var(--paper); }
  .gsv { display: block; width: 100%; height: auto; }
  .gsv .ax { stroke: #e5e7eb; stroke-width: 1; }
  .gsv .baseline { stroke: #9ca3af; stroke-width: 1.2; }
  .gsv text { fill: #667085; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; font-size: 11px; }
  .gsv .axislabel { fill: #667085; font-size: 10px; }
  .gsv .ttl { fill: #111827; font-size: 13px; font-weight: 700; }
  .gsv .lg { fill: #667085; font-size: 10.5px; }
  .ledger h3 { margin: 30px 0 12px; font-size: 15px; }
  .tablewrap { max-height: 480px; overflow: auto; border: 1px solid var(--line); }
  table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
  thead th { position: sticky; top: 0; padding: 9px 12px; background: var(--ink); color: var(--paper); font-weight: 600; text-align: right; white-space: nowrap; }
  thead th:first-child, tbody td:first-child { text-align: left; }
  tbody td { padding: 8px 12px; border-top: 1px solid var(--line); text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }
  tbody td:first-child { color: var(--muted); }
  tbody tr:nth-child(even) { background: var(--quiet); }

  .report { display: none; max-width: 1080px; margin: 0 auto; padding: 64px 76px 72px; }
  .report.open { display: block; }
  .reporttop { display: flex; justify-content: space-between; align-items: baseline; gap: 24px; padding-bottom: 20px; border-bottom: 3px solid var(--ink); }
  .reporttop h2 { margin: 0; font-size: 18px; }
  .reporttop span { color: var(--muted); font-size: 11px; }
  .reportintro { display: grid; grid-template-columns: 1.1fr .9fr; gap: 56px; padding: 52px 0 38px; }
  .reportintro h3 { margin: 0; max-width: 560px; font-size: clamp(36px, 5vw, 62px); line-height: .94; letter-spacing: -.06em; }
  .finding { align-self: end; border-left: 3px solid var(--sage); padding-left: 18px; }
  .finding b { display: block; font-size: 36px; line-height: 1; }
  .finding span { display: block; margin-top: 8px; color: var(--muted); font-size: 12px; }
  .reportchart { padding: 18px 0 10px; border-top: 1px solid var(--ink); border-bottom: 1px solid var(--line); }
  .reportcharthead { display: flex; justify-content: space-between; font-size: 13px; }
  .reportcharthead span { color: var(--muted); font-size: 11px; }
  .reportchart .gsv { margin-top: 14px; }
  .reportfoot { display: grid; grid-template-columns: 1.35fr .65fr; gap: 52px; margin-top: 28px; }
  .reportrow { display: grid; grid-template-columns: 1.2fr repeat(3, 1fr); gap: 14px; padding: 11px 0; border-top: 1px solid var(--line); font-size: 12px; }
  .reportrow span { color: var(--muted); }
  .interpretation { color: var(--muted); font-size: 12px; line-height: 1.7; }
  .interpretation b { color: var(--ink); }
  .back { margin-top: 38px; }
  .back button { padding: 9px 14px; border: 1px solid var(--line); background: var(--paper); color: var(--ink); font-size: 12px; }
  .back button:hover { border-color: var(--accent); color: var(--accent); }
  footer { padding: 0 44px 36px; color: var(--muted); font-size: 12px; }
  .spinner { width: 15px; height: 15px; margin-right: 8px; border: 2px solid var(--paper); border-top-color: transparent; border-radius: 50%; display: inline-block; vertical-align: -2px; animation: spin .7s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .err { margin-top: 18px; padding: 14px; border: 1px solid var(--accent); border-left: 4px solid var(--accent); background: #fff4f2; color: var(--accent); }
  @media (max-width: 1100px) {
    .workbench { grid-template-columns: 230px minmax(0, 1fr); gap: 24px; }
    form#run { padding: 16px; }
    .field { padding-right: 0; padding-left: 0; }
  }
  @media (max-width: 900px) {
    .app { grid-template-columns: 1fr; }
    .rail { border-right: 0; border-bottom: 1px solid var(--line); }
    .railnav { grid-template-columns: repeat(4, 1fr); margin-top: 28px; }
    .railfoot { display: none; }
    .workspace { padding: 28px 24px 36px; }
    .workbench { grid-template-columns: 1fr; gap: 24px; }
    .config { position: static; max-height: none; overflow: visible; }
    .confighead { padding: 14px 18px; }
    form#run { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 18px; padding: 14px 18px; }
    .field, .field:first-child { padding: 10px 0; margin-bottom: 10px; border-left: 0; border-bottom: 1px solid var(--line); }
    .field:first-child { padding-top: 0; }
    .field:last-of-type { padding-bottom: 10px; margin-bottom: 0; border-bottom: 0; }
    button#go { grid-column: 1 / -1; width: 100%; margin-top: 10px; }
    .report { padding: 42px 30px 52px; }
  }
  @media (max-width: 600px) {
    .workspace { padding: 24px 18px 36px; }
    .topbar, .resulthead, .topactions { display: block; }
    .topactions { margin-top: 15px; }
    .config { max-height: none; }
    form#run { grid-template-columns: 1fr; }
    button#go { grid-column: auto; }
    .metrics { grid-template-columns: repeat(2, 1fr); }
    .ggrid { grid-template-columns: 1fr; }
    .report { padding: 34px 22px 44px; }
    .reportintro, .reportfoot { grid-template-columns: 1fr; gap: 28px; }
    .reportrow { grid-template-columns: 1.5fr repeat(2, 1fr); }
    .reportrow span:last-child { display: none; }
  }
  @media print {
    .rail, .topbar, .config, footer, .back { display: none; }
    .app { display: block; }
    .report { display: block; max-width: none; }
  }
</style>
</head>
<body>
<div class="app">
  <aside class="rail">
    <div class="brand"><i class="mark"></i>Dairy Farm ABM</div>
    <nav class="railnav" aria-label="Main navigation">
      <button class="active" type="button">Run desk</button>
      <button type="button" data-view="graphs">Graphs</button>
      <button type="button" data-view="ledger">Ledger</button>
      <button type="button" id="rail-report">Exports</button>
    </nav>
    <div class="railfoot">Model status<br><b class="green">Ready for a run</b><br><span class="mono">baseline / calibrated</span></div>
  </aside>

  <main id="workspace" class="workspace">
    <header class="topbar">
      <div><h1>Farm overview</h1><p>Run calibrated scenarios, inspect outcomes, and compare farm systems.</p></div>
      <div class="topactions"><span class="status" id="stamp">READY</span><button class="ghost" id="open-report" type="button">Export research report</button></div>
    </header>
    <div class="workbench">
      <aside class="config">
        <div class="confighead"><h2>Run a simulation</h2><p>Configure, reproduce, and compare outcomes.</p></div>
        <form id="run">
          <div class="field"><label for="scenario"><span>Scenario</span><span>File</span></label><select id="scenario"></select></div>
          <div class="field"><label for="days"><span>Run length</span><span>Days</span></label><input id="days" type="number" min="1" max="3650" step="1"><div class="pills" id="presetbar"><button type="button" data-d="1">Day</button><button type="button" data-d="30">Month</button><button type="button" data-d="365">Year</button></div></div>
          <div class="field"><label for="seed"><span>Seed</span><span>Reproducible</span></label><input id="seed" type="number" step="1"><div class="hint">Same seed gives identical output.</div></div>
          <div class="field"><label for="herd"><span>Herd size</span><span>Animals</span></label><input id="herd" type="number" min="1" step="1"></div>
          <div class="field"><label><span>Active systems</span><span>7 available</span></label><div class="switches" id="switches"></div></div>
          <button id="go" type="submit">Run simulation</button>
        </form>
      </aside>
      <section class="result" id="results">
        <div class="empty-state" id="empty"><h2>See what the farm can become.</h2><p>Choose a scenario, set the run length, seed, and herd size, then run the model. Your results will appear here as a ledger or as clean graphs for daily, monthly, and yearly analysis.</p></div>
      </section>
    </div>
  </main>
</div>

<section id="report" class="report" aria-label="Research report export">
  <div class="reporttop"><h2>Dairy Farm ABM / Research report</h2><span class="mono" id="report-meta">READY FOR A RUN</span></div>
  <div id="report-content"><div class="empty-state"><h2>No report yet.</h2><p>Run a simulation first, then export the research report from the workbench.</p></div></div>
  <div class="back"><button id="back-workspace" type="button">Back to workbench</button></div>
</section>
<footer>Simulation output only - not validated scientific or financial results.<br>Same engine and seed rules as <code>python3 -m dairy_abm run</code>.</footer>

<script>
"use strict";
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const fmt = (n, d=0) => (n===null||n===undefined||isNaN(n)) ? "-" :
  Number(n).toLocaleString("en-US", {minimumFractionDigits:d, maximumFractionDigits:d});
let currentRunId = null;   // id of the run whose output can be downloaded

const PERIODS = [["daily","Daily"],["monthly","Monthly"],["yearly","Yearly"]];
const TABS = [["ledger","Ledger"],["graphs","Graphs"]];
const state = { view: "ledger", period: "daily", data: null };

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

// 1 = sum, 0 = average, for monthly / yearly roll-ups of the daily run.
const AGG = { milk_l:1, profit:1, net_kg_co2e:1, freshwater_withdrawal_l:1,
  active_disease_cases:1, kg_co2e_per_l_milk:0, energy_self_sufficiency_pct:0,
  input_circularity:0, output_circularity:0, cow_count:0, sustainability_score_0_100:0 };

async function loadDefaults() {
  const data = await (await fetch("/api/scenario")).json();
  const def = data.defaults;
  $("scenario").innerHTML = data.scenarios
    .map(s => `<option value="${esc(s)}">${esc(s.replace(/\.json$/,""))}</option>`).join("");
  $("scenario").value = data.scenarios.includes("baseline.json") ? "baseline.json" : data.scenarios[0];
  $("days").value = def.days; $("seed").value = def.seed; $("herd").value = def.herd_size;
  $("switches").innerHTML = TOGGLE_KEYS.map(([key,label]) =>
    `<label class="switch"><span>${label}</span>
      <input type="checkbox" data-k="${key}" ${def[key] ? "checked" : ""}></label>`).join("");
}

// Roll the daily series up to monthly or yearly rows.
function aggregate(rows, period) {
  if (period === "daily") return rows.slice();
  const g = new Map();
  rows.forEach(r => {
    const id = period === "monthly" ? r.day.slice(0,7) : r.day.slice(0,4);
    if (!g.has(id)) g.set(id, { sum:{}, n:0 });
    const b = g.get(id); b.n++;
    for (const k in AGG) if (r[k] != null) b.sum[k] = (b.sum[k]||0) + Number(r[k]);
  });
  return Array.from(g.keys()).sort().map(id => {
    const b = g.get(id), row = { day:id };
    for (const k in AGG) if (b.sum[k] != null) row[k] = AGG[k] ? b.sum[k] : b.sum[k]/b.n;
    return row;
  });
}

function periodLabel(day, period) {
  if (period === "yearly") return day;
  return period === "monthly" ? day.slice(2) : day.slice(5); // month or MM-DD
}

// ---------- SVG chart drawing (no dependencies) ----------
const CH = { W:520, H:244, L:76, R:18, T:48, B:40 };

function svgChart(o) {
  const rows = o.rows, W=CH.W, H=CH.H, L=CH.L, R=CH.R, T=CH.T, B=CH.B;
  const plotW = W-L-R, plotH = H-T-B, n = rows.length || 1;
  const gx = i => L + (n===1 ? plotW/2 : (i/(n-1))*plotW);
  const barX = i => L + ((i + 0.5)/n)*plotW;
  const all = [];
  o.series.forEach(s => rows.forEach(r => all.push(Number(r[s.key])||0)));
  let min = 0, max = Math.max(...all, 1);
  if (o.floor === false) { min = Math.min(...all); if (min > 0) min = 0; }
  if (max <= min) max = min + 1;
  const span = max - min;
  const gy = v => T + (1 - (v-min)/span)*plotH;
  const ydec = (o.ydec != null) ? o.ydec : (span < 10 ? 2 : 0);
  const valTxt = v => fmt(v, ydec);
  const xText = day => periodLabel(day, o.period);

  let grid = "", yLabels = "";
  const ticks = 4;
  for (let i=0; i<=ticks; i++) {
    const v = min + span*i/ticks, y = gy(v);
    grid += `<line x1="${L}" y1="${y.toFixed(1)}" x2="${W-R}" y2="${y.toFixed(1)}" class="ax"/>`;
    yLabels += `<text x="${L-10}" y="${(y+3).toFixed(1)}" class="axislabel" text-anchor="end">${valTxt(v)}</text>`;
  }
  const xIndexes = [...new Set(n<=1 ? [0] : [0, Math.floor((n-1)/2), n-1])];
  const xLabels = xIndexes.map(i =>
    `<text x="${gx(i).toFixed(1)}" y="${H-12}" class="axislabel" text-anchor="middle">${xText(rows[i].day)}</text>`).join("");
  const axes = `<line x1="${L}" y1="${T+plotH}" x2="${W-R}" y2="${T+plotH}" class="baseline"/>`;

  let body = "";
  o.series.forEach((s, si) => {
    const col = s.color;
    if (o.kind === "bar") {
      const bw = Math.min(48, Math.max(2, plotW/n*0.62));
      const base = gy(0);
      rows.forEach((r, i) => {
        const v = Number(r[s.key])||0, top = gy(v), hi = Math.abs(top-base);
        body += `<rect x="${(barX(i)-bw/2).toFixed(1)}" y="${Math.min(top,base).toFixed(1)}" width="${bw.toFixed(1)}" height="${hi.toFixed(1)}" fill="${col}" opacity="0.85"><title>${r.day} - ${fmt(v,o.dec||0)} ${o.unit||""}</title></rect>`;
      });
    } else {
      const pts = rows.map((r,i) => `${gx(i).toFixed(1)},${gy(Number(r[s.key])||0).toFixed(1)}`).join(" ");
      if (n === 1) body += `<circle cx="${gx(0).toFixed(1)}" cy="${gy(Number(rows[0][s.key])||0).toFixed(1)}" r="3" fill="${col}"/>`;
      if (o.area !== false) body += `<polygon points="${pts} ${gx(n-1).toFixed(1)},${gy(0).toFixed(1)} ${gx(0).toFixed(1)},${gy(0).toFixed(1)}" fill="${col}" opacity="${si===1?0.08:0.12}"/>`;
      body += `<polyline points="${pts}" fill="none" stroke="${col}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>`;
      rows.forEach((r,i) => body += `<circle cx="${gx(i).toFixed(1)}" cy="${gy(Number(r[s.key])||0).toFixed(1)}" r="14" fill="transparent"><title>${r.day} ${s.label}: ${fmt(Number(r[s.key])||0,o.dec||0)} ${o.unit||""}</title></circle>`);
    }
  });

  const ns = o.series.length;
  const legend = o.series.map((s,i) =>
    `<rect x="${W-R-14-ns*86+i*86}" y="11" width="8" height="8" fill="${s.color}"/>` +
    `<text x="${W-R-14-ns*86+i*86+12}" class="lg" y="19">${s.label}</text>`).join("");
  return `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" xmlns="http://www.w3.org/2000/svg" class="gsv">
      <rect width="${W}" height="${H}" fill="#fff"/>
      <text x="10" y="21" class="ttl">${esc(o.title)}</text>
      ${legend}${grid}${yLabels}${xLabels}${axes}${body}
    </svg>`;
}



function buildCharts(rows, period) {
  const D = (over) => Object.assign({rows, period}, over);
  return [
    { s: svgChart(D({title:"Milk produced", kind:"area", unit:"L", dec:0, ydec:0, series:[{key:"milk_l",color:"#b42318",label:"Milk"}]})) },
    { s: svgChart(D({title:"Net CO2e", kind:"bar", unit:"kg", dec:0, ydec:0, series:[{key:"net_kg_co2e",color:"#c2412d",label:"CO2e"}]})) },
    { s: svgChart(D({title:"Profit", kind:"area", unit:"", dec:0, ydec:0, floor:false, series:[{key:"profit",color:"#3f6b4f",label:"Profit"}]})) },
    { s: svgChart(D({title:"Energy self-sufficiency (%)", kind:"area", unit:"%", dec:1, ydec:0, series:[{key:"energy_self_sufficiency_pct",color:"#4f7d5c",label:"Self-suff"}]})) },
    { s: svgChart(D({title:"Freshwater drawn", kind:"bar", unit:"L", dec:0, ydec:0, series:[{key:"freshwater_withdrawal_l",color:"#527a61",label:"Water"}]})) },
    { s: svgChart(D({title:"Circularity (input / output)", kind:"area", unit:"", dec:3, ydec:2, floor:false, series:[{key:"input_circularity",color:"#b42318",label:"Input"},{key:"output_circularity",color:"#3f6b4f",label:"Output"}]})) },
    { s: svgChart(D({title:"Sustainability score", kind:"area", unit:"/100", dec:1, ydec:0, series:[{key:"sustainability_score_0_100",color:"#2f6f4e",label:"Score"}]})) },
    { s: svgChart(D({title:"Disease cases", kind:"bar", unit:"", dec:0, ydec:0, series:[{key:"active_disease_cases",color:"#b42318",label:"Cases"}]})) },
  ];
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
  const body = {
    scenario: $("scenario").value,
    days: parseInt($("days").value, 10),
    seed: $("seed").value === "" ? null : parseInt($("seed").value, 10),
    herd_size: $("herd").value === "" ? null : parseInt($("herd").value, 10),
  };
  document.querySelectorAll("#switches input").forEach(inp => body[inp.dataset.k] = inp.checked);
  try {
    const res = await fetch("/api/run", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(body)});
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || ("HTTP " + res.status));
    currentRunId = data.id;
    state.data = data;
    state.view = "graphs";
    state.period = "daily";
    render();
    $("stamp").textContent = "SIMULATED";
  } catch (err) {
    $("stamp").textContent = "ERROR";
    $("results").innerHTML = '<div class="err"><b>Run failed:</b> ' + esc(err.message) + '</div>';
  } finally {
    go.disabled = false;
    go.textContent = "Run simulation";
  }
}

async function download() {
  if (!currentRunId) return;
  const res = await fetch("/api/export/" + currentRunId);
  if (!res.ok) return;
  const blob = await res.blob();
  saveBlob(blob, "dairy-" + currentRunId + "-output.zip");
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
  if (b.dataset.view) { state.view = b.dataset.view; render(); }
  else if (b.dataset.period) { state.period = b.dataset.period; render(); }
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
loadDefaults();
$("run").addEventListener("submit", onRun);
$("open-report").addEventListener("click", showReport);
$("rail-report").addEventListener("click", showReport);
$("back-workspace").addEventListener("click", hideReport);
</script>
</body>
</html>
"""


def main() -> None:
    port = 8765
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print("Dairy Farm ABM run desk")
    print(f"  open http://localhost:{port}  (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()