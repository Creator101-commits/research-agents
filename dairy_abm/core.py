from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from random import Random
from typing import Any
import csv
import json


class ConfigError(ValueError):
    """Raised when scenario or calibration values are outside allowed bounds."""


@dataclass(frozen=True)
class Packet:
    source: str
    name: str
    day: date
    payload: dict[str, Any]
    quality: str = "ok"
    period: str = "daily"
    confidence: str = "estimated"
    stream_id: str | None = None


@dataclass
class EventLog:
    events: list[dict[str, Any]] = field(default_factory=list)

    def add(self, day: date, source: str, level: str, message: str, **fields: Any) -> None:
        self.events.append(
            {
                "day": day.isoformat(),
                "source": source,
                "level": level,
                "message": message,
                **fields,
            }
        )


@dataclass
class SimulationContext:
    scenario: dict[str, Any]
    calibration: dict[str, Any]
    rng: Random
    events: EventLog
    packets: dict[str, Packet] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)
    daily_records: list[dict[str, Any]] = field(default_factory=list)
    schedule_records: list[dict[str, Any]] = field(default_factory=list)
    monthly_records: list[dict[str, Any]] = field(default_factory=list)
    annual_records: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.state.setdefault("loop_credits", {"feed_offset_kg": 0.0, "water_offset_l": 0.0})
        self.state.setdefault("nutrient_credits", {"recovered_water_n_kg": 0.0})
        self.state.setdefault(
            "policy",
            {
                "cofeed_safety_approved": False,
                "coproduct_feed_allowed": True,
                "dairy_processor_unit_enabled": False,
                "whey_processor_unit_enabled": False,
                "thermochemical_route_active": False,
            },
        )
        self.state.setdefault("policy_history", [])
        self.state.setdefault("agent_histories", {})
        self.state.setdefault("environment_ledger", {})

    def publish(self, packet: Packet) -> None:
        self.packets[packet.name] = packet

    def get_packet(self, name: str, default: Any = None) -> Packet | Any:
        return self.packets.get(name, default)

    def record_environment_stream(self, packet: Packet) -> None:
        stream_name = packet.stream_id or packet.name
        key = f"{packet.source}:{stream_name}:{packet.day.isoformat()}:{packet.period}"
        ledger = self.state["environment_ledger"]
        if key in ledger:
            raise ConfigError(f"duplicate environmental stream: {key}")
        ledger[key] = packet


@dataclass(frozen=True)
class SimulationClock:
    start: date
    days: int

    def dates(self) -> list[date]:
        return [self.start + timedelta(days=offset) for offset in range(self.days)]

    @staticmethod
    def is_week_end(day: date) -> bool:
        return day.weekday() == 6

    @staticmethod
    def is_month_end(day: date) -> bool:
        return (day + timedelta(days=1)).month != day.month

    @staticmethod
    def is_year_end(day: date) -> bool:
        return day.month == 12 and day.day == 31


class BaseAgent:
    name = "base"

    def __init__(self, ctx: SimulationContext) -> None:
        self.ctx = ctx

    def tick(self, day: date) -> None:
        return None

    def weekly(self, day: date) -> None:
        return None

    def monthly(self, day: date) -> None:
        return None

    def annual(self, day: date) -> None:
        return None


def require_nonnegative(name: str, value: float) -> float:
    if value < 0:
        raise ConfigError(f"{name} must be nonnegative, got {value}")
    return value


def require_fraction(name: str, value: float) -> float:
    if not 0 <= value <= 1:
        raise ConfigError(f"{name} must be between 0 and 1, got {value}")
    return value


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = sorted({field for row in rows for field in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
