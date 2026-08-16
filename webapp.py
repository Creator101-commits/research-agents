#!/usr/bin/env python3
"""Web run-desk for the dairy farm agent-based model.

Zero-dependency local server (stdlib only). Serves the static web frontend and JSON API
that runs the real DairyFarmModel and returns the daily ledger plus summary figures.
results stay in memory and exports use temporary files outside the repository.

Usage:  python3 webapp.py   ->  open http://localhost:8765
"""

from __future__ import annotations

import io
import json
import mimetypes
import tempfile
import time
import uuid
import zipfile
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from dairy_abm.config import apply_calibration_overrides, calibration_inventory, load_calibration
from dairy_abm.core import read_json
from dairy_abm.dashboard import (
    serialize_comparison,
    serialize_dashboard_config,
    serialize_dashboard_run,
)
from dairy_abm.model import DairyFarmModel
from dairy_abm.reports import REPORT_CONTRACT, write_reports
ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
SCENARIO_DIR = ROOT / "scenarios"
DEFAULT_SCENARIO = read_json(SCENARIO_DIR / "baseline.json")
CALIBRATION = load_calibration(None)

@dataclass
class CachedRun:
    ctx: object
    duration_s: float
    calibration_overrides: dict
    serialized: dict | None = None


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
    if not isinstance(params, dict):
        raise ValueError("request body must be a JSON object")

    suspected = params.get("scenario")
    if suspected is not None and not isinstance(suspected, str):
        raise ValueError("scenario must be a file name")
    scenario = dict(DEFAULT_SCENARIO)
    if suspected:
        scenario_root = SCENARIO_DIR.resolve()
        path = (scenario_root / suspected).resolve()
        try:
            path.relative_to(scenario_root)
        except ValueError as exc:
            raise ValueError(f"scenario file must live under {SCENARIO_DIR.name}/") from exc
        if not path.is_file():
            raise ValueError(f"scenario file not found: {suspected}")
        scenario = read_json(path)

    override_keys = (
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
    )
    nested_overrides = params.get("scenario_overrides", {})
    if not isinstance(nested_overrides, dict):
        raise ValueError("scenario_overrides must be an object")
    unknown = set(nested_overrides) - set(override_keys)
    if unknown:
        raise ValueError(f"unsupported scenario override: {sorted(unknown)[0]}")

    scenario_updates = {key: params[key] for key in override_keys if key in params}
    duplicates = set(scenario_updates).intersection(nested_overrides)
    if duplicates:
        raise ValueError(f"scenario override provided twice: {sorted(duplicates)[0]}")
    scenario_updates.update(nested_overrides)
    nullable_keys = {"seed", "herd_size"}
    for key, override in scenario_updates.items():
        if override is None:
            if key in nullable_keys:
                continue
            raise ValueError(f"{key} must be provided")
        scenario[key] = override

    days = scenario.get("days", 10)
    if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 3650:
        raise ValueError("days must be a whole number between 1 and 3650")
    herd_size = scenario.get("herd_size", 100)
    if isinstance(herd_size, bool) or not isinstance(herd_size, int) or herd_size < 0:
        raise ValueError("herd_size must be a whole number of zero or more")
    seed = scenario.get("seed", 1)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be a whole number")
    for key in (
        "enable_processor",
        "enable_whey_processing",
        "enable_land_agent",
        "l1_nutrient_loop_enabled",
        "l2_water_loop_enabled",
        "l3_energy_loop_enabled",
        "l4_byproduct_loop_enabled",
    ):
        if key in scenario and not isinstance(scenario[key], bool):
            raise ValueError(f"{key} must be a boolean")
    calibration_overrides = params.get("calibration_overrides", {})
    if not isinstance(calibration_overrides, dict):
        raise ValueError("calibration_overrides must be an object")
    run_calibration = apply_calibration_overrides(CALIBRATION, calibration_overrides)

    t0 = time.perf_counter()
    ctx = DairyFarmModel(scenario, run_calibration).run()
    duration_s = time.perf_counter() - t0

    run_id = uuid.uuid4().hex[:8]
    result = serialize_dashboard_run(
        ctx, run_id, duration_s, calibration_overrides=calibration_overrides
    )
    RUN_CACHE[run_id] = CachedRun(
        ctx=ctx,
        duration_s=duration_s,
        calibration_overrides=dict(calibration_overrides),
        serialized=result,
    )
    while len(RUN_CACHE) > 10:  # keep the last ten runs downloadable
        RUN_CACHE.pop(next(iter(RUN_CACHE)))
    return result



