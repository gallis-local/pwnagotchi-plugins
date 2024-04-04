#!/bin/bash

# Path to the file you want to edit
FILE_PATH="/boot/firmware/config.txt"

# Check if the file exists
if [ ! -f "$FILE_PATH" ]; then
    echo "Error: File does not exist."
    exit 1
fi

# Use sed to toggle the comment status of 'dtoverlay=disable-wifi'
sed -i '/^#dtoverlay=disable-wifi/s/^#//; t; s/^dtoverlay=disable-wifi/#&/' "$FILE_PATH"

echo "Toggled the comment status of 'dtoverlay=disable-wifi' in $FILE_PATH."
