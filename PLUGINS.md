# Plugins

## s3_upload

S3 Upload Files

```
main.plugins.s3_upload.enabled = false
main.plugins.s3_upload.bucket = ""
main.plugins.s3_upload.region = ""
main.plugins.s3_upload.access_key = ""
main.plugins.s3_upload.secret_key = ""
main.plugins.s3_upload.endpoint_url = ""
main.plugins.s3_upload.max_retries = 3
main.plugins.s3_upload.retry_delay = 5
```

## whisplay_display

Whisplay HAT backlight, audio chimes, and UI status integration for the PiSugar
[Whisplay HAT](https://github.com/PiSugar/Whisplay) (240×280 ST7789 + WM8960 I2S DAC).

### Hardware

| Signal | BOARD pin | BCM GPIO | Notes |
|--------|-----------|----------|-------|
| Backlight (LED) | 15 | 22 | **Active LOW** — LOW = on |
| SPI DC | 13 | 27 | |
| SPI RST | 7 | 4 | |

The backlight pin is active LOW. The plugin inverts the duty cycle accordingly.

### Config

```toml
main.plugins.whisplay_display.enabled = true

# Hardware — BCM GPIO 22 (BOARD 15), active LOW
main.plugins.whisplay_display.backlight_pin = 22

# Audio — WM8960 I2S DAC on Whisplay HAT
main.plugins.whisplay_display.alsa_device = "hw:wm8960soundcard"
main.plugins.whisplay_display.alsa_control = "Speaker"
main.plugins.whisplay_display.boot_volume = 60

# Chimes
main.plugins.whisplay_display.boot_chime = true
main.plugins.whisplay_display.handshake_chime = true

# Backlight brightness levels (0–100)
main.plugins.whisplay_display.active_brightness = 100
main.plugins.whisplay_display.idle_brightness = 35
main.plugins.whisplay_display.sleep_brightness = 10

# UI status label position on the 240×280 display
main.plugins.whisplay_display.ui_position_x = 0
main.plugins.whisplay_display.ui_position_y = 92

# Optional: override bundled WAV paths
# main.plugins.whisplay_display.boot_sound_file = "/usr/local/share/pwnagotchi/custom-plugins/whisplay_boot.wav"
# main.plugins.whisplay_display.handshake_sound_file = "/usr/local/share/pwnagotchi/custom-plugins/whisplay_chime.wav"
```

### Notes

- `whisplay_boot.wav` and `whisplay_chime.wav` are bundled alongside the plugin and used automatically. Override paths only if you want custom sounds.
- Backlight brightness dims to `idle_brightness` when the AI reward is zero and steps down to `sleep_brightness` during sleep mode.
- The plugin does **not** drive the display itself — pwnagotchi's built-in display driver handles rendering. This plugin controls backlight, audio, and the `HAT HS:N` status label.

## WIP

`bt-tether` has been moved to [wip/bt-tether.py](/mnt/d/Github/pwnagotchi-plugins/wip/bt-tether.py) because the latest upstream Pwnagotchi version may already include the relevant fix.
