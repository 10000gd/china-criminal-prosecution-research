# -*- coding: utf-8 -*-
"""API限流中间件"""
import time
from functools import wraps
from flask import request, jsonify, g
from threading import Lock

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
        
        # 计算剩余时间和次数
        with cls._lock:
            remaining = int(limiter.tokens)
            reset_time = int(time.time() + (limiter.capacity - remaining) / limiter.rate if limiter.rate > 0 else 0)
        
        return allowed, remaining, reset_time


def rate_limit(limit: int = 60, period: int = 60):
    """限流装饰器"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            allowed, remaining, reset_time = RateLimitMiddleware.check_rate_limit()
            
            # 设置响应头
            response = f(*args, **kwargs)
            
            # 如果返回是元组 (response, status_code)
            if isinstance(response, tuple):
                resp, status = response
            else:
                resp = response
                status = 200
            
            # 添加限流头
            if hasattr(resp, 'headers'):
                resp.headers['X-RateLimit-Limit'] = str(limit)
                resp.headers['X-RateLimit-Remaining'] = str(remaining)
                resp.headers['X-RateLimit-Reset'] = str(reset_time)
            
            return resp, status if isinstance(response, tuple) else (resp if not allowed else 200)
        
        # 如果被限流，返回429
        if not RateLimitMiddleware.check_rate_limit()[0]:
            return jsonify({
                'error': '请求过于频繁，请稍后再试',
                'code': 429,
                'retry_after': 60
            }), 429, {
                'X-RateLimit-Limit': str(limit),
                'X-RateLimit-Remaining': '0',
                'X-RateLimit-Reset': str(int(time.time()) + 60)
            }
        
        return wrapper
    return decorator
