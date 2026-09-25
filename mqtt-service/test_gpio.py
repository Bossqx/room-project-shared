#!/usr/bin/env python3
"""
test_gpio_1.py

GPIO test script for light + door relays — Raspberry Pi 5 compatible.

RPi.GPIO does NOT work on Pi 5 (it accesses the BCM SoC directly; Pi 5
moved GPIO to the separate RP1 chip, causing "Cannot determine SOC
peripheral base address"). This version uses `lgpio`, which talks to
the kernel gpiochip interface and works on Pi 5 (and earlier Pi models).

Install:
    pip install lgpio --break-system-packages

Pin map (BCM numbering):
  GPIO17 (physical pin 11) → LIGHT relay
  GPIO27 (physical pin 13) → DOOR  relay
"""

import logging
import sys
import time

try:
    import lgpio
    ON_PI = True
except ImportError:
    ON_PI = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("gpio_test")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PIN_LIGHT = 13
PIN_DOOR  = 27

RELAY_ACTIVE_HIGH = True   # set False if your relay module is active-low
DOOR_UNLOCK_SEC   = 5

_ON  = 1 if RELAY_ACTIVE_HIGH else 0
_OFF = 0 if RELAY_ACTIVE_HIGH else 1

_chip = None   # lgpio chip handle, set in setup()


# ---------------------------------------------------------------------------
# GPIO bootstrap
# ---------------------------------------------------------------------------
def setup():
    global _chip
    if not ON_PI:
        log.warning("lgpio not found — outputs will be simulated (stdout only)")
        return
    try:
        _chip = lgpio.gpiochip_open(0)
        lgpio.gpio_claim_output(_chip, PIN_LIGHT, _OFF)
        lgpio.gpio_claim_output(_chip, PIN_DOOR,  _OFF)
        log.info("GPIO ready — LIGHT=GPIO%d  DOOR=GPIO%d", PIN_LIGHT, PIN_DOOR)
    except Exception as exc:
        log.error("GPIO setup failed: %s", exc)
        sys.exit(1)


def cleanup():
    if ON_PI and _chip is not None:
        try:
            lgpio.gpiochip_close(_chip)
            log.info("GPIO cleaned up")
        except Exception as exc:
            log.warning("GPIO cleanup error: %s", exc)


def write(pin: int, level: int, label: str):
    state = "ON" if level == _ON else "OFF"
    if ON_PI:
        lgpio.gpio_write(_chip, pin, level)
    log.info("  GPIO%-2d  %-12s -> %s", pin, label, state)


# ---------------------------------------------------------------------------
# Individual tests
# ---------------------------------------------------------------------------
def test_light():
    log.info("-- LIGHT relay test --------------------")
    write(PIN_LIGHT, _ON,  "LIGHT")
    log.info("  light ON  (check relay LED / connected load)")
    time.sleep(2)
    write(PIN_LIGHT, _OFF, "LIGHT")
    log.info("  light OFF")
    time.sleep(1)
    log.info("  PASS")


def test_door_auto_relock():
    log.info("-- DOOR unlock -> auto-relock (%ds) -----", DOOR_UNLOCK_SEC)
    write(PIN_DOOR, _ON,  "DOOR")
    log.info("  door UNLOCKED — will auto-relock in %d s", DOOR_UNLOCK_SEC)
    time.sleep(DOOR_UNLOCK_SEC)
    write(PIN_DOOR, _OFF, "DOOR")
    log.info("  door LOCKED (auto)")
    time.sleep(1)
    log.info("  PASS")


def test_door_hold():
    log.info("-- DOOR unlock-hold -> manual lock ------")
    write(PIN_DOOR, _ON,  "DOOR")
    log.info("  door UNLOCKED (hold) — waiting 3 s ...")
    time.sleep(3)
    write(PIN_DOOR, _OFF, "DOOR")
    log.info("  door LOCKED (manual)")
    time.sleep(1)
    log.info("  PASS")


def test_blink_light(count: int = 3):
    log.info("-- LIGHT blink x %d ----------------------", count)
    for _ in range(count):
        write(PIN_LIGHT, _ON,  "LIGHT")
        time.sleep(0.4)
        write(PIN_LIGHT, _OFF, "LIGHT")
        time.sleep(0.4)
    log.info("  PASS")


def run_all():
    log.info("=== Running all GPIO tests ================")
    test_blink_light()
    test_light()
    test_door_auto_relock()
    test_door_hold()
    log.info("=== All tests complete =====================")


if __name__ == "__main__":
    setup()
    try:
        run_all()
    finally:
        cleanup()