# Troubleshooting Guide

This document covers common issues and their solutions.

## Docker Compose Issues

### Alertmanager fails to start with "illegal option -" or "no route provided in config"

**What it looks like:**
```
alertmanager-1  | /entrypoint.sh: set: line 2: illegal option -
alertmanager-1  | time=...Z level=ERROR source=coordinator.go:117 msg="Loading configuration file failed" ... file="/tmp/alertmanager.yml\r"
```

**Root cause:**
The file `monitoring/alertmanager-entrypoint.sh` (and possibly other `.sh` files in `scripts/incident/`) have Windows line endings (CRLF instead of LF). Inside the Linux container, the shell interprets the `\r` as part of the line, breaking the script.

**How to fix:**
1. Open `monitoring/alertmanager-entrypoint.sh` in VS Code or your editor.
2. Look at the bottom-right status bar. If it says `CRLF`, click it.
3. Choose `LF` from the menu and save the file.
4. Repeat for any `.sh` files in `scripts/incident/` if the error persists.

You can also use the terminal:

```bash
# On macOS/Linux with dos2unix installed:
dos2unix monitoring/alertmanager-entrypoint.sh scripts/incident/*.sh

# On Windows with git bash:
git config core.safecrlf false  # Disable git's auto-conversion temporarily
# Then convert files as above
git config core.safecrlf true   # Re-enable after fixing
```

**Verification:**
After fixing, restart the stack:
```bash
docker compose up -d --force-recreate alertmanager
docker compose logs --tail 20 alertmanager  # Should show clean startup, no "illegal option" errors
```

---

## Test Failures

### Unit or integration tests fail with database connection errors

**How to fix:**
Ensure PostgreSQL is running locally on port 5432 and `.env` has the correct credentials:
```bash
createdb hackathon_db
uv run pytest tests/unit tests/integration
```

---

## Performance Issues

### High error rate or timeout errors under load

See [SCALABILITY.md](SCALABILITY.md) for load-testing guidance and Redis caching setup.

---

## Additional Help

Refer to the detailed documentation:
- [DEPLOY.md](DEPLOY.md) — deployment and rollback steps
- [CONFIG.md](CONFIG.md) — environment variable reference
- [INCIDENT_RESPONSE.md](INCIDENT_RESPONSE.md) — monitoring, alerting, and incident runbook
- [RELIABILITY.md](RELIABILITY.md) — error handling and chaos-mode verification
- [RUNBOOK.md](RUNBOOK.md) — on-call incident procedures
