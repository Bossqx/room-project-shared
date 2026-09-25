import os
import asyncio
import urllib.parse
import json
import time
import threading
import paho.mqtt.client as mqtt


from typing import Optional, Literal
from ipaddress import IPv4Address
from pydantic import BaseModel, Field, root_validator
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from src.models.roomBinding import RoomBinding_Controller

def _load_config() -> dict:
    try:
        with open('././config/config.json') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

_config = _load_config()
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", _config.get("broker_ip", "192.168.16.112"))
try:
    _DEFAULT_BROKER_IP = IPv4Address(MQTT_BROKER_HOST)
except ValueError:
    _DEFAULT_BROKER_IP = IPv4Address("127.0.0.1")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_KEEPALIVE = 60
API_BASE = _config.get("api_route", "http://localhost:8000").rstrip("/")

router = APIRouter(
    prefix="/send_2_device",
    tags=["send_2_device"],
    responses={404: {"description": "Not found"}},
)

class CommandTrigQR_BASE(BaseModel):
    """Request model for sending commands to devices"""
    device_id: str = Field(..., description="Unique device identifier")
    command: str = Field(..., description="Command to send")
    payload: Optional[str] = Field(None, description="URL-encoded payload string")
    qos: int = Field(1, ge=0, le=2, description="MQTT Quality of Service level")

    @root_validator(pre=True)
    def encode_payload_url(cls, values):
        payload = values.get("payload")
        if payload is None:
            return values
        if isinstance(payload, dict):
            values["payload"] = urllib.parse.urlencode(payload, doseq=True)
        else:
            values["payload"] = str(payload)
        return values

    class Config:
        example = {
            "device_id": "room-led-01",
            "command": "set_brightness",
            "payload": "subject_code=SUBJ001&user_name=John+Doe&timestamp=2024-06-01T12%3A00%3A00Z&message=Test+message",
            "qos": 1,
        }



def publish_to_mqtt(topic: str, message: str, qos: int = 1, host: str = MQTT_BROKER_HOST) -> None:
    client = mqtt.Client(client_id=f"control-api-sender-{int(time.time() * 1000)}")
    try:
        client.connect(host, MQTT_BROKER_PORT, MQTT_KEEPALIVE)
        client.loop_start()
        info = client.publish(topic, message, qos=qos)
        info.wait_for_publish(timeout=5)   # blocks; raises on failure
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"MQTT publish failed: {mqtt.error_string(info.rc)}")
    finally:
        client.loop_stop()
        client.disconnect()


def trigger_room_devices(room_no: str) -> None:
    """Publish an MQTT command to every device bound to a room."""
    room_binding = RoomBinding_Controller()
    try:
        rooms = room_binding.get_by_room(room_no)
        for room in rooms:
            topic_mq = f"device/{room['room_no']}/{room['devices']}"  # like send to device      
            message = json.dumps({"gpio_pin":room["pin"], "status": room["active_status"]})
            #print(message+"\n")
            publish_to_mqtt(topic_mq, message, qos=1, host=room["ip_address"])
    finally:
        del room_binding


class LightControlRequest(BaseModel):
    device_id: str = Field(..., description="Light device identifier")
    state: Literal["on", "off"] = Field(..., description="Turn light on or off")
    brightness: Optional[int] = Field(None, ge=0, le=100, description="Brightness 0-100 (optional)")
    qos: int = Field(1, ge=0, le=2)

class DoorControlRequest(BaseModel):
    device_id: str = Field(..., description="Door/lock device identifier")
    state: Literal["open", "close"] = Field(..., description="Open or close the door")
    qos: int = Field(1, ge=0, le=2)

class AirconControlRequest(BaseModel):
    device_id: str = Field(..., description="Air conditioner device identifier")
    state: Literal["on", "off"] = Field(..., description="Turn aircon on or off")
    temperature: Optional[int] = Field(None, ge=16, le=30, description="Target temperature in °C (optional)")
    mode: Optional[Literal["cool", "fan", "dry", "heat"]] = Field(None, description="AC mode (optional)")
    qos: int = Field(1, ge=0, le=2)


# Last-known state cache: device_id -> state snapshot
_device_states: dict = {}


