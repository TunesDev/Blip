"""
Desktop pet - updates. Once a day (if switched on) Blip asks GitHub, in the background,
whether there's a newer release. That's the only internet call Blip makes by itself.
If there is one, Blip asks you first. On "Update" it downloads the installer and its .sha256
file, checks the SHA-256, and runs the installer silently. Your settings, memory and
progress in %APPDATA%\\Blip are never touched by an update.
Developed by Tunes
"""
import datetime
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import urllib.request
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

import config

HEADERS = {"User-Agent": "Blip-updater", "Accept": "application/vnd.github+json"}


def api_url():
    # BLIP_UPDATE_URL lets us test with a local fake release
    return os.getenv("BLIP_UPDATE_URL") or f"https://api.github.com/repos/{config.UPDATE_REPO}/releases/latest"


def parse_version(v):
    v = (v or "").strip().lstrip("vV")
    parts = []
    for x in v.split("."):
        num = "".join(ch for ch in x if ch.isdigit())
        parts.append(int(num) if num else 0)
    return tuple((parts + [0, 0, 0])[:3])


def _get(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


class Updater(QObject):
    result = pyqtSignal(object)        # dict: {"status": "new"/"current"/"error", ...}
    progress = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.busy = False
        self.release = None

    # ---- checking ------------------------------------------------------------------------
    def due(self):
        try:
            return config.AUTO_UPDATE and __import__("time").time() - float(config.UPDATE_LAST or 0) > 6 * 3600
        except ValueError:
            return config.AUTO_UPDATE

    def check(self, manual=False):
        if self.busy:
            return
        self.busy = True
        config.UPDATE_LAST = str(int(__import__("time").time()))
        try:
            import settings
            settings.save()
        except Exception:
            pass
        threading.Thread(target=self._check, args=(manual,), daemon=True).start()

    def _check(self, manual):
        try:
            rel = json.loads(_get(api_url()))
            latest = rel.get("tag_name", "")
            if parse_version(latest) > parse_version(config.VERSION):
                assets = {a["name"]: a["browser_download_url"] for a in rel.get("assets", [])}
                setup = next((n for n in assets if n.lower().startswith("blipsetup") and n.lower().endswith(".exe")), None)
                sha = next((n for n in assets if n.lower().endswith(".sha256")), None)
                if setup and sha:
                    self.release = {"version": latest.lstrip("vV"), "setup": assets[setup],
                                    "setup_name": setup, "sha": assets[sha]}
                    self.result.emit({"status": "new", "version": latest.lstrip("vV"), "manual": manual})
                    return
                self.result.emit({"status": "error", "manual": manual,
                                  "msg": "A new version exists but its files aren't ready yet."})
                return
            self.result.emit({"status": "current", "version": config.VERSION, "manual": manual})
        except Exception as e:
            self.result.emit({"status": "error", "manual": manual, "msg": f"Couldn't check for updates ({e})"})
        finally:
            self.busy = False

    # ---- installing --------------------------------------------------------------------------
    def install(self, on_ready):
        """Download + verify in the background, then call on_ready(path) (or on_ready(None, msg))."""
        if not self.release:
            return

        def work():
            try:
                rel = self.release
                folder = Path(tempfile.gettempdir()) / "BlipUpdate"
                folder.mkdir(exist_ok=True)
                self.progress.emit("Downloading the update…")
                data = _get(rel["setup"], timeout=120)
                want = _get(rel["sha"]).decode("utf-8", "replace").split()[0].strip().lower()
                got = hashlib.sha256(data).hexdigest()
                if got != want:
                    on_ready(None, "The download didn't match its checksum, so I didn't install it.")
                    return
                path = folder / rel["setup_name"]
                path.write_bytes(data)
                on_ready(str(path), None)
            except Exception as e:
                on_ready(None, f"Update download failed ({e})")
        threading.Thread(target=work, daemon=True).start()


def run_installer(path):
    """Start the installer silently (it closes Blip, updates it and starts it again)."""
    subprocess.Popen([path, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/CLOSEAPPLICATIONS", "/UPDATE"],
                     creationflags=getattr(subprocess, "DETACHED_PROCESS", 0), close_fds=True)


def installed():
    """True when this Blip was installed with the installer (not run from a build folder)."""
    if not getattr(sys, "frozen", False):
        return False
    return (Path(sys.executable).parent / "unins000.exe").exists()
