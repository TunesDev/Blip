"""
Desktop pet - PC helper: shows what's using your RAM / CPU and lets YOU pick what to close.
Safety rules:
  * nothing is ever closed unless you tick it and press the button
  * Windows' own processes, antivirus, drivers, Blip, Ollama and the app
    you're using right now are never listed
  * apps with a window get a polite "please close" (like clicking X, they may ask to save);
    background-only processes get a normal terminate, never a forced kill
  * "Free up RAM" only asks Windows to page out unused memory: a light, temporary boost
Developed by Tunes
"""
import ctypes
import os
import time
from ctypes import wintypes

import psutil

NEVER = {
    "system", "system idle process", "idle", "registry", "memory compression", "secure system",
    "smss.exe", "csrss.exe", "wininit.exe", "winlogon.exe", "services.exe", "lsass.exe", "lsaiso.exe",
    "svchost.exe", "explorer.exe", "dwm.exe", "fontdrvhost.exe", "audiodg.exe", "sihost.exe",
    "ctfmon.exe", "taskhostw.exe", "runtimebroker.exe", "conhost.exe", "dllhost.exe", "spoolsv.exe",
    "searchhost.exe", "searchindexer.exe", "startmenuexperiencehost.exe", "shellexperiencehost.exe",
    "textinputhost.exe", "securityhealthservice.exe", "securityhealthsystray.exe", "msmpeng.exe",
    "nissrv.exe", "smartscreen.exe", "wudfhost.exe", "taskmgr.exe", "lockapp.exe", "applicationframehost.exe",
    "blip.exe", "ollama.exe", "ollama app.exe", "ollama_llama_server.exe", "llama-server.exe",
    "claude.exe", "node.exe", "powershell.exe", "pwsh.exe", "cmd.exe", "bash.exe", "git.exe",
    "windowsterminal.exe", "openconsole.exe", "python.exe", "pythonw.exe", "msedgewebview2.exe",
}
NEVER_PARTS = ("norton", "avast", "asw", "avg", "esrv", "memcompression", "vmmem", "defender", "antivirus", "nvcontainer", "nvdisplay", "nvidia", "amd",
               "realtek", "intel", "driver", "audio", "update", "service")
# Background-only processes that are safe to suggest (pre-ticked) when they have no window.
OBVIOUS_HOGS = {"xboxpcapp.exe", "widgets.exe", "msedge.exe", "phoneexperiencehost.exe",
                "onedrive.exe", "teams.exe", "ms-teams.exe", "gamebar.exe", "steamwebhelper.exe"}

user32 = ctypes.WinDLL("user32")
psapi = ctypes.WinDLL("psapi")
kernel32 = ctypes.WinDLL("kernel32")
EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [EnumWindowsProc, wintypes.LPARAM]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.GetForegroundWindow.restype = wintypes.HWND
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
psapi.EmptyWorkingSet.argtypes = [wintypes.HANDLE]
WM_CLOSE = 0x0010


def windows_by_pid():
    """{pid: [hwnd, ...]} for visible, titled windows."""
    found = {}

    @EnumWindowsProc
    def cb(hwnd, _):
        if user32.IsWindowVisible(hwnd) and user32.GetWindowTextLengthW(hwnd):
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            found.setdefault(pid.value, []).append(hwnd)
        return True
    user32.EnumWindows(cb, 0)
    return found


def _protected_pids():
    """Blip itself and whatever you're using right now (e.g. a game)."""
    keep = {os.getpid(), os.getppid()}
    fg = user32.GetForegroundWindow()
    if fg:
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(fg, ctypes.byref(pid))
        keep.add(pid.value)
    return keep


def _blocked(name, proc):
    n = name.lower()
    if n in NEVER or any(part in n for part in NEVER_PARTS):
        return True
    try:
        exe = ((proc.get("exe") if isinstance(proc, dict) else proc.info.get("exe")) or "").lower()
    except Exception:
        exe = ""
    return exe.startswith(r"c:\windows") or "steamapps" in exe


def ram_cpu():
    return psutil.virtual_memory().percent, psutil.cpu_percent(interval=None)


def cpu_now():
    """CPU use over the last moment (top_apps() already waited, so this is accurate)."""
    return psutil.cpu_percent(interval=None)


def top_apps(limit=12):
    """Groups processes by app name. Slow-ish (~0.7 s): call it from a thread.
    Returns [{name, mb, cpu, pids, windowed, suggest}] sorted by memory."""
    psutil.cpu_percent(interval=None)                # start the CPU measurement
    # Copy each process's info right away: psutil re-uses Process objects between calls,
    # so another scan running at the same time could otherwise swap .info under us.
    procs = []
    for p in psutil.process_iter(["pid", "name", "exe", "memory_info"]):
        try:
            procs.append((p, dict(p.info)))
        except Exception:
            pass
    for p, _ in procs:
        try:
            p.cpu_percent(None)                      # first sample
        except Exception:
            pass
    time.sleep(0.7)
    wins = windows_by_pid()
    keep = _protected_pids()
    cores = psutil.cpu_count() or 1
    groups = {}
    for p, info in procs:
        try:
            name = info.get("name") or ""
            if not name or p.pid in keep or _blocked(name, info):
                continue
            mi = info.get("memory_info")
            mem = mi.rss if mi else 0
            cpu = p.cpu_percent(None) / cores
        except Exception:
            continue                                 # gone, or not ours to touch: skip just this one
        g = groups.setdefault(name.lower(), {"name": name, "mb": 0.0, "cpu": 0.0,
                                             "pids": [], "windowed": False})
        g["mb"] += mem / 1048576
        g["cpu"] += cpu
        g["pids"].append(p.pid)
        g["windowed"] |= p.pid in wins
    if keep & {pid for g in groups.values() for pid in g["pids"]}:
        pass
    apps = sorted(groups.values(), key=lambda g: g["mb"] + g["cpu"] * 40, reverse=True)[:limit]
    for g in apps:
        g["suggest"] = g["name"].lower() in OBVIOUS_HOGS and not g["windowed"]
    return apps


