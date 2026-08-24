# Taglish evaluation harness and gate

**Type:** `wayfinder:research` — AFK
**Status:** closed — resolved 2026-08-24, research branch `research/07-taglish-eval-harness`
**Blocks:** 08-vram-latency-strategy (gates model choice)
**Resolution:** 30 wav local gate (10/10/10), jiwer WER/CER + DNT≥0.90 + boundary≥0.75, gates EN WER<0.08 TL CER<0.12 Taglish CER<0.25, <2min run, 14-day pruned history; evidence: [research/07-taglish-eval-harness.md](../../research/07-taglish-eval-harness.md) — appended to map Decisions so far.

## Question

How do we prove EN + TL + Taglish actually works on this laptop with numbers, not vibes?

Decide:

- Datasets: `sapinsapin/pld` (448 h, 10 langs, prompted), `sapinsapin/filipinospeechcorpus` (65 h, 305 k segs), `halo-livestream` 62 segs (natural code-switch, median RT CER 0.203) vs `Fleurs tl` / `CommonVoice tl`; how to carve a 30-utterance local gate (10 EN, 10 TL, 10 Taglish mid-clause like "punta tayo sa meeting tomorrow at 3pm")
- Metrics: WER for EN, CER for TL (Tagalog orthography variant tolerant), plus "do not translate" rate (TL → EN hallucination) and `kamag-anak`/`hanggang ngayon` boundary check; define pass gates (e.g., Taglish CER <0.25, EN WER <0.08 on harness)
- Harness: `python -m eval.harness --model large-v3-turbo --harness harness.jsonl` that runs faster-whisper + LLM polish and prints table; keep audio `.wav` 16 kHz local; no cloud
- Regression: harness runs in CI guard before/after each STT/LLM swap; history kept 14 days like Wispr audio playback for manual listen

Deliver `harness.jsonl` spec + metric script + proposed gate numbers for Phase 1 sign-off; link research branch.

## Why this is frontier

Can start in parallel with STT/LLM research; will gate their decisions in 08. Research ticket — call `research` skill.

## References

- `halo-livestream` pipeline: MMS-300M CTC alignment + Silero VAD + faster-whisper RT CER scoring
- Wispr language tier note: Tagalog uses general formatting, not dedicated (`docs.wisprflow.ai 4048537120`)
