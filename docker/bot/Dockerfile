FROM python:3.11-slim

# System deps: adb tools for direct ADB if needed, plus opencv runtime deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    adb \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY docker/bot/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot/ ./bot/
COPY monitoring/ ./monitoring/

# Persistent log/screenshot dirs (also mounted as volumes in compose)
RUN mkdir -p /app/logs /app/screenshots

CMD ["python", "-m", "bot.main"]
