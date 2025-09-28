# Plugins

## bt-tether

✅ Fix: Create the Bluetooth PAN profile first

You need to add a connection profile before you can modify it.

Run this one-liner to create it:
```
nmcli connection add type bluetooth con-name "<NAME>'s iPhone" ifname "*" bluetooth.type panu bluetooth.bdaddr <MAC ADDRESS>
nmcli connection modify "<Name>'s iPhone" connection.autoconnect yes connection.autoconnect-retries 0 ipv4.method manual ipv4.addresses 172.20.10.2/24 ipv4.gateway 172.20.10.1 ipv4.dns "8.8.8.8 1.1.1.1" ipv4.route-metric 50
```

## s3_upload

S3 Upload Files