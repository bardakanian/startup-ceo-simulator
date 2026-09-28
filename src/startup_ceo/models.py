"""Data models shared by the simulation and local services."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class MarketEvent:
    name: str
    description: str
    demand_multiplier: float = 1.0
    cost_multiplier: float = 1.0
    brand_delta: float = 0.0


@dataclass(slots=True)
class Decision:
    price: int = 79
    marketing: int = 90_000
    product: int = 80_000
    hires: int = 1
    layoffs: int = 0
    raise_funding: bool = False

    def validate(self) -> None:
        if not 39 <= self.price <= 149:
            raise ValueError("Price must be between $39 and $149.")
        if not 0 <= self.marketing <= 250_000:
            raise ValueError("Marketing spend must be between $0 and $250,000.")
        if not 0 <= self.product <= 200_000:
            raise ValueError("Product investment must be between $0 and $200,000.")
        if not 0 <= self.hires <= 8 or not 0 <= self.layoffs <= 5:
            raise ValueError("Hiring or layoff decision is outside the allowed range.")
        if self.hires and self.layoffs:
            raise ValueError("A company cannot hire and lay off in the same quarter.")


@dataclass(slots=True)
class QuarterResult:
    quarter: int
    event: MarketEvent
    revenue: float
    gross_profit: float
    operating_profit: float
    ending_cash: float
    customers: int
    new_customers: int
    churned_customers: int
    valuation: float
    narrative: str

    @property
    def growth(self) -> int:
        return self.new_customers - self.churned_customers


@dataclass(slots=True)
class DecisionRecord:
    quarter: int
    decision: Decision
    event_name: str


@dataclass(slots=True)
class GameState:
    company_name: str = "Northstar Labs"
    quarter: int = 0
    max_quarters: int = 12
    cash: float = 1_200_000
    revenue: float = 0
    operating_profit: float = 0
    customers: int = 800
    employees: int = 8
    product_quality: float = 55
    brand: float = 40
    morale: float = 72
    founder_ownership: float = 100
    valuation: float = 4_000_000
    last_growth: float = 0
    funding_rounds: int = 0
    bankrupt: bool = False
    current_price: int = 79
    history: list[QuarterResult] = field(default_factory=list)
    decision_history: list[DecisionRecord] = field(default_factory=list)

    @property
    def complete(self) -> bool:
        return self.quarter >= self.max_quarters or self.bankrupt

    @property
    def arr(self) -> float:
        return self.customers * self.current_price * 12

    @property
    def objective_progress(self) -> dict[str, bool]:
        return {
            "Finish with positive cash": self.cash > 0,
            "Reach at least 3,000 customers": self.customers >= 3_000,
            "Retain at least 80% founder ownership": self.founder_ownership >= 80,
        }

    def score(self) -> int:
        growth_score = max(0.0, min(30.0, self.last_growth * 60))
        value_score = min(35.0, self.valuation / 500_000)
        resilience = min(20.0, max(0.0, self.cash / 100_000))
        stakeholder = (self.product_quality + self.morale) / 20
        ownership = self.founder_ownership / 12
        objective_bonus = sum(self.objective_progress.values()) * 3
        return round(min(100, growth_score + value_score + resilience + stakeholder + ownership + objective_bonus))
