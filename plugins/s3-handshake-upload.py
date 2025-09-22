import os
import boto3
import socket
import logging
from pwnagotchi.plugins import Plugin
from pwnagotchi.utils import StatusFile, is_internet

class S3HandshakeUpload(Plugin):
    __author__ = 'Your Name'
    __version__ = '1.1.0'
    __license__ = 'GPL3'
    __description__ = 'Uploads handshakes to an S3 bucket.'

    def __init__(self):
        self.s3_client = None
        self.handshake_dir = None
        self.uploaded_files = set()
        logging.debug("S3HandshakeUpload plugin created")

    def on_loaded(self):
        self.handshake_dir = self.options.get('handshake_dir', '/home/pi/handshakes')
        s3_endpoint = self.options['s3_endpoint']
        s3_bucket = self.options['s3_bucket']
        s3_region = self.options['s3_region']
        s3_client_id = self.options['s3_client_id']
        s3_client_secret = self.options['s3_client_secret']

        self.s3_client = boto3.client(
            's3',
            endpoint_url=s3_endpoint,
            region_name=s3_region,
            aws_access_key_id=s3_client_id,
            aws_secret_access_key=s3_client_secret
        )

        self.hostname = socket.gethostname()
        self.uploaded_files_file = os.path.join(self.handshake_dir, 'uploaded_files.txt')
        self.load_uploaded_files()
        logging.warning("WARNING: this plugin should be disabled! options = %s" % self.options)

    def load_uploaded_files(self):
        if os.path.exists(self.uploaded_files_file):
            with open(self.uploaded_files_file, 'r') as f:
                self.uploaded_files = set(f.read().splitlines())

    def save_uploaded_files(self):
        with open(self.uploaded_files_file, 'w') as f:
            f.write('\n'.join(self.uploaded_files))

    def on_internet_available(self, agent):
        self.upload_handshakes()

    def on_handshake(self, filename, access_point, station, ap_station):
        if is_internet():
            self.upload_handshake(filename)

    def upload_handshakes(self):
        for filename in os.listdir(self.handshake_dir):
            if filename not in self.uploaded_files:
                self.upload_handshake(filename)

    def upload_handshake(self, filename):
        if not self.s3_client:
            self.log.error("S3 client is not initialized.")
            return

        file_path = os.path.join(self.handshake_dir, filename)
        if not os.path.isfile(file_path):
            self.log.error(f"Handshake file {file_path} does not exist.")
            return

        try:
            s3_key = f"{self.hostname}/{filename}"
            self.s3_client.upload_file(file_path, self.options['s3_bucket'], s3_key)
            self.log.info(f"Uploaded {filename} to S3 bucket {self.options['s3_bucket']} under {s3_key}.")
            self.uploaded_files.add(filename)
            self.save_uploaded_files()
        except Exception as e:
            self.log.error(f"Failed to upload {filename} to S3: {e}")