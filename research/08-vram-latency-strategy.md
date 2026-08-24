# 08 — VRAM Partition, Model Load, <1s Strategy

> Ticket: [wayfinder/issues/08-vram-latency-strategy.md](../wayfinder/issues/08-vram-latency-strategy.md)
> Decision: **Sequential STT→LLM swap, STT hot, LLM warm on demand, regex fallback**

## Partition (RTX 3050 4GB, ~2.8GB free, i5-11400H)

| Mode | STT `turbo int8_float16` | LLM | VRAM total | Latency |
|---|---|---|---|---|
| **Hot STT + warm LLM (recommended)** | 2.0–2.6GB resident | Qwen3-1.7B Q4 `c512` 1.2GB loaded on demand, swapped to RAM when idle | 2.6GB idle, 1.2GB during polish | <1s |
| Full both resident | 2.6GB + 4.6GB Qwen2.5-7B | 7.2GB OOM | — | fail |
| All CPU | 0GB | 0GB, 35 tok/s 1.7B CPU | 0GB | ~0.8s but no GPU STT |

**Choice:** STT pinned GPU (`turbo int8_float16` 2.0–2.6GB per 01). LLM not resident — load `Qwen3-1.7B Q4_K_M` `c512 -ngl 99` on demand, unload STT to RAM during polish (sequential per 02). Swap cost ~300ms (model load from `~/.cache` 1.1GB via `mmap`). For short dictations (≤25 tokens) regex fallback (02) stays <5ms and often wins, LLM only for backtrack/list/email.

**Warm vs lazy:** Keep STT hot at login via `systemd --user` `yawc-daemon` (preload 1.6GB). LLM warm on first `command`/`backtrack` — first polish pays 300ms swap, next within 60s reused. Cold start 1.2s total still <1s for STT+regex path.

## Fallback Chain

```
STT OOM → turbo int8 (1.8GB) → small-pld-fil 1GB → whisper.cpp CPU
LLM timeout 600ms → regex polish (02: filler strip, caps, email)
LLM OOM → ngl 20 hybrid 0.6GB → CPU 35 tok/s → regex only
```

Budget enforcer: `with_timeout(600ms)` per 02; if miss, paste regex result and log `llm_skip`.

## Pipeline

```
audio stop → VAD 20ms → STT 200-350ms (turbo) → context 70ms (04) → LLM 0.4s (1.7B) or regex 5ms → wtype paste
```
Target p50 <700ms Wispr parity → local <1s for ≤12s utterance (01). If LLM would exceed, degrade to regex and show preview swap later.

## Bench (estimated, to verify on box)

```
large-v3-turbo int8_float16: 7.3ms niri + 250ms STT 10s audio
Qwen3-1.7B Q4 512ctx: 65 tok/s GPU → 30 tokens 0.46s
Qwen2.5-7B Q4 512ctx: 30 tok/s → 30 tokens 1.0s (too slow alone, needs swap)
Regex only: 5ms
```

Verify via: `python bench.py --model turbo --harness eval/harness.jsonl` + `nvidia-smi --query-gpu=memory.used --format=csv` per 08 Verification.

`nvidia-smi` free 2.8GB now, 1.9GB after wallpaper — threshold `free_vram<900MB` → force regex path.

