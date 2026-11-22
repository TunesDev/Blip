"""
Desktop pet - skins: body materials you unlock with levels and prestige. All original,
all drawn in code. The still part of each skin is drawn ONCE into a cached image and then
just copied each frame (clipped to Blip's body shape). Animated skins add a few cheap
shapes on top, and freeze while Blip sleeps.
Developed by Tunes
"""
import math
import os
import random

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (QBrush, QColor, QConicalGradient, QImage, QLinearGradient, QPainter,
                         QPainterPath, QPen, QPolygonF, QRadialGradient)

SKINS = [
    ("None", ("level", 1)),
    ("Carbon Fibre", ("level", 5)), ("Digital Camo", ("level", 10)), ("Neon Grid", ("level", 15)),
    ("Circuit Board", ("level", 20)), ("Ice Crystal", ("level", 25)), ("Toxic Slime", ("level", 30)),
    ("Lava", ("level", 35)), ("Chrome", ("level", 40)), ("Gold", ("level", 45)),
    ("Diamond", ("level", 50)), ("Holographic", ("level", 55)),
    ("Bronze Ember", ("prestige", 1)), ("Galaxy", ("prestige", 2)), ("Electric", ("prestige", 3)),
    ("Blue Flame", ("prestige", 4)), ("Dark Matter", ("prestige", 5)), ("Aurora", ("prestige", 6)),
    ("Plasma", ("prestige", 7)), ("Void Glitch", ("prestige", 8)), ("Phoenix", ("prestige", 9)),
    ("Master Prism", ("prestige", 10)),
]
REQ = dict(SKINS)
ANIMATED = {"Lava", "Diamond", "Holographic", "Bronze Ember", "Galaxy", "Electric", "Blue Flame",
            "Dark Matter", "Aurora", "Plasma", "Void Glitch", "Phoenix", "Master Prism"}
# Prestige aura colours, P1 bronze ... P10 animated rainbow gold
AURA = [None, (205, 127, 50), (192, 192, 210), (255, 200, 60), (80, 220, 255), (200, 80, 255),
        (80, 255, 160), (255, 80, 120), (120, 120, 255), (255, 120, 30), "rainbow"]


def unlocked(name, prog):
    if os.getenv("BLIP_UNLOCK_ALL"):
        return True
    kind, n = REQ.get(name, ("level", 1))
    if kind == "prestige":
        return prog.prestige >= n
    return prog.prestige > 0 or prog.level >= n          # level skins are kept after prestige


def lock_text(name):
    kind, n = REQ[name]
    return f"Prestige {n}" if kind == "prestige" else f"Level {n}"


# ---------------------------------------------------------------------------
# Still textures (made once, 128x128, on Blip's 120-px grid)
# ---------------------------------------------------------------------------
_cache = {}
_bolts = {}
N = 128


