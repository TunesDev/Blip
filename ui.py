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
    pcm = glass_menu(menu)
    pcm.setTitle("Power && night light")
    pcm.addAction("Power saver", lambda: pet.set_power_mode("saver"))
    pcm.addAction("Balanced", lambda: pet.set_power_mode("balanced"))
    pcm.addAction("High performance", lambda: pet.set_power_mode("high"))
    pcm.addSeparator()
    nl_on = pcm.addAction("Night light on", lambda: pet.set_night_light("On"))
    nl_sched = pcm.addAction("Night light on a schedule", lambda: pet.set_night_light("Schedule"))
    nl_off = pcm.addAction("Night light off", lambda: pet.set_night_light("Off"))
    menu.addMenu(pcm)

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
    play.addAction("Snack catch (mini-game)", lambda: pet.trick("snackgame"))
    play.addAction("Prestige Shop…", lambda: ShopDialog(pet).exec())
    play.addAction("Trophies…", lambda: TrophyDialog().exec())
    play.addAction("Surprise me!", lambda: pet.trick())
    play.addSeparator()
    focus_action = play.addAction("Focus 25 min", lambda: pet.stop_focus() if extras.focus_left() else pet.start_focus(25))
    menu.addMenu(play)

    menu.addSeparator()
    hide = glass_menu(menu)
    hide.setTitle("Hide Blip")
    hide.addAction("For 15 minutes", lambda: pet.hide_for(15 * 60))
    hide.addAction("For 1 hour", lambda: pet.hide_for(3600))
    hide.addAction("For 3 hours", lambda: pet.hide_for(3 * 3600))
    hide.addAction("Until I bring him back", lambda: pet.hide_for(None))
    menu.addMenu(hide)
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
        more = QPushButton("More options…"); more.setAutoDefault(False)
        more.clicked.connect(lambda: MoreOptionsDialog(self.pet).exec())
        lvl.addWidget(more)
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
        ticked = [a["name"] for i, a in enumerate(self.apps)
                  if self.list.item(i).checkState() == Qt.CheckState.Checked and not a["windowed"]]
        if ticked:
            config.BOOST_APPS = sorted(set(config.BOOST_APPS) | set(ticked))[:10]
            settings.save()
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
        import re as _r
        hm = _r.search(r"\bhide\b.*?\bfor\b\s*(an?|\d+)\s*(min|minute|minutes|hour|hours|hr|h)\b", text, _r.I)
        if hm:
            n = 1 if hm.group(1).lower() in ("a", "an") else int(hm.group(1))
            secs = n * (3600 if hm.group(2).lower().startswith("h") else 60)
            self.add("blip", f"Okay, see you in {n} {'hour' if secs >= 3600 and n == 1 else hm.group(2)}! Right-click the tray icon to bring me back sooner.")
            QTimer.singleShot(1200, lambda: (self.close(), self.pet.hide_for(secs)))
            return
        pc = self.pc_command(text)
        if pc:
            self.add("blip", pc)
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
        self.last_text = text
        if not config.AI_CHAT:                          # AI chat switched off: built-in answers only
            self.partial = None
            self.render()
            self.add("blip", self.offline_answer(text))
            return
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

    def pc_command(self, text):
        """'power saving mode', 'balanced', 'game mode', 'night light on/off'"""
        import re
        low = text.lower()
        if re.search(r"night ?light", low):
            if re.search(r"\b(off|stop|disable)\b", low):
                self.pet.set_night_light("Off"); return "Night light off."
            if re.search(r"schedul|every night|automatic", low):
                self.pet.set_night_light("Schedule")
                return f"Night light will turn on at {config.NIGHT_LIGHT_FROM}:00 and off at {config.NIGHT_LIGHT_TO:02d}:00."
            self.pet.set_night_light("On"); return "Night light on. Easier on your eyes tonight."
        which = ("saver" if re.search(r"power sav|battery sav|eco mode|save power", low) else
                 "high" if re.search(r"high performance|game mode|performance mode|max power", low) else
                 "balanced" if re.search(r"\bbalanced\b", low) else None)
        if which:
            name = self.pet.set_power_mode(which)
            return f"Switched to {name}." if name else "Hmm, that power plan isn't on this PC."
        return None

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
        self.send_btn.setEnabled(True)
        if msg == "NO_BRAIN":
            self.add("blip", self.offline_answer(getattr(self, "last_text", "")))
            self.show_brain_help()
        else:
            self.add("blip", msg)

    CAN_DO = ("Here's what I can do right now:\n"
              "• \"remind me in 20 min to check the oven\"  • \"add milk to my list\"\n"
              "• \"play some radio\" / \"play chill radio\"  • \"focus for 25 min\"\n"
              "• \"I'm going to play CoD\" (opens your apps)  • \"how am I doing?\" (game stats)\n"
              "• \"power saving mode\"  • \"night light on\"  • \"hide for an hour\"")

    def offline_answer(self, text):
        """No AI brain: still answer the common things helpfully."""
        import re
        low = (text or "").lower()
        if re.search(r"music|song|listen|tunes|radio", low):
            QTimer.singleShot(400, lambda: open_radio(self.pet))
            return "I've got real radio stations! 📻 I opened my radio: pick one, or say \"play chill radio\"."
        if re.search(r"what can you do|help|commands|how do (i|you)", low):
            return self.CAN_DO
        if re.search(r"\b(hi|hello|hey|yo|sup)\b", low):
            return "Hey! 👋 " + self.CAN_DO
        return "I can't chat about everything yet. For that I need my AI brain (free, set it up below). " + self.CAN_DO

    def show_brain_help(self):
        """One-click AI setup card (nothing downloads until you press the button)."""
        if not config.AI_CHAT or getattr(self, "brain_help", None):
            return
        import aisetup
        need_ollama = aisetup.ollama_exe() is None
        box = QWidget()
        box.setStyleSheet("QWidget#card{background:rgba(255,255,255,14);border:1px solid rgba(160,110,255,110);"
                          "border-radius:10px}")
        box.setObjectName("card")
        lay = QVBoxLayout(box); lay.setContentsMargins(10, 8, 10, 8)
        self.setup_label = QLabel("Turn on chatting? I need Ollama (free)" + (" and" if need_ollama else ":") +
                                  " my brain: a 2 GB download (about 2 GB of disk space).")
        self.setup_label.setWordWrap(True)
        lay.addWidget(self.setup_label)
        self.setup_bar = GlassBar(0, "", 320); self.setup_bar.hide()
        lay.addWidget(self.setup_bar)
        row = QHBoxLayout()
        self.setup_go = QPushButton("Set it up for me"); self.setup_go.setObjectName("primary")
        self.setup_go.setAutoDefault(False); self.setup_go.clicked.connect(self.run_setup)
        self.setup_cancel = QPushButton("Cancel"); self.setup_cancel.setAutoDefault(False); self.setup_cancel.hide()
        link = QPushButton("Get Ollama myself"); link.setAutoDefault(False)
        link.clicked.connect(lambda: __import__("webbrowser").open("https://ollama.com/download"))
        row.addWidget(self.setup_go); row.addWidget(self.setup_cancel); row.addWidget(link); row.addStretch()
        lay.addLayout(row)
        self.root.insertWidget(self.root.count() - 2, box)
        self.brain_help = box
        self.adjustSize()

    def run_setup(self):
        import aisetup
        self.setup = aisetup.Setup()
        self.setup.progress.connect(self.setup_progress)
        self.setup.finished.connect(self.setup_done)
        self.setup_cancel.clicked.connect(self.setup.cancel)
        self.setup_go.setEnabled(False); self.setup_cancel.show(); self.setup_bar.show()
        self.setup.start()

    def setup_progress(self, msg, frac):
        self.setup_label.setText(msg)
        self.setup_bar.frac = max(0.0, frac) if frac >= 0 else 0.0
        self.setup_bar.text = f"{frac * 100:.0f}%" if frac >= 0 else "…"
        self.setup_bar.update()

    def setup_done(self, ok, msg):
        self.setup_cancel.hide()
        self.setup_label.setText(msg)
        if ok:
            self.setup_bar.frac, self.setup_bar.text = 1.0, "Done"
            self.setup_bar.update()
            self.brain.model = None
            self.add("blip", msg)
            self.setup_go.hide()
        else:
            self.setup_go.setText("Retry"); self.setup_go.setEnabled(True)

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
    """Blip Radio: now playing, controls, volume + mute, stations / favourites / recent / search."""

    TAB_STYLE = ("QTabWidget::pane{border:1px solid rgba(160,110,255,90);border-radius:8px}"
                 "QTabBar::tab{background:rgba(255,255,255,14);color:#EAF6FF;padding:6px 12px;"
                 "border-top-left-radius:6px;border-top-right-radius:6px;font:9pt 'Segoe UI'}"
                 "QTabBar::tab:selected{background:rgba(0,225,255,60)}")
    LIST_STYLE = ("QListWidget{background:rgba(10,8,24,150);color:#EAF6FF;border:none;"
                  "font:10pt 'Segoe UI';padding:4px}QListWidget::item{padding:6px;border-radius:6px}"
                  "QListWidget::item:selected{background:rgba(0,225,255,60)}"
                  "QListWidget::item:hover{background:rgba(255,255,255,18)}")

    def __init__(self, pet):
        from PyQt6.QtWidgets import QTabWidget
        super().__init__(f"{config.APP_NAME} Radio")
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.pet, self.m = pet, pet.music
        # --- now playing card
        self.card = NowPlayingCard()
        self.root.addWidget(self.card)
        # --- controls
        row = QHBoxLayout()
        self.prev_btn = self.round_btn("⏮", lambda: self.m.radio_next(-1))
        self.play_btn = self.round_btn("▶", self.play_pause, big=True)
        self.next_btn = self.round_btn("⏭", lambda: self.m.radio_next(1))
        self.stop_btn = self.round_btn("⏹", self.m.radio_stop)
        self.fav_btn = self.round_btn("☆", self.toggle_fav)
        self.fav_btn.setToolTip("Add to favourites")
        for b in (self.prev_btn, self.play_btn, self.next_btn, self.stop_btn, self.fav_btn):
            row.addWidget(b)
        row.addSpacing(10)
        self.mute_btn = self.round_btn("🔊", self.toggle_mute)
        row.addWidget(self.mute_btn)
        self.vol = slider(0, 100, config.RADIO_VOLUME)
        self.vol.setMinimumWidth(130)
        self.vol.valueChanged.connect(self.volume_changed)
        row.addWidget(self.vol)
        self.vol_label = QLabel(f"{config.RADIO_VOLUME}%"); self.vol_label.setFixedWidth(36)
        row.addWidget(self.vol_label)
        self.root.addLayout(row)
        # --- tabs
        self.tabs = QTabWidget(); self.tabs.setStyleSheet(self.TAB_STYLE)
        self.lists = {}
        for key, title in (("stations", "Stations"), ("favourites", "Favourites"), ("recent", "Recent")):
            lw = self.make_list()
            self.lists[key] = lw
            self.tabs.addTab(lw, title)
        self.tabs.addTab(self.make_search(), "Search")
        self.tabs.setMinimumSize(420, 260)
        self.root.addWidget(self.tabs)
        close = QPushButton("Close"); close.setAutoDefault(False); close.clicked.connect(self.close)
        self.root.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)
        self.add_credit()
        self.fill_lists()
        self.m.radio_changed.connect(self.refresh)
        self.refresh()
        self.adjustSize()
        area = pet.current_screen().availableGeometry()
        self.move(max(area.left() + 8, min(int(pet.x_pos) - 150, area.right() - self.width() - 8)),
                  max(area.top() + 8, int(pet.y_pos) - self.height() - 6))

    # ---- building blocks
    def round_btn(self, text, fn, big=False):
        b = QPushButton(text); b.setAutoDefault(False)
        size = 46 if big else 34
        b.setFixedSize(size, size)
        b.setStyleSheet("QPushButton{border-radius:%dpx;font:%dpt 'Segoe UI Symbol';padding:0;%s}"
                        "QPushButton:hover{background:rgba(0,225,255,70)}" % (
                            size // 2, 15 if big else 11,
                            "background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #9a5aff,stop:1 #00e1ff);"
                            "border:none;color:white" if big else ""))
        b.clicked.connect(fn)
        return b

    def make_list(self):
        from PyQt6.QtWidgets import QListWidget
        lw = QListWidget(); lw.setStyleSheet(self.LIST_STYLE)
        lw.itemDoubleClicked.connect(lambda it: self.play_item(it))
        return lw

    def make_search(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setContentsMargins(6, 6, 6, 6)
        row = QHBoxLayout()
        self.q = QLineEdit(); self.q.setPlaceholderText("Station name (e.g. FM104, Spin, Capital)…")
        self.q.returnPressed.connect(self.do_search)
        self.country = QComboBox()
        for label, code in (("Any country", ""), ("Ireland", "IE"), ("UK", "GB"), ("USA", "US"), ("Canada", "CA"),
                            ("Australia", "AU"), ("Germany", "DE"), ("France", "FR"), ("Spain", "ES"), ("Netherlands", "NL")):
            self.country.addItem(label, code)
        self.genre = QComboBox()
        for g in ("Any genre", "pop", "dance", "rock", "hip hop", "chillout", "jazz", "classical", "country",
                  "80s", "90s", "talk", "news"):
            self.genre.addItem(g)
        go = QPushButton("Search"); go.setObjectName("primary"); go.setAutoDefault(False); go.clicked.connect(self.do_search)
        row.addWidget(self.q); row.addWidget(self.country); row.addWidget(self.genre); row.addWidget(go)
        lay.addLayout(row)
        self.results = self.make_list()
        lay.addWidget(self.results)
        self.search_status = QLabel("Search thousands of real stations from around the world.")
        self.search_status.setStyleSheet("color: rgba(234,246,255,150); font: 8pt 'Segoe UI';")
        lay.addWidget(self.search_status)
        return page

    def add_stations(self, lw, stations, group=False):
        from PyQt6.QtWidgets import QListWidgetItem
        lw.clear()
        last = None
        for s_ in stations:
            if group and s_.get("country") != last:
                last = s_.get("country")
                head = QListWidgetItem(f"  {last}")
                head.setFlags(Qt.ItemFlag.NoItemFlags)
                head.setForeground(QColor(0, 225, 255))
                lw.addItem(head)
            star = "★ " if self.m.is_favourite(s_) else ""
            it = QListWidgetItem(f"{star}{s_['name']}    ·  {s_.get('genre', '')}"
                                 + ("" if group else f"  ·  {s_.get('country', '')}"))
            it.setData(Qt.ItemDataRole.UserRole, s_)
            lw.addItem(it)
        if not stations:
            empty = QListWidgetItem("  Nothing here yet.")
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            lw.addItem(empty)

    def fill_lists(self):
        self.add_stations(self.lists["stations"], self.m.get_stations(), group=True)
        self.add_stations(self.lists["favourites"], self.m.favourites())
        self.add_stations(self.lists["recent"], self.m.recent())

    # ---- actions
    def play_item(self, it):
        st = it.data(Qt.ItemDataRole.UserRole)
        if st:
            lw = it.listWidget()
            self.m.play_list = [lw.item(i).data(Qt.ItemDataRole.UserRole) for i in range(lw.count())
                                if lw.item(i).data(Qt.ItemDataRole.UserRole)]
            self.m.radio_play(st)
            self.fill_lists()

    def play_pause(self):
        if self.m.radio_on:
            self.m.play_pause()
        else:
            lw = self.tabs.currentWidget()
            it = lw.currentItem() if hasattr(lw, "currentItem") else None
            if it and it.data(Qt.ItemDataRole.UserRole):
                self.play_item(it)
            else:
                self.m.radio_play()

    def toggle_fav(self):
        if self.m.station:
            on = self.m.toggle_favourite(self.m.station)
            self.pet.bubble.say("Radio", ("Added to" if on else "Removed from") + " favourites.", 2)
            self.fill_lists()
            self.refresh()

    def toggle_mute(self):
        muted = not getattr(self.m, "muted", False)
        self.m.set_muted(muted)
        self.mute_btn.setText("🔇" if muted else "🔊")

    def volume_changed(self, v):
        self.m.set_volume(v)
        self.vol_label.setText(f"{v}%")
        self.mute_btn.setText("🔊")

    def do_search(self):
        import threading
        name, code = self.q.text().strip(), self.country.currentData()
        tag = "" if self.genre.currentIndex() == 0 else self.genre.currentText()
        self.search_status.setText("Searching…")
        relay = _Relay(); relay.ready.connect(self.show_results); self._search_relay = relay

        def work():
            import music
            try:
                relay.ready.emit(music.search_stations(name, code, tag))
            except Exception as e:
                relay.ready.emit(e)
        threading.Thread(target=work, daemon=True).start()

    def show_results(self, res):
        if isinstance(res, Exception):
            self.search_status.setText("Couldn't reach the station directory. Try again in a moment.")
            return
        self.add_stations(self.results, res)
        self.search_status.setText(f"{len(res)} stations found. Double-click to play, then ☆ to keep it.")

    def refresh(self):
        m = self.m
        if m.radio_on and m.station:
            state = "LIVE" if m.radio_playing else ("Paused" if not m.radio_error else "Station offline")
            self.card.set(m.station["name"], m.radio_song or m.station.get("genre", ""), state,
                          m.station.get("country", ""), error=m.radio_error)
            self.play_btn.setText("⏸" if m.radio_playing else "▶")
            self.fav_btn.setText("★" if m.is_favourite(m.station) else "☆")
        else:
            self.card.set("Blip Radio", "Pick a station and press play", "Off", "")
            self.play_btn.setText("▶")
            self.fav_btn.setText("☆")

    def closeEvent(self, e):
        try:
            self.m.radio_changed.disconnect(self.refresh)
        except TypeError:
            pass
        settings.save()                         # remember station + volume
        self.pet.radio_panel = None
        super().closeEvent(e)


class NowPlayingCard(QWidget):
    """Big glassy 'now playing' card with a little equaliser."""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(84)
        self.setMinimumWidth(420)
        self.name, self.song, self.state, self.country, self.error = "Blip Radio", "", "Off", "", None
        self.t0 = __import__("time").monotonic()
        self.timer = QTimer(self); self.timer.timeout.connect(self.update)

    def set(self, name, song, state, country, error=None):
        self.name, self.song, self.state, self.country, self.error = name, song, state, country, error
        if state == "LIVE":
            self.timer.start(120)               # the equaliser moves only while playing
        else:
            self.timer.stop()
        self.update()

    def paintEvent(self, e):
        import math
        import time as _t
        from PyQt6.QtGui import QFont
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0, QColor(110, 60, 220, 200)); g.setColorAt(1, QColor(0, 150, 200, 200))
        p.setPen(QPen(QColor(255, 255, 255, 60), 1)); p.setBrush(QBrush(g))
        p.drawRoundedRect(r, 14, 14)
        # equaliser
        t = _t.monotonic() - self.t0
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor(255, 255, 255, 220))
        for i in range(5):
            h = 10 + (abs(math.sin(t * (3 + i) + i)) * 34 if self.state == "LIVE" else 4)
            p.drawRoundedRect(QRectF(18 + i * 9, r.center().y() + 20 - h, 5, h), 2, 2)
        f = QFont("Segoe UI"); f.setPixelSize(19); f.setBold(True); p.setFont(f)
        p.setPen(QColor(255, 255, 255))
        p.drawText(QRectF(76, 12, r.width() - 160, 26), Qt.AlignmentFlag.AlignVCenter, self.name)
        f.setPixelSize(12); f.setBold(False); p.setFont(f); p.setPen(QColor(235, 245, 255, 220))
        p.drawText(QRectF(76, 40, r.width() - 160, 34), Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextWordWrap,
                   (self.song or "") + (f"   ·   {self.country}" if self.country else ""))
        # LIVE / Paused badge
        colour = {"LIVE": QColor(255, 60, 90), "Paused": QColor(120, 120, 150)}.get(self.state, QColor(90, 90, 110))
        p.setBrush(colour); p.setPen(Qt.PenStyle.NoPen)
        badge = QRectF(r.right() - 92, 14, 78, 22)
        p.drawRoundedRect(badge, 11, 11)
        f.setPixelSize(11); f.setBold(True); p.setFont(f); p.setPen(QColor(255, 255, 255))
        p.drawText(badge, Qt.AlignmentFlag.AlignCenter, ("● " if self.state == "LIVE" else "") + self.state)
        p.end()


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


