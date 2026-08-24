# Wayland + niri global hold/double-tap + text injection

**Type:** `wayfinder:prototype` — HITL
**Status:** closed — resolved 2026-08-24, prototype at `prototype/03-niri-injection/`
**Blocks:** 04-context-awareness-local, 09-packaging-permissions
**Resolution:** niri binds spawn-sh toggle + 300ms double-tap script, wtype+wl-copy restore primary (tested exit 0), ydotoold fallback (tested socket OK), evdev fails without input group (list_devices==[]), arecord 16kHz mono OK, Tauri 2 tray fallback available; prototype scripts + README linked — appended to map Decisions so far.

## Question

How do we implement **Wispr-faithful** `hold → speak → release paste` + `double-tap hands-free` with **tray toggle fallback** on **niri/Wayland** (no global hotkey API), and paste into any text field reliably?

Decide via a **cheap runnable prototype** (not shipped product) that proves on this laptop:

- Global grab: `niri` config `binds` → script vs `evdev`/`rdev` (needs `input` group) vs `ydotoold`/`wtype` + `sway IPC` compat; how to detect hold vs double-tap (300 ms) without swallowing other shortcuts; behavior under IME/lock screen
- Audio gate: PipeWire source select UI (`arecord -l`, `pactl`), mic quiz, whisper-mode close-talk (~1 cm) sensitivity, VAD gate vs push-hold gate, cancel on `Esc`
- Injection: `wtype` (Wayland) vs `ydotool` vs `wl-copy`+`Ctrl+V` clipboard restore (concealed vs plain), XWayland fallback via `xdotool`, handling password/numeric fields (skip like Wispr Enterprise)
- Tray fallback: `Tauri 2` Rust tray or `aylur` widget that toggles mic when compositor blocks hold

Deliver prototype repo/branch + 30-sec screen capture on niri showing hold, release→paste into Gmail/Slack/VS Code, double-tap, and tray fallback; list what needs `niri` config vs daemon vs udev.

## Why this is frontier

Platform seam — if this fails, Context/LLM choices moot. Prototype ticket — call `prototype` skill, link prototype asset, decision is which glue to spec.

## Context

Machine: `XDG_SESSION_TYPE=wayland`, `XDG_CURRENT_DESKTOP=niri`, `wl_display=wayland-1`, PipeWire; `nvidia 610.57` + `renderD128/129`; no `ydotool`/`wtype` verified yet.
