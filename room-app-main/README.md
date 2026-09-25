# QR Display App (Vue 3 + TypeScript)

A fullscreen kiosk app for Raspberry Pi that subscribes to MQTT messages and
renders a QR code on screen whenever a `show_qr` command is received.

Designed to fit the existing control_room MQTT message format:

```json
{
  "command": "show_qr",
  "payload": "https://cosai.nrru.ac.th/gePass/XXXX"
}
```

on topic `device/<id>/command`.

---

## 1. Prerequisite: enable MQTT over WebSockets on the broker

Browsers cannot open raw TCP MQTT connections (port 1993/1883) — they need
**MQTT over WebSocket**. Add a websocket listener to your Mosquitto config
on the Pi (192.168.1.177), alongside the existing TCP listener:

```conf
# /etc/mosquitto/mosquitto.conf (or mosquitto.conf.d/websockets.conf)

listener 1883
protocol mqtt

listener 9001
protocol websockets
```

If running Mosquitto in Docker, make sure port `9001` is also published
(`-p 9001:9001` or in `docker-compose.yml`), then restart the broker:

```bash
sudo systemctl restart mosquitto
# or
docker restart <mosquitto_container>
```

Test it works from a browser console or with `wscat`:
```bash
npm install -g wscat
wscat -c ws://192.168.1.177:9001
```

---

## 2. Configuration

Edit `src/App.vue` and adjust the constants near the top:

```ts
const MQTT_URL = 'ws://192.168.1.177:9001'
const TOPIC_FILTER = 'device/+/command'
```

If the broker requires authentication, uncomment and set:
```ts
const MQTT_OPTIONS = {
  ...
  username: 'youruser',
  password: 'yourpassword',
}
```

---

## 3. Install & build (on a dev machine, not necessarily the Pi)

```bash
npm install
npm run dev      # local dev server at http://localhost:5173
npm run build    # produces static files in dist/
```

---

## 4. Deploy to Raspberry Pi

Copy the built `dist/` folder to the Pi, e.g.:

```bash
scp -r dist pi@192.168.1.177:/home/pi/qr-display
```

### Serve it

Simplest option — Python's built-in server:
```bash
cd /home/pi/qr-display
python3 -m http.server 8080
```

Then open `http://localhost:8080` in the browser on the Pi.

(For production, `nginx` or `serve` are better, but `http.server` is fine
for a kiosk display on the local network.)

---

## 5. Run fullscreen (kiosk mode) on the Pi's display

Install Chromium if not already present:
```bash
sudo apt install chromium-browser
```

Launch in kiosk mode:
```bash
chromium-browser --kiosk --noerrdialog --disable-infobars \
  --disable-session-crashed-bubble http://localhost:8080
```

### Auto-start on boot (systemd, recommended)

**Service to serve the built files:**

`/etc/systemd/system/qr-display-server.service`
```ini
[Unit]
Description=QR Display static file server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/qr-display
ExecStart=/usr/bin/python3 -m http.server 8080
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Service to launch Chromium in kiosk mode (after the desktop session starts):**

`/etc/systemd/system/qr-display-kiosk.service`
```ini
[Unit]
Description=QR Display Chromium Kiosk
After=qr-display-server.service graphical.target
Wants=qr-display-server.service

[Service]
Type=simple
User=pi
Environment=DISPLAY=:0
ExecStartPre=/bin/sleep 5
ExecStart=/usr/bin/chromium-browser --kiosk --noerrdialog \
  --disable-infobars --disable-session-crashed-bubble \
  --check-for-update-interval=31536000 http://localhost:8080
Restart=on-failure
RestartSec=5

[Install]
WantedBy=graphical.target
```

Enable both:
```bash
sudo systemctl daemon-reload
sudo systemctl enable qr-display-server qr-display-kiosk
sudo systemctl start qr-display-server qr-display-kiosk
```

> Note: kiosk Chromium needs an active X session (`DISPLAY=:0`). If running
> Raspberry Pi OS Lite (no desktop), you'll need a minimal X setup
> (`xinit` + `openbox`) or use a different renderer (e.g. `cog`/Wayland
> kiosk shell). Let me know which OS image you're using and I can adjust
> this.

---

## 6. Testing end-to-end

From the sender server (192.168.1.176), publish a test command:

```bash
mosquitto_pub -h 192.168.1.177 -p 1883 -t "device/control_room_01/command" \
  -m '{"command":"show_qr","payload":"https://cosai.nrru.ac.th/gePass/0001"}'
```

The Pi's display should immediately render the QR code for that URL, and
the status dot in the top-left should show green ("connected").

---

## Notes / things to verify (audit checklist)

- **Reconnect handling**: `reconnectPeriod: 3000` means the app retries
  every 3s if the WebSocket connection drops — good for unattended kiosk
  displays.
- **Credentials in source**: if you set `username`/`password` in
  `App.vue`, they end up in the built JS bundle, visible to anyone who can
  reach the Pi's web server. Use a broker account scoped to read-only
  subscribe on `device/+/command` if possible, not an admin account.
- **CORS / mixed content**: served over `http://`, so `ws://` (not `wss://`)
  is correct. If you later add TLS to the frontend, you'll also need `wss://`
  on the Mosquitto websocket listener with a cert.
