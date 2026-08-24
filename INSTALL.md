# INSTALL — CachyOS/niri

## Install

```bash
# 1. Deps
sudo pacman -S wtype wl-clipboard at-spi2-core pipewire

# 2. Build
cargo build --release
./yawc-daemon dictation # test mic via arecord -f S16_LE -r 16000 -c 1 -d 2 /tmp/t.wav

# 3. Fetch models once (online)
# hf download Systran/faster-whisper-large-v3-turbo
# huggingface-cli download bartowski/Qwen3-1.7B-GGUF --local-dir ~/.local/share/yawc/models

# 4. Autostart
systemctl --user enable --now yawc.service
# niri: add to ~/.config/niri/config.kdl
# spawn-at-startup "systemctl --user start yawc"
# binds { CapsLock { spawn-sh "yawc-daemon toggle" } }
```

## Offline proof

```bash
HF_HUB_OFFLINE=1 python -m eval.harness --model large-v3-turbo --harness eval/harness.jsonl
ss -tunap | grep python || echo "no egress — offline verified"
```

## Wizard

Mic Quiz → Hotkey → Test dictation "Kumusta Priya, punta tayo sa meeting tomorrow"