def _cached_context(entry: object) -> object:
    return entry.ctx if isinstance(entry, CachedRun) else entry


def _cached_payload(run_id: str, entry: object) -> dict:
    if isinstance(entry, CachedRun) and entry.serialized is not None:
        return entry.serialized
    return serialize_dashboard_run(_cached_context(entry), run_id, 0.0)


def _export_zip(entry: object) -> bytes:
    """All report files for a finished run, zipped in memory (same files the CLI writes)."""
    with tempfile.TemporaryDirectory() as tmp:
        ctx = _cached_context(entry)
        write_reports(Path(tmp), ctx)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for file in sorted(Path(tmp).iterdir()):
                archive.write(file, file.name)
        return buffer.getvalue()


_EXPORT_FILES = {
    "summary.json": "application/json",
    "daily.csv": "text/csv; charset=utf-8",
    "schedule.csv": "text/csv; charset=utf-8",
    "monthly.csv": "text/csv; charset=utf-8",
    "annual.csv": "text/csv; charset=utf-8",
    "calibration_inventory.json": "application/json",
}
_EXPORT_ALIASES = {
    "summary": "summary.json",
    "daily": "daily.csv",
    "schedule": "schedule.csv",
    "monthly": "monthly.csv",
    "annual": "annual.csv",
    "calibration": "calibration_inventory.json",
    "calibration_inventory": "calibration_inventory.json",
    "zip": "export.zip",
}


def _export_file(entry: object, filename: str) -> bytes:
    filename = _EXPORT_ALIASES.get(filename, filename)
    if filename == "export.zip":
        return _export_zip(entry)
    if filename not in _EXPORT_FILES:
        raise ValueError(f"unknown export artifact: {filename}")
    with tempfile.TemporaryDirectory() as tmp:
        output_dir = Path(tmp)
        write_reports(output_dir, _cached_context(entry))
        return (output_dir / filename).read_bytes()


def _comparison_model_config(item: object, index: int) -> tuple[dict, str | None]:
    if not isinstance(item, dict):
        raise ValueError(f"runs[{index}] must be an object")
    allowed = {"label", "scenario", "scenario_overrides", "calibration_overrides"}
    unknown = set(item) - allowed
    if unknown:
        raise ValueError(f"runs[{index}] has unsupported field: {sorted(unknown)[0]}")
    label = item.get("label")
    if label is not None and (not isinstance(label, str) or not label.strip()):
        raise ValueError(f"runs[{index}].label must be a non-empty string")
    scenario = item.get("scenario")
    if not isinstance(scenario, str) or not scenario:
        raise ValueError(f"runs[{index}].scenario must be a file name")
    scenario_overrides = item.get("scenario_overrides", {})
    if not isinstance(scenario_overrides, dict):
        raise ValueError(f"runs[{index}].scenario_overrides must be an object")
    calibration_overrides = item.get("calibration_overrides", {})
    if not isinstance(calibration_overrides, dict):
        raise ValueError(f"runs[{index}].calibration_overrides must be an object")
    scenario_overrides = dict(scenario_overrides)
    if "seed" not in scenario_overrides:
        scenario_overrides["seed"] = DEFAULT_SCENARIO.get("seed", 1)
    return (
        {
            "scenario": scenario,
            "scenario_overrides": scenario_overrides,
            "calibration_overrides": dict(calibration_overrides),
        },
        label,
    )


def _compare_model_runs(params: dict) -> dict:
    if not isinstance(params, dict):
        raise ValueError("request body must be a JSON object")
    requested = params.get("runs")
    if not isinstance(requested, list) or len(requested) < 2:
        raise ValueError("comparison requires at least two run configurations")
    configs = [_comparison_model_config(item, index) for index, item in enumerate(requested)]
    runs = []
    for config, label in configs:
        result = _run_simulation(config)
        runs.append({"result": result, "label": label})
    return serialize_comparison(runs)


def _is_cached_comparison(params: dict) -> bool:
    if "run_ids" in params:
        return True
    requested = params.get("runs")
    return isinstance(requested, list) and all(
        isinstance(item, str)
        or (isinstance(item, dict) and ("run_id" in item or "id" in item))
        for item in requested
    )


