#!/usr/bin/env bash
# Stops nginx so the blackbox probe to http://nginx/health fails (ServiceDown alert after ~2m).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

docker compose stop nginx
echo "nginx is stopped. Blackbox probe should fail; expect ServiceDown after ~2 minutes."
echo "Restore with: ./scripts/incident/restore_nginx.sh"
