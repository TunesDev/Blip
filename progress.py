"""
Desktop pet - levels and prestige (like a shooter's prestige system, but for a pet).
Levels 1-55. At 55 you may Prestige: back to level 1, Prestige +1 (up to 10).
After Prestige 10 + level 55 Blip is a "Master" and keeps counting XP for fun.
Every XP source has a daily cap so it can't be farmed. One prestige takes about
4-6 weeks of normal daily use (about 1,000 XP a day; see the numbers in config.py).
Saved in %APPDATA%\\Blip\\progress.json (written atomically).
Developed by Tunes
"""
import datetime
import json
import os
import time

import config
from settings import DATA_DIR

FILE = DATA_DIR / "progress.json"
MAX_LEVEL = 55
MAX_PRESTIGE = 10

# Hats you unlock to wear any time of year (the seasonal ones still come by themselves).
HAT_UNLOCKS = {3: "Party hat", 7: "Shamrock", 13: "Pumpkin"}


def xp_for_level(level):
    """XP needed to go from `level` to `level + 1`."""
    return int(config.XP_BASE + config.XP_GROWTH * level)


def xp_per_prestige():
    return sum(xp_for_level(l) for l in range(1, MAX_LEVEL))


class Progress:
    def __init__(self):
        try:
            d = json.loads(FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            d = {}
        self.level = int(d.get("level", 1))
        self.xp = int(d.get("xp", 0))                    # towards the next level
        self.prestige = int(d.get("prestige", 0))
        self.total = int(d.get("total", 0))
        self.daily = d.get("daily", {})
        self.streak = int(d.get("streak", 0))
        self.last_day = d.get("last_day", "")
        self.skin = d.get("skin", "None")
        self.aura = bool(d.get("aura", True))
        self.birthday = d.get("birthday", "")             # "MM-DD"
        self.active_secs = 0

    # ---- saving --------------------------------------------------------------------------
    def save(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        d = {k: getattr(self, k) for k in ("level", "xp", "prestige", "total", "daily", "streak",
                                           "last_day", "skin", "aura", "birthday")}
        tmp = FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(d, indent=2), encoding="utf-8")
        os.replace(tmp, FILE)

    # ---- state ---------------------------------------------------------------------------
    @property
    def master(self):
        return self.prestige >= MAX_PRESTIGE and self.level >= MAX_LEVEL

    @property
    def can_prestige(self):
        return self.level >= MAX_LEVEL and self.prestige < MAX_PRESTIGE

    def title(self):
        if self.master:
            return f"Master · {self.total:,} XP"
        return f"Level {self.level}" + (f" · Prestige {self.prestige}" if self.prestige else "")

    def badge(self):
        return "Master" if self.master else (f"P{self.prestige}" if self.prestige else "")

    def unlocked_hats(self):
        if os.getenv("BLIP_UNLOCK_ALL") or self.prestige:
            return list(HAT_UNLOCKS.values())
        return [h for lvl, h in HAT_UNLOCKS.items() if self.level >= lvl]

    # ---- XP --------------------------------------------------------------------------------
    def award(self, source, amount=None):
        """Adds XP if today's cap for this source isn't reached. Returns a list of events:
        ("level", n), ("prestige_ready",), or [] if nothing special happened."""
        today = datetime.date.today().isoformat()
        if self.daily.get("day") != today:
            self.daily = {"day": today}
        gain, cap = config.XP_SOURCES.get(source, (0, 0))
        if amount is not None:
            gain = amount
        used = self.daily.get(source, 0)
        if used >= cap or gain <= 0:
            return []
        self.daily[source] = used + 1
        return self._add(gain)

    def _add(self, gain):
        events = []
        self.total += gain
        if self.level >= MAX_LEVEL:                       # waiting to prestige / Master
            self.save()
            return events
        self.xp += gain
        while self.level < MAX_LEVEL and self.xp >= xp_for_level(self.level):
            self.xp -= xp_for_level(self.level)
            self.level += 1
            events.append(("level", self.level))
            if self.level >= MAX_LEVEL:
                self.xp = 0
                if self.prestige < MAX_PRESTIGE:
                    events.append(("prestige_ready",))
        self.save()
        return events

    def daily_hello(self):
        """First time Blip sees you today: XP + streak bonus."""
        today = datetime.date.today()
        if self.last_day == today.isoformat():
            return []
        yesterday = (today - datetime.timedelta(days=1)).isoformat()
        self.streak = self.streak + 1 if self.last_day == yesterday else 1
        self.last_day = today.isoformat()
        bonus = min(config.XP_STREAK_MAX, config.XP_STREAK_BONUS * (self.streak - 1))
        return self.award("daily", config.XP_SOURCES["daily"][0] + bonus)

    def active_tick(self, seconds):
        """Called every few seconds while you're at the PC."""
        self.active_secs += seconds
        if self.active_secs >= 600:
            self.active_secs -= 600
            return self.award("active")
        return []

    def do_prestige(self):
        if not self.can_prestige:
            return False
        self.prestige += 1
        self.level, self.xp = 1, 0
        self.save()
        return True


_progress = None


def get():
    global _progress
    if _progress is None:
        _progress = Progress()
    return _progress
