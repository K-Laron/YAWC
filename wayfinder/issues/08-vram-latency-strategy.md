# VRAM partition, model load, and <1 s latency strategy

**Type:** `wayfinder:task` — AFK/HITL (needs benchmark run on this box)
**Status:** closed — resolved 2026-08-24, research at `research/08-vram-latency-strategy.md`
**Blocks:** 09-packaging-permissions (install size)
**Resolution:** Sequential STT hot + LLM warm Qwen3-1.7B 1.2GB c512 sequential swap, regex fallback 600ms timeout; evidence [research/08-vram-latency-strategy.md](../../research/08-vram-latency-strategy.md) — appended to map.

## Question

On **4 GB RTX 3050 + 15 GB RAM** how do we keep **STT + LLM** resident and hit **<1 s paste for <10 s utterances** without OOM or thermal throttle?

Decide:

- Partition: STT pinned to GPU (e.g., turbo FP16 ~1.5 GB) vs LLM split (layers offload) vs all CPU fallback; quantify `nvidia-smi` free (~2.8 GB now, ~1.9 GB after wallpaper engine) and `llama.cpp --n-gpu-layers` sweet spot; swap cost
- Load: preload both at login (fastest, RAM heavy) vs lazy load on first hold (saves RAM, first dictation pays ~1.2 s) vs keep STT hot, LLM warm on demand
- Fallback chain: when LLM would blow budget, degrade to deterministic Smart Formatting (regex fillers + lists + punctuation) and still paste; define budget enforcer (e.g., LLM timeout 400 ms → fallback)
- Pipeline: audio stop → VAD trim → STT (target <300 ms) → context inject (≤80 ms) → LLM or rule (≤400 ms) → paste; where to stream vs batch for perceived speed

Deliver benchmark table on this laptop (3 runs each): `large-v3-turbo FP16` + `Gemma-3-4B-Q4` vs `Qwen2.5-7B-Q4` vs rule-only, with cold vs warm latency and VRAM; pick the partition that meets gate from 07.

## Why this is blocked

Needs engine/model choices from 01/02 and gate from 07 to know what "good enough" is. Task — run the benchmarks and record.

## Verification

`python bench.py` output + `nvidia-smi --query-gpu=memory.used --format=csv` snapshot committed as asset; decision written to map.

# ponytail: global preload, per-app warm if throughput matters
