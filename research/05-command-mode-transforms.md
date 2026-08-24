# 05 — Command Mode + Transforms Voice-Editing (Phase 1 Decision)

> Ticket: [wayfinder/issues/05-command-mode-transforms.md](../wayfinder/issues/05-command-mode-transforms.md) — HITL grilling
> Decision: **Separate hold for commands, 3 shipped transforms + 3-slot custom, local text only, <1s via Qwen3-1.7B**

## Summary

**Triggers:** `Ctrl+Win+Alt` hold (niri `binds { spawn-sh }`) for Command Mode — separate from dictation `CapsLock` hold (avoids verb ambiguity). Same `Esc` cancel, same `wtype`+`wl-copy` plumbing from 03. "press enter" at end of command = voice key press (handled as literal `wtype -k Return` after transform, not as dictation).

**Scope Phase 1 (reliable locally with Qwen3-1.7B 55-75 tok/s):** reword, shorten, bulletify, fix grammar, expand TL/EN style within selection. **Defer:** move bullet, bold/italic (needs app semantics), EN↔TL translate (prompt only, warn if requested — STT never translates per 02).

**Transform UX:** 3 shipped (`concise`, `reword`, `structure`) + up to 3 custom (50-500 word samples each) in `~/.config/yawc/transforms.json`. Diff viewer: inline `+green`/`-red` with Undo `Ctrl+Z` via clipboard restore (03), Copy, Thumbs for future learning (logged only).

**Selection flow:** `wl-copy -p` (primary) or `wl-paste -p` grab → LLM with `cursor_context` from 04 → `wtype` replace selection → restore clipboard if cancelled. Failure: toast `Transform failed — pasted original` + manual paste fallback.

**Guard:** only visible selected text or last dictation (`≤500 chars`, `≤80ms` context read from 04) — no far-cursor edits to avoid mistakes.

## Hotkey Map (niri)

```
CapsLock                { spawn-sh "yawc dictation toggle" }          # dictation (03)
Ctrl+Win+Alt (hold)     { spawn-sh "yawc command hold" }            # Command Mode hold
Ctrl+Win+Alt+Esc        { spawn-sh "yawc command cancel" }          # cancel
Mod+Shift+T             { spawn-sh "yawc transform concise" }       # with selection
Mod+Shift+R             { spawn-sh "yawc transform reword" }
Mod+Shift+S             { spawn-sh "yawc transform structure" }
```

`repeat=false` for hold, `allow-when-locked=false`, `cooldown-ms=150`.

## Prompt List (exact wording)

**System base (shared with 02 polish, added `mode=command`):** `You are YAWC Command — edit ONLY the selected text. Never translate Taglish. Output polished text only.`

1. `concise`: `"Make this shorter by 30%, keep meaning and Taglish, no new facts."`
2. `reword`: `"Reword this clearly, same length, fix grammar, keep Tagalog/English as-is."`
3. `structure`: `"Turn this into bullets or paragraphs where it helps, keep all facts."`
4. custom slot: user JSON `{"name":"my-tone","prompt":"Rewrite in friendly tone...","samples":["before → after"]}` ≤500 words

Example custom `transforms.json`:
```json
{"custom":[{"name":"formal-email","prompt":"Rewrite as formal email, keep Taglish names","samples":["hi priya → Dear Priya,"] }]}
```

## Sequence Diagram

```
selection (wl-paste -p) → yawc-daemon --transform concise
  → at-spi context 70ms (04) → llama.cpp Qwen3-1.7B c512 0.4s (02)
  → diff view → wtype replace selection → wl-copy restore
  on Esc/timeout 600ms → fallback regex (02) or restore original selection
```

## Local Edits Only Guard

- Input len ≤500 chars, else chunk or reject `too long`.
- Source must be `selection` or `last_dictation` file `~/.local/share/yawc/last.txt` — never arbitrary cursor ±1000 chars.
- Preview before paste, Undo restores via `wl-copy` saved original (03 prototype).

## What Defer

Bold/italic app semantics, move-bullet, cross-doc edits, EN↔TL translate transform — need app-specific via `ydotool`/`atspi` `setText` and translation model; Phase 2.

