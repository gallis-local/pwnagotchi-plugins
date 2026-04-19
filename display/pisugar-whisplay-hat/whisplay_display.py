"""whisplay_display.py — Whisplay HAT hardware plugin for pwnagotchi

Manages:
  · RGB status LED   — colour tracks pwnagotchi AI state
  · Tactile button   — short press = ack flash / long press = audio test
  · I2S audio        — boot chime + handshake sound via WM8960

Pin assignments (BCM) from the WhisPlay HAT schematic (BOARD → BCM):
  RGB Red   BOARD 22 → BCM 25
  RGB Green BOARD 18 → BCM 24
  RGB Blue  BOARD 16 → BCM 23
  Button    BOARD 11 → BCM 17   pressed = HIGH, external pull-down on HAT

NOTE: GPIO.cleanup() is deliberately NOT called on unload — the display
driver (whisplay_hat.py) holds BCM 22 (backlight) LOW to keep the screen
on.  Cleaning up would float that pin HIGH and kill the backlight.
"""
import logging
import os
import subprocess
import threading
import time

import pwnagotchi.plugins as plugins

log = logging.getLogger(__name__)

# ── Hardware pin assignments (BCM) ────────────────────────────────────────────
# Sourced from WhisPlay.py (BOARD mode) → converted to BCM for our driver
_PIN_RED    = 25   # BOARD 22
_PIN_GREEN  = 24   # BOARD 18
_PIN_BLUE   = 23   # BOARD 16
_PIN_BUTTON = 17   # BOARD 11 — pressed = HIGH, external pull-down

# ── AI state → (R, G, B) 0-255 ───────────────────────────────────────────────
_STATE_COLORS = {
    'ready':    (0,   180, 0  ),   # green
    'bored':    (180, 120, 0  ),   # amber
    'sad':      (0,   0,   200),   # blue
    'excited':  (0,   200, 200),   # cyan
    'lonely':   (200, 80,  0  ),   # orange
    'sleeping': (15,  15,  15 ),   # dim white
    'resting':  (15,  15,  15 ),   # dim white
}

_LONG_PRESS_S = 2.0   # seconds held to trigger long-press action


# ── Software PWM ──────────────────────────────────────────────────────────────

class _SoftPWM:
    """Active-LOW software PWM for a single GPIO pin.

    duty_cycle   0  → always LOW  = full brightness (LED fully on)
    duty_cycle 100  → always HIGH = LED off
    """

    def __init__(self, gpio, pin, frequency=100):
        self._gpio = gpio
        self._pin  = pin
        self._freq = frequency
        self.duty_cycle = 100.0   # start off
        self._running   = False
        self._thread    = None

    def start(self):
        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1)
        try:
            self._gpio.output(self._pin, self._gpio.HIGH)   # ensure off
        except Exception:
            pass

    def _loop(self):
        while self._running:
            period = 1.0 / self._freq
            dc = max(0.0, min(100.0, self.duty_cycle))
            if dc <= 0:
                self._gpio.output(self._pin, self._gpio.LOW)
                time.sleep(period)
            elif dc >= 100:
                self._gpio.output(self._pin, self._gpio.HIGH)
                time.sleep(period)
            else:
                high_t = period * dc / 100.0
                low_t  = period - high_t
                self._gpio.output(self._pin, self._gpio.HIGH)
                time.sleep(high_t)
                self._gpio.output(self._pin, self._gpio.LOW)
                time.sleep(low_t)


def _rgb_duty(value: int) -> float:
    """Convert 0-255 colour channel to active-LOW duty cycle (0–100 %)."""
    return 100.0 - (value / 255.0 * 100.0)


# ── Plugin ────────────────────────────────────────────────────────────────────

