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
        """Initialize market histories and load optional observed-price data."""
        super().__init__(ctx)
        ctx.state.setdefault("market_history", [])
        ctx.state.setdefault("market_price_history", [])
        ctx.state.setdefault("market_last_valid", {})
        self._observations = self._load_observations()

    def _load_observations(self) -> list[dict[str, Any]]:
        """Load and normalize the configured market observation CSV."""
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
        """Normalize one wide- or long-format market observation row."""
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
        """Parse an optional numeric market value and reject malformed input."""
        if raw is None or raw.strip().lower() in {"", "na", "n/a", "null"}:
            return None
        try:
            return float(raw)
        except ValueError as exc:
            raise ConfigError(f"invalid numeric market observation: {raw!r}") from exc

    @staticmethod
    def _parse_int(raw: str | None) -> int | None:
        """Parse an optional integer market year."""
        if raw is None or not raw.strip():
            return None
        try:
            return int(raw)
        except ValueError as exc:
            raise ConfigError(f"invalid market year: {raw!r}") from exc

    @staticmethod
    def _parse_month(raw: str | None) -> int | None:
        """Parse and validate a market month or period number."""
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
        """Select the most specific observation available for a simulation day."""
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
        """Return calibrated fallback market prices."""
        return {
            "milk_price_per_l": float(value(self.ctx.calibration, "market.milk_price_per_l")),
            "feed_cost_per_kg_dm": float(value(self.ctx.calibration, "market.feed_cost_per_kg_dm")),
            "cull_cow_price": float(value(self.ctx.calibration, "market.cull_cow_price")),
            "electricity_price_per_kwh": float(value(self.ctx.calibration, "energy.electricity_price_per_kwh")),
            "heat_value_per_kwh": float(value(self.ctx.calibration, "energy.heat_value_per_kwh")),
        }

    def _observed_prices(self, day: date) -> tuple[dict[str, float], str, str]:
        """Merge observed prices with static and last-valid fallbacks."""
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

    @staticmethod
    def _usda_component_prices(prices: dict[str, Any]) -> dict[str, float | None]:
        """USDA class and component formulas (dymclassprices.pdf) when commodity prices exist."""
        butter = prices.get("butter_price_usd_lb")
        nfdm = prices.get("wholesale_nonfat_dry_milk_price_usd_lb")
        dry_whey = prices.get("wholesale_whey_price_usd_lb")
        butterfat = (float(butter) - 0.2272) * 1.211 if isinstance(butter, (int, float)) and butter else None
        nonfat_solids = (float(nfdm) - 0.2393) * 0.99 if isinstance(nfdm, (int, float)) and nfdm else None
        other_solids = (float(dry_whey) - 0.2668) * 1.03 if isinstance(dry_whey, (int, float)) and dry_whey else None
        class_iii_skim = prices.get("class_iii_skim_price_usd_cwt")
        class_iv_skim = prices.get("class_iv_skim_price_usd_cwt")
        class_iii = (
            float(class_iii_skim) * 0.965 + butterfat * 3.5
            if isinstance(class_iii_skim, (int, float)) and butterfat is not None
            else None
        )
        class_iv = (
            float(class_iv_skim) * 0.965 + butterfat * 3.5
            if isinstance(class_iv_skim, (int, float)) and butterfat is not None
            else None
        )
        return {
            "butterfat_price_usd_lb": butterfat,
            "nonfat_solids_price_usd_lb": nonfat_solids,
            "other_solids_price_usd_lb": other_solids,
            "class_iii_price_usd_cwt": class_iii,
            "class_iv_price_usd_cwt": class_iv,
        }

    @staticmethod
    def _volatility_overlay(macro: dict[str, Any]) -> float | None:
        """Optional Dong-Du-Gould regime overlay; null unless every determinant is supplied."""
        keys = ("constant", "seasonality", "cheese_use_supply", "usdx_return", "corn_vol", "vix", "speculation")
        if not all(isinstance(macro.get(key), (int, float)) for key in keys):
            return None
        return (
            float(macro["constant"]) + float(macro["seasonality"]) + 0.54 * float(macro["cheese_use_supply"])
            + 0.62 * float(macro["usdx_return"]) + 0.18 * float(macro["corn_vol"]) + 0.11 * float(macro["vix"])
            + 0.027 * float(macro["speculation"])
        )

    def tick(self, day: date) -> None:
        """Publish daily market prices, component context, and volatility signals."""
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
        butterfat_fraction = max(0.0, float(self.ctx.scenario.get("milk_fat_fraction", value(self.ctx.calibration, "herd.milk_fat_fraction"))))
        protein_fraction = max(0.0, float(self.ctx.scenario.get("milk_protein_fraction", value(self.ctx.calibration, "herd.milk_protein_fraction"))))
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
        # Blueprint Market section 4 (Dong, Du & Gould 2011): within-month log returns,
        # RV_t = sum r^2 and mvol_t = Var(dlog P) over the first 20 trading days.
        month_key = day.strftime("%Y-%m")
        month_returns = self.ctx.state.setdefault("market_month_returns", {}).setdefault(month_key, [])
        if len(history) >= 2 and history[-2] > 0.0 and history[-1] > 0.0 and day.weekday() < 5:
            month_returns.append(log(history[-1] / history[-2]))
        realized_variance_month = sum(r * r for r in month_returns)
        first20 = month_returns[:20]
        mean20 = sum(first20) / len(first20) if first20 else 0.0
        mvol_month = (
            sum((r - mean20) ** 2 for r in first20) / (len(first20) - 1) if len(first20) >= 2 else None
        )
        base_price = self.ctx.state.setdefault("market_base_milk_price", prices["milk_price_per_l"])
        price_index = prices["milk_price_per_l"] / base_price if base_price else None
        price_change = (
            (prices["milk_price_per_l"] - prior_milk_price) / prior_milk_price
            if prior_milk_price and prior_milk_price > 0.0
            else None
        )
        usda_components = self._usda_component_prices(prices)
        macro = dict(self.ctx.scenario.get("market_macro_context", {}))
        mvol_hat = self._volatility_overlay(macro)
        carbon_credit_price = max(0.0, float(self.ctx.scenario.get("carbon_credit_price_per_tonne_co2e", 0.0)))
        payload = {
            **prices,
            "source": source,
            "market_mode": mode,
            "period_selection": selection,
            "market_packet_quality_flag": quality,
            "realized_volatility": realized_volatility,
            "price_index": price_index,
            "price_change_fraction": price_change,
            "realized_variance_month": realized_variance_month,
            "mvol_first_20_trading_days": mvol_month,
            "mvol_regression_overlay": mvol_hat,
            "usda_component_prices": usda_components,
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
