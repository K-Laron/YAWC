#!/usr/bin/env python3
# ponytail: Dictation deep module per improve candidate 1 — Strong
# interface: dictate(Utterance) -> str, owns STT+Polish+Context, leaves paste outside
import dataclasses, time, json, pathlib, subprocess

@dataclasses.dataclass
class Utterance:
    wav_path: str
    cursor_left: str = ""
    app_id: str = ""
    title: str = ""
    transform_mode: str = ""  # 05: concise/reword/structure/custom
    # ponytail: Data Clumps fix — wav+cursor+app travel together

class Dictation:
    def __init__(self, hotwords: list[str], transforms: dict):
        self.hotwords = hotwords
        self.transforms = transforms
        self.hotwords_str = " ".join(hotwords)

    def dictate(self, u: Utterance) -> str:
        # ponytail: locality — Backtrack fix concentrates here, pill state via src/pill
        try: import src.pill as pill; pill.recording(1)
        except: pass
        raw = self._transcribe(u.wav_path)
        try: import src.pill as pill; pill.transcribing()
        except: pass
        ctx = self._get_context(u)
        if len(raw) > 500: raw = raw[:500]
        res = self._transform(raw, u.transform_mode, ctx) if u.transform_mode else self._polish(raw, ctx)
        try: import src.pill as pill; pill.polished(res)
        except: pass
        return res

    def _transcribe(self, wav_path: str) -> str:
        try:
            from faster_whisper import WhisperModel
            m = WhisperModel("large-v3-turbo", device="cuda", compute_type="int8_float16", local_files_only=True)
            segs, _ = m.transcribe(wav_path, language=None, task="transcribe", hotwords=self.hotwords_str, beam_size=5)
            return " ".join(s.text for s in segs)
        except:
            return f"[stub: {wav_path} hotwords={self.hotwords_str[:20]}]"

    def _get_context(self, u: Utterance) -> str:
        # 04: if Utterance already has cursor, use it else probe 80ms
        if u.cursor_left:
            cat = "Email" if "gmail" in u.title.lower() else "Other"
            return f'left="{u.cursor_left}" app={cat}'
        # probe niri + wl-paste per src/yawc_core.get_context (19ms)
        try:
            import src.yawc_core as yc
            ctx = yc.get_context(timeout_ms=80)
            return f'left="{ctx["cursor_left"]}" app={ctx["cat"]}'
        except:
            return 'left="" app=Other'

    def _polish(self, text: str, ctx: str) -> str:
        try:
            import src.yawc_core as yc
            return yc.llm_polish(text, ctx, timeout_ms=600)
        except:
            import src.yawc_core as yc
            return yc.regex_polish(text)

    def _transform(self, text: str, mode: str, ctx: str) -> str:
        import src.yawc_core as yc
        return yc.transform_text(text, mode, ctx)

class FakeDictation(Dictation):
    # ponytail: fake for tests — in-memory, no VRAM, interface is test surface
    def __init__(self): super().__init__(hotwords=[], transforms={})
    def _transcribe(self, wav_path: str) -> str: return "hello stub"
    def _get_context(self, u: Utterance) -> str: return 'left="" app=Other'