def _compare_cached_runs(params: dict) -> dict:
    if not isinstance(params, dict):
        raise ValueError("request body must be a JSON object")

    labels: dict[str, str] = {}
    run_ids = params.get("run_ids")
    if run_ids is None:
        requested = params.get("runs")
        if not isinstance(requested, list):
            raise ValueError("run_ids must be a list of cached run IDs")
        run_ids = []
        for item in requested:
            if isinstance(item, str):
                run_ids.append(item)
            elif isinstance(item, dict):
                run_id = item.get("run_id", item.get("id"))
                run_ids.append(run_id)
                if isinstance(run_id, str) and isinstance(item.get("label"), str):
                    labels[run_id] = item["label"]
            else:
                run_ids.append(item)

    if not isinstance(run_ids, list) or len(run_ids) < 2:
        raise ValueError("comparison requires at least two cached run IDs")
    if not isinstance(params.get("labels", {}), dict):
        raise ValueError("labels must be an object")
    labels.update(params.get("labels", {}))

    runs = []
    for run_id in run_ids:
        if not isinstance(run_id, str) or not run_id:
            raise ValueError("run IDs must be non-empty strings")
        entry = RUN_CACHE.get(run_id)
        if entry is None:
            raise ValueError(f"run not found or too old: {run_id}")
        item = {"result": _cached_payload(run_id, entry)}
        if isinstance(labels.get(run_id), str):
            item["label"] = labels[run_id]
        runs.append(item)
    return serialize_comparison(runs)


def _compare_runs(params: dict) -> dict:
    if not isinstance(params, dict):
        raise ValueError("request body must be a JSON object")
    return _compare_cached_runs(params) if _is_cached_comparison(params) else _compare_model_runs(params)

def _static_file(path: str) -> Path | None:
    """Resolve an allowed web path without permitting traversal or symlink escapes."""
    if path in ("/", "/index.html"):
        relative = Path("index.html")
    elif path.startswith("/assets/"):
        relative = Path(unquote(path.removeprefix("/assets/")))
    else:
        return None
    root = WEB_ROOT.resolve()
    try:
        candidate = (root / relative).resolve(strict=True)
        candidate.relative_to(root)
    except (OSError, ValueError):
        return None
    return candidate if candidate.is_file() else None


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

    def _send_file(self, path: Path) -> None:
        body = path.read_bytes()
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if path.suffix == ".js":
            ctype = "text/javascript; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = unquote(urlparse(self.path).path)
        static = _static_file(path)
        if static is not None:
            self._send_file(static)
            return
        if path in ("/", "/index.html") or path.startswith("/assets/"):
            self._send(404, {"error": "static file not found"})
            return
        if path == "/api/scenario":
            names = sorted(p.name for p in SCENARIO_DIR.glob("*.json"))
            self._send(200, {"defaults": DEFAULT_SCENARIO, "scenarios": names})
        elif path == "/api/config":
            names = sorted(p.name for p in SCENARIO_DIR.glob("*.json"))
            self._send(
                200,
                serialize_dashboard_config(DEFAULT_SCENARIO, CALIBRATION, names, REPORT_CONTRACT),
            )
        elif path == "/api/calibration":
            self._send(200, {"parameters": calibration_inventory(CALIBRATION)})
        elif path.startswith("/api/run/"):
            run_id = path.removeprefix("/api/run/")
            entry = RUN_CACHE.get(run_id)
            if entry is None:
                self._send(404, {"error": "run not found or too old"})
                return
            self._send(200, _cached_payload(run_id, entry))
        elif path.startswith("/api/export/"):
            relative = path.removeprefix("/api/export/")
            parts = relative.split("/")
            run_id = parts[0] if parts else ""
            artifact = parts[1] if len(parts) > 1 else "export.zip"
            entry = RUN_CACHE.get(run_id)
            if entry is None:
                self._send(404, {"error": "run not found or too old to export"})
                return
            canonical = _EXPORT_ALIASES.get(artifact, artifact)
            if len(parts) > 2 or (canonical != "export.zip" and canonical not in _EXPORT_FILES):
                self._send(404, {"error": "unknown export artifact"})
                return
            try:
                body = _export_file(entry, canonical)
            except ValueError as exc:
                self._send(404, {"error": str(exc)})
                return
            ctx = _cached_context(entry)
            name = ctx.scenario.get("name", "run")
            content_type = "application/zip" if canonical == "export.zip" else _EXPORT_FILES[canonical]
            download_name = f"{name}-output.zip" if canonical == "export.zip" else canonical
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Disposition", f'attachment; filename="{download_name}"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path not in ("/api/run", "/api/compare"):
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
        except Exception as exc:  # malformed request body
            self._send(400, {"error": f"bad request: {exc}"})
            return
        try:
            result = _run_simulation(body) if path == "/api/run" else _compare_runs(body)
            self._send(200, {"ok": True, **result})
        except (TypeError, ValueError) as exc:
            self._send(400, {"error": str(exc)})
        except Exception as exc:
            self._send(500, {"error": str(exc)})



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