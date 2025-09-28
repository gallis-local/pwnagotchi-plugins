# pwnagotchi-plugins

The realest - **https://pwnagotchi.org/**

RPIZERO2W Base Image of [JayofFelony - Pwnagotchi Image](https://github.com/jayofelony/pwnagotchi)

RPI4 Base Image of [aluminum-ice - Pwnagotchi Image](https://github.com/aluminum-ice/pwnagotchi/releases)

## Custom Plugins

- bt-tether - Slightly edited bt-tether for network route metric settings
- s3_upload - Uploads all handshakes, geojson, potfiles, and hash files to S3 Minio Endpoint on internet connection

## 🚀 Easy Installation

This repository provides automated plugin bundles compatible with Pwnagotchi's plugin system. **[📖 See Full Installation Guide](PLUGINS.md)**

### Quick Setup

Add to your `/etc/pwnagotchi/config.toml`:

```toml
main.custom_plugin_repos = [
    "https://github.com/gallis-local/pwnagotchi-plugins/releases/latest/download/pwnagotchi-plugins-bundle.zip"
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

## Credits

All referenced plugins will have source repository linked such as above

This repo is soley for ease of install of wip and custom plugins.



