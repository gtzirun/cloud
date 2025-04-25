# 第一阶段：构建依赖
FROM registry.cn-hangzhou.aliyuncs.com/aliyun-ubuntu/ubuntu:20.04 AS builder

# 设置非交互式安装
ENV DEBIAN_FRONTEND=noninteractive

# 更新 APT 源为阿里云镜像
RUN sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    sed -i 's/security.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 使用阿里云 PyPI 镜像安装 Python 依赖
RUN pip3 install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 第二阶段：运行时镜像
FROM registry.cn-hangzhou.aliyuncs.com/aliyun-ubuntu/ubuntu:20.04

# 设置非交互式安装
ENV DEBIAN_FRONTEND=noninteractive

# 更新 APT 源并安装 FFmpeg 和 Python
RUN sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    sed -i 's/security.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y ffmpeg python3 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 从构建阶段复制 Python 依赖
COPY --from=builder /usr/local/lib/python3.8/dist-packages /usr/local/lib/python3.8/dist-packages
COPY --from=builder /usr/local/bin/gunicorn /usr/local/bin/gunicorn

# 复制应用代码
COPY . .

# 暴露 Flask 端口
EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s \
    CMD curl -f http://localhost:5000/ || exit 1

# 启动 Gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
