# Failure Modes and Graceful Degradation (Gold Reliability)

This application is designed to degrade gracefully during adverse conditions. Instead of returning raw stack traces or breaking client applications with malformed HTML responses, it provides consistent predictable JSON structures.

## 1. Invalid Request Data (400 Bad Request)
If a client submits a request missing required fields (e.g., missing `user_id` or `original_url` when creating a URL), or uses invalid field formats (e.g., non-integer IDs, empty strings), the application immediately intercepts it. 
Instead of a system crash, it returns a `400 Bad Request` with an explicit reason matching the shape:
```json
{
  "error": "user_id and original_url are required"
}
```
*Malformed JSON payloads are parsed using `request.get_json(silent=True)`. When Flask encounters broken JSON strings, it silently returns `None` instead of throwing a `werkzeug.exceptions.BadRequest` that would normally render an HTML error page. This `None` is mapped to an empty dictionary `{}`, allowing our local explicit parameter guards (e.g., catching missing `user_id`) to trip naturally and return the clean JSON `400` payload.*

## 2. Missing Resources (404 Not Found)
Routing errors (e.g. requesting endpoints that do not exist) and explicit item lookup failures (e.g., fetching a `user_id` or `short_code` that is missing from the database) are uniformly handled with a `404 Not Found` response.
* For explicit missing resources, the message may read: `{"error": "url not found"}` or `{"error": "user not found"}`.
* For completely unregistered routes, it will fall back to the global `{"error": "not found"}` handler.

## 3. Unexpected Server Errors (500 Internal Server Error)
If a catastrophic failure occurs—such as database connectivity dropping mid-request or an unhandled python exception inside the logic loop—the global application error handler ensures the crash doesn't leak into the response body.
It absorbs the stack trace serverside and emits a sanitized `500 Internal Server Error` message:
```json
{
  "error": "internal server error"
}
```
This protects underlying infrastructure details from being exposed to the outside web while maintaining an easily parseable error signal for API clients.

## 4. Unsupported Methods (405 Method Not Allowed)
Submitting `POST` requests to `GET` endpoints natively triggers Werkzeug's HTTP routing exceptions. Our unified handler catches this and cleanly replies with:
```json
{
  "error": "method not allowed"
}
```

## 5. Chaos Mode (Automatic Restart Verification)

The application is configured to recover automatically if its running process fails unexpectedly. This can be verified using Docker’s container metadata together with the health endpoint.

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

4. Capture the app container’s current restart metadata before the failure:

```powershell
docker inspect pe-hackathon-template-2026-app-1 --format="RestartCount={{.RestartCount}} StartedAt={{.State.StartedAt}} Status={{.State.Status}}"
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

8. Exit the container shell if not already done:

```sh
exit
```

8. Wait a moment and run the same inspect command again:

```powershell
docker inspect pe-hackathon-template-2026-app-1 --format="RestartCount={{.RestartCount}} StartedAt={{.State.StartedAt}} Status={{.State.Status}}"
```

This should show an incremented `RestartCount` and a new `StartedAt` timestamp, confirming that the orchestrator detected the failure and restarted the process.

9. Confirm the app is healthy again:

```powershell
curl http://localhost:5000/health
```

This should return 200 OK with the JSON health response.
