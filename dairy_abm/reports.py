from __future__ import annotations

from pathlib import Path
from typing import Any

from dairy_abm.config import calibration_inventory, value
from dairy_abm.core import SimulationContext, write_csv, write_json


REPORT_CONTRACT = {
    "daily": {
        "period": "daily",
        "confidence": "per-record packet quality and confidence",
        "fields": {
            "report_confidence": "source:quality/confidence, pipe-delimited",
            "milk_l": "L",
            "purchased_feed_kg_dm": "kg dry matter",
            "irrigation_l": "L",
            "net_kwh": "kWh",
            "feedstock_tons": "tonnes/day",
            "electricity_generated_kwh": "kWh/day",
            "biogas_volume_m3": "m3/day",
            "biogas_gross_kwh": "kWh/day",
            "heat_generated_mj": "MJ/day",
            "energy_self_sufficiency_pct": "%",
            "net_water_l": "L",
            "freshwater_withdrawal_l": "L",
            "recycled_irrigation_l": "L",
            "recycled_irrigation_fraction": "fraction",
            "gross_kg_co2e": "kg CO2e",
            "avoided_kg_co2e": "kg CO2e",
            "net_kg_co2e": "kg CO2e",
            "kg_co2e_per_l_milk": "kg CO2e/L milk",
            "kg_co2e_per_kg_milk_protein": "kg CO2e/kg milk protein",
            "input_circularity": "fraction",
            "output_circularity": "fraction",
            "environment_nue": "fraction",
            "material_use_count": "count",
            "material_cycle_count": "count",
            "soil_carbon_delta_kg": "kg C/day",
            "synthetic_fertilizer_saved_kg": "kg N/day",
            "sustainability_score_0_100": "score",
            "disease_economic_cost": "currency/day",
            "policy_conflict_count": "count",
            "profit": "currency",
            "farm_system": "profile identifier",
            "raw_milk_revenue": "currency/day",
            "byproduct_revenue": "currency/day",
            "carbon_credit_value": "currency/day",
        },
    },
    "monthly": {
        "period": "calendar month",
        "confidence": "aggregated from daily packet confidence",
        "fields": {
            "milk_l": "L/month",
            "gross_kg_co2e": "kg CO2e/month",
            "avoided_kg_co2e": "kg CO2e/month",
            "net_kg_co2e": "kg CO2e/month",
            "profit": "currency/month",
            "soil_carbon_delta_kg": "kg C/month",
            "synthetic_fertilizer_saved_kg": "kg N/month",
        },
    },
    "annual": {
        "period": "calendar year",
        "confidence": "agent reported",
        "fields": {
            "genetic_gain_per_generation": "trait score/year",
            "herd_net_merit": "trait score",
        },
    },
    "experiment": {
        "period": "entire simulation",
        "confidence": "aggregated from daily packet confidence",
        "fields": {
            "net_kg_co2e": "kg CO2e/run",
            "kg_co2e_per_l_milk": "kg CO2e/L milk",
            "kg_co2e_per_kg_milk_protein": "kg CO2e/kg milk protein",
            "investment_analysis": "loop-level CapEx, annual net benefit, payback, 15-year ROI, and NPV",
            "dmc_analysis": "simulated IOFC screening separated from official USDA DMC margin",
        },
    },
}

def write_reports(output_dir: Path, ctx: SimulationContext) -> None:
    summary: dict[str, Any] = {
        "scenario_name": ctx.scenario.get("name", "unnamed"),
        "farm_system": ctx.scenario.get("farm_system", "conventional"),
        "farm_system_label": ctx.scenario.get("farm_system_label", "Conventional"),
        "farm_system_profile": ctx.state.get("farm_system_profile", {}),
        "daily_records": len(ctx.daily_records),
        "schedule_records": len(ctx.schedule_records),
        "monthly_records": len(ctx.monthly_records),
        "annual_records": len(ctx.annual_records),
        "report_contract": REPORT_CONTRACT,
        "output_files": [
            "summary.json",
            "calibration_inventory.json",
            "daily.csv",
            "schedule.csv",
            "monthly.csv",
            "annual.csv",
        ],
        "scenario_flags": {
            "enable_processor": bool(ctx.scenario.get("enable_processor", False)),
            "enable_whey_processing": bool(ctx.scenario.get("enable_whey_processing", False)),
            "enable_land_agent": bool(ctx.scenario.get("enable_land_agent", False)),
            "l1_nutrient_loop_enabled": bool(
                ctx.scenario.get(
                    "l1_nutrient_loop_enabled",
                    value(ctx.calibration, "manure.l1_nutrient_loop_enabled"),
                )
            ),
            "l2_water_loop_enabled": bool(
                ctx.scenario.get(
                    "l2_water_loop_enabled",
                    value(ctx.calibration, "water.l2_water_loop_enabled"),
                )
            ),
            "l3_energy_loop_enabled": bool(
                ctx.scenario.get(
                    "l3_energy_loop_enabled",
                    value(ctx.calibration, "energy.l3_energy_loop_enabled"),
                )
            ),
            "l4_byproduct_loop_enabled": bool(
                ctx.scenario.get(
                    "l4_byproduct_loop_enabled",
                    value(ctx.calibration, "dairy_processor.l4_byproduct_loop_enabled"),
                )
            ),
        },
        "policy": dict(ctx.state.get("policy", {})),
        "investment_analysis": ctx.state.get("investment_analysis", {}),
        "dmc_analysis": ctx.state.get("dmc_analysis", {}),
        "events": ctx.events.events,
        "latest_packets": {
            name: {
                "source": packet.source,
                "day": packet.day.isoformat(),
                "quality": packet.quality,
                "payload": packet.payload,
            }
            for name, packet in sorted(ctx.packets.items())
        },
    }
    write_json(output_dir / "summary.json", summary)
    write_json(output_dir / "calibration_inventory.json", calibration_inventory(ctx.calibration))
    write_csv(output_dir / "daily.csv", ctx.daily_records)
    write_csv(output_dir / "schedule.csv", ctx.schedule_records)
    write_csv(output_dir / "monthly.csv", ctx.monthly_records)
    write_csv(output_dir / "annual.csv", ctx.annual_records)
