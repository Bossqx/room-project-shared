import paho.mqtt.client as mqtt
import json
import time
import urllib.parse
import urllib.request

# ── Config ──────────────────────────────────────────────
BROKER_HOST = "localhost"
BROKER_PORT = 1883

DEVICE_ID   = "192.168.1.176"
TOPIC_SUB   = f"device/{DEVICE_ID}/command"  # ตรงกับที่ API ส่ง

USERNAME    = None
PASSWORD    = None

STM32_HOST  = "192.168.1.176"
STM32_PORT  = 80
STM32_TIMEOUT = 3  # seconds
# ────────────────────────────────────────────────────────


# def forward_to_stm32(command, decoded_payload):
#     if decoded_payload.startswith("http"):
#         url = decoded_payload
#     else:
#         encoded = urllib.parse.quote_plus(decoded_payload)
#         url = f"http://{STM32_HOST}:{STM32_PORT}/{command}?payload={encoded}"

#     try:
#         req = urllib.request.Request(url)
#         with urllib.request.urlopen(req, timeout=STM32_TIMEOUT) as resp:
#             body = resp.read().decode("utf-8", errors="replace")
#             print(f"  [STM32] → {url}")
#             print(f"  [STM32] ← {resp.status} {body[:120]}")
#     except Exception as e:
#         print(f"  [STM32] ✗ Failed to reach {url}: {e}")


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[Subscriber] Connected")
        print(f"[Subscriber] Subscribing to: {TOPIC_SUB}\n")
        client.subscribe(TOPIC_SUB, qos=1)
    else:
        print(f"[Subscriber] Connection failed (rc={rc})")


def on_disconnect(client, userdata, rc):
    if rc != 0:
        print(f"[Subscriber] Unexpected disconnect (rc={rc}), reconnecting...")


def on_message(client, userdata, msg):
    raw = msg.payload.decode("utf-8")
    print(f"{'─'*50}")
    print(f"[MQTT] ← {msg.topic}  (QoS {msg.qos})")

    try:
        data = json.loads(raw)

        command  = data.get("command", "")
        payload  = data.get("payload", "")
        sent_at  = data.get("sent_at", "")

        # decode URL-encoded payload
        try:
            decoded = urllib.parse.unquote_plus(str(payload))
        except Exception:
            decoded = payload

        print(f"  command  : {command}")
        print(f"  sent_at  : {sent_at}")
        print(f"  payload  : {decoded}")

       # forward_to_stm32(command, decoded)

        # ถ้า payload เป็น URL → แสดงแยกส่วน
        if decoded.startswith("http"):
            print(f"\n  ┌─ URL breakdown")
            print(f"  │  full    : {decoded}")
            from urllib.parse import urlparse
            parsed = urlparse(decoded)
            print(f"  │  scheme  : {parsed.scheme}")
            print(f"  │  host    : {parsed.netloc}")
            print(f"  │  path    : {parsed.path}")
            if parsed.query:
                print(f"  │  query   : {parsed.query}")
            print(f"  └{'─'*30}")

    except json.JSONDecodeError:
        print(f"  raw : {raw}")


def on_subscribe(client, userdata, mid, granted_qos):
    print(f"[Subscriber] Subscription confirmed (mid={mid}, qos={granted_qos})")


def create_client():
    client = mqtt.Client(client_id=f"qr-subscriber-{int(time.time())}")
    client.on_connect    = on_connect
    client.on_disconnect = on_disconnect
    client.on_message    = on_message
    client.on_subscribe  = on_subscribe

    if USERNAME and PASSWORD:
        client.username_pw_set(USERNAME, PASSWORD)

    return client


def main():
    client = create_client()

    print(f"[Subscriber] Connecting to {BROKER_HOST}:{BROKER_PORT}")
    print(f"[Subscriber] Watching device_id: {DEVICE_ID}\n")

    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)

    try:
        print("[Subscriber] Waiting for messages  (Ctrl+C to stop)...\n")
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[Subscriber] Stopped.")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()