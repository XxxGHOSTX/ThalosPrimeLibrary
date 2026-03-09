FROM python:3.12-slim
RUN useradd --create-home appuser && \
    apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . /app
RUN python -m pip install --upgrade pip && pip install --no-cache-dir . && \
    mkdir -p /app/data && chown appuser:appuser /app/data
USER appuser
ENV PYTHONUNBUFFERED=1 \
    THALOS_LIBRARY_PATH=/app/data
EXPOSE 8000
CMD ["uvicorn", "thalos_prime.api.server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
HEALTHCHECK --interval=30s --timeout=5s CMD curl -f http://127.0.0.1:8000/health || exit 1
