import paho.mqtt.client as mqtt
import json
import time

BROKER_IP = "192.168.1.177"
BROKER_PORT = 1883
# DEVICE_ID = "control_room_01"   # adjust to your device's ID
# TOPIC = f"device/{DEVICE_ID}/command"

# Connect
client = mqtt.Client(client_id="server_publisher", protocol=mqtt.MQTTv311)
client.connect(BROKER_IP, BROKER_PORT, keepalive=60)

# Build payload
payload = {
    "command": "show_qr",
    "payload": "https://cosai.nrru.ac.th/gePass/XXXX"
}

# Publish
#result = client.publish(TOPIC, json.dumps(payload), qos=1)
#result.wait_for_publish()

# print(f"Published to {TOPIC}: {payload}")
# print(f"Result: {result.rc} (0 = success)")

client.disconnect()