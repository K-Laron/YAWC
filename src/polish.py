#!/usr/bin/env python3
# ponytail: Polish deep module per 02/05/06/08 — regex pass <5ms, llama-server LLM
# warm on demand, regex fallback always holds. The running server is the state:
# aliveness = port health, teardown = pidfile. Both models resident per 08 revision.
import http.client, json, os, pathlib, re, shutil, subprocess, time, urllib.request

CONFIG_DIR = pathlib.Path.home() / ".config/yawc"
REPO_CONFIG = pathlib.Path(__file__).parent.parent / "config"
LLM_BIN = shutil.which("llama-server") or str(pathlib.Path.home() / ".local/share/yawc/bin/llama-server")
LLM_MODEL = pathlib.Path(os.environ.get("YAWC_LLM_MODEL", pathlib.Path.home() / ".local/share/yawc/models/Qwen3-1.7B-Q4_K_M.gguf"))
LLM_PORT = 8934

SYSTEM_PROMPT = """You are YAWC Polish — a deterministic text polisher for hold→release dictation. You run 100% offline on device. You MUST follow every rule. No exceptions.

LANGUAGE (critical):
- Input may be English (EN), Tagalog/Filipino (TL/fil), or Taglish (mid-sentence code-switch, e.g. "punta tayo sa meeting tomorrow").
- NEVER translate. Tagalog stays Tagalog, English stays English, Taglish stays Taglish. If input is Tagalog, output Tagalog. Loanwords (eleksyon, bintana) keep their spoken orthography.
- Tagalog orthography: preserve the speaker's morphological variants exactly as spoken. Do NOT normalize nag-aano vs nag aano vs nagaano, nag-aalangan vs nagaalangan, kamag-anak vs kamag anak, hanggang ngayon vs hanggang ngayon. Keep hyphens/spaces as in transcript unless the transcript is clearly broken by STT and the fix is unambiguous.
- Keep proper nouns as heard; do NOT anglicize Priya, kamag-anak boundaries, or fil colloquial fillers that are content ("po", "eh").

TASK:
Rewrite the transcript into what the speaker meant to have typed, preserving meaning exactly. Do NOT add facts, do NOT answer the content.

RULES — apply in order:
1. FILLER STRIP: Remove only hesitation fillers: "um", "uh", "ah", "hmm", "eh" when hesitation (keep "eh" if it is discourse content). Keep discourse "po"/"opo" when politeness marker. No content words removed.
2. BACKTRACK: If transcript contains self-correction cues — "actually", "scratch that", "I mean", "I mean actually", Tagalog "hindi pala", "teka", or a restatement with same intent — discard the superseded span and keep only the corrected version using full utterance context. Example: "punta tayo sa meeting tomorrow actually sa Friday na lang pala" → keep only "punta tayo sa meeting sa Friday na lang pala".
3. SMART FORMATTING (deterministic + infer):
   - Infer sentence punctuation (. , ? !), capitalization (sentence start, proper nouns, "I"), paragraph breaks on long pauses / topic shift.
   - Lists: detect "first … second … third" / "isa, dalawa" enumerations → bulleted or numbered list with line breaks.
   - Emails/phones/URLs: "john dot doe at gmail dot com" → "john.doe@gmail.com"; "nine one seven" + phone context → digits. Do not hallucinate domains.
   - Acronyms and code: keep casing as typed (e.g., "niri", "PipeWire").
4. CURSOR CONTEXT: Use the provided cursor_context to set casing/spacing/prefix. If cursor is mid-word, do not add leading space. If preceding char is not space/newline, prepend one space unless the polished text starts with punctuation. For app_category=Email: use formal paragraph style; Work/Personal messaging: keep compact single paragraph unless list; Other: default sentence case.
5. OUTPUT CONTRACT: Output ONLY the polished text. No preamble ("Here is…"), no quotes, no markdown code fences, no explanation, no translation, no trailing period if the polish ends with list/email. If input is empty or only fillers, output empty string.

FEW-SHOT (do not translate — preserve language):

[EN WITH FILLER+EMAIL]
cursor_context: left="Hi Priya, " right="" app=Email
transcript: "um hello actually hi this is john comma can you send me the file at john dot doe at gmail dot com"
→ "Hi, this is John. Can you send me the file at john.doe@gmail.com?"

[TL WITH BACKTRACK]
cursor_context: left="" right="" app=Other
transcript: "ah magandang umaga po ah nag aano ako nag aalangan ako actually nag-aalangan na baka hindi tayo matuloy"
→ "Magandang umaga po. Nag-aalangan na baka hindi tayo matuloy."

[TAGLISH WITH CODE-SWITCH + BACKTRACK]
cursor_context: left="" right="" app=Work messaging
transcript: "punta tayo sa meeting tomorrow um actually sa friday na lang pala and bring yung report"
→ "Punta tayo sa meeting sa Friday na lang pala and bring yung report."

[APP CATEGORY AWARE]
cursor_context: left="Re: Budget review\\n" right="" app=Email
transcript: "hi team first quarter results are good second we need to cut costs third lets meet next week"
→ "Hi team,\\n\\nFirst quarter results are good.\\nSecond, we need to cut costs.\\nThird, let's meet next week."

USER:
cursor_context: <<<CURSOR_CONTEXT>>>
transcript: <<<TRANSCRIPT>>>

ASSISTANT: (polished text only)"""

