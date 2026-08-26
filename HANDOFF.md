# Handoff — YAWC Phase 1 built and gated

**Date:** 2026-08-26
**Machine:** CachyOS rolling, niri/Wayland, i5-11400H, 15 GiB RAM, RTX 3050 Laptop 4GB (CUDA 13.3), PipeWire
**Models:** `~/.local/share/yawc/models/` — faster-whisper-large-v3-turbo (1.6G) + Qwen3-1.7B-Q4_K_M.gguf (1.2G)

## Live state

- **Working end-to-end**: Right Alt hold → speak → release → polished paste into focused app. Proven in the wild by Kenneth's own dictation.
- **Services** (`systemctl --user`): `yawc-evdev` (hold capture + STT resident), `yawc-pill` (overlay). Both active; evdev preloads llama-server once at startup — warm all day.
- **Latency** (`~/.local/share/yawc/latency.log`, JSONL per utterance): simple ~0.94s E2E warm (regex fast path), backtrack +~200ms LLM (~700ms first uncached hit).
- **Eval gates all pass**: EN WER 6.9% (<8) · TL CER 8.9% (<12) · Taglish CER 3.9% (<25) · DNT 1.0 (≥0.9) · boundary 1/1 (≥0.75). Run: `python3 -m eval.harness --harness eval/harness.jsonl`.
- **Offline proof**: `packaging/offline-proof.sh` → PASS, no egress outside loopback.
- **VRAM**: both models resident ≈ 3355/4096 MiB — [eval/vram-baseline.json](eval/vram-baseline.json).

## Architecture as built (differs from early tickets where noted)

- **LLM server lifecycle**: the running server IS the state. `polish.llm_alive()` = port health on :8934; teardown via `/tmp/yawc-llama.pid` (works cross-process, kills orphans); single spawn site (`_spawn_llm`, argv `-c 2048 -ngl 99 -fa on -ctk q8_0`); preloaded at daemon startup only. Recorder no longer touches it.
- **Polish routing** (`llm_polish`): ≤25 words without backtrack/list cues → regex (<5ms). Otherwise LLM (1500ms cap → regex fallback). VRAM gate guards cold spawns only. `/no_think` appended to every chat turn.
- **Backtrack verified live**: "punta tayo sa meeting tomorrow actually sa Friday na lang pala" → "Punta tayo sa meeting sa Friday na lang pala."
- **CUDA preload** in stt.py: pip nvidia wheels loaded RTLD_GLOBAL before faster-whisper touches CUDA.
- **Deep modules**: stt.py and pill.py are the template — tiny interfaces, hardware seams hidden.

## Open items

1. **Dogfooding** (Kenneth): command mode (Ctrl+Alt+X hold), transforms (Mod+Shift+T/R/S), snippets, natural backtrack — a week of real use decides everything below.
2. **Boundary corpus thin**: 1 kamag-anak, 0 hanggang ngayon utterances; research/07 wants ≥4. Record more via `eval/record.py`.
3. **Deferred refactor — command pipeline**: `command_release` bypasses Dictation (no backtrack/context). Fold into Utterance.transform_mode when usage justifies.
4. **Deferred refactor — pill ownership**: pill written from Dictation AND Recorder (double polished(), idle-after-sleep(2)). Move all UI writes into Recorder.
5. **Minor**: injection re-walks context for password guard (~80ms, TOCTOU regardless); personal hotwords (Kenneth/EDSA) live in repo config fallback until install.sh ships defaults.

## Recent history (2026-08-26 session)

LLM polish had never actually run — ctx512 rejected the >512-token prompt (HTTP 400)
and regex silently substituted. Fixed via c2048 + /no_think + preload + gate fix,
then the lifecycle was rebuilt around port-health truth after a three-agent review
(standards/spec/architecture) converged on that seam. Commits aa633b0..122a046.

## Conventions

- Wayfinder tickets are decision records: append "Implementation revision" sections, never rewrite history.
- `ponytail:` comments mark deliberate simplifications with upgrade paths.
- Tests: `python3 tests/test_yawc.py` — one runnable check per non-trivial module, no framework.
