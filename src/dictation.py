#!/usr/bin/env python3
# ponytail: Dictation deep module — dictate(Utterance) -> str, owns STT+Context+Polish,
# paste stays outside. Pill states via src/pill. Backtrack/snippets live in polish.
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
        import src.pill as pill
        pill.transcribing()
        raw = self._transcribe(u.wav_path)
        stt_ms = (time.perf_counter() - t0) * 1000
        if not raw:
            pill.idle()
            return ""
        t1 = time.perf_counter()
        raw = self._snippets(raw)
        ctx = self._context(u)
        ctx_ms = (time.perf_counter() - t1) * 1000
        if not polish:  # eval --no-polish: score raw STT
            self._log_latency(stt_ms, ctx_ms, 0.0, (time.perf_counter() - t0) * 1000)
            pill.polished(raw)
            return raw
        t2 = time.perf_counter()
        res = (self._transform(raw, u.transform_mode)
               if u.transform_mode else self._polish(raw, ctx))
        pol_ms = (time.perf_counter() - t2) * 1000
        total_ms = (time.perf_counter() - t0) * 1000
        self._log_latency(stt_ms, ctx_ms, pol_ms, total_ms)
        pill.polished(res)
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
            cursor, ctx = u.cursor_left, None
        else:
            ctx = context.get_context(timeout_ms=80)
            cat, cursor = ctx["cat"], ctx["cursor_left"]
            self._audit(ctx)
        return context.CursorContext(cursor_left=cursor, cat=cat)

    def _audit(self, ctx: dict) -> None:
        # 04: on-device audit log of context reads, 14-day prune — never the text itself
        import json, time, pathlib
        log = pathlib.Path.home() / ".local/share/yawc/context.log"
        try:
            log.parent.mkdir(parents=True, exist_ok=True)
            now = time.time()
            lines = []
            if log.exists():
                for ln in log.read_text().splitlines():
                    try:
                        if now - json.loads(ln)["ts"] < 14 * 86400:
                            lines.append(ln)
                    except Exception:
                        pass
            lines.append(json.dumps({"ts": int(now), "app": ctx.get("app_id"),
                                     "cat": ctx.get("cat"), "cursor_len": len(ctx.get("cursor_left", ""))}))
            log.write_text("\n".join(lines) + "\n")
        except Exception:
            pass

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
    # release callback for Recorder — dictate then inject into the focused field
    from src import polish, injection
    d = Dictation(hotwords=polish.load_hotwords())
    out = d.dictate(Utterance(wav_path=wav_path))
    if out:
        injection.inject(out, restore=True)
    return out
