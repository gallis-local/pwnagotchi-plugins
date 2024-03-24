# PiSugar3 Install

- https://github.com/nullm0ose/pwnagotchi-plugin-pisugar3

## Basic Install Script

1. ``` sudo raspi-config ``` - Enable I2C Interface

```
curl http://cdn.pisugar.com/release/pisugar-power-manager.sh | sudo bash
mkdir /etc/pwnagotchi/custom-plugins
cd /etc/pwnagotchi/custom-plugins
git clone https://github.com/nullm0ose/pwnagotchi-plugin-pisugar3.git
cp /etc/pwnagotchi/custom-plugins/pwnagotchi-plugin-pisugar3/pisugar3.py /etc/pwnagotchi/custom-plugins

```