#include <SPI.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <qrcode.h>
#include <time.h>

// Wall clock for the booking countdown. NTP is used as the time source (Wi-Fi is
// already up); a hardware RTC is not required. Thailand = UTC+7, no DST.
#define TZ_INFO     "ICT-7"
#define NTP_SERVER1 "pool.ntp.org"
#define NTP_SERVER2 "time.google.com"

// ---------- WiFi / MQTT config ----------
#define WIFI_SSID     "iotsmartlab"
#define WIFI_PASSWORD "00000000"
//---------- Room / device config ----------
#define ROOM                 "27.03.05"   // = request.room
#define APP_URL "https://cosai.nrru.ac.th/room-manager/"


//#define MQTT_HOST     "192.168.16.112"
#define MQTT_HOST "10.27.127.25"
#define MQTT_PORT     1883
// schedule_service.py publishes to "AP-TOPIC/<room>" with NO trailing slash;
// MQTT topic matching is exact, so the trailing "/" here used to make every
// message miss this subscription.
#define MQTT_TOPIC    "AP-TOPIC/" ROOM   // e.g. "AP-TOPIC/27.03.05"

// PubSubClient silently drops any inbound packet bigger than its buffer, so keep
// this comfortably above the largest schedule/device payload (topic + JSON).
#define MQTT_BUFFER_SIZE   1024
#define MQTT_KEEPALIVE_S   30
#define MQTT_SOCKET_TMO_S  8
#define MQTT_RETRY_MS      3000   // gap between reconnect attempts (non-blocking)

// Device/relay command topic — matches send_to_device.py's /device/command:
// topic "device/{room}/{device}", payload is either
//     {"targets":[{"gpio_pin":13,"status":"on"}, ...]}   or
//     {"gpio_pin":13,"status":"off"}          (single object, legacy)
// room/device here must match this board's row in room_binding (room_no / devices).
#define DEVICE               "door"       // = request.device
#define DEVICE_COMMAND_TOPIC "device/" ROOM "/" DEVICE
#define DEVICE_STATE_TOPIC   "device/" ROOM "/" DEVICE "/state"    // per-pin confirmation
#define DEVICE_STATUS_TOPIC  "device/" ROOM "/" DEVICE "/status"   // online / offline (LWT)
// Base URL of the room-manager web app (keep the trailing slash) — every QR
// link below is built from this prefix.

// Relay polarity: 0 = active-HIGH (on -> HIGH), 1 = active-LOW (on -> LOW)
#define ACTIVE_LOW 1

// QR code content: "<QR_BASE_URL><rowId>"
#define QR_BASE_URL           APP_URL "?rowId="

// Fallback QR shown when source_type is missing/"non" (no active schedule/booking)
#define STAFF_ACCESS_URL      APP_URL "staff-access/?room=" ROOM

// QR shown when the device (door) turns on: "<SUBMIT_CLOSE_URL_BASE>&rowId=<lastRowId>"
#define SUBMIT_CLOSE_URL_BASE APP_URL "submit-close?room=" ROOM

WiFiClient espClient;
PubSubClient mqttClient(espClient);

// ---------- TFT pins ----------
#define TFT_MISO 19
#define TFT_BL   32
#define TFT_SCLK 18
#define TFT_MOSI 23
#define TFT_DC   16
#define TFT_RST  17
#define TFT_CS   5

// Landscape (horizontal) orientation — 320 wide x 240 tall.
#define TFT_W 320
#define TFT_H 240

// RGB565 colours (swap the blues for reds if the panel renders BGR)
#define COLOR_WHITE     0xFFFF
#define COLOR_BLACK     0x0000
#define COLOR_BLUE      0x001F   // "SCAN ME" text / accents
#define COLOR_NAVY      0x0010   // header bar
#define COLOR_LIGHTBLUE 0xCE7F   // "SCAN ME" panel background
#define COLOR_GRAY      0x8410   // hairlines / dividers
#define COLOR_DGRAY     0x39E7   // secondary text (dark enough to read on white)
#define COLOR_GREEN     0x0640   // "IN USE" badge

// Buffer for whatever token we're currently displaying
// Starts with a sample token so the QR code is visible immediately at boot,
// before the first real MQTT message arrives.
char currentToken[512] = STAFF_ACCESS_URL;
volatile bool needsRedraw = true;

// Schedule details from the last MQTT message, drawn as text under the QR code.
// coursename is intentionally not stored/shown — it is Thai text and the 5x7
// bitmap font here is ASCII-only. coursecode (numeric) stands in for it.
char displayCourseCode[32]   = "";
char displayScheduleDate[16] = "";
char displayStartTime[12]    = "";
char displayFinishTime[12]   = "";
char displayUserCode[32]     = "";

// rowId from the last AP-TOPIC message — reused to build the submit-close QR
// when the device (door) turns on.
char lastRowId[32] = "";

// Same rowId, kept as a general-purpose global other code can read.
char globalRowId[32] = "";

// Caption drawn beside the QR code when there is no schedule info to show —
// flips between "SCAN ME"/"SCAN OFF" as the device command topic reports the
// door's status (see handleDeviceCommand).
char scanCaption[16] = "SCAN ME";

// true once the door has been driven open by a device command — the booking
// badge then reads "In-Use" instead of "Wait-Confirm" (see updateDoorQR).
bool doorInUse = false;

// Booking-countdown state (full description: "BOOKING COUNTDOWN MODULE" block
// further down, above timeSynced()).
//   bookingEndEpoch : unix time (s) when the slot ends; 0 = no countdown
//   cdX / cdY       : where showQRCode() placed the countdown line (-1 = none)
//   cdLastShown     : last seconds value painted, so loop() only repaints on change
time_t bookingEndEpoch = 0;
int    cdX = -1, cdY = -1;
long   cdLastShown = -1;

// IP status printing (non-blocking, in loop())
unsigned long lastIpPrint = 0;
const unsigned long IP_PRINT_INTERVAL = 30000; // every 30s

// When a device command arrives we paint a "DEVICE COMMAND" screen showing the
// target(s) from the MQTT host, hold it for DEVICE_SCREEN_MS, then fall back to
// the QR. deviceScreenUntil == 0 means "not showing the command screen".
#define DEVICE_SCREEN_MS 4000

// Countdown enters "alert" (blinking, ENDING SOON, beeping) at this many
// seconds left. Once it hits 0 the "TIME UP" alarm sounds for
// COUNTDOWN_END_ALARM_MS, then the panel resets to SCAN ME.
#define COUNTDOWN_ALERT_S     900     // 15 min before close: blink + beep
#define COUNTDOWN_END_ALARM_MS 20000

// Buzzer / speaker for the audible alert.
//   BUZZER_PIN     : GPIO the buzzer is wired to, or -1 to disable sound
//   BUZZER_PASSIVE : 1 = passive piezo (driven with tone()); 0 = active buzzer (on/off)
//   BUZZER_TONE_HZ : pitch for a passive piezo
#define BUZZER_PIN      25
#define BUZZER_PASSIVE  1
#define BUZZER_TONE_HZ  2600

unsigned long deviceScreenUntil = 0;
int deviceScreenY = 0;   // running Y cursor while painting the command screen

