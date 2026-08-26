# YAWC

Hold a key, talk, get typed text. Anywhere on your desktop. 100% offline.

The local Wispr Flow clone for **CachyOS + niri + RTX 3050 4GB** — English, Tagalog, and real mid-sentence Taglish. Your audio never leaves the machine, and there's a shell script that proves it.

---

## So... what is YAWC? A Wispr clone?

Kind of? Wispr Flow without the parts you can't have: no cloud, no account, no metering, no meeting recorder. What you get instead:

- **Hold-to-dictate anywhere** — Right Alt hold → talk → release → polished text lands in whatever app has focus. Email, Slack, terminal, doesn't matter.
- **Smart Formatting + Backtrack** — *"punta tayo sa meeting tomorrow actually sa Friday na lang pala"* becomes *"Punta tayo sa meeting sa Friday na lang pala."* It drops the cancelled plan, keeps the Taglish, translates nothing.
- **Real Taglish support** — Wispr's 100 languages don't include mid-clause code-switch. This does, because it was built by someone who says *"nag-send mo na ba kay Priya"* out loud.
- **Context Awareness, locally** — knows Gmail from Slack from your IDE and adjusts tone. Reads your cursor text too. On-device only.
- **Command Mode & Transforms** — select text, hold Ctrl+Alt+X, say *"make this shorter"*. Or tap Mod+Shift+T/R/S.
- **Personal dictionary** — Kenneth, Priya, kamag-anak come out spelled right because they're hotwords, not hopes.
- **Snippets** — say *"add disclaimer"*, get the whole paragraph.

This is **NOT** a product. There's no sync, no team plan, no enterprise tier. It's one opinionated tool tuned to exactly one laptop, because that's the whole point.

## YAWC Axioms

We'll be frank — this is an *opinionated project*. Three beliefs drive every decision:

### 1. Offline Means Offline

Privacy isn't a toggle called Privacy Mode. After install, STT and LLM run on-device and `packaging/offline-proof.sh` shows zero non-loopback sockets. Not policy. Architecture. If a feature needs the internet, it doesn't ship.

### 2. Taglish Is First-Class

Code-switching is not a translation problem. *"Nag-send mo na ba yung file"* must never become *"Did you send the file"*. Every model choice, prompt, and eval gate exists to protect the switch. The do-not-translate gate fails the build at <0.90.

### 3. One Machine, Deep Modules

This is optimized for exactly one box (specs below). No config matrix, no portability layer. In exchange: every module hides its mess behind a tiny interface, and every claim has a number behind it.

## The numbers

Not vibes. Gates:

| Gate | Score | Threshold |
|---|---|---|
| English WER | 6.9% | <8% |
| Tagalog CER | 8.9% | <12% |
| Taglish CER | 3.9% | <25% |
| Do-not-translate | 100% | ≥90% |
| Boundary (kamag-anak) | 1/1 | ≥75% |

Latency, warm: **~0.94s** hold-release-to-text for short dictations (Wispr target: <1s on local hardware).

## Getting Started

One-time setup on the target machine:

```bash
git clone <this repo> && cd YAWC
./packaging/install.sh          # deps check, units, niri binds, wizard
```

Then download models once (you, online, ~3GB):

```bash
huggingface-cli download Systran/faster-whisper-large-v3-turbo \
  --local-dir ~/.local/share/yawc/models/faster-whisper-large-v3-turbo
huggingface-cli download bartowski/Qwen3-1.7B-GGUF Qwen3-1.7B-Q4_K_M.gguf \
  --local-dir ~/.local/share/yawc/models
```

Full instructions including llama.cpp CUDA build: [`INSTALL.md`](INSTALL.md).

## Daily driver

| Action | Input |
|---|---|
| Dictate | hold **Right Alt**, talk, release |
| Command mode | select text, hold **Ctrl+Alt+X**, say what to do |
| Transforms | select text, tap **Mod+Shift+T** / **R** / **S** |
| Snippet | just say the cue — *"add disclaimer"* |

## Under the hood

faster-whisper large-v3-turbo (`int8_float16` CUDA) → Silero VAD → regex fast path (<5ms) or llama.cpp Qwen3-1.7B c2048 for backtrack and long-form → clipboard paste with restore via `wtype`. Both models resident on the same 4GB card as your wallpaper engine ([measured](eval/vram-baseline.json)). LLM server preloads at boot and answers health checks; if VRAM pressure ever kills it, polish degrades to regex instead of crashing. Every utterance logs phase timings to `~/.local/share/yawc/latency.log`.

## Where to look

- [`HANDOFF.md`](HANDOFF.md) — live state, open items, fresh-agent orientation
- [`wayfinder/map.md`](wayfinder/map.md) — decision record: 9 closed tickets, fog, revisions
- [`CONTEXT.md`](CONTEXT.md) — domain glossary
- [`eval/harness.py`](eval/harness.py) — the five gates above, runnable, <2min

## Why "YAWC"?

Yet Another Wispr Clone. Honest, meme-y, pronounceable — keeps the ambition in check. We know the giants exist. We just want it local, private, and speaking Taglish properly.
