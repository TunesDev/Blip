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
STATIONS_VERSION = 2
DEFAULT_STATIONS = [
    # Ireland
    {"name": "RTÉ Radio 1", "genre": "Talk & music", "country": "Ireland", "url": "http://icecast.rte.ie/radio1"},
    {"name": "RTÉ 2FM", "genre": "Pop", "country": "Ireland", "url": "https://liveaudio.rte.ie/hls-radio/2fm/chunklist.m3u8"},
    {"name": "RTÉ Gold", "genre": "Classic hits", "country": "Ireland", "url": "https://liveaudio.rte.ie/hls-radio/gold/chunklist.m3u8"},
    {"name": "Today FM", "genre": "Pop / rock", "country": "Ireland", "url": "https://stream.audioxi.com/TD"},
    {"name": "Dublin's 98FM", "genre": "Pop", "country": "Ireland", "url": "https://stream.audioxi.com/98"},
    {"name": "Beat 102 103", "genre": "Dance / pop", "country": "Ireland", "url": "https://stream.audioxi.com/BEAT"},
    {"name": "Newstalk", "genre": "News & talk", "country": "Ireland", "url": "https://edge.audioxi.com/NT"},
    # UK
    {"name": "BBC Radio 1", "genre": "Pop", "country": "UK",
     "url": "http://a.files.bbci.co.uk/ms6/live/3441A116-B12E-4D2F-ACA8-C1984642FA4B/audio/simulcast/hls/nonuk/pc_hd_abr_v2/ak/bbc_radio_one.m3u8"},
    {"name": "BBC Radio 2", "genre": "Pop / classics", "country": "UK",
     "url": "http://as-hls-ww-live.akamaized.net/pool_74208725/live/ww/bbc_radio_two/bbc_radio_two.isml/bbc_radio_two-audio%3d128000.norewind.m3u8"},
    {"name": "Capital", "genre": "Pop", "country": "UK", "url": "http://media-ice.musicradio.com/CapitalMP3"},
    {"name": "Capital XTRA", "genre": "Hip-hop / R&B", "country": "UK", "url": "https://media-the.musicradio.com/CapitalXTRALondonMP3"},
    {"name": "Capital Dance", "genre": "Dance", "country": "UK", "url": "https://icecast.thisisdax.com/CapitalDanceMP3"},
    {"name": "KISS UK", "genre": "Dance / R&B", "country": "UK", "url": "https://live-kiss.sharp-stream.com/kiss100.mp3"},
    {"name": "Heart UK", "genre": "Pop", "country": "UK", "url": "http://media-ice.musicradio.com/HeartUKMP3"},
    {"name": "Radio X", "genre": "Rock / indie", "country": "UK", "url": "http://media-the.musicradio.com/RadioXUK"},
    {"name": "Smooth", "genre": "Easy listening", "country": "UK", "url": "http://media-the.musicradio.com/SmoothLondon"},
    # chill & genres
    {"name": "Groove Salad", "genre": "Chill", "country": "Internet", "url": "https://ice4.somafm.com/groovesalad-128-mp3"},
    {"name": "Lofi 24/7", "genre": "Lofi", "country": "Internet", "url": "http://usa9.fastcast4u.com/proxy/jamz?mp=/1"},
    {"name": "Dance Wave!", "genre": "Dance", "country": "Internet", "url": "https://dancewave.online/dance.mp3"},
    {"name": "Indie Pop Rocks", "genre": "Indie", "country": "Internet", "url": "https://ice4.somafm.com/indiepop-128-mp3"},
]
RADIO_BROWSER = ["de1", "de2", "fi1", "nl1", "at1"]   # public, free directory of real stations


def _radio_data():
    try:
        d = json.loads(STATIONS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    if d.get("version", 1) < STATIONS_VERSION:            # new built-in list, keep your favourites
        d = {"version": STATIONS_VERSION, "stations": DEFAULT_STATIONS,
             "favourites": d.get("favourites", []), "recent": d.get("recent", [])}
        _save_radio(d)
    return d


def _save_radio(d):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    d.setdefault("_help", "Blip's radio. Add your own: name, genre, country and a stream URL.")
    tmp = STATIONS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, STATIONS_FILE)


