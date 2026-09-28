"""PySide6 strategy-canvas interface for Startup CEO Simulator."""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QFrame,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
    QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from .engine import Decision, SimulationEngine, money
from .report_service import export_pdf, report_html
from .save_service import SaveFileError, load_game, save_game
from .widgets import EffectRow, KpiCard, LabeledControl, ObjectiveRow


STYLESHEET = """
QWidget { background: #F3F6F8; color: #17283A; font-size: 13px; }
QLabel, QCheckBox { background: transparent; }
QMainWindow { background: #F3F6F8; }
QFrame#header { background: #10283E; }
QFrame#header QLabel { color: white; }
QLabel#brand { font-size: 16px; font-weight: 800; }
QLabel#company { color: #BDCBD6; font-size: 13px; }
QLabel#quarter, QLabel#score { background: #1D3B54; border: 1px solid #31536D; border-radius: 5px; padding: 6px 10px; font-weight: 700; }
QLabel#eyebrow { color: #65778A; font-size: 10px; font-weight: 800; }
QLabel#pageTitle { color: #14293D; font-size: 23px; font-weight: 800; }
QLabel#muted, QLabel#kpiDetail { color: #697B8C; font-size: 11px; }
QFrame#kpiCard, QFrame#canvasCard, QFrame#eventCard { background: white; border: 1px solid #DCE4E9; border-radius: 7px; }
QLabel#kpiLabel { color: #6D7D8D; font-size: 9px; font-weight: 800; }
QLabel#kpiValue { color: #152B3F; font-size: 19px; font-weight: 800; }
QLabel#sectionTitle { color: #173148; font-size: 15px; font-weight: 800; }
QLabel#controlLabel, QLabel#effectLabel { color: #2A4053; font-weight: 650; }
QSpinBox, QLineEdit { background: #F9FBFC; border: 1px solid #C9D5DD; border-radius: 5px; padding: 5px 7px; min-height: 21px; }
QSlider::groove:horizontal { height: 5px; background: #DDE6EB; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #16877F; border-radius: 2px; }
QSlider::handle:horizontal { background: #16877F; width: 15px; margin: -5px 0; border-radius: 7px; }
QFrame#effectRow { background: #F7F9FA; border: 1px solid #E4EAEE; border-radius: 5px; }
QLabel#effectValue { border-radius: 9px; padding: 3px 8px; font-size: 11px; font-weight: 800; }
QLabel#effectValue[tone="positive"] { color: #087269; background: #DDF3EF; }
QLabel#effectValue[tone="negative"] { color: #A33B3B; background: #FBE7E5; }
QLabel#effectValue[tone="neutral"] { color: #52687A; background: #E8EEF2; }
QLabel#canvasArrow { color: #16877F; font-size: 28px; font-weight: 700; }
QPushButton { border: 0; border-radius: 5px; padding: 8px 13px; font-weight: 700; }
QPushButton#primary { color: white; background: #137F78; min-height: 30px; font-size: 14px; }
QPushButton#primary:hover { background: #0E6E68; }
QPushButton#secondary { color: #DDE8EE; background: #1D3B54; border: 1px solid #3B5870; }
QPushButton#secondary:hover { background: #294A64; }
QCheckBox { color: #31485B; spacing: 7px; }
QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid #98AAB7; border-radius: 3px; background: white; }
QCheckBox::indicator:checked { border-color: #137F78; background: #137F78; }
QScrollArea { border: 0; background: transparent; }
QStatusBar { background: #E8EEF2; color: #52687A; }
"""


class WelcomeDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Begin a new simulation")
        self.setMinimumWidth(470)
        layout = QVBoxLayout(self)
        title = QLabel("Take the CEO seat")
        title.setObjectName("pageTitle")
        description = QLabel("Lead a SaaS company for 12 quarters. Balance growth, product strength, people, cash, and founder control.")
        description.setWordWrap(True)
        self.company = QLineEdit("Northstar Labs")
        goals = QLabel("<b>BOARD OBJECTIVES</b><br><br>○ Finish with positive cash<br>○ Reach at least 3,000 customers<br>○ Retain at least 80% founder ownership")
        goals.setStyleSheet("background: #F2F7F7; border: 1px solid #D5E7E5; border-radius: 6px; padding: 12px;")
        note = QLabel("All simulation data remains on this computer. No account or network connection is used.")
        note.setObjectName("muted")
        note.setWordWrap(True)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Launch company")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        for widget in (title, description, QLabel("Company name"), self.company, goals, note):
            layout.addWidget(widget)
        layout.addWidget(buttons)


