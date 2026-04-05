# Capacity Plan

How many users can we handle? Where is the limit?

---

## Scope

Full Docker Compose stack on a single machine (Docker Desktop):

- **PostgreSQL 16** — primary datastore
- **Redis 7** — short-code read cache
- **3× Flask/Gunicorn replicas** (`web1`, `web2`, `web3`)
- **Nginx 1.27** — `least_conn` load balancer on port 80
- **Prometheus, Alertmanager, Blackbox exporter, Grafana** — observability and alerting

Database seeded via `docker compose run --rm web1 uv run load_seed.py`.

## Load model

All tests use **k6** with the same traffic mix:

- ~85% `GET /s/<code>` (short-link resolution, mostly cache-backed)
- ~8% `GET /users/:id`
- ~5% `GET /urls/:id`
- ~2% `GET /health`

Each virtual user (VU) sleeps 50–300ms between requests, simulating realistic browser pacing. Requests target Nginx on `http://127.0.0.1` (port 80).

## SLOs / thresholds

| Metric | Target |
|--------|--------|
| `http_req_duration` p(95) | < 3000 ms |
| `http_req_failed` rate | < 5% |

These are enforced as k6 thresholds — a run **passes** only if both hold for the full duration.

## Results

### Before observability stack (app + Redis + Nginx only)

With Prometheus, Alertmanager, Blackbox exporter, and Grafana **not running**, the stack sustained **500 concurrent VUs** for 2 minutes while meeting both SLOs. Script: `scripts/k6/gold-tsunami.js` (500 VUs, 2m).

### After observability stack (full Compose)

With the full monitoring stack running on the same host, the validated maximum drops to **310 concurrent VUs**. Script: `scripts/k6/limit-test.js` (310 VUs, 2m).

Measured results (310 VUs, 2m run):

| Metric | Value |
|--------|-------|
| p(95) latency | 2.74s |
| p(90) latency | 2.67s |
| Median latency | 2.41s |
| Max latency | 3.18s |
| Error rate | 0.00% |
| Total HTTP requests | 14,538 |
| Throughput | ~118 req/s |
| All k6 thresholds | **PASS** |

```text
http_req_duration..............: avg=2.41s min=45.4ms med=2.41s max=3.18s p(90)=2.67s p(95)=2.74s
http_req_failed................: 0.00%  0 out of 14538
http_reqs......................: 14538  118.027125/s
iterations.....................: 14538  118.027125/s
vus............................: 10     min=10         max=310
vus_max........................: 310    min=310        max=310
```

## Where is the limit?

The **maximum validated capacity** on a single Docker Desktop host with the full stack is **310 concurrent VUs** (~118 req/s). Above this level, p95 latency is expected to exceed the 3-second SLO.

The capacity reduction from 500 to 310 VUs is caused by resource contention on a shared host. The monitoring containers (Prometheus scraping three replicas every 15s, Blackbox probing Nginx, Grafana rendering dashboards, Alertmanager evaluating rules) compete for the same CPU and memory pool as the application replicas. In a production deployment where monitoring runs on separate infrastructure, the 500-VU ceiling (or higher) would apply.

Likely bottleneck ordering on the single host:

1. **CPU saturation** — Gunicorn workers, Prometheus TSDB writes, and Grafana rendering share cores.
2. **Prometheus scrape overhead** — Three replica targets + blackbox every 15s adds load to both Prometheus and the app (serialising metrics on each scrape).
3. **Database connection pooling** — Three replicas each opening connections to one Postgres instance; under high concurrency, connection wait times grow.
4. **Redis** — Unlikely bottleneck; single-threaded but request volume (~118 req/s) is far below Redis capacity.

## Reproduce

```bash
docker compose up --build -d
docker compose run --rm web1 uv run load_seed.py
k6 run scripts/k6/limit-test.js
```

If either Docker Compose command fails because Docker is not running, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md#docker-compose-fails-because-docker-is-not-running).

The test runs 310 VUs for 2 minutes against `http://127.0.0.1` (Nginx). Both thresholds must pass for a valid result.

Reference environment: MacBook Pro, Docker Desktop.
