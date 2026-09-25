import json
import pathlib
import paho.mqtt.client as mqtt
import command_light_control

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_cfg  = json.loads((pathlib.Path(__file__).parent / "config.json").read_text())

BROKER = _cfg["broker"]
PORT   = int(_cfg["port"])
ROOM   = _cfg["room"]
DEVICE = _cfg["device"]
QOS    = int(_cfg.get("qos", 1))
TOPIC  = f"device/{ROOM}/{DEVICE}"
DEVICE_NO = "D1"  # for simplicity, we use a fixed device number in this example
STATUS="off"


# ---------------------------------------------------------------------------
# Command handler
# ---------------------------------------------------------------------------
def handle_command(data: dict) -> None:
    """
    Expected payload:
    {
        "host": "...", "room": "...", "device": "...", "qos": 1,
        "targets": [
            {"device_no": "1", "status": "on"},
            {"device_no": "2", "status": "off"}
        ]
    }
    """

    #print("PAYLOAD XXXXXX " + str(data))
    # json_data = json.loads(data)
    #print(data["device_no"])
    #command_light_control.setPin(13)   # ← point to the right relay pin
    if data["status"].lower() == "on":
        command_light_control.light_on()
        print(f"  → turn ON  device {data['device_no']}")
    elif data["status"].lower() == "off":
        command_light_control.light_off()
        print(f"  → turn OFF device {data['device_no']}")


# ---------------------------------------------------------------------------
# Publish
# ---------------------------------------------------------------------------
def light_pub(state: str, qos: int = QOS, retain: bool = False) -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(BROKER, PORT, keepalive=60)
    client.publish(TOPIC, state, qos=qos, retain=retain)
    client.disconnect()


# ---------------------------------------------------------------------------
# Subscribe / listen
# ---------------------------------------------------------------------------
def on_connect(client, *args):
    rc = args[2] if len(args) >= 3 else args[1]
    if rc == 0:
        print(f"[connected] {BROKER}:{PORT}")
        client.subscribe(TOPIC)
        print(f"[subscribed] {TOPIC}")
    else:
        print(f"[error] connection refused rc={rc}")


def on_message(*args):
    msg = args[2]
    raw = msg.payload.decode("utf-8", errors="replace")
    print(f"[message] topic={msg.topic}  payload={raw}")

    try:
        data = json.loads(raw)

        # DEVICE_NO = data['device_no']
        # STATUS = data['status']
        print(f"[parsed] data={data['device_no']} status={data['status']}")
    except json.JSONDecodeError:
        print(f"[warn] non-JSON payload: {raw}")
        return

    for t in data.get("targets", []):
        print(f"[target] device_no={t.get('device_no')}  status={t.get('status')}")

    handle_command(data)


def listen() -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, keepalive=60)
    print(f"[waiting] listening on {TOPIC} ...")
    client.loop_forever()


if __name__ == "__main__":
    listen()
