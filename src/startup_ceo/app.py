"""PySide6 strategy-canvas interface for Startup CEO Simulator."""

from __future__ import annotations

import math
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFrame,
    QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton,
    QScrollArea, QSizePolicy, QSpinBox, QVBoxLayout, QWidget,
)

from .dilemmas import describe_effect
from .engine import MIN_EMPLOYEES, Decision, SimulationEngine
from .formatting import money
from .models import DilemmaOption, GameState
from .report_service import export_pdf, report_html
from .save_service import SaveFileError, load_game, save_game
from .widgets import EffectRow, KpiCard, LabeledControl, ObjectiveRow, OptionCard, TrendChart


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
QLabel#alert { color: #8A2F2F; background: #FBE7E5; border: 1px solid #F1C9C5; border-radius: 5px; padding: 6px 9px; font-weight: 650; }
QSpinBox, QLineEdit, QComboBox { background: #F9FBFC; border: 1px solid #C9D5DD; border-radius: 5px; padding: 5px 7px; min-height: 21px; }
QSlider::groove:horizontal { height: 5px; background: #DDE6EB; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #16877F; border-radius: 2px; }
QSlider::handle:horizontal { background: #16877F; width: 15px; margin: -5px 0; border-radius: 7px; }
QSlider::sub-page:horizontal:disabled, QSlider::handle:horizontal:disabled { background: #A9B7C1; }
QLabel#controlLabel:disabled, QCheckBox:disabled, QSpinBox:disabled { color: #9AA8B4; }
QFrame#effectRow { background: #F7F9FA; border: 1px solid #E4EAEE; border-radius: 5px; }
QLabel#effectValue { border-radius: 9px; padding: 3px 8px; font-size: 11px; font-weight: 800; }
QLabel#effectValue[tone="positive"] { color: #087269; background: #DDF3EF; }
QLabel#effectValue[tone="negative"] { color: #A33B3B; background: #FBE7E5; }
QLabel#effectValue[tone="warning"] { color: #8A5A00; background: #FCEFD2; }
QLabel#effectValue[tone="neutral"] { color: #52687A; background: #E8EEF2; }
QLabel#canvasArrow { color: #16877F; font-size: 28px; font-weight: 700; }
QPushButton { border: 0; border-radius: 5px; padding: 8px 13px; font-weight: 700; }
QPushButton#primary { color: white; background: #137F78; min-height: 30px; font-size: 14px; }
QPushButton#primary:hover { background: #0E6E68; }
QPushButton#primary:disabled { background: #9DB5B3; }
QPushButton#secondary { color: #DDE8EE; background: #1D3B54; border: 1px solid #3B5870; }
QPushButton#secondary:hover { background: #294A64; }
QPushButton#report { color: #137F78; background: #E3F2F0; border: 1px solid #BFDFDB; }
QPushButton#report:hover { background: #D3EBE8; }
QCheckBox { color: #31485B; spacing: 7px; }
QCheckBox::indicator { width: 15px; height: 15px; border: 1px solid #98AAB7; border-radius: 3px; background: white; }
QCheckBox::indicator:checked { border-color: #137F78; background: #137F78; }
QFrame#dilemmaCard { background: #FFF8EC; border: 1px solid #EED6A8; border-radius: 7px; }
QLabel#dilemmaEyebrow { color: #9A6400; font-size: 10px; font-weight: 800; }
QFrame#optionCard { background: white; border: 1px solid #E3D5BC; border-radius: 6px; }
QFrame#optionCard[selected="true"] { border: 2px solid #137F78; background: #F2FAF9; }
QRadioButton { background: transparent; color: #17283A; font-weight: 700; spacing: 7px; }
QRadioButton:disabled { color: #9AA8B4; }
QRadioButton::indicator { width: 14px; height: 14px; border: 1px solid #98AAB7; border-radius: 8px; background: white; }
QRadioButton::indicator:checked { border: 4px solid #137F78; width: 8px; height: 8px; }
QScrollArea { border: 0; background: transparent; }
QStatusBar { background: #E8EEF2; color: #52687A; }
"""

GUIDE_HTML = """
<h2>How the simulation works</h2>
<p>You run the company for 12 quarters. Each quarter you set a plan, see the market condition that is coming,
and commit. Results come from a transparent, seeded rules engine, so the same scenario code and decisions
always produce the same outcome.</p>
<h3>Your levers</h3>
<ul>
<li><b>Price</b> raises revenue per customer but slows sign-ups. A stronger product makes buyers less price-sensitive,
and prices above $99 add churn unless quality is high.</li>
<li><b>Marketing</b> brings leads with diminishing returns, and it gets weaker as you win more of the market.</li>
<li><b>Product investment</b> lifts quality with diminishing returns. Quality improves conversion and retention and earns pricing power.</li>
<li><b>Hiring</b> adds support capacity (300 customers per employee) but adds payroll. When customers outgrow the team,
churn rises and quality and morale fall. The team can't shrink below three people. Hiring and layoffs are one-time actions and reset after each quarter.</li>
<li><b>Funding</b> adds cash now and dilutes you more with each round.</li>
</ul>
<h3>Board decisions</h3>
<p>In four quarters of every game the board brings you a dilemma, such as an acquisition offer, a security flaw or a price war.
You must pick a response before committing that quarter. Each option shows its direct consequences (a cash cost can be
covered by a funding round raised the same quarter); they take effect
at the start of the quarter, alongside your regular plan. Teams with the same scenario code face the same dilemmas.</p>
<h3>Scoring</h3>
<p>The CEO score (0 to 100) rewards the value of the founder's stake (valuation × ownership), compound customer growth,
cash on hand, product quality and morale, the three board objectives, and finishing profitable.
The company fails if cash falls below -$250K.</p>
<p><b>Shortcuts</b> (⌘ on macOS)<b>:</b> Ctrl+Enter commits the quarter, Ctrl+N starts a new game, Ctrl+S saves, Ctrl+O opens.</p>
"""

CHART_METRICS = {
    "Cash": ("ending_cash", money),
    "Revenue": ("revenue", money),
    "Operating profit": ("operating_profit", money),
    "Customers": ("customers", lambda value: f"{value:,.0f}"),
    "Valuation": ("valuation", money),
}


class WelcomeDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, seed: int = 2027) -> None:
        super().__init__(parent)
        self.setWindowTitle("Begin a new simulation")
        self.setMinimumWidth(470)
        layout = QVBoxLayout(self)
        title = QLabel("Take the CEO seat")
        title.setObjectName("pageTitle")
        description = QLabel("Lead a SaaS company for 12 quarters. Balance growth, product strength, people, cash, and founder control.")
        description.setWordWrap(True)
        self.company = QLineEdit("Northstar Labs")
        self.company.setMaxLength(80)
        self.seed = QSpinBox()
        self.seed.setRange(1, 999_999)
        self.seed.setValue(seed)
        seed_note = QLabel("Teams that use the same scenario code face the same market events, so results can be compared fairly.")
        seed_note.setObjectName("muted")
        seed_note.setWordWrap(True)
        goals = QLabel("<b>BOARD OBJECTIVES</b><br><br>○ Finish with positive cash<br>○ Reach at least 3,000 customers<br>○ Retain at least 80% founder ownership")
        goals.setStyleSheet("background: #F2F7F7; border: 1px solid #D5E7E5; border-radius: 6px; padding: 12px;")
        note = QLabel("All simulation data remains on this computer. No account or network connection is used.")
        note.setObjectName("muted")
        note.setWordWrap(True)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Launch company")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        for widget in (title, description, QLabel("Company name"), self.company, QLabel("Scenario code"), self.seed, seed_note, goals, note):
            layout.addWidget(widget)
        layout.addWidget(buttons)


class GuideDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("How it works")
        self.resize(620, 560)
        layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QLabel(GUIDE_HTML)
        content.setWordWrap(True)
        content.setTextFormat(Qt.TextFormat.RichText)
        content.setAlignment(Qt.AlignmentFlag.AlignTop)
        content.setMargin(14)
        scroll.setWidget(content)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(scroll, 1)
        layout.addWidget(buttons)


class FinalReportDialog(QDialog):
    def __init__(self, state, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = state
        self.setWindowTitle("Final Board Report")
        self.resize(760, 760)
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
        self.unsaved = False
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
        page.setContentsMargins(24, 16, 24, 20)
        page.setSpacing(12)
        title_row = QHBoxLayout()
        title = QLabel("Strategy Canvas")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Set the operating plan, review directional estimates, and commit one quarter at a time.")
        subtitle.setObjectName("muted")
        title_row.addWidget(title)
        title_row.addSpacing(12)
        title_row.addWidget(subtitle, 1, Qt.AlignmentFlag.AlignBottom)
        page.addLayout(title_row)
        page.addLayout(self._build_kpis())
        page.addWidget(self._build_dilemma_panel())
        page.addLayout(self._build_canvas())
        page.addWidget(self._build_event_panel())
        page.addLayout(self._build_history())
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
        for text, slot, tip in (
            ("Guide", self._show_guide, "How the simulation and score work"),
            ("New", self._new_simulation, "Start a new simulation (Ctrl+N)"),
            ("Save", self._save, "Save this simulation to a local file (Ctrl+S)"),
            ("Open", self._open, "Open a saved simulation (Ctrl+O)"),
        ):
            button = QPushButton(text)
            button.setObjectName("secondary")
            button.setToolTip(tip)
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
        choices_layout.setSpacing(10)
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
        self.price.setToolTip("Higher prices raise revenue per customer but slow sign-ups; product quality softens the effect.")
        self.marketing.setToolTip("Brings leads with diminishing returns, weaker as the market saturates.")
        self.product.setToolTip("Raises product quality with diminishing returns.")
        self.hires.setToolTip("Each employee supports about 300 customers and costs $27K per quarter plus $8K to onboard.")
        self.layoffs.setToolTip("Saves payroll but costs $18K severance per person and hurts morale.")
        choices_layout.addWidget(choices_title)
        choices_layout.addWidget(choices_note)
        for control in (self.price, self.marketing, self.product, self.hires, self.layoffs):
            choices_layout.addWidget(control)
        choices_layout.addWidget(self.funding)
        self.funding_note = QLabel()
        self.funding_note.setObjectName("muted")
        self.funding_note.setWordWrap(True)
        choices_layout.addWidget(self.funding_note)
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
        effects_layout.setSpacing(7)
        effects_title = QLabel("Expected Business Effects")
        effects_title.setObjectName("sectionTitle")
        estimate_note = QLabel("Directional estimates—not guaranteed outcomes")
        estimate_note.setObjectName("muted")
        self.effects = {
            name: EffectRow(name)
            for name in ("Customer growth", "Operating margin", "Product quality", "Service capacity", "Runway resilience", "Founder control")
        }
        effects_layout.addWidget(effects_title)
        effects_layout.addWidget(estimate_note)
        grid = QGridLayout()
        grid.setSpacing(7)
        for index, row in enumerate(self.effects.values()):
            grid.addWidget(row, index // 2, index % 2)
        effects_layout.addLayout(grid)
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
        self.choices = choices
        choices.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        effects.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(choices, 5)
        layout.addWidget(connector)
        layout.addWidget(effects, 5)
        return layout

    def _build_dilemma_panel(self) -> QFrame:
        self.dilemma_panel = QFrame()
        self.dilemma_panel.setObjectName("dilemmaCard")
        layout = QVBoxLayout(self.dilemma_panel)
        layout.setContentsMargins(18, 12, 18, 14)
        layout.setSpacing(5)
        self.dilemma_eyebrow = QLabel()
        self.dilemma_eyebrow.setObjectName("dilemmaEyebrow")
        self.dilemma_title = QLabel()
        self.dilemma_title.setObjectName("sectionTitle")
        self.dilemma_text = QLabel()
        self.dilemma_text.setObjectName("muted")
        self.dilemma_text.setWordWrap(True)
        self.dilemma_options = QHBoxLayout()
        self.dilemma_options.setSpacing(10)
        for widget in (self.dilemma_eyebrow, self.dilemma_title, self.dilemma_text):
            layout.addWidget(widget)
        layout.addSpacing(4)
        layout.addLayout(self.dilemma_options)
        self.dilemma_group = QButtonGroup(self)
        self.dilemma_group.buttonToggled.connect(self._dilemma_toggled)
        self.dilemma_cards: list[OptionCard] = []
        self.dilemma_choices: list[DilemmaOption] = []
        self.shown_dilemma: tuple[int, str] | None = None
        self.dilemma_panel.hide()
        return self.dilemma_panel

    def _refresh_dilemma(self) -> None:
        state = self.engine.state
        dilemma = self.engine.upcoming_dilemma()
        key = (state.quarter, dilemma.key) if dilemma else None
        if key == self.shown_dilemma:
            return
        self.shown_dilemma = key
        for button in self.dilemma_group.buttons():
            self.dilemma_group.removeButton(button)
        for card in self.dilemma_cards:
            self.dilemma_options.removeWidget(card)
            card.setParent(None)
            card.deleteLater()
        self.dilemma_cards = []
        self.dilemma_choices = []
        self.dilemma_panel.setVisible(dilemma is not None)
        if dilemma is None:
            return
        self.dilemma_eyebrow.setText(f"BOARD DECISION REQUIRED FOR Q{state.quarter + 1}")
        self.dilemma_title.setText(dilemma.title)
        self.dilemma_text.setText(dilemma.description)
        for option in dilemma.options:
            card = OptionCard(option.label, option.key, describe_effect(option.effect))
            self.dilemma_group.addButton(card.button)
            self.dilemma_options.addWidget(card, 1)
            self.dilemma_cards.append(card)
            self.dilemma_choices.append(option)

    def _update_dilemma_availability(self) -> None:
        """Re-check each option's cash need, since ticking the funding round can make one affordable."""
        raising = self.funding.isChecked()
        for card, option in zip(self.dilemma_cards, self.dilemma_choices):
            problem = self.engine.check_dilemma_option(option, raising)
            card.set_problem(problem)
            if problem and card.button.isChecked():
                self.dilemma_group.setExclusive(False)
                card.button.setChecked(False)
                self.dilemma_group.setExclusive(True)
                card.set_selected(False)

    def _dilemma_toggled(self) -> None:
        for card in self.dilemma_cards:
            card.set_selected(card.button.isChecked())
        self._update_previews()

    def _dilemma_choice(self) -> str:
        button = self.dilemma_group.checkedButton()
        return str(button.property("key")) if button else ""

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
        self.alert = QLabel()
        self.alert.setObjectName("alert")
        self.alert.setWordWrap(True)
        self.alert.hide()
        for widget in (eyebrow, self.event_title, self.event_text, self.outcome_text, self.alert):
            text.addWidget(widget)
        actions = QVBoxLayout()
        self.advance_button = QPushButton("Commit Strategy and Advance Quarter  →")
        self.advance_button.setObjectName("primary")
        self.advance_button.setMinimumWidth(330)
        self.advance_button.setToolTip("Ctrl+Enter")
        self.advance_button.clicked.connect(self._advance)
        self.report_button = QPushButton("View Final Board Report")
        self.report_button.setObjectName("report")
        self.report_button.clicked.connect(self._show_report)
        self.report_button.hide()
        actions.addStretch()
        actions.addWidget(self.advance_button)
        actions.addWidget(self.report_button)
        actions.addStretch()
        layout.addLayout(text, 1)
        layout.addLayout(actions)
        return panel

    def _build_history(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(12)
        trend = QFrame()
        trend.setObjectName("canvasCard")
        trend_layout = QVBoxLayout(trend)
        trend_layout.setContentsMargins(18, 14, 18, 12)
        heading = QHBoxLayout()
        trend_title = QLabel("Performance Trend")
        trend_title.setObjectName("sectionTitle")
        self.chart_metric = QComboBox()
        self.chart_metric.addItems(CHART_METRICS)
        self.chart_metric.currentTextChanged.connect(self._update_chart)
        heading.addWidget(trend_title)
        heading.addStretch()
        heading.addWidget(self.chart_metric)
        self.chart = TrendChart()
        trend_layout.addLayout(heading)
        trend_layout.addWidget(self.chart, 1)

        statement = QFrame()
        statement.setObjectName("canvasCard")
        statement_layout = QVBoxLayout(statement)
        statement_layout.setContentsMargins(18, 14, 18, 12)
        statement_title = QLabel("Last Quarter Income Statement")
        statement_title.setObjectName("sectionTitle")
        self.statement = QLabel()
        self.statement.setTextFormat(Qt.TextFormat.RichText)
        self.statement.setAlignment(Qt.AlignmentFlag.AlignTop)
        statement_layout.addWidget(statement_title)
        statement_layout.addWidget(self.statement, 1)
        layout.addWidget(trend, 6)
        layout.addWidget(statement, 4)
        return layout

    def _connect_controls(self) -> None:
        for control in (self.price, self.marketing, self.product, self.hires, self.layoffs):
            control.changed.connect(self._update_previews)
        self.hires.changed.connect(self._enforce_hiring_choice)
        self.layoffs.changed.connect(self._enforce_layoff_choice)
        self.funding.toggled.connect(self._update_previews)
        for sequence, slot in (
            ("Ctrl+Return", self._advance), ("Ctrl+Enter", self._advance),
            (QKeySequence.StandardKey.New, self._new_simulation),
            (QKeySequence.StandardKey.Save, self._save),
            (QKeySequence.StandardKey.Open, self._open),
        ):
            QShortcut(QKeySequence(sequence), self, activated=slot)

    def _enforce_hiring_choice(self) -> None:
        if self.hires.value() and self.layoffs.value():
            self.layoffs.set_value(0)

    def _enforce_layoff_choice(self) -> None:
        if self.layoffs.value() and self.hires.value():
            self.hires.set_value(0)

    def _decision(self) -> Decision:
        return Decision(
            self.price.value(), self.marketing.value() * 1_000, self.product.value() * 1_000,
            self.hires.value(), self.layoffs.value(), self.funding.isChecked(), self._dilemma_choice(),
        )

    def _update_previews(self) -> None:
        state = self.engine.state
        self._update_dilemma_availability()
        decision = self._decision()
        try:
            previews = self.engine.preview_effects(decision)
        except ValueError:
            return
        for name, value in previews.items():
            self.effects[name].set_value(value)
        runway = self.engine.preview_runway_months(decision)
        if math.isinf(runway):
            self.cards["Runway"].set_value("Self-funding", "Plan is cash-flow positive")
        else:
            self.cards["Runway"].set_value(f"{runway:.1f} mo", f"Net burn {money(self.engine.preview_net_burn(decision))}/qtr")
        raise_amount, dilution = self.engine.funding_offer()
        self.funding_note.setText(
            f"Next round: about {money(raise_amount)} for {dilution}% of the company "
            f"(ownership {state.founder_ownership:.1f}% → {state.founder_ownership * (1 - dilution / 100):.1f}%)."
        )
        warnings = []
        if not state.complete and runway < 6 and not decision.raise_funding:
            warnings.append(f"Runway is about {runway:.1f} months. The company fails below -$250K cash; cut spending or raise funding.")
        if not state.complete and previews["Service capacity"] == "Under pressure":
            warnings.append("Customers are outgrowing the team. Without hiring, churn will rise and morale will fall.")
        self.alert.setText("⚠  " + "  ".join(warnings) if warnings else "")
        self.alert.setVisible(bool(warnings))
        awaiting_response = self.engine.upcoming_dilemma() is not None and not decision.dilemma_choice
        self.advance_button.setEnabled(not state.complete and not awaiting_response)
        if state.complete:
            self.advance_button.setText("Simulation Complete")
        elif awaiting_response:
            self.advance_button.setText("Choose a Board Response First")
        else:
            self.advance_button.setText("Commit Strategy and Advance Quarter  →")

    def _update_chart(self) -> None:
        state = self.engine.state
        attribute, formatter = CHART_METRICS[self.chart_metric.currentText()]
        values = [float(getattr(result, attribute)) for result in state.history]
        start = GameState()
        opening = {"ending_cash": start.cash, "customers": start.customers, "valuation": start.valuation}
        if attribute in opening:
            self.chart.set_series([float(opening[attribute])] + values, formatter, state.max_quarters)
        else:
            self.chart.set_series(values, formatter, state.max_quarters, first_quarter=1)

    def _update_statement(self) -> None:
        state = self.engine.state
        if not state.history:
            self.statement.setText("<p style='color:#697B8C'>The income statement for each quarter appears here after you commit a strategy.</p>")
            return
        result = state.history[-1]
        rows = [("Revenue", result.revenue, True)]
        rows += [(f"&nbsp;&nbsp;{name}", -value, False) for name, value in result.costs.items() if value]
        rows.append(("Operating profit", result.operating_profit, True))
        cells = "".join(
            f"<tr><td style='padding:2px 18px 2px 0'>{'<b>' + name + '</b>' if bold else name}</td>"
            f"<td align='right' style='color:{'#A33B3B' if value < 0 else '#17283A'}'>{'<b>' + money(value) + '</b>' if bold else money(value)}</td></tr>"
            for name, value, bold in rows
        )
        self.statement.setText(
            f"<p style='color:#697B8C'>Q{result.quarter} · {result.event.name}</p><table width='100%'>{cells}</table>"
            f"<p style='color:#697B8C'>+{result.new_customers:,} new, -{result.churned_customers:,} churned customers"
            f" · support at {result.support_load:.0%} of capacity</p>"
        )

    def _update_dashboard(self) -> None:
        state = self.engine.state
        self.company_label.setText(f"{state.company_name}  ·  Scenario {self.engine.seed}")
        self.quarter_label.setText(f"QUARTER {state.quarter} / {state.max_quarters}")
        self.score_label.setText(f"CEO SCORE  {state.score()}")
        self.cards["Cash"].set_value(money(state.cash), "Available liquidity")
        self.cards["Revenue"].set_value(money(state.revenue), "Pre-launch plan" if not state.history else f"Op. profit {money(state.operating_profit)}")
        self.cards["Customers"].set_value(f"{state.customers:,}", "Starting customer base" if not state.history else f"{state.last_growth:+.1%} quarterly growth")
        self.cards["Valuation"].set_value(money(state.valuation), f"Founder stake {money(state.founder_stake)}")
        self.cards["Ownership"].set_value(f"{state.founder_ownership:.1f}%", f"{state.funding_rounds} funding round(s)")
        self.health_label.setText(
            f"CURRENT COMPANY HEALTH\nProduct quality {state.product_quality:.0f}/100  ·  Employee morale {state.morale:.0f}/100  ·  "
            f"{state.employees} employees supporting up to {state.support_capacity:,.0f} customers  ·  "
            f"{state.customers / state.market_size:.0%} of addressable market"
        )
        for name, achieved in state.objective_progress.items():
            self.objectives[name].set_achieved(achieved)
        upcoming = self.engine.upcoming_event()
        if state.bankrupt:
            self.event_title.setText("Company failed")
            self.event_text.setText("Cash fell below -$250K and the board ended the simulation. Review the board report to see what went wrong.")
        elif state.complete:
            self.event_title.setText("Simulation complete")
            self.event_text.setText("Review the final board report for the complete assessment.")
        else:
            self.event_title.setText(f"Q{state.quarter + 1}: {upcoming.name}")
            self.event_text.setText(upcoming.description)
        self.report_button.setVisible(state.complete)
        self.choices.setEnabled(not state.complete)
        self.layoffs.set_maximum(max(0, min(5, state.employees - MIN_EMPLOYEES)))
        self._refresh_dilemma()
        self._update_previews()
        self._update_chart()
        self._update_statement()

    def _reset_controls(self, decision: Decision | None = None) -> None:
        decision = decision or Decision()
        self.price.set_value(decision.price)
        self.marketing.set_value(decision.marketing // 1_000)
        self.product.set_value(decision.product // 1_000)
        self.hires.set_value(decision.hires)
        self.layoffs.set_value(decision.layoffs)
        self.funding.setChecked(False)
        self.shown_dilemma = None

    def _advance(self) -> None:
        if self.engine.state.complete or not self.advance_button.isEnabled():
            return
        try:
            result = self.engine.advance(self._decision())
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "Strategy cannot be committed", str(exc))
            return
        self.unsaved = True
        self.outcome_text.setText(f"Q{result.quarter} result — {result.narrative}")
        # Headcount changes and funding are one-off actions, so they do not carry into the next quarter.
        self.hires.set_value(0)
        self.layoffs.set_value(0)
        self.funding.setChecked(False)
        self._update_dashboard()
        if self.engine.state.complete:
            self._show_report()

    def _show_report(self) -> None:
        FinalReportDialog(self.engine.state, self).exec()

    def _show_guide(self) -> None:
        GuideDialog(self).exec()

    def _confirm_discard(self) -> bool:
        if not self.unsaved:
            return True
        answer = QMessageBox.question(
            self, "Discard unsaved progress?", "This simulation has unsaved quarters. Continue without saving?",
        )
        return answer == QMessageBox.StandardButton.Yes

    def _new_simulation(self) -> None:
        if not self._confirm_discard():
            return
        dialog = WelcomeDialog(self, self.engine.seed)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.engine.reset(dialog.company.text().strip() or "Northstar Labs", dialog.seed.value())
        self.unsaved = False
        self._reset_controls()
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
        self.unsaved = False
        self.statusBar().showMessage(f"Simulation saved locally: {path}", 6000)

    def _open(self) -> None:
        if not self._confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Open simulation", "", "Startup CEO saves (*.json);;JSON files (*.json)")
        if not path:
            return
        try:
            state, seed = load_game(path)
        except SaveFileError as exc:
            QMessageBox.warning(self, "Could not open simulation", str(exc))
            return
        self.engine = SimulationEngine.from_state(state, seed)
        self.unsaved = False
        if state.decision_history:
            last = state.decision_history[-1].decision
            self._reset_controls(Decision(last.price, last.marketing, last.product, 0, 0))
        else:
            self._reset_controls()
        self.outcome_text.setText("Saved simulation restored. Review the next market condition and set your strategy.")
        self._update_dashboard()
        self.statusBar().showMessage(f"Simulation opened: {path}", 6000)
        if state.complete:
            self._show_report()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()


def run() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Startup CEO Simulator")
    app.setFont(QFont())
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)
    window = MainWindow()
    window.show()
    return app.exec()
