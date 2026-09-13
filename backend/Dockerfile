FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV OMP_NUM_THREADS=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic



RUN uv sync --frozen --no-dev

EXPOSE 8000

# Run exactly one Uvicorn worker. The embedding model (FastEmbed/ONNX) is
# loaded once per process; multiple workers would duplicate that ~150 MB model
# footprint and OOM a 512 MB instance.
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1"]
