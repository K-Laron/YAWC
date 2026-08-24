#!/usr/bin/env bash
# ponytail: clipboard restore paste via wtype + wl-copy — throwaway prototype
set -euo pipefail
TEXT="${1:-hello from YAWC prototype $(date +%H:%M:%S)}"
echo "[yawc-clipboard] saving original clipboard..."
ORIG="$(wl-paste 2>/dev/null || echo "")"
echo "[yawc-clipboard] original: '$ORIG'"
echo "[yawc-clipboard] copying: '$TEXT'"
printf "%s" "$TEXT" | wl-copy
sleep 0.15
echo "[yawc-clipboard] injecting via wtype Ctrl+V..."
wtype -M ctrl -k v -m ctrl
sleep 0.05
echo "[yawc-clipboard] restoring original..."
printf "%s" "$ORIG" | wl-copy || true
echo "[yawc-clipboard] done — pasted '$TEXT' and restored clipboard"
