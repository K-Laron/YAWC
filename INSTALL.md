# INSTALL — YAWC on CachyOS/niri

## 1. Install (no root)

```bash
sudo pacman -S --needed wtype wl-clipboard alsa-utils at-spi2-core pipewire gtk4-layer-shell
./packaging/install.sh          # copies to ~/.local/share/yawc, units, niri snippet, wizard
```

Add the printed binds block to `~/.config/niri/config.kdl`.

## 2. Models (you do this, once, online)

```bash
pip install --user --break-system-packages faster-whisper
huggingface-cli download Systran/faster-whisper-large-v3-turbo \
  --local-dir ~/.local/share/yawc/models/faster-whisper-large-v3-turbo
huggingface-cli download bartowski/Qwen3-1.7B-GGUF Qwen3-1.7B-Q4_K_M.gguf \
  --local-dir ~/.local/share/yawc/models
# llama.cpp CUDA build:
#   cmake -B build -DGGML_CUDA=ON && cmake --build build -j
#   cp build/bin/llama-server ~/.local/share/yawc/bin/
```

Without models everything still runs — STT returns empty, polish falls back to regex.

## 3. Run

```bash
systemctl --user enable --now yawc-pill yawc-evdev   # pill overlay + Right Alt evdev hold
# or niri spawn-at-startup per install.sh snippet
yawc-daemon toggle                                   # hold→release dictation (niri bind)
yawc-daemon command                                  # Ctrl+Win+Alt command mode
```

## 4. Verify

```bash
./packaging/offline-proof.sh                          # no egress outside loopback
HF_HUB_OFFLINE=1 python -m eval.harness --harness eval/harness.jsonl   # 5 gates: EN WER, TL CER, Taglish CER, DNT >=0.90, boundary >=0.75
```

## Config

`~/.config/yawc/`: `dictionary.json` (hotwords), `snippets.json` (voice cue → text),
`transforms.json` (custom transforms). LLM model override: `YAWC_LLM_MODEL` env.
