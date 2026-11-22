"""
Desktop pet - reads things about your PC (stage 4):
  * which windows are open, so Blip can sit on top of them
  * how busy your CPU and RAM are, so Blip can sweat when they're maxed
Everything here quietly returns "nothing" on non-Windows systems or if a call fails.
Developed by Tunes
"""
import ctypes
import os
import sys

from PyQt6.QtCore import QRect

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    from ctypes import wintypes
    # Our own copies of the DLLs, so our argtypes don't clash with pet_window.py's.
    user32 = ctypes.WinDLL("user32")
    kernel32 = ctypes.WinDLL("kernel32")
    try:
        dwmapi = ctypes.WinDLL("dwmapi")
    except OSError:
        dwmapi = None

    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

    EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows.argtypes = [EnumWindowsProc, wintypes.LPARAM]
    user32.IsWindow.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.IsZoomed.argtypes = [wintypes.HWND]
    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongW.restype = ctypes.c_long
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.OpenInputDesktop.restype = ctypes.c_void_p
    user32.OpenInputDesktop.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    user32.SwitchDesktop.argtypes = [ctypes.c_void_p]
    user32.CloseDesktop.argtypes = [ctypes.c_void_p]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.MonitorFromWindow.restype = wintypes.HMONITOR
    user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
    user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MONITORINFO)]
    kernel32.GetSystemTimes.argtypes = [ctypes.POINTER(wintypes.FILETIME)] * 3
    kernel32.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(MEMORYSTATUSEX)]
    if dwmapi is not None:
        dwmapi.DwmGetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD,
                                                 ctypes.c_void_p, wintypes.DWORD]

    GWL_STYLE, GWL_EXSTYLE = -16, -20
    WS_CAPTION = 0x00C00000
    WS_EX_TOOLWINDOW = 0x00000080
    WS_EX_NOACTIVATE = 0x08000000
    DWMWA_EXTENDED_FRAME_BOUNDS = 9
    DWMWA_CLOAKED = 14
    MONITOR_DEFAULTTONEAREST = 2
    # The desktop, taskbar and Start/notification panels are not windows to sit on.
    SKIP_CLASSES = {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd",
                    "Windows.UI.Core.CoreWindow", "NotifyIconOverflowWindow",
                    "TopLevelWindowForOverflowXamlIsland", "XamlExplorerHostIslandWindow"}

MY_PID = os.getpid()
MIN_WIDTH = 160           # windows narrower than this are too small to stand on
MIN_HEIGHT = 120


# ---------------------------------------------------------------------------
# Windows Blip can sit on
# ---------------------------------------------------------------------------
def _real_rect(hwnd):
    """The window's visible rectangle in physical pixels (without the invisible
    resize border Windows 10/11 adds around every window)."""
    r = wintypes.RECT()
    if dwmapi is not None and dwmapi.DwmGetWindowAttribute(
            hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(r), ctypes.sizeof(r)) == 0:
        return r
    if user32.GetWindowRect(hwnd, ctypes.byref(r)):
        return r
    return None


def _cloaked(hwnd):
    """Hidden 'ghost' windows (apps suspended in the background, other virtual desktops)."""
    if dwmapi is None:
        return False
    val = ctypes.c_int(0)
    dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(val), ctypes.sizeof(val))
    return val.value != 0


def _is_candidate(hwnd):
    if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd) or _cloaked(hwnd):
        return False
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value == MY_PID:
        return False
    ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    if ex & (WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE):
        return False
    style = user32.GetWindowLongW(hwnd, GWL_STYLE)
    if style & WS_CAPTION != WS_CAPTION or user32.GetWindowTextLengthW(hwnd) == 0:
        return False
    name = ctypes.create_unicode_buffer(64)
    user32.GetClassNameW(hwnd, name, 64)
    return name.value not in SKIP_CLASSES


