# Command Mode + Transforms voice-editing

**Type:** `wayfinder:grilling` — HITL
**Status:** closed — resolved 2026-08-24, research at `research/05-command-mode-transforms.md`
**Blocks:** none
**Resolution:** Ctrl+Win+Alt hold command separate from dictation, 3 shipped +3 custom transforms, wl-copy -p → LLM → wtype replace, 600ms timeout, local ≤500 guard, diff+Undo; evidence [research/05-command-mode-transforms.md](../../research/05-command-mode-transforms.md) — appended to map.

## Question

What is the Phase 1 **voice-editing** surface that matches Wispr's Command Mode (`hold Fn+Ctrl → "make last sentence shorter" → release`) + Transforms (highlight → hotkey → LLM rewrite) but with a local LLM and <1 s?

Decide:

- Triggers: separate hold (`Ctrl+Win+Alt` on niri) vs same hold with mode verb; `Esc` cancel; "press enter" voice submit at end (case-insensitive, punctuation handling)
- Scope: which edits are reliable locally — reword, shorten, bulletify, fix grammar, translate EN↔TL (prompt only, not STT) — and which to defer (move bullet, bold phrase needing app semantics)
- Transform UX: 5 default prompts vs 3 shipped (concise/reword/structure) + up to 5 custom with 50-500 word samples; where prompt lives (JSON), how diff viewer shows add/remove with Undo/Copy/Thumbs
- Selection flow: `wl-copy -p` grab → LLM → `wtype` replace vs clipboard; failure toast + manual paste fallback; what apps are unsupported (custom editors)

Deliver voice-edit spec: hotkey map (niri binds), prompt list with exact wording, selection→LLM→replace sequence diagram, and "local edits only" guard (visible text / last dictation) to avoid far-cursor mistakes.

## Why this is blocked

Needs 02's LLM runtime/prompt shape and 04's context/select plumbing. Grilling — prototype a prompt with 2 samples and react.

## Call

Call `grilling` + `domain-modeling` + `prototype` (cheap Tauri command that runs prompt on selected text) and capture decision.
