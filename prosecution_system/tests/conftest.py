# -*- coding: utf-8 -*-
"""
pytest 配置 — tests/conftest.py

确保 src/ 目录在 sys.path，让测试可以导入 src.* 模块
"""
import sys
from pathlib import Path

# 将项目根目录的 src/ 加入 sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

# 同时将项目根目录也加入（run_production.py 等模块需要）
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
