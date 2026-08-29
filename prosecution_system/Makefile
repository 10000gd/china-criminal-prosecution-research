# ============================================================
# Makefile - 检察机关办案系统
# ============================================================
# 用法:
#   make build          # 构建 Docker 镜像
#   make up             # 启动所有服务（docker-compose）
#   make down           # 停止所有服务
#   make web            # 仅启动 Web 服务
#   make logs           # 查看日志
#   make cli CMD=health  # 运行 CLI 命令
#   make test           # 运行测试
#   make benchmark      # 运行 RAG benchmark
# ============================================================

IMAGE_NAME ?= prosecution-system
PORT       ?= 5000
COMPOSE    := docker-compose

.PHONY: build up down web logs cli test benchmark clean help

# ── Docker 构建 ──────────────────────────────────────────

build:
	docker build --platform linux/amd64 -t $(IMAGE_NAME) .

build-no-cache:
	docker build --platform linux/amd64 --no-cache -t $(IMAGE_NAME) .

# ── Docker Compose ───────────────────────────────────────

up:
	$(COMPOSE) up -d
	@echo "✅ Web 服务已启动: http://localhost:$(PORT)"
	@echo "   CLI 命令: make cli CMD=health"

down:
	$(COMPOSE) down

restart: down up

logs:
	$(COMPOSE) logs -f

# ── 独立 Web 服务 ─────────────────────────────────────────

web:
	docker run --rm \
		-p $(PORT):5000 \
		-v $(PWD)/cases:/app/cases \
		-v $(PWD)/data:/app/data \
		-v $(PWD)/output:/app/output \
		-e PORT=5000 \
		$(IMAGE_NAME)

# ── CLI 命令 ──────────────────────────────────────────────
# 示例: make cli CMD="health"
# 示例: make cli CMD="rag-search '盗窃罪数额较大'"
# 示例: make cli CMD="benchmark"

cli:
	docker run --rm --platform linux/amd64 \
		-v $(PWD)/cases:/app/cases \
		-v $(PWD)/data:/app/data \
		$(IMAGE_NAME) $(CMD)

# 直接运行（无需 Docker）
cli-local:
	@echo "Running: python -m src.cli $(CMD)"
	python3 -m src.cli $(CMD)

# ── 测试 ──────────────────────────────────────────────────

test:
	python3 -m pytest tests/ -v --tb=short

test-quick:
	python3 -m pytest tests/ -x --tb=short

# ── RAG Benchmark ─────────────────────────────────────────

benchmark:
	python3 -m src.rag_benchmark

benchmark-json:
	python3 -m src.rag_benchmark --export-json benchmark_results.json

# ── 清理 ──────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	rm -rf .pytest_cache 2>/dev/null || true
	rm -rf htmlcov 2>/dev/null || true
	rm -f benchmark_results.json 2>/dev/null || true
	@echo "✅ 清理完成"

# ── 帮助 ──────────────────────────────────────────────────

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
