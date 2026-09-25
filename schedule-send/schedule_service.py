"""
schedule_service.py

Fetches the current room-booking schedule from the CoSAI API at startup, and
again once per day at 06:00, then schedules a task to fire at the exact
start time of each booking.

Usage:
    python schedule_service.py

Config:
    Reads config.json next to this file (see config.json in the same folder).
"""

from __future__ import annotations

import json
import logging
import signal
import sys
import time
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #

CONFIG_PATH = Path(__file__).parent / "config.json"

# api_url / access_token_url are derived from api_base (see load_config) unless
# a config.json explicitly overrides one of them.
API_URL_PATH          = "/schedule_AP/get_booking_at_current_time/"
ACCESS_TOKEN_URL_PATH = "/schedule_AP/AP_device/access_token"
USAGE_STATUS_URL_PATH = "/schedule/set_schedule_usage_status/"

DEFAULT_CONFIG = {
    "api_base": "http://localhost:8000",
    "timezone": "Asia/Bangkok",
    "request_timeout_seconds": 10,
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            user_cfg = json.load(f)
        config = {**DEFAULT_CONFIG, **user_cfg}
    else:
        config = dict(DEFAULT_CONFIG)

    api_base = config["api_base"].rstrip("/")
    config.setdefault("api_url", f"{api_base}{API_URL_PATH}")
    config.setdefault("access_token_url", f"{api_base}{ACCESS_TOKEN_URL_PATH}")
    config.setdefault("usage_status_url", f"{api_base}{USAGE_STATUS_URL_PATH}")
    return config


# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #

LOG_PATH = Path(__file__).parent / "schedule_service.log"

# A background/windowless process (e.g. launched via pythonw.exe) has no
# console — sys.stderr is None there, so a StreamHandler would silently fail
# on every record. Always log to a file next to the script, and only add a
# console handler when a console actually exists (running in a terminal).
_log_handlers: list[logging.Handler] = [logging.FileHandler(LOG_PATH, encoding="utf-8")]
if sys.stderr is not None:
    _log_handlers.append(logging.StreamHandler())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=_log_handlers,
)
logger = logging.getLogger("schedule_service")


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class BookingSlot:
    row_id: int
    roomcode: str
    coursecode: str
    coursename: str
    teacher_name: str
    start_time: str   # "HH:MM"
    finish_time: str  # "HH:MM"
    schedule_date: date
    raw: dict

    @classmethod
    def from_api(cls, item: dict) -> "BookingSlot":
        # schedule_date arrives as an ISO string, e.g. "2026-08-25T00:00:00"
        sched_date = datetime.fromisoformat(item["schedule_date"]).date()
        return cls(
            row_id=item["rowId"],
            roomcode=item["roomcode"],
            coursecode=item["coursecode"],
            coursename=item["coursename"],
            teacher_name=item["teacher_name"],
            start_time=item["startTime"],
            finish_time=item["finishTime"],
            schedule_date=sched_date,
            raw=item,
        )

    @property
    def duration_seconds(self) -> int:
        """Seconds from start_time to finish_time ("HH:MM"); 0 if unparseable."""
        def to_minutes(t: str):
            try:
                h, m = str(t).split(":")[:2]
                return int(h) * 60 + int(m)
            except (ValueError, AttributeError):
                return None

        s, f = to_minutes(self.start_time), to_minutes(self.finish_time)
        if s is None or f is None:
            return 0
        return max(0, (f - s) * 60)

    def start_datetime(self, tz: ZoneInfo) -> datetime:
        hour, minute = (int(p) for p in self.start_time.split(":"))
        return datetime.combine(
            self.schedule_date, datetime.min.time(), tzinfo=tz
        ).replace(hour=hour, minute=minute)

    def finish_datetime(self, tz: ZoneInfo) -> datetime:
        hour, minute = (int(p) for p in self.finish_time.split(":"))
        return datetime.combine(
            self.schedule_date, datetime.min.time(), tzinfo=tz
        ).replace(hour=hour, minute=minute)


# --------------------------------------------------------------------------- #
# API access
# --------------------------------------------------------------------------- #

