"""
MQTT QR Receiver  –  auto-connect, QR-only display
====================================================
Subscribes to  device/{DEVICE_ID}/command  and renders the `payload` field
as a QR code whenever the message has  command == "qr".

Dependencies:
    pip install paho-mqtt qrcode[pil] pillow
"""

from __future__ import annotations

import json
import queue
import time
import tkinter as tk
from tkinter import ttk

import paho.mqtt.client as mqtt
import qrcode
from PIL import Image, ImageTk

# ── Config ──────────────────────────────────────────────────────────────────
BROKER_HOST = "localhost"
BROKER_PORT  = 1883
DEVICE_ID    = "192.168.1.176"
TOPIC_SUB    = f"device/{DEVICE_ID}/command"
QR_COMMAND   = "qr"
QR_MAX_SIZE  = 480
# ────────────────────────────────────────────────────────────────────────────


class MqttQrReceiver:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("QR Display")
        self.root.geometry("520x580")
        self.root.resizable(True, True)

        self._events: queue.Queue[tuple[str, str]] = queue.Queue()
        self._qr_photo: ImageTk.PhotoImage | None = None
        self.client: mqtt.Client | None = None

        self._build_ui()
        self.root.after(100, self._poll_events)
        self.root.after(200, self._auto_connect)

    # ── UI ──────────────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        bar = ttk.Frame(self.root)
        bar.pack(fill="x", padx=10, pady=(8, 0))

        ttk.Label(bar, text=f"Topic: {TOPIC_SUB}", foreground="gray").pack(side="left")
        self.status_var = tk.StringVar(value="Connecting…")
        self.status_lbl = ttk.Label(bar, textvariable=self.status_var, foreground="orange")
        self.status_lbl.pack(side="right")

        self.qr_label = ttk.Label(self.root, text="Waiting for QR data…", anchor="center")
        self.qr_label.pack(expand=True, fill="both", padx=10, pady=10)

        self.url_var = tk.StringVar(value="")
        ttk.Label(
            self.root,
            textvariable=self.url_var,
            foreground="gray",
            wraplength=500,
        ).pack(padx=10, pady=(0, 10))

    # ── MQTT connection ──────────────────────────────────────────────────────
    def _auto_connect(self) -> None:
        client = mqtt.Client(client_id=f"qr-receiver-{int(time.time())}")
        client.on_connect    = lambda *a: self._on_connect(a[0], a[3])
        client.on_disconnect = lambda *_: self._on_disconnect()
        client.on_message    = lambda *a: self._on_message(a[2])
        try:
            client.connect(BROKER_HOST, BROKER_PORT, keepalive=30)
        except Exception as exc:
            self._events.put(("status_err", f"Failed to connect: {exc}"))
            return
        client.loop_start()
        self.client = client

    # ── MQTT callbacks (network thread → queue only) ─────────────────────────
    def _on_connect(self, client: mqtt.Client, rc: int) -> None:
        if rc == 0:
            client.subscribe(TOPIC_SUB, qos=1)
            self._events.put(("status", "Connected"))
        else:
            self._events.put(("status_err", f"Connect failed (rc={rc})"))

    def _on_disconnect(self) -> None:
        self._events.put(("status_err", "Disconnected"))

    def _on_message(self, msg: mqtt.MQTTMessage) -> None:
        try:
            raw  = msg.payload.decode("utf-8", errors="replace")
            data = json.loads(raw)
            if isinstance(data, dict) and data.get("command") == QR_COMMAND:
                url = str(data.get("payload", "")).strip()
                if url:
                    self._events.put(("qr", url))
        except Exception:
            pass

    # ── Main-thread event drain ──────────────────────────────────────────────
    def _poll_events(self) -> None:
        try:
            while True:
                kind, value = self._events.get_nowait()
                if kind == "status":
                    self._set_status(value, "green")
                elif kind == "status_err":
                    self._set_status(value, "red")
                elif kind == "qr":
                    self._render_qr(value)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._poll_events)

    def _set_status(self, text: str, color: str) -> None:
        self.status_var.set(text)
        self.status_lbl.configure(foreground=color)

    # ── QR rendering ────────────────────────────────────────────────────────
    def _render_qr(self, url: str) -> None:
        try:
            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
            img.thumbnail((QR_MAX_SIZE, QR_MAX_SIZE), Image.Resampling.NEAREST)

            photo = ImageTk.PhotoImage(img)
            self.qr_label.configure(image=photo, text="")
            self._qr_photo = photo  # prevent GC
            self.url_var.set(url)
        except Exception as exc:
            self.qr_label.configure(image="", text=f"QR error: {exc}")


def main() -> None:
    root = tk.Tk()
    MqttQrReceiver(root)
    root.protocol("WM_DELETE_WINDOW", lambda: None)  # prevent close
    root.mainloop()


if __name__ == "__main__":
    main()
