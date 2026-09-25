"""
command_light_control.py

GPIO relay controller for a single light channel.
Import and call light_on() / light_off() from any service.

Usage:
    from command_light_control import light_on, light_off, cleanup
"""

import atexit
import signal
import sys
import time

try:
    import lgpio  # type: ignore
    _HAS_GPIO = True
except ImportError:
    _HAS_GPIO = False

# ---------------------------------------------------------------------------
# Pin config  (edit here or pass overrides at init time)
# ---------------------------------------------------------------------------
PIN       = 13   # BCM GPIO13 → physical pin 33
LEVEL_ON  = 0    # active-low: relay closes → light ON
LEVEL_OFF = 1    # relay opens → light OFF

_h: int      = -1     # chip handle; -1 = not opened
_ready: bool = False  # True once pin is successfully claimed


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _open_chip() -> int:
    if not _HAS_GPIO:
        return -1
    return lgpio.gpiochip_open(0)


def _claim(h: int, pin: int, retries: int = 3, delay: float = 0.2) -> None:
    """Claim pin as output, retrying on GPIO-busy errors."""
    global _ready
    _ready = False
    for attempt in range(retries):
        try:
            lgpio.gpio_free(h, pin)
        except Exception:
            pass
        try:
            lgpio.gpio_claim_output(h, pin, LEVEL_OFF)
            _ready = True
            return
        except Exception as exc:
            if attempt == retries - 1:
                lgpio.gpiochip_close(h)
                raise RuntimeError(
                    f"GPIO{pin} busy after {retries} attempts: {exc}"
                ) from exc
            time.sleep(delay)


def _write(level: int) -> bool:
    global _h, _ready
    if not _HAS_GPIO:
        print(f"[stub] GPIO{PIN} → {'ON' if level == LEVEL_ON else 'OFF'}")
        return True
    if not _ready or _h < 0:
        try:
            _h = _open_chip()
            _claim(_h, PIN)
        except RuntimeError as exc:
            print(f"[error] GPIO init failed: {exc}")
            return False
    try:
        lgpio.gpio_write(_h, PIN, level)
        return True
    except Exception as exc:
        print(f"[error] gpio_write failed: {exc} — re-initialising")
        _ready = False
        try:
            _h = _open_chip()
            _claim(_h, PIN)
            lgpio.gpio_write(_h, PIN, level)
            return True
        except Exception as exc2:
            print(f"[error] gpio_write failed after re-init: {exc2}")
            return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def init(pin: int = PIN) -> None:
    """Explicitly open chip and claim pin (optional — auto-called on first use)."""
    global _h, PIN
    PIN = pin
    if not _HAS_GPIO:
        print("[stub] lgpio not available — running in stub mode")
        return
    _h = _open_chip()
    _claim(_h, PIN)
    print(f"[gpio] initialised GPIO{PIN}")


def setPin(pin: int) -> None:
    """Switch to a different GPIO pin, releasing the previous one first."""
    global PIN, _ready
    if pin == PIN and _ready:
        return
    if _HAS_GPIO and _h >= 0:
        try:
            lgpio.gpio_write(_h, PIN, LEVEL_OFF)
            lgpio.gpio_free(_h, PIN)
        except Exception:
            pass
    _ready = False
    PIN = pin
    if _HAS_GPIO:
        _claim(_h, PIN)
    print(f"[gpio] pin switched → GPIO{PIN}")


def light_on() -> bool:
    ok = _write(LEVEL_ON)
    print(f"[gpio] GPIO{PIN} → ON  (relay closed)" if ok else f"[gpio] GPIO{PIN} ON failed — busy or unavailable")
    return ok


def light_off() -> bool:
    ok = _write(LEVEL_OFF)
    print(f"[gpio] GPIO{PIN} → OFF (relay open)" if ok else f"[gpio] GPIO{PIN} OFF failed — busy or unavailable")
    return ok


def cleanup() -> None:
    """Turn off relay and release GPIO resources."""
    global _h
    if not _HAS_GPIO or _h < 0:
        return
    try:
        lgpio.gpio_write(_h, PIN, LEVEL_OFF)
        lgpio.gpio_free(_h, PIN)
        lgpio.gpiochip_close(_h)
        print(f"[gpio] GPIO{PIN} released")
    except Exception as exc:
        print(f"[gpio] cleanup error: {exc}")
    finally:
        _h = -1


# ---------------------------------------------------------------------------
# Auto-cleanup on exit / signals
# ---------------------------------------------------------------------------
atexit.register(cleanup)

def _signal_handler(*_):
    cleanup()
    sys.exit(0)

signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT,  _signal_handler)
