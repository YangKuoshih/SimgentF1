FROM python:3.15.2-slim@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --require-hashes -r requirements.txt

# Router embedding model (pinned revision, SHA-256 checked); own layer so code changes reuse it
COPY scripts/fetch_models.py scripts/fetch_models.py
RUN python scripts/fetch_models.py

RUN groupadd --gid 10001 simgent && useradd --uid 10001 --gid 10001 --no-create-home simgent
COPY --chown=10001:10001 . .
USER 10001:10001

EXPOSE 8080

CMD ["sh", "-c", "exec uvicorn frontend.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
