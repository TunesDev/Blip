"""
Desktop pet - the music helper: a small second Blip process (Blip.exe --helper NAME).
It only runs while music is playing (or the radio is on), and quits when it's quiet,
so its memory really goes back to Windows. It does two jobs:
  * reads what's playing from Windows' media controls (any player) + Play/Pause/Next
  * plays Blip's mini radio
It talks to Blip over a local pipe (QLocalSocket), one JSON message per line.
Developed by Tunes
"""
import asyncio
import json
import sys

from PyQt6.QtCore import QCoreApplication, QTimer, QUrl
from PyQt6.QtNetwork import QLocalSocket

STATUS_PLAYING = 4


class Helper:
    def __init__(self, app, name):
        self.app = app
        self.sock = QLocalSocket()
        self.sock.readyRead.connect(self.read)
        self.sock.disconnected.connect(app.quit)          # Blip closed: we go too
        self.sock.connectToServer(name)
        if not self.sock.waitForConnected(5000):
            raise SystemExit(1)
        self.buf = b""
        self.loop = asyncio.new_event_loop()
        self.manager = None
        self.session = None
        self.media_failed = False
        self.last_media = None
        self.player = None                                # radio, created on demand
        self.audio = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.poll_media)
        self.timer.start(2000)
        self.poll_media()

    # ---- pipe ----------------------------------------------------------------------
    def send(self, msg):
        self.sock.write((json.dumps(msg) + "\n").encode("utf-8"))
        self.sock.flush()

    def read(self):
        self.buf += bytes(self.sock.readAll())
        while b"\n" in self.buf:
            line, self.buf = self.buf.split(b"\n", 1)
            try:
                self.handle(json.loads(line))
            except Exception as e:
                self.send({"t": "error", "msg": str(e)})

    def handle(self, m):
        cmd = m.get("cmd")
        if cmd == "quit":
            self.radio_stop()
            self.app.quit()
        elif cmd == "play_pause":
            self.media_control("try_toggle_play_pause_async")
        elif cmd == "next":
            self.media_control("try_skip_next_async")
        elif cmd == "previous":
            self.media_control("try_skip_previous_async")
        elif cmd == "radio_play":
            self.radio_play(m["url"], m.get("volume", 0.6))
        elif cmd == "radio_pause" and self.player:
            self.player.pause()
        elif cmd == "radio_resume" and self.player:
            self.player.play()
        elif cmd == "radio_stop":
            self.radio_stop()
        elif cmd == "volume" and self.audio:
            self.audio.setVolume(float(m["v"]))

    # ---- Windows media controls (any player) -------------------------------------------
    def poll_media(self):
        if self.media_failed:
            return
        try:
            if self.manager is None:
                from winrt.windows.media.control import (
                    GlobalSystemMediaTransportControlsSessionManager as Manager)
                self.manager = self.loop.run_until_complete(Manager.request_async())
            s = self.manager.get_current_session()
            self.session = s
            msg = {"t": "media", "song": None, "app": "", "playing": False}
            if s is not None:
                props = self.loop.run_until_complete(s.try_get_media_properties_async())
                title, artist = (props.title or "").strip(), (props.artist or "").strip()
                msg.update(song=f"{title} - {artist}" if title and artist else (title or None),
                           app=s.source_app_user_model_id or "",
                           playing=s.get_playback_info().playback_status == STATUS_PLAYING)
            if msg != self.last_media:
                self.last_media = msg
                self.send(msg)
        except Exception as e:
            self.media_failed = True
            self.send({"t": "error", "msg": f"media controls: {e}"})

    def media_control(self, method):
        try:
            self.poll_media()
            if self.session is not None:
                self.loop.run_until_complete(getattr(self.session, method)())
                QTimer.singleShot(400, self.poll_media)
        except Exception as e:
            self.send({"t": "error", "msg": f"media control: {e}"})

    # ---- mini radio -------------------------------------------------------------------
    def radio_play(self, url, volume):
        if self.player is None:
            from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
            self.audio = QAudioOutput()
            self.player = QMediaPlayer()
            self.player.setAudioOutput(self.audio)
            self.player.metaDataChanged.connect(self.radio_meta)
            self.player.playbackStateChanged.connect(self.radio_state)
            self.player.errorOccurred.connect(
                lambda err, text: self.send({"t": "radio", "playing": False, "error": text}))
        self.audio.setVolume(float(volume))
        self.player.setSource(QUrl(url))
        self.player.play()

    def radio_meta(self):
        from PyQt6.QtMultimedia import QMediaMetaData
        title = (self.player.metaData().stringValue(QMediaMetaData.Key.Title) or "").strip()
        self.send({"t": "radio", "song": title or None})

    def radio_state(self, state):
        from PyQt6.QtMultimedia import QMediaPlayer
        self.send({"t": "radio", "playing": state == QMediaPlayer.PlaybackState.PlayingState})

    def radio_stop(self):
        if self.player is not None:
            self.player.stop()
            self.player.deleteLater()
            self.audio.deleteLater()
            self.player = self.audio = None
            self.send({"t": "radio", "playing": False, "stopped": True})


def main(name):
    app = QCoreApplication(sys.argv[:1])
    helper = Helper(app, name)  # noqa: F841  (keep it alive)
    sys.exit(app.exec())
