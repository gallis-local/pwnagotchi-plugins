# pwnagotchi-plugins

The realest - **https://pwnagotchi.org/**

RPIZERO2W Base Image of [JayofFelony - Pwnagotchi Image](https://github.com/jayofelony/pwnagotchi)

RPI4 Base Image of [aluminum-ice - Pwnagotchi Image](https://github.com/aluminum-ice/pwnagotchi/releases)

## Custom Plugins

- **bt-tether** - Slightly edited bt-tether for network route metric settings
- **s3_upload** - Uploads all handshakes, geojson, potfiles, and hash files to S3 Minio Endpoint on internet connection
- **wifi_adapter_manager** - Automatically detects external USB wireless adapters and manages integrated WiFi configuration to prevent boot failures

## 🚀 Easy Installation

This repository provides automated plugin bundles compatible with Pwnagotchi's plugin system. **[📖 See Full Installation Guide](PLUGINS.md)**

### Quick Setup

Add to your `/etc/pwnagotchi/config.toml`:

```toml
main.custom_plugin_repos = [
    "https://github.com/gallis-local/pwnagotchi-plugins/archive/main.zip"
]
```

Then run:
```bash
sudo pwnagotchi plugins update
sudo pwnagotchi plugins install s3_upload
```

## Companion Apps

- [pwnios](https://github.com/BraedenP232/pwnios)

### Other Plugin Repositories

```toml
main.custom_plugin_repos = [
    "https://github.com/jayofelony/pwnagotchi-torch-plugins/archive/master.zip",
    "https://github.com/Sniffleupagus/pwnagotchi_plugins/archive/master.zip",
    "https://github.com/NeonLightning/pwny/archive/master.zip",
    "https://github.com/marbasec/UPSLite_Plugin_1_3/archive/master.zip",
    "https://github.com/wpa-2/Pwnagotchi-Plugins/archive/master.zip",
    "https://github.com/BraedenP232/pwnios/archive/main.zip",
    "https://github.com/gallis-local/pwnagotchi-plugins/archive/main.zip"
]
```

## Extra

### Utility Scripts

* scripts - pwngaotchi connection and utility

### 3D Printed Cases

A selection of the most consistent fitting 3D printed cases based on tolerances for both regular and the slimagotchi mod.

---

## 📡 WiFi Adapter Manager Plugin

### Overview

The **WiFi Adapter Manager** plugin automatically detects external USB wireless adapters and manages the Raspberry Pi's integrated WiFi configuration to prevent boot failures.

### Why This Plugin?

**The Problem:**
- Pwnagotchi won't boot without a wireless interface
- When using external USB WiFi adapters (for 5GHz support or better range), the integrated WiFi must be disabled via `/boot/config.txt` with `dtoverlay=disable-wifi`
- If you remove the external adapter, Pwnagotchi fails to boot because there's no wireless interface available
- Manual configuration is error-prone and requires multiple reboots

**The Solution:**
This plugin automatically:
- Detects when external USB wireless adapters are connected
- Manages the `dtoverlay=disable-wifi` setting in `/boot/config.txt`
- Prevents boot failures by ensuring at least one wireless interface is always available
- Provides a web UI for manual control and monitoring

### Features

✅ **Automatic Detection** - Detects external USB wireless adapters using `iw`, `iwconfig`, and `lsusb`
✅ **Smart Configuration** - Automatically manages `/boot/config.txt` settings
✅ **Safety First** - Multiple safety checks prevent lockouts
✅ **Monitor Mode Check** - Verifies external adapters support monitor mode (required for Pwnagotchi)
✅ **Web UI Dashboard** - View adapter status and manually control WiFi settings
✅ **Display Integration** - Shows adapter status on Pwnagotchi screen
✅ **Multiple Modes** - Auto, Safe, and Manual operating modes
✅ **State Persistence** - Tracks configuration across reboots

### Installation

1. Add this repository to your config:
```bash
# Edit /etc/pwnagotchi/config.toml
main.custom_plugin_repos = [
    "https://github.com/gallis-local/pwnagotchi-plugins/archive/main.zip"
]
```

2. Install the plugin:
```bash
sudo pwnagotchi plugins update
sudo pwnagotchi plugins install wifi_adapter_manager
```

3. Configure the plugin (copy from `wifi_adapter_manager.toml`):
```toml
# Enable the plugin
main.plugins.wifi_adapter_manager.enabled = true

# Operating mode: "auto", "manual", or "safe"
main.plugins.wifi_adapter_manager.mode = "safe"

# Check frequency (in epochs)
main.plugins.wifi_adapter_manager.check_interval = 10

# Require monitor mode support
main.plugins.wifi_adapter_manager.require_monitor_mode = true

# Auto-reboot after changes (WARNING: disconnects session)
main.plugins.wifi_adapter_manager.auto_reboot = false

# Display status on UI
main.plugins.wifi_adapter_manager.show_ui_status = true
```

4. Restart Pwnagotchi:
```bash
sudo systemctl restart pwnagotchi
```

### Operating Modes

| Mode | Behavior | Best For |
|------|----------|----------|
| **safe** (Recommended) | Only automatically re-enables integrated WiFi when no external adapter is detected. Will NOT auto-disable WiFi. | Beginners, testing external adapters |
| **auto** | Automatically enables/disables integrated WiFi based on adapter detection | Advanced users with tested external adapters |
| **manual** | No automatic changes, full manual control via web UI | Users who want complete control |

### Web UI

Access the plugin dashboard at:
```
http://<pwnagotchi-ip>:8080/plugins/wifi_adapter_manager
```

The dashboard shows:
- 📶 Current adapter status (integrated + external)
- 🔌 USB wireless adapter details
- ⚙️ Config.txt status
- 🔄 Manual control buttons
- 📖 Safety information and warnings

### Usage Workflow

**Recommended workflow for first-time setup:**

1. **Install external adapter**
   ```bash
   # Verify it's detected
   sudo iw dev
   sudo lsusb | grep -i wireless
   ```

2. **Enable plugin in "manual" mode**
   ```toml
   main.plugins.wifi_adapter_manager.enabled = true
   main.plugins.wifi_adapter_manager.mode = "manual"
   ```

3. **Access web UI and verify detection**
   - Go to `http://<ip>:8080/plugins/wifi_adapter_manager`
   - Confirm external adapter is listed
   - Verify it supports monitor mode

4. **Manually disable integrated WiFi**
   - Click "Disable Integrated WiFi" button
   - System will update `/boot/config.txt`
   - Reboot when prompted

5. **Test external adapter**
   - After reboot, confirm Pwnagotchi works
   - Check WiFi scanning is operational
   - Verify display and logging work

6. **Switch to "safe" or "auto" mode**
   ```toml
   main.plugins.wifi_adapter_manager.mode = "safe"
   ```
   - Safe mode prevents lockouts (recommended)
   - Auto mode for fully automatic operation

### Safety Features

The plugin includes multiple safety mechanisms:

🛡️ **Prevents Lockouts**
- Will NOT disable integrated WiFi unless external adapter is detected
- Automatically re-enables integrated WiFi if external adapter is removed

🛡️ **Monitor Mode Verification**
- Checks that external adapter supports monitor mode
- Prevents configuration with incompatible adapters

🛡️ **Atomic Config Updates**
- Config.txt updates are atomic (no partial writes)
- Backup mechanism prevents corruption

🛡️ **Persistent State Tracking**
- Status file at `/root/.wifi_adapter_manager_status.json`
- Tracks configuration across reboots

### Troubleshooting

**Q: I'm locked out (no wireless interface available)**

A: Recovery options:
1. Connect via USB or Bluetooth tethering
2. Or: Remove SD card, mount on another computer, edit `/boot/config.txt` or `/boot/firmware/config.txt`
3. Remove or comment out the line: `dtoverlay=disable-wifi`
4. Reboot

**Q: External adapter not detected**

A: Check the following:
```bash
# Check USB devices
lsusb

# Check wireless interfaces
iw dev
iwconfig

# Check kernel messages
dmesg | grep -i wlan
dmesg | grep -i usb

# Check if driver loaded
lsmod | grep -i 80211
```

**Q: Plugin says adapter doesn't support monitor mode**

A: Some adapters need drivers installed or don't support monitor mode:
```bash
# Test monitor mode manually
sudo iw wlan1 set monitor none
sudo iw wlan1 info
```

**Q: Config.txt changes don't take effect**

A: Ensure you've rebooted after configuration changes:
```bash
sudo reboot
```

### Compatible External Adapters

The plugin works with most USB WiFi adapters, but for Pwnagotchi you need:
- **Monitor mode support** (required for WiFi packet capture)
- **Linux driver support** (built-in or installable)

**Recommended adapters:**
- Alfa AWUS036ACH (5GHz, high power)
- Alfa AWUS036NHA (2.4GHz, long range)
- TP-Link TL-WN722N v1 (2.4GHz, budget-friendly)
- Panda PAU09 (dual-band, compact)

See [large 5GHz compatible WiFi USB adapter options](https://a.co/d/gtC9PBJ)

### Display Indicator

When `show_ui_status = true`, the plugin shows adapter status on the Pwnagotchi screen:

- `INT` - Integrated WiFi only
- `EXT+2` - External adapter detected (2 interfaces total)
- `EXT+2!` - Configuration pending reboot

### Technical Details

**Detection Methods:**
- `iw dev` - List wireless interfaces
- `lsusb` - Detect USB wireless devices
- `iw <interface> info` - Check monitor mode capability

**Config Files Modified:**
- `/boot/firmware/config.txt` (modern Raspberry Pi OS)
- `/boot/config.txt` (older Raspberry Pi OS)

**Status File:**
- `/root/.wifi_adapter_manager_status.json`

**Log Location:**
- Check Pwnagotchi logs: `sudo journalctl -u pwnagotchi -f`
- Look for `[WiFiAdapterMgr]` tags

---

## Credits

All referenced plugins will have source repository linked such as above

This repo is soley for ease of install of wip and custom plugins.



