"""Display formatting shared by the engine, reports and interface."""

from __future__ import annotations


def money(value: float) -> str:
    sign = "-" if value < 0 else ""
    value = abs(value)
    # Pick the unit after rounding so 999,600 reads "$1.00M", not "$1000K".
    if value >= 999_500:
        return f"{sign}${value / 1_000_000:.2f}M"
    if value >= 999.5:
        return f"{sign}${value / 1_000:.0f}K"
    return f"{sign}${value:,.0f}"
