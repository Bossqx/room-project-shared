#!/usr/bin/env python3
"""
mqtt_sub.py

Subscribes to MQTT topics and drives Raspberry Pi GPIO to control:
  - Light relay     → device/<id>/light
  - Door lock relay → device/<id>/door

Expected JSON payload:
  {"command": "light_on"}
  {"command": "light_off"}
  {"command": "door_unlock"}              # auto-relocks after DOOR_UNLOCK_SEC
  {"command": "door_unlock_hold"}         # stays unlocked until door_lock sent
  {"command": "door_lock"}
  {"command": "status"}                   # publishes current state back

GPIO pin map (BCM numbering):
  GPIO17 → Light relay   (HIGH = ON,     LOW = OFF)
  GPIO27 → Door relay    (HIGH = UNLOCK, LOW = LOCK)

Relay logic:
  Most relay modules are ACTIVE-LOW (LOW triggers the relay).
  Set RELAY_ACTIVE_HIGH = False if your board is active-low.
"""

import json
import logging
import signal
import sys
import threading
import time

import paho.mqtt.client as mqtt

try:
    import lgpio
    ON_PI = True
except ImportError:
    ON_PI = False          # dev/test on non-Pi machine — stubs used instead

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BROKER_IP   = "192.168.1.177"
BROKER_PORT = 1883
DEVICE_ID   = "room1"
QOS         = 1

# Topics
TOPIC_LIGHT  = f"device/{DEVICE_ID}/light"
TOPIC_DOOR   = f"device/{DEVICE_ID}/door"
TOPIC_STATUS = f"device/{DEVICE_ID}/status"

CLIENT_ID = f"controller_{DEVICE_ID}"
AUTH = None   # ("username", "password") or None

# GPIO pin numbers (BCM)
PIN_LIGHT = 13
PIN_DOOR  = 27

# Relay logic: True = active-HIGH (HIGH turns relay ON)
#              False = active-LOW  (LOW  turns relay ON)
RELAY_ACTIVE_HIGH = True

# Seconds before door auto-relocks after "door_unlock" (not "door_unlock_hold")
DOOR_UNLOCK_SEC = 5

LOG_LEVEL = logging.INFO

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("mqtt_controller")

# ---------------------------------------------------------------------------
# GPIO helpers  (lgpio — BCM pin numbers, gpiochip0)
# ---------------------------------------------------------------------------
_ON  = 1 if RELAY_ACTIVE_HIGH else 0
_OFF = 0 if RELAY_ACTIVE_HIGH else 1

_h: int = -1   # lgpio chip handle; -1 = not opened


def gpio_setup():
    global _h
    if not ON_PI:
        log.warning("lgpio not available — running in stub mode")
        return
    try:
        _h = lgpio.gpiochip_open(0)
        lgpio.gpio_claim_output(_h, PIN_LIGHT, _OFF)
        lgpio.gpio_claim_output(_h, PIN_DOOR,  _OFF)   # start locked
        log.info("GPIO initialised: LIGHT=GPIO%d  DOOR=GPIO%d", PIN_LIGHT, PIN_DOOR)
    except Exception as exc:
        log.error("GPIO setup failed: %s", exc)


def gpio_write(pin: int, level: int):
    if ON_PI and _h >= 0:
        lgpio.gpio_write(_h, pin, level)
    else:
        log.debug("[STUB] GPIO%d → %s", pin, "HIGH" if level else "LOW")


def gpio_cleanup():
    global _h
    if ON_PI and _h >= 0:
        lgpio.gpio_write(_h, PIN_LIGHT, _OFF)
        lgpio.gpio_write(_h, PIN_DOOR,  _OFF)
        lgpio.gpiochip_close(_h)
        _h = -1
        log.info("GPIO cleaned up")


# ---------------------------------------------------------------------------
# Device state  (mirrors physical relay state)
# ---------------------------------------------------------------------------
class DeviceState:
    def __init__(self):
        self.light_on    = False
        self.door_locked = True
        self._relock_timer: threading.Timer | None = None

    def to_dict(self) -> dict:
        return {
            "device": DEVICE_ID,
            "online": True,
            "light":  "on"       if self.light_on    else "off",
            "door":   "unlocked" if not self.door_locked else "locked",
            "ts":     time.strftime("%Y-%m-%dT%H:%M:%S"),
        }

    def cancel_relock(self):
        if self._relock_timer and self._relock_timer.is_alive():
            self._relock_timer.cancel()
            self._relock_timer = None

    def schedule_relock(self, callback, delay: int):
        self.cancel_relock()
        self._relock_timer = threading.Timer(delay, callback)
        self._relock_timer.daemon = True
        self._relock_timer.start()
        log.info("Auto-relock scheduled in %ds", delay)


state = DeviceState()


# ---------------------------------------------------------------------------
# Hardware abstraction
# ---------------------------------------------------------------------------
def hw_light_on():
    gpio_write(PIN_LIGHT, _ON)
    state.light_on = True
    log.info("[HW] Light → ON  (GPIO%d)", PIN_LIGHT)


