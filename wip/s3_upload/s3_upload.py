# Pwnagotchi Handshakes Upload to S3
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
        try:
            self.report = StatusFile('/root/.s3_uploads', data_format='json')
        except JSONDecodeError:
            os.remove('/root/.s3_uploads')
            self.report = StatusFile('/root/.s3_uploads', data_format='json')
        self.lock = Lock()
        
        if not BOTO3_AVAILABLE:
            self.LogInfo("boto3 not available. Please install with: pip install boto3")
            self.ready = False

    # Log Functions
    def LogInfo(self, text):
        logging.info(TAG + " " +text)
    
    # Log Functions
    def LogDebug(self, text):
        logging.debug(TAG + " " +text)
    
    # Log Functions - Loaded
    def on_loaded(self):
        self.ready = True
        uploaded_count = len(self.report.data_field_or('uploaded_files', default=[]))
        self.LogInfo(f"Pwnagotchi S3 Handshakes Upload Loaded. {uploaded_count} files previously uploaded.")

    # Log Functions - Unloaded
    def on_unload(self, ui):
        self.LogInfo("Pwnagotchi S3 Upload Unloaded.")

    # Get the handshakes directory from /etc/pwnagotchi/config.yml for the value of bettercap.handshakes
    def get_handshakes_dir(self):
        config = pwnagotchi.Config()
        return config['main']['bettercap']['handshakes']
    
    # Get the config values for S3
    def get_s3_config(self):
        config = pwnagotchi.Config()
        # check if the s3_upload config is present and contains the required fields
        if 's3_upload' not in config['main']['plugins']:
            self.LogInfo("Missing S3 Upload Config")
            return None
        s3_config = config['main']['plugins']['s3_upload']
        if 'bucket' not in s3_config:
            self.LogInfo("Missing S3 Config - Bucket")
            return None
        if 'region' not in s3_config:
            self.LogInfo("Missing S3 Config - Region")
            return None
        if 'access_key' not in s3_config:
            self.LogInfo("Missing S3 Config - Access Key")
            return None
        if 'secret_key' not in s3_config:
            self.LogInfo("Missing S3 Config - Secret Key")
            return None
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
        config = pwnagotchi.Config()
        if 's3_upload' not in config['main']['plugins']:
            return {'max_retries': 3, 'retry_delay': 5}
        plugin_config = config['main']['plugins']['s3_upload']
        
        # Set defaults
        plugin_config.setdefault('max_retries', 3)
        plugin_config.setdefault('retry_delay', 5)
        
        return plugin_config
    
    # Create compressed archive of handshakes directory
    def create_handshakes_archive(self):
        handshakes_dir = self.get_handshakes_dir()
        if not os.path.exists(handshakes_dir):
            self.LogDebug("Handshakes directory does not exist")
            return None
            
        # Get files to upload
        files_to_upload = self.get_files_to_upload()
        if not files_to_upload:
            self.LogDebug("No new handshake files to upload")
            return None, []
        
        timestamp = self.get_current_datetime()
        tar_filename = f"{timestamp}_handshakes.tar.gz"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = os.path.join(temp_dir, tar_filename)
            
            try:
                # Create compressed tar archive with only new files
                cmd = ["tar", "-czf", archive_path, "-C", handshakes_dir]
                cmd.extend(files_to_upload)
                
                self.LogDebug(f"Creating archive with {len(files_to_upload)} new handshake files")
                
                # Execute tar command
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    # Move archive to current directory for upload
                    final_path = os.path.join(os.getcwd(), tar_filename)
                    subprocess.run(["mv", archive_path, final_path])
                    self.LogInfo(f"Created handshakes archive: {tar_filename} with {len(files_to_upload)} files")
                    return tar_filename, files_to_upload
                else:
                    self.LogInfo(f"Failed to create archive: {result.stderr}")
                    return None, []
                    
            except Exception as e:
                self.LogInfo(f"Error creating archive: {e}")
                return None, []


    
    # Upload file to S3 with retry logic
    def upload_file_to_s3(self, local_file_path, s3_key):
        if not BOTO3_AVAILABLE:
            self.LogInfo("boto3 not available - cannot upload to S3")
            return False
            
        s3_config = self.get_s3_config()
        if s3_config is None:
            self.LogDebug("S3 Config has an error - Not uploading to S3")
            return False
        
        # Create S3 client
        try:
            s3_client = boto3.client(
                's3',
                aws_access_key_id=s3_config['access_key'],
                aws_secret_access_key=s3_config['secret_key'],
                region_name=s3_config['region'],
                endpoint_url=s3_config.get('endpoint_url')
            )
        except Exception as e:
            self.LogInfo(f"Failed to create S3 client: {e}")
            return False
        
        # Get retry settings from config
        plugin_config = self.get_plugin_config()
        max_retries = plugin_config.get('max_retries', 3)
        retry_delay = plugin_config.get('retry_delay', 5)
        
        # Retry upload with exponential backoff
        for attempt in range(max_retries):
            try:
                self.LogDebug(f"Uploading {local_file_path} to s3://{s3_config['bucket']}/{s3_key} (attempt {attempt + 1})")
                
                s3_client.upload_file(
                    local_file_path, 
                    s3_config['bucket'], 
                    s3_key,
                    ExtraArgs={
                        'Metadata': {
                            'uploaded_by': 'pwnagotchi',
                            'upload_time': self.get_current_datetime()
                        }
                    }
                )
                
                self.LogInfo(f"Successfully uploaded {s3_key} to S3")
                return True
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                self.LogDebug(f"S3 ClientError on attempt {attempt + 1}: {error_code} - {e}")
                
                if error_code in ['NoSuchBucket', 'AccessDenied', 'InvalidAccessKeyId']:
                    # These are permanent errors, don't retry
                    self.LogInfo(f"Permanent S3 error: {error_code} - {e}")
                    return False
                    
            except NoCredentialsError:
                self.LogInfo("S3 credentials not found or invalid")
                return False
                
            except BotoCoreError as e:
                self.LogDebug(f"BotoCore error on attempt {attempt + 1}: {e}")
                
            except Exception as e:
                self.LogDebug(f"Unexpected error on attempt {attempt + 1}: {e}")
            
            # Wait before retrying (exponential backoff)
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)
                self.LogDebug(f"Retrying upload in {wait_time} seconds...")
                time.sleep(wait_time)
        
        self.LogInfo(f"Failed to upload {s3_key} after {max_retries} attempts")
        return False
    
    # Main upload method for handshakes
    def upload_handshakes_to_s3(self):
        result = self.create_handshakes_archive()
        if result is None or result[0] is None:
            self.LogDebug("No archive created - skipping upload")
            return False
            
        archive_filename, uploaded_files = result
            
        try:
            # Upload to S3
            s3_key = f"handshakes/{archive_filename}"
            success = self.upload_file_to_s3(archive_filename, s3_key)
            
            if success:
                # Track successful upload of individual files
                self.track_uploaded_files(uploaded_files)
                self.LogInfo(f"Successfully uploaded {len(uploaded_files)} handshake files")
            
            return success
            
        finally:
            # Clean up local archive file
            if os.path.exists(archive_filename):
                os.remove(archive_filename)
                self.LogDebug(f"Removed local archive: {archive_filename}")

    # Check if there are new handshake files to upload
    def has_new_handshakes(self):
        files_to_upload = self.get_files_to_upload()
        return len(files_to_upload) > 0
    
    # Upload to S3 when internet is available and there are new handshakes
    def on_internet_available(self, agent):
        if not self.ready or self.lock.locked():
            self.LogDebug("Plugin not ready or locked")
            return
            
        if not BOTO3_AVAILABLE:
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
