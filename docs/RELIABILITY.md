# Reliability

## Bronze Reliability

Install dev dependencies once before running test commands:

```bash
uv sync --extra dev
```

Run the unit suite locally:

```bash
uv run pytest tests/unit
```

Run the app:

```bash
uv run run.py
```

Verify `/health`:

```bash
curl http://localhost:5000/health
```

CI runs only the unit suite from [tests/unit](../tests/unit) using [`.github/workflows/bronze.yml`](../.github/workflows/bronze.yml).
Integration tests live in [tests/integration](../tests/integration) and are excluded from the Bronze workflow.

## Silver Reliability

Run integration tests locally:

```bash
uv run pytest tests/integration
```

Run tests with coverage for app code only:

```bash
uv run pytest tests/unit tests/integration --cov=app --cov-report=term-missing
```

Enforce the Silver coverage target locally (>= 50%):

```bash
uv run pytest tests/unit tests/integration --cov=app --cov-report=term-missing --cov-fail-under=50
```

Silver requires at least 50% coverage on application code. Integration tests live in [tests/integration](../tests/integration) and are included in the [Silver workflow](../.github/workflows/silver.yml). A simulated deployment job is also configured, which will be blocked and skipped if any tests fail or code coverage drops below the limit.

## Gold Reliability

Run tests with coverage for app code only:

```bash
uv run pytest tests/unit tests/integration --cov=app --cov-report=term-missing
```

Enforce the Gold coverage target locally (>= 70%):

```bash
uv run pytest tests/unit tests/integration --cov=app --cov-report=term-missing --cov-fail-under=70
```

Gold also expects graceful failure responses and restart verification. Use the Error Handling and Chaos Mode sections below.
Gold CI coverage enforcement is configured in [`.github/workflows/gold.yml`](../.github/workflows/gold.yml).

## Error Handling

The application returns JSON error responses so API clients can handle failures predictably.

* **Route-level 404s** may return resource-specific JSON such as:
  * `{"error": "url not found"}`
  * `{"error": "user not found"}`
  * `{"error": "short code not found"}`
* **Unhandled 404 errors** return `{"error": "not found"}` with a `404` status code.
* **Unhandled 500 errors** return `{"error": "internal server error"}` with a `500` status code.

Returning JSON instead of default HTML error pages gives clients a consistent failure format, makes error handling simpler, and avoids exposing internal traceback details in normal API responses.

**Live demo:** Invalid/garbage input returns a controlled error response instead of an unhandled failure.
Video: https://youtube.com/shorts/HejXgdybKMM

## Chaos Mode (Automatic Restart Verification)

The application is configured to recover automatically if its running process fails unexpectedly. This can be verified using Docker's container metadata together with the health endpoint.

**Live demo:** The service recovers after the running container/process is terminated, supporting the restart verification described in this section.
Video: https://youtube.com/shorts/gdvL17P-jf0

### Verification steps

1. Start the stack so both the database and app container are running:

```powershell
docker compose up -d --build
```

If this fails because Docker is not running, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md#docker-compose-fails-because-docker-is-not-running).

2. Confirm the service is healthy before the failure test:

```powershell
curl http://localhost:5000/health
```

This should return 200 OK with the JSON health response.
If you get a temporary connection error right after `docker compose up -d --build`, wait a few seconds and retry this health check once.

3. Check the running containers to confirm the app container is up before the failure test:

```powershell
docker compose ps
```

In the output, note the app container name in the `NAME` column.
(Should be something like `<foldername>_app_1` depending on your directory name and compose project settings.)

4. Capture the app container's current restart metadata before the failure:

```powershell
docker inspect <app-container-name> --format="RestartCount={{.RestartCount}} StartedAt={{.State.StartedAt}} Status={{.State.Status}}"
```

This gives the baseline values to compare after the process is terminated.

5. Open a shell inside the app container:

```powershell
docker compose exec app sh
```

6. Inside the container, find the running child application process:

```sh
cat /proc/1/task/1/children
```

This prints the child PID for the application process.

7. Still inside the container, terminate that child process:

```sh
kill -9 <child-pid>
```

Replace <child-pid> with the number from the previous step.

It is normal for the shell prompt to come back after this command. The restart proof comes from the host-side `docker inspect` and `curl` checks in the next steps.

8. Exit the container shell if not already done:

```sh
exit
```

9. Wait a moment and run the same inspect command again:

```powershell
docker inspect <app-container-name> --format="RestartCount={{.RestartCount}} StartedAt={{.State.StartedAt}} Status={{.State.Status}}"
```

This should show an incremented `RestartCount` and a new `StartedAt` timestamp, confirming that the orchestrator detected the failure and restarted the process.

10. Confirm the app is healthy again:

```powershell
curl http://localhost:5000/health
```

This should return 200 OK with the JSON health response.

## HA Recovery Demo

This demo extends the single-container Chaos Mode above. Chaos Mode kills the lone `app` container and proves automatic restart. This section is about the replicated HA path: one web replica fails, Nginx keeps serving through the remaining replicas, and `web2` comes back through the normal restart policy.

The Nginx path should remain available during the replica restart, although a brief transient failure may still occur depending on timing.

### Verification steps

1. Start the stack so the app, `web1`, `web2`, and `web3` are running:

```powershell
docker compose up -d --build
```

The demo script can also start the required Compose services if they are not already running.

2. Confirm the Nginx path is healthy before the failure test:

```powershell
curl http://localhost/health
```

3. Run the HA recovery demo:

```bash
# from the repository root
./scripts/incident/simulate_web_replica_crash.sh
```

4. Watch `docker compose ps web2` and `docker inspect` to confirm the restart count increments.

5. Confirm the public path still works through Nginx during and after recovery:

```powershell
curl http://localhost/health
```

6. Optionally confirm the recovered replica responds again:

```powershell
docker compose exec web2 python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=2).read().decode())"
```

### Why this is different

- Chaos Mode proves the single `app` container restarts.
- HA Recovery proves one replica can die while Nginx keeps serving and the replica comes back automatically.
