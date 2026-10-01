import html
import json
import logging
import os
from typing import Any
from urllib import parse, request


logger = logging.getLogger("control-api.telegram")


def telegram_is_configured() -> bool:
    return bool(os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"))


def _safe(value: Any, fallback: str = "-") -> str:
    text = str(value).strip() if value is not None else ""
    return html.escape(text or fallback)


def build_booking_message(booking: dict[str, Any]) -> str:
    return "\n".join([
        "<b>มีคำขอจองห้องใหม่</b>",
        "",
        f"ห้อง: <b>{_safe(booking.get('room_no'))}</b>",
        f"ผู้จอง: {_safe(booking.get('user_name'))}",
        f"วันที่: {_safe(booking.get('booking_date'))}",
        f"เวลา: {_safe(booking.get('start_time'))} - {_safe(booking.get('finish_time'))}",
        f"รายวิชา: {_safe(booking.get('subject_code'))}",
        f"วัตถุประสงค์: {_safe(booking.get('objective'))}",
    ])


def send_booking_notification(booking: dict[str, Any]) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        logger.info("Telegram booking notification skipped: configuration is missing")
        return False

    body = parse.urlencode({
        "chat_id": chat_id,
        "text": build_booking_message(booking),
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }).encode("utf-8")
    telegram_request = request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with request.urlopen(telegram_request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not payload.get("ok"):
            raise RuntimeError(payload.get("description", "Telegram rejected the message"))
        return True
    except Exception:
        logger.exception("Unable to send Telegram booking notification")
        return False
