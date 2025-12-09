"""
WiFi Adapter Manager Plugin for Pwnagotchi

Automatically detects external USB wireless adapters and manages the
integrated WiFi configuration in /boot/config.txt to prevent boot failures.

When an external adapter is detected, the plugin can automatically disable
the integrated WiFi (required for proper operation). When removed, it can
re-enable the integrated WiFi to prevent boot failures.
"""

import logging
import os
import re
import subprocess
import json
import time
from threading import Lock
from flask import render_template_string, request, abort, redirect, jsonify

import pwnagotchi.plugins as plugins
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK
import pwnagotchi.ui.fonts as fonts


TAG = "[WiFiAdapterMgr]"


class WifiAdapterManager(plugins.Plugin):
    __author__ = 'pwnagotchi-plugins'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = 'Manages external WiFi adapter detection and auto-configures boot settings'

    def __init__(self):
        self.ready = False
        self.options = dict()
        self.lock = Lock()
        self._status_path = '/root/.wifi_adapter_manager_status.json'
        self._last_check = 0
        self._check_counter = 0
        self._pending_reboot = False

        # State tracking
        self._status = {
            'has_external_adapter': False,
            'interfaces': [],
            'usb_adapters': [],
            'integrated_wifi_disabled': False,
            'config_path': None,
            'last_check': None,
            'mode': 'auto',
            'pending_reboot': False,
            'last_action': None
        }

    def on_loaded(self):
        """Called when plugin is loaded"""
        # Set defaults
        if 'mode' not in self.options:
            self.options['mode'] = 'auto'
        if 'check_interval' not in self.options:
            self.options['check_interval'] = 10
        if 'require_monitor_mode' not in self.options:
            self.options['require_monitor_mode'] = True
        if 'auto_reboot' not in self.options:
            self.options['auto_reboot'] = False
        if 'show_ui_status' not in self.options:
            self.options['show_ui_status'] = True

        # Validate mode
        if self.options['mode'] not in ['auto', 'manual', 'safe']:
            logging.error(f"{TAG} Invalid mode '{self.options['mode']}'. Using 'safe' mode.")
            self.options['mode'] = 'safe'

        # Load previous status
        self._load_status()

        logging.info(f"{TAG} Plugin loaded in '{self.options['mode']}' mode")
        self.ready = True

    def on_ready(self, agent):
        """Called when Pwnagotchi is ready"""
        logging.info(f"{TAG} System ready, performing initial adapter check")
        self._perform_adapter_check()

    def on_config_changed(self, config):
        """Called when configuration changes"""
        logging.info(f"{TAG} Configuration changed, reloading settings")
        # Update mode if changed
        if 'mode' in self.options:
            self._status['mode'] = self.options['mode']
            self._persist_status()

    def on_epoch(self, agent, epoch, epoch_data):
        """Called at epoch boundaries - periodic adapter check"""
        if not self.ready:
            return

        self._check_counter += 1

        # Check at configured interval
        if self._check_counter >= self.options['check_interval']:
            self._check_counter = 0
            logging.debug(f"{TAG} Periodic adapter check (epoch {epoch})")
            self._perform_adapter_check()

    def on_ui_setup(self, ui):
        """Set up UI elements"""
        if not self.options['show_ui_status']:
            return

        # Add adapter status indicator
        ui.add_element('wifi_adapter', LabeledValue(
            color=BLACK,
            label='',
            value='',
            position=(0, 95),
            label_font=fonts.Small,
            text_font=fonts.Small
        ))

    def on_ui_update(self, ui):
        """Update UI display"""
        if not self.ready or not self.options['show_ui_status']:
            return

        with self.lock:
            if self._status['has_external_adapter']:
                status_text = f"EXT+{len(self._status['interfaces'])}"
            else:
                status_text = "INT"

            if self._pending_reboot:
                status_text += "!"

            ui.set('wifi_adapter', status_text)

    def on_webhook(self, path, request):
        """Handle web UI requests"""
        if not self.ready:
            return self._render_loading_page()

        # Main dashboard
        if path == '/' or not path:
            return self._render_dashboard()

        # API: Get current status
        elif path == '/status':
            return jsonify(self._status)

        # API: Force adapter check
        elif path == '/check':
            if request.method == 'POST':
                self._perform_adapter_check()
                return jsonify({'success': True, 'status': self._status})
            abort(405)

        # API: Toggle integrated WiFi
        elif path == '/toggle_wifi':
            if request.method == 'POST':
                enable_wifi = request.form.get('enable') == 'true'
                result = self._manual_toggle_wifi(enable_wifi)
                return jsonify(result)
            abort(405)

        # API: Reboot system
        elif path == '/reboot':
            if request.method == 'POST':
                logging.info(f"{TAG} Reboot requested via web UI")
                subprocess.Popen(['sudo', 'reboot'])
                return jsonify({'success': True, 'message': 'Rebooting...'})
            abort(405)

        abort(404)

    # =========================================================================
    # Core Detection Functions
    # =========================================================================

    def detect_external_adapters(self):
        """
        Detect external USB WiFi adapters
        Returns dict with detection results
        """
        detection = {
            'has_external': False,
            'interfaces': [],
            'usb_adapters': [],
            'monitor_capable': []
        }

        try:
            # Method 1: Check for wireless interfaces using iw
            result = subprocess.run(
                ['iw', 'dev'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                interfaces = re.findall(r'Interface (wlan\d+)', result.stdout)
                detection['interfaces'] = interfaces

                # Check each interface for monitor mode capability
                for interface in interfaces:
                    if self._check_monitor_mode(interface):
                        detection['monitor_capable'].append(interface)

                # If more than one interface, we have external adapter(s)
                detection['has_external'] = len(interfaces) > 1

        except subprocess.TimeoutExpired:
            logging.error(f"{TAG} Timeout while checking wireless interfaces")
        except FileNotFoundError:
            logging.warning(f"{TAG} 'iw' command not found, trying iwconfig")
            # Fallback to iwconfig
            try:
                result = subprocess.run(
                    ['iwconfig'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                interfaces = re.findall(r'(wlan\d+)', result.stdout)
                detection['interfaces'] = list(set(interfaces))
                detection['has_external'] = len(detection['interfaces']) > 1
            except Exception as e:
                logging.error(f"{TAG} Error using iwconfig: {e}")

        try:
            # Method 2: Check USB devices for wireless adapters
            result = subprocess.run(
                ['lsusb'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                wifi_keywords = [
                    'Wireless', 'WiFi', '802.11', 'WLAN',
                    'Realtek', 'Ralink', 'Atheros', 'MediaTek',
                    'TP-Link', 'Alfa', 'Panda'
                ]

                for line in result.stdout.split('\n'):
                    if any(keyword in line for keyword in wifi_keywords):
                        detection['usb_adapters'].append(line.strip())

        except subprocess.TimeoutExpired:
            logging.error(f"{TAG} Timeout while checking USB devices")
        except Exception as e:
            logging.error(f"{TAG} Error checking USB devices: {e}")

        return detection

    def _check_monitor_mode(self, interface):
        """Check if an interface supports monitor mode"""
        try:
            result = subprocess.run(
                ['iw', interface, 'info'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                return 'monitor' in result.stdout.lower()

        except Exception as e:
            logging.debug(f"{TAG} Could not check monitor mode for {interface}: {e}")

        return False

    # =========================================================================
    # Config.txt Management
    # =========================================================================

    def check_config_txt(self):
        """
        Check if disable-wifi is set in config.txt
        Returns (is_disabled, config_path)
        """
        config_paths = [
            '/boot/firmware/config.txt',
            '/boot/config.txt'
        ]

        for path in config_paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        content = f.read()
                        is_disabled = (
                            'dtoverlay=disable-wifi' in content or
                            'dtoverlay=pi3-disable-wifi' in content
                        )
                        return is_disabled, path
                except PermissionError:
                    logging.error(f"{TAG} Permission denied reading {path}")
                except Exception as e:
                    logging.error(f"{TAG} Error reading {path}: {e}")

        logging.warning(f"{TAG} Could not find config.txt")
        return False, None

    def update_config_txt(self, enable_disable_wifi):
        """
        Add or remove disable-wifi overlay from config.txt
        Returns (success, message, reboot_required)
        """
        is_disabled, config_path = self.check_config_txt()

        if config_path is None:
            return False, "Could not find config.txt", False

        # Check if change is needed
        if enable_disable_wifi and is_disabled:
            return True, "Integrated WiFi already disabled", False
        if not enable_disable_wifi and not is_disabled:
            return True, "Integrated WiFi already enabled", False

        try:
            # Read current config
            with open(config_path, 'r') as f:
                lines = f.readlines()

            # Modify config
            if enable_disable_wifi:
                # Add disable-wifi overlay
                if not any('disable-wifi' in line for line in lines):
                    # Add comment and overlay
                    lines.append('\n# Disable integrated WiFi (managed by wifi_adapter_manager plugin)\n')
                    lines.append('dtoverlay=disable-wifi\n')
                    action = "Added disable-wifi overlay"
            else:
                # Remove disable-wifi overlay and related comments
                new_lines = []
                skip_next = False
                for line in lines:
                    if 'wifi_adapter_manager' in line.lower():
                        skip_next = True
                        continue
                    if 'disable-wifi' in line:
                        skip_next = False
                        continue
                    if not skip_next:
                        new_lines.append(line)
                    skip_next = False
                lines = new_lines
                action = "Removed disable-wifi overlay"

            # Write atomically (write to temp file, then replace)
            temp_path = config_path + '.tmp'
            with open(temp_path, 'w') as f:
                f.writelines(lines)

            os.replace(temp_path, config_path)

            logging.info(f"{TAG} {action} in {config_path}")
            self._status['last_action'] = action
            self._pending_reboot = True
            self._status['pending_reboot'] = True
            self._persist_status()

            return True, action, True

        except PermissionError:
            msg = f"Permission denied writing to {config_path}"
            logging.error(f"{TAG} {msg}")
            return False, msg, False
        except Exception as e:
            msg = f"Error updating config.txt: {e}"
            logging.error(f"{TAG} {msg}")
            return False, msg, False

    # =========================================================================
    # Safety Checks
    # =========================================================================

    def is_safe_to_disable_wifi(self):
        """
        Ensure it's safe to disable integrated WiFi
        Returns (is_safe, reason)
        """
        detection = self.detect_external_adapters()

        # Safety rule 1: Must have external adapter
        if not detection['has_external']:
            return False, "No external adapter detected"

        # Safety rule 2: External adapter must support monitor mode (if required)
        if self.options['require_monitor_mode']:
            external_interfaces = detection['interfaces'][1:]  # Skip wlan0
            monitor_capable = [iface for iface in external_interfaces
                             if iface in detection['monitor_capable']]

            if not monitor_capable:
                return False, "External adapter does not support monitor mode"

        # Safety rule 3: At least one interface must be available
        if len(detection['interfaces']) == 0:
            return False, "No wireless interfaces found"

        return True, "Safe to disable integrated WiFi"

    def is_safe_to_enable_wifi(self):
        """
        Ensure it's safe to enable integrated WiFi
        Always safe - this is the fallback configuration
        """
        return True, "Safe to enable integrated WiFi"

    # =========================================================================
    # Main Logic
    # =========================================================================

    def _perform_adapter_check(self):
        """Perform adapter detection and auto-configuration"""
        if not self.ready:
            return

        with self.lock:
            logging.debug(f"{TAG} Performing adapter check")

            # Detect adapters
            detection = self.detect_external_adapters()

            # Update status
            self._status['has_external_adapter'] = detection['has_external']
            self._status['interfaces'] = detection['interfaces']
            self._status['usb_adapters'] = detection['usb_adapters']
            self._status['last_check'] = time.strftime('%Y-%m-%d %H:%M:%S')

            # Check current config.txt state
            is_disabled, config_path = self.check_config_txt()
            self._status['integrated_wifi_disabled'] = is_disabled
            self._status['config_path'] = config_path

            # Log current state
            logging.info(f"{TAG} Adapter check: external={detection['has_external']}, "
                        f"interfaces={detection['interfaces']}, "
                        f"wifi_disabled={is_disabled}")

            # Auto-configuration based on mode
            if self.options['mode'] == 'auto':
                self._auto_configure(detection, is_disabled)
            elif self.options['mode'] == 'safe':
                self._safe_auto_configure(detection, is_disabled)

            self._persist_status()

    def _auto_configure(self, detection, currently_disabled):
        """Auto mode: automatically enable/disable based on adapter presence"""
        if detection['has_external'] and not currently_disabled:
            # External adapter present, integrated WiFi not disabled
            is_safe, reason = self.is_safe_to_disable_wifi()
            if is_safe:
                logging.info(f"{TAG} External adapter detected, disabling integrated WiFi")
                success, message, reboot_req = self.update_config_txt(True)
                if success and reboot_req:
                    logging.info(f"{TAG} {message} - REBOOT REQUIRED")
                    if self.options['auto_reboot']:
                        self._schedule_reboot()
            else:
                logging.warning(f"{TAG} Cannot disable WiFi: {reason}")

        elif not detection['has_external'] and currently_disabled:
            # No external adapter, integrated WiFi is disabled - DANGER!
            logging.warning(f"{TAG} No external adapter detected, re-enabling integrated WiFi")
            success, message, reboot_req = self.update_config_txt(False)
            if success and reboot_req:
                logging.info(f"{TAG} {message} - REBOOT REQUIRED")
                if self.options['auto_reboot']:
                    self._schedule_reboot()

    def _safe_auto_configure(self, detection, currently_disabled):
        """Safe mode: only re-enable WiFi if no external adapter, never disable"""
        if not detection['has_external'] and currently_disabled:
            # No external adapter, integrated WiFi is disabled - DANGER!
            logging.warning(f"{TAG} [SAFE MODE] No external adapter, re-enabling integrated WiFi")
            success, message, reboot_req = self.update_config_txt(False)
            if success and reboot_req:
                logging.info(f"{TAG} {message} - REBOOT REQUIRED")
                if self.options['auto_reboot']:
                    self._schedule_reboot()
        elif detection['has_external'] and not currently_disabled:
            logging.info(f"{TAG} [SAFE MODE] External adapter detected, but not auto-disabling (use manual mode)")

    def _manual_toggle_wifi(self, enable_wifi):
        """Manual toggle from web UI"""
        with self.lock:
            if enable_wifi:
                # User wants to enable integrated WiFi
                is_safe, reason = self.is_safe_to_enable_wifi()
                if not is_safe:
                    return {'success': False, 'message': reason}

                success, message, reboot_req = self.update_config_txt(False)
            else:
                # User wants to disable integrated WiFi
                is_safe, reason = self.is_safe_to_disable_wifi()
                if not is_safe:
                    return {'success': False, 'message': reason}

                success, message, reboot_req = self.update_config_txt(True)

            return {
                'success': success,
                'message': message,
                'reboot_required': reboot_req,
                'status': self._status
            }

    def _schedule_reboot(self):
        """Schedule system reboot"""
        logging.info(f"{TAG} Scheduling reboot in 10 seconds...")
        subprocess.Popen(['sudo', 'shutdown', '-r', '+1', 'WiFi adapter configuration changed'])

    # =========================================================================
    # State Persistence
    # =========================================================================

    def _load_status(self):
        """Load status from disk"""
        if os.path.exists(self._status_path):
            try:
                with open(self._status_path, 'r') as f:
                    saved_status = json.load(f)
                    self._status.update(saved_status)
                    self._pending_reboot = self._status.get('pending_reboot', False)
                    logging.debug(f"{TAG} Loaded status from {self._status_path}")
            except Exception as e:
                logging.error(f"{TAG} Error loading status: {e}")

    def _persist_status(self):
        """Persist status to disk"""
        try:
            with open(self._status_path, 'w') as f:
                json.dump(self._status, f, indent=2)
        except Exception as e:
            logging.error(f"{TAG} Error persisting status: {e}")

    # =========================================================================
    # Web UI Rendering
    # =========================================================================

    def _render_loading_page(self):
        """Render loading page when plugin not ready"""
        return """
        <html>
        <head><title>WiFi Adapter Manager</title></head>
        <body style="font-family: monospace; padding: 20px;">
            <h1>WiFi Adapter Manager</h1>
            <p style="color: orange;">Plugin is loading...</p>
        </body>
        </html>
        """

    def _render_dashboard(self):
        """Render main dashboard"""
        detection = self.detect_external_adapters()
        is_disabled, config_path = self.check_config_txt()

        # Safety check for disable action
        can_disable, disable_reason = self.is_safe_to_disable_wifi()
        can_enable, enable_reason = self.is_safe_to_enable_wifi()

        return render_template_string(DASHBOARD_TEMPLATE,
            status=self._status,
            detection=detection,
            is_disabled=is_disabled,
            config_path=config_path,
            can_disable=can_disable,
            disable_reason=disable_reason,
            can_enable=can_enable,
            enable_reason=enable_reason,
            mode=self.options['mode'],
            pending_reboot=self._pending_reboot
        )


# =============================================================================
# Web UI Template
# =============================================================================

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>WiFi Adapter Manager</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: 'Courier New', monospace;
            background-color: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
            max-width: 1000px;
            margin: 0 auto;
        }
        h1 { color: #4ec9b0; border-bottom: 2px solid #4ec9b0; padding-bottom: 10px; }
        h2 { color: #569cd6; margin-top: 30px; }
        .card {
            background-color: #252526;
            border: 1px solid #3e3e42;
            border-radius: 5px;
            padding: 15px;
            margin: 15px 0;
        }
        .status-good { color: #4ec9b0; }
        .status-warning { color: #ce9178; }
        .status-error { color: #f48771; }
        .badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 0.85em;
            margin-left: 10px;
        }
        .badge-external { background-color: #4ec9b0; color: #000; }
        .badge-internal { background-color: #569cd6; color: #000; }
        .badge-disabled { background-color: #f48771; color: #000; }
        .badge-mode { background-color: #c586c0; color: #000; }
        button {
            background-color: #0e639c;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 3px;
            cursor: pointer;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            margin: 5px;
        }
        button:hover { background-color: #1177bb; }
        button:disabled {
            background-color: #3e3e42;
            color: #6e6e6e;
            cursor: not-allowed;
        }
        button.danger { background-color: #c94f4f; }
        button.danger:hover { background-color: #e06363; }
        button.success { background-color: #4ec9b0; color: #000; }
        button.success:hover { background-color: #5edcc0; }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
        }
        th, td {
            text-align: left;
            padding: 8px;
            border-bottom: 1px solid #3e3e42;
        }
        th { color: #569cd6; }
        .warning-box {
            background-color: #3d2a1f;
            border-left: 4px solid #ce9178;
            padding: 15px;
            margin: 15px 0;
        }
        .info-box {
            background-color: #1f2d3d;
            border-left: 4px solid #569cd6;
            padding: 15px;
            margin: 15px 0;
        }
        .success-box {
            background-color: #1f3d2f;
            border-left: 4px solid #4ec9b0;
            padding: 15px;
            margin: 15px 0;
        }
        code {
            background-color: #1e1e1e;
            padding: 2px 6px;
            border-radius: 3px;
            color: #ce9178;
        }
        #message {
            display: none;
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
        }
        #message.show { display: block; }
        #message.success { background-color: #1f3d2f; border-left: 4px solid #4ec9b0; }
        #message.error { background-color: #3d1f1f; border-left: 4px solid #f48771; }
    </style>
</head>
<body>
    <h1>📡 WiFi Adapter Manager</h1>

    <div class="card">
        <strong>Operating Mode:</strong>
        <span class="badge badge-mode">{{ mode.upper() }}</span>
        {% if mode == 'auto' %}
            <p style="margin-top: 10px; color: #858585;">Automatically manages WiFi based on adapter detection</p>
        {% elif mode == 'manual' %}
            <p style="margin-top: 10px; color: #858585;">Manual control only - use buttons below</p>
        {% elif mode == 'safe' %}
            <p style="margin-top: 10px; color: #858585;">Only re-enables WiFi if no adapter detected (prevents lockout)</p>
        {% endif %}
    </div>

    {% if pending_reboot %}
    <div class="warning-box">
        <strong>⚠️ REBOOT REQUIRED</strong><br>
        Configuration changes have been made. A reboot is required for changes to take effect.
        <br><br>
        <button class="danger" onclick="rebootSystem()">Reboot Now</button>
    </div>
    {% endif %}

    <div id="message"></div>

    <h2>📶 Current Status</h2>
    <div class="card">
        <table>
            <tr>
                <th>Property</th>
                <th>Value</th>
            </tr>
            <tr>
                <td>External Adapter</td>
                <td>
                    {% if detection['has_external'] %}
                        <span class="status-good">✓ Detected</span>
                        <span class="badge badge-external">EXTERNAL</span>
                    {% else %}
                        <span class="status-warning">✗ Not detected</span>
                    {% endif %}
                </td>
            </tr>
            <tr>
                <td>Wireless Interfaces</td>
                <td>
                    {% if detection['interfaces'] %}
                        {{ ', '.join(detection['interfaces']) }}
                    {% else %}
                        <span class="status-error">None found</span>
                    {% endif %}
                </td>
            </tr>
            <tr>
                <td>Monitor Mode Capable</td>
                <td>
                    {% if detection['monitor_capable'] %}
                        <span class="status-good">{{ ', '.join(detection['monitor_capable']) }}</span>
                    {% else %}
                        <span class="status-warning">None</span>
                    {% endif %}
                </td>
            </tr>
            <tr>
                <td>Integrated WiFi Status</td>
                <td>
                    {% if is_disabled %}
                        <span class="status-error">DISABLED</span>
                        <span class="badge badge-disabled">dtoverlay=disable-wifi</span>
                    {% else %}
                        <span class="status-good">ENABLED</span>
                        <span class="badge badge-internal">ACTIVE</span>
                    {% endif %}
                </td>
            </tr>
            <tr>
                <td>Config File</td>
                <td><code>{{ config_path or 'Not found' }}</code></td>
            </tr>
            <tr>
                <td>Last Check</td>
                <td>{{ status['last_check'] or 'Never' }}</td>
            </tr>
            {% if status['last_action'] %}
            <tr>
                <td>Last Action</td>
                <td>{{ status['last_action'] }}</td>
            </tr>
            {% endif %}
        </table>
    </div>

    {% if detection['usb_adapters'] %}
    <h2>🔌 USB Wireless Adapters</h2>
    <div class="card">
        <table>
            <tr>
                <th>USB Device</th>
            </tr>
            {% for adapter in detection['usb_adapters'] %}
            <tr>
                <td><code>{{ adapter }}</code></td>
            </tr>
            {% endfor %}
        </table>
    </div>
    {% endif %}

    <h2>⚙️ Manual Controls</h2>
    <div class="card">
        {% if mode == 'manual' or mode == 'safe' %}
        <div class="info-box">
            <strong>ℹ️ Manual Mode Active</strong><br>
            Use the buttons below to manually control the integrated WiFi configuration.
        </div>
        {% endif %}

        <button class="success" onclick="checkAdapters()">🔄 Refresh Adapter List</button>

        {% if is_disabled %}
            <button class="success" onclick="toggleWifi(true)"
                    {% if not can_enable %}disabled{% endif %}>
                ✓ Enable Integrated WiFi
            </button>
            {% if not can_enable %}
                <p class="status-warning">⚠️ {{ enable_reason }}</p>
            {% endif %}
        {% else %}
            <button class="danger" onclick="toggleWifi(false)"
                    {% if not can_disable %}disabled{% endif %}>
                ✗ Disable Integrated WiFi
            </button>
            {% if not can_disable %}
                <p class="status-error">⚠️ {{ disable_reason }}</p>
            {% else %}
                <p class="status-warning">⚠️ Only disable if external adapter is working properly!</p>
            {% endif %}
        {% endif %}
    </div>

    <h2>📖 Information</h2>
    <div class="card">
        <h3>Why This Plugin?</h3>
        <p>
            Pwnagotchi requires a wireless interface to function. When using an external USB WiFi adapter
            (for 5GHz support or better range), the integrated WiFi must be disabled via
            <code>/boot/config.txt</code> to work properly. However, if the external adapter is removed,
            Pwnagotchi won't boot without a wireless interface.
        </p>
        <p>
            This plugin automatically detects external adapters and manages the configuration to prevent
            boot failures while ensuring proper operation with external adapters.
        </p>

        <h3>Operating Modes</h3>
        <ul>
            <li><strong>Auto:</strong> Automatically enables/disables integrated WiFi based on adapter detection</li>
            <li><strong>Safe:</strong> Only re-enables integrated WiFi if no adapter detected (prevents lockout)</li>
            <li><strong>Manual:</strong> Full manual control via web UI</li>
        </ul>

        <h3>Safety Features</h3>
        <ul>
            <li>✓ Prevents disabling WiFi without external adapter present</li>
            <li>✓ Verifies external adapter supports monitor mode</li>
            <li>✓ Atomic config.txt updates (no partial writes)</li>
            <li>✓ Persistent state tracking across reboots</li>
        </ul>
    </div>

    <script>
        function showMessage(text, type) {
            const msg = document.getElementById('message');
            msg.textContent = text;
            msg.className = 'show ' + type;
            setTimeout(() => { msg.classList.remove('show'); }, 5000);
        }

        function checkAdapters() {
            showMessage('Checking adapters...', 'success');
            fetch('/plugins/wifi_adapter_manager/check', { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    showMessage('Adapter check complete!', 'success');
                    setTimeout(() => location.reload(), 1000);
                })
                .catch(err => showMessage('Error: ' + err, 'error'));
        }

        function toggleWifi(enable) {
            const action = enable ? 'enable' : 'disable';
            const confirm_msg = enable
                ? 'Enable integrated WiFi? This is safe.'
                : 'Disable integrated WiFi? Only do this if external adapter is working!';

            if (!confirm(confirm_msg)) return;

            showMessage(action === 'enable' ? 'Enabling WiFi...' : 'Disabling WiFi...', 'success');

            const formData = new FormData();
            formData.append('enable', enable);

            fetch('/plugins/wifi_adapter_manager/toggle_wifi', {
                method: 'POST',
                body: formData
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    showMessage(data.message + (data.reboot_required ? ' - REBOOT REQUIRED' : ''), 'success');
                    setTimeout(() => location.reload(), 2000);
                } else {
                    showMessage('Error: ' + data.message, 'error');
                }
            })
            .catch(err => showMessage('Error: ' + err, 'error'));
        }

        function rebootSystem() {
            if (!confirm('Reboot the system now? This will disconnect your session.')) return;

            showMessage('Rebooting system...', 'success');
            fetch('/plugins/wifi_adapter_manager/reboot', { method: 'POST' })
                .then(() => {
                    showMessage('Reboot initiated. Pwnagotchi will be back shortly!', 'success');
                })
                .catch(err => showMessage('Error: ' + err, 'error'));
        }
    </script>
</body>
</html>
"""
