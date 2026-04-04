# URL shortener — API and seed data

This project includes a small REST API for users and shortened URLs. JSON routes return JSON; resolving a short code returns an HTTP redirect.

## Users (`users` blueprint)

| Method | Path | What it does |
|--------|------|----------------|
| `GET` | `/users` | Lists all users (ordered by id). |
| `GET` | `/users/<user_id>` | Returns one user by id, or `404` with `{"error":"user not found"}`. |
| `GET` | `/users/<user_id>/urls` | Lists all URLs owned by that user; `404` if the user does not exist. |

## URLs (`urls` blueprint)

| Method | Path | What it does |
|--------|------|----------------|
| `GET` | `/urls` | Lists all shortened URL records. Optional query: `?user_id=<int>` filters by owner. |
| `GET` | `/urls/<url_id>` | Returns one URL record by its database id, or `404` if missing. |
| `POST` | `/urls` | Creates a new short link. JSON body must include `user_id` (integer) and `original_url` (non-empty string). Optional: `title`. The server assigns a unique 6-character `short_code` and returns `201` with the new row. Returns `400` for bad input, `404` if `user_id` does not exist. |
| `GET` | `/s/<short_code>` | Resolves a short code: `302` redirect to `original_url` if the link exists and `is_active` is true. `404` if unknown; `410` if the link is inactive. |

## Sample terminal commands (`curl`)

Assume the API is at `http://127.0.0.1:5000` (default for `uv run run.py`). Start the server, run `uv run load_seed.py` once so users and URLs exist, then paste these into a terminal.

```bash
# Optional: shorter base URL for copy-paste
export API=http://127.0.0.1:5000

# --- Users ---
curl -s "$API/users"
curl -s "$API/users/1"
curl -s "$API/users/1/urls"
curl -s "$API/users/999999"   # expect 404 JSON

# --- URLs (JSON list / detail / filter) ---
curl -s "$API/urls"
curl -s "$API/urls?user_id=1"
curl -s "$API/urls/1"
curl -s "$API/urls/999999"    # expect 404 JSON

# --- Create a short link (response includes new short_code) ---
curl -s -X POST "$API/urls" \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"original_url":"https://example.com/hello","title":"Demo"}'

# --- Resolve short codes (-i shows status + Location header) ---
# From seed data: BqJLDM is active → 302; TnKwuS is inactive → 410
curl -i "$API/s/BqJLDM"
curl -i "$API/s/TnKwuS"
curl -i "$API/s/zzzzzz"     # expect 404 JSON
```

After `POST /urls`, copy the `short_code` from the JSON body and run `curl -i "$API/s/<that_code>"` to follow the new link.

## Load seed data (`load_seed.py`)

`load_seed.py` creates database tables (if needed) and imports CSV files from `app/data/` (users, URLs, events) via `app.seed.load_csv_seed`. By default it skips CSV import if the **users** table already has at least one row (`skip_if_populated=True`), so re-running does not duplicate data.

**Prerequisites:** PostgreSQL is running, `.env` matches your database (see `.env.example`), and `uv sync` has been run.

```bash
# From the project root
uv run load_seed.py
```

On success you will see a line like: `Seed done: users=…, urls=…, events=…`.

To load again from scratch, truncate or drop the relevant tables in PostgreSQL first, then run the command again (or pass `skip_if_populated=False` to `load_csv_seed` in `load_seed.py` if you intend to support re-runs that way).

## Related files

- `app/routes/users.py`, `app/routes/urls.py` — route handlers  
- `app/seed.py` — `load_csv_seed`  
- `app/data/` — seed CSVs  
