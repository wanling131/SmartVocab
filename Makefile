# SmartVocab Makefile - 常用命令快捷方式
# 使用: make <command>

.PHONY: help test test-unit test-e2e run lint format clean install db-test

# 默认显示帮助
help:
	@echo "SmartVocab 常用命令:"
	@echo ""
	@echo "  make run         启动开发服务器"
	@echo "  make test        运行所有单元测试"
	@echo "  make test-unit   运行单元测试（快速模式）"
	@echo "  make test-e2e    运行 E2E 测试"
	@echo "  make lint        代码检查 (flake8 + isort)"
	@echo "  make format      格式化代码 (black + isort)"
	@echo "  make clean       清理缓存和临时文件"
	@echo "  make install     安装依赖"
	@echo "  make db-test     测试数据库连接"
	@echo ""

# 启动开发服务器
run:
	python main.py

# 运行单元测试
test:
	python -m pytest tests/ -v --tb=short

# 快速单元测试（跳过深度学习加载）
test-unit:
	SMARTVOCAB_SKIP_DL_INIT=1 python -m pytest tests/ -v --tb=short

# E2E 测试
test-e2e:
	cd tests/e2e && npx playwright test

# 代码检查
lint:
	flake8 api/ core/ tools/ --max-line-length=100 --extend-ignore=E203,W503
	isort --check-only --profile=black api/ core/ tools/

# 格式化代码
format:
	black --line-length=100 api/ core/ tools/
	isort --profile=black api/ core/ tools/

# 清理缓存
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov/ 2>/dev/null || true

# 安装依赖
install:
	pip install -r requirements.txt
	cd tests/e2e && npm install

# 测试数据库连接
db-test:
	python -c "from tools.database import test_connection; test_connection()"