#!/usr/bin/env bash
# Starts background CPU burn threads in each gunicorn worker (via POST /simulation/cpu-burn/start).
# Requires INCIDENT_SIMULATION_ENABLED=true. Hits nginx so requests spread across web1–web3.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

BASE_URL="${INCIDENT_BASE_URL:-http://localhost}"
DURATION_SEC="${DURATION_SEC:-200}"
START_HITS="${START_HITS:-15}"
STOP_HITS="${STOP_HITS:-15}"

if ! curl -fsS "${BASE_URL}/health" >/dev/null 2>&1; then
  echo "Cannot reach ${BASE_URL}/health." >&2
  exit 1
fi

echo "Posting cpu-burn/start (${START_HITS}x) to ${BASE_URL} (spread across replicas)..."
for _ in $(seq 1 "${START_HITS}"); do
  curl -fsS -o /dev/null -X POST "${BASE_URL}/simulation/cpu-burn/start" || true
done

echo "CPU burn running for ${DURATION_SEC}s (expect HighCPU after ~2m if workers stay hot)."
sleep "${DURATION_SEC}"

echo "Posting cpu-burn/stop (${STOP_HITS}x)..."
for _ in $(seq 1 "${STOP_HITS}"); do
  curl -fsS -o /dev/null -X POST "${BASE_URL}/simulation/cpu-burn/stop" || true
done

echo "Stop signals sent. Wait a few seconds for threads to exit."
