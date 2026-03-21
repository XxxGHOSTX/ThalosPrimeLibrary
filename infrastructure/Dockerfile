# PROPRIETARY AND CONFIDENTIAL
# Copyright © 2026 Tony Ray Macier III. All Rights Reserved.

FROM python:3.12-slim

LABEL maintainer="Tony Ray Macier III"
LABEL description="Thalos Prime Infrastructure — Base Image"
LABEL version="2.0.0"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "services.control_plane.main:app", "--host", "0.0.0.0", "--port", "8000"]
