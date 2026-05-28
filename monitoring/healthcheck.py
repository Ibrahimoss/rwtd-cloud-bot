"""
Tiny Flask healthcheck endpoint.

Exposes:
  GET /        - human-readable status page
  GET /health  - JSON for monitoring systems
"""

import time
from flask import Flask, jsonify


def start_health_server(port: int, state: dict):
    app = Flask(__name__)

    @app.route("/health")
    def health():
        uptime = time.time() - state.get("uptime_start", time.time())
        return jsonify({
            "status": state.get("status", "unknown"),
            "last_action": state.get("last_action"),
            "uptime_seconds": int(uptime),
        })

    @app.route("/")
    def index():
        uptime = int(time.time() - state.get("uptime_start", time.time()))
        return (
            f"<h1>rwtd-cloud-bot</h1>"
            f"<p>Status: {state.get('status', 'unknown')}</p>"
            f"<p>Last action: {state.get('last_action', 'n/a')}</p>"
            f"<p>Uptime: {uptime}s</p>"
        )

    # silence default Flask request logs
    import logging
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
