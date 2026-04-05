# PE Hackathon Template

Starter app for the MLH PE Hackathon.
Includes Flask, PostgreSQL, Peewee models, JSON logging, metrics, and seed loading.

## Getting Started

Two setup options are available:

- [Docker Compose - easiest option and fastest path](#docker-compose-recommended)
- [Local setup - uv + PostgreSQL](#local-setup-uv--postgresql)

## Documentation

- [API.md](API.md)
- [RELIABILITY.md](RELIABILITY.md)
- [INCIDENT_RESPONSE.md](INCIDENT_RESPONSE.md)
- [RUNBOOK.md](RUNBOOK.md)
- [SCALABILITY.md](SCALABILITY.md)

## Architecture

```mermaid
flowchart LR
    Client[Browser or curl] --> App[Flask app]
    App --> DB[(PostgreSQL)]
    App --> Logs[JSON logs]
    App --> Metrics["/metrics"]
```

## Project Structure

```text
app/
  models/
  routes/
  data/
monitoring/
nginx/
scripts/
  incident/
  k6/
API.md
README.md
RELIABILITY.md
INCIDENT_RESPONSE.md
RUNBOOK.md
SCALABILITY.md
Dockerfile
docker-compose.yml
run.py
load_seed.py
```

## Docker Compose (recommended)

This option starts the full stack: PostgreSQL, Redis, three app replicas, Nginx, Prometheus, Alertmanager, and Grafana.

### What you need

- Docker Desktop for Windows/macOS
- Docker Engine + Docker Compose plugin for Linux

Docker download/install reference:
https://www.docker.com/products/docker-desktop/

Verify:

```bash
docker --version
docker compose version
```

Clone the repo:

```bash
git clone https://github.com/ndhaliwal59/PE-Hackathon-Template-2026/
cd PE-Hackathon-Template-2026
```

Run:

```bash
docker compose up -d --build
```

Check:

```bash
curl http://localhost:5000/health
```

---

## Local Setup (uv + PostgreSQL)

### What you need

- uv
- PostgreSQL running on `localhost:5432`

1. Install uv

   Choose the command for your platform:

   - Windows PowerShell

     ```powershell
     powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
     ```

   - macOS / Linux

     ```bash
     curl -LsSf https://astral.sh/uv/install.sh | sh
     ```

   Official uv installation docs: https://docs.astral.sh/uv/getting-started/installation/

2. Clone the repo

  ```bash
  git clone https://github.com/ndhaliwal59/PE-Hackathon-Template-2026/
  cd PE-Hackathon-Template-2026
  ```

3. Install dependencies

  ```bash
  uv sync
  ```

4. Create the local `.env` file

   Choose the command for your platform:

   - Windows PowerShell

     ```powershell
     Copy-Item .env.example .env
     ```

   - macOS / Linux

     ```bash
     cp .env.example .env
     ```

5. Create the database

  ```bash
  createdb hackathon_db
  ```

6. Run the app

  ```bash
  uv run run.py
  ```

7. Check the app

  ```bash
  curl http://localhost:5000/health
  ```

## Seed Data

After app and database are ready:

```bash
uv run load_seed.py
```
