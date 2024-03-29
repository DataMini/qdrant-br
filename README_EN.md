# Qdrant Backup and Restore

This Docker image is used for the periodic backup of the Qdrant database and supports restoring data from these backups. It supports storing backup data on AWS S3 or Alibaba Cloud OSS.

## Preparation

Before you start, make sure you have:

- The URL and access credentials for the Qdrant service.
- Access keys and bucket information for AWS S3 or Alibaba Cloud OSS.

## Using the Image

### Environment Variables

- `STORAGE_SERVICE`: The type of storage service, either `S3` or `OSS`.
- `STORAGE_REGION`: The region of the storage service, for example, `us-east-1` or `cn-shanghai`.
- `QDRANT_URL`: The URL of the Qdrant service.
- `ACCESS_KEY`: Access key ID for the storage service.
- `SECRET_KEY`: Secret access key for the storage service.
- `BUCKET_NAME`: The name of the storage bucket.
- `URI_PREFIX`: The prefix for the backup files stored in the bucket, the default is `qdrant_backups`.
- `BACKUP_CRON_SCHEDULE`: The Cron expression for scheduling backups, the default is to execute at midnight every day (`0 0 * * *`).

### Starting the Container

1. Build the Docker image:

    ```bash
    docker build -t qdrant-br.py .
    ```
   or pull it from the Docker Hub:
   
    ```bash
    docker pull datamini/qdrant-br.py
    ```

2. Run the container:

    Using AWS S3:

    ```bash
    docker run -d \
    -e QDRANT_URL=http://your-qdrant-url:6333 \
    -e QDRANT_KEY=your-qdrant-key \
    -e STORAGE_SERVICE=S3 \
    -e STORAGE_REGION=us-east-1 \
    -e ACCESS_KEY=your-access-key \
    -e SECRET_KEY=your-secret-key \
    -e BUCKET_NAME=your-bucket-name \
    -e BACKUP_CRON_SCHEDULE="0 0 * * *" \
    qdrant-br
    ```
    
    Using Alibaba Cloud OSS:
    
    ```bash
    docker run -d \
    -e QDRANT_URL=http://your-qdrant-url:6333 \
    -e QDRANT_KEY=your-qdrant-key \
    -e STORAGE_SERVICE=OSS \
    -e STORAGE_REGION=cn-hangzhou \
    -e ACCESS_KEY=your-access-key \
    -e SECRET_KEY=your-secret-key \
    -e BUCKET_NAME=your-bucket-name \
    -e BACKUP_CRON_SCHEDULE="0 0 * * *" \
    qdrant-br
    ```

### Using the CLI Tool

Enter the container, you can use the CLI tool (`qdrant-br`) to perform manual backups, restores, or list backup files:
        
```bash
docker exec -it [container ID or name] /bin/bash
```

Then:

* Perform a backup: `qdrant-br backup`
* List backups: `qdrant-br list --days 3`
* Restore from a backup: `qdrant-br restore [snapshot_name] [collection_name]`
* Check configuration: `qdrant-br check`

### Verification

Upon container startup, it will automatically execute a check command to verify the storage service credentials. If the check fails, the container will not start.

## Considerations

Make sure your storage service credentials are correct, and the Qdrant service URL is accessible. Incorrect configuration will cause the container to fail to start or the backup process to not work properly.