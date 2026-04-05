# API

This repo includes a small JSON API for users, URLs, and events. Most routes return JSON. The short-code routes return redirects.

## Health and Observability

| Method | Path | What it does | Success response |
| --- | --- | --- | --- |
| `GET` | `/health` | Checks that the app is running. | `200` with `{"status":"ok"}` |
| `GET` | `/metrics` | Returns simple process and system memory data. | `200` with `cpu_percent`, `memory_percent`, and `system_memory` |
| `GET` | `/prometheus/metrics` | Returns Prometheus text metrics and app process gauges. | `200` with Prometheus exposition text |

## Incident Simulation

These routes are only registered when `INCIDENT_SIMULATION_ENABLED=true`.

| Method | Path | What it does | Success response |
| --- | --- | --- | --- |
| `GET` | `/simulation/http-500` | Returns a simulated server error for incident drills. | `500` with `{"error":"simulated server error"}` |
| `POST` | `/simulation/cpu-burn/start` | Starts a background CPU burn for alert simulation. | `200` with `{"status":"cpu burn started"}` |
| `POST` | `/simulation/cpu-burn/stop` | Stops the background CPU burn. | `200` with `{"status":"cpu burn stop requested"}` |

## Users

| Method | Path | What it does | Request data | Success response | Common errors |
| --- | --- | --- | --- | --- | --- |
| `GET` | `/users` | Lists users. | Optional query: `page`, `per_page` | `200` JSON list, or paged JSON object | - |
| `POST` | `/users` | Creates a user. | JSON body: `username`, `email` | `201` with the new user | `422` for bad body or empty fields |
| `GET` | `/users/<user_id>` | Returns one user. | Path param: `user_id` | `200` with one user | `404` if user is missing |
| `PUT` | `/users/<user_id>` | Updates username or email. | JSON body with `username` and/or `email` | `200` with the updated user | `404`, `422` |
| `DELETE` | `/users/<user_id>` | Deletes one user. | Path param: `user_id` | `204` | `404` |
| `GET` | `/users/<user_id>/urls` | Lists URLs owned by one user. | Path param: `user_id` | `200` JSON list | `404` |
| `POST` | `/users/bulk` | Loads many users from a CSV file. | Multipart form with `file` | `200` with `{"count": <number>}` | `400` for missing or bad CSV |

## URLs

| Method | Path | What it does | Request data | Success response | Common errors |
| --- | --- | --- | --- | --- | --- |
| `GET` | `/urls` | Lists URL records. | Optional query: `user_id`, `is_active` | `200` JSON list | - |
| `POST` | `/urls` | Creates a short URL. | JSON body: `user_id`, `original_url`, optional `title` | `201` with the new URL and `short_code` | `400`, `404` |
| `GET` | `/urls/<url_id>` | Returns one URL record. | Path param: `url_id` | `200` with one URL | `404` |
| `PUT` | `/urls/<url_id>` | Updates title or active state. | JSON body with `title` and/or `is_active` | `200` with the updated URL | `404`, `422` |
| `DELETE` | `/urls/<url_id>` | Deletes one URL record. | Path param: `url_id` | `204` | `404` |
| `GET` | `/s/<short_code>` | Resolves a short code. | Path param: `short_code` | `302` redirect to the original URL | `404`, `410` |
| `GET` | `/urls/<short_code>/redirect` | Alias for short-code resolution. | Path param: `short_code` | Same as `/s/<short_code>` | Same as `/s/<short_code>` |

## Events

| Method | Path | What it does | Request data | Success response | Common errors |
| --- | --- | --- | --- | --- | --- |
| `GET` | `/events` | Lists event records. | Optional query: `url_id`, `user_id`, `event_type` | `200` JSON list | - |
| `POST` | `/events` | Creates one event record. | JSON body: `url_id`, `user_id`, `event_type`, optional `details` | `201` with the new event | `400`, `404` |

## Notes

- All JSON endpoints return JSON error bodies on failure.
- The short-code routes return redirects when a link is active.
- Seed data can be loaded with `uv run load_seed.py`.