#!/usr/bin/env python3
# ponytail: pill UI stub per Wispr flow pill — wlr-layer-shell overlay
# States: idle → recording (dot + 00:02) → transcribing → polished preview
# For now: prints state to terminal + writes /tmp/yawc-pill.state for Tauri overlay to read
import pathlib, time, json, os
PILL_STATE = pathlib.Path("/tmp/yawc-pill.state")

def show(state: str, text=""):
    # state in idle, recording, transcribing, polished, error
    data={"state":state,"text":text[:80],"ms":int(time.time()*1000)}
    PILL_STATE.write_text(json.dumps(data))
    # ponytail: no Tauri window yet — log is the pill for headless test
    icons={"idle":"○","recording":"● REC","transcribing":"◐","polished":"✓","error":"✕"}
    print(f"[pill] {icons.get(state, state)} {text[:60]}")

def recording(duration_s=0):
    show("recording", f"{duration_s:02.0f}:00")

def transcribing(): show("transcribing", "transcribing...")

def polished(text): show("polished", text)

def idle(): 
    show("idle", "")
    try: PILL_STATE.unlink()
    except: pass

if __name__=="__main__":
    import sys
    cmd=sys.argv[1] if len(sys.argv)>1 else "idle"
    if cmd=="recording": recording(float(sys.argv[2]) if len(sys.argv)>2 else 1)
    elif cmd=="transcribing": transcribing()
    elif cmd=="polished": polished(" ".join(sys.argv[2:]))
    else: idle()
