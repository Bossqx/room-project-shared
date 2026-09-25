import os
import json
import paho.mqtt.client as mqtt

BROKER = os.getenv("MQTT_BROKER_HOST", "192.168.1.176")
PORT   = int(os.getenv("MQTT_BROKER_PORT", "1883"))
TOPIC  = "update_schedule"
QOS    = 1


def handle_update(status: str, update_time: str) -> None:
    print(f"[update] status={status}  update_time={update_time}")
    # TODO: trigger schedule reload or notify connected clients


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

    status      = data.get("status", "")
    update_time = data.get("update", "")

    if not status:
        print("[warn] missing 'status' field")
        return

    handle_update(status, update_time)


def listen() -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, keepalive=60)
    print(f"[waiting] listening on {TOPIC} ...")
    client.loop_forever()


if __name__ == "__main__":
    listen()
