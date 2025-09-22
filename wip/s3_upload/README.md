# Pwnagotchi S3 Handshakes Upload Plugin

A simple and efficient Pwnagotchi plugin that automatically uploads WiFi handshake files to Amazon S3 or S3-compatible storage when internet connectivity is available.

## Features

- **Handshakes Only**: Focused on uploading WiFi handshake files (.pcap, .22000, etc.)
- **Filename-Based Tracking**: Simple and fast duplicate prevention using filenames
- **Easy Monitoring**: Clear list of uploaded files for review
- **Robust Error Handling**: Automatic retry with exponential backoff
- **Compression**: Creates compressed tar.gz archives to minimize bandwidth
- **Flexible Storage**: Support for AWS S3 or custom S3-compatible endpoints

## Installation

1. **Install boto3 dependency**:
   ```bash
   pip install boto3
   ```

2. **Copy the plugin files**:
   ```bash
   cp s3_upload.py /usr/local/share/pwnagotchi/custom-plugins/
   ```

3. **Configure the plugin** in `/etc/pwnagotchi/config.toml`

## Configuration

```toml
# Pwnagotchi S3 Handshakes Upload Plugin Configuration
main.plugins.s3_upload.enabled = true

# S3 Configuration
main.plugins.s3_upload.bucket = "pwnagotchi-handshakes"
main.plugins.s3_upload.region = "us-east-1"
main.plugins.s3_upload.access_key = "your-access-key"
main.plugins.s3_upload.secret_key = "your-secret-key"

# Optional: Custom S3 endpoint (leave empty for AWS S3)
main.plugins.s3_upload.endpoint_url = ""

# Upload Settings
main.plugins.s3_upload.max_retries = 3
main.plugins.s3_upload.retry_delay = 5
```

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `false` | Enable/disable the plugin |
| `bucket` | string | `"pwnagotchi-handshakes"` | S3 bucket name |
| `region` | string | `"us-east-1"` | AWS region |
| `access_key` | string | `""` | AWS access key ID |
| `secret_key` | string | `""` | AWS secret access key |
| `endpoint_url` | string | `""` | Custom S3 endpoint (optional) |
| `max_retries` | integer | `3` | Maximum upload retry attempts |
| `retry_delay` | integer | `5` | Initial retry delay in seconds |

## How It Works

1. **Detection**: When internet becomes available, scans handshakes directory
2. **Filtering**: Identifies files not yet uploaded using simple filename tracking
3. **Archive**: Creates compressed tar.gz with only new handshake files
4. **Upload**: Uploads to S3 under `handshakes/` prefix
5. **Tracking**: Records uploaded filenames in `/root/.s3_uploads`
6. **Cleanup**: Removes local archive after successful upload

## File Organization

Files are uploaded to S3 with this structure:
```
s3://your-bucket/handshakes/YYYY-MM-DD_HH-MM-SS_handshakes.tar.gz
```

Each archive contains only the new handshake files from your pwnagotchi.

## Monitoring & Statistics

The plugin tracks:
- **Total handshake files** found in directory
- **Uploaded count** - files already uploaded
- **Pending count** - files waiting for upload
- **Upload history** with timestamps

Check `/root/.s3_uploads` for detailed tracking information:
```json
{
  "uploaded_files": ["network1_handshake.pcap", "network2.22000", ...],
  "last_upload": "2025-09-21_14-30-15",
  "total_uploaded": 42
}
```

## AWS S3 Setup

1. **Create S3 Bucket**:
   ```bash
   aws s3 mb s3://pwnagotchi-handshakes
   ```

2. **Create IAM Policy**:
   ```json
   {
       "Version": "2012-10-17",
       "Statement": [
           {
               "Effect": "Allow",
               "Action": [
                   "s3:PutObject"
               ],
               "Resource": "arn:aws:s3:::pwnagotchi-handshakes/*"
           }
       ]
   }
   ```

3. **Create IAM User** and attach the policy
4. **Generate Access Keys** for the user

## Alternative S3 Storage

For **MinIO**, **DigitalOcean Spaces**, or other S3-compatible services:

```toml
main.plugins.s3_upload.endpoint_url = "https://sfo3.digitaloceanspaces.com"
```

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `boto3 not available` | `pip install boto3` |
| `Access denied` | Check IAM permissions and bucket name |
| `Network timeouts` | Increase `retry_delay` and `max_retries` |
| `No files uploading` | Verify handshakes directory path |

### Logs

Monitor plugin activity:
```bash
tail -f /var/log/pwnagotchi.log | grep "S3 Plugin"
```

### Upload Status

Check current status programmatically:
```python
# Access plugin stats
stats = plugin.get_upload_stats()
print(f"Uploaded: {stats['uploaded_count']}/{stats['total_handshakes']}")
```

## Performance Benefits

- **No MD5 Hashing**: Uses simple filename comparison for speed
- **Incremental Uploads**: Only uploads new files since last run
- **Compressed Archives**: Reduces bandwidth usage
- **Efficient Tracking**: Lightweight JSON-based file tracking

## Security Notes

- Store credentials securely (consider environment variables)
- Use least-privilege IAM policies
- Enable S3 bucket versioning for backup
- Consider S3 server-side encryption
- Review bucket access logs periodically

## Version History

### v2.0.0
- Simplified to handshakes-only uploads
- Replaced MD5 hashing with filename tracking
- Improved upload statistics and monitoring
- Streamlined configuration options
- Better performance for large handshake collections