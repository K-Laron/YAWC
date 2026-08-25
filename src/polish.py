#!/usr/bin/env python3
# ponytail: Polish deep module per 02/05/06/08 — regex pass <5ms, llama-server LLM
# warm on demand with 600ms deadline, regex fallback always holds <1s E2E.
# Sequential VRAM per 08: release_llm() before recording frees VRAM for STT.
import json, os, pathlib, re, shutil, subprocess, time, urllib.request

CONFIG_DIR = pathlib.Path.home() / ".config/yawc"
REPO_CONFIG = pathlib.Path(__file__).parent.parent / "config"
LLM_BIN = shutil.which("llama-server") or str(pathlib.Path.home() / ".local/share/yawc/bin/llama-server")
LLM_MODEL = pathlib.Path(os.environ.get("YAWC_LLM_MODEL", pathlib.Path.home() / ".local/share/yawc/models/Qwen3-1.7B-Q4_K_M.gguf"))
LLM_PORT = 8934
_llm_proc = None

# 02 system prompt — verbatim from research/02-local-llm-polish.md (single prompt, no branching)
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

# 05 command base — shared with 02, mode=command
COMMAND_PROMPT = """You are YAWC Command — edit ONLY the selected text. Never translate Taglish. Output polished text only.
Apply the spoken instruction to the selected text. Output ONLY the resulting text, no explanation, no quotes.
/no_think"""


def _config(name: str) -> pathlib.Path:
    p = CONFIG_DIR / name
    return p if p.exists() else REPO_CONFIG / name


def load_hotwords() -> str:
    try:
        rows = json.loads(_config("dictionary.json").read_text())
        return " ".join(x["term"] for x in rows)
    except Exception:
        return "Priya kamag-anak hanggang ngayon"


def expand_snippets(text: str) -> str:
    # 06: voice cue -> full formatted text, applied post-STT pre-polish
    try:
        snips = json.loads(_config("snippets.json").read_text())
    except Exception:
        return text
    low = text.lower()
    for cue, body in snips.items():
        if cue in low:
            text = re.sub(re.escape(cue), body, text, flags=re.I)
    return text


def regex_polish(text: str, cursor_left: str = "") -> str:
    # 02 deterministic fallback — 5ms, meaning-preserving only
    if not text.strip():
        return ""
    t = re.sub(r"\b(um|uh|ah|hmm)\b[,\s]*", "", text, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"\s+([,.!?])", r"\1", t)
    t = re.sub(r"(^|[.!?]\s+)(\w)", lambda m: m.group(1) + m.group(2).upper(), t)
    for hw in load_hotwords().split():
        t = re.sub(re.escape(hw), hw, t, flags=re.I)
    if t and t[-1] not in ".!?":
        t += "."
    if cursor_left and cursor_left[-1].isalnum() and t and t[0].isalnum():
        t = " " + t
    return t


def _strip_think(s: str) -> str:
    # Qwen3 may emit <think> even with /no_think — never paste it
    return re.sub(r"<think>.*?</think>", "", s, flags=re.S).strip()


def _ensure_server(timeout_s: float = 0.3) -> bool:
    """Start llama-server warm (08: LLM on demand, Qwen3-1.7B 1.2GB c512).
    Short budget: cold load must not eat the 600ms deadline — first utterance
    falls back to regex while the server finishes loading in background."""
    global _llm_proc
    if _llm_proc and _llm_proc.poll() is None:
        return True
    if not (pathlib.Path(LLM_BIN).exists() and LLM_MODEL.exists()):
        return False
    _llm_proc = subprocess.Popen(
        [str(LLM_BIN), "-m", str(LLM_MODEL), "-c", "512", "-ngl", "99",
         "--host", "127.0.0.1", "--port", str(LLM_PORT), "-fa", "on", "-ctk", "q8_0"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{LLM_PORT}/health", timeout=0.2)
            return True
        except Exception:
            time.sleep(0.05)
    return _llm_proc.poll() is None


def release_llm():
    # 08 sequential VRAM: call before recording so STT gets its 2.0-2.6GB back
    global _llm_proc
    if _llm_proc and _llm_proc.poll() is None:
        _llm_proc.terminate()
    _llm_proc = None


def _chat(messages: list, timeout_s: float) -> str:
    req = urllib.request.Request(
        f"http://127.0.0.1:{LLM_PORT}/v1/chat/completions",
        data=json.dumps({"messages": messages, "temperature": 0.0, "top_p": 0.8,
                         "max_tokens": 160, "repeat_penalty": 1.05}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]


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
    cur = _cursor_of(header)
    # 02 deterministic fast path: short utterance, no backtrack/list cues -> regex only
    cues = re.search(r"\b(actually|scratch that|i mean|hindi pala|teka|first|second|third|dot|at)\b", text, re.I)
    words = text.split()
    if len(words) <= 25 and not cues:
        return regex_polish(text, cur)
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


def _cursor_of(ctx: str) -> str:
    m = re.search(r'left="([^"]*)"', ctx)
    return m.group(1) if m else ""


def transform_text(text: str, mode: str = "concise") -> str:
    # 05: 3 shipped + custom from transforms.json; instruction may be free speech (command mode)
    prompts = {"concise": "Make this about 30% shorter. Keep every fact. Keep Taglish.",
               "reword": "Reword clearly, same length, fix grammar. Keep Tagalog/English mix.",
               "structure": "Turn into bullets or short paragraphs where it helps. Keep Taglish."}
    try:
        for c in json.loads(_config("transforms.json").read_text()).get("custom", []):
            prompts[c["name"]] = c["prompt"]
    except Exception:
        pass
    instruction = prompts.get(mode, mode)  # unknown mode = free-text instruction (05)
    if not _ensure_server():
        return _regex_transform(text, mode)
    try:
        out = _chat([{"role": "system", "content": COMMAND_PROMPT},
                     {"role": "user", "content": f"Instruction: {instruction}\n\nSelected text:\n{text}"}],
                    timeout_s=0.6)
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