def _img(fill):
    img = QImage(N, N, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(QColor(*fill))
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    return img, p


def _gradient_img(stops, vertical=True):
    img, p = _img((0, 0, 0))
    g = QLinearGradient(0, 0, 0 if not vertical else 0, N) if vertical else QLinearGradient(0, 0, N, 0)
    for pos, col in stops:
        g.setColorAt(pos, QColor(*col))
    p.fillRect(0, 0, N, N, QBrush(g))
    return img, p


def texture(name):
    if name in _cache:
        return _cache[name]
    rnd = random.Random(name)
    if name == "Carbon Fibre":
        img, p = _img((28, 28, 32))
        for y in range(0, N, 8):
            for x in range(0, N, 8):
                g = QLinearGradient(x, y, x + 8, y + 8)
                light = (x // 8 + y // 8) % 2
                g.setColorAt(0, QColor(70, 70, 78) if light else QColor(40, 40, 46))
                g.setColorAt(1, QColor(30, 30, 34))
                p.fillRect(x, y, 8, 8, QBrush(g))
    elif name == "Digital Camo":
        img, p = _img((92, 110, 84))
        cols = [(60, 74, 52), (130, 140, 110), (44, 52, 40), (108, 96, 70)]
        for _ in range(260):
            p.fillRect(rnd.randrange(0, N, 4), rnd.randrange(0, N, 4), 4 * rnd.randint(1, 3),
                       4 * rnd.randint(1, 2), QColor(*rnd.choice(cols)))
    elif name == "Neon Grid":
        img, p = _gradient_img([(0, (40, 10, 70)), (1, (10, 0, 30))])
        p.setPen(QPen(QColor(255, 60, 200, 200), 1.2))
        for i in range(-8, 9):
            p.drawLine(QPointF(64 + i * 6, 40), QPointF(64 + i * 30, N))
        p.setPen(QPen(QColor(0, 230, 255, 200), 1.2))
        y = 44.0
        while y < N:
            p.drawLine(QPointF(0, y), QPointF(N, y))
            y += (y - 36) * 0.35 + 2
    elif name == "Circuit Board":
        img, p = _img((10, 60, 40))
        for _ in range(26):
            x, y = rnd.randrange(0, N, 8), rnd.randrange(0, N, 8)
            path = QPainterPath(QPointF(x, y))
            for _ in range(3):
                x += rnd.choice((-16, 0, 16)); y += rnd.choice((0, 16))
                path.lineTo(QPointF(x, y))
            p.setPen(QPen(QColor(90, 255, 170, 200), 1.4)); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(220, 255, 120))
            p.drawEllipse(QPointF(x, y), 2, 2)
    elif name == "Ice Crystal":
        img, p = _gradient_img([(0, (220, 245, 255)), (1, (120, 190, 240))])
        for _ in range(30):
            cx, cy = rnd.uniform(0, N), rnd.uniform(0, N)
            pts = [QPointF(cx + rnd.uniform(-18, 18), cy + rnd.uniform(-18, 18)) for _ in range(3)]
            p.setPen(QPen(QColor(255, 255, 255, 150), 0.8))
            p.setBrush(QColor(255, 255, 255, rnd.randint(10, 60)))
            p.drawPolygon(QPolygonF(pts))
    elif name == "Toxic Slime":
        img, p = _gradient_img([(0, (150, 255, 60)), (1, (40, 160, 20))])
        p.setPen(Qt.PenStyle.NoPen)
        for _ in range(18):
            p.setBrush(QColor(210, 255, 120, 90))
            p.drawEllipse(QPointF(rnd.uniform(0, N), rnd.uniform(0, N)), rnd.uniform(4, 12), rnd.uniform(4, 10))
        for _ in range(7):                                  # drips
            x = rnd.uniform(10, N - 10)
            p.setBrush(QColor(90, 200, 30, 220))
            p.drawRoundedRect(QRectF(x, rnd.uniform(60, 90), 5, rnd.uniform(14, 30)), 2.5, 2.5)
    elif name == "Lava":
        img, p = _img((40, 8, 4))
        p.setBrush(Qt.BrushStyle.NoBrush)
        for _ in range(16):
            path = QPainterPath(QPointF(rnd.uniform(0, N), rnd.uniform(0, N)))
            for _ in range(4):
                path.lineTo(path.currentPosition() + QPointF(rnd.uniform(-20, 20), rnd.uniform(-20, 20)))
            p.setPen(QPen(QColor(255, 120, 20, 220), rnd.uniform(1.2, 2.6)))
            p.drawPath(path)
    elif name == "Chrome":
        img, p = _gradient_img([(0, (250, 250, 255)), (0.35, (150, 155, 170)), (0.5, (240, 240, 250)),
                                (0.7, (110, 115, 130)), (1, (220, 222, 235))])
    elif name == "Gold":
        img, p = _gradient_img([(0, (255, 240, 160)), (0.35, (215, 160, 40)), (0.55, (255, 225, 120)),
                                (0.8, (170, 115, 20)), (1, (240, 200, 90))])
    elif name == "Diamond":
        img, p = _gradient_img([(0, (235, 250, 255)), (1, (170, 210, 245))])
        for i in range(0, N, 16):
            for j in range(0, N, 16):
                p.setPen(QPen(QColor(255, 255, 255, 170), 0.8))
                p.setBrush(QColor(255, 255, 255, rnd.randint(0, 70)))
                p.drawPolygon(QPolygonF([QPointF(i + 8, j), QPointF(i + 16, j + 8), QPointF(i + 8, j + 16),
                                         QPointF(i, j + 8)]))
    elif name == "Bronze Ember":
        img, p = _gradient_img([(0, (230, 150, 80)), (0.5, (150, 80, 30)), (1, (90, 40, 15))])
    elif name == "Galaxy":
        img, p = _img((8, 6, 30))
        p.setPen(Qt.PenStyle.NoPen)
        for _ in range(4):
            g = QRadialGradient(QPointF(rnd.uniform(20, 108), rnd.uniform(20, 108)), 40)
            g.setColorAt(0, QColor(*rnd.choice([(120, 60, 220), (40, 120, 255), (255, 80, 180)]), 120))
            g.setColorAt(1, QColor(0, 0, 0, 0))
            p.setBrush(QBrush(g)); p.drawRect(0, 0, N, N)
        for _ in range(70):
            p.setBrush(QColor(255, 255, 255, rnd.randint(120, 255)))
            p.drawEllipse(QPointF(rnd.uniform(0, N), rnd.uniform(0, N)), 0.7, 0.7)
    elif name == "Electric":
        img, p = _gradient_img([(0, (20, 40, 110)), (1, (5, 10, 40))])
    elif name == "Blue Flame":
        img, p = _gradient_img([(0, (140, 220, 255)), (0.5, (30, 110, 255)), (1, (10, 20, 90))])
    elif name == "Dark Matter":
        img, p = _img((6, 4, 12))
    elif name == "Aurora":
        img, p = _gradient_img([(0, (10, 20, 50)), (1, (2, 6, 20))])
    elif name == "Plasma":
        img, p = _img((40, 0, 60))
    elif name == "Void Glitch":
        img, p = _img((4, 4, 8))
    elif name == "Phoenix":
        img, p = _gradient_img([(0, (255, 220, 90)), (0.45, (255, 110, 30)), (1, (150, 20, 20))])
    elif name in ("Holographic", "Master Prism"):
        img, p = _img((0, 0, 0, 0))
    else:
        return None
    p.end()
    _cache[name] = img
    return img


# ---------------------------------------------------------------------------
def paint(p, name, path, body, t, frozen=False):
    """Fill Blip's body (`path`, inside rect `body`, 120-px grid) with the skin."""
    if not name or name == "None":
        return
    img = texture(name)
    if img is None:
        return
    if frozen:                       # asleep: the animation stops
        t = 0.0
    p.save()
    p.setClipPath(path)
    p.setOpacity(0.9)
    if name == "Galaxy":             # stars slowly swirl inside the glass
        p.translate(body.center())
        p.rotate(t * 8)
        p.translate(-body.center())
        p.drawImage(QRectF(body.center().x() - 70, body.center().y() - 70, 140, 140), img)
    elif name not in ("Holographic", "Master Prism"):
        p.drawImage(body.adjusted(-4, -4, 4, 4), img)
    _animate(p, name, body, t)
    p.restore()


def _animate(p, name, body, t):
    cx, cy = body.center().x(), body.center().y()
    if name in ("Holographic", "Master Prism"):
        g = QConicalGradient(QPointF(cx, cy), t * 40)
        cols = [(255, 80, 120), (255, 200, 60), (80, 255, 160), (60, 160, 255), (200, 80, 255), (255, 80, 120)]
        if name == "Master Prism":
            cols = [(255, 215, 80), (255, 120, 200), (255, 235, 150), (120, 220, 255), (255, 200, 60), (255, 215, 80)]
        for i, c in enumerate(cols):
            g.setColorAt(i / (len(cols) - 1), QColor(*c, 210))
        p.fillRect(body.adjusted(-4, -4, 4, 4), QBrush(g))
        if name == "Master Prism":
            _sparkles(p, body, t, 4)
    elif name == "Lava":                                     # cracks glow brighter and dimmer
        p.fillRect(body, QColor(255, 140, 30, int(40 + 35 * (1 + math.sin(t * 1.5)))))
    elif name == "Diamond":
        _sparkles(p, body, t, 3)
    elif name == "Bronze Ember":
        for i in range(6):
            u = (t * 0.4 + i / 6) % 1.0
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 170, 60, int(230 * (1 - u))))
            p.drawEllipse(QPointF(body.left() + (i * 37 % 100) / 100 * body.width(), body.bottom() - u * body.height()),
                          1.6, 1.6)
    elif name == "Electric":
        seed = int(t * 3)                                    # new lightning 3x a second (cached)
        key = (seed, round(body.left()), round(body.top()), round(body.width()), round(body.height()))
        if _bolts.get("key") != key:
            rnd = random.Random(seed)
            paths = []
            for _ in range(2):
                path = QPainterPath(QPointF(rnd.uniform(body.left(), body.right()), body.top()))
                for k in range(5):
                    path.lineTo(QPointF(rnd.uniform(body.left(), body.right()),
                                        body.top() + (k + 1) * body.height() / 5))
                paths.append(path)
            _bolts.update(key=key, paths=paths)
        p.setPen(QPen(QColor(150, 230, 255, 230), 1.4)); p.setBrush(Qt.BrushStyle.NoBrush)
        for path in _bolts["paths"]:
            p.drawPath(path)
    elif name == "Blue Flame":
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(6):
            x = body.left() + (i + 0.5) * body.width() / 6
            h = 10 + 6 * math.sin(t * 6 + i)
            p.setBrush(QColor(170, 235, 255, 150))
            p.drawEllipse(QPointF(x, body.top() + h * 0.5), 4, h * 0.6)
    elif name == "Dark Matter":
        rnd = random.Random(int(t * 4))
        p.setPen(Qt.PenStyle.NoPen)
        for _ in range(8):
            p.setBrush(QColor(190, 90, 255, rnd.randint(120, 255)))
            p.drawEllipse(QPointF(rnd.uniform(body.left(), body.right()), rnd.uniform(body.top(), body.bottom())), 1.4, 1.4)
    elif name == "Aurora":
        for i, col in enumerate(((60, 255, 160), (140, 90, 255), (60, 200, 255))):
            path = QPainterPath(QPointF(body.left(), cy))
            for k in range(9):
                x = body.left() + k * body.width() / 8
                path.lineTo(QPointF(x, cy - 10 + i * 8 + 7 * math.sin(t * 1.2 + k * 0.8 + i)))
            p.setPen(QPen(QColor(*col, 150), 6)); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
    elif name == "Plasma":
        for i, col in enumerate(((255, 60, 200), (60, 160, 255), (255, 160, 40))):
            g = QRadialGradient(QPointF(cx + 18 * math.sin(t * 0.9 + i * 2), cy + 14 * math.cos(t * 1.1 + i)), 30)
            g.setColorAt(0, QColor(*col, 200)); g.setColorAt(1, QColor(*col, 0))
            p.fillRect(body, QBrush(g))
    elif name == "Void Glitch":
        rnd = random.Random(int(t * 5))
        for _ in range(4):
            y = rnd.uniform(body.top(), body.bottom())
            p.fillRect(QRectF(body.left() + rnd.uniform(-6, 6), y, body.width(), rnd.uniform(2, 6)),
                       QColor(*rnd.choice([(0, 255, 200), (255, 0, 120), (120, 120, 255)]), 170))
    elif name == "Phoenix":
        p.fillRect(body, QColor(255, 200, 80, int(30 + 25 * math.sin(t * 3))))


