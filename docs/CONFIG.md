# Configuration Reference

This file lists environment variables used by the app and Compose stack.

## Required For Normal Run

| Variable | Example | Used by | Purpose |
| --- | --- | --- | --- |
| `DATABASE_NAME` | `hackathon_db` | App, Postgres container | Database name |
| `DATABASE_USER` | `postgres` | App, Postgres container | Database user |
| `DATABASE_PASSWORD` | `postgres` | App, Postgres container | Database password |
| `DATABASE_PORT` | `5432` | App | Database port |

## Common Runtime Variables

| Variable | Example | Used by | Purpose |
| --- | --- | --- | --- |
| `DATABASE_HOST` | `localhost` (local) / `postgres` (Compose override) | App | Database host |
| `FLASK_DEBUG` | `true` (local) / `false` (Compose override) | App | Flask debug mode |
| `REDIS_URL` | `redis://redis:6379/0` | App cache layer | Enables Redis-backed cache |
| `INCIDENT_SIMULATION_ENABLED` | `false` | Simulation routes | Enables `/simulation/*` drill endpoints |
| `DISCORD_WEBHOOK_URL` | `<discord webhook url>` | Alertmanager | Sends alert notifications to Discord |

## Compose-Managed Variables

Some variables are set by `docker-compose.yml` and override local `.env` values inside containers:

- `DATABASE_HOST=postgres`
- `FLASK_DEBUG=false`
- `REDIS_URL=redis://redis:6379/0`

## Related Docs

- Deploy steps and rollback: [DEPLOY.md](DEPLOY.md)
- Incident and monitoring setup: [INCIDENT_RESPONSE.md](INCIDENT_RESPONSE.md)
- Troubleshooting: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
