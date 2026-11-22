"""
Desktop pet - more random antics (v1.2). All drawn in code, a few seconds each.
  full auto (toy blaster goes off), banana slip, bubble gum, giant dumbbell, paper plane,
  balloon ride, hot chili, skateboard wipeout, magic trick gone wrong.
Developed by Tunes
"""
import math
import random

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainterPath, QPen, QPolygonF

import config
from antics import Antic, draw_star, s
from character import THEMES, rgba


def say_text(p, k, x, y, text, size=11, color=(255, 255, 255)):
    f = QFont("Segoe UI", 1); f.setBold(True); f.setPixelSize(int(size * k))
    p.setFont(f); p.setPen(QColor(*color))
    p.drawText(QPointF(x * k, y * k), text)


def stars(p, k, t, x=60, y=70):
    for i in range(3):
        a = t * 5 + i * 2.1
        draw_star(p, (x + math.cos(a) * 18) * k, (y + math.sin(a) * 6) * k, 5 * k, 230)


# ---------------------------------------------------------------------------
def draw_blaster(p, k, x, y, angle, f):
    """A chunky toy foam-dart blaster (original design)."""
    p.save()
    p.translate(x * k, y * k); p.rotate(angle); p.scale(f, 1)
    p.setPen(QPen(QColor(40, 30, 60), 1.2 * k))
    p.setBrush(QColor(255, 140, 30)); p.drawRoundedRect(QRectF(-14 * k, -7 * k, 28 * k, 12 * k), 4 * k, 4 * k)
    p.setBrush(QColor(60, 140, 255)); p.drawRect(QRectF(12 * k, -5 * k, 14 * k, 6 * k))
    p.setBrush(QColor(255, 230, 60)); p.drawRect(QRectF(-4 * k, 3 * k, 7 * k, 11 * k))
    p.setBrush(QColor(80, 220, 120)); p.drawEllipse(QPointF(-6 * k, -9 * k), 6 * k, 4 * k)   # dart drum
    p.restore()


