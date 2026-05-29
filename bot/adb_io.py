"""
ADB / Airtest connection helpers.

Airtest does the heavy lifting (touch, swipe, snapshot, template matching).
We just wrap the connection bootstrap to deal with redroid's slow boot.
"""

import time
from loguru import logger
from airtest.core.api import connect_device as airtest_connect
from airtest.core.android.android import Android


def connect_device(host: str, port: int, max_retries: int = 60, delay: float = 5.0):
    """
    Try to connect to a redroid/emulator over ADB.

    redroid takes 30-90 seconds to boot the first time, longer on slow VMs.
    Retry with a generous timeout instead of failing fast.
    """
    # Airtest URI: Android://[adbhost]/<serial>
    # Empty adbhost means "use the local adb server in this container".
    # Serial is host:port — Airtest runs `adb connect host:port` for us.
    uri = f"Android:///{host}:{port}"
    for attempt in range(1, max_retries + 1):
        try:
            dev: Android = airtest_connect(uri)
            # Confirm device responds
            dev.shell("echo ok")
            return dev
        except Exception as e:
            logger.info(f"Connect attempt {attempt}/{max_retries} failed: {e}")
            time.sleep(delay)
    return None
