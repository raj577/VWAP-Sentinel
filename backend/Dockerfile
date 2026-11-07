FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-backend.txt ./
RUN pip install --no-cache-dir -r requirements-backend.txt

COPY backend ./backend
COPY migrations ./migrations
COPY alembic.ini ./
COPY config.py login.py ./
COPY data ./data
COPY indicators ./indicators
COPY scanner ./scanner
COPY docs ./docs

RUN mkdir -p /app/data /app/logs

ENV FYERS_TOKEN_FILE=/app/data/access_token.txt \
    FYERS_TOKEN_META_FILE=/app/data/token_meta.json \
    FYERS_CACHE_DIR=/app/data/cache \
    FYERS_LOG_DIR=/app/logs \
    FYERS_PRESETS_FILE=/app/data/presets.json

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
