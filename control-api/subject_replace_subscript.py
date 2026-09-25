import os
import json
import paho.mqtt.client as mqtt
from pydantic import ValidationError
from src.models.scheduleReplace import SendSchedule_Base

BROKER = os.getenv("MQTT_BROKER_HOST", "127.0.0.1")
PORT   = int(os.getenv("MQTT_BROKER_PORT", "1883"))
TOPIC  = "mq_replace_delete/"
QOS    = 1


def handle_schedule(schedule: SendSchedule_Base) -> None:
    print(f"[schedule] roomcode={schedule.roomcode}  course={schedule.coursecode}  status={schedule.status}")
    print(f"           period {schedule.timeperiodfrom}–{schedule.timeperiodto}"
          f"  ({schedule.startTime} – {schedule.finishTime})")
    for t in schedule.teacher:
        print(f"           teacher: {t.prefixname}{t.officername} {t.officersurname}  ({t.officerlogin})")


def on_connect(client, _userdata, _flags, rc, _properties=None):
    if rc == 0:
        print(f"[connected] {BROKER}:{PORT}")
        client.subscribe(TOPIC, qos=QOS)
        print(f"[subscribed] {TOPIC}")
    else:
        print(f"[error] connection refused rc={rc}")


def on_message(client, userdata, msg):
    raw = msg.payload.decode("utf-8", errors="replace")
    print(f"[message] topic={msg.topic}  payload={raw}")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(f"[warn] non-JSON payload: {raw}")
        return

    try:
        schedule = SendSchedule_Base(**data)
    except ValidationError as exc:
        print(f"[warn] payload validation failed: {exc}")
        return

    handle_schedule(schedule)


def listen() -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, keepalive=60)
    print(f"[waiting] listening on {TOPIC} ...")
    client.loop_forever()


if __name__ == "__main__":
    listen()
