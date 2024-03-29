# Qdrant Backup and Restore

这个Docker镜像用于定时备份Qdrant数据库，并支持从这些备份中恢复数据。它支持将备份数据存储在AWS S3或阿里云OSS。

## 准备

在开始之前，请确保你已经拥有：

- Qdrant服务的URL和访问凭证。
- AWS S3或阿里云OSS的访问密钥和存储桶信息。

## 镜像使用

### 环境变量

- `STORAGE_SERVICE`: 存储服务类型，`S3` 或 `OSS`。
- `STORAGE_REGION`: 存储服务的区域，例如 `us-east-1`或`cn-shanghai`。
- `ACCESS_KEY`: 存储服务的访问密钥ID。
- `SECRET_KEY`: 存储服务的访问密钥。
- `BUCKET_NAME`: 存储桶的名称。
- `URI_PREFIX`: 存储在存储桶中的备份文件前缀，默认为 `qdrant_backups`。
- `BACKUP_CRON_SCHEDULE`: 定时备份的Cron表达式，默认为每天午夜执行（`0 0 * * *`）。
- `QDRANT_URL`: Qdrant服务的URL。
- `QDRANT_KEY`: Qdrant服务的访问密钥。


### 启动容器

1. 构建Docker镜像：
    
    ```bash
    docker build -t qdrant-br .
    ```
   
    或者从Docker Hub拉取：
    
    ```bash
    docker pull datamini/qdrant-br
    ```

2. 运行容器：

   使用AWS S3:

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
    
    使用阿里云OSS:
    
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


### 使用CLI工具

进入容器内部，你可以使用CLI工具(`qdrant-br`)执行手动备份、恢复或列出备份文件：
        
```bash
docker exec -it [容器ID或名称] /bin/bash
```

然后：
* 执行备份：`qdrant-br backup`
* 列出备份：`qdrant-br list --days 3`
* 恢复备份：`qdrant-br restore [backup_name] [collection_name]`
* 检查配置：`qdrant-br check`


### 验证
在容器启动时，它会自动执行一个check命令来验证存储服务的凭证。如果检查失败，容器将不会启动。


## 注意事项

确保你的存储服务凭证是正确的，并且Qdrant服务URL是可访问的。错误的配置会导致容器启动失败或备份过程无法正常工作。



