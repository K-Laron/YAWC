#!/usr/bin/env python3
# ponytail: Command Mode entry per 05 — Ctrl+Win+Alt hold: speech = instruction about
# EXISTING selected text, not new dictation. Recorder owns capture; this owns the edit.
import pathlib, subprocess, sys, time

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from src.recorder import Recorder


def _selection() -> str:
    out = subprocess.run(["wl-paste", "-p"], capture_output=True, text=True, timeout=1)
    return out.stdout.strip()


def command_release(wav_path: str) -> str:
    # pill states belong to Recorder — this returns result strings only
    from src import stt, polish, injection
    sel = _selection()
    if not sel:
        return "no selection"
    try:
        instruction = stt.transcribe(wav_path).strip().lower()
    except Exception:
        return "no STT model"
    if not instruction:
        return "no instruction"
    if len(sel) > 500:  # 05 guard: local only ≤500 chars
        return "selection too long"
    # 05 physical commands that are keys, not text edits
    if "press enter" in instruction or "new line" in instruction:
        subprocess.run(["wtype", "-k", "Return"], timeout=1)
        return "⏎"
    out = polish.transform_text(sel, mode=instruction)  # free-text instruction
    injection.inject(out, restore=False)  # replace selection; old clipboard gone intentionally
    return out[:60]


if __name__ == "__main__":
    Recorder("cmd", on_release=command_release).toggle()