# ---------------------------------------------------------------------------
# v1.2 windows: more options, startup apps, trophies
# ---------------------------------------------------------------------------
class MoreOptionsDialog(GlassDialog):
    def __init__(self, pet):
        super().__init__("More options")
        self.pet = pet
        self.care = QCheckBox("PC care: disk alerts, weekly tidy-up, startup check, game boost, restart tips")
        self.care.setChecked(config.PC_CARE)
        self.nudges = QCheckBox("Wellbeing nudges (tea, water, stretch...)")
        self.nudges.setChecked(config.NUDGES)
        row = QHBoxLayout(); row.addWidget(self.nudges); row.addWidget(QLabel("every"))
        self.every = QComboBox(); self.every.addItems(["30", "45", "60", "90", "120"])
        self.every.setCurrentText(str(config.NUDGE_MINUTES)); row.addWidget(self.every)
        row.addWidget(QLabel("min")); row.addStretch()
        self.summary = QCheckBox("Evening summary of your day")
        self.summary.setChecked(config.DAILY_SUMMARY)
        nl = QHBoxLayout(); nl.addWidget(QLabel("Night light"))
        self.nl_mode = QComboBox(); self.nl_mode.addItems(["Off", "On", "Schedule"])
        self.nl_mode.setCurrentText(config.NIGHT_LIGHT_MODE); nl.addWidget(self.nl_mode)
        self.nl_from = QComboBox(); self.nl_from.addItems([str(h) for h in range(17, 24)])
        self.nl_from.setCurrentText(str(config.NIGHT_LIGHT_FROM))
        self.nl_to = QComboBox(); self.nl_to.addItems([str(h) for h in range(4, 11)])
        self.nl_to.setCurrentText(str(config.NIGHT_LIGHT_TO))
        nl.addWidget(QLabel("from")); nl.addWidget(self.nl_from); nl.addWidget(QLabel("to")); nl.addWidget(self.nl_to)
        nl.addWidget(QLabel("warmth")); self.nl_warm = slider(10, 100, config.NIGHT_LIGHT_WARMTH)
        self.nl_warm.setMinimumWidth(100); nl.addWidget(self.nl_warm)
        self.nl_games = QCheckBox("Off while gaming"); self.nl_games.setChecked(config.NIGHT_LIGHT_OFF_IN_GAMES)
        nl.addWidget(self.nl_games)
        self.root.addLayout(nl)
        gm = QHBoxLayout(); gm.addWidget(QLabel("During fullscreen games"))
        self.game_mode = QComboBox(); self.game_mode.addItems(["Move to my other screen", "Hide"])
        self.game_mode.setCurrentIndex(0 if config.GAME_MODE == "Move" else 1)
        gm.addWidget(self.game_mode); gm.addStretch()
        self.root.addLayout(gm)
        self.props = QCheckBox("Morning coffee mug and nightcap")
        self.props.setChecked(config.TIME_PROPS)
        self.ai = QCheckBox("AI chat (free chatting through Ollama on this PC)")
        self.ai.setChecked(config.AI_CHAT)
        self.root.addWidget(self.ai)
        self.clip = QCheckBox("Clipboard helper: copied colour codes and sums show in a bubble")
        self.clip.setChecked(config.CLIPBOARD_HELPER)
        note = QLabel("The clipboard helper only looks at what you copy while it's on, right on your PC.\n"
                      "Nothing is saved or sent anywhere.")
        note.setStyleSheet("color: rgba(234,246,255,150); font: 8pt 'Segoe UI';")
        self.root.addWidget(self.care); self.root.addLayout(row)
        for w in (self.summary, self.props, self.clip, note):
            self.root.addWidget(w)
        tools = QHBoxLayout()
        b1 = QPushButton("Startup apps…"); b1.clicked.connect(lambda: StartupDialog(pet).exec())
        b2 = QPushButton("Trophies…"); b2.clicked.connect(lambda: TrophyDialog().exec())
        b3 = QPushButton("Tidy up now"); b3.clicked.connect(lambda: (pet.tidy_up(), self.accept()))
        for b in (b1, b2, b3):
            b.setAutoDefault(False); tools.addWidget(b)
        self.root.addLayout(tools)
        save = QPushButton("Save"); save.setObjectName("primary"); save.setAutoDefault(False)
        save.clicked.connect(self.save)
        self.root.addWidget(save, alignment=Qt.AlignmentFlag.AlignRight)
        self.add_credit()

    def save(self):
        config.PC_CARE = self.care.isChecked()
        config.NUDGES = self.nudges.isChecked()
        config.NUDGE_MINUTES = int(self.every.currentText())
        config.DAILY_SUMMARY = self.summary.isChecked()
        config.TIME_PROPS = self.props.isChecked()
        config.CLIPBOARD_HELPER = self.clip.isChecked()
        config.AI_CHAT = self.ai.isChecked()
        config.GAME_MODE = "Move" if self.game_mode.currentIndex() == 0 else "Hide"
        config.NIGHT_LIGHT_MODE = self.nl_mode.currentText()
        config.NIGHT_LIGHT_FROM = int(self.nl_from.currentText())
        config.NIGHT_LIGHT_TO = int(self.nl_to.currentText())
        config.NIGHT_LIGHT_WARMTH = self.nl_warm.value()
        config.NIGHT_LIGHT_OFF_IN_GAMES = self.nl_games.isChecked()
        settings.save()
        self.pet.night_light_tick(__import__("time").monotonic(), force=True)
        self.accept()


