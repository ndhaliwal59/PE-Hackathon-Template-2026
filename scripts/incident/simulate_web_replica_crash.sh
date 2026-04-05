#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

log() {
  printf '%s\n' "$*"
}

die() {
  printf '%s\n' "Error: $*" >&2
  exit 1
}

web_service="web2"
proxy_health_url="${INCIDENT_BASE_URL:-http://localhost}/health"

ensure_stack() {
  if curl -fsS "$proxy_health_url" >/dev/null 2>&1; then
    return 0
  fi

  log "Starting the Compose services needed for the demo..."
  docker compose up -d --build postgres redis web1 web2 web3 nginx >/dev/null
}

log "Starting HA recovery demo for $web_service"
ensure_stack

log "Waiting for the Nginx path to become healthy..."
i=1
while [ "$i" -le 30 ]; do
  if curl -fsS "$proxy_health_url" >/dev/null; then
    log "Nginx health OK before the crash."
    break
  fi

  i=$((i + 1))
  sleep 2
done

[ "$i" -le 30 ] || die "Nginx health check failed before the demo."

web_container_id="$(docker compose ps -q "$web_service")"
[ -n "$web_container_id" ] || die "Could not find the $web_service container."

before_restart_count="$(docker inspect --format '{{.RestartCount}}' "$web_container_id")"
log "$web_service restart count before crash: $before_restart_count"

web_pid="$(docker compose exec -T "$web_service" sh -lc 'set -- $(cat /proc/1/task/1/children); printf "%s" "$1"')"
[ -n "$web_pid" ] || die "Could not find the running child process inside $web_service."

log "Crashing $web_service child process $web_pid..."
docker compose exec -T "$web_service" sh -lc "kill -9 $web_pid" >/dev/null 2>&1 || true

log "Watching Nginx stay available while $web_service restarts..."
restarted=0
i=1
while [ "$i" -le 30 ]; do
  if curl -fsS "$proxy_health_url" >/dev/null; then
    log "Nginx health OK (attempt $i)"
  else
    log "Nginx health temporarily failed (attempt $i)"
  fi

  current_restart_count="$(docker inspect --format '{{.RestartCount}}' "$web_container_id")"
  if [ "$current_restart_count" -gt "$before_restart_count" ]; then
    restarted=1
    log "$web_service restart count increased to $current_restart_count"
    break
  fi

  i=$((i + 1))
  sleep 2
done

[ "$restarted" -eq 1 ] || die "$web_service did not restart in time."

log "Waiting for $web_service to report healthy again..."
j=1
while [ "$j" -le 20 ]; do
  if docker compose exec -T "$web_service" sh -lc 'python -c "import urllib.request; urllib.request.urlopen(\"http://127.0.0.1:5000/health\", timeout=2).read()"' >/dev/null 2>&1; then
    log "$web_service is healthy again."
    break
  fi

  j=$((j + 1))
  sleep 2
done

[ "$j" -le 20 ] || die "$web_service did not recover health in time."

curl -fsS "$proxy_health_url" >/dev/null || die "Nginx health check failed after recovery."

log "Demo complete: Nginx stayed available and $web_service recovered."
