from __future__ import annotations

import csv
from datetime import date
from math import log, sqrt
from pathlib import Path
from statistics import pstdev
from typing import Any

from dairy_abm.config import value
from dairy_abm.core import BaseAgent, ConfigError, Packet, require_nonnegative


class MarketAgent(BaseAgent):
    name = "market"

    _STATIC_FIELDS = (
        "milk_price_per_l",
        "feed_cost_per_kg_dm",
        "cull_cow_price",
        "electricity_price_per_kwh",
        "heat_value_per_kwh",
    )
    _LONG_FORMAT_ALIASES = {
        "all milk price": "all_milk_price_usd_cwt",
        "class iii price": "class_iii_price_usd_cwt",
        "class iv price": "class_iv_price_usd_cwt",
        "butter price": "butter_price_usd_lb",
        "cheddar blocks price": "wholesale_cheddar_price_usd_lb",
        "cheddar barrels price": "cheddar_barrels_price_usd_lb",
        "dry whey price": "wholesale_whey_price_usd_lb",
        "nonfat dry milk price": "wholesale_nonfat_dry_milk_price_usd_lb",
    }

    def __init__(self, ctx) -> None:
        super().__init__(ctx)
        ctx.state.setdefault("market_history", [])
        ctx.state.setdefault("market_price_history", [])
        ctx.state.setdefault("market_last_valid", {})
        self._observations = self._load_observations()

    def _load_observations(self) -> list[dict[str, Any]]:
        configured_path = self.ctx.scenario.get("market_data_csv")
        if not configured_path:
            return []
        path = Path(str(configured_path))
        if not path.is_file():
            raise ConfigError(f"market_data_csv does not exist: {path}")
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise ConfigError("market_data_csv requires a header row")
            rows = [self._normalize_row(row) for row in reader]
        return [row for row in rows if row]

    def _normalize_row(self, raw: dict[str, str | None]) -> dict[str, Any]:
        row = {str(key).strip().lower(): (value or "").strip() for key, value in raw.items() if key}
        normalized: dict[str, Any] = {
            "date": row.get("date"),
            "year": self._parse_int(row.get("year")),
            "month": self._parse_month(row.get("month") or row.get("period")),
            "frequency": row.get("frequency", "").lower(),
        }
        if "data_item" in row and "value" in row:
            item = row["data_item"].lower()
            field = self._LONG_FORMAT_ALIASES.get(item, item.replace(" ", "_").replace("-", "_"))
            normalized[field] = self._parse_number(row["value"])
            if row.get("unit"):
                normalized[f"{field}_unit"] = row["unit"]
            return normalized
        for field, raw_value in row.items():
            if field not in {"date", "year", "month", "period", "frequency"}:
                normalized[field] = self._parse_number(raw_value)
        return normalized

    @staticmethod
    def _parse_number(raw: str | None) -> float | None:
        if raw is None or raw.strip().lower() in {"", "na", "n/a", "null"}:
            return None
        try:
            return float(raw)
        except ValueError as exc:
            raise ConfigError(f"invalid numeric market observation: {raw!r}") from exc

    @staticmethod
    def _parse_int(raw: str | None) -> int | None:
        if raw is None or not raw.strip():
            return None
        try:
            return int(raw)
        except ValueError as exc:
            raise ConfigError(f"invalid market year: {raw!r}") from exc

    @staticmethod
    def _parse_month(raw: str | None) -> int | None:
        if raw is None or not raw.strip():
            return None
        try:
            month = int(raw)
        except ValueError as exc:
            raise ConfigError(f"invalid market month/period: {raw!r}") from exc
        if not 1 <= month <= 12:
            raise ConfigError(f"market month/period must be 1..12, got {month}")
        return month

    def _select_observation(self, day: date) -> tuple[dict[str, Any] | None, str]:
        day_text = day.isoformat()
        for row in self._observations:
            if row.get("date") == day_text:
                return row, "daily"
        for row in self._observations:
            if row.get("year") == day.year and row.get("month") == day.month:
                return row, "monthly"
        for row in self._observations:
            if row.get("year") == day.year and row.get("frequency") in {"annual", "yearly"}:
                return row, "annual_fallback"
        return None, "no_observation"

    def _static_prices(self) -> dict[str, float]:
        return {
            "milk_price_per_l": float(value(self.ctx.calibration, "market.milk_price_per_l")),
            "feed_cost_per_kg_dm": float(value(self.ctx.calibration, "market.feed_cost_per_kg_dm")),
            "cull_cow_price": float(value(self.ctx.calibration, "market.cull_cow_price")),
            "electricity_price_per_kwh": float(value(self.ctx.calibration, "energy.electricity_price_per_kwh")),
            "heat_value_per_kwh": float(value(self.ctx.calibration, "energy.heat_value_per_kwh")),
        }

    def _observed_prices(self, day: date) -> tuple[dict[str, float], str, str]:
        row, selection = self._select_observation(day)
        prices = self._static_prices()
        last_valid: dict[str, float] = self.ctx.state["market_last_valid"]
        quality = "ok"
        if row is None:
            if last_valid:
                prices.update(last_valid)
                quality = "low_confidence"
                self.ctx.events.add(day, self.name, "warning", "market observation missing; carried forward")
                return prices, quality, selection
            self.ctx.events.add(day, self.name, "warning", "market observation missing; using static fallback")
            return prices, "low_confidence", selection

        fields = set(self._STATIC_FIELDS) | {
            key for key, raw_value in row.items() if isinstance(raw_value, (float, int)) or raw_value is None
        }
        fields -= {"year", "month"}
        for field in fields:
            observed = row.get(field)
            if observed is None:
                if field in last_valid:
                    prices[field] = last_valid[field]
                    quality = "low_confidence"
                elif field not in prices:
                    quality = "low_confidence"
                continue
            observed_value = float(observed)
            if observed_value < 0.0:
                observed_value = 0.0
                quality = "low_confidence"
                self.ctx.events.add(
                    day,
                    self.name,
                    "warning",
                    "negative observed market price was clamped",
                    field=field,
                )
            prices[field] = observed_value
            last_valid[field] = observed_value
        if quality == "low_confidence":
            self.ctx.events.add(day, self.name, "warning", "market observation contains missing values")
        return prices, quality, selection

    def tick(self, day: date) -> None:
        mode = str(self.ctx.scenario.get("market_mode", "static"))
        if mode not in {"static", "observed", "observed_plus_shock"}:
            raise ConfigError(f"market_mode must be static, observed, or observed_plus_shock, got {mode!r}")
        if mode == "static":
            prices = self._static_prices()
            quality = "ok"
            source = "static_config"
            selection = "static"
        else:
            prices, quality, selection = self._observed_prices(day)
            source = "observed_csv"

        if mode in {"static", "observed_plus_shock"}:
            shock_stddev = float(value(self.ctx.calibration, "market.price_shock_stddev_fraction"))
            shock = self.ctx.rng.gauss(0.0, shock_stddev) if shock_stddev else 0.0
            for field in ("milk_price_per_l", "feed_cost_per_kg_dm"):
                prices[field] *= 1.0 + shock

        for field, price in list(prices.items()):
            prices[field] = require_nonnegative(field, float(price))
        prior_prices: list[float] = self.ctx.state["market_price_history"]
        prior_milk_price = prior_prices[-1] if prior_prices else None
        realized_volatility = (
            abs(prices["milk_price_per_l"] - prior_milk_price) / prior_milk_price
            if prior_milk_price and prior_milk_price > 0.0
            else 0.0
        )
        self.ctx.state["market_price_history"].append(prices["milk_price_per_l"])
        density = max(0.1, float(self.ctx.scenario.get("milk_density_kg_per_l", 1.03)))
        cwt_to_l = 45.359237 / density
        class_prices = {
            label: float(prices.get(field, 0.0))
            for label, field in {"II": "class_ii_price_usd_cwt", "III": "class_iii_price_usd_cwt", "IV": "class_iv_price_usd_cwt"}.items()
        }
        class_prices_per_l = {label: amount / cwt_to_l for label, amount in class_prices.items() if amount > 0.0}
        component_price_per_l = 0.0
        if class_prices_per_l:
            component_price_per_l = sum(class_prices_per_l.values()) / len(class_prices_per_l)
        butterfat_fraction = max(0.0, float(self.ctx.scenario.get("milk_fat_fraction", 0.039)))
        protein_fraction = max(0.0, float(self.ctx.scenario.get("milk_protein_fraction", 0.032)))
        other_solids_fraction = max(0.0, float(self.ctx.scenario.get("milk_other_solids_fraction", 0.057)))
        lb_per_kg = 2.20462262
        component_wholesale_price_per_l = (
            density
            * lb_per_kg
            * (
                butterfat_fraction * float(prices.get("butter_price_usd_lb", 0.0))
                + protein_fraction * float(prices.get("wholesale_cheddar_price_usd_lb", 0.0))
                + other_solids_fraction * float(prices.get("wholesale_nonfat_dry_milk_price_usd_lb", 0.0))
            )
        )
        if bool(self.ctx.scenario.get("use_usda_component_pricing", False)):
            prices["milk_price_per_l"] = component_price_per_l or component_wholesale_price_per_l or prices["milk_price_per_l"]
        history = self.ctx.state["market_price_history"]
        returns = [log(history[index] / history[index - 1]) for index in range(1, len(history)) if history[index - 1] > 0.0 and history[index] > 0.0]
        dong_du_gould_volatility = pstdev(returns[-20:]) * sqrt(252.0) if len(returns) >= 2 else 0.0
        carbon_credit_price = max(0.0, float(self.ctx.scenario.get("carbon_credit_price_per_tonne_co2e", 0.0)))
        payload = {
            **prices,
            "source": source,
            "market_mode": mode,
            "period_selection": selection,
            "market_packet_quality_flag": quality,
            "realized_volatility": realized_volatility,
            "dong_du_gould_volatility_20d": dong_du_gould_volatility,
            "usda_class_prices_usd_cwt": class_prices,
            "usda_class_prices_per_l": class_prices_per_l,
            "component_implied_milk_price_per_l": component_price_per_l or None,
            "component_wholesale_milk_price_per_l": component_wholesale_price_per_l or None,
            "component_pricing_inputs": {
                "butterfat_fraction": butterfat_fraction,
                "protein_fraction": protein_fraction,
                "other_solids_fraction": other_solids_fraction,
            },
            "milk_density_kg_per_l": density,
            "carbon_credit_price_per_tonne_co2e": carbon_credit_price,
            "macro_context": dict(self.ctx.scenario.get("market_macro_context", {})),
            "market_regime_label": "volatile" if realized_volatility > 0.0 else "stable",
        }
        self.ctx.state["market_history"].append({"day": day.isoformat(), **payload})
        self.ctx.publish(
            Packet(
                source=self.name,
                name="market_price_packet",
                day=day,
                quality="static_config" if source == "static_config" else quality,
                payload=payload,
                confidence="observed" if source == "observed_csv" else "scenario",
            )
        )
        self.ctx.state.setdefault("execution_order", []).append(self.name)
