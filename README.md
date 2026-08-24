# YAWC — Yet Another Wispr Clone

100% offline, local-device-only Wispr Flow clone for **CachyOS + niri + RTX 3050 4GB**. English + Tagalog + true Taglish code-switch, no audio ever leaves the machine.

> Name: honest, meme-y, pronounceable. Keeps the ambition in check ("yet another" = we know the giants exist, we just want it local and private). For a private repo it's perfect. If you ever publish, consider `Yawc` (like `awk` family) or a Tagalog-rooted name (`Bulong` — whisper, `Salita` — word) — but `YAWC` as codename ships today.

## Where to look

- **Wayfinder map** (source of truth): [`wayfinder/map.md`](wayfinder/map.md) — destination, decisions, fog, out-of-scope
- **Tickets** (ordered decisions): [`wayfinder/issues/`](wayfinder/issues/) — 9 tickets, 4 on frontier
- **Handoff** (context for fresh agent): [`HANDOFF.md`](HANDOFF.md)
- **Context glossary:** [`CONTEXT.md`](CONTEXT.md)

## Quick start for next session

```bash
# frontier (takeable now, one per session)
cat wayfinder/issues/01-stt-engine-taglish.md        # research — STT engine
cat wayfinder/issues/02-local-llm-polish.md          # research — local LLM
cat wayfinder/issues/03-wayland-niri-hotkey-injection.md  # prototype — niri hold→paste (hardest, do early)
cat wayfinder/issues/07-taglish-eval-harness.md      # research — harness
```

Claim a ticket, resolve it, append one-line gist to `wayfinder/map.md` → `Decisions so far`, graduate fog → new tickets.

## Phase 1 (this map)

Hold→release dictation anywhere + double-tap hands-free (tray fallback) + Smart Formatting/Backtrack + full local Context Awareness + dictionary/snippets + Command Mode/Transforms. <1 s paste. EN+TL+Taglish. 100% offline.

Phase 2 (fog): Notetaker (diarization + MCP) + TTS (`facebook/mms-tts-tgl`).

## Machine target

CachyOS rolling, Wayland niri, i5-11400H, 15 GiB RAM, RTX 3050 Laptop 4GB (CUDA 13.3), PipeWire. All decisions tuned for this box.

## Stack hint (not decided — see tickets 01/02)

- STT: `faster-whisper` + `large-v3-turbo` + Silero VAD
- LLM: `llama.cpp`/`Ollama` + `Gemma-3-4B-Q4` or `Qwen2.5-7B-Q4`
- Injection: `wtype`/`ydotool` + `wl-copy`, `niri` binds, Tauri 2 tray
