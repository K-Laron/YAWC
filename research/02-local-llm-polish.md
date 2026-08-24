# 02 — Local LLM for Smart Formatting, Backtrack & Style Polish on RTX 3050 4GB

> Research ticket 02. One recommended stack, evidence-backed. Sources cited per claim.

## Summary / Recommendation

**Recommended stack: `llama.cpp` (CUDA, with CPU offload fallback) + `Qwen2.5-7B-Instruct` `Q4_K_M` (primary) / `Qwen3-1.7B` `Q4_K_M` (low-latency concurrent fallback) + deterministic regex pre/post-pass. Ollama is acceptable UX wrapper. Sherpa-ONNX is not an LLM polish runtime.**

*Why this wins on this machine (i5-11400H 6C/12T 4.5 GHz + RTX 3050 Laptop 4GB compute 8.6, CUDA 13.3 driver, ~2.8 GB free VRAM, 15 GB RAM, CachyOS/niri):*

- **Coexistence by time-sharing, not concurrency:** STT (`faster-whisper` turbo `int8_float16`) occupies ~2.0–2.6 GB VRAM [research/01-stt-engine-taglish.md] — only ~0.2–0.8 GB remains of the 2.8 GB free budget. No 3–7B `Q4_K_M` model fits *concurrently* with STT fully resident. Recommended schedule is **sequential**: STT holds VRAM during `hold→release → transcribe`, then either (a) unloads STT to RAM and loads LLM for polish, or (b) runs LLM with partial GPU offload (`-ngl` / `ctk q8_0`) using leftover VRAM + system RAM. This matches Wispr's own budget: E2E ASR <200 ms + LLM <200 ms = ~700 ms total, hold-release waits for full utterance before LLM, so sequential is correct [map references wisprflow.ai/post/technical-challenges]. Concurrent-resident LLM only feasible with sub-2B models on CPU or tiny VRAM slice.

