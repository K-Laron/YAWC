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
        import src.pill as pill
        pill.transcribing()
        raw = self._transcribe(u.wav_path)
        if not raw:
            pill.idle()
            return ""
        raw = self._snippets(raw)
        ctx = self._context(u)
        if not polish:  # eval --no-polish: score raw STT
            pill.polished(raw)
            return raw
        res = (self._transform(raw, u.transform_mode)
               if u.transform_mode else self._polish(raw, ctx))
        pill.polished(res)
        return res

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
        return polish.llm_polish(raw, ctx, timeout_ms=600)

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
