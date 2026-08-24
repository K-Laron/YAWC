# CONTEXT — YAWC

Domain language for the local Wispr clone. Glossary only — no implementation.

## Glossary

| Term | Meaning |
|---|---|
| **Dictation** | One hold→release utterance captured as audio, transcribed to text, then polished and pasted into the focused field |
| **Utterance** | Continuous speech between hold-start and release-stop (Wispr waits for full utterance before LLM) |
| **Taglish** | Mid-sentence code-switch between Tagalog/Filipino and English (e.g., "punta tayo sa meeting tomorrow") — must not be translated, only transcribed |
| **Smart Formatting** | Deterministic + LLM pass that adds punctuation/caps/lists/emails/paragraphs and strips fillers without changing meaning |
| **Backtrack** | Self-correction handling: `actually`, `scratch that`, or restating triggers LLM to rewrite prior part of same utterance using full context |
| **Context Awareness** | Reading active app name, cursor-adjacent text, and (for IDEs) file names — plus optional local screenshot — to fix proper nouns and switch style; stays on-device |
| **App Category** | Wispr's 4 buckets used for style: `Email`, `Work messaging`, `Personal messaging`, `Other` (browser site sniff aggregates to same) |
| **Command Mode** | Separate hold (`Ctrl+Win+Alt` on niri) where speech is an instruction about existing text ("make last sentence shorter", "press enter") not new dictation |
| **Transform** | Highlight text → hotkey → LLM rewrite with a prompt (concise/reword/structure + custom samples) |
| **Snippet** | Voice cue that expands to full formatted text (e.g., "add disclaimer") |
| **Hotword** | Term boosted in STT via `initial_prompt`/`hotwords` so `Priya`, `kamag-anak` favor correct spelling without retraining |
| **Frontier** | Open, unblocked, unclaimed wayfinder tickets — the edge of what can be decided now |

## Boundaries

- **YAWC ≠ YAWC Team Cloud** — no shared cloud dict, no sync, no enterprise wrapper in Phase 1
- **Offline means offline** — `SS -tunap` must show no egress for STT/LLM after install; "Privacy Mode" is not a toggle, it's architecture
- **Language scope** — EN + TL only for Phase 1; 100+ langs is Wispr's scope, not YAWC's
