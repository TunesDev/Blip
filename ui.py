"""
Desktop pet - the right-click menu, Settings window and About window.
All in the glass purple/cyan style.
Developed by Tunes
"""
from PyQt6.QtCore import QPoint, QRectF, Qt, QTimer
from PyQt6.QtGui import QAction, QBrush, QColor, QLinearGradient, QPainter, QPen
from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout,
                             QLabel, QLineEdit, QMenu, QPushButton, QSlider, QTextBrowser,
                             QVBoxLayout, QWidget)
import html
import os
from pathlib import Path
import time

import autostart
import config
import settings
from character import CHARACTERS, HATS, THEMES, draw_pet

STYLE = """
QMenu {
    background: rgba(26, 18, 46, 238);
    border: 1px solid rgba(160, 110, 255, 170);
    border-radius: 12px;
    padding: 6px;
    color: #EAF6FF;
    font: 10pt "Segoe UI";
}
QMenu::item { padding: 7px 26px 7px 14px; border-radius: 7px; }
QMenu::item:selected { background: rgba(0, 225, 255, 55); }
QMenu::item:disabled { color: rgba(234, 246, 255, 110); }
QMenu::separator { height: 1px; background: rgba(160, 110, 255, 90); margin: 5px 8px; }

QLabel { color: #EAF6FF; font: 10pt "Segoe UI"; background: transparent; }
QLabel#title { font: bold 15pt "Segoe UI"; color: white; }
QLabel#credit { color: rgba(0, 225, 255, 200); font: 9pt "Segoe UI"; }
QCheckBox { color: #EAF6FF; font: 10pt "Segoe UI"; spacing: 8px; background: transparent; }
QCheckBox::indicator {
    width: 16px; height: 16px; border-radius: 5px;
    border: 1px solid rgba(160, 110, 255, 200); background: rgba(255, 255, 255, 20);
}
QCheckBox::indicator:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #9a5aff, stop:1 #00e1ff);
    border: 1px solid white;
}
QComboBox {
    background: rgba(255, 255, 255, 22); color: white; border: 1px solid rgba(160, 110, 255, 150);
    border-radius: 7px; padding: 4px 10px; font: 10pt "Segoe UI"; min-width: 130px;
}
QComboBox QAbstractItemView {
    background: rgb(30, 22, 52); color: white; selection-background-color: rgba(0, 225, 255, 80);
    border: 1px solid rgba(160, 110, 255, 150);
}
QSlider::groove:horizontal { height: 4px; background: rgba(255, 255, 255, 40); border-radius: 2px; }
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #9a5aff, stop:1 #00e1ff);
    border-radius: 2px;
}
QSlider::handle:horizontal {
    width: 14px; height: 14px; margin: -6px 0; border-radius: 7px;
    background: white; border: 2px solid #00e1ff;
}
QPushButton {
    background: rgba(255, 255, 255, 22); color: white; border: 1px solid rgba(160, 110, 255, 160);
    border-radius: 8px; padding: 7px 18px; font: 10pt "Segoe UI";
}
QPushButton:hover { background: rgba(0, 225, 255, 55); }
QTextBrowser {
    background: rgba(10, 8, 24, 150); color: #EAF6FF; border: 1px solid rgba(160, 110, 255, 110);
    border-radius: 10px; padding: 6px; font: 10pt "Segoe UI";
}
QLineEdit {
    background: rgba(255, 255, 255, 22); color: white; border: 1px solid rgba(160, 110, 255, 150);
    border-radius: 8px; padding: 7px 10px; font: 10pt "Segoe UI";
}
QLineEdit:focus { border: 1px solid #00e1ff; }
QPushButton#close { padding: 2px 9px; border: none; background: transparent; font: 12pt "Segoe UI"; }
QPushButton#primary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(154,90,255,200), stop:1 rgba(0,225,255,200));
    border: none; font-weight: bold;
}
"""


def glass_menu(parent=None) -> QMenu:
    m = QMenu(parent)
    # Needed so the rounded corners are see-through instead of black.
    m.setWindowFlags(m.windowFlags() | Qt.WindowType.FramelessWindowHint
                     | Qt.WindowType.NoDropShadowWindowHint)
    m.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    m.setStyleSheet(STYLE)
    return m


def build_menu(pet, app) -> QMenu:
    """The menu used for right-clicking the pet AND the tray icon."""
    menu = glass_menu()
    _PET["pet"] = pet

    title = QAction(f"{config.APP_NAME}  ·  {config.CREDIT}", menu)
    title.setEnabled(False)
    menu.addAction(title)
    menu.addSeparator()

    # Kept short on purpose; less-used things live in Customise & settings.
    import extras
    dnd = glass_menu(menu)
    dnd.setTitle("Do not disturb")
    dnd_1h = dnd.addAction("For 1 hour", lambda: (extras.set_dnd(3600), settings.save(), pet.update()))
    dnd_on = dnd.addAction("Until I turn it off", lambda: (extras.set_dnd(float("inf")), settings.save(), pet.update()))
    dnd_off = dnd.addAction("Turn off", lambda: (extras.set_dnd(None), settings.save(), pet.update()))
    menu.addMenu(dnd)
    menu.addAction("Chat with Blip…", lambda: open_chat(pet))
    menu.addAction("Help my PC…", lambda: open_helper(pet))

    music = glass_menu(menu)
    music.setTitle("Music")
    music.addAction("What's playing?", pet.show_song)
    music.addAction("Play / Pause", lambda: pet.music.play_pause())
    music.addAction("Next song", lambda: pet.music.next_track())
    music.addAction("Previous song", lambda: pet.music.previous_track())
    music.addSeparator()
    music.addAction("Radio…", lambda: open_radio(pet))
    music_action = menu.addMenu(music)

    play = glass_menu(menu)
    play.setTitle("Play")
    sleep_action = QAction("Go to sleep", play)
    sleep_action.triggered.connect(pet.toggle_sleep)
    play.addAction(sleep_action)
    play.addAction("Jump!", pet.jump)
    play.addAction("Feed a snack", pet.feed)
    play.addSeparator()
    play.addAction("Football", lambda: pet.trick("football"))
    play.addAction("Throw the NFL ball", lambda: pet.trick("nfl"))
    play.addAction("Climb the desktop", lambda: pet.trick("climb"))
    play.addAction("Hide and seek", lambda: pet.trick("seek"))
    emotes = glass_menu(play)
    emotes.setTitle("Emotes")
    play.addMenu(emotes)
    play.addAction("Prestige Shop…", lambda: ShopDialog(pet).exec())
    play.addAction("Surprise me!", lambda: pet.trick())
    play.addSeparator()
    focus_action = play.addAction("Focus 25 min", lambda: pet.stop_focus() if extras.focus_left() else pet.start_focus(25))
    menu.addMenu(play)

    menu.addSeparator()
    menu.addAction("Customise && settings…", lambda: SettingsDialog(pet).exec())
    menu.addAction("Quit", app.quit)

    # Update things each time the menu opens.
    def refresh():
        sleep_action.setText("Wake up" if pet.state == "sleep" else "Go to sleep")
        import progress
        badge = progress.get().badge()
        title.setText(f"{config.APP_NAME}  {badge}  ·  {config.CREDIT}" if badge else
                      f"{config.APP_NAME}  ·  {config.CREDIT}")
        emotes.clear()
        owned = [i for i in progress.get().owned if i in ("Wave", "Flex", "Laugh")]
        for e in owned:
            emotes.addAction(e, lambda e=e: pet.trick("emote:" + e))
        if not owned:
            emotes.addAction("Buy emotes in the Prestige Shop").setEnabled(False)
        on = extras.dnd_on()
        dnd.setTitle("Do not disturb (on)" if on else "Do not disturb")
        dnd_off.setEnabled(on)
        focus_action.setText(f"Stop focus ({int(extras.focus_left() // 60) + 1} min left)"
                             if extras.focus_left() else "Focus 25 min")
        m = pet.music
        for a in music.actions()[:4]:                # grey out when nothing is playing
            a.setEnabled(m.session is not None)
    menu.aboutToShow.connect(refresh)
    return menu


