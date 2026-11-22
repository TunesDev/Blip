"""
Desktop pet - uninstall Blip (Customise & settings > Uninstall Blip…).
  * removes Blip's "start with Windows" entry (only if it points at THIS Blip)
  * optionally deletes your Blip data in %APPDATA%\\Blip (settings, chat memory, app list)
  * optionally removes the AI model Blip downloaded (llama3.2:3b, ~2 GB)
  * deletes the installed app (the dist\\Blip folder with Blip.exe) once Blip has closed
Your source code folder (the .py files) is never touched.
Developed by Tunes
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import autostart
from settings import DATA_DIR

MODEL = "llama3.2:3b"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def app_folder():
    """The folder holding Blip.exe, or None when running from the .py files."""
    if not getattr(sys, "frozen", False):
        return None
    folder = Path(sys.executable).resolve().parent
    return folder if is_app_folder(folder) else None


def is_app_folder(folder):
    """Safety: only ever a PyInstaller output folder "...\\dist\\Blip" with Blip.exe and
    no .py source files in it."""
    folder = Path(folder)
    return (folder.name.lower() == "blip" and folder.parent.name.lower() == "dist"
            and (folder / "Blip.exe").exists() and not any(folder.glob("*.py")))


def _autostart_value(name):
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, autostart.RUN_KEY) as key:
            return winreg.QueryValueEx(key, name)[0]
    except OSError:
        return None


def _remove_autostart(name, folder):
    """Remove the Run entry only if it starts THIS copy of Blip."""
    value = _autostart_value(name)
    if value is None:
        return False
    mine = str(folder / "Blip.exe") if folder else str(Path(__file__).resolve().with_name("main.py"))
    if mine.lower() not in value.lower():
        return False
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, autostart.RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.DeleteValue(key, name)
    return True


def ollama_running():
    import urllib.request
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2).close()
        return True
    except Exception:
        return False


def run(delete_data=True, delete_model=False, data_dir=None, app_dir=None,
        run_value=autostart.VALUE_NAME, wait_pid=None):
    """Does the uninstall. Returns a list of what happened."""
    done = []
    folder = Path(app_dir) if app_dir else app_folder()

    if _remove_autostart(run_value, folder):
        done.append("removed from Windows start-up")

    data_dir = Path(data_dir or DATA_DIR)
    if delete_data and data_dir.exists():
        shutil.rmtree(data_dir, ignore_errors=True)
        done.append("deleted Blip's memory and settings")

    if delete_model:
        if ollama_running():
            subprocess.run(["ollama", "rm", MODEL], capture_output=True, timeout=60,
                           creationflags=NO_WINDOW)
            done.append(f"removed the AI model {MODEL}")
        else:
            done.append("Ollama isn't running, so the AI model was left alone")

    exe_dir = Path(sys.executable).resolve().parent
    if app_dir is None and getattr(sys, "frozen", False) and (exe_dir / "unins000.exe").exists():
        # Installed with the installer: let Windows' own uninstaller remove the app,
        # shortcuts and the "Installed apps" entry once Blip has closed.
        pid = wait_pid or os.getpid()
        script = (f"Wait-Process -Id {pid} -Timeout 60 -ErrorAction SilentlyContinue; "
                  f"Start-Process -FilePath '{exe_dir / 'unins000.exe'}' "
                  f"-ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART'")
        subprocess.Popen(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", script],
                         creationflags=NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, close_fds=True)
        done.append("Blip's uninstaller will finish removing it when Blip closes")
    elif folder is not None and is_app_folder(folder):
        # Blip.exe can't delete itself while it runs: a hidden helper waits for it
        # to close, then removes the app folder.
        pid = wait_pid or os.getpid()
        script = (f"Wait-Process -Id {pid} -Timeout 60 -ErrorAction SilentlyContinue; "
                  f"Start-Sleep -Milliseconds 500; "
                  f"Remove-Item -LiteralPath '{folder}' -Recurse -Force -ErrorAction SilentlyContinue")
        subprocess.Popen(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", script],
                         creationflags=NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, close_fds=True)
        done.append(f"the app folder {folder} will be deleted when Blip closes")
    else:
        done.append("running from the code files, so no app folder was deleted")
    return done
