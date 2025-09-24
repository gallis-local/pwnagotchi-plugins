#!/bin/bash
# assigned to the double tap function via Custom Script on pisguar server web-ui
# Path to the file you want to edit
sudo sed -i '/^#dtoverlay=disable-wifi$/s/^#//;t;/^dtoverlay=disable-wifi$/s/^/#/;t' /boot/firmware/config.txt && sudo reboot