# ---------------------------------------------------------------------------
class GlassDialog(QDialog):
    """Frameless rounded glass window you can drag around."""

    def __init__(self, title):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.WindowStaysOnTopHint)
        # Solid window with rounded corners cut out by a mask: a see-through window let
        # the apps behind show through and made the text hard to read.
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setStyleSheet(STYLE)
        self.setWindowTitle(title)
        self._drag = None

        self.root = QVBoxLayout(self)
        self.root.setContentsMargins(26, 22, 26, 20)
        self.root.setSpacing(12)
        t = QLabel(title)
        t.setObjectName("title")
        self.root.addWidget(t)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0, QColor(40, 22, 76))
        g.setColorAt(1, QColor(12, 34, 62))
        p.fillRect(self.rect(), QColor(26, 18, 52))
        p.setBrush(QBrush(g))
        p.setPen(QPen(QColor(160, 110, 255, 180), 1.2))
        p.drawRoundedRect(r, 16, 16)
        # soft shine along the top
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 14))
        p.drawRoundedRect(QRectF(r.left() + 2, r.top() + 2, r.width() - 4, 50), 14, 14)
        p.end()

    def hideEvent(self, e):
        super().hideEvent(e)
        import desktop                               # panel closed: hand its memory back
        QTimer.singleShot(1500, desktop.trim_self)

    def resizeEvent(self, e):
        from PyQt6.QtGui import QPainterPath, QRegion
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 16, 16)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))
        super().resizeEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag is not None:
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, e):
        self._drag = None

    def add_credit(self):
        c = QLabel(config.CREDIT)
        c.setObjectName("credit")
        c.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.root.addWidget(c)


class PetPreview(QWidget):
    """Small live preview of the pet inside the settings window."""

    def __init__(self, get_look, size=110):
        super().__init__()
        self.get_look = get_look
        self.setFixedSize(size, size)
        self.start = time.monotonic()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(66)          # ~15 FPS, only while the window is open

    def paintEvent(self, e):
        p = QPainter(self)
        character, theme, hat = self.get_look()
        draw_pet(p, self.width(), "idle", time.monotonic() - self.start,
                 character=character, theme=theme, hat=hat)
        p.end()


def slider(lo, hi, value):
    s = QSlider(Qt.Orientation.Horizontal)
    s.setRange(lo, hi)
    s.setValue(int(value))
    s.setMinimumWidth(180)
    return s


