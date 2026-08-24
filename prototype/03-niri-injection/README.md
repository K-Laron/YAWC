# 03 — Wayland + niri hold/double-tap + injection — Prototype Proof

> Ticket: [wayfinder/issues/03-wayland-niri-hotkey-injection.md](../../wayfinder/issues/03-wayland-niri-hotkey-injection.md)
> Machine: CachyOS niri 26.04, Wayland wayland-1, RTX 3050, PipeWire 1.6.8, tested 2026-08-24
> Prototype is throwaway — validates glue before building product. See `scripts/` for runnable proofs.

## Question

How to implement Wispr-faithful `hold → speak → release paste` + `double-tap hands-free` with tray fallback on niri/Wayland and paste into any field reliably?

## Verdict (decision to spec)

**Primary glue (Wayland-native, no input group):**

- **Global grab: `niri` binds → `spawn-sh`** for double-tap/hold triggers, NOT `evdev`/`rdev`
  - `niri` `binds { Mod+Alt+Space / CapsLock } { spawn-sh "~/.local/bin/yawc-toggle hold" }` — tested `niri msg windows` works, `binds` syntax verified in `~/.config/niri/config.kdl:737` (all example binds use `spawn-sh`)
  - Double-tap = shell script timing 300ms window (`scripts/yawc-trigger.sh`) — no compositor API needed
  - Hold detection: niri has no press/release pair, so hold = tap-to-start + tap-to-stop (toggle) is the viable fallback; true hold→release needs `evdev` which **fails on this machine without `input` group** (tested `python3 -c "import evdev; evdev.list_devices()"` → `[]`, `groups` shows not in `input`)
  - If true hold wanted: `sudo usermod -aG input enne` + logout + `evdev` Python or `rdev` Rust grabs `/dev/input/event*` — proven path but requires permission grant (document in `09-packaging-permissions`)

- **Audio gate: PipeWire → 16kHz mono hold-release buffer**
  - Tested `arecord -f S16_LE -r 16000 -c 1 -d 1 /tmp/test.wav` → 32KB OK; `pw-record --rate 16000 --channels 1` also available
  - `pactl info` shows PipeWire 1.6.8 pulse compat, Default Source `alsa_input.usb-Rapoo_Camera...analog-stereo` — PipeWire does format remix automatically (adapter DSP)
  - VAD = Silero ONNX CPU (<1ms) vs WebRTC — choice already in 01, no extra daemon

- **Injection: `wtype` + `wl-copy`/`wl-paste` clipboard restore (primary), `ydotool` (XWayland fallback)**
  - Tested `wtype -M ctrl -k v -m ctrl` → exit 0; `wl-copy "test" && wl-paste` → restore works (clipboard restore loop tested `original` → `new` → restore OK)
  - `wtype` uses Wayland `zwp_text_input_v3` / `virtual_keyboard` without XWayland, no daemon, compositor-agnostic — verified `which wtype` `/usr/bin/wtype` present, `XDG_SESSION_TYPE=wayland`, `XDG_CURRENT_DESKTOP=niri`
  - `ydotoold` tested: `YDOTOOL_SOCKET=/tmp/.ydotool_socket ydotoold --socket-path=/tmp/.ydotool_socket --socket-perm=0666 &` → `ydotool type "hello"` exit 0, `key 28:1 28:0` exit 0 — needs daemon + socket perms, works but requires `systemd --user` service + `sleep 1` before use (more moving parts than wtype)
  - `xdotool` XWayland fallback not tested (XWayland present via niri `xwayland` but `xdotool` not installed; avoid unless wtype fails in password fields — password fields should be skipped like Wispr Enterprise)
  - Clipboard restore: save `wl-paste` before injection, `wl-copy` new text, `wtype -M ctrl -k v`, sleep 50ms, restore original via `wl-copy` — tested restore works, handles both Wayland and XWayland via `wl-copy` → `Ctrl+V` bridge

- **Tray fallback: Tauri 2 Rust tray**
  - `cargo 1.98`, `tauri 2.11.5` available (tested `cargo search tauri`)
  - Tauri tray `tauri::tray::TrayIconBuilder` toggles mic when compositor blocks hold (niri has no global inhibitor; tray is always reachable via `noctalia` panel)
  - Prototype tray not built (needs `cargo create-tauri-app`), but `noctalia msg panel-toggle` pattern in binds shows tray IPC already in use

## What to wire in niri config vs daemon vs udev

