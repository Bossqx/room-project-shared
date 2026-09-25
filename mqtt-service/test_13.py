#!/usr/bin/env python3
"""
trigger_gpio13.py

Triggers BCM GPIO13 (physical pin 33) HIGH/LOW using lgpio.
Compatible with Raspberry Pi 5 (RP1 chip) -- RPi.GPIO does NOT work on Pi 5.

Install first:
    pip install lgpio --break-system-packages

Run:
    python3 trigger_gpio13.py
"""

import lgpio
import time

PIN = 13   # BCM numbering -> physical pin 33

h = lgpio.gpiochip_open(0)
lgpio.gpio_claim_output(h, PIN, 0)   # claim as output, initial LOW

try:
    print(f"GPIO{PIN} -> HIGH")
    lgpio.gpio_write(h, PIN, 1)
    time.sleep(3)

    print(f"GPIO{PIN} -> LOW")
    lgpio.gpio_write(h, PIN, 0)
    time.sleep(1)

    print("Done.")
finally:
    lgpio.gpiochip_close(h)