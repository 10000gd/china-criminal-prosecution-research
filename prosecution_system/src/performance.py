# -*- coding: utf-8 -*-
"""性能优化模块"""
import functools
import hashlib
import pickle
from typing import Callable, Any
from datetime import datetime, timedelta

class LRUCache:
    """LRU缓存"""
    
    def __init__(self, maxsize: int = 128):
        self.maxsize = maxsize
        self.cache = {}
        self.access_order = []
    
    def get(self, key: str) -> Any:
        if key in self.cache:
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        if key in self.cache:
            self.access_order.remove(key)
        elif len(self.cache) >= self.maxsize:
            oldest = self.access_order.pop(0)
            del self.cache[oldest]
        self.cache[key] = value
        self.access_order.append(key)
    
    def clear(self):
        self.cache.clear()
        self.access_order.clear()


class QueryCache:
    """查询缓存"""
    
    def __init__(self):
        self.cache = {}
        self.expiry = {}
    
    def _make_key(self, *args, **kwargs) -> str:
        key_data = f"{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key: str) -> Any:
        if key in self.cache:
            if datetime.now() < self.expiry[key]:
                return self.cache[key]
            else:
                del self.cache[key]
                del self.expiry[key]
        return None
    
    def set(self, key: str, value: Any, ttl_seconds: int = 300):
        self.cache[key] = value
        self.expiry[key] = datetime.now() + timedelta(seconds=ttl_seconds)
    
    def clear_expired(self):
        now = datetime.now()
        expired = [k for k, v in self.expiry.items() if now >= v]
        for k in expired:
            self.cache.pop(k, None)
            self.expiry.pop(k, None)


# 全局缓存实例
query_cache = QueryCache()
route_cache = LRUCache(maxsize=256)


def cached(ttl: int = 300):
    """缓存装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            result = query_cache.get(key)
            if result is not None:
                return result
            result = func(*args, **kwargs)
            query_cache.set(key, result, ttl)
            return result
        return wrapper
    return decorator


def lrucached(maxsize: int = 128):
    """LRU缓存装饰器"""
    cache = LRUCache(maxsize)
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            result = cache.get(key)
            if result is not None:
                return result
            result = func(*args, **kwargs)
            cache.set(key, result)
            return result
        wrapper.cache = cache
        return wrapper
    return decorator
