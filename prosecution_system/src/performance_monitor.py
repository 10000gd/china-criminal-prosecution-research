# -*- coding: utf-8 -*-
"""性能监控和告警模块"""
import time
import logging
import psutil
import threading
from collections import deque
from datetime import datetime
from flask import g, request

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """性能监控器"""
    
    _instance = None
    _lock = threading.Lock()
    
    # 监控配置
    MAX_HISTORY = 1000  # 保留最近1000条记录
    SLOW_THRESHOLD = 1.0  # 慢请求阈值（秒）
    MEMORY_WARNING = 0.8  # 内存使用率警告（80%）
    CPU_WARNING = 0.8  # CPU使用率警告（80%）
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance
    
    def _init(self):
        """初始化"""
        self.request_history = deque(maxlen=self.MAX_HISTORY)
        self.slow_requests = deque(maxlen=100)
        self.errors = deque(maxlen=100)
        self.start_time = time.time()
        self._lock = threading.Lock()
    
    def record_request(self, endpoint: str, method: str, duration: float, 
                       status_code: int, ip: str = None):
        """记录请求"""
        with self._lock:
            record = {
                'timestamp': datetime.now().isoformat(),
                'endpoint': endpoint,
                'method': method,
                'duration': duration,
                'status': status_code,
                'ip': ip or request.remote_addr if request else 'unknown'
            }
            self.request_history.append(record)
            
            # 慢请求告警
            if duration > self.SLOW_THRESHOLD:
                self.slow_requests.append(record)
                logger.warning(f"慢请求: {method} {endpoint} 耗时 {duration:.2f}s")
            
            # 错误记录
            if status_code >= 400:
                self.errors.append(record)
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        with self._lock:
            if not self.request_history:
                return {
                    'total_requests': 0,
                    'avg_duration': 0,
                    'error_rate': 0,
                    'slow_requests': 0
                }
            
            total = len(self.request_history)
            durations = [r['duration'] for r in self.request_history]
            errors = sum(1 for r in self.request_history if r['status'] >= 400)
            slow = sum(1 for r in self.request_history if r['duration'] > self.SLOW_THRESHOLD)
            
            return {
                'total_requests': total,
                'avg_duration': sum(durations) / len(durations),
                'max_duration': max(durations),
                'min_duration': min(durations),
                'error_rate': errors / total if total > 0 else 0,
                'slow_requests': slow,
                'uptime': time.time() - self.start_time
            }
    
    def get_system_stats(self) -> dict:
        """获取系统资源使用情况"""
        try:
            memory = psutil.virtual_memory()
            cpu = psutil.cpu_percent(interval=0.1)
            
            stats = {
                'memory_percent': memory.percent,
                'memory_available_mb': memory.available / (1024 * 1024),
                'cpu_percent': cpu,
                'memory_warning': memory.percent > self.MEMORY_WARNING * 100,
                'cpu_warning': cpu > self.CPU_WARNING * 100
            }
            
            # 告警
            if stats['memory_warning']:
                logger.warning(f"内存使用率过高: {memory.percent:.1f}%")
            if stats['cpu_warning']:
                logger.warning(f"CPU使用率过高: {cpu:.1f}%")
            
            return stats
        except Exception as e:
            logger.error(f"获取系统统计失败: {e}")
            return {}
    
    def get_recent_errors(self, limit: int = 10) -> list:
        """获取最近错误"""
        with self._lock:
            return list(self.errors)[-limit:]
    
    def get_slow_requests(self, limit: int = 10) -> list:
        """获取慢请求"""
        with self._lock:
            return sorted(self.slow_requests, key=lambda x: x['duration'], reverse=True)[:limit]


# 全局实例
monitor = PerformanceMonitor()


def setup_performance_monitoring(app):
    """配置性能监控"""
    
    @app.before_request
    def before_request():
        """请求开始时记录时间"""
        g.request_start_time = time.time()
    
    @app.after_request
    def after_request(response):
        """请求结束后记录性能数据"""
        if hasattr(g, 'request_start_time'):
            duration = time.time() - g.request_start_time
            monitor.record_request(
                endpoint=request.path,
                method=request.method,
                duration=duration,
                status_code=response.status_code
            )
            
            # 添加性能头
            response.headers['X-Response-Time'] = f'{duration*1000:.0f}ms'
        
        return response
    
    logger.info("性能监控已启用")
    return monitor
