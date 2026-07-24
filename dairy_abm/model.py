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
from dairy_abm.core import EventLog, SimulationClock, SimulationContext


class DairyFarmModel:
    """Top-level simulation shell."""

    def __init__(self, scenario: dict[str, Any], calibration: dict[str, Any]) -> None:
        seed = int(scenario.get("seed", 1))
        self.ctx = SimulationContext(
            scenario=scenario,
            calibration=calibration,
            rng=Random(seed),
            events=EventLog(),
        )
        self.genetics_agent = GeneticsAgent(self.ctx)
        self.agents: list[Any] = [
            MarketAgent(self.ctx),
            SensorsAgent(self.ctx),
            DiseaseAgent(self.ctx),
            *([LandManagementAgent(self.ctx)] if self._land_enabled() else []),
            CowAgent(self.ctx),
            FeedCropAgent(self.ctx),
            DairyProcessorAgent(self.ctx),
            ManureAgent(self.ctx),
            EnergyAgent(self.ctx),
            WaterAgent(self.ctx),
            EnvironmentAgent(self.ctx),
            FarmManagerAgent(self.ctx),
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

    def _run_daily(self, day: date) -> None:
        self.ctx.state["execution_order"] = []
        for agent in self.agents:
            agent.tick(day)
        self._record_schedule(day, "daily", [agent.name for agent in self.agents])

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
        self._record_schedule(day, "annual", [self.genetics_agent.name])

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
        self.ctx.daily_records.append(
            {
                "day": day.isoformat(),
                "agent_count": len(self.agents),
                "execution_order": ",".join(self.ctx.state["execution_order"]),
                "cow_count": cow_packet.payload["cow_count"] if cow_packet is not None else 0,
                "milk_l": cow_packet.payload["milk_l"] if cow_packet is not None else 0.0,
                "dmi_kg": cow_packet.payload["dmi_kg"] if cow_packet is not None else 0.0,
                "manure_kg": cow_packet.payload["manure_kg"] if cow_packet is not None else 0.0,
                "enteric_ch4_kg": cow_packet.payload["enteric_ch4_kg"] if cow_packet is not None else 0.0,
                "milk_revenue": cow_packet.payload["milk_revenue"] if cow_packet is not None else 0.0,
                "feed_cost": feed_packet.payload["feed_cost"] if feed_packet is not None else 0.0,
                "feed_loop_offset_kg": feed_packet.payload["feed_offset_kg"] if feed_packet is not None else 0.0,
                "water_loop_offset_l": feed_packet.payload["water_offset_l"] if feed_packet is not None else 0.0,
                "new_disease_cases": disease_packet.payload["new_cases"] if disease_packet is not None else 0,
                "active_disease_cases": disease_packet.payload["active_cases"] if disease_packet is not None else 0,
                "milk_price_per_l": market_packet.payload["milk_price_per_l"] if market_packet is not None else 0.0,
                "digester_kg": manure_packet.payload["digester_kg"] if manure_packet is not None else 0.0,
                "compost_kg": manure_packet.payload["compost_kg"] if manure_packet is not None else 0.0,
                "storage_kg": manure_packet.payload["storage_kg"] if manure_packet is not None else 0.0,
                "net_kwh": energy_packet.payload["net_kwh"] if energy_packet is not None else 0.0,
                "energy_value": energy_packet.payload["energy_value"] if energy_packet is not None else 0.0,
                "net_water_l": water_packet.payload["net_water_l"] if water_packet is not None else 0.0,
                "water_cost": water_packet.payload["water_cost"] if water_packet is not None else 0.0,
                "gross_kg_co2e": environment_packet.payload["gross_kg_co2e"] if environment_packet is not None else 0.0,
                "net_kg_co2e": environment_packet.payload["net_kg_co2e"] if environment_packet is not None else 0.0,
                "circularity_score": environment_packet.payload["circularity_score"] if environment_packet is not None else 0.0,
                "total_revenue": manager_packet.payload["total_revenue"] if manager_packet is not None else 0.0,
                "total_cost": manager_packet.payload["total_cost"] if manager_packet is not None else 0.0,
                "profit": manager_packet.payload["profit"] if manager_packet is not None else 0.0,
                "manager_recommendation": manager_packet.payload["recommendation"] if manager_packet is not None else "",
                "processor_enabled": processor_packet.payload["enabled"] if processor_packet is not None else False,
                "milk_processed_l": processor_packet.payload["milk_processed_l"] if processor_packet is not None else 0.0,
                "land_owner": self.ctx.state.get("land_owner", "feed_crop"),
            }
        )