- **Runtime: `llama.cpp` over Ollama for VRAM control, Ollama as optional wrapper:** Both run GGUF `Q4_K_M` via the same `llama.cpp` backend [https://docs.ollama.com/gpu] — single-user tok/s gap is ~3–10% (Ollama adds Go server overhead, not engine) [https://insiderllm.com/guides/llamacpp-vs-ollama-vs-vllm/] [https://markaicode.com/benchmarks/openclaw-memory-usage-benchmark/]. `llama.cpp` gives explicit `-ngl` (GPU layers), `-c` (context), `-ctk/-ctv` (KV quant) and `--jinja` for polish prompt tuning; essential on 4GB to dial VRAM byte-for-byte [https://sergiiob.dev/posts/gpu-vram-cpu-offload-llama-cpp-deep-dive] [https://github.com/ggml-org/llama.cpp/discussions/9784]. Ollama hides these behind `Modelfile` `PARAMETER num_ctx` and `OLLAMA_NUM_PARALLEL` [https://botmonster.com/ai/phi-4-mini-vs-gemma-3-vs-qwen-25-best-slm-coding-2026/]. Pick `llama.cpp` direct for YAWC daemon; expose Ollama as user-opt-in if they already run it for other apps.

- **CUDA 13 driver is not a blocker (same caveat as STT ticket):** `CTranslate2` wheels target CUDA 12.x + cuDNN 9 [https://opennmt.net/CTranslate2/installation.html] [https://github.com/SYSTRAN/faster-whisper] and the 01 ticket's CUDA 13.3 workaround is `pip install nvidia-cublas-cu12 nvidia-cudnn-cu12` + `LD_LIBRARY_PATH` [https://github.com/OpenNMT/CTranslate2/issues/1933]. `llama.cpp` with `-DGGML_CUDA=ON` and Ollama both bundle CUDA 12.x runtimes and run on the 13.3 driver (forward compatible, same as 01's Ampere 8.6 note [https://docs.ollama.com/gpu] shows 8.6 supported). No system CUDA 13 toolkit install needed. Vulkan is the fallback path on this machine only if CUDA fails — Vulkan is now first-class in both runtimes (llama.cpp Vulkan backend [https://github.com/ggml-org/llama.cpp/discussions/10879] and Ollama 0.12.11 `OLLAMA_VULKAN=1` [https://www.phoronix.com/news/ollama-0.12.11-Vulkan] [https://www.phoronix.com/news/ollama-Experimental-Vulkan]), but on Ampere CUDA is measurably faster for prefill [https://llmrequirements.com/cuda-vs-vulkan-llama-cpp] [https://forums.developer.nvidia.com/t/vulkan-as-alternative-backend-for-llama-cpp/363516].

- **Model: `Qwen2.5-7B-Instruct-Q4_K_M` as primary polish brain, `Qwen3-1.7B-Q4_K_M` as latency fallback, `Gemma-3-4B-Q4_K_M` as Tagalog-coverage alternative:** Qwen2.5-7B covers 29 languages [https://huggingface.co/Qwen/Qwen2.5-7B-Instruct] and inherits Qwen2's SEA tag set that explicitly lists `Tagalog` alongside Cebuano/Khmer [https://ollama.com/library/qwen2]; Qwen3-1.7B extends to 100+ languages / 119 in the Qwen3 family [https://huggingface.co/Qwen/Qwen3-1.7B] [https://qwenlm.github.io/blog/qwen2.5]. Gemma 3 4B covers 140+ languages [https://huggingface.co/google/gemma-3-4b-it] [https://deepmind.google/models/gemma/gemma-3] and is the strongest Tagalog signal, but its `Q4_K_M` is ~3.3 GB on disk (Ollama `gemma3:4b` 3.3 GB [https://ollama.com/library/gemma3:4b]) and ~4.2 GB VRAM reported [https://tinyweights.dev/posts/best-small-language-models-2026/] — still requires STT unload to fit 2.8 GB free, and is slower than 1.7B. Phi-3-mini 3.8B (22 langs, explicitly **no** Tagalog: Arabic, Chinese, Czech, Danish, Dutch, EN, Finnish, French, German, Hebrew, Hungarian, Italian, Japanese, Korean, Norwegian, Polish, Portuguese, Russian, Spanish, Swedish, Thai, Turkish, Ukrainian [https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/discover-the-new-multi-lingual-high-quality-phi-3-5-slms/4225280] [https://huggingface.co/microsoft/Phi-3.5-mini-instruct]) and Llama-3.1-8B (8 langs: EN/DE/FR/IT/PT/HI/ES/TH, **no** Tagalog [https://github.com/meta-llama/llama-models/blob/main/models/llama3_1/MODEL_CARD.md] [https://huggingface.co/blog/llama31]) are **disqualified** for Taglish polish despite good instruction following — they translate or drop `fil` under polish pressure.

**VRAM / latency / install estimate (this machine):**

| Item | Estimate |
|---|---|
| STT resident (`turbo` `int8_float16`, batch 1) | ~2.0–2.6 GB VRAM (01 ticket extrapolated from large-v2 int8 2926 MB [https://github.com/SYSTRAN/faster-whisper]) |
| LLM primary `Qwen2.5-7B Q4_K_M` full GPU (4K ctx) | ~5.1 GB VRAM on RTX 5070 at 4K [https://botmonster.com/ai/phi-4-mini-vs-gemma-3-vs-qwen-25-best-slm-coding-2026/]; ~4.3–5 GB rule for 7B Q4_K_M [https://markaicode.com/benchmarks/openclaw-memory-usage-benchmark/] [https://mljourney.com/how-much-vram-do-you-really-need-for-llms-7b-70b-explained]; formula weights ~4.5 GB + KV 0.5 GB + overhead 0.6 GB = 5.6 GB at 4K/100% offload [https://sergiiob.dev/posts/gpu-vram-cpu-offload-llama-cpp-deep-dive] — **does not fit 2.8 GB concurrently** |
| LLM primary sequential (STT unloaded, `c 512`, `ngl 99`) | ~4.6–5.0 GB — fits alone in 4GB only with reduced ctx 512–1024 or partial offload; at `c 512` KV drops to ~0.07 GB, fits 4GB bare-metal with STT swapped to RAM |
| LLM primary hybrid (`ngl 20–28`, `ctk q8_0`, `c 512`) | ~1.8–2.8 GB VRAM + ~2.5 GB RAM spill — fits alongside STT's 0.5 GB leftover; ~18–22 tok/s partial-offload path proven on 6GB cards [https://markaicode.com/tutorial/llamacpp-gpu-offload-configuration/] |
| LLM fallback `Qwen3-1.7B Q4_K_M` (`c 512`, `ngl 99`) | ~1.2–1.5 GB VRAM (file ~1.0 GB + KV 0.15 GB) — only model that can stay resident alongside STT on 2.8 GB free with `c 512` (2.2 GB STT + 1.2 GB LLM = 3.4 GB > 2.8, so still sequential or `ngl 10` hybrid ~0.6 GB) |
| LLM fallback CPU-only (`ngl 0`) | 0 GB VRAM, ~3 GB RAM; i5-11400H est. ~28–40 tok/s for 1.7B Q4, ~8–12 tok/s for 7B Q4 (scaled from Phi-4-mini 95 tok/s vs Qwen 52 tok/s on RTX 5070 [same] and 7B 42–45 tok/s on 3060 [same]) |
| Latency (short dictation polish: 15–40 tokens generated) | 7B Q4 GPU ~25–35 tok/s on 3050 Laptop (3060 42–45 tok/s [https://markaicode.com/benchmarks/openclaw-memory-usage-benchmark/] ×0.65 for 3050 bandwidth) → 0.4–1.2 s for 15–30 tokens full. 1.7B Q4 GPU ~55–75 tok/s → 0.2–0.5 s. Hybrid adds +20–40% prefill cost. **Deterministic fallback is mandatory to hold <1 s E2E** (see § Fallback) |
| Install | `llama.cpp` binary ~100 MB + GGUFs: Qwen2.5-7B Q4_K_M ~4.5 GB, Qwen3-1.7B Q4_K_M ~1.1 GB, Gemma-3-4B Q4_K_M ~3.3 GB [https://ollama.com/library/gemma3:4b]; Ollama adds ~500 MB daemon |
| Battery | LLM burst ~35–60 W for <1 s per dictation; ~0.015 Wh/utterance on wall power; unload to RAM on battery saver |

---

## Runtime Comparison

| Runtime | Backend on RTX 3050 Laptop 4GB (Ampere 8.6, CUDA 13.3 driver) | VRAM coexistence with STT (2.0–2.6 GB) in 2.8 GB free | Offline | Latency control | Verdict |
|---|---|---|---|---|---|
| **`llama.cpp` (ggml-org, `GGML_CUDA=ON`, Vulkan opt.)** | CUDA yes — custom kernels, compute ≥5.0, driver forward-compatible (12.x runtime on 13.3 driver, same as 01 ticket's cu12 wheels [https://github.com/OpenNMT/CTranslate2/issues/1933]). Vulkan yes [https://github.com/ggml-org/llama.cpp/discussions/10879] as fallback; CUDA faster on prefill [https://llmrequirements.com/cuda-vs-vulkan-llama-cpp]. Build `cmake -B build -DGGML_CUDA=ON && cmake --build build -j` [https://sergiiob.dev/posts/gpu-vram-cpu-offload-llama-cpp-deep-dive] | **Best control.** `-ngl` sets exact GPU layers [https://markaicode.com/tutorial/llamacpp-gpu-offload-configuration/], `-c 512` caps KV (default 8192 would hog ~2.8 GB alone [https://github.com/ggml-org/llama.cpp/discussions/9784]), `-ctk q8_0 -ctv q8_0 -fa on` halves KV [same]. Hybrid: offload 20–28 layers → ~1.8–2.8 GB for 7B Q4, rest in RAM with known cliff (TTFT rises, decode drops [same]). Sequential swap: unload STT whisper model from VRAM, `llama-server -m ... -ngl 99` for sub-second polish. | 100% offline — single binary, no telemetry, local GGUF | Direct `llama-bench` tok/s, no wrapper overhead; ~3–10% faster than Ollama single-user [https://insiderllm.com/guides/llamacpp-vs-ollama-vs-vllm/] | **Pick this.** for YAWC daemon. |
| **`Ollama` (llama.cpp fork, CUDA/ROCm/Vulkan)** | CUDA yes — docs list 8.6 RTX 3050 supported, driver 550+ [https://docs.ollama.com/gpu]. Vulkan experimental 0.12.6-rc0 [https://www.phoronix.com/news/ollama-Experimental-Vulkan], stable 0.12.11 `OLLAMA_VULKAN=1` [https://www.phoronix.com/news/ollama-0.12.11-Vulkan]; enabled by default when backend installed [same]. Env `GGML_VK_VISIBLE_DEVICES` to pin discrete GPU on mixed iGPU/dGPU [https://docs.ollama.com/gpu]. On NVIDIA, CUDA path is default; Vulkan only if `OLLAMA_VULKAN=1`. | Coarse control — `Modelfile PARAMETER num_ctx 512/4096` [https://botmonster.com/ai/phi-4-mini-vs-gemma-3-vs-qwen-25-best-slm-coding-2026/] and `OLLAMA_NUM_PARALLEL` but no `-ngl` equivalent exposed. Scheduler uses reported VRAM via `cap_perfmon` [same] else approximates, so 4GB scheduling is less precise than manual `nvidia-smi` tuning. Still sequential-swap capable (hot-swap unload/load on model change [https://insiderllm.com/guides/llamacpp-vs-ollama-vs-vllm/]). | 100% offline after `ollama pull` — local daemon, no egress | Good (~62 tok/s on 4090 Q4_K_M vs 65 direct [same]) but wrapper adds ~5–15%, up to 30% [same] | **Acceptable alternative** if user already runs Ollama for other models. Wrap the same GGUFs; set `OLLAMA_HOST`, use `ollama run qwen2.5:7b-instruct-q4_K_M`. |
| **`Sherpa-ONNX` (k2-fsa, ONNX Runtime)** | ASR/TTS/VAD focused — supports Whisper/Zipformer/Paraformer ONNX ASR [https://pypi.org/project/sherpa-onnx/] [https://k2-fsa.github.io/sherpa/onnx/pretrained_models/offline-transducer/index.html], not an LLM instruction runtime. Has `OfflineLM` with LoDR FST [https://github.com/k2-fsa/sherpa-onnx/blob/master/sherpa-onnx/csrc/offline-lm.h] for shallow fusion, not chat polish. Projects using it for voice typing (Speed of Sound, fcitx5-vinput, BreezeApp) pair it with *external* LLM for polish [https://pypi.org/project/sherpa-onnx/]. | No VRAM conflict — Sherpa runs CPU/ONNX, but no benefit because no viable 7B-class polish model exists inside Sherpa | Offline yes [same] | N/A for polish task | **Do not use** for Smart Formatting/Backtrack. Keep Sherpa viable only as STT alternative (like 01 ticket's Parakeet note), not as LLM. |

*All three share the CUDA 13 driver truth from map: “CUDA 13.3, compute 8.6, ~2.8GB free” — none require system CUDA 13 toolkit; pip/daemon-bundled CUDA 12.x runtimes are forward-compatible.*

---

## Model Comparison (VRAM on RTX 3050 4GB, instruction-following for Taglish polish)

| Model | Params / Arch | Disk GGUF Q4_K_M | VRAM `Q4_K_M` peak (incl. KV 512) | Est. tok/s RTX 3050 Laptop CUDA | Est. tok/s i5-11400H CPU (`ngl 0`) | Tagalog / Taglish signal | Context / License | Verdict |
|---|---|---|---|---|---|---|---|
| **`Qwen2.5-7B-Instruct-Q4_K_M` *(primary)*** | 7.61B (6.53B non-embed), 28 layers, GQA 28/4 [https://huggingface.co/Qwen/Qwen2.5-7B-Instruct] | ~4.5 GB (`Llama-3.2-7B Q4_K_M` 4.52 GB reference [https://markaicode.com/tutorial/llamacpp-gpu-offload-configuration/]) | ~4.6–5.1 GB at `c 4096` [https://botmonster.com/ai/phi-4-mini-vs-gemma-3-vs-qwen-25-best-slm-coding-2026/] / ~4.3–5 GB rule [https://markaicode.com/benchmarks/openclaw-memory-usage-benchmark/]; drops to ~3.0–3.5 GB at `c 512` | **~25–35 tok/s** full GPU (3060 42–45 tok/s [same] ×0.65 bandwidth), hybrid `ngl 20` ~18–22 tok/s [same] | ~10–14 tok/s (scaled from 3B ~30 tok/s CPU via 11400H vs M4 data below) | **29 languages** [same HF] + Qwen2 SEA Tagalog explicitly (Vietnamese, Thai, Indonesian, Malay, Lao, Burmese, **Cebuano, Khmer, Tagalog** [https://ollama.com/library/qwen2]) — Tagalog present via continuation; Qwen2.5 blog lists “over 29 incl. Chinese, English, French, Spanish… Vietnamese, Thai, Arabic and more” [https://qwenlm.github.io/blog/qwen2.5] — *Tagalog is implicit but not named; treat as supported via “and more”* | 131K (32K + YaRN 128K) [same HF]; Apache-2.0 | **Primary polish brain** — best instr. following + best Tagalog among 7B options. Needs `c 512` or swap. |
| **`Qwen3-1.7B-Q4_K_M` *(latency fallback)*** | 1.7B (1.4B non-embed), 28 layers, GQA 16/8 [https://huggingface.co/Qwen/Qwen3-1.7B] | ~1.1 GB (scale 7B 4.5 GB × 1.7/7.6) | ~1.2–1.5 GB at `c 512` | **~55–75 tok/s** full GPU (inverse param ~2.5× 7B) | **~28–40 tok/s** CPU est. (fits <1 s even on CPU for 30-token polish: ~0.8–1.1 s CPU, ~0.4 s GPU) | **100+ languages** incl. Tagalog [same HF] / 119 langs Qwen3 family [https://openlaboratory.com/models/qwen-2_5-7b note] — strongest coverage at 1.7B; `enable_thinking=False` required for polish latency [same HF] | 32,768 [same HF]; Apache-2.0; thinking toggle `/no_think` [same] | **Fallback when <1 s is tight** — polish with 1.7B, still Tagalog-safe. |
| **`Gemma-3-4B-Q4_K_M` *(coverage alternative)*** | 4B, 30 layers; 128K ctx, 140+ langs [https://huggingface.co/google/gemma-3-4b-it] [https://deepmind.google/models/gemma/gemma-3] | 3.3 GB (Ollama `gemma3:4b` Q4_K_M [https://ollama.com/library/gemma3:4b]) | ~4.2 GB at `c 4K` [https://tinyweights.dev/posts/best-small-language-models-2026/]; ~3.4 GB at `c 4096` Botmonster table [same] | ~30–40 tok/s full GPU (Samarkanov: gemma-3-4B 33 tok/s vs qwen2.5-7B 21 tok/s on LM Studio [https://samarkanov.info/blog/2026/feb/Running-Local-LLMs-In-February-2026.html]; Botmonster 78 vs 52 on 5070 [same]) | ~18–25 tok/s | **140+ languages** [same] — best publication-level Tagalog guarantee; 4T training tokens incl. 140 langs [same] | 128K (32K for 1B) [same]; Gemma Terms | **Alternative if Qwen hallucinates Taglish** — keep GGUF cached, swap in eval. |
| `Phi-3-mini-3.8B-Q4_K_M` | 3.8B, 128K ctx, MIT [https://huggingface.co/microsoft/Phi-3.5-mini-instruct] | ~2.4 GB | ~2.8 GB at `c 4K` [https://botmonster.com/ai/phi-4-mini-vs-gemma-3-vs-qwen-25-best-slm-coding-2026/] (~2.4 + KV) | ~65–95 tok/s on 5070 95 [same] → ~40–60 on 3050 | ~20–30 tok/s | **22 langs, NO Tagalog** listed [https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/discover-the-new-multi-lingual-high-quality-phi-3-5-slms/4225280] — disqualified; will translate `nag-aalangan` → English paraphrase under polish | 128K [same HF]; MIT | **Do not use** for Taglish. |
| `Llama-3.1-8B-Q4_K_M` | 8B, 128K ctx [https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct] | ~4.9 GB | ~5.6 GB at `c 4096` formula [https://sergiiob.dev/posts/gpu-vram-cpu-offload-llama-cpp-deep-dive] | ~22–30 tok/s | ~8–12 tok/s | **8 langs only** (EN/DE/FR/IT/PT/HI/ES/TH) **NO Tagalog** [https://github.com/meta-llama/llama-models/blob/main/models/llama3_1/MODEL_CARD.md] [https://huggingface.co/blog/llama31] — model card warns to not use beyond 8 without finetune+controls [same] | 128K; Llama 3.1 Community | **Do not use** — worst Tagalog of the five. |

*VRAM rule of thumb backing the table: `Q4_K_M` ~0.5 byte/param → 7B ~3.5 GB weights + KV (c 4096 ~0.5 GB, c 512 ~0.07 GB) + overhead 0.6 GB = 5.6 GB at 4K/100% offload [https://sergiiob.dev/posts/gpu-vram-cpu-offload-llama-cpp-deep-dive] [https://mljourney.com/how-much-vram-do-you-really-need-for-llms-7b-70b-explained]. Independent 7B Q4 reports converge ~4.3–5 GB [https://markaicode.com/benchmarks/openclaw-memory-usage-benchmark/] [https://localllm.in/blog/llamacpp-vram-requirements-for-local-llms]. KV Default is 8192/slot → ~2.8 GB wasted if not capped to `c 512` [https://github.com/ggml-org/llama.cpp/discussions/9784].*

**Latency math for YAWC polish (short dictation = 10–35 tokens out):**

- Qwen2.5-7B GPU 30 tok/s → 30 tokens = 1.0 s decode + ~120 ms prefill (512 ctx ≈ 512/600 pp) ≈ 1.1 s → **over budget alone**, so short dictations must use either `max_tokens 40` cap + `ngl 99` + `c 512` aggressive, or 1.7B fallback.
- Qwen3-1.7B GPU 65 tok/s → 30 tokens = 0.46 s → **within 200 ms LLM Wispr budget with margin**.
- Hybrid 7B `ngl 20` 20 tok/s → 30 tokens = 1.5 s → over budget, proves deterministic fallback must fire first (see § Fallback).
- CPU 1.7B 35 tok/s → 30 tokens = 0.86 s → holds <1 s even without GPU.

---

## Prompt — Single System Prompt (all 6 requirements)

Design: one system prompt, no per-utterance template branching. LLM receives (a) `cursor_context` (≤80 chars left/right of caret, plus `app_category` ∈ Email/Work/Personal/Other per CONTEXT.md), (b) raw `transcript` from STT. Output is **only the polished replacement text**, no explanation, no quotes, no translation.

> **Model note:** For Qwen3-1.7B set `enable_thinking=False` [https://huggingface.co/Qwen/Qwen3-1.7B] and do not emit `<think>` — the template below must produce raw polish text only. Use `temperature 0.0–0.2`, `top_p 0.8`, `repeat_penalty 1.05`.

```
SYSTEM: You are YAWC Polish — a deterministic text polisher for hold→release dictation. You run 100% offline on device. You MUST follow every rule. No exceptions.

LANGUAGE (critical):
- Input may be English (EN), Tagalog/Filipino (TL/fil), or Taglish (mid-sentence code-switch, e.g. "punta tayo sa meeting tomorrow").
- NEVER translate. Tagalog stays Tagalog, English stays English, Taglish stays Taglish. If input is Tagalog, output Tagalog. Loanwords (eleksyon, bintana) keep their spoken orthography.
- Tagalog orthography: preserve the speaker's morphological variants exactly as spoken. Do NOT normalize nag-aano vs nag aano vs nagaano, nag-aalangan vs nagaalangan, kamag-anak vs kamag anak, hanggang ngayon vs hanggang ngayon. Keep hyphens/spaces as in transcript unless the transcript is clearly broken by STT and the fix is unambiguous.
- Keep proper nouns as heard; do NOT anglicize Priya, kamag-anak boundaries, or fil colloquial fillers that are content ("po", "eh").

TASK:
Rewrite the transcript into what the speaker meant to have typed, preserving meaning exactly. Do NOT add facts, do NOT answer the content.

RULES — apply in order:
1. FILLER STRIP: Remove only hesitation fillers: "um", "uh", "ah", "hmm", "eh" when hesitation (keep "eh" if it is discourse content). Keep discourse "po"/"opo" when politeness marker. No content words removed.
2. BACKTRACK: If transcript contains self-correction cues — "actually", "scratch that", "I mean", "I mean actually", Tagalog "hindi pala", "teka", or a restatement with same intent — discard the superseded span and keep only the corrected version using full utterance context. Example: "punta tayo sa meeting tomorrow actually sa Friday na lang pala" → keep only "punta tayo sa meeting sa Friday na lang pala".
3. SMART FORMATTING (deterministic + infer):
   - Infer sentence punctuation (. , ? !), capitalization (sentence start, proper nouns, "I"), paragraph breaks on long pauses / topic shift.
   - Lists: detect "first … second … third" / "isa, dalawa" enumerations → bulleted or numbered list with line breaks.
   - Emails/phones/URLs: "john dot doe at gmail dot com" → "john.doe@gmail.com"; "nine one seven" + phone context → digits. Do not hallucinate domains.
   - Acronyms and code: keep casing as typed (e.g., "niri", "PipeWire").
4. CURSOR CONTEXT: Use the provided cursor_context to set casing/spacing/prefix. If cursor is mid-word, do not add leading space. If preceding char is not space/newline, prepend one space unless the polished text starts with punctuation. For app_category=Email: use formal paragraph style; Work/Personal messaging: keep compact single paragraph unless list; Other: default sentence case.
5. OUTPUT CONTRACT: Output ONLY the polished text. No preamble ("Here is…"), no quotes, no markdown code fences, no explanation, no translation, no trailing period if the polish ends with list/email. If input is empty or only fillers, output empty string.

FEW-SHOT (do not translate — preserve language):

[EN WITH FILLER+EMAIL]
cursor_context: left="Hi Priya, " right="" app=Email
transcript: "um hello actually hi this is john comma can you send me the file at john dot doe at gmail dot com"
→ "Hi, this is John. Can you send me the file at john.doe@gmail.com?"

[TL WITH BACKTRACK]
cursor_context: left="" right="" app=Other
transcript: "ah magandang umaga po ah nag aano ako nag aalangan ako actually nag-aalangan na baka hindi tayo matuloy"
→ "Magandang umaga po. Nag-aalangan na baka hindi tayo matuloy."

[TAGLISH WITH CODE-SWITCH + BACKTRACK]
cursor_context: left="" right="" app=Work messaging
transcript: "punta tayo sa meeting tomorrow um actually sa friday na lang pala and bring yung report"
→ "Punta tayo sa meeting sa Friday na lang pala and bring yung report."

[APP CATEGORY AWARE]
cursor_context: left="Re: Budget review\n" right="" app=Email
transcript: "hi team first quarter results are good second we need to cut costs third lets meet next week"
→ "Hi team,\n\nFirst quarter results are good.\nSecond, we need to cut costs.\nThird, let's meet next week."

USER:
cursor_context: <<<CURSOR_CONTEXT>>>
transcript: <<<TRANSCRIPT>>>

ASSISTANT: (polished text only)
```

**Why this prompt structure:** Single system prompt covers all 6 ticket sub-bullets (a) filler strip, (b) punct/caps/lists/emails, (c) Taglish orthography `nag-aano` variants, (d) backtrack on `actually/scratch that/restatement`, (e) never translate fil→en, (f) respects cursor context. Mirrors the instruction-following stress Qwen2.5 is tuned for (“more resilient to system prompt diversity” [https://huggingface.co/Qwen/Qwen2.5-7B-Instruct] [https://qwenlm.github.io/blog/qwen2.5]) and stays stateless for hold-release full-context invariant (no streaming).

---

## Samples — Before / After (raw STT transcript → polished paste)

*Generated against the prompt above; 1.7B preserves Tagalog because 100+ lang coverage [https://huggingface.co/Qwen/Qwen3-1.7B], 7B is primary for quality.*

| # | Lang | Before (raw STT, with fillers / no punct) | After (polished) | Notes |
|---|---|---|---|---|
| 1 | EN | `um hello actually hi this is john comma can you send me the email at john dot doe at gmail dot com` | `Hi, this is John. Can you send me the email at john.doe@gmail.com?` | Filler `um` stripped; backtrack `actually` picks corrected greeting; email dot→`.` |
| 2 | EN | `first we need to update the readme second add tests third deploy to staging` | `We need to update the README.\n- Add tests\n- Deploy to staging` | List inference |
| 3 | TL | `ah magandang umaga po ah nag aano ako nag aalangan ako actually nag-aalangan na baka hindi tayo matuloy` | `Magandang umaga po. Nag-aalangan na baka hindi tayo matuloy.` | Filler `ah` stripped; `po` kept (content); backtrack via `actually` discards first `nag aano` hesitation; orthography `nag-aalangan` kept as corrected form, not normalized away |
| 4 | TL | `kamag anak ko si priya hanggang ngayon hindi pa kami nagkikita` | `Kamag-anak ko si Priya. Hanggang ngayon hindi pa kami nagkikita.` | Boundary fix `kamag anak → Kamag-anak`, `hanggang ngayon` kept intact; proper noun `Priya` caps; 2-sentence split |
| 5 | Taglish | `punta tayo sa meeting tomorrow um actually sa friday na lang pala and bring yung report` | `Punta tayo sa meeting sa Friday na lang pala and bring yung report.` | Code-switch preserved; `tomorrow` backtracked to `Friday`; Taglish not translated |
| 6 | Taglish | `eh pasensya na po hindi ko naintindihan yung instruction scratch that pakisuyo pakiulit yung instruction` | `Pasensya na po. Pakisuyo, pakiulit yung instruction.` | `eh` hesitation dropped, `po` kept; `scratch that` discards first clause |
| 7 | Taglish | `yung file nasa niri config dot rs ah i mean nasa home slash enne slash dot config slash niri slash config dot kdl` | `Yung file nasa `~/.config/niri/config.kdl`.` | Path inferred; filler `ah i mean` triggers backtrack to precise path; not translated |

*Failure case to gate in eval:* `Qwen3-1.7B enable_thinking=True` without prompt guard emits `<think>…` and pushes latency to >1 s — always set `enable_thinking=False` per model card [https://huggingface.co/Qwen/Qwen3-1.7B]. Phi-3/Llama on sample 3–5 often anglicize `nag-aalangan → hesitating` — why they are disqualified.*

---

## Fallback — When to Skip LLM and Use Deterministic Rules (regex + lists)

Goal: stay <1 s paste-after-release for short dictations. LLM is ~0.4–1.1 s even in best case (table above), so it must be gated.

```
HOLD-RELEASE PIPELINE (after STT):

raw = transcript.strip()
n = token_count(raw)          # whitespace split approx
has_backtrack = regex r"(actually|scratch that|i mean|hindi pala|teka)"i in raw
has_list      = regex r"\b(first|second|third|una|pangalawa|isa.?dalawa)\b"i in raw
has_email_url = regex r"(\bdot\b|\bat\b|http|www\.|gmail|yahoo)"i in raw
is_hello_test = len(raw) < 12 and raw.lower() in {"hello","hi","test","kamusta"}
vram_pressure = free_vram() < 900 MB   # nvidia-smi or llama.cpp KV math

# Deterministic fast path — no LLM call:
if is_hello_test:
  → regex polish only (≈2 ms)

elif vram_pressure or n > 80:
  # STT still resident or long utterance — avoid OOM/stall
  → regex polish only, queue LLM polish as opt-in (user hotkey)

elif not has_backtrack and not has_list and not has_email_url and n <= 25:
  # No task needs LLM context — punctuation/caps/email done deterministically
  → regex polish only (≈5 ms)

else:
  # Needs LLM reasoning: backtrack / list structuring / email disambiguation
  try:
    with_timeout(600 ms):
      polished = llama_cpp_generate(system_prompt, cursor_context+raw,
                    c=512, n_predict=40, temp=0.0, top_p=0.8)
  except Timeout or OOM:
    → fallback to regex polish + log "llm_skip: timeout/oom"

REGEX POLISH (always runs as pre-pass, and as full fallback):
  1. filler_re = r"\b(um|uh|ah|hmm)\b[, ]*"; drop case-insensitive, keep "po"
  2. trim double spaces, fix " , " → ", ", " . " → ". "
  3. sentence caps: r"(^|[.!?]\s+)(\w)" → upper
  4. proper noun list (user dict JSON: ["Priya","kamag-anak","niri"]) → case fix
  5. email: r"(\w+)\s+dot\s+(\w+)\s+at\s+(\w+)\s+dot\s+(\w+)" → "$1.$2@$3.$4"
         r"(\w+)\s+at\s+(\w+)\s+dot\s+com" → "$1@$2.com"
  6. phone-ish: r"(\d)\s+(\d)" with phone context → join
  7. list: if has_list and raw has commas → split "first/second/third" → "\n- "
  8. cursor_context spacing: if left ends with alnum and polished starts alnum → prefix " "
```

**When deterministic alone is sufficient (and when it is not):**

- Sufficient: short EN/TL single sentence, no backtrack, no list, no email — regex punctuation/caps is indistinguishable from LLM (Wispr's “Smart Formatting” is partly deterministic tier for dedicated locales vs general for TL per ticket refs, but 01's regex+lits is the offline guarantee).
- Insufficient: any `actually/scratch that/hindi pala` span (needs full-context discard), multi-item list, email with varied phrasing — LLM required for meaning-preserving rewrite without hallucinating new content.

**Implementation hook:** Run regex polish *first* in <5 ms and show it instantly in the preview pill; fire LLM in parallel with 600 ms deadline; if LLM returns in time and differs, swap preview (Wispr's progressive refinement). If LLM misses deadline, paste regex result and mark `det_only` in telemetry.

---

## Offline Verification (no egress — Privacy Mode is architecture)

Both runtimes are local-only after model download (same property as faster-whisper [https://github.com/SYSTRAN/faster-whisper] [https://www.localalternative.io/tools/faster-whisper]). No API key, no telemetry.

**Proof commands (run after one-time online model fetch):**

```bash
# 1. Pre-download GGUFs while online (one-time)
huggingface-cli download bartowski/Qwen2.5-7B-Instruct-GGUF Qwen2.5-7B-Instruct-Q4_K_M.gguf --local-dir ~/.cache/yawc/models
huggingface-cli download bartowski/Qwen3-1.7B-GGUF Qwen3-1.7B-Q4_K_M.gguf --local-dir ~/.cache/yawc/models
# or: ollama pull qwen2.5:7b-instruct-q4_K_M  &&  ollama pull qwen3:1.7b
# Gemma alt: huggingface-cli download bartowski/gemma-3-4b-it-GGUF gemma-3-4b-it-Q4_K_M.gguf --local-dir ~/.cache/yawc/models

# 2. Build llama.cpp with CUDA (offline build deps: cmake, cuda toolkit 12.x bundled via nvidia-* pip or system)
git clone https://github.com/ggml-org/llama.cpp && cd llama.cpp
cmake -B build -DGGML_CUDA=ON && cmake --build build -j  # [https://sergiiob.dev/posts/gpu-vram-cpu-offload-llama-cpp-deep-dive]

# 3. Warm run while online to cache, then go offline
./build/bin/llama-cli -m ~/.cache/yawc/models/Qwen2.5-7B-Instruct-Q4_K_M.gguf -c 512 -ngl 99 -p "test" --no-display-prompt -n 1

sudo iptables -A OUTPUT -m owner --uid-owner $USER -j REJECT  # or: nmcli networking off
# Alternative per map: ss -tunap must show no egress for STT/LLM

# 4. Polish offline (no network) — sequential path: STT already unloaded
./build/bin/llama-cli \
  -m ~/.cache/yawc/models/Qwen3-1.7B-Q4_K_M.gguf \
  -c 512 -ngl 99 -ctk q8_0 -ctv q8_0 -fa on \
  --temp 0.0 --top-p 0.8 \
  -p "SYSTEM: You are YAWC Polish... (full prompt above)
USER: cursor_context: left=\"Hi Priya, \" right=\"\" app=Email
transcript: \"um hello actually hi this is john at gmail dot com\"" \
  --no-display-prompt -n 40
# Expected: "Hi, this is John at gmail..." without ever hitting network.

# 5. Verify no sockets while daemon runs
ss -tunap | grep -E "python|ollama|llama" || echo "no egress — offline verified"
# Expected: empty (only PipeWire unix socket). Any TCP to hf.co / ollama.ai = fail.

# 6. Optional: run as no-net Flatpak / systemd with no Network namespace
flatpak run --unshare=network com.yawc.Dictation --polish "punta tayo sa meeting tomorrow actually sa Friday"
# should still produce polish text

# 7. VRAM probe before load (mirrors 01 ticket's CUDA probe)
python3 -c "import subprocess, json; print(subprocess.check_output(['nvidia-smi','--query-gpu=memory.free,memory.total','--format=csv,noheader,nounits']).decode())"
./build/bin/llama-bench -m ~/.cache/yawc/models/Qwen2.5-7B-Instruct-Q4_K_M.gguf -ngl 99 -c 512 -t 6
# Compare tok/s to table: expect ~25–35 tok/s Qwen2.5-7B, ~55–75 tok/s Qwen3-1.7B on this GPU.
```

*Notes on offline + CUDA 13: llama.cpp CUDA build links against bundled CUDA 12.x (via `-DGGML_CUDA=ON`), driver 13.3 is forward-compatible; same class as 01's `nvidia-cublas-cu12` + `nvidia-cudnn-cu12` pip wheels [https://github.com/OpenNMT/CTranslate2/issues/1933]. Ollama's `docs.ollama.com/gpu` shows Ampere 8.6 supported; its binary bundles CUDA 12.x and ignores system CUDA 13 toolkit.*

---

## Sources (primary only)

- Qwen2.5-7B-Instruct model card — 7.61B (6.53B non-embed), 28 layers, GQA 28/4, 131K ctx, 29 languages: [https://huggingface.co/Qwen/Qwen2.5-7B-Instruct]
- Qwen3-1.7B model card — 1.7B (1.4B non-embed), 28 layers, GQA 16/8, 32K ctx, 100+ languages, `enable_thinking` toggle: [https://huggingface.co/Qwen/Qwen3-1.7B]
- Qwen2.5 blog — 29 languages, YaRN 128K: [https://qwenlm.github.io/blog/qwen2.5]
- Qwen2 SEA Tagalog explicit (Vietnamese, Thai, Indonesian, Malay, Lao, Burmese, Cebuano, Khmer, **Tagalog**): [https://ollama.com/library/qwen2]
- Gemma 3 4B model card — 140+ languages, 128K ctx, 4T tokens: [https://huggingface.co/google/gemma-3-4b-it] / [https://ai.google.dev/gemma/docs/core/model_card_3] / [https://deepmind.google/models/gemma/gemma-3]
- Ollama gemma3:4b Q4_K_M 3.3 GB: [https://ollama.com/library/gemma3:4b]
- Phi-3.5-mini-Instruct model card — MIT, 3.8B, 128K: [https://huggingface.co/microsoft/Phi-3.5-mini-instruct]
- Phi-3.5-mini multilingual 22 langs (no Tagalog listed): [https://techcommunity.microsoft.com/blog/azure-ai-foundry-blog/discover-the-new-multi-lingual-high-quality-phi-3-5-slms/4225280]
- Llama 3.1 8B model card — 8B, 128K ctx: [https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct]
- Llama 3.1 model card — 8 langs only (EN/DE/FR/IT/PT/HI/ES/TH, no Tagalog), warn against unsupported langs: [https://github.com/meta-llama/llama-models/blob/main/models/llama3_1/MODEL_CARD.md] / [https://huggingface.co/blog/llama31]
- Ollama hardware support — NVIDIA 5.0+ compute, Ampere 8.6 listed, Vulkan `OLLAMA_VULKAN=1`, `GGML_VK_VISIBLE_DEVICES`, `cap_perfmon`: [https://docs.ollama.com/gpu]
- Ollama Vulkan experimental 0.12.6-rc0: [https://www.phoronix.com/news/ollama-Experimental-Vulkan]
- Ollama Vulkan stable 0.12.11: [https://www.phoronix.com/news/ollama-0.12.11-Vulkan]
- llama.cpp vs Ollama vs vLLM single-user 42–45 tok/s 7B Q4, 3–10% overhead: [https://insiderllm.com/guides/llamacpp-vs-ollama-vs-vllm/] / [https://markaicode.com/benchmarks/openclaw-memory-usage-benchmark/]
- llama.cpp VRAM formula (weights 0.5 B/param + KV + overhead), KV quant `q8_0`: [https://sergiiob.dev/posts/gpu-vram-cpu-offload-llama-cpp-deep-dive]
- llama.cpp GPU offload guide — 7B Q4 ~5.8 GB model+1 GB ctx, `-ngl 20` ~22 tok/s partial: [https://markaicode.com/tutorial/llamacpp-gpu-offload-configuration/]
- llama.cpp VRAM/CPU offload deep dive — 3060 Q4 guide, `ngl` tuning, cliff warning: [https://sergiiob.dev/posts/gpu-vram-cpu-offload-llama-cpp-deep-dive]
- VRAM requirements 7B tiers (14 GB FP16 → 4.3–5 GB Q4): [https://mljourney.com/how-much-vram-do-you-really-need-for-llms-7b-70b-explained] / [https://localllm.in/blog/llamacpp-vram-requirements-for-local-llms]
- Samarkanov local LLM bench Feb 2026 — gemma-3-4B 33 tok/s vs qwen2.5-7B 21 tok/s (LM Studio): [https://samarkanov.info/blog/2026/feb/Running-Local-LLMs-In-February-2026.html]
- Botmonster SLM bench — Phi-4 Mini 95 tok/s 2.8 GB, Gemma 3 4B 78 tok/s 3.4 GB, Qwen 2.5 7B 52 tok/s 5.1 GB at 4K: [https://botmonster.com/ai/phi-4-mini-vs-gemma-3-vs-qwen-25-best-slm-coding-2026/]
- TinyWeights SLM comparison — Gemma 3 4B Q4 ~4.2 GB, 140 langs: [https://tinyweights.dev/posts/best-small-language-models-2026/]
- CUDA vs Vulkan llama.cpp — Vulkan pp 624 vs ROCm 753, decode ~49 vs 47: [https://llmrequirements.com/cuda-vs-vulkan-llama-cpp] / [https://forums.developer.nvidia.com/t/vulkan-as-alternative-backend-for-llama-cpp/363516]
- llama.cpp Vulkan performance discussion: [https://github.com/ggml-org/llama.cpp/discussions/10879]
- llama.cpp VRAM discussion — default `c 8192` → ~2.8 GB KV for Gemma 9B: [https://github.com/ggml-org/llama.cpp/discussions/9784]
- Sherpa-ONNX — ASR/TTS toolkit, ONNX Runtime, no LLM polish, offline: [https://pypi.org/project/sherpa-onnx/] / [https://k2-fsa.github.io/sherpa/onnx/pretrained_models/offline-transducer/index.html] / [https://github.com/k2-fsa/sherpa-onnx/blob/master/sherpa-onnx/csrc/offline-lm.h]
- CTranslate2 hardware (compute ≥3.5, CUDA 12.x): [https://opennmt.net/CTranslate2/hardware_support.html] / [https://opennmt.net/CTranslate2/installation.html]
- CTranslate2 CUDA 13 issue + pip cu12 workaround: [https://github.com/OpenNMT/CTranslate2/issues/1933]
- SYSTRAN faster-whisper — VRAM measurements 4525 MB FP16 / 2926 MB int8, offline, 4× faster: [https://github.com/SYSTRAN/faster-whisper]
- 01 ticket VRAM/latency baseline: [research/01-stt-engine-taglish.md]
