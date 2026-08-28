# Dockerfile - 中国刑事追诉智能辅助系统

FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY prosecution_system/requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY prosecution_system/ .

# 创建输出目录
RUN mkdir -p /app/output /app/logs /app/data

# 暴露端口
EXPOSE 5000

# 环境变量
ENV FLASK_ENV=production
ENV PORT=5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/ || exit 1

# 启动命令
# 开发模式
# CMD ["python", "src/web_app.py"]
# 生产模式（推荐）
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "120", "src.web_app:app"]
