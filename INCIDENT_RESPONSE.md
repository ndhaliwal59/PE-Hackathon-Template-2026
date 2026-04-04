# Incident Response (Bronze + Silver)

This document covers the Bronze and Silver incident response quests for this repo.

## Run the app

Start the app the same way as the rest of the project:

```bash
uv run run.py
```

If you are using Docker Compose, you can also start the full stack with:

```bash
docker compose up -d --build
```

## Check metrics

The app exposes a JSON metrics endpoint at `/metrics`:

```bash
curl http://localhost:5000/metrics
```

Example response shape:

```json
{
  "cpu_percent": 0.0,
  "memory_percent": 0.0,
  "system_memory": {
    "total_bytes": 0,
    "used_bytes": 0,
    "percent": 0.0
  }
}
```

## View logs without SSH

Use Docker Compose to follow the app logs:

```bash
docker compose logs -f --tail 20 app
```

This shows the last 20 log lines from the app container and keeps following new lines.

## Quick checks

```bash
curl http://localhost:5000/health
curl http://localhost:5000/metrics
```

If both commands return JSON successfully, the app is running and the incident response Bronze checks are in place.

## Silver (Prometheus, Alertmanager, Discord)

Silver adds **Prometheus** (rules + scraping), **Blackbox** (synthetic health through nginx), and **Alertmanager** (notifications to **Discord** via webhook). Alert rule definitions live in [`monitoring/rules/incident.yml`](monitoring/rules/incident.yml). [`monitoring/alertmanager-entrypoint.sh`](monitoring/alertmanager-entrypoint.sh) merges [`monitoring/alertmanager.yml.tpl`](monitoring/alertmanager.yml.tpl) with `DISCORD_WEBHOOK_URL` at container start.

### Configure Discord

1. Create a Discord incoming webhook for your channel.
2. Set `DISCORD_WEBHOOK_URL` in `.env` (see [`.env.example`](.env.example)). If unset, Compose uses a placeholder URL so stacks still start; Discord will reject notifications until you set a real webhook.

### Start the stack

```bash
docker compose up -d --build
```

- Prometheus UI: [http://localhost:9090](http://localhost:9090)
- Alertmanager UI: [http://localhost:9093](http://localhost:9093)

### Prometheus scrape endpoint (text)

The app still serves Bronze JSON at `/metrics`. Prometheus scrapes **text** exposition at `/prometheus/metrics` on each `web*` replica (not exposed on the host by default; use Docker networking or `docker compose exec`).

```bash
docker compose exec web1 curl -sS http://127.0.0.1:5000/prometheus/metrics | head
```

### Fire drills (demo alerts)

Helper scripts (set `INCIDENT_SIMULATION_ENABLED=true` in `.env` and restart Compose before the error-rate and CPU drills) live under [`scripts/incident/`](scripts/incident/); see [`scripts/incident/README.md`](scripts/incident/README.md).

- **Service down**: [`scripts/incident/simulate_service_down.sh`](scripts/incident/simulate_service_down.sh) stops nginx; restore with [`scripts/incident/restore_nginx.sh`](scripts/incident/restore_nginx.sh). The blackbox probe to `http://nginx/health` fails for **2+ minutes** (`ServiceDown`).
- **High error rate**: [`scripts/incident/simulate_high_error_rate.sh`](scripts/incident/simulate_high_error_rate.sh) loops `GET /simulation/http-500` so **5xx** share exceeds the rule threshold (`HighErrorRate`).
- **High CPU**: [`scripts/incident/simulate_high_cpu.sh`](scripts/incident/simulate_high_cpu.sh) starts background CPU burn in workers via `POST /simulation/cpu-burn/start` (`HighCPU`).

Alerts use `for: 2m` and 15s scrape/evaluation intervals so firing stays **within the 5-minute** quest window after the condition is true.

### Show the configuration (loot)

- Rules: [`monitoring/rules/incident.yml`](monitoring/rules/incident.yml)
- Prometheus scrape config: [`monitoring/prometheus.yml`](monitoring/prometheus.yml)
- Blackbox modules: [`monitoring/blackbox.yml`](monitoring/blackbox.yml)
- Alertmanager template (Discord webhook placeholder): [`monitoring/alertmanager.yml.tpl`](monitoring/alertmanager.yml.tpl)