class FullAuto(Antic):
    """Finds a toy blaster, holds the trigger by accident, recoil drags him across the screen."""
    duration = 7.5
    margin = 110

    def __init__(self, pet):
        super().__init__(pet)
        self.dir = -pet.facing                       # recoil pushes him backwards
        self.darts = []
        self.casings = []
        self.rnd = random.Random()

    def update(self, dt):
        done = super().update(dt)
        t, pet = self.t, self.pet
        if 1.3 <= t < 4.3:                           # FIRING: recoil drags him
            pet.x_pos += self.dir * 140 * dt
            if self.rnd.random() < 0.7:
                self.darts.append([0.0, self.rnd.uniform(-0.25, 0.25)])
                self.casings.append([0.0, self.rnd.uniform(-1, 1)])
        elif t >= 5.2:                               # tiptoe away
            pet.x_pos -= self.dir * 25 * dt
            pet.step += dt * 6
        left, right = pet.walk_bounds()
        pet.x_pos = max(left, min(pet.x_pos, right))
        for d in self.darts:
            d[0] += dt
        for c in self.casings:
            c[0] += dt
        self.darts = [d for d in self.darts if d[0] < 0.6]
        self.casings = [c for c in self.casings if c[0] < 0.8]
        if 1.3 <= t and int((t - dt) * 6) != int(t * 6) and t < 4.3:
            __import__("extras").play("boop")
        return done

    def paint(self, p):
        k, t = s(), self.t
        f = -self.dir                                # facing = where the blaster points
        if t < 0.8:                                  # spots the blaster
            self.pet.draw_body(p, state="idle", expr="happy", look=(f, 0.6))
            draw_blaster(p, k, 60 + f * 40, 106, 0, f)
        elif t < 1.3:                                # picks it up
            self.pet.draw_body(p, state="idle", expr="happy")
            draw_blaster(p, k, 60 + f * 30, 86, 0, f)
        elif t < 4.3:                                # oops, full auto
            lean = -f * (14 + math.sin(t * 30) * 4)       # skidding backwards, leaning into it
            self.pet.draw_body(p, state="fall", expr=None, angle=lean, pivot=(60, 110),
                               dx=math.sin(t * 40) * 1.5)
            p.setPen(Qt.PenStyle.NoPen)
            for i in range(3):                             # dust puffs from his skidding feet
                u = (t * 3 + i / 3) % 1.0
                p.setBrush(QColor(220, 220, 230, int(150 * (1 - u))))
                p.drawEllipse(QPointF((60 + f * (10 + u * 22)) * k, (110 - u * 6) * k), (3 + u * 4) * k, (2 + u * 3) * k)
            gx, gy = 60 + f * 30, 84
            draw_blaster(p, k, gx, gy, math.sin(t * 30) * 8, f)
            p.setPen(Qt.PenStyle.NoPen)
            if int(t * 20) % 2 == 0:                 # muzzle flash
                p.setBrush(QColor(255, 240, 120, 230))
                p.drawEllipse(QPointF((gx + f * 30) * k, (gy - 2) * k), 6 * k, 4 * k)
            for age, spread in self.darts:           # foam darts
                x = gx + f * (30 + age * 260); y = gy - 2 + spread * age * 120
                p.setBrush(QColor(60, 140, 255)); p.drawRoundedRect(QRectF(x * k, y * k, 9 * k, 3 * k), 1.5 * k, 1.5 * k)
                p.setBrush(QColor(255, 120, 40)); p.drawEllipse(QPointF((x + (9 if f > 0 else 0)) * k, (y + 1.5) * k), 2 * k, 2 * k)
            for age, side in self.casings:           # little casings bouncing out
                x = gx - f * age * 50 + side * 6; y = gy - 10 - math.sin(min(1, age * 2) * math.pi) * 16 + age * 40
                p.setBrush(QColor(255, 210, 60, int(255 * (1 - age / 0.8))))
                p.drawRect(QRectF(x * k, y * k, 3 * k, 2 * k))
            p.setBrush(QColor(110, 210, 255, 220))   # sweat drop
            p.drawEllipse(QPointF((60 - f * 30) * k, 58 * k), 3 * k, 4 * k)
        elif t < 5.2:                                # *click* ... drops it
            self.pet.draw_body(p, state="fall", expr=None)
            u = (t - 4.3) / 0.9
            draw_blaster(p, k, 60 + f * 30, 84 + u * 22, u * 90, f)
            say_text(p, k, 60 + f * 20, 40, "*click*", 10)
        else:                                        # tiptoes away, whistling
            self.pet.draw_body(p, state="walk", expr=None, dy=-abs(math.sin(t * 8)) * 3, look=(-f, -0.4))
            draw_blaster(p, k, 60 + f * (40 + (t - 5.2) * 8), 106, 90, f)
            say_text(p, k, 74, 40, "la la la", 9, (200, 230, 255))


class BananaSlip(Antic):
    duration = 4.2
    margin = 60
    walking_ok = True

    def paint(self, p):
        k, t, f = s(), self.t, self.pet.facing
        px = 60 + f * max(0, 46 - t * 40)            # the peel comes to his feet
        if t < 1.1:
            self.pet.draw_body(p, state="walk", expr=None)
            self.peel(p, k, px)
        elif t < 2.8:                                 # whoops! flat on his back
            u = min(1, (t - 1.1) / 0.3)
            self.pet.draw_body(p, state="fall", expr=None, angle=-f * 95 * u, pivot=(60, 108),
                               dy=-math.sin(u * math.pi) * 20)
            self.peel(p, k, px + f * 30 * u)
            if t > 1.5:
                stars(p, k, t, 60, 60)
        else:
            self.pet.draw_body(p, state="idle", expr="happy" if t > 3.4 else None,
                               dx=math.sin(t * 30) * 3 * max(0, 3.4 - t))

    def update(self, dt):
        if 1.0 < self.t < 1.6:
            self.pet.x_pos += self.pet.facing * 60 * dt
        return super().update(dt)

    @staticmethod
    def peel(p, k, x):
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(255, 220, 60))
        for a in (-35, 0, 35):
            p.save(); p.translate(x * k, 110 * k); p.rotate(a)
            p.drawEllipse(QRectF(-3 * k, -10 * k, 6 * k, 10 * k)); p.restore()