class ScreenMap:
    """Converts Windows' physical pixels to Qt's logical pixels for one monitor."""

    def __init__(self, my_hwnd, qt_screen):
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(mi)
        mon = user32.MonitorFromWindow(my_hwnd, MONITOR_DEFAULTTONEAREST)
        if not user32.GetMonitorInfoW(mon, ctypes.byref(mi)):
            raise OSError("GetMonitorInfo failed")
        self.mon = mi.rcMonitor
        g = qt_screen.geometry()
        self.qx, self.qy = g.left(), g.top()
        self.scale = max(1e-6, (mi.rcMonitor.right - mi.rcMonitor.left) / max(1, g.width()))

    def to_qt(self, r):
        s = self.scale
        left = self.qx + (r.left - self.mon.left) / s
        top = self.qy + (r.top - self.mon.top) / s
        right = self.qx + (r.right - self.mon.left) / s
        bottom = self.qy + (r.bottom - self.mon.top) / s
        return QRect(round(left), round(top), round(right - left), round(bottom - top))


def windows_on_screen(my_hwnd, qt_screen):
    """All normal app windows, front-most first, as (hwnd, QRect, maximised) in
    Qt coordinates. Only windows that overlap the pet's screen are returned."""
    if not IS_WINDOWS:
        return []
    try:
        smap = ScreenMap(my_hwnd, qt_screen)
        found = []

        @EnumWindowsProc
        def callback(hwnd, _):
            try:
                if _is_candidate(hwnd):
                    r = _real_rect(hwnd)
                    if r is not None:
                        found.append((hwnd, smap.to_qt(r), bool(user32.IsZoomed(hwnd))))
            except Exception:
                pass
            return True

        user32.EnumWindows(callback, 0)
        area = qt_screen.geometry()
        return [w for w in found if w[1].intersects(area)]
    except Exception as e:
        print("Window list failed:", e)
        return []


def perch_spots(my_hwnd, qt_screen, top_limit):
    """Window top edges Blip could stand on: [(hwnd, left, right, top)].
    Skips maximised/tiny windows and edges hidden behind other windows."""
    wins = windows_on_screen(my_hwnd, qt_screen)
    spots = []
    for i, (hwnd, r, zoomed) in enumerate(wins):
        if zoomed or r.width() < MIN_WIDTH or r.height() < MIN_HEIGHT or r.top() <= top_limit + 40:
            continue
        left, right, top = r.left(), r.right(), r.top()
        # Cut away parts of the top edge that a window in front is covering.
        segments = [(left, right)]
        for _, front, _ in wins[:i]:
            if front.top() <= top + 2 and front.bottom() >= top - 2:
                new = []
                for a, b in segments:
                    if front.right() < a or front.left() > b:
                        new.append((a, b))
                        continue
                    if front.left() > a:
                        new.append((a, front.left() - 1))
                    if front.right() < b:
                        new.append((front.right() + 1, b))
                segments = new
        for a, b in segments:
            if b - a >= 70:
                spots.append((hwnd, a, b, top))
    return spots


def window_still_there(hwnd, my_hwnd, qt_screen):
    """Current QRect of a window, or None if it was closed / minimised / hidden."""
    if not IS_WINDOWS:
        return None
    try:
        if not user32.IsWindow(hwnd) or not user32.IsWindowVisible(hwnd) \
                or user32.IsIconic(hwnd) or user32.IsZoomed(hwnd) or _cloaked(hwnd):
            return None
        r = _real_rect(hwnd)
        return ScreenMap(my_hwnd, qt_screen).to_qt(r) if r is not None else None
    except Exception:
        return None


def foreground_class():
    """Class name of the window you're using right now (Task Manager = 'TaskManagerWindow')."""
    if not IS_WINDOWS:
        return ""
    try:
        fg = user32.GetForegroundWindow()
        if not fg:
            return ""
        name = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(fg, name, 64)
        return name.value
    except Exception:
        return ""


def pc_locked():
    """True while the lock screen is showing."""
    if not IS_WINDOWS:
        return False
    try:
        desk = user32.OpenInputDesktop(0, False, 0x0100)     # DESKTOP_SWITCHDESKTOP
        if not desk:
            return True
        ok = user32.SwitchDesktop(desk)
        user32.CloseDesktop(desk)
        return not ok
    except Exception:
        return False


def window_titles():
    """[(process id, title)] of every visible top-level window that has a title."""
    if not IS_WINDOWS:
        return []
    out = []
    try:
        @EnumWindowsProc
        def callback(hwnd, _):
            try:
                if user32.IsWindowVisible(hwnd):
                    n = user32.GetWindowTextLengthW(hwnd)
                    if n:
                        buf = ctypes.create_unicode_buffer(n + 1)
                        user32.GetWindowTextW(hwnd, buf, n + 1)
                        pid = wintypes.DWORD()
                        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                        out.append((pid.value, buf.value))
            except Exception:
                pass
            return True
        user32.EnumWindows(callback, 0)
    except Exception:
        pass
    return out


