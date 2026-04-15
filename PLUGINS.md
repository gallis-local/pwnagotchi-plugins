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

Whisplay HAT backlight and audio helper.

```
main.plugins.whisplay_display.enabled = false
main.plugins.whisplay_display.backlight_pin = 24
main.plugins.whisplay_display.boot_volume = 60
main.plugins.whisplay_display.boot_chime = true
main.plugins.whisplay_display.handshake_chime = true
main.plugins.whisplay_display.active_brightness = 100
main.plugins.whisplay_display.idle_brightness = 35
main.plugins.whisplay_display.sleep_brightness = 10
main.plugins.whisplay_display.boot_sound_file = "/etc/pwnagotchi/custom-plugins/whisplay_boot.wav"
main.plugins.whisplay_display.handshake_sound_file = "/etc/pwnagotchi/custom-plugins/whisplay_chime.wav"
```

- Optional `whisplay_boot.wav` and `whisplay_chime.wav` files can live beside the plugin, or you can override the paths in config.
- This plugin handles backlight, audio, and UI feedback. Your TFT panel driver still needs to be configured separately in the image if required by your hardware.

## WIP

`bt-tether` has been moved to [wip/bt-tether.py](/mnt/d/Github/pwnagotchi-plugins/wip/bt-tether.py) because the latest upstream Pwnagotchi version may already include the relevant fix.
