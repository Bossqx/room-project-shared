#!/usr/bin/env python3
"""
schedule_notifier.py

Background service that checks a list of scheduled start times and
publishes an MQTT notification ONCE per day for each, within a
+/- N minute window of the scheduled start time.

Designed to run as a systemd service (see schedule_notifier.service).
"""

import json
import logging
import signal
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import paho.mqtt.client as mqtt

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CONFIG_FILE = Path("/etc/schedule_notifier/config.json")
DB_FILE = Path("/var/lib/schedule_notifier/state.db")
CHECK_INTERVAL_SEC = 60       # how often to check (seconds)
WINDOW_MINUTES = 5            # +/- window around startTime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("schedule_notifier")


# ---------------------------------------------------------------------------
# State storage (SQLite) - tracks which periods have already fired today
# ---------------------------------------------------------------------------
def init_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sent_log (
            period_id TEXT NOT NULL,
            sent_date TEXT NOT NULL,
            sent_at   TEXT NOT NULL,
            PRIMARY KEY (period_id, sent_date)
        )
        """
    )
    conn.commit()
    return conn


def already_sent(conn: sqlite3.Connection, period_id: str, day: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sent_log WHERE period_id = ? AND sent_date = ?",
        (period_id, day),
    )
    return cur.fetchone() is not None


def mark_sent(conn: sqlite3.Connection, period_id: str, day: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO sent_log (period_id, sent_date, sent_at) VALUES (?, ?, ?)",
        (period_id, day, datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()


def cleanup_old_entries(conn: sqlite3.Connection, keep_days: int = 7) -> None:
    cutoff = (datetime.now() - timedelta(days=keep_days)).strftime("%Y-%m-%d")
    conn.execute("DELETE FROM sent_log WHERE sent_date < ?", (cutoff,))
    conn.commit()


# ---------------------------------------------------------------------------
# Schedule loading
# ---------------------------------------------------------------------------
def load_schedules(config: dict) -> list:
    """
    Expected format in config["schedules"]:
        [
          {"id": "p1", "startTime": "07:50", "topic": "device/room1/command",
           "payload": {"command": "show_qr", "label": "Period 1"}},
          ...
        ]
    """
    schedules = []
    for item in config.get("schedules", []):
        hh, mm = map(int, item["startTime"].split(":"))
        schedules.append(
            {
                "id": item["id"],
                "start_time": (hh, mm),
                "topic": item.get("topic", config.get("default_topic")),
                "payload": item.get("payload", {}),
            }
        )
    return schedules


# ---------------------------------------------------------------------------
# MQTT
# ---------------------------------------------------------------------------
def build_mqtt_client(config: dict) -> mqtt.Client:
    client = mqtt.Client(client_id=config.get("mqtt_client_id", "schedule_notifier"))

    user = config.get("mqtt_username")
    pwd = config.get("mqtt_password")
    if user:
        client.username_pw_set(user, pwd)

    client.connect(config["mqtt_host"], config.get("mqtt_port", 1883), keepalive=60)
    client.loop_start()
    return client


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
_running = True


def _handle_signal(signum, frame):
    global _running
    log.info("Received signal %s, shutting down...", signum)
    _running = False


def main():
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    if not CONFIG_FILE.exists():
        log.error("Config file not found: %s", CONFIG_FILE)
        sys.exit(1)

    config = json.loads(CONFIG_FILE.read_text())
    schedules = load_schedules(config)
    conn = init_db(DB_FILE)
    mqtt_client = build_mqtt_client(config)

    log.info("Loaded %d schedule entries", len(schedules))
    log.info(
        "Service started. Checking every %ds, window +/-%dmin",
        CHECK_INTERVAL_SEC, WINDOW_MINUTES,
    )

    last_cleanup_day = None

    while _running:
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")

        # Daily cleanup of old log entries (once per day)
        if last_cleanup_day != today_str:
            cleanup_old_entries(conn)
            last_cleanup_day = today_str

        for period in schedules:
            hh, mm = period["start_time"]
            start_dt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            window_start = start_dt - timedelta(minutes=WINDOW_MINUTES)
            window_end = start_dt + timedelta(minutes=WINDOW_MINUTES)

            if window_start <= now <= window_end:
                if not already_sent(conn, period["id"], today_str):
                    try:
                        payload_str = json.dumps(period["payload"])
                        mqtt_client.publish(period["topic"], payload_str, qos=1)
                        mark_sent(conn, period["id"], today_str)
                        log.info(
                            "Sent notification for period %s -> topic %s",
                            period["id"], period["topic"],
                        )
                    except Exception:
                        log.exception(
                            "Failed to publish for period %s", period["id"]
                        )

        # Sleep in 1s chunks so SIGTERM/SIGINT are responsive
        for _ in range(CHECK_INTERVAL_SEC):
            if not _running:
                break
            time.sleep(1)

    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    conn.close()
    log.info("Service stopped cleanly.")


if __name__ == "__main__":
    main()
