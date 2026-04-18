"""
Whisplay HAT integration plugin for Pwnagotchi.

Handles:
- GPIO backlight control (BCM 22 / BOARD 15, active LOW) with optional PWM dimming
- ALSA volume and WAV playback via WM8960 sound card for boot and handshake chimes
- Pwnagotchi UI hooks for a simple handshake counter
"""

import logging
import os
import subprocess
import threading

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK

log = logging.getLogger(__name__)

PLUGIN_DIR = os.path.dirname(os.path.realpath(__file__))
DEFAULT_CHIME_FILE = os.path.join(PLUGIN_DIR, "whisplay_chime.wav")
DEFAULT_BOOT_SOUND = os.path.join(PLUGIN_DIR, "whisplay_boot.wav")

# BCM 22 = BOARD pin 15 = Whisplay HAT LED/backlight (active LOW)
DEFAULT_BACKLIGHT_PIN = 22
DEFAULT_VOLUME = 60
DEFAULT_PWM_FREQUENCY = 1000
DEFAULT_ACTIVE_BRIGHTNESS = 100
DEFAULT_IDLE_BRIGHTNESS = 35
DEFAULT_SLEEP_BRIGHTNESS = 10
DEFAULT_ALSA_DEVICE = "hw:wm8960soundcard"
DEFAULT_ALSA_CONTROL = "Speaker"
DEFAULT_UI_POSITION = (0, 92)


def _coerce_int(value, fallback):
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _coerce_percent(value, fallback):
    return max(0, min(100, _coerce_int(value, fallback)))


def _coerce_bool(value, fallback=False):
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in ("1", "true", "yes", "on"):
            return True
        if normalized in ("0", "false", "no", "off"):
            return False
    return fallback


def _set_volume(percent, device=DEFAULT_ALSA_DEVICE, control=DEFAULT_ALSA_CONTROL):
    try:
        subprocess.run(
            ["amixer", "-D", device, "-q", "sset", control,
             f"{_coerce_percent(percent, DEFAULT_VOLUME)}%"],
            check=True,
            timeout=5,
        )
    except Exception as exc:
        log.warning("[whisplay] volume set failed (device=%s control=%s): %s", device, control, exc)


def _play_sound(path):
    """Play a WAV file in a background thread."""
    if not path or not os.path.exists(path):
        log.debug("[whisplay] sound file not found: %s", path)
        return

    def _play():
        try:
            subprocess.run(["aplay", "-q", path], timeout=10)
        except Exception as exc:
            log.warning("[whisplay] aplay error: %s", exc)

    threading.Thread(target=_play, daemon=True).start()