class BubbleGum(Antic):
    duration = 4.0
    margin = 40

    def paint(self, p):
        k, t = s(), self.t
        self.pet.draw_body(p, state="idle", expr=None, blink=0.4)
        if t < 2.4:                                   # blowing...
            r = 3 + t * 9
            p.setPen(QPen(QColor(255, 150, 200), 1 * k)); p.setBrush(QColor(255, 150, 200, 200))
            p.drawEllipse(QPointF((60 + self.pet.look[0] * 4) * k, (88 + r * 0.3) * k), r * k, r * k)
        else:                                          # POP - gum all over his face
            u = min(1, (t - 2.4) / 0.2)
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(255, 150, 200, int(220 * max(0, 1 - (t - 3.2)))))
            for i in range(7):
                a = i * 0.9
                p.drawEllipse(QPointF((60 + math.cos(a) * 16 * u) * k, (78 + math.sin(a) * 10 * u) * k), 7 * k, 5 * k)
            if t < 2.8:
                say_text(p, k, 74, 46, "POP!", 12, (255, 120, 180))


class Dumbbell(Antic):
    duration = 5.0
    margin = 50

    def paint(self, p):
        k, t = s(), self.t
        if t < 2.2:                                   # strain...
            shake = math.sin(t * 50) * (1.5 + t)
            self.pet.draw_body(p, state="idle", expr="grumpy", dx=shake)
            lift = max(0, (t - 1.2) * 18)
            self.bell(p, k, 92 - lift)
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(255, 60, 60, int(60 * t / 2.2)))
            p.drawEllipse(QPointF(60 * k, 78 * k), 32 * k, 28 * k)
        elif t < 3.8:                                  # ...SQUASH
            p.save()
            p.translate(60 * k, 112 * k); p.scale(1.4, 0.35); p.translate(-60 * k, -112 * k)
            self.pet.draw_body(p, state="land", expr=None)
            p.restore()
            self.bell(p, k, 92)
            stars(p, k, t, 60, 86)
        else:                                          # pops back out
            u = (t - 3.8) / 1.2
            self.pet.draw_body(p, state="idle", expr="happy", dy=-math.sin(min(1, u * 2) * math.pi) * 14)
            self.bell(p, k, 92, alpha=int(255 * max(0, 1 - u * 2)))

    @staticmethod
    def bell(p, k, y, alpha=255):
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(90, 90, 100, alpha))
        p.drawRect(QRectF(14 * k, (y - 2) * k, 92 * k, 4 * k))
        p.setBrush(QColor(40, 40, 50, alpha))
        for x in (8, 100):
            p.drawRoundedRect(QRectF(x * k, (y - 14) * k, 12 * k, 28 * k), 3 * k, 3 * k)
        say_text(p, k, 48, y + 5, "500KG", 6, (255, 255, 255))


class PaperPlane(Antic):
    duration = 4.6
    margin = 90

    def paint(self, p):
        k, t, f = s(), self.t, self.pet.facing
        bonk = t > 3.3
        self.pet.draw_body(p, state="fall" if bonk else "idle", expr="happy" if t < 1 else None,
                           look=(math.cos(t * 2.2) * f, -0.6) if 0.6 < t < 3.3 else None)
        if t < 3.3:                                    # out... loop the loop... and back
            a = t / 3.3 * 2 * math.pi
            x = 60 + f * math.sin(a) * 70
            y = 50 - (1 - math.cos(a)) * 30
            ang = math.degrees(math.atan2(math.sin(a + 0.05) - math.sin(a), 1)) + (0 if f > 0 else 180)
            p.save(); p.translate(x * k, y * k); p.rotate(ang * 0.6 + a * 57 * f)
            p.setPen(QPen(QColor(180, 190, 210), 0.8 * k)); p.setBrush(QColor(250, 250, 255))
            p.drawPolygon(QPolygonF([QPointF(10 * k, 0), QPointF(-8 * k, -6 * k), QPointF(-4 * k, 0),
                                     QPointF(-8 * k, 6 * k)]))
            p.restore()
        else:
            stars(p, k, t, 60, 56)
            say_text(p, k, 72, 44, "BONK", 10, (255, 230, 120))


