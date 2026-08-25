#!/usr/bin/env bash
# ponytail: 3-screen wizard per 09 — mic -> hotkey -> test dictation
set -euo pipefail
YAWC="${YAWC_DIR:-$HOME/.local/share/yawc}"
[ -d "$YAWC/src" ] || YAWC="$(cd "$(dirname "$0")/.." && pwd)"

echo "== 1/3 mic check =="
echo 'say: "Kumusta Priya, punta tayo sa meeting tomorrow"'
arecord -f S16_LE -r 16000 -c 1 -d 3 /tmp/yawc-wizard.wav
echo "playing back..."
aplay /tmp/yawc-wizard.wav
read -rp "did you hear yourself? [y/N] " ok
[ "$ok" = "y" ] || { echo "fix mic (pavucontrol -> Input), rerun"; exit 1; }

echo "== 2/3 hotkey =="
echo 'add to ~/.config/niri/config.kdl:'
echo '    Alt+Meta+X { spawn-sh "yawc-daemon toggle"; }'
read -rp "bound it? [y/N] " ok
[ "$ok" = "y" ] || echo "  (toggle mode still works: yawc-daemon toggle)"

echo "== 3/3 test dictation (same recording) =="
if python3 -c "import faster_whisper" 2>/dev/null; then
  "$YAWC/yawc-daemon" dictate /tmp/yawc-wizard.wav
else
  echo "  faster-whisper not installed yet — see INSTALL.md step 2 (pip --break-system-packages)"
fi
echo "wizard done"
