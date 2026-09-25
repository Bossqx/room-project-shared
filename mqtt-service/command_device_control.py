"""
command_light_control.py

GPIO relay controller for a single light channel.
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


class command_device:
    LEVEL_ON  = 0  # active-low: relay closes → light ON
    LEVEL_OFF = 1  # relay opens → light OFF

    def __init__(self, pin: int = 13):
        self._pin: int  = pin
        self._h: int    = -1
        self._ready: bool = False

        if not _HAS_GPIO:
            print("[stub] lgpio not available — running in stub mode")
            return

        self._h = lgpio.gpiochip_open(0)
        self._claim(self._pin)
        print(f"[gpio] initialised GPIO{self._pin}")

        atexit.register(self.cleanup)
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT,  self._signal_handler)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_pin(self, pin: int) -> None:
        """Switch to a different GPIO pin, releasing the previous one first."""
        if pin == self._pin and self._ready:
            return
        if _HAS_GPIO and self._h >= 0:
            try:
                lgpio.gpio_write(self._h, self._pin, self.LEVEL_OFF)
                lgpio.gpio_free(self._h, self._pin)
            except Exception:
                pass
        self._ready = False
        self._pin = pin
        if _HAS_GPIO:
            self._claim(self._pin)
        print(f"[gpio] pin switched → GPIO{self._pin}")

    def light_on(self) -> bool:
        ok = self._write(self.LEVEL_ON)
        print(f"[gpio] GPIO{self._pin} → ON  (relay closed)" if ok else f"[gpio] GPIO{self._pin} ON failed")
        return ok

    def light_off(self) -> bool:
        ok = self._write(self.LEVEL_OFF)
        print(f"[gpio] GPIO{self._pin} → OFF (relay open)" if ok else f"[gpio] GPIO{self._pin} OFF failed")
        return ok

    def cleanup(self) -> None:
        """Turn off relay and release GPIO resources."""
        if not _HAS_GPIO or self._h < 0:
            return
        try:
            lgpio.gpio_write(self._h, self._pin, self.LEVEL_OFF)
            lgpio.gpio_free(self._h, self._pin)
            lgpio.gpiochip_close(self._h)
            print(f"[gpio] GPIO{self._pin} released")
        except Exception as exc:
            print(f"[gpio] cleanup error: {exc}")
        finally:
            self._h = -1

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _claim(self, pin: int, retries: int = 3, delay: float = 0.2) -> None:
        self._ready = False
        for attempt in range(retries):
            try:
                lgpio.gpio_free(self._h, pin)
            except Exception:
                pass
            try:
                lgpio.gpio_claim_output(self._h, pin, self.LEVEL_OFF)
                self._ready = True
                return
            except Exception as exc:
                if attempt == retries - 1:
                    lgpio.gpiochip_close(self._h)
                    raise RuntimeError(
                        f"GPIO{pin} busy after {retries} attempts: {exc}"
                    ) from exc
                time.sleep(delay)

    def _write(self, level: int) -> bool:
        if not _HAS_GPIO:
            print(f"[stub] GPIO{self._pin} → {'ON' if level == self.LEVEL_ON else 'OFF'}")
            return True
        if not self._ready or self._h < 0:
            try:
                self._h = lgpio.gpiochip_open(0)
                self._claim(self._pin)
            except RuntimeError as exc:
                print(f"[error] GPIO init failed: {exc}")
                return False
        try:
            lgpio.gpio_write(self._h, self._pin, level)
            return True
        except Exception as exc:
            print(f"[error] gpio_write failed: {exc} — re-initialising")
            self._ready = False
            try:
                self._h = lgpio.gpiochip_open(0)
                self._claim(self._pin)
                lgpio.gpio_write(self._h, self._pin, level)
                return True
            except Exception as exc2:
                print(f"[error] gpio_write failed after re-init: {exc2}")
                return False

    def _signal_handler(self, *_):
        self.cleanup()
        sys.exit(0)
