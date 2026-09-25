"""
MQTT QR Receiver
=================
Companion to the FastAPI `send_2_device` router's `/send_QR` endpoint.

That endpoint publishes to:

    topic:   device/{device_id}/command
    payload: {
                "command": "qr",
                "payload": "<url or urlencoded string>",
                "sent_at": "2024-06-01T12:00:00Z"
             }

This GUI subscribes to that topic for a given device_id and auto-detects
the message format:

  - JSON object with a "payload" field (the send_QR format above): the
    "command" field is checked against the configured filter (if set),
    and the "payload" field is rendered as the QR code.
  - Anything else (a plain string, bare URL, JSON array/number, etc.):
    the raw message body itself is rendered as the QR code, with no
    command filtering applied.

This lets the same receiver work with the FastAPI backend's wrapped
messages as well as a simple `mosquitto_pub -m "<url>"` test message.

Dependencies:
    pip install paho-mqtt qrcode[pil] pillow

Run:
    python mqtt_qr_receiver.py
"""

from __future__ import annotations

import json
import queue
import time
import tkinter as tk
from tkinter import messagebox, ttk

import paho.mqtt.client as mqtt
import qrcode
from PIL import Image, ImageTk

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 1883
DEFAULT_DEVICE_ID = "192.168.1.176"
DEFAULT_COMMAND = "qr"
DEFAULT_KEEPALIVE = 30
QR_MAX_SIZE_PX = 320


def topic_for_device(device_id: str) -> str:
    """Match the backend: device/{device_id}/command"""
    return f"device/{device_id}/command"