class SettingsDialog(GlassDialog):
    def __init__(self, pet):
        super().__init__(f"Customise {config.APP_NAME}")
        self.pet = pet

        # --- Looks, with a live preview ---
        top = QHBoxLayout()
        self.preview = PetPreview(self.current_look)
        top.addWidget(self.preview)
        looks = QFormLayout()
        self.character = QComboBox(); self.character.addItems(CHARACTERS)
        self.character.setCurrentText(config.CHARACTER)
        self.theme = QComboBox(); self.theme.addItems(list(THEMES))
        self.theme.setCurrentText(config.THEME)
        import progress
        import shop
        shop_hats = [i for i in progress.get().owned if shop.ITEMS.get(i, ("",))[0] == "hat"]
        self.hat = QComboBox(); self.hat.addItems(HATS + progress.get().unlocked_hats() + shop_hats)
        self.hat.setCurrentText(config.HAT)
        looks.addRow("Character", self.character)
        looks.addRow("Colours", self.theme)
        looks.addRow("Hat", self.hat)
        self.antics = QComboBox(); self.antics.addItems(["Off", "Rare", "Normal", "Lots"])
        self.antics.setCurrentText(config.ANTICS)
        looks.addRow("Random antics", self.antics)
        top.addLayout(looks)
        self.root.addLayout(top)

        # --- Behaviour ---
        form = QFormLayout()
        form.setHorizontalSpacing(16)
        self.size = slider(70, 220, config.PET_SIZE)
        self.speed = slider(15, 180, config.WALK_SPEED)
        self.bounce = slider(0, 85, config.BOUNCE * 100)
        self.sleep_after = slider(1, 30, config.USER_IDLE_SLEEP_SECONDS / 60)
        self.sleep_label = QLabel()
        self.sleep_after.valueChanged.connect(self.update_sleep_label)
        self.update_sleep_label()
        form.addRow("Size", self.size)
        form.addRow("Walk speed", self.speed)
        form.addRow("Bounciness", self.bounce)
        sl = QHBoxLayout(); sl.addWidget(self.sleep_after); sl.addWidget(self.sleep_label)
        form.addRow("Sleep when I'm away", sl)
        self.root.addLayout(form)

        self.eyes = QCheckBox("Eyes follow my cursor")
        self.eyes.setChecked(config.EYES_FOLLOW_CURSOR)
        self.games = QCheckBox("Hide during fullscreen games and videos")
        self.games.setChecked(config.HIDE_IN_FULLSCREEN)
        self.windows = QCheckBox("Sit on top of my windows (falls off when they move)")
        self.windows.setChecked(config.SIT_ON_WINDOWS)
        self.sweat = QCheckBox("Sweat when my CPU or RAM is maxed out")
        self.sweat.setChecked(config.SWEAT_WHEN_BUSY)
        self.helper = QCheckBox("Offer to help when my PC is struggling (max every 30 min)")
        self.helper.setChecked(config.PC_HELPER)
        self.night = QCheckBox("Get sleepy and yawn late at night")
        self.night.setChecked(config.SLEEPY_AT_NIGHT)
        self.questions = QCheckBox("Blip asks me a question now and then (max 3 a day)")
        self.questions.setChecked(config.ASK_QUESTIONS)
        self.games_buddy = QCheckBox("Game buddy: ask how my match went, keep my stats")
        self.games_buddy.setChecked(config.GAME_BUDDY)
        self.dance = QCheckBox("Dance to music (moves + headphones)")
        self.dance.setChecked(config.DANCE)
        self.music = QCheckBox("Show what's playing (song bubbles + music controls)")
        self.music.setChecked(config.LISTEN_TO_MUSIC)
        for box in (self.eyes, self.games, self.windows, self.sweat, self.helper, self.night,
                    self.dance, self.music, self.questions, self.games_buddy):
            self.root.addWidget(box)
        # --- Blip's level ---
        import progress, skins
        prog = progress.get()
        lvl = QHBoxLayout()
        need = progress.xp_for_level(prog.level)
        frac = 1.0 if prog.level >= progress.MAX_LEVEL else prog.xp / need
        xp_text = "MAX" if prog.level >= progress.MAX_LEVEL else f"{prog.xp:,} / {need:,} XP"
        lvl.addWidget(QLabel(f"<b>{prog.title()}</b>"))
        lvl.addWidget(GlassBar(frac, xp_text, 190))
        lvl.addWidget(QLabel(f"streak {prog.streak}d · {prog.tokens} tokens"))
        lvl.addStretch()
        if prog.can_prestige:
            pb = QPushButton("Prestige!"); pb.setObjectName("primary"); pb.setAutoDefault(False)
            pb.clicked.connect(self.do_prestige)
            lvl.addWidget(pb)
        sk = QPushButton(f"Skins… ({prog.skin})"); sk.setAutoDefault(False)
        sk.clicked.connect(lambda: SkinsDialog(self.pet).exec())
        lvl.addWidget(sk)
        shop_btn = QPushButton("Prestige Shop…"); shop_btn.setAutoDefault(False)
        shop_btn.clicked.connect(lambda: ShopDialog(self.pet).exec())
        lvl.addWidget(shop_btn)
        self.root.addLayout(lvl)
        quests = QHBoxLayout()
        parts = []
        for q, count, done in prog.today_quests():
            parts.append(("✔ " if done else "○ ") + f"{q[1]} ({min(count, q[3])}/{q[3]})")
        wk, wk_done = prog.week_progress()
        qlabel = QLabel("<b>Today's quests:</b>  " + "   ·   ".join(parts) +
                        f"<br><b>Weekly:</b> finish {progress.WEEKLY_GOAL} quests ({min(wk, progress.WEEKLY_GOAL)}/"
                        f"{progress.WEEKLY_GOAL}){' ✔' if wk_done else ''}  → +{progress.WEEKLY_XP} XP + 1 token")
        qlabel.setWordWrap(True)
        quests.addWidget(qlabel)
        self.root.addLayout(quests)
        self.aura = QCheckBox("Show my prestige aura around Blip")
        self.aura.setChecked(prog.aura)
        if prog.prestige:
            self.root.addWidget(self.aura)
        self.seasonal = QCheckBox("Seasonal outfits (Santa hat in December, pumpkin at Halloween...)")
        self.seasonal.setChecked(config.SEASONAL)
        self.root.addWidget(self.seasonal)
        snd = QHBoxLayout()
        snd.addWidget(QLabel("Tiny sounds"))
        self.sounds = QComboBox(); self.sounds.addItems(["Off", "Low", "Normal"])
        self.sounds.setCurrentText(config.SOUNDS)
        snd.addWidget(self.sounds)
        import extras
        happy = int(extras.happiness())
        snd.addStretch()
        snd.addWidget(QLabel("Happiness"))
        snd.addWidget(GlassBar(happy / 100, f"{happy}%", 150, pink=True))
        self.root.addLayout(snd)
        self.auto_update = QCheckBox("Install updates automatically (checks every 6 hours)")
        self.auto_update.setChecked(config.AUTO_UPDATE)
        self.root.addWidget(self.auto_update)
        self.startup = QCheckBox("Start Blip with Windows")
        self.startup.setChecked(autostart.is_enabled())
        self.root.addWidget(self.startup)

        extras = QHBoxLayout()                   # less-used things (moved out of the menu)
        for text, action in (("Edit app list…", lambda: __import__("launcher").edit_list()),
                             ("Forget everything…", lambda: ForgetDialog().exec()),
                             (f"About {config.APP_NAME}", lambda: AboutDialog(self.pet).exec()),
                             ("Uninstall Blip…",
                              lambda: UninstallDialog(self.pet, QApplication.instance()).exec())):
            b = QPushButton(text)
            if text.startswith("Uninstall"):
                b.setStyleSheet(DANGER)
            b.setAutoDefault(False)
            b.clicked.connect(action)
            extras.addWidget(b)
        self.root.addLayout(extras)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("Cancel"); cancel.clicked.connect(self.reject)
        save = QPushButton("Save"); save.setObjectName("primary"); save.clicked.connect(self.save)
        cancel.setAutoDefault(False)
        buttons.addWidget(cancel); buttons.addWidget(save)
        self.root.addLayout(buttons)
        self.add_credit()

    def do_prestige(self):
        import progress
        if ConfirmDialog("Prestige?", "Go back to Level 1 and earn Prestige "
                         f"{progress.get().prestige + 1}?\nYou keep all your unlocked skins and hats,\n"
                         "and get a new badge and aura forever.", yes="Prestige!", no="Not yet").exec():
            if progress.get().do_prestige():
                self.pet.celebrate_prestige()
                self.accept()

    def current_look(self):
        return self.character.currentText(), self.theme.currentText(), self.hat.currentText()

    def update_sleep_label(self):
        self.sleep_label.setText(f"{self.sleep_after.value()} min")

    def save(self):
        config.CHARACTER, config.THEME, config.HAT = self.current_look()
        config.PET_SIZE = self.size.value()
        config.WALK_SPEED = self.speed.value()
        config.BOUNCE = self.bounce.value() / 100
        config.USER_IDLE_SLEEP_SECONDS = self.sleep_after.value() * 60
        config.EYES_FOLLOW_CURSOR = self.eyes.isChecked()
        config.HIDE_IN_FULLSCREEN = self.games.isChecked()
        config.SIT_ON_WINDOWS = self.windows.isChecked()
        config.SWEAT_WHEN_BUSY = self.sweat.isChecked()
        config.SLEEPY_AT_NIGHT = self.night.isChecked()
        config.PC_HELPER = self.helper.isChecked()
        config.LISTEN_TO_MUSIC = self.music.isChecked()
        config.DANCE = self.dance.isChecked()
        config.SEASONAL = self.seasonal.isChecked()
        import progress
        progress.get().aura = self.aura.isChecked()
        progress.get().save()
        config.SOUNDS = self.sounds.currentText()
        config.AUTO_UPDATE = self.auto_update.isChecked()
        config.ASK_QUESTIONS = self.questions.isChecked()
        config.GAME_BUDDY = self.games_buddy.isChecked()
        config.ANTICS = self.antics.currentText()
        if self.startup.isChecked() != autostart.is_enabled():
            autostart.set_enabled(self.startup.isChecked())
        settings.save()
        self.pet.settings_changed()
        self.accept()


class AboutDialog(GlassDialog):
    def __init__(self, pet=None):
        import progress
        super().__init__(f"About {config.APP_NAME}")
        row = QHBoxLayout()
        row.addWidget(PetPreview(lambda: (None, None, None), 96))
        text = QLabel(f"<b>{config.APP_NAME}</b> &nbsp;v{config.VERSION} &nbsp; {progress.get().badge()}<br>"
                      f"{progress.get().title()}<br><br>"
                      "Your little desktop buddy.<br>"
                      "Everything runs on your PC. The only internet use is the<br>"
                      "daily update check, radio streams and the optional AI download.")
        row.addWidget(text)
        self.root.addLayout(row)
        buttons = QHBoxLayout(); buttons.addStretch()
        pet = pet or _PET.get("pet")
        if pet is not None:
            upd = QPushButton("Check for updates"); upd.setAutoDefault(False)
            upd.clicked.connect(lambda: (pet.check_updates(), self.accept()))
            buttons.addWidget(upd)
        close = QPushButton("Close"); close.setObjectName("primary"); close.setAutoDefault(False)
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        self.root.addLayout(buttons)
        self.add_credit()


