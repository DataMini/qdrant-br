#!/bin/bash

# 设置Cron表达式环境变量，默认每天凌晨执行备份
BACKUP_CRON_SCHEDULE="${BACKUP_CRON_SCHEDULE:-0 0 * * *}"

# 先执行检查命令，如果检查失败，则退出
qdrant-br check
if [ $? -ne 0 ]; then
    echo "Check failed, exiting."
    exit 1
fi

# 添加Cron任务
echo "$BACKUP_CRON_SCHEDULE root qdrant-br backup" >> /etc/crontab

# 启动Cron服务
cron -f
