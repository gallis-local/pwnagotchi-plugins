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
import os
import subprocess
import tempfile
import time
from threading import Lock
from pwnagotchi.utils import StatusFile
from json import JSONDecodeError

# Try to import boto3, install if not available
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

TAG = "[S3 Plugin]"

class PwnS3Upload(plugins.Plugin):
    __author__ = 'gallis-local'
    __version__ = '2.0.0'
    __license__ = 'GPL3'
    __description__ = 'Upload handshake files to S3 storage'

    def __init__(self):
        self.ready = False
        self.options = dict()
        self._handshakes_dir = '/home/pi/handshakes'  # Default path
        try:
            self.report = StatusFile('/root/.s3_uploads', data_format='json')
        except JSONDecodeError:
            os.remove('/root/.s3_uploads')
            self.report = StatusFile('/root/.s3_uploads', data_format='json')
        self.lock = Lock()
        
        # Ensure boto3 dependencies are available
        self.ensure_dependencies()

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
        uploaded_count = len(self.report.data_field_or('uploaded_files', default=[]))
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
    def get_handshake_files(self):
        handshakes_dir = self.get_handshakes_dir()
        if not os.path.exists(handshakes_dir):
            return []
        
        handshake_files = []
        for file in os.listdir(handshakes_dir):
            filepath = os.path.join(handshakes_dir, file)
            if os.path.isfile(filepath):
                handshake_files.append(file)
        return handshake_files
    
    # Track uploaded files by filename
    def track_uploaded_files(self, filenames):
        uploaded_files = self.report.data_field_or('uploaded_files', default=[])
        timestamp = self.get_current_datetime()
        
        for filename in filenames:
            if filename not in uploaded_files:
                uploaded_files.append(filename)
                
        self.report.update(data={
            'uploaded_files': uploaded_files,
            'last_upload': timestamp,
            'total_uploaded': len(uploaded_files)
        })
        self.LogInfo(f"Tracked {len(filenames)} uploaded files. Total: {len(uploaded_files)}")
    
    # Check if file was already uploaded
    def is_file_uploaded(self, filename):
        uploaded_files = self.report.data_field_or('uploaded_files', default=[])
        return filename in uploaded_files
    
    # Get list of files that need to be uploaded
    def get_files_to_upload(self):
        all_files = self.get_handshake_files()
        uploaded_files = self.report.data_field_or('uploaded_files', default=[])
        
        files_to_upload = [f for f in all_files if f not in uploaded_files]
        self.LogDebug(f"Found {len(files_to_upload)} new files to upload out of {len(all_files)} total files")
        return files_to_upload
    
    # Get upload statistics for review
    def get_upload_stats(self):
        uploaded_files = self.report.data_field_or('uploaded_files', default=[])
        all_files = self.get_handshake_files()
        pending_files = self.get_files_to_upload()
        
        return {
            'total_handshakes': len(all_files),
            'uploaded_count': len(uploaded_files),
            'pending_count': len(pending_files),
            'uploaded_files': uploaded_files,
            'pending_files': pending_files,
            'last_upload': self.report.data_field_or('last_upload', 'Never')
        }
    
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
    def get_files_for_upload(self):
        handshakes_dir = self.get_handshakes_dir()
        if not os.path.exists(handshakes_dir):
            self.LogDebug("Handshakes directory does not exist")
            return []
            
        # Get files to upload
        files_to_upload = self.get_files_to_upload()
        if not files_to_upload:
            self.LogDebug("No new handshake files to upload")
            return []
        
        # Get hostname for S3 organization
        hostname = self.get_hostname()
        self.LogDebug(f"Using hostname for S3 organization: {hostname}")
        
        # Return full file paths for upload
        file_paths = []
        for filename in files_to_upload:
            file_path = os.path.join(handshakes_dir, filename)
            if os.path.isfile(file_path):
                file_paths.append({
                    'local_path': file_path,
                    'filename': filename,
                    's3_key': f"{hostname}/{filename}"  # Upload directly under hostname
                })
        
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
    def upload_handshakes_to_s3(self):
        files_for_upload = self.get_files_for_upload()
        if not files_for_upload:
            self.LogDebug("No files ready for upload - skipping")
            return False
        
        uploaded_files = []
        failed_files = []
        
        self.LogInfo(f"Starting upload of {len(files_for_upload)} handshake files")
        
        for file_info in files_for_upload:
            local_path = file_info['local_path']
            filename = file_info['filename']
            s3_key = file_info['s3_key']
            
            self.LogDebug(f"Uploading file: {filename}")
            
            success = self.upload_file_to_s3(local_path, s3_key)
            
            if success:
                uploaded_files.append(filename)
                self.LogInfo(f"Successfully uploaded: {filename}")
            else:
                failed_files.append(filename)
                self.LogInfo(f"Failed to upload: {filename}")
        
        # Track successful uploads
        if uploaded_files:
            self.track_uploaded_files(uploaded_files)
            self.LogInfo(f"Upload summary: {len(uploaded_files)} successful, {len(failed_files)} failed")
        
        if failed_files:
            self.LogInfo(f"Failed uploads: {', '.join(failed_files)}")
        
        # Return True if at least one file was uploaded successfully
        return len(uploaded_files) > 0

    # Check if there are new handshake files to upload
    def has_new_handshakes(self):
        files_to_upload = self.get_files_to_upload()
        return len(files_to_upload) > 0
    
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
                # Check if there are new handshakes to upload
                if self.has_new_handshakes():
                    files_to_upload = self.get_files_to_upload()
                    self.LogDebug(f"New handshakes detected - uploading {len(files_to_upload)} files to S3")
                    success = self.upload_handshakes_to_s3()
                    
                    # Update status report
                    uploaded_files = self.report.data_field_or('uploaded_files', default=[])
                    self.report.update(data={
                        'last_upload_attempt': self.get_current_datetime(),
                        'last_upload_success': success,
                        'uploaded_files': uploaded_files,
                        'total_uploaded': len(uploaded_files)
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
