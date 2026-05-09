FROM python:3.12-slim

WORKDIR /app

RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/screenshots /app/resumes && chown -R appuser:appuser /app

USER appuser

# Local default; Railway sets PORT at runtime. Exec-form CMD does not expand $PORT — use shell wrapper.
ENV PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD /bin/sh -c 'python -c "import os, urllib.request; p=os.environ.get(\"PORT\", \"8000\"); urllib.request.urlopen(\"http://127.0.0.1:\" + p + \"/health\")"' || exit 1

CMD ["/bin/sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port \"${PORT:-8000}\" --workers 2"]