def _send_control(device_id: str, command: str, payload: dict, qos: int) -> dict:
    topic = f"device/{device_id}/control"
    message = {
        "command": command,
        "payload": payload,
        "sent_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    try:
        publish_to_mqtt(topic, json.dumps(message), qos=qos)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    _device_states[device_id] = {"device_id": device_id, **payload, "updated_at": message["sent_at"]}
    return {"success": True, "device_id": device_id, "topic": topic, **message}


# @router.post("/light")
# async def control_light(request: LightControlRequest):
#     """Turn a light on or off, with optional brightness level."""
#     payload: dict = {"type": "light", "state": request.state}
#     if request.brightness is not None:
#         payload["brightness"] = request.brightness
#     return _send_control(request.device_id, f"light_{request.state}", payload, request.qos)


# @router.get("/light/{device_id}/status")
# async def light_status(device_id: str):
#     """Return the last known state of a light device (on/off, brightness)."""
#     entry = _device_states.get(device_id)
#     if not entry or entry.get("type") != "light":
#         raise HTTPException(status_code=404, detail=f"No light status found for device '{device_id}'")
#     return entry




# @router.post("/door")
# async def control_door(request: DoorControlRequest):
#     """Open or close a door/lock."""
#     return _send_control(request.device_id, f"door_{request.state}", {"type": "door", "state": request.state}, request.qos)


# @router.get("/door/{device_id}/status")
# async def door_status(device_id: str):
#     """Return the last known state of a door device (open/close)."""
#     entry = _device_states.get(device_id)
#     if not entry or entry.get("type") != "door":
#         raise HTTPException(status_code=404, detail=f"No door status found for device '{device_id}'")
#     return entry


# @router.post("/aircon")
# async def control_aircon(request: AirconControlRequest):
#     """Turn an air conditioner on or off, with optional temperature and mode."""
#     payload: dict = {"type": "aircon", "state": request.state}
#     if request.temperature is not None:
#         payload["temperature"] = request.temperature
#     if request.mode is not None:
#         payload["mode"] = request.mode
#     return _send_control(request.device_id, f"aircon_{request.state}", payload, request.qos)


# @router.get("/aircon/{device_id}/status")
# async def aircon_status(device_id: str):
#     """Return the last known state of an aircon device (on/off, temperature, mode)."""
#     entry = _device_states.get(device_id)
#     if not entry or entry.get("type") != "aircon":
#         raise HTTPException(status_code=404, detail=f"No aircon status found for device '{device_id}'")
#     return entry


@router.post("/send_QR")
async def send_to_device(request: CommandTrigQR_BASE):
    """Send data to a device via MQTT broker (Mosquitto compatible)."""
    topic = f"device/{request.device_id}/command"
    payload_message = {
        "command": request.command,
        "payload": request.payload,
        "sent_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    try:
        publish_to_mqtt(topic, json.dumps(payload_message), qos=request.qos)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "success": True,
        "device_id": request.device_id,
        "topic": topic,
        "command": request.command,
        "payload": request.payload,
    }


class DoorLockRequest(BaseModel):
    host:    IPv4Address = Field(_DEFAULT_BROKER_IP, description="MQTT broker IPv4 address, e.g. 192.168.1.176")
    room:    str = Field(..., description="Room identifier, e.g. 'room1'")
    command: Literal["door_unlock", "door_unlock_hold", "door_lock"] = Field(
        ..., description="door_unlock = auto-relock after 5 s | door_unlock_hold = hold open | door_lock = lock now"
    )
    qos:     int = Field(1, ge=0, le=2)


# @router.post("/door/command")
# async def door_command(request: DoorLockRequest):
#     """
#     Control a door lock.

#     Equivalent to:
#         mosquitto_pub -h <broker> -t "device/<room>/door" -m '{"command":"<command>"}'

#     Commands:
#       door_unlock      — unlock and auto-relock after 5 s
#       door_unlock_hold — unlock and hold open
#       door_lock        — lock immediately
#     """
#     topic   = f"device/{request.room}/light"
#     message = json.dumps({"command": request.command})
#     try:
#         publish_to_mqtt(topic, message, qos=request.qos, host=str(request.host))
#     except Exception as exc:
#         raise HTTPException(status_code=500, detail=str(exc))
#     return {"success": True, "host": str(request.host), "topic": topic, "command": request.command}


class DeviceTarget(BaseModel):
    # device_no: str = Field(..., description="Device number or sub-identifier, e.g. '1'")
    gpio_pin: Optional[int] = Field(None, description="GPIO pin number for the device (if applicable)")
    status:    str = Field(..., description="Desired status, e.g. 'on' or 'off'")


class DeviceCommandRequest(BaseModel):
    host:    str               = Field(MQTT_BROKER_HOST, description="MQTT broker IP or hostname")
    room:    str               = Field(..., description="Room identifier, e.g. 'room1'")
    device:  str               = Field(..., description="Device type, e.g. 'light'")
    targets: list[DeviceTarget] = Field(..., description="One or more devices to command")
    qos:     int               = Field(1, ge=0, le=2)


class APTarget(BaseModel):
    token:    str = Field(..., description="Desired status, e.g. 'on' or 'off'")
    

class APCommandRequest(BaseModel):
    host:    str               = Field(MQTT_BROKER_HOST, description="MQTT broker IP or hostname")
    room:    str               = Field(..., description="Room identifier, e.g. 'room1'")
    targets: list[APTarget] = Field(..., description="One or more devices to command")
    qos:     int               = Field(1, ge=0, le=2)





#Specific Special Usage to service pi
@router.post("/device/command")
async def device_command(request: DeviceCommandRequest):
    """
    Publish a command to one or more devices.

    Each target produces one MQTT message:
        topic:   device/<room>/<device>
        payload: {"device_no": "<n>", "status": "<status>"}
    """
    topic   = f"device/{request.room}/{request.device}"
    results = []
    errors  = []

    for target in request.targets:
        message = json.dumps({"gpio_pin":target.gpio_pin, "status": target.status})
        try:
            publish_to_mqtt(topic, message, qos=request.qos, host=request.host)
            results.append({ "gpio_pin": target.gpio_pin, "status": target.status, "sent": True})
        except Exception as exc:
            errors.append({ "gpio_pin": target.gpio_pin, "error": str(exc)})

    return {
        "success": len(errors) == 0,
        "host":    request.host,
        "topic":   topic,
        "results": results,
        "errors":  errors,
    }
    

# ---------------------------------------------------------------------------
# ESP32 GPIO command — everything is carried in the topic path, no JSON needed.
#     topic: device/<room>/<gpio>/<status>
# The ESP32 subscribes to  device/<room>/+/+  (or device/#) and reads the gpio
# pin and status straight out of the topic segments.
# ---------------------------------------------------------------------------

class GpioTarget(BaseModel):
    gpio:   int = Field(..., description="GPIO pin number, e.g. 13")
    status: Literal["on", "off"] = Field(..., description="Desired pin state")


class EspGpioRequest(BaseModel):
    host:    str = Field(MQTT_BROKER_HOST, description="MQTT broker IP or hostname")
    room:    str = Field(..., description="Room identifier, e.g. '27.03.04'")
    targets: list[GpioTarget] = Field(..., description="One or more GPIO/status pairs")
    qos:     int = Field(1, ge=0, le=2)


def _publish_gpio(room: str, gpio: int, status: str, host: str, qos: int) -> dict:
    """Publish one device/<room>/<gpio>/<status> message; payload echoes the same."""
    topic = f"device/{room}/{gpio}/{status}"
    payload = json.dumps({
        "room": room,
        "gpio_pin": gpio,
        "status": status,
        "sent_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    publish_to_mqtt(topic, payload, qos=qos, host=host)
    return {"topic": topic, "gpio_pin": gpio, "status": status}


# --- receiver side: consume the messages the /esp32 endpoints publish ---------

# f"{room}/{gpio}" -> latest received entry
_esp32_gpio_cache: dict = {}


def _parse_esp32_topic(topic: str):
    """'device/<room>/<gpio>/<status>' -> (room, gpio|None, status|None)."""
    parts = topic.split("/")
    if len(parts) < 4 or parts[0] != "device":
        return None, None, None
    try:
        gpio = int(parts[2])
    except ValueError:
        gpio = None
    return parts[1], gpio, parts[3]


def receive_esp32_gpio(room: str = "+", timeout: float = 10.0,
                       host: str = MQTT_BROKER_HOST) -> Optional[dict]:
    """
    Subscribe to device/<room>/+/+ and return the first GPIO command received
    (i.e. a message published by _publish_gpio / the /esp32 endpoints).

    room="+" listens across every room. Blocks up to `timeout` seconds.
    Also updates _esp32_gpio_cache on success.
    """
    topic = f"device/{room}/+/+"
    result: dict = {}
    received = threading.Event()

    def on_connect(client, _userdata, _flags, rc):
        if rc == 0:
            client.subscribe(topic, qos=1)

    def on_message(_client, _userdata, msg):
        try:
            raw = msg.payload.decode("utf-8")
            t_room, t_gpio, t_status = _parse_esp32_topic(msg.topic)
            try:
                body = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                body = {}
            result.update({
                "topic":       msg.topic,
                "room":        body.get("room", t_room),
                "gpio_pin":    body.get("gpio_pin", t_gpio),
                "status":      body.get("status", t_status),
                "sent_at":     body.get("sent_at"),
                "raw":         raw,
                "received_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })
        except Exception as exc:
            result["error"] = str(exc)
        finally:
            received.set()

    client = mqtt.Client(client_id=f"control-api-esp32-recv-{int(time.time() * 1000)}")
    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect(host, MQTT_BROKER_PORT, MQTT_KEEPALIVE)
        client.loop_start()
        received.wait(timeout=timeout)
    finally:
        client.loop_stop()
        client.disconnect()

    if not result:
        return None
    if "error" not in result and result.get("gpio_pin") is not None:
        _esp32_gpio_cache[f"{result['room']}/{result['gpio_pin']}"] = result
    return result


@router.get("/esp32/{room}/{gpio}/{status}")
async def esp32_gpio_get(
    room: str,
    gpio: int,
    status: Literal["on", "off"],
    host: str = Query(MQTT_BROKER_HOST, description="MQTT broker IP or hostname"),
    qos: int = Query(1, ge=0, le=2),
):
    """
    Toggle one ESP32 GPIO. The topic path carries room / gpio / status:
        mosquitto_pub -h <host> -t "device/<room>/<gpio>/<status>" -m '{...}'
    """
    try:
        sent = _publish_gpio(room, gpio, status, host, qos)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {"success": True, "host": host, "room": room, **sent}


@router.get("/esp32_receive/{room}")
async def esp32_gpio_receive(
    room: str,
    timeout: float = Query(10.0, gt=0, le=60),
    host: str = Query(MQTT_BROKER_HOST, description="MQTT broker IP or hostname"),
):
    """
    Wait for the next device/<room>/<gpio>/<status> message and return it.
    Pass room = '+' (or 'all') to listen across every room.
    """
    if room in ("+", "all", "*"):
        room = "+"
    result = receive_esp32_gpio(room, timeout, host)
    if not result:
        raise HTTPException(
            status_code=408,
            detail=f"No ESP32 GPIO message for room '{room}' within {timeout}s",
        )
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@router.get("/esp32_latest")
async def esp32_gpio_latest(room: str, gpio: int):
    """Return the last message cached by receive_esp32_gpio for room/gpio."""
    entry = _esp32_gpio_cache.get(f"{room}/{gpio}")
    if not entry:
        raise HTTPException(status_code=404, detail=f"No cached ESP32 state for {room}/{gpio}")
    return entry


# --- event stream: push every device/<room>/<gpio>/<status> as it arrives ------
# One persistent MQTT subscriber (device/+/+/+) fans messages out to every
# connected SSE client. Mirrors mqtt_stream.py's approach.

_esp32_event_loop: Optional[asyncio.AbstractEventLoop] = None
_esp32_subscribers: set[asyncio.Queue] = set()
_esp32_listener: Optional[mqtt.Client] = None
_esp32_listener_lock = threading.Lock()


def _esp32_on_event(_client, _userdata, msg) -> None:
    """paho callback (network thread) — normalize + fan out to SSE queues."""
    try:
        raw = msg.payload.decode("utf-8")
    except UnicodeDecodeError:
        return

    t_room, t_gpio, t_status = _parse_esp32_topic(msg.topic)
    try:
        body = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        body = {}

    event = {
        "topic":       msg.topic,
        "room":        body.get("room", t_room),
        "gpio_pin":    body.get("gpio_pin", t_gpio),
        "status":      body.get("status", t_status),
        "sent_at":     body.get("sent_at"),
        "received_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if event["gpio_pin"] is not None:
        _esp32_gpio_cache[f"{event['room']}/{event['gpio_pin']}"] = event

    loop = _esp32_event_loop
    if loop is None:
        return

    def _broadcast():
        dead = []
        for q in _esp32_subscribers:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            _esp32_subscribers.discard(q)

    loop.call_soon_threadsafe(_broadcast)


def _ensure_esp32_listener(host: str = MQTT_BROKER_HOST) -> None:
    """Start the shared background subscriber once."""
    global _esp32_listener
    with _esp32_listener_lock:
        if _esp32_listener is not None:
            return
        client = mqtt.Client(client_id=f"control-api-esp32-events-{int(time.time() * 1000)}")
        client.on_connect = lambda c, *_: c.subscribe("device/+/+/+", qos=1)
        client.on_message = _esp32_on_event
        client.connect(host, MQTT_BROKER_PORT, MQTT_KEEPALIVE)
        client.loop_start()
        _esp32_listener = client


async def _esp32_event_generator(room: Optional[str]):
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _esp32_subscribers.add(q)
    try:
        yield ": connected\n\n"
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=15)
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"      # stop proxies from closing the stream
                continue
            if room and room not in ("+", "all", "*") and event.get("room") != str(room):
                continue
            yield f"data: {json.dumps(event)}\n\n"
    except asyncio.CancelledError:
        raise
    finally:
        _esp32_subscribers.discard(q)


@router.get("/esp32_events")
async def esp32_events(
    room: Optional[str] = Query(None, description="Filter to one room; omit or '+' for all"),
    host: str = Query(MQTT_BROKER_HOST, description="MQTT broker IP or hostname"),
):
    """
    Server-Sent Events stream of every ESP32 GPIO command published by
    GET /esp32/{room}/{gpio}/{status} (topic device/<room>/<gpio>/<status>).

    Each event: {"topic","room","gpio_pin","status","sent_at","received_at"}
    """
    global _esp32_event_loop
    _esp32_event_loop = asyncio.get_running_loop()
    try:
        _ensure_esp32_listener(host)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"MQTT listener failed: {exc}")

    return StreamingResponse(
        _esp32_event_generator(room),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/esp32/gpio")
async def esp32_gpio_post(request: EspGpioRequest):
    """
    Toggle one or more ESP32 GPIOs. Each target produces one MQTT message on
    topic  device/<room>/<gpio>/<status>.
    """
    results, errors = [], []
    for target in request.targets:
        try:
            results.append({**_publish_gpio(request.room, target.gpio, target.status,
                                            request.host, request.qos), "sent": True})
        except Exception as exc:
            errors.append({"gpio_pin": target.gpio, "status": target.status, "error": str(exc)})

    return {
        "success": len(errors) == 0,
        "host":    request.host,
        "room":    request.room,
        "results": results,
        "errors":  errors,
    }


@router.post("/AP_device/access_token")
async def device_command(request: APCommandRequest):
    """
    Publish a command to one or more devices.

    Each target produces one MQTT message:
        topic:   device/<room>/<device>
        payload: {"device_no": "<n>", "status": "<status>"}
    """
    topic   = f"device/{request.room}/{request.device}"
    results = []
    errors  = []

    for target in request.targets:
        message = json.dumps({"token":target.token})
        try:
            publish_to_mqtt(topic, message, qos=request.qos, host=request.host)
            results.append({ "token": target.token, "sent": True})
        except Exception as exc:
            errors.append({ "token": target.token, "error": str(exc)})

    return {
        "success": len(errors) == 0,
        "host":    request.host,
        "topic":   topic,
        "results": results,
        "errors":  errors,
    }






class StaffAccessRequest(BaseModel):
    room_no: str = Field(..., description="Room number or identifier")
    status:  str = Field(..., description="Access status, e.g. 'granted' or 'revoked'")
    subject_code: Optional[str] = Field(None, description="Optional subject code for logging")
    user_name: Optional[str] = Field(None, description="Optional user name for logging")    


@router.get("/toggle_popup/{room_no}")
async def toggle_popup(room_no: str,status: str = "on"):
    """Toggle the panel in a room."""
    topic = f"toggle_popup/popup"
    payload = json.dumps({"room_no": room_no, "command": "toggle", "status": status})
    try:
        publish_to_mqtt(topic, payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {"success": True, "room_no": room_no, "topic": topic}


@router.get("/staff_access_get/{room_no}")
async def staff_access_get(room_no: str, status: str):
    """Notify devices in a room that staff access was granted."""
    #device/27.03.04/door

    topic = f"staff_access/on/{room_no}"
    payload = json.dumps({
        "command": "staff_access",
        "room_no": room_no,
        "status": status,
        "sent_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    try:
        topic=f"""device/{room_no}/door"""
        print("Topic",topic)
        publish_to_mqtt(topic, payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {"success": True, "room_no": room_no, "topic": topic}


#*************Addmin Access room Admin,Cleaner or staff and trigger device too
@router.get("/admin_access_get/{room_no}")
async def admin_access_get(room_no: str):
    """Notify devices in a room that staff access was granted."""
    #device/27.03.04/door

    topic = f"staff_access/on/{room_no}"
    payload = json.dumps({
        "command": "staff_access",
        "room_no": room_no,
        "status": "on",
        "sent_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    try:
        print("Topic",topic)
         #Send message to server cosai
        publish_to_mqtt(topic, payload)
        # Send trigger to device
        trigger_room_devices(room_no)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {"success": True, "room_no": room_no, "topic": topic}

#***********Addess by schedule and trig device too
@router.post("/schedule_access_post/")
async def schedule_access_post(request: StaffAccessRequest):
    """Notify devices in a room that staff access was granted."""
    topic = f"staff_access/on/{request.room_no}"
    payload = json.dumps({
        "command": "staff_access",
        "room_no": request.room_no,
        "status": request.status,
        "subject_code": request.subject_code,
        "user_name": request.user_name,
        "sent_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    try:
        #Send message to server cosai
        publish_to_mqtt(topic, payload)
        #Sender trigger to device
        trigger_room_devices(request.room_no)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {"success": True, "room_no": request.room_no, "topic": topic}



@router.post("/staff_access/")
async def staff_access_post(request: StaffAccessRequest):
    """Notify devices in a room that staff access was granted."""
    topic = f"staff_access/on/{request.room_no}"
    payload = json.dumps({
        "command": "staff_access",
        "room_no": request.room_no,
        "status": request.status,
        "subject_code": request.subject_code,
        "user_name": request.user_name,
        "sent_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    try:
        publish_to_mqtt(topic, payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {"success": True, "room_no": request.room_no, "topic": topic}

class SubmitClose_Request(BaseModel):
    room_no: str = Field(..., description="Room number or identifier")
    status:  str = Field(..., description="Access status, e.g. 'granted' or 'revoked'")

@router.post("/submit_close/")
async def submit_close(request: SubmitClose_Request):
    """Notify devices in a room that staff access was granted."""
    topic = f"submit_close/{request.room_no}"
    payload = json.dumps({
        "command": "submit_close",
        "room_no": request.room_no,
        "status": request.status,
        "sent_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    try:
        publish_to_mqtt(topic, payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {"success": True, "room_no": request.room_no, "topic": topic}


class SendURLRequest(BaseModel):
    """Publish a raw message to any topic — mirrors mosquitto_pub flags."""
    host:     IPv4Address = Field(IPv4Address("192.168.1.177"), description="-h  broker host")
    port:     int           = Field(1883, ge=1, le=65535, description="-p  broker port")
    topic:    str           = Field(...,  description="-t  MQTT topic")
    message:  str           = Field(...,  description="-m  message payload")
    qos:      int           = Field(1, ge=0, le=2, description="-q  QoS 0/1/2")
    username: Optional[str] = Field(None, description="-u  username (optional)")
    password: Optional[str] = Field(None, description="-P  password (optional)")





@router.post("/send_url")
async def send_url(request: SendURLRequest):
    """
    Publish a message directly to any broker/topic.
    Equivalent to:
        mosquitto_pub -h <host> -p <port> -t <topic> -m <message> -q <qos>
    """
    client = mqtt.Client(
        client_id=f"send-url-{int(time.time() * 1000)}",
        protocol=mqtt.MQTTv311,
    )
    if request.username:
        client.username_pw_set(request.username, request.password)

    try:
        client.connect(request.host, request.port, keepalive=MQTT_KEEPALIVE)
        client.loop_start()
        info = client.publish(request.topic, request.message, qos=request.qos)
        info.wait_for_publish(timeout=5)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"Publish failed: {mqtt.error_string(info.rc)}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        client.loop_stop()
        client.disconnect()

    return {
        "success": True,
        "host":    request.host,
        "port":    request.port,
        "topic":   request.topic,
        "message": request.message,
        "qos":     request.qos,
    }


