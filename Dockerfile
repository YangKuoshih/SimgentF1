FROM python:3.14.8-slim@sha256:f85c5697265c178cc6887276c55fe16cf3d14ca35c3df6a5eab3b360534a55d2

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --require-hashes -r requirements.txt

RUN groupadd --gid 10001 simgent && useradd --uid 10001 --gid 10001 --no-create-home simgent
COPY --chown=10001:10001 . .
USER 10001:10001

EXPOSE 8080

CMD ["sh", "-c", "exec uvicorn frontend.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
