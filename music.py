"""
Desktop pet - music: Blip dances to whatever is playing, and has a mini radio.
Kept light:
  * Blip itself only uses the cheap volume-mixer check (is any app making sound?).
  * Only while something plays (or the radio is on) a small helper process runs
    (helper.py: song name, Play/Pause/Next, radio). After 2 minutes of silence it is
    closed, so its memory goes back to Windows.
Works with any player (Spotify, browsers, VLC, radio apps...). No other app needs Blip.
Developed by Tunes
"""
import json
import os
import sys
import time
from pathlib import Path

from PyQt6.QtCore import QObject, QProcess, pyqtSignal
from PyQt6.QtNetwork import QLocalServer

import config
from settings import DATA_DIR

AudioUtilities = IAudioMeterInformation = None


def _load_pycaw():
    """Loaded the first time music features are used (not at all if they're off)."""
    global AudioUtilities, IAudioMeterInformation
    if AudioUtilities is None:
        try:
            from pycaw.pycaw import AudioUtilities as AU, IAudioMeterInformation as IM
            AudioUtilities, IAudioMeterInformation = AU, IM
        except Exception:
            return False
    return True

QUIET_SECONDS = 120          # helper closes after this long without sound
RADIO_PAUSE_SECONDS = 120    # a paused radio is switched off after this long
STATIONS_FILE = DATA_DIR / "stations.json"
DEFAULT_STATIONS = [
    {"name": "Groove Salad", "genre": "Chill", "url": "https://ice4.somafm.com/groovesalad-128-mp3"},
    {"name": "Smooth Chill", "genre": "Chill", "url": "https://media-ssl.musicradio.com/ChillMP3"},
    {"name": "Lofi 24/7", "genre": "Lofi", "url": "http://usa9.fastcast4u.com/proxy/jamz?mp=/1"},
    {"name": "Indie Pop Rocks", "genre": "Pop", "url": "https://ice4.somafm.com/indiepop-128-mp3"},
    {"name": "PopTron", "genre": "Pop", "url": "https://ice4.somafm.com/poptron-128-mp3"},
    {"name": "Dance Wave!", "genre": "Dance", "url": "https://dancewave.online/dance.mp3"},
    {"name": "Beat Blender", "genre": "Electronic", "url": "https://ice4.somafm.com/beatblender-128-mp3"},
    {"name": "West Coast G-Funk", "genre": "Hip-Hop", "url": "https://r.bgp.rodeo/listen/west_coast/radio.mp3"},
    {"name": "Underground 80s", "genre": "80s", "url": "https://ice4.somafm.com/u80s-128-mp3"},
]


def load_stations():
    try:
        st = json.loads(STATIONS_FILE.read_text(encoding="utf-8"))["stations"]
        if st:
            return st
    except (OSError, ValueError, KeyError):
        pass
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STATIONS_FILE.write_text(json.dumps({
        "_help": "Blip's radio stations. Add your own: name, genre and a stream URL (mp3/aac).",
        "stations": DEFAULT_STATIONS}, indent=2), encoding="utf-8")
    return list(DEFAULT_STATIONS)


