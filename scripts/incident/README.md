# Incident simulation (Silver alerts)

These scripts trigger the three Prometheus alerts. Use only on a **local / demo** stack.

## Prerequisite

1. Set in `.env` (then restart Compose so app containers pick it up):

   ```bash
   INCIDENT_SIMULATION_ENABLED=true
   ```

2. Stack up: `docker compose up -d --build`

3. Optional: `INCIDENT_BASE_URL` (default `http://localhost`) if you use another host/port. Through **nginx** use port **80** (default URL is correct).

## Scripts

| Script | Alert | What it does |
|--------|--------|----------------|
| `simulate_service_down.sh` | `ServiceDown` | `docker compose stop nginx` |
| `restore_nginx.sh` | (clear) | `docker compose start nginx` |
| `simulate_high_error_rate.sh` | `HighErrorRate` | Loops `GET /simulation/http-500` for `DURATION_SEC` (default 200s) |
| `simulate_high_cpu.sh` | `HighCPU` | POSTs `cpu-burn/start`, sleeps `DURATION_SEC`, then `cpu-burn/stop` |

## HA recovery demo

This is separate from the Silver alert simulations. It crashes `web2`, keeps traffic flowing through Nginx, and waits for the replica to restart.
The script starts the required Compose services if they are not already running.

```bash
./simulate_web_replica_crash.sh
```

Rules use `for: 2m`; keep `DURATION_SEC` at **200** or higher so the alert can fire within the quest window.

## Run

From repo root:

```bash
chmod +x scripts/incident/*.sh
./scripts/incident/simulate_service_down.sh
# after demo:
./scripts/incident/restore_nginx.sh
```

```bash
./scripts/incident/simulate_high_error_rate.sh
```

```bash
./scripts/incident/simulate_high_cpu.sh
```

**Do not** enable `INCIDENT_SIMULATION_ENABLED` in production.
