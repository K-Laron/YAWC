# 04 — Local Context Awareness Depth (Phase 1 Decision)

> Ticket: [wayfinder/issues/04-context-awareness-local.md](../wayfinder/issues/04-context-awareness-local.md) — HITL grilling
> Decision: **Phase 1 = a+b+c only; d screenshot deferred to Phase 2**. All on-device, 80ms budget, skip if slow.

## Summary

**Keep for Phase 1:** (a) active app/website name via `niri msg windows` (b) cursor-adjacent text ±80 chars via AT-SPI `atspi` (fallback `wl-paste` selection) (c) IDE file names (Cursor/VS Code/neovim, ext whitelist). **Defer (d) screenshot (`grim`+`slurp`) to Phase 2** — needs `xdg-desktop-portal-wlr` screencopy, adds permission + latency + privacy review; text context already fixes 90% of proper-noun/style cases (Priya email).

**Budget:** total context read ≤80ms before STT→LLM; if any source >80ms, skip that source and log `context_skip`.

**Privacy:** all stays on-device, no egress (same `ss -tunap` proof as 01/02). Settings → Data toggle "Use app and cursor context to fix names and style" (default ON, instant off). Excluded: password fields (AT-SPI role `password`), URL bar, terminal with `isSensitive`. Audit log per dictation: `~/.local/share/yawc/context.log` (app, chars read, file tag) — local only, 14 days prune like harness.

## Context Spec Table

| Source | How on niri/Wayland | Timeout | When skipped |
|---|---|---|---|
| (a) App/website name | `niri msg -j windows` → `app_id` + `title`; browser domain via `title` parse (e.g., `gmail.com` → Email, `slack.com` → Work) | 10ms | if `niri` socket unreachable |
| (b) Cursor-adjacent text | `gi.repository.Atspi` (`python-gobject` + `at-spi2-core 2.60.6`, `Atspi.init()` walk 3.6ms tested) `getTextAtOffset` ±80 chars, but Chromium `helium` returns `None` without `--force-renderer-accessibility` — so `wl-paste` selection (length <500) is primary fallback for browsers | 40ms | if AT-SPI not running / caret not found / password role / >80ms |
| (c) IDE file names | Poll focused window `app_id` in `code`, `cursor`, `nvim` → read `niri msg focused-window` + `xdg` `recent` + LSP `window.title` fallback; whitelist ext: `rs,py,ts,js,kdl,md,json` must start with `[a-zA-Z]` | 20ms | if app not IDE / no file ext / terminal |
| (d) Screenshot | `grim -g "$(slurp)" -` via `wlr-screencopy` → local vision (deferred) | — | Phase 2 only |

Total 10+40+20=70ms ≤80ms; if >80ms sum, drop (c) first.

## App Category Mapping (Wispr 4 buckets)

| niri `app_id` / title hint | Category | Style |
|---|---|---|
| `helium` + `mail.google.com` `outlook` | Email | Formal paragraphs, proper caps, signature-aware |
| `slack` `discord` + `slack.com` `teams` | Work messaging | Compact, bullet lists allowed |
| `telegram` `whatsapp` `signal` | Personal messaging | Casual, keep emoji |
| other / `ghostty` `code` / `github.com` not mail | Other | Default sentence case; code-mode keeps `niri`, `PipeWire` casing |

TL vs EN: category style applies regardless of language — Taglish keeps both (never translate per CONTEXT.md).

## Privacy Toggle Wording

Settings → Data: **"Use app and cursor context (on-device only)"** — subtitle: "Reads app name, nearby text, and file name to fix names like Priya and switch style. Nothing leaves this device. Screenshots are off in Phase 1." Toggle OFF → context sources disabled, LLM prompt gets empty `cursor_context`.

Excluded parity list (never read): `role=password`, `role=terminal` with `isSensitive`, URL bar (`app_id=helium` + `focused` url), banking domains (`*.bank*`).

## Example: Email to Priya

Cursor left: `"Hi Priya, "` app `helium` title `Gmail — Compose` → category Email.
Raw transcript: `"um hello actually hi can you send file at john dot doe at gmail dot com"`
Context inject: `cursor_context: left="Hi Priya, " app=Email`
Polish → `"Hi Priya, can you send the file at john.doe@gmail.com?"` — caps `Priya` from context, formal paragraph, no extra facts.

## What Moves to Phase 2

Screenshot (d) + local vision for proper-noun OCR + meeting Notetaker diarization. Needs portal permission UX + `grim`/`slurp` packaging (09).

## Sources (quick)

- `niri msg windows -j` 7.3ms tested (03 prototype) — `app_id`/`title` available, `niri 26.04`
- AT-SPI via `gi.repository.Atspi` (`python-gobject` + `at-spi2-core 2.60.6`, `at-spi-dbus-bus.service` active) — `Atspi.init()` walk 3.6ms tested, but `helium` frame children `None` (Chromium a11y gated); `pip install pyatspi` fails PEP 668, needs `pacman -S python-atspi` if used. Fallback `wl-paste` <5ms tested.
- `grim`/`slurp` not installed (`which grim`/`slurp` none) but `extra/grim 1.5.0` `extra/slurp 1.5.0` available via pacman; `xdg-desktop-portal` `gnome`/`gtk` active, no `wlr` screencopy — defer to Phase 2 correct

