import asyncio
import json
import logging
import os
from typing import Any, Callable, Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

logger = logging.getLogger("staff_access_stream")
router = APIRouter(prefix="/staff-access-stream", tags=["staff-access-stream"])

_event_loop: Optional[asyncio.AbstractEventLoop] = None
_subscribers: set[asyncio.Queue] = set()


def _load_config() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), "config", "config.json")
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception:
        return {}


_cfg = _load_config()
BROKER = os.getenv("MQTT_BROKER_HOST", _cfg.get("broker_ip", "127.0.0.1"))
PORT = int(os.getenv("MQTT_BROKER_PORT", _cfg.get("broker_port", 1883)))
TOPIC = "staff_access/#"
QOS = 1


def set_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _event_loop
    _event_loop = loop


# --- Handlers now RETURN a dict instead of print()-ing, so the same
# --- function can feed both a device-trigger side effect AND the SSE
# --- broadcast, without duplicating the "what happened" logic twice.
def handle_on(room_no: str, date: str) -> dict[str, Any]:
    logger.info("staff_access/on room_no=%s date=%s", room_no, date)
    # TODO: trigger device-on command for the room
    return {"action": "on", "room_no": room_no, "date": date}


def handle_off(room_no: str, date: str) -> dict[str, Any]:
    logger.info("staff_access/off room_no=%s date=%s", room_no, date)
    # TODO: trigger device-off command for the room
    return {"action": "off", "room_no": room_no, "date": date}


ACTION_HANDLERS: dict[str, Callable[[str, str], dict[str, Any]]] = {
    "on": handle_on,
    "off": handle_off,
}


def on_connect(client, _userdata, _flags, rc, _properties=None):
    if rc == 0:
        logger.info("connected %s:%s", BROKER, PORT)
        client.subscribe(TOPIC, qos=QOS)
        logger.info("subscribed %s", TOPIC)
    else:
        logger.error("connection refused rc=%s", rc)


def on_message(_client, _userdata, msg) -> None:
    raw = msg.payload.decode("utf-8", errors="replace")
    logger.info("message topic=%s payload=%s", msg.topic, raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("non-JSON payload: %s", raw)
        _broadcast({"kind": "error", "topic": msg.topic, "message": f"non-JSON payload: {raw}"})
        return

    room_no = data.get("room_no", "")
    date = data.get("date", "") or data.get("sent_at", "")

    # FIX: parts[-1] on "staff_access/on/27.03.05" gives the room number,
    # not the action. Prefer the JSON payload's own "status" field —
    # it's already typed and doesn't depend on topic depth.
    action = data.get("status") or msg.topic.split("/")[1] if len(msg.topic.split("/")) > 1 else ""

    handler = ACTION_HANDLERS.get(action)
    if handler:
        result = handler(room_no, date)
        _broadcast({"kind": "staff_access", "topic": msg.topic, **result})
    else:
        logger.warning("unknown action: %r", action)
        _broadcast({"kind": "unknown", "topic": msg.topic, "action": action, "payload": data})


def _broadcast(event: dict[str, Any]) -> None:
    if _event_loop is None:
        logger.warning("event loop not set yet, dropping event on %s", event.get("topic"))
        return

    def _enqueue():
        dead = []
        for q in _subscribers:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            _subscribers.discard(q)
            logger.warning("dropped slow SSE subscriber, queue was full")

    _event_loop.call_soon_threadsafe(_enqueue)


async def _event_generator():
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers.add(q)
    logger.info("SSE client connected, total=%d", len(_subscribers))
    try:
        while True:
            event = await q.get()
            yield f"data: {json.dumps(event)}\n\n"
    except asyncio.CancelledError:
        raise
    finally:
        _subscribers.discard(q)
        logger.info("SSE client disconnected, total=%d", len(_subscribers))


@router.get("/subscribe")
async def staff_access_subscribe():
    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/health")
async def staff_access_health():
    return {"subscriber_count": len(_subscribers)}