import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

logger = logging.getLogger("mqtt_stream")

router = APIRouter(prefix="/mqtt-stream-V1", tags=["mqtt-stream-V1"])

# Bridges paho's callback thread -> FastAPI's asyncio event loop
_event_loop: Optional[asyncio.AbstractEventLoop] = None
_subscribers: set[asyncio.Queue] = set()


def set_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Called once at FastAPI startup — see lifespan in main.py."""
    global _event_loop
    _event_loop = loop


def on_message(client, userdata, msg) -> None:
    """
    paho callback — runs on paho's network thread, NOT the asyncio loop.
    Must not block; must not touch asyncio.Queue directly (not thread-safe
    from a foreign thread). Use call_soon_threadsafe to hop onto the loop.
    """
    try:
        payload_raw = msg.payload.decode("utf-8")
    except UnicodeDecodeError as e:
        logger.error("undecodable payload on %s: %s", msg.topic, e)
        return

    try:
        payload = json.loads(payload_raw)
    except json.JSONDecodeError:
        payload = payload_raw  # not every topic guarantees JSON

    event = {"topic": msg.topic, "qos": msg.qos, "payload": payload}

    if _event_loop is None:
        logger.warning("event loop not set yet, dropping message on %s", msg.topic)
        return

    def _broadcast():
        dead = []
        for q in _subscribers:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                # slow client — drop it rather than block/slow down everyone else
                dead.append(q)
        for q in dead:
            _subscribers.discard(q)
            logger.warning("dropped slow SSE subscriber, queue was full")

    _event_loop.call_soon_threadsafe(_broadcast)


async def _event_generator():
    """One queue per connected SSE client — enables fan-out to multiple viewers."""
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers.add(q)
    logger.info("SSE client connected, total subscribers=%d", len(_subscribers))
    try:
        while True:
            event = await q.get()
            yield f"data: {json.dumps(event)}\n\n"
    except asyncio.CancelledError:
        # client disconnected — expected, not an error
        raise
    finally:
        _subscribers.discard(q)
        logger.info("SSE client disconnected, total subscribers=%d", len(_subscribers))


@router.get("/subscribe")
async def mqtt_subscribe_stream():
    """
    SSE endpoint. Streams every MQTT message received on the topics
    main.py subscribed to (device/+/command, staff_access/#, etc.)
    as it arrives, to any number of connected clients.
    """
    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # required behind your nginx proxy
        },
    )


@router.get("/health")
async def mqtt_stream_health():
    return {"subscriber_count": len(_subscribers)}