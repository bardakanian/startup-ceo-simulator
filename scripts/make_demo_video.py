"""Render a captioned, square demo video of a scripted playthrough (for LinkedIn and similar feeds).

The real application runs offscreen; each frame is a capture of the window, framed with a
caption band, a drawn cursor, and smooth zooms. Requires ffmpeg on the PATH.

    QT_QPA_PLATFORM=offscreen python scripts/make_demo_video.py [output.mp4]
"""

from __future__ import annotations

import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# Render the app at 2x so zoomed-in shots stay sharp.
os.environ.setdefault("QT_SCALE_FACTOR", "2")

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QApplication, QScrollArea, QStyle, QStyleOptionSlider, QWidget

from startup_ceo.app import STYLESHEET, FinalReportDialog, MainWindow
from startup_ceo.models import SUPPORT_PER_EMPLOYEE


SIZE = 1080
FPS = 30
WINDOW_W, WINDOW_H = 1440, 1140
CAPTION_H = 150
CONTENT_H = round(SIZE * WINDOW_H / WINDOW_W)
FOOTER_H = SIZE - CAPTION_H - CONTENT_H
SEED = 12
NAVY = QColor("#10283E")
TEAL = QColor("#137F78")
MINT = QColor("#7FD6CC")
FULL = QRectF(0, 0, WINDOW_W, WINDOW_H)


