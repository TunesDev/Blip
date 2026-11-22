"""
Desktop pet - small extras, all ~free when not in use:
  * Do Not Disturb        (no antics, questions or pop-ups; reminders stay quiet)
  * seasonal outfits      (Santa hat in December, pumpkin at Halloween, shamrock on Paddy's Day...)
  * focus timer           ("focus for 25 min": one single-shot timer)
  * happiness meter       (worked out from timestamps - no timer at all)
  * tiny sounds           (made in code, played with winsound; off by default)
Developed by Tunes
"""
import datetime
import math
import struct
import time

import config

# ---------------------------------------------------------------------------
# Do Not Disturb
# ---------------------------------------------------------------------------
FOREVER = 4102444800.0          # "until I turn it off" (the year 2100)


def dnd_on():
    return time.time() < config.DND_UNTIL or focus_left() > 0


def set_dnd(seconds):
    """seconds: None = off, float('inf') = until turned off, else for that long."""
    config.DND_UNTIL = 0.0 if seconds is None else (FOREVER if seconds == float("inf")
                                                    else time.time() + seconds)


# ---------------------------------------------------------------------------
# Seasonal outfits
# ---------------------------------------------------------------------------
def season(today=None):
    """(hat, effect) for special days, or (None, None)."""
    d = today or datetime.date.today()
    m, day = d.month, d.day
    try:
        import progress
        if progress.get().birthday == f"{m:02d}-{day:02d}":
            return "Party hat", "confetti"                  # it's your birthday!
    except Exception:
        pass
    if m == 12 and day <= 26:
        return "Santa hat", "snow"
    if (m == 12 and day == 31) or (m == 1 and day == 1):
        return "Party hat", "confetti"
    if m == 10 and day >= 24 or (m == 11 and day == 1):
        return "Pumpkin", None
    if m == 3 and day == 17:
        return "Shamrock", None
    if m == 2 and day == 14:
        return None, "hearts"
    return None, None


_season_cache = (None, (None, None))


def effective_hat():
    """The hat Blip wears right now (seasonal one wins, unless switched off)."""
    global _season_cache
    today = datetime.date.today()
    if _season_cache[0] != today:
        _season_cache = (today, season(today))
    hat, _ = _season_cache[1]
    if config.SEASONAL and hat:
        return hat
    return config.HAT


def season_effect():
    effective_hat()
    return _season_cache[1][1] if config.SEASONAL else None


# ---------------------------------------------------------------------------
# Focus timer
# ---------------------------------------------------------------------------
focus_end = 0.0


def focus_left():
    return max(0.0, focus_end - time.time())


# ---------------------------------------------------------------------------
# Happiness (0-100). Decays slowly with real time, worked out when it's read.
# ---------------------------------------------------------------------------
DECAY_PER_HOUR = 1.5             # gentle: a day away = about -36
FLOOR = 15                       # never drops below this (no harsh punishment)
GAINS = {"feed": 8, "poke": 1, "pet": 3, "chat": 2, "trick": 3, "reminder": 2, "game": 2,
         "focus": 4, "win": 5}


def happiness():
    if config.HAPPY_AT <= 0:                     # first run: start from now
        config.HAPPY_AT = time.time()
    hours = max(0.0, (time.time() - config.HAPPY_AT) / 3600)
    return max(FLOOR, min(100.0, config.HAPPY - hours * DECAY_PER_HOUR))


_gained_today = {}


XP_FOR = {"feed": "feed", "poke": "poke", "pet": "pet", "chat": "chat", "trick": "trick",
          "reminder": "task", "game": "game", "focus": "focus", "win": "seek"}
on_xp = None                     # set by the pet window: shows level-up celebrations


def cheer(kind):
    """Something nice happened. Pokes etc. are capped per day so it can't be spammed."""
    try:
        import progress
        events = progress.get().award(XP_FOR.get(kind, kind))
        if events and on_xp:
            on_xp(events)
    except Exception as e:
        print("XP:", e)
    today = datetime.date.today().isoformat()
    key = (today, kind)
    _gained_today[key] = _gained_today.get(key, 0) + 1
    if _gained_today[key] > {"poke": 10, "chat": 15}.get(kind, 30):
        return
    config.HAPPY = min(100.0, happiness() + GAINS.get(kind, 1))
    config.HAPPY_AT = time.time()
    try:
        import settings
        settings.save()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Tiny sounds, synthesised in code (no files, no audio library in Blip itself)
# ---------------------------------------------------------------------------
_sounds = {}
RATE = 22050


def _wav(samples):
    data = struct.pack(f"<{len(samples)}h", *samples)
    return (b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " +
            struct.pack("<IHHIIHH", 16, 1, 1, RATE, RATE * 2, 2, 16) +
            b"data" + struct.pack("<I", len(data)) + data)


def _tone(parts, volume):
    """parts: [(start Hz, end Hz, seconds)] glued together, with a soft envelope."""
    out = []
    for f0, f1, dur in parts:
        n = int(RATE * dur)
        phase = 0.0
        for i in range(n):
            u = i / n
            f = f0 + (f1 - f0) * u
            phase += 2 * math.pi * f / RATE
            env = min(1.0, u * 12) * (1 - u) ** 1.5
            out.append(int(32767 * volume * env * math.sin(phase)))
    return _wav(out)


def _noise(dur, volume):
    import random
    n = int(RATE * dur)
    return _wav([int(32767 * volume * (1 - i / n) ** 2 * random.uniform(-1, 1)) for i in range(n)])


SOUND_SHAPES = {
    "boop": [(660, 880, 0.07)],
    "giggle": [(900, 1200, 0.05), (950, 1300, 0.05), (1000, 1400, 0.06)],
    "yay": [(523, 523, 0.09), (659, 659, 0.09), (784, 1046, 0.18)],
    "chime": [(1046, 1046, 0.18), (1318, 1318, 0.3)],
}


def play(name):
    """Plays a tiny sound if sounds are switched on. Made the first time it's needed."""
    if config.SOUNDS == "Off":
        return
    try:
        import winsound
        from settings import DATA_DIR
        vol = 0.12 if config.SOUNDS == "Low" else 0.3
        key = (name, vol)
        if key not in _sounds:              # winsound can't play from memory in the background,
            folder = DATA_DIR / "sounds"     # so each sound is written once as a tiny .wav file
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / f"{name}_{config.SOUNDS.lower()}.wav"
            path.write_bytes(_noise(0.25, vol) if name == "sneeze" else _tone(SOUND_SHAPES[name], vol))
            _sounds[key] = str(path)
        winsound.PlaySound(_sounds[key], winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
    except Exception:
        pass
