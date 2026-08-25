#!/usr/bin/env bash
# ponytail: offline proof per 09/CONTEXT — reviewer-runnable, no egress from YAWC procs
set -euo pipefail
echo "YAWC processes and their sockets:"
procs=$(pgrep -f "pill_overlay|yawc|arecord|llama-server" || true)
[ -z "$procs" ] && echo "  (none running — start yawc-daemon toggle first)" && exit 0
for p in $procs; do
  conns=$(ss -tunp 2>/dev/null | grep "pid=$p," || true)
  # loopback llama-server (127.0.0.1) is allowed — model inference on-device
  egress=$(echo "$conns" | grep -v "127.0.0.1\|::1" || true)
  if [ -n "$egress" ]; then
    echo "FAIL pid $p has non-loopback sockets:"; echo "$egress"; exit 1
  fi
done
echo "PASS — no egress outside loopback (offline verified)"