// Buzzer state (non-blocking, driven from loop()).
unsigned long buzzerBeepUntil = 0;   // active-buzzer: when to release the pin
unsigned long buzzerNextBeep  = 0;   // when the next beep in the alert may fire

// millis() when the countdown first reached 0; 0 = not in the "TIME UP" alarm.
unsigned long overtimeStart = 0;

// ---------- Low-level TFT ----------
void cmd(uint8_t c)
{
  digitalWrite(TFT_DC, LOW);
  digitalWrite(TFT_CS, LOW);
  SPI.transfer(c);
  digitalWrite(TFT_CS, HIGH);
}

void data8(uint8_t d)
{
  digitalWrite(TFT_DC, HIGH);
  digitalWrite(TFT_CS, LOW);
  SPI.transfer(d);
  digitalWrite(TFT_CS, HIGH);
}

void data16(uint16_t d)
{
  data8(d >> 8);
  data8(d);
}

void addr(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1)
{
  cmd(0x2A);
  data16(x0);
  data16(x1);
  cmd(0x2B);
  data16(y0);
  data16(y1);
  cmd(0x2C);
}

void fill(uint16_t color)
{
  addr(0, 0, TFT_W - 1, TFT_H - 1);
  digitalWrite(TFT_DC, HIGH);
  digitalWrite(TFT_CS, LOW);
  for (uint32_t i = 0; i < (uint32_t)TFT_W * TFT_H; i++)
  {
    SPI.transfer(color >> 8);
    SPI.transfer(color);
  }
  digitalWrite(TFT_CS, HIGH);
}

void rect(uint16_t x, uint16_t y, uint16_t w, uint16_t h, uint16_t color)
{
  addr(x, y, x + w - 1, y + h - 1);
  digitalWrite(TFT_DC, HIGH);
  digitalWrite(TFT_CS, LOW);
  for (uint32_t i = 0; i < (uint32_t)w * h; i++)
  {
    SPI.transfer(color >> 8);
    SPI.transfer(color);
  }
  digitalWrite(TFT_CS, HIGH);
}

// ---------- Minimal text rendering ----------
// 5x7 bitmap font — space, uppercase A-Z, digits 0-9, and '-' '.' ':'
// (enough for course codes, dates, times, and user codes). Each glyph is
// 5 columns of 7 bits; bit 0 is the top row.
static const uint8_t FONT5x7[40][5] = {
  {0x00,0x00,0x00,0x00,0x00}, // ' '
  {0x7E,0x11,0x11,0x11,0x7E}, // A
  {0x7F,0x49,0x49,0x49,0x36}, // B
  {0x3E,0x41,0x41,0x41,0x22}, // C
  {0x7F,0x41,0x41,0x22,0x1C}, // D
  {0x7F,0x49,0x49,0x49,0x41}, // E
  {0x7F,0x09,0x09,0x09,0x01}, // F
  {0x3E,0x41,0x49,0x49,0x7A}, // G
  {0x7F,0x08,0x08,0x08,0x7F}, // H
  {0x00,0x41,0x7F,0x41,0x00}, // I
  {0x20,0x40,0x41,0x3F,0x01}, // J
  {0x7F,0x08,0x14,0x22,0x41}, // K
  {0x7F,0x40,0x40,0x40,0x40}, // L
  {0x7F,0x02,0x0C,0x02,0x7F}, // M
  {0x7F,0x04,0x08,0x10,0x7F}, // N
  {0x3E,0x41,0x41,0x41,0x3E}, // O
  {0x7F,0x09,0x09,0x09,0x06}, // P
  {0x3E,0x41,0x51,0x21,0x5E}, // Q
  {0x7F,0x09,0x19,0x29,0x46}, // R
  {0x46,0x49,0x49,0x49,0x31}, // S
  {0x01,0x01,0x7F,0x01,0x01}, // T
  {0x3F,0x40,0x40,0x40,0x3F}, // U
  {0x1F,0x20,0x40,0x20,0x1F}, // V
  {0x3F,0x40,0x38,0x40,0x3F}, // W
  {0x63,0x14,0x08,0x14,0x63}, // X
  {0x07,0x08,0x70,0x08,0x07}, // Y
  {0x61,0x51,0x49,0x45,0x43}, // Z
  {0x3E,0x51,0x49,0x45,0x3E}, // 0
  {0x00,0x42,0x7F,0x40,0x00}, // 1
  {0x42,0x61,0x51,0x49,0x46}, // 2
  {0x21,0x41,0x45,0x4B,0x31}, // 3
  {0x18,0x14,0x12,0x7F,0x10}, // 4
  {0x27,0x45,0x45,0x45,0x39}, // 5
  {0x3C,0x4A,0x49,0x49,0x30}, // 6
  {0x01,0x71,0x09,0x05,0x03}, // 7
  {0x36,0x49,0x49,0x49,0x36}, // 8
  {0x06,0x49,0x49,0x29,0x1E}, // 9
  {0x08,0x08,0x08,0x08,0x08}, // -
  {0x00,0x60,0x60,0x00,0x00}, // .
  {0x00,0x36,0x36,0x00,0x00}, // :
};

int fontIndex(char c)
{
  if (c >= 'a' && c <= 'z') c -= 32; // uppercase it
  if (c >= 'A' && c <= 'Z') return 1 + (c - 'A');
  if (c >= '0' && c <= '9') return 27 + (c - '0');
  if (c == '-') return 37;
  if (c == '.') return 38;
  if (c == ':') return 39;
  return 0; // space and any unsupported char render blank
}

void drawChar(uint16_t x, uint16_t y, char c, uint8_t scale, uint16_t color)
{
  const uint8_t* glyph = FONT5x7[fontIndex(c)];
  for (uint8_t col = 0; col < 5; col++)
  {
    uint8_t bits = glyph[col];
    for (uint8_t row = 0; row < 7; row++)
    {
      if (bits & (1 << row))
      {
        rect(x + col * scale, y + row * scale, scale, scale, color);
      }
    }
  }
}

void drawText(uint16_t x, uint16_t y, const char* text, uint8_t scale, uint16_t color)
{
  uint16_t cursorX = x;
  for (const char* p = text; *p != '\0'; p++)
  {
    drawChar(cursorX, y, *p, scale, color);
    cursorX += 6 * scale; // 5 columns + 1 column gap
  }
}

int textWidthPx(const char* text, uint8_t scale)
{
  int n = (int)strlen(text);
  if (n == 0) return 0;
  return n * 6 * scale - scale; // 6px advance/char, no trailing gap
}

// Draws one line of text centered horizontally at y, returns the y for the next line
int drawCenteredLine(int y, const char* text, uint8_t scale, uint16_t color)
{
  int textX = (TFT_W - textWidthPx(text, scale)) / 2;
  drawText(textX, y, text, scale, color);
  return y + 7 * scale + 6; // glyph height + line gap
}

// Draws one left-aligned line at (x, y), returns the y for the next line.
int drawLeftLine(int x, int y, const char* text, uint8_t scale, uint16_t color)
{
  drawText(x, y, text, scale, color);
  return y + 7 * scale + 8;
}

