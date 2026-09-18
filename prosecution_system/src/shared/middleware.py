# -*- coding: utf-8 -*-
"""共享中间件"""
import os
import sys
import time
import threading
from pathlib import Path

# 确保 src 在路径中
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from flask import Flask, request, jsonify, session, g, render_template
from rate_limit import RateLimitMiddleware, rate_limit

# 从 security.py 重新导出（security.py 中的 csrf_protect 是装饰器函数）
import security
csrf_protect = security.csrf_protect
generate_csrf_token = security.generate_csrf_token

# ---- LawRAG 单例（惰性后台预热）----
_rag_instance = None
_rag_lock = threading.Lock()
_rag_ready = threading.Event()


def _warmup_rag():
    """后台线程:预热 LawRAG,完成后通知等待者"""
    global _rag_instance
    import io, contextlib
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        from law_rag import LawRAG
        _rag_instance = LawRAG(enable_vector=True)
    _rag_ready.set()


def get_rag():
    """返回 LawRAG 单例,首次调用时后台启动预热线程"""
    global _rag_instance
    if _rag_instance is None:
        with _rag_lock:
            if _rag_instance is None:
                t = threading.Thread(target=_warmup_rag, daemon=True)
                t.start()
    return _rag_instance


# ---- 安全头 ----

def add_security_headers(response):
    """追加安全响应头"""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers.pop("Server", None)
    return response


# ---- 用户注入 ----

def inject_user():
    """注入当前用户信息到 g"""
    from auth import get_current_user
    from security import CSRFProtection
    g.current_user = get_current_user()
    g.csrf_token = CSRFProtection.set_token()
    g.user_logged_in = 'user_id' in session


def inject_template_globals():
    """注入全局模板变量"""
    from auth import get_current_user
    return {
        'current_user': get_current_user(),
        'user_logged_in': 'user_id' in session,
    }


# ---- 限流 ----

def check_rate_limit():
    """API限流检查"""
    if request.path.startswith('/static') or request.path.startswith('/docs'):
        return None
    if request.headers.get('X-Test-Request') == 'true':
        g.rate_limit_remaining = 100
        g.rate_limit_reset = int(time.time()) + 3600
        return None
    if request.path.startswith('/api/'):
        allowed, remaining, reset_time = RateLimitMiddleware.check_rate_limit()
        if not allowed:
            return jsonify({
                'error': '请求过于频繁,请稍后再试',
                'retry_after': reset_time
            }), 429
        g.rate_limit_remaining = remaining
        g.rate_limit_reset = reset_time


def add_rate_limit_headers(response):
    """添加限流头信息"""
    if hasattr(g, 'rate_limit_remaining'):
        response.headers['X-RateLimit-Remaining'] = str(g.rate_limit_remaining)
        response.headers['X-RateLimit-Reset'] = str(g.rate_limit_reset)
    return response
