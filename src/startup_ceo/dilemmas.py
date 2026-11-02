"""Board dilemmas: one-off strategic decisions that arrive in some quarters.

Each dilemma is scheduled from the scenario seed, so every team playing the same
scenario meets the same decisions in the same quarters.
"""

from __future__ import annotations

from functools import lru_cache
import random

from .formatting import money
from .models import DilemmaEffect as Effect, DilemmaOption as Option, StrategicDilemma as Dilemma


DILEMMAS = (
    Dilemma(
        "enterprise_pilot",
        "Enterprise pilot request",
        "A Fortune 500 company will sign a large pilot, but only if you build custom features for it.",
        (
            Option("build", "Build the custom features", "The pilot closed, but the custom work pulled engineers off the core roadmap.",
                   Effect(expense=120_000, customers=180, quality=-4, morale=-3)),
            Option("partner", "Deliver through an integration partner", "A partner handled the customization; the deal was smaller but the roadmap stayed intact.",
                   Effect(expense=40_000, customers=70)),
            Option("decline", "Offer only the standard product", "The prospect walked away, and the team stayed focused on the core product.",
                   Effect(brand=-1, quality=1)),
        ),
    ),
    Dilemma(
        "security_flaw",
        "Security vulnerability reported",
        "An outside researcher has found a flaw that could expose customer data. No breach has happened yet.",
        (
            Option("disclose", "Disclose publicly and fix now", "Customers praised the transparency, and the fix strengthened the platform.",
                   Effect(expense=90_000, brand=3, quality=3)),
            Option("audit", "Pause releases for a full security audit", "The audit hardened the product, but the release freeze slowed new sales.",
                   Effect(expense=150_000, quality=7, demand_multiplier=0.88)),
            Option("quiet", "Patch quietly without telling customers", "Word leaked out. Trust fell, churn rose, and staff were uneasy about the cover-up.",
                   Effect(brand=-5, morale=-5, churn_delta=0.03)),
        ),
    ),
    Dilemma(
        "key_engineer",
        "Lead engineer is being poached",
        "A well-funded rival has offered your lead engineer a 40% raise.",
        (
            Option("equity", "Counter with an equity grant", "The engineer stayed, at the cost of a slice of founder ownership.",
                   Effect(dilution=2, morale=2)),
            Option("team_bonus", "Fund retention bonuses for the whole team", "The engineer stayed and the whole team felt valued.",
                   Effect(expense=70_000, morale=6)),
            Option("let_go", "Let them leave", "Losing the lead engineer slowed product work and unsettled the team.",
                   Effect(quality=-6, morale=-4)),
        ),
    ),
    Dilemma(
        "acquihire",
        "Acqui-hire opportunity",
        "A struggling startup with four engineers and 300 customers wants to be acquired.",
        (
            Option("cash", "Acquire it for $450K cash", "The team and customers joined, and integration briefly strained morale.",
                   Effect(cash=-450_000, employees=4, customers=300, morale=-2)),
            Option("stock", "Acquire it for stock", "The deal preserved cash but diluted the founder.",
                   Effect(dilution=6, employees=4, customers=300, morale=-2)),
            Option("pass", "Pass on the deal", "You stayed focused on organic growth."),
        ),
    ),
    Dilemma(
        "marketplace",
        "Marketplace partnership",
        "A large software marketplace offers to feature you this quarter in exchange for a 15% revenue share.",
        (
            Option("join", "Join the marketplace", "The marketplace brought a wave of sign-ups, but its revenue share squeezed margins.",
                   Effect(demand_multiplier=1.35, variable_cost_delta=0.15)),
            Option("direct", "Stay direct-only", "You kept full margins and control of the customer relationship.",
                   Effect(brand=1)),
        ),
    ),
    Dilemma(
        "viral_complaint",
        "Viral customer complaint",
        "An angry customer's post about an outage is trending across the industry.",
        (
            Option("apologize", "CEO apology with service credits", "The candid response turned critics into advocates.",
                   Effect(expense=50_000, brand=2, churn_delta=-0.01)),
            Option("ignore", "Let it blow over", "Silence looked like indifference; prospects hesitated and some customers left.",
                   Effect(brand=-4, churn_delta=0.02, demand_multiplier=0.92)),
        ),
    ),
    Dilemma(
        "price_war",
        "Competitor price war",
        "Your largest rival has cut its price by 30% and is targeting your customers.",
        (
            Option("match", "Run a matching discount this quarter", "The discount protected the customer base at the cost of a quarter's revenue.",
                   Effect(revenue_multiplier=0.85, churn_delta=-0.025, demand_multiplier=1.1)),
            Option("premium_support", "Add premium support instead", "Better service justified the price gap, though the team felt the extra load.",
                   Effect(expense=70_000, churn_delta=-0.02, morale=-2)),
            Option("hold", "Hold price and stay the course", "Some price-sensitive customers left for the cheaper rival.",
                   Effect(churn_delta=0.02, demand_multiplier=0.85)),
        ),
    ),
    Dilemma(
        "research_grant",
        "Government R&D grant",
        "You qualify for a $250K innovation grant with heavy reporting requirements.",
        (
            Option("apply", "Accept the grant", "The non-dilutive cash helped, though the paperwork distracted the team.",
                   Effect(cash=250_000, expense=40_000, morale=-2, demand_multiplier=0.95)),
            Option("skip", "Skip it and stay focused", "The team stayed focused on customers."),
        ),
    ),
    Dilemma(
        "workplace",
        "Workplace strategy",
        "Your lease is up. The team is split between going remote-first and opening a new headquarters.",
        (
            Option("remote", "Go remote-first", "Lower overhead and flexibility lifted morale, though collaboration suffered slightly.",
                   Effect(expense=-30_000, morale=3, quality=-1)),
            Option("hq", "Open a new headquarters", "The new office energized the team and impressed customers, at a real cost.",
                   Effect(expense=160_000, morale=5, brand=2)),
            Option("renew", "Renew the current lease", "Nothing changed, for better or worse."),
        ),
    ),
)