class Balloon(Antic):
    duration = 5.5
    margin = 70
    controls_y = True

    def __init__(self, pet):
        super().__init__(pet)
        self.y0 = pet.y_pos
        self.fall_at_end = True

    def update(self, dt):
        done = super().update(dt)
        t = self.t
        if 0.8 < t < 4.2:
            self.pet.y_pos = self.y0 - min(260, (t - 0.8) ** 1.5 * 90)
            self.pet.x_pos += math.sin(t * 2) * 30 * dt
        if done:
            self.pet.vx, self.pet.vy = 0.0, 0.0       # POP: back down with the normal gravity
        return done

    def paint(self, p):
        k, t = s(), self.t
        popped = t > 4.2
        panic = 1.6 < t < 4.2
        self.pet.draw_body(p, state="fall" if panic or popped else "idle",
                           expr="happy" if t < 1.6 else None)
        if panic:
            from dance import Dancer
            flap = math.sin(t * 30) * 14
            Dancer.arms(p, k, ((20, 60 + flap), (100, 60 - flap)), 0, (60, 110), 0, 0)
        if not popped:
            p.setPen(QPen(QColor(255, 255, 255, 160), 0.8 * k))
            p.drawLine(QPointF(60 * k, 46 * k), QPointF((60 + math.sin(t * 2) * 4) * k, 4 * k + 18 * k))
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(255, 70, 110, 235))
            p.drawEllipse(QPointF((60 + math.sin(t * 2) * 4) * k, 8 * k), 13 * k, 15 * k)
            p.setBrush(QColor(255, 255, 255, 90)); p.drawEllipse(QPointF((56 + math.sin(t * 2) * 4) * k, 3 * k), 3 * k, 4 * k)
            if panic:
                say_text(p, k, 80, 40, "too high!", 9, (255, 230, 120))
        else:
            say_text(p, k, 50, 20, "POP!", 13, (255, 120, 150))


class Chili(Antic):
    duration = 4.6
    margin = 90

    def paint(self, p):
        k, t, f = s(), self.t, self.pet.facing
        if t < 1.2:                                    # munch
            self.pet.draw_body(p, state="idle", expr="happy")
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(230, 30, 30))
            p.drawEllipse(QRectF((60 + f * 8) * k, 88 * k, 14 * k, 6 * k))
            p.setBrush(QColor(40, 160, 60)); p.drawRect(QRectF((60 + f * 8 + (14 if f > 0 else -2)) * k, 89 * k, 3 * k, 3 * k))
            return
        hot = min(1, (t - 1.2) / 0.6)
        self.pet.draw_body(p, state="fall", expr=None, dx=math.sin(t * 40) * 2 * hot)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(255, 40, 30, int(110 * hot * max(0, min(1, 4.4 - t)))))
        p.drawEllipse(QPointF(60 * k, 78 * k), 34 * k, 30 * k)
        if 1.8 < t < 3.8:                              # fire breath
            for i in range(10):
                u = ((t * 3 + i / 10) % 1.0)
                x = 60 + f * (22 + u * 70); y = 90 + math.sin(i * 7 + t * 10) * u * 10
                p.setBrush(QColor(255, int(220 * (1 - u)), 40, int(230 * (1 - u))))
                p.drawEllipse(QPointF(x * k, y * k), (4 + u * 6) * k, (3 + u * 5) * k)
        if t > 1.4:
            say_text(p, k, 70, 34, "HOT!", 12, (255, 200, 80))