_PET = {}


class WelcomeDialog(GlassDialog):
    """First start: your name, a character, and start with Windows."""

    def __init__(self, pet):
        super().__init__(f"Welcome to {config.APP_NAME}! 👋")
        self.pet = pet
        self.root.addWidget(QLabel(f"Hi! I'm {config.APP_NAME}, your new desktop buddy.\n"
                                   "I'll walk on your taskbar, nap, dance to your music and help you out.\n"
                                   "Right-click me any time for the menu."))
        form = QFormLayout()
        self.name = QLineEdit(); self.name.setPlaceholderText("What should I call you?")
        self.character = QComboBox(); self.character.addItems(CHARACTERS)
        self.character.setCurrentText(config.CHARACTER)
        form.addRow("Your name", self.name)
        form.addRow("Pick me", self.character)
        self.root.addLayout(form)
        self.startup = QCheckBox("Start Blip with Windows")
        self.startup.setChecked(True)
        self.root.addWidget(self.startup)
        go = QPushButton("Let's go!"); go.setObjectName("primary"); go.setAutoDefault(False)
        go.clicked.connect(self.finish)
        self.root.addWidget(go, alignment=Qt.AlignmentFlag.AlignRight)
        self.add_credit()

    def finish(self):
        import brain
        name = self.name.text().strip()
        if name:
            mem = brain.load_memory()
            mem["name"] = name[:30]
            brain.save_memory(mem)
        config.CHARACTER = self.character.currentText()
        config.FIRST_RUN_DONE = True
        if self.startup.isChecked() != autostart.is_enabled():
            autostart.set_enabled(self.startup.isChecked())
        settings.save()
        self.pet.settings_changed()
        self.pet.bubble.say("Yay!", f"Nice to meet you{', ' + name if name else ''}!", 4)
        self.accept()


# ---------------------------------------------------------------------------
# Chat (stage 5) + memory (stage 6)
# ---------------------------------------------------------------------------
import re
from PyQt6.QtCore import QObject, pyqtSignal

HELP_WORDS = re.compile(r"(pc|computer|laptop)('?s| is)? (so |really |super )?(slow|laggy|lagging|struggling|"
                        r"hot|overheating|dying)|clean ?up my|speed up my|free (up )?(some )?ram|"
                        r"boost my (pc|fps)", re.I)


def open_helper(pet):
    if getattr(pet, "helper", None) is not None:
        pet.helper.raise_()
        return
    pet.helper = HelperPanel(pet)
    pet.helper.show()


class _Relay(QObject):
    ready = pyqtSignal(object)


class HelperPanel(GlassDialog):
    """Lists the apps using the most RAM / CPU. YOU tick what to close."""

    def __init__(self, pet):
        import threading
        from PyQt6.QtWidgets import QListWidget
        super().__init__("Help my PC")
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.pet = pet
        self.status = QLabel("Checking what's using your PC…")
        self.status.setWordWrap(True)
        self.root.addWidget(self.status)
        self.list = QListWidget()
        self.list.setMinimumSize(420, 260)
        self.list.setStyleSheet("QListWidget{background:rgba(10,8,24,150);color:#EAF6FF;"
                                "border:1px solid rgba(160,110,255,110);border-radius:10px;"
                                "font:10pt 'Segoe UI';padding:4px}"
                                "QListWidget::item{padding:4px}")
        self.root.addWidget(self.list)
        note = QLabel("Only ticked apps get closed, with a polite \"please close\" (they may ask you\n"
                      "to save). Windows, antivirus, drivers, the app you're using and Blip are never listed.")
        note.setStyleSheet("color: rgba(234,246,255,150); font: 8pt 'Segoe UI';")
        self.root.addWidget(note)
        row = QHBoxLayout()
        self.free_btn = QPushButton("Free up RAM (light boost)")
        self.free_btn.clicked.connect(self.free)
        self.close_btn = QPushButton("Close ticked apps"); self.close_btn.setObjectName("primary")
        self.close_btn.clicked.connect(self.close_ticked)
        done = QPushButton("Done"); done.clicked.connect(self.close)
        buttons = [self.free_btn, self.close_btn, done]
        for b in buttons:
            b.setAutoDefault(False)
            row.addWidget(b)
        self.root.addLayout(row)
        row2 = QHBoxLayout()
        self.temp_btn = QPushButton("Clean temp files…")
        self.temp_btn.setEnabled(False)
        self.temp_btn.clicked.connect(self.clean_temp)
        self.power = QComboBox()
        self.power.setEnabled(False)
        self.power_btn = QPushButton("Switch power plan…")
        self.power_btn.setEnabled(False)
        self.power_btn.clicked.connect(self.switch_power)
        for w in (self.temp_btn, self.power, self.power_btn):
            if isinstance(w, QPushButton):
                w.setAutoDefault(False)
            row2.addWidget(w)
        self.root.addLayout(row2)
        self.add_credit()
        self.temp_mb = 0.0
        self.plans = []
        self.relay = _Relay()
        self.relay.ready.connect(self.show_apps)
        self.apps = []
        self.adjustSize()
        area = pet.current_screen().availableGeometry()
        self.move(max(area.left() + 8, min(int(pet.x_pos) - 150, area.right() - self.width() - 8)),
                  max(area.top() + 8, int(pet.y_pos) - self.height() - 6))
        threading.Thread(target=self.load, daemon=True).start()

    def load(self):
        """Each part on its own, so one failure never empties the whole panel."""
        import pchelper
        apps, ram, cpu, temps = [], 0.0, 0.0, None
        errors = []
        try:
            apps = pchelper.top_apps()
        except Exception as e:
            errors.append(f"app list: {e!r}")
        try:
            ram, cpu = pchelper.ram_cpu()     # CPU measured since top_apps() started
        except Exception as e:
            errors.append(f"RAM/CPU: {e!r}")
        try:
            import sensors
            gpu = sensors.gpu_temp()
            temps = pchelper.temperatures() or (f"GPU {gpu}°C (CPU temp needs LibreHardwareMonitor)"
                                                if gpu is not None else None)
        except Exception:
            pass
        try:
            self.temp_mb = pchelper.temp_size_mb()
        except Exception as e:
            errors.append(f"temp files: {e!r}")
        try:
            self.plans = pchelper.power_plans()
        except Exception as e:
            errors.append(f"power plans: {e!r}")
        if errors:
            print("Help my PC:", "; ".join(errors))
        self.relay.ready.emit((apps, ram, cpu, temps))

    def show_apps(self, result):
        from PyQt6.QtWidgets import QListWidgetItem
        if isinstance(result, Exception):
            self.status.setText(f"Couldn't check your PC: {result}")
            return
        self._last = result
        self.apps, ram, cpu, temps = result
        self.status.setText(f"RAM {ram:.0f}% used  ·  CPU {cpu:.0f}%  ·  "
                            + (temps or "temperature: needs LibreHardwareMonitor running"))
        self.temp_btn.setText(f"Clean temp files ({self.temp_mb:,.0f} MB)…")
        self.temp_btn.setEnabled(self.temp_mb >= 1)
        self.power.clear()
        for guid, name, active in self.plans:
            self.power.addItem(("● " if active else "") + name, guid)
            if active:
                self.power.setCurrentIndex(self.power.count() - 1)
        self.power.setEnabled(bool(self.plans))
        self.power_btn.setEnabled(bool(self.plans))
        self.list.clear()
        for app in self.apps:
            n = len(app["pids"])
            text = (f"{app['name']}  —  {app['mb']:,.0f} MB  ·  {app['cpu']:.0f}% CPU"
                    + (f"  ({n} processes)" if n > 1 else "")
                    + ("" if app["windowed"] else "  · background"))
            item = QListWidgetItem(text)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if app["suggest"] else Qt.CheckState.Unchecked)
            self.list.addItem(item)

    def close_ticked(self):
        import pchelper
        names = []
        for i, app in enumerate(self.apps):
            if self.list.item(i).checkState() == Qt.CheckState.Checked:
                pchelper.close_app(app)
                names.append(app["name"])
        self.status.setText(("Asked to close: " + ", ".join(names)) if names
                            else "Tick the apps you want closed first.")
        if names:
            self.pet.set_expr("happy", 2.0)

    def free(self):
        import pchelper
        self.status.setText("Freeing up RAM…")
        self.repaint()
        mb = pchelper.free_ram()
        ram, _ = pchelper.ram_cpu()
        self.status.setText(f"Freed about {mb:,.0f} MB (RAM now {ram:.0f}%). It's a light, "
                            "temporary boost; closing apps helps more.")
        self.pet.set_expr("happy", 2.0)

    def clean_temp(self):
        mb = self.temp_mb
        if not ConfirmDialog("Clean temp files?",
                             f"Delete about {mb:,.0f} MB of old files in your temp folder?\n"
                             "Only files older than a day; files in use are skipped.\n"
                             "Deleted files don't go to the Recycle Bin.").exec():
            return
        import pchelper
        freed = pchelper.clean_temp()
        self.temp_mb = max(0.0, mb - freed)
        self.temp_btn.setText(f"Clean temp files ({self.temp_mb:,.0f} MB)…")
        self.status.setText(f"Cleaned {freed:,.0f} MB of temp files. ✨")
        self.pet.set_expr("happy", 2.0)

    def switch_power(self):
        guid = self.power.currentData()
        name = self.power.currentText().removeprefix("● ")
        if not guid or not ConfirmDialog("Switch power plan?",
                                         f"Switch Windows to the \"{name}\" power plan?\n"
                                         "High/Ultimate performance = faster but warmer and more power.\n"
                                         "You can switch back here any time.").exec():
            return
        import pchelper
        pchelper.set_power_plan(guid)
        self.plans = pchelper.power_plans()
        active = next((n for g, n, a in self.plans if a), "?")
        self.status.setText(f"Power plan is now: {active}")
        self.show_apps((self.apps, *self._last[1:])) if hasattr(self, "_last") else None

    def closeEvent(self, e):
        self.pet.helper = None
        super().closeEvent(e)


