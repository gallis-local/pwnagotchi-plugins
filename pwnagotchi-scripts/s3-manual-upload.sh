#!/bin/bash
# s3-manual-upload.sh
# This script is used to upload handshakes to an S3 bucket
# It will tar the handshakes directory and upload it to the S3 bucket 
# The script is intended to be run manually, but can be automated with a cron job
# The script requires the following environment variables to be set:
# S3_KEY - The AWS access key
# S3_SECRET - The AWS secret key
# S3_REGION - The AWS region
# S3_BUCKET - The AWS S3 bucket name
# S3_FOLDER - The folder within the S3 bucket to upload the handshakes to
# S3_HOST - The AWS S3 host (default: s3.amazonaws.com)


# Define S3 VARS
S3_KEY="${S3_KEY:-}"
S3_SECRET="${S3_SECRET:-}"
S3_REGION="${S3_REGION:-}"
S3_HOST="${S3_HOST:-s3.amazonaws.com}"
S3_BUCKET="${S3_BUCKET:-pwnagotchi}"
S3_FOLDER="${S3_FOLDER:-handshakes}"

# Define the source directory of the handshakes
SOURCE_DIR="/root/handshakes"

# Get the current date - month/day/year format
CURRENT_DATE=$(date +%Y-%m-%d)

# Define the target file with the current date in the filename
TARGET_FILE="/tmp/handshakes_$CURRENT_DATE.tar.gz"

# Create the tar archive
echo "Creating archive of $SOURCE_DIR"
tar -czf $TARGET_FILE -C $SOURCE_DIR .
echo "Archive created at $TARGET_FILE"

# S3 upload configuration and curl command
hostname=$(hostname)
bucket=$S3_BUCKET
file=$TARGET_FILE
dest_file=$(basename "$file")
host=$S3_HOST
folder=$S3_FOLDER
s3_key=$S3_KEY
s3_secret=$S3_SECRET
resource="/${bucket}/${hostname}/${folder}/${dest_file}"
content_type="application/octet-stream"
date=`date -R`
_signature="PUT\n\n${content_type}\n${date}\n${resource}"
signature=`echo -en ${_signature} | openssl sha1 -hmac ${s3_secret} -binary | base64`

# Upload to S3 via curl
curl -X PUT -T "${file}" \
          -H "Host: ${host}" \
          -H "Date: ${date}" \
          -H "Content-Type: ${content_type}" \
          -H "Authorization: AWS ${s3_key}:${signature}" \
          https://${host}${resource}

# Check if the upload was successful
if [ $? -ne 0 ]; then
    echo "Failed to upload $file to remote s3 bucket: $resource"
    exit 1
fi

# Clean up
echo "Uploaded $file to remote s3 bucket: $resource"
rm $TARGET_FILE
echo "Removed upload tar locally"

# Exit
exit 0