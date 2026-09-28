"""Reusable presentation widgets for the strategy canvas."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSlider, QSpinBox, QVBoxLayout, QWidget


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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        row = QHBoxLayout()
        label = QLabel(title)
        label.setObjectName("controlLabel")
        self.spin = QSpinBox()
        self.spin.setRange(minimum, maximum)
        self.spin.setValue(value)
        self.spin.setPrefix(prefix)
        self.spin.setSuffix(suffix)
        self.spin.setFixedWidth(88)
        row.addWidget(label)
        row.addStretch()
        row.addWidget(self.spin)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(minimum, maximum)
        self.slider.setValue(value)
        self.slider.valueChanged.connect(self.spin.setValue)
        self.spin.valueChanged.connect(self.slider.setValue)
        self.spin.valueChanged.connect(self.changed)
        layout.addLayout(row)
        layout.addWidget(self.slider)

    def value(self) -> int:
        return self.spin.value()

    def set_value(self, value: int) -> None:
        self.spin.setValue(value)


class EffectRow(QFrame):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.setObjectName("effectRow")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        label = QLabel(title)
        label.setObjectName("effectLabel")
        self.value = QLabel("Moderate")
        self.value.setObjectName("effectValue")
        layout.addWidget(label)
        layout.addStretch()
        layout.addWidget(self.value)

    def set_value(self, value: str) -> None:
        self.value.setText(value)
        tone = "negative" if value in {"Low", "Under pressure"} else "positive" if value in {"High", "Improving"} else "neutral"
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
