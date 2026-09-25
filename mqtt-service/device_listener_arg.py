"""
device_listener_arg.py

MQTT subscriber for a single device instance.
Run: python device_listener_arg.py --device D01

Payload shape expected inside 'targets':
    {"device_no": "D01", "gpio_pin": 13, "status": "on"|"off"}
"""

import json
import pathlib
import argparse
import paho.mqtt.client as mqtt
from command_device_control import command_device

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_cfg   = json.loads((pathlib.Path(__file__).parent / "config.json").read_text())

BROKER = _cfg["broker"]
PORT   = int(_cfg["port"])
ROOM   = _cfg["room"]
QOS    = int(_cfg.get("qos", 1))

# ---------------------------------------------------------------------------
# Args
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Device Listener MQTT Service")
    parser.add_argument("--device", type=str, required=True,
                        help="Device ID to listen for (e.g. D01)")
    return parser.parse_args()

# ---------------------------------------------------------------------------
# Command handler
# ---------------------------------------------------------------------------
def handle_command(target: dict, ctrl: command_device) -> None:
    """
    Expected target shape: {"device_no": "D01", "gpio_pin": 13, "status": "on"|"off"}
    """
    #t_no   = str(target.get("device_no", ""))
    pin    = target.get("gpio_pin")
    status = target.get("status", "").lower()

    if status == "on":
        ctrl.light_on()
        print(f"[gpio] device pin={pin} → ON")
    elif status == "off":
        ctrl.light_off()
        print(f"[gpio] device pin={pin} → OFF")
    else:
        print(f"[warn] unknown status '{status}' for device {pin}")

# ---------------------------------------------------------------------------
# Listen
# ---------------------------------------------------------------------------
def listen(device: str) -> None:
    topic = f"device/{ROOM}/{device}"
    ctrl: command_device | None = None

    def on_connect(client, *args):
        reason_code = args[2]
        if reason_code == 0:
            print(f"[connected] {BROKER}:{PORT}")
            client.subscribe(topic, qos=QOS)
            print(f"[subscribed] {topic}")
        else:
            print(f"[error] connection refused rc={reason_code}")

    def on_message(*args):
        nonlocal ctrl
        msg = args[2]
        raw = msg.payload.decode("utf-8", errors="replace")
        print(f"[message] topic={msg.topic}  payload={raw}")

        try:
            data = json.loads(raw)
            print("Data",data)
        except json.JSONDecodeError:
            print(f"[warn] non-JSON payload ignored: {raw}")
            return
        
        pin = data["gpio_pin"]
        if ctrl is None:
            ctrl = command_device(pin=int(pin))
            print(f"[init] device={device}  pin=GPIO{pin}")
        handle_command(data, ctrl)


    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(BROKER, PORT, keepalive=60)
        print(f"[waiting] device={device}  topic={topic}")
        client.loop_forever()
    except KeyboardInterrupt:
        print("[exit] interrupted")
    finally:
        if ctrl is not None:
            ctrl.cleanup()

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    args = parse_args()
    listen(args.device)
