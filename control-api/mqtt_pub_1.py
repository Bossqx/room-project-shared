"""
mqtt_pub_1.py  –  publish one message, same flags as mosquitto_pub

Usage:
    python mqtt_pub_1.py -h 192.168.1.177 -p 1883 -t "test/ping" -m "hello chatchai"

Flags:
    -h  broker host        (default: 192.168.1.177)
    -p  broker port        (default: 1883)
    -t  topic              (default: test/ping)
    -m  message payload    (default: hello)
    -q  QoS 0/1/2          (default: 1)
    -u  username           (optional)
    -P  password           (optional)
"""

import argparse
import time

import paho.mqtt.client as mqtt


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Publish one MQTT message (mosquitto_pub-compatible flags)",
        add_help=False,
    )
    p.add_argument("--help", action="help", help="Show this help message and exit")
    p.add_argument("-h", dest="host",     default="192.168.1.177", help="Broker host")
    p.add_argument("-p", dest="port",     default=1883, type=int,  help="Broker port")
    p.add_argument("-t", dest="topic",    default="test/ping",     help="Topic")
    p.add_argument("-m", dest="message",  default="hello aaaaa",         help="Message payload")
    p.add_argument("-q", dest="qos",      default=1, type=int,     help="QoS (0/1/2)")
    p.add_argument("-u", dest="username", default=None,            help="Username")
    p.add_argument("-P", dest="password", default=None,            help="Password")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    client = mqtt.Client(
        client_id=f"mqtt-pub-{int(time.time())}",
        protocol=mqtt.MQTTv311,
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    )

    if args.username:
        client.username_pw_set(args.username, args.password)

    print(f"Connecting to {args.host}:{args.port} ...")
    client.connect(args.host, args.port, keepalive=60)
    client.loop_start()

    info = client.publish(args.topic, args.message, qos=args.qos)
    info.wait_for_publish(timeout=5)

    print(f"Published  topic={args.topic}  payload={args.message!r}  qos={args.qos}")

    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    main()
