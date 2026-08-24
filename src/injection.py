#!/usr/bin/env python3
# ponytail: Injection module per improve candidate 2 — Worth exploring
# interface: inject(text, restore=True) -> bool, adapters: Wtype vs Ydotool
import shutil, subprocess, time, os

def _is_password_field() -> bool:
    # 04 excluded: password role / URL bar — stub per 04, real via gi.Atspi check when needed
    return False

class WtypeAdapter:
    def inject(self, text: str, restore=True) -> bool:
        if _is_password_field(): return False
        orig = subprocess.run(["wl-paste"], capture_output=True, text=True).stdout if os.environ.get("WAYLAND_DISPLAY") else ""
        subprocess.run(["wl-copy"], input=text, text=True)
        time.sleep(0.05)
        try: subprocess.run(["wtype","-M","ctrl","-k","v","-m","ctrl"], timeout=1)
        except: return False
        time.sleep(0.05)
        if restore and orig:
            subprocess.run(["wl-copy"], input=orig, text=True)
        return True

class YdotoolAdapter:
    def inject(self, text: str, restore=True) -> bool:
        if _is_password_field(): return False
        # 03 ydotoold fallback per prototype
        sock = os.environ.get("YDOTOOL_SOCKET","/tmp/.ydotool_socket")
        os.environ["YDOTOOL_SOCKET"]=sock
        try:
            subprocess.run(["ydotool","type", text], timeout=1)
            return True
        except: return False

def inject(text: str, restore=True) -> bool:
    # auto-detect per 03: wtype if WAYLAND_DISPLAY else ydotool
    if os.environ.get("WAYLAND_DISPLAY") and shutil.which("wtype"):
        return WtypeAdapter().inject(text, restore)
    if shutil.which("ydotool"):
        return YdotoolAdapter().inject(text, restore)
    # fallback: wl-copy only
    subprocess.run(["wl-copy"], input=text, text=True)
    return False
