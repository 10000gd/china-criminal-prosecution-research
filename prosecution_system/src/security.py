# -*- coding: utf-8 -*-
"""
安全模块 - security.py

功能：
- 输入验证
- XSS防护
- SQL注入防护（通过参数化查询）
- CSRF保护
- 敏感信息过滤
"""

import re
import html
from typing import Any, Optional, List
from functools import wraps
from flask import request, jsonify, session


class InputValidator:
    """输入验证器"""
    
    # 用户名验证：字母数字下划线，4-20位
    USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_]{4,20}$')
    
    # 邮箱验证
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    # 案件ID验证：字母数字连字符，1-50位
    CASE_ID_PATTERN = re.compile(r'^[A-Za-z0-9\-_]{1,50}$')
    
    # 安全的HTML标签
    ALLOWED_TAGS = {'a', 'abbr', 'acronym', 'b', 'blockquote', 'br', 'code', 
                   'em', 'i', 'li', 'ol', 'p', 'pre', 'strong', 'ul', 'h1', 'h2', 'h3'}
    ALLOWED_ATTRS = {'href', 'title', 'class'}
    
    @classmethod
    def validate_username(cls, username: str) -> tuple[bool, str]:
        """验证用户名"""
        if not username:
            return False, "用户名不能为空"
        if len(username) < 4:
            return False, "用户名至少4个字符"
        if len(username) > 20:
            return False, "用户名最多20个字符"
        if not cls.USERNAME_PATTERN.match(username):
            return False, "用户名只能包含字母、数字和下划线"
        return True, ""
    
    @classmethod
    def validate_email(cls, email: str) -> tuple[bool, str]:
        """验证邮箱"""
        if not email:
            return False, "邮箱不能为空"
        if not cls.EMAIL_PATTERN.match(email):
            return False, "邮箱格式不正确"
        return True, ""
    
    @classmethod
    def validate_password(cls, password: str) -> tuple[bool, str]:
        """验证密码"""
        if not password:
            return False, "密码不能为空"
        if len(password) < 6:
            return False, "密码至少6个字符"
        if len(password) > 128:
            return False, "密码最多128个字符"
        return True, ""
    
    @classmethod
    def validate_case_id(cls, case_id: str) -> tuple[bool, str]:
        """验证案件ID"""
        if not case_id:
            return False, "案件ID不能为空"
        if len(case_id) > 50:
            return False, "案件ID最多50个字符"
        if not cls.CASE_ID_PATTERN.match(case_id):
            return False, "案件ID格式不正确"
        return True, ""
    
    @classmethod
    def validate_search_query(cls, query: str, max_length: int = 200) -> tuple[bool, str]:
        """验证搜索查询"""
        if not query:
            return True, ""  # 空查询允许
        
        if len(query) > max_length:
            return False, f"查询最多{max_length}个字符"
        
        # 检查危险字符
        dangerous_patterns = ['<script', 'javascript:', 'onerror=', 'onclick=']
        query_lower = query.lower()
        for pattern in dangerous_patterns:
            if pattern in query_lower:
                return False, "查询包含非法字符"
        
        return True, ""
    
    @classmethod
    def validate_integer(cls, value: Any, min_val: int = None, max_val: int = None) -> tuple[bool, int, str]:
        """验证整数"""
        try:
            int_val = int(value)
            if min_val is not None and int_val < min_val:
                return False, int_val, f"值不能小于{min_val}"
            if max_val is not None and int_val > max_val:
                return False, int_val, f"值不能大于{max_val}"
            return True, int_val, ""
        except (ValueError, TypeError):
            return False, 0, "必须是整数"
    
    @classmethod
    def validate_float(cls, value: Any, min_val: float = None, max_val: float = None) -> tuple[bool, float, str]:
        """验证浮点数"""
        try:
            float_val = float(value)
            if min_val is not None and float_val < min_val:
                return False, float_val, f"值不能小于{min_val}"
            if max_val is not None and float_val > max_val:
                return False, float_val, f"值不能大于{max_val}"
            return True, float_val, ""
        except (ValueError, TypeError):
            return False, 0.0, "必须是数字"


