# Decision Log

Technical choices for this project, with rationale and tradeoffs.

---

## Redis (cache layer)

**Choice:** Redis 7 (Alpine) as a read-through cache for short-code lookups.

**Why:** The workload is heavily read-biased — roughly 85% of traffic is `GET /s/<code>`, resolving a short code to its target URL. Without caching, every request hits Postgres. Redis keeps hot entries in memory with a 10-minute TTL for hits and a 1-minute TTL for misses (`app/cache.py`), cutting database load and dropping per-request latency significantly under concurrency.

**Tradeoff:** Adds an extra service to operate and monitor. If Redis goes down, the app falls back gracefully — `cache.py` returns `BYPASS` on connection errors, so correctness is never affected, only latency. Acceptable complexity for Gold-tier load targets.

---

## Nginx (load balancer)

**Choice:** Nginx 1.27 (Alpine) on port 80, `least_conn` balancing across three Gunicorn replicas (`web1`, `web2`, `web3`).

**Why:** Provides a single stable entrypoint for clients, distributes load based on active connection count (better than round-robin for variable request durations), and supports automatic retry on backend failures (`proxy_next_upstream error timeout http_502 http_503 http_504`, up to 3 tries). This keeps the service available when individual replicas restart or crash.

**Tradeoff:** An application-level load balancer like Nginx is simple and proven but does not auto-discover new backends — replicas are statically listed in `nginx.conf`. For this project's fixed three-replica topology that is fine; a larger deployment would use service discovery or a cloud LB.

---

## PostgreSQL (primary datastore)

**Choice:** Postgres 16 (Alpine) with a persistent Docker volume.

**Why:** Required by the application for users, URLs, and short-code data. Postgres is the default for Flask/SQLAlchemy projects, well supported, and the template ships with it. No alternative was considered since the schema and seed pipeline already target it.

---

## Observability stack (Prometheus, Alertmanager, Blackbox, Grafana)

**Choice:**

| Service | Version | Role |
|---------|---------|------|
| Prometheus | v2.55.1 | Scrapes `/prometheus/metrics` on each web replica every 15s; evaluates alert rules |
| Alertmanager | v0.28.1 | Routes firing alerts to Discord via webhook |
| Blackbox exporter | v0.25.0 | Synthetic `http_2xx` probe against `http://nginx/health` |
| Grafana | 11.4.0 | Pre-provisioned Incident Command Center dashboard (four golden signals + availability) |

**Why:** Gold-tier incident response requires defined SLOs, alerting on breaches, and a dashboard for on-call triage. Prometheus is the standard for container-native metrics; Grafana visualises them; Alertmanager delivers notifications; Blackbox probes end-to-end health through the load balancer (not just individual replicas). Together they power the three alerts in `monitoring/rules/incident.yml` (ServiceDown, HighErrorRate, HighCPU) and the runbook in `docs/RUNBOOK.md`.

**Tradeoff:** Running four additional containers on the same Docker Desktop host consumes CPU and memory that the application replicas would otherwise use. Under k6 load testing on a single machine, this reduces the maximum sustainable VUs from ~500 (app + cache + LB only) to ~310 before p95 latency breaches the 3-second SLO. See [CAPACITY_PLAN.md](CAPACITY_PLAN.md) for measured numbers. In a production environment the monitoring stack would run on separate infrastructure, eliminating this contention.