class StartupDialog(GlassDialog):
    """Apps that start with Windows. Untick to switch off (your own ones only), reversible."""

    def __init__(self, pet):
        from PyQt6.QtWidgets import QListWidget, QListWidgetItem
        import care
        super().__init__("Startup apps")
        self.pet = pet
        self.root.addWidget(QLabel("These start when Windows starts. Untick the ones you don't need,\n"
                                   "then press Apply. You can turn them all back on later."))
        self.list = QListWidget(); self.list.setMinimumSize(440, 260)
        self.list.setStyleSheet("QListWidget{background:rgba(10,8,24,150);color:#EAF6FF;border:1px solid "
                                "rgba(160,110,255,110);border-radius:10px;font:10pt 'Segoe UI';padding:4px}"
                                "QListWidget::item{padding:4px}")
        self.apps = care.startup_apps()
        for name, value, where, editable in self.apps:
            it = QListWidgetItem(f"{name}   ·   {where}")
            if editable:
                it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                it.setCheckState(Qt.CheckState.Checked)
            else:
                it.setFlags(Qt.ItemFlag.ItemIsEnabled)
                it.setForeground(QColor(234, 246, 255, 110))
            self.list.addItem(it)
        self.root.addWidget(self.list)
        row = QHBoxLayout()
        back = QPushButton("Turn back on what Blip switched off"); back.clicked.connect(self.restore)
        apply = QPushButton("Apply"); apply.setObjectName("primary"); apply.clicked.connect(self.apply)
        close = QPushButton("Close"); close.clicked.connect(self.accept)
        for b in (back, close, apply):
            b.setAutoDefault(False); row.addWidget(b)
        self.root.addLayout(row)
        self.add_credit()

    def apply(self):
        import care
        off = [a for i, a in enumerate(self.apps)
               if a[3] and self.list.item(i).checkState() == Qt.CheckState.Unchecked]
        if not off:
            self.accept(); return
        if ConfirmDialog("Switch off?", "Stop these starting with Windows?\n" + "\n".join("  " + a[0] for a in off),
                         yes="Switch off", no="Cancel").exec():
            care.disable_startup(off)
            self.pet.bubble.say("Startup apps", f"Switched off {len(off)} startup app(s).", 4)
            self.accept()

    def restore(self):
        import care
        n = care.restore_startup()
        self.pet.bubble.say("Startup apps", f"Turned {n} app(s) back on." if n else "Nothing to turn back on.", 4)
        self.accept()