def ease(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return t * t * (3 - 2 * t)


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp_rect(a: QRectF, b: QRectF, t: float) -> QRectF:
    return QRectF(lerp(a.x(), b.x(), t), lerp(a.y(), b.y(), t), lerp(a.width(), b.width(), t), lerp(a.height(), b.height(), t))


def font(pixels: int, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    result = QFont()
    result.setPixelSize(pixels)
    result.setWeight(weight)
    return result


class Encoder:
    def __init__(self, path: Path) -> None:
        self.frames = 0
        self.process = subprocess.Popen(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{SIZE}x{SIZE}", "-r", str(FPS), "-i", "-",
                "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", str(path),
            ],
            stdin=subprocess.PIPE,
        )

    def write(self, image: QImage) -> None:
        frame = image.convertToFormat(QImage.Format.Format_RGB888)
        self.process.stdin.write(frame.constBits().tobytes())
        self.frames += 1

    def close(self) -> None:
        self.process.stdin.close()
        if self.process.wait() != 0:
            raise RuntimeError("ffmpeg failed to encode the video")


class Director:
    """Keeps the camera, cursor and caption state and turns it into frames."""

    def __init__(self, app: QApplication, window: MainWindow, encoder: Encoder) -> None:
        self.app = app
        self.window = window
        self.encoder = encoder
        self.camera = QRectF(FULL)
        self.cursor: QPointF | None = None
        self.caption = ""
        self.caption_age = 99.0
        self.dialog_image: QImage | None = None
        self.last = QImage()
        self.snap()

    # Capturing -------------------------------------------------------------

    def settle(self) -> None:
        for _ in range(3):
            self.app.processEvents()

    def snap(self) -> None:
        self.settle()
        self.image = self.window.grab().toImage()

    def point(self, widget: QWidget) -> QPointF:
        return QPointF(widget.mapTo(self.window, widget.rect().center()))

    def handle(self, control) -> QPointF:
        slider = control.slider
        option = QStyleOptionSlider()
        slider.initStyleOption(option)
        rect = slider.style().subControlRect(QStyle.ComplexControl.CC_Slider, option, QStyle.SubControl.SC_SliderHandle, slider)
        return QPointF(slider.mapTo(self.window, rect.center()))

    def focus(self, *widgets: QWidget, pad: float = 36) -> QRectF:
        area = QRectF()
        for widget in widgets:
            top_left = widget.mapTo(self.window, widget.rect().topLeft())
            area = area.united(QRectF(top_left.x(), top_left.y(), widget.width(), widget.height()))
        area.adjust(-pad, -pad, pad, pad)
        aspect = WINDOW_W / WINDOW_H
        if area.width() / area.height() < aspect:
            grow = area.height() * aspect - area.width()
            area.adjust(-grow / 2, 0, grow / 2, 0)
        else:
            grow = area.width() / aspect - area.height()
            area.adjust(0, -grow / 2, 0, grow / 2)
        if area.width() > WINDOW_W:
            return QRectF(FULL)
        area.moveLeft(min(max(area.left(), 0), WINDOW_W - area.width()))
        area.moveTop(min(max(area.top(), 0), WINDOW_H - area.height()))
        return area

    # Drawing ---------------------------------------------------------------

    def to_canvas(self, point: QPointF) -> QPointF:
        return QPointF(
            (point.x() - self.camera.x()) / self.camera.width() * SIZE,
            CAPTION_H + (point.y() - self.camera.y()) / self.camera.height() * CONTENT_H,
        )

    def compose(self, pulse: float = 0.0) -> QImage:
        canvas = QImage(SIZE, SIZE, QImage.Format.Format_ARGB32_Premultiplied)
        canvas.fill(NAVY)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        content = QRectF(0, CAPTION_H, SIZE, CONTENT_H)
        ratio = self.image.devicePixelRatio()
        source = QRectF(self.camera.x() * ratio, self.camera.y() * ratio, self.camera.width() * ratio, self.camera.height() * ratio)
        painter.drawImage(content, self.image, source)

        if self.dialog_image is not None:
            painter.fillRect(content, QColor(10, 24, 38, 150))
            # Drawn with a target rect, so the 2x capture is scaled down crisply.
            scale = min((CONTENT_H - 40) / self.dialog_image.height(), (SIZE - 80) / self.dialog_image.width())
            width, height = self.dialog_image.width() * scale, self.dialog_image.height() * scale
            painter.drawImage(QRectF((SIZE - width) / 2, CAPTION_H + (CONTENT_H - height) / 2, width, height), self.dialog_image)

        if self.cursor is not None and self.dialog_image is None:
            tip = self.to_canvas(self.cursor)
            if pulse:
                radius = 12 + 30 * pulse
                painter.setPen(QPen(QColor(19, 127, 120, int(220 * (1 - pulse))), 4))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(tip, radius, radius)
            arrow = QPolygonF([QPointF(0, 0), QPointF(0, 26), QPointF(7, 20), QPointF(12, 31), QPointF(17, 29), QPointF(12, 18), QPointF(21, 18)])
            arrow.translate(tip)
            painter.setPen(QPen(QColor("#111111"), 1.6))
            painter.setBrush(QColor("white"))
            painter.drawPolygon(arrow)

        painter.fillRect(QRectF(0, 0, SIZE, CAPTION_H), NAVY)
        painter.fillRect(QRectF(0, CAPTION_H - 4, SIZE, 4), TEAL)
        alpha = int(255 * ease(self.caption_age / 0.35))
        painter.setPen(QColor(255, 255, 255, alpha))
        painter.setFont(font(36, QFont.Weight.Bold))
        painter.drawText(QRectF(48, 0, SIZE - 96, CAPTION_H), Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap, self.caption)

        footer = QRectF(48, CAPTION_H + CONTENT_H, SIZE - 96, FOOTER_H)
        painter.fillRect(QRectF(0, footer.top(), SIZE, FOOTER_H), NAVY)
        painter.setFont(font(20, QFont.Weight.Bold))
        painter.setPen(QColor("white"))
        painter.drawText(footer, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "◆  STARTUP CEO SIMULATOR")
        painter.setFont(font(19))
        painter.setPen(MINT)
        painter.drawText(footer, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, "An MBA strategy game · Python + PySide6")
        painter.end()
        return canvas

    def emit(self, frame: QImage) -> None:
        self.encoder.write(frame)
        self.last = frame
        self.caption_age += 1 / FPS

    # Shots -----------------------------------------------------------------

    def say(self, caption: str) -> None:
        if caption != self.caption:
            self.caption = caption
            self.caption_age = 0.0

    def move(self, seconds: float, camera: QRectF | None = None, cursor: QPointF | None = None, step=None) -> None:
        """Animate camera and cursor together; step(t) may change the app, which is then recaptured."""
        start_camera, start_cursor = QRectF(self.camera), self.cursor
        frames = max(1, round(seconds * FPS))
        for index in range(1, frames + 1):
            t = ease(index / frames)
            if camera is not None:
                self.camera = lerp_rect(start_camera, camera, t)
            if cursor is not None:
                origin = start_cursor or QPointF(cursor.x() + 140, cursor.y() + 160)
                self.cursor = QPointF(lerp(origin.x(), cursor.x(), t), lerp(origin.y(), cursor.y(), t))
            if step is not None:
                step(index / frames)
                self.snap()
            self.emit(self.compose())

    def hold(self, seconds: float) -> None:
        self.move(seconds)

    def click(self, widget: QWidget, action, travel: float = 0.6) -> None:
        self.move(travel, cursor=self.point(widget))
        frames = round(0.35 * FPS)
        for index in range(frames):
            if index == frames // 3:
                action()
                self.snap()
            self.emit(self.compose(pulse=index / frames))

    def card(self, seconds: float, title: str, lines: list[str], fade_in: float = 0.0) -> None:
        canvas = QImage(SIZE, SIZE, QImage.Format.Format_ARGB32_Premultiplied)
        canvas.fill(NAVY)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(MINT)
        painter.setFont(font(26, QFont.Weight.Bold))
        painter.drawText(QRectF(90, 300, SIZE - 180, 40), Qt.AlignmentFlag.AlignLeft, "◆  STARTUP CEO SIMULATOR")
        painter.fillRect(QRectF(90, 352, 90, 6), TEAL)
        painter.setPen(QColor("white"))
        painter.setFont(font(64, QFont.Weight.Black))
        painter.drawText(QRectF(90, 380, SIZE - 180, 240), Qt.TextFlag.TextWordWrap, title)
        painter.setFont(font(30))
        painter.setPen(QColor("#C9D6E0"))
        painter.drawText(QRectF(90, 640, SIZE - 180, 300), Qt.TextFlag.TextWordWrap, "\n".join(lines))
        painter.end()
        self.fade_to(canvas, fade_in)
        for _ in range(round(seconds * FPS)):
            self.emit(canvas)

    def fade_to(self, target: QImage, seconds: float) -> None:
        frames = round(seconds * FPS)
        for index in range(1, frames + 1):
            blend = QImage(target)
            painter = QPainter(blend)
            painter.setOpacity(1 - ease(index / frames))
            painter.drawImage(0, 0, self.last)
            painter.end()
            self.emit(blend)


def plan_hires(state) -> int:
    return max(0, min(8, math.ceil(state.customers * 1.25 / (SUPPORT_PER_EMPLOYEE * 0.9)) - state.employees))


def main() -> int:
    if shutil.which("ffmpeg") is None:
        raise SystemExit("ffmpeg is required: install it (for example `brew install ffmpeg`) and try again.")
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "work" / "startup-ceo-demo-linkedin.mp4"
    output.parent.mkdir(parents=True, exist_ok=True)

    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)
    window = MainWindow()
    window._show_report = lambda: None
    window.engine.reset("Northstar Labs", SEED)
    window._reset_controls()
    window.statusBar().hide()
    window.resize(WINDOW_W, WINDOW_H)
    window.show()
    window._update_dashboard()

    encoder = Encoder(output)
    director = Director(app, window, encoder)

    def commit() -> None:
        director.click(window.advance_button, window._advance, travel=0.5)

    def set_plan(hires: int) -> None:
        window.hires.set_value(hires)
        director.snap()

    def choose(index: int) -> None:
        card = window.dilemma_cards[index]
        director.click(card.button, lambda: card.button.setChecked(True))

    # 1. Title.
    director.card(2.6, "Run a startup for 12 quarters.", ["Every decision is a trade-off between growth,", "cash, people and founder control."])

    # 2. The canvas.
    director.say("An MBA strategy game: set the plan, see the effects, commit the quarter.")
    director.fade_to(director.compose(), 0.5)
    director.hold(1.6)

    # 3. Adjusting the plan.
    director.say("Price, marketing, product, hiring: the estimates update as you plan.")
    canvas_view = director.focus(window.choices, pad=16)
    director.move(1.0, camera=canvas_view, cursor=director.handle(window.price))
    director.move(1.3, cursor=director.handle(window.price), step=lambda t: window.price.set_value(round(lerp(79, 99, t))))
    director.move(0.35, cursor=director.handle(window.price))
    director.move(0.5, cursor=director.handle(window.marketing))
    director.move(1.3, step=lambda t: (window.marketing.set_value(round(lerp(90, 180, t))), setattr(director, "cursor", director.handle(window.marketing))))
    director.move(0.5, cursor=director.handle(window.hires))
    director.move(0.5, step=lambda t: (window.hires.set_value(0), setattr(director, "cursor", director.handle(window.hires))))
    director.hold(0.6)

    # 4. Committing quarters.
    director.say("Commit, and the quarter plays out: market events, churn, costs and cash.")
    director.move(0.8, camera=QRectF(FULL))
    commit()
    director.hold(0.9)
    set_plan(plan_hires(window.engine.state))
    commit()
    director.hold(0.6)

    # 5. A board dilemma (a security flaw arrives in Q3 for scenario 12).
    director.say("Board dilemmas force real calls. A security flaw: disclose, audit, or stay quiet?")
    director.move(1.0, camera=director.focus(window.dilemma_cards[0], window.dilemma_cards[1], pad=72))
    director.hold(1.4)
    choose(0)
    director.hold(0.9)
    director.say("Every response shows its consequences up front.")
    director.move(0.8, camera=QRectF(FULL))
    commit()
    director.hold(0.5)

    # 6. Growth until runway gets short, then a funding round (Q6, alongside a price war).
    director.say("Grow, hire to keep up with customers, and watch the runway.")
    while window.engine.state.quarter < 5:
        set_plan(plan_hires(window.engine.state))
        commit()
        director.hold(0.35)
    set_plan(plan_hires(window.engine.state))
    director.say("Runway getting short? Raise a round, and accept the dilution.")
    director.move(0.9, camera=director.focus(window.funding, window.funding_note, window.hires, window.alert, pad=24))
    director.hold(0.8)
    director.click(window.funding, lambda: window.funding.setChecked(True))
    director.hold(1.0)
    director.say("A rival starts a price war in the same quarter.")
    director.move(0.8, camera=director.focus(window.dilemma_cards[0], window.dilemma_cards[1], pad=72))
    choose(0)
    director.hold(0.6)
    director.move(0.7, camera=QRectF(FULL))
    commit()
    director.hold(0.5)

    # 7. Fast-forward with the trend chart.
    director.say("Twelve quarters of trade-offs, tracked in charts and income statements.")
    history = director.focus(window.chart, window.chart_metric, pad=16)
    director.move(0.9, camera=history)
    director.click(window.chart_metric, lambda: window.chart_metric.setCurrentText("Customers"), travel=0.5)
    while not window.engine.state.complete:
        if window.dilemma_group.buttons():
            window.dilemma_group.buttons()[0].setChecked(True)
        set_plan(plan_hires(window.engine.state))
        window._advance()
        director.snap()
        director.cursor = None
        director.hold(0.45)
    director.hold(1.0)

    # 8. The board report.
    state = window.engine.state
    director.say(f"Then face the board: CEO score {state.score()}/100, objectives and every decision.")
    director.move(0.6, camera=QRectF(FULL))
    dialog = FinalReportDialog(state, window)
    dialog.resize(760, 860)
    dialog.show()
    scroll = dialog.findChild(QScrollArea).verticalScrollBar()
    director.settle()
    director.dialog_image = dialog.grab().toImage()
    director.fade_to(director.compose(), 0.5)
    director.hold(1.6)
    bottom = scroll.maximum()

    def scroll_report(t: float) -> None:
        scroll.setValue(round(lerp(0, bottom * 0.62, ease(t))))
        director.settle()
        director.dialog_image = dialog.grab().toImage()

    director.move(2.4, step=scroll_report)
    director.hold(1.2)
    dialog.close()

    # 9. Close.
    director.card(
        3.4, "Built to make strategy tangible.",
        ["Python · PySide6 · fully offline", "Deterministic, seeded scenarios for classroom comparison", "", "github.com/bardakanian/startup-ceo-simulator"],
        fade_in=0.6,
    )

    encoder.close()
    print(f"{output}  ({encoder.frames / FPS:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
