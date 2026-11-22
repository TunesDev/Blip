"""
Desktop pet - dance moves while music plays (any player or Blip's radio).
Blip grows little glassy noodle arms and switches moves every 8-15 s, in time with the
beat (a simple "loudness jumped" beat guess from the volume meter):
  raise the roof, shuffle, (cute, PG) booty wiggle, floss, dab, robot, disco point, spin.
Now and then: a "Watch this!" big-move combo. Only runs while Blip is dancing.
Developed by Tunes
"""
import math
import os
import random
import time

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QPainterPath, QPen

import config
from character import THEMES, rgba

MOVES = ["roof", "shuffle", "wiggle", "floss", "dab", "robot", "disco"]   # (no spinning)


class Dancer:
    def __init__(self):
        self.move = random.choice(MOVES)
        self.move_until = 0.0
        self.last_beat = time.monotonic()
        self.period = 0.5             # seconds per beat (guessed)
        self.avg = 0.0
        self.big_until = 0.0
        self.next_big = time.monotonic() + random.uniform(60, 150)

    def update(self, now, level, pet):
        forced = os.getenv("BLIP_DANCE")                    # hidden: force one move
        # beat guess: loudness jumps well above its recent average
        self.avg = self.avg * 0.92 + level * 0.08
        if level > self.avg * 1.35 + 0.02 and now - self.last_beat > 0.28:
            gap = now - self.last_beat
            if gap < 1.0:
                self.period = self.period * 0.7 + gap * 0.3
            self.last_beat = now
        if forced in MOVES:
            self.move = forced
        elif now >= self.move_until:
            self.move = random.choice([m for m in MOVES if m != self.move])
            self.move_until = now + random.uniform(8, 15)
        if not forced and now >= self.next_big:              # the big combo, rarely
            self.next_big = now + random.uniform(90, 240)
            self.big_until = now + 3.0
            pet.bubble.say("Watch this!", "Big move incoming...", 2.5)

    def beat(self, now):
        """0..1 position inside the current beat, and a 1 -> 0 pulse right after it."""
        u = ((now - self.last_beat) / max(0.3, self.period)) % 1.0
        return u, max(0.0, 1.0 - u * 2.5)

    # ---- drawing -------------------------------------------------------------------------
    def paint(self, p, pet, level):
        now = time.monotonic()
        k = config.PET_SIZE / 120.0
        u, pulse = self.beat(now)
        lv = min(1.0, 0.35 + level * 1.8)
        move = self.move
        if now < self.big_until:                             # big move: spin, then dab
            move = "shuffle" if self.big_until - now > 1.2 else "dab"
        t = now - pet.start
        sw = math.sin(u * 2 * math.pi)                       # -1..1 swing on the beat
        f = pet.facing

        # body + where the hands go (all on the 120-px grid; shoulders ~ (60±27, 80))
        body = dict(state="idle", expr=None, music=True)
        hands = None
        if move == "roof":
            body.update(dy=-pulse * 6 * lv)
            push = 8 * pulse * lv
            hands = ((32, 38 - push), (88, 38 - push))
        elif move == "shuffle":
            pet.step = t * 14
            body.update(state="walk", dx=math.sin(t * 7) * 5)
            hands = ((30, 92 + sw * 6), (90, 92 - sw * 6))
        elif move == "wiggle":                               # cartoony booty wiggle (PG)
            body.update(angle=math.sin(t * 22) * 7 * lv, pivot=(60, 60), dy=2)
            hands = ((34, 100), (86, 100))                   # hands on knees
        elif move == "floss":
            x = math.sin(t * 7) * 34
            body.update(dx=-x * 0.12)
            hands = ((60 + x - 10, 104), (60 + x + 10, 100))
        elif move == "dab":
            on = (t % 2.4) < 1.0
            if on:
                body.update(angle=-f * 14, pivot=(60, 100))
                hands = ((60 - f * 52, 30), (60 + f * 4, 62))   # arm up + arm across the face
            else:
                body.update(dy=-pulse * 5)
                hands = ((30, 96), (90, 96))
        elif move == "robot":
            step = int(t * 4) % 4                            # stiff, jerky
            ang = (-8, 0, 8, 0)[step]
            body.update(angle=ang, pivot=(60, 100), dx=(-3, 0, 3, 0)[step], expr=None)
            up = (0, 1, 0, 1)[step]
            hands = ((30, 60 if up else 96), (90, 96 if up else 60))
        elif move == "disco":                                # Saturday-night point
            up = (int(t / max(0.35, self.period)) % 2) == 0
            body.update(angle=(-6 if up else 6) * f, pivot=(60, 100))
            hands = ((60 + f * 44, 22), (36, 96)) if up else ((60 - f * 30, 112), (88, 92))
        elif move == "spin":
            body.update(angle=(t * 360 / 1.4) % 360, pivot=(60, 76), dy=-4)
            hands = ((18, 74), (102, 74))
        pet.draw_body(p, **body)
        if hands and move != "spin":
            self.arms(p, k, hands, body.get("angle", 0.0), body.get("pivot", (60, 100)),
                      body.get("dx", 0.0), body.get("dy", 0.0))
        elif hands:
            p.save()
            p.translate(60 * k, 76 * k)
            p.rotate(body["angle"])
            p.translate(-60 * k, -76 * k)
            self.arms(p, k, hands, 0, (60, 76), 0, -4)
            p.restore()

    @staticmethod
    def arms(p, k, hands, angle, pivot, dx, dy):
        """Two glassy noodle arms from the shoulders to the hands."""
        main_c, accent = THEMES.get(config.THEME, THEMES["Nexus"])
        p.save()
        p.translate(dx * k, dy * k)
        if angle:
            p.translate(pivot[0] * k, pivot[1] * k)
            p.rotate(angle)
            p.translate(-pivot[0] * k, -pivot[1] * k)
        for side, (hx, hy) in zip((-1, 1), hands):
            sx, sy = 60 + side * 27, 82
            path = QPainterPath(QPointF(sx * k, sy * k))
            cx, cy = (sx + hx) / 2 + side * 10, (sy + hy) / 2 + 6     # a little bend = noodle
            path.quadTo(QPointF(cx * k, cy * k), QPointF(hx * k, hy * k))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(rgba(accent, 120), 7.5 * k, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawPath(path)
            p.setPen(QPen(rgba(main_c, 230), 4.5 * k, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawPath(path)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(rgba(accent, 240))
            p.drawEllipse(QPointF(hx * k, hy * k), 4.2 * k, 4.2 * k)          # hand
        p.restore()
