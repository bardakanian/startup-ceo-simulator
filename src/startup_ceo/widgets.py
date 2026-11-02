"""Reusable presentation widgets for the strategy canvas."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QRadioButton, QSizePolicy, QSlider, QSpinBox, QVBoxLayout, QWidget


class KpiCard(QFrame):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.setObjectName("kpiCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(2)
        label = QLabel(title.upper())
        label.setObjectName("kpiLabel")
        self.value = QLabel("—")
        self.value.setObjectName("kpiValue")
        self.detail = QLabel("Ready")
        self.detail.setObjectName("kpiDetail")
        layout.addWidget(label)
        layout.addWidget(self.value)
        layout.addWidget(self.detail)

    def set_value(self, value: str, detail: str) -> None:
        self.value.setText(value)
        self.detail.setText(detail)


class LabeledControl(QWidget):
    changed = Signal()

    def __init__(self, title: str, minimum: int, maximum: int, value: int, prefix: str = "", suffix: str = "") -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(12)
        label = QLabel(title)
        label.setObjectName("controlLabel")
        label.setMinimumWidth(170)
        self.spin = QSpinBox()
        self.spin.setRange(minimum, maximum)
        self.spin.setValue(value)
        self.spin.setPrefix(prefix)
        self.spin.setSuffix(suffix)
        self.spin.setFixedWidth(88)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(minimum, maximum)
        self.slider.setValue(value)
        self.slider.valueChanged.connect(self.spin.setValue)
        self.spin.valueChanged.connect(self.slider.setValue)
        self.spin.valueChanged.connect(self.changed)
        layout.addWidget(label)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.spin)

    def value(self) -> int:
        return self.spin.value()

    def set_value(self, value: int) -> None:
        self.spin.setValue(value)

    def set_maximum(self, maximum: int) -> None:
        self.spin.setMaximum(maximum)
        self.slider.setMaximum(maximum)


class EffectRow(QFrame):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.setObjectName("effectRow")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        label = QLabel(title)
        label.setObjectName("effectLabel")
        self.value = QLabel("Moderate")
        self.value.setObjectName("effectValue")
        layout.addWidget(label)
        layout.addStretch()
        layout.addWidget(self.value)

    def set_value(self, value: str) -> None:
        self.value.setText(value)
        tone = (
            "negative" if value in {"Low", "Under pressure", "Declining"}
            else "warning" if value == "Stretched"
            else "positive" if value in {"High", "Improving"}
            else "neutral"
        )
        self.value.setProperty("tone", tone)
        self.value.style().unpolish(self.value)
        self.value.style().polish(self.value)


class ObjectiveRow(QFrame):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.title = title
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        self.icon = QLabel("○")
        self.label = QLabel(title)
        layout.addWidget(self.icon)
        layout.addWidget(self.label, 1)

    def set_achieved(self, achieved: bool) -> None:
        self.icon.setText("✓" if achieved else "○")
        color = "#137F78" if achieved else "#7A8699"
        self.icon.setStyleSheet(f"color: {color}; font-weight: 800;")


class OptionCard(QFrame):
    """A board-decision option; clicking anywhere on the card selects it."""

    def __init__(self, label: str, key: str, details: str) -> None:
        super().__init__()
        self.setObjectName("optionCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(3)
        self.button = QRadioButton(label)
        self.button.setProperty("key", key)
        self.summary = details
        self.details = QLabel(details)
        self.details.setObjectName("muted")
        self.details.setWordWrap(True)
        layout.addWidget(self.button)
        layout.addWidget(self.details)
        layout.addStretch()

    def mousePressEvent(self, event) -> None:
        if self.button.isEnabled():
            self.button.setChecked(True)
        super().mousePressEvent(event)

    def set_problem(self, problem: str | None) -> None:
        """Disable the option and explain why, or re-enable it when problem is None."""
        self.button.setEnabled(problem is None)
        self.details.setText(f"{self.summary}  —  {problem}" if problem else self.summary)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)


class TrendChart(QWidget):
    """A lightweight line chart for one metric across completed quarters."""

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(170)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.values: list[float] = []
        self.formatter: Callable[[float], str] = str
        self.max_quarters = 12
        self.first_quarter = 0

    def set_series(self, values: list[float], formatter: Callable[[float], str], max_quarters: int, first_quarter: int = 0) -> None:
        self.values = values
        self.formatter = formatter
        self.max_quarters = max(1, max_quarters)
        self.first_quarter = first_quarter
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        font = QFont(self.font())
        font.setPixelSize(10)
        painter.setFont(font)
        plot = QRectF(self.rect()).adjusted(58, 10, -14, -24)
        muted = QColor("#7A8A99")
        if len(self.values) < 2:
            painter.setPen(muted)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Trends appear after the first quarters are committed.")
            return
        low, high = min(self.values + [0.0]), max(self.values + [0.0])
        if high == low:
            high = low + 1
        span = high - low

        def point(index: int, value: float) -> QPointF:
            x = plot.left() + plot.width() * (index + self.first_quarter) / self.max_quarters
            return QPointF(x, plot.bottom() - plot.height() * (value - low) / span)

        painter.setPen(QPen(QColor("#E4EAEE"), 1))
        for step in range(5):
            value = low + span * step / 4
            y = point(0, value).y()
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            painter.setPen(muted)
            painter.drawText(QRectF(0, y - 8, plot.left() - 8, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self.formatter(value))
            painter.setPen(QPen(QColor("#E4EAEE"), 1))
        if low < 0 < high:
            painter.setPen(QPen(QColor("#C24B4B"), 1, Qt.PenStyle.DashLine))
            zero = point(0, 0).y()
            painter.drawLine(QPointF(plot.left(), zero), QPointF(plot.right(), zero))
        painter.setPen(muted)
        for quarter in range(0, self.max_quarters + 1, max(1, self.max_quarters // 6)):
            x = point(quarter - self.first_quarter, low).x()
            painter.drawText(QRectF(x - 16, plot.bottom() + 6, 32, 14), Qt.AlignmentFlag.AlignCenter, f"Q{quarter}")

        path = QPainterPath(point(0, self.values[0]))
        for index, value in enumerate(self.values[1:], 1):
            path.lineTo(point(index, value))
        painter.setPen(QPen(QColor("#137F78"), 2.4))
        painter.drawPath(path)
        painter.setBrush(QColor("#137F78"))
        painter.setPen(Qt.PenStyle.NoPen)
        last = point(len(self.values) - 1, self.values[-1])
        painter.drawEllipse(last, 4, 4)
