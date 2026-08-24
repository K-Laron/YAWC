# 07 — Taglish Evaluation Harness and Gate on RTX 3050 4GB (Offline)

> Research ticket 07. One recommended harness + gate, evidence-backed. Sources cited per claim. Reads ticket [wayfinder/issues/07-taglish-eval-harness.md](../wayfinder/issues/07-taglish-eval-harness.md), map [wayfinder/map.md](../wayfinder/map.md), prior decisions [research/01-stt-engine-taglish.md](01-stt-engine-taglish.md) and [research/02-local-llm-polish.md](02-local-llm-polish.md).

## Summary / Recommendation

**Recommended harness: a 30-utterance local gate (10 EN / 10 TL / 10 Taglish mid-clause) with `harness.jsonl` + `python -m eval.harness --model large-v3-turbo --harness harness.jsonl` that runs `faster-whisper` (CTranslate2, `int8_float16`, CUDA) then the local LLM polish pass, scoring WER (EN), CER (TL/Taglish) via `jiwer`, plus two hard gates — do-not-translate rate and `kamag-anak`/`hanggang ngayon` boundary detection — all audio kept as `.wav` 16kHz mono local, no network, history kept 14 days for regression.**

*Why this wins on this machine (CachyOS/niri + RTX 3050 Laptop 4GB compute 8.6, CUDA 13.3 driver, ~2.8GB free, PipeWire 1.6.8, 15GB RAM):*

