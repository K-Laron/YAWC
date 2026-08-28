#!/usr/bin/env python3
# ponytail: STT deep module per 01 — faster-whisper large-v3-turbo int8_float16 CUDA,
# Silero VAD via vad_filter, language=None + task=transcribe (blocks translation),
# hotwords via initial_prompt. Model singleton — load once, keep hot per 08.
import os, pathlib

os.environ.setdefault("HF_HUB_OFFLINE", "1")  # offline boundary: never fetch at runtime
MODEL_DIR = pathlib.Path.home() / ".local/share/yawc/models/faster-whisper-large-v3-turbo"
MODEL_NAME = "large-v3-turbo"
_model = None


class ModelMissing(Exception):
    pass


def available() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return MODEL_DIR.exists()
    except ImportError:
        return False


def _preload_cuda():
    # pip nvidia wheels: ctranslate2 needs libcublas/libcudnn — load them RTLD_GLOBAL
    # before faster_whisper touches CUDA (works for systemd-spawned processes too)
    import ctypes, glob
    dirs = glob.glob(os.path.expanduser("~/.local/lib/python3.*/site-packages/nvidia/*/lib"))
    dirs += glob.glob("/usr/lib/python3*/site-packages/nvidia/*/lib")
    pats = ["libcublasLt.so*", "libcublas.so*", "libcudnn*.so*"]
    for pat in pats:
        for d in dirs:
            for so in sorted(glob.glob(f"{d}/{pat}")):
                try:
                    ctypes.CDLL(so, mode=ctypes.RTLD_GLOBAL)
                except OSError:
                    pass


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
        import struct, math
        p = pathlib.Path(wav_path)
        if not p.exists() or p.stat().st_size <= 44 + 9600:  # <0.3s
            return False
        with open(p, "rb") as f:
            f.seek(44)
            data = f.read()
        # sample at most 3s evenly to avoid reading huge files fully
        n_total = len(data) // 2
        if n_total < 1024:
            return False
        # downsample: take every k-th sample for ~32k samples max
        step = max(1, n_total // 32000)
        samples = struct.unpack(f"<{n_total}h", data[: n_total * 2])[::step]
        n = len(samples)
        rms = math.sqrt(sum(s * s for s in samples) / n) / 32768.0
        return rms < thresh
    except Exception:
        return False


def _dedupe_hallucination(text: str) -> str:
    # ponytail: Whisper loops on silence/noise — "X X X" where X is 4+ words repeated.
    # Collapse consecutive repeated n-grams (4-7 words) instead of pasting the loop.
    import re
    if not text:
        return text
    # quick compression check: highly repetitive text compresses well
    words = text.split()
    if len(words) < 12:
        return text
    # collapse "phrase, phrase, phrase" -> "phrase"
    for n in (7, 6, 5, 4):
        pat = r"\b((?:\w+(?:['-]\w+)?(?:\s+|$)){" + str(n) + r"})\1{2,}"
        # use case-insensitive for hallucinated English loops
        m = re.search(pat, text, flags=re.I)
        if m:
            # keep one copy of the repeated phrase
            text = text[: m.start()] + m.group(1).strip() + text[m.end() :]
            break
    return re.sub(r"\s+", " ", text).strip()


def transcribe(wav_path: str, hotwords: str = "") -> str:
    """wav (16kHz mono S16) -> raw transcript. Raises ModelMissing if no model."""
    if not available():
        raise ModelMissing("faster-whisper or model not installed — download per INSTALL.md")
    # long silent holds hallucinate before Whisper even runs — skip the call
    if _wav_is_silence(wav_path):
        return ""
    m = _load()
    segs, info = m.transcribe(
        wav_path,
        language=None,          # auto EN/TL, never translates per 01
        task="transcribe",
        hotwords=hotwords or None,
        initial_prompt="Transcribe Taglish code-switching exactly. Never translate Tagalog to English.",
        beam_size=5,
        vad_filter=True,        # Silero VAD bundled — trims silence per 01
        vad_parameters=dict(min_silence_duration_ms=500, threshold=0.5),
        condition_on_previous_text=False,  # break hallucination loops across segments
        compression_ratio_threshold=2.4,
        log_prob_threshold=-1.0,
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
        kept.append(s.text)
    raw = " ".join(kept).strip()
    return _dedupe_hallucination(raw)
