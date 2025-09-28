# Pwnagotchi Handshakes Upload to S3
# This plugin automatically attempts to install boto3 if it's not available
# Dependencies: boto3 (auto-installation attempted, see README for manual install)
# 
# IMPORTANT: If auto-installation fails, manually install boto3:
#   sudo apt install python3-boto3
#   OR
#   pip3 install boto3 --break-system-packages
import pwnagotchi.plugins as plugins
import pwnagotchi
import logging
import datetime
import json
import os
import subprocess
import time
import hashlib
from threading import Lock
from pwnagotchi.utils import StatusFile
from json import JSONDecodeError
from flask import abort, render_template_string, Response, url_for

try:
    from flask_wtf.csrf import generate_csrf
except ImportError:  # pragma: no cover - fallback when csrf extension unavailable
    def generate_csrf():
        return ''

# Try to import boto3, install if not available
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

TAG = "[S3 Plugin]"

WEB_STATUS_TEMPLATE = """
{% extends "base.html" %}
{% set active_page = "plugins" %}
{% block title %}S3 Upload Status{% endblock %}

{% block styles %}
{{ super() }}
<style>
  .s3-status .card {
    margin-bottom: 2rem;
  }

  .s3-status .card-title {
    margin-bottom: 1rem;
    font-weight: 600;
    color: #263238;
  }

  .s3-status .status-meta {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 1rem;
  }

  .s3-status .status-chip {
    background: #eceff1;
    border-radius: 12px;
    padding: 0.9rem 1.1rem;
    line-height: 1.45;
    box-shadow: inset 0 0 0 1px rgba(120, 144, 156, 0.18);
  }

  .s3-status .status-chip .label {
    text-transform: uppercase;
    font-size: 0.7rem;
    letter-spacing: 0.08em;
    color: #546e7a;
    display: block;
    margin-bottom: 0.35rem;
  }

  .s3-status .status-chip .value {
    font-weight: 600;
    font-size: 0.95rem;
    word-break: break-word;
    color: #1c313a;
  }

  .s3-status .card-action {
    display: flex;
    justify-content: flex-end;
  }

  .s3-status .card-action .btn {
    background-color: #546e7a;
  }

  .s3-status .card-action .btn:hover {
    background-color: #455a64;
  }

  .s3-status .table-wrapper {
    margin-top: 1rem;
    overflow-x: auto;
    border-radius: 12px;
    border: 1px solid rgba(176, 190, 197, 0.6);
  }

  .s3-status table {
    margin-bottom: 0;
    width: 100%;
    min-width: 640px;
    border-collapse: collapse;
  }

  .s3-status table thead th {
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 0.72rem;
    color: #455a64;
    background-color: #eceff1;
    border-bottom: 1px solid rgba(120, 144, 156, 0.3);
  }

  .s3-status table td,
  .s3-status table th {
    padding: 0.85rem 1rem;
  }

  .s3-status table tbody tr:nth-child(even) {
    background-color: rgba(236, 239, 241, 0.35);
  }

  .s3-status table tbody tr:hover {
    background-color: rgba(207, 216, 220, 0.5);
  }

  .s3-status table tbody td {
    font-size: 0.9rem;
    color: #37474f;
  }

  .s3-status td code,
  .s3-status td .mono {
    word-break: break-all;
    font-family: "Roboto Mono", "Source Code Pro", monospace;
    font-size: 0.85rem;
    color: #263238;
  }

  .s3-status td code {
    background-color: rgba(207, 216, 220, 0.35);
    padding: 0.2rem 0.35rem;
    border-radius: 4px;
    display: inline-block;
  }

  .s3-status .truncate {
    display: inline-flex;
    align-items: center;
    max-width: 100%;
  }

  .s3-status .inline-form {
    display: inline-flex;
    align-items: center;
  }

  .s3-status .inline-form button {
    padding: 0;
  }

  .s3-status .inline-form button.icon-only {
    width: 2.5rem;
    height: 2.5rem;
    border-radius: 999px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }
  .s3-status .inline-form button.icon-only i {
    font-size: 1.25rem;
  }

  .s3-status th.right-align,
  .s3-status td.right-align {
    text-align: right;
  }

  @media (max-width: 720px) {
    .s3-status .table-wrapper {
      overflow: visible;
    }

    .s3-status table,
    .s3-status thead,
    .s3-status tbody,
    .s3-status th,
    .s3-status td,
    .s3-status tr {
      display: block;
    }

    .s3-status thead tr {
      display: none;
    }

    .s3-status tr {
      margin-bottom: 1.2rem;
      border: 1px solid rgba(176, 190, 197, 0.6);
      border-radius: 6px;
      padding: 0.75rem;
    }

    .s3-status td {
      border: none;
      position: relative;
      padding-left: 45%;
      min-height: 2.5rem;
    }

    .s3-status td::before {
      content: attr(data-label);
      position: absolute;
      left: 0.9rem;
      width: 42%;
      font-weight: 600;
      color: #546e7a;
      text-transform: uppercase;
      font-size: 0.7rem;
      letter-spacing: 0.08em;
    }

    .s3-status td[data-label="Actions"] {
      padding-left: 1rem;
    }

    .s3-status td[data-label="Actions"]::before {
      display: none;
    }

    .s3-status .inline-form {
      justify-content: flex-end;
    }

    .s3-status .inline-form button {
      width: 2.5rem;
      height: 2.5rem;
    }
  }
</style>
{% endblock %}

{% block content %}
<div class="s3-status">
  {% if feedback %}
  <div class="card-panel {{ 'green lighten-5' if feedback.category == 'success' else 'red lighten-5' }}">
    <span class="{{ 'green-text text-darken-4' if feedback.category == 'success' else 'red-text text-darken-4' }}">{{ feedback.message }}</span>
  </div>
  {% endif %}

  <div class="card">
    <div class="card-content">
      <span class="card-title">Status Overview</span>
      <div class="status-meta">
        <div class="status-chip">
          <span class="label">Status file</span>
          <span class="value">{{ status_path }}</span>
        </div>
        <div class="status-chip">
          <span class="label">Exists</span>
          <span class="value">{{ 'Yes' if status_exists else 'No' }}</span>
        </div>
        <div class="status-chip">
          <span class="label">Last updated</span>
          <span class="value">{{ status_mtime or 'Never' }}</span>
        </div>
        <div class="status-chip">
          <span class="label">Total uploaded (unique)</span>
          <span class="value">{{ status_summary.total_uploaded }}</span>
        </div>
        <div class="status-chip">
          <span class="label">Last upload</span>
          <span class="value">{{ status_summary.last_upload }}</span>
        </div>
        <div class="status-chip">
          <span class="label">Total handshakes found</span>
          <span class="value">{{ status_summary.total_handshakes }}</span>
        </div>
        <div class="status-chip">
          <span class="label">Pending uploads</span>
          <span class="value">{{ status_summary.pending_count }}</span>
        </div>
        <div class="status-chip">
          <span class="label">Tracked records</span>
          <span class="value">{{ uploaded_records|length }}</span>
        </div>
      </div>
    </div>
    <div class="card-action">
      <a href="{{ status_download_url }}" class="btn" download>Download status JSON</a>
    </div>
  </div>

  <div class="card">
    <div class="card-content">
      <span class="card-title">Tracked Uploads</span>
      {% if uploaded_records %}
      <div class="table-wrapper">
        <table class="responsive-table striped highlight">
          <thead>
            <tr>
              <th scope="col">File</th>
              <th scope="col">Checksum</th>
              <th scope="col">Size</th>
              <th scope="col">Uploaded</th>
              <th scope="col">Last Updated</th>
              <th scope="col" class="right-align">Actions</th>
            </tr>
          </thead>
          <tbody>
            {% for record in uploaded_records %}
            <tr>
              <td data-label="File"><span class="truncate mono">{{ record.display_path }}</span></td>
              <td data-label="Checksum"><code>{{ record.display_checksum }}</code></td>
              <td data-label="Size">{{ record.display_size }}</td>
              <td data-label="Uploaded">{{ record.uploaded_at }}</td>
              <td data-label="Last Updated">{{ record.updated_at }}</td>
              <td data-label="Actions" class="right-align">
                <form method="post" action="{{ page_url }}" class="inline-form">
                  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                  <input type="hidden" name="action" value="clear">
                  <input type="hidden" name="identifier" value="{{ record.clear_identifier }}">
                  <button type="submit" class="btn-flat btn-small waves-effect waves-light red-text text-darken-2 icon-only" title="Remove this record" aria-label="Remove this record">
                    <i class="material-icons" aria-hidden="true">delete</i>
                  </button>
                </form>
              </td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
      {% else %}
      <p class="grey-text text-darken-1">No upload records available.</p>
      {% endif %}
    </div>
  </div>
</div>
{% endblock %}
"""

