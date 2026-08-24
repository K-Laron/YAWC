# Personal dictionary, snippets, and hotwords persistence

**Type:** `wayfinder:task` — HITL (needs file location decision) / AFK for impl
**Status:** closed — resolved 2026-08-24, research at `research/06-personal-dictionary-hotwords.md`
**Blocks:** none
**Resolution:** JSON dict+snippets at ~/.config/yawc/, hotwords+initial_prompt injection, auto-learn toast, git import; evidence [research/06-personal-dictionary-hotwords.md](../../research/06-personal-dictionary-hotwords.md) — appended to map.

## Question

Where and how does the local clone store and apply **personal dictionary / team terms / snippets** so a correction sticks without retraining, and Taglish proper nouns stay right?

Decide:

- Storage: `~/.config/wispr-local/dictionary.json` + `snippets.json` vs SQLite; schema: `term | phonetic hint | lang | app scope`; snippets: `cue → full text` (e.g., "add disclaimer" → block)
- Application: `faster-whisper` `hotwords` + `initial_prompt` vs `whisper.cpp` prompt vs LLM system prompt injection; weight/boost for Tagalog names with `ng` clusters
- Learning loop: manual add vs auto-learn on user edit (undo of AI edit → add to dict) with confirm toast; per-app scoping (email names) vs global; how to avoid polluting EN with TL terms
- Sync story for local-only: no team cloud; maybe git-synced file for teammates, out-of-scope for Phase 1 but format must allow import

Deliver file paths, JSON examples (EN + TL), and hotword injection code snippet for chosen STT engine; note team-shared dict is Phase 2 import, not cloud.

## Why this is blocked

Engine determines hotword API (`faster-whisper` supports `hotwords`, `whisper.cpp` uses `prompt`). Task ticket — create the two JSON files with sample terms and verify on-device.

## Definition of done

Two JSON fixtures + one script that loads them into chosen STT and passes a test: saying "kumusta Priya" after adding `Priya` once never mismatches.
