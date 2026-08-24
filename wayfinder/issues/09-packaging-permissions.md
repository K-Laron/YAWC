# Packaging, autostart, and CachyOS permissions

**Type:** `wayfinder:task` — HITL (needs manual Arch check)
**Status:** closed — resolved 2026-08-24, research at `research/09-packaging-permissions.md`
**Blocks:** none (last Phase 1 ticket)
**Resolution:** PKGBUILD + install.sh + systemd niri autostart, wizard 3 screens, offline proof ss -tunap; evidence [research/09-packaging-permissions.md](../../research/09-packaging-permissions.md) — appended to map.

## Question

How does a non-technical user install and keep the clone running on **CachyOS/niri rolling** with correct Wayland permissions, and prove it is offline?

Decide:

- Package: `PKGBUILD` (AUR) vs bare `Tauri` binary + `install.sh` vs `AppImage` (note Wayland input limits); where models live (`~/.local/share/wispr-local/models` vs `/usr/share`), download-once script with checksum and offline flag
- Autostart: `niri` autostart vs `systemd --user` service vs both; tray icon, start-hidden, crash-restart
- Permissions UX: `input` group for `evdev`, `xdg-desktop-portal` screencopy for context screenshot, AT-SPI enable, mic chooser (PipeWire default source + `Microphone Quiz` like Wispr), first-run wizard steps (3 screens: mic → hotkey → test dictation)
- Offline proof: `ExecStart` with `firejail --net=none` option or `iptables` doc + `ss -tunap` verification command user can run; where telemetry would be if we had it (we don't)

Deliver install doc (`INSTALL.md` for CachyOS) + `PKGBUILD` skeleton + wizard copy + permission checklist; capture install on this laptop as video.

## Why this is blocked

Needs 03's niri glue decision and 08's total install size/VRAM to set package deps. Task — perform checklist on this box.

## Out of scope note

Team/Packaged Notetaker/MCP and TTS voices not in this ticket; they ride Phase 2 fog.
