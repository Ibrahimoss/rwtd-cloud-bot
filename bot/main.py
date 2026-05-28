"""
Bot entry point.

Wires together:
- Airtest connection to redroid via ADB
- State machine loaded from YAML
- Health endpoint
- Discord notifier (optional)
"""

import os
import sys
import time
import threading
from pathlib import Path

from loguru import logger

from bot.engine import StateMachineRunner
from bot.adb_io import connect_device
from monitoring.healthcheck import start_health_server
from monitoring.discord_notifier import DiscordNotifier


def main():
    # --- Config ---
    adb_host = os.getenv("ADB_HOST", "android")
    adb_port = int(os.getenv("ADB_PORT", "5555"))
    state_file = os.getenv("STATE_MACHINE", "bot/states/rwtd.yaml")
    poll_interval = float(os.getenv("POLL_INTERVAL_SECONDS", "3"))
    discord_url = os.getenv("DISCORD_WEBHOOK_URL", "")
    health_port = int(os.getenv("HEALTHCHECK_PORT", "8080"))

    # --- Logging ---
    log_dir = Path("/app/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    logger.add(log_dir / "bot_{time}.log", rotation="50 MB", retention="7 days")
    logger.info("Bot starting up")

    # --- Notifier ---
    notifier = DiscordNotifier(discord_url) if discord_url else None
    if notifier:
        notifier.send("🤖 Bot starting")

    # --- Health server in background thread ---
    health_state = {"status": "starting", "last_action": None, "uptime_start": time.time()}
    threading.Thread(
        target=start_health_server,
        args=(health_port, health_state),
        daemon=True,
    ).start()

    # --- Wait for Android to be ready ---
    device = connect_device(adb_host, adb_port, max_retries=60)
    if device is None:
        logger.error("Could not connect to Android after 5 minutes. Exiting.")
        if notifier:
            notifier.send("❌ Bot failed to connect to Android")
        sys.exit(1)

    health_state["status"] = "running"
    logger.info(f"Connected to {adb_host}:{adb_port}")

    # --- Run the state machine ---
    runner = StateMachineRunner(
        state_file=state_file,
        device=device,
        poll_interval=poll_interval,
        on_state_change=lambda s: health_state.update({"last_action": s}),
        notifier=notifier,
    )

    try:
        runner.run_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down")
    except Exception as e:
        logger.exception("Bot crashed")
        if notifier:
            notifier.send(f"💥 Bot crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
