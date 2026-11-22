"""
Desktop pet - the Prestige Shop: things you buy with Prestige Tokens.
Tokens: 3 per prestige + 1 for every 10 levels you gain (so new players get some too).
Everything is drawn in code, and only the equipped items are drawn.
Slots: hat, glasses, extra (neck/back), trail (while walking or flying), tag (name-tag colour),
emotes (extra moves in Play > Emotes).
Developed by Tunes
"""
import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QLinearGradient, QPainterPath, QPen, QPolygonF

# id: (slot, price in tokens, prestige needed)
ITEMS = {
    # glasses
    "Sunglasses": ("glasses", 1, 0), "Pixel shades": ("glasses", 2, 0), "Aviators": ("glasses", 2, 0),
    "Heart glasses": ("glasses", 2, 0), "3D glasses": ("glasses", 2, 0), "Monocle": ("glasses", 3, 1),
    "Visor": ("glasses", 4, 2),
    # hats (also wearable from Customise once bought)
    "Beanie": ("hat", 1, 0), "Cowboy hat": ("hat", 2, 0), "Top hat": ("hat", 2, 0), "Chef hat": ("hat", 2, 0),
    "Graduation cap": ("hat", 2, 0), "Wizard hat": ("hat", 3, 1), "Viking helmet": ("hat", 3, 1),
    "Silver crown": ("hat", 3, 1), "Halo": ("hat", 4, 2), "Horns": ("hat", 4, 2), "Gem crown": ("hat", 6, 3),
    # extras
    "Bow tie": ("extra", 1, 0), "Scarf": ("extra", 1, 0), "Headband": ("extra", 1, 0),
    "Gold chain": ("extra", 3, 1), "Cape": ("extra", 4, 2),
    # trails
    "Sparkle trail": ("trail", 2, 0), "Heart trail": ("trail", 2, 0), "Star trail": ("trail", 3, 1),
    "Rainbow trail": ("trail", 4, 2), "Fire trail": ("trail", 5, 3),
    # name-tag colours
    "Gold tag": ("tag", 1, 0), "Neon tag": ("tag", 1, 0), "Rainbow tag": ("tag", 3, 1),
    # emotes
    "Wave": ("emote", 1, 0), "Flex": ("emote", 2, 0), "Laugh": ("emote", 2, 0),
}
SLOTS = ["glasses", "hat", "extra", "trail", "tag", "emote"]
SLOT_NAMES = {"glasses": "Glasses", "hat": "Hats", "extra": "Extras", "trail": "Trails",
              "tag": "Name tags", "emote": "Emotes"}
TAG_COLOURS = {"Gold tag": ((255, 215, 80), (200, 140, 30)), "Neon tag": ((0, 255, 200), (255, 60, 220)),
               "Rainbow tag": "rainbow"}


def col(r, g, b, a=255):
    return QColor(r, g, b, a)


