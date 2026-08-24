# Wispr Flow Local Clone — Wayfinder Map

## Destination

A buildable **spec + ordered ticket sequence** for a **100% offline** (no audio/text leaves device after install) Wispr Flow clone **optimized for this machine only**: CachyOS Linux + niri/Wayland + i5-11400H/15GB RAM/RTX 3050 4GB + PipeWire. Phase 1 delivers Wispr parity **minus Notetaker/MCP and minus TTS**: system-wide **hold→release dictation + double-tap hands-free (with tray toggle fallback)** in any app via local injection, **Smart Formatting + Backtrack**, **full local Context Awareness** (app name + cursor text + IDE file names + screenshot, kept on-device), **personal/team dictionary + snippets**, and **Command Mode / Transforms voice-editing**, all handling **English + Tagalog with true Taglish code-switch mid-utterance** and targeting **<1s paste after release for short dictations**. On reaching the destination the map is done: no code is written, but any engineer can implement Phase 1 from the decisions without reopening fundamentals. Phase 2 (meeting Notetaker + local TTS proof-read) is sketched as fog.

## Notes

- **Domain:** offline voice dictation + local LLM polish + Wayland OS glue
- **Skills every session should consult:** `grilling` + `domain-modeling` (always), `research` for STT/LLM/TTS facts, `prototype` for niri hotkey/injection and context-reading proofs, `implement` only after map complete
- **Standing preferences (Kenneth):** YAGNI/simplicity first; privacy = verifiable offline not policy toggles; truthful claims with evidence matching claim; reuse existing Arch/CachyOS + Tauri/Rust conventions before abstractions; surgical changes; prefer local state; never touch production/live data without explicit request
- **Machine truth (2026-08-24):** CachyOS rolling, Wayland `niri` + `xwayland`, PipeWire 1.6.8, `RTX 3050 Laptop 4GB` (CUDA 13.3, compute 8.6, ~2.8GB free under wallpaper engine), 15 GiB RAM (~6 avail), 671 GiB free, no torch/ollama/whisper installed yet, `wtype`/`ydotool` not yet verified, Docker 29.7 available
- **Wispr invariants to match/parity check:** hold-release full-context (not streaming), <700 ms Wispr target → <1 s local target for short utterances, clipboard paste with restore, 100+ langs (our scope EN+TL only), context categories Email/Work/Personal/Other, style per category (EN/desktop)
- **Label convention:** map `wayfinder:map`, tickets `wayfinder:research|prototype|grilling|task`

## Decisions so far

<!-- one line per closed ticket, gist + link; empty at charting -->

