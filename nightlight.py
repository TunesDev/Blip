"""
Desktop pet - Blip's own night light: a warm screen filter for the evening.
Windows has no public API for its own Night light, so Blip sets a warm "gamma ramp" on each
monitor (SetDeviceGammaRamp: no admin, zero CPU once it's set). Normal colours are put back
when you switch it off, when Blip closes, and on the next start if Blip ever crashed.
If a display refuses the warm ramp, Blip opens Windows' own Night light settings instead.
Developed by Tunes
"""
import ctypes
from ctypes import wintypes

import config

user32 = ctypes.WinDLL("user32")
gdi32 = ctypes.WinDLL("gdi32")
gdi32.CreateDCW.restype = wintypes.HDC
gdi32.CreateDCW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_void_p]
gdi32.SetDeviceGammaRamp.argtypes = [wintypes.HDC, ctypes.c_void_p]
gdi32.GetDeviceGammaRamp.argtypes = [wintypes.HDC, ctypes.c_void_p]
gdi32.DeleteDC.argtypes = [wintypes.HDC]

Ramp = (ctypes.c_ushort * 256) * 3


class MONITORINFOEX(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT), ("rcWork", wintypes.RECT),
                ("dwFlags", wintypes.DWORD), ("szDevice", wintypes.WCHAR * 32)]


def _displays():
    names = []
    Proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(wintypes.RECT),
                              wintypes.LPARAM)

    def cb(hmon, hdc, rect, lp):
        mi = MONITORINFOEX(); mi.cbSize = ctypes.sizeof(mi)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            names.append(mi.szDevice)
        return True
    user32.EnumDisplayMonitors(None, None, Proc(cb), 0)
    return names


def _ramp(warmth):
    """warmth 0..100 -> a gamma ramp that turns down blue (and a little green)."""
    w = max(0, min(100, warmth)) / 100
    gains = (1.0, 1.0 - 0.22 * w, 1.0 - 0.48 * w)       # red, green, blue
    r = Ramp()
    for c in range(3):
        for i in range(256):
            r[c][i] = min(65535, int(i * 257 * gains[c]))
    return r


def _apply(ramp):
    ok = True
    for dev in _displays():
        dc = gdi32.CreateDCW(dev, None, None, None)
        if not dc:
            ok = False
            continue
        if not gdi32.SetDeviceGammaRamp(dc, ctypes.byref(ramp)):
            ok = False
        gdi32.DeleteDC(dc)
    return ok


def turn_on(warmth=None):
    """Returns True if every display took the warm filter."""
    ok = _apply(_ramp(config.NIGHT_LIGHT_WARMTH if warmth is None else warmth))
    if ok:
        mark(True)
    else:
        restore()
        import os
        os.startfile("ms-settings:nightlight")             # Windows' own Night light instead
    return ok


def restore():
    """Normal colours on every display."""
    _apply(_ramp(0))
    mark(False)


def mark(on):
    if config.NIGHT_LIGHT_ACTIVE != on:
        config.NIGHT_LIGHT_ACTIVE = on
        try:
            import settings
            settings.save()
        except Exception:
            pass


def read_blue_at(level=255):
    """For testing: the blue value at the top of each display's ramp."""
    out = []
    for dev in _displays():
        dc = gdi32.CreateDCW(dev, None, None, None)
        r = Ramp()
        if dc and gdi32.GetDeviceGammaRamp(dc, ctypes.byref(r)):
            out.append((dev, r[0][level], r[1][level], r[2][level]))
        if dc:
            gdi32.DeleteDC(dc)
    return out


def scheduled_now(hour, minute=0):
    start, end = config.NIGHT_LIGHT_FROM, config.NIGHT_LIGHT_TO
    now = hour + minute / 60
    return now >= start or now < end if start > end else start <= now < end


def should_be_on(hour, minute, gaming):
    mode = config.NIGHT_LIGHT_MODE
    on = mode == "On" or (mode == "Schedule" and scheduled_now(hour, minute))
    if gaming and config.NIGHT_LIGHT_OFF_IN_GAMES:
        on = False
    return on
