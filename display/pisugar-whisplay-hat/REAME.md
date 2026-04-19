# PiSugar Whisplay HAT Display Plugin for Pwnagotchi

This repository contains a custom display plugin for Pwnagotchi, designed to work with the PiSugar Whisplay HAT. The plugin provides backlight control and UI status integration for the 240×280 ST7789 display and WM8960 I2S DAC.

## Features
- Backlight control for the PiSugar Whisplay HAT
- UI status integration to display relevant information on the screen
- Compatibility with Pwnagotchi's plugin system for easy installation and updates

## Installation


1. Create `whisplay-display` systemd service:

	 ```yaml
	 - name: Create whisplay-display systemd service
		 copy:
			 dest: /etc/systemd/system/whisplay-display.service
			 mode: "0644"
			 content: |
				 [Unit]
				 Description=Whisplay HAT Display Init
				 After=basic.target
				 Before=pwnagotchi.service

				 [Service]
				 Type=oneshot
				 ExecStart=/opt/whisplay/venv/bin/python3 /opt/whisplay/init_display.py
				 RemainAfterExit=yes
				 SyslogIdentifier=whisplay-display

				 [Install]
				 WantedBy=multi-user.target
	 ```
2. Add the whisplay_hat.py to the display_plugins directory of your Pwnagotchi installation.
3. Install the whisplay_display plugin using Pwnagotchi's custom-plugin system.
4. Enable and start the whisplay-display systemd service:

    ```bash
    sudo systemctl enable whisplay-display
    sudo systemctl start whisplay-display
    ```
5. Enable the whisplay_display plugin in your Pwnagotchi configuration:

    ```toml
    [main.plugins.whisplay_display]
    enabled = true
    ```
6. Reboot your Pwnagotchi to see the changes.