# ---------------------------------------------------------------------------
def draw_glasses(p, name, ex_l, ex_r, eye_y):
    """Glasses over the eyes (positions on the 120-px grid)."""
    if not name:
        return
    p.save()
    w = 11
    if name == "Sunglasses" or name == "Aviators":
        p.setPen(QPen(col(30, 30, 40), 1.6))
        g = QLinearGradient(0, eye_y - 6, 0, eye_y + 6)
        g.setColorAt(0, col(40, 40, 60, 240)); g.setColorAt(1, col(10, 10, 20, 240))
        if name == "Aviators":
            g.setColorAt(0, col(255, 190, 90, 220)); g.setColorAt(1, col(200, 90, 40, 220))
        p.setBrush(QBrush(g))
        for x in (ex_l, ex_r):
            if name == "Aviators":
                p.drawEllipse(QRectF(x - w / 2 - 1, eye_y - 6, w + 2, 12))
            else:
                p.drawRoundedRect(QRectF(x - w / 2 - 1, eye_y - 5, w + 2, 10), 3, 3)
        p.drawLine(QPointF(ex_l + w / 2, eye_y - 2), QPointF(ex_r - w / 2, eye_y - 2))
        p.setPen(QPen(col(255, 255, 255, 120), 1.2))
        for x in (ex_l, ex_r):
            p.drawLine(QPointF(x - 3, eye_y - 3), QPointF(x - 1, eye_y - 3))
    elif name == "Pixel shades":                         # "deal with it"
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(col(10, 10, 14))
        px = 2.4
        p.drawRect(QRectF(ex_l - 9, eye_y - 4, ex_r - ex_l + 18, px))
        for x in (ex_l, ex_r):
            for i in range(4):
                p.drawRect(QRectF(x - 6 + i * px * 0.6, eye_y - 4 + px, 12 - i * px * 1.2, px))
        p.setBrush(col(255, 255, 255))
        for x in (ex_l, ex_r):
            p.drawRect(QRectF(x - 4, eye_y - 4 + px, px, px))
    elif name == "Heart glasses":
        p.setPen(QPen(col(180, 20, 80), 1.2)); p.setBrush(col(255, 70, 140, 220))
        for x in (ex_l, ex_r):
            path = QPainterPath(QPointF(x, eye_y + 6))
            path.cubicTo(x - 10, eye_y, x - 5, eye_y - 9, x, eye_y - 3)
            path.cubicTo(x + 5, eye_y - 9, x + 10, eye_y, x, eye_y + 6)
            p.drawPath(path)
        p.drawLine(QPointF(ex_l + 6, eye_y - 3), QPointF(ex_r - 6, eye_y - 3))
    elif name == "3D glasses":
        p.setPen(QPen(col(240, 240, 240), 1.4))
        p.setBrush(col(255, 40, 40, 200)); p.drawRect(QRectF(ex_l - 6, eye_y - 5, 12, 9))
        p.setBrush(col(40, 160, 255, 200)); p.drawRect(QRectF(ex_r - 6, eye_y - 5, 12, 9))
        p.drawLine(QPointF(ex_l + 6, eye_y - 2), QPointF(ex_r - 6, eye_y - 2))
    elif name == "Monocle":
        p.setPen(QPen(col(230, 190, 80), 1.6)); p.setBrush(col(255, 255, 255, 40))
        p.drawEllipse(QPointF(ex_r, eye_y), 7.5, 7.5)
        p.drawLine(QPointF(ex_r + 5, eye_y + 5), QPointF(ex_r + 9, eye_y + 22))
    elif name == "Visor":
        g = QLinearGradient(ex_l - 10, 0, ex_r + 10, 0)
        g.setColorAt(0, col(0, 230, 255, 200)); g.setColorAt(1, col(200, 80, 255, 200))
        p.setPen(QPen(col(255, 255, 255, 160), 1)); p.setBrush(QBrush(g))
        p.drawRoundedRect(QRectF(ex_l - 10, eye_y - 5, ex_r - ex_l + 20, 10), 5, 5)
    p.restore()


