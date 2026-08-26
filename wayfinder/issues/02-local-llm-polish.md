# Local LLM for Smart Formatting, Backtrack, and style polish

**Type:** `wayfinder:research` — AFK
**Status:** closed — resolved 2026-08-24, research branch `research/02-local-llm-polish`
**Blocks:** 05-command-mode-transforms, 08-vram-latency-strategy
**Resolution:** llama.cpp CUDA + Qwen2.5-7B Q4_K_M sequential (c 512) + Qwen3-1.7B fallback (55–75 tok/s); prompt covers filler/backtrack/Taglish preserve/never translate; 600ms timeout → regex fallback; evidence: [research/02-local-llm-polish.md](../../research/02-local-llm-polish.md) — appended to map Decisions so far.

## Question

Which **local** LLM on this box polishes whispered/mumbled Taglish dictation into "what you meant" (Wispr's Smart Formatting + Backtrack) without leaving device or translating Tagalog to English, under <1 s for short dictations?

Decide:

- Runtime: `Ollama` (Vulkan/CUDA) vs `llama.cpp` (Vulkan + CPU offload) vs `Sherpa-ONNX` lightweight; how coexists with STT in 4 GB VRAM + 15 GB RAM
- Model: `Qwen2.5-7B-Instruct-Q4_K_M` vs `Gemma-3-4B-Q4` vs `Phi-3-mini-3.8B-Q4` vs `Qwen3-1.7B` vs `Llama-3.1-8B-Q4`; Tagalog quality vs latency tradeoff on 11400H
- Prompt design: single system prompt that (a) strips fillers (`um`, `ah`), (b) infers punctuation/caps/lists/emails, (c) preserves Taglish orthography (`nag-aano` variants), (d) backtracks on `actually`/`scratch that`/restatement, (e) never translates `fil`→`en`, (f) respects cursor context casing/spacing
- Fallback: when to skip LLM and use deterministic rules (regex + lists) to stay <1 s

Deliver recommended runtime+model+prompt with measured tokens/s on this CPU/GPU, VRAM split with STT, and sample before/after (EN, TL, Taglish).

## Why this is frontier

Independent of STT except for VRAM sharing (both will be re-resolved in 08). Research ticket — subagent resolves via `research`.

## References

- Wispr budget: E2E ASR <200 ms, LLM <200 ms, net <200 ms = 700 ms total (`wisprflow.ai/post/technical-challenges`)
- Wispr Smart Formatting locale tiers: dedicated EN/FR/etc, general for TL (`docs.wisprflow.ai 4048537120`)

## Implementation revision — 2026-08-26

As specced (c512, 600ms), the LLM polish path never executed: SYSTEM_PROMPT alone
exceeds 512 tokens, so every request returned HTTP 400 and the graceful fallback
silently substituted regex forever. Revisions, all measured:

- ctx **512 → 2048** (prompt + headroom; KV cost fits both-resident layout)
- `/no_think` appended to every `_chat` user turn — Qwen3 thinking otherwise eats
  `max_tokens` and returns empty content
- polish timeout **600ms → 1500ms**: first uncached prefill measured 713ms on this card
- server lifecycle: aliveness = port health (`llm_alive()`), teardown = pidfile;
  spawned once by yawc-evdev at daemon startup (`preload_llm`), never per hold

Evidence: warm backtrack rewrite verified live ("punta tayo sa meeting tomorrow
actually sa Friday na lang pala" → "Punta tayo sa meeting sa Friday na lang pala."),
~200ms cached / ~700ms uncached. Commit ae65f3a.
