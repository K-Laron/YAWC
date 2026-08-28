#!/usr/bin/env python3
# ponytail: Dictation deep module — dictate(Utterance) -> str, owns STT+Context+Polish.
# Pure compute: no UI writes (pill belongs to Recorder), paste stays outside.
import dataclasses

@dataclasses.dataclass
class Utterance:
    wav_path: str
    cursor_left: str = ""
    app_id: str = ""
    title: str = ""
    transform_mode: str = ""  # 05: concise/reword/structure/custom/free-text instruction


class Dictation:
    def __init__(self, hotwords: str = ""):
        self.hotwords = hotwords

    def dictate(self, u: Utterance, polish: bool = True) -> str:
        # <1s target per map: audio stop -> text ready. Phase timings -> latency.log
        import time
        t0 = time.perf_counter()
        raw = self._transcribe(u.wav_path)
        stt_ms = (time.perf_counter() - t0) * 1000
        if not raw:
            return ""
        t1 = time.perf_counter()
        raw = self._snippets(raw)
        ctx = self._context(u)
        ctx_ms = (time.perf_counter() - t1) * 1000
        if not polish:  # eval --no-polish: score raw STT
            self._log_latency(stt_ms, ctx_ms, 0.0, (time.perf_counter() - t0) * 1000)
            return raw
        t2 = time.perf_counter()
        res = (self._transform(raw, u.transform_mode)
               if u.transform_mode else self._polish(raw, ctx))
        pol_ms = (time.perf_counter() - t2) * 1000
        total_ms = (time.perf_counter() - t0) * 1000
        self._log_latency(stt_ms, ctx_ms, pol_ms, total_ms)
        # trace: raw vs polished split — enabled by `touch /tmp/yawc-trace`, local only
        try:
            import pathlib
            if pathlib.Path("/tmp/yawc-trace").exists():
                with open("/tmp/yawc-debug-transcript.log", "a") as tf:
                    tf.write(f"[{int(time.time())}] raw: {raw!r}\npolished: {res!r}\n---\n")
        except Exception:
            pass
        return res

    def _log_latency(self, stt_ms: float, ctx_ms: float, pol_ms: float, total_ms: float):
        import json, time, pathlib
        line = json.dumps({"ts": int(time.time()), "stt_ms": round(stt_ms),
                           "ctx_ms": round(ctx_ms), "polish_ms": round(pol_ms),
                           "total_ms": round(total_ms)})
        try:
            log = pathlib.Path.home() / ".local/share/yawc/latency.log"
            log.parent.mkdir(parents=True, exist_ok=True)
            with log.open("a") as f:
                f.write(line + "\n")
        except Exception:
            pass

    def _transcribe(self, wav_path: str) -> str:
        from src import stt
        try:
            return stt.transcribe(wav_path, hotwords=self.hotwords)
        except Exception:
            return ""  # no model yet (downloads later) — degrade silently

    def _snippets(self, raw: str) -> str:
        from src import polish
        return polish.expand_snippets(raw)

    def _context(self, u: Utterance):
        from src import context
        if u.cursor_left or u.app_id or u.title:
            cat = context.categorize(u.app_id, u.title)
            cursor = u.cursor_left
        else:
            ctx = context.get_context(timeout_ms=80)  # audits itself per 04
            cat, cursor = ctx["cat"], ctx["cursor_left"]
        return context.CursorContext(cursor_left=cursor, cat=cat)

    def _polish(self, raw: str, ctx) -> str:
        from src import polish
        return polish.llm_polish(raw, ctx, timeout_ms=1500)

    def _transform(self, raw: str, mode: str) -> str:
        from src import polish
        return polish.transform_text(raw, mode)


class FakeDictation(Dictation):
    # ponytail: fake for tests — in-memory, no VRAM, interface is test surface
    def __init__(self): super().__init__()
    def _transcribe(self, wav_path: str) -> str: return "hello stub"
    def _snippets(self, raw: str) -> str: return raw
    def _context(self, u: Utterance):
        from src import context
        return context.CursorContext()
    def _polish(self, raw: str, ctx) -> str: return raw


def dictate_and_paste(wav_path: str) -> str:
    # release callback for Recorder — composition root: ONE context walk feeds
    # polish facts and the paste guard; Recorder owns all pill rendering
    from src import polish, injection, context
    d = Dictation(hotwords=polish.load_hotwords())
    ctx = context.get_context(timeout_ms=80)
    u = Utterance(wav_path=wav_path, cursor_left=ctx.get("cursor_left", ""),
                  app_id=ctx.get("app_id", ""), title=ctx.get("title", ""))
    out = d.dictate(u)
    injection.inject(out, restore=True,
                     is_password=None if ctx.get("skip") else bool(ctx.get("is_password")))
    return out
