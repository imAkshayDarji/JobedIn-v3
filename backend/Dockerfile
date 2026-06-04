FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libffi-dev \
        shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/screenshots /app/resumes && chown -R appuser:appuser /app

USER appuser

# Local default; Railway sets PORT at runtime. Exec-form CMD does not expand $PORT — use shell wrapper.
ENV PORT=8000
# Single worker by default keeps memory predictable on small Railway instances; override with UVICORN_WORKERS.
ENV UVICORN_WORKERS=1

# Match listening port: set Railway variable PORT (e.g. 8000) to align edge routing with uvicorn.
EXPOSE 8000

CMD ["/bin/sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port \"${PORT:-8000}\" --workers \"${UVICORN_WORKERS:-1}\""]
