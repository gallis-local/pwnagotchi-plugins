# pwnagotchi-plugins

The realest - **https://pwnagotchi.org/**

RPIZERO2W Base Image of [JayofFelony - Pwnagotchi Image](https://github.com/jayofelony/pwnagotchi)

RPI4 Base Image of [aluminum-ice - Pwnagotchi Image](https://github.com/aluminum-ice/pwnagotchi/releases)

## Master Plugin List

- [itsdarklikehell's awesome list](https://github.com/itsdarklikehell/pwnagotchi-plugins)

## Utility Scripts

* pwnagotchi-scripts - execute on the pwnagotchi via SSH
* scripts - execute on host machine of USB OTG connection

## Custom Plugins

- Clock Custom to side

## Current Repo List of Plugins

```
main.custom_plugin_repos = [
 "https://github.com/itsdarklikehell/pwnagotchi-plugins/archive/refs/heads/master.zip"
]
```

## Initial Setup

```
sudo pwnagotchi plugins update
sudo pwnagotchi plugins install exp
sudo pwnagotchi plugins install show_pwd
sudo pwnagotchi plugins install session-stats_ng

```

## Original List of Plugins from Image

```
main.custom_plugin_repos = [
    "https://github.com/jayofelony/pwnagotchi-torch-plugins/archive/master.zip",
    "https://github.com/tisboyo/pwnagotchi-pisugar2-plugin/archive/master.zip",
    "https://github.com/nullm0ose/pwnagotchi-plugin-pisugar3/archive/master.zip",
    "https://github.com/Sniffleupagus/pwnagotchi_plugins/archive/master.zip",
    "https://github.com/NeonLightning/pwny/archive/master.zip",
    "https://github.com/marbasec/UPSLite_Plugin_1_3/archive/master.zip"
]
```

## Credits

All referenced plugins will have source repository linked such as above

This repo is soley for ease of install of wip and custom plugins.



