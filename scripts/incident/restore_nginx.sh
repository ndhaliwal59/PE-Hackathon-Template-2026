#!/usr/bin/env bash
# Starts nginx again after simulate_service_down.sh.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

docker compose start nginx
echo "nginx started."