def open_chat(pet, blip_says=None):
    if getattr(pet, "chat", None) is not None:
        if blip_says:
            pet.chat.blip_asks(blip_says)
        pet.chat.raise_()
        pet.chat.activateWindow()
        pet.chat.input.setFocus()
        return
    pet.chat = ChatWindow(pet, blip_says)
    pet.chat.show()
    pet.chat.activateWindow()
    pet.chat.input.setFocus()


class ChatWindow(GlassDialog):
    """Small chat window next to Blip. Talks to Ollama only while it's open."""

    def __init__(self, pet, blip_says=None):
        from brain import Brain, greeting
        super().__init__(f"Chat with {config.APP_NAME}")
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.pet = pet
        self.brain = Brain()
        self.brain.token.connect(self.on_token)
        self.brain.finished.connect(self.on_finished)
        self.brain.failed.connect(self.on_failed)
        self.brain.learned.connect(self.on_learned)

        close = QPushButton("✕"); close.setObjectName("close"); close.clicked.connect(self.close)
        title = self.root.takeAt(0).widget()        # move the title into a row with ✕
        title_row = QHBoxLayout()
        title_row.addWidget(title)
        title_row.addStretch(); title_row.addWidget(close)
        self.root.insertLayout(0, title_row)

        self.log = QTextBrowser()
        self.log.setOpenExternalLinks(False)
        self.log.setMinimumSize(330, 280)
        self.root.addWidget(self.log)
        row = QHBoxLayout()
        self.input = QLineEdit(); self.input.setPlaceholderText("Say something to Blip…")
        self.input.returnPressed.connect(self.send)
        self.send_btn = QPushButton("Send"); self.send_btn.setObjectName("primary")
        self.send_btn.clicked.connect(self.send)
        row.addWidget(self.input); row.addWidget(self.send_btn)
        self.root.addLayout(row)
        self.add_credit()
        # In a dialog, Enter "clicks" the default button (that was the ✕ = close!).
        for b in (close, self.send_btn):
            b.setAutoDefault(False)
            b.setDefault(False)

        self.lines = []                     # finished html lines
        self.partial = None                 # Blip's reply while it streams in
        if blip_says:
            self.blip_asks(blip_says)
        else:
            self.add("blip", greeting(self.brain.mem))
        self.adjustSize()
        self.place_near_pet()

    def place_near_pet(self):
        area = self.pet.current_screen().availableGeometry()
        x = int(self.pet.x_pos + config.PET_SIZE / 2 - self.width() / 2)
        x = max(area.left() + 8, min(x, area.right() - self.width() - 8))
        y = int(self.pet.y_pos - self.height() - 6)
        y = max(area.top() + 8, y)
        self.move(x, y)

    def add(self, who, text):
        safe = html.escape(text).replace("\n", "<br>")
        if who == "me":
            self.lines.append(f'<p align="right" style="margin:6px 0"><span style="color:#00e1ff">'
                              f'<b>You</b></span><br>{safe}</p>')
        elif who == "note":
            self.lines.append(f'<p style="margin:4px 0;color:rgba(234,246,255,140)"><i>{safe}</i></p>')
        else:
            self.lines.append(f'<p style="margin:6px 0"><span style="color:#c9a6ff">'
                              f'<b>{config.APP_NAME}</b></span><br>{safe}</p>')
        self.render()

    def render(self):
        body = "".join(self.lines)
        if self.partial is not None:
            body += (f'<p style="margin:6px 0"><span style="color:#c9a6ff"><b>{config.APP_NAME}</b>'
                     f'</span><br>{html.escape(self.partial or "…")}</p>')
        self.log.setHtml(body)
        bar = self.log.verticalScrollBar()
        bar.setValue(bar.maximum())

    def send(self):
        text = self.input.text().strip()
        if not text or self.brain.busy:
            return
        self.input.clear()
        self.add("me", text)
        __import__("extras").cheer("chat")
        __import__("extras").cheer("first_chat")
        import re as _re
        fm = _re.search(r"\bfocus\b(?:\s+(?:for\s+)?(\d+)\s*(?:min|mins|minutes|m)?)?", text, _re.I)
        if fm and _re.search(r"\b(focus for|focus mode|let'?s focus|start focus|focus \d)", text, _re.I):
            mins = int(fm.group(1) or 25)
            self.pet.start_focus(max(1, min(mins, 180)))
            self.add("blip", f"Focus mode on for {mins} minutes 🎯 I'll stay quiet and tell you when it's break time.")
            return
        radio = self.radio_command(text)
        if radio:
            self.add("blip", radio)
            return
        bday = self.birthday_command(text)
        if bday:
            self.add("blip", bday)
            return
        import buddy
        local = buddy.handle_chat(text)            # reminders, to-do list, game stats
        if local and local.startswith("Nice one!"):
            __import__("extras").cheer("reminder")  # ticked off a to-do: XP
        if local:
            self.add("blip", local)
            self.pet.schedule_reminders()
            return
        self.open_app_for(text)
        if HELP_WORDS.search(text):
            self.add("note", "🧹 Opening the PC helper: tick what you want closed, nothing closes by itself.")
            open_helper(self.pet)
        self.partial = ""
        self.render()
        self.send_btn.setEnabled(False)
        self.brain.send(text)

    def open_app_for(self, text):
        """'I'm going to play Call of Duty' -> open it (only apps in apps.json)."""
        import launcher
        try:
            app = launcher.match(text)
            if app is None:
                return
            launcher.launch(app)
            __import__("extras").cheer("launch")
            self.add("note", f"🚀 Opening {app['name']}… {app.get('say', '')}")
            self.pet.set_expr("happy", 2.5)
            self.pet.jump()
        except Exception as e:
            self.add("note", f"Couldn't open that app: {e}")

    def birthday_command(self, text):
        import re, progress
        months = ["january", "february", "march", "april", "may", "june", "july", "august",
                  "september", "october", "november", "december"]
        if not re.search(r"birthday|born on|b-?day", text, re.I):
            return None
        low = text.lower()
        m = next((i + 1 for i, name in enumerate(months) if name in low or name[:3] + " " in low + " "), None)
        d = re.search(r"\b(\d{1,2})(st|nd|rd|th)?\b", low)
        if not m or not d or not 1 <= int(d.group(1)) <= 31:
            return None
        prog = progress.get()
        prog.birthday = f"{m:02d}-{int(d.group(1)):02d}"
        prog.save()
        return f"Saved! 🎂 {int(d.group(1))} {months[m - 1].title()}. I'll throw you a party that day!"

    def radio_command(self, text):
        """'play some radio', 'play chill radio', 'stop the radio'"""
        import re
        m = self.pet.music
        if re.search(r"\b(stop|turn off|switch off)\b.*\bradio\b", text, re.I):
            m.radio_stop()
            return "Radio off 📻 Back to the quiet life."
        if re.search(r"\b(play|put on|start|turn on|switch on)\b.*\bradio\b", text, re.I):
            station = m.find_station(text)
            m.radio_play(station)
            open_radio(self.pet)
            return f"📻 Tuning in to {m.station['name']} ({m.station['genre']})!"
        return None

    def blip_asks(self, question):
        """Blip starts the conversation (from a question bubble)."""
        self.add("blip", question)
        self.brain.mem["history"].append({"role": "assistant", "content": question})

    def on_token(self, piece):
        if self.partial is not None:
            self.partial += piece
            self.render()

    def on_finished(self, reply):
        self.partial = None
        self.add("blip", reply)
        self.send_btn.setEnabled(True)
        self.pet.set_expr("happy", 1.5)

    def on_failed(self, msg):
        self.partial = None
        self.add("blip", msg)
        self.send_btn.setEnabled(True)
        if ("brain" in msg or "Ollama" in msg) and not getattr(self, "brain_help", None):
            self.show_brain_help()

    def show_brain_help(self):
        """No AI yet: the built-in commands still work; offer to set up the AI (never automatic)."""
        import shutil
        self.add("note", "I can still do reminders, lists, apps, radio, focus and your game stats "
                         "without my AI brain. For free chatting, I need Ollama (free) + a 2 GB brain.")
        row = QHBoxLayout()
        get = QPushButton("Get Ollama"); get.setAutoDefault(False)
        get.clicked.connect(lambda: __import__("webbrowser").open("https://ollama.com/download"))
        dl = QPushButton("Download Blip's brain (2 GB)"); dl.setAutoDefault(False)
        dl.setEnabled(shutil.which("ollama") is not None)
        if not dl.isEnabled():
            dl.setToolTip("Install Ollama first")
        dl.clicked.connect(self.download_brain)
        row.addWidget(get); row.addWidget(dl)
        self.root.insertLayout(self.root.count() - 1, row)
        self.brain_help = (get, dl)

    def download_brain(self):
        from PyQt6.QtCore import QProcess
        from brain import PREFERRED_MODELS
        self.brain_help[1].setEnabled(False)
        self.pull = QProcess(self)
        self.pull.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.pull.readyRead.connect(self.pull_progress)
        self.pull.finished.connect(lambda code, *_: self.add(
            "note", "Brain downloaded! Say hi to me 😊" if code == 0 else "The download didn't finish. Try again later."))
        self.pull.start("ollama", ["pull", PREFERRED_MODELS[0]])
        self.add("note", "Downloading my brain… (about 2 GB, this can take a while)")

    def pull_progress(self):
        import re
        text = bytes(self.pull.readAll()).decode("utf-8", "replace")
        pct = re.findall(r"(\d+)%", text)
        if pct:
            self.setWindowTitle(f"Chat with Blip: downloading {pct[-1]}%")
            if self.lines and "Downloading my brain" in self.lines[-1]:
                self.lines.pop()
            self.add("note", f"Downloading my brain… {pct[-1]}%")

    def on_learned(self, fact):
        self.add("note", f"💡 Blip will remember: {fact}")

    def keyPressEvent(self, e):
        """Enter sends (handled by the text box); never let it close the chat."""
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.send()
            return
        if e.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(e)

    def closeEvent(self, e):
        self.pet.chat = None
        super().closeEvent(e)