def hw_light_off():
    gpio_write(PIN_LIGHT, _OFF)
    state.light_on = False
    log.info("[HW] Light → OFF (GPIO%d)", PIN_LIGHT)


def hw_door_unlock(auto_relock: bool = True, client: mqtt.Client | None = None):
    gpio_write(PIN_DOOR, _ON)
    state.door_locked = False
    log.info("[HW] Door → UNLOCKED (GPIO%d)", PIN_DOOR)
    if auto_relock:
        def _relock():
            hw_door_lock()
            if client:
                publish_status(client)
        state.schedule_relock(_relock, DOOR_UNLOCK_SEC)


def hw_door_lock():
    state.cancel_relock()
    gpio_write(PIN_DOOR, _OFF)
    state.door_locked = True
    log.info("[HW] Door → LOCKED (GPIO%d)", PIN_DOOR)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------
def handle_light(client: mqtt.Client, payload: dict):
    cmd = payload.get("command", "").lower()
    if cmd == "light_on":
        hw_light_on()
    elif cmd == "light_off":
        hw_light_off()
    elif cmd == "status":
        pass   # fall through to publish_status below
    else:
        log.warning("Unknown light command: %s", cmd)
        return
    publish_status(client)


def handle_door(client: mqtt.Client, payload: dict):
    cmd = payload.get("command", "").lower()
    if cmd == "door_unlock":
        hw_door_unlock(auto_relock=True, client=client)
    elif cmd == "door_unlock_hold":
        hw_door_unlock(auto_relock=False, client=client)
    elif cmd == "door_lock":
        hw_door_lock()
    elif cmd == "status":
        pass
    else:
        log.warning("Unknown door command: %s", cmd)
        return
    publish_status(client)


def publish_status(client: mqtt.Client):
    data = json.dumps(state.to_dict())
    client.publish(TOPIC_STATUS, data, qos=QOS, retain=True)
    log.info("Status published → %s : %s", TOPIC_STATUS, data)


# ---------------------------------------------------------------------------
# MQTT callbacks — paho-mqtt v2.x (5 positional args each)
# ---------------------------------------------------------------------------
def on_connect(client, userdata, *args):
    # paho v1: args = (flags, rc)
    # paho v2 VERSION2: args = (connect_flags, reason_code, properties)
    rc = args[1] if len(args) >= 2 else args[0]
    if rc == 0:
        log.info("Connected to %s:%d", BROKER_IP, BROKER_PORT)
        for topic in (TOPIC_LIGHT, TOPIC_DOOR):
            client.subscribe(topic, qos=QOS)
            log.info("Subscribed → %s", topic)
        publish_status(client)
    else:
        log.error("Connection failed: reason_code=%s", rc)


def on_disconnect(client, userdata, *args):
    # paho v1: args = (rc,)
    # paho v2 VERSION2: args = (disconnect_flags, reason_code, properties)
    rc = args[1] if len(args) >= 2 else (args[0] if args else 0)
    if rc != 0:
        log.warning("Unexpected disconnect rc=%s — will retry", rc)
    else:
        log.info("Disconnected cleanly")


def on_message(client, userdata, msg):
    raw = msg.payload.decode("utf-8", errors="replace")
    log.debug("MSG  %s  %s", msg.topic, raw)

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("Non-JSON payload on %s: %s", msg.topic, raw)
        return

    if msg.topic == TOPIC_LIGHT:
        handle_light(client, payload)
    elif msg.topic == TOPIC_DOOR:
        handle_door(client, payload)
    else:
        log.debug("Unhandled topic: %s", msg.topic)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    gpio_setup()

    try:
        client = mqtt.Client(
            client_id=CLIENT_ID,
            protocol=mqtt.MQTTv311,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )
    except AttributeError:
        # paho-mqtt < 2.0 — CallbackAPIVersion does not exist
        client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)

    if AUTH:
        client.username_pw_set(AUTH[0], AUTH[1])

    client.on_connect    = on_connect
    client.on_disconnect = on_disconnect
    client.on_message    = on_message

    # Last-will: mark device offline if connection drops unexpectedly
    client.will_set(
        TOPIC_STATUS,
        json.dumps({"device": DEVICE_ID, "online": False}),
        qos=QOS,
        retain=True,
    )

    def _shutdown(signum, frame):
        log.info("Signal %s received — shutting down", signum)
        hw_light_off()
        hw_door_lock()
        client.disconnect()
        gpio_cleanup()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT,  _shutdown)

    log.info("Connecting to %s:%d ...", BROKER_IP, BROKER_PORT)
    try:
        client.connect(BROKER_IP, BROKER_PORT, keepalive=60)
    except Exception as e:
        log.error("Could not connect: %s", e)
        sys.exit(1)

    client.loop_forever(retry_first_connection=True)


if __name__ == "__main__":
    main()