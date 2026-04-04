# Reliability

This document collects the reliability notes that used to live in README, plus the Docker-native restart verification flow.

## Bronze Reliability

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

CI runs only the unit suite from [tests/unit](tests/unit) using [`.github/workflows/bronze.yml`](.github/workflows/bronze.yml).
Integration tests live in [tests/integration](tests/integration) and are excluded from the Bronze workflow.

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

Silver requires at least 50% coverage on application code. Integration tests live in [tests/integration](tests/integration) and are included in the [Silver workflow](.github/workflows/silver.yml). A simulated deployment job is also configured, which will be blocked and skipped if any tests fail or code coverage drops below the limit.

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

## Error Handling

The application returns JSON error responses so API clients can handle failures predictably.

* **Route-level 404s** may return resource-specific JSON such as:
  * `{"error": "url not found"}`
  * `{"error": "user not found"}`
  * `{"error": "short code not found"}`
* **Unhandled 404 errors** return `{"error": "not found"}` with a `404` status code.
* **Unhandled 500 errors** return `{"error": "internal server error"}` with a `500` status code.

Returning JSON instead of default HTML error pages gives clients a consistent failure format, makes error handling simpler, and avoids exposing internal traceback details in normal API responses.

## Chaos Mode (Automatic Restart Verification)

The application is configured to recover automatically if its running process fails unexpectedly. This can be verified using Docker's container metadata together with the health endpoint.

### Verification steps

1. Start the stack so both the database and app container are running:

```powershell
docker compose up -d --build
```

2. Confirm the service is healthy before the failure test:

```powershell
curl http://localhost:5000/health
```

This should return 200 OK with the JSON health response.

3. Check the running containers to confirm the app container is up before the failure test:

```powershell
docker compose ps
```

In the output, note the app container name in the `NAME` column.

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
