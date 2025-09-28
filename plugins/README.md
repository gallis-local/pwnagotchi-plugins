# Plugins

## bt-tether

[Source as of (v2.9.5.3)](https://github.com/jayofelony/pwnagotchi/issues/405#issuecomment-2961326871)

[Pull Request](https://github.com/jayofelony/pwnagotchi/pull/407)


✅ Fix: Create the Bluetooth PAN profile first

You need to add a connection profile before you can modify it.

Run this one-liner to create it:
```
nmcli connection add type bluetooth con-name "<NAME>'s iPhone" ifname "*" bluetooth.type panu bluetooth.bdaddr <MAC ADDRESS>
nmcli connection modify "<Name>'s iPhone" connection.autoconnect yes connection.autoconnect-retries 0 ipv4.method manual ipv4.addresses 172.20.10.2/24 ipv4.gateway 172.20.10.1 ipv4.dns "8.8.8.8 1.1.1.1" ipv4.route-metric 50
```

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