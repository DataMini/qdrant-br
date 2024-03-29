FROM python:3.11-slim

# 安装依赖
WORKDIR /app
COPY requirements.txt /app/
RUN pip install -r requirements.txt

# 复制 qdrant-br.py 到容器中
COPY qdrant-br.py /usr/local/bin/qdrant-br

# 确保脚本可执行
RUN chmod +x /usr/local/bin/qdrant-br


# 设置启动脚本
COPY start.sh /start.sh
RUN chmod +x /start.sh

CMD ["/start.sh"]