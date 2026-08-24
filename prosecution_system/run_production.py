# -*- coding: utf-8 -*-
"""
生产级启动脚本 - prosecution_system/run_production.py

推荐启动方式（优先级从高到低）：

1. gunicorn（推荐，用于真实生产环境）:
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 'src.web_app:app'

2. waitress（Windows或单服务器环境）:
   pip install waitress
   python run_production.py

3. 内置服务器（仅用于开发调试）:
   python src/web_app.py

⚠️ 禁止在生产环境使用 python src/web_app.py（Flask内置服务器不安全且不支持并发）
"""

import os
import sys
import warnings
from pathlib import Path

# Add src to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Suppress deprecation warnings in production
os.environ.setdefault("FLASK_ENV", "production")

import jinja2
from flask import Flask

# Import the app from web_app
from web_app import app as flask_app

APP = flask_app


def run_with_waitress():
    """使用 waitress 生产服务器（纯 Python，无需编译）"""
    try:
        from waitress import serve
        port = int(os.environ.get("PORT", 5000))
        host = os.environ.get("HOST", "0.0.0.0")
        threads = int(os.environ.get("WAITRESS_THREADS", 8))
        print(f"🚀 [生产模式] 使用 waitress 启动 (threads={threads})")
        print(f"   访问地址: http://{host}:{port}")
        print(f"   Workers: 1 (waitress单进程多线程)")
        print(f"   线程数: {threads}")
        print(f"   启动时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        serve(
            APP,
            host=host,
            port=port,
            threads=threads,
            channel_timeout=120,
            cleanup_interval=60,
        )
    except ImportError:
        print("❌ waitress 未安装。运行以下命令安装：")
        print("   pip install waitress")
        print("   或使用 gunicorn：gunicorn -w 4 -b 0.0.0.0:5000 'src.web_app:app'")
        sys.exit(1)


def run_with_gunicorn():
    """使用 gunicorn（推荐生产方案）"""
    import shlex
    port = os.environ.get("PORT", "5000")
    host = os.environ.get("HOST", "0.0.0.0")
    workers = os.environ.get("GUNICORN_WORKERS", "4")
    timeout = os.environ.get("GUNICORN_TIMEOUT", "120")

    cmd = f"gunicorn -w {workers} -b {host}:{port} --timeout {timeout} --access-logfile - 'src.web_app:app'"
    print(f"🚀 [生产模式] 使用 gunicorn 启动")
    print(f"   命令: {cmd}")
    print(f"   Workers: {workers}, Timeout: {timeout}s")
    os.system(cmd)


def run_dev_warning():
    """仅用于开发调试，不适合生产"""
    warnings.warn(
        "⚠️ 使用 Flask 内置服务器（仅开发用）！"
        "生产环境请使用: gunicorn -w 4 -b 0.0.0.0:5000 'src.web_app:app'"
        "或 waitress: python run_production.py",
        UserWarning,
        stacklevel=2,
    )
    from web_app import app
    port = int(os.environ.get("PORT", 5000))
    print("=" * 60)
    print("⚠️  警告：使用开发模式启动！")
    print("   这不是生产安全的配置。")
    print("   生产启动方式:")
    print("   gunicorn -w 4 -b 0.0.0.0:5000 'src.web_app:app'")
    print("   或: python run_production.py")
    print("=" * 60)
    print(f"🚀 追诉系统启动: http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)


def main():
    mode = os.environ.get("SERVER_MODE", "auto").lower()

    if mode == "gunicorn":
        run_with_gunicorn()
    elif mode == "waitress":
        run_with_waitress()
    elif mode == "dev":
        run_dev_warning()
    else:
        # 自动检测：优先gunicorn，次选waitress，最后开发模式
        try:
            import gunicorn
            run_with_gunicorn()
        except ImportError:
            try:
                import waitress
                run_with_waitress()
            except ImportError:
                print("⚠️ 未检测到生产服务器（gunicorn/waitress）")
                print("建议安装: pip install gunicorn (Linux) 或 pip install waitress (Windows)")
                print("临时使用开发模式（不安全，仅调试用）...")
                print()
                run_dev_warning()


if __name__ == "__main__":
    main()
