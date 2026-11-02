"""Capture a deterministic dashboard screenshot for visual QA."""

from __future__ import annotations

import os
from pathlib import Path
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from startup_ceo.app import MainWindow, STYLESHEET
from startup_ceo.engine import Decision


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setFont(QFont())
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)
    window = MainWindow()
    window.resize(1440, 940)
    latest_result = None
    # Stop before Q4 so the preview shows the board decision scheduled for scenario 2027.
    for quarter in range(3):
        latest_result = window.engine.advance(
            Decision(
                price=79 + quarter * 3,
                marketing=95_000,
                product=85_000,
                hires=1 if quarter < 2 else 0,
                raise_funding=quarter == 2,
            )
        )
    window._update_dashboard()
    if latest_result is not None:
        window.outcome_text.setText(f"Q{latest_result.quarter} result — {latest_result.narrative}")
    window.show()
    app.processEvents()
    output = Path(__file__).resolve().parents[1] / "work" / "dashboard-preview.png"
    output.parent.mkdir(exist_ok=True)
    if not window.grab().save(str(output)):
        raise RuntimeError("Could not save screenshot")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