# ---------------------------------------------------------------------------
# CPU and RAM
# ---------------------------------------------------------------------------
def _ft(ft):
    return (ft.dwHighDateTime << 32) | ft.dwLowDateTime


class LoadMeter:
    """Call sample() every couple of seconds; returns (cpu %, ram %)."""

    def __init__(self):
        self.last = None

    def sample(self):
        if not IS_WINDOWS:
            return 0.0, 0.0
        try:
            idle, kern, user = wintypes.FILETIME(), wintypes.FILETIME(), wintypes.FILETIME()
            kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kern), ctypes.byref(user))
            now = (_ft(idle), _ft(kern), _ft(user))
            cpu = 0.0
            if self.last is not None:
                d_idle = now[0] - self.last[0]
                d_total = (now[1] - self.last[1]) + (now[2] - self.last[2])  # kernel includes idle
                if d_total > 0:
                    cpu = max(0.0, min(100.0, 100.0 * (d_total - d_idle) / d_total))
            self.last = now
            mem = MEMORYSTATUSEX()
            mem.dwLength = ctypes.sizeof(mem)
            kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
            return cpu, float(mem.dwMemoryLoad)
        except Exception:
            return 0.0, 0.0


# ---------------------------------------------------------------------------
# Desktop icons (READ-ONLY, for the "cheeky climber" antic)
# ---------------------------------------------------------------------------
def desktop_icons(my_hwnd, qt_screen):
    """[QRect] of desktop icons on Blip's screen that you can actually see right now
    (not covered by a window). Uses Windows UI Automation: it only READS where the icons
    are - nothing is ever moved, opened or changed."""
    if not IS_WINDOWS:
        return []
    try:
        import comtypes.client
        try:
            from comtypes.gen import UIAutomationClient as UIA
        except ImportError:
            comtypes.client.GetModule("UIAutomationCore.dll")
            from comtypes.gen import UIAutomationClient as UIA
        user32.FindWindowW.restype = wintypes.HWND
        user32.FindWindowExW.restype = wintypes.HWND
        user32.FindWindowExW.argtypes = [wintypes.HWND, wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR]
        user32.WindowFromPoint.restype = wintypes.HWND
        user32.WindowFromPoint.argtypes = [wintypes.POINT]
        prog = user32.FindWindowW("Progman", None)
        view = user32.FindWindowExW(prog, None, "SHELLDLL_DefView", None)
        w = None
        while not view:
            w = user32.FindWindowExW(None, w, "WorkerW", None)
            if not w:
                return []
            view = user32.FindWindowExW(w, None, "SHELLDLL_DefView", None)
        lv = user32.FindWindowExW(view, None, "SysListView32", None)
        if not lv or not user32.IsWindowVisible(lv):
            return []                                     # icons hidden (View > Show icons off)
        auto = comtypes.client.CreateObject(UIA.CUIAutomation, interface=UIA.IUIAutomation)
        items = auto.ElementFromHandle(lv).FindAll(UIA.TreeScope_Children, auto.CreateTrueCondition())
        smap = ScreenMap(my_hwnd, qt_screen)
        area = qt_screen.geometry()
        icons = []
        for i in range(items.Length):
            r = items.GetElement(i).CurrentBoundingRectangle
            if r.right <= r.left:
                continue
            # visible? the window at the icon's centre must be the desktop itself
            hit = user32.WindowFromPoint(wintypes.POINT((r.left + r.right) // 2, (r.top + r.bottom) // 2))
            if hit not in (lv, view):
                continue
            rect = wintypes.RECT(r.left, r.top, r.right, r.bottom)
            q = smap.to_qt(rect)
            if area.contains(q.center()):
                icons.append(q)
        return icons
    except Exception as e:
        print("Desktop icons not available:", e)
        return []


def trim_self():
    """Give Blip's unused memory back to Windows (after start-up / closing a panel)."""
    if not IS_WINDOWS:
        return
    try:
        psapi = ctypes.WinDLL("psapi")
        psapi.EmptyWorkingSet.argtypes = [wintypes.HANDLE]
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.EmptyWorkingSet(kernel32.GetCurrentProcess())
    except Exception:
        pass
