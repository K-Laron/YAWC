#!/usr/bin/env python3
# ponytail: pill state seam — pure write/parse/UI-mapping; the GTK overlay is a dumb renderer.
# Atomic rename, never unlink: no race with the overlay poll.
import json, pathlib

PILL_STATE = pathlib.Path("/tmp/yawc-pill.state")


def show(state: str, text: str = ""):
    data = {"state": state, "text": text[:80]}
    tmp = PILL_STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data))
    tmp.rename(PILL_STATE)
    icons = {"idle": "○", "recording": "● REC", "transcribing": "◐", "polished": "✓", "error": "✕"}
    print(f"[pill] {icons.get(state, state)} {text[:60]}")


def parse() -> dict | None:
    try:
        return json.loads(PILL_STATE.read_text())
    except Exception:
        return None


def ui_for(data: dict | None) -> dict:
    """state -> UI intents. Pure — assertable without Gtk."""
    if not data:
        return {"visible": False}
    s = data.get("state")
    if s == "recording":
        return {"visible": True, "label": "Listening", "wave": True, "spinner": False, "timer": True}
    if s == "transcribing":
        return {"visible": True, "label": "Transcribing", "wave": False, "spinner": True, "timer": False}
    if s == "polished":
        return {"visible": True, "label": "✓ Done", "wave": False, "spinner": False, "timer": False}
    if s == "idle":
        return {"visible": False}
    return {"visible": True, "label": data.get("text", "")[:50], "wave": False, "spinner": False, "timer": False}


def recording(duration_s=0): show("recording")

def transcribing(): show("transcribing")

def polished(text): show("polished", text)

def idle(): show("idle")
