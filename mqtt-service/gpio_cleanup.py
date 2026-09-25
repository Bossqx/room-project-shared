# gpio_cleanup.py
import lgpio

PINS = [17, 27, 13]

h = lgpio.gpiochip_open(0)
for pin in PINS:
    try:
        lgpio.gpio_free(h, pin)
        print(f"[ok] GPIO{pin} freed")
    except Exception as e:
        print(f"[skip] GPIO{pin}: {e}")
lgpio.gpiochip_close(h)
print("[done]")