class MusicWatcher(QObject):
    radio_changed = pyqtSignal()          # for the radio panel

    def __init__(self):
        super().__init__()
        self.server = None
        self.proc = None
        self.sock = None
        self.buf = b""
        self.queue = []                   # commands waiting for the helper to connect
        self.next_scan = 0.0
        self.last_sound = 0.0
        self.sessions = []                # (process name, pid, meter) of apps with audio
        self.meters = []                  # meters we follow for the dance
        self.media = {"song": None, "app": "", "playing": False}
        # radio
        self.stations = None
        self.radio_on = False             # a station is loaded in the helper
        self.radio_playing = False
        self.radio_paused_at = 0.0
        self.radio_song = None
        self.radio_error = None
        self.station = None
        self.level = 0.0
        self.last_loud = 0.0

    # ---- helper process ------------------------------------------------------------
    @property
    def helper_running(self):
        return self.proc is not None and self.proc.state() != QProcess.ProcessState.NotRunning

    def start_helper(self):
        if self.helper_running:
            return
        name = f"blip-helper-{os.getpid()}"
        if self.server is None:
            QLocalServer.removeServer(name)
            self.server = QLocalServer(self)
            self.server.newConnection.connect(self._connected)
            self.server.listen(name)
        self.proc = QProcess(self)
        if getattr(sys, "frozen", False):
            self.proc.start(sys.executable, ["--helper", name])
        else:
            exe = Path(sys.executable)
            exe = exe.with_name("pythonw.exe") if exe.with_name("pythonw.exe").exists() else exe
            self.proc.start(str(exe), [str(Path(__file__).with_name("main.py")), "--helper", name])
        self.proc.finished.connect(self._helper_gone)

    def stop_helper(self):
        if self.helper_running:
            self.send({"cmd": "quit"})
            self.proc.waitForFinished(1500) or self.proc.kill()

    def _connected(self):
        self.sock = self.server.nextPendingConnection()
        self.sock.readyRead.connect(self._read)
        for m in self.queue:
            self._write(m)
        self.queue = []

    def _helper_gone(self, *_):
        self.sock = None
        self.proc = None
        self.media = {"song": None, "app": "", "playing": False}
        if self.radio_on:
            self.radio_on = self.radio_playing = False
            self.radio_changed.emit()

    def send(self, m):
        if self.sock is not None and self.sock.isOpen():
            self._write(m)
        else:
            self.queue.append(m)
            self.start_helper()

    def _write(self, m):
        self.sock.write((json.dumps(m) + "\n").encode("utf-8"))
        self.sock.flush()

    def _read(self):
        self.buf += bytes(self.sock.readAll())
        while b"\n" in self.buf:
            line, self.buf = self.buf.split(b"\n", 1)
            try:
                m = json.loads(line)
            except ValueError:
                continue
            if m.get("t") == "media":
                self.media = {k: m.get(k) for k in ("song", "app", "playing")}
                self.meters = []                      # follow the new player's audio
            elif m.get("t") == "radio":
                if "playing" in m:
                    self.radio_playing = bool(m["playing"])
                    if not self.radio_playing:
                        self.radio_paused_at = time.monotonic()
                if "song" in m:
                    self.radio_song = m["song"]
                if m.get("error"):
                    self.radio_error = m["error"]
                if m.get("stopped"):
                    self.radio_on = False
                self.radio_changed.emit()
            elif m.get("t") == "error":
                print("Music helper:", m.get("msg"))

    # ---- cheap check (every 2 s) -------------------------------------------------------
    def scan(self):
        self.sessions = []
        if not _load_pycaw():
            return
        try:
            for s in AudioUtilities.GetAllSessions():
                if not s.Process or s.ProcessId == os.getpid():
                    continue
                m = s._ctl.QueryInterface(IAudioMeterInformation)
                self.sessions.append((s.Process.name().lower(), s.ProcessId, m))
                if m.GetPeakValue() > 0.01:
                    self.last_sound = time.monotonic()
        except Exception as e:
            print("Audio check failed:", e)

    def _pick_meters(self):
        """The meter(s) of the app that's playing: the radio helper, or the media app."""
        if self.radio_on and self.proc is not None:
            pid = int(self.proc.processId())
            mine = [m for _, p, m in self.sessions if p == pid]
            # (from the .py files, pythonw may hand over to another python process)
            return mine or [m for name, _, m in self.sessions if name in ("blip.exe", "python.exe")]
        app = (self.media.get("app") or "").lower()
        key = app.removesuffix(".exe").split("!")[-1].split(".")[-1]
        return [m for name, _, m in self.sessions
                if key and (name.removesuffix(".exe") == key or name.startswith(key)
                            or key.startswith(name.removesuffix(".exe")))]

    # ---- every frame ------------------------------------------------------------------
    def update(self):
        """Returns (song or None, level 0..1, playing?)."""
        now = time.monotonic()
        if now >= self.next_scan:
            self.next_scan = now + 2.0
            self.scan()
            sound = now - self.last_sound < QUIET_SECONDS
            if config.music_active() and (sound or self.radio_on) and not self.helper_running:
                self.start_helper()                  # something's playing: find out what
            elif self.helper_running and not self.radio_on and not sound:
                self.stop_helper()                   # quiet for 2 min: free the memory
            if self.radio_on and not self.radio_playing and \
                    now - self.radio_paused_at > RADIO_PAUSE_SECONDS:
                self.radio_stop()
            self.meters = self._pick_meters()
        playing = self.radio_playing if self.radio_on else bool(self.media.get("playing"))
        peak = 0.0
        if playing:
            for m in self.meters:
                try:
                    peak = max(peak, m.GetPeakValue())
                except Exception:
                    self.meters = []
        self.level = peak if peak > self.level else self.level * 0.8 + peak * 0.2
        if peak > 0.02:
            self.last_loud = now
        song = (self.radio_song or (self.station or {}).get("name")) if self.radio_on \
            else self.media.get("song")
        return song, self.level, playing and now - self.last_loud < 1.5

    @property
    def session(self):
        """Something to control? (used to grey out the Music menu)"""
        return True if (self.radio_on or self.media.get("app")) else None

    failed = False

    # ---- buttons ----------------------------------------------------------------------
    def play_pause(self):
        if self.radio_on:
            self.send({"cmd": "radio_pause" if self.radio_playing else "radio_resume"})
        else:
            self.send({"cmd": "play_pause"})

    def next_track(self):
        if self.radio_on:
            self.radio_next()
        else:
            self.send({"cmd": "next"})

    def previous_track(self):
        if not self.radio_on:
            self.send({"cmd": "previous"})

    # ---- radio --------------------------------------------------------------------------
    def get_stations(self):
        if self.stations is None:
            self.stations = load_stations()
        return self.stations

    def radio_play(self, station=None):
        st = self.get_stations()
        if station is None:
            station = next((s for s in st if s["name"] == config.RADIO_STATION), st[0])
        self.station = station
        self.radio_on, self.radio_song, self.radio_error = True, None, None
        config.RADIO_STATION = station["name"]
        self.send({"cmd": "radio_play", "url": station["url"], "volume": config.RADIO_VOLUME / 100})
        self.radio_changed.emit()

    def radio_next(self):
        st = self.get_stations()
        i = next((k for k, s in enumerate(st) if self.station and s["name"] == self.station["name"]), -1)
        self.radio_play(st[(i + 1) % len(st)])

    def radio_stop(self):
        if self.radio_on:
            self.send({"cmd": "radio_stop"})
        self.radio_on = self.radio_playing = False
        self.radio_song = None
        self.radio_changed.emit()

    def set_volume(self, v):
        config.RADIO_VOLUME = int(v)
        if self.radio_on:
            self.send({"cmd": "volume", "v": v / 100})

    def find_station(self, words):
        """'chill' -> a chill station; '' -> last station."""
        st = self.get_stations()
        w = words.lower()
        return next((s for s in st if s["genre"].lower() in w or s["name"].lower() in w), None)