class FinalReportDialog(QDialog):
    def __init__(self, state, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = state
        self.setWindowTitle("Final Board Report")
        self.resize(720, 700)
        layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QLabel(report_html(state))
        content.setWordWrap(True)
        content.setTextFormat(Qt.TextFormat.RichText)
        content.setAlignment(Qt.AlignmentFlag.AlignTop)
        content.setMargin(18)
        scroll.setWidget(content)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        export_button = buttons.addButton("Export professional PDF", QDialogButtonBox.ButtonRole.ActionRole)
        export_button.clicked.connect(self._export)
        buttons.rejected.connect(self.reject)
        layout.addWidget(scroll, 1)
        layout.addWidget(buttons)

    def _export(self) -> None:
        suggested = f"{self.state.company_name.replace(' ', '-')}-board-report.pdf"
        path, _ = QFileDialog.getSaveFileName(self, "Export board report", suggested, "PDF files (*.pdf)")
        if not path:
            return
        try:
            export_pdf(path, self.state)
        except OSError as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        QMessageBox.information(self, "Report exported", "The final board report was exported successfully.")


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.engine = SimulationEngine()
        self.setWindowTitle("Startup CEO Simulator")
        self.resize(1380, 900)
        self.setMinimumSize(1080, 760)
        self._build_ui()
        self._connect_controls()
        self._update_dashboard()

    def _build_ui(self) -> None:
        root = QWidget()
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._build_header())
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        page = QVBoxLayout(body)
        page.setContentsMargins(24, 18, 24, 20)
        page.setSpacing(12)
        eyebrow = QLabel("INTERACTIVE STRATEGIC CASE STUDY")
        eyebrow.setObjectName("eyebrow")
        title = QLabel("Strategy Canvas")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Set the operating plan, review directional estimates, and commit one quarter at a time.")
        subtitle.setObjectName("muted")
        page.addWidget(eyebrow)
        page.addWidget(title)
        page.addWidget(subtitle)
        page.addLayout(self._build_kpis())
        page.addLayout(self._build_canvas(), 1)
        page.addWidget(self._build_event_panel())
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)
        self.setCentralWidget(root)
        self.statusBar().showMessage("Local-only simulation · No network activity")

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("header")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(22, 10, 22, 10)
        brand = QLabel("◆  STARTUP CEO SIMULATOR")
        brand.setObjectName("brand")
        self.company_label = QLabel("Northstar Labs")
        self.company_label.setObjectName("company")
        self.quarter_label = QLabel("QUARTER 0 / 12")
        self.quarter_label.setObjectName("quarter")
        self.score_label = QLabel("CEO SCORE  0")
        self.score_label.setObjectName("score")
        buttons = []
        for text, slot in (("New", self._new_simulation), ("Save", self._save), ("Open", self._open)):
            button = QPushButton(text)
            button.setObjectName("secondary")
            button.clicked.connect(slot)
            buttons.append(button)
        layout.addWidget(brand)
        layout.addWidget(self.company_label)
        layout.addStretch()
        layout.addWidget(self.quarter_label)
        layout.addWidget(self.score_label)
        for button in buttons:
            layout.addWidget(button)
        return header

    def _build_kpis(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(9)
        self.cards = {name: KpiCard(name) for name in ("Cash", "Revenue", "Customers", "Valuation", "Ownership", "Runway")}
        for card in self.cards.values():
            layout.addWidget(card)
        return layout

    def _build_canvas(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(12)
        choices = QFrame()
        choices.setObjectName("canvasCard")
        choices_layout = QVBoxLayout(choices)
        choices_layout.setContentsMargins(18, 15, 18, 15)
        choices_layout.setSpacing(9)
        choices_title = QLabel("Management Choices")
        choices_title.setObjectName("sectionTitle")
        choices_note = QLabel("Controllable inputs for the upcoming quarter")
        choices_note.setObjectName("muted")
        self.price = LabeledControl("Monthly subscription price", 39, 149, 79, "$")
        self.marketing = LabeledControl("Marketing investment", 0, 250, 90, "$", "K")
        self.product = LabeledControl("Product investment", 0, 200, 80, "$", "K")
        self.hires = LabeledControl("Employees to hire", 0, 8, 1)
        self.layoffs = LabeledControl("Employees to lay off", 0, 5, 0)
        self.funding = QCheckBox("Raise a funding round for cash and accept dilution")
        choices_layout.addWidget(choices_title)
        choices_layout.addWidget(choices_note)
        for control in (self.price, self.marketing, self.product, self.hires, self.layoffs):
            choices_layout.addWidget(control)
        choices_layout.addWidget(self.funding)
        choices_layout.addStretch()

        connector = QWidget()
        connector.setFixedWidth(105)
        connector_layout = QVBoxLayout(connector)
        connector_layout.addStretch()
        for text, name in (("MANAGEMENT\nCHOICES", "eyebrow"), ("→", "canvasArrow"), ("BUSINESS\nEFFECTS", "eyebrow")):
            label = QLabel(text)
            label.setObjectName(name)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            connector_layout.addWidget(label)
        connector_layout.addStretch()

        effects = QFrame()
        effects.setObjectName("canvasCard")
        effects_layout = QVBoxLayout(effects)
        effects_layout.setContentsMargins(18, 15, 18, 15)
        effects_layout.setSpacing(8)
        effects_title = QLabel("Expected Business Effects")
        effects_title.setObjectName("sectionTitle")
        estimate_note = QLabel("Directional estimates—not guaranteed outcomes")
        estimate_note.setObjectName("muted")
        self.effects = {name: EffectRow(name) for name in ("Customer growth", "Operating margin", "Product quality", "Runway resilience", "Founder control")}
        effects_layout.addWidget(effects_title)
        effects_layout.addWidget(estimate_note)
        for row in self.effects.values():
            effects_layout.addWidget(row)
        self.health_label = QLabel()
        self.health_label.setObjectName("muted")
        self.health_label.setWordWrap(True)
        effects_layout.addWidget(self.health_label)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #DCE4E9;")
        effects_layout.addWidget(line)
        objective_title = QLabel("Board Objectives")
        objective_title.setObjectName("sectionTitle")
        effects_layout.addWidget(objective_title)
        self.objectives = {name: ObjectiveRow(name) for name in self.engine.state.objective_progress}
        for row in self.objectives.values():
            effects_layout.addWidget(row)
        effects_layout.addStretch()
        choices.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        effects.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(choices, 5)
        layout.addWidget(connector)
        layout.addWidget(effects, 5)
        return layout

    def _build_event_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("eventCard")
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(18, 12, 18, 12)
        text = QVBoxLayout()
        eyebrow = QLabel("UPCOMING MARKET CONDITION")
        eyebrow.setObjectName("eyebrow")
        self.event_title = QLabel()
        self.event_title.setObjectName("sectionTitle")
        self.event_text = QLabel()
        self.event_text.setObjectName("muted")
        self.event_text.setWordWrap(True)
        self.outcome_text = QLabel("Commit a strategy to see the quarter's result.")
        self.outcome_text.setWordWrap(True)
        for widget in (eyebrow, self.event_title, self.event_text, self.outcome_text):
            text.addWidget(widget)
        self.advance_button = QPushButton("Commit Strategy and Advance Quarter  →")
        self.advance_button.setObjectName("primary")
        self.advance_button.setMinimumWidth(330)
        self.advance_button.clicked.connect(self._advance)
        layout.addLayout(text, 1)
        layout.addWidget(self.advance_button)
        return panel

    def _connect_controls(self) -> None:
        for control in (self.price, self.marketing, self.product, self.hires, self.layoffs):
            control.changed.connect(self._update_previews)
        self.hires.changed.connect(self._enforce_hiring_choice)
        self.layoffs.changed.connect(self._enforce_layoff_choice)
        self.funding.toggled.connect(self._update_previews)

    def _enforce_hiring_choice(self) -> None:
        if self.hires.value() and self.layoffs.value():
            self.layoffs.set_value(0)

    def _enforce_layoff_choice(self) -> None:
        if self.layoffs.value() and self.hires.value():
            self.hires.set_value(0)

    def _decision(self) -> Decision:
        return Decision(self.price.value(), self.marketing.value() * 1_000, self.product.value() * 1_000, self.hires.value(), self.layoffs.value(), self.funding.isChecked())

    def _runway(self) -> float:
        return max(0, self.engine.state.cash) / max(1, self.engine.preview_cost(self._decision())) * 3

    def _update_previews(self) -> None:
        try:
            previews = self.engine.preview_effects(self._decision())
        except ValueError:
            return
        for name, value in previews.items():
            self.effects[name].set_value(value)
        self.cards["Runway"].set_value(f"{self._runway():.1f} mo", "Estimated before revenue")

    def _update_dashboard(self) -> None:
        state = self.engine.state
        self.company_label.setText(state.company_name)
        self.quarter_label.setText(f"QUARTER {state.quarter} / {state.max_quarters}")
        self.score_label.setText(f"CEO SCORE  {state.score()}")
        self.cards["Cash"].set_value(money(state.cash), "Available liquidity")
        self.cards["Revenue"].set_value(money(state.revenue), "Pre-launch plan" if not state.history else f"Op. profit {money(state.operating_profit)}")
        self.cards["Customers"].set_value(f"{state.customers:,}", "Starting customer base" if not state.history else f"{state.last_growth:+.1%} quarterly growth")
        self.cards["Valuation"].set_value(money(state.valuation), "Modelled enterprise value")
        self.cards["Ownership"].set_value(f"{state.founder_ownership:.1f}%", f"{state.funding_rounds} funding round(s)")
        self.health_label.setText(f"CURRENT COMPANY HEALTH\nProduct quality {state.product_quality:.0f}/100  ·  Employee morale {state.morale:.0f}/100  ·  {state.employees} employees")
        for name, achieved in state.objective_progress.items():
            self.objectives[name].set_achieved(achieved)
        upcoming = self.engine.upcoming_event()
        self.event_title.setText(f"Q{state.quarter + 1}: {upcoming.name}" if not state.complete else "Simulation complete")
        self.event_text.setText(upcoming.description if not state.complete else "Review the final board report for the complete assessment.")
        self.advance_button.setEnabled(not state.complete)
        self.advance_button.setText("Simulation Complete" if state.complete else "Commit Strategy and Advance Quarter  →")
        self._update_previews()

    def _advance(self) -> None:
        try:
            result = self.engine.advance(self._decision())
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Strategy cannot be committed", str(exc))
            return
        self.outcome_text.setText(f"Q{result.quarter} result — {result.narrative}")
        self.funding.setChecked(False)
        self._update_dashboard()
        if self.engine.state.complete:
            FinalReportDialog(self.engine.state, self).exec()

    def _new_simulation(self) -> None:
        if self.engine.state.quarter:
            answer = QMessageBox.question(self, "Start a new simulation?", "The current unsaved progress will be cleared.")
            if answer != QMessageBox.StandardButton.Yes:
                return
        dialog = WelcomeDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.engine.reset(dialog.company.text().strip() or "Northstar Labs")
        self.outcome_text.setText("Commit a strategy to see the quarter's result.")
        self._update_dashboard()

    def _save(self) -> None:
        suggested = f"{self.engine.state.company_name.replace(' ', '-')}.startup-ceo.json"
        path, _ = QFileDialog.getSaveFileName(self, "Save simulation", suggested, "Startup CEO saves (*.json)")
        if not path:
            return
        try:
            save_game(path, self.engine.state, self.engine.seed)
        except SaveFileError as exc:
            QMessageBox.critical(self, "Save failed", str(exc))
            return
        self.statusBar().showMessage(f"Simulation saved locally: {path}", 6000)

    def _open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open simulation", "", "Startup CEO saves (*.json);;JSON files (*.json)")
        if not path:
            return
        try:
            state, seed = load_game(path)
        except SaveFileError as exc:
            QMessageBox.warning(self, "Could not open simulation", str(exc))
            return
        self.engine = SimulationEngine.from_state(state, seed)
        if state.decision_history:
            last = state.decision_history[-1].decision
            self.price.set_value(last.price)
            self.marketing.set_value(last.marketing // 1_000)
            self.product.set_value(last.product // 1_000)
            self.hires.set_value(0)
            self.layoffs.set_value(0)
        self.funding.setChecked(False)
        self.outcome_text.setText("Saved simulation restored. Review the next market condition and set your strategy.")
        self._update_dashboard()
        self.statusBar().showMessage(f"Simulation opened: {path}", 6000)
        if state.complete:
            FinalReportDialog(state, self).exec()


def run() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Startup CEO Simulator")
    app.setFont(QFont())
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)
    window = MainWindow()
    window.show()
    return app.exec()