// Same as drawText but drawn twice (1px offset) for a faux-bold weight.
void drawTextBold(int x, int y, const char* text, uint8_t scale, uint16_t color)
{
  drawText(x, y, text, scale, color);
  drawText(x + 1, y, text, scale, color);
}

// Rectangle outline of thickness t.
void drawBorder(int x, int y, int w, int h, int t, uint16_t color)
{
  rect(x, y, w, t, color);
  rect(x, y + h - t, w, t, color);
  rect(x, y, t, h, color);
  rect(x + w - t, y, t, h, color);
}

// Small solid triangle pointing left — a little "look over here" arrow toward
// the QR code. (tipX,tipY) is the tip; grows h px right and 2h px tall.
void drawLeftArrow(int tipX, int tipY, int h, uint16_t color)
{
  for (int i = 0; i < h; i++)
    rect(tipX + i, tipY - (h - i), 2, 2 * (h - i), color);
}

// A tidy label row:  [] KEY VALUE   with a small blue bullet.
int drawField(int x, int y, const char* text, uint8_t scale, uint16_t color)
{
  int bump = (7 * scale) / 2 - 2;
  rect(x, y + bump, 5, 5, COLOR_BLUE);
  drawText(x + 12, y, text, scale, color);
  return y + 7 * scale + 9;
}

// ===========================================================================
//  BOOKING COUNTDOWN MODULE
// ===========================================================================
//  Shows a live "TIME LEFT" timer on the QR screen's right panel while a
//  booking is active, warns as the slot nears its end, and sounds a buzzer
//  when time is up.
//
//  TIME SOURCE
//    NTP only (Wi-Fi is already up; no hardware RTC). configTzTime(TZ_INFO,...)
//    is called once in setup(); time() is valid a few seconds later.
//    timeSynced() reports whether that has happened. If NTP never syncs the
//    whole module stays dormant (countdownRemaining() returns -1).
//
//  LIFECYCLE
//    1. mqttCallback() receives an AP-TOPIC booking (has a rowId) and sets
//         bookingEndEpoch = end-of-slot unix time
//       computed from schedule_date + finishTime, or (fallback) now + the
//       payload's "duration" seconds.
//    2. showQRCode() lays out the panel and records where the timer goes
//       (cdX, cdY); it calls drawCountdown() once on that full redraw.
//    3. loop() every iteration:
//         - updateBuzzer(secondsLeft)  -> audible alert, its own cadence
//         - once/second: drawCountdown()  -> repaints just the timer line
//    4. At 0 seconds loop() records overtimeStart and holds the blinking
//       "TIME UP" alarm for COUNTDOWN_END_ALARM_MS, then calls
//       updateDoorQR(false) to clear everything back to the "SCAN ME" card.
//    Any of these also clear the module early: a new AP-TOPIC message, the
//    door closing (updateDoorQR(false)).
//
//  DISPLAY STATES  (drawCountdown)
//    > COUNTDOWN_ALERT_S      "TIME LEFT"    black, static
//    <= COUNTDOWN_ALERT_S     "ENDING SOON"  blinks blue/white  (+ buzzer)
//    == 0                     "TIME UP"      blinks              (+ urgent buzzer)
//
//  KEY STATE  (globals declared near the top of the file)
//    bookingEndEpoch  unix time the slot ends; 0 = module idle
//    cdX, cdY         pixel position of the timer line; -1 = not on screen
//    cdLastShown      last seconds value painted (repaint only on change)
//    overtimeStart    millis() when it hit 0; 0 = not in the TIME UP alarm
//    buzzerBeepUntil / buzzerNextBeep   non-blocking buzzer timing
// ===========================================================================

// ---------- clock helpers ----------

// True once NTP has answered (system epoch is past 2023-11); until then any
// countdown math would be meaningless.
bool timeSynced()
{
  return time(nullptr) > 1700000000;
}

// "YYYY-MM-DD" (trailing "THH:MM:SS" ignored) + "HH:MM"  ->  unix time, 0 on error
time_t epochFromDateTime(const char* ymd, const char* hm)
{
  int Y, Mo, D, h, mi;
  if (sscanf(ymd, "%d-%d-%d", &Y, &Mo, &D) != 3) return 0;
  if (sscanf(hm,  "%d:%d",    &h, &mi)     != 2) return 0;

  struct tm t = {0};
  t.tm_year = Y - 1900;
  t.tm_mon  = Mo - 1;
  t.tm_mday = D;
  t.tm_hour = h;
  t.tm_min  = mi;
  t.tm_isdst = 0;
  time_t e = mktime(&t);          // TZ env (TZ_INFO) makes this local -> UTC
  return e > 0 ? e : 0;
}

// Seconds left on the current booking: -1 = no countdown / clock not ready,
// 0 = finished, else remaining seconds.
long countdownRemaining()
{
  if (bookingEndEpoch == 0 || !timeSynced()) return -1;
  long r = (long)bookingEndEpoch - (long)time(nullptr);
  return r < 0 ? 0 : r;
}

// Repaints the countdown label + value at (cdX, cdY). Called by showQRCode() on
// a full redraw and by loop() once per second. Three looks:
//   TIME LEFT     black, static           (> COUNTDOWN_ALERT_S)
//   ENDING SOON   blinks blue/white       (<= COUNTDOWN_ALERT_S)
//   TIME UP       blinks blue/white       (== 0)
// Does nothing if the timer isn't on screen (cdY < 0) or the clock isn't ready
// (secs < 0). Each call toggles `blink`, so calling it ~1 Hz gives the flash.
void drawCountdown()
{
  if (cdY < 0) return;
  long secs = countdownRemaining();
  if (secs < 0) return;

  int hh = secs / 3600, mm = (secs % 3600) / 60, ss = secs % 60;
  char t[16];
  if (hh) snprintf(t, sizeof(t), "%d:%02d:%02d", hh, mm, ss);
  else    snprintf(t, sizeof(t), "%02d:%02d", mm, ss);

  bool timeUp = (secs == 0);
  bool alert  = timeUp || (secs <= COUNTDOWN_ALERT_S);

  static bool blink = false;
  blink = !blink;

  uint16_t bg, fg;
  if (alert) { bg = blink ? COLOR_BLUE  : COLOR_WHITE;
               fg = blink ? COLOR_WHITE : COLOR_BLUE; }
  else       { bg = COLOR_WHITE; fg = COLOR_BLACK; }

  const char* label = timeUp ? "TIME UP" : alert ? "ENDING SOON" : "TIME LEFT";

  int boxX = cdX;
  int boxW = (TFT_W - 12) - cdX;
  int labelY = cdY - 12;   // matches showQRCode's "y += 7 + 5" before cdY

  rect(boxX, labelY - 2, boxW, (cdY + 16) - (labelY - 2), bg);   // clear label + value
  drawText(cdX, labelY, label, 1, alert ? fg : COLOR_DGRAY);
  rect(cdX, cdY + 3, 5, 5, fg);                                  // bullet
  drawText(cdX + 12, cdY, t, 2, fg);
}

// ---------- audible alert (non-blocking) ----------
// The buzzer is never driven with delay(): buzzerBeep() starts a beep and
// stamps buzzerBeepUntil; updateBuzzer(), run every loop(), ends it and
// schedules the next one. All three compile to nothing when BUZZER_PIN < 0.

