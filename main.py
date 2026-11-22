"""
Blip - your desktop pet (Stage 4)
Run:  python main.py
Developed by Tunes
"""
import os
import signal
import sys

if __name__ == "__main__" and "--helper" in sys.argv:
    # Blip's small music/radio helper process: load only what it needs.
    import helper
    helper.main(sys.argv[sys.argv.index("--helper") + 1])
    sys.exit(0)

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon

import config
import settings
from character import draw_pet
from pet_window import PetWindow
import ui
from PyQt6.QtCore import QTimer
from ui import build_menu


def make_icon() -> QIcon:
    """Tray icon: the pet itself, drawn at 64x64."""
    pix = QPixmap(64, 64)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    draw_pet(p, 64, "idle", 0.0)
    p.end()
    return QIcon(pix)


def already_running() -> bool:
    """Only one Blip at a time (e.g. started with Windows AND by double-click)."""
    if sys.platform != "win32":
        return False
    import ctypes
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
    global _MUTEX                    # keep the handle alive while Blip runs
    _MUTEX = kernel32.CreateMutexW(None, False, "Local\\BlipDesktopPet_Tunes")
    return ctypes.get_last_error() == 183          # ERROR_ALREADY_EXISTS


def main():
    # Let Ctrl+C in the VS Code terminal close the app.
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    if already_running():
        print(f"{config.APP_NAME} is already running (look on your taskbar / tray).")
        return

    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setQuitOnLastWindowClosed(False)

    first_run = not settings.SETTINGS_FILE.exists()
    settings.load()                  # your saved character, colours, hat, etc.

    pet = PetWindow()
    menu = build_menu(pet, app)
    pet.menu = menu                  # right-click the pet
    pet.show()

    tray = QSystemTrayIcon(make_icon(), app)
    tray.setToolTip(f"{config.APP_NAME}\n{config.CREDIT}")
    tray.setContextMenu(menu)        # right-click the tray icon
    tray.activated.connect(          # left-click the tray icon too
        lambda reason: menu.popup(QCursor.pos())
        if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
    # Refresh the tray icon after you change looks in Settings.
    pet.after_settings = lambda: tray.setIcon(make_icon())

    def update_tray():
        import progress
        tray.setToolTip(f"{config.APP_NAME} · {progress.get().title()}\n{config.CREDIT}")
    pet.update_tray = update_tray
    update_tray()
    tray.show()

    if first_run or os.getenv("BLIP_DEBUG_OPEN") == "welcome":
        def welcome():
            pet.welcome = ui.WelcomeDialog(pet)      # keep a reference, or it vanishes
            pet.welcome.show()
        QTimer.singleShot(1500, welcome)

    # Hidden testing aid: BLIP_DEBUG_OPEN=helper|settings|radio|chat opens that window.
    debug = os.getenv("BLIP_DEBUG_OPEN")
    if debug:
        opener = {"helper": lambda: ui.open_helper(pet), "radio": lambda: ui.open_radio(pet),
                  "chat": lambda: ui.open_chat(pet),
                  "settings": lambda: ui.SettingsDialog(pet).show()}.get(debug)
        if opener:
            QTimer.singleShot(2000, opener)

    g = pet.geometry()
    print(f"{config.APP_NAME} is running! {config.CREDIT}")
    print(f"Look on top of your taskbar at x={g.x()}, y={g.y()} "
          f"(screen: {pet.current_screen().name()}). Tray icon: bottom-right, maybe under ^.")
    print("Press Ctrl+C here to quit.", flush=True)

    def restore_screen():                 # normal colours when Blip closes
        if config.NIGHT_LIGHT_ACTIVE:
            import nightlight
            nightlight.restore()
    app.aboutToQuit.connect(restore_screen)
    if config.NIGHT_LIGHT_ACTIVE or config.NIGHT_LIGHT_MODE != "Off":
        QTimer.singleShot(2000, lambda: pet.night_light_tick(__import__("time").monotonic(), force=True))

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
