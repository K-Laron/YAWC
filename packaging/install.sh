#!/usr/bin/env bash
# ponytail: install per 09 — bare binary layout in ~/.local/share/yawc, systemd --user,
# no root, no egress after install. Models downloaded separately (INSTALL.md step 2).
set -euo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)"
PREFIX="${HOME}/.local/share/yawc"

echo "[1/5] deps"
missing=""
for c in wtype wl-copy wl-paste arecord niri python3; do command -v "$c" >/dev/null || missing="$missing $c"; done
[ -n "$missing" ] && echo "  MISSING:$missing — sudo pacman -S wtype wl-clipboard alsa-utils niri python" && exit 1
if id -nG "$USER" | grep -qw input; then
  echo "  input group: yes (evdev hold available)"
else
  echo "  input group: NO — evdev hold needs: sudo usermod -aG input $USER + re-login"
fi

echo "[2/5] copy to $PREFIX"
mkdir -p "$PREFIX/bin" "$HOME/.local/bin" "$HOME/.config/yawc"
cp -r "$SRC/src" "$SRC/yawc-daemon" "$SRC/packaging" "$PREFIX/"
cp -n "$SRC/config/"*.json "$HOME/.config/yawc/" 2>/dev/null || true
ln -sf "$PREFIX/yawc-daemon" "$HOME/.local/bin/yawc-daemon"

echo "[3/5] systemd user units"
mkdir -p "$HOME/.config/systemd/user"
for u in yawc-pill yawc-evdev; do
  sed "s|%h/.local/share/yawc|$PREFIX|g" "$SRC/systemd/$u.service" > "$HOME/.config/systemd/user/$u.service"
done
systemctl --user daemon-reload

echo "[4/5] niri binds (add to ~/.config/niri/config.kdl)"
# keys deviate from research defaults (CapsLock/Ctrl+Win+Alt) — ergonomics fog item
cat <<'EOF'
# top-level:
spawn-at-startup "systemctl" "--user" "start" "yawc-pill"
spawn-at-startup "systemctl" "--user" "start" "yawc-evdev"
# inside binds { }:
binds {
    Alt+Meta+X   { spawn-sh "yawc-daemon toggle"; }      // hold-to-dictate (fallback; evdev hold is the hot path)
    Ctrl+Alt+X   { spawn-sh "yawc-daemon command"; }     // command mode hold
    Mod+Shift+T  { spawn-sh "yawc-daemon transform concise"; }
    Mod+Shift+R  { spawn-sh "yawc-daemon transform reword"; }
    Mod+Shift+S  { spawn-sh "yawc-daemon transform structure"; }
}
EOF

echo "[5/5] wizard"
"$PREFIX/packaging/wizard.sh" || true
echo "done — models not downloaded yet, see INSTALL.md step 2"