DILEMMAS_PER_GAME = 4


@lru_cache(maxsize=64)
def dilemma_schedule(seed: int, max_quarters: int = 12) -> dict[int, Dilemma]:
    """Return {quarter: dilemma}; uses its own random stream so market events are unaffected."""
    rng = random.Random(seed * 7_919 + 104_729)
    quarters = sorted(rng.sample(range(2, max_quarters + 1), min(DILEMMAS_PER_GAME, max_quarters - 1)))
    return dict(zip(quarters, rng.sample(DILEMMAS, len(quarters))))


def describe_effect(effect: Effect) -> str:
    """Plain-language summary of an option's consequences for the UI."""
    parts = []
    if effect.cash:
        parts.append(f"Cash {'+' if effect.cash > 0 else '-'}{money(abs(effect.cash))}")
    if effect.expense:
        parts.append(f"{'Cost' if effect.expense > 0 else 'Savings'} {money(abs(effect.expense))}")
    if effect.customers:
        parts.append(f"{effect.customers:+,} customers")
    if effect.employees:
        parts.append(f"{effect.employees:+d} employees")
    for label, value in (("Quality", effect.quality), ("Brand", effect.brand), ("Morale", effect.morale)):
        if value:
            parts.append(f"{label} {value:+g}")
    if effect.dilution:
        parts.append(f"Founder diluted {effect.dilution:g}%")
    if effect.demand_multiplier != 1:
        parts.append(f"New demand {effect.demand_multiplier - 1:+.0%}")
    if effect.revenue_multiplier != 1:
        parts.append(f"Revenue {effect.revenue_multiplier - 1:+.0%}")
    if effect.variable_cost_delta:
        parts.append(f"Revenue share {effect.variable_cost_delta:.0%}")
    if effect.churn_delta:
        parts.append(f"Churn {effect.churn_delta * 100:+.1f} pts")
    return " · ".join(parts) if parts else "No direct effect"
