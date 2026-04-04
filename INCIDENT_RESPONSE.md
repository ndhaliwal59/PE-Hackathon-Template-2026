# Incident Response Bronze

This document covers the Bronze incident response quest for this repo.

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
  "memory_percent": 0.0
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