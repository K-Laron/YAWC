# Handoff — Wispr Flow Local Clone (Wayfinder Charted)

**Date:** 2026-08-24 19:54 UTC
**Source conversation:** wayfinder charting for 100% offline local Wispr Flow clone (EN+TL+Taglish)
**Machine:** CachyOS Linux rolling, niri/Wayland, i5-11400H 6c/12t, 15 GiB RAM (~6 avail), RTX 3050 Laptop 4GB (CUDA 13.3, compute 8.6, ~2.8 GiB free), 671 GiB free, PipeWire 1.6.8, Python 3.14, Node 26, no torch/ollama/whisper yet

## What happened

1. **Research pass** — inventoried Wispr Flow's 6 pillars from docs + 2026 comparisons:
   - hold→release dictation (not streaming) → paste via clipboard, <700 ms target
   - Smart Formatting + Backtrack (`actually`/`scratch that`), Context Awareness (app+cursor+screenshot+file names → cloud unless Privacy Mode), personal/team dict + snippets, Command Mode (`Fn+Ctrl`) + Transforms, Notetaker (Mac-only recorder + MCP)
   - 100+ langs but only 10 with dedicated formatting (EN/FR/DE/HI/IT/PT/ES/TH/JA/KO); Tagalog uses general formatting, highest ASR confidence does NOT include Taglish; cloud-only, no offline
   - No TTS in Wispr — user wants it as extra (deferred to Phase 2)
   - Verified local TTS gap: `rhasspy/piper` has no `tl_PH` voice; `facebook/mms-tts-tgl` is viable Tagalog TTS; `XTTS-v2` has no Tagalog

2. **Wayfinder charting** — two grilling rounds + domain-modeling to lock destination:
   - **Destination:** buildable spec + ordered ticket sequence for 100% offline clone on this machine only, Phase 1 = parity minus Notetaker/MCP minus TTS; true Taglish mid-sentence required; hold+double-tap with tray toggle fallback; full local Context Awareness (screenshot stays on-device); dictation polish only (no meeting analysis) in Phase 1; <1 s for short dictations
   - Answers: spec+tickets, full parity minus Notetaker, Taglish required, 100% offline after install, this machine only, hold+toggle fallback, full context local, polish only, <1 s, TTS deferred
   - **Map created** at `/home/enne/wispr-flow-local-wayfinder/map.md` (label `wayfinder:map`) + 9 tickets in `/home/enne/wispr-flow-local-wayfinder/issues/`

## Artifacts (reference, do not duplicate)

- **Wayfinder map:** `/home/enne/wispr-flow-local-wayfinder/map.md` — Destination, Notes, Decisions so far (empty), Not yet specified (fog), Out of scope
- **Tickets (child issues of map):**
  - `issues/01-stt-engine-taglish.md` — `wayfinder:research` — frontier — engine/model for Taglish
  - `issues/02-local-llm-polish.md` — `wayfinder:research` — frontier — local LLM for Smart Formatting/Backtrack
  - `issues/03-wayland-niri-hotkey-injection.md` — `wayfinder:prototype` — frontier — niri hold/double + `wtype`/`ydotool` injection (hardest platform risk)
  - `issues/07-taglish-eval-harness.md` — `wayfinder:research` — frontier — harness from `sapinsapin/pld` + `halo-livestream`
  - `issues/04-context-awareness-local.md` — `wayfinder:grilling` — blocked by 03
  - `issues/05-command-mode-transforms.md` — `wayfinder:grilling` — blocked by 02+04
  - `issues/06-personal-dictionary-hotwords.md` — `wayfinder:task` — blocked by 01
  - `issues/08-vram-latency-strategy.md` — `wayfinder:task` — blocked by 01+02+07
  - `issues/09-packaging-permissions.md` — `wayfinder:task` — blocked by 03+08
- **This handoff:** `/tmp/opencode/handoff-wispr-flow-local-2026-08-24.md`

## Frontier right now

Takeable (unblocked, unclaimed):
- 01 STT engine Taglish
- 02 Local LLM polish
- 03 Wayland niri hotkey/prototype (recommend first — platform risk)
- 07 Taglish eval harness

Blocked:
- 04, 05, 06, 08, 09 (see map for edges)

Fog (will graduate as frontier clears):
- mic/whisper-mode tuning, hotkey ergonomics, dictionary learning loop, code-mode file tagging, latency proof method, privacy proof artefact, Phase 2 Notetaker/MCP + TTS sketch

Out of scope (Phase 1):
- Cloud STT/LLM, cross-device sync, team/enterprise SSO, mobile/Windows/macOS clients, Phase 2 Notetaker+TTS build

## User's next intent

- User will create a **new project folder** and send its path. Next agent should **move/copy** `wispr-flow-local-wayfinder/` (map + issues) into that folder, adjust to tracker's local-markdown location if needed, and prepare a plan file there (plus this handoff reference). No code yet — map is done, execution waits.

## How to continue

1. Await `New project location: /path/to/folder` from user.
2. `mkdir -p /path/to/folder && cp -r /home/enne/wispr-flow-local-wayfinder/. /path/to/folder/wayfinder/` (or per tracker's expected layout) and copy handoff pointer.
3. If tracker wants git issues, create repo + issues; otherwise keep local-markdown as now.
4. Claim next ticket in order — recommend **03 Wayland prototype** first (validates feasibility) in parallel with **01/02/07 research** subagents (`research` skill).
5. On each ticket close, append one-line gist to map's **Decisions so far** and graduate newly-sharp fog into tickets.

## Suggested skills for next agent

- `grilling` + `domain-modeling` — for 04 and 05 (context depth, command-mode decisions)
- `research` — for 01, 02, 07 (STT/LLM/harness facts, branch `research/<name>`)
- `prototype` — for 03 (niri hotkey + injection runnable proof, 30-sec capture)
- `implement` — only after map 100% decided, to build tracer (not now)
- `wayfinder` — to work through map ticket-by-ticket after project folder move

## Notes / cautions

- No sensitive keys/PII in artifacts; map is local-only privacy-verifiable design
- Keep Wayfinder rule: refer to tickets by **name** not bare number in user-facing narration
- Don't hand-resolve more than one ticket per session (research parallel exception allowed)
