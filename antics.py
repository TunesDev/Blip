"""
Desktop pet - random antics, just for a laugh. All drawn in code.
Each antic runs for a few seconds, then Blip goes back to normal. Clicking Blip cancels it.
While an antic runs, Blip's window grows a little (a see-through margin) so things like the
football fit around it; the NFL throw also uses one temporary "friend" window.
Nothing here runs between antics.
Developed by Tunes
"""
import math
import random

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget

import config
from character import THEMES, draw_pet, rgba

FREQUENCY = {"Off": None, "Rare": (8 * 60, 15 * 60), "Normal": (3 * 60, 8 * 60), "Lots": (60, 3 * 60)}


def s():
    return config.PET_SIZE / 120.0


class Antic:
    margin = 0          # extra see-through space around Blip (px, at size 120)
    walking_ok = False  # may start while walking

    def __init__(self, pet):
        self.pet = pet
        self.t = 0.0

    def update(self, dt):
        """Advance; return True when finished."""
        self.t += dt
        return self.t >= self.duration

    def paint(self, p):
        self.pet.draw_body(p)

    def end(self):
        pass


# ---------------------------------------------------------------------------
def draw_star(p, x, y, r, alpha, color=(255, 230, 90)):
    path = QPainterPath()
    for i in range(10):
        a = math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pt = QPointF(x + math.cos(a) * rr, y - math.sin(a) * rr)
        path.moveTo(pt) if i == 0 else path.lineTo(pt)
    path.closeSubpath()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(*color, alpha))
    p.drawPath(path)


class Trip(Antic):
    """Stumbles, faceplants, sees stars, gets up and shakes it off."""
    duration = 3.2
    margin = 30
    walking_ok = True

    def paint(self, p):
        t, k = self.t, s()
        f = self.pet.facing
        if t < 0.35:                                   # stumble forward
            ang = f * 25 * (t / 0.35)
            self.pet.draw_body(p, state="fall", angle=ang)
        elif t < 2.3:                                  # face down, flat
            squash = 1 if t > 0.5 else (t - 0.35) / 0.15
            self.pet.draw_body(p, state="land", angle=f * 80 * min(1, 0.3 + squash), dy=-4)
            for i in range(3):                         # stars circling
                a = t * 5 + i * 2.1
                draw_star(p, (60 + f * 35 + math.cos(a) * 18) * k, (78 + math.sin(a) * 6) * k,
                          5 * k, 230)
        else:                                          # up again, shake it off
            shake = math.sin((t - 2.3) * 40) * 5 * max(0, 1 - (t - 2.3) / 0.9)
            self.pet.draw_body(p, state="idle", dx=shake, expr="happy" if t > 2.8 else None)


def draw_football(p, x, y, r, spin, alpha):
    p.save()
    p.translate(x, y)
    p.rotate(spin % 360)
    p.setPen(QPen(QColor(30, 30, 40, alpha), 1.0))
    p.setBrush(QColor(250, 250, 250, alpha))
    p.drawEllipse(QPointF(0, 0), r, r)
    p.setBrush(QColor(30, 30, 40, alpha))
    hexagon = QPainterPath()
    for i in range(5):
        a = i * 2 * math.pi / 5
        pt = QPointF(math.cos(a) * r * 0.38, math.sin(a) * r * 0.38)
        hexagon.moveTo(pt) if i == 0 else hexagon.lineTo(pt)
    hexagon.closeSubpath()
    p.drawPath(hexagon)
    p.restore()


def draw_nfl_ball(p, x, y, r, angle, alpha=255):
    p.save()
    p.translate(x, y)
    p.rotate(angle)
    p.setPen(QPen(QColor(70, 35, 15, alpha), 1.0))
    p.setBrush(QColor(150, 75, 30, alpha))
    p.drawEllipse(QRectF(-r * 1.5, -r, r * 3, r * 2))
    p.setPen(QPen(QColor(255, 255, 255, alpha), 1.2))
    p.drawLine(QPointF(-r * 0.6, 0), QPointF(r * 0.6, 0))
    for i in range(-2, 3):
        p.drawLine(QPointF(i * r * 0.25, -r * 0.25), QPointF(i * r * 0.25, r * 0.25))
    p.restore()


