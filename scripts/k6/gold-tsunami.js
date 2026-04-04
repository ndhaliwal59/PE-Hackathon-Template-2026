/**
 * Gold tier — 500 concurrent VUs through the load balancer (Nginx on port 80).
 *
 * Traffic mix: mostly short-link clicks (`/s/...`), light `/users/:id`, `/urls/:id`, rare `/health`.
 * Short codes from `app/data/urls.csv` (seed); `zzzzzz` → unknown / 404.
 *
 * Prerequisites: `docker compose up --build -d` (includes Redis), then seed:
 *   docker compose run --rm web1 uv run load_seed.py
 *
 * Run:
 *   k6 run scripts/k6/gold-tsunami.js
 *
 * Optional:
 *   BASE_URL=http://127.0.0.1:8080 k6 run scripts/k6/gold-tsunami.js
 *   k6 run --summary-export=scripts/k6/summary-gold.json scripts/k6/gold-tsunami.js
 */
import http from "k6/http";
import { check, sleep } from "k6";

// Valid API outcomes — not counted as http_req_failed (5xx / 0 still are)
http.setResponseCallback(
  http.expectedStatuses({ min: 200, max: 399 }, 404, 410),
);

const SHORT_CODES = [
  "BqJLDM",
  "TnKwuS",
  "i9X9Xs",
  "86JzDz",
  "Wz2f07",
  "Oh0USc",
  "7Vn3oZ",
  "vZiKww",
  "DwvT8C",
  "zzzzzz",
];

function pickShortCode() {
  return SHORT_CODES[Math.floor(Math.random() * SHORT_CODES.length)];
}

function pickUserId() {
  return 1 + Math.floor(Math.random() * 500);
}

function pickUrlId() {
  return 1 + Math.floor(Math.random() * 2000);
}

export const options = {
  vus: 500,
  duration: "2m",
  thresholds: {
    http_req_duration: ["p(95)<3000"],
    http_req_failed: ["rate<0.05"],
  },
};

const BASE = __ENV.BASE_URL || "http://127.0.0.1";

export default function () {
  const roll = Math.random();
  let res;

  if (roll < 0.85) {
    res = http.get(`${BASE}/s/${pickShortCode()}`, { redirects: 0 });
    check(res, {
      "short resolve 302/404/410": (r) =>
        r.status === 302 || r.status === 404 || r.status === 410,
    });
  } else if (roll < 0.93) {
    res = http.get(`${BASE}/users/${pickUserId()}`);
    check(res, {
      "user ok": (r) => r.status === 200 || r.status === 404,
    });
  } else if (roll < 0.98) {
    res = http.get(`${BASE}/urls/${pickUrlId()}`);
    check(res, {
      "url detail ok": (r) => r.status === 200 || r.status === 404,
    });
  } else {
    res = http.get(`${BASE}/health`);
    check(res, { "health status 200": (r) => r.status === 200 });
  }

  sleep(0.05 + Math.random() * 0.25);
}
