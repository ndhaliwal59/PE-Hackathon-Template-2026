FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates tini \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /app/pyproject.toml
RUN pip install --no-cache-dir \
    "flask>=3.1" \
    "peewee>=3.17" \
    "psycopg2-binary>=2.9" \
    "python-dotenv>=1.0" \
    "faker>=33.0"

COPY . /app

EXPOSE 5000

ENTRYPOINT ["tini", "--"]
CMD ["python", "run.py"]
