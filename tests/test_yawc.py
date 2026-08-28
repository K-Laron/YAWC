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

# transforms — regex mimic fallback (test the deterministic path; live LLM wording varies)
from src.polish import _regex_transform
check("structure transform", "- First" in _regex_transform("first we eat second we go", mode="structure"))
check("concise shortens", len(_regex_transform(" ".join(["word"] * 30), mode="concise")) < 200)

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
check("real degrade empty", out == "" and time.time() - t0 < 15)  # CUDA OOM vs daemon costs ~4s; bound catches hangs only

# cursor context — owned by context.py, string built once (C2)
from src.context import CursorContext
check("ctx header", CursorContext("Hi ", "Email").prompt_header() == 'left="Hi " app=Email')

# pill state mapping — pure, no Gtk (C3)
from src.pill import ui_for
check("ui recording", ui_for({"state": "recording"})["wave"] is True)
check("ui idle hides", ui_for({"state": "idle"})["visible"] is False)
check("ui missing hides", ui_for(None)["visible"] is False)

# recorder — release path flushes wav and stays fast (regression: no blind sleep/pkill)
import shutil
if shutil.which("arecord"):
    from src.recorder import Recorder
    calls, stamps = [], []
    def _on_rel(p):
        stamps.append(time.time())
        calls.append(1)
        return "ok"
    rec = Recorder("selftest", on_release=_on_rel)
    rec.begin()
    assert rec.proc is not None
    first = rec.proc
    rec.begin()  # second node emitting hold must not spawn a second arecord
    same = rec.proc is first and first.poll() is None
    time.sleep(0.25)  # let arecord deliver >44B so on_release actually runs
    t0 = time.time(); res = rec.release(); dt_total = time.time() - t0
    capture_dt = (stamps[0] - t0) if stamps else 99.0  # capture phase only (tail sleeps 2s)
    res2 = rec.release()  # sibling node release: silent no-op, never re-runs pipeline
    check("recorder release fused + no duplicate dictation",
          capture_dt < 0.18 and dt_total < 2.6 and rec.proc is None and same
          and res2 is None
          and len(calls) == (0 if res is None else 1))
else:
    check("recorder skip headless", True)

# injection — clipboard poll converges on fresh text, restores user clipboard
from src.injection import _clipboard_settled
if os.environ.get("WAYLAND_DISPLAY") and shutil.which("wl-copy"):
    orig = subprocess.run(["wl-paste"], capture_output=True, text=True, errors="replace").stdout
    # DEVNULL: wl-copy daemonizes — its child must not hold the test's stdout pipes
    def _copy(s):
        subprocess.run(["wl-copy"], input=s, text=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _copy("yawc-selftest-clip")
    t0 = time.time(); hit = _clipboard_settled("yawc-selftest-clip"); dt = time.time() - t0
    if orig:
        _copy(orig)
    check("clipboard poll converges fast", hit and dt < 0.1)
else:
    check("clipboard poll skip headless", True)

# injection — password guard: explicit fact never walks, None falls back, True refuses
from src import injection
if os.environ.get("WAYLAND_DISPLAY") and shutil.which("wtype"):
    sent, walks = [], [0]
    real_gc = getattr(__import__("src.context", fromlist=["get_context"]), "get_context")
    def counting_gc(*a, **k):
        walks[0] += 1
        return real_gc(*a, **k)
    import src.context as _ctxmod
    orig_wp, orig_gc = injection._wtype_paste, _ctxmod.get_context
    injection._wtype_paste = lambda t, r: sent.append(t) or True
    _ctxmod.get_context = counting_gc
    try:
        refused = injection.inject("nope", is_password=True) is False and sent == [] and walks[0] == 0
        allowed = injection.inject("yes", is_password=False) is True and sent == ["yes"] and walks[0] == 0
        fallback_walks = walks[0]
        injection.inject("fb", is_password=None)  # unknown → must walk once itself
        check("password guard uses caller facts", refused and allowed and fallback_walks == 0 and walks[0] == 1)
    finally:
        injection._wtype_paste = orig_wp
        _ctxmod.get_context = orig_gc
else:
    check("password guard skip headless", True)

print(f"\n{ok} checks passed")