COMMAND_PROMPT = """You are YAWC Command — edit ONLY the selected text. Never translate Taglish. Output polished text only.
Apply the spoken instruction to the selected text. Output ONLY the resulting text, no explanation, no quotes.
/no_think"""

# Precompiled regular expressions for fast path
_CUES_RE = re.compile(r"\b(actually|scratch that|i mean|hindi pala|teka|first|second|third|dot)\b", re.I)
_FILLER_RE = re.compile(r"\b(um|uh|ah|hmm)\b[,\s]*", flags=re.I)
_MULTI_WS_RE = re.compile(r"\s+")
_PUNCT_CLEAN_RE = re.compile(r"\s+([,.!?])")
_CAP_START_RE = re.compile(r"(^|[.!?]\s+)(\w)")
_STANDALONE_I_RE = re.compile(r"\bi\b")
_THINK_RE = re.compile(r"<think>.*?</think>", flags=re.S)

# Mtime-aware configuration cache
_CONFIG_CACHE: dict[str, tuple[pathlib.Path, int, any]] = {}
_HW_PAT_CACHE: tuple[str, list[tuple[re.Pattern, str]]] | None = None
_http_conn: http.client.HTTPConnection | None = None


def _config(name: str) -> pathlib.Path:
    p = CONFIG_DIR / name
    return p if p.exists() else REPO_CONFIG / name


def _read_config_json(name: str):
    path = _config(name)
    try:
        if not path.exists():
            return None
        mtime = path.stat().st_mtime_ns
        cached = _CONFIG_CACHE.get(name)
        if cached and cached[0] == path and cached[1] == mtime:
            return cached[2]
        data = json.loads(path.read_text())
        _CONFIG_CACHE[name] = (path, mtime, data)
        return data
    except Exception:
        return None


def load_hotwords() -> str:
    data = _read_config_json("dictionary.json")
    if data and isinstance(data, list):
        try:
            return " ".join(x["term"] for x in data)
        except Exception:
            pass
    return "Priya kamag-anak hanggang ngayon"


def _get_hotword_patterns() -> list[tuple[re.Pattern, str]]:
    global _HW_PAT_CACHE
    hw_str = load_hotwords()
    if _HW_PAT_CACHE and _HW_PAT_CACHE[0] == hw_str:
        return _HW_PAT_CACHE[1]
    pats = [(re.compile(re.escape(hw), flags=re.I), hw) for hw in hw_str.split() if hw]
    _HW_PAT_CACHE = (hw_str, pats)
    return pats


