"""Board-report content and PDF export service."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path

from PySide6.QtCore import QMarginsF
from PySide6.QtGui import QGuiApplication, QPageLayout, QPageSize, QPdfWriter, QTextDocument

from .engine import money
from .models import GameState


@dataclass(slots=True, frozen=True)
class BoardReport:
    best_quarter: str
    decisions: tuple[str, ...]
    assessment: str


def build_board_report(state: GameState) -> BoardReport:
    best = max(state.history, key=lambda result: result.operating_profit, default=None)
    best_quarter = "No completed quarters" if best is None else f"Q{best.quarter} ({money(best.operating_profit)} operating profit)"
    funding = sum(record.decision.raise_funding for record in state.decision_history)
    total_hires = sum(record.decision.hires for record in state.decision_history)
    total_layoffs = sum(record.decision.layoffs for record in state.decision_history)
    avg_product = (
        sum(record.decision.product for record in state.decision_history) / len(state.decision_history)
        if state.decision_history else 0
    )
    decisions = (
        f"Completed {state.quarter} quarters with {funding} funding round(s).",
        f"Hired {total_hires} and laid off {total_layoffs} employees.",
        f"Average quarterly product investment was {money(avg_product)}.",
    )
    wins = sum(state.objective_progress.values())
    if state.bankrupt:
        assessment = "Growth spending outpaced available capital. Improve runway discipline and stage investments against measurable demand."
    elif wins == 3:
        assessment = "The strategy balanced growth, liquidity, and founder control. Continue converting product strength into efficient retention-led growth."
    elif state.cash > 0:
        assessment = "The company preserved liquidity, but one or more growth or ownership goals remain. Focus capital on the highest-return operating lever."
    else:
        assessment = "The company created operating momentum but finished under cash pressure. Reduce fixed commitments or secure capital earlier."
    return BoardReport(best_quarter, decisions, assessment)


def report_html(state: GameState) -> str:
    report = build_board_report(state)
    objectives = "".join(
        f"<li><b>{'Achieved' if achieved else 'Not achieved'}:</b> {escape(name)}</li>"
        for name, achieved in state.objective_progress.items()
    )
    decisions = "".join(f"<li>{escape(item)}</li>" for item in report.decisions)
    return f"""
    <style>
      body {{ font-family: sans-serif; color: #172033; line-height: 1.45; }}
      h1 {{ color: #123047; font-size: 26px; }} h2 {{ color: #137F78; font-size: 16px; margin-top: 24px; }}
      table {{ width: 100%; border-collapse: collapse; }} td {{ padding: 8px; border-bottom: 1px solid #DDE5EA; }}
    </style>
    <h1>{escape(state.company_name)} - Final Board Report</h1>
    <p>Startup CEO Simulator - End of Q{state.quarter}</p>
    <h2>CEO Score: {state.score()} / 100</h2>
    <table>
      <tr><td>Final valuation</td><td><b>{money(state.valuation)}</b></td></tr>
      <tr><td>Ending cash</td><td><b>{money(state.cash)}</b></td></tr>
      <tr><td>Customers</td><td><b>{state.customers:,}</b></td></tr>
      <tr><td>Founder ownership</td><td><b>{state.founder_ownership:.1f}%</b></td></tr>
      <tr><td>Best-performing quarter</td><td><b>{escape(report.best_quarter)}</b></td></tr>
    </table>
    <h2>Board objectives</h2><ul>{objectives}</ul>
    <h2>Major strategic decisions</h2><ul>{decisions}</ul>
    <h2>Board assessment</h2><p>{escape(report.assessment)}</p>
    """


def export_pdf(path: str | Path, state: GameState) -> None:
    application = QGuiApplication.instance() or QGuiApplication([])
    destination = Path(path)
    if destination.suffix.lower() != ".pdf":
        destination = destination.with_suffix(".pdf")
    writer = QPdfWriter(str(destination))
    writer.setTitle(f"{state.company_name} Final Board Report")
    writer.setCreator("Startup CEO Simulator")
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.Letter))
    writer.setPageMargins(QMarginsF(18, 18, 18, 18), QPageLayout.Unit.Millimeter)
    document = QTextDocument()
    document.setHtml(report_html(state))
    document.print_(writer)
    application.processEvents()
    if not destination.exists() or destination.stat().st_size < 1_000:
        raise OSError("The PDF report could not be created.")
