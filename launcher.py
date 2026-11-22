"""
Desktop pet - opens your apps from the chat ("I'm going to play Call of Duty").
Blip can ONLY open apps listed in %APPDATA%\\Blip\\apps.json (right-click > Edit app list…).
The AI never decides what gets run: a simple keyword match against that list does.
Developed by Tunes
"""
import json
import os
import re
import subprocess
from pathlib import Path

from settings import DATA_DIR

APPS_FILE = DATA_DIR / "apps.json"
START_MENUS = [Path(os.getenv("ProgramData", r"C:\ProgramData")) / r"Microsoft\Windows\Start Menu\Programs",
               Path(os.getenv("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs"]

# Start menu shortcut name -> (name Blip uses, keywords, what Blip says)
KNOWN = [
    ("Call of Duty", "Call of Duty", ["call of duty", "cod", "warzone", "black ops", "modern warfare"],
     "Good luck out there, soldier! 🎮"),
    ("Visual Studio Code", "VS Code", ["coding", "code", "vs code", "vscode", "programming", "python"],
     "Happy coding! Don't forget to save 💻"),
    ("Visual Studio", "Visual Studio", ["visual studio"], "Time to build something cool! 💻"),
    ("Steam", "Steam", ["steam", "gaming", "games", "a game"], "Game time! 🎮"),
    ("Discord", "Discord", ["discord", "call my friends", "chat with my friends"], "Say hi to your friends for me! 👋"),
    ("Roblox Studio", "Roblox Studio", ["roblox studio"], "Build something awesome! 🧱"),
    ("Roblox Player", "Roblox", ["roblox"], "Have fun in Roblox! 🧱"),
    ("Spotify", "Spotify", ["spotify"], "Music time! 🎧"),
    ("Brave", "Brave", ["brave", "browser", "internet", "the web", "youtube"], "Opening the internet! 🌐"),
    ("Google Chrome", "Chrome", ["chrome"], "Opening Chrome! 🌐"),
    ("Firefox", "Firefox", ["firefox"], "Opening Firefox! 🦊"),
]
INTENT = re.compile(r"\b(open|launch|start|play|playing|run|load|going to|gonna|wanna|want to|"
                    r"about to|time to|time for|let'?s|fire up|boot up|put on)\b", re.I)


def _find_shortcut(name):
    for base in START_MENUS:
        for ext in (".lnk", ".url"):
            hits = sorted(base.rglob(name + ext), key=lambda p: len(str(p)))
            if hits:
                return str(hits[0])
    return None


def detect_apps():
    """Build the starting app list from what's installed on this PC."""
    apps = []
    for shortcut, name, keywords, say in KNOWN:
        target = _find_shortcut(shortcut)
        if target:
            apps.append({"name": name, "keywords": keywords, "target": target, "args": [], "say": say})
    return apps


def load_apps():
    try:
        return json.loads(APPS_FILE.read_text(encoding="utf-8"))["apps"]
    except (OSError, ValueError, KeyError):
        apps = detect_apps()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        APPS_FILE.write_text(json.dumps({
            "_help": "Apps Blip may open from the chat. 'keywords' are words in your message; "
                     "'target' is the .exe or shortcut; 'args' are optional extra arguments.",
            "apps": apps}, indent=2, ensure_ascii=False), encoding="utf-8")
        return apps


def match(text):
    """The app your message asks for (longest keyword wins), or None."""
    low = " " + text.lower() + " "
    if not INTENT.search(low):
        return None
    best, best_len = None, 0
    for app in load_apps():
        for kw in app.get("keywords", []) + [app.get("name", "")]:
            kw = kw.lower().strip()
            if kw and re.search(r"(?<![a-z0-9])" + re.escape(kw) + r"(?![a-z0-9])", low) \
                    and len(kw) > best_len:
                best, best_len = app, len(kw)
    return best


def launch(app):
    target = app["target"]
    args = app.get("args") or []
    if args:
        subprocess.Popen([target, *args], cwd=app.get("cwd") or None,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    else:
        os.startfile(target)


def edit_list():
    load_apps()                                  # make sure the file exists
    subprocess.Popen(["notepad.exe", str(APPS_FILE)])