def expand_snippets(text: str) -> str:
    # 06: voice cue -> full formatted text, applied post-STT pre-polish
    snips = _read_config_json("snippets.json")
    if not snips or not isinstance(snips, dict):
        return text
    low = text.lower()
    for cue, body in snips.items():
        if cue.lower() in low:
            text = re.sub(re.escape(cue), body, text, flags=re.I)
    return text


def regex_polish(text: str, cursor_left: str = "") -> str:
    # 02 deterministic fallback — 5ms, meaning-preserving only
    if not text.strip():
        return ""
    t = _FILLER_RE.sub("", text)
    t = _MULTI_WS_RE.sub(" ", t).strip()
    t = _PUNCT_CLEAN_RE.sub(r"\1", t)
    t = _CAP_START_RE.sub(lambda m: m.group(1) + m.group(2).upper(), t)
    t = _STANDALONE_I_RE.sub("I", t)  # English standalone i is always capital
    for pat, hw in _get_hotword_patterns():
        t = pat.sub(hw, t)
    if t and t[-1] not in ".!?":
        t += "."
    if cursor_left and cursor_left[-1].isalnum() and t and t[0].isalnum():
        t = " " + t
    return t


def _strip_think(s: str) -> str:
    # Qwen3 may emit <think> even with /no_think — never paste it
    return _THINK_RE.sub("", s).strip()


LLM_PIDFILE = pathlib.Path("/tmp/yawc-llama.pid")
_LLM_ARGV = [str(LLM_BIN), "-m", str(LLM_MODEL), "-c", "2048", "-ngl", "99",
             "--host", "127.0.0.1", "--port", str(LLM_PORT), "-fa", "on", "-ctk", "q8_0"]


def llm_alive() -> bool:
    # the running server is the state — port health, not any Python global
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{LLM_PORT}/health", timeout=0.2)
        return True
    except Exception:
        return False


def _spawn_llm():
    # single spawn site; pidfile makes release work across processes
    if not (pathlib.Path(LLM_BIN).exists() and LLM_MODEL.exists()):
        return None
    proc = subprocess.Popen(_LLM_ARGV,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    LLM_PIDFILE.write_text(str(proc.pid))
    return proc


def _ensure_server(timeout_s: float = 0.3) -> bool:
    """True when a server answers :8934. Short budget: cold load must not eat
    the polish deadline — first utterance falls back to regex while the model
    finishes loading in background."""
    if llm_alive():
        return True
    proc = _spawn_llm()
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if llm_alive():
            return True
        time.sleep(0.05)
    return proc is not None and proc.poll() is None


def release_llm():
    # kill by pidfile so any process can tear down any server (orphans included)
    try:
        os.kill(int(LLM_PIDFILE.read_text()), 15)
    except Exception:
        pass
    LLM_PIDFILE.unlink(missing_ok=True)


def preload_llm():
    # both models fit this card (whisper ~1.1G + llama ~1.45G + desktop ≈ 3.5/4G).
    # Long-lived daemons call this once at startup; one-shot CLIs never do.
    if not llm_alive():
        _spawn_llm()


def _get_http_conn(timeout_s: float) -> http.client.HTTPConnection:
    global _http_conn
    if _http_conn is None:
        _http_conn = http.client.HTTPConnection("127.0.0.1", LLM_PORT, timeout=timeout_s)
    else:
        _http_conn.timeout = timeout_s
    return _http_conn


def _chat(messages: list, timeout_s: float) -> str:
    # /no_think: Qwen3 soft switch — thinking would eat max_tokens, content comes back empty
    messages = messages[:-1] + [{"role": messages[-1]["role"],
                                 "content": messages[-1]["content"] + "\n/no_think"}]
    body = json.dumps({"messages": messages, "temperature": 0.0, "top_p": 0.8,
                       "max_tokens": 160, "repeat_penalty": 1.05}).encode()
    headers = {"Content-Type": "application/json", "Connection": "keep-alive"}

    global _http_conn
    conn = _get_http_conn(timeout_s)
    try:
        conn.request("POST", "/v1/chat/completions", body=body, headers=headers)
        resp = conn.getresponse()
        if resp.status == 200:
            data = json.loads(resp.read().decode())
            return data["choices"][0]["message"]["content"]
    except Exception:
        # Reconnect once on broken socket / server bounce
        try:
            conn.close()
        except Exception:
            pass
        _http_conn = http.client.HTTPConnection("127.0.0.1", LLM_PORT, timeout=timeout_s)
        _http_conn.request("POST", "/v1/chat/completions", body=body, headers=headers)
        resp = _http_conn.getresponse()
        if resp.status == 200:
            data = json.loads(resp.read().decode())
            return data["choices"][0]["message"]["content"]
    raise RuntimeError("LLM request failed")


def _vram_free_mb() -> int | None:
    # 08: free VRAM <900MB -> force regex path (LLM would OOM-swap)
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.free",
                              "--format=csv,noheader,nounits"], capture_output=True,
                             text=True, timeout=0.2)
        return int(out.stdout.strip().splitlines()[0])
    except Exception:
        return None


