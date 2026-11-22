"""
Desktop pet - a little glass speech bubble that floats above Blip
(used for "now playing" and other messages). Clicks go straight through it.
Developed by Tunes
"""
import time

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget

PAD_X, PAD_Y, TAIL = 14, 8, 9


def plain(text):
    """Bubbles above Blip skip emoji/symbols: the first emoji makes Windows load its
    colour-emoji font (~40 MB of RAM that never goes away). The chat keeps its emoji."""
    out = "".join(ch for ch in text if ord(ch) < 0x2100 or 0x3000 <= ord(ch) < 0xD800)
    return " ".join(out.split())
MAX_TEXT_WIDTH = 320


class Bubble(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
                            | Qt.WindowType.Tool | Qt.WindowType.WindowDoesNotAcceptFocus
                            | Qt.WindowType.WindowTransparentForInput)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.font = QFont("Segoe UI", 10)
        self.small = QFont("Segoe UI", 8)
        self.title, self.text = "", ""
        self.until = 0.0
        self.shown_at = 0.0

    def say(self, title, text, seconds=6.0):
        title, text = plain(title), plain(text)
        fm = QFontMetrics(self.font)
        self.title = title
        self.text = fm.elidedText(text, Qt.TextElideMode.ElideRight, MAX_TEXT_WIDTH)
        w = max(fm.horizontalAdvance(self.text), QFontMetrics(self.small).horizontalAdvance(title))
        self.setFixedSize(w + PAD_X * 2 + 2, fm.height() * 2 + PAD_Y * 2 + TAIL)
        self.shown_at = time.monotonic()
        self.until = self.shown_at + seconds
        self.setWindowOpacity(1.0)
        self.show()
        self.update()

    def follow(self, pet_x, pet_y, pet_size, screen_rect):
        """Keep the bubble above Blip's head; fade out at the end."""
        if not self.isVisible():
            return
        now = time.monotonic()
        if now >= self.until:
            self.hide()
            return
        left = now - self.shown_at
        self.setWindowOpacity(min(1.0, left / 0.25, (self.until - now) / 0.6))
        x = int(pet_x + pet_size / 2 - self.width() / 2)
        x = max(screen_rect.left() + 4, min(x, screen_rect.right() - self.width() - 4))
        y = int(pet_y + pet_size * 0.12 - self.height())
        y = max(screen_rect.top() + 4, y)
        self.tail_x = pet_x + pet_size / 2 - x
        self.move(x, y)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        body = QRectF(1, 1, self.width() - 2, self.height() - TAIL - 2)
        tx = max(18.0, min(getattr(self, "tail_x", self.width() / 2), self.width() - 18.0))
        path = QPainterPath()
        path.addRoundedRect(body, 12, 12)
        tail = QPainterPath()
        tail.moveTo(tx - 8, body.bottom() - 1)
        tail.lineTo(tx, body.bottom() + TAIL - 1)
        tail.lineTo(tx + 8, body.bottom() - 1)
        tail.closeSubpath()
        path = path.united(tail)
        p.setBrush(QColor(30, 18, 56, 228))
        p.setPen(QPen(QColor(160, 110, 255, 200), 1.2))
        p.drawPath(path)
        p.setPen(QColor(0, 225, 255, 230))
        p.setFont(self.small)
        fm = QFontMetrics(self.font)
        p.drawText(QPointF(PAD_X, PAD_Y + QFontMetrics(self.small).ascent()), self.title)
        p.setPen(QColor(240, 250, 255))
        p.setFont(self.font)
        p.drawText(QPointF(PAD_X, PAD_Y + fm.height() + fm.ascent() - 2), self.text)
        p.end()


class AskBubble(QWidget):
    """A speech bubble with a question and Yes / No buttons. Created only when needed,
    and deleted as soon as it closes (Yes, No, or after `seconds`)."""

    def __init__(self, text, on_yes, on_no, seconds=20.0, yes="Yes please", no="No thanks",
                 extra=None):
        from PyQt6.QtCore import QTimer
        from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
                            | Qt.WindowType.Tool | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.on_yes, self.on_no = on_yes, on_no
        self.answered = False
        lay = QVBoxLayout(self)
        lay.setContentsMargins(PAD_X, PAD_Y + 2, PAD_X, PAD_Y + TAIL + 2)
        lay.setSpacing(8)
        label = QLabel(plain(text))
        label.setWordWrap(True)
        label.setMaximumWidth(260)
        label.setStyleSheet("color: #F0FAFF; font: 10pt 'Segoe UI'; background: transparent;")
        lay.addWidget(label)
        row = QHBoxLayout()
        row.addStretch()
        style = ("QPushButton{color:white;border-radius:8px;padding:5px 12px;font:9pt 'Segoe UI';"
                 "border:1px solid rgba(160,110,255,160);background:rgba(255,255,255,22)}"
                 "QPushButton:hover{background:rgba(0,225,255,60)}")
        choices = [(no, self.no, False)]
        if extra:                                   # e.g. ("Lost 💀", callback)
            choices.append((extra[0], lambda: self.answer(extra[1]), False))
        choices.append((yes, self.yes, True))
        for txt, cb, primary in choices:
            b = QPushButton(plain(txt))
            b.setStyleSheet(style + ("QPushButton{border:none;background:qlineargradient(x1:0,y1:0,"
                                     "x2:1,y2:0,stop:0 rgba(154,90,255,220),stop:1 rgba(0,225,255,220));"
                                     "font-weight:bold}" if primary else ""))
            b.clicked.connect(cb)
            row.addWidget(b)
        lay.addLayout(row)
        self.adjustSize()
        self.tail_x = self.width() / 2
        QTimer.singleShot(int(seconds * 1000), self.no)      # no answer = "no"

    def yes(self):
        if not self.answered:
            self.answered = True
            self.close()
            self.on_yes()

    def answer(self, callback):
        if not self.answered:
            self.answered = True
            self.close()
            callback()

    def no(self):
        if not self.answered:
            self.answered = True
            self.close()
            self.on_no()

    def follow(self, pet_x, pet_y, pet_size, screen_rect):
        x = int(pet_x + pet_size / 2 - self.width() / 2)
        x = max(screen_rect.left() + 4, min(x, screen_rect.right() - self.width() - 4))
        y = max(screen_rect.top() + 4, int(pet_y + pet_size * 0.12 - self.height()))
        self.tail_x = pet_x + pet_size / 2 - x
        if (x, y) != (self.x(), self.y()):
            self.move(x, y)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        body = QRectF(1, 1, self.width() - 2, self.height() - TAIL - 2)
        tx = max(18.0, min(self.tail_x, self.width() - 18.0))
        path = QPainterPath()
        path.addRoundedRect(body, 12, 12)
        tail = QPainterPath()
        tail.moveTo(tx - 8, body.bottom() - 1)
        tail.lineTo(tx, body.bottom() + TAIL - 1)
        tail.lineTo(tx + 8, body.bottom() - 1)
        tail.closeSubpath()
        p.setBrush(QColor(30, 18, 56, 235))
        p.setPen(QPen(QColor(160, 110, 255, 210), 1.2))
        p.drawPath(path.united(tail))
        p.end()