class WhisplayDisplay(plugins.Plugin):
    __author__ = "mobile-rpi"
    __version__ = "1.2.0"
    __license__ = "MIT"
    __description__ = (
        "Whisplay HAT backlight, audio, and lightweight UI integration for pwnagotchi."
    )

    def __init__(self):
        self._gpio = None
        self._backlight_pwm = None
        self._backlight_pin = DEFAULT_BACKLIGHT_PIN
        self._boot_volume = DEFAULT_VOLUME
        self._pwm_frequency = DEFAULT_PWM_FREQUENCY
        self._active_brightness = DEFAULT_ACTIVE_BRIGHTNESS
        self._idle_brightness = DEFAULT_IDLE_BRIGHTNESS
        self._sleep_brightness = DEFAULT_SLEEP_BRIGHTNESS
        self._alsa_device = DEFAULT_ALSA_DEVICE
        self._alsa_control = DEFAULT_ALSA_CONTROL
        self._boot_sound = DEFAULT_BOOT_SOUND
        self._handshake_sound = DEFAULT_CHIME_FILE
        self._boot_chime = True
        self._handshake_chime = True
        self._session_handshakes = 0
        self._handshake_lock = threading.Lock()

    def _init_backlight(self):
        try:
            import RPi.GPIO as GPIO
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self._backlight_pin, GPIO.OUT)
            # Backlight is active LOW — drive HIGH to ensure it starts off
            # until _set_backlight is called with actual brightness
            GPIO.output(self._backlight_pin, GPIO.HIGH)
            self._gpio = GPIO

            try:
                self._backlight_pwm = GPIO.PWM(self._backlight_pin, self._pwm_frequency)
                # Active LOW: start at 100% duty (fully HIGH = backlight off)
                # _set_backlight will immediately set the correct duty
                self._backlight_pwm.start(100)
                log.info(
                    "[whisplay] backlight PWM on GPIO %s at %s Hz (active LOW)",
                    self._backlight_pin,
                    self._pwm_frequency,
                )
            except Exception as exc:
                self._backlight_pwm = None
                log.debug("[whisplay] PWM unavailable, falling back to on/off: %s", exc)
        except Exception as exc:
            self._gpio = None
            self._backlight_pwm = None
            log.warning("[whisplay] backlight init failed: %s", exc)

    def _set_backlight(self, brightness):
        """Set backlight brightness 0-100. Pin is active LOW."""
        brightness = _coerce_percent(brightness, DEFAULT_ACTIVE_BRIGHTNESS)

        if self._gpio is None:
            return

        try:
            if self._backlight_pwm is not None:
                # Active LOW: invert duty cycle
                self._backlight_pwm.ChangeDutyCycle(100 - brightness)
            else:
                # Active LOW: LOW = on, HIGH = off
                self._gpio.output(
                    self._backlight_pin,
                    self._gpio.LOW if brightness > 0 else self._gpio.HIGH,
                )
        except Exception as exc:
            log.warning("[whisplay] backlight update failed: %s", exc)

    def _shutdown_backlight(self):
        if self._gpio is None:
            return
        try:
            if self._backlight_pwm is not None:
                self._backlight_pwm.ChangeDutyCycle(100)  # active LOW: full HIGH = off
                self._backlight_pwm.stop()
            self._gpio.output(self._backlight_pin, self._gpio.HIGH)  # active LOW: HIGH = off
            self._gpio.cleanup(self._backlight_pin)
        except Exception as exc:
            log.debug("[whisplay] backlight shutdown issue: %s", exc)
        finally:
            self._backlight_pwm = None
            self._gpio = None

    def on_loaded(self):
        log.info("[whisplay] plugin loaded")

        self._backlight_pin = _coerce_int(
            self.options.get("backlight_pin", DEFAULT_BACKLIGHT_PIN),
            DEFAULT_BACKLIGHT_PIN,
        )
        self._boot_volume = _coerce_percent(
            self.options.get("boot_volume", DEFAULT_VOLUME),
            DEFAULT_VOLUME,
        )
        self._pwm_frequency = _coerce_int(
            self.options.get("pwm_frequency", DEFAULT_PWM_FREQUENCY),
            DEFAULT_PWM_FREQUENCY,
        )
        self._active_brightness = _coerce_percent(
            self.options.get("active_brightness", DEFAULT_ACTIVE_BRIGHTNESS),
            DEFAULT_ACTIVE_BRIGHTNESS,
        )
        self._idle_brightness = _coerce_percent(
            self.options.get("idle_brightness", DEFAULT_IDLE_BRIGHTNESS),
            DEFAULT_IDLE_BRIGHTNESS,
        )
        self._sleep_brightness = _coerce_percent(
            self.options.get("sleep_brightness", DEFAULT_SLEEP_BRIGHTNESS),
            DEFAULT_SLEEP_BRIGHTNESS,
        )
        self._alsa_device = self.options.get("alsa_device", DEFAULT_ALSA_DEVICE)
        self._alsa_control = self.options.get("alsa_control", DEFAULT_ALSA_CONTROL)
        self._boot_chime = _coerce_bool(self.options.get("boot_chime", True), True)
        self._handshake_chime = _coerce_bool(self.options.get("handshake_chime", True), True)
        self._boot_sound = self.options.get("boot_sound_file", DEFAULT_BOOT_SOUND)
        self._handshake_sound = self.options.get("handshake_sound_file", DEFAULT_CHIME_FILE)
        self._session_handshakes = 0

        self._init_backlight()
        self._set_backlight(self._active_brightness)
        _set_volume(self._boot_volume, self._alsa_device, self._alsa_control)

        if self._boot_chime:
            _play_sound(self._boot_sound)

    def on_unloaded(self):
        log.info("[whisplay] plugin unloaded")
        self._shutdown_backlight()

    def on_ui_setup(self, ui):
        try:
            x = _coerce_int(self.options.get("ui_position_x", DEFAULT_UI_POSITION[0]), DEFAULT_UI_POSITION[0])
            y = _coerce_int(self.options.get("ui_position_y", DEFAULT_UI_POSITION[1]), DEFAULT_UI_POSITION[1])
            ui.add_element(
                "whisplay_status",
                LabeledValue(
                    color=BLACK,
                    label="HAT",
                    value="HS:0",
                    position=(x, y),
                    label_font=fonts.Bold,
                    text_font=fonts.Medium,
                ),
            )
        except Exception as exc:
            log.debug("[whisplay] ui_setup error: %s", exc)

    def on_ui_update(self, ui):
        try:
            with self._handshake_lock:
                count = self._session_handshakes
            ui.set("whisplay_status", f"HS:{count}")
        except Exception:
            pass

    def on_ready(self, agent):
        log.info("[whisplay] pwnagotchi ready")
        self._set_backlight(self._active_brightness)

    def on_handshake(self, agent, filename, access_point, client_station):
        with self._handshake_lock:
            self._session_handshakes += 1
            count = self._session_handshakes

        essid = access_point.get("essid", "?") if access_point else "?"
        bssid = access_point.get("bssid", "?") if access_point else "?"
        log.info("[whisplay] handshake #%s: %s (%s)", count, essid, bssid)

        if self._handshake_chime:
            _play_sound(self._handshake_sound)

    def on_epoch(self, agent, epoch, epoch_data):
        # reward > 0 indicates the AI is actively scanning/associating
        active = False
        if epoch_data:
            active = _coerce_int(epoch_data.get("reward", 0), 0) > 0
        self._set_backlight(self._active_brightness if active else self._idle_brightness)

    def on_sleep(self, agent):
        log.info("[whisplay] pwnagotchi sleeping")
        self._set_backlight(self._sleep_brightness)

    def on_wake(self, agent):
        log.info("[whisplay] pwnagotchi waking")
        self._set_backlight(self._active_brightness)

    def on_internet_available(self, agent):
        log.info("[whisplay] internet available")

    def on_association(self, agent, access_point):
        essid = access_point.get("essid", "?") if access_point else "?"
        log.debug("[whisplay] associated with %s", essid)

    def on_deauthentication(self, agent, access_point, client_station):
        essid = access_point.get("essid", "?") if access_point else "?"
        client_mac = client_station.get("mac", "?") if client_station else "?"
        log.debug("[whisplay] deauth - AP: %s client: %s", essid, client_mac)
