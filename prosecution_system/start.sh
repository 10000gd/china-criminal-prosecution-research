#!/bin/bash
# 刑事追诉系统启动脚本

set -e

echo "=========================================="
echo "  刑事追诉智能辅助系统 v2.0"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 未找到Python3${NC}"
    exit 1
fi

# 检查依赖
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}创建虚拟环境...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install -q -r requirements.txt
else
    source venv/bin/activate
fi

# 检查数据库
if [ ! -f "data/prosecution.db" ]; then
    echo -e "${YELLOW}初始化数据库...${NC}"
    mkdir -p data backups logs output
fi

# 启动选项
case "${1:-dev}" in
    dev)
        echo -e "${GREEN}启动开发服务器...${NC}"
        python src/web_app.py
        ;;
    prod)
        echo -e "${GREEN}启动生产服务器...${NC}"
        pip install -q gunicorn
        gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 'src.web_app:app'
        ;;
    docker)
        echo -e "${GREEN}启动Docker容器...${NC}"
        docker-compose up -d
        echo -e "${GREEN}访问 http://localhost:5000${NC}"
        ;;
    stop)
        echo -e "${YELLOW}停止Docker容器...${NC}"
        docker-compose down
        ;;
    restart)
        echo -e "${YELLOW}重启服务...${NC}"
        docker-compose restart
        ;;
    status)
        docker-compose ps
        ;;
    logs)
        docker-compose logs -f
        ;;
    stats)
        python3 cli_tools.py stats
        ;;
    *)
        echo "用法: $0 {dev|prod|docker|stop|restart|status|logs|stats}"
        exit 1
        ;;
esac
