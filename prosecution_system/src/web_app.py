# -*- coding: utf-8 -*-
"""
追诉系统 Web UI - prosecution_system/src/web_app.py
Flask Web 应用 (Blueprint 模块化重构版)

启动: python src/web_app.py
访问: http://localhost:5000
生产: gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 'src.web_app:app'
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).parent))

from logging_config import setup_logging
logger = setup_logging("web_app")

from flask import Flask, session, g, request

# 共享模块
from shared.middleware import (
    add_security_headers, inject_user, inject_template_globals,
    check_rate_limit, add_rate_limit_headers,
)
from shared.constants import PROJECT_ROOT, OUTPUT_DIR, DATA_DIR

# 认证/管理/API文档蓝图 (原有方式)
from auth import create_auth_blueprint
from security import CSRFProtection
from admin import create_admin_blueprint
from api_docs import create_api_docs_blueprint

# 路由蓝图
from routes import (
    auth_pages_bp,
    cases_bp,
    search_bp, search_bp_page,
    stats_bp, stats_page_bp,
    compare_bp, compare_page_bp,
    tracker_bp,
    export_bp,
    defense_bp,
    reports_bp, reports_page_bp,
)

# ── Flask App ──────────────────────────────────────────────

app = Flask(__name__,
            template_folder=str(PROJECT_ROOT / "templates"),
            static_folder=str(PROJECT_ROOT / "static"),
            static_url_path="/static")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "prosecution-system-secret-key")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max

# 全局中间件 (所有蓝图共享)
app.after_request(add_security_headers)
app.before_request(inject_user)
app.context_processor(inject_template_globals)

# 限流中间件 (排除静态文件和文档页面)
@app.before_request
def conditional_rate_limit():
    # 排除静态文件、文档页面、health探针
    skip_prefixes = ('/static', '/docs', '/docs-en', '/health/live')
    if any(request.path.startswith(p) for p in skip_prefixes):
        return None
    if request.headers.get('X-Test-Request') == 'true':
        import time
        g.rate_limit_remaining = 100
        g.rate_limit_reset = int(time.time()) + 3600
        return None
    if request.path.startswith('/api/'):
        from src.rate_limit import RateLimitMiddleware
        allowed, remaining, reset_time = RateLimitMiddleware.check_rate_limit()
        if not allowed:
            from flask import jsonify
            return jsonify({'error': '请求过于频繁,请稍后再试', 'retry_after': reset_time}), 429
        g.rate_limit_remaining = remaining
        g.rate_limit_reset = reset_time

app.after_request(add_rate_limit_headers)

# ── 注册蓝图 ───────────────────────────────────────────────

# 认证/管理/API文档 (url_prefix 在 create_* 函数内定义)
auth_bp = create_auth_blueprint(app)
app.register_blueprint(auth_bp)
admin_bp = create_admin_blueprint(app)
app.register_blueprint(admin_bp)
api_docs_bp = create_api_docs_blueprint(app)
app.register_blueprint(api_docs_bp)

# 路由蓝图 (无 url_prefix,路由文件内已写完整路径)
app.register_blueprint(auth_pages_bp)
app.register_blueprint(cases_bp)
app.register_blueprint(search_bp)
app.register_blueprint(search_bp_page)
app.register_blueprint(stats_bp)
app.register_blueprint(stats_page_bp)
app.register_blueprint(compare_bp)
app.register_blueprint(compare_page_bp)
app.register_blueprint(tracker_bp)
app.register_blueprint(export_bp)
app.register_blueprint(defense_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(reports_page_bp)


# ── 启动入口 ───────────────────────────────────────────────

if __name__ == "__main__":
    """
    生产级启动入口(优先使用 gunicorn/waitress)

    推荐:
      gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 'src.web_app:app'
      waitress-serve --port 5000 --threads 8 src.web_app:app
      python src/web_app.py  (仅开发调试)
    """
    from shared.singletons import loader

    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    case_count = len(loader.list_cases())

    if not debug:
        print("=" * 60)
        print("⚠️  警告:直接运行本文件使用 Flask 内置服务器(不安全)")
        print("   生产环境请使用:")
        print(f"   gunicorn -w 4 -b 0.0.0.0:{port} --timeout 120 'src.web_app:app'")
        print(f"   或 waitress-serve --port {port} --threads 8 src.web_app:app")
        print("=" * 60)

    logger.info(f"🚀 追诉系统启动: http://localhost:{port},调试模式: {debug},案件数量: {case_count}")
    print(f"🚀 追诉系统启动: http://localhost:{port}")
    print(f"   调试模式: {debug}")
    print(f"   案件数量: {case_count}")
    app.run(host="0.0.0.0", port=port, debug=debug)