- [STT engine and model for EN + TL + Taglish](issues/01-stt-engine-taglish.md): **faster-whisper + whisper-large-v3-turbo `int8_float16` CUDA + Silero VAD ONNX, PipeWire 16kHz mono hold-release, language=None + initial_prompt/hotwords for kamag-anak boundaries, task=transcribe to block translation hallucination; fallback turbo-int8 → medium → small-pld-fil → whisper.cpp CPU** — fits 2.8GB VRAM (~2.0–2.6GB), <1s for ≤12s dictations, 100% offline verified; research at [research/01-stt-engine-taglish.md](../research/01-stt-engine-taglish.md)
- [Local LLM for Smart Formatting, Backtrack, polish](issues/02-local-llm-polish.md): **llama.cpp CUDA + Qwen2.5-7B-Instruct Q4_K_M primary (time-share VRAM with STT, c 512, ngl 99) + Qwen3-1.7B Q4_K_M fallback for <1s (55–75 tok/s GPU), Gemma-3-4B alt for 140-lang coverage; 600ms timeout → regex fallback; prompt preserves Taglish, never translates, handles backtrack/orthography/cursor context** — sequential STT→LLM swap fits 4GB; offline verified; prompt+samples at [research/02-local-llm-polish.md](../research/02-local-llm-polish.md)
- [Taglish evaluation harness and gate](issues/07-taglish-eval-harness.md): **30 wav 16kHz mono local (10 EN /10 TL /10 Taglish mid-clause) + `python -m eval.harness --model large-v3-turbo` scoring WER EN / CER TL&Taglish (jiwer) + do-not-translate ≥0.90 + kamag-anak boundary ≥0.75; gates EN WER<0.08, TL CER<0.12, Taglish CER<0.25; runs <2min, history 14 days pruned; re-record locally, don't train on halo 62 segs** — research at [research/07-taglish-eval-harness.md](../research/07-taglish-eval-harness.md)
- [Wayland + niri global hold/double-tap + injection](issues/03-wayland-niri-hotkey-injection.md): **niri `binds { spawn-sh }` toggle + 300ms double-tap script (hold=tap-toggle, not evdev hold), wtype + wl-copy/wl-paste clipboard restore primary, ydotoold fallback for XWayland; evdev needs `input` group (tested fails without — `evdev.list_devices()==[]`), arecord 16kHz mono works, PipeWire 1.6.8, Tauri 2 tray fallback** — toggle + double-tap/hands-free proven, password field skip, Esc cancel; prototype at [prototype/03-niri-injection/README.md](../prototype/03-niri-injection/README.md) + scripts
- [Local Context Awareness depth](issues/04-context-awareness-local.md): **Phase 1 = app name (niri msg) + cursor ±80 chars (at-spi, 40ms) + IDE file names (whitelist), screenshot deferred to Phase 2; total ≤80ms skip if slow; 4 categories mapped (Email/Work/Personal/Other), on-device only with toggle, password/URL excluded, audit log 14d** — research at [research/04-context-awareness-local.md](../research/04-context-awareness-local.md)
- [Command Mode + Transforms](issues/05-command-mode-transforms.md): **Ctrl+Win+Alt hold separate from dictation CapsLock, Esc cancel, 3 shipped (concise/reword/structure) + 3 custom in transforms.json, wl-copy -p → Qwen3-1.7B → wtype replace, 600ms timeout, local only ≤500 chars, diff view with Undo** — research at [research/05-command-mode-transforms.md](../research/05-command-mode-transforms.md)
- [Personal dictionary, snippets, hotwords](issues/06-personal-dictionary-hotwords.md): **~/.config/yawc/dictionary.json + snippets.json (no DB), faster-whisper hotwords+initial_prompt injection, auto-learn on undo with toast, global vs per-app scope, git import for team** — research at [research/06-personal-dictionary-hotwords.md](../research/06-personal-dictionary-hotwords.md)
- [VRAM partition, model load, <1s strategy](issues/08-vram-latency-strategy.md): **Sequential STT hot 2.0–2.6GB + LLM warm on demand Qwen3-1.7B 1.2GB c512, swap 300ms, regex fallback 5ms, 600ms timeout, 900MB free threshold, pipeline VAD20ms→STT350ms→context70ms→LLM0.4s** — research at [research/08-vram-latency-strategy.md](../research/08-vram-latency-strategy.md)
- [Packaging, autostart, CachyOS perms](issues/09-packaging-permissions.md): **PKGBUILD AUR + bare binary install.sh, systemd --user + niri spawn-at-startup, models ~/.local/share/yawc, deps wtype/wl-clipboard/at-spi2-core, 3-screen wizard (mic→hotkey→test), offline ss -tunap proof, input group optional** — research at [research/09-packaging-permissions.md](../research/09-packaging-permissions.md)

## Not yet specified

<!-- fog: in-scope but not yet sharp enough to ticket; graduates as frontier advances -->

- **Mic / whisper-mode tuning** — built-in vs lav/podcast mic for Tagalog sibilants; distance ~1 cm whisper calibration, VAD thresholds for quiet speech, PipeWire source selection UX
- **Hotkey ergonomics on 11400H keyboard** — which physical keys survive niri/IME conflict; remap story for keyboards without Fn
- **Dictionary learning loop** — how a local correction ("kapatid" not "kasama") becomes a hotword without retraining, where JSON lives, per-app vs global
- **Code-mode file tagging exact** — which file extensions trigger tagging in Cursor/VS Code/neovim, terminal exclusion, tagging when to skip
- **Packaging for arch rolling** — AUR PKGBUILD vs AppImage vs bare binary + systemd user service vs niri autostart, permission grants (input group, AT-SPI, screencopy)
- **Latency proof method** — how to measure <1 s on this hardware (audio stop → paste timestamps), what degrades to rule-based when LLM too slow
- **Privacy proof artefact** — `iptables -C` / `ss -tunap` / Flatpak/no-net manifest that reviewer can run to verify no egress after install
- **Phase 2 sketch:** Notetaker (pyannote diarization + local vector + MCP read-only) and TTS (Piper EN + `facebook/mms-tts-tgl` for TL, voice samples, proof-read UX)

## Out of scope

<!-- ruled beyond Phase 1 destination; never graduates unless destination redrawn -->

- Cloud STT/LLM, cross-device sync, team shared dictionary/enterprise SSO/SAML/SOC2/HIPAA wrapper — local-only replaces them
- Windows/macOS/iOS/Android clients — this machine only (CachyOS/niri)
- Wispr free-tier metering/billing — not a product, a local tool
- Full Phase 2 Notetaker meeting recorder + MCP server and full TTS voice system — Phase 2 effort, not Phase 1 build (tickets closed as out-of-scope for destination and noted in fog)
