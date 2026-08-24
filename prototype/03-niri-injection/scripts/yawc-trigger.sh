#!/usr/bin/env bash
# ponytail: double-tap vs hold timing prototype — 300ms window like ticket spec
set -euo pipefail
STATE_FILE="/tmp/yawc-trigger.state"
NOW=$(date +%s%3N)
LAST=$(cat "$STATE_FILE" 2>/dev/null || echo 0)
DIFF=$((NOW - LAST))
echo "$NOW" > "$STATE_FILE"
THRESHOLD=300
if [ "$DIFF" -lt "$THRESHOLD" ] && [ "$LAST" -ne 0 ]; then
  echo "[yawc-trigger] DOUBLE-TAP detected (diff ${DIFF}ms < ${THRESHOLD}ms) → hands-free mode"
  echo "hands-free" > /tmp/yawc-mode
else
  echo "[yawc-trigger] SINGLE tap (diff ${DIFF}ms) → toggle hold start/stop"
  # toggle hold state
  if [ -f /tmp/yawc-hold ]; then
    echo "[yawc-trigger] HOLD RELEASE → stop recording, transcribe, paste"
    rm -f /tmp/yawc-hold
    echo "release" > /tmp/yawc-mode
  else
    echo "[yawc-trigger] HOLD START → start PipeWire capture"
    touch /tmp/yawc-hold
    echo "hold" > /tmp/yawc-mode
  fi
fi
cat /tmp/yawc-mode