def fetch_bookings(api_url: str, timeout: int) -> list[BookingSlot]:
    logger.info("Fetching current bookings from %s", api_url)
    resp = requests.get(api_url, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    slots: list[BookingSlot] = []
    for item in data:
        try:
            slots.append(BookingSlot.from_api(item))
        except (KeyError, ValueError) as exc:
            logger.warning("Skipping malformed booking row %s: %s", item.get("rowId"), exc)
    logger.info("Fetched %d booking(s)", len(slots))
    return slots


# --------------------------------------------------------------------------- #
# Task executed at each booking's start time
# --------------------------------------------------------------------------- #

def _send_access_token(
    slot: BookingSlot, access_token_url: str, timeout: int, topic: str | None = None
) -> None:
    """
    Builds a booking's AP-device payload and POSTs it to control-api's
    /schedule_AP/AP_device/access_token, which relays it as an MQTT message
    on the given AP topic (see schedule_AP.py device_command()). Defaults to
    the room's normal AP-TOPIC; pass topic= to target a different one (e.g.
    AP-TOPIC-CLOSE at finish time).
    """
    if topic is None:
        topic = f"AP-TOPIC/{slot.roomcode}"

    payload = {
        "rowId": str(slot.row_id),
        "topic": topic,
        "room": slot.roomcode,
        "targets": [
            {
                "rowId": str(slot.row_id),
                "token": slot.raw.get("id", ""),
                "source_type": slot.raw.get("objective", ""),
                "duration": slot.duration_seconds,
            }
        ],
        "qos": 1,
    }

    try:
        logger.debug("POST %s payload=%s timeout=%s", access_token_url, payload, timeout)
        resp = requests.post(access_token_url, json=payload, timeout=timeout)
        resp.raise_for_status()
        logger.info(
            "Sent access-token command for booking %s (room %s): %s",
            slot.row_id, slot.roomcode, resp.json(),
        )
    except requests.RequestException as exc:
        logger.error(
            "Failed to send access-token command for booking %s (room %s): %s",
            slot.row_id, slot.roomcode, exc,
        )


def _set_usage_status(slot: BookingSlot, status: int, usage_status_url: str, timeout: int) -> None:
    """
    Marks the booking's room-usage status in control-api:
        GET /schedule/set_schedule_usage_status/?schedule_id=<rowId>&status=<status>&source_type=<objective>
    """
    params = {
        "schedule_id": slot.row_id,
        "status": status,
        "source_type": slot.raw.get("objective", ""),
    }
    try:
        logger.debug("GET %s params=%s timeout=%s", usage_status_url, params, timeout)
        resp = requests.get(usage_status_url, params=params, timeout=timeout)
        resp.raise_for_status()
        logger.info(
            "Set usage status=%s for booking %s (room %s): %s",
            status, slot.row_id, slot.roomcode, resp.json(),
        )
    except requests.RequestException as exc:
        logger.error(
            "Failed to set usage status=%s for booking %s (room %s): %s",
            status, slot.row_id, slot.roomcode, exc,
        )


def run_booking_task(
    slot: BookingSlot, access_token_url: str, usage_status_url: str, timeout: int
) -> None:
    """Executed exactly at (or immediately, if already due) a booking's start time."""
    logger.info(
        "START booking=%s room=%s course=%s (%s) teacher=%s time=%s-%s",
        slot.row_id,
        slot.roomcode,
        slot.coursecode,
        slot.coursename,
        slot.teacher_name,
        slot.start_time,
        slot.finish_time,
    )
    _send_access_token(slot, access_token_url, timeout)
    _set_usage_status(slot, 1, usage_status_url, timeout)


def run_booking_finish_task(
    slot: BookingSlot, access_token_url: str, timeout: int
) -> None:
    """Executed exactly at (or immediately, if already due) a booking's finish time."""
    logger.info(
        "FINISH booking=%s room=%s course=%s (%s) teacher=%s time=%s-%s",
        slot.row_id,
        slot.roomcode,
        slot.coursecode,
        slot.coursename,
        slot.teacher_name,
        slot.start_time,
        slot.finish_time,
    )
    close_topic = f"AP-TOPIC-CLOSE/{slot.roomcode}"
    _send_access_token(slot, access_token_url, timeout, topic=close_topic)


# --------------------------------------------------------------------------- #
# Scheduling
# --------------------------------------------------------------------------- #

def schedule_bookings(
    scheduler: BackgroundScheduler,
    slots: list[BookingSlot],
    tz: ZoneInfo,
    access_token_url: str,
    usage_status_url: str,
    request_timeout_seconds: int,
) -> None:
    now = datetime.now(tz)
    for slot in slots:
        run_at = slot.start_datetime(tz)
        job_id = f"booking-{slot.row_id}-start"

        if run_at <= now:
            logger.info(
                "Booking %s (room %s) start time %s already passed (now %s) - running immediately",
                slot.row_id, slot.roomcode, run_at.isoformat(), now.isoformat(),
            )
            run_booking_task(slot, access_token_url, usage_status_url, request_timeout_seconds)
        else:
            scheduler.add_job(
                run_booking_task,
                trigger=DateTrigger(run_date=run_at, timezone=tz),
                args=[slot, access_token_url, usage_status_url, request_timeout_seconds],
                id=job_id,
                replace_existing=True,
                misfire_grace_time=60,
            )
            logger.info(
                "Scheduled booking %s (room %s) start task to run at %s",
                slot.row_id, slot.roomcode, run_at.isoformat(),
            )

        finish_at = slot.finish_datetime(tz)
        finish_job_id = f"booking-{slot.row_id}-finish"

        if finish_at <= now:
            logger.info(
                "Booking %s (room %s) finish time %s already passed (now %s) - running immediately",
                slot.row_id, slot.roomcode, finish_at.isoformat(), now.isoformat(),
            )
            run_booking_finish_task(slot, access_token_url, request_timeout_seconds)
        else:
            scheduler.add_job(
                run_booking_finish_task,
                trigger=DateTrigger(run_date=finish_at, timezone=tz),
                args=[slot, access_token_url, request_timeout_seconds],
                id=finish_job_id,
                replace_existing=True,
                misfire_grace_time=60,
            )
            logger.info(
                "Scheduled booking %s (room %s) finish task to run at %s",
                slot.row_id, slot.roomcode, finish_at.isoformat(),
            )


def refresh_bookings(scheduler: BackgroundScheduler, config: dict, tz: ZoneInfo) -> None:
    """
    Daily re-fetch (runs at 06:00, see main()): pulls the current day's
    bookings and (re)schedules their start-time tasks. Unlike the startup
    fetch, a failure here is logged and skipped rather than crashing the
    process — tomorrow's 06:00 run gets another chance.
    """
    try:
        slots = fetch_bookings(config["api_url"], config["request_timeout_seconds"])
    except requests.RequestException as exc:
        logger.error("Daily booking refresh failed: %s", exc)
        return

    schedule_bookings(
        scheduler, slots, tz,
        config["access_token_url"],
        config["usage_status_url"],
        config["request_timeout_seconds"],
    )


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #

def main() -> None:
    config = load_config()
    tz = ZoneInfo(config["timezone"])

    scheduler = BackgroundScheduler(timezone=tz)

    def shutdown(signum, _frame):
        logger.info("Received signal %s, shutting down scheduler...", signum)
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    # Initial fetch happens here, at process startup, so a restart mid-day
    # still picks up today's remaining bookings.
    try:
        slots = fetch_bookings(config["api_url"], config["request_timeout_seconds"])
    except requests.RequestException as exc:
        logger.error("Failed to fetch bookings on startup: %s", exc)
        sys.exit(1)

    scheduler.start()
    schedule_bookings(
        scheduler, slots, tz,
        config["access_token_url"],
        config["usage_status_url"],
        config["request_timeout_seconds"],
    )

    # Re-fetch once per day at 06:00 so each new day's bookings get picked up
    # without restarting the process.
    scheduler.add_job(
        refresh_bookings,
        trigger=CronTrigger(hour=6, minute=0, timezone=tz),
        args=[scheduler, config, tz],
        id="daily-booking-refresh",
        replace_existing=True,
    )

    logger.info("Scheduler running with %d job(s) queued. Press Ctrl+C to exit.", len(scheduler.get_jobs()))
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown(signal.SIGINT, None)


if __name__ == "__main__":
    main()