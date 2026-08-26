# Handoff — YAWC Phase 1 built and gated

**Date:** 2026-08-26
**Machine:** CachyOS rolling, niri/Wayland, i5-11400H, 15 GiB RAM, RTX 3050 Laptop 4GB (CUDA 13.3), PipeWire
**Models:** `~/.local/share/yawc/models/` — faster-whisper-large-v3-turbo (1.6G) + Qwen3-1.7B-Q4_K_M.gguf (1.2G)

## Live state

- **Working end-to-end**: Right Alt hold → speak → release → polished paste into focused app. Proven in the wild by a real dictation.
- **Services** (`systemctl --user`): `yawc-evdev` (hold capture + STT resident, supervisor rescans devices every 5s — survives USB re-enumeration; `Restart=always`), `yawc-pill` (overlay). Both active; evdev preloads llama-server once at startup — warm all day.
- **Latency** (`~/.local/share/yawc/latency.log`, JSONL per utterance): warm short ~0.85–0.95s E2E (regex fast path) after the 2026-08-26 perf pass removed release-path dead waits (recorder stop ~210→~114ms, injection settle poll); backtrack +~400–900ms LLM (live-verified 459ms/905ms polish hits); beam_size=1 tested and rejected (941 vs 906ms mean over eval set — turbo decoder makes beam nearly free).
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

1. **Dogfooding**: command mode (Ctrl+Alt+X hold), transforms (Mod+Shift+T/R/S), snippets, natural backtrack — a week of real use decides everything below.
2. **Boundary corpus thin**: 1 kamag-anak, 0 hanggang ngayon utterances; research/07 wants ≥4. Record more via `eval/record.py`.
3. **Deferred refactor — command pipeline**: `command_release` bypasses Dictation (no backtrack/context). Fold into Utterance.transform_mode when usage justifies.
4. ~~Minor: injection re-walks context for password guard~~ — **resolved 2026-08-26**: one context walk at the composition root (`dictate_and_paste`); `inject(is_password=...)` takes caller facts, `None` falls back to a walk (CLI safe default). Context audit moved inside `get_context` so "every read is audited" holds by construction.
5. **Minor**: personal hotwords (EDSA + a personal name) live in repo config fallback until install.sh ships defaults.

## Architecture as deepened (2026-08-26)

- **Pill has one owner** (closes old Open item 4): Recorder is the sole pill writer — `begin()` shows recording, `release()` shows transcribing → polished → idle tail. Dictation is pure compute (`dictate(Utterance) -> str`, no UI), command mode returns result strings only. The stuck-pill bug class is now structurally unwriteable outside recorder.py. `Pill` added to CONTEXT.md glossary.
- **Recorder interface collapsed** to `begin()` / `release()` (+ `toggle()` wrapper): multi-node press/release guard, pipeline invocation, and outcome tail all live behind two methods; entries hold no lifecycle knowledge.
- **One context walk per dictation**: `get_context()` runs once at the composition root; its facts feed both the polish header and the paste guard. Saves the ~80ms second Atspi walk in non-terminal apps; `is_password=None` keeps injection safe-by-default for CLI callers.

## Recent history (2026-08-26 session)

LLM polish had never actually run — ctx512 rejected the >512-token prompt (HTTP 400)
and regex silently substituted. Fixed via c2048 + /no_think + preload + gate fix,
then the lifecycle was rebuilt around port-health truth after a three-agent review
(standards/spec/architecture) converged on that seam. Commits aa633b0..122a046.

## Performance pass (2026-08-26)

Measured on live hardware; do not re-litigate without new numbers.

- **beam_size 5 vs 1 — REJECTED**: 906ms vs 941ms mean over 30 eval wavs (turbo's
  4-layer decoder makes beam width nearly free). stt.py stays beam_size=5.
- **recorder.stop()** — was pkill + blind `sleep(0.2)` (~210ms every release); now
  stores the Popen handle, `terminate()`→`wait(0.15)`→`kill()` fallback (~114ms,
  SIGTERM lets arecord flush). Regression-checked in tests.
- **injection settle** — fixed 50ms sleep replaced by `_clipboard_settled` poll
  (150ms cap). Discovery: this machine's clipboard manager re-serves text with a
  trailing `\n`, so the poll matches `startswith`, not `==`.
- **Test flake fixed**: "real degrade empty" bound 5s→15s — with the daemon
  resident, real-STT CUDA OOM degrade costs ~4s; bound exists to catch hangs.
- Expected warm E2E ~0.94s → ~0.8s; confirm via next latency.log entries.
- Known long-term lever (unstarted): streaming/partial-decode STT — STT is still
  ~95% of budget and scales with utterance length.

- **evdev supervisor (long-term fix)**: USB receiver re-enumeration killed read
  streams silently while the process stayed alive holding stale fds (2026-08-26
  incident: udevmon bounce + SSCYPL renumber → presses lost, nothing logged).
  evdev_hold now runs a 5s rescan loop respawning per-device handlers and logging
  stream death; died-mid-hold flushes capture + clears pill; Recorder.start is
  idempotent (Rapoo emits RIGHTALT on multiple nodes); unit Restart=always.
  Verify by unplugging/replugging the wireless receiver mid-session.

## Conventions

- Wayfinder tickets are decision records: append "Implementation revision" sections, never rewrite history.
- `ponytail:` comments mark deliberate simplifications with upgrade paths.
- Tests: `python3 tests/test_yawc.py` — one runnable check per non-trivial module, no framework.