class Skateboard(Antic):
    duration = 4.4
    margin = 70
    walking_ok = True
    controls_y = False

    def __init__(self, pet):
        super().__init__(pet)
        self.fall_at_end = True

    def update(self, dt):
        done = super().update(dt)
        pet = self.pet
        if self.t < 3.0:
            pet.x_pos += pet.facing * 220 * dt
            left, right = pet.walk_bounds()
            if not left <= pet.x_pos <= right:
                pet.facing *= -1
                pet.x_pos = max(left, min(pet.x_pos, right))
        if done:                                       # wipeout: flies off with the normal physics
            pet.vx, pet.vy = pet.facing * 380, -520
        return done

    def paint(self, p):
        k, t, f = s(), self.t, self.pet.facing
        wobble = math.sin(t * 14) * (2 + t * 3)
        self.pet.draw_body(p, state="idle" if t < 2.4 else "fall", expr="happy" if t < 2.4 else None,
                           angle=wobble, pivot=(60, 112), dy=-8)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(60, 40, 90))
        p.drawRoundedRect(QRectF(30 * k, 108 * k, 60 * k, 5 * k), 2.5 * k, 2.5 * k)
        p.setBrush(QColor(255, 220, 60))
        for x in (38, 82):
            p.drawEllipse(QPointF(x * k, 115 * k), 3.2 * k, 3.2 * k)
        if t > 2.6:
            say_text(p, k, 66, 40, "uh oh", 10, (255, 230, 120))


class Magician(Antic):
    duration = 5.2
    margin = 70

    def paint(self, p):
        k, t, f = s(), self.t, self.pet.facing
        hx = 60 + f * 34
        surprised = t > 2.4
        self.pet.draw_body(p, state="fall" if surprised else "idle", expr="happy" if t < 2.0 else None)
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(25, 25, 30))       # the magic hat on the floor
        p.drawRoundedRect(QRectF((hx - 12) * k, 100 * k, 24 * k, 12 * k), 2 * k, 2 * k)
        p.drawRect(QRectF((hx - 16) * k, 98 * k, 32 * k, 3 * k))
        if t < 2.0:                                     # wave the wand...
            ang = math.sin(t * 10) * 30
            p.save(); p.translate((60 + f * 18) * k, 84 * k); p.rotate(ang - f * 50)
            p.setBrush(QColor(20, 20, 20)); p.drawRect(QRectF(0, -1.5 * k, 22 * k, 3 * k))
            p.setBrush(QColor(255, 255, 255)); p.drawRect(QRectF(18 * k, -1.5 * k, 4 * k, 3 * k)); p.restore()
            if t > 1.4:
                say_text(p, k, 40, 36, "Ta-da!", 11, (255, 230, 120))
        else:                                           # ...a pigeon bursts out and flaps off
            u = min(1, (t - 2.0) / 3.0)
            bx, by = hx + f * u * 30, 96 - u * 90
            flap = math.sin(t * 20) * 6
            p.setBrush(QColor(200, 205, 215))
            p.drawEllipse(QPointF(bx * k, by * k), 7 * k, 5 * k)
            p.drawEllipse(QPointF((bx + f * 6) * k, (by - 3) * k), 3.5 * k, 3.5 * k)
            for side in (-1, 1):
                p.drawEllipse(QRectF((bx - 6) * k, (by - 4 + side * flap) * k, 9 * k, 4 * k))
            p.setBrush(QColor(255, 170, 40))
            p.drawEllipse(QPointF((bx + f * 9.5) * k, (by - 3) * k), 1.5 * k, 1 * k)
            if surprised and t < 4:
                say_text(p, k, 72, 40, "?!", 12, (255, 255, 255))


NEW = {"fullauto": FullAuto, "banana": BananaSlip, "gum": BubbleGum, "dumbbell": Dumbbell,
       "plane": PaperPlane, "balloon": Balloon, "chili": Chili, "skate": Skateboard, "magic": Magician}
NEW_WEIGHTS = {"fullauto": 3, "banana": 3, "gum": 2, "dumbbell": 2, "plane": 2, "balloon": 2,
               "chili": 2, "skate": 2, "magic": 2}


import antics as _antics  # noqa: E402
_antics.ALL.update(NEW)
_antics.WEIGHTS.update(NEW_WEIGHTS)
