"""Deterministic business simulation engine.

The engine deliberately has no GUI dependencies, which keeps the business
rules testable and makes the model useful in classroom discussion.
"""

from __future__ import annotations

import math
import random

from .dilemmas import dilemma_schedule
from .formatting import money
from .models import (
    SUPPORT_PER_EMPLOYEE, Decision, DecisionRecord, DilemmaEffect, DilemmaOption, GameState,
    MarketEvent, QuarterResult, StrategicDilemma,
)


EVENTS = (
    MarketEvent("Steady market", "Demand follows the expected category trend."),
    MarketEvent("Enterprise spotlight", "A major industry newsletter features your product.", 1.18, 1.0, 3),
    MarketEvent("Economic slowdown", "Customers scrutinize new software spending.", 0.82, 1.0, -1),
    MarketEvent("Supplier price increase", "Cloud and vendor costs rise this quarter.", 1.0, 1.22),
    MarketEvent("Competitor outage", "A rival's service failure sends buyers into the market.", 1.14, 1.0, 2),
    MarketEvent("Privacy concern", "Category-wide privacy concerns slow new adoption.", 0.90, 1.04, -2),
    MarketEvent("Market expansion", "The addressable market grows faster than forecast.", 1.12, market_growth=0.08),
)

BASE_MARKET_GROWTH = 0.02
FIXED_OVERHEAD = 75_000
SALARY = 27_000
HIRING_COST = 8_000
SEVERANCE = 18_000
VARIABLE_COST_RATE = 0.19
MIN_EMPLOYEES = 3