// Silence the buzzer immediately (call on reset / booking change).
void buzzerStop()
{
#if BUZZER_PIN >= 0
 #if BUZZER_PASSIVE
  noTone(BUZZER_PIN);
 #else
  digitalWrite(BUZZER_PIN, LOW);
 #endif
  buzzerBeepUntil = 0;
#endif
}

// Start a single beep of `ms` milliseconds (non-blocking).
void buzzerBeep(uint16_t ms)
{
#if BUZZER_PIN >= 0
 #if BUZZER_PASSIVE
  tone(BUZZER_PIN, BUZZER_TONE_HZ, ms);   // passive piezo: tone() auto-stops after ms
 #else
  digitalWrite(BUZZER_PIN, HIGH);         // active buzzer: updateBuzzer() releases it
 #endif
  buzzerBeepUntil = millis() + ms;
#endif
}

// Run every loop() with the seconds left (-1 = no countdown). Ends a finished
// beep, then (inside the alert window) schedules the next one — cadence tightens
// as the deadline nears and is hardest at 0. Silent outside the window.
void updateBuzzer(long secs)
{
#if BUZZER_PIN >= 0
  unsigned long now = millis();

  if (buzzerBeepUntil && now >= buzzerBeepUntil) {
   #if !BUZZER_PASSIVE
    digitalWrite(BUZZER_PIN, LOW);
   #endif
    buzzerBeepUntil = 0;
  }

  // secs == 0 ("time up") beeps hardest; -1 means no active countdown.
  bool alerting = (secs >= 0 && secs <= COUNTDOWN_ALERT_S);
  if (!alerting) {
    if (buzzerNextBeep) { buzzerNextBeep = 0; buzzerStop(); }
    return;
  }

  unsigned long interval = (secs == 0)   ?   600UL :   // time up: urgent
                           (secs <= 10)  ?  1000UL :
                           (secs <= 60)  ?  3000UL :
                           (secs <= 300) ? 12000UL : 30000UL;  // 15..5 min: gentle

  if (now >= buzzerNextBeep) {
    buzzerNextBeep = now + interval;
    buzzerBeep(secs == 0 ? 400 : (secs <= 10 ? 350 : 150));
  }
#endif
}

// Landscape layout inside a framed card:
//   left  — QR code in a white quiet-zone box
//   right — schedule/booking details, or a pretty blue "SCAN ME" panel
void showQRCode(esp_qrcode_handle_t qrcode)
{
  int qrSize = esp_qrcode_get_size(qrcode);

  fill(COLOR_WHITE);

  // ---------- card frame ----------
  drawBorder(2, 2, TFT_W - 4, TFT_H - 4, 3, COLOR_BLUE);
  drawBorder(8, 8, TFT_W - 16, TFT_H - 16, 1, COLOR_GRAY);

  // ---------- header bar ----------
  const int headerH = 28;
  rect(8, 8, TFT_W - 16, headerH, COLOR_BLUE);
  {
    char hdr[24];
    snprintf(hdr, sizeof(hdr), "ROOM %s", ROOM);
    int w = textWidthPx(hdr, 2);
    drawTextBold((TFT_W - w) / 2, 8 + (headerH - 14) / 2, hdr, 2, COLOR_WHITE);
  }

  const int contentTop = 8 + headerH + 10;
  const int contentBot = TFT_H - 12;
  const int contentH   = contentBot - contentTop;

  // ---------- QR on the left ----------
  int scale = 4;
  while (scale > 2 && qrSize * scale > contentH - 8) scale--;
  int size = qrSize * scale;

  int x0 = 22;
  int y0 = contentTop + (contentH - size) / 2;
  if (y0 < contentTop) y0 = contentTop;

  drawBorder(x0 - 7, y0 - 7, size + 14, size + 14, 1, COLOR_GRAY);

  for (int y = 0; y < qrSize; y++)
    for (int x = 0; x < qrSize; x++)
      if (esp_qrcode_get_module(qrcode, x, y))
        rect(x0 + x * scale, y0 + y * scale, scale, scale, COLOR_BLACK);

  // ---------- right-hand panel ----------
  int panelX = x0 + size + 20;
  int panelW = (TFT_W - 12) - panelX;

  // vertical divider between QR and panel
  rect(panelX - 10, contentTop, 1, contentH, COLOR_GRAY);

  // Any active target (rowId) -> "In-Use" panel; otherwise the "SCAN ME" card.
  bool haveInfo = globalRowId[0] ||
                  displayCourseCode[0] || displayStartTime[0] || displayFinishTime[0];

  cdX = cdY = -1;   // no countdown unless the info panel places one below

  if (!haveInfo)
  {
    // Pretty call-to-action: "SCAN ME" / "SCAN OFF" in a soft blue card.
    char w1[16] = "", w2[16] = "";
    const char* sp = strchr(scanCaption, ' ');
    if (sp)
    {
      size_t n = (size_t)(sp - scanCaption);
      if (n >= sizeof(w1)) n = sizeof(w1) - 1;
      memcpy(w1, scanCaption, n);
      w1[n] = '\0';
      snprintf(w2, sizeof(w2), "%s", sp + 1);
    }
    else
    {
      snprintf(w1, sizeof(w1), "%s", scanCaption);
    }

    int cardY = contentTop + 6;
    int cardH = contentH - 12;
    rect(panelX, cardY, panelW, cardH, COLOR_LIGHTBLUE);
    drawBorder(panelX, cardY, panelW, cardH, 2, COLOR_BLUE);

    uint8_t s = (textWidthPx(w1, 3) <= panelW - 16) ? 3 : 2;
    int lineH = 7 * s;
    int block = w2[0] ? lineH * 2 + 12 : lineH;
    int ty = cardY + (cardH - block) / 2 - 6;

    int w1x = panelX + (panelW - textWidthPx(w1, s)) / 2;
    drawTextBold(w1x, ty, w1, s, COLOR_BLUE);
    if (w2[0])
    {
      int w2x = panelX + (panelW - textWidthPx(w2, s)) / 2;
      drawTextBold(w2x, ty + lineH + 12, w2, s, COLOR_BLUE);
    }

    // underline + arrow nudging toward the QR
    int uy = ty + block + 10;
    rect(panelX + panelW / 2 - 18, uy, 36, 3, COLOR_BLUE);
    drawLeftArrow(panelX + 6, cardY + cardH / 2, 7, COLOR_BLUE);
    return;
  }

  // Schedule / booking in progress — badge + tidy field list.
  int y = contentTop + 4;

  char badge[16];
  snprintf(badge, sizeof(badge), "%s", doorInUse ? "In-Use" : "Wait-Confirm");
  int bw = textWidthPx(badge, 1) + 12;
  rect(panelX, y, bw, 16, COLOR_GREEN);
  drawText(panelX + 6, y + 1, badge, 1, COLOR_WHITE);
  y += 26;

  if (displayCourseCode[0])
    y = drawField(panelX, y, displayCourseCode, 2, COLOR_BLACK);

  if (displayStartTime[0] || displayFinishTime[0])
  {
    char timeLine[24];
    snprintf(timeLine, sizeof(timeLine), "%s-%s", displayStartTime, displayFinishTime);
    uint8_t ts = (textWidthPx(timeLine, 2) <= panelW - 14) ? 2 : 1;
    y = drawField(panelX, y, timeLine, ts, COLOR_BLACK);
  }

  if (displayScheduleDate[0])
    y = drawField(panelX, y, displayScheduleDate, 1, COLOR_DGRAY);

  if (displayUserCode[0])
    y = drawField(panelX, y, displayUserCode, 1, COLOR_DGRAY);

  // Countdown to the end of the slot — drawCountdown() paints the label + value
  // and loop() keeps it current (blinks under COUNTDOWN_ALERT_S).
  if (bookingEndEpoch != 0)
  {
    y += 6 + 12;          // room for the label drawCountdown() draws above cdY
    cdX = panelX;
    cdY = y;
    drawCountdown();
    y += 7 * 2 + 9;
  }
}

