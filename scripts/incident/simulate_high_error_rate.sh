#!/usr/bin/env bash
# Floods GET /simulation/http-500 so 5xx share exceeds the HighErrorRate rule (>5% for 2m).
# Requires INCIDENT_SIMULATION_ENABLED=true in .env and containers rebuilt/restarted.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

BASE_URL="${INCIDENT_BASE_URL:-http://localhost}"
DURATION_SEC="${DURATION_SEC:-200}"

if ! curl -fsS "${BASE_URL}/health" >/dev/null 2>&1; then
  echo "Cannot reach ${BASE_URL}/health. Use INCIDENT_BASE_URL (default http://localhost) through nginx (port 80)." >&2
  exit 1
fi

echo "Sending simulated 5xx to ${BASE_URL}/simulation/http-500 for ${DURATION_SEC}s..."
echo "Ensure INCIDENT_SIMULATION_ENABLED=true is set for app containers."

end=$((SECONDS + DURATION_SEC))
while (( SECONDS < end )); do
  curl -sS -o /dev/null "${BASE_URL}/simulation/http-500" || true
  sleep 0.05
done

echo "Done."