def _sparkles(p, body, t, n):
    for i in range(n):
        u = (t * 0.7 + i / n) % 1.0
        a = math.sin(u * math.pi)
        x = body.left() + ((i * 53) % 100) / 100 * body.width()
        y = body.top() + ((i * 31 + 20) % 100) / 100 * body.height()
        p.setPen(QPen(QColor(255, 255, 255, int(255 * a)), 1.2))
        r = 4 * a
        p.drawLine(QPointF(x - r, y), QPointF(x + r, y))
        p.drawLine(QPointF(x, y - r), QPointF(x, y + r))


def paint_wings(p, body, t):
    """Phoenix: fire wings (shown while jumping / flying)."""
    for side in (-1, 1):
        path = QPainterPath(QPointF(body.center().x() + side * body.width() * 0.4, body.center().y()))
        flap = math.sin(t * 14) * 8
        path.quadTo(QPointF(body.center().x() + side * (body.width() * 0.9), body.top() - 10 + flap),
                    QPointF(body.center().x() + side * (body.width() * 0.95), body.center().y() + 12))
        path.closeSubpath()
        g = QLinearGradient(QPointF(body.center().x(), body.top()), QPointF(body.center().x(), body.bottom()))
        g.setColorAt(0, QColor(255, 230, 100, 200)); g.setColorAt(1, QColor(255, 60, 20, 160))
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(g)); p.drawPath(path)


def paint_aura(p, prestige, center, radius, t):
    """Subtle prestige ring around Blip."""
    if prestige <= 0:
        return
    col = AURA[min(prestige, 10)]
    if col == "rainbow":
        g = QConicalGradient(center, t * 60)
        for i, c in enumerate(((255, 215, 80), (255, 120, 200), (120, 220, 255), (255, 215, 80))):
            g.setColorAt(i / 3, QColor(*c, 160))
        p.setPen(QPen(QBrush(g), 2.2))
    else:
        p.setPen(QPen(QColor(*col, 120 + int(40 * math.sin(t * 2))), 1.8))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(center, radius, radius)
