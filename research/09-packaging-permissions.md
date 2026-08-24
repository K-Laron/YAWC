# 09 — Packaging, Autostart, CachyOS Permissions

> Ticket: [wayfinder/issues/09-packaging-permissions.md](../wayfinder/issues/09-packaging-permissions.md)
> Decision: **PKGBUILD AUR + systemd --user + niri autostart, bare binary first**

## Package

- **Phase 1:** `PKGBUILD` skeleton in `packaging/PKGBUILD` + `install.sh` bare binary (Tauri `cargo build --release` → `~/.local/bin/yawc`). Models in `~/.local/share/yawc/models` + `~/.cache/huggingface` (download-once `yawc-models fetch` with SHA256, `HF_HUB_OFFLINE=1` after).
- **Not AppImage** — Wayland text-input/input limits, AUR fits CachyOS rolling.
- Deps: `wtype`, `wl-clipboard`, `at-spi2-core`, `pipewire`, `python` (CTranslate2 via pip `nvidia-cublas-cu12` per 01), `llama.cpp` binary.
- Size: turbo 1.6GB + Qwen3-1.7B 1.1GB + binary 50MB ≈2.8GB on disk, VRAM 2.6GB per 08.

## Autostart

- Both: `systemd --user` `yawc.service` (`WantedBy=default.target`, `Restart=on-failure`, `RestartSec=2`) + `niri` `spawn-at-startup "systemctl --user start yawc"` in `~/.config/niri/config.kdl`. Tray `start-hidden`, `noctalia` panel.
- `systemctl --user enable --now yawc` — keeps STT hot per 08.

## Permissions UX (first-run wizard 3 screens)

1. **Mic Quiz:** PipeWire default source `@DEFAULT_AUDIO_SOURCE` via `pactl info` + `arecord -l` chooser, test `arecord -d 2` level, whisper ~1cm hint.
2. **Hotkey:** niri binds `CapsLock` dictation + `Ctrl+Win+Alt` command (03) + `input` group optional for true hold (`sudo usermod -aG input $USER` → logout, only if user wants hold).
3. **Test Dictation:** "Kumusta Priya, punta tayo sa meeting tomorrow" → STT+polish → paste, verifies 07 harness gate local.

Checklist: `at-spi2-core` enabled (02), `xdg-desktop-portal` screencopy deferred (04), mic `audio` group already (`groups` shows `audio` yes), `input` group optional.

## Offline Proof

- After install, `yawc --offline` sets `HF_HUB_OFFLINE=1`, `iptables -A OUTPUT -m owner --uid-owner $USER -j REJECT` or `firejail --net=none yawc` — prove `ss -tunap | grep python` empty per 01/02/07. No telemetry.
- `INSTALL.md` includes `ss -tunap` + `flatpak --unshare=network` check.

## Out of Scope

Notetaker/MCP + TTS (`mms-tts-tgl`) Phase 2 fog — package not include.

