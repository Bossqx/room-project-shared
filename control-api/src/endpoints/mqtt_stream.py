import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

logger = logging.getLogger("mqtt_stream")

router = APIRouter(prefix="/mqtt-stream", tags=["mqtt-stream"])

_event_loop: Optional[asyncio.AbstractEventLoop] = None
_subscribers: set[asyncio.Queue] = set()

# room_no -> {"count": int, "topic": str, "received_at": str}
_latest_person_counts: dict[str, dict[str, Any]] = {}

# Mirrors the Vue side's status sets, kept as constants so a future
# change to accepted values only happens in one place.
SCHEDULE_REFRESH_STATUSES = {"replace", "delete"}
MQ_SCHEDULE_REFRESH_STATUSES = {"booking_schedule", "cancel_schedule"}
STAFF_ACCESS_ON = "on"
STAFF_ACCESS_OFF = "off"


def set_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _event_loop
    _event_loop = loop


@dataclass
class StreamEvent:
    """Normalized event shape pushed to every SSE subscriber."""
    kind: str                      # "update_schedule" | "mq_update_schedule" | "staff_access" | "schedule_item" | "error" | "unknown"
    topic: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_sse(self) -> str:
        return f"data: {json.dumps({'kind': self.kind, 'topic': self.topic, **self.data})}\n\n"


def handle_message(topic: str, raw: str) -> StreamEvent:
    """
    Pure function: topic + raw payload string -> normalized StreamEvent.
    No I/O, no MQTT/asyncio coupling — this is what you unit test.
    Mirrors the Vue handleMessage() branching exactly.
    """
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("invalid JSON on topic=%s payload=%s", topic, raw)
        return StreamEvent(kind="error", topic=topic, data={"message": f"Invalid JSON on {topic}: {raw}"})

    if topic == "update_schedule":
        status = parsed.get("status")
        update_time = parsed.get("update")
        should_refresh = status in SCHEDULE_REFRESH_STATUSES
        logger.info("update_schedule status=%s update=%s refresh=%s", status, update_time, should_refresh)
        return StreamEvent(
            kind="update_schedule",
            topic=topic,
            data={"status": status, "update": update_time, "should_refresh": should_refresh},
        )

    if topic == "mq_update_schedule":
        status = parsed.get("status")
        date = parsed.get("date")
        should_refresh = status in MQ_SCHEDULE_REFRESH_STATUSES
        logger.info("mq_update_schedule status=%s date=%s refresh=%s", status, date, should_refresh)
        return StreamEvent(
            kind="mq_update_schedule",
            topic=topic,
            data={"status": status, "update": date, "should_refresh": should_refresh},
        )

    if topic.startswith("staff_access/"):
        room_no = parsed.get("room_no")
        status = parsed.get("status")
        subject_code = parsed.get("subject_code")
        user_name = parsed.get("user_name")
        logger.info("staff_access room=%s status=%s subject=%s user=%s", room_no, status, subject_code, user_name)
        return StreamEvent(
            kind="staff_access",
            topic=topic,
            data={"room_no": room_no, "status": status, "subject_code": subject_code, "user_name": user_name},
        )

    if topic == "toggle_popup/popup":
        room_no = parsed.get("room_no")
        status = parsed.get("status")
        logger.info("toggle_popup room=%s status=%s", room_no, status)
        return StreamEvent(
            kind="toggle_popup",
            topic=topic,
            data={"room_no": room_no, "status": status},
        )

    if topic == "camera/person-count" or (topic.startswith("camera/") and topic.endswith("/person-count")):
        room_no = parsed.get("room_no")
        count = parsed.get("count")
        logger.info("person_count room=%s count=%s", room_no, count)
        return StreamEvent(
            kind="person_count",
            topic=topic,
            data={"room_no": room_no, "count": count},
        )

    # Generic schedule item — mirrors: Array.isArray(parsed) ? parsed[0] : parsed
    item = parsed[0] if isinstance(parsed, list) and parsed else parsed
    if isinstance(item, dict) and item.get("id") and item.get("coursecode"):
        return StreamEvent(kind="schedule_item", topic=topic, data={"item": item})

    return StreamEvent(kind="unknown", topic=topic, data={"payload": parsed})


def on_message(client, userdata, msg) -> None:
    """paho callback — runs on paho's network thread, not the asyncio loop."""
    try:
        raw = msg.payload.decode("utf-8").strip()
    except UnicodeDecodeError as e:
        logger.error("undecodable payload on %s: %s", msg.topic, e)
        return

    event = handle_message(msg.topic, raw)

    if event.kind == "person_count" and event.data.get("room_no"):
        _latest_person_counts[event.data["room_no"]] = {
            "count": event.data["count"],
            "topic": event.topic,
            "received_at": datetime.utcnow().isoformat() + "Z",
        }

    if _event_loop is None:
        logger.warning("event loop not set yet, dropping message on %s", msg.topic)
        return

    def _broadcast():
        dead = []
        for q in _subscribers:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            _subscribers.discard(q)
            logger.warning("dropped slow SSE subscriber, queue was full")

    _event_loop.call_soon_threadsafe(_broadcast)


async def _event_generator():
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers.add(q)
    logger.info("SSE client connected, total=%d", len(_subscribers))
    try:
        while True:
            event: StreamEvent = await q.get()
            yield event.to_sse()
    except asyncio.CancelledError:
        raise
    finally:
        _subscribers.discard(q)
        logger.info("SSE client disconnected, total=%d", len(_subscribers))


@router.get("/subscribe/")
async def mqtt_subscribe_stream():
    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )



@router.get("/subscribe_payload/")
async def mqtt_subscribe_payload_stream():
    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/subscribe_payload_cancel/")
async def subscribe_payload_cancel_stream():
    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )



@router.get("/subscribe_payload_update/")
async def subscribe_payload_update_stream():
    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )







@router.get("/person_count/{room_no}")
async def get_person_count(room_no: str):
    """Latest person count received for a room, from camera/{room_no}/person-count."""
    entry = _latest_person_counts.get(room_no)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"No person-count data received yet for room '{room_no}'")
    return {"room_no": room_no, **entry}


@router.get("/person_count/")
async def get_all_person_counts():
    """Latest known person count for every room that has published one."""
    return _latest_person_counts


@router.get("/health/")
async def mqtt_stream_health():
    return {"subscriber_count": len(_subscribers)}