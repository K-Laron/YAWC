# YAWC Plan — Points to Wayfinder Map

This file is a pointer. Source of truth is the wayfinder map; this exists so `PLAN.md` is where humans look first.

## Map

→ [`wayfinder/map.md`](wayfinder/map.md)

## How to read it

- **Destination:** 100% offline Wispr parity minus Notetaker/TTS on this CachyOS/niri/RTX 3050 box, Taglish required, <1 s
- **Notes:** skills (`grilling`, `domain-modeling`, `research`, `prototype`), machine truth 2026-08-24
- **Decisions so far:** empty (charted, none closed)
- **Not yet specified:** 9 fog patches (mic tuning, hotkey ergonomics, harness, etc.)
- **Out of scope:** cloud, team, mobile, Phase 2

## Tickets

| # | Name | Type | State |
|---|---|---|---|
| 01 | [STT engine and model for EN + TL + Taglish](wayfinder/issues/01-stt-engine-taglish.md) | research | frontier |
| 02 | [Local LLM for Smart Formatting, Backtrack, polish](wayfinder/issues/02-local-llm-polish.md) | research | frontier |
| 03 | [Wayland + niri global hold/double-tap + injection](wayfinder/issues/03-wayland-niri-hotkey-injection.md) | prototype | frontier — do early |
| 07 | [Taglish evaluation harness and gate](wayfinder/issues/07-taglish-eval-harness.md) | research | frontier |
| 04 | [Local Context Awareness depth](wayfinder/issues/04-context-awareness-local.md) | grilling | blocked by 03 |
| 05 | [Command Mode + Transforms](wayfinder/issues/05-command-mode-transforms.md) | grilling | blocked by 02+04 |
| 06 | [Personal dictionary, snippets, hotwords](wayfinder/issues/06-personal-dictionary-hotwords.md) | task | blocked by 01 |
| 08 | [VRAM partition, model load, <1 s strategy](wayfinder/issues/08-vram-latency-strategy.md) | task | blocked by 01+02+07 |
| 09 | [Packaging, autostart, CachyOS perms](wayfinder/issues/09-packaging-permissions.md) | task | blocked by 03+08 |

Close one per session, append gist to map, graduate fog → new tickets.
