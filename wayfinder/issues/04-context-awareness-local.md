# Local Context Awareness depth and privacy boundary

**Type:** `wayfinder:grilling` — HITL (needs your call)
**Status:** closed — resolved 2026-08-24, research at `research/04-context-awareness-local.md`
**Blocks:** 05-command-mode-transforms (context passed to LLM)
**Resolution:** Phase 1 keep a+b+c (app via niri msg 10ms + cursor via at-spi 40ms + IDE file names 20ms =70ms ≤80ms), defer screenshot to Phase 2; 4 categories mapped, privacy toggle on-device only, excluded password/URL, audit 14d; evidence [research/04-context-awareness-local.md](../../research/04-context-awareness-local.md) — appended to map.

## Question

You chose **full Wispr parity local** (app name + cursor text + IDE file names + screenshot, kept on-device). Exactly where is the line, so Phase 1 is useful without being creepy, and implementable on niri?

Decide:

- Sources: (a) active app/website name via `niri msg` + AT-SPI, (b) cursor-adjacent text (before/after selection) via `at-spi2` / `wl-clipboard` before snapshot, (c) IDE file names in Cursor/VS Code/neovim (file must have extension, start with letter), (d) screenshot via `grim` + `slurp` (region) vs full window — does (d) stay or drop for Phase 1?
- Budget: context read must not slow dictation — Wispr skips if not quick. Define timeout (e.g., 80 ms) and skip rule.
- Categories: keep Wispr's 4 buckets (Email/Work msg/Personal/Other + browser site sniff) for style switching; map niri app IDs to them; define per-category style (Formal/Casual) for EN vs TL
- Privacy: screenshot + textbox contents never leave device; explicit toggle in Settings → Data, excluded fields (password, banking, URL bar) parity list; audit log of what was read per dictation

Deliver context spec table (source | how | timeout | when skipped) + privacy toggle wording + example: dictating email to `Priya` pulls recipient name from cursor context.

## Why this is blocked

Needs 03's proven injection/accessibility channel; can't decide AT-SPI vs screenshot until hotkey prototype proves what's grabbable on niri.

## Call

Grilling session — call `grilling` + `domain-modeling` to lock terms (`Context`, `Selection`, `App Category`) and write to `CONTEXT.md` inline.
