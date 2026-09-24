from __future__ import annotations

from datetime import date

from dairy_abm.analysis.cdairy_economics import CdairyPrices, loop_feed_saving
from dairy_abm.config import value
from dairy_abm.core import BaseAgent, Packet, require_nonnegative


class FarmManagerAgent(BaseAgent):
    name = "farm_manager"
    _OBJECTIVES = ("profit", "environment", "animal_welfare", "circularity")

    def __init__(self, ctx) -> None:
        """Initialize objective weights and manager history state."""
        super().__init__(ctx)
        self.prices = CdairyPrices.from_calibration(ctx.calibration)
        ctx.state.setdefault(
            "objective_weights",
            {
                obj: float(value(ctx.calibration, f"farm_manager.objective_weight_{obj}"))
                for obj in self._OBJECTIVES
            },
        )

    def dispatch_policy(self, day: date) -> None:
        """Apply user/event policy before biological agents run for the day."""
        policy = self.ctx.state["policy"]
        updates = self.ctx.scenario.get("policy_updates", {})
        dated_updates = updates.get(day.isoformat(), updates.get("default", {})) if isinstance(updates, dict) else {}
        if isinstance(dated_updates, dict):
            for key, policy_value in dated_updates.items():
                if key in policy:
                    policy[key] = policy_value

        disease = self.ctx.get_packet("disease_state_packet")
        environment = self.ctx.get_packet("environment_packet")
        feed = self.ctx.get_packet("feed_crop_packet")
        energy = self.ctx.get_packet("energy_packet")
        automatic_actions: list[dict[str, str]] = []
        active_cases = int(disease.payload.get("active_cases", 0)) if disease is not None else 0
        if active_cases > 0 and bool(self.ctx.scenario.get("auto_biosecurity_response", True)):
            policy["biosecurity_level_pct"] = max(float(policy.get("biosecurity_level_pct", 0.0)), 0.75)
            policy["vaccination_policy_active"] = True
            automatic_actions.append(
                {"policy": "biosecurity_level_pct", "reason": "active_disease_cases"}
            )
        net_emissions = float(environment.payload.get("net_kg_co2e", 0.0)) if environment else 0.0
        emissions_trigger = float(self.ctx.scenario.get("auto_emissions_trigger_kg_co2e", 1000.0))
        if net_emissions > emissions_trigger and bool(self.ctx.scenario.get("auto_environment_response", True)):
            policy["catch_crop_active"] = True
            policy["manure_route_policy"] = {"digester": 1.0, "compost": 0.0, "storage": 0.0}
            automatic_actions.append(
                {"policy": "catch_crop_active", "reason": "net_emissions_above_trigger"}
            )
        feed_cost = float(feed.payload.get("feed_cost", 0.0)) if feed else 0.0
        feed_cost_trigger = float(self.ctx.scenario.get("auto_feed_cost_trigger", 500.0))
        if feed_cost > feed_cost_trigger and bool(self.ctx.scenario.get("auto_feed_response", True)):
            policy["amino_acid_policy_active"] = True
            policy["feed_mode"] = "precision"
            automatic_actions.append(
                {"policy": "feed_mode", "reason": "feed_cost_above_trigger"}
            )
        self_sufficiency = float(energy.payload.get("energy_self_sufficiency_pct", 100.0)) if energy else 100.0
        if self_sufficiency < float(self.ctx.scenario.get("auto_energy_sufficiency_trigger_pct", 30.0)) and bool(
            self.ctx.scenario.get("auto_energy_response", True)
        ):
            policy["energy_conversion_mode"] = "chp"
            automatic_actions.append(
                {"policy": "energy_conversion_mode", "reason": "low_energy_self_sufficiency"}
            )
        policy["market_scenario"] = str(policy.get("market_scenario", "NM")).upper()
        self.ctx.state["last_automatic_policy_actions"] = automatic_actions
        self.ctx.state["policy_history"].append(
            {"day": day.isoformat(), "automatic_actions": automatic_actions, **policy}
        )
        self.ctx.publish(
            Packet(
                source=self.name,
                name="manager_policy_packet",
                day=day,
                payload=dict(policy),
                confidence="scenario",
            )
        )
        self.ctx.state.setdefault("execution_order", []).append("farm_manager_policy")

    def tick(self, day: date) -> None:
        """Calculate daily farm economics, objective scores, and management recommendations."""
        cow = self.ctx.get_packet("cow_daily_packet")
        feed = self.ctx.get_packet("feed_crop_packet")
        water = self.ctx.get_packet("water_packet")
        energy = self.ctx.get_packet("energy_packet")
        market = self.ctx.get_packet("market_price_packet")
        processor = self.ctx.get_packet("processor_packet")
        disease = self.ctx.get_packet("disease_state_packet")
        environment = self.ctx.get_packet("environment_packet")
        sensors = self.ctx.get_packet("sensor_observation_packet")
        cow_count = int(cow.payload["cow_count"]) if cow is not None else 0
        raw_milk_revenue = float(cow.payload["milk_revenue"]) if cow is not None else 0.0
        processor_enabled = bool(processor.payload["enabled"]) if processor is not None else False
        # Farm revenue always uses the workbook's milk component sales; processor
        # product sales are reported separately and kept out of profit because
        # the model carries no product-side costs (fix_prompt 2.3).
        milk_revenue = raw_milk_revenue
        purchased_feed_cost = float(feed.payload["feed_cost"]) if feed is not None else 0.0
        water_cost = float(water.payload["water_cost"]) if water is not None else 0.0
        energy_value = float(energy.payload["energy_value"]) if energy is not None else 0.0
        electricity_price = (
            float(market.payload["electricity_price_per_kwh"])
            if market is not None
            else float(value(self.ctx.calibration, "energy.electricity_price_per_kwh"))
        )
        milk_l = float(cow.payload["milk_l"]) if cow is not None else 0.0
        cooling_cost = milk_l * float(
            value(self.ctx.calibration, "dairy_processor.milk_cooling_kwh_per_l_milk")
        ) * electricity_price
        processing_energy_cost = (
            float(processor.payload["processing_energy_kwh"]) * electricity_price
            if processor is not None and processor_enabled
            else 0.0
        )
        treatment_cost = float(disease.payload["treatment_cost"]) if disease is not None else 0.0
        # Lost milk is already missing from milk sales, so it is not charged again.
        disease_cost = (
            max(0.0, float(disease.payload.get("outbreak_economic_cost", treatment_cost))
                - float(disease.payload.get("milk_loss_cost", 0.0)))
            if disease is not None
            else 0.0
        )
        sensor_alert_count = (
            len(sensors.payload.get("filtered_alerts", [])) if sensors is not None else 0
        )
        carbon_credit_value = float(environment.payload.get("carbon_credit_value", 0.0)) if environment is not None else 0.0
        processor_revenue = float(processor.payload["processor_revenue"]) if processor is not None and processor_enabled else 0.0
        byproduct_revenue = (
            float(processor.payload.get("byproduct_revenue", 0.0)) if processor is not None and processor_enabled else 0.0
        )
        # Herd economics use the Cdairy workbook's revenue and cost rows
        # (Excel precedence); circular-loop items are added on top.
        herd = dict(cow.payload.get("workbook_daily_economics", {})) if cow is not None else {}
        get = lambda key: float(herd.get(key, 0.0))  # noqa: E731
        adjustment = float(value(self.ctx.calibration, "cdairy_economics.profit_deviation_adjustment"))
        cow_sales = get("cow_sales") + get("other_heifer_sales") * adjustment
        calf_sales = get("bull_calf_sales") + (get("female_calf_sales") + get("extra_embryo_sales")) * adjustment
        profit_deviation = (get("profit_deviation_cows") + get("profit_deviation_heifers")) * adjustment
        breeding_cost = get("embryo_donor_cost") + get("breeding_cost_cows") + get("breeding_cost_heifers")
        reproduction_cost = (
            get("heat_detection_cost_cows") + get("heat_detection_cost_heifers") + get("pregnancy_diagnosis_cost")
            + get("presynch_cost_cows") + get("presynch_cost_heifers") + get("firstsynch_cost_heifers")
            + get("resynch_cost_heifers")
        )
        other_variable_cost = get("open_pregnant_wet_cost") + get("milking_dry_cost")
        # Workbook rows 28-29 charge all intake, home-grown included; circular
        # feed offsets (L1 nutrient, L4 by-product) are valued at the same prices.
        workbook_feed_cost = get("wet_feed_cost") + get("dry_feed_cost")
        loop_feed_offset_kg = (
            float(feed.payload.get("l1_feed_offset_kg", 0.0)) + float(feed.payload.get("l4_feed_offset_kg", 0.0))
            if feed is not None
            else 0.0
        )
        dmi_wet = float(cow.payload.get("dmi_lactating_kg", 0.0)) if cow is not None else 0.0
        dmi_dry = float(cow.payload.get("dmi_dry_kg", 0.0)) if cow is not None else 0.0
        loop_feed_saving_value = loop_feed_saving(dmi_wet, dmi_dry, loop_feed_offset_kg, self.prices)
        feed_cost = max(0.0, workbook_feed_cost - loop_feed_saving_value)
        heifer_cost = get("heifer_raised_cost") + get("heifer_purchased_cost") + get("genomic_testing_cost")
        mastitis_cost = get("mastitis_treatment_cost")
        dry_cow_therapy_cost = get("dry_cow_therapy_cost")
        fixed_cost = get("fixed_costs")
        herd_revenue = milk_revenue + cow_sales + calf_sales + profit_deviation
        herd_cost = (
            workbook_feed_cost + breeding_cost + reproduction_cost + other_variable_cost + heifer_cost
            + mastitis_cost + dry_cow_therapy_cost + fixed_cost
        )
        manure_packet = self.ctx.get_packet("manure_packet")
        compost_revenue = (
            float(manure_packet.payload.get("compost_product_kg", 0.0))
            * float(value(self.ctx.calibration, "manure.compost_value_per_kg"))
            if manure_packet is not None
            else 0.0
        )
        heat_value = float(energy.payload.get("heat_value", 0.0)) if energy is not None else 0.0
        electricity_value = energy_value - heat_value
        # Circular-loop layer, listed line by line on top of the workbook herd economics.
        loop_lines = {
            "electricity_value": electricity_value,
            "heat_value": heat_value,
            "carbon_credit_value": carbon_credit_value,
            "compost_revenue": compost_revenue,
            "byproduct_revenue": byproduct_revenue,
            "loop_feed_saving": loop_feed_saving_value,
            "water_cost": -water_cost,
            "cooling_cost": -cooling_cost,
            "processing_energy_cost": -processing_energy_cost,
            "disease_cost": -disease_cost,
        }
        loop_revenue = byproduct_revenue + energy_value + carbon_credit_value + compost_revenue
        loop_cost = water_cost + cooling_cost + processing_energy_cost + disease_cost
        loop_net = sum(loop_lines.values())
        total_revenue = herd_revenue + loop_revenue
        # The feed saving lowers the charged feed cost rather than adding revenue.
        total_cost = herd_cost - loop_feed_saving_value + loop_cost
        profit = total_revenue - total_cost

        circularity_score = float(environment.payload.get("circularity_score", 0.0)) if environment is not None else 0.0
        cow_health_score = (
            (float(cow.payload["cow_count"]) - float(cow.payload["sick_cows"])) / max(1.0, float(cow.payload["cow_count"]))
            if cow is not None and float(cow.payload["cow_count"]) > 0.0
            else 0.0
        )
        profit_norm = 0.5 + profit / 1000.0
        profit_norm = max(0.0, min(1.0, profit_norm))
        env_score = (
            1.0 - max(0.0, min(1.0, float(environment.payload.get("net_kg_co2e", 0.0)) / 5000.0))
            if environment is not None
            else 0.5
        )
        objectives = self.ctx.state["objective_weights"]
        operating_point = (
            profit_norm * objectives["profit"]
            + env_score * objectives["environment"]
            + cow_health_score * objectives["animal_welfare"]
            + circularity_score * objectives["circularity"]
        )

        cash_balance = float(
            self.ctx.state.setdefault(
                "farm_cash_balance", float(self.ctx.scenario.get("initial_cash_balance", 0.0))
            )
        ) + profit
        self.ctx.state["farm_cash_balance"] = cash_balance
        schedule = self.ctx.scenario.get("circular_investment_schedule", [])
        scheduled_cost = sum(float(item.get("cost", 0.0)) for item in schedule if isinstance(item, dict))
        investment_cost = self.ctx.scenario.get("circular_investment_cost", scheduled_cost or None)
        annual_circular_benefit = (
            energy_value + carbon_credit_value + byproduct_revenue + compost_revenue + loop_feed_saving_value
        ) * 365.0
        if investment_cost is None or float(investment_cost) <= 0.0:
            roi_circular_investment = None
            payback_period_years = None
        else:
            investment_cost = float(investment_cost)
            roi_circular_investment = annual_circular_benefit / investment_cost
            payback_period_years = (
                investment_cost / annual_circular_benefit if annual_circular_benefit > 0.0 else None
            )
        recommendations = self._recommendation_details(profit, feed_cost, treatment_cost, sensor_alert_count)
        policy_conflicts = self._policy_conflicts(
            profit=profit,
            net_emissions=float(environment.payload.get("net_kg_co2e", 0.0)) if environment else 0.0,
            active_cases=int(disease.payload.get("active_cases", 0)) if disease else 0,
            circularity_score=circularity_score,
        )
        equipment_roi = self._equipment_roi(
            raw_milk_revenue, processor_revenue, byproduct_revenue, energy_value, carbon_credit_value
        )
        self.ctx.publish(
            Packet(
                source=self.name,
                name="manager_packet",
                day=day,
                payload={
                    "milk_revenue": require_nonnegative("milk_revenue", milk_revenue),
                    "raw_milk_revenue": require_nonnegative("raw_milk_revenue", raw_milk_revenue),
                    "processor_revenue": require_nonnegative("processor_revenue", processor_revenue),
                    "byproduct_revenue": require_nonnegative("byproduct_revenue", byproduct_revenue),
                    "energy_value": require_nonnegative("energy_value", energy_value),
                    "carbon_credit_value": require_nonnegative("carbon_credit_value", carbon_credit_value),
                    "feed_cost": require_nonnegative("feed_cost", feed_cost),
                    "workbook_feed_cost": require_nonnegative("workbook_feed_cost", workbook_feed_cost),
                    "loop_feed_saving": require_nonnegative("loop_feed_saving", loop_feed_saving_value),
                    "loop_feed_offset_kg": loop_feed_offset_kg,
                    "purchased_feed_cost": require_nonnegative("purchased_feed_cost", purchased_feed_cost),
                    "processor_revenue_not_in_profit": require_nonnegative("processor_revenue_not_in_profit", processor_revenue),
                    "water_cost": require_nonnegative("water_cost", water_cost),
                    "cooling_cost": require_nonnegative("cooling_cost", cooling_cost),
                    "processing_energy_cost": require_nonnegative(
                        "processing_energy_cost", processing_energy_cost
                    ),
                    "treatment_cost": require_nonnegative("treatment_cost", treatment_cost),
                    "disease_cost": require_nonnegative("disease_cost", disease_cost),
                    "sensor_alert_count": sensor_alert_count,
                    "fixed_cost": require_nonnegative("fixed_cost", fixed_cost),
                    "cow_sales": cow_sales,
                    "calf_sales": calf_sales,
                    "profit_deviation": profit_deviation,
                    "breeding_cost": require_nonnegative("breeding_cost", breeding_cost),
                    "reproduction_management_cost": require_nonnegative("reproduction_management_cost", reproduction_cost),
                    "other_variable_cost": require_nonnegative("other_variable_cost", other_variable_cost),
                    "heifer_cost": require_nonnegative("heifer_cost", heifer_cost),
                    "mastitis_treatment_cost": require_nonnegative("mastitis_treatment_cost", mastitis_cost),
                    "dry_cow_therapy_cost": require_nonnegative("dry_cow_therapy_cost", dry_cow_therapy_cost),
                    "herd_revenue": herd_revenue,
                    "herd_cost": herd_cost,
                    "herd_profit": herd_revenue - herd_cost,
                    "loop_revenue": loop_revenue,
                    "compost_revenue": compost_revenue,
                    "loop_cost": loop_cost,
                    "loop_lines": loop_lines,
                    "loop_net": loop_net,
                    "total_revenue": total_revenue,
                    "total_cost": require_nonnegative("total_cost", total_cost),
                    "profit": profit,
                    "cash_balance": cash_balance,
                    "annual_circular_benefit": require_nonnegative(
                        "annual_circular_benefit", annual_circular_benefit
                    ),
                    "investment_cost_basis": investment_cost,
                    "roi_circular_investment": roi_circular_investment,
                    "payback_period_years": payback_period_years,
                    "recommendation": recommendations[0]["action"],
                    "ranked_recommendations": [item["action"] for item in recommendations],
                    "actionable_recommendations": recommendations,
                    "policy_change_triggers": [item["trigger"] for item in recommendations],
                    "policy_conflicts": policy_conflicts,
                    "automatic_policy_actions": list(
                        self.ctx.state.get("last_automatic_policy_actions", [])
                    ),
                    "planning_horizon_days": int(self.ctx.scenario.get("planning_horizon_days", 365)),
                    "budget_remaining": self.ctx.scenario.get("budget_remaining"),
                    "equipment_roi": equipment_roi,
                    "dashboard_summary_packet": {
                        "profit": profit,
                        "environment_net_kg_co2e": float(environment.payload.get("net_kg_co2e", 0.0)) if environment else 0.0,
                        "animal_welfare_score": cow_health_score,
                        "circularity_score": circularity_score,
                    },
                    "operating_point": operating_point,
                    "profit_norm": profit_norm,
                    "env_score": env_score,
                    "cow_health_score": cow_health_score,
                    "objective_weights": dict(objectives),
                    "effective_policy": dict(self.ctx.state["policy"]),
                },
            )
        )
        self.ctx.state.setdefault("execution_order", []).append(self.name)

    def monthly(self, day: date) -> None:
        """Aggregate manager economics for the current calendar month."""
        if not self.ctx.daily_records:
            return
        month = day.strftime("%Y-%m")
        rows = [row for row in self.ctx.daily_records if row["day"].startswith(month)]
        environment_report = self.ctx.get_packet("environment_report_packet")
        self.ctx.monthly_records.append(
            {
                "month": month,
                "report": "farm_manager",
                "milk_revenue": sum(float(row.get("milk_revenue", 0.0)) for row in rows),
                "total_revenue": sum(float(row.get("total_revenue", 0.0)) for row in rows),
                "total_cost": sum(float(row.get("total_cost", 0.0)) for row in rows),
                "profit": sum(float(row.get("profit", 0.0)) for row in rows),
                "environment_net_kg_co2e": (
                    float(environment_report.payload["net_kg_co2e"])
                    if environment_report is not None
                    else None
                ),
            }
        )

    def annual(self, day: date) -> None:
        """Record the annual genetics review supplied by the breeding agent."""
        genetics = self.ctx.get_packet("genetics_packet")
        if genetics is None:
            return
        review = {
            "year": day.year,
            "report": "farm_manager_genetics_review",
            "net_merit_template": genetics.payload.get("net_merit_template"),
            "herd_net_merit_score": genetics.payload.get("herd_net_merit_score"),
            "genetic_gain_per_generation": genetics.payload.get("genetic_gain_per_generation"),
            "selected_parent_count": genetics.payload.get("selected_parent_count"),
            "breeding_recommendation": genetics.payload.get("breeding_recommendation"),
        }
        self.ctx.annual_records.append(review)
        self.ctx.publish(Packet(source=self.name, name="manager_annual_review_packet", day=day, payload=review, period="annual"))

    @staticmethod
    def _recommendation(profit: float, feed_cost: float, treatment_cost: float) -> str:
        """Choose the highest-priority recommendation from daily cost signals."""
        if treatment_cost > feed_cost:
            return "review_health_protocol"
        if profit < 0:
            return "review_cost_structure"
        return "maintain_current_policy"

    @staticmethod
    def _ranked_recommendations(profit: float, feed_cost: float, treatment_cost: float) -> list[str]:
        """Order policy recommendations by health, profitability, and default priority."""
        recommendations = ["maintain_current_policy"]
        if profit < 0.0:
            recommendations.insert(0, "review_cost_structure")
        if treatment_cost > feed_cost:
            recommendations.insert(0, "review_health_protocol")
        return recommendations

    @staticmethod
    def _recommendation_details(
        profit: float, feed_cost: float, treatment_cost: float, sensor_alert_count: int
    ) -> list[dict[str, str]]:
        """Build actionable recommendations with severity, triggers, and reasons."""
        recommendations: list[dict[str, str]] = []
        if treatment_cost > feed_cost:
            recommendations.append({"tier": "Critical", "action": "review_health_protocol", "trigger": "treatment_cost_exceeds_feed_cost", "reason": "Disease cost is the dominant controllable daily cost."})
        if sensor_alert_count:
            recommendations.append({"tier": "Important", "action": "review_sensor_alerts", "trigger": "filtered_sensor_alerts", "reason": "Filtered sensor alerts require management review."})
        if profit < 0.0:
            recommendations.append({"tier": "Important", "action": "review_cost_structure", "trigger": "negative_profit", "reason": "The current operating point is cash-negative."})
        recommendations.append({"tier": "Advisory", "action": "maintain_current_policy", "trigger": "routine_review", "reason": "No higher-priority policy change is required."})
        rank = {"Critical": 0, "Important": 1, "Advisory": 2}
        return sorted(recommendations, key=lambda item: rank[item["tier"]])

    def _equipment_roi(
        self,
        raw_milk_revenue: float,
        processor_revenue: float,
        byproduct_revenue: float,
        energy_value: float,
        carbon_credit_value: float,
    ) -> dict[str, dict[str, float | None]]:
        """Estimate equipment benefits, return on investment, and payback periods."""
        configured = self.ctx.scenario.get("equipment_capex", {})
        defaults = {
            "milking_parlour_bulk_tank": 0.0,
            "dairy_processor": 0.0,
            "whey_processor": 0.0,
            "manure_system": 0.0,
        }
        capex = {name: float(configured.get(name, default)) for name, default in defaults.items()} if isinstance(configured, dict) else defaults
        benefits = {
            "milking_parlour_bulk_tank": raw_milk_revenue * 365.0,
            "dairy_processor": max(0.0, processor_revenue - raw_milk_revenue) * 365.0,
            "whey_processor": byproduct_revenue * 365.0,
            "manure_system": (energy_value + carbon_credit_value) * 365.0,
        }
        return {
            name: {
                "capex": capex[name],
                "annual_benefit": benefits[name],
                "roi": benefits[name] / capex[name] if capex[name] > 0.0 else None,
                "payback_years": capex[name] / benefits[name] if capex[name] > 0.0 and benefits[name] > 0.0 else None,
            }
            for name in defaults
        }

    def _policy_conflicts(
        self, profit: float, net_emissions: float, active_cases: int, circularity_score: float
    ) -> list[dict[str, str]]:
        """Expose competing objectives instead of hiding them behind a scalar score."""
        conflicts: list[dict[str, str]] = []
        policy = self.ctx.state["policy"]
        if profit < 0.0 and bool(policy.get("catch_crop_active", False)):
            conflicts.append(
                {
                    "objectives": "profit/environment",
                    "reason": "catch_crop policy remains active while daily profit is negative",
                    "resolution": "review catch-crop cost and carbon benefit at the planning horizon",
                }
            )
        if active_cases > 0 and float(policy.get("biosecurity_level_pct", 0.0)) < 0.75:
            conflicts.append(
                {
                    "objectives": "profit/animal_welfare",
                    "reason": "disease cases are active below the biosecurity response threshold",
                    "resolution": "raise biosecurity and schedule vaccination rollout",
                }
            )
        if net_emissions > float(self.ctx.scenario.get("auto_emissions_trigger_kg_co2e", 1000.0)) and circularity_score < 0.5:
            conflicts.append(
                {
                    "objectives": "environment/circularity",
                    "reason": "emissions exceed the action trigger while circular resource recovery is low",
                    "resolution": "prioritize digestate use, water reuse, or energy recovery",
                }
            )
        return conflicts
