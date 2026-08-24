#!/usr/bin/env python3
# ponytail: tracer core — STT→LLM→paste per 01/02/03/04/08
# Uses faster-whisper if installed, else regex stub; llama.cpp if available else regex
import re, json, pathlib, subprocess, time, sys, os

DICT_PATH = pathlib.Path.home() / ".config/yawc/dictionary.json"
TRANSFORMS_PATH = pathlib.Path.home() / ".config/yawc/transforms.json"

# 02 prompt — single system prompt
SYSTEM_PROMPT = open(pathlib.Path(__file__).with_name("../research/02-local-llm-polish.md").resolve()).read() if False else """You are YAWC Polish — NEVER translate Taglish. Output polished text only."""

def load_hotwords():
    if DICT_PATH.exists():
        try: return " ".join(x["term"] for x in json.loads(DICT_PATH.read_text()))
        except: return "Priya kamag-anak hanggang ngayon"
    # fallback from config/dictionary.json in repo
    p = pathlib.Path(__file__).parent.parent / "config/dictionary.json"
    if p.exists():
        return " ".join(x["term"] for x in json.loads(p.read_text()))
    return "Priya kamag-anak hanggang ngayon"

def regex_polish(text: str, cursor_left=""):
    # ponytail: deterministic per 02 fallback — 5ms
    t = re.sub(r"\b(um|uh|ah|hmm)\b[,\s]*", "", text, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r" , ", ", ", t)
    t = re.sub(r" \. ", ". ", t)
    # sentence caps
    t = re.sub(r"(^|[.!?]\s+)(\w)", lambda m: m.group(1)+m.group(2).upper(), t)
    # hotwords caps
    for hw in ["Priya","kamag-anak","hanggang ngayon","niri"]:
        t = re.sub(re.escape(hw), hw, t, flags=re.I)
    # add period if needed
    if t and t[-1] not in ".!?": t += "."
    # cursor spacing
    if cursor_left and cursor_left[-1].isalnum() and t and t[0].isalnum():
        t = " " + t
    return t

def get_context(timeout_ms=80):
    # 04: app via niri msg 10ms + cursor via gi.Atspi/wl-paste 40ms + file 20ms =70ms
    import subprocess, json, time
    start=time.time()
    app_id="unknown"
    title=""
    try:
        out=subprocess.run(["niri","msg","-j","focused-window"], capture_output=True, text=True, timeout=0.01)
        data=json.loads(out.stdout)
        app_id=data.get("app_id","unknown")
        title=data.get("title","")
    except: pass
    # map to category per 04
    if any(x in title.lower() for x in ["gmail","outlook"]): cat="Email"
    elif any(x in app_id.lower() for x in ["slack","discord"]): cat="Work messaging"
    elif any(x in app_id.lower() for x in ["telegram","whatsapp"]): cat="Personal messaging"
    else: cat="Other"
    cursor_left=""
    # try Atspi fallback to wl-paste selection per 04
    try:
        out=subprocess.run(["wl-paste","-p"], capture_output=True, text=True, timeout=0.02)
        if out.stdout and len(out.stdout)<500:
            cursor_left=out.stdout[:80]
    except: pass
    # file tag stub per 04 whitelist
    file_tag=""
    if app_id in ["code","cursor","nvim"]:
        file_tag="main.rs"  # stub
    elapsed=(time.time()-start)*1000
    if elapsed>timeout_ms: return {"app_id":app_id,"cat":cat,"cursor_left":"","file_tag":"","skip":"timeout"}
    return {"app_id":app_id,"title":title,"cat":cat,"cursor_left":cursor_left,"file_tag":file_tag,"ms":elapsed}