// Renders whatever is currently in currentToken[]
void drawQRCode()
{
  esp_qrcode_config_t cfg = ESP_QRCODE_CONFIG_DEFAULT();
  cfg.display_func = showQRCode;
  cfg.max_qrcode_version = 5; // version 3 (~53 bytes) is too small for a full URL; v5 (~106 bytes) still fits the left half at scale=4 (37*4=148px)
  cfg.qrcode_ecc_level = ESP_QRCODE_ECC_LOW;
  esp_qrcode_generate(&cfg, currentToken);
}

// ---------- "DEVICE COMMAND" screen ----------
// Paints the header for an incoming device command (topic DEVICE_COMMAND_TOPIC).
// Pull "<room>" and "<device>" out of an incoming topic "device/<room>/<device>[/...]".
// Falls back to the ROOM / DEVICE macros for any segment that is missing.
void splitDeviceTopic(const char* topic, char* room, size_t roomLen,
                                         char* device, size_t deviceLen)
{
  snprintf(room, roomLen, "%s", ROOM);
  snprintf(device, deviceLen, "%s", DEVICE);
  if (!topic) return;

  const char* p = strchr(topic, '/');          // after "device"
  if (!p) return;
  p++;
  const char* slash2 = strchr(p, '/');
  if (!slash2) { snprintf(room, roomLen, "%s", p); return; }

  size_t rlen = (size_t)(slash2 - p);
  if (rlen >= roomLen) rlen = roomLen - 1;
  memcpy(room, p, rlen);
  room[rlen] = '\0';

  const char* d = slash2 + 1;
  const char* slash3 = strchr(d, '/');         // stop before "/state" etc.
  size_t dlen = slash3 ? (size_t)(slash3 - d) : strlen(d);
  if (dlen >= deviceLen) dlen = deviceLen - 1;
  memcpy(device, d, dlen);
  device[dlen] = '\0';
}

// The font only knows A-Z / 0-9 / space - . : so keep every string in that set.
void beginDeviceCommandScreen(const char* room, const char* device, int count)
{
  fill(COLOR_WHITE);
  drawBorder(2, 2, TFT_W - 4, TFT_H - 4, 3, COLOR_BLUE);
  drawBorder(8, 8, TFT_W - 16, TFT_H - 16, 1, COLOR_GRAY);

  int y = 18;
  y = drawCenteredLine(y, "DEVICE COMMAND", 2, COLOR_BLACK);

  char sub[40];
  snprintf(sub, sizeof(sub), "%s - %s", room, device);   // e.g. "27.03.04 - DOOR"
  y = drawCenteredLine(y, sub, 2, COLOR_BLACK);

  char n[24];
  snprintf(n, sizeof(n), "TARGETS %d", count);
  y = drawCenteredLine(y, n, 1, COLOR_BLACK);

  deviceScreenY = y + 14;
}

// One target row. reason == nullptr -> applied ok (green ON / red OFF),
// otherwise a short skip reason is shown in gray.
void deviceCommandScreenRow(int gpioPin, bool turnOn, const char* reason)
{
  char line[24];
  uint16_t color;

  if (reason) {
    if (gpioPin >= 0) snprintf(line, sizeof(line), "PIN %d  %s", gpioPin, reason);
    else              snprintf(line, sizeof(line), "%s", reason);
    color = 0x8410;                       // gray
  } else {
    snprintf(line, sizeof(line), "PIN %d  %s", gpioPin, turnOn ? "ON" : "OFF");
    color = turnOn ? 0x07E0 : 0xF800;     // green / red
  }

  deviceScreenY = drawCenteredLine(deviceScreenY, line, 3, color);
}

void ili9341Init()
{
  digitalWrite(TFT_RST, LOW);
  delay(20);
  digitalWrite(TFT_RST, HIGH);
  delay(150);

  cmd(0x01);
  delay(150);
  cmd(0x28);
  cmd(0x3A);
  data8(0x55);
  cmd(0x36);
  data8(0x28);   // MADCTL: MV=1, BGR=1 -> landscape (horizontal)
  cmd(0x11);
  delay(150);
  cmd(0x29);
  delay(50);
}

// ---------- MQTT ----------

// TFT (and buzzer) pins must never be reassigned by an incoming device command —
// doing so would hijack a pin away from the display driver and break SPI silently.
bool isReservedTftPin(int pin)
{
  return pin == TFT_MISO || pin == TFT_BL   || pin == TFT_SCLK || pin == TFT_MOSI ||
         pin == TFT_DC   || pin == TFT_RST  || pin == TFT_CS
#if BUZZER_PIN >= 0
         || pin == BUZZER_PIN
#endif
         ;
}

// "on"/"1"/"true"/"high" -> true ; "off"/"0"/"false"/"low" -> false ; else ok=false
bool parseStatus(const char* status, bool& ok)
{
  ok = true;
  if (!status) { ok = false; return false; }
  if (!strcasecmp(status, "on")  || !strcasecmp(status, "1") ||
      !strcasecmp(status, "true")|| !strcasecmp(status, "high")) return true;
  if (!strcasecmp(status, "off") || !strcasecmp(status, "0") ||
      !strcasecmp(status, "false")|| !strcasecmp(status, "low")) return false;
  ok = false;
  return false;
}

// Publish {"gpio_pin":N,"status":"on|off"} back to DEVICE_STATE_TOPIC
void publishState(int gpioPin, bool turnOn)
{
  StaticJsonDocument<96> out;
  out["gpio_pin"] = gpioPin;
  out["status"]   = turnOn ? "on" : "off";
  char buf[96];
  size_t n = serializeJson(out, buf);
  mqttClient.publish(DEVICE_STATE_TOPIC, (const uint8_t*)buf, n, false);
}

