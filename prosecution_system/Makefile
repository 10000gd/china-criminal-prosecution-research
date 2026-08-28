.PHONY: help install dev prod docker test clean backup

help:
	@echo "刑事追诉智能辅助系统 - Makefile"
	@echo ""
	@echo "可用命令:"
	@echo "  make install    - 安装依赖"
	@echo "  make dev       - 开发模式运行"
	@echo "  make prod      - 生产模式运行"
	@echo "  make docker    - Docker部署"
	@echo "  make test      - 运行测试"
	@echo "  make clean     - 清理缓存"
	@echo "  make backup    - 备份数据库"

install:
	python3 -m venv venv
	./venv/bin/pip install -r requirements.txt

dev:
	./venv/bin/python src/web_app.py

prod:
	./venv/bin/pip install gunicorn
	./venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 'src.web_app:app'

docker-build:
	docker build -t prosecution-system .

docker:
	docker-compose up -d
	@echo "访问 http://localhost:5000"

docker-stop:
	docker-compose down

docker-logs:
	docker-compose logs -f

test:
	PYTHONPATH=src ./venv/bin/python -m pytest tests/ -v

test-cov:
	PYTHONPATH=src ./venv/bin/python -m pytest tests/ --cov=src --cov-report=html

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache htmlcov
	rm -rf venv

backup:
	@mkdir -p backups
	cp data/prosecution.db backups/backup_$$(date +%Y%m%d_%H%M%S).db
	@echo "备份完成"

stats:
	./venv/bin/python cli_tools.py stats

cli-search:
	@read -p "搜索关键词: " q; ./venv/bin/python cli_tools.py search "$$q"