class WhisplayDisplay(plugins.Plugin):
    __author__      = 'gallis-local'
    __version__     = '2.0.0'
    __license__     = 'GPL3'
    __description__ = (
        'Whisplay HAT — RGB status LED, tactile button, and I2S audio (WM8960)'
    )

    def __init__(self):
        super().__init__()
        self._gpio           = None
        self._red_pwm        = None
        self._green_pwm      = None
        self._blue_pwm       = None
        self._current_color  = (0, 0, 0)
        self._agent          = None
        self._btn_press_time = None          # monotonic time of the last press edge
        self._btn_thread_running = False

    # ── Plugin lifecycle ──────────────────────────────────────────────────────

    def on_loaded(self):
        log.info('[whisplay] plugin loaded — initialising RGB LED and button')
        try:
            import RPi.GPIO as GPIO

            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)

            # RGB LED pins: initialise HIGH (active-LOW → all channels off)
            GPIO.setup(
                [_PIN_RED, _PIN_GREEN, _PIN_BLUE],
                GPIO.OUT,
                initial=GPIO.HIGH,
            )

            # Button: HAT has an external pull-down resistor — no internal pull
            GPIO.setup(_PIN_BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_OFF)

            # Assign _gpio BEFORE starting the poll thread so it never sees None
            self._gpio = GPIO

            self._red_pwm   = _SoftPWM(GPIO, _PIN_RED)
            self._green_pwm = _SoftPWM(GPIO, _PIN_GREEN)
            self._blue_pwm  = _SoftPWM(GPIO, _PIN_BLUE)

            self._red_pwm.start()
            self._green_pwm.start()
            self._blue_pwm.start()

            # Start button poll thread after GPIO is fully set up
            self._btn_thread_running = True
            threading.Thread(target=self._button_poll, daemon=True).start()

            log.info(
                '[whisplay] GPIO ready  RGB BCM %d/%d/%d  button BCM %d',
                _PIN_RED, _PIN_GREEN, _PIN_BLUE, _PIN_BUTTON,
            )
        except Exception:
            log.exception('[whisplay] GPIO init failed — LED/button unavailable')

    def on_ready(self, agent):
        self._agent = agent
        self._set_state_color('ready')
        self._play_sound('whisplay_boot.wav')

    def on_unload(self, ui):
        log.info('[whisplay] unloading — stopping PWM and button poll thread')
        self._btn_thread_running = False
        for pwm in (self._red_pwm, self._green_pwm, self._blue_pwm):
            try:
                if pwm:
                    pwm.stop()
            except Exception:
                pass
        try:
            if self._gpio:
                # Do NOT call GPIO.cleanup() — see module docstring.
                pass
        except Exception:
            log.exception('[whisplay] cleanup error')

    # ── AI state hooks ────────────────────────────────────────────────────────

    def on_bored(self, agent):
        self._agent = agent
        self._set_state_color('bored')

    def on_sad(self, agent):
        self._agent = agent
        self._set_state_color('sad')

    def on_excited(self, agent):
        self._agent = agent
        self._set_state_color('excited')

    def on_lonely(self, agent):
        self._agent = agent
        self._set_state_color('lonely')

    def on_resting(self, agent):
        self._agent = agent
        self._set_state_color('resting')

    def on_sleeping(self, agent, secs):
        self._agent = agent
        self._set_state_color('sleeping')

    # ── Handshake ─────────────────────────────────────────────────────────────

    def on_peer_detected(self, agent, peer):
        self._agent = agent
        threading.Thread(target=self._peer_flash, daemon=True).start()

    def on_association(self, agent, ap):
        self._agent = agent
        threading.Thread(target=self._association_flash, daemon=True).start()

    def on_wifi_update(self, agent, access_points):
        self._agent = agent
        threading.Thread(target=self._scan_pulse, daemon=True).start()

    def on_handshake(self, agent, filename, access_point, client_station):
        self._agent = agent
        threading.Thread(target=self._handshake_flash, daemon=True).start()
        if self.options.get('handshake_chime', True):
            self._play_sound('whisplay_chime.wav')

    # ── Colour helpers ────────────────────────────────────────────────────────

    def _set_state_color(self, state: str):
        self._set_color(*_STATE_COLORS.get(state, (0, 180, 0)))

    def _set_color(self, r: int, g: int, b: int):
        self._current_color = (r, g, b)
        if not (self._red_pwm and self._green_pwm and self._blue_pwm):
            return
        try:
            self._red_pwm.duty_cycle   = _rgb_duty(r)
            self._green_pwm.duty_cycle = _rgb_duty(g)
            self._blue_pwm.duty_cycle  = _rgb_duty(b)
        except Exception:
            log.exception('[whisplay] _set_color failed')

    def _restore_color(self):
        self._set_color(*self._current_color)

    # ── LED effects ───────────────────────────────────────────────────────────

    def _handshake_flash(self):
        """Double white flash, then restore previous state colour."""
        for _ in range(2):
            self._set_color(255, 255, 255)
            time.sleep(0.25)
            self._set_color(0, 0, 0)
            time.sleep(0.15)
        self._restore_color()

    def _peer_flash(self):
        """Three quick blue flashes when another pwnagotchi is nearby."""
        for _ in range(3):
            self._set_color(0, 80, 255)
            time.sleep(0.15)
            self._set_color(0, 0, 0)
            time.sleep(0.1)
        self._restore_color()

    def _association_flash(self):
        """Single short yellow flash on AP association."""
        self._set_color(220, 200, 0)
        time.sleep(0.2)
        self._restore_color()

    def _scan_pulse(self):
        """Very brief dim-white tick on each channel scan — stays subtle."""
        self._set_color(40, 40, 40)
        time.sleep(0.05)
        self._restore_color()

    def _mode_flash(self, switched_to_auto: bool):
        """Three flashes to confirm mode change: green=auto, purple=manual."""
        color = (0, 200, 0) if switched_to_auto else (150, 0, 200)
        for _ in range(3):
            self._set_color(*color)
            time.sleep(0.2)
            self._set_color(0, 0, 0)
            time.sleep(0.15)
        self._restore_color()

    def _long_press_flash(self):
        """Three slow cyan pulses to confirm a long press was registered."""
        saved = self._current_color
        for _ in range(3):
            self._set_color(0, 200, 200)
            time.sleep(0.3)
            self._set_color(0, 0, 0)
            time.sleep(0.2)
        self._set_color(*saved)

    # ── Audio ─────────────────────────────────────────────────────────────────

    def _play_sound(self, filename: str):
        """Play a WAV file from plugins_dir via aplay (non-blocking)."""
        # Use 'or' fallbacks — pwnagotchi's dotted-toml converter can produce
        # empty strings for values with colons (e.g. "hw:wm8960soundcard").
        plugins_dir = (
            self.options.get('plugins_dir')
            or '/usr/local/share/pwnagotchi/custom-plugins/'
        )
        path = os.path.join(plugins_dir, filename)
        if not os.path.isfile(path):
            log.warning('[whisplay] sound file not found: %s', path)
            return

        alsa_dev = self.options.get('alsa_device') or 'hw:wm8960soundcard'
        volume   = int(self.options.get('boot_volume') or 60)
        alsa_ctl = self.options.get('alsa_control') or 'Speaker'

        # aplay via plughw: for automatic sample-rate/format conversion
        play_dev = alsa_dev.replace('hw:', 'plughw:', 1)

        def _run():
            try:
                # Set mixer volume before playback
                subprocess.run(
                    ['amixer', 'sset', alsa_ctl, f'{volume}%'],
                    check=False, capture_output=True,
                )
                subprocess.run(
                    ['aplay', '-D', play_dev, path],
                    check=False, capture_output=True,
                )
            except Exception:
                log.exception('[whisplay] audio playback failed')

        threading.Thread(target=_run, daemon=True).start()

    # ── Button ────────────────────────────────────────────────────────────────

    def _button_poll(self):
        """Poll BCM 17 every 10 ms for state changes.
        Avoids GPIO kernel edge-detection (sysfs) which fails when a previous
        crashed run left the export in place.
        HIGH = pressed (external pull-down on HAT), LOW = released.
        """
        last_state = 0
        while self._btn_thread_running:
            try:
                state = self._gpio.input(_PIN_BUTTON)
                if state != last_state:
                    last_state = state
                    if state:   # rising edge = pressed
                        self._btn_press_time = time.monotonic()
                    else:       # falling edge = released
                        if self._btn_press_time is not None:
                            held = time.monotonic() - self._btn_press_time
                            self._btn_press_time = None
                            if held >= _LONG_PRESS_S:
                                threading.Thread(
                                    target=self._on_long_press, daemon=True
                                ).start()
                            else:
                                threading.Thread(
                                    target=self._on_short_press, daemon=True
                                ).start()
            except Exception:
                if self._btn_thread_running:
                    log.exception('[whisplay] button poll error')
            time.sleep(0.01)   # 10 ms — same interval as official WhisPlay driver

    def _on_short_press(self):
        """Short press (<2 s): toggle pwnagotchi between auto and manual mode."""
        log.info('[whisplay] button short press — toggling mode')
        if self._agent is None:
            log.warning('[whisplay] agent not ready yet')
            return
        try:
            import pwnagotchi
            is_auto = (self._agent.mode == pwnagotchi.AUTO)
            if is_auto:
                self._agent.set_mode(pwnagotchi.MANUAL)
                log.info('[whisplay] switched to MANUAL mode')
            else:
                self._agent.set_mode(pwnagotchi.AUTO)
                log.info('[whisplay] switched to AUTO mode')
            self._mode_flash(not is_auto)
        except Exception:
            log.exception('[whisplay] mode toggle failed')

    def _on_long_press(self):
        """Long press (≥2 s): play boot sound as hardware audio test."""
        log.info('[whisplay] button long press — triggering audio test')
        self._long_press_flash()
        self._play_sound('whisplay_boot.wav')
