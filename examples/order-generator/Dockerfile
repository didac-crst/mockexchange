# Use slim Python base for smaller image
FROM python:3.12-slim

# Configure virtual environment and install deps
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system libs that httpx’s optional features may rely on (TLS, DNS)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency list first so Docker can cache layers if code changes later
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY scripts/ ./

# Default envs (can be overridden via docker‑compose or `docker run -e`)
ENV URL_API="http://localhost:8000" \
    API_KEY="changeme"

# Run the generator
CMD ["python", "order_generator.py"]