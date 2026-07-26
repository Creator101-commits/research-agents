from __future__ import annotations

from datetime import date
from random import Random
from typing import Any

from dairy_abm.agents.cow_agent import CowAgent
from dairy_abm.agents.dairy_processor_agent import DairyProcessorAgent
from dairy_abm.agents.disease_agent import DiseaseAgent
from dairy_abm.agents.energy_agent import EnergyAgent
from dairy_abm.agents.environment_agent import EnvironmentAgent
from dairy_abm.agents.farm_manager_agent import FarmManagerAgent
from dairy_abm.agents.feed_crop_agent import FeedCropAgent
from dairy_abm.agents.genetics_agent import GeneticsAgent
from dairy_abm.agents.land_agent import LandManagementAgent
from dairy_abm.agents.manure_agent import ManureAgent
from dairy_abm.agents.market_agent import MarketAgent
from dairy_abm.agents.sensors_agent import SensorsAgent
from dairy_abm.agents.water_agent import WaterAgent
from dairy_abm.config import validate_calibration, value
from dairy_abm.core import ConfigError, EventLog, SimulationClock, SimulationContext


class DairyFarmModel:
    """Top-level simulation shell."""

    def __init__(self, scenario: dict[str, Any], calibration: dict[str, Any]) -> None:
        validate_calibration(calibration)
        seed = int(scenario.get("seed", 1))
        self.ctx = SimulationContext(
            scenario=scenario,
            calibration=calibration,
            rng=Random(seed),
            events=EventLog(),
        )
        self._validate_scenario_dependencies()
        self._initialize_policy_state()
        self.genetics_agent = GeneticsAgent(self.ctx)
        self.market_agent = MarketAgent(self.ctx)
        self.sensors_agent = SensorsAgent(self.ctx)
        self.land_agent = LandManagementAgent(self.ctx) if self._land_enabled() else None
        self.feed_crop_agent = FeedCropAgent(self.ctx)
        self.farm_manager_agent = FarmManagerAgent(self.ctx)
        self.disease_agent = DiseaseAgent(self.ctx)
        self.water_agent = WaterAgent(self.ctx)
        self.cow_agent = CowAgent(self.ctx)
        self.processor_agent = DairyProcessorAgent(self.ctx)
        self.manure_agent = ManureAgent(self.ctx)
        self.energy_agent = EnergyAgent(self.ctx)
        self.environment_agent = EnvironmentAgent(self.ctx)
        self.agents: list[Any] = [
            self.market_agent,
            self.sensors_agent,
            *([self.land_agent] if self.land_agent is not None else []),
            self.feed_crop_agent,
            self.disease_agent,
            self.cow_agent,
            self.processor_agent,
            self.manure_agent,
            self.energy_agent,
            self.water_agent,
            self.environment_agent,
            self.farm_manager_agent,
        ]

    def run(self) -> SimulationContext:
        start = date.fromisoformat(self.ctx.scenario.get("start_date", "2026-01-01"))
        days = int(self.ctx.scenario.get("days", 1))
        clock = SimulationClock(start=start, days=days)
        for day in clock.dates():
            self._run_daily(day)
            self._record_daily(day)
            if SimulationClock.is_week_end(day):
                self._run_weekly(day)
            if SimulationClock.is_month_end(day):
                self._run_monthly(day)
            if SimulationClock.is_year_end(day):
                self._run_annual(day)
        return self.ctx

    def _land_enabled(self) -> bool:
        calibration_land = self.ctx.calibration.get("land", {}).get("enabled", {}).get("value", False)
        return bool(self.ctx.scenario.get("enable_land_agent", calibration_land))

    def _validate_scenario_dependencies(self) -> None:
        """Reject scenario overrides that cannot be represented by active agents."""
        processor_enabled = bool(
            self.ctx.scenario.get(
                "enable_processor",
                value(self.ctx.calibration, "dairy_processor.enabled"),
            )
        )
        whey_enabled = bool(
            self.ctx.scenario.get(
                "enable_whey_processing",
                value(self.ctx.calibration, "dairy_processor.whey_processing_enabled"),
            )
        )
        if whey_enabled and not processor_enabled:
            raise ConfigError("enable_whey_processing requires enable_processor")

        land_overrides = {"land_seasonal_availability", "land_grazing_enabled"}
        if land_overrides.intersection(self.ctx.scenario) and not self._land_enabled():
            raise ConfigError("land scenario overrides require enable_land_agent")

    def _initialize_policy_state(self) -> None:
        policy = self.ctx.state["policy"]
        policy.update(
            {
                "cofeed_safety_approved": bool(
                    self.ctx.scenario.get(
                        "cofeed_safety_approved",
                        value(self.ctx.calibration, "farm_manager.cofeed_safety_approved"),
                    )
                ),
                "coproduct_feed_allowed": bool(
                    self.ctx.scenario.get(
                        "coproduct_feed_allowed",
                        value(self.ctx.calibration, "farm_manager.coproduct_feed_allowed"),
                    )
                ),
                "dairy_processor_unit_enabled": bool(
                    self.ctx.scenario.get(
                        "enable_processor",
                        value(self.ctx.calibration, "dairy_processor.enabled"),
                    )
                ),
                "whey_processor_unit_enabled": bool(
                    self.ctx.scenario.get(
                        "enable_whey_processing",
                        value(self.ctx.calibration, "dairy_processor.whey_processing_enabled"),
                    )
                ),
                "thermochemical_route_active": bool(
                    self.ctx.scenario.get(
                        "thermochemical_route_active",
                        value(self.ctx.calibration, "farm_manager.thermochemical_route_active"),
                    )
                ),
                "milking_parlour_bulk_tank_active": bool(
                    self.ctx.scenario.get("milking_parlour_bulk_tank_active", True)
                ),
                "biosecurity_level_pct": float(
                    self.ctx.scenario.get(
                        "biosecurity_level_pct", self.ctx.scenario.get("biosecurity_level", 0.0)
                    )
                ),
                "vaccination_policy_active": bool(self.ctx.scenario.get("vaccination_policy_active", False)),
                "amino_acid_policy_active": bool(
                    self.ctx.scenario.get(
                        "amino_acid_policy_active",
                        value(self.ctx.calibration, "water.amino_acid_policy_active_default"),
                    )
                ),
                "catch_crop_active": bool(self.ctx.scenario.get("catch_crop_active", False)),
                "feed_mode": str(self.ctx.scenario.get("feed_mode", "balanced")),
                "market_scenario": str(self.ctx.scenario.get("market_scenario", "NM")).upper(),
                "user_breeding_priority": str(self.ctx.scenario.get("user_breeding_priority", "profit")),
                "manure_route_policy": dict(self.ctx.scenario.get("manure_route_policy", {})),
                "digester_capacity_kg_day": self.ctx.scenario.get("digester_capacity_kg_day"),
                "energy_conversion_mode": str(self.ctx.scenario.get("energy_conversion_mode", "chp")),
                "solar_capacity_kw": float(self.ctx.scenario.get("solar_capacity_kw", 0.0)),
                "sdg_reporting_mode": bool(self.ctx.scenario.get("sdg_reporting_mode", False)),
            }
        )

    def _run_daily(self, day: date) -> None:
        self.ctx.state["execution_order"] = []
        # The blueprint requires a pre-production phase: rations must be ready
        # before Cow production, and management policy must reach Disease first.
        self.market_agent.tick(day)
        self.sensors_agent.tick(day)
        if self.land_agent is not None:
            self.land_agent.tick(day)
        self.feed_crop_agent.tick(day)
        self.farm_manager_agent.dispatch_policy(day)
        self.disease_agent.tick(day)
        self.water_agent.prepare_delivery(day)
        self.cow_agent.tick(day)
        self.processor_agent.tick(day)
        self.manure_agent.tick(day)
        self.energy_agent.tick(day)
        self.water_agent.tick(day)
        self.environment_agent.tick(day)
        self.farm_manager_agent.tick(day)
        self.genetics_agent.record_daily_intake(day)
        self._record_schedule(day, "daily", list(self.ctx.state["execution_order"]))

    def _run_weekly(self, day: date) -> None:
        for agent in self.agents:
            agent.weekly(day)
        self._record_schedule(day, "weekly", [agent.name for agent in self.agents])

    def _run_monthly(self, day: date) -> None:
        for agent in self.agents:
            agent.monthly(day)
        self._record_schedule(day, "monthly", [agent.name for agent in self.agents])

    def _run_annual(self, day: date) -> None:
        self.genetics_agent.annual(day)
        self.farm_manager_agent.annual(day)
        self._record_schedule(day, "annual", [self.genetics_agent.name, self.farm_manager_agent.name])

    def _record_schedule(self, day: date, phase: str, agents: list[str]) -> None:
        self.ctx.schedule_records.append(
            {
                "day": day.isoformat(),
                "phase": phase,
                "agents": ",".join(agents),
            }
        )

    def _record_daily(self, day: date) -> None:
        cow_packet = self.ctx.get_packet("cow_daily_packet")
        feed_packet = self.ctx.get_packet("feed_crop_packet")
        disease_packet = self.ctx.get_packet("disease_state_packet")
        market_packet = self.ctx.get_packet("market_price_packet")
        manure_packet = self.ctx.get_packet("manure_packet")
        energy_packet = self.ctx.get_packet("energy_packet")
        water_packet = self.ctx.get_packet("water_packet")
        environment_packet = self.ctx.get_packet("environment_packet")
        manager_packet = self.ctx.get_packet("manager_packet")
        processor_packet = self.ctx.get_packet("processor_packet")
        report_confidence = self._report_confidence(
            {
                "cow": cow_packet,
                "disease": disease_packet,
                "energy": energy_packet,
                "environment": environment_packet,
                "feed_crop": feed_packet,
                "farm_manager": manager_packet,
                "manure": manure_packet,
                "market": market_packet,
                "processor": processor_packet,
                "water": water_packet,
            }
        )
        self.ctx.daily_records.append(
            {
                "day": day.isoformat(),
                "report_confidence": report_confidence,
                "agent_count": len(self.agents),
                "execution_order": ",".join(self.ctx.state["execution_order"]),
                "cow_count": cow_packet.payload["cow_count"] if cow_packet is not None else 0,
                "milk_l": cow_packet.payload["milk_l"] if cow_packet is not None else 0.0,
                "dmi_kg": cow_packet.payload["dmi_kg"] if cow_packet is not None else 0.0,
                "cow_ration_coverage_fraction": cow_packet.payload["ration_coverage_fraction"] if cow_packet is not None else 1.0,
                "manure_kg": cow_packet.payload["manure_kg"] if cow_packet is not None else 0.0,
                "enteric_ch4_kg": cow_packet.payload["enteric_ch4_kg"] if cow_packet is not None else 0.0,
                "milk_protein_nitrogen_kg": cow_packet.payload["milk_protein_nitrogen_kg"] if cow_packet is not None else 0.0,
                "nitrogen_use_efficiency": cow_packet.payload["nitrogen_use_efficiency"] if cow_packet is not None else None,
                "milk_revenue": cow_packet.payload["milk_revenue"] if cow_packet is not None else 0.0,
                "feed_cost": feed_packet.payload["feed_cost"] if feed_packet is not None else 0.0,
                "purchased_feed_kg_dm": feed_packet.payload["purchased_feed_kg_dm"] if feed_packet is not None else 0.0,
                "irrigation_l": feed_packet.payload["irrigation_l"] if feed_packet is not None else 0.0,
                "ration_crude_protein_kg": feed_packet.payload["ration_crude_protein_kg"] if feed_packet is not None else 0.0,
                "ration_metabolizable_protein_kg": feed_packet.payload["ration_metabolizable_protein_kg"] if feed_packet is not None else 0.0,
                "ration_nitrogen_kg": feed_packet.payload["ration_nitrogen_kg"] if feed_packet is not None else 0.0,
                "feed_loop_offset_kg": feed_packet.payload["feed_offset_kg"] if feed_packet is not None else 0.0,
                "water_loop_offset_l": feed_packet.payload["water_offset_l"] if feed_packet is not None else 0.0,
                "new_disease_cases": disease_packet.payload["new_cases"] if disease_packet is not None else 0,
                "active_disease_cases": disease_packet.payload["active_cases"] if disease_packet is not None else 0,
                "disease_economic_cost": disease_packet.payload.get("outbreak_economic_cost", 0.0) if disease_packet is not None else 0.0,
                "days_to_herd_immunity": disease_packet.payload.get("days_to_herd_immunity") if disease_packet is not None else None,
                "milk_price_per_l": market_packet.payload["milk_price_per_l"] if market_packet is not None else 0.0,
                "digester_kg": manure_packet.payload["digester_kg"] if manure_packet is not None else 0.0,
                "compost_kg": manure_packet.payload["compost_kg"] if manure_packet is not None else 0.0,
                "storage_kg": manure_packet.payload["storage_kg"] if manure_packet is not None else 0.0,
                "net_kwh": energy_packet.payload["net_kwh"] if energy_packet is not None else 0.0,
                "energy_value": energy_packet.payload["energy_value"] if energy_packet is not None else 0.0,
                "biogas_volume_m3": energy_packet.payload.get("biogas_volume_m3", 0.0) if energy_packet is not None else 0.0,
                "biogas_gross_kwh": energy_packet.payload.get("biogas_gross_kwh", 0.0) if energy_packet is not None else 0.0,
                "heat_generated_mj": energy_packet.payload.get("heat_generated_mj") if energy_packet is not None else None,
                "energy_self_sufficiency_pct": energy_packet.payload.get("energy_self_sufficiency_pct") if energy_packet is not None else None,
                "carbon_credits_earned": energy_packet.payload.get("carbon_credits_earned", 0.0) if energy_packet is not None else 0.0,
                "net_water_l": water_packet.payload["net_water_l"] if water_packet is not None else 0.0,
                "water_cost": water_packet.payload["water_cost"] if water_packet is not None else 0.0,
                "freshwater_withdrawal_l": water_packet.payload.get("freshwater_withdrawal_l", 0.0) if water_packet is not None else 0.0,
                "recycled_irrigation_l": water_packet.payload.get("recycled_irrigation_l", 0.0) if water_packet is not None else 0.0,
                "recycled_irrigation_fraction": water_packet.payload.get("recycled_irrigation_fraction", 0.0) if water_packet is not None else 0.0,
                "gross_kg_co2e": environment_packet.payload["gross_kg_co2e"] if environment_packet is not None else 0.0,
                "avoided_kg_co2e": environment_packet.payload["avoided_kg_co2e"] if environment_packet is not None else 0.0,
                "net_kg_co2e": environment_packet.payload["net_kg_co2e"] if environment_packet is not None else 0.0,
                "energy_offset_kg_co2e": environment_packet.payload["energy_offset_kg_co2e"] if environment_packet is not None else 0.0,
                "fertilizer_offset_kg_co2e": environment_packet.payload["fertilizer_offset_kg_co2e"] if environment_packet is not None else 0.0,
                "kg_co2e_per_l_milk": environment_packet.payload["kg_co2e_per_l_milk"] if environment_packet is not None else None,
                "kg_co2e_per_kg_milk_protein": environment_packet.payload["kg_co2e_per_kg_milk_protein"] if environment_packet is not None else None,
                "circularity_score": environment_packet.payload["circularity_score"] if environment_packet is not None else 0.0,
                "input_circularity": environment_packet.payload.get("ICirc", 0.0) if environment_packet is not None else 0.0,
                "output_circularity": environment_packet.payload.get("OCirc", 0.0) if environment_packet is not None else 0.0,
                "environment_nue": environment_packet.payload.get("NUE") if environment_packet is not None else None,
                "material_use_count": environment_packet.payload.get("use_count", 0) if environment_packet is not None else 0,
                "material_cycle_count": environment_packet.payload.get("cycle_count", 0) if environment_packet is not None else 0,
                "soil_carbon_delta_kg": environment_packet.payload.get("soil_carbon_delta_kg", 0.0) if environment_packet is not None else 0.0,
                "synthetic_fertilizer_saved_kg": environment_packet.payload.get("synthetic_fertilizer_saved_kg", 0.0) if environment_packet is not None else 0.0,
                "sustainability_score_0_100": environment_packet.payload.get("sustainability_score_0_100", 0.0) if environment_packet is not None else 0.0,
                "total_revenue": manager_packet.payload["total_revenue"] if manager_packet is not None else 0.0,
                "total_cost": manager_packet.payload["total_cost"] if manager_packet is not None else 0.0,
                "profit": manager_packet.payload["profit"] if manager_packet is not None else 0.0,
                "manager_recommendation": manager_packet.payload["recommendation"] if manager_packet is not None else "",
                "policy_conflict_count": len(manager_packet.payload.get("policy_conflicts", [])) if manager_packet is not None else 0,
                "automatic_policy_action_count": len(manager_packet.payload.get("automatic_policy_actions", [])) if manager_packet is not None else 0,
                "processor_enabled": processor_packet.payload["enabled"] if processor_packet is not None else False,
                "milk_processed_l": processor_packet.payload["milk_processed_l"] if processor_packet is not None else 0.0,
                "processor_revenue": processor_packet.payload["processor_revenue"] if processor_packet is not None else 0.0,
                "processing_energy_kwh": processor_packet.payload["processing_energy_kwh"] if processor_packet is not None else 0.0,
                "whey_l": processor_packet.payload.get("whey_l", 0.0) if processor_packet is not None else 0.0,
                "scotta_l": processor_packet.payload.get("scotta_l", 0.0) if processor_packet is not None else 0.0,
                "processor_residual_energy_kg": processor_packet.payload.get("residual_energy_kg", 0.0) if processor_packet is not None else 0.0,
                "cooling_cost": manager_packet.payload["cooling_cost"] if manager_packet is not None else 0.0,
                "processing_energy_cost": manager_packet.payload["processing_energy_cost"] if manager_packet is not None else 0.0,
                "cash_balance": manager_packet.payload["cash_balance"] if manager_packet is not None else 0.0,
                "roi_circular_investment": manager_packet.payload["roi_circular_investment"] if manager_packet is not None else None,
                "payback_period_years": manager_packet.payload["payback_period_years"] if manager_packet is not None else None,
                "land_owner": self.ctx.state.get("land_owner", "feed_crop"),
            }
        )

    @staticmethod
    def _report_confidence(packets: dict[str, Any]) -> str:
        """Preserve source packet quality and confidence in a CSV-safe field."""
        return "|".join(
            f"{source}:{packet.quality}/{packet.confidence}" if packet is not None else f"{source}:missing"
            for source, packet in packets.items()
        )
