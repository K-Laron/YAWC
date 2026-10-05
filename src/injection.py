#!/usr/bin/env python3
# ponytail: Injection deep module per 03 — Wayland clipboard paste, wtype Ctrl+Shift+V
# into focused window, restore original clipboard. Password fields excluded (04 safety).
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
    startswith, not ==: clipboard managers may re-serve with trailing newline.
    Progressive delays minimize process spawn overhead while converging fast."""
    deadline = time.time() + cap_s
    delays = (0.005, 0.010, 0.020, 0.025)
    step = 0
    while time.time() < deadline:
        try:
            res = subprocess.run(["wl-paste"], capture_output=True, text=True, errors="replace", timeout=0.04)
            if res.stdout.startswith(text):
                return True
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass
        delay = delays[min(step, len(delays) - 1)]
        time.sleep(delay)
        step += 1
    return False


def _wtype_paste(text: str, restore: bool) -> bool:
    orig = subprocess.run(["wl-paste"], capture_output=True, text=True, errors="replace").stdout \
        if os.environ.get("WAYLAND_DISPLAY") else ""
    subprocess.run(["wl-copy"], input=text, text=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _clipboard_settled(text)
    try:
        r = subprocess.run(["wtype", "-M", "ctrl", "-k", "v", "-m", "ctrl"], timeout=1)
        ok = r.returncode == 0
    except Exception:
        ok = False
    if restore:
        time.sleep(0.05)  # 50ms hold gives Wayland app time to consume paste event
        subprocess.run(["wl-copy"], input=orig, text=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return ok


def _ydotool_paste(text: str, restore: bool) -> bool:
    orig = subprocess.run(["wl-paste"], capture_output=True, text=True, errors="replace").stdout \
        if os.environ.get("WAYLAND_DISPLAY") else ""
    subprocess.run(["wl-copy"], input=text, text=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _clipboard_settled(text)
    try:
        r = subprocess.run(["ydotool", "key", "29:1", "47:1", "47:0", "29:0"], timeout=1)
        ok = r.returncode == 0
    except Exception:
        ok = False
    if restore:
        time.sleep(0.05)
        subprocess.run(["wl-copy"], input=orig, text=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return ok


def inject(text: str, restore: bool = True, is_password: bool | None = None) -> bool:
    # 04 invariant: password fields NEVER receive dictated text
    pw = _is_password_field() if is_password is None else is_password
    if pw:
        return False
    if not text:
        return True
    # prefer wtype (wayland-native, no root daemon); fall back to ydotool for XWayland
    if shutil.which("wtype"):
        return _wtype_paste(text, restore)
    if shutil.which("ydotool"):
        return _ydotool_paste(text, restore)
    return False
