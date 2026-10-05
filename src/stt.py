#!/usr/bin/env python3
# ponytail: STT deep module per 01 — faster-whisper large-v3-turbo int8_float16 CUDA,
# Silero VAD via vad_filter, language=None + task=transcribe (blocks translation),
# hotwords via initial_prompt. Model singleton — load once, keep hot per 08.
import array, math, os, pathlib, re, sys

os.environ.setdefault("HF_HUB_OFFLINE", "1")  # offline boundary: never fetch at runtime
MODEL_DIR = pathlib.Path.home() / ".local/share/yawc/models/faster-whisper-large-v3-turbo"
MODEL_NAME = "deepdml/faster-whisper-large-v3-turbo-ct2"
_model = None

# Precompiled regular expressions for deduplication
_REPEAT_3_PLUS_RE = re.compile(r"(\b.+?\b)(?:\s+\1){3,}", flags=re.I)
_REPEAT_ICELANDIC_RE = re.compile(r"(\b[a-zA-Záðéíóöúýþæ]{3,}\b)(?:\s+\1){2,}", flags=re.I)


class ModelMissing(Exception):
    pass


def available() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return MODEL_DIR.exists()
    except ImportError:
        return False


def _preload_cuda():
    # CachyOS: torch/ctranslate2 need system CUDA libs in LD_LIBRARY_PATH
    candidates = [
        pathlib.Path("/opt/cuda/lib64"),
        pathlib.Path("/usr/local/cuda/lib64"),
        pathlib.Path.home() / ".local/lib",
    ]
    cur = os.environ.get("LD_LIBRARY_PATH", "")
    for c in candidates:
        if c.exists() and str(c) not in cur:
            os.environ["LD_LIBRARY_PATH"] = f"{c}:{cur}" if cur else str(c)
            break


def _load():
    global _model
    if _model is not None:
        return _model
    _preload_cuda()
    from faster_whisper import WhisperModel
    # local dir per 09 layout, else HF-cache name — both local_files_only
    path = str(MODEL_DIR) if MODEL_DIR.exists() else MODEL_NAME
    _model = WhisperModel(path, device="cuda", compute_type="int8_float16", local_files_only=True)
    return _model


def _wav_is_silence(wav_path: str, thresh: float = 0.008) -> bool:
    # ponytail: long silent holds (11s) hallucinate Icelandic/Spanish loops — catch before Whisper
    # Check whole-file RMS; short clips (<0.6s) let Whisper/VAD decide
    try:
        p = pathlib.Path(wav_path)
        sz = p.stat().st_size if p.exists() else 0
        if sz <= 44 + 9600:  # <0.3s
            return False
        audio_bytes = sz - 44
        samples = array.array("h")
        with open(p, "rb") as f:
            if audio_bytes <= 1024 * 1024:
                f.seek(44)
                data = f.read()
                n_bytes = len(data) - (len(data) % 2)
                samples.frombytes(data[:n_bytes])
            else:
                # Sample 32 chunks evenly across the file to cover beginning, middle, and end
                num_chunks = 32
                chunk_size = 32768  # 32KB = 16k samples = 1s per chunk
                interval = (audio_bytes - chunk_size) // (num_chunks - 1)
                for i in range(num_chunks):
                    f.seek(44 + i * interval)
                    data = f.read(chunk_size)
                    n_bytes = len(data) - (len(data) % 2)
                    samples.frombytes(data[:n_bytes])
        if sys.byteorder == "big":
            samples.byteswap()
        n = len(samples)
        if n < 1024:
            return False
        # sample at most ~32k samples evenly to avoid scanning huge files fully
        step = max(1, n // 32000)
        sampled = samples[::step] if step > 1 else samples
        rms = math.sqrt(sum(s * s for s in sampled) / len(sampled)) / 32768.0
        return rms < thresh
    except Exception:
        return False


def _dedupe_hallucination(text: str) -> str:
    # ponytail: Whisper loops on silence/noise — "X X X" where X is 4+ words repeated.
    # Collapse consecutive repeated n-grams (4-7 words) instead of pasting the loop.
    if not text:
        return ""
    words = text.split()
    if len(words) < 8:
        return text
    # 4-gram dedupe: slide window, require at least 3 consecutive copies before deleting
    for n in (6, 5, 4):
        i = 0
        while i + 3 * n <= len(words):
            phrase = [w.lower() for w in words[i:i + n]]
            if phrase == [w.lower() for w in words[i + n:i + 2 * n]] and phrase == [w.lower() for w in words[i + 2 * n:i + 3 * n]]:
                end = i + n
                while end + n <= len(words) and phrase == [w.lower() for w in words[end:end + n]]:
                    end += n
                del words[i + n:end]
            else:
                i += 1
    t = " ".join(words)
    # also strip single-token runs >3 ("ja ja ja ja" / "the the the the")
    t = _REPEAT_3_PLUS_RE.sub(r"\1", t)
    # catch Icelandic/Nordic loop tokens common in Turbo silence: "og", "að", "er", "sem"
    t = _REPEAT_ICELANDIC_RE.sub(r"\1", t)
    return t.strip()


def preload():
    # Long-lived daemons call this once at startup; one-shot CLIs never do.
    _load()


def transcribe(wav_path: str, hotwords: str = "") -> str:
    """wav (16kHz mono S16) -> raw transcript. Raises ModelMissing if no model."""
    if not available():
        raise ModelMissing("faster-whisper or model not installed — download per INSTALL.md")
    # 01/09: local faster-whisper inference in <150ms for short audio,
    # never translates Taglish (language=None + task="transcribe").
    # Silence guard runs first — avoid spinning GPU on empty audio.
    if _wav_is_silence(wav_path):
        return ""
    m = _load()
    segs, info = m.transcribe(
        wav_path,
        language=None,             # auto-detect per utterance; EN + Tagalog both work
        task="transcribe",         # CRITICAL: "translate" would force EN, violating 01
        vad_filter=True,           # Silero VAD drops leading/trailing/inter-phrase silence
        vad_parameters=dict(
            min_silence_duration_ms=250,
            speech_pad_ms=100,
        ),
        beam_size=1,               # greedy — fastest on RTX 3050 (<150ms typical)
        best_of=1,
        temperature=0.0,
        initial_prompt=hotwords or None,  # dictionary hotwords bias acoustic decoder
        condition_on_previous_text=False, # prevent cross-utterance hallucination bleed
        log_prob_threshold=-1.0,   # drop pure noise hallucination segments
        no_speech_threshold=0.6,
    )
    # segment-level guard: Whisper still emits low-confidence hallucinations (e.g. Icelandic on silence)
    kept = []
    for s in segs:
        # faster-whisper exposes per-segment no_speech_prob / avg_logprob
        try:
            if getattr(s, "no_speech_prob", 0) > 0.6:
                continue
            if getattr(s, "avg_logprob", 0) < -1.0:
                continue
        except Exception:
            pass
        t = s.text.strip()
        if t:
            kept.append(t)
    out = " ".join(kept).strip()
    return _dedupe_hallucination(out)