class PwnS3Upload(plugins.Plugin):
    __author__ = 'gallis-local'
    __version__ = '2.0.0'
    __license__ = 'GPL3'
    __description__ = 'Upload handshake files to S3 storage'

    def __init__(self):
        self.ready = False
        self.options = dict()
        self._handshakes_dir = '/home/pi/handshakes'  # Default path
        self._status_path = '/root/.s3_uploads'
        try:
            self.report = StatusFile(self._status_path, data_format='json')
        except JSONDecodeError:
            os.remove(self._status_path)
            self.report = StatusFile(self._status_path, data_format='json')
        self.lock = Lock()

        self._status_data = self._load_status_data()

        # In-memory checksum cache to avoid recomputing hashes repeatedly
        persisted_cache = self.status_field_or('checksum_cache', default={})
        if isinstance(persisted_cache, dict):
            self._checksum_cache = dict(persisted_cache)
        else:
            self._checksum_cache = {}
        
        # Ensure boto3 dependencies are available
        self.ensure_dependencies()

    def _load_status_data(self):
        """Return the persisted status data stored on disk."""
        try:
            with open(self._status_path, 'r', encoding='utf-8') as handle:
                data = json.load(handle)
        except FileNotFoundError:
            return {}
        except (OSError, ValueError, TypeError) as exc:
            self.LogInfo(f"Failed to load status file {self._status_path}: {exc}")
            return {}

        if isinstance(data, dict):
            return data

        self.LogInfo(
            f"Unexpected data format in status file {self._status_path} - resetting cache"
        )
        return {}

    def _persist_status_data(self):
        """Persist the in-memory status data to disk and the StatusFile helper."""
        tmp_path = f"{self._status_path}.tmp"
        try:
            with open(tmp_path, 'w', encoding='utf-8') as handle:
                json.dump(self._status_data, handle, ensure_ascii=False, indent=2, sort_keys=True)
            os.replace(tmp_path, self._status_path)
        except OSError as exc:
            self.LogInfo(f"Failed to persist status file {self._status_path}: {exc}")
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass
        else:
            try:
                self.report.update(data=self._status_data)
            except Exception as exc:
                self.LogDebug(f"Unable to sync StatusFile helper: {exc}")

    def _refresh_status_data_from_disk(self):
        """Reload the status data from disk when external updates occur."""
        loaded = self._load_status_data()
        if loaded != self._status_data:
            self._status_data = loaded

        checksum_cache = self._status_data.get('checksum_cache')
        if isinstance(checksum_cache, dict):
            self._checksum_cache = dict(checksum_cache)
        else:
            self._checksum_cache = {}

    def status_field_or(self, field, default=None):
        """Return a status field value without exposing mutable references."""
        value = self._status_data.get(field, default)
        if isinstance(value, dict):
            return dict(value)
        if isinstance(value, list):
            return list(value)
        return value

    def _update_status_data(self, updates):
        """Merge updates into the status data and persist the result."""
        if not isinstance(updates, dict):
            return

        changed = False
        for key, value in updates.items():
            if self._status_data.get(key) != value:
                self._status_data[key] = value
                changed = True

        if changed:
            self._persist_status_data()
            if 'checksum_cache' in updates and isinstance(updates['checksum_cache'], dict):
                self._checksum_cache = dict(updates['checksum_cache'])

    def ensure_dependencies(self):
        """Ensure required dependencies are installed"""
        global BOTO3_AVAILABLE, boto3, ClientError, NoCredentialsError, BotoCoreError
        
        if not BOTO3_AVAILABLE:
            deps = ["boto3"]
            for dep in deps:
                # Try multiple installation methods
                installation_methods = [
                    # Method 1: Try with --break-system-packages (for modern Python environments)
                    ["pip3", "install", dep, "--break-system-packages"],
                    # Method 2: Try with system package manager
                    ["apt", "install", "-y", f"python3-{dep}"],
                    # Method 3: Try regular pip (for older systems)
                    ["pip3", "install", dep],
                    # Method 4: Try pip without sudo
                    ["python3", "-m", "pip", "install", dep, "--user"]
                ]
                
                for method in installation_methods:
                    try:
                        self.LogInfo(f"Attempting to install {dep} using: {' '.join(method)}")
                        result = subprocess.run(
                            method,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            check=True,
                            text=True
                        )
                        self.LogInfo(f"Successfully installed {dep} using: {' '.join(method)}")
                        
                        # Try to import after installation
                        if dep == "boto3":
                            import boto3
                            from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError
                            BOTO3_AVAILABLE = True
                            self.LogInfo("boto3 is now available")
                            return  # Success, exit early
                            
                    except subprocess.CalledProcessError as e:
                        self.LogInfo(f"Method failed ({' '.join(method)}): {e.stderr}")
                        continue  # Try next method
                    except ImportError:
                        self.LogInfo(f"Failed to import {dep} after installation with {' '.join(method)}")
                        continue  # Try next method
                    except Exception as e:
                        self.LogInfo(f"Unexpected error with method {' '.join(method)}: {e}")
                        continue  # Try next method
                
                # If we get here, all methods failed
                self.LogInfo(f"All installation methods failed for {dep}. Please install manually:")
                self.LogInfo(f"  Option 1: sudo apt install python3-boto3")
                self.LogInfo(f"  Option 2: pip3 install boto3 --break-system-packages")
                self.LogInfo(f"  Option 3: sudo pip3 install boto3 --break-system-packages")

    def _check_boto3_available(self):
        """Check if boto3 is available, try to install if not"""
        global BOTO3_AVAILABLE, boto3, ClientError, NoCredentialsError, BotoCoreError
        
        if BOTO3_AVAILABLE:
            return True
            
        # Try to import boto3 in case it was installed outside this plugin
        try:
            import boto3
            from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError
            BOTO3_AVAILABLE = True
            return True
        except ImportError:
            # Try to install it
            self.ensure_dependencies()
            return BOTO3_AVAILABLE

    # Log Functions
    def LogInfo(self, text):
        logging.info(TAG + " " +text)
    
    # Log Functions
    def LogDebug(self, text):
        logging.debug(TAG + " " +text)
    
    # Configuration changed callback
    def on_config_changed(self, config):
        """Called when the configuration changes"""
        # Get handshakes directory from bettercap config
        if 'bettercap' in config and 'handshakes' in config['bettercap']:
            self._handshakes_dir = config['bettercap']['handshakes']
        else:
            self._handshakes_dir = '/home/pi/handshakes'  # Default
        
        self.LogInfo(f"Configuration loaded - handshakes directory: {self._handshakes_dir}")
        
        # Enhanced configuration debugging
        self.LogInfo("=== S3 Plugin Configuration Debug ===")
        self.LogInfo(f"Raw plugin options count: {len(self.options) if self.options else 0}")
        self.LogInfo(f"Plugin options keys: {list(self.options.keys()) if self.options else 'None'}")
        
        if self.options:
            # Log configuration without sensitive data
            config_summary = {}
            for key, value in self.options.items():
                if key in ['secret_key']:
                    config_summary[key] = "***" + str(value)[-4:] if value and len(str(value)) > 4 else "***"
                elif key in ['access_key']:
                    config_summary[key] = str(value)[:8] + "..." if value and len(str(value)) > 8 else "***"
                else:
                    config_summary[key] = value
            
            self.LogInfo(f"S3 Plugin configuration summary: {config_summary}")
            
            # Check for MinIO vs AWS configuration
            if self.options.get('endpoint_url'):
                self.LogInfo(f"🔧 MinIO configuration detected - endpoint: {self.options.get('endpoint_url')}")
                # Validate MinIO specific requirements
                required_fields = ['bucket', 'access_key', 'secret_key', 'endpoint_url']
                missing_fields = [field for field in required_fields if not self.options.get(field)]
                if missing_fields:
                    self.LogInfo(f"❌ MinIO config incomplete - missing: {missing_fields}")
                else:
                    self.LogInfo("✅ MinIO configuration appears complete")
            else:
                self.LogInfo("🔧 AWS S3 configuration detected (no endpoint_url)")
                # Validate AWS specific requirements
                required_fields = ['bucket', 'region', 'access_key', 'secret_key']
                missing_fields = [field for field in required_fields if not self.options.get(field)]
                if missing_fields:
                    self.LogInfo(f"❌ AWS S3 config incomplete - missing: {missing_fields}")
                else:
                    self.LogInfo("✅ AWS S3 configuration appears complete")
            
            # Check for empty values
            empty_fields = [key for key, value in self.options.items() 
                          if value is None or (isinstance(value, str) and value.strip() == '')]
            if empty_fields:
                self.LogInfo(f"⚠️  Empty configuration fields detected: {empty_fields}")
        else:
            self.LogInfo("❌ CRITICAL: No plugin options loaded!")
            self.LogInfo("   This usually means:")
            self.LogInfo("   1. Plugin not enabled in config.toml: main.plugins.s3_upload.enabled = true")
            self.LogInfo("   2. Configuration not in correct location: /etc/pwnagotchi/config.toml")
            self.LogInfo("   3. Invalid TOML syntax in configuration file")
            self.LogInfo("   4. Plugin configuration section missing or incorrectly formatted")
        
        self.LogInfo("=== End Configuration Debug ===")
        
        # Also log the full pwnagotchi config structure for debugging (filtered)
        if config:
            self.LogInfo("Pwnagotchi config structure inspection:")
            if 'main' in config:
                if 'plugins' in config['main']:
                    available_plugins = list(config['main']['plugins'].keys()) if config['main']['plugins'] else []
                    self.LogInfo(f"  Available plugins in config: {available_plugins}")
                    
                    if 's3_upload' in available_plugins:
                        s3_config_raw = config['main']['plugins']['s3_upload']
                        self.LogInfo(f"  Raw s3_upload config from main config: {list(s3_config_raw.keys()) if s3_config_raw else 'None'}")
                    else:
                        self.LogInfo("  s3_upload plugin not found in main.plugins section")
                else:
                    self.LogInfo("  No 'plugins' section found in main config")
            else:
                self.LogInfo("  No 'main' section found in config")

    # Log Functions - Loaded
    def on_loaded(self):
        self.ready = True
        uploaded_count = len(self.status_field_or('uploaded_files', default=[]))
        self.LogInfo(f"Pwnagotchi S3 Handshakes Upload Loaded. {uploaded_count} files previously uploaded.")
        
        # Debug: Check if options are loaded at startup
        self.LogInfo(f"Plugin loaded with {len(self.options)} configuration options")
        if not self.options:
            self.LogInfo("WARNING: Plugin options are empty at startup - configuration may not be loaded yet")
        
        # Log configuration status
        s3_config = self.get_s3_config()
        if s3_config:
            self.LogInfo(f"S3 configuration validated - ready for uploads to bucket: {s3_config['bucket']}")
            # Log credential info (without exposing secrets)
            access_key_preview = s3_config['access_key'][:8] + "..." if len(s3_config['access_key']) > 8 else "***"
            secret_key_preview = "***" + s3_config['secret_key'][-4:] if len(s3_config['secret_key']) > 4 else "***"
            self.LogDebug(f"Using AWS credentials: {access_key_preview} / {secret_key_preview}")
        else:
            self.LogInfo("S3 configuration incomplete - please check plugin configuration")

    # Log Functions - Unloaded
    def on_unload(self, ui):
        self.LogInfo("Pwnagotchi S3 Upload Unloaded.")

    # Get the handshakes directory from configuration
    def get_handshakes_dir(self):
        # Default handshakes path if not configured
        return self._handshakes_dir if hasattr(self, '_handshakes_dir') else '/home/pi/handshakes'
    
    # Get the config values for S3
    def get_s3_config(self):
        # Use self.options which contains the plugin configuration
        s3_config = self.options
        
        # Debug: Log what we actually have in options
        self.LogDebug(f"Current plugin options: {list(s3_config.keys()) if s3_config else 'None'}")
        
        if not s3_config:
            self.LogInfo("No S3 configuration found in plugin options")
            return None
        
        # Check if required fields are present and not empty
        if 'bucket' not in s3_config or not s3_config['bucket']:
            self.LogInfo(f"Missing or empty S3 Config - Bucket. Available keys: {list(s3_config.keys())}")
            return None
        if 'region' not in s3_config or not s3_config['region']:
            self.LogInfo(f"Missing or empty S3 Config - Region. Available keys: {list(s3_config.keys())}")
            return None
        if 'access_key' not in s3_config or not s3_config['access_key']:
            self.LogInfo(f"Missing or empty S3 Config - Access Key. Available keys: {list(s3_config.keys())}")
            return None
        if 'secret_key' not in s3_config or not s3_config['secret_key']:
            self.LogInfo(f"Missing or empty S3 Config - Secret Key. Available keys: {list(s3_config.keys())}")
            return None
        
        self.LogDebug(f"S3 config validated successfully - bucket: {s3_config['bucket']}")
        return s3_config
    

        
    # Get the current date and time
    def get_current_datetime(self):
        return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    # Get list of handshake files
    def normalize_relative_path(self, handshakes_dir, file_path):
        """Return a normalized POSIX-style relative path for tracking."""
        relative_path = os.path.relpath(file_path, handshakes_dir)
        return relative_path.replace(os.sep, '/')

    def should_consider_file(self, relative_path):
        """Return True when a file should be considered for upload."""
        lower_name = relative_path.lower()
        basename = os.path.basename(lower_name)

        # Always include geo.json derivatives and hash/potfile exports
        if basename in {'geo.json'} or lower_name.endswith('.geo.json'):
            return True

        monitored_suffixes = (
            '.pcap', '.pcapng', '.cap', '.hccap', '.hccapx', '.pcap.gz', '.pcapng.gz',
            '.cap.gz', '.16800', '.22000', '.potfile', '.pot', '.hash', '.hc22000', '.hc16800'
        )
        if any(lower_name.endswith(suffix) for suffix in monitored_suffixes):
            return True

        # Skip obvious temporary/editor files but include everything else for compatibility
        ignored_suffixes = ('.tmp', '.swp', '.lock', '.part')
        if basename.startswith('.') or lower_name.endswith(ignored_suffixes):
            return False

        return True

    def get_handshake_files(self):
        handshakes_dir = self.get_handshakes_dir()
        if not os.path.exists(handshakes_dir):
            return []

        handshake_files = []
        for root, dirs, files in os.walk(handshakes_dir):
            dirs.sort()
            files.sort()
            for file_name in files:
                file_path = os.path.join(root, file_name)
                if not os.path.isfile(file_path):
                    continue

                relative_path = self.normalize_relative_path(handshakes_dir, file_path)
                if self.should_consider_file(relative_path):
                    handshake_files.append(relative_path)

        return handshake_files
    
    def get_uploaded_records(self):
        """Return normalized upload records stored in the status file."""
        raw_records = self.status_field_or('uploaded_files', default=[])

        normalized_records = []
        for item in raw_records:
            if isinstance(item, dict):
                record = dict(item)
            elif isinstance(item, str):
                # Backwards compatibility with filename-only tracking
                record = {'filename': item}
            else:
                continue

            if 'path' not in record:
                if record.get('filename'):
                    record['path'] = record['filename']
                elif record.get('relative_path'):
                    record['path'] = record['relative_path']

            normalized_records.append(record)

        # Ensure the status file always stores the normalized representation
        if raw_records != normalized_records:
            self._update_status_data({
                'uploaded_files': normalized_records,
                'total_uploaded': len(normalized_records)
            })

        return normalized_records

    def get_uploaded_checksums(self):
        """Return a set of previously uploaded file checksums."""
        return {
            record['checksum']
            for record in self.get_uploaded_records()
            if record.get('checksum')
        }

    def get_uploaded_paths(self):
        """Return a set of previously uploaded relative paths (legacy support friendly)."""
        return {
            record.get('path') or record.get('filename')
            for record in self.get_uploaded_records()
            if record.get('path') or record.get('filename')
        }

    def get_file_checksum(self, file_path):
        """Calculate the SHA256 checksum for a file."""
        sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as file_handle:
                for chunk in iter(lambda: file_handle.read(65536), b''):
                    sha256.update(chunk)
        except (OSError, IOError) as exc:
            self.LogInfo(f"Failed to compute checksum for {file_path}: {exc}")
            return None
        return sha256.hexdigest()

    @staticmethod
    def _format_size(num_bytes):
        """Return a human readable string for a byte count."""
        if not isinstance(num_bytes, (int, float)) or num_bytes < 0:
            return 'n/a'

        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
        size = float(num_bytes)
        unit_index = 0
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024.0
            unit_index += 1

        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"

        return f"{size:.2f} {units[unit_index]}"

    def track_uploaded_file(self, relative_path, checksum):
        """Record a successfully uploaded file using its checksum."""
        if not relative_path and not checksum:
            return

        timestamp = self.get_current_datetime()
        records = self.get_uploaded_records()

        updated = False
        if checksum:
            for record in records:
                if record.get('checksum') == checksum:
                    # Update path if it changed, retain original timestamp
                    if relative_path and record.get('path') != relative_path:
                        record['path'] = relative_path
                        record['filename'] = os.path.basename(relative_path)
                        record['updated_at'] = timestamp
                    updated = True
                    break
        else:
            # Fall back to path-based tracking when checksum is unavailable
            for record in records:
                existing_path = record.get('path') or record.get('filename')
                if existing_path == relative_path:
                    updated = True
                    break

        if not updated:
            records.append({
                'path': relative_path,
                'filename': os.path.basename(relative_path),
                'checksum': checksum,
                'uploaded_at': timestamp
            })

        identifiers = [
            record.get('checksum') or record.get('path') or record.get('filename')
            for record in records
            if record.get('checksum') or record.get('path') or record.get('filename')
        ]
        total_unique = len(set(identifiers))

        self._update_status_data({
            'uploaded_files': records,
            'last_upload': timestamp,
            'total_uploaded': total_unique
        })
        self.LogInfo(
            f"Recorded upload for {relative_path} "
            f"({'checksum ' + checksum if checksum else 'no checksum'})"
        )

    def clear_uploaded_record(self, identifier):
        """Remove a tracked upload entry by checksum or path."""
        if not identifier:
            return False

        with self.lock:
            self._refresh_status_data_from_disk()
            records = self.get_uploaded_records()
            retained_records = []
            removed = False
            removed_paths = set()

            for record in records:
                record_identifiers = {
                    record.get('checksum'),
                    record.get('path'),
                    record.get('filename')
                }
                if identifier in record_identifiers:
                    removed = True
                    record_path = record.get('path') or record.get('filename')
                    if record_path:
                        removed_paths.add(record_path)
                    continue
                retained_records.append(record)

            if not removed:
                return False

            identifiers = [
                item.get('checksum') or item.get('path') or item.get('filename')
                for item in retained_records
                if item.get('checksum') or item.get('path') or item.get('filename')
            ]
            total_unique = len(set(identifiers))

            updates = {
                'uploaded_files': retained_records,
                'total_uploaded': total_unique
            }

            if removed_paths:
                cache = dict(self._checksum_cache) if self._checksum_cache else {}
                cache_modified = False
                for path in removed_paths:
                    if cache.pop(path, None) is not None:
                        cache_modified = True
                if cache_modified:
                    updates['checksum_cache'] = cache

            self._update_status_data(updates)
            return True

    # Get list of files that need to be uploaded
    def collect_pending_uploads(self):
        """Scan the handshake directory and build a chronologically ordered upload queue."""

        handshakes_dir = self.get_handshakes_dir()
        if not os.path.exists(handshakes_dir):
            return []

        self._refresh_status_data_from_disk()
        uploaded_records = self.get_uploaded_records()
        checksum_to_record = {}
        path_to_record = {}
        for record in uploaded_records:
            record_path = record.get('path') or record.get('filename')
            if record_path:
                path_to_record[record_path] = record
            record_checksum = record.get('checksum')
            if record_checksum:
                checksum_to_record[record_checksum] = record

        checksum_cache = self._checksum_cache
        if checksum_cache:
            checksum_cache = dict(checksum_cache)
        else:
            persisted_cache = self.status_field_or('checksum_cache', default={})
            checksum_cache = persisted_cache if isinstance(persisted_cache, dict) else {}

        updated_cache = {}
        pending_files = []
        scanned_file_count = 0
        records_updated = False

        for root, dirs, files in os.walk(handshakes_dir):
            dirs.sort()
            files.sort()

            for file_name in files:
                file_path = os.path.join(root, file_name)
                if not os.path.isfile(file_path):
                    continue

                relative_path = self.normalize_relative_path(handshakes_dir, file_path)
                if not self.should_consider_file(relative_path):
                    continue

                scanned_file_count += 1

                try:
                    stat_result = os.stat(file_path)
                    size = stat_result.st_size
                    mtime_ns = getattr(stat_result, 'st_mtime_ns', None)
                    if mtime_ns is None:
                        mtime_ns = int(stat_result.st_mtime * 1_000_000_000)
                except OSError as exc:
                    self.LogInfo(f"Failed to stat {file_path}: {exc}")
                    continue

                cache_entry = checksum_cache.get(relative_path)
                checksum = None
                metadata_matches = (
                    cache_entry
                    and cache_entry.get('size') == size
                    and cache_entry.get('mtime_ns') == mtime_ns
                )

                if metadata_matches and cache_entry.get('checksum'):
                    checksum = cache_entry.get('checksum')
                else:
                    checksum = self.get_file_checksum(file_path)

                if checksum:
                    updated_cache[relative_path] = {
                        'checksum': checksum,
                        'size': size,
                        'mtime_ns': mtime_ns
                    }
                elif cache_entry:
                    updated_cache[relative_path] = cache_entry

                record_for_checksum = checksum_to_record.get(checksum) if checksum else None
                record_for_path = path_to_record.get(relative_path)

                if record_for_checksum:
                    current_timestamp = None
                    existing_path = record_for_checksum.get('path') or record_for_checksum.get('filename')
                    if existing_path and existing_path != relative_path:
                        path_to_record.pop(existing_path, None)
                        record_for_checksum['path'] = relative_path
                        record_for_checksum['filename'] = os.path.basename(relative_path)
                        current_timestamp = current_timestamp or self.get_current_datetime()
                        record_for_checksum['updated_at'] = current_timestamp
                        records_updated = True

                    if record_for_checksum.get('size') != size:
                        record_for_checksum['size'] = size
                        current_timestamp = current_timestamp or self.get_current_datetime()
                        record_for_checksum['updated_at'] = current_timestamp
                        records_updated = True

                    if record_for_checksum.get('mtime_ns') != mtime_ns:
                        record_for_checksum['mtime_ns'] = mtime_ns
                        current_timestamp = current_timestamp or self.get_current_datetime()
                        record_for_checksum['updated_at'] = current_timestamp
                        records_updated = True

                    path_to_record[relative_path] = record_for_checksum
                    self.LogDebug(f"Skipping {relative_path} - checksum already uploaded")
                    continue

                if record_for_path and checksum:
                    record_for_path_checksum = record_for_path.get('checksum')
                    if record_for_path_checksum == checksum or not record_for_path_checksum:
                        current_timestamp = self.get_current_datetime()
                        record_for_path['checksum'] = checksum
                        record_for_path['size'] = size
                        record_for_path['mtime_ns'] = mtime_ns
                        record_for_path['path'] = relative_path
                        record_for_path['filename'] = os.path.basename(relative_path)
                        record_for_path['updated_at'] = current_timestamp
                        checksum_to_record[checksum] = record_for_path
                        records_updated = True
                        self.LogDebug(
                            f"Skipping {relative_path} - associated legacy record refreshed"
                        )
                        continue

                if not checksum and record_for_path:
                    self.LogDebug(
                        f"Skipping {relative_path} - path already uploaded (legacy tracking)"
                    )
                    continue

                pending_files.append({
                    'path': relative_path,
                    'local_path': file_path,
                    'checksum': checksum,
                    'size': size,
                    'mtime_ns': mtime_ns
                })

        if checksum_cache != updated_cache:
            self._update_status_data({'checksum_cache': updated_cache})
            self._checksum_cache = updated_cache
        else:
            self._checksum_cache = checksum_cache

        if records_updated:
            identifiers = [
                record.get('checksum') or record.get('path') or record.get('filename')
                for record in uploaded_records
                if record.get('checksum') or record.get('path') or record.get('filename')
            ]
            total_unique = len(set(identifiers))
            self._update_status_data({
                'uploaded_files': uploaded_records,
                'total_uploaded': total_unique
            })

        pending_files.sort(key=lambda item: (item.get('mtime_ns') or 0, item['path']))
        self.LogDebug(
            f"Queued {len(pending_files)} pending uploads from {scanned_file_count} eligible handshake files"
        )
        return pending_files
    
    # Get upload statistics for review
    def get_upload_stats(self):
        self._refresh_status_data_from_disk()
        uploaded_records = self.get_uploaded_records()
        all_files = self.get_handshake_files()
        pending_files = self.collect_pending_uploads()

        uploaded_file_names = [
            record.get('path') or record.get('filename') or record.get('checksum')
            for record in uploaded_records
        ]
        pending_file_names = [item['path'] for item in pending_files]

        return {
            'total_handshakes': len(all_files),
            'uploaded_count': len(uploaded_records),
            'pending_count': len(pending_files),
            'uploaded_files': uploaded_file_names,
            'pending_files': pending_file_names,
            'last_upload': self.status_field_or('last_upload', 'Never')
        }

    def on_webhook(self, path, request):
        """Serve S3 upload status information within the web UI."""
        normalized_path = (path or '').strip('/')

        if normalized_path in {'', None}:
            feedback = None
            if request.method == 'POST':
                action = request.form.get('action') if request.form else None
                if action == 'clear':
                    identifier = (request.form.get('identifier') or '').strip()
                    if identifier:
                        if self.clear_uploaded_record(identifier):
                            feedback = {
                                'category': 'success',
                                'message': f"Removed tracked entry for '{identifier}'."
                            }
                        else:
                            feedback = {
                                'category': 'error',
                                'message': f"No tracked entry matched '{identifier}'."
                            }
                    else:
                        feedback = {
                            'category': 'error',
                            'message': 'Unable to clear entry without an identifier.'
                        }
                else:
                    feedback = {
                        'category': 'error',
                        'message': 'Unsupported action requested.'
                    }

            self._refresh_status_data_from_disk()
            uploaded_records = self.get_uploaded_records()

            try:
                summary = self.get_upload_stats()
            except Exception as exc:
                self.LogDebug(f"Failed to refresh upload stats for web UI: {exc}")
                summary = {
                    'total_handshakes': 'n/a',
                    'pending_count': 'n/a',
                    'uploaded_count': len(uploaded_records),
                    'uploaded_files': [],
                    'pending_files': [],
                    'last_upload': self.status_field_or('last_upload', 'Never'),
                    'total_uploaded': self.status_field_or('total_uploaded', len(uploaded_records))
                }

            if 'total_uploaded' not in summary:
                summary['total_uploaded'] = self.status_field_or('total_uploaded', len(uploaded_records))

            status_exists = os.path.exists(self._status_path)
            status_mtime = None
            if status_exists:
                try:
                    mtime = os.path.getmtime(self._status_path)
                    status_mtime = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                except OSError:
                    status_mtime = None

            plugin_name = self.__module__.split('.')[-1]
            page_url = url_for('plugins', name=plugin_name)
            status_download_url = url_for('plugins', name=plugin_name, subpath='status.json')

            display_records = []
            for record in uploaded_records:
                identifier = record.get('checksum') or record.get('path') or record.get('filename')
                display_path = record.get('path') or record.get('filename') or 'n/a'
                display_records.append({
                    'display_path': display_path,
                    'display_checksum': record.get('checksum') or 'n/a',
                    'display_size': self._format_size(record.get('size')),
                    'uploaded_at': record.get('uploaded_at') or 'n/a',
                    'updated_at': record.get('updated_at') or record.get('uploaded_at') or 'n/a',
                    'clear_identifier': identifier or '',
                })

            return render_template_string(
                WEB_STATUS_TEMPLATE,
                status_path=self._status_path,
                status_exists=status_exists,
                status_mtime=status_mtime,
                status_summary=summary,
                uploaded_records=display_records,
                status_download_url=status_download_url,
                page_url=page_url,
                feedback=feedback,
                csrf_token=generate_csrf
            )

        if normalized_path == 'status.json':
            self._refresh_status_data_from_disk()
            response = Response(
                json.dumps(self._status_data, indent=2, sort_keys=True),
                mimetype='application/json'
            )
            response.headers['Content-Disposition'] = 'attachment; filename="s3_upload_status.json"'
            return response

        abort(404)
    
    # Get plugin configuration with defaults
    def get_plugin_config(self):
        plugin_config = self.options.copy()
        
        # Set defaults
        plugin_config.setdefault('max_retries', 3)
        plugin_config.setdefault('retry_delay', 5)
        
        return plugin_config
    
    # Get hostname for organizing files in S3
    def get_hostname(self):
        """Get the pwnagotchi hostname for S3 organization"""
        # Check if custom hostname is configured
        if 'hostname' in self.options and self.options['hostname']:
            hostname = self.options['hostname']
        else:
            try:
                import socket
                hostname = socket.gethostname()
            except:
                hostname = 'pwnagotchi'  # fallback name
        
        # Clean hostname for S3 (remove invalid characters and make S3-safe)
        hostname = hostname.replace('_', '-').replace(' ', '-').replace('.', '-').lower()
        # Remove any characters that aren't alphanumeric or hyphens
        hostname = ''.join(c for c in hostname if c.isalnum() or c == '-')
        # Ensure it doesn't start or end with hyphen
        hostname = hostname.strip('-')
        
        return hostname if hostname else 'pwnagotchi'

    # Get files ready for upload (individual files instead of archive)
    def get_files_for_upload(self, pending_files=None):
        handshakes_dir = self.get_handshakes_dir()
        if not os.path.exists(handshakes_dir):
            self.LogDebug("Handshakes directory does not exist")
            return []

        if pending_files is None:
            pending_files = self.collect_pending_uploads()

        if not pending_files:
            self.LogDebug("No new handshake files to upload")
            return []

        # Get hostname for S3 organization
        hostname = self.get_hostname()
        self.LogDebug(f"Using hostname for S3 organization: {hostname}")

        # Return full file paths for upload
        file_paths = []
        for file_info in pending_files:
            file_entry = file_info.copy()
            s3_relative_key = file_entry['path'].replace(os.sep, '/')
            file_entry['s3_key'] = f"{hostname}/{s3_relative_key}"
            file_paths.append(file_entry)

        self.LogInfo(f"Found {len(file_paths)} handshake files ready for upload to s3://bucket/{hostname}/")
        return file_paths


    
    # Upload file to S3 with retry logic
    def upload_file_to_s3(self, local_file_path, s3_key):
        # Check if boto3 is available, try to install if not
        if not self._check_boto3_available():
            self.LogInfo("boto3 not available and could not be installed - cannot upload to S3")
            return False
            
        s3_config = self.get_s3_config()
        if s3_config is None:
            self.LogDebug("S3 Config has an error - Not uploading to S3")
            return False
        
        # Create S3 client
        try:
            # Import boto3 locally to handle dynamic installation
            import boto3
            from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError
            from botocore.config import Config
            
            # Log configuration details (without secrets)
            self.LogDebug(f"S3 Configuration - Bucket: {s3_config['bucket']}, Region: {s3_config['region']}")
            if s3_config.get('endpoint_url'):
                self.LogDebug(f"Using custom S3 endpoint: {s3_config['endpoint_url']}")
            
            # MinIO-specific configuration
            is_minio = s3_config.get('endpoint_url') is not None
            
            # Configure boto3 for MinIO compatibility
            boto3_config = {}
            if is_minio:
                # MinIO typically requires path-style addressing and signature version 4
                boto3_config = Config(
                    signature_version='s3v4',
                    s3={
                        'addressing_style': 'path'  # Critical for MinIO
                    },
                    retries={'max_attempts': 1},  # Reduce retries for faster debugging
                    user_agent=f'pwnagotchi-upload/{self.__version__}'  # Custom user agent for identification
                )
                self.LogInfo("Configured boto3 for MinIO with path-style addressing, signature v4, and custom user agent")
                
                # For MinIO, region is often not critical, but let's ensure it's set
                if s3_config['region'] in ['', None]:
                    s3_config['region'] = 'us-east-1'  # MinIO default
                    self.LogInfo("Set default region 'us-east-1' for MinIO")
            else:
                # Standard AWS S3 configuration
                boto3_config = Config(
                    signature_version='s3v4',
                    retries={'max_attempts': 3},
                    user_agent=f'pwnagotchi-upload/{self.__version__}'  # Custom user agent for identification
                )
            
            s3_client = boto3.client(
                's3',
                aws_access_key_id=s3_config['access_key'],
                aws_secret_access_key=s3_config['secret_key'],
                region_name=s3_config['region'],
                endpoint_url=s3_config.get('endpoint_url'),
                config=boto3_config
            )
            
            self.LogDebug("S3 client created successfully")
            
            # Check if this is MinIO or AWS S3
            is_minio = s3_config.get('endpoint_url') is not None
            
            # Basic bucket access check
            try:
                s3_client.head_bucket(Bucket=s3_config['bucket'])
                self.LogDebug(f"Bucket access verified: {s3_config['bucket']}")
            except Exception as bucket_error:
                if hasattr(bucket_error, 'response') and 'Error' in bucket_error.response:
                    error_code = bucket_error.response['Error']['Code']
                    if error_code == '404':
                        self.LogInfo(f"Bucket not found: {s3_config['bucket']} - check bucket name and region")
                        return False
                    elif error_code == '403':
                        self.LogDebug("Bucket access denied - continuing with upload attempt")
                else:
                    self.LogDebug(f"Bucket check failed: {bucket_error}")
                # Continue anyway as some configurations don't allow ListBucket but allow PutObject
            
        except ImportError as e:
            self.LogInfo(f"boto3 still not available after installation attempt: {e}")
            return False
        except Exception as e:
            self.LogInfo(f"Failed to create S3 client: {type(e).__name__} - {e}")
            return False
        
        # Get retry settings from config
        plugin_config = self.get_plugin_config()
        max_retries = plugin_config.get('max_retries', 3)
        retry_delay = plugin_config.get('retry_delay', 5)
        
        # Retry upload with exponential backoff
        for attempt in range(max_retries):
            try:
                # Import exceptions locally for each attempt
                from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError
                
                self.LogDebug(f"Uploading {local_file_path} to s3://{s3_config['bucket']}/{s3_key} (attempt {attempt + 1})")
                
                # For MinIO, avoid metadata to prevent signature issues
                extra_args = {}
                if not is_minio:
                    # Only add metadata for AWS S3, not MinIO
                    # Use actual pwnagotchi hostname for identification
                    pwnagotchi_hostname = self.get_hostname()
                    extra_args['Metadata'] = {
                        'uploaded_by': f'pwnagotchi-{pwnagotchi_hostname}',
                        'upload_time': self.get_current_datetime()
                    }
                
                s3_client.upload_file(
                    local_file_path, 
                    s3_config['bucket'], 
                    s3_key,
                    ExtraArgs=extra_args
                )
                
                self.LogInfo(f"Successfully uploaded {s3_key} to S3")
                return True
                
            except Exception as e:
                error_type = type(e).__name__
                error_message = str(e)
                self.LogInfo(f"Upload attempt {attempt + 1} failed: {error_type} - {error_message}")
                
                # Handle ClientError specifically if available
                if 'ClientError' in str(type(e)) and hasattr(e, 'response'):
                    error_code = e.response['Error']['Code']
                    error_msg = e.response['Error'].get('Message', 'No message')
                    self.LogInfo(f"S3 Error - Code: {error_code}, Message: {error_msg}")
                    
                    # Handle specific error cases
                    if error_code == 'AccessDenied' or error_code == '403':
                        if is_minio:
                            self.LogInfo("MinIO access denied - check bucket policy and user permissions")
                        else:
                            self.LogInfo("AWS S3 access denied - check IAM permissions")
                        return False
                    elif error_code in ['NoSuchBucket', 'InvalidAccessKeyId', 'SignatureDoesNotMatch']:
                        # These are permanent errors, don't retry
                        self.LogInfo(f"Permanent S3 error: {error_code} - {error_msg}")
                        if error_code == 'SignatureDoesNotMatch' and is_minio:
                            self.LogInfo("MinIO signature mismatch - check access/secret keys are correct")
                        return False
                elif 'NoCredentialsError' in str(type(e)):
                    self.LogInfo("S3 credentials not found or invalid")
                    return False
                elif 'EndpointConnectionError' in str(type(e)):
                    if s3_config.get('endpoint_url'):
                        self.LogInfo(f"Cannot connect to MinIO endpoint: {s3_config['endpoint_url']} - check URL and network connectivity")
                    else:
                        self.LogInfo("Cannot connect to S3 endpoint - check network connectivity")
                elif 'ConnectTimeoutError' in str(type(e)):
                    self.LogInfo("Connection timeout - check network connectivity and endpoint URL")
                elif 'SSLError' in str(type(e)):
                    self.LogInfo("SSL/TLS error - for MinIO, try using HTTP instead of HTTPS in endpoint_url")
                else:
                    self.LogInfo(f"Upload error: {error_type} - {error_message}")
                    if is_minio:
                        self.LogInfo("Check MinIO endpoint URL, credentials, and bucket permissions")
            
            # Wait before retrying (exponential backoff)
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)
                self.LogDebug(f"Retrying upload in {wait_time} seconds...")
                time.sleep(wait_time)
        
        self.LogInfo(f"Failed to upload {s3_key} after {max_retries} attempts")
        return False
    
    # Main upload method for handshakes
    def upload_handshakes_to_s3(self, files_for_upload):
        if not files_for_upload:
            self.LogDebug("No files ready for upload - skipping")
            return False
        
        uploaded_files = []
        failed_files = []
        
        self.LogInfo(f"Starting upload of {len(files_for_upload)} handshake files")
        
        for file_info in files_for_upload:
            local_path = file_info['local_path']
            relative_path = file_info['path']
            s3_key = file_info['s3_key']
            checksum = file_info.get('checksum')

            self.LogDebug(f"Uploading file: {relative_path}")

            success = self.upload_file_to_s3(local_path, s3_key)

            if success:
                uploaded_files.append(relative_path)
                self.track_uploaded_file(relative_path, checksum)
                self.LogInfo(f"Successfully uploaded: {relative_path}")
            else:
                failed_files.append(relative_path)
                self.LogInfo(f"Failed to upload: {relative_path}")

        if uploaded_files:
            self.LogInfo(f"Upload summary: {len(uploaded_files)} successful, {len(failed_files)} failed")

        if failed_files:
            self.LogInfo(f"Failed uploads: {', '.join(failed_files)}")

        # Return True if at least one file was uploaded successfully
        return len(uploaded_files) > 0

    # Upload to S3 when internet is available and there are new handshakes
    def on_internet_available(self, agent):
        if not self.ready or self.lock.locked():
            self.LogDebug("Plugin not ready or locked")
            return
            
        if not self._check_boto3_available():
            self.LogDebug("boto3 not available - skipping upload")
            return
            
        with self.lock:
            display = agent.view()
            self.LogDebug("Internet is available, checking for new handshakes")
            
            try:
                pending_files = self.collect_pending_uploads()
                if pending_files:
                    upload_queue = self.get_files_for_upload(pending_files)
                    self.LogDebug(f"New handshakes detected - uploading {len(upload_queue)} files to S3")
                    success = self.upload_handshakes_to_s3(upload_queue)

                    # Update status report
                    uploaded_records = self.get_uploaded_records()
                    self._update_status_data({
                        'last_upload_attempt': self.get_current_datetime(),
                        'last_upload_success': success,
                        'uploaded_files': uploaded_records,
                        'total_uploaded': len(uploaded_records)
                    })
                    
                    if success:
                        self.LogInfo("Handshakes successfully uploaded to S3")
                    else:
                        self.LogInfo("Failed to upload handshakes to S3")
                else:
                    self.LogDebug("No new handshakes to upload")
                    
            except Exception as e:
                self.LogInfo(f"Error during upload process: {e}")
            finally:
                display.on_normal()