class SimulationEngine:
    """Advances a company one quarter using explainable business rules."""

    def __init__(self, seed: int = 2027, company_name: str = "Northstar Labs") -> None:
        self.seed = seed
        self.state = GameState(company_name=company_name)

    def reset(self, company_name: str | None = None, seed: int | None = None) -> GameState:
        if seed is not None:
            self.seed = seed
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

    def upcoming_dilemma(self) -> StrategicDilemma | None:
        """Return the board decision due next quarter, if any."""
        if self.state.complete:
            return None
        return dilemma_schedule(self.seed, self.state.max_quarters).get(self.state.quarter + 1)

    def funding_offer(self) -> tuple[float, int]:
        """Cash raised and percentage dilution if the company raises a round this quarter."""
        return 750_000 + self.state.valuation * 0.04, 9 + self.state.funding_rounds * 2

    def check_dilemma_option(self, option: DilemmaOption, raising_funding: bool = False) -> str | None:
        """Explain why an option is unavailable, or return None if it can be chosen."""
        available = self.state.cash + (self.funding_offer()[0] if raising_funding else 0)
        if option.effect.cash < 0 and available + option.effect.cash < 0:
            return f"Not enough cash: this option needs {money(-option.effect.cash)}."
        return None

    def headcount_after(self, decision: Decision) -> int:
        return self.state.employees + self._preview_effect(decision).employees + decision.hires - decision.layoffs

    def _chosen_option(self, decision: Decision) -> tuple[StrategicDilemma | None, DilemmaOption | None]:
        dilemma = self.upcoming_dilemma()
        if dilemma is None:
            return None, None
        return dilemma, dilemma.option(decision.dilemma_choice)

    def _preview_effect(self, decision: Decision) -> DilemmaEffect:
        _, option = self._chosen_option(decision)
        return option.effect if option else DilemmaEffect()

    def preview_cost(self, decision: Decision) -> float:
        """Quarterly cash costs before revenue-linked variable costs."""
        effect = self._preview_effect(decision)
        headcount = max(MIN_EMPLOYEES, self.headcount_after(decision))
        return (
            effect.expense
            + FIXED_OVERHEAD
            + headcount * SALARY
            + decision.marketing
            + decision.product
            + decision.hires * HIRING_COST
            + decision.layoffs * SEVERANCE
        )

    def preview_net_burn(self, decision: Decision) -> float:
        """Estimated quarterly cash burn assuming today's customers stay (negative means cash-generating)."""
        effect = self._preview_effect(decision)
        revenue = (self.state.customers + effect.customers) * decision.price * 3 * effect.revenue_multiplier
        return self.preview_cost(decision) + revenue * (VARIABLE_COST_RATE + effect.variable_cost_delta) - revenue

    def preview_runway_months(self, decision: Decision) -> float:
        burn = self.preview_net_burn(decision)
        if burn <= 0:
            return math.inf
        cash = self.state.cash + self._preview_effect(decision).cash
        if decision.raise_funding:
            cash += self.funding_offer()[0]
        return max(0.0, cash) / burn * 3

    def preview_effects(self, decision: Decision) -> dict[str, str]:
        """Give directional estimates; actual results still include the market event."""
        decision.validate()
        state = self.state
        effect = self._preview_effect(decision)
        headcount = max(MIN_EMPLOYEES, self.headcount_after(decision))
        customers = state.customers + effect.customers
        saturation = max(0.1, 1 - customers / state.market_size)
        price_pressure = (decision.price - 79) / 70
        growth_signal = (
            (decision.marketing / 250_000 + decision.product / 400_000 - price_pressure) * min(1.0, saturation / 0.6)
            * effect.demand_multiplier - effect.churn_delta * 5
        )
        margin_signal = -self.preview_net_burn(decision)
        quality_signal = (
            1.8 * math.sqrt(decision.product / 50_000) + headcount / 40 - (state.product_quality / 25 - 1) + effect.quality
        )
        runway_months = self.preview_runway_months(decision)
        support_load = customers * 1.15 / (headcount * SUPPORT_PER_EMPLOYEE)

        def level(value: float, low: float, high: float) -> str:
            return "Low" if value < low else "High" if value > high else "Moderate"

        return {
            "Customer growth": level(growth_signal, 0.35, 0.85),
            "Operating margin": "Improving" if margin_signal > 0 else "Under pressure",
            "Product quality": "Improving" if quality_signal > 0.5 else "Declining" if quality_signal < -0.5 else "Stable",
            "Service capacity": "Under pressure" if support_load > 1 else "Stretched" if support_load > 0.85 else "Stable",
            "Runway resilience": "High" if runway_months >= 12 else "Moderate" if runway_months >= 6 else "Under pressure",
            "Founder control": "Under pressure" if decision.raise_funding or effect.dilution else "Stable",
        }

    def advance(self, decision: Decision) -> QuarterResult:
        decision.validate()
        state = self.state
        if state.complete:
            raise RuntimeError("The simulation has already ended.")
        dilemma, option = self._chosen_option(decision)
        if dilemma is not None and option is None:
            raise ValueError(f"The board needs your response to \"{dilemma.title}\" before the quarter can be committed.")
        if option is not None and (problem := self.check_dilemma_option(option, decision.raise_funding)):
            raise ValueError(problem)
        headcount = self.headcount_after(decision)
        if headcount < MIN_EMPLOYEES:
            raise ValueError(f"At least {MIN_EMPLOYEES} employees must remain to run the company.")
        effect = option.effect if option else DilemmaEffect()

        opening_customers = state.customers
        # Board decisions take effect at the start of the quarter.
        state.customers += effect.customers
        state.cash += effect.cash
        state.founder_ownership *= 1 - effect.dilution / 100
        state.product_quality = min(100, max(0, state.product_quality + effect.quality))
        state.brand = min(100, max(0, state.brand + effect.brand))
        state.morale = min(100, max(10, state.morale + effect.morale))
        old_customers = state.customers
        state.quarter += 1
        rng = random.Random(self.seed + state.quarter * 7919)
        event = EVENTS[rng.randrange(len(EVENTS))]

        support_capacity = headcount * SUPPORT_PER_EMPLOYEE
        state.market_size *= 1 + BASE_MARKET_GROWTH + event.market_growth
        saturation = max(0.1, 1 - old_customers / state.market_size)
        # A stronger product earns pricing power: buyers are less price-sensitive.
        price_factor = math.pow(79 / decision.price, 1.6 - state.product_quality / 100)
        marketing_leads = math.sqrt(decision.marketing + 1) * 3.2
        conversion = 0.24 + state.product_quality / 500 + state.brand / 800
        competitive_noise = rng.uniform(0.94, 1.06)
        potential_new = (
            marketing_leads * conversion * price_factor * saturation
            * event.demand_multiplier * effect.demand_multiplier * competitive_noise
        )
        new_customers = max(0, min(round(potential_new), round(support_capacity * 0.5)))
        # Customers beyond what the team can support wait longer and leave sooner.
        support_load = (old_customers + new_customers) / support_capacity
        overload = max(0.0, support_load - 1)

        churn_rate = 0.115 - state.product_quality / 1200 - state.morale / 2500 + overload * 0.15 + effect.churn_delta
        if decision.price > 99:
            churn_rate += (decision.price - 99) / 900 * (1.5 - state.product_quality / 100)
        churned = min(old_customers, max(0, round(old_customers * max(0.025, churn_rate))))
        state.customers = max(0, old_customers + new_customers - churned)

        average_customers = (old_customers + state.customers) / 2
        revenue = average_customers * decision.price * 3 * effect.revenue_multiplier
        costs = {
            "Variable costs": revenue * (VARIABLE_COST_RATE * event.cost_multiplier + effect.variable_cost_delta),
            "Payroll": headcount * SALARY,
            "Marketing": float(decision.marketing),
            "Product": float(decision.product),
            "Overhead": float(FIXED_OVERHEAD),
            "Hiring and severance": float(decision.hires * HIRING_COST + decision.layoffs * SEVERANCE),
        }
        if effect.expense:
            costs["Board decision"] = float(effect.expense)
        operating_profit = revenue - sum(costs.values())
        gross_profit = revenue - costs["Variable costs"]

        if decision.raise_funding:
            funding, dilution = self.funding_offer()
            state.cash += funding
            state.founder_ownership *= (1 - dilution / 100)
            state.funding_rounds += 1

        state.cash += operating_profit
        state.employees = headcount
        quality_gain = 1.8 * math.sqrt(decision.product / 50_000) + headcount / 40
        quality_decay = state.product_quality / 25 - 1 + overload * 6
        state.product_quality = min(100, max(0, state.product_quality + quality_gain - quality_decay))
        state.brand = min(100, max(0, state.brand + decision.marketing / 65_000 + event.brand_delta - 1))
        morale_change = 1.5 if operating_profit > 0 else -1.5
        morale_change += min(2.0, decision.product / 100_000) - decision.layoffs * 5 - decision.hires * 0.3 - overload * 10
        state.morale = min(100, max(10, state.morale + morale_change))
        state.last_growth = (state.customers - opening_customers) / max(1, opening_customers)

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
        if overload > 0:
            narrative += f" Support ran at {support_load:.0%} of capacity, which raised churn and hurt morale; hire ahead of demand."
        elif saturation < 0.45:
            narrative += " The core market is maturing, so each marketing dollar now wins fewer customers; retention and price matter more."
        if dilemma is not None and option is not None:
            narrative = f"{dilemma.title}: {option.outcome} {narrative}"

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
            costs=costs,
            support_load=support_load,
        )
        state.history.append(result)
        state.decision_history.append(
            DecisionRecord(
                state.quarter, decision, event.name,
                dilemma=dilemma.title if dilemma else "", response=option.label if option else "",
                acquired_employees=effect.employees,
            )
        )
        return result

