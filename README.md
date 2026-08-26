# YAWC — Yet Another Wispr Clone

100% offline, local-device-only Wispr Flow clone for **CachyOS + niri + RTX 3050 4GB**. English + Tagalog + true Taglish code-switch, no audio ever leaves the machine.

> Name: honest, meme-y, pronounceable. Keeps the ambition in check ("yet another" = we know the giants exist, we just want it local and private). For a private repo it's perfect. If you ever publish, consider `Yawc` (like `awk` family) or a Tagalog-rooted name (`Bulong` — whisper, `Salita` — word) — but `YAWC` as codename ships today.

## Status: Phase 1 built and gated (2026-08-26)

Hold→release dictation works end-to-end on this machine: Right Alt hold → speak →
release → polished text typed into the focused app (~0.94s warm for short
utterances). Backtrack ("actually, sa Friday na lang"), Command Mode, Transforms,
snippets, personal dictionary — all implemented. All five eval gates pass:
EN WER 6.9% (<8), TL CER 8.9% (<12), Taglish CER 3.9% (<25), DNT 1.0 (≥0.9),
boundary 1/1 (≥0.75). Offline proof: `packaging/offline-proof.sh` PASS.

## How it works

```
Right Alt hold → arecord 16k mono → faster-whisper large-v3-turbo (CUDA int8_float16)
  → context (niri focused window + at-spi cursor, local only)
  → polish: regex fast path (<5ms) or llama.cpp Qwen3-1.7B c2048 (backtrack/long-form)
  → wl-copy + wtype ctrl-v (clipboard restored, password fields skipped)
```

Pill overlay (gtk4-layer-shell, bottom center) mirrors state. LLM server preloads
at daemon startup and stays resident; both models fit the 4GB card alongside the
desktop ([eval/vram-baseline.json](eval/vram-baseline.json)).

## Use it

See [`INSTALL.md`](INSTALL.md) for setup. Daily driver binds (niri):

- **Right Alt hold** — dictate
- **Ctrl+Alt+X hold** — command mode ("make this shorter")
- **Mod+Shift+T/R/S** — transform selection (concise/reword/structure)

## Where to look

- **Wayfinder map** (decision record): [`wayfinder/map.md`](wayfinder/map.md)
- **Tickets** (closed decisions + implementation revisions): [`wayfinder/issues/`](wayfinder/issues/)
- **Handoff** (live state for fresh agents): [`HANDOFF.md`](HANDOFF.md)
- **Domain glossary:** [`CONTEXT.md`](CONTEXT.md)
- **Eval:** `python -m eval.harness --harness eval/harness.jsonl` — five gates, <2min

## Machine target

CachyOS rolling, Wayland niri, i5-11400H, 15 GiB RAM, RTX 3050 Laptop 4GB (CUDA 13.3),
PipeWire. All decisions tuned for this box.

## Stack (decided — see tickets 01/02)

- STT: `faster-whisper` large-v3-turbo `int8_float16` CUDA, Silero VAD via vad_filter
- LLM: llama-server + Qwen3-1.7B-Q4_K_M, c2048, `/no_think`, regex fallback always holds
- Injection: `wtype`/`wl-copy` (+ ydotool fallback for XWayland), niri binds
- Services: systemd --user (`yawc-evdev`, `yawc-pill`)

Phase 2 (fog): Notetaker (diarization + MCP) + TTS (`facebook/mms-tts-tgl`).
