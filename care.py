"""
Desktop pet - PC care, achievements, nudges and little helpers (v1.2).
Everything here is checked from Blip's existing 6-second check, at most every few
minutes, and always ASKS before doing anything to your PC.
  * low disk space alert          * startup apps check (weekly)
  * game boost (and restore)      * "restart helps" nudge after 7 days on
  * weekly tidy-up report         * daily summary
  * achievements + trophy shelf   * hourly wellbeing nudges ("Fancy a cup of tea?")
  * clipboard helper: copied colour codes and simple sums
Developed by Tunes
"""
import ast
import datetime
import json
import operator
import os
import random
import re
import shutil
import time
import winreg

import config
from settings import DATA_DIR

STARTUP_BACKUP = DATA_DIR / "startup_backup.json"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

# ---------------------------------------------------------------------------
# Achievements: (id, name, description, counter, target, bonus XP)
# ---------------------------------------------------------------------------
ACHIEVEMENTS = [
    ("throw10", "Frequent flyer", "Throw Blip 10 times", "throw", 10, 100),
    ("throw100", "Air Blip", "Throw Blip 100 times", "throw", 100, 400),
    ("catch10", "Safe hands", "Catch Blip in mid-air 10 times", "catch", 10, 150),
    ("feed25", "Snack master", "Feed Blip 25 times", "feed", 25, 200),
    ("pet20", "Best friends", "Pet Blip 20 times", "pet", 20, 200),
    ("seek5", "Eagle eyes", "Win hide and seek 5 times", "seek", 5, 200),
    ("focus10", "Deep focus", "Finish 10 focus sessions", "focus", 10, 300),
    ("chat50", "Chatterbox", "Chat with Blip 50 times", "chat", 50, 200),
    ("quest20", "Quest hunter", "Complete 20 daily quests", "quest", 20, 300),
    ("streak7", "One week together", "7-day streak", "streak", 7, 300),
    ("streak30", "Inseparable", "30-day streak", "streak", 30, 1000),
    ("level25", "Halfway there", "Reach level 25", "level", 25, 0),
    ("prestige1", "Prestige!", "Prestige for the first time", "prestige", 1, 0),
    ("snack50", "Snack catcher", "Catch 50 snacks in the mini-game", "snackgame", 50, 250),
    ("nudge20", "Healthy habits", "Follow 20 wellbeing nudges", "nudge", 20, 250),
    ("tidy5", "Neat freak", "Clean up your PC 5 times", "tidy", 5, 200),
]


def bump(prog, counter, amount=1, value=None):
    """Count something; returns [("achievement", name, desc, bonus)] for new unlocks."""
    stats = prog.__dict__.setdefault("stats", {})
    if value is not None:
        stats[counter] = max(stats.get(counter, 0), value)
    else:
        stats[counter] = stats.get(counter, 0) + amount
    got = prog.__dict__.setdefault("achievements", [])
    new = []
    for aid, name, desc, c, target, bonus in ACHIEVEMENTS:
        if c == counter and aid not in got and stats.get(c, 0) >= target:
            got.append(aid)
            new.append(("achievement", name, desc, bonus))
            if bonus and counter not in ("level",):
                new += prog._add(bonus)
    return new


# ---------------------------------------------------------------------------
# Wellbeing nudges (about once an hour of active use)
# ---------------------------------------------------------------------------
NUDGES = [
    "Fancy a cup of tea?", "Time for a glass of water?", "Stretch your legs for a minute?",
    "20-20-20: look at something 20 feet away for 20 seconds.", "Check your posture! Sit up tall.",
    "Take three deep breaths with me.", "Snack break? Something healthy maybe!",
    "Roll your shoulders a few times.", "Blink a few times, your eyes will thank you.",
    "Open a window for some fresh air?", "Message a friend you haven't talked to in a while?",
    "Stand up and walk around for a minute?",
]


def pick_nudge():
    return random.choice(NUDGES)