def draw_extra(p, name, body, bw, t, behind=False):
    """Neck / back items. Capes are drawn behind the body (behind=True)."""
    if not name:
        return
    cx, top, bottom = body.center().x(), body.top(), body.bottom()
    neck_y = bottom - body.height() * 0.22
    p.save()
    p.setPen(Qt.PenStyle.NoPen)
    if name == "Cape" and behind:
        sway = math.sin(t * 2.5) * 4
        path = QPainterPath(QPointF(cx - bw * 0.35, top + 18))
        path.quadTo(QPointF(cx - bw * 0.65 + sway, bottom), QPointF(cx - bw * 0.45 + sway, bottom + 6))
        path.lineTo(QPointF(cx + bw * 0.45 + sway, bottom + 6))
        path.quadTo(QPointF(cx + bw * 0.65 + sway, bottom), QPointF(cx + bw * 0.35, top + 18))
        path.closeSubpath()
        g = QLinearGradient(cx, top, cx, bottom)
        g.setColorAt(0, col(200, 30, 60, 230)); g.setColorAt(1, col(120, 10, 40, 230))
        p.setBrush(QBrush(g)); p.drawPath(path)
    elif behind:
        pass
    elif name == "Bow tie":
        p.setBrush(col(220, 40, 70))
        for side in (-1, 1):
            p.drawPolygon(QPolygonF([QPointF(cx, neck_y), QPointF(cx + side * 9, neck_y - 5),
                                     QPointF(cx + side * 9, neck_y + 5)]))
        p.setBrush(col(255, 120, 140)); p.drawEllipse(QPointF(cx, neck_y), 2.6, 2.6)
    elif name == "Scarf":
        p.setBrush(col(255, 90, 60, 230))
        p.drawRoundedRect(QRectF(cx - bw * 0.36, neck_y - 4, bw * 0.72, 8), 4, 4)
        p.setBrush(col(255, 200, 80, 230))
        for i in range(-3, 4):
            p.drawRect(QRectF(cx + i * bw * 0.1 - 1, neck_y - 4, 2.5, 8))
        p.setBrush(col(255, 90, 60, 230))
        p.drawRoundedRect(QRectF(cx + bw * 0.12, neck_y, 7, 16 + math.sin(t * 3) * 2), 3, 3)
    elif name == "Headband":
        p.setBrush(col(255, 255, 255, 230))
        p.drawRoundedRect(QRectF(cx - bw * 0.45, top + body.height() * 0.16, bw * 0.9, 5), 2.5, 2.5)
        p.setBrush(col(255, 60, 90))
        p.drawRect(QRectF(cx - bw * 0.45, top + body.height() * 0.16 + 1.5, bw * 0.9, 2))
    elif name == "Gold chain":
        p.setPen(QPen(col(255, 210, 70), 2)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(cx - bw * 0.3, neck_y - 14, bw * 0.6, 22), 200 * 16, 140 * 16)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(col(255, 220, 90))
        p.drawEllipse(QPointF(cx, neck_y + 8), 4, 4)
    p.restore()


def draw_trail(p, name, size, t, facing, moving):
    """Little particles behind Blip while he walks or flies (inside his own window)."""
    if not name or not moving:
        return
    k = size / 120
    p.save()
    p.setPen(Qt.PenStyle.NoPen)
    for i in range(6):
        u = (t * 1.6 + i / 6) % 1.0
        x = (60 - facing * (34 + u * 26)) * k
        y = (100 - u * 30 - (i % 3) * 6) * k
        a = int(230 * (1 - u))
        if name == "Sparkle trail":
            p.setBrush(col(255, 255, 220, a)); p.drawEllipse(QPointF(x, y), 1.8 * k, 1.8 * k)
        elif name == "Heart trail":
            from character import draw_heart
            draw_heart(p, x, y, 3.5 * k, a)
        elif name == "Star trail":
            from antics import draw_star
            draw_star(p, x, y, 4 * k, a)
        elif name == "Rainbow trail":
            hue = (i * 60 + t * 120) % 360
            c = QColor.fromHsv(int(hue), 200, 255, a)
            p.setBrush(c); p.drawEllipse(QPointF(x, y), 3 * k, 3 * k)
        elif name == "Fire trail":
            p.setBrush(col(255, int(200 * (1 - u)), 40, a)); p.drawEllipse(QPointF(x, y), (3.5 - u * 2) * k, (4.5 - u * 2) * k)
    p.restore()


