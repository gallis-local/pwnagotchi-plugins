# Pwnagothi Hash File Upload to S3
import pwnagotchi.plugins as plugins
import pwnagotchi
import logging
import datetime
import os
import subprocess
import requests
from threading import Lock
from pwnagotchi.utils import StatusFile
from json import JSONDecodeError

TAG = "[S3 Plugin]"

class PwnS3Upload(plugins.Plugin):
    __author__ = 'gallis-local'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = 'S3 Offload for pwnagotchi'

    def __init__(self):
        self.ready = False
        try:
            self.report = StatusFile('/root/.s3_uploads', data_format='json')
        except JSONDecodeError:
            os.remove('/root/.s3_uploads')
            self.report = StatusFile('/root/.s3_uploads', data_format='json')
        self.lock = Lock()

    # Log Functions
    def LogInfo(self, text):
        logging.info(TAG + " " +text)
    
    # Log Functions
    def LogDebug(self, text):
        logging.debug(TAG + " " +text)
    
    # Log Functions - Loaded
    def on_loaded(self):
        self.ready = True
        self.LogInfo("Pwnagotchi S3 Upload Loaded.")

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
        # check if the s3 config is present and contains the required fields
        if 's3' not in config['main']['plugins']:
            self.LogInfo("Missing S3 Config")
            return None
        if 'bucket' not in config['main']['plugins']['s3']:
            self.LogInfo("Missing S3 Config - Bucket")
            return None
        if 'region' not in config['main']['plugins']['s3']:
            self.LogInfo("Missing S3 Config - Region")
            return None
        if 'access_key' not in config['main']['plugins']['s3']:
            self.LogInfo("Missing S3 Config - Access Key")
            return None
        if 'secret_key' not in config['main']['plugins']['s3']:
            self.LogInfo("Missing S3 Config  - Secret Key")
            return None
        return config['main']['plugins']['s3']
    
    # Get a list of all hash files in the handshakes directory
    def get_hash_files(self):
        handshakes_dir = self.get_handshakes_dir()
        self.LogDebug("Handshakes Directory: " + handshakes_dir)
        return [f for f in os.listdir(handshakes_dir) if os.path.isfile(os.path.join(handshakes_dir, f))]
        
    # Get the current date and time
    def get_current_datetime(self):
        return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    # Tar all handshakes into a single file
    def tar_handshakes(self):
        handshakes_dir = self.get_handshakes_dir()
        tar_filename = self.get_current_datetime() + "_handshakes.tar"
        self.LogDebug("Creating tar file: " + tar_filename)
        subprocess.run(["tar", "-cf", tar_filename, handshakes_dir])
        self.LogDebug("Tar file created: " + tar_filename)
        return tar_filename

    # Create S3 filename
    def create_s3_filename(self, filename):
        return self.get_current_datetime() + "_" + filename
    
    # Upload the tar file to S3
    def upload_tar_to_s3(self):
        tar_filename = self.tar_handshakes()
        s3_config = self.get_s3_config()
        if s3_config is None:
            self.LogDebug("S3 Config has an error - Not uploading to S3")
        elif s3_config.endpoint_url is None:
            self.LogDebug("S3 Endpoint URL not found - Using AWS Default")
            url = f"https://{s3_config.bucket}.s3.{s3_config.region}.amazonaws.com/{tar_filename}"
            headers = {
                "x-amz-access-key": s3_config.access_key,
                "x-amz-secret-key": s3_config.secret_key
            }
            with open(tar_filename, "rb") as file:
                response = requests.put(url, data=file, headers=headers)
            if response.status_code == 200:
                self.LogDebug("Tar file uploaded to S3: " + tar_filename)
            else:
                self.LogDebug("Failed to upload tar file to S3: " + tar_filename)
        else:
            self.LogDebug("Using S3 Endpoint URL: " + s3_config.endpoint_url)
            url = f"{s3_config.endpoint_url}/{s3_config.bucket}/{tar_filename}"
            headers = {
                "x-amz-access-key": s3_config.access_key,
                "x-amz-secret-key": s3_config.secret_key
            }
            with open(tar_filename, "rb") as file:
                response = requests.put(url, data=file, headers=headers)
            if response.status_code == 200:
                self.LogInfo("Tar file uploaded to S3: " + tar_filename)
            else:
                self.LogInfo("Failed to upload tar file to S3: " + tar_filename)
        self.LogDebug("Removing tar file: " + tar_filename)
        os.remove(tar_filename)
        self.LogDebug("Tar file removed: " + tar_filename)

    # Only upload to S3 if there are 1 hash files and internet is available
    def on_internet_available(self, agent):
        if not self.ready or self.lock.locked():
            self.LogDebug("Not ready locked.")
            return
        with self.lock:
            display = agent.view()
            reported = self.report.data_field_or('reported', default=list())
            self.LogDebug("Internet is available")
            hash_files = self.get_hash_files()
            if len(hash_files) >= 1:
                self.LogDebug("Uploading to S3")
                self.report.update(data={'reported': reported, 'count': len(hash_files), 'last': self.get_current_datetime()})
                self.upload_tar_to_s3()
            else:
                self.LogDebug("No hash files to upload to S3")
                self.report.update(data={'reported': reported, 'count': len(hash_files), 'last': self.get_current_datetime()})
            display.on_normal()
