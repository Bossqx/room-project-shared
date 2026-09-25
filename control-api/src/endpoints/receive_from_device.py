import os
import json
import time
import threading
import urllib.parse
from typing import Optional, Any

from fastapi import APIRouter, HTTPException, Form

import paho.mqtt.client as mqtt

MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_KEEPALIVE = 60

router = APIRouter(
    prefix="/receive_from_device",
    tags=["receive_from_device"],
    responses={404: {"description": "Not found"}},
)

# In-memory cache: device_id -> latest received entry
_device_cache: dict[str, Any] = {}


def _parse_payload(raw: str) -> dict:
    """Parse a URL-encoded or JSON payload string into a dict."""
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return dict(urllib.parse.parse_qsl(raw, keep_blank_values=True))


def _subscribe_once(device_id: str, topic_suffix: str, timeout: float) -> Optional[dict]:
    """Connect to MQTT broker, subscribe to a device topic, and return the first message."""
    topic = f"device/{device_id}/{topic_suffix}"
    result: dict = {}
    received = threading.Event()

    def on_connect(client, _userdata, _flags, rc):
        if rc == 0:
            client.subscribe(topic, qos=1)

    def on_message(_client, _userdata, msg):
        try:
            raw = msg.payload.decode("utf-8")
            result["device_id"] = device_id
            result["topic"] = msg.topic
            result["raw"] = raw
            result["payload"] = _parse_payload(raw)
            result["received_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        except Exception as exc:
            result["error"] = str(exc)
        finally:
            received.set()

    client = mqtt.Client(client_id=f"control-api-recv-{int(time.time() * 1000)}")
    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_KEEPALIVE)
        client.loop_start()
        received.wait(timeout=timeout)
    finally:
        client.loop_stop()
        client.disconnect()

    return result if result else None


# ── HTTP form endpoint ────────────────────────────────────────────────────────

@router.post("/form")
async def receive_form_payload(
    device_id: str = Form(..., description="Unique device identifier"),
    command: str = Form(..., description="Command or event name sent by the device"),
    payload: Optional[str] = Form(None, description="URL-encoded or JSON payload string"),
):
    """
    Accept a form-encoded POST from a device (e.g. ESP32/ESP8266).

    Expected Content-Type: application/x-www-form-urlencoded
    """
    parsed = _parse_payload(payload) if payload else {}
    entry = {
        "device_id": device_id,
        "command": command,
        "payload": parsed,
        "received_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _device_cache[device_id] = entry
    return entry


@router.get("/latest/{device_id}")
async def get_latest(device_id: str):
    """Return the most recently received HTTP-form message from a device."""
    entry = _device_cache.get(device_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"No data cached for device '{device_id}'")
    return entry


# ── MQTT poll endpoint ────────────────────────────────────────────────────────

@router.get("/poll/{device_id}")
async def poll_device(
    device_id: str,
    topic_suffix: str = "data",
    timeout: float = 10.0,
):
    """
    Subscribe to device/{device_id}/{topic_suffix} on the MQTT broker
    and return the first message received within `timeout` seconds.
    """
    result = _subscribe_once(device_id, topic_suffix, timeout)
    if not result:
        raise HTTPException(
            status_code=408,
            detail=f"No message from device '{device_id}' within {timeout}s",
        )
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    _device_cache[device_id] = result
    return result