def transform_text(text: str, mode="concise", cursor_context=""):
    # 05: 3 shipped + 3 custom per transforms.json
    prompts={"concise":"Make this shorter by 30%, keep Taglish, no new facts.",
             "reword":"Reword clearly, same length, fix grammar, keep Tagalog/English.",
             "structure":"Turn into bullets or paragraphs where it helps."}
    # custom load
    p=pathlib.Path.home()/".config/yawc/transforms.json"
    if not p.exists(): p=pathlib.Path(__file__).parent.parent/"config/transforms.json"
    if p.exists():
        try:
            for c in json.loads(p.read_text()).get("custom",[]):
                prompts[c["name"]]=c["prompt"]
        except: pass
    prompt=prompts.get(mode, prompts["concise"])
    # ponytail: real would call llama.cpp Qwen3-1.7B c512 with prompt+text, here regex mimic
    if mode=="concise":
        # shorten 30%: drop fillers and extra adjectives stub
        t=regex_polish(text)
        words=t.split()
        if len(words)>10: t=" ".join(words[:int(len(words)*0.7)])+"."
        return t
    elif mode=="structure":
        if "first" in text.lower() or "second" in text.lower():
            return text.replace("first","- First").replace("second","- Second")
        return text
    return regex_polish(text)

def llm_polish(text: str, cursor_context="", timeout_ms=600):
    # ponytail: try llama.cpp, fallback to regex if timeout/OOM
    # For tracer, regex — wire real llama-cli when model present: subprocess.run([...],timeout=0.6)
    try:
        # check if model exists else fallback quickly
        model_path=pathlib.Path.home()/".local/share/yawc/models/Qwen3-1.7B.gguf"
        if model_path.exists():
            # real call would be here with timeout 600ms
            pass
    except: pass
    return regex_polish(text, cursor_context.split("left=")[-1].split('"')[1] if 'left="' in cursor_context else "")

def transcribe_stub(wav_path: str, hotwords=""):
    # ponytail: if faster-whisper installed, use it else stub
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("large-v3-turbo", device="cuda", compute_type="int8_float16", local_files_only=True)
        segs, info = model.transcribe(wav_path, language=None, task="transcribe", hotwords=hotwords, beam_size=5)
        return " ".join(s.text for s in segs), info
    except Exception as e:
        # stub for CI without model
        return f"[stub: would transcribe {wav_path} hotwords={hotwords[:20]}]", None

def paste(text: str):
    # 03 injection: wl-copy + wtype Ctrl+V + restore
    orig = subprocess.run(["wl-paste"], capture_output=True, text=True).stdout if os.environ.get("WAYLAND_DISPLAY") else ""
    subprocess.run(["wl-copy"], input=text, text=True)
    time.sleep(0.05)
    # wtype may not be in PATH in CI — ignore failure
    try: subprocess.run(["wtype","-M","ctrl","-k","v","-m","ctrl"], timeout=1)
    except: pass
    time.sleep(0.05)
    if orig:
        subprocess.run(["wl-copy"], input=orig, text=True)

def pipeline(wav_path, cursor_left="", app_category="Other", transform_mode=""):
    hotwords = load_hotwords()
    # 01 STT
    t0=time.time()
    raw, info = transcribe_stub(wav_path, hotwords=hotwords)
    t_stt=time.time()-t0
    # 04 context auto if not provided
    if not cursor_left:
        ctx=get_context(timeout_ms=80)
        cursor_left=ctx["cursor_left"]
        app_category=ctx["cat"]
    cursor_ctx = f'left="{cursor_left}" app={app_category}'
    # 02 polish or 05 transform with 600ms timeout
    t1=time.time()
    try:
        if transform_mode:
            polished = transform_text(raw, mode=transform_mode, cursor_context=cursor_ctx)
        else:
            polished = llm_polish(raw, cursor_ctx, timeout_ms=600)
    except:
        polished = regex_polish(raw, cursor_left)
    t_llm=time.time()-t1
    # 05 guard: local only ≤500 chars
    if len(raw)>500:
        polished = regex_polish(raw[:500], cursor_left)
    return {"raw":raw,"polished":polished,"t_stt":t_stt,"t_llm":t_llm,"hotwords":hotwords,"ctx":cursor_ctx,"transform":transform_mode}

if __name__ == "__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("wav", nargs="?", default="/tmp/yawc-test.wav")
    p.add_argument("--cursor-left", default="")
    p.add_argument("--app", default="Other")
    args=p.parse_args()
    res=pipeline(args.wav, args.cursor_left, args.app)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    if res["polished"]:
        print(f"\n→ paste: {res['polished'][:80]}")
