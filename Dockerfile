FROM python:3.11-slim AS build
WORKDIR /app
COPY pyproject.toml setup.py ./
COPY thalos_prime thalos_prime
RUN python -m pip install --upgrade pip && pip install --no-cache-dir .

FROM python:3.11-slim
RUN useradd --create-home appuser && \
    apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=build /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=build /usr/local/bin/uvicorn /usr/local/bin/uvicorn
COPY . /app
USER appuser
ENV PYTHONUNBUFFERED=1 \
    THALOS_LIBRARY_PATH=/app/data
EXPOSE 8000
CMD ["uvicorn", "thalos_prime.api.server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
HEALTHCHECK --interval=30s --timeout=5s CMD curl -f http://127.0.0.1:8000/health || exit 1
