#!/usr/bin/env python3
# ponytail: one runnable check per non-trivial module — no framework, `python3 tests/test_yawc.py`
import pathlib, subprocess, sys, time

ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
ok = 0

def check(name, cond):
    global ok
    assert cond, f"FAIL {name}"
    ok += 1
    print(f"  ok {name}")

# polish.regex_polish — filler strip, caps, period, hotwords, cursor spacing
from src.polish import regex_polish, expand_snippets, transform_text, _strip_think, load_hotwords
check("filler strip", regex_polish("um hello world") == "Hello world.")
check("empty in empty out", regex_polish("   ") == "")
check("cursor spacing", regex_polish("hello", "Hi") == " Hello.")
check("hotword caps", regex_polish("kumusta priya") == "Kumusta Priya.")
check("strip think", _strip_think("<think>x</think>Done") == "Done")

# snippets — cue expansion, case-insensitive, missing file safe
import json, tempfile, os
tmp = tempfile.mkdtemp()
pathlib.Path(tmp, "snippets.json").write_text(json.dumps({"add disclaimer": "DISCLAIMER_TEXT"}))
import src.polish as polish
old, polish.REPO_CONFIG = polish.REPO_CONFIG, pathlib.Path(tmp)
check("snippet expand", "DISCLAIMER_TEXT" in expand_snippets("please add disclaimer here"))
check("snippet no-op", expand_snippets("nothing here") == "nothing here")
polish.REPO_CONFIG = old

# transforms — regex mimic fallback (no llama-server in CI)
check("structure transform", "- First" in transform_text("first we eat second we go", mode="structure"))
check("concise shortens", len(transform_text(" ".join(["word"] * 30), mode="concise")) < 200)

# context — category buckets per 04, file tag from title
from src.context import categorize, get_context
check("email cat", categorize("firefox", "Inbox - Gmail") == "Email")
check("work cat", categorize("Slack", "#yawc") == "Work messaging")
check("personal cat", categorize("telegram", "chat") == "Personal messaging")
check("other cat", categorize("foot", "some game") == "Other")
ctx = get_context(timeout_ms=80)
check("context shape", {"app_id", "cat", "cursor_left"} <= set(ctx))
t0 = time.time(); get_context(timeout_ms=80); dt = (time.time() - t0) * 1000
check("context within 3x budget", dt < 240)

# stt — guarded degrade without model
from src import stt
if not stt.available():
    try:
        stt.transcribe("/tmp/nonexistent.wav")
        check("stt degrade", False)
    except stt.ModelMissing:
        check("stt degrade", True)
else:
    check("stt degrade", True)  # model present — real path, skip

# dictation — FakeDictation interface + real degrade (no model -> empty, no crash)
from src.dictation import Dictation, FakeDictation, Utterance
check("fake dictate", FakeDictation().dictate(Utterance(wav_path="x")) == "hello stub")
d = Dictation(hotwords="Priya")
t0 = time.time()
out = d.dictate(Utterance(wav_path="/tmp/definitely-missing.wav"))
check("real degrade empty", out == "" and time.time() - t0 < 5)

# cursor context — owned by context.py, string built once (C2)
from src.context import CursorContext
check("ctx header", CursorContext("Hi ", "Email").prompt_header() == 'left="Hi " app=Email')

# pill state mapping — pure, no Gtk (C3)
from src.pill import ui_for
check("ui recording", ui_for({"state": "recording"})["wave"] is True)
check("ui idle hides", ui_for({"state": "idle"})["visible"] is False)
check("ui missing hides", ui_for(None)["visible"] is False)

print(f"\n{ok} checks passed")
