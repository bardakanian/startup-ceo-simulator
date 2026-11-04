"""Board-report content and PDF export service."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
import os
from pathlib import Path
import tempfile

from PySide6.QtCore import QMarginsF
from PySide6.QtGui import QGuiApplication, QPageLayout, QPageSize, QPdfWriter, QTextDocument

from .formatting import money
from .models import GameState


@dataclass(slots=True, frozen=True)
class BoardReport:
    best_quarter: str
    decisions: tuple[str, ...]
    assessment: str
    board_decisions: tuple[str, ...] = ()


def build_board_report(state: GameState) -> BoardReport:
    best = max(state.history, key=lambda result: result.operating_profit, default=None)
    best_quarter = "No completed quarters" if best is None else f"Q{best.quarter} ({money(best.operating_profit)} operating profit)"
    funding = sum(record.decision.raise_funding for record in state.decision_history)
    total_hires = sum(record.decision.hires for record in state.decision_history)
    total_layoffs = sum(record.decision.layoffs for record in state.decision_history)
    acquired = sum(record.acquired_employees for record in state.decision_history)
    avg_product = (
        sum(record.decision.product for record in state.decision_history) / len(state.decision_history)
        if state.decision_history else 0
    )
    decisions = (
        f"Completed {state.quarter} quarters with {funding} funding round(s).",
        f"Hired {total_hires} and laid off {total_layoffs} employees"
        + (f", and added {acquired} through acquisitions." if acquired else "."),
        f"Average quarterly product investment was {money(avg_product)}.",
    )
    peak_load = max((result.support_load for result in state.history), default=0)
    if peak_load > 1:
        decisions += (f"Support peaked at {peak_load:.0%} of team capacity, which raised churn.",)
    wins = sum(state.objective_progress.values())
    if state.bankrupt:
        assessment = "Growth spending outpaced available capital. Improve runway discipline and stage investments against measurable demand."
    elif wins == 3:
        assessment = "The strategy balanced growth, liquidity, and founder control. Continue converting product strength into efficient retention-led growth."
    elif state.cash > 0:
        assessment = "The company preserved liquidity, but one or more growth or ownership goals remain. Focus capital on the highest-return operating lever."
    else:
        assessment = "The company created operating momentum but finished under cash pressure. Reduce fixed commitments or secure capital earlier."
    board_decisions = tuple(
        f"Q{record.quarter} - {record.dilemma}: {record.response}"
        for record in state.decision_history if record.dilemma
    )
    return BoardReport(best_quarter, decisions, assessment, board_decisions)


def report_html(state: GameState) -> str:
    report = build_board_report(state)
    objectives = "".join(
        f"<li><b>{'Achieved' if achieved else 'Not achieved'}:</b> {escape(name)}</li>"
        for name, achieved in state.objective_progress.items()
    )
    decisions = "".join(f"<li>{escape(item)}</li>" for item in report.decisions)
    board_decisions = "".join(f"<li>{escape(item)}</li>" for item in report.board_decisions) or "<li>No board dilemmas were reached.</li>"
    breakdown = "".join(
        f"<tr><td>{escape(name)}</td><td align='right'>{points:.1f}</td></tr>"
        for name, points in state.score_breakdown().items()
    )
    quarters = "".join(
        f"<tr><td>Q{result.quarter}</td><td>{escape(result.event.name)}</td><td align='right'>{money(result.revenue)}</td>"
        f"<td align='right'>{money(result.operating_profit)}</td><td align='right'>{result.customers:,}</td>"
        f"<td align='right'>{money(result.ending_cash)}</td></tr>"
        for result in state.history
    )
    record = state.decision_history
    choices = "".join(
        f"<tr><td>Q{item.quarter}</td><td align='right'>${item.decision.price}</td><td align='right'>{money(item.decision.marketing)}</td>"
        f"<td align='right'>{money(item.decision.product)}</td><td align='right'>{item.decision.hires - item.decision.layoffs + item.acquired_employees:+d}</td>"
        f"<td align='center'>{'Yes' if item.decision.raise_funding else ''}</td></tr>"
        for item in record
    )
    return f"""
    <style>
      body {{ font-family: sans-serif; color: #172033; line-height: 1.45; }}
      h1 {{ color: #123047; font-size: 26px; }} h2 {{ color: #137F78; font-size: 16px; margin-top: 24px; }}
      table {{ width: 100%; border-collapse: collapse; }} td {{ padding: 8px; border-bottom: 1px solid #DDE5EA; }}
      th {{ padding: 6px 8px; text-align: left; color: #52687A; border-bottom: 1px solid #B9C7D1; }}
      table.compact td {{ padding: 4px 8px; }}
    </style>
    <h1>{escape(state.company_name)} - Final Board Report</h1>
    <p>Startup CEO Simulator - End of Q{state.quarter}{' (company failed)' if state.bankrupt else ''}</p>
    <h2>CEO Score: {state.score()} / 100</h2>
    <table>
      <tr><td>Final valuation</td><td><b>{money(state.valuation)}</b></td></tr>
      <tr><td>Ending cash</td><td><b>{money(state.cash)}</b></td></tr>
      <tr><td>Customers</td><td><b>{state.customers:,}</b></td></tr>
      <tr><td>Founder ownership</td><td><b>{state.founder_ownership:.1f}%</b></td></tr>
      <tr><td>Founder stake value</td><td><b>{money(state.founder_stake)}</b></td></tr>
      <tr><td>Best-performing quarter</td><td><b>{escape(report.best_quarter)}</b></td></tr>
    </table>
    <h2>Board objectives</h2><ul>{objectives}</ul>
    <h2>Major strategic decisions</h2><ul>{decisions}</ul>
    <h2>Board dilemmas</h2><ul>{board_decisions}</ul>
    <h2>Board assessment</h2><p>{escape(report.assessment)}</p>
    <h2>Score breakdown</h2>
    <table class="compact">{breakdown}<tr><td><b>CEO score</b></td><td align='right'><b>{state.score()}</b></td></tr></table>
    <h2>Quarter-by-quarter results</h2>
    <table class="compact"><tr><th>Quarter</th><th>Market</th><th>Revenue</th><th>Op. profit</th><th>Customers</th><th>Cash</th></tr>{quarters}</table>
    <h2>Decision log</h2>
    <table class="compact"><tr><th>Quarter</th><th>Price</th><th>Marketing</th><th>Product</th><th>Headcount</th><th>Funding</th></tr>{choices}</table>
    """


def export_pdf(path: str | Path, state: GameState) -> None:
    application = QGuiApplication.instance() or QGuiApplication([])
    destination = Path(path)
    if destination.suffix.lower() != ".pdf":
        destination = Path(f"{destination}.pdf")
    if destination.exists() and not os.access(destination, os.W_OK):
        raise OSError(f"{destination.name} is read-only, so it can't be replaced.")
    # Write to a temporary file first so a failed export can't leave an old or partial report looking new.
    handle, temporary = tempfile.mkstemp(suffix=".pdf", dir=destination.parent)
    os.close(handle)
    writer = QPdfWriter(temporary)
    writer.setTitle(f"{state.company_name} Final Board Report")
    writer.setCreator("Startup CEO Simulator")
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.Letter))
    writer.setPageMargins(QMarginsF(18, 18, 18, 18), QPageLayout.Unit.Millimeter)
    document = QTextDocument()
    document.setHtml(report_html(state))
    document.print_(writer)
    del writer
    application.processEvents()
    if os.path.getsize(temporary) < 1_000:
        os.remove(temporary)
        raise OSError("The PDF report could not be created.")
    # mkstemp makes owner-only files; keep the permissions an ordinary export (or the replaced file) would have.
    os.chmod(temporary, destination.stat().st_mode & 0o777 if destination.exists() else 0o644)
    os.replace(temporary, destination)