class ForgetDialog(GlassDialog):
    def __init__(self):
        super().__init__("Forget everything?")
        self.root.addWidget(QLabel(f"{config.APP_NAME} will forget your name, everything it\n"
                                   "learned about you and your past chats.\nThis can't be undone."))
        row = QHBoxLayout(); row.addStretch()
        cancel = QPushButton("Cancel"); cancel.clicked.connect(self.reject)
        ok = QPushButton("Forget"); ok.setObjectName("primary"); ok.clicked.connect(self.forget)
        row.addWidget(cancel); row.addWidget(ok)
        self.root.addLayout(row)
        self.add_credit()

    def forget(self):
        from brain import forget_everything
        forget_everything()
        self.accept()


class ConfirmDialog(GlassDialog):
    """Yes / No box. Nothing happens unless you press Yes."""

    def __init__(self, title, text, yes="Yes", no="No"):
        super().__init__(title)
        self.root.addWidget(QLabel(text))
        row = QHBoxLayout(); row.addStretch()
        b_no = QPushButton(no); b_no.clicked.connect(self.reject)
        b_yes = QPushButton(yes); b_yes.setObjectName("primary"); b_yes.clicked.connect(self.accept)
        for b in (b_no, b_yes):
            b.setAutoDefault(False)
            row.addWidget(b)
        self.root.addLayout(row)
        self.add_credit()