// Drive one target pin and print a table row.
// Returns true if a pin was actually driven; *outOn = resulting on/off state.
bool applyTarget(int idx, int gpioPin, const char* status, bool* outOn)
{
  const char* statusText = status ? status : "(null)";

  if (gpioPin < 0) {
    Serial.printf("| %2d | %-8s | %-7s | %-24s |\n", idx, "-", statusText, "SKIP: missing gpio_pin");
    deviceCommandScreenRow(gpioPin, false, "NO PIN");
    return false;
  }
  if (isReservedTftPin(gpioPin)) {
    Serial.printf("| %2d | %8d | %-7s | %-24s |\n", idx, gpioPin, statusText, "SKIP: reserved TFT pin");
    deviceCommandScreenRow(gpioPin, false, "RESERVED");
    return false;
  }

  bool ok;
  bool turnOn = parseStatus(status, ok);
  if (!ok) {
    Serial.printf("| %2d | %8d | %-7s | %-24s |\n", idx, gpioPin, statusText, "SKIP: unknown status");
    deviceCommandScreenRow(gpioPin, false, "BAD STATUS");
    return false;
  }

  pinMode(gpioPin, OUTPUT);

  // ACTIVE_LOW = 0 -> "on" drives the pin HIGH ; ACTIVE_LOW = 1 -> "on" drives it LOW
  int level = turnOn ? (ACTIVE_LOW ? LOW : HIGH)
                     : (ACTIVE_LOW ? HIGH : LOW);
  digitalWrite(gpioPin, level);

  int readback = digitalRead(gpioPin);
  Serial.printf(">> digitalWrite(GPIO %d, %s)  status=%s  ACTIVE_LOW=%d  readback=%s\n",
                gpioPin, level == HIGH ? "HIGH" : "LOW",
                turnOn ? "on" : "off", ACTIVE_LOW,
                readback == HIGH ? "HIGH" : "LOW");

  char action[28];
  snprintf(action, sizeof(action), "%s -> %s",
           turnOn ? "ON " : "OFF", level == HIGH ? "HIGH" : "LOW");
  Serial.printf("| %2d | %8d | %-7s | %-24s |\n", idx, gpioPin, statusText, action);
  deviceCommandScreenRow(gpioPin, turnOn, nullptr);

  publishState(gpioPin, turnOn);
  if (outOn) *outOn = turnOn;
  return true;
}

// The door's open/closed state drives what the on-screen QR points to.
void updateDoorQR(bool doorOpen)
{
  if (doorOpen) {
    // Door opened — switch the QR to the submit-close link for this booking.
    int written = snprintf(currentToken, sizeof(currentToken), "%s&rowId=%s",
                           SUBMIT_CLOSE_URL_BASE, lastRowId);
    if (written < 0 || (size_t)written >= sizeof(currentToken)) {
      Serial.println("Submit-close URL too long for currentToken buffer, ignoring");
      return;
    }
    snprintf(scanCaption, sizeof(scanCaption), "SCAN OFF");
    doorInUse = true;   // booking badge -> "In-Use"
  } else {
    // Door closed — revert to the idle staff-access link and drop the booking
    // so the panel goes back to the "SCAN ME" card.
    snprintf(currentToken, sizeof(currentToken), "%s", STAFF_ACCESS_URL);
    snprintf(scanCaption, sizeof(scanCaption), "SCAN ME");
    doorInUse = false;
    bookingEndEpoch        = 0;
    overtimeStart          = 0;
    buzzerStop();
    globalRowId[0]         = '\0';
    lastRowId[0]           = '\0';
    displayCourseCode[0]   = '\0';
    displayStartTime[0]    = '\0';
    displayFinishTime[0]   = '\0';
    displayScheduleDate[0] = '\0';
    displayUserCode[0]     = '\0';
  }
  needsRedraw = true;
  Serial.print("New QR content set: ");
  Serial.println(currentToken);
}

// Handles a device/{room}/{device} command. Accepts both:
//   {"targets":[{"gpio_pin":13,"status":"on"}, ...]}   and
//   {"gpio_pin":13,"status":"off"}
void handleDeviceCommand(JsonDocument &doc, const char* topic)
{
  Serial.printf("Incoming device command: %s\n", topic);
  JsonArray targets;
  bool isArray = doc["targets"].is<JsonArray>();
  if (isArray) targets = doc["targets"].as<JsonArray>();
  int count = isArray ? (int)targets.size() : 1;

  // room / device come from the topic the message actually arrived on
  char room[24], device[24];
  splitDeviceTopic(topic, room, sizeof(room), device, sizeof(device));

  Serial.println();
  Serial.println(F("+====================== DEVICE COMMAND ======================+"));
  Serial.printf ("  topic  : %s\n", topic);
  Serial.printf ("  room   : %-12s device : %s\n", room, device);
  Serial.printf ("  targets: %d\n", count);
  Serial.println(F("+----+----------+---------+--------------------------+"));
  Serial.println(F("| #  | gpio_pin | status  | action                   |"));
  Serial.println(F("+----+----------+---------+--------------------------+"));

  // Paint the command on the TFT — applyTarget() adds one row per target.
  beginDeviceCommandScreen(room, device, count);

  bool anyApplied = false;
  bool lastOn = false;

  if (isArray) {
    int idx = 1;
    for (JsonObject t : targets) {
      int         pin    = t["gpio_pin"] | -1;
      const char* status = t["status"]   | (const char*)nullptr;
      bool on = false;
      if (applyTarget(idx++, pin, status, &on)) { anyApplied = true; lastOn = on; }
    }
  } else {
    int         pin    = doc["gpio_pin"] | -1;
    const char* status = doc["status"]   | (const char*)nullptr;
    bool on = false;
    if (applyTarget(1, pin, status, &on)) { anyApplied = true; lastOn = on; }
  }

  Serial.println(F("+----+----------+---------+--------------------------+"));

  // The QR/caption follows the last pin actually driven by this command.
  // updateDoorQR() sets needsRedraw; suppress it so the command screen stays
  // up for DEVICE_SCREEN_MS, then loop() flips back to the (updated) QR.
  if (anyApplied) updateDoorQR(lastOn);
  needsRedraw = false;
  deviceScreenUntil = millis() + DEVICE_SCREEN_MS;
}

