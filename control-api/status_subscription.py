import os
import json
import paho.mqtt.client as mqtt
from src.models.roomUsage import RoomUsage_Controller

#this subscriptoon for wait update and cancel 

BROKER = os.getenv("MQTT_BROKER_HOST", "127.0.0.1")
PORT   = int(os.getenv("MQTT_BROKER_PORT", "1883"))
TOPIC  = "mq_update_schedule"
QOS    = 1


def handle_booking_schedule(date: str) -> None:
    print(f"[booking_schedule] date={date}")
    ctrl    = RoomUsage_Controller()
    matched = ctrl.check_usage_room_flag()
    if matched:
        print(f"[booking_schedule] {len(matched)} room usage(s) set to status=2")
        for u in matched:
            print(f"  id={u.get('id')}  room={u.get('room_no')}  "
                  f"finish={u.get('finish_time')}  user={u.get('user_name')}")
    else:
        print("[booking_schedule] no matching room usages in range")


def handle_cancel_schedule(date: str) -> None:
    print(f"[cancel_schedule] date={date}")


STATUS_HANDLERS = {
    "booking_schedule": handle_booking_schedule,
    "cancel_schedule":  handle_cancel_schedule,
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
        data   = json.loads(raw)
        status = data.get("status", "")
        date   = data.get("date", "")
    except json.JSONDecodeError:
        print(f"[warn] non-JSON payload: {raw}")
        return

    handler = STATUS_HANDLERS.get(status)
    if handler:
        handler(date)
    else:
        print(f"[warn] unknown status: {status!r}")


def listen() -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, keepalive=60)
    print(f"[waiting] listening on {TOPIC} ...")
    client.loop_forever()


if __name__ == "__main__":
    listen()
