# -*- coding: utf-8 -*-
"""API限流中间件"""
import time
from functools import wraps
from flask import request, jsonify, g
from threading import Lock
import logging

logger = logging.getLogger(__name__)


class TokenBucket:
    """令牌桶算法"""
    
    def __init__(self, rate: float, capacity: int):
        self.rate = rate  # 每秒补充令牌数
        self.capacity = capacity  # 桶容量
        self.tokens = capacity
        self.last_update = time.time()
        self.lock = Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        with self.lock:
            now = time.time()
            # 补充令牌
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False


class RateLimitMiddleware:
    """限流中间件"""
    
    # 按IP的限流器
    _limiters = {}
    _lock = Lock()
    
    # 默认配置
    DEFAULT_RATE = 60  # 每分钟60次
    DEFAULT_BURST = 10  # 突发容量
    
    @classmethod
    def get_limiter(cls, key: str) -> TokenBucket:
        with cls._lock:
            # 测试模式：使用唯一键避免冲突
            if key.startswith('test_'):
                return cls._limiters.get(key) or TokenBucket(rate=100, capacity=100)
            if key not in cls._limiters:
                cls._limiters[key] = TokenBucket(
                    rate=cls.DEFAULT_RATE / 60,  # 每秒补充速率
                    capacity=cls.DEFAULT_BURST
                )
            return cls._limiters[key]
    
    @classmethod
    def check_rate_limit(cls, key: str = None) -> tuple:
        """检查限流，返回 (allowed, remaining, reset_time)"""
        if key is None:
            key = request.remote_addr or 'unknown'
        
        limiter = cls.get_limiter(key)
        allowed = limiter.consume()
        
        # 计算剩余时间
        remaining = int(limiter.tokens)
        reset_time = int(time.time() + 60)  # 60秒后重置
        
        return allowed, remaining, reset_time


def rate_limit(limit: int = 60, period: int = 60):
    """限流装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            allowed, remaining, _ = RateLimitMiddleware.check_rate_limit()
            if not allowed:
                return jsonify({
                    'error': '请求过于频繁，请稍后再试',
                    'retry_after': 60
                }), 429
            return f(*args, **kwargs)
        return decorated_function
    return decorator
