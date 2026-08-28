#!/usr/bin/env python3
# ponytail: Injection — ONE paste shape (wl-copy -> wtype ctrl-v, clipboard restore),
# password guard always on. ydotool fallback for XWayland per 03.
import os, shutil, subprocess, time


def _is_password_field() -> bool:
    # fallback walk for callers with no context facts (CLI); hot path passes the flag
    try:
        from src import context
        return bool(context.get_context(timeout_ms=80).get("is_password"))
    except Exception:
        return False


def _clipboard_settled(text: str, cap_s: float = 0.15) -> bool:
    """wl-copy daemonizes — poll until new text is served (<10ms typical).
    startswith, not ==: clipboard managers may re-serve with trailing newline."""
    deadline = time.time() + cap_s
    while time.time() < deadline:
        if subprocess.run(["wl-paste"], capture_output=True, text=True, errors="replace").stdout.startswith(text):
            return True
        time.sleep(0.005)
    return False


def _wtype_paste(text: str, restore: bool) -> bool:
    orig = subprocess.run(["wl-paste"], capture_output=True, text=True, errors="replace").stdout \
        if os.environ.get("WAYLAND_DISPLAY") else ""
    subprocess.run(["wl-copy"], input=text, text=True)
    _clipboard_settled(text)
    try:
        subprocess.run(["wtype", "-M", "ctrl", "-k", "v", "-m", "ctrl"], timeout=1)
    except Exception:
        return False
    time.sleep(0.05)  # let the target app read clipboard before restore
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



def inject(text: str, restore: bool = True, is_password: bool | None = None) -> bool:
    """is_password: fact from the caller's context walk. None = unknown → walk
    here (safe default for CLI); hot path passes it to skip the second walk."""
    if not text:
        return False
    if is_password is None:
        is_password = _is_password_field()
    if is_password:
        return False  # 04 exclusion: never type into password fields
    if os.environ.get("WAYLAND_DISPLAY") and shutil.which("wtype"):
        return _wtype_paste(text, restore)
    if shutil.which("ydotool"):
        return _ydotool_paste(text, restore)
    subprocess.run(["wl-copy"], input=text, text=True)  # last resort: clipboard only
    return False
