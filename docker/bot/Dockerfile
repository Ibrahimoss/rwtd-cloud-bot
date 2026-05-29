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

# Airtest ships an x86-only adb. On ARM, replace it with the system adb
# so the bundled binary doesn't fail with "Exec format error".
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then \
      AIRTEST_ADB=$(python -c "import airtest, os; print(os.path.join(os.path.dirname(airtest.__file__), 'core/android/static/adb/linux/adb'))") && \
      rm -f "$AIRTEST_ADB" && \
      ln -s /usr/bin/adb "$AIRTEST_ADB" && \
      echo "Replaced bundled adb with system adb at $AIRTEST_ADB"; \
    fi

COPY bot/ ./bot/
COPY monitoring/ ./monitoring/

# Persistent log/screenshot dirs (also mounted as volumes in compose)
RUN mkdir -p /app/logs /app/screenshots

CMD ["python", "-m", "bot.main"]
