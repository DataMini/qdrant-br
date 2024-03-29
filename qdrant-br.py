#!/usr/bin/env python
import os
import sys
import click
import logging
import requests
import tempfile
import math
import urllib.parse
from datetime import datetime, timedelta
import boto3
import oss2
from qdrant_client import QdrantClient
from dotenv import load_dotenv
from tabulate import tabulate


# 设置日志
logger = logging.getLogger(__name__)
log_format = '%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.WARN, format=log_format, stream=sys.stdout)

# load envs from .env if exists
load_dotenv()

# 环境变量
STORAGE_SERVICE = os.getenv("STORAGE_SERVICE", "OSS")
STORAGE_REGION = os.getenv("STORAGE_REGION", "us-east-1")
ACCESS_KEY = os.getenv("ACCESS_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
BUCKET_NAME = os.getenv("BUCKET_NAME")
URI_PREFIX = os.getenv("URI_PREFIX", "qdrant_backups")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_KEY = os.getenv("QDRANT_KEY")


def log_or_print(message, level=logging.INFO):
    ctx = click.get_current_context()
    if ctx.obj and ctx.obj.get('VERBOSE'):
        logger.log(level, message)
    else:
        print(message)


def format_timestamp(unix_timestamp):
    """将UNIX时间戳转换为人类友好的日期时间字符串。"""
    return datetime.fromtimestamp(unix_timestamp).strftime('%Y-%m-%d %H:%M:%S')


def convert_size(size_bytes):
    if size_bytes == 0:
        return '0B'
    size_names = ('B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB')
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f'{s} {size_names[i]}'


def download_snapshot(snapshot_url, local_path):
    headers = {'api-key': QDRANT_KEY} if QDRANT_KEY else {}
    response = requests.get(snapshot_url, headers=headers)
    response.raise_for_status()  # 确保请求成功
    with open(local_path, 'wb') as f:
        f.write(response.content)
    logger.info(f"Downloaded {snapshot_url}")


def restore_collection_from_file(snapshot_file_path, collection_name):
    url = f"{QDRANT_URL}/collections/{collection_name}/snapshots/upload?priority=snapshot"
    headers = {'api-key': QDRANT_KEY} if QDRANT_KEY else {}
    files = {'snapshot': open(snapshot_file_path, 'rb')}

    response = requests.post(url, headers=headers, files=files)

    if response.status_code == 200:
        logger.info(f"Collection {collection_name} restored successfully from uploaded snapshot.")
    else:
        logger.error(
            f"Failed to restore collection {collection_name} from uploaded snapshot. Response: {response.text}",
        )


def get_storage_client(service, region):
    if service == "S3":
        logger.info(f"Using S3 in region {region}")
        return boto3.client(
            's3',
            region_name=region,
            aws_access_key_id=ACCESS_KEY,
            aws_secret_access_key=SECRET_KEY
        )
    elif service == "OSS":
        endpoint = f"https://oss-{region}.aliyuncs.com"
        logger.info(f"Using OSS with endpoint: {endpoint}")
        return oss2.Bucket(oss2.Auth(ACCESS_KEY, SECRET_KEY), endpoint, BUCKET_NAME)
    else:
        raise ValueError(f"Unsupported storage service: {service}")


def get_port_from_url(url):
    # 解析每个URL并提取端口号
    parsed_url = urllib.parse.urlparse(url)
    port = parsed_url.port
    if port is None:
        if parsed_url.scheme == 'http':
            port = 80
        elif parsed_url.scheme == 'https':
            port = 443
    return port


# 使用上面定义的函数来获取存储客户端
try:
    storage_client = get_storage_client(STORAGE_SERVICE, STORAGE_REGION)
except Exception:
    print("Failed to initialize storage client. Please check your credentials.")
    sys.exit(1)

# 创建Qdrant客户端
qdrant_port = get_port_from_url(QDRANT_URL)
client = QdrantClient(url=QDRANT_URL, port=qdrant_port, api_key=QDRANT_KEY)


def backup_collections():
    now = datetime.now()
    date_prefix = now.strftime('%Y-%m-%d')
    backup_path = f"{URI_PREFIX}/{date_prefix}/"

    # 获取所有的collections并备份
    collections = client.http.collections_api.get_collections().result.collections

    for collection in collections:
        print(f"Backing up collection: {collection.name} ...")
        logger.info(f"Backing up collection: {collection.name}")
        collection_name = collection.name
        snapshot_info = client.http.snapshots_api.create_snapshot(collection_name=collection_name)
        snapshot_name = f"{snapshot_info.result.name}"
        snapshot_url = f"{QDRANT_URL}/collections/{collection_name}/snapshots/{snapshot_name}"
        storage_key_name = f"{backup_path}{snapshot_name}"

        local_path = f"/tmp/{snapshot_name}"

        # 下载快照到本地
        try:
            download_snapshot(snapshot_url, local_path)
        except Exception as e:
            logger.error(f"Failed to download {snapshot_url} {e}")
            continue

        # 上传快照
        if STORAGE_SERVICE == "OSS":
            with open(local_path, "rb") as snapshot_file:
                storage_client.put_object(storage_key_name, snapshot_file)
        else:
            with open(local_path, "rb") as snapshot_file:
                storage_client.upload_fileobj(snapshot_file, BUCKET_NAME, storage_key_name)

        # 删除临时文件
        try:
            os.remove(local_path)
            logger.info(f"Temporary snapshot file {local_path} deleted.")
        except OSError as e:
            logger.error(f"Error deleting temporary snapshot file {local_path}: {e}")
        log_or_print(f"Collection {collection_name} backed up to {STORAGE_SERVICE} in path {storage_key_name}.")


def restore_collection(backup_uri, collection_name):
    with tempfile.NamedTemporaryFile() as tmp_file:
        print(f"Restoring collection {collection_name} from backup {backup_uri}...")
        logger.info(f"Restoring collection {collection_name} from backup {backup_uri}.")
        local_path = tmp_file.name

        if STORAGE_SERVICE == "OSS":
            # 注意，OSS的下载逻辑可能需要调整以写入到tmp_file.file直接，或保持当前方式
            storage_client.get_object_to_file(backup_uri, local_path)
        else:
            # 对于S3，直接将下载的文件内容写入临时文件
            storage_client.download_fileobj(BUCKET_NAME, backup_uri, tmp_file)

        logger.info(f"Downloaded {backup_uri} from {STORAGE_SERVICE}. Ready for restoration.")

        # 重置文件指针
        tmp_file.seek(0)

        restore_collection_from_file(local_path, collection_name)
        log_or_print(f"Collection {collection_name} restored from backup {backup_uri}.")


def delete_backup(backup_uri):
    if STORAGE_SERVICE == "OSS":
        # 对于OSS，使用oss2库来删除对象
        try:
            storage_client.delete_object(backup_uri)
        except Exception as e:
            logger.error(f"Failed to delete {backup_uri} from OSS: {e}")
    else:
        # 对于S3，使用boto3库来删除对象
        try:
            storage_client.delete_object(Bucket=BUCKET_NAME, Key=backup_uri)
        except Exception as e:
            logger.error(f"Failed to delete {backup_uri} from S3: {e}")
    log_or_print(f"Backup {backup_uri} deleted.")


def list_backups(days=3):
    now = datetime.now()
    backup_list = []  # 用于收集所有备份的列表

    for day_offset in range(days):
        date_prefix = (now - timedelta(days=day_offset)).strftime('%Y-%m-%d')
        prefix = f"{URI_PREFIX}/{date_prefix}/"
        if STORAGE_SERVICE == "OSS":
            for obj in oss2.ObjectIterator(storage_client, prefix=prefix):
                last_modified = obj.last_modified  # 假设这是一个时间戳或datetime对象
                size = obj.size  # 获取文件大小
                backup_list.append([obj.key, last_modified, size])
        else:
            response = storage_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)
            for obj in response.get('Contents', []):
                last_modified = obj['LastModified']  # datetime对象
                size = obj['Size']  # 获取文件大小
                backup_list.append([obj['Key'], last_modified, size])

    # 按时间正序排序
    backup_list.sort(key=lambda x: x[1])

    # 格式化时间并打印
    formatted_list = [[item[0], format_timestamp(item[1]), convert_size(item[2])] for item in backup_list]
    log_or_print(tabulate(formatted_list, headers=['Backup Name', 'Last Modified', 'Size'], tablefmt="plain"))


