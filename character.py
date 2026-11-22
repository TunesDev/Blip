"""
Desktop pet - draws the character with code (no image files).
Glassmorphism body + glow. Supports several characters, colour themes and hats.
Developed by Tunes
"""
import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (QBrush, QColor, QFont, QLinearGradient, QPainter,
                         QPainterPath, QPen, QPolygonF, QRadialGradient)

import config

CHARACTERS = ["Blob", "Cat", "Bunny", "Ghost"]
HATS = ["None", "Santa hat", "Crown", "Headphones", "Bow"]
THEMES = {
    "Nexus":  ((150, 90, 255), (0, 225, 255)),    # purple / cyan
    "Ember":  ((255, 80, 60), (255, 180, 40)),    # red / orange
    "Mint":   ((30, 200, 140), (120, 255, 230)),  # green / aqua
    "Frost":  ((110, 160, 255), (225, 245, 255)), # blue / white
    "Sakura": ((255, 100, 185), (255, 215, 120)), # pink / gold
}
GRUMPY_RED = (255, 60, 90)


def rgba(rgb, alpha):
    return QColor(rgb[0], rgb[1], rgb[2], alpha)


def draw_pet(p: QPainter, size: int, state: str, t: float,
             facing: int = 1, blink: float = 0.0, step: float = 0.0,
             look=(0.0, 0.0), expr=None, character=None, theme=None, hat=None,
             sweat=False, sleepy=False, yawn=0.0, music=0.0, skin="auto"):
    """
    state     - "idle", "walk", "sleep", "held", "fall" or "land"
    t         - time in seconds (drives breathing / bobbing)
    facing    - 1 = right, -1 = left
    blink     - 0.0 open ... 1.0 closed
    step      - walking cycle (moves the feet)
    look      - (x, y) from -1 to 1: where the eyes look (your cursor)
    expr      - None, "happy" or "grumpy"
    character / theme / hat - looks; default to what's in config (settings)
    sweat     - True when your PC is working hard (sweat drops + worried brows)
    sleepy    - True late at night (droopy eyes)
    yawn      - 0.0 ... 1.0 how wide the yawn is right now (0 = not yawning)
    music     - 0 = no music; above 0 = music is playing, value = loudness 0..1
    """
    dancing = music > 0.0 and state in ("idle", "land")
    if music > 0.0 and state in ("idle", "land", "walk"):
        hat = "Headphones"                       # music on = headphones on
    yawning = yawn > 0.0 and state in ("idle", "land")
    character = character or config.CHARACTER
    main_c, accent = THEMES.get(theme or config.THEME, THEMES["Nexus"])
    hat = hat or __import__("extras").effective_hat()
    ghost = character == "Ghost"

    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size / 120.0                 # everything is designed on a 120px grid
    p.save()
    p.scale(s, s)

    cx = 60.0
    ground = 112.0

    # --- body shape per state ---------------------------------------------
    bob = 0.0
    if state == "sleep":
        br = math.sin(t * 1.6) * 1.5
        bw, bh = 72 + br, 54 - br
    elif state == "walk":
        bw, bh = 66, 62
        bob = -abs(math.sin(step)) * 4
    elif state in ("held", "fall"):
        bw, bh = 60, 68
    elif state == "land":
        bw, bh = 78, 50
    else:
        br = math.sin(t * 2.4) * 1.2
        bw, bh = 66 + br * 0.5, 62 - br
    if yawning:                                  # big stretch
        bw, bh = bw - 4 * yawn, bh + 6 * yawn
    if dancing and expr is None:                 # bounce to the beat
        lv = min(1.0, music * 2.2)
        bob = -lv * 9
        bw, bh = bw + lv * 5, bh - lv * 4
    if expr == "happy" and state in ("idle", "land"):
        bob = -abs(math.sin(t * 9)) * 3          # happy little bounces
    if ghost:
        bob += -6 + math.sin(t * 2.2) * 3        # ghosts float

    feet_h = 8
    body_bottom = ground - feet_h + 3 + bob
    body = QRectF(cx - bw / 2, body_bottom - bh, bw, bh)
    bcx, bcy = body.center().x(), body.center().y()

    glow_main = GRUMPY_RED if expr == "grumpy" else main_c
    glow_acc = GRUMPY_RED if expr == "grumpy" else accent

    # --- outer glow ---------------------------------------------------------
    dim = state == "sleep"
    glow = QRadialGradient(QPointF(bcx, bcy), 56)
    glow.setColorAt(0.0, rgba(glow_main, 70 if dim else 115))
    glow.setColorAt(0.55, rgba(glow_acc, 22 if dim else 42))
    glow.setColorAt(1.0, rgba(glow_acc, 0))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(glow))
    p.drawEllipse(QPointF(bcx, bcy), 56, 56)

    fill = QLinearGradient(body.topLeft(), body.bottomRight())
    fill.setColorAt(0.0, rgba(main_c, 170))
    fill.setColorAt(1.0, rgba(accent, 150))
    rim = QPen(QColor(255, 255, 255, 150), 1.6)

    # --- ears (behind the body) ----------------------------------------------
    if character == "Cat":
        p.setBrush(QBrush(fill)); p.setPen(rim)
        for side in (-1, 1):
            x0 = bcx + side * bw * 0.32
            ear = QPolygonF([QPointF(x0 - side * 12, body.top() + 10),
                             QPointF(x0 + side * 6, body.top() - 14),
                             QPointF(x0 + side * 14, body.top() + 12)])
            p.drawPolygon(ear)
    elif character == "Bunny":
        p.setBrush(QBrush(fill)); p.setPen(rim)
        for side in (-1, 1):
            tilt = side * (8 + (math.sin(t * 3) * 3 if state == "idle" else 0))
            p.save()
            p.translate(bcx + side * bw * 0.2, body.top() + 6)
            p.rotate(tilt)
            p.drawRoundedRect(QRectF(-6, -34, 12, 38), 6, 6)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255, 70))
            p.drawRoundedRect(QRectF(-2.5, -29, 5, 26), 3, 3)
            p.restore()
            p.setBrush(QBrush(fill)); p.setPen(rim)

    # --- feet (ghosts have none) ------------------------------------------------
    if not ghost:
        if state == "walk":
            lift_l, lift_r = max(0.0, math.sin(step)) * 5, max(0.0, -math.sin(step)) * 5
        elif state in ("held", "fall"):
            lift_l, lift_r = math.sin(t * 16) * 3, -math.sin(t * 16) * 3
        else:
            lift_l = lift_r = 0
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(rgba(accent, 190))
        p.drawRoundedRect(QRectF(cx - 22, ground - feet_h - lift_l, 16, feet_h), 4, 4)
        p.drawRoundedRect(QRectF(cx + 6, ground - feet_h - lift_r, 16, feet_h), 4, 4)

    # --- glass body ---------------------------------------------------------------
    path = QPainterPath()
    if ghost:
        r = bw / 2
        top = body.top()
        path.moveTo(body.left(), top + r)
        path.arcTo(QRectF(body.left(), top, bw, bw), 180, -180)
        bottom = body.bottom() + 4
        path.lineTo(body.right(), bottom)
        waves = 4
        for i in range(waves):                      # wavy ghost tail
            x1 = body.right() - (i + 0.5) * bw / waves
            x2 = body.right() - (i + 1) * bw / waves
            wob = math.sin(t * 5 + i) * 2
            path.quadTo(QPointF(x1, bottom - 9 + wob), QPointF(x2, bottom))
        path.closeSubpath()
    else:
        path.addRoundedRect(body, bw * 0.45, bh * 0.5)

    if skin == "auto":
        import progress
        skin = progress.get().skin
    if skin and skin != "None" and state in ("fall", "held") and skin == "Phoenix":
        import skins
        skins.paint_wings(p, body, t)
    p.setBrush(QBrush(fill))
    p.setPen(rim)
    p.drawPath(path)
    if skin and skin != "None":
        import skins
        skins.paint(p, skin, path, body, t, frozen=(state == "sleep"))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(rim)
        p.drawPath(path)

    shine = QRadialGradient(QPointF(bcx - bw * 0.2, body.top() + bh * 0.25), bw * 0.6)
    shine.setColorAt(0.0, QColor(255, 255, 255, 80))
    shine.setColorAt(1.0, QColor(255, 255, 255, 0))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(shine))
    p.drawPath(path)
    p.setBrush(QColor(255, 255, 255, 120))
    p.drawEllipse(QRectF(body.left() + bw * 0.16, body.top() + bh * 0.12, bw * 0.22, bh * 0.12))

    # --- face -------------------------------------------------------------------------
    if state == "walk":
        lx, ly = facing * 1.0, 0.0
    else:
        lx, ly = look
    look_x, look_y = lx * 4, ly * 3
    eye_y = bcy - bh * 0.04 + look_y
    eye_dx = bw * 0.18
    eye_col = QColor(240, 252, 255, 245)
    line_pen = QPen(QColor(235, 250, 255, 235), 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)

    for side, ex in ((-1, bcx - eye_dx + look_x), (1, bcx + eye_dx + look_x)):
        if state == "sleep" or (yawning and yawn > 0.35):
            p.setPen(line_pen); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(QRectF(ex - 6, eye_y - 4, 12, 8), 200 * 16, 140 * 16)       # ‿
        elif expr == "happy" or (dancing and expr is None):
            p.setPen(line_pen); p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(QRectF(ex - 6, eye_y - 3, 12, 10), 20 * 16, 140 * 16)       # ^
        else:
            eg = QRadialGradient(QPointF(ex, eye_y), 12)
            eg.setColorAt(0.0, rgba(glow_acc, 145))
            eg.setColorAt(1.0, rgba(glow_acc, 0))
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(eg))
            p.drawEllipse(QPointF(ex, eye_y), 12, 12)
            p.setBrush(eye_col)
            if state in ("held", "fall"):
                p.drawEllipse(QPointF(ex, eye_y), 6, 7)                           # O O
            else:
                h = 14 * (1.0 - blink)
                if expr == "grumpy":
                    h = min(h, 8)
                elif sleepy or yawning:
                    h = min(h, 9)                                                  # droopy
                h = max(2.0, h)
                p.drawRoundedRect(QRectF(ex - 4, eye_y - h / 2, 8, h), 4, 4)
            if expr == "grumpy":                                                   # angry brows
                p.setPen(QPen(QColor(255, 235, 240, 235), 2.6, Qt.PenStyle.SolidLine,
                              Qt.PenCapStyle.RoundCap))
                p.drawLine(QPointF(ex - 7 * side, eye_y - 12), QPointF(ex + 5 * side, eye_y - 7))
            elif sweat:                                                            # worried brows
                p.setPen(QPen(QColor(235, 250, 255, 220), 2.2, Qt.PenStyle.SolidLine,
                              Qt.PenCapStyle.RoundCap))
                p.drawLine(QPointF(ex + 6 * side, eye_y - 10), QPointF(ex - 5 * side, eye_y - 14))

    p.setPen(QPen(QColor(255, 255, 255, 175), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.setBrush(Qt.BrushStyle.NoBrush)
    mx = bcx + look_x
    if yawning:                                                                    # big O yawn
        mw, mh = 7 + 7 * yawn, 4 + 13 * yawn
        p.setBrush(QColor(40, 20, 70, 210))
        p.drawEllipse(QRectF(mx - mw / 2, eye_y + 6, mw, mh))
        p.setBrush(Qt.BrushStyle.NoBrush)
    elif state in ("held", "fall"):
        p.drawEllipse(QRectF(mx - 3.5, eye_y + 9, 7, 8))
    elif expr == "grumpy":
        p.drawLine(QPointF(mx - 5, eye_y + 11), QPointF(mx + 5, eye_y + 10))
    elif expr == "happy" or (dancing and expr is None):
        p.drawArc(QRectF(mx - 7, eye_y + 4, 14, 10), 200 * 16, 140 * 16)
    else:
        p.drawArc(QRectF(mx - 5, eye_y + 6, 10, 6), 200 * 16, 140 * 16)
    if character == "Cat" and state != "sleep":                                  # whiskers
        p.setPen(QPen(QColor(255, 255, 255, 110), 1.2))
        for side in (-1, 1):
            for dy in (-2, 2):
                p.drawLine(QPointF(mx + side * 12, eye_y + 9 + dy),
                           QPointF(mx + side * 24, eye_y + 8 + dy * 2))

    draw_hat(p, hat, body, bw, t)
    if music > 0.0 and state in ("idle", "land", "walk"):
        draw_notes(p, bcx, body.top(), bw, t, accent, main_c)

    # --- extras ---------------------------------------------------------------------
    if expr == "happy":
        rise = (t * 0.8) % 1.0
        draw_heart(p, bcx + 26, body.top() - 4 - rise * 18, 7, int(255 * (1 - rise)))
    if sweat and state != "sleep":
        for i, side in enumerate((1, -1)):
            phase = (t * 0.9 + i * 0.5) % 1.0
            x = bcx + side * (bw * 0.47 + phase * 4)
            y = body.top() + bh * 0.08 + phase * bh * 0.55
            draw_drop(p, x, y, 4.8, int(255 * (1 - phase) ** 0.5))
    if state == "sleep":
        font = QFont("Segoe UI", 1)
        font.setBold(True)
        for i in range(3):
            phase = (t * 0.35 + i / 3.0) % 1.0
            font.setPixelSize(int(9 + phase * 8))
            p.setFont(font)
            p.setPen(rgba(accent if i % 2 else main_c, int(255 * (1 - phase))))
            p.drawText(QPointF(bcx + 18 + phase * 14, body.top() - 2 - phase * 26), "z")

    p.restore()


def draw_heart(p, x, y, r, alpha):
    path = QPainterPath()
    path.moveTo(x, y + r * 0.9)
    path.cubicTo(x - r * 1.6, y - r * 0.2, x - r * 0.6, y - r * 1.3, x, y - r * 0.4)
    path.cubicTo(x + r * 0.6, y - r * 1.3, x + r * 1.6, y - r * 0.2, x, y + r * 0.9)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(255, 90, 160, alpha))
    p.drawPath(path)


def draw_notes(p, bcx, top, bw, t, accent, main_c):
    """Music notes floating up next to Blip. Drawn as shapes (not font symbols), because
    symbol/emoji fonts cost Windows ~40 MB of RAM the first time they're used."""
    for i, side in enumerate((-1, 1, -1)):
        phase = (t * 0.45 + i / 3.0) % 1.0
        s = 0.8 + phase * 0.4
        x = bcx + side * (bw * 0.5 + 4 + phase * 8) + math.sin(t * 3 + i) * 3
        y = top + 18 - phase * 28
        col = rgba(accent if i % 2 else main_c, int(255 * (1 - phase) ** 0.7))
        p.setPen(QPen(col, 1.6 * s))
        p.setBrush(col)
        p.drawEllipse(QPointF(x, y), 2.6 * s, 2.0 * s)              # note head
        p.drawLine(QPointF(x + 2.4 * s, y), QPointF(x + 2.4 * s, y - 9 * s))   # stem
        if i % 2:                                                 # double note: beam
            p.drawEllipse(QPointF(x + 7 * s, y - 1 * s), 2.6 * s, 2.0 * s)
            p.drawLine(QPointF(x + 9.4 * s, y - 1 * s), QPointF(x + 9.4 * s, y - 10 * s))
            p.drawLine(QPointF(x + 2.4 * s, y - 9 * s), QPointF(x + 9.4 * s, y - 10 * s))
        else:                                                     # flag
            p.drawLine(QPointF(x + 2.4 * s, y - 9 * s), QPointF(x + 5.5 * s, y - 6 * s))


def draw_drop(p, x, y, r, alpha):
    """A sweat drop: pointy on top, round at the bottom."""
    path = QPainterPath()
    path.moveTo(x, y - r * 2.2)
    path.cubicTo(x + r * 0.4, y - r * 1.2, x + r, y - r * 0.6, x + r, y)
    path.arcTo(QRectF(x - r, y - r, 2 * r, 2 * r), 0, -180)
    path.cubicTo(x - r, y - r * 0.6, x - r * 0.4, y - r * 1.2, x, y - r * 2.2)
    p.setPen(QPen(QColor(20, 90, 170, alpha), 1.0))
    p.setBrush(QColor(110, 210, 255, alpha))
    p.drawPath(path)
    p.setPen(Qt.PenStyle.NoPen)                      # little shine
    p.setBrush(QColor(255, 255, 255, int(alpha * 0.8)))
    p.drawEllipse(QPointF(x - r * 0.35, y - r * 0.2), r * 0.28, r * 0.28)


def draw_hat(p, hat, body, bw, t):
    top, cx = body.top(), body.center().x()
    p.setPen(Qt.PenStyle.NoPen)
    if hat == "Santa hat":
        path = QPainterPath()
        path.moveTo(cx - 20, top + 6)
        path.quadTo(QPointF(cx - 2, top - 26), QPointF(cx + 26, top - 14))
        path.quadTo(QPointF(cx + 10, top - 6), QPointF(cx + 20, top + 6))
        path.closeSubpath()
        p.setBrush(QColor(230, 40, 60, 235)); p.drawPath(path)
        p.setBrush(QColor(255, 255, 255, 240))
        p.drawRoundedRect(QRectF(cx - 24, top + 1, 48, 9), 4.5, 4.5)
        p.drawEllipse(QPointF(cx + 27, top - 14), 5, 5)
    elif hat == "Crown":
        crown = QPolygonF([QPointF(cx - 16, top + 6), QPointF(cx - 18, top - 12),
                           QPointF(cx - 8, top - 3), QPointF(cx, top - 16),
                           QPointF(cx + 8, top - 3), QPointF(cx + 18, top - 12),
                           QPointF(cx + 16, top + 6)])
        g = QLinearGradient(QPointF(cx, top - 16), QPointF(cx, top + 6))
        g.setColorAt(0, QColor(255, 235, 120)); g.setColorAt(1, QColor(240, 170, 30))
        p.setBrush(QBrush(g)); p.drawPolygon(crown)
        p.setBrush(QColor(0, 225, 255))
        p.drawEllipse(QPointF(cx, top - 1), 2.5, 2.5)
    elif hat == "Headphones":
        p.setPen(QPen(QColor(40, 40, 60, 230), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(cx - bw / 2 + 2, top - 8, bw - 4, 40), 20 * 16, 140 * 16)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(40, 40, 60, 240))
        for side in (-1, 1):
            p.drawRoundedRect(QRectF(cx + side * (bw / 2 - 2) - 6, top + 10, 12, 18), 5, 5)
        p.setBrush(QColor(0, 225, 255, 200))
        for side in (-1, 1):
            p.drawEllipse(QPointF(cx + side * (bw / 2 - 2), top + 19), 2.5, 2.5)
    elif hat == "Party hat":
        cone = QPolygonF([QPointF(cx - 14, top + 6), QPointF(cx + 2, top - 30), QPointF(cx + 16, top + 6)])
        g = QLinearGradient(QPointF(cx - 14, top), QPointF(cx + 16, top))
        g.setColorAt(0, QColor(255, 90, 170)); g.setColorAt(1, QColor(0, 225, 255))
        p.setBrush(QBrush(g)); p.drawPolygon(cone)
        p.setBrush(QColor(255, 235, 120))
        p.drawEllipse(QPointF(cx + 2, top - 31), 4, 4)
        for i, col in enumerate(((255, 255, 255), (255, 230, 90), (255, 255, 255))):
            p.setBrush(QColor(*col, 220))
            p.drawEllipse(QPointF(cx - 6 + i * 7, top - 6 - i * 7), 1.8, 1.8)
    elif hat == "Pumpkin":
        p.setBrush(QColor(255, 140, 30, 240))
        for dx in (-9, 0, 9):
            p.drawEllipse(QPointF(cx + dx, top - 4), 9, 10)
        p.setBrush(QColor(60, 140, 50))
        p.drawRoundedRect(QRectF(cx - 2, top - 19, 4, 7), 2, 2)
        p.setBrush(QColor(40, 20, 10, 220))                       # little face
        p.drawPolygon(QPolygonF([QPointF(cx - 7, top - 7), QPointF(cx - 3, top - 7), QPointF(cx - 5, top - 10)]))
        p.drawPolygon(QPolygonF([QPointF(cx + 3, top - 7), QPointF(cx + 7, top - 7), QPointF(cx + 5, top - 10)]))
        p.drawRect(QRectF(cx - 5, top - 2, 10, 2))
    elif hat == "Shamrock":
        p.setBrush(QColor(40, 190, 90, 240))
        sx, sy = cx + bw * 0.22, top - 4
        for a in (90, 210, 330):
            r = math.radians(a)
            p.drawEllipse(QPointF(sx + math.cos(r) * 6, sy - math.sin(r) * 6), 5.5, 5.5)
        p.setPen(QPen(QColor(30, 140, 70), 2))
        p.drawLine(QPointF(sx, sy), QPointF(sx + 3, sy + 10))
        p.setPen(Qt.PenStyle.NoPen)
    elif hat == "Bow":
        bx, by = cx + bw * 0.26, top + 4
        p.setBrush(QColor(255, 110, 180, 235))
        for side in (-1, 1):
            p.drawPolygon(QPolygonF([QPointF(bx, by), QPointF(bx + side * 12, by - 8),
                                     QPointF(bx + side * 12, by + 8)]))
        p.setBrush(QColor(255, 180, 215))
        p.drawEllipse(QPointF(bx, by), 3.5, 3.5)


def draw_snack(p: QPainter, size: int, t: float = 0.0):
    """A little glowing glass candy."""
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    main_c, accent = THEMES.get(config.THEME, THEMES["Nexus"])
    c = size / 2
    r = size * 0.28
    g = QRadialGradient(QPointF(c, c), c)
    g.setColorAt(0, rgba(accent, 120)); g.setColorAt(1, rgba(accent, 0))
    p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(g))
    p.drawEllipse(QPointF(c, c), c, c)
    p.setBrush(QColor(255, 255, 255, 200))   # wrapper twists
    for side in (-1, 1):
        p.drawPolygon(QPolygonF([QPointF(c + side * r * 0.8, c),
                                 QPointF(c + side * r * 1.7, c - r * 0.6),
                                 QPointF(c + side * r * 1.7, c + r * 0.6)]))
    body = QRadialGradient(QPointF(c - r * 0.3, c - r * 0.3), r * 1.4)
    body.setColorAt(0, QColor(255, 255, 255, 230)); body.setColorAt(0.4, rgba(main_c, 230))
    body.setColorAt(1, rgba(accent, 230))
    p.setBrush(QBrush(body))
    p.setPen(QPen(QColor(255, 255, 255, 170), 1))
    p.drawEllipse(QPointF(c, c), r, r)
