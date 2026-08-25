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


def transcribe(wav_path: str, hotwords: str = "") -> str:
    """wav (16kHz mono S16) -> raw transcript. Raises ModelMissing if no model."""
    if not available():
        raise ModelMissing("faster-whisper or model not installed — download per INSTALL.md")
    m = _load()
    segs, _ = m.transcribe(
        wav_path,
        language=None,          # auto EN/TL, never translates per 01
        task="transcribe",
        hotwords=hotwords or None,
        initial_prompt="Transcribe Taglish code-switching exactly. Never translate Tagalog to English." if hotwords else None,
        beam_size=5,
        vad_filter=True,        # Silero VAD bundled — trims silence per 01
    )
    return " ".join(s.text for s in segs).strip()