class MqttQrReceiver:
    """Subscribes to device/{device_id}/command and shows QR codes for
    messages whose "command" field matches the configured QR command.

    All MQTT callbacks run on paho-mqtt's network thread and only push
    onto a queue; Tkinter widgets are only touched from the main thread
    via root.after() polling.
    """

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("MQTT QR Receiver")
        self.root.geometry("440x680")
        self.root.minsize(400, 600)

        self.client: mqtt.Client | None = None
        self.connected = False
        self._events: queue.Queue[tuple[str, str]] = queue.Queue()
        self._current_qr_image: ImageTk.PhotoImage | None = None

        self._build_ui()
        self.root.after(100, self._poll_events)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        conn_frame = ttk.LabelFrame(self.root, text="Broker connection")
        conn_frame.pack(fill="x", padx=10, pady=8)
        conn_frame.columnconfigure(1, weight=1)
        conn_frame.columnconfigure(3, weight=1)

        ttk.Label(conn_frame, text="Host:").grid(row=0, column=0, sticky="w", padx=4, pady=3)
        self.host_var = tk.StringVar(value=DEFAULT_HOST)
        ttk.Entry(conn_frame, textvariable=self.host_var).grid(row=0, column=1, sticky="we", padx=4, pady=3)

        ttk.Label(conn_frame, text="Port:").grid(row=0, column=2, sticky="w", padx=4, pady=3)
        self.port_var = tk.StringVar(value=str(DEFAULT_PORT))
        ttk.Entry(conn_frame, textvariable=self.port_var, width=8).grid(row=0, column=3, sticky="we", padx=4, pady=3)

        ttk.Label(conn_frame, text="Device ID:").grid(row=1, column=0, sticky="w", padx=4, pady=3)
        self.device_var = tk.StringVar(value=DEFAULT_DEVICE_ID)
        ttk.Entry(conn_frame, textvariable=self.device_var).grid(
            row=1, column=1, columnspan=3, sticky="we", padx=4, pady=3
        )

        ttk.Label(conn_frame, text="Command filter\n(JSON msgs only):").grid(row=2, column=0, sticky="w", padx=4, pady=3)
        self.command_var = tk.StringVar(value=DEFAULT_COMMAND)
        ttk.Entry(conn_frame, textvariable=self.command_var, width=14).grid(
            row=2, column=1, sticky="w", padx=4, pady=3
        )

        ttk.Label(conn_frame, text="Username:").grid(row=3, column=0, sticky="w", padx=4, pady=3)
        self.user_var = tk.StringVar(value="")
        ttk.Entry(conn_frame, textvariable=self.user_var).grid(row=3, column=1, sticky="we", padx=4, pady=3)

        ttk.Label(conn_frame, text="Password:").grid(row=3, column=2, sticky="w", padx=4, pady=3)
        self.pass_var = tk.StringVar(value="")
        ttk.Entry(conn_frame, textvariable=self.pass_var, show="*").grid(
            row=3, column=3, sticky="we", padx=4, pady=3
        )

        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self._toggle_connection)
        self.connect_btn.grid(row=4, column=0, columnspan=2, sticky="we", padx=4, pady=(6, 4))

        self.status_var = tk.StringVar(value="Disconnected")
        self.status_lbl = ttk.Label(conn_frame, textvariable=self.status_var, foreground="red")
        self.status_lbl.grid(row=4, column=2, columnspan=2, sticky="e", padx=4, pady=(6, 4))

        self.topic_var = tk.StringVar(value=f"Topic: {topic_for_device(DEFAULT_DEVICE_ID)}")
        ttk.Label(conn_frame, textvariable=self.topic_var, foreground="gray").grid(
            row=5, column=0, columnspan=4, sticky="w", padx=4, pady=(0, 4)
        )
        self.device_var.trace_add("write", lambda *_: self._update_topic_preview())

        # QR code display
        qr_frame = ttk.LabelFrame(self.root, text="QR code")
        qr_frame.pack(fill="both", expand=True, padx=10, pady=8)

        self.qr_label = ttk.Label(qr_frame, text="Waiting for QR command...", anchor="center")
        self.qr_label.pack(expand=True, pady=10)

        # Last message display
        msg_frame = ttk.LabelFrame(self.root, text="Last message")
        msg_frame.pack(fill="x", padx=10, pady=8)

        grid = ttk.Frame(msg_frame)
        grid.pack(fill="x", padx=4, pady=4)
        grid.columnconfigure(1, weight=1)

        ttk.Label(grid, text="Command:").grid(row=0, column=0, sticky="w")
        self.last_command_var = tk.StringVar(value="-")
        ttk.Label(grid, textvariable=self.last_command_var).grid(row=0, column=1, sticky="w")

        ttk.Label(grid, text="Sent at:").grid(row=1, column=0, sticky="w")
        self.last_sent_var = tk.StringVar(value="-")
        ttk.Label(grid, textvariable=self.last_sent_var).grid(row=1, column=1, sticky="w")

        ttk.Label(grid, text="Received:").grid(row=2, column=0, sticky="w")
        self.received_var = tk.StringVar(value="-")
        ttk.Label(grid, textvariable=self.received_var).grid(row=2, column=1, sticky="w")

        ttk.Label(msg_frame, text="Payload:").pack(anchor="w", padx=4)
        self.payload_text = tk.Text(msg_frame, height=4, wrap="word")
        self.payload_text.pack(fill="x", padx=4, pady=(0, 4))
        self.payload_text.configure(state="disabled")

        # Raw message log
        log_frame = ttk.LabelFrame(self.root, text="Message log")
        log_frame.pack(fill="both", expand=False, padx=10, pady=(0, 8))

        self.log_text = tk.Text(log_frame, height=5, wrap="none", state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=4, pady=4)

    def _update_topic_preview(self) -> None:
        device_id = self.device_var.get().strip() or "<device_id>"
        self.topic_var.set(f"Topic: {topic_for_device(device_id)}")

    # ------------------------------------------------------------------
    # Connection handling
    # ------------------------------------------------------------------
    def _toggle_connection(self) -> None:
        if self.connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self) -> None:
        host = self.host_var.get().strip()
        device_id = self.device_var.get().strip()

        if not host:
            messagebox.showerror("Invalid input", "Host cannot be empty.")
            return
        if not device_id:
            messagebox.showerror("Invalid input", "Device ID cannot be empty.")
            return
        try:
            port = int(self.port_var.get().strip())
        except ValueError:
            messagebox.showerror("Invalid input", "Port must be a number.")
            return

        client = mqtt.Client()

        username = self.user_var.get().strip()
        if username:
            client.username_pw_set(username, self.pass_var.get())

        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message

        try:
            client.connect(host, port, keepalive=DEFAULT_KEEPALIVE)
        except Exception as exc:  # noqa: BLE001 - surface connection errors to the user
            messagebox.showerror("Connection failed", str(exc))
            return

        client.loop_start()
        self.client = client
        self.connect_btn.configure(text="Disconnect")
        self._set_status("Connecting...", "orange")

    def _disconnect(self) -> None:
        if self.client is not None:
            self.client.loop_stop()
            self.client.disconnect()
            self.client = None
        self.connected = False
        self.connect_btn.configure(text="Connect")
        self._set_status("Disconnected", "red")

    def _set_status(self, text: str, color: str) -> None:
        self.status_var.set(text)
        self.status_lbl.configure(foreground=color)

    # ------------------------------------------------------------------
    # MQTT callbacks (run on the paho-mqtt network thread)
    # ------------------------------------------------------------------
    def _on_connect(self, client: mqtt.Client, userdata, flags, rc: int) -> None:
        if rc == 0:
            topic = topic_for_device(self.device_var.get().strip())
            client.subscribe(topic)
            self._events.put(("connected", topic))
        else:
            self._events.put(("connect_error", f"Connect failed, rc={rc}"))

    def _on_disconnect(self, client: mqtt.Client, userdata, rc: int) -> None:
        self._events.put(("disconnected", ""))

    def _on_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage) -> None:
        raw = msg.payload.decode("utf-8", errors="replace")
        self._events.put(("message", json.dumps({"topic": msg.topic, "raw": raw})))

    # ------------------------------------------------------------------
    # Main-thread event queue polling
    # ------------------------------------------------------------------
    def _poll_events(self) -> None:
        try:
            while True:
                kind, value = self._events.get_nowait()
                if kind == "connected":
                    self.connected = True
                    self._set_status("Connected", "green")
                    self._log(f"Subscribed to {value}")
                elif kind == "connect_error":
                    self.connected = False
                    self._set_status(value, "red")
                    self.connect_btn.configure(text="Connect")
                elif kind == "disconnected":
                    self.connected = False
                    if self.client is not None:
                        self._set_status("Disconnected (lost connection)", "red")
                        self.connect_btn.configure(text="Connect")
                elif kind == "message":
                    data = json.loads(value)
                    self._handle_message(data["topic"], data["raw"])
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._poll_events)

    # ------------------------------------------------------------------
    # Message handling / QR rendering
    # ------------------------------------------------------------------
    def _handle_message(self, topic: str, raw: str) -> None:
        self._log(f"[{topic}] {raw}")

        command: object = None
        sent_at: object = "-"
        qr_payload: str

        # Try to interpret as the send_QR JSON envelope:
        #   {"command": "...", "payload": "...", "sent_at": "..."}
        data = None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = None

        if isinstance(data, dict) and "payload" in data:
            command = data.get("command")
            sent_at = data.get("sent_at", "-")

            expected = self.command_var.get().strip()
            if expected and command != expected:
                self._log(f"  -> ignored: command '{command}' != '{expected}'")
                return

            payload_value = data.get("payload")
            if not payload_value:
                self._log("  -> ignored: 'payload' field is empty")
                return
            qr_payload = str(payload_value)
        else:
            # Not the JSON envelope -- treat the raw message body itself
            # as the QR data (plain URL/string, JSON array, number, etc.)
            if not raw.strip():
                self._log("  -> ignored: empty message")
                return
            qr_payload = raw
            self._log("  -> raw payload (not a {command, payload} envelope), using as-is")

        self.last_command_var.set(str(command) if command is not None else "-")
        self.last_sent_var.set(str(sent_at))
        self.received_var.set(time.strftime("%Y-%m-%d %H:%M:%S"))

        self.payload_text.configure(state="normal")
        self.payload_text.delete("1.0", "end")
        self.payload_text.insert("1.0", qr_payload)
        self.payload_text.configure(state="disabled")

        self._render_qr(qr_payload)

    def _render_qr(self, data: str) -> None:
        try:
            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=8,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
            img.thumbnail((QR_MAX_SIZE_PX, QR_MAX_SIZE_PX), Image.Resampling.NEAREST)

            photo = ImageTk.PhotoImage(img)
            self.qr_label.configure(image=photo, text="")
            self._current_qr_image = photo  # prevent GC
        except Exception as exc:
            self.qr_label.configure(image="", text=f"QR error: {exc}")
            self._log(f"  [render error] {exc}")

    def _log(self, line: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", line + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------
    def on_close(self) -> None:
        self._disconnect()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    app = MqttQrReceiver(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()