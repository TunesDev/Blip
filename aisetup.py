"""
Desktop pet - one-click setup for Blip's AI chat (only when you press "Set it up for me").
  1. If Ollama isn't installed: download the official installer from ollama.com, check its
     digital signature really is "Ollama Inc." (Windows Authenticode), then run it.
  2. Download Blip's brain (llama3.2:3b, about 2 GB) through Ollama's own local API, with progress.
Nothing is downloaded without your click. Cancel stops it.
Developed by Tunes
"""
import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal

OLLAMA_URL = "https://ollama.com/download/OllamaSetup.exe"
API = "http://127.0.0.1:11434"
MODEL = "llama3.2:3b"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def ollama_exe():
    found = shutil.which("ollama")
    if found:
        return found
    p = Path(os.getenv("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
    return str(p) if p.exists() else None


def api_up():
    try:
        urllib.request.urlopen(API + "/api/tags", timeout=2).close()
        return True
    except Exception:
        return False


def has_model():
    try:
        with urllib.request.urlopen(API + "/api/tags", timeout=3) as r:
            names = [m["name"] for m in json.load(r).get("models", [])]
        return any(n.startswith("llama3.2") for n in names)
    except Exception:
        return False


def start_ollama():
    """Ollama installed but not running: start it quietly."""
    app = Path(os.getenv("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama app.exe"
    try:
        if app.exists():
            subprocess.Popen([str(app)], creationflags=NO_WINDOW)
        elif ollama_exe():
            subprocess.Popen([ollama_exe(), "serve"], creationflags=NO_WINDOW,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
    for _ in range(30):
        if api_up():
            return True
        time.sleep(1)
    return False


def signed_by_ollama(path):
    """Windows Authenticode check: valid signature whose signer is Ollama Inc."""
    script = (f"$s = Get-AuthenticodeSignature -LiteralPath '{path}'; "
              "Write-Output ($s.Status.ToString() + '|' + $s.SignerCertificate.Subject)")
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", script], capture_output=True,
                             text=True, timeout=60, creationflags=NO_WINDOW).stdout.strip()
    except Exception:
        return False
    status, _, subject = out.partition("|")
    return status == "Valid" and "CN=Ollama" in subject


class Setup(QObject):
    progress = pyqtSignal(str, float)      # message, 0..1 (or -1 = unknown)
    finished = pyqtSignal(bool, str)       # ok, message

    def __init__(self):
        super().__init__()
        self.cancelled = False

    def cancel(self):
        self.cancelled = True

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            if not ollama_exe():
                if not self._install_ollama():
                    return
            if not api_up():
                self.progress.emit("Starting Ollama…", -1)
                if not start_ollama():
                    self.finished.emit(False, "Ollama didn't start. Open it from the Start menu, then press Retry.")
                    return
            if not has_model():
                if not self._pull():
                    return
            self.finished.emit(True, "I'm ready to chat! Say hi 😊")
        except OSError as e:
            low = str(e).lower()
            msg = ("Your disk is full. Free some space (about 3 GB) and press Retry." if "space" in low
                   else "I couldn't reach the internet. Check your connection and press Retry.")
            self.finished.emit(False, msg)
        except Exception as e:
            self.finished.emit(False, f"Setup stopped ({e}). Press Retry to try again.")

    def _install_ollama(self):
        dest = Path(tempfile.gettempdir()) / "BlipSetup" / "OllamaSetup.exe"
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(OLLAMA_URL, headers={"User-Agent": "Blip/1.3"})
        with urllib.request.urlopen(req, timeout=30) as r, open(dest, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            done = 0
            while True:
                if self.cancelled:
                    self.finished.emit(False, "Cancelled.")
                    return False
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                self.progress.emit(f"Downloading Ollama… {done / 1048576:,.0f} MB"
                                   + (f" of {total / 1048576:,.0f} MB" if total else ""),
                                   done / total if total else -1)
        self.progress.emit("Checking the installer's signature…", -1)
        if not signed_by_ollama(dest):
            self.finished.emit(False, "The download didn't have Ollama's signature, so I didn't run it. "
                                      "You can get Ollama yourself from ollama.com.")
            return False
        self.progress.emit("Installing Ollama… (follow the installer if it asks anything)", -1)
        subprocess.run([str(dest)], creationflags=0)       # the normal Ollama installer
        for _ in range(60):
            if ollama_exe() and api_up():
                return True
            time.sleep(1)
        if ollama_exe():
            return True
        self.finished.emit(False, "Ollama didn't finish installing. Press Retry.")
        return False

    def _pull(self):
        req = urllib.request.Request(API + "/api/pull", data=json.dumps({"model": MODEL, "stream": True}).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            for line in r:
                if self.cancelled:
                    self.finished.emit(False, "Cancelled. Press Retry to continue later (it resumes).")
                    return False
                if not line.strip():
                    continue
                m = json.loads(line)
                if m.get("error"):
                    raise OSError(m["error"])
                total, done = m.get("total"), m.get("completed")
                if total and done:
                    self.progress.emit(f"Downloading my brain… {done / 1073741824:.2f} of {total / 1073741824:.2f} GB",
                                       done / total)
                else:
                    self.progress.emit(m.get("status", "Getting ready…").capitalize(), -1)
        return True