class TrophyDialog(GlassDialog):
    def __init__(self):
        from PyQt6.QtWidgets import QGridLayout
        import care, progress
        super().__init__("Trophies")
        prog = progress.get()
        got = set(getattr(prog, "achievements", []))
        stats = getattr(prog, "stats", {})
        self.root.addWidget(QLabel(f"{len(got)} of {len(care.ACHIEVEMENTS)} unlocked"))
        grid = QGridLayout(); grid.setSpacing(8)
        for i, (aid, name, desc, counter, target, bonus) in enumerate(care.ACHIEVEMENTS):
            done = aid in got
            have = min(stats.get(counter, 0), target)
            lab = QLabel(("🏆 " if done else "🔒 ") + f"<b>{name}</b><br><span style='font-size:8pt'>{desc}"
                         + ("" if done else f" ({have}/{target})") + "</span>")
            lab.setStyleSheet("QLabel{background:rgba(255,255,255,%d);border:1px solid rgba(160,110,255,90);"
                              "border-radius:8px;padding:6px;color:%s}" % (24 if done else 8,
                                                                             "#FFF2B0" if done else "rgba(234,246,255,150)"))
            lab.setFixedWidth(210)
            grid.addWidget(lab, i // 3, i % 3)
        self.root.addLayout(grid)
        close = QPushButton("Close"); close.setObjectName("primary"); close.setAutoDefault(False)
        close.clicked.connect(self.accept)
        self.root.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)
        self.add_credit()
