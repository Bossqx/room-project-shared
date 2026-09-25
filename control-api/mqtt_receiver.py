#!/usr/bin/env python3
"""
mqtt_receiver.py

Subscribes to the MQTT broker (Mosquitto on Raspberry Pi, 192.168.1.177:1993)
and listens for messages published by another server (e.g. 192.168.1.176).

Use this to verify that publishes from the sender server are actually
arriving at the broker and have the expected topic/payload structure,
before wiring up the STM32 / control_room device side.
"""

import paho.mqtt.client as mqtt
import json
import logging
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BROKER_IP = "192.168.1.177"
BROKER_PORT = 1883
KEEPALIVE = 60

# Subscribe to all device command topics: device/<id>/command
TOPIC_FILTER = "device/+/command"
QOS = 1

# If your broker requires auth, set these (or leave as None)
USERNAME = None
PASSWORD = None

LOG_LEVEL = logging.INFO

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("mqtt_receiver")


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        log.info(f"Connected to broker {BROKER_IP}:{BROKER_PORT}")
        client.subscribe(TOPIC_FILTER, qos=QOS)
        log.info(f"Subscribed to topic filter: {TOPIC_FILTER} (QoS {QOS})")
    else:
        log.error(f"Connection failed with result code {rc}")


def on_disconnect(client, userdata, rc, properties=None):
    if rc != 0:
        log.warning(f"Unexpected disconnect (rc={rc}), will auto-reconnect")
    else:
        log.info("Disconnected cleanly")


def on_message(client, userdata, msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    raw_payload = msg.payload.decode("utf-8", errors="replace")

    log.info(f"--- Message received [{timestamp}] ---")
    log.info(f"Topic: {msg.topic}")
    log.info(f"QoS:   {msg.qos}")
    log.info(f"Raw:   {raw_payload}")

    # Try to parse as JSON (expected format: {"command": ..., "payload": ...})
    try:
        data = json.loads(raw_payload)
        command = data.get("command")
        payload = data.get("payload")
        log.info(f"Parsed -> command: {command!r}, payload: {payload!r}")

        # Extract device_id from topic: device/<id>/command
        parts = msg.topic.split("/")
        device_id = parts[1] if len(parts) >= 2 else "unknown"
        log.info(f"Device ID: {device_id}")

        # ------------------------------------------------------------
        # TODO: dispatch based on command, e.g.:
        # if command == "show_qr":
        #     handle_show_qr(device_id, payload)
        # elif command == "relay":
        #     handle_relay(device_id, payload)
        # ------------------------------------------------------------

    except json.JSONDecodeError:
        log.warning("Payload is not valid JSON, skipping parse")

    log.info("-" * 40)


def on_log(client, userdata, level, buf):
    # Uncomment for verbose paho-mqtt internal debug logs
    # log.debug(f"paho-mqtt: {buf}")
    pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    client = mqtt.Client(
        client_id="server_receiver",
        protocol=mqtt.MQTTv311,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )

    if USERNAME:
        client.username_pw_set(USERNAME, PASSWORD)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.on_log = on_log

    log.info(f"Connecting to {BROKER_IP}:{BROKER_PORT} ...")
    try:
        client.connect(BROKER_IP, BROKER_PORT, keepalive=KEEPALIVE)
    except Exception as e:
        log.error(f"Could not connect to broker: {e}")
        return

    try:
        client.loop_forever(retry_first_connection=True)
    except KeyboardInterrupt:
        log.info("Interrupted by user, shutting down...")
        client.disconnect()


if __name__ == "__main__":
    main()