// Briefly paints the payload received on an AP-TOPIC message. Held on screen
// for DEVICE_SCREEN_MS (same mechanism as the DEVICE COMMAND screen), then
// loop() redraws the QR.
void showApTopicScreen(const char* rowId, const char* sourceType,
                       const char* course, const char* startT,
                       const char* finishT, const char* userCode)
{
  fill(COLOR_WHITE);
  drawBorder(2, 2, TFT_W - 4, TFT_H - 4, 3, COLOR_BLUE);
  drawBorder(8, 8, TFT_W - 16, TFT_H - 16, 1, COLOR_GRAY);

  const int headerH = 28;
  rect(8, 8, TFT_W - 16, headerH, COLOR_BLUE);
  int hw = textWidthPx("AP-TOPIC", 2);
  drawTextBold((TFT_W - hw) / 2, 8 + (headerH - 14) / 2, "AP-TOPIC", 2, COLOR_WHITE);

  bool active = !(sourceType[0] == '\0' || strcmp(sourceType, "non") == 0);

  int x = 22;
  int y = 8 + headerH + 14;
  char line[64];

  snprintf(line, sizeof(line), "SOURCE: %s", active ? sourceType : "NONE");
  y = drawLeftLine(x, y, line, 2, active ? COLOR_GREEN : COLOR_DGRAY);

  snprintf(line, sizeof(line), "ROWID: %s", rowId[0] ? rowId : "-");
  y = drawLeftLine(x, y, line, 2, COLOR_BLACK);

  if (course[0]) {
    snprintf(line, sizeof(line), "COURSE: %s", course);
    y = drawLeftLine(x, y, line, 2, COLOR_BLACK);
  }
  if (startT[0] || finishT[0]) {
    snprintf(line, sizeof(line), "TIME: %s-%s", startT, finishT);
    y = drawLeftLine(x, y, line, 2, COLOR_BLACK);
  }
  if (userCode[0]) {
    snprintf(line, sizeof(line), "USER: %s", userCode);
    y = drawLeftLine(x, y, line, 1, COLOR_DGRAY);
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length)
{
  Serial.printf("\n[mqtt] <- topic=%s  len=%u\n", topic, length);

  // Bound the copy — never trust length blindly
  if (length >= MQTT_BUFFER_SIZE) {
    Serial.println("Payload too large, ignoring");
    return;
  }

  char buf[MQTT_BUFFER_SIZE];
  size_t copyLen = min((size_t)length, sizeof(buf) - 1);
  memcpy(buf, payload, copyLen);
  buf[copyLen] = '\0';

  Serial.print("Raw payload: ");
  Serial.println(buf);

  // Heap-allocated so a 1 KB buffer + doc don't both sit on the loopTask stack.
  DynamicJsonDocument doc(MQTT_BUFFER_SIZE);
  DeserializationError err = deserializeJson(doc, buf);

  if (err) {
    Serial.print("JSON parse failed: ");
    Serial.println(err.c_str());
    return;
  }

  Serial.println("JSON parsed successfully");
  serializeJson(doc, Serial);


  if (strcmp(topic, DEVICE_COMMAND_TOPIC) == 0) {
    handleDeviceCommand(doc, topic);
    return;
  }
  Serial.printf("[mqtt] topic is not DEVICE_COMMAND_TOPIC (%s) -> treating as AP-TOPIC message\n",
                DEVICE_COMMAND_TOPIC);

  // Publisher sends one flat object per room topic: {"rowId": "<id>", "token": "<token>"}
  const char* rowId      = doc["rowId"]      | "";
  const char* sourceType = doc["source_type"]| "";
  snprintf(lastRowId, sizeof(lastRowId), "%s", rowId);
  snprintf(globalRowId, sizeof(globalRowId), "%s", rowId);
  Serial.println("-------------------------");

  // if (rowId == nullptr || strlen(rowId) == 0) {
  //   Serial.println("Missing/invalid rowId in payload, ignoring");
  //   return;
  // }

  // A fresh AP-TOPIC message restarts the booking cycle at "Wait-Confirm";
  // the badge only becomes "In-Use" once the door is driven open.
  doorInUse = false;
  overtimeStart = 0;
  buzzerStop();

  int written;
  if (rowId[0] == '\0') {
    // No target in the payload — show the staff-access QR, no badge.
    written = snprintf(currentToken, sizeof(currentToken), "%s", STAFF_ACCESS_URL);
    // Clear the schedule text beside the QR so stale info doesn't linger.
    displayCourseCode[0]   = '\0';
    displayStartTime[0]    = '\0';
    displayFinishTime[0]   = '\0';
    displayScheduleDate[0] = '\0';
    displayUserCode[0]     = '\0';
    bookingEndEpoch        = 0;
  } else {
    // Any message carrying a rowId -> confirm QR (QR_BASE_URL + rowId) and the
    // booking panel ("Wait-Confirm" badge until the door opens).
    written = snprintf(currentToken, sizeof(currentToken), "%s%s", QR_BASE_URL, rowId);
    // Schedule details drawn beside the QR by showQRCode().
    snprintf(displayCourseCode,   sizeof(displayCourseCode),   "%s", doc["coursecode"]    | "");
    snprintf(displayStartTime,    sizeof(displayStartTime),    "%s", doc["startTime"]     | "");
    snprintf(displayFinishTime,   sizeof(displayFinishTime),   "%s", doc["finishTime"]    | "");
    snprintf(displayScheduleDate, sizeof(displayScheduleDate), "%s", doc["schedule_date"] | "");
    snprintf(displayUserCode,     sizeof(displayUserCode),     "%s", doc["userCode"]      | "");

    // Arm the countdown module (see its header block). Prefer the real slot end
    // (schedule_date + finishTime); fall back to now + the payload's "duration"
    // seconds if those can't be parsed. 0 if neither works -> module stays idle.
    long durationSec = doc["duration"] | 0;
    time_t endE = epochFromDateTime(displayScheduleDate, displayFinishTime);
    if (endE == 0 && durationSec > 0 && timeSynced())
      endE = time(nullptr) + durationSec;
    bookingEndEpoch = endE;
    cdLastShown = -1;            // force the next drawCountdown() to paint

    Serial.printf("Schedule: course=%s time=%s-%s date=%s user=%s  duration=%lds end_epoch=%ld synced=%d\n",
                  displayCourseCode, displayStartTime, displayFinishTime,
                  displayScheduleDate, displayUserCode,
                  durationSec, (long)bookingEndEpoch, (int)timeSynced());
  }
  if (written < 0 || (size_t)written >= sizeof(currentToken)) {
    Serial.println("URL too long for currentToken buffer, ignoring");
    return;
  }

  Serial.print("New QR content set: ");
  Serial.println(currentToken);

  // Show the received AP-TOPIC payload for a few seconds, then loop() falls
  // back to redrawing the (now updated) QR.
  showApTopicScreen(rowId, sourceType,
                    displayCourseCode, displayStartTime, displayFinishTime,
                    displayUserCode);
  needsRedraw = false;
  deviceScreenUntil = millis() + DEVICE_SCREEN_MS;
}

void connectWiFi()
{
  Serial.print("Connecting to WiFi");
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.persistent(false);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  // Modem power-save adds latency and drops the occasional inbound MQTT packet —
  // keep the radio awake so subscriptions deliver promptly.
  WiFi.setSleep(false);
  Serial.println(" connected");

  Serial.println("========================================");
  Serial.print("ESP32 IP Address: ");
  Serial.println(WiFi.localIP());
  Serial.print("Gateway: ");
  Serial.println(WiFi.gatewayIP());
  Serial.print("Subnet: ");
  Serial.println(WiFi.subnetMask());
  Serial.print("MAC Address: ");
  Serial.println(WiFi.macAddress());
  Serial.println("========================================");
}

// Table of topics to (re)subscribe to on every successful connect. Add more
// entries here rather than more subscribe() calls scattered in mqttEnsureConnected().
struct MqttSubscription {
  const char* topic;
  uint8_t     qos;
};

const MqttSubscription MQTT_SUBSCRIPTIONS[] = {
  { MQTT_TOPIC,           1 },
  { DEVICE_COMMAND_TOPIC, 1 },
};
const size_t MQTT_SUBSCRIPTION_COUNT = sizeof(MQTT_SUBSCRIPTIONS) / sizeof(MQTT_SUBSCRIPTIONS[0]);

// PubSubClient rc/state -> text, so the serial log says *why* a connect failed.
const char* mqttStateStr(int s)
{
  switch (s) {
    case -4: return "TIMEOUT";
    case -3: return "CONN_LOST";
    case -2: return "CONNECT_FAILED (TCP)";
    case -1: return "DISCONNECTED";
    case  0: return "CONNECTED";
    case  1: return "BAD_PROTOCOL";
    case  2: return "BAD_CLIENT_ID";
    case  3: return "SERVER_UNAVAILABLE";
    case  4: return "BAD_CREDENTIALS";
    case  5: return "UNAUTHORIZED";
    default: return "UNKNOWN";
  }
}

// One non-blocking connect attempt. Returns true once connected + subscribed.
// loop() calls this on a timer so a down broker never freezes the display.
bool mqttEnsureConnected()
{
  if (mqttClient.connected()) return true;

  static unsigned long lastTry = 0;
  unsigned long now = millis();
  if (lastTry != 0 && (now - lastTry) < MQTT_RETRY_MS) return false;
  lastTry = now;

  if (WiFi.status() != WL_CONNECTED) return false;

  Serial.print("[mqtt] connecting to ");
  Serial.print(MQTT_HOST);
  Serial.print(":");
  Serial.print(MQTT_PORT);
  Serial.print(" ... ");

  String clientId = "esp32-qr-" + String((uint32_t)ESP.getEfuseMac(), HEX);

  // LWT: broker publishes "offline" to DEVICE_STATUS_TOPIC if this board drops.
  if (!mqttClient.connect(clientId.c_str(), nullptr, nullptr,
                          DEVICE_STATUS_TOPIC, 0, true, "offline")) {
    Serial.printf("failed, state=%d (%s)\n", mqttClient.state(),
                  mqttStateStr(mqttClient.state()));
    return false;
  }

  Serial.println("connected");
  mqttClient.publish(DEVICE_STATUS_TOPIC, "online", true);

  bool allOk = true;
  for (size_t i = 0; i < MQTT_SUBSCRIPTION_COUNT; i++) {
    bool ok = mqttClient.subscribe(MQTT_SUBSCRIPTIONS[i].topic, MQTT_SUBSCRIPTIONS[i].qos);
    Serial.printf("[mqtt] subscribe %-24s %s\n",
                  MQTT_SUBSCRIPTIONS[i].topic, ok ? "OK" : "FAILED");
    if (!ok) allOk = false;
  }

  // A half-subscribed session would silently miss messages — drop it and let
  // the next attempt start clean.
  if (!allOk) {
    Serial.println("[mqtt] subscribe incomplete, forcing reconnect");
    mqttClient.disconnect();
    return false;
  }
  return true;
}

void setup()
{
  Serial.begin(115200);

  pinMode(TFT_CS, OUTPUT);
  pinMode(TFT_DC, OUTPUT);
  pinMode(TFT_RST, OUTPUT);
  pinMode(TFT_BL, OUTPUT);

  digitalWrite(TFT_CS, HIGH);
  digitalWrite(TFT_BL, HIGH);

#if BUZZER_PIN >= 0
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);
#endif

  SPI.begin(TFT_SCLK, TFT_MISO, TFT_MOSI, TFT_CS);
  SPI.beginTransaction(SPISettings(16000000, MSBFIRST, SPI_MODE0));

  ili9341Init();
  drawQRCode(); // shows sample QR code initially
  Serial.println("Sample QR shown");

  connectWiFi();

  // Start NTP — powers the booking countdown. Non-blocking; time() becomes valid
  // a few seconds after the first server reply.
  configTzTime(TZ_INFO, NTP_SERVER1, NTP_SERVER2);

  mqttClient.setServer(MQTT_HOST, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);
  mqttClient.setKeepAlive(MQTT_KEEPALIVE_S);
  mqttClient.setSocketTimeout(MQTT_SOCKET_TMO_S);

  bool bufOk = mqttClient.setBufferSize(MQTT_BUFFER_SIZE); // default 256 is too small for JSON + topic
  Serial.printf("[mqtt] buffer=%d (%s), keepalive=%ds\n",
                MQTT_BUFFER_SIZE, bufOk ? "ok" : "ALLOC FAILED", MQTT_KEEPALIVE_S);

  mqttEnsureConnected();
}

