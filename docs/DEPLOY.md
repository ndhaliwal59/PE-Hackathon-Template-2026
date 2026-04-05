# Deploy Guide

This guide covers local production-like deployment with Docker Compose and a safe rollback path.

## Prerequisites

- Docker + Docker Compose installed
- Repo cloned
- `.env` file created from `.env.example`

See [CONFIG.md](CONFIG.md) for all environment variables.

## Deploy (Compose)

From repo root:

```bash
cp .env.example .env
docker compose up -d --build
```

If this fails because Docker is not running, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md#docker-compose-fails-because-docker-is-not-running).

Verify key paths:

```bash
# Direct app path
curl http://localhost:5000/health

# Load-balanced path through nginx
curl http://localhost/health
```

Optional UI checks:

- Prometheus: http://localhost:9090
- Alertmanager: http://localhost:9093
- Grafana: http://localhost:3000

## Rollback

Use this when a new deployment is unhealthy.

1. Stop the current stack:

```bash
docker compose down
```

2. Check out the previous known-good commit:

```bash
git log --oneline -n 5
git checkout <good_commit_sha>
```

3. Start services again with the known-good revision:

```bash
docker compose up -d --build
```

4. Re-run health checks:

```bash
curl http://localhost:5000/health
curl http://localhost/health
```

5. Return to `main` after incident handling:

```bash
git checkout main
```

## Notes

- If startup fails due to shell-script line endings, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
- For incident triage and on-call flow, see [INCIDENT_RESPONSE.md](INCIDENT_RESPONSE.md) and [RUNBOOK.md](RUNBOOK.md).
