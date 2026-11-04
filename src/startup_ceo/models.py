"""Data models shared by the simulation and local services."""

from __future__ import annotations

from dataclasses import dataclass, field


STARTING_CUSTOMERS = 800
SUPPORT_PER_EMPLOYEE = 300
MIN_EMPLOYEES = 3


@dataclass(slots=True, frozen=True)
class MarketEvent:
    name: str
    description: str
    demand_multiplier: float = 1.0
    cost_multiplier: float = 1.0
    brand_delta: float = 0.0
    market_growth: float = 0.0


@dataclass(slots=True, frozen=True)
class DilemmaEffect:
    """One-off consequences of a board decision, applied in the quarter it is made."""

    cash: float = 0.0
    expense: float = 0.0
    customers: int = 0
    employees: int = 0
    quality: float = 0.0
    brand: float = 0.0
    morale: float = 0.0
    dilution: float = 0.0
    demand_multiplier: float = 1.0
    revenue_multiplier: float = 1.0
    variable_cost_delta: float = 0.0
    churn_delta: float = 0.0


@dataclass(slots=True, frozen=True)
class DilemmaOption:
    key: str
    label: str
    outcome: str
    effect: DilemmaEffect = DilemmaEffect()


@dataclass(slots=True, frozen=True)
class StrategicDilemma:
    key: str
    title: str
    description: str
    options: tuple[DilemmaOption, ...]

    def option(self, key: str) -> DilemmaOption | None:
        return next((option for option in self.options if option.key == key), None)


@dataclass(slots=True)
class Decision:
    price: int = 79
    marketing: int = 90_000
    product: int = 80_000
    hires: int = 1
    layoffs: int = 0
    raise_funding: bool = False
    dilemma_choice: str = ""

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
    costs: dict[str, float] = field(default_factory=dict)
    support_load: float = 0.0
    acquired_customers: int = 0
    funding_raised: float = 0.0
    board_cash: float = 0.0

    @property
    def growth(self) -> int:
        return self.new_customers + self.acquired_customers - self.churned_customers


@dataclass(slots=True)
class DecisionRecord:
    quarter: int
    decision: Decision
    event_name: str
    dilemma: str = ""
    response: str = ""
    acquired_employees: int = 0


@dataclass(slots=True)
class GameState:
    company_name: str = "Northstar Labs"
    quarter: int = 0
    max_quarters: int = 12
    cash: float = 1_200_000
    revenue: float = 0
    operating_profit: float = 0
    customers: int = STARTING_CUSTOMERS
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
    market_size: float = 20_000
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

    @property
    def support_capacity(self) -> float:
        return self.employees * SUPPORT_PER_EMPLOYEE

    @property
    def founder_stake(self) -> float:
        return self.valuation * self.founder_ownership / 100

    def score_breakdown(self) -> dict[str, float]:
        """CEO score components; the founder's stake rewards value creation net of dilution."""
        quarters = max(1, self.quarter)
        compound_growth = (max(1, self.customers) / STARTING_CUSTOMERS) ** (1 / quarters) - 1
        return {
            "Founder stake value": 35 * min(1.0, max(0.0, self.founder_stake / 30_000_000)),
            "Customer growth": 20 * min(1.0, max(0.0, compound_growth / 0.15)) if self.history else 0.0,
            # Capped low so that raising money late in the game is not a shortcut to points.
            "Liquidity": 10 * min(1.0, max(0.0, self.cash / 1_000_000)),
            "Product and people": 15 * (self.product_quality + self.morale) / 200,
            "Board objectives": 5.0 * sum(self.objective_progress.values()),
            "Profitability": 5.0 if self.operating_profit > 0 else 0.0,
        }

    def score(self) -> int:
        return round(min(100, sum(self.score_breakdown().values())))
