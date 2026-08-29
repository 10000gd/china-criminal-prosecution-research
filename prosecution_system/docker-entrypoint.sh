#!/bin/bash
# ============================================================
# Docker Entrypoint - 检察机关办案系统
# ============================================================
# 用法:
#   docker run prosecution-system          # 启动 Web 服务
#   docker run prosecution-system health     # CLI: 健康检查
#   docker run prosecution-system rag-search "盗窃罪数额"  # CLI: RAG 检索
#   docker run prosecution-system benchmark  # CLI: 检索 benchmark
# ============================================================

set -e

export PORT="${PORT:-5000}"

# 首次启动：等待数据库就绪
if [ ! -f "/app/data/prosecution.db" ]; then
    echo "[entrypoint] 初始化数据库..."
    mkdir -p /app/data /app/backups /app/output
fi

# 如果没有传入命令，默认启动 Web 服务
if [ $# -eq 0 ]; then
    echo "[entrypoint] 启动 Web 服务（gunicorn :$PORT）..."
    exec gunicorn \
        --bind "0.0.0.0:$PORT" \
        --workers 4 \
        --timeout 120 \
        --access-logfile - \
        --error-logfile - \
        "src.web_app:app"
fi

# CLI 模式：透传命令给 src.cli
echo "[entrypoint] 执行 CLI: $*"
exec python -m src.cli "$@"
