"""
Desktop pet - a snack that drops onto the taskbar for the pet to eat.
You can also pick it up and throw it.
Developed by Tunes
"""
import time

from PyQt6.QtCore import QPoint, Qt, QTimer
from PyQt6.QtGui import QGuiApplication, QPainter
from PyQt6.QtWidgets import QWidget

import config
from character import draw_snack

SIZE = 36


class Snack(QWidget):
    def __init__(self, x, y):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.WindowStaysOnTopHint
                            | Qt.WindowType.Tool
                            | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(SIZE, SIZE)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        self.x_pos, self.y_pos = float(x), float(y)
        self.vy = 0.0
        self.on_ground = False
        self.dragging = False
        self.grab = QPoint()
        self.last = time.monotonic()
        self.move(int(x), int(y))

        # Only ticks while falling, then stops (costs nothing while resting).
        self.timer = QTimer(self)
        self.timer.setInterval(1000 // config.FPS_PHYSICS)
        self.timer.timeout.connect(self.fall)
        self.timer.start()

    def floor_y(self):
        c = QPoint(int(self.x_pos + SIZE / 2), int(self.y_pos + SIZE / 2))
        screen = QGuiApplication.screenAt(c) or QGuiApplication.primaryScreen()
        return screen.availableGeometry().bottom() - SIZE + 1

    def fall(self):
        now = time.monotonic()
        dt = min(now - self.last, 0.05)
        self.last = now
        self.vy += config.GRAVITY * dt
        self.y_pos += self.vy * dt
        floor = self.floor_y()
        if self.y_pos >= floor:
            self.y_pos = floor
            if self.vy > 300:
                self.vy = -self.vy * 0.35
            else:
                self.vy = 0.0
                self.on_ground = True
                self.timer.stop()
        self.move(int(self.x_pos), int(self.y_pos))

    def center_x(self):
        return self.x_pos + SIZE / 2

    # drag it around
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.dragging, self.on_ground = True, False
            self.timer.stop()
            self.grab = e.position().toPoint()

    def mouseMoveEvent(self, e):
        if self.dragging:
            pos = e.globalPosition().toPoint() - self.grab
            self.x_pos, self.y_pos = float(pos.x()), float(pos.y())
            self.move(pos)

    def mouseReleaseEvent(self, e):
        if self.dragging:
            self.dragging = False
            self.vy = 0.0
            self.last = time.monotonic()
            self.timer.start()

    def paintEvent(self, e):
        p = QPainter(self)
        draw_snack(p, SIZE)
        p.end()