def load_stations():
    return list(_radio_data().get("stations") or DEFAULT_STATIONS)


def search_stations(name="", country="", tag="", limit=40):
    """Real stations from the free Radio Browser directory (only when you search)."""
    import urllib.parse
    import urllib.request
    q = {"order": "clickcount", "reverse": "true", "hidebroken": "true", "limit": str(limit)}
    if name:
        q["name"] = name
    if country:
        q["countrycode"] = country
    if tag:
        q["tag"] = tag
    last = None
    for host in RADIO_BROWSER:
        try:
            req = urllib.request.Request(f"https://{host}.api.radio-browser.info/json/stations/search?"
                                         + urllib.parse.urlencode(q), headers={"User-Agent": "Blip/1.3"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.load(r)
            out, seen = [], set()
            for s in data:
                url = s.get("url_resolved") or s.get("url")
                key = (s.get("name", "").strip().lower())
                if url and key not in seen:
                    seen.add(key)
                    tags = ", ".join(x for x in (s.get("tags") or "").split(",")[:2] if x)
                    out.append({"name": s.get("name", "?").strip()[:60], "genre": tags.title() or "Radio",
                                "country": s.get("country") or s.get("countrycode") or "", "url": url})
            return out
        except Exception as e:
            last = e
    raise ConnectionError(f"Radio directory unreachable ({last})")


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
                was = bool(self.media.get("playing"))
                self.media = {k: m.get(k) for k in ("song", "app", "playing")}
                if self.radio_on and self.radio_playing and self.media["playing"] and not was \
                        and time.monotonic() - getattr(self, "radio_started", 0) > 4:
                    self.send({"cmd": "radio_pause"})       # you started other music: radio steps aside
                    self.note = ("Radio paused", "You're playing other music, so I paused the radio.")
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

    def favourites(self):
        return _radio_data().get("favourites", [])

    def recent(self):
        return _radio_data().get("recent", [])

    def toggle_favourite(self, station):
        d = _radio_data()
        favs = d.setdefault("favourites", [])
        if any(f["url"] == station["url"] for f in favs):
            d["favourites"] = [f for f in favs if f["url"] != station["url"]]
        else:
            favs.insert(0, station)
        _save_radio(d)
        return any(f["url"] == station["url"] for f in d["favourites"])

    def is_favourite(self, station):
        return bool(station) and any(f["url"] == station["url"] for f in self.favourites())

    def set_muted(self, muted):
        self.muted = muted
        if self.radio_on:
            self.send({"cmd": "volume", "v": 0 if muted else config.RADIO_VOLUME / 100})

    def radio_play(self, station=None):
        st = self.get_stations()
        if station is None:
            station = next((s for s in st if s["name"] == config.RADIO_STATION), st[0])
        self.station = station
        self.radio_on, self.radio_song, self.radio_error = True, None, None
        self.radio_started = time.monotonic()
        config.RADIO_STATION = station["name"]
        if self.media.get("playing"):                    # don't play over your music
            self.send({"cmd": "pause_media"})
        d = _radio_data()                                 # remember as recently played
        d["recent"] = ([station] + [r for r in d.get("recent", []) if r["url"] != station["url"]])[:12]
        _save_radio(d)
        self.send({"cmd": "radio_play", "url": station["url"], "volume": config.RADIO_VOLUME / 100})
        self.radio_changed.emit()

    def radio_next(self, step=1):
        st = getattr(self, "play_list", None) or self.get_stations()
        i = next((k for k, s in enumerate(st) if self.station and s["name"] == self.station["name"]), -1)
        self.radio_play(st[(i + step) % len(st)])

    def radio_stop(self):
        if self.radio_on:
            self.send({"cmd": "radio_stop"})
        self.radio_on = self.radio_playing = False
        self.radio_song = None
        self.radio_changed.emit()

    def set_volume(self, v):
        config.RADIO_VOLUME = int(v)
        self.muted = False
        if self.radio_on:
            self.send({"cmd": "volume", "v": v / 100})

    def find_station(self, words):
        """'chill' -> a chill station; '' -> last station."""
        st = self.get_stations()
        w = words.lower()
        return next((s for s in st if s["genre"].lower() in w or s["name"].lower() in w), None)
