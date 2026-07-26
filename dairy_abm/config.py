from __future__ import annotations

from pathlib import Path
from typing import Any

from dairy_abm.core import ConfigError, deep_merge, read_json


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CALIBRATION_PATH = ROOT / "configs" / "calibration.json"


def load_calibration(path: str | None = None) -> dict[str, Any]:
    base = read_json(DEFAULT_CALIBRATION_PATH)
    if path is None:
        validate_calibration(base)
        return base
    calibration = deep_merge(base, read_json(Path(path)))
    validate_calibration(calibration)
    return calibration


def calibration_inventory(calibration: dict[str, Any]) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []

    def walk(prefix: str, node: Any) -> None:
        if isinstance(node, dict) and {"value", "unit", "source", "assumption"} <= set(node):
            inventory.append(
                {
                    "key": prefix,
                    "agent": prefix.split(".", 1)[0],
                    "default": node["value"],
                    "unit": node["unit"],
                    "source": node["source"],
                    "assumption": node["assumption"],
                    "description": node.get("description", ""),
                    "valid_range": node.get("valid_range", ""),
                }
            )
            return
        if isinstance(node, dict):
            for key, value in node.items():
                walk(f"{prefix}.{key}" if prefix else key, value)

    walk("", calibration)
    return sorted(inventory, key=lambda item: item["key"])


def value(calibration: dict[str, Any], dotted_key: str) -> Any:
    node: Any = calibration
    for part in dotted_key.split("."):
        node = node[part]
    if isinstance(node, dict) and "value" in node:
        return node["value"]
    return node


def validate_calibration(calibration: dict[str, Any]) -> None:
    inventory = calibration_inventory(calibration)
    if not inventory:
        raise ConfigError("calibration inventory is empty")
    required_fields = {"key", "agent", "default", "unit", "source", "assumption", "description", "valid_range"}
    for row in inventory:
        missing = required_fields - set(row)
        if missing:
            raise ConfigError(f"calibration row {row.get('key', '<unknown>')} missing {sorted(missing)}")
        if not isinstance(row["assumption"], bool):
            raise ConfigError(f"calibration row {row['key']} assumption must be boolean")
        if row["valid_range"] == "true,false" and not isinstance(row["default"], bool):
            raise ConfigError(f"calibration row {row['key']} must have a boolean value")

    _require_sum(
        calibration,
        [
            "genetics.trait_weights.milk_yield",
            "genetics.trait_weights.feed_efficiency",
            "genetics.trait_weights.fertility",
            "genetics.trait_weights.health",
            "genetics.trait_weights.survivability",
        ],
        "genetics trait weights",
    )
    _require_sum(
        calibration,
        [
            "manure.digester_route_fraction",
            "manure.compost_route_fraction",
            "manure.storage_route_fraction",
        ],
        "manure route fractions",
    )
    _require_sum(
        calibration,
        [
            "environment.circularity_weight_energy",
            "environment.circularity_weight_nutrients",
            "environment.circularity_weight_water",
            "environment.circularity_weight_products",
        ],
        "circularity weights",
    )
    _require_sum(
        calibration,
        [
            "dairy_processor.product_mix_cheese",
            "dairy_processor.product_mix_butter",
            "dairy_processor.product_mix_yogurt",
            "dairy_processor.product_mix_fresh",
            "dairy_processor.product_mix_functional",
        ],
        "processor product mix",
    )
    _require_fractions(
        calibration,
        [
            "dairy_processor.fraction_whey_to_feed",
            "dairy_processor.fraction_sludge_to_energy",
            "dairy_processor.fraction_waste_milk_to_feed",
        ],
        "processor residual route fractions",
    )


def _require_sum(calibration: dict[str, Any], keys: list[str], label: str) -> None:
    total = sum(float(value(calibration, key)) for key in keys)
    if abs(total - 1.0) > 0.000001:
        raise ConfigError(f"{label} must sum to 1.0, got {total}")


def _require_fractions(calibration: dict[str, Any], keys: list[str], label: str) -> None:
    for key in keys:
        fraction = float(value(calibration, key))
        if not 0.0 <= fraction <= 1.0:
            raise ConfigError(f"{label}: {key} must be between 0.0 and 1.0, got {fraction}")
