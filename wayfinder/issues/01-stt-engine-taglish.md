# STT engine and model for EN + TL + Taglish code-switch

**Type:** `wayfinder:research` — AFK
**Status:** closed — resolved 2026-08-24, research branch `research/01-stt-engine-taglish`
**Blocks:** 06-personal-dictionary-hotwords, 08-vram-latency-strategy, 07-taglish-eval-harness
**Resolution:** faster-whisper + large-v3-turbo int8_float16 CUDA + Silero VAD ONNX, hold-release, language=None + initial_prompt/hotwords, task=transcribe; fallback chain documented; offline verified via `ss -tunap` / `HF_HUB_OFFLINE=1`. Evidence: [research/01-stt-engine-taglish.md](../../research/01-stt-engine-taglish.md) — appended to map Decisions so far.

## Question

Which STT stack on this machine (i5-11400H + RTX 3050 4GB + Wayland) delivers 100% offline EN + Tagalog with **true Taglish mid-sentence code-switch**, within <1 s? Decide:

- Engine: `faster-whisper` (CTranslate2 CUDA) vs `whisper.cpp` (Vulkan/GGML) vs `NeMo Parakeet` / `Canary`; include VAD choice (`Silero VAD` vs `WebRTC VAD`) and audio pipeline (PipeWire → 16 kHz mono → chunking)
- Model: `large-v3-turbo` vs `medium` vs `large-v3` vs fine-tuned `whisper-small-fsc` / `small` Filipino; quantization (FP16, INT8) and VRAM footprint on 4 GB
- Language handling: `language=None` auto-detect vs `tl` pinned vs per-utterance prompt with Tagalog hotwords vs segmented detect; how to avoid Whisper's known Tagalog→English hallucination/translation and handle `kamag-anak`/`hanggang ngayon` boundary errors
- Streaming vs hold-release full-context (Wispr waits then pastes) — choose for <1 s target

Deliver one recommended stack with VRAM/battery estimate, install size, offline proof, and fallback chain (turbo → medium → tiny) if VRAM pressure.

## Why this is frontier

No dependency; all other tickets assume STT choice. Research ticket — subagent calls `research` skill, writes findings to `research/stt-engine-taglish` branch and links asset, then closes with decision + link added to map's Decisions so far.

## References

- `huggingface.co/openai/whisper-large-v3` (128 mels, 1 M+4 M hrs), turbo optimized variant
- `blog.americanarchive.org 2023-08-24` (Tagalog error taxonomy: kapatid/kasama, kamag-anak, translation)
- `sapinsapin/pld` 448 h + `filipinospeechcorpus` 65 h + `halo-livestream` Taglish CER 0.203
