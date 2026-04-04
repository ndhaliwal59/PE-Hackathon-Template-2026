# syntax=docker/dockerfile:1
FROM python:3.13-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache --no-dev

COPY . .
RUN uv sync --frozen --no-cache --no-dev

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 5000

CMD ["sh", "-c", "exec gunicorn -w 1 -b 0.0.0.0:5000 'app:create_app()'"]
