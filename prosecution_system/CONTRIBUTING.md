# 贡献指南

欢迎贡献代码！

## 开发环境

```bash
# 克隆
git clone <repo>
cd prosecution_system

# 安装
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 开发
python src/web_app.py
```

## 代码规范

- Python使用UTF-8编码
- 中文注释
- 遵循PEP 8
- 函数/类添加docstring

## 测试

```bash
# 运行测试
PYTHONPATH=src python -m pytest tests/ -v

# 覆盖率
PYTHONPATH=src python -m pytest tests/ --cov=src --cov-report=html
```

## 提交规范

```
feat: 新功能
fix: 修复bug
docs: 文档更新
test: 测试更新
refactor: 重构
perf: 性能优化
```

## Pull Request流程

1. Fork项目
2. 创建特性分支 `git checkout -b feature/xxx`
3. 提交更改
4. 推送到远程
5. 创建Pull Request