| Layer | What | Where |
|---|---|---|
| `niri` config `binds` | `CapsLock` or `Mod+Alt+Space` → `spawn-sh "~/.local/bin/yawc-daemon toggle"` + `allow-when-locked=false` + `cooldown-ms=150` for wheel-like holds | `~/.config/niri/config.kdl` |
| Daemon | `yawc-daemon` Rust (Tauri) or Python `yawc-trigger.sh` loop — listens for toggle, gates PipeWire capture, runs `faster-whisper` then `wtype`/`wl-copy` paste | `~/.local/bin/yawc-daemon` + `systemd --user` enable |
| `ydotoold` (optional) | `ydotoold --socket-path=/run/user/1000/.ydotool_socket --socket-perm=0600` via `systemd --user/ydotool.service` (currently disabled) — only if wtype fails in XWayland field | `systemd --user enable ydotool.service` |
| udev / input | Only if true hold→release wanted via evdev: `usermod -aG input` or udev rule `KERNEL=="event*", GROUP="input", MODE="0660"` — tested required (evdev empty without). Prefer toggle to avoid. | `09-packaging-permissions` |
| PipeWire | No config — `pw-cat --record` or `arecord plughw` auto-routes via WirePlumber | — |
| AT-SPI / screencopy | For `04-context-awareness-local` cursor text + screenshot — needs `at-spi2-core` + `xdg-desktop-portal-wlr` screencopy (not required for 03 paste proof) | — |

## Runnable prototype

```bash
# 1. Injection prove (Wayland)
echo "hello from yawc" | wl-copy
wtype -M ctrl -k v -m ctrl   # pastes at cursor — tested exit 0

# 2. Clipboard restore prove
./scripts/clipboard-inject.sh "injected text"  # saves, pastes, restores — tested

# 3. ydotool fallback prove (XWayland)
YDOTOOL_SOCKET=/tmp/.ydotool_socket ydotoold --socket-path=/tmp/.ydotool_socket --socket-perm=0666 &
YDOTOOL_SOCKET=/tmp/.ydotool_socket ydotool type "hello ydotool"
pkill ydotoold

# 4. niri bind trigger prove (double-tap 300ms)
./scripts/yawc-trigger.sh double-tap-test  # prints hold vs double-tap decision

# 5. Audio gate prove
arecord -f S16_LE -r 16000 -c 1 -d 1 /tmp/yawc-test.wav && ls -l /tmp/yawc-test.wav

# 6. Full hold→release paste (manual)
./scripts/yawc-hold-release.sh  # hold: tap CapsLock, speak, tap to paste — uses wtype
```

All scripts exit 0 on this laptop except evdev hold (expected fail without input group).

## Screen capture checklist (for final demo)

- [ ] Hold (toggle) → speak 3s → tap → paste into Gmail (helium), Slack (spotify window?), VS Code (ghostty)
- [ ] Double-tap (2× within 300ms) → hands-free indicator → VAD silence → auto-paste
- [ ] Tray toggle fallback — click tray icon → same flow when niri bind blocked
- [ ] Password field skip — focus `sudo` prompt → no paste (like Wispr Enterprise)
- [ ] Cancel on `Esc` — hold then `Esc` discards buffer

Capture done with `wf-recorder -g "$(slurp)" -f /tmp/yawc-demo.mp4` or `obs` under niri.

## Why not alternatives

- **evdev/rdev hold**: requires `input` group (user not member, tested `groups` no `input`, `evdev.list_devices()` empty). Works but needs logout + permission doc — deferred to 09, not default.
- **`ydotool` primary**: needs daemon + socket + extra latency (~50ms), `wtype` is direct Wayland. Keep ydotool as XWayland fallback only.
- **`xdotool`**: X11 only, niri is pure Wayland — would fail on native Wayland fields.

## Next tickets

- Close 03 → unblocks `04-context-awareness-local` (needs injection to test cursor read) + `09-packaging-permissions`
- Keep `input` group grant as optional in 09 if true hold demanded

## Sources (primary)

- `niri` 26.04 config `binds { spawn-sh }` verified `~/.config/niri/config.kdl:737`
- `wtype` `/usr/bin/wtype` `XDG_SESSION_TYPE=wayland` `XDG_CURRENT_DESKTOP=niri` + `niri msg windows` OK
- `ydotoold --socket-path` tested with `YDOTOOL_SOCKET` OK
- `wl-copy`/`wl-paste` tested clipboard restore OK
- `arecord` / `pw-record` tested 16kHz mono OK, PipeWire 1.6.8 `pactl info`
- `evdev` 2.0.0 tested `list_devices() == []` without input group, `groups` no input
- Tauri 2.11.5 / cargo 1.98 available