class UninstallDialog(GlassDialog):
    """Confirm first, then uninstall: start-up entry, (optionally) data and AI model,
    and the installed app folder once Blip has closed."""

    def __init__(self, pet, app):
        import uninstall
        super().__init__(f"Uninstall {config.APP_NAME}?")
        self.pet, self.app = pet, app
        self.root.addWidget(QLabel(f"This removes {config.APP_NAME} from your PC."))
        self.data = QCheckBox(f"Also delete {config.APP_NAME}'s memory and settings")
        self.data.setChecked(True)
        self.model = QCheckBox(f"Also remove {config.APP_NAME}'s AI model ({uninstall.MODEL}, about 2 GB)")
        self.model.setChecked(False)
        self.root.addWidget(self.data)
        self.root.addWidget(self.model)
        folder = uninstall.app_folder()
        note = QLabel("Other apps that use Ollama might use that model too.\n"
                      + (f"App folder to delete: {folder}" if folder else
                         "Running from the code files: the app folder won't be deleted.")
                      + "\nYour code folder is never deleted.")
        note.setStyleSheet("color: rgba(234,246,255,150); font: 8pt 'Segoe UI';")
        self.root.addWidget(note)
        row = QHBoxLayout(); row.addStretch()
        cancel = QPushButton("Cancel"); cancel.clicked.connect(self.reject)
        go = QPushButton("Uninstall"); go.setStyleSheet(DANGER); go.clicked.connect(self.go)
        for b in (cancel, go):
            b.setAutoDefault(False)
            row.addWidget(b)
        self.root.addLayout(row)
        self.add_credit()

    def go(self):
        import uninstall
        from brain import load_memory
        name = load_memory().get("name")
        uninstall.run(self.data.isChecked(), self.model.isChecked())
        self.accept()
        self.pet.bubble.say("Goodbye 👋", f"Bye {name}! 👋" if name else "Bye! 👋", 3)
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(2500, self.app.quit)


DANGER = ("QPushButton{background:rgba(255,60,90,170);border:1px solid rgba(255,120,140,220);"
          "color:white;border-radius:8px;padding:7px 18px;font:10pt 'Segoe UI'}"
          "QPushButton:hover{background:rgba(255,60,90,230)}")


# ---------------------------------------------------------------------------
# Mini radio
# ---------------------------------------------------------------------------
def open_radio(pet):
    if getattr(pet, "radio_panel", None) is not None:
        pet.radio_panel.raise_()
        return
    pet.radio_panel = RadioPanel(pet)
    pet.radio_panel.show()


class RadioPanel(GlassDialog):
    """Pick a station; Blip's helper plays it. Closing this panel keeps the music on."""

    def __init__(self, pet):
        from PyQt6.QtWidgets import QListWidget
        super().__init__(f"{config.APP_NAME} Radio 📻")
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.pet, self.m = pet, pet.music
        self.now = QLabel(); self.now.setWordWrap(True)
        self.root.addWidget(self.now)
        self.list = QListWidget()
        self.list.setMinimumSize(300, 220)
        self.list.setStyleSheet("QListWidget{background:rgba(10,8,24,150);color:#EAF6FF;"
                                "border:1px solid rgba(160,110,255,110);border-radius:10px;"
                                "font:10pt 'Segoe UI';padding:4px}"
                                "QListWidget::item{padding:5px}"
                                "QListWidget::item:selected{background:rgba(0,225,255,60)}")
        for s in self.m.get_stations():
            self.list.addItem(f"{s['name']}  ·  {s['genre']}")
        self.list.itemDoubleClicked.connect(lambda _: self.play_selected())
        self.root.addWidget(self.list)
        row = QHBoxLayout()
        self.play_btn = QPushButton("▶ Play"); self.play_btn.setObjectName("primary")
        self.play_btn.clicked.connect(self.play_pause)
        nxt = QPushButton("⏭ Next"); nxt.clicked.connect(self.m.radio_next)
        stop = QPushButton("⏹ Stop"); stop.clicked.connect(self.m.radio_stop)
        for b in (self.play_btn, nxt, stop):
            b.setAutoDefault(False)
            row.addWidget(b)
        self.root.addLayout(row)
        vol = QHBoxLayout()
        vol.addWidget(QLabel("🔊"))
        self.vol = slider(0, 100, config.RADIO_VOLUME)
        self.vol.valueChanged.connect(self.m.set_volume)
        vol.addWidget(self.vol)
        self.root.addLayout(vol)
        close = QPushButton("Close"); close.setAutoDefault(False); close.clicked.connect(self.close)
        self.root.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)
        self.add_credit()
        self.m.radio_changed.connect(self.refresh)
        self.refresh()
        self.adjustSize()
        area = pet.current_screen().availableGeometry()
        self.move(max(area.left() + 8, min(int(pet.x_pos) - 100, area.right() - self.width() - 8)),
                  max(area.top() + 8, int(pet.y_pos) - self.height() - 6))

    def play_selected(self):
        row = self.list.currentRow()
        if row >= 0:
            self.m.radio_play(self.m.get_stations()[row])

    def play_pause(self):
        if self.m.radio_on:
            self.m.play_pause()
        elif self.list.currentRow() >= 0:
            self.play_selected()
        else:
            self.m.radio_play()

    def refresh(self):
        m = self.m
        if m.radio_on and m.station:
            names = [s["name"] for s in m.get_stations()]
            if m.station["name"] in names:
                self.list.setCurrentRow(names.index(m.station["name"]))
            state = "▶ Playing" if m.radio_playing else "⏸ Paused / connecting…"
            song = f"\n♪ {m.radio_song}" if m.radio_song else ""
            err = f"\n⚠ {m.radio_error}" if m.radio_error else ""
            self.now.setText(f"{state}: {m.station['name']}{song}{err}")
            self.play_btn.setText("⏸ Pause" if m.radio_playing else "▶ Play")
        else:
            self.now.setText("Pick a station and press Play (or double-click it).")
            self.play_btn.setText("▶ Play")

    def closeEvent(self, e):
        try:
            self.m.radio_changed.disconnect(self.refresh)
        except TypeError:
            pass
        settings.save()                         # remember station + volume
        self.pet.radio_panel = None
        super().closeEvent(e)