def llm_polish(text: str, cursor_context, timeout_ms: int = 600) -> str:
    """cursor_context: context.CursorContext (or its prompt_header str)."""
    if not text.strip():
        return ""
    header = cursor_context.prompt_header() if hasattr(cursor_context, "prompt_header") else str(cursor_context)
    # contract: read cursor_left off the object — never re-parse the rendered header
    cur = getattr(cursor_context, "cursor_left", "") or ""
    # 02 deterministic fast path: short utterance, no backtrack/list cues -> regex only
    cues = _CUES_RE.search(text)
    words = text.split()
    if len(words) <= 25 and not cues:
        return regex_polish(text, cur)
    # VRAM gate guards cold spawns only — an already-running server costs no new VRAM
    if not llm_alive():
        free = _vram_free_mb()
        if free is not None and free < 900:
            return regex_polish(text, cur)
    if not _ensure_server():
        return regex_polish(text, cur)
    try:
        out = _chat([{"role": "system", "content": SYSTEM_PROMPT},
                     {"role": "user", "content": f"cursor_context: {header}\ntranscript: {text}"}],
                    timeout_s=timeout_ms / 1000)
        return _strip_think(out) or regex_polish(text, cur)
    except Exception:
        return regex_polish(text, cur)


def transform_text(text: str, mode: str = "concise") -> str:
    # 05: 3 shipped + custom from transforms.json; instruction may be free speech (command mode)
    prompts = {"concise": "Make this about 30% shorter. Keep every fact. Keep Taglish.",
               "reword": "Reword clearly, same length, fix grammar. Keep Tagalog/English mix.",
               "structure": "Turn into bullets or short paragraphs where it helps. Keep Taglish."}
    custom_data = _read_config_json("transforms.json")
    if custom_data and isinstance(custom_data, dict):
        for c in custom_data.get("custom", []):
            if isinstance(c, dict) and "name" in c and "prompt" in c:
                prompts[c["name"]] = c["prompt"]
    instruction = prompts.get(mode, mode)  # unknown mode = free-text instruction (05)
    if not _ensure_server():
        return _regex_transform(text, mode)
    try:
        out = _chat([{"role": "system", "content": COMMAND_PROMPT},
                     {"role": "user", "content": f"Instruction: {instruction}\n\nSelected text:\n{text}"}],
                    timeout_s=1.5)
        return _strip_think(out) or _regex_transform(text, mode)
    except Exception:
        return _regex_transform(text, mode)


def _regex_transform(text: str, mode: str) -> str:
    # deterministic mimic when no LLM — never blocks, never invents
    t = regex_polish(text)
    if mode == "concise":
        words = t.split()
        if len(words) > 10:
            t = " ".join(words[: int(len(words) * 0.7)]) + "."
    elif mode == "structure":
        t = re.sub(r"\bfirst\b", "- First", t, flags=re.I)
        t = re.sub(r"\bsecond\b", "- Second", t, flags=re.I)
        t = re.sub(r"\bthird\b", "- Third", t, flags=re.I)
    return t