- Offline-fixed by architecture: `faster-whisper` + `llama.cpp` are 100% offline after model download (same proof as 01/02) — harness reuses that stack with `local_files_only=True` / `HF_HUB_OFFLINE=1`; verification is `ss -tunap` must show no egress (map requirement, 01 §Offline Verification).
- VRAM/time budget respected: a 30-utterance gate at ~5–7s mean length ≈ 3 minutes of audio; at turbo `int8_float16` RTF ~0.12–0.18 on this GPU (01: large-v2 FP16 4525 MB / int8 2926 MB, turbo ~2.0–2.6GB) the STT stage is ~20–35s wall-clock; LLM polish at `c 512` is ~0.4s per utterance on `Qwen3-1.7B` GPU (02 table). Full gate runs in <2 minutes on this laptop, repeatable in CI without new downloads.
- Taglish is first-class, not an afterthought: no existing corpus gives a ready-made 30-item mid-clause code-switch benchmark. PLD and FSC are large but *prompted monolingual* (prompts written in one language), so they cannot supply natural mid-clause Taglish — that is exactly why `halo-livestream` exists ("studio corpora don't capture it because prompts are written in one language" [https://huggingface.co/datasets/sapinsapin/halo-livestream](https://huggingface.co/datasets/sapinsapin/halo-livestream)). The gate therefore **curates** 30 items from a mix: live-recorded Taglish for the 10 code-switch slots, plus filtered PLD/FSC/FLEURS reads for the 20 monolingual slots — then re-records all 30 locally at 16kHz to make the gate deterministic and offline.

**Carve decision (short):** do not use raw PLD/FSC/FLEURS as-is for the gate. Use them as *source pools* to sample prompts, then **re-record 30 utterances on this mic** (same speaker or 2 speakers, 16kHz mono `.wav`), human-transcribed once, frozen. This eliminates the three traps that make *direct* reuse unreliable: `text_is_prompt` in PLD spontaneous, the 56% single-word `machine` skew in FSC, and FLEURS n-way parallelism that has no code-switch. Ship `eval/audio/*.wav` + `harness.jsonl` in repo (git-lfs or `audio/` ignored with checksum manifest — see §Regression).

---

## Dataset Comparison — Which Pool Feeds Which Slot

| Dataset | HF id / scale | What it covers | Audio / format | Taglish? | Quality signals | Trap for naive use | Role in 30-utterance gate |
|---|---|---|---|---|---|---|---|
| **PLD** (Philippine Languages Database) | `sapinsapin/pld` — **334k rows (301k train / 33.4k test)**, **448.2h**, **980 speakers**, **10 langs** (`fil`, `eng`, `ceb`, `bcl`, `hil`, `ilo`, `war`, `pam`, `pag`, `tsg`) [https://huggingface.co/datasets/sapinsapin/pld](https://huggingface.co/datasets/sapinsapin/pld) / stats 334,268 utts 448.2h via [https://github.com/sapinsapin/halohalo](https://github.com/sapinsapin/halohalo) / paper 454h [https://aclanthology.org/anthology-files/pdf/sigul/2024.sigul-1.32.pdf](https://aclanthology.org/anthology-files/pdf/sigul/2024.sigul-1.32.pdf) | Prompted read + isolated + digits + spontaneous, domains news/medical/education/tourism | One WAV per prompt, **16kHz mono FLAC** (lossless), `duration 0.28–150s`, columns `language` vs `corpus_language` (EngW lists read by Filipino speakers are `language=eng` but `corpus_language=fil`) | **No** mid-clause code-switch — prompts are monolingual by design; `eng` rows are English *words* read with Filipino accent, not Taglish | `speech_type` (`read`/`isolated`/`digits`/`spontaneous`), `prompt_category`/`prompt_source` (308/543 values), `text_is_prompt`, `speaker_dialect`/`mother_dialect` | `spontaneous` rows store the **elicitation question**, not the answer transcript — blind training on them repeats the same question verbatim while audio is 20–90s free speech [halohalo README]. Also `text_is_prompt=true` masquerades as data. | **Pool for TL + EN prompts** — sample `language=fil` `read` with `num_words≥5` and `speech_type=read` for 10 TL candidates; sample `language=eng` `read` for 10 EN candidates. Do not ship raw PLD audio in gate; re-record selected sentences locally to control mic/silence/VAD. |
| **Filipino Speech Corpus (FSC)** | `sapinsapin/filipinospeechcorpus` — **305,246 rows** (274,730 train / 30,516 test), **313,322 segments raw**, **65.1h**, **125 speakers**, **MIT** → published 6.9GB, 139 shards [https://huggingface.co/datasets/sapinsapin/filipinospeechcorpus](https://huggingface.co/datasets/sapinsapin/filipinospeechcorpus) / halohalo pipeline [same repo] | Studio read + spontaneous + **machine word tokens** (unit-selection / keyword) | **16kHz mono Parquet inline audio**, `duration ~0–1639s`, median **0.62s**, p95 1.21s, mean 0.75s | **No** — same monolingual prompt limitation as PLD | `speech_type` (`machine`/`read`/`spontaneous`), `duration`, `num_words`, `speaker_id`, `age_group` (97.5% 20–27) | **56.1% is `machine` single-word tokens** (175,854 rows) — training without filter = word-level model. Longest segment 1,640s. Random 90/10 split leaks speakers across splits. | Same role as PLD — **alternate TL pool**. Filter to sentence-level ASR subset: `speech_type in (read, spontaneous) and 1.5 ≤ duration ≤ 30 and num_words ≥3` → ~8.5k utts (~7h). Prefer reading from PLD `fil read` over FSC when possible because FSC's useful sentence subset is ~8.5k vs PLD's larger read pool; keep FSC as fallback for `read` prompts when PLD lacks colloquial coverage. |
| **halo-livestream** (`kumu-livestream-segmented`) | `sapinsapin/halo-livestream` — **62 segments, ~7 min**, **3 speakers**, **1 source recording**, seed release [https://huggingface.co/datasets/sapinsapin/halo-livestream](https://huggingface.co/datasets/sapinsapin/halo-livestream) (= `kumu-livestream-segmented` gated mirror) | **Real Taglish code-switched livestream speech**, spontaneous | `asr` **16kHz / 53 segs ~6.4min** mean 7.3s; `tts` 24kHz / 9 segs strict subset; audio mono, bracket tags stripped | **Yes — the only natural mid-clause Taglish** of the three. Explicit purpose: "Filipino speakers switch between Tagalog and English mid-clause, constantly. Studio corpora don't capture it because prompts are written in one language." [same] | Per-segment: `alignment` (`forced` MMS-300M CTC / `interpolated`), `align_score` 0–1, **`asr_cer` (human vs faster-whisper large-v3 round-trip CER) median 0.203 asr / 0.087 tts**, `overlap` bool, `speech_ratio`, `snr_db`, `lufs`, `clip_ratio` | Tiny (any metric on 62 segs is noise — card says so). Transcripts imperfect: median 0.203 reflects orthography variance `nag-aano`/`nagaano`/`nag aano` [same]. Music/stream artifacts, variable mic. Gated raw `halo-livestream-raw` is privacy-gated. | **Pool + pipeline for the 10 Taglish slots, not as training data.** Reference the 62 segs for prompt inspiration and as a **real-audio smoke test** (run gate on its `asr` split to sanity-check median CER), but **re-record 10 bespoke Taglish utterances** for the frozen gate with the same quality-metadata pattern (MMS-300M + Silero VAD + round-trip CER) to get deterministic local `.wav`s. Do not train on these 62. |
| **FLEURS `fil_ph`** | `google/fleurs` — **3.27k rows fil_ph** (viewer: `af_za` 1.49k … `fil_ph` 3.27k; splits train ~1.03k rows / val 198 / test 264 per viewer; HF commit shows 1884 train before parquet conversion [https://huggingface.co/datasets/google/fleurs](https://huggingface.co/datasets/google/fleurs) / commit [https://huggingface.co/datasets/google/fleurs/commit/2747a5f283e09be566127752966bc2768108c844](https://huggingface.co/datasets/google/fleurs/commit/2747a5f283e09be566127752966bc2768108c844)) — **~12h per language** target [paper 2205.12446](https://doi.org/10.48550/arxiv.2205.12446) | N-way parallel read speech (FLoRes 101 sentences, 1–3 recordings each, 2.3 avg, 2009 sentences, 102 langs) — built for few-shot eval [same] | 16kHz mono via HF Datasets, fields `audio`/`transcription`/`raw_transcription`, `gender`, `lang_id`, `language`, `lang_group_id` (SEA) | **No** — parallel translations, not code-switch | `transcription` (normalized) + `raw_transcription` (verbatim) pair; CC-BY-4.0 | Sentences are news/wikipedia formal; not colloquial Taglish. No `asr_cer`/`overlap` signals. | **Benchmark anchor** — sample 5–6 TL candidates from `fil_ph` test (formal register) to validate generalization beyond PLD/FSC news domain; keep FLEURS itself as an *external validation* set (report WER/CER on full `fil_ph test` in nightly sweep, not in the 30-item gate which must stay small/fast). |
| **Common Voice `tl` / `fil`** | `common-voice/cv-dataset` via [Mozilla Data Collective](https://mozilladatacollective.com/organization/cmfh0j9o10006ns07jq45h7xk) / [https://commonvoice.mozilla.org](https://commonvoice.mozilla.org) — **type SCS active 290 langs v25.0, SPS 72** [https://github.com/Common-Voice/cv-dataset](https://github.com/Common-Voice/cv-dataset) | Scripted read (SCS mp3 + tsv) + spontaneous speech (SPS) + code-switching alpha — generic Mozilla infra | MP3, CC0 | Tagalog presence as of 2024–2026 is **present on CommonVoice platform but no large validated `tl` split comparable to FLEURS**; `tl`/`fil` not among the large validated releases in 19.0–25.0 public dumps without community contribution | `up_votes`/`down_votes`, `age`/`gender`/`accent` | **Do not rely on CV `tl` for Phase 1 gate** — validated hours are negligible vs PLD/FSC/FLEURS, and quality signals (`snr_db`, `asr_cer`) are absent. Treat as **future** drift-check source if validated `tl` set reaches ≥5h. |
| **NCSpeech comparative (not a pool)** | `NCSpeech/stt_tl_fastconformer_hybrid_large` — 115M hybrid Transducer/CTC, BPE 1024, ~520h Tagalog training [https://huggingface.co/NCSpeech/stt_tl_fastconformer_hybrid_large](https://huggingface.co/NCSpeech/stt_tl_fastconformer_hybrid_large) | Tagalog STT | 16kHz | N/A | Reports **FLEURS `fil_ph` test WER** per model: FastConformer 9.34%, whisper-large-v3-turbo 11.60%, ElevenLabs 9.19%, Google 7.42% (same card) — the best independent turbo-on-Tagalog number for gate calibration | — | Use only for **gate calibration** (see §Metrics). Not a data pool. |

`wayfinder/issues/07-taglish-eval-harness.md` already names `halo-livestream` pipeline as reference: `MMS-300M CTC alignment + Silero VAD + faster-whisper RT CER scoring` — the dataset card confirms that exact stack: stage order parse → align (MMS-300M CTC romanization-based, code-switch-safe) → QC (VAD snapping + large-v3 round-trip CER + `snr_db`/`lufs`/`clip_ratio`/`overlap`/`speech_ratio`) → export gated `asr`/`tts` configs [https://huggingface.co/datasets/sapinsapin/halo-livestream](https://huggingface.co/datasets/sapinsapin/halo-livestream). Pipeline source is `process_livestream.py` + `docs/livestream_pipeline.md` in [https://github.com/sapinsapin/halohalo](https://github.com/sapinsapin/halohalo).

---

## Harness Spec

### Invocation (ticket contract)

```bash
# STT: faster-whisper large-v3-turbo, int8_float16, CUDA
# Polish: llama.cpp Qwen3-1.7B Q4_K_M c512 ngl99 (or Qwen2.5-7B sequential)
python -m eval.harness --model large-v3-turbo --harness harness.jsonl
python -m eval.harness --model large-v3-turbo --harness harness.jsonl --no-polish   # STT-only ablation
python -m eval.harness --model large-v3-turbo --harness harness.jsonl --json runs/2026-08-24.json
```

Prints a table (stdout) + writes `runs/<date>.json` for regression history. No network at runtime — models loaded `local_files_only=True` / `HF_HUB_OFFLINE=1` after one-time download (proof in §Offline Proof).

### Filesystem layout

```
eval/
  harness.jsonl          # 30 lines, frozen, committed
  audio/
    en_01.wav            # 16kHz mono PCM, 1–12s per utterance (<=30s Whisper window)
    ...
    tl_10.wav
    taglish_01.wav
    ...
  harness.schema.json    # JSON Schema for harness.jsonl (optional, for CI validation)
  metrics.py             # scoring script (jiwer + gates)
  harness.py             # runner (pkg: eval.harness, `python -m eval.harness`)

runs/
  2026-08-24.json        # one JSON per run, kept 14 days (gitignored or artifact store)
  history.csv            # rolling aggregate for CI sparkline (optional)
```

Audio: **`.wav` 16kHz mono float32/PCM16** local — matches Silero VAD and faster-whisper expectations at 16k [https://github.com/snakers4/silero-vad](https://github.com/snakers4/silero-vad) and [https://github.com/SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper). Resample once at record time via PipeWire (`pw-record --rate 16000 --channels 1`) or offline `ffmpeg -ar 16000 -ac 1`. No cloud storage, no HF streaming at eval time.

### `harness.jsonl` schema — one JSON per line, no header

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | `str` | yes | Stable key `en_01` … `taglish_10`, lexicographically sortable. Used for table row key and regression diff. |
| `audio` | `str` | yes | Relative path `audio/<id>.wav`. Must exist on disk; CI fails fast if missing. |
| `reference` | `str` | yes | Human transcript (verbatim, with punctuation as intended for *polished* reference — see polish mode below). For STT-only mode, a second key `reference_raw` may be present (lowercased, no punct) — but the runner prefers `reference` with normalization instead of a second field. |
| `language` | `str` | yes | `en` / `tl` / `taglish` (== `tgl-eng` in halo-livestream schema). Gate aggregates per this field. |
| `category` | `str` | no | Free tag for slice reporting: `boundary` / `do_not_translate` / `backtrack` / `list` / `email` / `numbers`. |
| `tags` | `str[]` | no | Alias for `category` as array when an utterance covers multiple gates (e.g., `["boundary","do_not_translate"]`). |
| `speaker` | `str` | no | Speaker key for multi-speaker drift tracking (keep to 1–2 speakers for Phase 1 to stay small). |
| `duration_hint` | `float` | no | Informational seconds; runner verifies actual file duration is within 0.5s. |

Minimal line example:

```json
{"id": "taglish_03", "audio": "audio/taglish_03.wav", "reference": "Punta tayo sa meeting sa Friday na lang pala and bring yung report.", "language": "taglish", "tags": ["backtrack"]}
{"id": "tl_04", "audio": "audio/tl_04.wav", "reference": "Kamag-anak ko si Priya hanggang ngayon hindi pa kami nagkikita.", "language": "tl", "tags": ["boundary"]}
```

Schema validation (optional `harness.schema.json`) — validate in CI with `jsonschema` or `ajv`, but not required for offline run; the runner validates required fields itself.

### Runner (`eval/harness.py`) — what it does

Pseudo-code mirrors `halo-livestream` QC stage (MMS → VAD → faster-whisper CER) but as an **eval loop**:

```python
# eval/harness.py  (sketch, sync, single-GPU sequential STT→LLM)
import json, time, pathlib, jiwer
from faster_whisper import WhisperModel
from eval.metrics import score_all, check_boundary, check_do_not_translate
# LLM polish import is lazy — only if --no-polish not given
# from llama_cpp import Llama  (or subprocess to llama-cli binary)

def load_harness(path):
    rows = [json.loads(l) for l in open(path) if l.strip()]
    assert len(rows) == 30
    assert sum(1 for r in rows if r["language"]=="en")==10
    assert sum(1 for r in rows if r["language"]=="tl")==10
    assert sum(1 for r in rows if r["language"]=="taglish")==10
    for r in rows:
        assert pathlib.Path("eval/"+r["audio"]).exists(), r["audio"]
    return rows

def transcribe(model, wav_path, language_hint=None):
    # faster-whisper contract from 01: language=None auto-detect for taglish,
    # tl pin for TL-heavy meetings as fallback, task="transcribe" never translate
    segments, info = model.transcribe(
        wav_path,
        language=language_hint,  # None for taglish/en auto, "tl" for tl suite
        task="transcribe",
        vad_filter=True,  # Silero VAD built-in
        vad_parameters=dict(min_silence_duration_ms=300, speech_pad_ms=30),
        initial_prompt="Kamusta! Kasama si Priya, kamag-anak, hanggang ngayon, pakisuyo, salamat — Taglish, do not translate.",
        hotwords="Priya kamag-anak hanggang ngayon kamag anak pakisuyo",
        beam_size=5, best_of=1, temperature=0.0,
        condition_on_previous_text=False,
    )
    return " ".join(s.text.strip() for s in segments), info

def polish(text, cursor_context=""):
    # 02 ticket prompt: sequential STT→LLM with c 512, timeout 600ms → fallback regex
    # If no LLM available, return deterministic regex polish (see 02 §Fallback)
    ...

def main(model_name, harness_path):
    rows = load_harness(harness_path)
    model = WhisperModel(model_name, device="cuda", compute_type="int8_float16",
                         local_files_only=True)  # offline
    t0 = time.time()
    results = []
    for r in rows:
        lang_hint = None if r["language"]=="taglish" else (None if r["language"]=="en" else "tl")
        # warm: two-pass option for TL — first auto, second pinned if auto=="en" with high prob
        raw_hyp, info = transcribe(model, "eval/"+r["audio"], lang_hint)
        hyp = polish(raw_hyp) if not args.no_polish else raw_hyp
        results.append((r, raw_hyp, hyp, info))
    scores = score_all(rows, [h for _,_,h,_ in results])
    print_table(scores)  # also prints do_not_translate, boundary, RT / WER/CER breakdown
    save_json(scores, "runs/....json")
```

Notes:
- `hotwords` / `initial_prompt` are the exact 01 recommendation for `kamag-anak`/`hanggang ngayon` boundary hardening; harness measures with and without them as an ablation (`--no-hotwords` flag, report CER delta ≥0.02 expected per 01's gate).
- `language` pinning: gate runs **both** modes and reports — `None` (auto) and `tl`-pinned — because AAPB study shows `language=None` translates Tagalog to English more often while `language="tl"` reduces it [https://blog.americanarchive.org/2023/08/24/assessment-of-whisper-ai-as-a-tagalog-language-transcription-tool/](https://blog.americanarchive.org/2023/08/24/assessment-of-whisper-ai-as-a-tagalog-language-transcription-tool/). Ticket asks to check do-not-translate.
- Large-v3 `int8_float16` on this GPU needs `nvidia-cublas-cu12` + `nvidia-cudnn-cu12==9.*` via pip + `LD_LIBRARY_PATH` on driver 13.3 (01 workaround via [https://github.com/OpenNMT/CTranslate2/issues/1933](https://github.com/OpenNMT/CTranslate2/issues/1933)); runner probes `get_cuda_device_count()` first and falls back to `whisper.cpp` CPU path if probe fails.

### Metric script (`eval/metrics.py`) — scoring pseudo

```python
# eval/metrics.py — depends only on jiwer (RapidFuzz C++ impl) + stdlib
# https://jitsi.github.io/jiwer/  /  https://github.com/jitsi/jiwer
import jiwer, re, unicodedata

# Normalization — must match Wispr STT reporting: lower, NFC, strip punct for STT CER,
# keep punct for polish scoring via a second pass. The harness reports both.
def normalize_tl(text: str) -> str:
    t = unicodedata.normalize("NFC", text).lower().strip()
    # Tagalog orthography variant tolerant: hyphens/en-dash → space, collapse whitespace
    # This makes kamag-anak == kamag anak == kamag-anak (orthographic, not error)
    # per halo-livestream limitation: "nag-aano / nagaano / nag aano" unstandardised [HF card]
    t = re.sub(r"[\u2010-\u2015\-]", " ", t)
    t = re.sub(r"[^\w\s']", "", t, flags=re.UNICODE)  # keep apostrophe for Tagalog clitics
    t = re.sub(r"\s+", " ", t)
    return t

def normalize_en(text: str) -> str:
    t = unicodedata.normalize("NFC", text).lower().strip()
    t = re.sub(r"[^\w\s']", "", t)
    t = re.sub(r"\s+", " ", t)
    return t

def cer_pair(ref, hyp, lang):
    norm = normalize_tl if lang in ("tl","taglish") else normalize_en
    # jiwer.cer includes space as char by default — that's desired so we keep normalized spaces
    return jiwer.cer(norm(ref), norm(hyp))

def wer_pair(ref, hyp):
    return jiwer.wer(normalize_en(ref), normalize_en(hyp))

def score_all(rows, hyps):
    # corpus-level: sum edit distance across all rows per jiwer convention
    # jiwer.cer(list_refs, list_hyps) does global alignment — use that, not mean of per-row
    en_refs = [normalize_en(r["reference"]) for r,h in zip(rows,hyps) if r["language"]=="en"]
    en_hyps = [normalize_en(h) for r,h in zip(rows,hyps) if r["language"]=="en"]
    tl_refs = [normalize_tl(r["reference"]) for r,h in zip(rows,hyps) if r["language"]=="tl"]
    tl_hyps = [normalize_tl(h) for r,h in zip(rows,hyps) if r["language"]=="tl"]
    mix_refs = [normalize_tl(r["reference"]) for r,h in zip(rows,hyps) if r["language"]=="taglish"]
    mix_hyps = [normalize_tl(h) for r,h in zip(rows,hyps) if r["language"]=="taglish"]
    return {
        "en_wer": jiwer.wer(en_refs, en_hyps) if en_refs else None,
        "tl_cer": jiwer.cer(tl_refs, tl_hyps) if tl_refs else None,
        "taglish_cer": jiwer.cer(mix_refs, mix_hyps) if mix_refs else None,
        "all_cer": jiwer.cer([normalize_tl(r["reference"]) for r in rows],
                             [normalize_tl(h) for h in hyps]),
        "do_not_translate": do_not_translate_rate(rows, hyps),
        "boundary": boundary_score(rows, hyps),
        "per_row": [ {"id": r["id"], "cer": cer_pair(r["reference"], h, r["language"]),
                      "wer": wer_pair(r["reference"], h) if r["language"]=="en" else None}
                     for r,h in zip(rows, hyps) ],
    }

TAGALOG_STOP = {"ako","ikaw","siya","kami","tayo","kayo","sila",
                "nasa","sa","ng","ang","mga","na","ay","hindi","huwag","po","opo",
                "kamag","anak","hanggang","ngayon","kapatid","kasama","punta","tayo"}

def do_not_translate_rate(rows, hyps):
    # Heuristic: if reference is tl/taglish, hyp should still contain Tagalog tokens
    # Flag translation hallucination when hyp has zero Tagalog stop/tag words while ref has ≥2
    # Matches ticket's "TL → EN hallucination" + 01's AAPB translation finding
    flags = 0
    for r,h in zip(rows, hyps):
        if r["language"] in ("tl","taglish"):
            ref_has_tl = sum(1 for w in normalize_tl(r["reference"]).split() if w in TAGALOG_STOP) >= 2
            hyp_has_tl = sum(1 for w in normalize_tl(h).split() if w in TAGALOG_STOP) >= 1
            if ref_has_tl and not hyp_has_tl:
                flags += 1
    denom = sum(1 for r in rows if r["language"] in ("tl","taglish"))
    return 1 - flags/max(1,denom)  # pass rate

def check_boundary(rows, hyps):
    # Exact ticket gates: kamag-anak (hyphen variants) and hanggang ngayon (boundary)
    checks = []
    for r,h in zip(rows, hyps):
        nh = normalize_tl(h)
        if "kamag anak" in normalize_tl(r["reference"]):  # reference contains the concept
            checks.append(("kamag-anak", "kamag anak" in nh))
        if "hanggang ngayon" in normalize_tl(r["reference"]):
            # accept hanggang ngayon, reject hanggang ayon / hanggang ngyon drop
            checks.append(("hanggang ngayon", "hanggang ngayon" in nh))
    return {"pass": sum(1 for _,ok in checks if ok), "total": len(checks),
            "rate": sum(1 for _,ok in checks if ok)/max(1,len(checks)),
            "details": checks}
```

Why `jiwer`: standard, C++-backed minimum-edit distance, supports `wer`/`cer`/`mer`/`wil`/`wip` [https://jitsi.github.io/jiwer/](https://jitsi.github.io/jiwer/) / [https://github.com/jitsi/jiwer](https://github.com/jitsi/jiwer), pip `jiwer>=3`, Apache-2.0, Python ≥3.8. Paper justification for CER over WER on TL: CER correlates better with human judgement on morphologically complex languages and tolerates orthographic variation (Malayalam/Arabic study finds CER rank correlation +4.75% over WER) [https://aclanthology.org/2025.findings-naacl.277/](https://aclanthology.org/2025.findings-naacl.277/) / preprint [https://doi.org/10.48550/arxiv.2410.07400](https://doi.org/10.48550/arxiv.2410.07400); Taglish needs the same lenience (halo-livestream card states CER is the honest metric for Taglish).

Output table (stdout + JSON):

```
language  n   WER     CER     DNT    boundary   p50-CER
en        10  0.062   0.041   -      -          0.038
tl        10  -       0.118   1.00   0.80       0.102
taglish   10  -       0.183   0.90   0.83       0.171
all       30  -       0.119   0.95   0.82       -
```

JSON (`runs/YYYY-MM-DD.json`) includes every `per_row.cer`, `info.language`/`language_probability`, `rtf`, `model`, `harness_hash`, `audio_checksums` for diff.

---

## Metrics / Gates

| Metric | Scope | Gate (Phase 1 sign-off) | Rationale / anchor | Fail action |
|---|---|---|---|---|
| **EN WER** (jiwer, `wer_default` lower+punct strip via `normalize_en`) | `language=en` 10 | **<0.08** (8%) | LibriSpeech-clean turbo FP16 WER 1.9% / int8 4.6% on 13min [https://github.com/SYSTRAN/faster-whisper/issues/1030](https://github.com/SYSTRAN/faster-whisper/issues/1030); open benchmark EN WER ~4–5% on large-v3-turbo [https://huggingface.co/openai/whisper-large-v3-turbo](https://huggingface.co/openai/whisper-large-v3-turbo). 8% is generous for prompted near-field read; flags mic/VAD or EN hallucination without being flaky. | Block STT/LLM merge; check `initial_prompt` not leaking EN bias, check VAD `speech_pad_ms`. |
| **TL CER** (jiwer `cer`, orthography-tolerant `normalize_tl`, hyphen→space) | `language=tl` 10 | **<0.12** (12%) | whisper-small-fsc on FSC held-out WER 15.91% CER 7.06% [https://huggingface.co/sapinsapin/whisper-small-fsc](https://huggingface.co/sapinsapin/whisper-small-fsc) (lowercased); NCSpeech turbo FLEURS `fil_ph` WER 11.6% [https://huggingface.co/NCSpeech/stt_tl_fastconformer_hybrid_large](https://huggingface.co/NCSpeech/stt_tl_fastconformer_hybrid_large) → ~6–8% CER equivalent. 12% is reachable without fine-tune while exposing regressions. | Block; try `language="tl"` pin ablation; try PLD fine-tune specialist `whisper-small-pld-fil` (CER 4.63% on PLD lowercased [https://huggingface.co/sapinsapin/whisper-small-pld-fil](https://huggingface.co/sapinsapin/whisper-small-pld-fil)) as diagnostic. |
| **Taglish CER** | `language=taglish` 10 | **<0.25** (25%) — ticket example | halo-livestream **median RT CER 0.203 asr** (human vs large-v3 round-trip) on *real* Taglish [HF card]. Gate 0.25 is median + margin for re-recorded cleaner audio (our audio is studio, not livestream-with-music). PolyWER recommends CER threshold α=0.25 for transliteration acceptance [https://aclanthology.org/2024.findings-emnlp.356.pdf](https://aclanthology.org/2024.findings-emnlp.356.pdf). Fails if model translates or splits boundaries. | Block; inspect do-not-translate + boundary slices below. |
| **Corpus CER (all 30)** | all | **<0.15** | Aggregate sanity; prevents EN-good/TL-bad trade-off hiding behind per-slice means. | Informational warn if alone. |
| **Do-not-translate rate** (`TAGALOG_STOP` heuristic above) | `tl`+`taglish` 20 | **≥0.90** (≤2 of 20 translated) | AAPB study: Whisper with `language=None` "more frequently translated Tagalog utterances into English" [https://blog.americanarchive.org/2023/08/24/assessment-of-whisper-ai-as-a-tagalog-language-transcription-tool/](https://blog.americanarchive.org/2023/08/24/assessment-of-whisper-ai-as-a-tagalog-language-transcription-tool/). Prompt `task="transcribe"` + `initial_prompt "do not translate"` is the mitigation; rate <0.9 means mitigation broken. See also PolyWER §translation vs transliteration [same PDF]. | Block; force `task="transcribe"` assert + add `initial_prompt` hotword check; gate fails closed. |
| **Boundary check** (`kamag-anak` + `hanggang ngayon`) | subset tagged `boundary` (≥4 utterances contain the phrases) | **≥0.75** (3/4) | 01 ticket names these two splits as the canonical failure: `kamag-anak → kama ganak` (boundary split) and `hanggang ngayon → hanggang ayon` (coda drop) [01 §Language Handling + AAPB]. 01 gate is CER drop ≥0.02 when hotwords present. | Block; verify `hotwords`/`initial_prompt` wired; try `language="tl"` pin. |
| **Latency** | all | p50 STT+polish **<1.0s** for ≤12s utterances | Map Wispr parity <1s (Wispr <700ms) [map] + 01's RTF 0.12–0.18 measurement; 02's polish timeout 600ms. | Warn; switch to `Qwen3-1.7B` or regex fallback (`--no-polish`). |
| **Polish fidelity** (LLM) | all | No added facts, no translation (checked by DNT + boundary + CER) | 02 prompt contract: never translate, preserve Taglish, handle backtrack. | Spot-check `per_row` polish vs raw. |

The harness prints **pass/fail per gate** and exits non-zero if any hard gate fails — suitable as a CI guard.

### Why CER for TL, WER for EN (and both for Taglish reporting)

- EN is analytic with clean word boundaries — WER is the de-facto standard and the benchmark numbers above are reported as WER. Keep WER for EN.
- Filipino/Tagalog is agglutinative with hyphen/space variation (`mag-` prefix, `kamag-anak`) and no single orthographic authority — WER punishes `kamag-anak` vs `kamag anak` as a full-word error (40–75% WER on valid variants in other languages [preprint]) while CER is ~4–11% on the same pair. Advocates for multilingual ASR evaluation show CER correlates better with human ratings even for English [Findings NAACL 2025]. halo-livestream card mandates CER as the honest metric for Taglish for the same reason.
- For Taglish we report **CER primary, WER informational** — the gate is on CER <0.25.

---

## Regression / Storage

### History: 14 days (Wispr audio playback parity)

Ticket asks "history kept 14 days like Wispr audio playback for manual listen". Wispr retains last 14 days of audio for playback; the harness mirrors that as a **rolling 14-day history of gate runs** (JSON + optional audio preview), not indefinite accumulation.

Storage options (pick one; all fit on this machine — 30 wavs ≈ 5 MB, 14 JSONs ≈ 200KB):

| Option | Where | Retention | How |
|---|---|---|---|
| **A (recommended) local `runs/`** | `eval/runs/YYYY-MM-DDTHHMMSS.json` + `runs/audio_preview/` symlink | 14 days rolling via `find runs -mtime +14 -delete` or `runs/history.csv` prune | CI step: `python -m eval.harness ... --json runs/$(date -Iseconds).json` then `python eval/prune.py --keep 14` (delete older than 14 days). Simplest, no infra, works offline, mirrors Wispr "14 days" exactly. Audio stays in `eval/audio/` (source of truth), not duplicated per run. |
| B `git` branch `research/eval-history` | Orphan branch with one commit per run (JSON only, not wavs) | `git log --since="14 days ago"` / force-push truncate | Harder to `git bisect` real code; only if remote history desired. |
| C system `journald` / `sqlite` | `~/.local/share/yawc/eval.db` | TTL delete | Overkill for Phase 1. |

Recommended **A** — the deliverable is just `prune.py` + `.gitignore` entry for `runs/`.

### CI guard before/after STT/LLM swap

The gate is a **blocking check** invoked before and after every STT or LLM change (model, `compute_type`, `hotwords`, `initial_prompt`, Q4_K_M → Q8, `ngl`, polish prompt, or dependency bump). Pattern:

```yaml
# .github/workflows/eval-gate.yml  (offline runner or container with cached models)
# or local pre-commit / pre-push hook for offline laptop:
# .git/hooks/pre-push: python -m eval.harness --model large-v3-turbo --harness eval/harness.jsonl --json runs/pre-push-$(date +%s).json || exit 1

jobs:
  gate:
    runs-on: [self-hosted, linux]  # your CachyOS laptop or Docker with --gpus all
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r eval/requirements.txt  # jiwer, faster-whisper, soundfile
      - run: python -m eval.harness --model large-v3-turbo --harness eval/harness.jsonl --json runs/ci-$(date -Iseconds).json
        env:
          HF_HUB_OFFLINE: "1"
      - run: python eval/compare.py runs/prev.json runs/ci-*.json --markdown >> $GITHUB_STEP_SUMMARY
        # compare.py: diff per-gate (ΔCER, ΔWER, ΔDNT, Δboundary, Δlatency), flag regressions > (+0.02 CER or +0.01 WER or -0.10 DNT)
      - run: python eval/prune.py --keep 14
```

`compare.py` pseudo:

```python
# eval/compare.py — regression detector
import json, sys
prev, cur = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
thresholds = {"en_wer": 0.015, "tl_cer": 0.02, "taglish_cer": 0.03, "all_cer": 0.02}
for k, tol in thresholds.items():
    delta = cur[k] - prev[k]
    if delta > tol:
        print(f"REGRESSION {k}: {prev[k]:.3f} → {cur[k]:.3f} (Δ+{delta:.3f} > {tol})", file=sys.stderr)
        sys.exit(2)  # block merge
# also check DNT/boundary drops
if cur["do_not_translate"] < prev["do_not_translate"] - 0.10: sys.exit(2)
if cur["boundary"]["rate"] < prev["boundary"]["rate"] - 0.20: sys.exit(2)
```

Keep the last passing run as `runs/baseline.json` (or tag) for delta baseline; on `main` the guard compares `HEAD` vs `HEAD~1` JSON.

### Carving the 30 (how to pick without cheating)

1. **EN 10** — prompt-sample from PLD `language=eng` `read` with `num_words` 8–18, mean duration 3–7s (avoids `isolated` 1-word and `digits`). Include 2 with numbers/emails (e.g., `john dot doe at gmail dot com`), 1 with list (`first … second … third`), 1 with backtrack cue (`actually`), rest neutral. Re-record with same mic/VAD as TL.
2. **TL 10** — prompt-sample from PLD `fil` `read` + FLEURS `fil_ph` test (formal). Must include at least 2 with `kamag-anak`, 2 with `hanggang ngayon`, 2 with `nag-aalangan`/`nag-aano` variants to stress orthography. Filter `duration 2–12s`, `num_words ≥5`.
3. **Taglish 10** — **do not sample from PLD/FSC** (no mid-clause switch). Draft 10 new sentences following halo-livestream's spontaneous pattern (median 7.3s) — English verb/noun inserted mid-Tagalog clause, e.g., "punta tayo sa meeting tomorrow at 3pm" (ticket prompt). Inspire from the 62 halo segments' sentence shapes but re-record locally for quality control.

All 30 are recorded in one session (PipeWire 16kHz, quiet room, 1–2 speakers) and frozen. If a second speaker is added later, tag `speaker` and report speaker-split CER.

---

## Proposed 30-Uutterance List (Examples — Record Locally, Freeze References)

> Record each prompt as a single hold→release utterance, 2–10s, 16kHz mono. Reference is the *intended polished* text (punctuated), which the harness normalizes for STT scoring and checks verbatim for polish scoring. Tags drive slice gates.

### EN 10 — WER gate <0.08

| id | Reference (polished) | Tags | Note |
|---|---|---|---|
| `en_01` | Hello, this is John. Can you send me the file at john.doe@gmail.com? | `email` | Dots-and-at verbalization |
| `en_02` | First, we need to update the README. Second, add tests. Third, deploy to staging. | `list` | List inference |
| `en_03` | I have a meeting tomorrow at 3 PM in the main hall. | `numbers` | Time + numeral |
| `en_04` | Please bring the report and the budget spreadsheet for review. | — | Neutral |
| `en_05` | Actually, let's move the call to Friday at ten. | `backtrack` | Polish must drop pre-backtrack, keep Friday |
| `en_06` | The file is at ~/.config/niri/config.kdl on this machine. | `path` / APP_CATEG=Other | Path inference, keep casing `niri` |
| `en_07` | Hi Priya, thanks for the update on the sprint. Looks good to me. | — | Proper noun `Priya` |
| `en_08` | Could you confirm the delivery for nine one seven three four? | `numbers` | Digit string |
| `en_09` | Let's meet at Crimson Beach Resort next Monday. | — | PLD-style hotel/landmark (isolated→read carry) |
| `en_10` | She had your dark suit in greasy wash water all year. | — | Standard pangramlike read (PLD EngShib) — mic sanity |

### TL 10 — CER gate <0.12, DNT ≥0.90, boundary ≥0.75

| id | Reference (polished) | Tags | Note |
|---|---|---|---|
| `tl_01` | Kamag-anak ko si Priya hanggang ngayon hindi pa kami nagkikita. | `boundary` `do_not_translate` | Core boundary pair — gate fails if split to `kama ganak` / `hanggang ayon` |
| `tl_02` | Magandang umaga po. Nag-aalangan na baka hindi tayo matuloy. | `do_not_translate` | Filler/backtrack variant `nag-aano → nag-aalangan` |
| `tl_03` | Ah... nag-aano ako... actually, pakisuyo, pakiulit yung instruction. | `backtrack` | Backtrack `actually` discards first clause |
| `tl_04` | Ang unemployment bumaba ng seven point four porsiyento ngayong quarter. | `numbers` `do_not_translate` | Real PLD prompt `Unemployment, bumaba ng seven point four porsiyento.` (PLD viewer) — loan numeral + boundary `porsiyento` |
| `tl_05` | Sinabi ni Governor Manny na malaking tulong ito para sa kabuhayan. | `do_not_translate` | News domain carry from PLD `BCL_Utt_News02` filial pattern |
| `tl_06` | Ikuwento sa amin ang iyong pang-araw-araw na gawain at mga lakarin. | `do_not_translate` | PLD spontaneous prompt verbatim (PLD `TGL_spontaneous.txt` 53s excerpt) — tests TL without translation |
| `tl_07` | Kapatid ko siya, hindi kasama. Hanggang ngayon magkasama pa rin kami. | `boundary` | Minimal pair `kapatid` vs `kasama` (AAPB taxonomy) + second `hanggang ngayon` |
| `tl_08` | Pasensya na po kamo sa aking pagkasala, hanggang ngayon nagsisisi ako. | `boundary` | Second `hanggang ngayon` in apology register (Bikol greet → TL adaptation) |
| `tl_09` | Magpahimo sin thyroid scan pagbalik, bukas ng umaga. | `do_not_translate` | Medical domain carry (`Thyroid Scan` PLD) — ensures `scan` not translated |
| `tl_10` | Kumusta kayo? Magkita tayo bukas sa Maynila. | — | Neutral TL greeting — DNT sanity (must stay `Kumusta`, not `How are you`) |

### Taglish 10 — CER gate <0.25 (mid-clause code-switch, never translated)

| id | Reference (polished) | Tags | Note |
|---|---|---|---|
| `taglish_01` | Punta tayo sa meeting tomorrow at 3 PM. | `do_not_translate` | Ticket canonical "punta tayo sa meeting tomorrow at 3pm" — mid-clause EN `meeting tomorrow` |
| `taglish_02` | Punta tayo sa meeting sa Friday na lang pala and bring yung report. | `backtrack` | Full 02 prompt sample with backtrack `tomorrow → Friday` |
| `taglish_03` | Yes, saglit lang, paalis ako eh. Bukas paalis na kami for the presentation. | `do_not_translate` | Adapted real halo-livestream first segment `Yes mi. Saglit lang… paalis ako eh.` [HF card quickstart] — filler `eh` vs hesitation |
| `taglish_04` | Yung file nasa ~/.config/niri/config.kdl, i mean nasa home slash enne slash dot config slash niri slash config dot kdl. | `backtrack` `path` | 02 sample — path backtrack with language mix |
| `taglish_05` | Kamag-anak ko si Priya, actually my cousin, hanggang ngayon hindi pa kami nagkikita. | `boundary` `do_not_translate` `backtrack` | Boundary + DNT + `actually` in one utterance — harshest gate item |
| `taglish_06` | Eh pasensya na po, hindi ko naintindihan yung instruction, scratch that, pakisuyo pakiulit yung instruction. | `backtrack` | 02 sample — `scratch that` English backtrack cue inside Tagalog |
| `taglish_07` | First quarter results are good, pero kailangan nating mag-cut ng costs before next week. | `list` `do_not_translate` | Work-messaging register + financial loanwords `cut costs` code-switched |
| `taglish_08` | Nag-aalangan ako kung punta tayo sa meeting tomorrow or sa Friday na lang. | `do_not_translate` | `nag-aalangan` orthography variant in Taglish context |
| `taglish_09` | Paki-send yung deck tonight, let's review it bukas ng umaga. | `do_not_translate` | Verb `paki-send` (English verb with Tagalog prefix) — must not be normalized to `send` alone |
| `taglish_10` | Hindi pala tomorrow, sa Friday na lang pala yung workshop, see you there! | `backtrack` `do_not_translate` | Tagalog backtrack cue `hindi pala` (02 fallback regex) inside Taglish |

*All 30 references above are draft prompts to be read verbatim for recording. After recording, re-transcribe any mic-specific misread and update `harness.jsonl` reference to the actual spoken words — the harness scores what was *spoken*, not what was planned.*

---

## Offline Proof

Same guarantee as 01/02 — no audio/text leaves the device after install. Ticket: "`SS -tunap` must show no egress for STT/LLM after install" [wayfinder/issues/07 …] and map " `SS -tunap` must show no egress for STT/LLM after install; Privacy Mode is not a toggle, it's architecture" [map Note 4].

### One-time online fetch (before going offline)

```bash
# STT
pip install faster-whisper soundfile jiwer
hf download Systran/faster-whisper-large-v3-turbo --local-dir ~/.cache/huggingface/hub
# or let faster-whisper auto-download on first run (01 §Offline Verification)

# LLM polish (pick one; Qwen3-1.7B is fallback, 02 §Offline)
huggingface-cli download bartowski/Qwen3-1.7B-GGUF Qwen3-1.7B-Q4_K_M.gguf --local-dir ~/.cache/yawc/models
# or bartowski/Qwen2.5-7B-Instruct-GGUF

# Datasets for *carving* prompts only (not needed at eval runtime)
# huggingface-cli download sapinsapin/pld --repo-type dataset --local-dir /tmp/pld
# Not required on the gate laptop — just sample prompts once, record locally.
```

### Offline run (the gate that matters)

```bash
export HF_HUB_OFFLINE=1
# optional hard offline: sudo iptables -A OUTPUT -m owner --uid-owner $USER -j REJECT
# or: nmcli networking off

python -m eval.harness --model large-v3-turbo --harness eval/harness.jsonl
# Expected: table printed, no TCP sockets opened

# Proof: no egress while harness runs (run in second terminal)
ss -tunap | grep -E "python|faster|whisper|llama" || echo "no egress — offline verified"
# Expected: empty (only PipeWire unix socket). Any TCP to huggingface.co / openai.com = fail.

# Alternative: flatpak/no-net manifest (05 ticket direction)
flatpak run --unshare=network com.yawc.Dictation --eval eval/harness.jsonl
# should still transcribe + polish

# Cleanup: remove offline block
# sudo iptables -D OUTPUT -m owner --uid-owner $USER -j REJECT
```

### CUDA 13.3 note (same as 01/02)

CTranslate2 pip wheels target CUDA 12.x + cuDNN 9 [https://opennmt.net/CTranslate2/installation.html](https://opennmt.net/CTranslate2/installation.html) and fail on driver 13.3 without the `nvidia-cublas-cu12` + `nvidia-cudnn-cu12==9.*` + `LD_LIBRARY_PATH` workaround tracked at [https://github.com/OpenNMT/CTranslate2/issues/1933](https://github.com/OpenNMT/CTranslate2/issues/1933). The runner probes `ctranslate2.get_cuda_device_count()` at startup; if 0, it reports `whisper.cpp CPU fallback` instead of pretending GPU ran. This is not a network issue — it's a driver mismatch that would also be caught by the latency gate.

---

## Storage / Size Accounting (This Laptop)

| Item | Size | Where |
|---|---|---|
| 30 wavs (5s avg, 16k mono PCM16) | ~30 × 5s × 32KB/s ≈ **4.8 MB** (FLAC ~2.5 MB) | `eval/audio/*.wav` (committed or git-lfs) |
| `harness.jsonl` | ~10 KB | `eval/harness.jsonl` |
| `runs/*.json` (14 days, ~1/day) | ~14 × 15 KB ≈ **210 KB** | `runs/` (gitignored, pruned) |
| Faster-whisper turbo `int8_float16` model | ~1.6 GB (FP16) / cache | `~/.cache/huggingface` (once) |
| LLM polish GGUF Qwen3-1.7B Q4_K_M | ~1.1 GB | `~/.cache/yawc/models` (once) |
| Total extra for gate beyond prior tickets | **<6 MB** committed | — |

No bucket, no cloud sync (YAWC ≠ YAWC Team Cloud [CONTEXT.md]), no `halo-livestream-raw` gated download needed for the gate itself.

---

## Sources (Primary Only)

- PLD dataset card + viewer — `sapinsapin/pld`, 334k rows, 448h, 10 langs, `speech_type`/`text_is_prompt`/`language` columns: [https://huggingface.co/datasets/sapinsapin/pld](https://huggingface.co/datasets/sapinsapin/pld)
- Filipino Speech Corpus dataset card — `sapinsapin/filipinospeechcorpus`, 305,246 rows, 65.1h, 125 speakers, 16kHz, `speech_type` / median 0.62s / p95 1.21s misuse warning: [https://huggingface.co/datasets/sapinsapin/filipinospeechcorpus](https://huggingface.co/datasets/sapinsapin/filipinospeechcorpus)
- halo-livestream dataset card — `sapinsapin/halo-livestream` (also `kumu-livestream-segmented`), 62 segments seed, `asr` 16kHz / `tts` 24kHz, MMS-300M CTC + Silero VAD + faster-whisper large-v3 `asr_cer` median 0.203, quality fields `align_score`/`asr_cer`/`overlap`/`speech_ratio`/`snr_db`/`lufs`/`clip_ratio`: [https://huggingface.co/datasets/sapinsapin/halo-livestream](https://huggingface.co/datasets/sapinsapin/halo-livestream) (= [https://huggingface.co/datasets/sapinsapin/kumu-livestream-segmented](https://huggingface.co/datasets/sapinsapin/kumu-livestream-segmented))
- halohalo repo — PLD/FSC stats (334,268 utts / 448.2h / 980 speakers; FSC pipeline `process_fsc.py`; livestream pipeline `process_livestream.py` / `docs/livestream_pipeline.md`): [https://github.com/sapinsapin/halohalo](https://github.com/sapinsapin/halohalo)
- PLD paper — 454h multilingual PLD, 10 langs: [https://aclanthology.org/anthology-files/pdf/sigul/2024.sigul-1.32.pdf](https://aclanthology.org/anthology-files/pdf/sigul/2024.sigul-1.32.pdf)
- FLEURS dataset card + viewer — `google/fleurs` 102 langs, CC-BY-4.0, n-way parallel, `fil_ph` ~3.27k rows, train/val/test via parquet; per-language ~12h / ~1–3 recordings per sentence: [https://huggingface.co/datasets/google/fleurs](https://huggingface.co/datasets/google/fleurs)
- FLEURS HF commit `2747a5f` — `fil_ph` split bytes/examples: [https://huggingface.co/datasets/google/fleurs/commit/2747a5f283e09be566127752966bc2768108c844](https://huggingface.co/datasets/google/fleurs/commit/2747a5f283e09be566127752966bc2768108c844)
- FLEURS paper — 102 langs, FLoRes-101 base: [https://doi.org/10.48550/arxiv.2205.12446](https://doi.org/10.48550/arxiv.2205.12446)
- NCSpeech model card — `stt_tl_fastconformer_hybrid_large` 115M hybrid, FLEURS `fil_ph` WER table (9.34% / turbo 11.60% / ElevenLabs 9.19% / Google 7.42%): [https://huggingface.co/NCSpeech/stt_tl_fastconformer_hybrid_large](https://huggingface.co/NCSpeech/stt_tl_fastconformer_hybrid_large)
- whisper-small-fsc — WER 0.1591 CER 0.0706 lowercased on FSC held-out: [https://huggingface.co/sapinsapin/whisper-small-fsc](https://huggingface.co/sapinsapin/whisper-small-fsc)
- whisper-small-pld-fil — WER 0.1145 CER 0.0463 lowercased on PLD: [https://huggingface.co/sapinsapin/whisper-small-pld-fil](https://huggingface.co/sapinsapin/whisper-small-pld-fil)
- SYSTRAN faster-whisper — CTranslate2, 4× faster, benchmarks 13min 4525MB FP16 / 2953MB int8, turbo 2537MB FP16 / 1545MB int8, WER 1.9%: [https://github.com/SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper) / turbo issue [https://github.com/SYSTRAN/faster-whisper/issues/1030](https://github.com/SYSTRAN/faster-whisper/issues/1030)
- CTranslate2 hardware / install — compute ≥3.5, CUDA 12.x requirement: [https://opennmt.net/CTranslate2/hardware_support.html](https://opennmt.net/CTranslate2/hardware_support.html) / [https://opennmt.net/CTranslate2/installation.html](https://opennmt.net/CTranslate2/installation.html)
- CTranslate2 CUDA 13 issue + pip `cu12` workaround: [https://github.com/OpenNMT/CTranslate2/issues/1933](https://github.com/OpenNMT/CTranslate2/issues/1933)
- OpenAI whisper / whisper-large-v3-turbo — 809M 32-enc/4-dec, 99 langs including `tl`: [https://huggingface.co/openai/whisper-large-v3-turbo](https://huggingface.co/openai/whisper-large-v3-turbo)
- AAPB Tagalog assessment — `kapatid`/`kasama`, `kamag-anak` boundary, `hanggang ngayon` drop, translation tendency with `language=None` vs `tl` pin: [https://blog.americanarchive.org/2023/08/24/assessment-of-whisper-ai-as-a-tagalog-language-transcription-tool/](https://blog.americanarchive.org/2023/08/24/assessment-of-whisper-ai-as-a-tagalog-language-transcription-tool/)
- Silero VAD — 2MB JIT, <1ms/30ms chunk, 16kHz: [https://github.com/snakers4/silero-vad](https://github.com/snakers4/silero-vad)
- MMS-300M CTC forced alignment — romanization-based code-switch-safe (halo-livestream §How it was built): [HF card above] + pipeline in [halohalo repo]
- jiwer — WER/CER via RapidFuzz, `wer`/`cer`/`process_words`/`process_characters`, default includes space in CER: [https://jitsi.github.io/jiwer/](https://jitsi.github.io/jiwer/) / [https://github.com/jitsi/jiwer](https://github.com/jitsi/jiwer) / [https://pypi.org/project/jiwer/](https://pypi.org/project/jiwer/)
- CER advocacy — CER correlates better than WER for multilingual / orthographic variance (rank +4.75%): [https://aclanthology.org/2025.findings-naacl.277/](https://aclanthology.org/2025.findings-naacl.277/) / preprint [https://doi.org/10.48550/arxiv.2410.07400](https://doi.org/10.48550/arxiv.2410.07400)
- PolyWER — code-switch tolerant WER via CER α=0.25 + BERT β=0.85, α threshold for transliteration: [https://aclanthology.org/2024.findings-emnlp.356.pdf](https://aclanthology.org/2024.findings-emnlp.356.pdf)
- Common Voice dataset infra — MDC / SCS/SPS/CS types / releases 25.0 290 langs: [https://github.com/Common-Voice/cv-dataset](https://github.com/Common-Voice/cv-dataset) / [https://mozilladatacollective.com/organization/cmfh0j9o10006ns07jq45h7xk](https://mozilladatacollective.com/organization/cmfh0j9o10006ns07jq45h7xk) / [https://commonvoice.mozilla.org](https://commonvoice.mozilla.org)
- Moiz? Common Voice 19.0 release 131 langs (no large tl): [https://www.mozillafoundation.org/en/blog/common-voice-190/](https://www.mozillafoundation.org/en/blog/common-voice-190/)
- Prior decisions: [research/01-stt-engine-taglish.md](01-stt-engine-taglish.md) / [research/02-local-llm-polish.md](02-local-llm-polish.md) / ticket [wayfinder/issues/07-taglish-eval-harness.md](../wayfinder/issues/07-taglish-eval-harness.md) / map [wayfinder/map.md](../wayfinder/map.md)