class GoalWindow(QWidget):
    """See-through strip from Blip to the far end of the screen: the goal + the ball in flight."""

    def __init__(self, left, top, width, height, side):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
                            | Qt.WindowType.Tool | Qt.WindowType.WindowDoesNotAcceptFocus
                            | Qt.WindowType.WindowTransparentForInput)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setGeometry(left, top, width, height)
        self.side = side              # +1: goal on the right, -1: on the left
        self.alpha = 0.0              # goal fades in / out
        self.ripple = 0.0             # net wobble after a goal (seconds left)
        self.ball = None              # (x, y, spin, alpha)
        self.t = 0.0

    def goal_rect(self):
        k = s()
        w, h = 70 * k, 58 * k
        x = self.width() - w - 6 if self.side > 0 else 6
        return QRectF(x, self.height() - h - 2, w, h)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        a = int(255 * self.alpha)
        g = self.goal_rect()
        if a > 0:
            # net (wobbles after a goal)
            wob = math.sin(self.t * 30) * 4 * s() * min(1, self.ripple)
            p.setPen(QPen(QColor(255, 255, 255, int(a * 0.45)), 1))
            back = g.right() - 10 * s() if self.side > 0 else g.left() + 10 * s()
            for i in range(1, 6):
                y = g.top() + i * g.height() / 6
                p.drawLine(QPointF(g.left(), y + wob * (i % 2)), QPointF(g.right(), y - wob * (i % 2)))
            for i in range(1, 7):
                x = g.left() + i * g.width() / 7 + wob
                p.drawLine(QPointF(x, g.top()), QPointF(x, g.bottom()))
            # glass posts + crossbar
            main_c, accent = THEMES.get(config.THEME, THEMES["Nexus"])
            p.setPen(QPen(rgba(accent, a), 4 * s(), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(g.bottomLeft(), g.topLeft())
            p.drawLine(g.topLeft(), g.topRight())
            p.drawLine(g.topRight(), g.bottomRight())
            p.setPen(QPen(QColor(255, 255, 255, int(a * 0.7)), 1.2 * s()))
            p.drawLine(g.topLeft() + QPointF(1, 1), g.topRight() + QPointF(-1, 1))
        if self.ball:
            x, y, spin, ba = self.ball
            draw_football(p, x, y, 8 * s(), spin, int(ba))
        p.end()


class Football(Antic):
    """Keepy-ups, then a goal appears at the far end of the screen: dribble + 3 shots."""
    duration = 14.0
    margin = 90

    def __init__(self, pet):
        super().__init__(pet)
        area = pet.ground_area()
        me = pet.center_x()
        self.side = 1 if me - area.left() < area.right() - me else -1      # goal far away
        pet.facing = self.side
        height = int(config.PET_SIZE * 2.4)
        left = int(me) if self.side > 0 else area.left()
        right = area.right() + 1 if self.side > 0 else int(me)
        self.win = None
        self.geo = (left, area.bottom() + 1 - height, max(200, right - left), height)
        outcomes = ["goal", random.choice(["goal", "post", "over"]), random.choice(["goal", "post", "over"])]
        random.shuffle(outcomes)
        self.outcomes = outcomes
        self.phase, self.pt = "keepy", 0.0
        self.shot = 0
        self.ball_start = None
        self.kick_face = None

    def _next(self, phase):
        self.phase, self.pt = phase, 0.0

    def update(self, dt):
        self.t += dt
        self.pt += dt
        pet = self.pet
        if self.win is not None:
            self.win.t = self.t
            self.win.ripple = max(0.0, self.win.ripple - dt)
        if self.phase == "keepy" and self.pt >= 2.0:
            self.win = GoalWindow(*self.geo, self.side)
            self.win.show()
            self._next("appear")
        elif self.phase == "appear":
            self.win.alpha = min(1.0, self.pt / 0.5)
            if self.pt >= 0.5:
                self._next("dribble")
        elif self.phase == "dribble":                       # a few steps towards the goal
            left, right = pet.walk_bounds()
            pet.x_pos = max(left, min(pet.x_pos + self.side * 70 * dt, right))
            pet.step += dt * 12
            if self.pt >= 1.0:
                self._next("shoot")
        elif self.phase == "shoot":
            self._shoot(dt)
        elif self.phase == "fade":
            self.win.alpha = max(0.0, 1 - self.pt / 0.8)
            self.win.ball = None
            if self.pt >= 0.9:
                return True
        if self.win is not None:
            self.win.update()
        return self.t > 20                                   # safety net

    def _shoot(self, dt):
        pet, w = self.pet, self.win
        k = s()
        result = self.outcomes[self.shot]
        if self.ball_start is None:                          # ball at Blip's foot
            self.ball_start = (pet.center_x() + self.side * 24 * k - w.x(), w.height() - 9 * k)
        x0, y0 = self.ball_start
        g = w.goal_rect()
        tx = g.center().x() + self.side * g.width() * 0.25
        ty = {"goal": g.center().y(), "post": g.top() + 4, "over": g.top() - 30 * k}[result]
        if self.pt < 0.3:                                    # wind-up
            w.ball = (x0, y0, 0, 255)
            return
        u = min(1.0, (self.pt - 0.3) / 0.9)
        if result == "post" and u >= 1.0:                    # bounce back off the post
            v = min(1.0, (self.pt - 1.2) / 0.6)
            bx = tx - self.side * v * 120 * k
            by = ty + math.sin(v * math.pi) * -30 * k + v * (y0 - ty)
            w.ball = (bx, by, self.t * -900, 255 * (1 - v))
        elif result == "over" and u >= 1.0:
            v = min(1.0, (self.pt - 1.2) / 0.6)
            w.ball = (tx + self.side * v * 40 * k, ty - v * 40 * k, self.t * 900, 255 * (1 - v))
        else:
            arc = math.sin(u * math.pi) * (30 if result != "over" else 60) * k
            w.ball = (x0 + (tx - x0) * u, y0 + (ty - y0) * u - arc, self.t * 900,
                      255 if not (result == "goal" and u >= 1) else 200)
        if u >= 1.0 and self.kick_face is None:              # the moment it arrives
            self.kick_face = result
            if result == "goal":
                w.ripple = 1.2
                pet.bubble.say("GOAL!", random.choice(["What a strike!", "Top bins!", "Back of the net!"]), 2.2)
                __import__("extras").play("yay")
            else:
                pet.bubble.say("So close!", "Off the post!" if result == "post" else "Way over the bar...", 2.0)
        if self.pt >= 2.0:
            self.shot += 1
            self.ball_start, self.kick_face = None, None
            w.ball = None
            self._next("fade" if self.shot >= len(self.outcomes) else "shoot")

    def paint(self, p):
        t, k = self.t, s()
        if self.phase == "keepy":                            # keepy-ups next to Blip
            hop = 0.6
            phase = (t % hop) / hop
            self.pet.draw_body(p, state="idle", dy=-abs(math.sin(phase * math.pi)) * 4, expr="happy")
            draw_football(p, (60 + self.pet.facing * 22) * k, (104 - math.sin(phase * math.pi) * 62) * k,
                          8 * k, t * 600, 255)
        elif self.phase == "dribble":
            self.pet.draw_body(p, state="walk", expr=None)
        elif self.phase == "shoot":
            if self.kick_face == "goal" or (self.kick_face is None and self.pt < 0.3):
                self.pet.draw_body(p, state="idle", expr="happy",
                                   dy=-math.sin(min(1, max(0, self.pt - 1.2) / 0.5) * math.pi) * 16
                                   if self.kick_face == "goal" else 0,
                                   angle=-self.pet.facing * 10 * (self.pt / 0.3) if self.pt < 0.3 else 0)
            elif self.kick_face in ("post", "over"):
                self.pet.draw_body(p, state="fall", expr=None)       # (O_O) noooo
            else:                                                     # follow-through
                self.pet.draw_body(p, state="idle", angle=self.pet.facing * 12 * max(0, 1 - (self.pt - 0.3) * 3),
                                   expr=None)
        else:
            self.pet.draw_body(p, state="idle", expr="happy" if "goal" in self.outcomes else None)

    def end(self):
        if self.win is not None:
            self.win.close()
            self.win.deleteLater()
            self.win = None


class Sneeze(Antic):
    """Ah... ah... CHOO! and a hop backwards."""
    duration = 2.4
    margin = 40

    def update(self, dt):
        before = self.t
        done = super().update(dt)
        if before < 1.2 <= self.t:                     # the sneeze: hop back
            self.pet.x_pos -= self.pet.facing * 14
            __import__("extras").play("sneeze")
        return done

    def paint(self, p):
        t, k, f = self.t, s(), self.pet.facing
        if t < 1.2:                                     # build-up: leaning back, squinting
            lean = -f * 10 * (t / 1.2)
            self.pet.draw_body(p, state="idle", angle=lean, blink=0.7, dy=-t * 3)
        else:
            u = t - 1.2
            self.pet.draw_body(p, state="land" if u < 0.25 else "idle", angle=f * 12 * max(0, 1 - u * 3))
            for i in range(6):                          # spray puffs
                a = (i - 2.5) * 0.25
                d = 30 + u * 60
                alpha = int(200 * max(0, 1 - u / 1.0))
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(200, 235, 255, alpha))
                p.drawEllipse(QPointF((60 + f * (30 + d * math.cos(a))) * k, (70 + d * math.sin(a) * 0.6) * k),
                              3 * k, 3 * k)


class Butterfly(Antic):
    """A tiny butterfly flutters by and Blip chases it."""
    duration = 6.0
    margin = 90

    def update(self, dt):
        done = super().update(dt)
        bx = self.bx()
        target = self.pet.x_pos + (bx - 60) * s() * 0.9
        self.pet.facing = 1 if bx > 60 else -1
        self.pet.x_pos += max(-60 * dt, min(60 * dt, (target - self.pet.x_pos) * dt * 2))
        left, right = self.pet.walk_bounds()
        self.pet.x_pos = max(left, min(self.pet.x_pos, right))
        self.pet.step += dt * 10
        return done

    def bx(self):
        return 60 + math.sin(self.t * 1.3) * 70

    def paint(self, p):
        t, k = self.t, s()
        self.pet.draw_body(p, state="walk", look=(1 if self.bx() > 60 else -1, -0.8))
        bx = self.bx()
        by = 35 + math.sin(t * 3.1) * 15 - max(0, t - 4.5) * 60     # flies away at the end
        alpha = 255 if t < 4.5 else int(255 * max(0, 1 - (t - 4.5) / 1.5))
        flap = abs(math.sin(t * 18))
        p.setPen(Qt.PenStyle.NoPen)
        for side in (-1, 1):
            p.setBrush(QColor(255, 140, 200, alpha))
            p.drawEllipse(QRectF((bx + side * 1) * k - (side < 0) * 7 * k * flap, (by - 6) * k,
                                 7 * k * flap, 7 * k))
            p.setBrush(QColor(255, 200, 90, alpha))
            p.drawEllipse(QRectF((bx + side * 1) * k - (side < 0) * 5 * k * flap, by * k,
                                 5 * k * flap, 5 * k))
        p.setBrush(QColor(60, 40, 60, alpha))
        p.drawRect(QRectF((bx - 0.7) * k, (by - 5) * k, 1.4 * k, 10 * k))


class Spin(Antic):
    """A little spin dance."""
    duration = 2.2
    margin = 30

    def paint(self, p):
        t = self.t
        ang = 360 * min(1.0, t / 1.6) ** 0.8 * (1 if self.pet.facing > 0 else -1)
        self.pet.draw_body(p, state="idle", angle=ang, pivot=(60, 70), expr="happy",
                           dy=-math.sin(min(1, t / 1.6) * math.pi) * 14)


class Doze(Antic):
    """Dozes off mid-walk... then jolts awake."""
    duration = 3.0
    margin = 30
    walking_ok = True

    def update(self, dt):
        done = super().update(dt)
        if self.t < 1.8:                                 # still shuffling forward, slowly
            self.pet.x_pos += self.pet.facing * 12 * dt * max(0, 1 - self.t / 1.8)
            left, right = self.pet.walk_bounds()
            self.pet.x_pos = max(left, min(self.pet.x_pos, right))
        return done

    def paint(self, p):
        t = self.t
        if t < 2.2:
            nod = math.sin(t * 3) * 4 * min(1, t)
            self.pet.draw_body(p, state="sleep" if t > 0.8 else "idle", angle=nod,
                               blink=min(1, t / 0.8))
        else:                                             # jolt!
            u = t - 2.2
            self.pet.draw_body(p, state="fall", dy=-math.sin(min(1, u / 0.35) * math.pi) * 14)


class Climb(Antic):
    """Cheeky climber: uses a column of desktop icons as a ladder. Icons are only READ
    (positions), never touched."""
    margin = 50
    controls_y = True
    duration = 30.0                     # safety net; usually ends much sooner

    def __init__(self, pet, icons=None):
        super().__init__(pet)
        self.fall_at_end = False
        self.steps = self._plan(icons if icons is not None else [])
        self.phase, self.pt = ("walk", 0.0) if self.steps else ("done", 0.0)
        self.i = -1                     # index of the icon we're standing on
        self.hop_from = None
        self.slip_step = random.randrange(1, max(2, len(self.steps))) if self.steps else -1
        self.ending = random.choice(["proud", "proud", "sit", "fall"])

    @staticmethod
    def find_icons(pet):
        from desktop import desktop_icons
        return desktop_icons(int(pet.winId()), pet.current_screen())

    def _plan(self, icons):
        """Pick the icon column closest to Blip and the icons to climb, bottom first."""
        if not icons:
            return []
        floor_feet = self.pet.ground_area().bottom()
        cols = {}
        for r in icons:
            cols.setdefault(round(r.center().x() / 40), []).append(r)
        best = None
        for col in cols.values():
            col.sort(key=lambda r: -r.top())
            if col[0].top() < floor_feet - 220:               # lowest icon too high to reach
                continue
            ladder = [col[0]]
            for r in col[1:]:                                  # stacked, no big gaps
                if 40 <= ladder[-1].top() - r.top() <= 160:
                    ladder.append(r)
                else:
                    break
            if len(ladder) >= 2:
                d = abs(ladder[0].center().x() - self.pet.center_x())
                if best is None or d < best[0]:
                    best = (d, ladder)
        if best is None:
            return []
        return best[1][:random.randint(3, 6)]

    def feet_y(self, r):
        return r.top() + 1 - round(config.PET_SIZE * 112 / 120)

    def _next(self, phase):
        self.phase, self.pt = phase, 0.0

    def update(self, dt):
        self.t += dt
        self.pt += dt
        pet = self.pet
        if self.phase == "done":
            return True
        if self.phase == "walk":
            target = self.steps[0].center().x() - config.PET_SIZE / 2
            d = target - pet.x_pos
            stepx = config.WALK_SPEED * 1.5 * dt
            pet.facing = 1 if d > 0 else -1
            pet.y_pos = pet.floor_y()
            if abs(d) <= stepx or self.pt > 10:
                pet.x_pos = target
                self.hop_from = (pet.x_pos, pet.y_pos)
                self._next("hop")
            else:
                pet.x_pos += stepx * pet.facing
                pet.step += dt * 10
            return False
        if self.phase == "hop":                                # arc up onto the next icon
            nxt = self.steps[self.i + 1]
            x0, y0 = self.hop_from
            x1, y1 = nxt.center().x() - config.PET_SIZE / 2, self.feet_y(nxt)
            u = min(1.0, self.pt / 0.45)
            pet.x_pos = x0 + (x1 - x0) * u
            pet.y_pos = y0 + (y1 - y0) * u - math.sin(u * math.pi) * 40 * s()
            if u >= 1:
                self.i += 1
                self._next("slip" if self.i == self.slip_step else "wobble")
            return False
        if self.phase in ("wobble", "slip"):
            r = self.steps[self.i]
            pet.y_pos = self.feet_y(r) + (math.sin(self.pt * 30) * 4 * s() if self.phase == "slip"
                                          and self.pt < 0.6 else 0)
            if self.pt >= (1.1 if self.phase == "slip" else random.uniform(0.35, 0.7)):
                if self.i + 1 < len(self.steps):
                    self.hop_from = (pet.x_pos, pet.y_pos)
                    self._next("hop")
                else:
                    self._next(self.ending)
                    if self.ending == "proud":
                        pet.bubble.say("Top of the world!", "I'm the king of the desktop!", 2.5)
            return False
        if self.phase in ("proud", "sit"):
            pet.y_pos = self.feet_y(self.steps[self.i])
            if self.pt >= (2.2 if self.phase == "proud" else 3.5):
                self._next("jump_off")
            return False
        if self.phase == "fall" and self.pt < 0.9:              # slips... and falls!
            pet.y_pos = self.feet_y(self.steps[self.i]) + math.sin(self.pt * 25) * 3 * s()
            return False
        # jump off / fall: hand over to the normal gravity + bounce
        self.fall_at_end = True
        pet.vx = -pet.facing * random.uniform(80, 180)
        pet.vy = -200.0 if self.phase != "fall" else 0.0
        return True

    def paint(self, p):
        from dance import Dancer
        k, t, ph = s(), self.t, self.phase
        f = self.pet.facing
        level = (self.i + 1) / max(1, len(self.steps))          # cheekier the higher it goes
        if ph == "walk":
            self.pet.draw_body(p, state="walk", expr=None)
        elif ph == "hop":
            self.pet.draw_body(p, state="fall", expr=None)
        elif ph == "slip":                                       # near miss: arms flailing
            ang = math.sin(self.pt * 30) * 12 * max(0, 1 - self.pt)
            self.pet.draw_body(p, state="fall", angle=ang, expr=None)
            flap = math.sin(self.pt * 40) * 16
            Dancer.arms(p, k, ((20, 50 + flap), (100, 50 - flap)), ang, (60, 112), 0, 0)
        elif ph == "wobble":
            self.pet.draw_body(p, state="idle", angle=math.sin(t * 9) * 4,
                               expr="happy" if level > 0.6 else None)
        elif ph == "proud":
            self.pet.draw_body(p, state="idle", expr="happy", dy=-abs(math.sin(t * 6)) * 3)
            Dancer.arms(p, k, ((34, 36), (86, 36)), 0, (60, 112), 0, 0)
        elif ph == "sit":                                         # sitting, swinging legs
            self.pet.draw_body(p, state="land", expr=None, look=(f * 0.6, 0.5),
                               angle=math.sin(t * 2) * 3)
            for side in (-1, 1):
                swing = math.sin(t * 6 + side) * 6
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(rgba(THEMES.get(config.THEME, THEMES["Nexus"])[1], 200))
                p.drawRoundedRect(QRectF((60 + side * 12 - 7 + swing * 0.3) * k, (110 + abs(swing) * 0.4) * k,
                                         14 * k, 8 * k), 4 * k, 4 * k)
        else:                                                    # "fall" wobble before the drop
            ang = math.sin(self.pt * 25) * 10
            self.pet.draw_body(p, state="fall", angle=ang, expr=None)
            Dancer.arms(p, k, ((18, 40), (102, 40)), ang, (60, 112), 0, 0)


class HideSeek(Antic):
    """Blip hides at the edge of the screen, peeking out. Click him within 30 s to win."""
    margin = 0
    controls_y = True
    duration = 30.0

    def __init__(self, pet):
        super().__init__(pet)
        area = pet.ground_area()
        size = config.PET_SIZE
        spot = random.choice(["left", "right", "bottom", "bottom", "window"])
        self.side = random.choice((-1, 1))
        self.y = random.uniform(area.top() + 80, area.bottom() - size - 120)
        if spot == "left":
            self.side = -1
            self.x = area.left() - size * random.uniform(0.5, 0.65)
        elif spot == "right":
            self.side = 1
            self.x = area.right() - size * random.uniform(0.35, 0.5)
        elif spot == "bottom":                            # just his head peeking over the taskbar
            self.x = random.uniform(area.left() + 40, area.right() - size - 40)
            self.y = area.bottom() - size * random.uniform(0.35, 0.45)
        else:                                              # peeking over the top of a window
            spots = pet.find_spots(force=True)
            if spots:
                _, a, b, top = random.choice(spots)
                self.x = random.uniform(a, max(a, b - size))
                self.y = top - size * random.uniform(0.25, 0.35)
            else:
                self.x = area.left() - size * 0.55
                self.side = -1
        pet.facing = -self.side if spot in ("left", "right") else random.choice((-1, 1))
        self.found = False
        self.fall_at_end = True
        pet.bubble.say("Hide and seek!", "Find me within 30 seconds... ready or not!", 3)

    def update(self, dt):
        self.t += dt
        if self.t < 0.6:                                   # zoom off to the hiding spot
            return False
        self.pet.x_pos, self.pet.y_pos = self.x, self.y
        if not self.found:                                 # no bubble or XP tag giving him away
            self.pet.bubble.hide()
            pop = getattr(self.pet, "xp_popup", None)
            if pop is not None:
                pop.hide()
        if self.found:
            return True
        if self.t >= self.duration:
            self.pet.bubble.say("Haha!", "I win this time! Wanna go again?", 3)
            self.pet.vx, self.pet.vy = -self.side * 300, -300
            return True
        return False

    def caught(self):
        """You clicked Blip: you win!"""
        self.found = True
        self.pet.bubble.say("You found me!", "Okay okay, you win!", 3)
        self.pet.vx, self.pet.vy = -self.side * 250, -400
        __import__("extras").cheer("win")
        __import__("extras").play("yay")

    def paint(self, p):
        if self.t < 0.6:
            self.pet.draw_body(p, state="fall", expr=None)
            return
        wiggle = math.sin(self.t * 2.5) * 4                # peeking in and out a little
        self.pet.draw_body(p, state="idle", expr="happy" if (self.t % 6) < 1 else None,
                           dx=-self.side * (6 + wiggle), look=(-self.side * 1.0, 0))


class Pose(Antic):
    """Screenshot! Blip strikes a peace-sign pose."""
    duration = 2.2
    margin = 20
    walking_ok = True

    def paint(self, p):
        from dance import Dancer
        k = s()
        f = self.pet.facing
        self.pet.draw_body(p, state="idle", expr="happy", angle=-f * 6, pivot=(60, 110))
        hx, hy = 60 + f * 40, 34
        Dancer.arms(p, k, ((32, 96), (hx, hy)) if f > 0 else ((hx, hy), (88, 96)), -f * 6, (60, 110), 0, 0)
        p.setPen(QPen(rgba(THEMES.get(config.THEME, THEMES["Nexus"])[1], 240), 2.4 * k,
                      Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for a in (-0.35, 0.35):                            # the V fingers
            p.drawLine(QPointF(hx * k, hy * k), QPointF((hx + math.sin(a) * 9) * k, (hy - math.cos(a) * 9) * k))


class Emote(Antic):
    """Shop emotes: Wave, Flex, Laugh (Play > Emotes)."""
    duration = 2.4
    margin = 20
    walking_ok = True
    kind = "Wave"

    def paint(self, p):
        from dance import Dancer
        k, t, f = s(), self.t, self.pet.facing
        if self.kind == "Wave":
            self.pet.draw_body(p, state="idle", expr="happy")
            sw = math.sin(t * 14) * 10
            Dancer.arms(p, k, ((34, 96), (96 + sw * 0.3, 30 + abs(sw) * 0.3)), 0, (60, 110), 0, 0)
        elif self.kind == "Flex":
            self.pet.draw_body(p, state="idle", expr=None, dy=-abs(math.sin(t * 5)) * 3)
            pump = abs(math.sin(t * 5)) * 4
            Dancer.arms(p, k, ((14, 52 - pump), (106, 52 - pump)), 0, (60, 110), 0, 0)
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(rgba(THEMES.get(config.THEME, THEMES["Nexus"])[1], 230))
            for x in (22, 98):                               # little muscles
                p.drawEllipse(QPointF(x * k, (60 - pump) * k), 5 * k, 4 * k)
        else:                                                # Laugh
            shake = math.sin(t * 30) * 2
            self.pet.draw_body(p, state="idle", expr="happy", dx=shake, dy=-abs(math.sin(t * 12)) * 3)
            if int(t * 3) % 2 == 0:
                from PyQt6.QtGui import QFont
                f = QFont("Segoe UI", 1); f.setBold(True); f.setPixelSize(int(11 * k)); p.setFont(f)
                p.setPen(rgba(THEMES.get(config.THEME, THEMES["Nexus"])[1], 240))
                p.drawText(QPointF(70 * k, 30 * k), "HA HA")


class SnackGameWindow(QWidget):
    """See-through strip over the screen where snacks fall. Clicks go through it."""

    def __init__(self, rect):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
                            | Qt.WindowType.Tool | Qt.WindowType.WindowDoesNotAcceptFocus
                            | Qt.WindowType.WindowTransparentForInput)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setGeometry(rect)
        self.snacks, self.score, self.left = [], 0, 20.0

    def paintEvent(self, e):
        from character import draw_snack
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        for x, y, _ in self.snacks:
            p.save(); p.translate(x - 14, y - 14); draw_snack(p, 28); p.restore()
        from PyQt6.QtGui import QFont
        f = QFont("Segoe UI", 1); f.setBold(True); f.setPixelSize(18); p.setFont(f)
        p.setPen(QColor(0, 0, 0, 0)); p.setBrush(QColor(25, 16, 50, 200))
        p.drawRoundedRect(QRectF(self.width() / 2 - 120, 6, 240, 30), 12, 12)
        p.setPen(QColor(240, 250, 255))
        p.drawText(QRectF(self.width() / 2 - 120, 6, 240, 30), Qt.AlignmentFlag.AlignCenter,
                   f"Snacks: {self.score}    Time: {max(0, int(self.left))}s")
        p.end()


class SnackGame(Antic):
    """Mini-game: move your mouse to steer Blip and catch the falling snacks (20 s)."""
    margin = 0
    duration = 21.0
    walking_ok = True

    def __init__(self, pet):
        super().__init__(pet)
        area = pet.ground_area()
        from PyQt6.QtCore import QRect
        self.top = area.bottom() - int(config.PET_SIZE * 4.5)
        self.win = SnackGameWindow(QRect(area.left(), self.top, area.width(), area.bottom() - self.top))
        self.win.show()
        self.area = area
        self.next_drop = 0.5
        self.rnd = random.Random()
        pet.bubble.say("Snack catch!", "Move your mouse to steer me. Catch the snacks!", 3)

    def update(self, dt):
        from PyQt6.QtGui import QCursor
        self.t += dt
        w = self.win
        w.left = 20 - self.t
        pet = self.pet
        target = QCursor.pos().x() - config.PET_SIZE / 2                # Blip follows the mouse
        step = 900 * dt
        pet.x_pos += max(-step, min(step, target - pet.x_pos))
        left, right = pet.walk_bounds()
        pet.x_pos = max(left, min(pet.x_pos, right))
        pet.facing = 1 if target > pet.x_pos else -1
        pet.step += dt * 12
        if self.t >= self.next_drop and w.left > 1:
            self.next_drop = self.t + self.rnd.uniform(0.35, 0.8)
            w.snacks.append([self.rnd.uniform(30, w.width() - 30), -20.0, self.rnd.uniform(220, 380)])
        catch_y = w.height() - config.PET_SIZE * 0.75
        mouth = pet.center_x() - w.x()
        keep = []
        for s_ in w.snacks:
            s_[1] += s_[2] * dt
            if abs(s_[1] - catch_y) < 22 and abs(s_[0] - mouth) < config.PET_SIZE * 0.4:
                w.score += 1
                pet.set_expr("happy", 0.6)
                continue
            if s_[1] < w.height() + 20:
                keep.append(s_)
        w.snacks = keep
        w.update()
        if self.t >= self.duration:
            score = w.score
            import progress
            prog = progress.get()
            ev = prog.award("snackgame", score * 5)
            import care
            ev += care.bump(prog, "snackgame", score)
            prog.save()
            pet.bubble.say("Game over!", f"You caught {score} snacks! +{score * 5} XP", 4)
            pet.handle_xp(ev)
            return True
        return False

    def paint(self, p):
        self.pet.draw_body(p, state="walk", expr="happy" if self.pet.expr == "happy" else None)

    def end(self):
        if self.win is not None:
            self.win.close(); self.win.deleteLater(); self.win = None


def make_emote(kind):
    return type(f"Emote{kind}", (Emote,), {"kind": kind})


# ---------------------------------------------------------------------------
class FriendWindow(QWidget):
    """A second mini Blip that peeks in from the screen edge to play catch.
    The window spans from the edge to Blip so the ball can fly between them."""

    def __init__(self, side, left, top, width, height, theme):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
                            | Qt.WindowType.Tool | Qt.WindowType.WindowDoesNotAcceptFocus
                            | Qt.WindowType.WindowTransparentForInput)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.side, self.theme = side, theme
        self.setGeometry(left, top, width, height)
        self.friend_x = 0.0           # friend's left edge inside this window
        self.friend_state = "idle"
        self.wave = False
        self.ball = None              # (x, y, angle) inside this window, or None
        self.t = 0.0

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        size = int(config.PET_SIZE * 0.8)
        p.save()
        p.translate(self.friend_x, self.height() - size)
        draw_pet(p, size, self.friend_state, self.t, facing=-self.side, theme=self.theme,
                 expr="happy" if self.wave else None, hat="None")
        if self.wave:                                       # waving arm
            k = size / 120
            p.setPen(QPen(rgba(THEMES[self.theme][1], 230), 6 * k, Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.RoundCap))
            ang = math.sin(self.t * 14) * 0.5
            sx, sy = 60 - self.side * 30, 70
            p.drawLine(QPointF(sx * k, sy * k),
                       QPointF((sx - self.side * 14 * math.cos(ang)) * k, (sy - 20 + math.sin(ang) * 6) * k))
        p.restore()
        if self.ball:
            draw_nfl_ball(p, *self.ball[:2], 6 * s(), self.ball[2])
        p.end()


class NflThrow(Antic):
    """Blip and a friend throw an American football back and forth."""
    duration = 9.0
    margin = 0

    def __init__(self, pet):
        super().__init__(pet)
        area = pet.ground_area()
        center = pet.center_x()
        self.side = -1 if center - area.left() < area.right() - center else 1   # nearest edge
        self.gap = 300 * s()
        fsize = config.PET_SIZE * 0.8
        # Blip moves to a spot `gap` away from that edge
        edge_x = area.left() if self.side < 0 else area.right()
        target_center = edge_x - self.side * (self.gap + fsize / 2)
        self.target_x = target_center - config.PET_SIZE / 2
        self.edge_x = edge_x
        self.friend = None
        self.theme = random.choice([t for t in THEMES if t != config.THEME])
        self.throws = 0
        self.phase = "walk"
        self.phase_t = 0.0

    def _open_friend(self):
        area = self.pet.ground_area()
        pet_center = self.pet.center_x()
        if self.side < 0:
            left, right = area.left(), int(pet_center)
        else:
            left, right = int(pet_center), area.right() + 1
        height = int(config.PET_SIZE * 2.4)
        self.friend = FriendWindow(self.side, left, area.bottom() + 1 - height, right - left, height,
                                   self.theme)
        self.fsize = config.PET_SIZE * 0.8
        self.friend_home = 0.0 if self.side < 0 else self.friend.width() - self.fsize
        self.friend.friend_x = -self.fsize if self.side < 0 else self.friend.width()
        self.friend.show()

    def update(self, dt):
        self.t += dt
        self.phase_t += dt
        pet = self.pet
        if self.phase == "walk":                       # walk over to a good spot
            dist = self.target_x - pet.x_pos
            step = config.WALK_SPEED * 1.6 * dt
            pet.facing = 1 if dist > 0 else -1
            if abs(dist) <= step or self.phase_t > 8:
                pet.x_pos = self.target_x
                pet.facing = self.side
                self._open_friend()
                self._next("peek")
            else:
                pet.x_pos += step * pet.facing
                pet.step += dt * 10
            return False
        f = self.friend
        f.t = self.t
        if self.phase == "peek":                       # friend slides in from the edge
            u = min(1, self.phase_t / 0.7)
            start = -self.fsize if self.side < 0 else f.width()
            f.friend_x = start + (self.friend_home - start) * u
            if u >= 1:
                self._next("throw")
        elif self.phase == "throw":                    # ball arcs between them
            u = min(1, self.phase_t / 1.0)
            blip = (f.width() - 22 * s()) if self.side < 0 else 22 * s()
            friend = self.friend_home + self.fsize / 2
            a, b = (blip, friend) if self.throws % 2 == 0 else (friend, blip)
            x = a + (b - a) * u
            y = f.height() - self.fsize * 0.8 - math.sin(u * math.pi) * f.height() * 0.55
            f.ball = (x, y, (u * 720) if self.throws % 2 else -(u * 720))
            if u >= 1:
                self.throws += 1
                f.ball = None if self.throws >= 4 else f.ball
                self._next("wave" if self.throws >= 4 else "throw")
        elif self.phase == "wave":
            f.wave = True
            if self.phase_t > 1.4:
                self._next("leave")
        elif self.phase == "leave":
            u = min(1, self.phase_t / 0.7)
            end = -self.fsize if self.side < 0 else f.width()
            f.friend_x = self.friend_home + (end - self.friend_home) * u
            if u >= 1:
                return True
        f.update()
        return False

    def _next(self, phase):
        self.phase, self.phase_t = phase, 0.0

    def paint(self, p):
        walking = self.phase == "walk"
        throwing = self.phase == "throw" and self.friend and self.friend.ball and self.throws % 2 == 1 \
            and self.phase_t > 0.75
        self.pet.draw_body(p, state="walk" if walking else ("held" if throwing else "idle"),
                           expr="happy" if self.phase in ("wave", "leave") else None)

    def end(self):
        if self.friend is not None:
            self.friend.close()
            self.friend.deleteLater()
            self.friend = None


ALL = {"trip": Trip, "football": Football, "nfl": NflThrow, "sneeze": Sneeze,
       "butterfly": Butterfly, "spin": Spin, "doze": Doze, "climb": Climb,
       "seek": HideSeek, "pose": Pose,
       "emote:Wave": make_emote("Wave"), "emote:Flex": make_emote("Flex"), "emote:Laugh": make_emote("Laugh"),
       "snackgame": SnackGame}
# How likely each one is in the random pick (football + NFL a bit more, doze-off rare).
WEIGHTS = {"trip": 3, "football": 4, "nfl": 4, "sneeze": 3, "butterfly": 3, "spin": 3, "doze": 1, "climb": 3}

# v1.2: more random antics (blaster, banana, gum, dumbbell, plane, balloon, chili, skateboard, magic)
import antics2  # noqa: E402,F401  (registers itself in ALL / WEIGHTS)