def close_app(app):
    """Politely close an app: WM_CLOSE to its windows, terminate() for background parts."""
    wins = windows_by_pid()
    closed = 0
    for pid in app["pids"]:
        try:
            if pid in wins:
                for hwnd in wins[pid]:
                    user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
            elif not app["windowed"]:
                psutil.Process(pid).terminate()
            closed += 1
        except (psutil.Error, OSError):
            pass
    return closed


def free_ram():
    """Ask Windows to trim unused memory from normal apps. Returns MB freed (roughly)."""
    before = psutil.virtual_memory().available
    keep = _protected_pids()
    for p in psutil.process_iter(["pid", "name", "exe"]):
        try:
            info = dict(p.info)
            if p.pid in keep or _blocked(info.get("name") or "", info):
                continue
            h = kernel32.OpenProcess(0x0100 | 0x0400, False, p.pid)   # SET_QUOTA | QUERY_INFO
            if h:
                psapi.EmptyWorkingSet(h)
                kernel32.CloseHandle(h)
        except Exception:
            pass
    time.sleep(0.5)
    return max(0, (psutil.virtual_memory().available - before) / 1048576)


def temperatures():
    """CPU / GPU temperature, only if LibreHardwareMonitor is running with its web server
    (Options > Remote Web Server, port 8085). Returns e.g. "CPU 71°C · GPU 64°C" or None."""
    import json
    import urllib.request
    try:
        with urllib.request.urlopen("http://localhost:8085/data.json", timeout=0.6) as r:
            root = json.load(r)
    except Exception:
        return None
    found = {}

    def walk(node, hw=""):
        text = node.get("Text", "")
        img = node.get("ImageURL", "")
        if img.endswith(("cpu.png", "nvidia.png", "ati.png", "amd.png")):
            hw = "CPU" if img.endswith("cpu.png") else "GPU"
        if hw and "°C" in str(node.get("Value", "")) and hw not in found \
                and any(k in text for k in ("Package", "Tctl", "GPU Core", "Core Average")):
            found[hw] = str(node["Value"]).replace(" ", "")
        for child in node.get("Children", []):
            walk(child, hw)
    walk(root)
    return " · ".join(f"{k} {v}" for k, v in sorted(found.items())) or None


# ---------------------------------------------------------------------------
# Temp files (your own %TEMP% folder only)
# ---------------------------------------------------------------------------
def _temp_files(min_age_hours=24):
    """Files in %TEMP% not touched for a day (fresh ones may still be in use)."""
    import tempfile
    cutoff = time.time() - min_age_hours * 3600
    for root, _dirs, files in os.walk(tempfile.gettempdir()):
        for f in files:
            path = os.path.join(root, f)
            try:
                st = os.stat(path)
                if st.st_mtime < cutoff:
                    yield path, st.st_size
            except OSError:
                pass


def temp_size_mb():
    return sum(size for _, size in _temp_files()) / 1048576


def clean_temp():
    """Deletes old files in %TEMP%; files in use are skipped. Returns MB freed."""
    import tempfile
    freed = 0
    for path, size in list(_temp_files()):
        try:
            os.remove(path)
            freed += size
        except OSError:
            pass                                   # in use: leave it
    for root, dirs, _ in os.walk(tempfile.gettempdir(), topdown=False):
        for d in dirs:
            try:
                os.rmdir(os.path.join(root, d))    # only removes folders that are now empty
            except OSError:
                pass
    return freed / 1048576


# ---------------------------------------------------------------------------
# Windows power plan (powercfg works without admin for your own plans)
# ---------------------------------------------------------------------------
def _powercfg(*args):
    import subprocess
    out = subprocess.run(["powercfg", *args], capture_output=True, timeout=10,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
    for enc in ("utf-8", "mbcs", "cp850"):
        try:
            return out.decode(enc)
        except (UnicodeDecodeError, LookupError):
            pass
    return out.decode("utf-8", "replace")


def power_plans():
    """[(guid, name, active)]"""
    import re
    plans = []
    for line in _powercfg("/list").splitlines():
        m = re.search(r"([0-9a-f-]{36})\s+\((.+?)\)\s*(\*)?", line)
        if m:
            plans.append((m.group(1), m.group(2), bool(m.group(3))))
    return plans


def set_power_plan(guid):
    _powercfg("/setactive", guid)
