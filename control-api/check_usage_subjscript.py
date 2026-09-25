import os
import json
import requests
import paho.mqtt.client as mqtt
from src.models.roomUsage import RoomUsage_Controller

def _load_config() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), "config", "config.json")
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception:
        return {}

_cfg     = _load_config()
BROKER   = os.getenv("MQTT_BROKER_HOST", _cfg.get("broker_ip",   "127.0.0.1"))
PORT     = int(os.getenv("MQTT_BROKER_PORT", _cfg.get("broker_port", 1883)))
API_BASE = _cfg.get("api_route", "http://localhost:8000").rstrip("/")
TOPIC    = "mq_update_schedule"
QOS      = 1


def control_devices(room_no: str) -> None:
    try:
        res      = requests.get(f"{API_BASE}/room-binding/get_by_room/{room_no}", timeout=5)
        bindings = res.json()
        if not isinstance(bindings, list) or not bindings:
            return
        for b in bindings:
            requests.post(f"{API_BASE}/send_2_device/device/command", json={
                "host":    b["ip_address"],
                "room":    b["room_no"],
                "device":  b["devices"],
                "targets": [{"gpio_pin": b["pin"], "status": b["active_status"]}],
                "qos":     1,
            }, timeout=5)
            print(f"[device] {b['devices']} pin={b['pin']} → {b['active_status']}  room={room_no}")
    except Exception as e:
        print(f"[device] error room={room_no}: {e}")


def handle_check() -> None:
    ctrl    = RoomUsage_Controller()
    matched = ctrl.check_usage_room_flag()
    if matched:
        print(f"[check] {len(matched)} room usage(s) set to status=2")
        for u in matched:
            room_no = u.get("room_no", "")
            print(f"        id={u.get('id')}  room={room_no}  "
                  f"finish={u.get('finish_time')}  user={u.get('user_name')}")
            if room_no:
                control_devices(room_no)
    else:
        print("[check] no matching room usages in range")


def on_connect(client, _userdata, _flags, rc, _properties=None):
    if rc == 0:
        print(f"[connected] {BROKER}:{PORT}")
        client.subscribe(TOPIC, qos=QOS)
        print(f"[subscribed] {TOPIC}")
    else:
        print(f"[error] connection refused rc={rc}")


def on_message(_client, _userdata, msg):
    raw = msg.payload.decode("utf-8", errors="replace")
    print(f"[message] topic={msg.topic}  payload={raw}")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {}

    status = data.get("status", "")
    if status in ("replace", "delete", "booking_schedule", ""):
        handle_check()


def listen() -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, keepalive=60)
    print(f"[waiting] listening on {TOPIC} ...")
    client.loop_forever()


if __name__ == "__main__":
    listen()
