"""
Desktop pet - temperature, the light way.
GPU: asks the NVIDIA driver directly (nvml.dll, the same data nvidia-smi
uses) - no extra program is started, so it costs almost nothing.
CPU: Windows only gives CPU temperature to admin apps, so Blip reads it only if
LibreHardwareMonitor is running (see pchelper.temperatures). Otherwise: None.
Developed by Tunes
"""
import ctypes
import os

_nvml = None
_gpu = None
_failed = False


def gpu_temp():
    """GPU temperature in °C, or None if there's no NVIDIA GPU / driver."""
    global _nvml, _gpu, _failed
    if os.getenv("BLIP_DEBUG_HOT"):                 # for testing the "too hot" question
        return 90
    if _failed:
        return None
    try:
        if _nvml is None:
            _nvml = ctypes.WinDLL("nvml.dll")
            if _nvml.nvmlInit_v2() != 0:
                raise OSError("nvmlInit failed")
            handle = ctypes.c_void_p()
            if _nvml.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(handle)) != 0:
                raise OSError("no GPU 0")
            _gpu = handle
        t = ctypes.c_uint()
        if _nvml.nvmlDeviceGetTemperature(_gpu, 0, ctypes.byref(t)) != 0:   # 0 = GPU core
            return None
        return int(t.value)
    except Exception:
        _failed = True                                # don't keep trying every check
        return None
