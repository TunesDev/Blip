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
import random
import time

import config
from settings import DATA_DIR

FILE = DATA_DIR / "progress.json"
MAX_LEVEL = 55
MAX_PRESTIGE = 10

# Daily quests: (id, text, XP source that counts, how many, bonus XP)
QUESTS = [
    ("feed2", "Feed Blip twice", "feed", 2, 120),
    ("pet1", "Pet Blip", "pet", 1, 80),
    ("seek1", "Win hide and seek", "seek", 1, 150),
    ("focus1", "Finish a focus session", "focus", 1, 150),
    ("throw1", "Throw Blip across the screen", "throw", 1, 100),
    ("catch1", "Catch Blip in mid-air", "catch", 1, 120),
    ("chat3", "Chat with Blip 3 times", "chat", 3, 100),
    ("trick2", "Ask Blip for 2 tricks", "trick", 2, 100),
    ("music2", "Listen to music with Blip for 30 min", "music", 2, 120),
    ("task1", "Finish a reminder or to-do", "task", 1, 100),
    ("jump3", "Make Blip jump 3 times", "jump", 3, 80),
    ("app1", "Open an app through Blip", "launch", 1, 80),
]
WEEKLY_GOAL = 12                 # daily quests in a week -> weekly challenge done
WEEKLY_XP, WEEKLY_TOKENS = 600, 1

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
        self.stats = d.get("stats", {})                     # counters for achievements
        self.achievements = d.get("achievements", [])
        self.tokens = int(d.get("tokens", 0))              # Prestige Shop currency
        self.levels_gained = int(d.get("levels_gained", 0))
        self.owned = list(d.get("owned", []))
        self.equipped = dict(d.get("equipped", {}))         # slot -> item (glasses, extra, trail, tag)
        self.quests = d.get("quests", {})                   # {"day":..., "list":[[id, count, done]]}
        self.weekly = d.get("weekly", {})                   # {"week":..., "count":n, "done":bool}
        self.active_secs = 0

    # ---- saving --------------------------------------------------------------------------
    def save(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        d = {k: getattr(self, k) for k in ("level", "xp", "prestige", "total", "daily", "streak",
                                           "last_day", "skin", "aura", "birthday", "tokens",
                                           "levels_gained", "owned", "equipped", "quests", "weekly",
                                           "stats", "achievements")}
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
        events = self.quest_step(source)                  # quests count even past the XP cap
        import care
        if source != "snackgame":                         # (the mini-game counts snacks itself)
            events += care.bump(self, source)             # achievements count every time
        used = self.daily.get(source, 0)
        if used >= cap or gain <= 0:
            if events:
                self.save()
            return events
        self.daily[source] = used + 1
        return events + self._add(gain)

    def _add(self, gain):
        events = [("xp", gain)]
        self.total += gain
        self.daily["xp"] = self.daily.get("xp", 0) + gain
        if self.level >= MAX_LEVEL:                       # waiting to prestige / Master
            self.save()
            return events
        self.xp += gain
        while self.level < MAX_LEVEL and self.xp >= xp_for_level(self.level):
            self.xp -= xp_for_level(self.level)
            self.level += 1
            self.levels_gained += 1
            import care
            events += care.bump(self, "level", value=self.level)
            events.append(("level", self.level))
            if self.levels_gained % 10 == 0:              # a token every 10 levels
                self.tokens += 1
                events.append(("token", 1))
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
        import care
        return self.award("daily", config.XP_SOURCES["daily"][0] + bonus) + \
            care.bump(self, "streak", value=self.streak)

    def active_tick(self, seconds):
        """Called every few seconds while you're at the PC."""
        self.active_secs += seconds
        self.daily["active_secs"] = self.daily.get("active_secs", 0) + seconds
        if self.active_secs >= 600:
            self.active_secs -= 600
            return self.award("active")
        return []

    def do_prestige(self):
        if not self.can_prestige:
            return False
        self.prestige += 1
        self.tokens += 3
        import care
        care.bump(self, "prestige", value=self.prestige)
        self.level, self.xp = 1, 0
        self.save()
        return True


    # ---- daily quests + weekly challenge -----------------------------------------------------
    def today_quests(self):
        today = datetime.date.today().isoformat()
        if self.quests.get("day") != today:
            picks = random.Random(today).sample(QUESTS, 3)
            self.quests = {"day": today, "list": [[q[0], 0, False] for q in picks]}
        return [(dict((q[0], q) for q in QUESTS)[qid], count, done) for qid, count, done in self.quests["list"]]

    def quest_step(self, source):
        events = []
        self.today_quests()
        for entry in self.quests["list"]:
            q = dict((x[0], x) for x in QUESTS)[entry[0]]
            if entry[2] or q[2] != source:
                continue
            entry[1] += 1
            if entry[1] >= q[3]:
                entry[2] = True
                import care
                events += care.bump(self, "quest")
                events.append(("quest", q[1], q[4]))
                events += self._add(q[4])
                events += self.weekly_step()
        return events

    def weekly_step(self):
        y, w, _ = datetime.date.today().isocalendar()
        key = f"{y}-W{w}"
        if self.weekly.get("week") != key:
            self.weekly = {"week": key, "count": 0, "done": False}
        self.weekly["count"] += 1
        if not self.weekly["done"] and self.weekly["count"] >= WEEKLY_GOAL:
            self.weekly["done"] = True
            self.tokens += WEEKLY_TOKENS
            return [("weekly", WEEKLY_XP)] + self._add(WEEKLY_XP)
        return []

    def week_progress(self):
        y, w, _ = datetime.date.today().isocalendar()
        if self.weekly.get("week") != f"{y}-W{w}":
            return 0, False
        return self.weekly.get("count", 0), self.weekly.get("done", False)

    # ---- shop ------------------------------------------------------------------------------
    def buy(self, item):
        import shop
        slot, price, need = shop.ITEMS[item]
        if item in self.owned or self.tokens < price or self.prestige < need:
            return False
        self.tokens -= price
        self.owned.append(item)
        self.save()
        return True


_progress = None


def get():
    global _progress
    if _progress is None:
        _progress = Progress()
    return _progress
