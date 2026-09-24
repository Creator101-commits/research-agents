"""Build the read-only formula and value reference served by the dashboard."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "web" / "data" / "formulas_values.json"

DAILY_STAGES = [
    ("Market", "self.market_agent.tick(day)", "Set prices and market signals."),
    ("Sensors", "self.sensors_agent.tick(day)", "Observe weather, feed, health, and reproduction signals."),
    ("Land, when enabled", "self.land_agent.tick(day)", "Publish land and grazing context."),
    ("Feed and crop", "self.feed_crop_agent.tick(day)", "Build the ration and account for feed and nutrients."),
    ("Policy dispatch", "self.farm_manager_agent.dispatch_policy(day)", "Apply management decisions before production."),
    ("Disease", "self.disease_agent.tick(day)", "Update infections, recovery, and treatment."),
    ("Water delivery", "self.water_agent.prepare_delivery(day)", "Prepare drinking and parlor water."),
    ("Cow", "self.cow_agent.tick(day)", "Update individual cows and herd production."),
    ("Dairy processor", "self.processor_agent.tick(day)", "Process milk and route byproducts when enabled."),
    ("Manure", "self.manure_agent.tick(day)", "Route manure to digestion, compost, and storage."),
    ("Energy", "self.energy_agent.tick(day)", "Convert available inputs to electricity and heat."),
    ("Water accounting", "self.water_agent.tick(day)", "Treat, reuse, and price water."),
    ("Environment", "self.environment_agent.tick(day)", "Post emissions, offsets, nutrients, and circularity."),
    ("Farm manager", "self.farm_manager_agent.tick(day)", "Close daily revenue, cost, and profit accounts."),
    ("Genetics intake", "self.genetics_agent.record_daily_intake(day)", "Record intake evidence for selection."),
]


def _paths() -> list[Path]:
    paths = sorted((ROOT / "dairy_abm").rglob("*.py"))
    paths.extend([ROOT / "webapp.py", ROOT / "web" / "js" / "dashboard.js"])
    paths.extend([ROOT / "configs" / "calibration.json", ROOT / "configs" / "genetics_nm9.json"])
    paths.extend(sorted((ROOT / "scenarios").glob("*.json")))
    return paths


def _name_for(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> str:
    parts = []
    current = parents.get(node)
    while current is not None:
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            parts.append(current.name)
        current = parents.get(current)
    return ".".join(reversed(parts)) or "module"


def _python_indexes(path: str, source: str) -> tuple[list[dict], list[dict]]:
    tree = ast.parse(source)
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    calculations = []
    literals = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Return)):
            expression = node.value
            if expression is not None and any(
                isinstance(part, (ast.BinOp, ast.IfExp, ast.Compare)) for part in ast.walk(expression)
            ):
                segment = ast.get_source_segment(source, node)
                if segment:
                    calculations.append({
                        "path": path, "line": node.lineno,
                        "scope": _name_for(node, parents), "expression": segment,
                    })
        if isinstance(node, ast.Constant) and type(node.value) in (int, float, bool):
            line = source.splitlines()[node.lineno - 1].strip()
            literals.append({
                "path": path, "line": node.lineno,
                "scope": _name_for(node, parents),
                "value": node.value, "context": line,
            })
    calculations.sort(key=lambda item: item["line"])
    literals.sort(key=lambda item: item["line"])
    return calculations, literals


def _javascript_indexes(path: str, source: str) -> tuple[list[dict], list[dict]]:
    """Index executable JavaScript lines while masking strings and comments."""
    calculations = []
    literals = []
    number = re.compile(r"(?<![\w$.])(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?")
    block_comment = False
    quote = None
    scope = "module"
    for line_number, line in enumerate(source.splitlines(), 1):
        masked = []
        index = 0
        while index < len(line):
            char = line[index]
            next_char = line[index + 1] if index + 1 < len(line) else ""
            if block_comment:
                if char == "*" and next_char == "/":
                    masked.extend("  ")
                    index += 2
                    block_comment = False
                else:
                    masked.append(" ")
                    index += 1
                continue
            if quote is not None:
                if char == "\\":
                    masked.extend("  " if next_char else " ")
                    index += 2 if next_char else 1
                elif char == quote:
                    masked.append(" ")
                    index += 1
                    quote = None
                else:
                    masked.append(" ")
                    index += 1
                continue
            if char == "/" and next_char == "/":
                masked.extend(" " * (len(line) - index))
                break
            if char == "/" and next_char == "*":
                masked.extend("  ")
                index += 2
                block_comment = True
                continue
            if char in ("'", '"', "`"):
                quote = char
                masked.append(" ")
            else:
                masked.append(char)
            index += 1
        if quote != "`":
            quote = None
        code = "".join(masked)
        function = re.search(r"\b(?:async\s+)?function\s+(\w+)\s*\(", code)
        declaration = re.search(r"^\s*const\s+([A-Z][A-Z_]+)\s*=", code)
        if function:
            scope = function.group(1)
        elif declaration:
            scope = declaration.group(1)
        for match in number.finditer(code):
            literals.append({
                "path": path, "line": line_number, "scope": scope,
                "value": match.group(), "context": line.strip(),
            })
        if re.search(r"[=+*/%<>?-]", code) and re.search(r"[+*/%<>?-]|\breturn\b", code):
            if code.strip() and not code.lstrip().startswith(("import ", "export ")):
                calculations.append({
                    "path": path, "line": line_number,
                    "scope": scope, "expression": line.strip(),
                })
    return calculations, literals


def _calibration_values() -> list[dict]:
    data = json.loads((ROOT / "configs" / "calibration.json").read_text())
    rows = []

    def visit(node: dict, prefix: str) -> None:
        for key, entry in node.items():
            name = f"{prefix}.{key}" if prefix else key
            if not isinstance(entry, dict):
                continue
            if "value" in entry:
                rows.append({"key": name, "group": name.split(".")[0], **entry})
            else:
                visit(entry, name)

    for group, entries in data.items():
        if group != "metadata" and isinstance(entries, dict):
            visit(entries, group)
    return sorted(rows, key=lambda item: item["key"])


def _configuration_values() -> list[dict]:
    rows = []
    config_paths = [ROOT / "configs" / "genetics_nm9.json", *sorted((ROOT / "scenarios").glob("*.json"))]

    def visit(node: object, prefix: str, path: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                visit(value, f"{prefix}.{key}" if prefix else key, path)
        elif isinstance(node, list):
            for index, value in enumerate(node):
                visit(value, f"{prefix}[{index}]", path)
        else:
            rows.append({"path": path, "key": prefix, "value": node})

    for file in config_paths:
        path = file.relative_to(ROOT).as_posix()
        visit(json.loads(file.read_text()), "", path)
    return rows


def build_reference() -> dict:
    files = []
    calculations = []
    literals = []
    frontend_calculations = []
    frontend_literals = []
    for file in _paths():
        path = file.relative_to(ROOT).as_posix()
        source = file.read_text()
        files.append({
            "path": path,
            "sha256": hashlib.sha256(source.encode()).hexdigest(),
            "lines": len(source.splitlines()),
            "text": source,
        })
        if file.suffix == ".py":
            found_calculations, found_literals = _python_indexes(path, source)
            calculations.extend(found_calculations)
            literals.extend(found_literals)
        elif path == "web/js/dashboard.js":
            frontend_calculations, frontend_literals = _javascript_indexes(path, source)
    daily_source = (ROOT / "dairy_abm" / "model.py").read_text()
    daily_body = ast.get_source_segment(
        daily_source,
        next(node for node in ast.walk(ast.parse(daily_source))
             if isinstance(node, ast.FunctionDef) and node.name == "_run_daily"),
    )
    assert daily_body is not None
    positions = [daily_body.index(call) for _, call, _ in DAILY_STAGES]
    if positions != sorted(positions):
        raise ValueError("daily scheduler order changed; update the reference")
    return {
        "schema": 1,
        "scope": "Current Python model, its dashboard adapter, the active dashboard script, and configuration files.",
        "daily_process": [
            {"number": number, "name": name, "call": call, "description": description}
            for number, (name, call, description) in enumerate(DAILY_STAGES, 1)
        ],
        "calendar_process": [
            {"name": "Every day", "description": "Run the daily sequence and record daily outputs."},
            {"name": "Sunday", "description": "Run each agent's weekly hook."},
            {"name": "Month end", "description": "Run each agent's monthly hook."},
            {"name": "December 31", "description": "Run annual hooks, including genetics selection."},
            {"name": "Run end", "description": "Finalize investment and DMC analyses."},
        ],
        "calibration": _calibration_values(),
        "configuration": _configuration_values(),
        "calculations": calculations,
        "literals": literals,
        "frontend_calculations": frontend_calculations,
        "frontend_literals": frontend_literals,
        "files": files,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the dashboard snapshot is stale")
    args = parser.parse_args()
    rendered = json.dumps(build_reference(), ensure_ascii=False, separators=(",", ":")) + "\n"
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text() != rendered:
            raise SystemExit("formula reference is stale; rerun scripts/generate_formula_reference.py")
        print("formula reference is current")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(rendered)
        print(f"wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
