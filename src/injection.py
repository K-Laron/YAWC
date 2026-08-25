#!/usr/bin/env python3
# ponytail: Injection — ONE paste shape (wl-copy -> wtype ctrl-v, clipboard restore),
# password guard always on. ydotool fallback for XWayland per 03.
import os, shutil, subprocess, time


def _is_password_field() -> bool:
    # 04 exclusion: never type into password fields
    try:
        from src import context
        return bool(context.get_context(timeout_ms=80).get("is_password"))
    except Exception:
        return False


def _wtype_paste(text: str, restore: bool) -> bool:
    orig = subprocess.run(["wl-paste"], capture_output=True, text=True).stdout \
        if os.environ.get("WAYLAND_DISPLAY") else ""
    subprocess.run(["wl-copy"], input=text, text=True)
    time.sleep(0.05)
    try:
        subprocess.run(["wtype", "-M", "ctrl", "-k", "v", "-m", "ctrl"], timeout=1)
    except Exception:
        return False
    time.sleep(0.05)
    if restore and orig:
        subprocess.run(["wl-copy"], input=orig, text=True)
    return True


def _ydotool_paste(text: str, restore: bool) -> bool:
    os.environ.setdefault("YDOTOOL_SOCKET", "/tmp/.ydotool_socket")
    try:
        subprocess.run(["ydotool", "type", text], timeout=1)
        return True
    except Exception:
        return False


def inject(text: str, restore: bool = True) -> bool:
    if not text or _is_password_field():
        return False
    if os.environ.get("WAYLAND_DISPLAY") and shutil.which("wtype"):
        return _wtype_paste(text, restore)
    if shutil.which("ydotool"):
        return _ydotool_paste(text, restore)
    subprocess.run(["wl-copy"], input=text, text=True)  # last resort: clipboard only
    return False
