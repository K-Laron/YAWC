#!/usr/bin/env bash
# ponytail: full hold→release flow prototype (toggle version, no evdev hold)
set -euo pipefail
MODE_FILE="/tmp/yawc-hold"
WAV="/tmp/yawc-hold.wav"
if [ -f "$MODE_FILE" ]; then
  echo "[yawc] RELEASE — stopping capture..."
  pkill -f "arecord.*$WAV" 2>/dev/null || true
  sleep 0.2
  if [ -f "$WAV" ]; then
    echo "[yawc] captured $(stat -c%s "$WAV") bytes → would transcribe via faster-whisper"
    echo "[yawc] fake transcript: 'Magandang umaga po kamag-anak'"
    echo "[yawc] polishing via regex..."
    TEXT="Magandang umaga po, kamag-anak."
    echo "[yawc] injecting: $TEXT"
    "$(dirname "$0")/clipboard-inject.sh" "$TEXT"
    rm -f "$MODE_FILE" "$WAV"
  else
    echo "[yawc] no wav — capture failed"
    rm -f "$MODE_FILE"
  fi
else
  echo "[yawc] HOLD — starting PipeWire capture to $WAV (speak now, run again to release)..."
  touch "$MODE_FILE"
  arecord -f S16_LE -r 16000 -c 1 "$WAV" &
  echo "[yawc] arecord pid $! — run $0 again to release"
fi