# ---------------------------------------------------------------------------
# Skins picker
# ---------------------------------------------------------------------------
class SkinsDialog(GlassDialog):
    def __init__(self, pet):
        from PyQt6.QtWidgets import QGridLayout, QToolButton
        from PyQt6.QtGui import QIcon, QPixmap
        from PyQt6.QtCore import QSize
        import progress, skins
        super().__init__("Skins")
        self.pet = pet
        self.prog = progress.get()
        self.preview = PetPreview(lambda: (None, None, None), 110)
        self.root.addWidget(self.preview, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.info = QLabel(f"Wearing: {self.prog.skin}")
        self.root.addWidget(self.info, alignment=Qt.AlignmentFlag.AlignHCenter)
        grid = QGridLayout(); grid.setSpacing(6)
        for i, (name, _) in enumerate(skins.SKINS):
            pix = QPixmap(64, 64); pix.fill(Qt.GlobalColor.transparent)
            p = QPainter(pix)
            ok = skins.unlocked(name, self.prog)
            if not ok:
                p.setOpacity(0.3)
            draw_pet(p, 64, "idle", 1.0, skin=name, hat="None")
            p.end()
            b = QToolButton()
            b.setIcon(QIcon(pix)); b.setIconSize(QSize(56, 56))
            b.setText(name if ok else f"🔒 {skins.lock_text(name)}")
            b.setToolTip(name if ok else f"{name}: unlocks at {skins.lock_text(name)}")
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            b.setFixedSize(96, 92)
            b.setEnabled(ok)
            b.setStyleSheet("QToolButton{color:#EAF6FF;font:8pt 'Segoe UI';background:rgba(255,255,255,12);"
                            "border:1px solid rgba(160,110,255,90);border-radius:8px}"
                            "QToolButton:hover{background:rgba(0,225,255,50)}")
            b.clicked.connect(lambda _=False, n=name: self.pick(n))
            grid.addWidget(b, i // 6, i % 6)
        self.root.addLayout(grid)
        close = QPushButton("Done"); close.setObjectName("primary"); close.setAutoDefault(False)
        close.clicked.connect(self.accept)
        self.root.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)
        self.add_credit()

    def pick(self, name):
        self.prog.skin = name
        self.prog.save()
        self.info.setText(f"Wearing: {name}")
        self.preview.update()
        self.pet.update()
        if self.pet.after_settings:
            self.pet.after_settings()


# ---------------------------------------------------------------------------
# Glass progress bar + Prestige Shop
# ---------------------------------------------------------------------------
class GlassBar(QWidget):
    """Rounded bar: dark track, purple-to-cyan (or pink) gradient fill, text inside."""

    def __init__(self, frac, text, width=180, pink=False):
        super().__init__()
        self.frac, self.text, self.pink = max(0.0, min(1.0, frac)), text, pink
        self.setFixedSize(width, 18)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QPen(QColor(160, 110, 255, 120), 1))
        p.setBrush(QColor(12, 8, 30, 220))
        p.drawRoundedRect(r, 9, 9)
        if self.frac > 0:
            g = QLinearGradient(r.topLeft(), r.topRight())
            if self.pink:
                g.setColorAt(0, QColor(255, 90, 170)); g.setColorAt(1, QColor(255, 200, 120))
            else:
                g.setColorAt(0, QColor(154, 90, 255)); g.setColorAt(1, QColor(0, 225, 255))
            p.setPen(Qt.PenStyle.NoPen); p.setBrush(QBrush(g))
            p.drawRoundedRect(QRectF(r.left() + 1, r.top() + 1, max(16, (r.width() - 2) * self.frac), r.height() - 2), 8, 8)
            p.setBrush(QColor(255, 255, 255, 40))
            p.drawRoundedRect(QRectF(r.left() + 3, r.top() + 2, max(10, (r.width() - 6) * self.frac), 5), 3, 3)
        p.setPen(QColor(245, 250, 255))
        from PyQt6.QtGui import QFont
        f = QFont("Segoe UI", 8); f.setBold(True); p.setFont(f)
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, self.text)
        p.end()


class ShopDialog(GlassDialog):
    def __init__(self, pet):
        from PyQt6.QtWidgets import QGridLayout, QToolButton, QTabWidget
        from PyQt6.QtGui import QIcon, QPixmap
        from PyQt6.QtCore import QSize
        import progress, shop
        super().__init__("Prestige Shop")
        self.pet, self.prog = pet, progress.get()
        self.tokens = QLabel()
        self.root.addWidget(self.tokens)
        self.root.addWidget(QLabel("Earn tokens: 3 per prestige, 1 for every 10 levels, 1 per weekly challenge."))
        tabs = QTabWidget()
        tabs.setStyleSheet("QTabWidget::pane{border:1px solid rgba(160,110,255,90);border-radius:8px}"
                           "QTabBar::tab{background:rgba(255,255,255,14);color:#EAF6FF;padding:6px 12px;"
                           "border-top-left-radius:6px;border-top-right-radius:6px;font:9pt 'Segoe UI'}"
                           "QTabBar::tab:selected{background:rgba(0,225,255,60)}")
        self.buttons = {}
        for slot in shop.SLOTS:
            page = QWidget(); grid = QGridLayout(page); grid.setSpacing(6)
            items = [n for n, v in shop.ITEMS.items() if v[0] == slot]
            for i, name in enumerate(items):
                b = QToolButton()
                b.setIcon(QIcon(self.preview_pix(name, slot))); b.setIconSize(QSize(56, 56))
                b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
                b.setFixedSize(112, 96)
                b.setStyleSheet("QToolButton{color:#EAF6FF;font:8pt 'Segoe UI';background:rgba(255,255,255,12);"
                                "border:1px solid rgba(160,110,255,90);border-radius:8px}"
                                "QToolButton:hover{background:rgba(0,225,255,50)}"
                                "QToolButton:disabled{color:rgba(234,246,255,90)}")
                b.clicked.connect(lambda _=False, n=name: self.click(n))
                grid.addWidget(b, i // 4, i % 4)
                self.buttons[name] = b
            tabs.addTab(page, shop.SLOT_NAMES[slot])
        self.root.addWidget(tabs)
        close = QPushButton("Done"); close.setObjectName("primary"); close.setAutoDefault(False)
        close.clicked.connect(self.accept)
        self.root.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)
        self.add_credit()
        self.refresh()

    def preview_pix(self, name, slot):
        from PyQt6.QtGui import QPixmap
        pix = QPixmap(64, 64); pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        gear = {k: v for k, v in self.prog.equipped.items()}
        hat = "None"
        if slot == "hat":
            hat = name
        elif slot in ("glasses", "extra", "trail"):
            gear = {slot: name}
        draw_pet(p, 64, "walk" if slot == "trail" else "idle", 1.0, hat=hat, gear=gear, skin="None")
        if slot == "trail":
            import shop
            shop.draw_trail(p, name, 64, 1.0, 1, True)
        p.end()
        return pix

    def state(self, name):
        import shop
        slot, price, need = shop.ITEMS[name]
        if name in self.prog.owned:
            on = (config.HAT == name) if slot == "hat" else (self.prog.equipped.get(slot) == name)
            return "equipped" if on else "owned"
        if self.prog.prestige < need:
            return f"Prestige {need}"
        return f"{price} token" + ("s" if price != 1 else "")

    def refresh(self):
        self.tokens.setText(f"<b>Prestige Tokens: {self.prog.tokens}</b>")
        for name, b in self.buttons.items():
            st = self.state(name)
            label = {"equipped": "✔ Equipped", "owned": "Equip"}.get(st, st)
            b.setText(f"{name}\n{label}")
            b.setEnabled(not st.startswith("Prestige"))

    def click(self, name):
        import shop
        slot, price, need = shop.ITEMS[name]
        st = self.state(name)
        if st == "equipped":                                # take it off
            if slot == "hat":
                config.HAT = "None"
            elif slot != "emote":
                self.prog.equipped.pop(slot, None)
        elif st == "owned":
            if slot == "hat":
                config.HAT = name
            elif slot == "emote":
                self.pet.trick("emote:" + name)
            else:
                self.prog.equipped[slot] = name
        else:
            if self.prog.tokens < price:
                self.pet.bubble.say("Prestige Shop", f"You need {price} tokens for that ({self.prog.tokens} now).", 4)
                return
            if not ConfirmDialog("Buy?", f"Buy {name} for {price} token{'s' if price != 1 else ''}?",
                                 yes="Buy", no="Cancel").exec():
                return
            if self.prog.buy(name):
                if slot == "hat":
                    config.HAT = name
                elif slot != "emote":
                    self.prog.equipped[slot] = name
                __import__("extras").play("yay")
        self.prog.save()
        settings.save()
        self.pet.update()
        if self.pet.after_settings:
            self.pet.after_settings()
        self.refresh()