void loop()
{
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[wifi] link down, reconnecting");
    connectWiFi();
  }

  // Non-blocking: attempts a reconnect at most every MQTT_RETRY_MS.
  static bool wasConnected = false;
  bool nowConnected = mqttEnsureConnected();
  if (nowConnected != wasConnected) {
    Serial.printf("[mqtt] link %s\n", nowConnected ? "UP (subscribed)" : "DOWN");
    wasConnected = nowConnected;
  }

  mqttClient.loop();

  // The DEVICE COMMAND screen holds for DEVICE_SCREEN_MS, then we fall back to
  // the QR (which handleDeviceCommand already updated via updateDoorQR).
  if (deviceScreenUntil != 0 && (long)(millis() - deviceScreenUntil) >= 0) {
    deviceScreenUntil = 0;
    needsRedraw = true;
  }

  if (needsRedraw) {
    //Serial.print("Redraw Test.");
    needsRedraw = false;
    drawQRCode();
    Serial.println("QR redrawn");
  }

  // ---- booking countdown (see the BOOKING COUNTDOWN MODULE block above) ----
  // cdSecs: seconds left, or -1 when there is no live countdown (idle, clock not
  // synced, or a DEVICE COMMAND / AP-TOPIC splash is currently on screen).
  long cdSecs = (bookingEndEpoch != 0 && deviceScreenUntil == 0)
                  ? countdownRemaining() : -1;

  updateBuzzer(cdSecs);          // audible alert — runs every loop, self-paced

  // Visual: repaint just the timer line ~1 Hz (no full redraw).
  static unsigned long lastCdTick = 0;
  if (cdSecs >= 0 && !needsRedraw && cdY >= 0 &&
      millis() - lastCdTick >= 1000) {
    lastCdTick = millis();
    if (cdSecs != cdLastShown || cdSecs == 0) {   // value at 0 is static but must keep blinking
      cdLastShown = cdSecs;
      drawCountdown();
    }
  }

  // Countdown hit 0 -> hold on the blinking "TIME UP" alarm for a while
  // (buzzer keeps pulsing via updateBuzzer(0)), then reset to SCAN ME.
  if (cdSecs == 0) {
    if (overtimeStart == 0) {
      overtimeStart = millis();
      Serial.println("[countdown] TIME UP");
    } else if (millis() - overtimeStart >= COUNTDOWN_END_ALARM_MS) {
      Serial.println("[countdown] alarm done -> reset");
      overtimeStart = 0;
      buzzerStop();
      updateDoorQR(false);       // clears fields + bookingEndEpoch, forces redraw
    }
  }

  // Periodic IP/MQTT status reminder on Serial (non-blocking)
  if (millis() - lastIpPrint >= IP_PRINT_INTERVAL) {
    lastIpPrint = millis();
    Serial.printf("[status] IP:%s RSSI:%ddBm  MQTT:%s (state=%d)  topics: %s , %s\n",
                  WiFi.localIP().toString().c_str(), WiFi.RSSI(),
                  mqttClient.connected() ? "connected" : "DISCONNECTED",
                  mqttClient.state(), MQTT_TOPIC, DEVICE_COMMAND_TOPIC);
  }
}
