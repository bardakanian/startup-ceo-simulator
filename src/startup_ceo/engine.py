"""Deterministic business simulation engine.

The engine deliberately has no GUI dependencies, which keeps the business
rules testable and makes the model useful in classroom discussion.
"""

from __future__ import annotations

from dataclasses import replace
import math
import random

from .dilemmas import dilemma_schedule
from .formatting import money
from .models import (
    MIN_EMPLOYEES, SUPPORT_PER_EMPLOYEE, Decision, DecisionRecord, DilemmaEffect, DilemmaOption, GameState,
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
PRICE_INCREASE_CHURN = 0.25
CHURN_MULTIPLE_PENALTY = 10
HEALTHY_CHURN = 0.03


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

    def preview_net_burn(self, decision: Decision) -> float:
        """Projected quarterly operating cash burn (negative means the plan generates cash)."""
        return -self._project(decision)[0].operating_profit

    def preview_runway_months(self, decision: Decision) -> float:
        burn = self.preview_net_burn(decision)
        if burn <= 0:
            return math.inf
        cash = self.state.cash + self._preview_effect(decision).cash
        if decision.raise_funding:
            cash += self.funding_offer()[0]
        return max(0.0, cash) / burn * 3

    def _project(self, decision: Decision) -> tuple[QuarterResult, GameState]:
        """Play the quarter on a throwaway copy of the state: same rules and announced market event,
        but average demand instead of the quarter's random variation, so previews stay estimates."""
        dilemma, option = self._chosen_option(decision)
        state = replace(self.state, history=[], decision_history=[])
        headcount = max(MIN_EMPLOYEES, self.headcount_after(decision))
        return self._play_quarter(state, decision, dilemma, option, headcount, projection=True), state

    def preview_effects(self, decision: Decision) -> dict[str, str]:
        """Give directional estimates; actual results still include the quarter's demand variation."""
        decision.validate()
        state = self.state
        effect = self._preview_effect(decision)
        projected, after = self._project(decision)
        growth = (projected.customers - state.customers) / max(1, state.customers)
        quality_change = after.product_quality - state.product_quality
        runway_months = self.preview_runway_months(decision)

        return {
            "Customer growth": "Low" if growth < 0.03 else "High" if growth > 0.10 else "Moderate",
            "Operating margin": "Improving" if projected.operating_profit > 0 else "Under pressure",
            "Product quality": "Improving" if quality_change > 0.5 else "Declining" if quality_change < -0.5 else "Stable",
            "Service capacity": "Under pressure" if projected.support_load > 1 else "Stretched" if projected.support_load > 0.85 else "Stable",
            "Runway resilience": "High" if runway_months >= 12 else "Moderate" if runway_months >= 6 else "Under pressure",
            "Founder control": "Under pressure" if decision.raise_funding or effect.dilution else "Stable",
        }

    def advance(self, decision: Decision) -> QuarterResult:
        decision.validate()
        if self.state.complete:
            raise RuntimeError("The simulation has already ended.")
        dilemma, option = self._chosen_option(decision)
        if dilemma is not None and option is None:
            raise ValueError(f"The board needs your response to \"{dilemma.title}\" before the quarter can be committed.")
        if option is not None and (problem := self.check_dilemma_option(option, decision.raise_funding)):
            raise ValueError(problem)
        headcount = self.headcount_after(decision)
        if headcount < MIN_EMPLOYEES:
            raise ValueError(f"At least {MIN_EMPLOYEES} employees must remain to run the company.")
        return self._play_quarter(self.state, decision, dilemma, option, headcount)

    def _play_quarter(
        self, state: GameState, decision: Decision, dilemma: StrategicDilemma | None,
        option: DilemmaOption | None, headcount: int, projection: bool = False,
    ) -> QuarterResult:
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
        competitive_noise = rng.uniform(0.94, 1.06)
        if projection:
            competitive_noise = 1.0

        support_capacity = headcount * SUPPORT_PER_EMPLOYEE
        state.market_size *= 1 + BASE_MARKET_GROWTH + event.market_growth
        saturation = max(0.1, 1 - old_customers / state.market_size)
        # A stronger product earns pricing power: buyers are less price-sensitive.
        price_factor = math.pow(79 / decision.price, 1.6 - state.product_quality / 100)
        marketing_leads = math.sqrt(decision.marketing + 1) * 3.2
        conversion = 0.24 + state.product_quality / 500 + state.brand / 800
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
        # Raising the price on existing customers pushes some of them to leave.
        churn_rate += max(0.0, decision.price / state.current_price - 1) * PRICE_INCREASE_CHURN
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

        funding = 0.0
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
        # Investors value organic momentum: acquired customers add revenue but are not growth.
        organic_growth = (state.customers - old_customers) / max(1, old_customers)
        quarterly_churn = churned / max(1, old_customers)

        annualized_revenue = revenue * 4
        margin = operating_profit / revenue if revenue else -1
        multiple = max(1.2, min(7.0,
            3.2 + organic_growth * 8 + margin * 1.5 + state.product_quality / 100
            - max(0.0, quarterly_churn - HEALTHY_CHURN) * CHURN_MULTIPLE_PENALTY
        ))
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
            acquired_customers=effect.customers,
            funding_raised=funding,
            board_cash=effect.cash,
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

