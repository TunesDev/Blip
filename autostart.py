"""
Desktop pet - "Start with Windows" (stage 9).
Adds/removes Blip in HKEY_CURRENT_USER\\...\\Run, the same list Task Manager's
"Startup apps" tab shows, so you can also switch it off there.
Developed by Tunes
"""
import sys
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "Blip"

try:
    import winreg
except ImportError:            # not Windows
    winreg = None


def launch_command() -> str:
    """How Windows should start Blip: the .exe, or pythonw + main.py when run from code."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    exe = Path(sys.executable)
    pythonw = exe.with_name("pythonw.exe")
    if pythonw.exists():
        exe = pythonw
    main_py = Path(__file__).resolve().with_name("main.py")
    return f'"{exe}" "{main_py}"'


def is_enabled() -> bool:
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, VALUE_NAME)
            return True
    except OSError:
        return False


def set_enabled(on: bool):
    if winreg is None:
        return
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if on:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, launch_command())
        else:
            try:
                winreg.DeleteValue(key, VALUE_NAME)
            except FileNotFoundError:
                pass