def draw_hat_extra(p, hat, cx, top, bw, t):
    """The shop hats (the basic hats are drawn in character.draw_hat). Returns True if drawn."""
    p.setPen(Qt.PenStyle.NoPen)
    if hat == "Beanie":
        p.setBrush(col(60, 120, 220)); p.drawChord(QRectF(cx - 22, top - 14, 44, 34), 0, 180 * 16)
        p.setBrush(col(255, 255, 255)); p.drawRoundedRect(QRectF(cx - 23, top + 1, 46, 6), 3, 3)
        p.drawEllipse(QPointF(cx, top - 15), 4.5, 4.5)
    elif hat == "Cowboy hat":
        p.setBrush(col(150, 95, 50)); p.drawEllipse(QRectF(cx - 32, top - 2, 64, 10))
        p.setBrush(col(170, 110, 60)); p.drawRoundedRect(QRectF(cx - 15, top - 18, 30, 20), 8, 8)
        p.setBrush(col(90, 50, 20)); p.drawRect(QRectF(cx - 15, top - 3, 30, 3))
    elif hat == "Top hat":
        p.setBrush(col(25, 25, 30)); p.drawRoundedRect(QRectF(cx - 24, top, 48, 6), 3, 3)
        p.drawRect(QRectF(cx - 14, top - 26, 28, 27))
        p.setBrush(col(200, 30, 50)); p.drawRect(QRectF(cx - 14, top - 6, 28, 4))
    elif hat == "Chef hat":
        p.setBrush(col(250, 250, 250))
        for dx in (-10, 0, 10):
            p.drawEllipse(QPointF(cx + dx, top - 14), 10, 10)
        p.drawRoundedRect(QRectF(cx - 15, top - 12, 30, 15), 3, 3)
    elif hat == "Graduation cap":
        p.setBrush(col(30, 30, 40))
        p.drawPolygon(QPolygonF([QPointF(cx - 28, top - 8), QPointF(cx, top - 18), QPointF(cx + 28, top - 8),
                                 QPointF(cx, top + 2)]))
        p.drawRect(QRectF(cx - 12, top - 6, 24, 9))
        p.setPen(QPen(col(255, 210, 60), 1.5))
        p.drawLine(QPointF(cx, top - 10), QPointF(cx + 20, top - 2 + math.sin(t * 3) * 2))
    elif hat == "Wizard hat":
        p.setBrush(col(70, 40, 160))
        p.drawPolygon(QPolygonF([QPointF(cx - 22, top + 4), QPointF(cx + 6, top - 40), QPointF(cx + 22, top + 4)]))
        p.drawEllipse(QRectF(cx - 28, top - 1, 56, 8))
        from antics import draw_star
        draw_star(p, cx + 2, top - 14, 4, 255)
    elif hat == "Viking helmet":
        p.setBrush(col(160, 165, 175)); p.drawChord(QRectF(cx - 22, top - 14, 44, 34), 0, 180 * 16)
        p.setBrush(col(245, 235, 210))
        for side in (-1, 1):
            p.drawPolygon(QPolygonF([QPointF(cx + side * 18, top - 4), QPointF(cx + side * 32, top - 20),
                                     QPointF(cx + side * 22, top + 2)]))
    elif hat in ("Silver crown", "Gem crown"):
        crown = QPolygonF([QPointF(cx - 16, top + 6), QPointF(cx - 18, top - 12), QPointF(cx - 8, top - 3),
                           QPointF(cx, top - 16), QPointF(cx + 8, top - 3), QPointF(cx + 18, top - 12),
                           QPointF(cx + 16, top + 6)])
        g = QLinearGradient(QPointF(cx, top - 16), QPointF(cx, top + 6))
        if hat == "Silver crown":
            g.setColorAt(0, col(250, 250, 255)); g.setColorAt(1, col(150, 155, 170))
        else:
            g.setColorAt(0, col(255, 240, 150)); g.setColorAt(1, col(230, 160, 30))
        p.setBrush(QBrush(g)); p.drawPolygon(crown)
        if hat == "Gem crown":
            for i, c in enumerate(((255, 40, 80), (40, 200, 255), (80, 255, 120))):
                p.setBrush(col(*c)); p.drawEllipse(QPointF(cx - 8 + i * 8, top - 1), 2.6, 2.6)
    elif hat == "Halo":
        p.setPen(QPen(col(255, 230, 120, 230), 3)); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(cx - 18, top - 18 + math.sin(t * 2) * 2, 36, 9))
    elif hat == "Horns":
        p.setBrush(col(200, 30, 40))
        for side in (-1, 1):
            p.drawPolygon(QPolygonF([QPointF(cx + side * 10, top + 6), QPointF(cx + side * 22, top - 14),
                                     QPointF(cx + side * 20, top + 8)]))
    else:
        return False
    return True
