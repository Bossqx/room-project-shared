import os
import json
import paho.mqtt.client as mqtt

def _load_config() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), "config", "config.json")
    
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception:
        return {}

_cfg   = _load_config()
BROKER = os.getenv("MQTT_BROKER_HOST", _cfg.get("broker_ip",   "127.0.0.1"))
PORT   = int(os.getenv("MQTT_BROKER_PORT", _cfg.get("broker_port", 1883)))
TOPIC  = "staff_access/#"
QOS    = 1


def handle_on(room_no: str, date: str) -> None:
    print(f"[staff_access/on] room_no={room_no}  date={date}")
    # TODO: trigger device-on command for the room


def handle_off(room_no: str, date: str) -> None:
    print(f"[staff_access/off] room_no={room_no}  date={date}")
    # TODO: trigger device-off command for the room


ACTION_HANDLERS = {
    "on":  handle_on,
    "off": handle_off,
}


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
        print(f"[warn] non-JSON payload: {raw}")
        return

    room_no = data.get("room_no", "")
    date    = data.get("date", "")
    action  = msg.topic.split("/")[-1]

    handler = ACTION_HANDLERS.get(action)
    if handler:
        handler(room_no, date)
    else:
        print(f"[warn] unknown action: {action!r}")


def listen() -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, keepalive=60)
    print(f"[waiting] listening on {TOPIC} ...")
    client.loop_forever()


if __name__ == "__main__":
    listen()
