#!/bin/bash
# 启动脚本：warmup workers 后再开放服务
cd /root/.openclaw/workspace/prosecution_system
gunicorn -c gunicorn_config.py src.web_app:app >> logs/gunicorn.log 2>&1 &
GUNICORN_PID=$!

echo "[startup] 等待 workers 启动..."
sleep 8

echo "[startup] Warmup 请求（触发 LawRAG 初始化）..."
WORKERS=4
for i in $(seq 1 $WORKERS); do
  curl -s http://localhost:5000/health > /dev/null
  echo "  worker warmup $i/4"
done

echo "[startup] Workers 已就绪 (PID $GUNICORN_PID)"
echo "[startup] 服务: http://localhost:5000"
