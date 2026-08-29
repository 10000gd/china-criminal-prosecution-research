# ============================================================
# 检察机关办案系统 Dockerfile
# ============================================================
# 用法:
#   docker build -t prosecution-system .          # 构建
#   docker run -p 5000:5000 prosecution-system    # 运行 Web
#   docker run prosecution-system health           # CLI 健康检查
#   docker run prosecution-system rag-search "盗窃罪数额"  # CLI RAG 检索
# ============================================================

# ── 构建阶段 ──────────────────────────────────────────────
FROM python:3.12-slim as builder

WORKDIR /build

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# 预下载 Python 包（避免每次重复下载）
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ── 生产镜像 ──────────────────────────────────────────────
FROM python:3.12-slim

LABEL maintainer="prosecution-system"
LABEL description="检察机关办案系统 - RAG 增强法律检索平台"

WORKDIR /app

# 安装运行时系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        vim \
    && rm -rf /var/lib/apt/lists/*

# 从 builder 复制已安装的包
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# 创建非 root 用户
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# ── 复制应用代码 ──────────────────────────────────────────
COPY --chown=appuser:appuser . .

# ── 环境变量 ──────────────────────────────────────────────
ENV FLASK_ENV=production
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HF_HUB_DOWNLOAD_TIMEOUT=10       # HuggingFace 下载超时（秒）
ENV HF_HUB_HTTP_TIMEOUT=10

# ── 端口 ──────────────────────────────────────────────────
EXPOSE 5000

# ── 健康检查 ──────────────────────────────────────────────
# Web 服务健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health/live \
    || python -m src.cli health \
    || exit 1

# ── 入口点脚本 ──────────────────────────────────────────
COPY --chown=appuser:appuser docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]
CMD []