def check_credentials():
    try:
        if STORAGE_SERVICE == "OSS":
            auth = oss2.Auth(ACCESS_KEY, SECRET_KEY)
            endpoint = f"https://oss-{STORAGE_REGION}.aliyuncs.com"
            bucket = oss2.Bucket(auth, endpoint, BUCKET_NAME)
            bucket.get_bucket_info()  # 获取存储桶信息来验证凭证
        else:
            storage_client.list_buckets()
    except Exception as e:
        logger.error(f"Failed to verify storage credentials: {e}")
        sys.exit(1)
    log_or_print(f"Storage credentials for {STORAGE_SERVICE} are valid.")


@click.group()
@click.option('--verbose', '-v', is_flag=True, help="Enable verbose output (debug level logging).")
@click.pass_context
def cli(ctx, verbose):
    """Qdrant Backup CLI"""
    if verbose:
        logger.setLevel(logging.INFO)
    ctx.ensure_object(dict)
    ctx.obj['VERBOSE'] = verbose


@click.command(help="Check storage credentials")
def check():
    check_credentials()


@click.command(help="Backup Qdrant collection to Storage")
def backup():
    backup_collections()


@click.command(name='list', help="List recent backups")
@click.option("--days", default=3, help="How many days to look back for backups")
def list_backups_cmd(days):
    list_backups(days)


@click.command(help="Restore Qdrant collection from a backup in Storage")
@click.argument("backup_name")
@click.argument("collection_name")
def restore(backup_name, collection_name):
    restore_collection(backup_name, collection_name)


@click.command(help="Delete a Qdrant backup from Storage")
@click.argument("backup_uri")
def delete(backup_uri):
    delete_backup(backup_uri)


cli.add_command(check)
cli.add_command(backup)
cli.add_command(list_backups_cmd)
cli.add_command(restore)
cli.add_command(delete)


if __name__ == "__main__":
    cli()