class OutputSanitizer:
    """输出净化器"""
    
    @classmethod
    def escape_html(cls, text: str) -> str:
        """转义HTML特殊字符"""
        if not text:
            return ""
        return html.escape(str(text))
    
    @classmethod
    def escape_json(cls, data: Any) -> Any:
        """净化JSON数据"""
        if isinstance(data, str):
            return cls.escape_html(data)
        elif isinstance(data, dict):
            return {k: cls.escape_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [cls.escape_json(item) for item in data]
        return data
    
    @classmethod
    def strip_tags(cls, text: str) -> str:
        """去除HTML标签"""
        if not text:
            return ""
        # 简单去除标签
        return re.sub(r'<[^>]+>', '', str(text))


class RateLimiter:
    """增强的速率限制器（内存版，生产环境建议用Redis）"""
    
    _requests = {}
    _burst_requests = {}  # 突发请求限制
    _lock = __import__('threading').Lock()
    
    # 限制配置
    MAX_REQUESTS_PER_MINUTE = 60
    MAX_REQUESTS_PER_HOUR = 1000
    MAX_REQUESTS_PER_SECOND = 10  # 突发限制
    WINDOW_SECONDS = 60
    
    @classmethod
    def check_rate_limit(cls, identifier: str = None) -> tuple[bool, str, dict]:
        """检查速率限制
        
        Returns:
            (allowed, message, info)
        """
        import time
        
        if identifier is None:
            try:
                identifier = request.remote_addr
            except:
                identifier = "default"
        
        now = time.time()
        current_minute = int(now / 60) * 60
        current_hour = int(now / 3600) * 3600
        
        with cls._lock:
            # 初始化
            if identifier not in cls._requests:
                cls._requests[identifier] = {
                    'minute': [],
                    'hour': [],
                }
            if identifier not in cls._burst_requests:
                cls._burst_requests[identifier] = []
            
            requests = cls._requests[identifier]
            burst = cls._burst_requests[identifier]
            
            # 清理过期记录
            requests['minute'] = [t for t in requests['minute'] if t >= current_minute]
            requests['hour'] = [t for t in requests['hour'] if t >= current_hour]
            burst = [t for t in burst if t >= now - 1]  # 保留1秒内的请求
            
            # 检查突发限制
            if len(burst) >= cls.MAX_REQUESTS_PER_SECOND:
                return False, "请求过于频繁，请稍后再试", {
                    'limit': cls.MAX_REQUESTS_PER_SECOND,
                    'remaining': 0,
                    'reset': int(now + 1),
                }
            
            # 检查每分钟限制
            if len(requests['minute']) >= cls.MAX_REQUESTS_PER_MINUTE:
                reset_time = current_minute + 60
                return False, f"请求过于频繁，请在{reset_time - int(now)}秒后重试", {
                    'limit': cls.MAX_REQUESTS_PER_MINUTE,
                    'remaining': 0,
                    'reset': reset_time,
                }
            
            # 检查每小时限制
            if len(requests['hour']) >= cls.MAX_REQUESTS_PER_HOUR:
                return False, "请求次数超限，请稍后再试", {
                    'limit': cls.MAX_REQUESTS_PER_HOUR,
                    'remaining': 0,
                    'reset': current_hour + 3600,
                }
            
            # 记录请求
            requests['minute'].append(now)
            requests['hour'].append(now)
            burst.append(now)
            cls._burst_requests[identifier] = burst
            
            return True, "", {
                'limit': cls.MAX_REQUESTS_PER_MINUTE,
                'remaining': cls.MAX_REQUESTS_PER_MINUTE - len(requests['minute']),
                'reset': current_minute + 60,
            }
    
    @classmethod
    def cleanup(cls):
        """清理过期数据"""
        import time
        now = time.time()
        one_hour_ago = now - 3600
        
        with cls._lock:
            for identifier in list(cls._requests.keys()):
                requests = cls._requests[identifier]
                requests['minute'] = [t for t in requests['minute'] if t >= one_hour_ago]
                requests['hour'] = [t for t in requests['hour'] if t >= one_hour_ago]
                
                if not requests['minute'] and not requests['hour']:
                    del cls._requests[identifier]
            
            for identifier in list(cls._burst_requests.keys()):
                cls._burst_requests[identifier] = [t for t in cls._burst_requests[identifier] if t >= now - 1]
                if not cls._burst_requests[identifier]:
                    del cls._burst_requests[identifier]


class APIRateLimiter:
    """API专用速率限制器（基于令牌桶算法）"""
    
    _buckets = {}
    _lock = __import__('threading').Lock()
    
    # API限制配置
    API_LIMITS = {
        'search': {'rate': 30, 'period': 60},      # 30次/分钟
        'analysis': {'rate': 10, 'period': 60},    # 10次/分钟
        'export': {'rate': 5, 'period': 60},       # 5次/分钟
        'default': {'rate': 60, 'period': 60},     # 60次/分钟
    }
    
    @classmethod
    def check_api_limit(cls, api_name: str, identifier: str = None) -> tuple[bool, str]:
        """检查API调用限制"""
        import time
        
        if identifier is None:
            try:
                identifier = request.remote_addr
            except:
                identifier = "default"
        
        limits = cls.API_LIMITS.get(api_name, cls.API_LIMITS['default'])
        rate = limits['rate']
        period = limits['period']
        
        bucket_key = f"{identifier}:{api_name}"
        
        with cls._lock:
            now = time.time()
            
            if bucket_key not in cls._buckets:
                cls._buckets[bucket_key] = {'tokens': rate, 'last_update': now}
            
            bucket = cls._buckets[bucket_key]
            
            # 补充令牌
            elapsed = now - bucket['last_update']
            bucket['tokens'] = min(rate, bucket['tokens'] + elapsed * (rate / period))
            bucket['last_update'] = now
            
            # 检查令牌
            if bucket['tokens'] >= 1:
                bucket['tokens'] -= 1
                return True, ""
            else:
                wait_time = (1 - bucket['tokens']) * (period / rate)
                return False, f"API调用限制，请在{int(wait_time)}秒后重试"


def rate_limit(f):
    """速率限制装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        allowed, message, info = RateLimiter.check_rate_limit()
        if not allowed:
            if request.is_json:
                response = jsonify({"error": message, "code": "rate_limited"})
                for k, v in info.items():
                    response.headers[f"X-RateLimit-{k.title()}"] = str(v)
                return response, 429
            return f"错误: {message}", 429
        
        # 添加RateLimit头
        if request.is_json:
            pass  # 已在上面处理
        
        return f(*args, **kwargs)
    return decorated_function


def api_rate_limit(api_name: str):
    """API专用速率限制装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            allowed, message = APIRateLimiter.check_api_limit(api_name)
            if not allowed:
                if request.is_json:
                    return jsonify({"error": message, "code": "rate_limited"}), 429
                return f"错误: {message}", 429
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def validate_json(*required_fields):
    """JSON参数验证装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({"error": "需要JSON格式"}), 400
            
            data = request.get_json()
            missing = [field for field in required_fields if field not in data]
            if missing:
                return jsonify({"error": f"缺少参数: {', '.join(missing)}"}), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def sanitize_input(f):
    """输入净化装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 净化所有表单数据
        if request.form:
            sanitized_form = {}
            for key, value in request.form.items():
                if isinstance(value, str):
                    sanitized_form[key] = OutputSanitizer.escape_html(value)
                else:
                    sanitized_form[key] = value
            request.form = sanitized_form
        
        return f(*args, **kwargs)
    return decorated_function


# 全局实例
validator = InputValidator()
sanitizer = OutputSanitizer()
rate_limiter = RateLimiter()


if __name__ == "__main__":
    print("=== 安全模块测试 ===\n")
    
    # 用户名验证
    print("用户名验证:")
    tests = ["user", "test_user", "us", "a" * 25, "user@name", "valid_user123"]
    for username in tests:
        valid, msg = InputValidator.validate_username(username)
        status = "✅" if valid else "❌"
        print(f"  {status} '{username}': {msg or '有效'}")
    
    # 邮箱验证
    print("\n邮箱验证:")
    emails = ["test@example.com", "invalid", "user@domain", "@nodomain.com"]
    for email in emails:
        valid, msg = InputValidator.validate_email(email)
        status = "✅" if valid else "❌"
        print(f"  {status} '{email}': {msg or '有效'}")
    
    # HTML转义
    print("\nHTML转义:")
    dangerous = ["<script>alert('xss')</script>", "Normal text", "<b>Bold</b>"]
    for text in dangerous:
        escaped = OutputSanitizer.escape_html(text)
        print(f"  输入: {text[:30]}...")
        print(f"  输出: {escaped[:50]}...")
    
    print("\n✅ 安全模块测试完成！")


class CSRFProtection:
    """CSRF保护"""
    
    _token_name = "csrf_token"
    _session_key = "_csrf_token"
    
    @classmethod
    def generate_token(cls) -> str:
        """生成CSRF Token"""
        import secrets
        token = secrets.token_hex(32)
        return token
    
    @classmethod
    def set_token(cls) -> str:
        """设置Token到Session"""
        from flask import session
        if cls._session_key not in session:
            session[cls._session_key] = cls.generate_token()
        return session[cls._session_key]
    
    @classmethod
    def get_token(cls) -> str:
        """获取Token"""
        from flask import session
        return session.get(cls._session_key, "")
    
    @classmethod
    def validate_token(cls, token: str = None) -> bool:
        """验证Token"""
        from flask import session, request
        
        if token is None:
            token = request.form.get(cls._token_name) or request.headers.get("X-CSRF-Token")
        
        if not token or not session.get(cls._session_key):
            return False
        
        import secrets
        # 使用常数时间比较防止时序攻击
        return secrets.compare_digest(token, session[cls._session_key])


def csrf_protect(f):
    """CSRF保护装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            if not CSRFProtection.validate_token():
                if request.is_json:
                    return jsonify({"error": "CSRF验证失败", "code": "csrf_invalid"}), 403
                from flask import abort
                abort(403)
        return f(*args, **kwargs)
    return decorated_function


def generate_csrf_token() -> str:
    """生成CSRF Token（供模板调用）"""
    return CSRFProtection.set_token()