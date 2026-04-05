# Incident Runbook

> **Audience:** The on-call engineer at 3 AM who is not functioning.
> Read the alert name, jump to the matching section, follow the steps.

---

## Quick links

| Tool | URL |
|------|-----|
| Grafana dashboard | [http://localhost:3000/d/incident-command-center](http://localhost:3000/d/incident-command-center) |
| Prometheus | [http://localhost:9090](http://localhost:9090) |
| Alertmanager | [http://localhost:9093](http://localhost:9093) |

For the replicated web crash recovery demo, see [RELIABILITY.md](RELIABILITY.md#ha-recovery-demo).

---

## General triage (first 2 minutes)

1. Open the **Incident Command Center** dashboard in Grafana.
2. Check the **Firing Alerts** panel at the bottom — it shows exactly which alerts Prometheus considers active.
3. Glance at the **Replica Status** and **Blackbox Probe** stat panels — are all three replicas UP? Is the nginx health check green?
4. Look at the four golden-signal panels (Latency, Traffic, Errors, Saturation) for the time window surrounding the alert.
5. If you need raw logs: `docker compose logs -f --tail 50 web1 web2 web3`.

---

## Alert: ServiceDown (severity: critical)

**What it means:** The blackbox probe to `http://nginx/health` returned failure for at least 2 minutes. End users cannot reach the application.

### Dashboard signals

- **Blackbox Probe** stat turns red / shows "DOWN".
- **Synthetic Latency** panel flatlines or disappears.
- **Traffic** panel drops to zero (no requests reaching backends).

### Steps

1. Run `docker compose ps` — is the `nginx` container running?
2. If nginx is stopped: `docker compose start nginx`. Wait 30 seconds, verify the Blackbox Probe stat turns green.
3. If nginx is running but unhealthy, check its logs: `docker compose logs --tail 30 nginx`.
4. Check whether backend replicas are reachable: `docker compose exec nginx curl -sS http://web1:5000/health`.
5. If backends are down, restart them: `docker compose restart web1 web2 web3`.

### Resolution

Confirm `probe_success == 1` on Prometheus or the dashboard stat is green. The alert auto-resolves after one successful scrape cycle (~15 s).

---

## Alert: HighErrorRate (severity: warning)

**What it means:** More than 5% of HTTP responses across all replicas have been 5xx for at least 2 minutes. Something is throwing server errors.

### Dashboard signals

- **Error Ratio** panel rises above the 0.05 threshold line.
- **Errors (req/s)** panel shows a spike in the 5xx series.
- **Latency** p95/p99 may also climb if errors are slow failures.

### Steps

1. Check structured logs for the error source:
   ```bash
   docker compose logs --tail 100 web1 web2 web3 | grep '"levelname": "ERROR"'
   ```
2. Look at the `path` and `status_code` fields in log lines to identify which endpoint is failing.
3. Common causes:
   - **Database connection lost** — check `docker compose ps postgres` and `docker compose logs postgres`.
   - **Redis down** — check `docker compose ps redis` and `docker compose logs redis`.
   - **Application bug** — look for stack traces in the log output.
4. Once the root cause is fixed, the 5xx rate drops and the alert auto-resolves after the `for: 2m` window clears.

### Resolution

Confirm the **Error Ratio** panel is back below 0.05. Verify in Alertmanager that the alert has moved to "resolved."

---

## Alert: HighCPU (severity: warning)

**What it means:** At least one web replica's process CPU usage exceeded 90% for at least 2 minutes. The replica may be saturated and responding slowly.

### Dashboard signals

- **Saturation (CPU & Memory %)** panel shows one or more CPU lines near or above 90%.
- **Latency** p95/p99 likely increases as the overloaded replica gets slower.

### Steps

1. Identify the hot replica from the dashboard legend (e.g. `cpu web2:5000`).
2. Check what it is doing:
   ```bash
   docker compose exec web2 top -bn1
   ```
3. Check if there is runaway application work:
   ```bash
   docker compose logs --tail 50 web2
   ```
4. If a simulation is running, stop the CPU burn:
   ```bash
   curl -X POST http://localhost/simulation/cpu-burn/stop
   ```
5. As a quick mitigation, restart the hot replica: `docker compose restart web2`.

### Resolution

Confirm CPU in the Saturation panel drops below 90%. The alert auto-resolves after the `for: 2m` window clears.

---

## Escalation

If the issue is not resolved within 15 minutes:

1. Notify the team lead / project owner (Slack / Discord).
2. Collect a snapshot: screenshot the Grafana dashboard, copy the last 200 log lines (`docker compose logs --tail 200 > incident_$(date +%s).log`).
3. If data loss is possible (database issues), prioritize backups before further debugging.

---

## Sherlock Mode: diagnosing a fake incident from the dashboard

This walkthrough demonstrates how to find a root cause using only the dashboard and logs (the "Sherlock Mode" verification for Gold tier).

### Scenario: High Error Rate

1. **Enable simulation** (if not already):
   ```bash
   # In .env set INCIDENT_SIMULATION_ENABLED=true, then:
   docker compose up -d --build
   ```

2. **Trigger the incident:**
   ```bash
   ./scripts/incident/simulate_high_error_rate.sh
   ```

3. **Observe the dashboard** (wait ~2 minutes for the rule to evaluate):
   - The **Error Ratio** panel climbs past the 0.05 red threshold.
   - The **Errors (req/s)** panel shows a clear 5xx spike.
   - The **Firing Alerts** bar chart lights up with `HighErrorRate (warning)`.
   - **Traffic** remains steady (the simulation is adding load, not reducing it).
   - **Latency** p95 may rise slightly as error responses take time.

4. **Narrow the root cause from logs:**
   ```bash
   docker compose logs --tail 30 web1 | grep '"status_code": 500'
   ```
   The log lines show `"path": "/simulation/http-500"` and `"levelname": "ERROR"` — the failures are isolated to the simulation endpoint, not organic traffic.

5. **Conclusion:** Root cause is the simulation script flooding `/simulation/http-500`. In a real incident, the `path` field in the logs would point to the failing endpoint, and you would investigate that endpoint's dependencies (database, Redis, external API).

6. **Resolve:** Stop the simulation script (Ctrl+C or wait for it to finish). The error ratio drops and the alert auto-resolves.

This process — dashboard signals first, then targeted log queries — is the pattern for any production incident.
