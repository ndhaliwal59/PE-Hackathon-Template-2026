# Scalability quest

Bronze → Silver → Gold. This file tracks what each tier needs and how to run it.

---

## Bronze (baseline) — done

**Goal:** Stress test the app, **50 concurrent users**, record **p95 latency** and **error rate**.

The k6 script simulates **real shortener traffic**: mostly **`GET /s/<code>`** (link clicks), with smaller shares of **`/users/:id`**, **`/urls/:id`**, and **`/health`** (short codes aligned with `../app/data/urls.csv` in the script).

**Install k6** (not a Python package):

- macOS: `brew install k6`
- Other: [k6 install docs](https://grafana.com/docs/k6/latest/set-up/install-k6/)

**Before the test**

1. PostgreSQL running, `.env` configured.
2. API: `uv run run.py`
3. Seed once: `uv run load_seed.py`

**Run**

```bash
k6 run ../scripts/k6/bronze-baseline.js
```

Optional: `BASE_URL=http://127.0.0.1:5000 k6 run ../scripts/k6/bronze-baseline.js`

**What to save for judging**

- Screenshot of the terminal summary showing **50 VUs** (`vus_max`, or “50 looping VUs”).
- **p95** from `http_req_duration` (line `p(95)=...`).
- **Error rate** from `http_req_failed`.

Fill a small notes table in this section if you want a single place for numbers.

---

## Silver (scale out) — done

**Goal:** **200 concurrent users**, **p95 &lt; 3 s**, **horizontal** scaling (three app replicas, not bigger VMs).

**What you get:** PostgreSQL, **three** identical Flask/Gunicorn containers (`web1`, `web2`, `web3`), and **one Nginx** container on port **80** that load-balances across them (`least_conn`).

### Install

1. **Docker** — [Docker Desktop](https://docs.docker.com/desktop/) (macOS/Windows) or Docker Engine + [Compose plugin](https://docs.docker.com/compose/install/) (Linux).
2. **k6** (same as Bronze):
   - macOS: `brew install k6`
   - Other: [k6 install docs](https://grafana.com/docs/k6/latest/set-up/install-k6/)

### Configure

1. From the repo root, ensure `.env` exists and matches how you want Postgres seeded (same variables as local dev):
   ```bash
   cp .env.example .env   # edit if needed
   ```
   Compose maps these to the `postgres` service. App containers set **`DATABASE_HOST=postgres`** automatically (overrides `localhost` from `.env`).
2. **Port 80** must be free on your machine (Nginx publishes `80:80`).
3. **Docker build** uses `uv.lock`. If the file is missing, run `uv lock` once, then build again.

### Run the stack

```bash
docker compose up --build -d
```

Seed the database **once** (creates tables and loads CSVs; same as `uv run load_seed.py` locally):

```bash
docker compose run --rm web1 uv run load_seed.py
```

Quick check through the load balancer:

```bash
curl http://127.0.0.1/health
# → {"status":"ok"}
```

### Load test (200 VUs)

```bash
k6 run ../scripts/k6/silver-horde.js
```

Traffic goes to **Nginx** by default (`BASE_URL` is `http://127.0.0.1`, port 80). Override if you changed the published port:

```bash
BASE_URL=http://127.0.0.1:8080 k6 run ../scripts/k6/silver-horde.js
```

The script asserts **p(95) &lt; 3000 ms** and **http_req_failed &lt; 5%**. Traffic mix matches Bronze (mostly **`/s/...`** — same shape as [`scripts/k6/bronze-baseline.js`](../scripts/k6/bronze-baseline.js)).

### Proof for judging

- **`docker ps`** — expect **3** app containers (image built from this repo), **1** `nginx`, **1** `postgres`.
- **k6 summary** — **200** VUs (`vus_max` / “200 looping VUs”), **p(95)** on `http_req_duration`, and threshold pass/fail.

### Stop / reset

```bash
docker compose down
```

Drop the database volume as well (wipes Postgres data):

```bash
docker compose down -v
```

---

## Gold (cache + heavy load)

**Goal:** **500+ concurrent users**, **p95 &lt; 3 s**, **&lt; 5%** errors, with **Redis** caching hot short-code reads (see [`app/cache.py`](../app/cache.py), [`app/routes/urls.py`](../app/routes/urls.py)).

**Stack:** Same horizontal layout as Silver (**Postgres**, **three** Gunicorn app containers, **Nginx** on port **80**), plus a **Redis** service. Compose sets **`REDIS_URL=redis://redis:6379/0`** on each app replica (see [`docker-compose.yml`](../docker-compose.yml)).

### Install

Same as **Silver**: Docker + Compose, **k6**, and a repo-root **`.env`** (see Silver **Configure**).

### Run the Docker stack

From the **repository root**:

```bash
docker compose up --build -d
```

This builds the app image, starts **postgres**, **redis**, **web1** / **web2** / **web3**, and **nginx** (load balancer on **port 80**).

Seed the database **once** (same as local `uv run load_seed.py`):

```bash
docker compose run --rm web1 uv run load_seed.py
```

Sanity check through Nginx:

```bash
curl http://127.0.0.1/health
# → {"status":"ok"}
```

Optional: confirm cache headers (first request may be **MISS**, repeat the same URL and expect **`X-Cache: HIT`**):

```bash
curl -s -o /dev/null -D - http://127.0.0.1/s/BqJLDM | grep -i x-cache
```

### Load test (500 VUs)

```bash
k6 run ../scripts/k6/gold-tsunami.js
```

Export a summary JSON (optional):

```bash
k6 run --summary-export=../scripts/k6/summary-gold.json ../scripts/k6/gold-tsunami.js
```

The script uses **500 VUs** for **2m**, with thresholds **p(95) &lt; 3000 ms** and **http_req_failed &lt; 5%** (same traffic shape as Bronze/Silver: mostly **`/s/...`**).

### Stop / reset

```bash
docker compose down
```

Wipe Postgres (and Redis ephemeral data in the default setup):

```bash
docker compose down -v
```

---

## Files

| Tier   | Artifact |
|--------|----------|
| Bronze | [`scripts/k6/bronze-baseline.js`](../scripts/k6/bronze-baseline.js) |
| Silver | [`Dockerfile`](../Dockerfile), [`docker-compose.yml`](../docker-compose.yml), [`nginx/nginx.conf`](../nginx/nginx.conf), [`scripts/k6/silver-horde.js`](../scripts/k6/silver-horde.js) |
| Gold   | [`app/cache.py`](../app/cache.py), Redis in [`docker-compose.yml`](../docker-compose.yml), [`scripts/k6/gold-tsunami.js`](../scripts/k6/gold-tsunami.js) |
