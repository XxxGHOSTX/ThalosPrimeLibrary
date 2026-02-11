FROM python:3.11-slim AS build
WORKDIR /app
COPY requirements.txt .
RUN python -m pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
RUN useradd --create-home appuser
WORKDIR /app
COPY --from=build /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY . /app
USER appuser
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "src.api.__init__:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
HEALTHCHECK --interval=30s --timeout=5s CMD curl -f http://127.0.0.1:8000/api/status || exit 1
