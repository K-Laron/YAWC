#!/usr/bin/env python3
# ponytail: Context deep module per 04 — app (niri 10ms) + cursor ±80 (Atspi 40ms,
# primary-selection fallback) + IDE file tag from title. Total ≤80ms, skip if slow.
# All on-device. Password/URL detection here too (04 exclusion + injection guard).
import json, re, subprocess, time
from dataclasses import dataclass

FILE_RE = re.compile(r"[\w./-]+\.(py|rs|ts|tsx|js|jsx|json|md|kdl|toml|go|c|cpp|h|css|html|sh)\b")


@dataclass
class CursorContext:
    """02 prompt contract owner — built once here, never string-parsed elsewhere."""
    cursor_left: str = ""
    cat: str = "Other"

    def prompt_header(self) -> str:
        return f'left="{self.cursor_left}" app={self.cat}'


def _niri_window() -> dict:
    try:
        out = subprocess.run(["niri", "msg", "-j", "focused-window"],
                             capture_output=True, text=True, timeout=0.05)
        return json.loads(out.stdout)
    except Exception:
        return {}


def categorize(app_id: str, title: str) -> str:
    # 04 buckets; browser site sniff aggregates to same buckets
    t, a = title.lower(), app_id.lower()
    if any(x in t for x in ["gmail", "outlook", "mail"]):
        return "Email"
    if any(x in a for x in ["slack", "teams", "zoom"]):
        return "Work messaging"
    if any(x in a for x in ["telegram", "whatsapp", "discord", "messenger"]):
        return "Personal messaging"
    if any(x in t for x in ["mail", "message"]):  # browser tabs
        return "Email"
    return "Other"


def _walk_focused(deadline: float):
    """Find focused accessible object within time budget; None if slow."""
    try:
        import gi
        gi.require_version("Atspi", "2.0")
        from gi.repository import Atspi
    except Exception:
        return None
    try:
        desktop = Atspi.get_desktop(0)
        for i in range(desktop.get_child_count()):
            app = desktop.get_child_at_index(i)
            for j in range(app.get_child_count()):
                frame = app.get_child_at_index(j)
                if frame.get_state_set().contains(Atspi.StateType.ACTIVE):
                    return _find_caret(frame, deadline)
    except Exception:
        return None
    return None


def _find_caret(node, deadline: float, depth: int = 0):
    try:
        import gi
        gi.require_version("Atspi", "2.0")
        from gi.repository import Atspi
    except Exception:
        return None
    if time.time() > deadline or depth > 6 or node is None:
        return None
    try:
        if node.get_state_set().contains(Atspi.StateType.FOCUSED) and node.get_text(0, 0):
            return node
    except Exception:
        pass
    try:
        for k in range(node.get_child_count()):
            found = _find_caret(node.get_child_at_index(k), deadline, depth + 1)
            if found is not None:
                return found
    except Exception:
        pass
    return None


def _atspi_cursor(budget_ms: int = 40) -> tuple[str, bool]:
    """(cursor_left ±80 chars, is_password). Empty if nothing found in budget."""
    deadline = time.time() + budget_ms / 1000
    node = _walk_focused(deadline)
    if node is None:
        return "", False
    try:
        import gi
        gi.require_version("Atspi", "2.0")
        from gi.repository import Atspi
        is_pw = node.get_role() == Atspi.Role.PASSWORD_TEXT
        text = node.queryText()
        caret = text.get_caret_offset()
        if caret <= 0:
            return "", is_pw
        left = text.get_text(max(0, caret - 80), caret)
        return left, is_pw
    except Exception:
        return "", False


def _primary_selection() -> str:
    try:
        out = subprocess.run(["wl-paste", "-p"], capture_output=True, text=True, timeout=0.05)
        return out.stdout[:80] if out.stdout else ""
    except Exception:
        return ""


TERMINALS = ("foot", "kitty", "alacritty", "wezterm", "gnome-terminal")


def get_context(timeout_ms: int = 80) -> dict:
    start = time.time()
    win = _niri_window()
    app_id, title = win.get("app_id", "unknown"), win.get("title", "")
    cat = categorize(app_id, title)
    # 04 exclusions: terminals and URL bars never get cursor text read
    url_bar = "http" in title.lower()
    if app_id.lower() in TERMINALS or url_bar:
        cursor_left, is_pw = "", False
    else:
        cursor_left, is_pw = _atspi_cursor(budget_ms=max(10, timeout_ms - 40))
        if not cursor_left:
            # ponytail: primary-selection fallback is not password-aware —
            # Chromium a11y gating (04) is the real guard there
            cursor_left = _primary_selection()
    if time.time() - start > timeout_ms / 1000:
        return {"app_id": app_id, "cat": cat, "cursor_left": "", "file_tag": "", "skip": "timeout"}
    file_tag_m = FILE_RE.search(title) if app_id.lower() in ("code", "cursor", "nvim", "zed") else None
    return {"app_id": app_id, "title": title, "cat": cat,
            "cursor_left": cursor_left, "file_tag": file_tag_m.group(0) if file_tag_m else "",
            "is_password": is_pw}


def cursor_context(ctx: dict) -> CursorContext:
    return CursorContext(cursor_left=ctx.get("cursor_left", ""), cat=ctx.get("cat", "Other"))
