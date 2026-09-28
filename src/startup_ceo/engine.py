"""Deterministic business simulation engine.

The engine deliberately has no GUI dependencies, which keeps the business
rules testable and makes the model useful in classroom discussion.
"""

from __future__ import annotations

import math
import random

from .models import Decision, DecisionRecord, GameState, MarketEvent, QuarterResult


EVENTS = (
    MarketEvent("Steady market", "Demand follows the expected category trend."),
    MarketEvent("Enterprise spotlight", "A major industry newsletter features your product.", 1.18, 1.0, 3),
    MarketEvent("Economic slowdown", "Customers scrutinize new software spending.", 0.82, 1.0, -1),
    MarketEvent("Supplier price increase", "Cloud and vendor costs rise this quarter.", 1.0, 1.22),
    MarketEvent("Competitor outage", "A rival's service failure sends buyers into the market.", 1.14, 1.0, 2),
    MarketEvent("Privacy concern", "Category-wide privacy concerns slow new adoption.", 0.90, 1.04, -2),
    MarketEvent("Market expansion", "The addressable market grows faster than forecast.", 1.12),
)


class SimulationEngine:
    """Advances a company one quarter using explainable business rules."""

    def __init__(self, seed: int = 2027, company_name: str = "Northstar Labs") -> None:
        self.seed = seed
        self.state = GameState(company_name=company_name)

    def reset(self, company_name: str | None = None) -> GameState:
        self.state = GameState(company_name=company_name or self.state.company_name)
        return self.state

    @classmethod
    def from_state(cls, state: GameState, seed: int = 2027) -> SimulationEngine:
        engine = cls(seed=seed, company_name=state.company_name)
        engine.state = state
        return engine

    def upcoming_event(self) -> MarketEvent:
        """Return the next event without consuming or changing simulation state."""
        rng = random.Random(self.seed + (self.state.quarter + 1) * 7919)
        return EVENTS[rng.randrange(len(EVENTS))]

    def preview_cost(self, decision: Decision) -> float:
        headcount = max(3, self.state.employees + decision.hires - decision.layoffs)
        return (
            75_000
            + headcount * 27_000
            + decision.marketing
            + decision.product
            + decision.hires * 8_000
            + decision.layoffs * 18_000
        )

    def preview_effects(self, decision: Decision) -> dict[str, str]:
        """Give directional estimates; actual results still include the market event."""
        decision.validate()
        state = self.state
        price_pressure = (decision.price - 79) / 70
        growth_signal = decision.marketing / 250_000 + decision.product / 400_000 - price_pressure
        margin_signal = decision.price / 100 - self.preview_cost(decision) / max(state.revenue or 450_000, 1)
        quality_signal = decision.product / 80_000 + decision.hires / 8 - decision.layoffs / 4
        runway_months = state.cash / max(1, self.preview_cost(decision)) * 3

        def level(value: float, low: float, high: float) -> str:
            return "Low" if value < low else "High" if value > high else "Moderate"

        return {
            "Customer growth": level(growth_signal, 0.35, 0.85),
            "Operating margin": "Improving" if margin_signal > 0 else "Under pressure",
            "Product quality": "Improving" if quality_signal >= 1 else "Stable",
            "Runway resilience": "High" if runway_months >= 12 else "Moderate" if runway_months >= 6 else "Under pressure",
            "Founder control": "Under pressure" if decision.raise_funding else "Stable",
        }

    def advance(self, decision: Decision) -> QuarterResult:
        decision.validate()
        state = self.state
        if state.complete:
            raise RuntimeError("The simulation has already ended.")
        if decision.layoffs >= state.employees:
            raise ValueError("At least one employee must remain.")

        old_customers = state.customers
        state.quarter += 1
        rng = random.Random(self.seed + state.quarter * 7919)
        event = EVENTS[rng.randrange(len(EVENTS))]

        headcount = max(3, state.employees + decision.hires - decision.layoffs)
        capacity = 650 + headcount * 165 + state.product_quality * 9
        price_factor = math.pow(79 / decision.price, 1.15)
        marketing_leads = math.sqrt(decision.marketing + 1) * 3.2
        conversion = 0.24 + state.product_quality / 500 + state.brand / 800
        competitive_noise = rng.uniform(0.94, 1.06)
        potential_new = marketing_leads * conversion * price_factor * event.demand_multiplier * competitive_noise
        new_customers = max(0, min(round(potential_new), round(capacity * 0.36)))

        churn_rate = 0.115 - state.product_quality / 1200 - state.morale / 2500
        if decision.price > 99:
            churn_rate += (decision.price - 99) / 900
        churned = min(old_customers, max(0, round(old_customers * max(0.025, churn_rate))))
        state.customers = max(0, old_customers + new_customers - churned)

        average_customers = (old_customers + state.customers) / 2
        revenue = average_customers * decision.price * 3
        variable_costs = revenue * 0.19 * event.cost_multiplier
        payroll = headcount * 27_000
        operating_costs = (
            variable_costs + payroll + 75_000 + decision.marketing + decision.product
            + decision.hires * 8_000 + decision.layoffs * 18_000
        )
        operating_profit = revenue - operating_costs
        gross_profit = revenue - variable_costs

        if decision.raise_funding:
            funding = 750_000 + state.valuation * 0.04
            dilution = 9 + state.funding_rounds * 2
            state.cash += funding
            state.founder_ownership *= (1 - dilution / 100)
            state.funding_rounds += 1

        state.cash += operating_profit
        state.employees = headcount
        state.product_quality = min(100, state.product_quality + decision.product / 42_000 + headcount / 30 - 1.2)
        state.brand = min(100, max(0, state.brand + decision.marketing / 65_000 + event.brand_delta - 1))
        morale_change = 1.5 if operating_profit > 0 else -1.5
        morale_change += min(2.0, decision.product / 100_000) - decision.layoffs * 5 - decision.hires * 0.3
        state.morale = min(100, max(10, state.morale + morale_change))
        state.last_growth = (state.customers - old_customers) / max(1, old_customers)

        annualized_revenue = revenue * 4
        margin = operating_profit / revenue if revenue else -1
        multiple = max(1.2, min(7.0, 3.2 + state.last_growth * 8 + margin * 1.5 + state.product_quality / 100))
        state.valuation = max(500_000, annualized_revenue * multiple + max(0, state.cash) * 0.6)
        state.revenue = revenue
        state.operating_profit = operating_profit
        state.current_price = decision.price
        state.bankrupt = state.cash < -250_000

        if state.last_growth > 0.08 and operating_profit > 0:
            narrative = "Efficient growth: customer momentum and positive operating profit improved investor confidence."
        elif state.last_growth > 0.08:
            narrative = "Growth accelerated, but the burn rate increased. The next quarter should test operating leverage."
        elif operating_profit > 0:
            narrative = "Disciplined operations protected cash, although customer growth remained modest."
        else:
            narrative = "The business lost cash and growth was limited. Revisit pricing, acquisition spend, and capacity."

        result = QuarterResult(
            quarter=state.quarter,
            event=event,
            revenue=revenue,
            gross_profit=gross_profit,
            operating_profit=operating_profit,
            ending_cash=state.cash,
            customers=state.customers,
            new_customers=new_customers,
            churned_customers=churned,
            valuation=state.valuation,
            narrative=narrative,
        )
        state.history.append(result)
        state.decision_history.append(DecisionRecord(state.quarter, decision, event.name))
        return result


def money(value: float) -> str:
    sign = "-" if value < 0 else ""
    value = abs(value)
    if value >= 1_000_000:
        return f"{sign}${value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"{sign}${value / 1_000:.0f}K"
    return f"{sign}${value:,.0f}"
