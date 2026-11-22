"""
Desktop pet - saves your settings to a small JSON file and loads them on start.
File lives in %APPDATA%\\Blip\\settings.json (keeps working after we make the .exe).
Developed by Tunes
"""
import json
import os
from pathlib import Path

import config

# Settings that the Settings window can change.
SAVED_KEYS = ["CHARACTER", "THEME", "HAT", "EYES_FOLLOW_CURSOR", "PET_SIZE",
              "WALK_SPEED", "BOUNCE", "USER_IDLE_SLEEP_SECONDS", "HIDE_IN_FULLSCREEN",
              "SIT_ON_WINDOWS", "SWEAT_WHEN_BUSY", "SLEEPY_AT_NIGHT",
              "LISTEN_TO_MUSIC", "PC_HELPER",
              "ASK_QUESTIONS", "GAME_BUDDY",
              "RADIO_STATION", "RADIO_VOLUME",
              "ANTICS", "DANCE",
              "DND_UNTIL", "SEASONAL", "HAPPY", "HAPPY_AT", "SOUNDS",
              "AUTO_UPDATE", "UPDATE_LAST", "FIRST_RUN_DONE", "LAST_VERSION",
              "PC_CARE", "NUDGES", "NUDGE_MINUTES", "CLIPBOARD_HELPER", "DAILY_SUMMARY",
              "TIME_PROPS", "BOOST_APPS", "CARE_STATE", "NIGHT_LIGHT_MODE", "NIGHT_LIGHT_FROM",
              "NIGHT_LIGHT_TO", "NIGHT_LIGHT_WARMTH", "NIGHT_LIGHT_OFF_IN_GAMES", "NIGHT_LIGHT_ACTIVE"]

DATA_DIR = Path(os.getenv("APPDATA", Path.home())) / "Blip"
SETTINGS_FILE = DATA_DIR / "settings.json"


def load():
    """Copy saved values over the defaults in config.py."""
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    for key in SAVED_KEYS:
        if key in data and type(data[key]) in (type(getattr(config, key)), int, float):
            setattr(config, key, data[key])


def save():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data = {key: getattr(config, key) for key in SAVED_KEYS}
    SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
