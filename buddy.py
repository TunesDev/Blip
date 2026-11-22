"""
Desktop pet - making the chat useful (all light: no AI needed, no extra timers):
  * reminders + to-do list   ("remind me in 20 min to check the pizza", "add milk to my list")
  * Blip asks you a question now and then (max 3 a day, never at night or while gaming)
  * game buddy: after a game, "How did the match go?" -> wins / losses / streak
Files: %APPDATA%\\Blip\\tasks.json, questions.json, games.json
Developed by Tunes
"""
import datetime
import json
import random
import re
import time

from settings import DATA_DIR

TASKS = DATA_DIR / "tasks.json"
QUESTIONS = DATA_DIR / "questions.json"
GAMES = DATA_DIR / "games.json"


def _load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _save(path, data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Reminders + to-do list
# ---------------------------------------------------------------------------
def load_tasks():
    data = _load(TASKS, {})
    return {"reminders": data.get("reminders", []), "todo": data.get("todo", [])}


def save_tasks(data):
    _save(TASKS, data)


UNIT = r"(seconds?|secs?|minutes?|mins?|m|hours?|hrs?|h)"
SECONDS = {"s": 1, "m": 60, "h": 3600}


def _unit_seconds(unit):
    u = unit.lower()
    return SECONDS["h"] if u.startswith("h") else SECONDS["s"] if u.startswith("s") else SECONDS["m"]


def _clock(hour, minute, ampm):
    h, m = int(hour), int(minute or 0)
    if ampm:
        h = h % 12 + (12 if ampm.lower() == "pm" else 0)
    now = datetime.datetime.now()
    due = now.replace(hour=h % 24, minute=m, second=0, microsecond=0)
    if due <= now:
        due += datetime.timedelta(days=1)
    return due.timestamp()


def _clean(task):
    task = re.sub(r"^(to|that|about)\s+", "", task.strip(), flags=re.I)
    return task.strip(" .!?") or "this"


def _when(ts):
    d = datetime.datetime.fromtimestamp(ts)
    day = "" if d.date() == datetime.date.today() else " tomorrow"
    return d.strftime("%H:%M") + day


def add_reminder(text, due):
    data = load_tasks()
    data["reminders"].append({"id": int(time.time() * 1000), "text": text, "due": due})
    save_tasks(data)


def handle_tasks(msg):
    """Reminder / to-do commands. Returns Blip's reply, or None if it's not one."""
    m = msg.strip()
    r = re.search(rf"remind me (?:in )?(\d+)\s*{UNIT}\b\s*(.*)", m, re.I)
    if r:
        due = time.time() + int(r.group(1)) * _unit_seconds(r.group(2))
        task = _clean(r.group(3))
        add_reminder(task, due)
        return f"Got it! ⏰ I'll remind you to {task} at {_when(due)}."
    r = re.search(rf"remind me (?:to )?(.+?) in (\d+)\s*{UNIT}\b", m, re.I)
    if r:
        due = time.time() + int(r.group(2)) * _unit_seconds(r.group(3))
        task = _clean(r.group(1))
        add_reminder(task, due)
        return f"Got it! ⏰ I'll remind you to {task} at {_when(due)}."
    r = re.search(r"remind me at (\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*(.*)", m, re.I)
    if r:
        due = _clock(r.group(1), r.group(2), r.group(3))
        task = _clean(r.group(4))
        add_reminder(task, due)
        return f"Got it! ⏰ I'll remind you to {task} at {_when(due)}."
    r = re.search(r"remind me (?:to )?(.+?) at (\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", m, re.I)
    if r:
        due = _clock(r.group(2), r.group(3), r.group(4))
        task = _clean(r.group(1))
        add_reminder(task, due)
        return f"Got it! ⏰ I'll remind you to {task} at {_when(due)}."

    data = load_tasks()
    r = re.search(r"add (.+?) to (?:my )?(?:to-?do )?list", m, re.I)
    if r:
        item = r.group(1).strip(" .!")
        data["todo"].append(item)
        save_tasks(data)
        return f"Added \"{item}\" to your list 📝 ({len(data['todo'])} things on it)."
    if re.search(r"clear (?:my )?(?:to-?do )?list", m, re.I):
        data["todo"] = []
        save_tasks(data)
        return "List cleared! ✨ Fresh start."
    r = re.search(r"(?:i'?m |i am )?(?:done with|finished|tick off|cross off|remove) (.+?)"
                  r"(?: from (?:my )?(?:to-?do )?list)?[.!]*$", m, re.I)
    if r and data["todo"]:
        want = r.group(1).lower().strip()
        hit = next((t for t in data["todo"] if want in t.lower() or t.lower() in want), None)
        if hit:
            data["todo"].remove(hit)
            save_tasks(data)
            left = len(data["todo"])
            return f"Nice one! ✅ Ticked off \"{hit}\". " + (f"{left} left." if left else "List's empty! 🎉")
    if re.search(r"(what'?s|what is|show) (?:on )?my (?:to-?do )?list|my to-?do", m, re.I):
        if not data["todo"]:
            return "Your list is empty! 🎉 Say \"add ... to my list\" to add something."
        return "Your list 📝\n" + "\n".join(f"• {t}" for t in data["todo"])
    if re.search(r"(what are |show )?my reminders", m, re.I):
        rem = sorted(data["reminders"], key=lambda x: x["due"])
        if not rem:
            return "No reminders right now ⏰"
        return "Your reminders ⏰\n" + "\n".join(f"• {x['text']} at {_when(x['due'])}" for x in rem)
    return None


def due_reminders():
    now = time.time()
    return [r for r in load_tasks()["reminders"] if r["due"] <= now]


def next_due():
    rem = load_tasks()["reminders"]
    return min((r["due"] for r in rem), default=None)


def finish_reminder(rid, snooze_seconds=0):
    data = load_tasks()
    for r in data["reminders"]:
        if r["id"] == rid:
            if snooze_seconds:
                r["due"] = time.time() + snooze_seconds
            else:
                data["reminders"].remove(r)
            break
    save_tasks(data)


# ---------------------------------------------------------------------------
# Blip asks you questions
# ---------------------------------------------------------------------------
QUESTION_LIST = [
    "How's your day going? 😊",
    "Have you drunk some water lately? 💧",
    "What are you working on right now?",
    "What's your favourite song at the moment? 🎵",
    "Done anything fun today?",
    "What game are you playing most this week? 🎮",
    "What's something you're looking forward to?",
    "If you could have any snack right now, what would it be? 🍕",
    "Learned anything cool today?",
    "How are you feeling right now?",
]
MAX_PER_DAY = 3
MIN_GAP = 2 * 3600


def question_due(hour):
    """True if Blip may ask a question now (limits are checked here)."""
    if not 9 <= hour < 23:
        return False
    st = _load(QUESTIONS, {})
    today = datetime.date.today().isoformat()
    count = st.get("count", 0) if st.get("day") == today else 0
    return count < MAX_PER_DAY and time.time() - st.get("last", 0) >= MIN_GAP


def pick_question():
    st = _load(QUESTIONS, {})
    today = datetime.date.today().isoformat()
    recent = st.get("recent", [])
    q = random.choice([q for q in QUESTION_LIST if q not in recent] or QUESTION_LIST)
    _save(QUESTIONS, {"day": today,
                      "count": (st.get("count", 0) if st.get("day") == today else 0) + 1,
                      "last": time.time(), "recent": (recent + [q])[-6:]})
    return q


# ---------------------------------------------------------------------------
# Game buddy
# ---------------------------------------------------------------------------
GAME_TITLES = ["call of duty", "warzone", "black ops", "modern warfare", "fortnite", "valorant",
               "rocket league", "counter-strike", "apex legends", "overwatch", "rainbow six",
               "league of legends", "ea sports fc", "fifa"]
MIN_PLAY = 10 * 60
CHEERS = ["LET'S GOOO! 🏆 You're on fire!", "GG! Another W for the collection 🏆",
          "Winner winner! 🍗 I knew you had it!", "Too easy for you 😎🏆"]
ROASTS = ["Oof 💀 Lag, right? Definitely the lag.", "Unlucky! 💀 The enemy team must've been hacking.",
          "Hey, even pros lose sometimes 💀 ...a lot.", "💀 Shake it off, next one's yours!"]


def game_title(titles):
    """The running game's name if a known game window is open, else None."""
    for t in titles:
        low = t.lower()
        for g in GAME_TITLES:
            if g in low:
                return t.strip() or g.title()
    return None


def load_games():
    d = _load(GAMES, {})
    return {"wins": d.get("wins", 0), "losses": d.get("losses", 0), "streak": d.get("streak", 0),
            "best": d.get("best", 0), "history": d.get("history", [])}


def record_match(won, game):
    g = load_games()
    if won:
        g["wins"] += 1
        g["streak"] = g["streak"] + 1 if g["streak"] > 0 else 1
        g["best"] = max(g["best"], g["streak"])
    else:
        g["losses"] += 1
        g["streak"] = g["streak"] - 1 if g["streak"] < 0 else -1
    g["history"] = (g["history"] + [{"game": game, "won": won, "at": int(time.time())}])[-30:]
    _save(GAMES, g)
    line = random.choice(CHEERS if won else ROASTS)
    if g["streak"] >= 3:
        line += f" {g['streak']} wins in a row!"
    elif g["streak"] <= -3:
        line += f" ({-g['streak']} losses in a row... take a break? 🥤)"
    return line


def stats_reply(msg):
    if not re.search(r"how am i doing|my (game )?stats|my record|win ?rate|k/?d", msg, re.I):
        return None
    g = load_games()
    total = g["wins"] + g["losses"]
    if not total:
        return "No matches logged yet! 🎮 After a game I'll ask you how it went."
    rate = 100 * g["wins"] / total
    streak = (f"{g['streak']}-win streak 🔥" if g["streak"] > 0 else
              f"{-g['streak']} losses in a row 💀" if g["streak"] < 0 else "no streak")
    return (f"Your record 🎮: {g['wins']} wins, {g['losses']} losses ({rate:.0f}% win rate). "
            f"Right now: {streak}. Best streak: {g['best']}.")


def handle_chat(msg):
    """Everything Blip can answer by itself (no AI needed)."""
    return handle_tasks(msg) or stats_reply(msg)
