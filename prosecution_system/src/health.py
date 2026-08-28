# -*- coding: utf-8 -*-
"""健康检查与监控模块"""
import psutil
import time
from datetime import datetime
from typing import Dict

class HealthChecker:
    """健康检查器"""
    
    @classmethod
    def check(cls) -> Dict:
        """执行健康检查"""
        return {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'checks': {
                'database': cls.check_database(),
                'disk': cls.check_disk(),
                'memory': cls.check_memory(),
                'cpu': cls.check_cpu(),
            }
        }
    
    @classmethod
    def check_database(cls) -> Dict:
        """检查数据库"""
        try:
            from database import db
            with db.get_connection() as conn:
                conn.execute("SELECT 1")
            return {'status': 'ok', 'message': '数据库连接正常'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    @classmethod
    def check_disk(cls) -> Dict:
        """检查磁盘空间"""
        usage = psutil.disk_usage('/')
        percent = usage.percent
        if percent > 90:
            return {'status': 'warning', 'percent': percent, 'message': '磁盘空间不足'}
        return {'status': 'ok', 'percent': percent, 'message': f'磁盘使用 {percent:.1f}%'}
    
    @classmethod
    def check_memory(cls) -> Dict:
        """检查内存"""
        mem = psutil.virtual_memory()
        percent = mem.percent
        if percent > 85:
            return {'status': 'warning', 'percent': percent, 'message': '内存使用率过高'}
        return {'status': 'ok', 'percent': percent, 'message': f'内存使用 {percent:.1f}%'}
    
    @classmethod
    def check_cpu(cls) -> Dict:
        """检查CPU"""
        percent = psutil.cpu_percent(interval=1)
        if percent > 80:
            return {'status': 'warning', 'percent': percent, 'message': 'CPU使用率过高'}
        return {'status': 'ok', 'percent': percent, 'message': f'CPU使用 {percent:.1f}%'}


class MetricsCollector:
    """指标收集器"""
    
    _metrics = {
        'requests': 0,
        'errors': 0,
        'response_times': [],
        'start_time': time.time(),
    }
    
    @classmethod
    def record_request(cls, response_time: float, is_error: bool = False):
        """记录请求"""
        cls._metrics['requests'] += 1
        if is_error:
            cls._metrics['errors'] += 1
        cls._metrics['response_times'].append(response_time)
        # 保留最近1000条
        if len(cls._metrics['response_times']) > 1000:
            cls._metrics['response_times'] = cls._metrics['response_times'][-1000:]
    
    @classmethod
    def get_metrics(cls) -> Dict:
        """获取指标"""
        times = cls._metrics['response_times']
        return {
            'total_requests': cls._metrics['requests'],
            'total_errors': cls._metrics['errors'],
            'error_rate': cls._metrics['errors'] / max(cls._metrics['requests'], 1),
            'avg_response_time': sum(times) / len(times) if times else 0,
            'max_response_time': max(times) if times else 0,
            'min_response_time': min(times) if times else 0,
            'uptime_seconds': int(time.time() - cls._metrics['start_time']),
        }
    
    @classmethod
    def reset(cls):
        """重置指标"""
        cls._metrics['requests'] = 0
        cls._metrics['errors'] = 0
        cls._metrics['response_times'] = []
        cls._metrics['start_time'] = time.time()
