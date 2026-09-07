from __future__ import annotations

from copy import deepcopy
from typing import Any

from dairy_abm.config import apply_calibration_overrides
from dairy_abm.core import ConfigError, deep_merge


FARM_SYSTEM_PROFILES: dict[str, dict[str, Any]] = {
    "conventional": {
        "label": "Conventional",
        "scenario_defaults": {
            "production_system": "high_intensity",
            "enable_land_agent": False,
            "market_scenario": "NM",
            "milking_system": "conventional_parlor",
        },
        "constraints": {},
    },
    "robotic": {
        "label": "Robotic",
        "scenario_defaults": {
            "production_system": "high_intensity",
            "enable_land_agent": False,
            "market_scenario": "NM",
            "milking_system": "robotic",
            "precision_dairy_technology_count": 2,
        },
        "constraints": {
            "description": "Robotic milking and individual-cow sensing are active profile attributes. Operating effects require observed or explicitly overridden inputs.",
        },
    },
    "certified_organic": {
        "label": "Certified organic",
        "scenario_defaults": {
            "production_system": "humid_temperate",
            "enable_land_agent": True,
            "land_grazing_enabled": True,
            "market_scenario": "GM",
            "milking_system": "conventional_parlor",
            "organic_minimum_grazing_days": 120,
            "organic_minimum_pasture_dmi_fraction": 0.30,
        },
        "constraints": {
            "minimum_grazing_days": 120,
            "minimum_pasture_dmi_fraction": 0.30,
            "source": "https://www.ams.usda.gov/rules-regulations/organic/handbook/5017-1",
        },
    },
    "raw_milk": {
        "label": "Raw milk",
        "scenario_defaults": {
            "production_system": "humid_temperate",
            "enable_land_agent": False,
            "enable_processor": False,
            "enable_whey_processing": False,
            "direct_raw_milk_sales": True,
            "market_scenario": "FM",
            "milking_system": "conventional_parlor",
        },
        "constraints": {
            "description": "Milk remains in the farm-gate/raw-milk route. Price premiums and regulatory eligibility must be supplied as scenario or observed-market data.",
        },
    },
    "beef_on_dairy": {
        "label": "Beef-on-dairy",
        "scenario_defaults": {
            "production_system": "high_intensity",
            "enable_land_agent": False,
            "market_scenario": "CM",
            "milking_system": "conventional_parlor",
            "beef_on_dairy_enabled": True,
            "user_breeding_priority": "beef_on_dairy",
        },
        "constraints": {
            "description": "The profile changes breeding context. Calf-market revenue requires explicit observed or scenario values and is not inferred.",
        },
    },
}


def list_farm_systems() -> tuple[str, ...]:
    return tuple(FARM_SYSTEM_PROFILES)


def resolve_farm_system(
    scenario: dict[str, Any], calibration: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Apply a named system profile, then preserve explicit scenario overrides."""
    requested = str(scenario.get("farm_system", "conventional")).strip().lower().replace("-", "_")
    if requested not in FARM_SYSTEM_PROFILES:
        allowed = ", ".join(list_farm_systems())
        raise ConfigError(f"unsupported farm_system {requested!r}; expected one of {allowed}")

    profile = deepcopy(FARM_SYSTEM_PROFILES[requested])
    resolved = deep_merge(profile["scenario_defaults"], deepcopy(scenario))
    resolved["farm_system"] = requested
    resolved["farm_system_label"] = profile["label"]
    resolved["farm_system_constraints"] = deepcopy(profile["constraints"])

    overrides: dict[str, Any] = {}
    profile_overrides = profile.get("calibration_overrides", {})
    if isinstance(profile_overrides, dict):
        overrides.update(profile_overrides)
    scenario_overrides = resolved.get("calibration_overrides", {})
    if scenario_overrides:
        if not isinstance(scenario_overrides, dict):
            raise ConfigError("calibration_overrides must be an object")
        overrides.update(scenario_overrides)
    resolved_calibration = (
        apply_calibration_overrides(calibration, overrides) if overrides else deepcopy(calibration)
    )
    return resolved, resolved_calibration, profile
