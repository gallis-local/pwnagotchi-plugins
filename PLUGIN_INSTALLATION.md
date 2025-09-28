# Pwnagotchi Plugin Installation Guide

This repository provides a collection of custom Pwnagotchi plugins packaged for easy installation via the Pwnagotchi plugin system.

## 🚀 Quick Start

### Release Channels

This repository provides two release channels:

- **🚀 Main Branch** (`main`) - Production-ready releases with stable, tested plugins
- **🧪 Release Candidate** (`rc`) - Pre-release versions for testing new features and fixes

### Method 1: Using Custom Plugin Repositories (Recommended)

1. **Add Repository URL to Pwnagotchi Configuration**

   Edit your Pwnagotchi configuration file (`/etc/pwnagotchi/config.toml`) and add:

   ```toml
   main.custom_plugin_repos = [
       "https://github.com/gallis-local/pwnagotchi-plugins/releases/latest/download/pwnagotchi-plugins-bundle.zip"
   ]
   ```

   > **Branch Options:**
   > - **Latest (main)**: `releases/latest/download/pwnagotchi-plugins-bundle.zip` - Production ready
   > - **Release Candidate (rc)**: Check [releases page](https://github.com/gallis-local/pwnagotchi-plugins/releases) for latest RC version
   > - **Specific Version**: Replace `latest` with specific version tag (e.g., `v2024.09.28-main-abc1234`)

2. **Update Plugin Database**

   ```bash
   sudo pwnagotchi plugins update
   ```

3. **List Available Plugins**

   ```bash
   sudo pwnagotchi plugins list
   ```

4. **Install Specific Plugin**

   ```bash
   sudo pwnagotchi plugins install s3_upload
   # or any other plugin name from the list
   ```

5. **Enable Plugin in Configuration**

   Add plugin configuration to your `config.toml`:

   ```toml
   main.plugins.s3_upload.enabled = true
   main.plugins.s3_upload.bucket = "your-bucket-name"
   # Add other plugin-specific configuration options
   ```

6. **Restart Pwnagotchi**

   ```bash
   sudo systemctl restart pwnagotchi
   ```

### Method 2: Manual Installation

1. **Download Plugin Bundle**

   Download the latest `pwnagotchi-plugins-simple.zip` from the [releases page](https://github.com/gallis-local/pwnagotchi-plugins/releases).

2. **Extract to Custom Plugins Directory**

   ```bash
   # Create custom plugins directory if it doesn't exist
   sudo mkdir -p /usr/local/share/pwnagotchi/installed-plugins/
   
   # Extract plugins
   cd /tmp
   unzip pwnagotchi-plugins-simple.zip
   sudo cp *.py *.toml /usr/local/share/pwnagotchi/installed-plugins/
   ```

3. **Update Pwnagotchi Configuration**

   Add the custom plugins path to your `config.toml`:

   ```toml
   main.custom_plugins = "/usr/local/share/pwnagotchi/installed-plugins"
   ```

4. **Configure and Enable Plugins**

   Add plugin-specific configuration as shown in Method 1, step 5.

## 📋 Available Plugins

This repository currently includes:

### s3_upload Plugin

Automatically uploads captured handshakes and other files to Amazon S3 or S3-compatible storage.

**Configuration Example:**
```toml
main.plugins.s3_upload.enabled = true
main.plugins.s3_upload.bucket = "pwnagotchi-handshakes"
main.plugins.s3_upload.region = "us-east-1"
main.plugins.s3_upload.access_key = "YOUR_ACCESS_KEY"
main.plugins.s3_upload.secret_key = "YOUR_SECRET_KEY"
main.plugins.s3_upload.endpoint_url = ""  # Leave empty for AWS S3
main.plugins.s3_upload.max_retries = 3
main.plugins.s3_upload.retry_delay = 5
```

### bt-tether Plugin

Bluetooth tethering support for sharing internet connection via mobile devices.

**Configuration Example:**
```toml
main.plugins.bt-tether.enabled = true
main.plugins.bt-tether.phone-name = "Your Phone"
main.plugins.bt-tether.phone = "android"  # or "ios"
main.plugins.bt-tether.mac = "XX:XX:XX:XX:XX:XX"
main.plugins.bt-tether.ip = "192.168.44.100"
```

> For a complete list of plugins and their configurations, check the `plugin_registry.json` file in the latest release.

## 🔧 Troubleshooting

### Plugin Not Found After Update

1. Check internet connection:
   ```bash
   ping google.com
   ```

2. Verify plugin repository configuration:
   ```bash
   sudo cat /etc/pwnagotchi/config.toml | grep custom_plugin_repos
   ```

3. Check plugin update logs:
   ```bash
   sudo pwnagotchi plugins update
   ```

### Plugin Installation Fails

1. Check available plugins:
   ```bash
   sudo pwnagotchi plugins list
   ```

2. Verify custom plugins directory exists:
   ```bash
   ls -la /usr/local/share/pwnagotchi/installed-plugins/
   ```

3. Check disk space:
   ```bash
   df -h
   ```

### Plugin Not Loading

1. Check plugin syntax:
   ```bash
   python3 -m py_compile /path/to/plugin.py
   ```

2. Review Pwnagotchi logs:
   ```bash
   sudo journalctl -u pwnagotchi -f
   ```

3. Verify plugin configuration in `config.toml`

## 🔄 Updating Plugins

To update to the latest plugin versions:

1. **Update Plugin Database**
   ```bash
   sudo pwnagotchi plugins update
   ```

2. **Upgrade Specific Plugin**
   ```bash
   sudo pwnagotchi plugins upgrade s3_upload
   ```

3. **Upgrade All Plugins**
   ```bash
   sudo pwnagotchi plugins upgrade "*"
   ```

## 🏗️ Development and Contributions

### Plugin Development

When developing plugins for this repository:

1. Follow the Pwnagotchi plugin structure:
   ```python
   import pwnagotchi.plugins as plugins
   
   class YourPlugin(plugins.Plugin):
       __author__ = 'your-email@example.com'
       __version__ = '1.0.0'
       __license__ = 'GPL3'
       __description__ = 'Brief description of your plugin'
       
       def __init__(self):
           # Plugin initialization
           pass
       
       def on_loaded(self):
           # Called when plugin is loaded
           pass
   ```

2. Include plugin metadata in the class:
   - `__author__`: Your contact information
   - `__version__`: Plugin version (semantic versioning)
   - `__license__`: License type (usually GPL3)
   - `__description__`: Brief description

3. Add configuration template as `.toml` file if needed

### Creating a Release

The repository uses GitHub Actions to automatically create plugin bundles:

1. **Manual Release**
   - Go to Actions tab in GitHub
   - Run "Release Pwnagotchi Plugins Bundle" workflow
   - Specify version tag (e.g., `v1.0.0`)

2. **Tag-based Release**
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

The workflow will:
- Extract plugin metadata
- Create ZIP bundles compatible with Pwnagotchi
- Generate plugin registry
- Create GitHub release with downloadable assets
- Provide installation URLs

## 📞 Support

### Getting Help

1. **Check Plugin Documentation**: Each plugin should include usage instructions
2. **Review Logs**: Use `sudo journalctl -u pwnagotchi -f` to monitor plugin behavior
3. **Community Support**: Visit [Pwnagotchi Discord](https://discord.gg/pwnagotchi) or forums
4. **GitHub Issues**: Report bugs or request features in this repository's issue tracker

### Common Configuration

```toml
# Example complete configuration section
main.custom_plugin_repos = [
    "https://github.com/gallis-local/pwnagotchi-plugins/releases/latest/download/pwnagotchi-plugins-bundle.zip"
]

main.custom_plugins = "/usr/local/share/pwnagotchi/installed-plugins"

# Plugin configurations
main.plugins.s3_upload.enabled = true
main.plugins.s3_upload.bucket = "my-pwnagotchi-bucket"
main.plugins.s3_upload.access_key = "AKIA..."
main.plugins.s3_upload.secret_key = "..."

main.plugins.bt-tether.enabled = false  # Enable when needed
```

---

## 📚 Additional Resources

- [Official Pwnagotchi Documentation](https://pwnagotchi.ai/)
- [Pwnagotchi GitHub Repository](https://github.com/jayofelony/pwnagotchi)
- [Plugin Development Guide](https://pwnagotchi.ai/plugins/)
- [Community Plugins](https://github.com/topics/pwnagotchi-plugin)

---

*This documentation is maintained for the pwnagotchi-plugins repository. For issues or contributions, please use the repository's issue tracker.*