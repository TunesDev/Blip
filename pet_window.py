"""
Desktop pet - the see-through window and the pet's behaviour.

States:
  idle  -> stands and breathes
  walk  -> walks along the taskbar of the screen it's on
  sleep -> naps, or sleeps while you're away
  held  -> you're dragging it with the mouse
  fall  -> flying / falling with gravity, bounces when it hits the floor
  land  -> short squash after landing
Plus: expressions (happy / grumpy / yawn), eyes that follow the cursor, eating snacks.
Stage 4: sits on top of your windows (and falls off when they move), sweats when
your CPU/RAM is maxed, and gets sleepy late at night.
Developed by Tunes
"""
import ctypes
import datetime
from ctypes import wintypes
import math
import random
import sys
import time
from collections import deque

from PyQt6.QtCore import QPoint, Qt, QTimer
from PyQt6.QtGui import QCursor, QGuiApplication, QPainter
from PyQt6.QtWidgets import QWidget

import config
import desktop
from bubble import Bubble
from character import draw_pet
from music import MusicWatcher
from snack import Snack, SIZE as SNACK_SIZE

YAWN_SECONDS = 2.4


# ---------------------------------------------------------------------------
# Small Windows helpers (they just return "nothing special" on other systems)
# ---------------------------------------------------------------------------
IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]

    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.MonitorFromWindow.restype = wintypes.HMONITOR
    user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
    user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MONITORINFO)]
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]

    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongW.restype = ctypes.c_long
    user32.IsZoomed.argtypes = [wintypes.HWND]

    MONITOR_DEFAULTTONEAREST = 2
    GWL_STYLE = -16
    WS_CAPTION = 0x00C00000
    # The desktop itself and the taskbar are not "fullscreen apps".
    IGNORE_CLASSES = {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"}


def user_idle_seconds() -> float:
    """Seconds since you last moved the mouse / pressed a key."""
    if not IS_WINDOWS:
        return 0.0
    try:
        return _idle_seconds()
    except Exception:
        return 0.0


def _idle_seconds():
    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(info)
    if not user32.GetLastInputInfo(ctypes.byref(info)):
        return 0.0
    return ((kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF) / 1000.0


def fullscreen_app_on_my_screen(my_hwnd: int):
    """Returns the window class name if the active window fills the whole monitor
    that the pet is on (a game like Call of Duty, a fullscreen video...), else None."""
    if not IS_WINDOWS:
        return None
    try:
        return _fullscreen_check(my_hwnd)
    except Exception as e:          # never let this check crash the pet
        print("Fullscreen check failed:", e)
        return None


def _fullscreen_check(my_hwnd):
    fg = user32.GetForegroundWindow()
    if not fg or fg == my_hwnd:
        return None

    name = ctypes.create_unicode_buffer(64)
    user32.GetClassNameW(fg, name, 64)
    if name.value in IGNORE_CLASSES:
        return None

    # Normal or maximised windows (VS Code, a browser...) never count.
    style = user32.GetWindowLongW(fg, GWL_STYLE)
    if style & WS_CAPTION == WS_CAPTION or user32.IsZoomed(fg):
        return None

    fg_monitor = user32.MonitorFromWindow(fg, MONITOR_DEFAULTTONEAREST)
    my_monitor = user32.MonitorFromWindow(my_hwnd, MONITOR_DEFAULTTONEAREST)
    if fg_monitor != my_monitor:
        return None    # game is on your other screen -> pet can stay

    mi = MONITORINFO()
    mi.cbSize = ctypes.sizeof(mi)
    if not user32.GetMonitorInfoW(fg_monitor, ctypes.byref(mi)):
        return None
    r = wintypes.RECT()
    user32.GetWindowRect(fg, ctypes.byref(r))
    m = mi.rcMonitor
    if r.left <= m.left and r.top <= m.top and r.right >= m.right and r.bottom >= m.bottom:
        return name.value or "unknown"
    return None


# ---------------------------------------------------------------------------
class PetWindow(QWidget):
    def __init__(self):
        super().__init__()

        # Frameless, always on top, hidden from the taskbar, see-through.
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(config.PET_SIZE, config.PET_SIZE)
        self.setWindowTitle(config.APP_NAME)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        # Behaviour state
        self.state = "idle"
        self.facing = 1
        self.x_pos = 0.0
        self.y_pos = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.target_x = 0.0
        self.step = 0.0
        self.state_until = 0.0
        self.napping = False
        self.hidden_for_game = False
        self.walk_boost = 1.0            # walks faster when going for a snack

        self.menu = None                 # right-click menu (set in main.py)
        self.after_settings = None       # callback after Settings are saved
        self.snack = None
        self.expr = None                 # None / "happy" / "grumpy"
        self.expr_until = 0.0
        self.look = (0.0, 0.0)
        self.pokes = deque(maxlen=10)    # times of recent clicks
        self.press_global = QPoint()
        self.press_time = 0.0

        # Stage 4
        self.perch = None                # window we're standing on: (hwnd, left, right, top)
        self.perch_rect = None           # that window's full rectangle when we checked last
        self.no_land = (None, 0.0)       # (window, until): don't land right back on it
        self.press_perch = None
        self.spots = []                  # window tops we could land on while falling
        self.spots_at = 0.0
        self.next_cover_check = 0.0
        self.load = desktop.LoadMeter()
        self.load.sample()
        self.cpu_avg = 0.0
        self.sweating = False
        self.next_load = 0.0
        self.help_offer_until = 0.0
        self.snooze = {}                 # question -> don't ask again before this time
        self.ask = None                  # the Yes/No bubble, only while it's showing
        self.pending_say = None          # message from a background job, shown by tick()
        self.antic = None                # the funny antic running right now (antics.py)
        self.margin = 0                  # see-through space around Blip during an antic
        self.next_antic = time.monotonic() + random.uniform(120, 300)
        self.game = None                 # game window that's open right now (game buddy)
        self.game_start = 0.0
        self.game_gone = 0
        # Reminders: ONE single-shot timer, set for the next reminder (no polling).
        self.reminder_timer = QTimer(self)
        self.reminder_timer.setSingleShot(True)
        self.reminder_timer.timeout.connect(self.fire_reminders)
        self.reminder_timer.start(5000)  # first look shortly after start: missed reminders
        self.confetti_until = 0.0
        self.blush_until = 0.0
        self.pet_moves = deque(maxlen=12)
        self.last_pet = 0.0
        self.setMouseTracking(True)      # for petting (wiggle the mouse over Blip)
        import extras
        extras.on_xp = self.handle_xp
        QTimer.singleShot(6000, self.hello_today)
        self.helper = None
        self.chat = None
        self.music = MusicWatcher()      # any music app
        self.dancer = None               # dance moves (dance.py), created on first music
        self.bubble = Bubble()
        self.song = None
        self.music_on = False
        self.music_level = 0.0

        # Dragging
        self.grab_offset = QPoint()
        self.drag_trail = deque(maxlen=8)    # recent (time, x, y) for throw speed

        now = time.monotonic()
        self.start = now
        self.last_tick = now
        self.next_blink = now + random.uniform(*config.BLINK_EVERY)
        self.blink_start = -1.0
        self.next_check = now
        self.next_yawn = now + random.uniform(4.0, 12.0)

        # Start somewhere random on the main screen's taskbar
        area = QGuiApplication.primaryScreen().availableGeometry()
        self.x_pos = random.uniform(area.left(), area.right() - config.PET_SIZE)
        self.y_pos = area.bottom() - config.PET_SIZE + 1
        self.move(int(self.x_pos), int(self.y_pos))

        # One timer drives everything; its speed depends on the state.
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.CoarseTimer)
        self.timer.timeout.connect(self.tick)
        self.set_state("idle")
        self.timer.start()

    # ---------- screen helpers -------------------------------------------------
    def current_screen(self):
        """The monitor the pet is on right now (works with 2+ screens)."""
        c = QPoint(int(self.x_pos + config.PET_SIZE / 2),
                   int(self.y_pos + config.PET_SIZE / 2))
        screen = QGuiApplication.screenAt(c)
        if screen is None:   # in a gap between monitors: use the one below/above
            for s in QGuiApplication.screens():
                g = s.geometry()
                if g.left() <= c.x() <= g.right():
                    return s
            screen = QGuiApplication.primaryScreen()
        return screen

    def ground_area(self):
        """Desktop area NOT covered by the taskbar. Its bottom = top of taskbar."""
        return self.current_screen().availableGeometry()

    def floor_y(self):
        if self.perch is not None:
            return self.perch_floor(self.perch[3])
        return self.ground_area().bottom() - config.PET_SIZE + 1

    @staticmethod
    def perch_floor(window_top):
        """y position that puts Blip's feet right on a window's top edge."""
        return window_top + 1 - round(config.PET_SIZE * 112 / 120)

    def walk_bounds(self):
        """Leftmost / rightmost x Blip may walk to (taskbar, or the window it's on)."""
        if self.perch is not None:
            _, left, right, _ = self.perch
            half = config.PET_SIZE / 2
            return left + 22 - half, right - 22 - half
        area = self.ground_area()
        return area.left(), area.right() - config.PET_SIZE + 1

    def stick_to_ground(self):
        left, right = self.walk_bounds()
        self.x_pos = max(left, min(self.x_pos, right))
        self.y_pos = self.floor_y()
        self.move(int(self.x_pos), int(self.y_pos))

    def center_x(self):
        return self.x_pos + config.PET_SIZE / 2

    # ---------- state machine --------------------------------------------------
    def set_state(self, state, duration=None, target=None):
        now = time.monotonic()
        if getattr(self, "state", None) == "sleep" and state != "sleep":
            self.awake_since = now               # for "only nap after 20 min awake"
        self.state = state
        if state == "idle":
            self.state_until = now + (duration or random.uniform(*config.IDLE_TIME))
        elif state == "walk":
            left, right = self.walk_bounds()
            self.walk_boost = 1.0
            if target is not None:
                self.target_x = target
                self.walk_boost = 1.7
            else:
                min_walk = min(80, (right - left) / 3)
                for _ in range(10):          # walk a random distance, at least 80px
                    self.target_x = random.uniform(left, right)
                    if abs(self.target_x - self.x_pos) > min_walk:
                        break
            self.facing = 1 if self.target_x > self.x_pos else -1
        elif state == "sleep":
            self.state_until = now + (duration or random.uniform(*config.NAP_TIME))
        elif state == "land":
            self.state_until = now + 0.18
        self.apply_fps()

    def apply_fps(self):
        if self.hidden_for_game:
            fps = config.FPS_HIDDEN
        else:
            fps = {"walk": config.FPS_WALK, "idle": config.FPS_IDLE,
                   "sleep": config.FPS_SLEEP, "land": config.FPS_PHYSICS,
                   "held": config.FPS_WALK, "fall": config.FPS_PHYSICS,
                   "antic": config.FPS_WALK}[self.state]
            if self.music_on and config.DANCE and self.state in ("idle", "land"):
                fps = max(fps, config.FPS_DANCE)         # smooth enough, still light
        if getattr(self, "paused", False):
            fps = config.FPS_PAUSED                      # locked / display off
        self.timer.setInterval(int(1000 / fps))

    # ---------- pause when nobody can see Blip (locked / display off) --------------------
    def showEvent(self, e):
        super().showEvent(e)
        if not getattr(self, "_registered", False) and IS_WINDOWS:
            self._registered = True
            try:
                hwnd = int(self.winId())
                ctypes.WinDLL("wtsapi32").WTSRegisterSessionNotification(wintypes.HWND(hwnd), 0)
                guid = (ctypes.c_ubyte * 16).from_buffer_copy(       # GUID_CONSOLE_DISPLAY_STATE
                    __import__("uuid").UUID("6fe69556-704a-47a0-8f24-c28d936fda47").bytes_le)
                self._power_note = ctypes.WinDLL("user32").RegisterPowerSettingNotification(
                    wintypes.HANDLE(hwnd), ctypes.byref(guid), 0)
            except Exception as ex:
                print("Pause-when-locked not available:", ex)
            QTimer.singleShot(15000, desktop.trim_self)     # give back start-up memory
            try:
                ctypes.WinDLL("user32").AddClipboardFormatListener(wintypes.HWND(int(self.winId())))
            except Exception:
                pass

    def nativeEvent(self, event_type, message):
        try:
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x02B1:                        # WM_WTSSESSION_CHANGE
                if msg.wParam == 7:                          # locked
                    self.set_paused("locked", True)
                elif msg.wParam == 8:                        # unlocked
                    self.set_paused("locked", False)
            elif msg.message == 0x031D:                      # WM_CLIPBOARDUPDATE: a screenshot?
                QTimer.singleShot(150, self.screenshot_pose)
            elif msg.message == 0x0218 and msg.wParam == 0x8013:   # display on/off
                data = ctypes.cast(msg.lParam, ctypes.POINTER(ctypes.c_ubyte * 24)).contents
                self.set_paused("display", data[20] == 0)    # 0 = off, 1 = on, 2 = dimmed
        except Exception:
            pass
        return False, 0

    def set_paused(self, why, on):
        reasons = getattr(self, "pause_reasons", set())
        (reasons.add if on else reasons.discard)(why)
        self.pause_reasons = reasons
        was = getattr(self, "paused", False)
        self.paused = bool(reasons)
        if self.paused != was:
            if not self.paused:
                self.last_tick = time.monotonic()
            self.apply_fps()

    def tick(self):
        now = time.monotonic()
        if getattr(self, "paused", False):
            self.last_tick = now
            return                                       # nobody can see Blip: do nothing
        dt = min(now - self.last_tick, 0.05)
        self.last_tick = now

        # Once a second: are you away? is a fullscreen game on my screen?
        if now >= self.next_check:
            self.next_check = now + 1.0
            self.check_fullscreen()
            if self.state not in ("held", "fall", "land", "antic"):
                self.check_user_idle()
        if now >= self.next_load:
            self.next_load = now + 6.0
            self.check_pc_load()
            self.check_buddy(now)

        if self.hidden_for_game:
            self.bubble.hide()
            return                       # paused: do nothing, draw nothing

        self.check_music()

        if self.perch is not None and self.state in ("idle", "walk", "sleep", "land"):
            self.check_perch(now)

        if self.state == "walk":
            dist = self.target_x - self.x_pos
            move = config.WALK_SPEED * self.walk_boost * dt
            if abs(dist) <= move:
                self.x_pos = self.target_x
                self.set_state("idle")
            else:
                self.x_pos += move * self.facing
                self.step += dt * 10
            self.stick_to_ground()

        elif self.state == "fall":
            self.physics(dt)

        elif self.state == "antic":
            if self.antic is None or self.antic.update(dt):
                self.end_antic()
            else:
                if not getattr(self.antic, "controls_y", False):
                    self.y_pos = self.floor_y()
                self.move(int(self.x_pos), int(self.y_pos))

        elif self.state == "land" and now >= self.state_until:
            self.set_state("idle")

        elif self.state == "idle" and now >= self.state_until and self.expr != "yawn":
            self.choose_next()

        elif self.state == "sleep" and self.napping and now >= self.state_until:
            self.napping = False
            self.set_state("idle")

        # Expressions wear off
        if self.expr and now >= self.expr_until:
            self.expr = None

        # Late at night: yawn now and then
        if (self.state == "idle" and self.expr is None and now >= self.next_yawn
                and self.is_night()):
            self.set_expr("yawn", YAWN_SECONDS)
            self.state_until = max(self.state_until, now + YAWN_SECONDS + 0.4)
            self.next_yawn = now + random.uniform(*config.YAWN_EVERY)

        self.update_look()
        self.check_snack()

        # Blinking (not while asleep)
        if self.state != "sleep" and now >= self.next_blink:
            self.blink_start = now
            self.next_blink = now + random.uniform(*config.BLINK_EVERY)

        # Keep sitting on the taskbar if the screen/taskbar changes
        if self.state in ("idle", "sleep", "land"):
            self.stick_to_ground()

        if self.pending_say:
            self.bubble.say(*self.pending_say)
            self.pending_say = None
        if getattr(self, "pending_update", None):
            self.finish_update()
        if getattr(self, "pending_xp", None):
            ev, self.pending_xp = self.pending_xp, None
            self.handle_xp(ev)
        pop = getattr(self, "xp_popup", None)
        if pop is not None:
            if pop.alive():
                pop.follow(self.x_pos, self.y_pos, config.PET_SIZE,
                           self.current_screen().availableGeometry())
            else:                                    # gone: free it
                pop.close(); pop.deleteLater(); self.xp_popup = None
        if self.ask is not None:
            self.ask.follow(self.x_pos, self.y_pos, config.PET_SIZE,
                            self.current_screen().availableGeometry())
        self.bubble.follow(self.x_pos, self.y_pos, config.PET_SIZE,
                           self.current_screen().availableGeometry())
        self.update()   # repaint (calls paintEvent)

    # ---------- music ---------------------------------------------------------
    def check_music(self):
        if not config.music_active():            # both music options off: no checks at all
            if self.music_on:
                self.music_on = False
                self.apply_fps()
            if self.music.helper_running and not self.music.radio_on:
                self.music.stop_helper()
            return
        song, level, playing = self.music.update()
        if playing != self.music_on:
            self.music_on = playing
            self.apply_fps()
        self.music_level = level if playing else 0.0
        if playing or __import__("os").getenv("BLIP_DANCE"):
            if self.dancer is None:
                from dance import Dancer
                self.dancer = Dancer()
            self.dancer.update(time.monotonic(), level, self)
        if song and song != self.song and self.state != "sleep" and config.LISTEN_TO_MUSIC \
                and not __import__("extras").dnd_on():
            self.show_song(song)
        self.song = song

    def show_song(self, song=None):
        """Speech bubble with the song that's playing."""
        song = song or self.song
        if song:
            self.bubble.say("♪ Now playing", song)
        elif self.music_on:
            self.bubble.say("♪ Music", "I can hear music but I don't know the song!", 4.0)
        else:
            self.bubble.say("♪ Music", "Nothing playing right now", 4.0)
        self.bubble.follow(self.x_pos, self.y_pos, config.PET_SIZE,
                           self.current_screen().availableGeometry())

    def choose_next(self):
        """Idle time is over: walk, nap, climb onto a window or hop down."""
        import extras
        if extras.focus_left() > 0:                      # focusing: sit quietly
            self.set_state("idle", duration=10)
            return
        if extras.happiness() < 30 and random.random() < 0.1:
            self.set_expr("grumpy", 2.0)                 # a little sulk
            self.set_state("idle", duration=3)
            return
        awake_long = time.monotonic() - getattr(self, "awake_since", self.start) >= config.NAP_MIN_AWAKE
        nap_chance = 0.0 if (self.music_on or not awake_long) else \
            config.NAP_CHANCE * (2.5 if self.is_night() else 1.0)
        r = random.random()
        if self.music_on and r < 0.6:
            self.set_state("idle")                       # keep dancing!
        elif self.perch is not None and r < config.HOP_DOWN_CHANCE:
            self.hop_down()
        elif self.perch is None and config.SIT_ON_WINDOWS and r < config.CLIMB_CHANCE \
                and self.climb():
            pass
        elif random.random() < nap_chance:
            self.napping = True
            self.set_state("sleep")
        else:
            self.set_state("walk")

    # ---------- stage 4: night time --------------------------------------------
    @staticmethod
    def is_night():
        if not config.SLEEPY_AT_NIGHT:
            return False
        h = datetime.datetime.now().hour
        start, end = config.NIGHT_START_HOUR, config.NIGHT_END_HOUR
        return h >= start or h < end if start > end else start <= h < end

    # ---------- stage 4: CPU / RAM sweat ----------------------------------------
    def check_pc_load(self):
        """Every 6 seconds: sweat when busy, and maybe ask if you want help."""
        if not (config.SWEAT_WHEN_BUSY or config.PC_HELPER):
            self.sweating = False
            return
        cpu, ram = self.load.sample()
        self.cpu_avg = self.cpu_avg * 0.5 + cpu * 0.5          # smooth out short spikes
        if not config.SWEAT_WHEN_BUSY:
            self.sweating = False
        elif not self.sweating and (self.cpu_avg >= config.CPU_SWEAT_AT or ram >= config.RAM_SWEAT_AT):
            self.sweating = True
            print(f"Phew, your PC is working hard (CPU {self.cpu_avg:.0f}%, RAM {ram:.0f}%). Sweating!")
        elif self.sweating and self.cpu_avg < config.CPU_SWEAT_AT - 15                 and ram < config.RAM_SWEAT_AT - 4:
            self.sweating = False
            print("PC cooled down, no more sweating.")
        if config.PC_HELPER:
            self.maybe_ask(ram)

    # ---------- PC helper questions (Yes / No bubble) ---------------------------
    def maybe_ask(self, ram):
        if __import__("extras").dnd_on():
            return
        if self.ask is not None or self.hidden_for_game or self.state == "sleep"                 or self.helper is not None or self.chat is not None:
            return
        import sensors
        now = time.monotonic()
        ready = lambda key: now >= self.snooze.get(key, self.start + 20)
        gpu = sensors.gpu_temp()
        if gpu is not None and gpu >= config.GPU_HOT_AT and ready("hot"):
            self.ask_question("hot", f"My PC is getting hot! 🥵 Your GPU is at {gpu}°C. "
                              "Want me to help cool it down?", self.open_helper)
        elif ram >= config.RAM_SWEAT_AT and ready("ram"):
            self.ask_question("ram", f"Your RAM is nearly full ({ram:.0f}%) 😰 "
                              "Want me to free some up?", self.free_ram_now)
        elif self.cpu_avg >= config.CPU_SWEAT_AT and ready("cpu"):
            self.ask_question("cpu", "Your PC is working really hard! 😓 "
                              "Want to see what's using it?", self.open_helper)

    # ---------- reminders, questions, game buddy -----------------------------------
    def schedule_reminders(self):
        import buddy
        due = buddy.next_due()
        if due is None:
            self.reminder_timer.stop()
            return
        ms = int(max(1.0, min(due - __import__("time").time(), 86400.0)) * 1000)
        self.reminder_timer.start(ms)

    def fire_reminders(self):
        import buddy
        due = buddy.due_reminders()
        if not due:
            self.schedule_reminders()
            return
        if self.ask is not None or self.hidden_for_game:
            self.reminder_timer.start(30000)          # busy: try again in 30 s
            return
        r = due[0]
        import extras
        if extras.dnd_on():                           # Do Not Disturb: one small quiet bubble
            buddy.finish_reminder(r["id"])
            self.bubble.say("Reminder", r["text"][:1].upper() + r["text"][1:], 10)
            self.schedule_reminders()
            return
        extras.play("chime")
        if self.state == "sleep":
            self.napping = False
            self.set_state("idle")
        self.jump()

        def done(snooze):
            if not snooze:
                extras.cheer("reminder")
            buddy.finish_reminder(r["id"], snooze)
            self.ask = None
            self.schedule_reminders()
        from bubble import AskBubble
        self.ask = AskBubble(f"⏰ {r['text'][:1].upper()}{r['text'][1:]}!",
                             lambda: done(0), lambda: done(600), seconds=90,
                             yes="Done ✅", no="Snooze 10 min")
        self.ask.follow(self.x_pos, self.y_pos, config.PET_SIZE,
                        self.current_screen().availableGeometry())
        self.ask.show()

    def check_buddy(self, now):
        """Every 6 s (same check as CPU/RAM): game buddy, the odd question, antics."""
        self.maybe_antic(now)
        self.maybe_check_updates(now)
        self.night_light_tick(now)
        if user_idle_seconds() < 60 and not self.paused_now():
            import progress
            prog = progress.get()
            ev = prog.active_tick(6)
            if self.music_on:                        # listening to music together
                self.music_secs = getattr(self, "music_secs", 0) + 6
                if self.music_secs >= 900:
                    self.music_secs = 0
                    ev += prog.award("music")
            if __import__("extras").happiness() >= 70:
                ev += prog.award("happy")
            if ev:
                self.handle_xp(ev)
            self.maybe_offer_seek(now)
            self.care_tick(now)
        import buddy
        titles = [t for _, t in desktop.window_titles()]
        game = buddy.game_title(titles)
        if game:
            if self.game is None:
                self.game, self.game_start = game, now
                self.offer_game_boost(game)
            self.game_gone = 0
        elif self.game is not None:
            self.game_gone += 1
            if self.game_gone >= 2:                       # gone for ~12 s: match over
                played = now - self.game_start
                finished, self.game = self.game, None
                self.end_game_boost()
                min_play = 5 if __import__("os").getenv("BLIP_DEBUG_GAME") else buddy.MIN_PLAY
                if played >= min_play and config.GAME_BUDDY and not __import__("extras").dnd_on():
                    self.ask_match(finished)

        if (config.ASK_QUESTIONS and self.ask is None and self.chat is None
                and not __import__("extras").dnd_on()
                and not self.hidden_for_game and self.state != "sleep" and self.game is None
                and now - self.start > 600 and user_idle_seconds() < 60
                and random.random() < 0.1
                and buddy.question_due(datetime.datetime.now().hour)):
            q = buddy.pick_question()
            from ui import open_chat
            self.ask_bubble(q, lambda: open_chat(self, blip_says=q), yes="Reply", no="Not now",
                            seconds=30)

    def ask_match(self, game):
        import buddy

        def result(won):
            import extras
            extras.cheer("game")
            if won:
                extras.play("yay")
            self.bubble.say("GG! 🏆" if won else "Oof 💀", buddy.record_match(won, game), 6)
            if won:
                self.set_expr("happy", 3)
                self.jump()
        name = "the match" if len(game) > 30 else game
        self.ask_bubble(f"How did {name} go? 🎮", lambda: result(True), yes="Won 🏆",
                        no="Skip", extra=("Lost 💀", lambda: result(False)), seconds=60)

    def ask_bubble(self, text, on_yes, yes, no, seconds=20, extra=None):
        from bubble import AskBubble

        def wrap(cb):
            def run():
                self.ask = None
                if cb:
                    cb()
            return run
        self.bubble.hide()
        self.ask = AskBubble(text, wrap(on_yes), wrap(None), seconds=seconds, yes=yes, no=no,
                             extra=(extra[0], wrap(extra[1])) if extra else None)
        self.ask.follow(self.x_pos, self.y_pos, config.PET_SIZE,
                        self.current_screen().availableGeometry())
        self.ask.show()

    def ask_question(self, key, text, on_yes):
        from bubble import AskBubble
        self.snooze[key] = time.monotonic() + config.PC_HELPER_COOLDOWN   # yes, no or ignored
        self.bubble.hide()

        def done(action=None):
            self.ask = None
            if action:
                action()
        self.ask = AskBubble(text, lambda: done(on_yes), done)
        self.ask.follow(self.x_pos, self.y_pos, config.PET_SIZE,
                        self.current_screen().availableGeometry())
        self.ask.show()
        self.set_expr(None, 0)

    def open_helper(self):
        from ui import open_helper
        open_helper(self)

    def free_ram_now(self):
        import threading

        def work():
            import pchelper
            mb = pchelper.free_ram()
            ram, _ = pchelper.ram_cpu()
            self.pending_say = ("All done! ✨", f"Freed about {mb:,.0f} MB, RAM is now {ram:.0f}%.")
        self.bubble.say("On it! 🧹", "Freeing up some RAM…", 3)
        threading.Thread(target=work, daemon=True).start()

    # ---------- stage 4: sitting on windows --------------------------------------
    def find_spots(self, force=False):
        now = time.monotonic()
        if force or now - self.spots_at > 0.3:
            self.spots_at = now
            area = self.ground_area()
            spots = desktop.perch_spots(int(self.winId()), self.current_screen(),
                                        area.top() + config.PET_SIZE * 0.75)
            # keep only the part of each edge that's on this screen
            self.spots = [(h, max(a, area.left()), min(b, area.right()), top)
                          for h, a, b, top in spots
                          if min(b, area.right()) - max(a, area.left()) >= 70
                          and top < area.bottom() - 40]
        return self.spots

    def climb(self):
        """Jump up onto a nearby window. Returns False if there's none in reach."""
        ground = self.ground_area().bottom() - config.PET_SIZE + 1
        me = self.center_x()
        best = None
        for spot in self.find_spots(force=True):
            _, a, b, top = spot
            land_y = self.perch_floor(top)
            height = ground - land_y
            if height < 90 or height > 700:
                continue
            land_x = max(a + 45, min(me, b - 45))
            dist = abs(land_x - me)
            if dist > 900:
                continue
            if best is None or dist + height * 0.3 < best[0]:
                best = (dist + height * 0.3, land_x, height)
        if best is None:
            return False
        _, land_x, height = best
        g, k = config.GRAVITY, config.AIR_DRAG
        over = 45.0                                   # aim a little above the edge
        vy = math.sqrt(2 * g * (height + over))
        t = vy / g + math.sqrt(2 * over / g)          # time until we're back at the edge
        dx = land_x - me
        vx = dx * k / (1 - math.exp(-k * t)) if k > 0 else dx / t
        self.perch = None
        self.napping = False
        self.vx, self.vy = vx, -vy
        self.facing = 1 if dx >= 0 else -1
        self.last_tick = time.monotonic()
        self.set_state("fall")
        return True

    def hop_down(self, toward=None):
        """Jump off the window we're standing on."""
        if self.perch is None:
            return
        _, a, b, _ = self.perch
        me = self.center_x()
        if toward is None:
            toward = -1 if me - a < b - me else 1       # nearest edge
        self.leave_perch(1.5)
        self.facing = toward
        self.vx, self.vy = toward * 260.0, -520.0
        self.last_tick = time.monotonic()
        self.set_state("fall")

    def fall_off(self):
        """The window moved / closed / got covered: whoops!"""
        self.leave_perch(2.0)
        self.napping = False
        self.vx, self.vy = random.uniform(-60, 60), -180.0
        self.last_tick = time.monotonic()
        self.set_state("fall")

    def leave_perch(self, no_land_seconds):
        if self.perch is not None:
            self.no_land = (self.perch[0], time.monotonic() + no_land_seconds)
        self.perch = None
        self.spots_at = 0.0                          # look at the windows again

    def set_perch(self, spot):
        self.perch = spot
        self.perch_rect = desktop.window_still_there(spot[0], int(self.winId()),
                                                     self.current_screen())
        self.next_cover_check = time.monotonic() + 0.8

    def check_perch(self, now):
        hwnd = self.perch[0]
        r = desktop.window_still_there(hwnd, int(self.winId()), self.current_screen())
        pr = self.perch_rect
        if r is None or pr is None or abs(r.top() - pr.top()) > 2 \
                or (abs(r.left() - pr.left()) > 2 and abs(r.right() - pr.right()) > 2):
            self.fall_off()                          # closed, minimised, moved or maximised
            return
        self.perch_rect = r
        me = self.center_x()
        if not (r.left() + 10 <= me <= r.right() - 10):
            self.fall_off()                          # window got narrower under our feet
            return
        if now >= self.next_cover_check:             # another window put on top of ours?
            self.next_cover_check = now + 0.8
            for h, sa, sb, stop in self.find_spots(force=True):
                if h == hwnd and sa <= me <= sb:
                    self.perch = (hwnd, sa, sb, stop)
                    return
            self.fall_off()

    # ---------- eyes, snacks, expressions -------------------------------------
    def set_expr(self, expr, seconds):
        self.expr = expr
        self.expr_until = time.monotonic() + seconds

    def update_look(self):
        """Point the eyes at the mouse cursor."""
        if not config.EYES_FOLLOW_CURSOR or self.state in ("walk", "sleep"):
            self.look = (0.0, 0.0)
            return
        c = QCursor.pos()
        dx = c.x() - (self.x_pos + config.PET_SIZE / 2)
        dy = c.y() - (self.y_pos + config.PET_SIZE / 2)
        d = (dx * dx + dy * dy) ** 0.5
        if d < 1:
            self.look = (0.0, 0.0)
            return
        k = min(d / 250.0, 1.0)            # far away = look all the way over
        self.look = (dx / d * k, dy / d * k)

    def check_snack(self):
        snack = self.snack
        if snack is None:
            return
        if not snack.isVisible():
            self.snack = None
            return
        if not snack.on_ground or self.state not in ("idle", "walk"):
            return
        if self.perch is not None:                       # snack is down there: hop down!
            self.hop_down(toward=1 if snack.center_x() > self.center_x() else -1)
            return
        area = self.ground_area()
        reachable = (abs(snack.floor_y() + SNACK_SIZE - (self.floor_y() + config.PET_SIZE)) < 4
                     and area.left() <= snack.center_x() <= area.right())
        if not reachable:
            return
        target = snack.center_x() - config.PET_SIZE / 2
        if abs(target - self.x_pos) < 14:
            snack.close()
            snack.deleteLater()
            self.snack = None
            self.set_state("idle", duration=2.5)
            self.set_expr("happy", 2.5)                  # yum!
            import extras
            extras.cheer("feed")
            extras.play("giggle")
        elif self.state == "idle" or abs(self.target_x - target) > 2:
            self.set_state("walk", target=target)

    # ---------- actions used by the right-click menu -------------------------
    def toggle_sleep(self):
        if self.state == "sleep":
            self.napping = False
            self.set_state("idle")
        else:
            self.napping = True                          # stays asleep until woken
            self.set_state("sleep", duration=10 ** 9)

    def jump(self):
        if self.state in ("held", "fall"):
            return
        self.napping = False
        self.perch = None
        self.vx = self.facing * 120.0
        self.vy = -config.JUMP_SPEED
        self.last_tick = time.monotonic()
        self.set_state("fall")

    def feed(self):
        if self.snack is not None:
            self.snack.close()
            self.snack.deleteLater()
        area = self.ground_area()
        x = self.x_pos + config.PET_SIZE / 2 + random.uniform(-260, 260)
        x = max(area.left() + 10, min(x, area.right() - SNACK_SIZE - 10))
        self.snack = Snack(x, area.top() + 10)
        self.snack.show()
        if self.state == "sleep":
            self.napping = False
            self.set_state("idle")

    def settings_changed(self):
        """Called after Save in the Settings window."""
        self.end_antic()
        self.setFixedSize(config.PET_SIZE, config.PET_SIZE)
        if self.perch is not None and not config.SIT_ON_WINDOWS:
            self.fall_off()
        if not config.SWEAT_WHEN_BUSY:
            self.sweating = False
        if self.state not in ("held", "fall"):
            self.stick_to_ground()
        if self.hidden_for_game and not config.HIDE_IN_FULLSCREEN:
            self.hidden_for_game = False
            self.show()
        self.apply_fps()
        self.update()
        if self.after_settings:
            self.after_settings()

    def contextMenuEvent(self, event):
        if self.menu is not None:
            self.menu.exec(event.globalPos())

    def check_user_idle(self):
        # Watching a video / listening / gaming with a controller doesn't count as "away".
        sound = time.monotonic() - self.music.last_sound < 15
        away = (user_idle_seconds() >= config.USER_IDLE_SLEEP_SECONDS
                and not sound and not self.hidden_for_game)
        if away and self.state != "sleep":
            self.napping = False
            self.set_state("sleep", duration=10 ** 9)   # sleep until you return
        elif not away and self.state == "sleep" and not self.napping:
            self.set_state("idle")                      # you're back, wake up

    def check_fullscreen(self):
        if not config.HIDE_IN_FULLSCREEN or self.state == "held":
            return
        full = fullscreen_app_on_my_screen(int(self.winId()))
        if full and not self.hidden_for_game:
            print(f"Hiding: a fullscreen app is on my screen ({full}). "
                  "Turn this off in Customise & settings if it's wrong.")
            self.hidden_for_game = True
            self.hide()
            self.apply_fps()
        elif not full and self.hidden_for_game:
            print("Fullscreen app gone, I'm back!")
            self.hidden_for_game = False
            self.show()
            self.apply_fps()

    # ---------- physics ---------------------------------------------------------
    def physics(self, dt):
        old_y = self.y_pos
        self.vy += config.GRAVITY * dt
        self.vx *= max(0.0, 1.0 - config.AIR_DRAG * dt)
        self.x_pos += self.vx * dt
        self.y_pos += self.vy * dt

        # Falling past the top edge of a window? Land (or bounce) on it.
        if self.vy > 0 and config.SIT_ON_WINDOWS:
            me = self.center_x()
            for spot in self.find_spots():
                hwnd, a, b, top = spot
                if hwnd == self.no_land[0] and time.monotonic() < self.no_land[1]:
                    continue                             # just left this one
                fy = self.perch_floor(top)
                if old_y <= fy <= self.y_pos and a + 20 <= me <= b - 20:
                    self.y_pos = fy
                    if self.vy > 250:                    # still fast: bounce
                        self.vy = -self.vy * config.BOUNCE
                        self.vx *= config.GROUND_FRICTION
                    else:                                # slow: land on the window
                        self.vx = self.vy = 0.0
                        self.set_perch(spot)
                        self.set_state("land")
                    self.move(int(self.x_pos), int(self.y_pos))
                    return

        # Walls = outer left/right edges of all your screens together
        desk = QGuiApplication.primaryScreen().virtualGeometry()
        left, right = desk.left(), desk.right() - config.PET_SIZE + 1
        if self.x_pos < left:
            self.x_pos, self.vx = left, abs(self.vx) * config.BOUNCE
        elif self.x_pos > right:
            self.x_pos, self.vx = right, -abs(self.vx) * config.BOUNCE

        area = self.ground_area()
        # Ceiling
        if self.y_pos < area.top():
            self.y_pos, self.vy = area.top(), abs(self.vy) * config.BOUNCE
        # Floor (top of the taskbar)
        floor = self.floor_y()
        if self.y_pos >= floor:
            self.y_pos = floor
            if self.vy > 250:                        # still fast: bounce
                self.vy = -self.vy * config.BOUNCE
                self.vx *= config.GROUND_FRICTION
            else:                                    # slow: land
                self.vx = self.vy = 0.0
                self.set_state("land")
                if getattr(self, "throw_from", None) is not None:
                    dist = abs(self.x_pos - self.throw_from)
                    self.throw_from = None
                    if dist > 500:                   # thrown far across the screen
                        import progress
                        self.handle_xp(progress.get().award("throw", int(min(80, dist / 15))))

        if abs(self.vx) > 30:
            self.facing = 1 if self.vx > 0 else -1
        self.move(int(self.x_pos), int(self.y_pos))

    # ---------- mouse: drag, throw, double-click jump ----------------------------
    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        offset = QPoint(self.margin, self.margin)
        if self.state == "fall" and abs(self.vy) + abs(self.vx) > 300 and self.antic is None:
            __import__("extras").cheer("catch")        # caught him in mid-air!
        if self.antic is not None:
            if type(self.antic).__name__ == "HideSeek" and self.antic.t >= 0.6:
                self.antic.caught()             # found him!
                return
            self.end_antic()                    # clicking cancels the antic
        now = time.monotonic()
        self.pokes.append(now)
        recent = [p for p in self.pokes if now - p < 2.0]
        if len(recent) >= config.POKES_TO_GET_GRUMPY and self.expr != "grumpy":
            self.set_expr("grumpy", config.GRUMPY_SECONDS)      # stop poking me!
            self.pokes.clear()
        self.press_global = event.globalPosition().toPoint()
        self.press_time = now
        self.napping = False
        self.press_perch = self.perch           # put back if this is just a poke
        self.perch = None
        self.grab_offset = event.position().toPoint() - offset
        self.drag_trail.clear()
        g = event.globalPosition()
        self.drag_trail.append((time.monotonic(), g.x(), g.y()))
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        self.set_state("held")
        self.update()

    def mouseMoveEvent(self, event):
        if self.state != "held":
            self.check_petting(event)
            return
        g = event.globalPosition()
        self.drag_trail.append((time.monotonic(), g.x(), g.y()))
        top_left = g.toPoint() - self.grab_offset
        self.x_pos, self.y_pos = float(top_left.x()), float(top_left.y())
        self.move(top_left)

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or self.state != "held":
            return
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        # A quick click without moving = a friendly poke
        moved = (event.globalPosition().toPoint() - self.press_global).manhattanLength()
        if moved < 5 and time.monotonic() - self.press_time < 0.35:
            if self.expr != "grumpy":
                self.set_expr("happy", 1.2)
                import extras
                extras.cheer("poke")
                extras.play("boop")
            if time.monotonic() < self.help_offer_until:  # poked after "want help?"
                self.help_offer_until = 0.0
                self.bubble.hide()
                from ui import open_helper
                open_helper(self)
            if self.press_perch is not None:     # poked while sitting on a window
                self.perch = self.press_perch
                self.set_state("idle")
                return
            if self.y_pos >= self.floor_y() - 1:
                self.set_state("idle")
                return
        # Throw speed = how far the mouse moved in the last ~0.1 seconds
        now = time.monotonic()
        recent = [p for p in self.drag_trail if now - p[0] < 0.1]
        if len(recent) >= 2 and recent[-1][0] > recent[0][0]:
            t0, x0, y0 = recent[0]
            t1, x1, y1 = recent[-1]
            self.vx = (x1 - x0) / (t1 - t0)
            self.vy = (y1 - y0) / (t1 - t0)
        else:
            self.vx = self.vy = 0.0
        cap = config.MAX_THROW_SPEED
        self.vx = max(-cap, min(cap, self.vx))
        self.vy = max(-cap, min(cap, self.vy))
        self.last_tick = now
        self.throw_from = self.x_pos if abs(self.vx) > 600 else None
        self.set_state("fall")

    def mouseDoubleClickEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        if self.expr == "grumpy":                 # grumpy Blip refuses to jump
            self.perch = self.press_perch
            self.set_state("idle")
            return
        self.set_state("idle")
        self.jump()
        __import__("extras").cheer("jump")

    # ---------- drawing ---------------------------------------------------------
    def blink_amount(self):
        if self.blink_start < 0:
            return 0.0
        k = (time.monotonic() - self.blink_start) / 0.16   # blink lasts 0.16s
        if k >= 1.0:
            self.blink_start = -1.0
            return 0.0
        return 1.0 - abs(k * 2 - 1)    # 0 -> 1 -> 0

    def paintEvent(self, event):
        now = time.monotonic()
        yawn = 0.0
        if self.expr == "yawn":
            k = 1.0 - (self.expr_until - now) / YAWN_SECONDS
            yawn = math.sin(math.pi * max(0.0, min(1.0, k)))
        p = QPainter(self)
        if self.antic is not None:
            p.translate(self.margin, self.margin)
            self.antic.paint(p)
            p.end()
            return
        if self.dancer is not None and config.DANCE and (self.music_on or __import__("os").getenv("BLIP_DANCE"))                 and self.state in ("idle", "land") and self.expr not in ("yawn", "grumpy"):
            self.dancer.paint(p, self, self.music_level)
            self.paint_badges(p)
            p.end()
            return
        draw_pet(p, config.PET_SIZE, self.state, now - self.start,
                 facing=self.facing, blink=self.blink_amount(), step=self.step,
                 look=self.look, expr=self.expr, sweat=self.sweating,
                 sleepy=self.is_night() or __import__("extras").happiness() < 30, yawn=yawn,
                 music=max(self.music_level, 0.001) if (self.music_on and config.DANCE) else 0.0)
        self.paint_badges(p)
        p.end()

    def paint_badges(self, p):
        """Small extras on top of Blip: DND moon, focus minutes, seasonal snow/confetti/hearts."""
        import extras
        from PyQt6.QtGui import QColor, QFont
        from PyQt6.QtCore import QPointF
        k = config.PET_SIZE / 120.0
        t = time.monotonic() - self.start
        left = extras.focus_left()
        if left > 0:
            f = QFont("Segoe UI", 1); f.setBold(True); f.setPixelSize(int(11 * k))
            p.setFont(f)
            p.setPen(QColor(0, 0, 0, 0))
            p.setBrush(QColor(20, 14, 40, 200))
            p.drawRoundedRect(int(4 * k), int(6 * k), int(30 * k), int(15 * k), 6, 6)
            p.setPen(QColor(0, 225, 255))
            p.drawText(int(7 * k), int(17 * k), f"{int(left // 60) + 1}m")
        elif extras.dnd_on():                            # crescent moon
            p.setPen(QColor(0, 0, 0, 0))
            p.setBrush(QColor(255, 225, 120, 230))
            p.drawEllipse(QPointF(14 * k, 16 * k), 7 * k, 7 * k)
            p.setBrush(QColor(0, 0, 0, 0))
            from PyQt6.QtGui import QPainter
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            p.setBrush(QColor(0, 0, 0))
            p.drawEllipse(QPointF(17.5 * k, 13.5 * k), 6 * k, 6 * k)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        import progress as _pg
        trail = _pg.get().equipped.get("trail")
        if trail:
            import shop
            shop.draw_trail(p, trail, config.PET_SIZE, t, self.facing, self.state in ("walk", "fall", "held"))
        effect = "confetti" if time.monotonic() < self.confetti_until else extras.season_effect()
        if time.monotonic() < self.blush_until:              # petted: rosy cheeks
            p.setPen(QColor(0, 0, 0, 0))
            p.setBrush(QColor(255, 120, 170, 140))
            for side in (-1, 1):
                p.drawEllipse(QPointF((60 + side * 22) * k, 86 * k), 6 * k, 3.5 * k)
        import progress
        prog = progress.get()
        if config.TIME_PROPS:
            self.paint_time_props(p, k, t)
        if prog.aura and prog.prestige and self.state != "sleep":
            import skins
            skins.paint_aura(p, prog.prestige, QPointF(60 * k, 78 * k), 46 * k, t)
        if effect and self.state != "sleep":
            import random as rnd
            rng = rnd.Random(7)
            for i in range(7):
                x = rng.uniform(8, 112)
                speed = rng.uniform(0.15, 0.3)
                y = ((t * speed + rng.random()) % 1.0) * 110
                if effect == "snow":
                    p.setPen(QColor(0, 0, 0, 0)); p.setBrush(QColor(255, 255, 255, 200))
                    p.drawEllipse(QPointF(x * k + math.sin(t + i) * 3, y * k), 1.8 * k, 1.8 * k)
                elif effect == "confetti":
                    cols = ((255, 90, 170), (0, 225, 255), (255, 230, 90), (150, 255, 120))
                    p.setPen(QColor(0, 0, 0, 0)); p.setBrush(QColor(*cols[i % 4], 220))
                    p.save(); p.translate(x * k, y * k); p.rotate(t * 200 + i * 40)
                    p.drawRect(int(-2 * k), int(-1 * k), int(4 * k), int(2 * k)); p.restore()
                elif effect == "hearts" and i < 3:
                    from character import draw_heart
                    draw_heart(p, (20 + i * 40) * k, (100 - y * 0.6) * k, 4 * k, int(200 * (1 - y / 110)))

    # ---------- random antics ---------------------------------------------------------
    def move(self, *args):
        """Same as QWidget.move, but keeps Blip in place when the antic margin is on."""
        if len(args) == 1:
            x, y = args[0].x(), args[0].y()
        else:
            x, y = args
        m = getattr(self, "margin", 0)
        super().move(int(x) - m, int(y) - m)

    def set_margin(self, m):
        self.margin = int(m)
        self.setFixedSize(config.PET_SIZE + 2 * self.margin, config.PET_SIZE + 2 * self.margin)
        self.move(int(self.x_pos), int(self.y_pos))

    def draw_body(self, p, state=None, expr="same", angle=0.0, pivot=(60, 112), dx=0.0, dy=0.0,
                  look=None, blink=None, music=False):
        """Draws Blip for an antic: optionally tilted around `pivot` (120-px grid) and shifted."""
        k = config.PET_SIZE / 120.0
        p.save()
        p.translate(dx * k, dy * k)
        if angle:
            p.translate(pivot[0] * k, pivot[1] * k)
            p.rotate(angle)
            p.translate(-pivot[0] * k, -pivot[1] * k)
        draw_pet(p, config.PET_SIZE, state or "idle", time.monotonic() - self.start,
                 facing=self.facing, blink=self.blink_amount() if blink is None else blink,
                 step=self.step, look=self.look if look is None else look,
                 expr=self.expr if expr == "same" else expr, sweat=self.sweating,
                 music=max(self.music_level, 0.001) if music else 0.0)
        p.restore()

    # ---------- focus timer (one single-shot timer) --------------------------------------
    def start_focus(self, minutes=25):
        import extras
        extras.focus_end = time.time() + minutes * 60
        if not hasattr(self, "focus_timer"):
            self.focus_timer = QTimer(self)
            self.focus_timer.setSingleShot(True)
            self.focus_timer.timeout.connect(self.focus_done)
        self.focus_timer.start(int(minutes * 60 * 1000))
        self.end_antic()
        self.set_state("idle", duration=10)
        self.bubble.say("Focus mode", f"{minutes} minutes. I'll be quiet! Do Not Disturb is on.", 4)

    def stop_focus(self):
        import extras
        extras.focus_end = 0.0
        if hasattr(self, "focus_timer"):
            self.focus_timer.stop()
        self.bubble.say("Focus", "Focus stopped.", 2)

    def focus_done(self):
        import extras
        extras.focus_end = 0.0
        extras.cheer("focus")
        extras.play("chime")
        self.jump()

        def take_break():
            self.bubble.say("Break", "Enjoy your 5 minute break!", 4)
            QTimer.singleShot(5 * 60 * 1000, lambda: (extras.play("chime"),
                              self.bubble.say("Break's over!", "Ready for another focus round?", 8)))
        self.ask_bubble("Break time! Stretch", take_break, yes="5 min break", no="Keep going",
                        seconds=60)
        # "Keep going" (the No button) starts another round
        ask = self.ask
        if ask is not None:
            old_no = ask.on_no
            ask.on_no = lambda: (old_no(), self.start_focus(25))

    # ---------- levels, petting, hide and seek, screenshot pose ------------------------------
    # ---------- updates (once a day, asks before doing anything) ---------------------------
    def get_updater(self):
        if getattr(self, "updater", None) is None:
            from updater import Updater
            self.updater = Updater()
            self.updater.result.connect(self.on_update_result)
        return self.updater

    def maybe_check_updates(self, now):
        if getattr(self, "update_waiting", False) and self.good_time_to_update():
            self.update_waiting = False
            self.start_update()
            return
        if now - self.start < 60 or not config.AUTO_UPDATE:
            return
        try:
            last = float(config.UPDATE_LAST or 0)
        except ValueError:
            last = 0.0
        if time.time() - last < 6 * 3600:
            return
        self.get_updater().check()

    def good_time_to_update(self):
        import extras
        return (not self.hidden_for_game and self.chat is None and extras.focus_left() <= 0
                and self.antic is None)

    def check_updates(self):
        self.bubble.say("Updates", "Checking for updates…", 3)
        self.get_updater().check(manual=True)

    def on_update_result(self, r):
        if r["status"] == "new":
            self.update_version = r["version"]
            if config.AUTO_UPDATE or r.get("manual"):
                if self.good_time_to_update():
                    self.start_update()
                else:
                    self.update_waiting = True          # after the game / chat / focus session
            else:
                self.ask_bubble(f"Update available (v{r['version']})!", self.start_update,
                                yes="Update", no="Later", seconds=60)
        elif r.get("manual"):
            if r["status"] == "current":
                self.bubble.say("Updates", f"You're up to date (v{r['version']}).", 4)
            else:
                self.bubble.say("Updates", r.get("msg", "Couldn't check for updates."), 6)

    def start_update(self):
        self.bubble.say("Updating", f"Updating to v{getattr(self, 'update_version', '')}…", 20)

        def ready(path, msg):                       # (called from the download thread)
            self.pending_update = (path, msg)
        self.get_updater().install(ready)

    def finish_update(self):
        path, msg = self.pending_update
        self.pending_update = None
        if not path:
            self.bubble.say("Update", msg or "Update failed.", 6)
            return
        import updater, settings
        settings.save()
        self.bubble.say("Updating", "See you in a moment!", 3)
        updater.run_installer(path)
        from PyQt6.QtWidgets import QApplication
        QTimer.singleShot(1500, QApplication.instance().quit)

    # ---------- v1.2: PC care, nudges, summary, time props ----------------------------------
    def care_ok(self):
        import extras
        return (not self.hidden_for_game and not extras.dnd_on() and extras.focus_left() <= 0
                and self.state != "sleep" and self.ask is None and self.chat is None
                and self.antic is None and self.game is None)

    def care_tick(self, now):
        before = dict(config.CARE_STATE)
        self._care_tick(now)
        if config.CARE_STATE != before:                   # remember what was shown / asked
            __import__("settings").save()

    def _care_tick(self, now):
        """Every 6 s while you're active; the actual checks run every few minutes."""
        import datetime as dt
        st = config.CARE_STATE
        today = dt.date.today().isoformat()
        hour = dt.datetime.now().hour
        # hourly wellbeing nudges
        if config.NUDGES:
            self.nudge_secs = getattr(self, "nudge_secs", 0) + 6
            if self.nudge_secs >= config.NUDGE_MINUTES * 60 and 8 <= hour < 23 and self.care_ok():
                self.nudge_secs = 0
                self.show_nudge()
                return
        # evening summary
        if config.DAILY_SUMMARY and hour >= 20 and st.get("summary") != today and self.care_ok():
            st["summary"] = today
            self.show_summary()
            return
        if not hasattr(self, "next_care"):
            self.next_care = now + 1800                   # first PC check 30 min after start
        if not config.PC_CARE or now < self.next_care or not self.care_ok():
            return
        self.next_care = now + 600                        # PC checks: every 10 minutes at most
        import care
        full, free_gb = care.disk_full_percent()
        if full >= 90 and st.get("disk") != today:
            st["disk"] = today
            self.ask_bubble(f"Your C: drive is {full:.0f}% full ({free_gb:.1f} GB free). Clean temp files?",
                            self.tidy_up, yes="Clean up", no="Not now", seconds=30)
            return
        if care.uptime_days() >= 7 and st.get("restart") != today:
            st["restart"] = today
            self.bubble.say("Restart tip", "Your PC has been on for 7+ days. A restart keeps it snappy!", 8)
            return
        week = "%d-W%02d" % dt.date.today().isocalendar()[:2]
        if st.get("tidy_week") != week:
            st["tidy_week"] = week
            freed = st.get("freed_mb", 0)
            if freed:
                self.bubble.say("Weekly report", f"Last week I helped free {freed / 1024:.1f} GB. Nice!", 6)
                st["freed_mb"] = 0
            self.ask_bubble("Weekly tidy-up? I'll clean old temp files and empty the Recycle Bin.",
                            self.tidy_up, yes="Tidy up", no="Skip", seconds=30)
            return
        if st.get("startup_week") != week:
            st["startup_week"] = week
            from ui import StartupDialog
            self.ask_bubble("Want to check which apps start with Windows? Fewer = faster boot.",
                            lambda: StartupDialog(self).exec(), yes="Show me", no="Not now", seconds=30)
            return
        self.check_ram_hog(today)

    def check_ram_hog(self, today):
        try:
            import psutil
            vm = psutil.virtual_memory()
            if vm.percent < 85:                            # only look closer when RAM is really full
                return
            total = vm.total
            best = None
            for p_ in psutil.process_iter(["name", "memory_info"]):
                mi = p_.info.get("memory_info")
                if mi and (best is None or mi.rss > best[1]):
                    best = (p_.info.get("name") or "?", mi.rss)
            if best and best[1] > total * 0.35:
                key = "hog_" + best[0]
                if config.CARE_STATE.get(key) != today:
                    config.CARE_STATE[key] = today
                    from ui import open_helper
                    self.ask_bubble(f"{best[0]} is using {best[1] / 1073741824:.1f} GB of RAM. Have a look?",
                                    lambda: open_helper(self), yes="Show me", no="It's fine", seconds=25)
        except Exception:
            pass

    def tidy_up(self):
        import threading

        def work():
            import pchelper, ctypes
            mb = pchelper.clean_temp()
            try:                                           # Recycle Bin (you said yes)
                class Q(ctypes.Structure):
                    _fields_ = [("cbSize", ctypes.c_ulong), ("i64Size", ctypes.c_longlong),
                                ("i64NumItems", ctypes.c_longlong)]
                q = Q(); q.cbSize = ctypes.sizeof(Q)
                sh = ctypes.WinDLL("shell32")
                sh.SHQueryRecycleBinW(None, ctypes.byref(q))
                if q.i64NumItems:
                    sh.SHEmptyRecycleBinW(None, None, 0x7)  # no confirm / progress / sound
                    mb += q.i64Size / 1048576
            except Exception:
                pass
            config.CARE_STATE["freed_mb"] = config.CARE_STATE.get("freed_mb", 0) + int(mb)
            self.pending_say = ("All tidy!", f"Freed about {mb:,.0f} MB.")
            import progress, care
            prog = progress.get()
            self.pending_xp = prog.award("tidy")
        self.bubble.say("Tidying up", "Cleaning temp files and the Recycle Bin…", 4)
        threading.Thread(target=work, daemon=True).start()

    def offer_game_boost(self, game):
        if not config.PC_CARE or __import__("extras").dnd_on():
            return
        import pchelper
        plans = pchelper.power_plans()
        fast = next((g for g, n, a in plans if "ultimate" in n.lower()), None) or \
            next((g for g, n, a in plans if "high" in n.lower()), None)
        active = next((g for g, n, a in plans if a), None)
        if not fast or fast == active and not config.BOOST_APPS:
            return

        def boost():
            self.boost_restore = active
            if fast and fast != active:
                pchelper.set_power_plan(fast)
            closed = []
            for app in pchelper.top_apps(limit=40):
                if app["name"] in config.BOOST_APPS and not app["windowed"]:
                    pchelper.close_app(app)
                    closed.append(app["name"])
            self.pending_say = ("Boost on!", "High performance on" + (f", closed {', '.join(closed)}" if closed else "")
                                + ". I'll switch back after your game.")
        extra = f" and close {', '.join(config.BOOST_APPS[:3])}" if config.BOOST_APPS else ""
        self.ask_bubble(f"Game time! Switch to High performance{extra}?", lambda: __import__("threading").Thread(
            target=boost, daemon=True).start(), yes="Boost!", no="No thanks", seconds=20)

    def end_game_boost(self):
        guid = getattr(self, "boost_restore", None)
        if guid:
            self.boost_restore = None
            import pchelper
            pchelper.set_power_plan(guid)
            self.bubble.say("Boost off", "Power plan switched back.", 3)

    def show_nudge(self):
        import care
        last = getattr(self, "last_nudge", None)
        text = care.pick_nudge()
        while text == last and len(care.NUDGES) > 1:
            text = care.pick_nudge()
        self.last_nudge = text

        def done():
            import progress
            prog = progress.get()
            self.handle_xp(prog.award("nudge"))
            self.set_expr("happy", 2)
        self.ask_bubble(text, done, yes="Done!", no="Later", seconds=30)

    def show_summary(self):
        import progress
        prog = progress.get()
        secs = prog.daily.get("active_secs", 0)
        quests = sum(1 for _, _, d in prog.today_quests() if d)
        focus = prog.daily.get("focus", 0)
        self.bubble.say("Today with Blip", f"{int(secs // 3600)}h {int(secs % 3600 // 60)}m at the PC · "
                        f"{focus} focus · {quests}/3 quests · +{prog.daily.get('xp', 0)} XP", 10)

    def paint_time_props(self, p, k, t):
        from PyQt6.QtGui import QColor, QPen
        from PyQt6.QtCore import QPointF, QRectF
        h = __import__("datetime").datetime.now().hour
        if 6 <= h < 11 and self.state == "idle" and not self.music_on and self.antic is None:
            x, y = 96 * k, 92 * k                        # morning coffee mug
            p.setPen(QPen(QColor(255, 255, 255, 200), 1.2 * k))
            p.setBrush(QColor(240, 240, 250))
            p.drawRoundedRect(QRectF(x - 6 * k, y - 8 * k, 12 * k, 13 * k), 2 * k, 2 * k)
            p.setBrush(QColor(0, 0, 0, 0))
            p.drawArc(QRectF(x + 4 * k, y - 5 * k, 6 * k, 7 * k), -90 * 16, 180 * 16)
            p.setPen(QPen(QColor(255, 255, 255, 120), 1 * k))
            for i in range(2):                            # steam
                sx = x - 2 * k + i * 4 * k
                p.drawLine(QPointF(sx + __import__("math").sin(t * 3 + i) * 1.5 * k, y - 11 * k),
                           QPointF(sx, y - 16 * k))
        elif self.state == "sleep" and (h >= 23 or h < 6):
            from PyQt6.QtGui import QPolygonF          # nightcap
            p.setPen(QColor(0, 0, 0, 0))
            p.setBrush(QColor(60, 80, 200, 230))
            p.drawPolygon(QPolygonF([QPointF(36 * k, 58 * k), QPointF(70 * k, 40 * k), QPointF(84 * k, 58 * k)]))
            p.setBrush(QColor(255, 255, 255))
            p.drawEllipse(QPointF(72 * k, 40 * k), 4 * k, 4 * k)

    # ---------- night light + power modes ------------------------------------------------
    def night_light_tick(self, now, force=False):
        if config.NIGHT_LIGHT_MODE == "Off" and not config.NIGHT_LIGHT_ACTIVE and not force:
            return                                       # nothing to do: no code runs
        import datetime as dt, nightlight
        n = dt.datetime.now()
        want = nightlight.should_be_on(n.hour, n.minute, self.hidden_for_game)
        is_on = config.NIGHT_LIGHT_ACTIVE
        if want and (not is_on or force or now >= getattr(self, "nl_refresh", 0)):
            self.nl_refresh = now + 300                  # re-apply now and then (Windows can reset it)
            if not nightlight.turn_on():
                config.NIGHT_LIGHT_MODE = "Off"
                self.bubble.say("Night light", "This screen won't take my filter. I opened Windows' Night light.", 6)
        elif not want and is_on:
            nightlight.restore()

    def set_night_light(self, mode):
        config.NIGHT_LIGHT_MODE = mode
        __import__("settings").save()
        self.night_light_tick(time.monotonic(), force=True)
        msg = {"On": "Night light on. Easier on the eyes!", "Off": "Night light off.",
               "Schedule": f"Night light will come on {config.NIGHT_LIGHT_FROM}:00-{config.NIGHT_LIGHT_TO:02d}:00."}[mode]
        self.bubble.say("Night light", msg, 3)

    def set_power_mode(self, which):
        """which: 'saver', 'balanced' or 'high'. Uses Windows' own power plans (no admin)."""
        import pchelper
        plans = pchelper.power_plans()
        want = {"saver": ("power saver", "eco"), "balanced": ("balanced",),
                "high": ("ultimate", "high performance")}[which]
        pick = None
        for key in want:
            pick = next(((g, n) for g, n, a in plans if key in n.lower()), None)
            if pick:
                break
        if not pick:
            self.bubble.say("Power mode", "That power plan isn't on this PC.", 4)
            return None
        pchelper.set_power_plan(pick[0])
        self.bubble.say("Power mode", f"Switched to {pick[1]}.", 3)
        return pick[1]

    def paused_now(self):
        return getattr(self, "paused", False)

    def hello_today(self):
        import progress, extras, datetime as dt
        if config.LAST_VERSION != config.VERSION:
            if config.LAST_VERSION:
                self.bubble.say("Updated!", f"Updated to v{config.VERSION}!", 5)
            config.LAST_VERSION = config.VERSION
            __import__("settings").save()
        prog = progress.get()
        ev = prog.daily_hello()
        if ev:
            self.handle_xp(ev)
        today = dt.date.today()
        if prog.birthday == f"{today.month:02d}-{today.day:02d}":
            name = __import__("brain").load_memory().get("name")
            self.confetti_until = time.monotonic() + 10
            self.bubble.say("Happy birthday!", f"Happy birthday {name}!" if name else "Happy birthday!", 10)
            extras.play("yay")
        # look again just after midnight (one single-shot timer)
        now = dt.datetime.now()
        tomorrow = dt.datetime.combine(today + dt.timedelta(days=1), dt.time(0, 0, 30))
        QTimer.singleShot(int((tomorrow - now).total_seconds() * 1000), self.hello_today)

    def handle_xp(self, events):
        import extras
        for ev in events:
            if ev[0] == "achievement":
                self.bubble.say("Achievement unlocked!", f"{ev[1]}: {ev[2]}", 5)
                self.confetti_until = time.monotonic() + 3
                extras.play("yay")
        events = [e for e in events if e[0] != "achievement"]
        gain = sum(ev[1] for ev in events if ev[0] == "xp")
        if gain:
            self.show_xp_popup(gain)
        for ev in events:
            if ev[0] == "quest":
                self.bubble.say("Quest complete!", f"{ev[1]}  +{ev[2]} XP", 4)
                extras.play("yay")
            elif ev[0] == "weekly":
                self.bubble.say("Weekly challenge done!", f"+{ev[1]} XP and a Prestige Token", 5)
            elif ev[0] == "token":
                self.bubble.say("Prestige Token!", "You earned a token for the Prestige Shop.", 4)
            elif ev[0] == "level":
                self.confetti_until = time.monotonic() + 3.5
                self.bubble.say("LEVEL UP!", f"Level {ev[1]}", 3.5)
                extras.play("yay")
                if self.state in ("idle", "walk") and self.antic is None:
                    self.jump()
            elif ev[0] == "prestige_ready":
                self.bubble.say("Level 55!", "You can Prestige now in Customise & settings!", 8)
        if getattr(self, "update_tray", None):
            self.update_tray()

    def show_xp_popup(self, gain):
        import progress, shop
        prog = progress.get()
        need = progress.xp_for_level(prog.level)
        after = 1.0 if prog.level >= progress.MAX_LEVEL else prog.xp / need
        before = max(0.0, after - gain / need)
        if getattr(self, "xp_popup", None) is None:
            from bubble import XPPopup
            self.xp_popup = XPPopup()
        badge = prog.badge()
        name = config.APP_NAME + (f" {badge}" if badge else "")
        self.xp_popup.add(gain, name, prog.level, before, after,
                          shop.TAG_COLOURS.get(prog.equipped.get("tag")))
        self.xp_popup.follow(self.x_pos, self.y_pos, config.PET_SIZE,
                             self.current_screen().availableGeometry())

    def celebrate_prestige(self):
        import progress, extras
        prog = progress.get()
        self.confetti_until = time.monotonic() + 8
        self.bubble.say("PRESTIGE!", f"Prestige {prog.prestige}! Back to level 1, badge forever.", 6)
        extras.play("yay")
        self.jump()
        QTimer.singleShot(1200, self.jump)
        if getattr(self, "update_tray", None):
            self.update_tray()

    def check_petting(self, event):
        """Wiggle the mouse back and forth over Blip (no clicking) to pet him."""
        now = time.monotonic()
        x = event.position().x()
        if self.pet_moves and abs(x - self.pet_moves[-1][1]) < 3:
            return
        self.pet_moves.append((now, x))
        pts = [m for m in self.pet_moves if now - m[0] < 1.5]
        turns = sum(1 for a, b, c in zip(pts, pts[1:], pts[2:])
                    if (b[1] - a[1]) * (c[1] - b[1]) < 0)
        if turns >= 4 and now - self.last_pet > 8 and self.state != "sleep":
            import extras
            self.last_pet = now
            self.pet_moves.clear()
            self.blush_until = now + 3
            self.set_expr("happy", 3)
            extras.cheer("pet")
            extras.play("giggle")
            self.bubble.say("Purrr...", "That's nice!", 2)

    def maybe_offer_seek(self, now):
        import extras, progress
        if (extras.dnd_on() or self.ask is not None or self.antic is not None or self.chat is not None
                or self.state not in ("idle", "walk") or random.random() > 0.004):
            return
        prog = progress.get()
        today = __import__("datetime").date.today().isoformat()
        if prog.daily.get("seek_offer") == today:
            return
        prog.daily["seek_offer"] = today
        prog.save()
        self.ask_bubble("Wanna play hide and seek?", lambda: self.trick("seek"), yes="Let's play!",
                        no="Not now", seconds=20)

    def screenshot_pose(self):
        from PyQt6.QtWidgets import QApplication
        md = QApplication.clipboard().mimeData()
        if config.CLIPBOARD_HELPER and md is not None and md.hasText() and not md.hasImage():
            import care
            info = care.clipboard_info(md.text())     # read here, never stored or sent
            if info:
                self.bubble.say(info[0], info[1], 6, swatch=info[2])
            return
        if md is not None and md.hasImage() and self.antic is None and self.state in ("idle", "walk") \
                and not self.paused_now():
            self.start_antic("pose")

    def trick(self, name=None):
        """Play ▸ menu: do an antic now (football, NFL throw, or a random one)."""
        if self.antic is not None:
            self.end_antic()
        if self.state == "held":                     # being dragged: not now
            return
        self.vx = self.vy = 0.0
        self.napping = False
        self.perch = None
        self.set_state("idle")
        self.stick_to_ground()
        self.start_antic(name)
        __import__("extras").cheer("trick")          # XP after it started (a level-up won't block it)

    def antic_allowed(self):
        return (self.antic is None and self.state in ("idle", "walk") and self.perch is None
                and not self.hidden_for_game and self.ask is None and self.chat is None
                and self.helper is None and getattr(self, "radio_panel", None) is None
                and not self.bubble.isVisible() and user_idle_seconds() < 60)

    def maybe_antic(self, now):
        import antics
        if __import__("extras").dnd_on():
            return
        debug = __import__("os").getenv("BLIP_DEBUG_ANTICS")   # hidden: every 15 s, in turn
        freq = (15, 15) if debug else antics.FREQUENCY.get(config.ANTICS)
        if freq is None or now < self.next_antic:
            return
        if self.antic_allowed():
            self.next_antic = now + random.uniform(*freq)
            name = None
            if debug:
                names = list(antics.ALL)
                self.debug_i = (getattr(self, "debug_i", -1) + 1) % len(names)
                name = names[self.debug_i]
            self.start_antic(name)

    def start_antic(self, name=None):
        import antics
        if name is None:
            names = [n for n in antics.WEIGHTS if self.state == "idle" or antics.ALL[n].walking_ok]
            name = random.choices(names, weights=[antics.WEIGHTS[n] for n in names])[0]
        cls = antics.ALL[name]
        if name == "climb":
            icons = cls.find_icons(self)              # read once, at the start only
            self.antic = cls(self, icons)
            if not self.antic.steps:                  # no visible icon ladder: something else
                self.antic = None
                if names_fallback := [n for n in antics.ALL if n != "climb"]:
                    return self.start_antic(random.choice(names_fallback))
                return
        else:
            self.antic = cls(self)
        self.napping = False
        self.set_margin(cls.margin * config.PET_SIZE / 120)
        self.last_tick = time.monotonic()
        self.set_state("antic")

    def end_antic(self):
        falls = False
        if self.antic is not None:
            falls = getattr(self.antic, "fall_at_end", False)
            self.antic.end()
            self.antic = None
        if self.margin:
            self.set_margin(0)
        if falls:                                    # e.g. jumping off the desktop icons
            self.last_tick = time.monotonic()
            self.set_state("fall")
            return
        if self.state == "antic":
            self.set_state("idle")
        self.stick_to_ground()
