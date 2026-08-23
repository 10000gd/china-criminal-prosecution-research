# -*- coding: utf-8 -*-
"""
统一日志配置 - prosecution_system/src/logging_config.py

功能：
- JSON 格式日志（生产环境）
- 控制台彩色输出（开发环境）
- 日志轮转（10MB，保留 5 个）

用法：
    from logging_config import setup_logging
    logger = setup_logging("prosecution_system")

环境变量：
    LOG_LEVEL      - 日志级别（DEBUG/INFO/WARNING/ERROR），默认 INFO
    LOG_ENV        - 环境（production/development），默认读取 FLASK_DEBUG
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# 按需导入（colored 需要 coloredlogs 包）
try:
    import coloredlogs
    COLOREDLOGS_AVAILABLE = True
except ImportError:
    COLOREDLOGS_AVAILABLE = False

# 项目根目录（src/ 的父级）
PROJECT_ROOT = Path(__file__).parent.parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 全局安装标志（防止重复 install）
_logging_installed = False


class JSONFormatter(logging.Formatter):
    """
    JSON 格式日志（用于生产环境文件输出）
    """

    def __init__(self, fmt_dict=None, **kwargs):
        super().__init__()
        self.fmt_dict = fmt_dict or {}

    def format(self, record: logging.LogRecord) -> str:
        import json
        from datetime import datetime, timezone

        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # 附加 extra 字段
        for key, val in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "exc_info", "exc_text", "thread", "threadName",
                "message", "asctime",
            ):
                log_entry[key] = val

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class ColoredConsoleFormatter(logging.Formatter):
    """
    彩色控制台格式（用于开发环境）
    """

    COLORS = {
        "DEBUG":    "\033[36m",    # cyan
        "INFO":     "\033[32m",    # green
        "WARNING":  "\033[33m",    # yellow
        "ERROR":    "\033[31m",    # red
        "CRITICAL": "\033[35m",    # magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        record.msg = f"{color}{record.msg}{self.RESET}"
        return super().format(record)


def _get_log_env() -> str:
    """判断当前运行环境"""
    log_env = os.environ.get("LOG_ENV", "").lower()
    if log_env in ("production", "prod"):
        return "production"
    if os.environ.get("FLASK_DEBUG", "").lower() == "true":
        return "development"
    if sys.flags.debug:  # python -d
        return "development"
    return "production"


def setup_logging(
    name: str = "prosecution_system",
    level: str = None,
    log_env: str = None,
    log_dir: Path = LOG_DIR,
    to_file: bool = True,
    to_console: bool = True,
    json_file: bool = None,
) -> logging.Logger:
    """
    配置并返回 logger 实例

    参数：
        name        - logger 名称
        level       - 日志级别（默认从 LOG_LEVEL 环境变量或 INFO）
        log_env     - 强制指定环境（production/development）
        log_dir     - 日志文件目录
        to_file     - 是否输出到文件
        to_console  - 是否输出到控制台
        json_file   - 文件是否用 JSON 格式（None=生产环境用JSON，开发环境用普通格式）
    """
    global _logging_installed

    env = log_env or _get_log_env()
    is_prod = env == "production"

    log_level = (level or os.environ.get("LOG_LEVEL", "INFO")).upper()
    log_level_num = getattr(logging, log_level, logging.INFO)

    # 主 logger
    logger = logging.getLogger(name)
    logger.setLevel(log_level_num)
    logger.handlers.clear()

    # ---- 文件处理器（带轮转）----
    if to_file:
        if json_file is None:
            json_file = is_prod

        log_file = log_dir / f"{name}.log"
        file_handler = RotatingFileHandler(
            filename=str(log_file),
            maxBytes=10 * 1024 * 1024,   # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level_num)

        if json_file:
            file_handler.setFormatter(JSONFormatter())
        else:
            file_fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(module)s:%(funcName)s:%(lineno)d | %(message)s"
            file_handler.setFormatter(logging.Formatter(file_fmt))

        logger.addHandler(file_handler)

    # ---- 控制台处理器 ----
    if to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level_num)

        if COLOREDLOGS_AVAILABLE and not is_prod:
            # 使用 coloredlogs（彩色且结构化）
            coloredlogs.install(
                logger=logger,
                level=log_level_num,
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%H:%M:%S",
            )
        else:
            if is_prod:
                # 生产环境控制台用 JSON
                console_handler.setFormatter(JSONFormatter())
            else:
                # 开发环境控制台用彩色简单格式
                console_fmt = "%(asctime)s \033[90m%(name)s\033[0m | %(levelname)-8s | %(message)s"
                console_handler.setFormatter(
                    ColoredConsoleFormatter(console_fmt, datefmt="%H:%M:%S")
                )
            logger.addHandler(console_handler)

    return logger


# ---- 全局快捷函数 ----

_default_logger: logging.Logger = None


def get_logger(name: str = "prosecution_system") -> logging.Logger:
    """获取已配置的 logger（延迟初始化）"""
    global _default_logger
    if _default_logger is None:
        _default_logger = setup_logging(name)
    return _default_logger


# ---- 自动安装（import 时生效）----
# 注意：直接 import 本模块不会自动安装，需要调用 setup_logging()
# 各模块应在其入口处调用：logger = setup_logging(模块名)
