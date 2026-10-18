# Multi-stage lightweight Python runtime (< 180MB)
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final production stage
FROM python:3.12-slim

WORKDIR /app

# Non-root user for maximum security on VPS
RUN useradd -m -u 1000 clusteruser && \
    mkdir -p /app/data && \
    chown -R clusteruser:clusteruser /app

COPY --from=builder /root/.local /home/clusteruser/.local
COPY --chown=clusteruser:clusteruser src/ /app/src/

ENV PATH=/home/clusteruser/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

USER clusteruser

EXPOSE 8000

# Healthcheck for Docker Compose
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

ENTRYPOINT ["python3", "src/cluster/main.py"]
