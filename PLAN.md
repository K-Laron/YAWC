# YAWC Plan — Points to Wayfinder Map

This file is a pointer. Source of truth is the wayfinder map; this exists so `PLAN.md` is where humans look first.

## Map

→ [`wayfinder/map.md`](wayfinder/map.md)

## State: all 9 tickets closed — Phase 1 built and gated (2026-08-26)

- **Decisions so far:** 9, two with implementation revisions (02 LLM context/timeout, 08 both-resident VRAM)
- **Not yet specified:** fog reduced to mic tuning, hotkey ergonomics, dictionary auto-learning, code-mode tagging, boundary corpus depth, command-mode pipeline shape
- **Out of scope:** cloud, team, mobile, Phase 2

## Tickets

| # | Name | Type | State |
|---|---|---|---|
| 01 | [STT engine and model for EN + TL + Taglish](wayfinder/issues/01-stt-engine-taglish.md) | research | closed |
| 02 | [Local LLM for Smart Formatting, Backtrack, polish](wayfinder/issues/02-local-llm-polish.md) | research | closed + revision |
| 03 | [Wayland + niri global hold/double-tap + injection](wayfinder/issues/03-wayland-niri-hotkey-injection.md) | prototype | closed |
| 07 | [Taglish evaluation harness and gate](wayfinder/issues/07-taglish-eval-harness.md) | research | closed + implemented |
| 04 | [Local Context Awareness depth](wayfinder/issues/04-context-awareness-local.md) | grilling | closed |
| 05 | [Command Mode + Transforms](wayfinder/issues/05-command-mode-transforms.md) | grilling | closed |
| 06 | [Personal dictionary, snippets, hotwords](wayfinder/issues/06-personal-dictionary-hotwords.md) | task | closed |
| 08 | [VRAM partition, model load, <1 s strategy](wayfinder/issues/08-vram-latency-strategy.md) | task | closed + revision |
| 09 | [Packaging, autostart, CachyOS perms](wayfinder/issues/09-packaging-permissions.md) | task | closed |

Live state and open items: [`HANDOFF.md`](HANDOFF.md).