# ---------------------------------------------------------------------------
# Disk, uptime, startup apps
# ---------------------------------------------------------------------------
def disk_full_percent(drive=None):
    drive = drive or os.getenv("SystemDrive", "C:") + "\\"
    try:
        u = shutil.disk_usage(drive)
        return 100.0 * u.used / u.total, u.free / 1073741824
    except OSError:
        return 0.0, 0.0


def uptime_days():
    try:
        import ctypes
        k = ctypes.WinDLL("kernel32")
        k.GetTickCount64.restype = ctypes.c_ulonglong
        return k.GetTickCount64() / 86400000
    except Exception:
        return 0.0


def startup_apps():
    """[(name, command, where, can_disable)] for apps that start with Windows."""
    apps = []
    for root, label, editable in ((winreg.HKEY_CURRENT_USER, "You", True),
                                  (winreg.HKEY_LOCAL_MACHINE, "All users (needs admin)", False)):
        try:
            with winreg.OpenKey(root, RUN_KEY) as k:
                i = 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(k, i)
                    except OSError:
                        break
                    apps.append((name, str(value), label, editable and name != "Blip"))
                    i += 1
        except OSError:
            pass
    folder = os.path.join(os.getenv("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")
    if os.path.isdir(folder):
        for f in os.listdir(folder):
            if f.lower().endswith((".lnk", ".url", ".exe", ".bat")):
                apps.append((os.path.splitext(f)[0], os.path.join(folder, f), "Startup folder", True))
    return apps


def disable_startup(entries):
    """Turn off the chosen start-up apps. A backup is kept so they can be turned back on."""
    try:
        backup = json.loads(STARTUP_BACKUP.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        backup = []
    for name, value, where, _ in entries:
        if where == "You":
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
                winreg.DeleteValue(k, name)
            backup.append({"type": "run", "name": name, "value": value})
        elif where == "Startup folder" and os.path.exists(value):
            dst = DATA_DIR / "startup_disabled"
            dst.mkdir(parents=True, exist_ok=True)
            shutil.move(value, dst / os.path.basename(value))
            backup.append({"type": "file", "name": name, "from": value, "to": str(dst / os.path.basename(value))})
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STARTUP_BACKUP.write_text(json.dumps(backup, indent=2), encoding="utf-8")


def restore_startup():
    """Turn every app Blip switched off back on."""
    try:
        backup = json.loads(STARTUP_BACKUP.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    for b in backup:
        try:
            if b["type"] == "run":
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
                    winreg.SetValueEx(k, b["name"], 0, winreg.REG_SZ, b["value"])
            elif os.path.exists(b["to"]):
                shutil.move(b["to"], b["from"])
        except OSError:
            pass
    STARTUP_BACKUP.unlink(missing_ok=True)
    return len(backup)


# ---------------------------------------------------------------------------
# Clipboard helper
# ---------------------------------------------------------------------------
HEX = re.compile(r"^\s*#?([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\s*$")
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.Mod: operator.mod, ast.FloorDiv: operator.floordiv, ast.USub: operator.neg}


def _calc(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        if isinstance(node.op, ast.Pow) and abs(_calc(node.right)) > 100:
            raise ValueError("too big")
        return _OPS[type(node.op)](_calc(node.left), _calc(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_calc(node.operand))
    raise ValueError("not maths")


def clipboard_info(text):
    """Returns (title, text) for a copied colour or sum, else None. Nothing leaves your PC."""
    t = (text or "").strip()
    if not t or len(t) > 60:
        return None
    m = HEX.match(t)
    if m and (t.startswith("#") or re.search(r"[a-fA-F]", t)):
        h = m.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return "Colour", f"#{h.upper()}  =  rgb({r}, {g}, {b})", (r, g, b)
    if re.fullmatch(r"[\d\s.+\-*/%()^x×÷]+", t) and re.search(r"\d\s*[-+*/x×÷^%]\s*\d", t):
        expr = t.replace("x", "*").replace("×", "*").replace("÷", "/").replace("^", "**")
        try:
            v = _calc(ast.parse(expr, mode="eval").body)
            v = round(v, 6) if isinstance(v, float) else v
            return "Maths", f"{t} = {v:,}" if isinstance(v, int) else f"{t} = {v}", None
        except Exception:
            return None
    return None
