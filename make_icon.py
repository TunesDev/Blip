"""Draws Blip into assets/blip.ico (used for the .exe). Run: python make_icon.py"""
import sys
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication, QImage, QPainter
from character import draw_pet

app = QGuiApplication(sys.argv)
img = QImage(256, 256, QImage.Format.Format_ARGB32)
img.fill(Qt.GlobalColor.transparent)
p = QPainter(img)
draw_pet(p, 256, "idle", 0.0)
p.end()
print("saved" if img.save("assets/blip.ico") else "could not save icon")
