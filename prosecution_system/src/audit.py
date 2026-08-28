# -*- coding: utf-8 -*-
"""
审计日志模块 - audit.py

功能：
- 记录所有操作
- 合规审计追踪
- 安全事件记录
"""

from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, asdict
from database import db


class AuditAction(Enum):
    """审计动作类型"""
    # 认证
    LOGIN = "login"
    LOGOUT = "logout"
    REGISTER = "register"
    PASSWORD_CHANGE = "password_change"
    
    # 用户操作
    USER_VIEW = "user_view"
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    USER_ROLE_CHANGE = "user_role_change"
    
    # 案件操作
    CASE_VIEW = "case_view"
    CASE_CREATE = "case_create"
    CASE_UPDATE = "case_update"
    CASE_DELETE = "case_delete"
    
    # 收藏
    FAVORITE_ADD = "favorite_add"
    FAVORITE_REMOVE = "favorite_remove"
    
    # 搜索
    SEARCH = "search"
    SEARCH_HISTORY_CLEAR = "search_history_clear"
    
    # 分析
    ANALYSIS_SENTENCING = "analysis_sentencing"
    ANALYSIS_DEFENSE = "analysis_defense"
    ANALYSIS_COMPARISON = "analysis_comparison"
    
    # 导出
    EXPORT_PDF = "export_pdf"
    EXPORT_DATA = "export_data"
    
    # 系统
    SYSTEM_CONFIG = "system_config"
    BACKUP = "backup"
    RESTORE = "restore"
    
    # 安全
    SECURITY_ALERT = "security_alert"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    INVALID_ACCESS = "invalid_access"


class AuditLevel(Enum):
    """审计级别"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditLog:
    """审计日志条目"""
    log_id: str
    user_id: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    details: Dict
    ip_address: Optional[str]
    user_agent: Optional[str]
    level: str
    result: str  # success, failure
    timestamp: str


class AuditLogger:
    """审计日志记录器"""
    
    _sensitive_fields = {'password', 'password_hash', 'token', 'secret', 'api_key'}
    _exclude_actions = {AuditAction.LOGIN, AuditAction.LOGOUT}
    
    @classmethod
    def log(
        cls,
        action: AuditAction,
        user_id: str = None,
        resource_type: str = None,
        resource_id: str = None,
        details: Dict = None,
        ip_address: str = None,
        user_agent: str = None,
        level: AuditLevel = AuditLevel.INFO,
        result: str = "success",
    ) -> str:
        """记录审计日志"""
        import secrets
        
        # 清理敏感信息
        if details:
            details = cls._sanitize_details(details)
        
        log_id = f"audit_{secrets.token_hex(8)}"
        timestamp = datetime.now().isoformat()
        
        log_entry = AuditLog(
            log_id=log_id,
            user_id=user_id,
            action=action.value,
            resource_type=resource_type or "",
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            level=level.value,
            result=result,
            timestamp=timestamp,
        )
        
        # 保存到数据库
        try:
            db.log_operation(
                user_id=user_id,
                action=action.value,
                target=resource_id,
                details=log_entry.details,
                ip_address=ip_address,
            )
        except Exception as e:
            print(f"审计日志保存失败: {e}")
        
        return log_id
    
    @classmethod
    def _sanitize_details(cls, details: Dict) -> Dict:
        """清理敏感信息"""
        sanitized = {}
        for key, value in details.items():
            key_lower = key.lower()
            if any(field in key_lower for field in cls._sensitive_fields):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = cls._sanitize_details(value)
            else:
                sanitized[key] = value
        return sanitized
    
    @classmethod
    def log_login(cls, user_id: str, ip_address: str = None, success: bool = True):
        """记录登录"""
        cls.log(
            action=AuditAction.LOGIN,
            user_id=user_id if success else None,
            ip_address=ip_address,
            result="success" if success else "failure",
            level=AuditLevel.INFO if success else AuditLevel.WARNING,
        )
    
    @classmethod
    def log_logout(cls, user_id: str, ip_address: str = None):
        """记录登出"""
        cls.log(
            action=AuditAction.LOGOUT,
            user_id=user_id,
            ip_address=ip_address,
        )
    
    @classmethod
    def log_case_access(cls, user_id: str, case_id: str, action: str = "view", ip_address: str = None):
        """记录案件访问"""
        action_map = {
            "view": AuditAction.CASE_VIEW,
            "create": AuditAction.CASE_CREATE,
            "update": AuditAction.CASE_UPDATE,
            "delete": AuditAction.CASE_DELETE,
        }
        cls.log(
            action=action_map.get(action, AuditAction.CASE_VIEW),
            user_id=user_id,
            resource_type="case",
            resource_id=case_id,
            ip_address=ip_address,
        )
    
    @classmethod
    def log_search(cls, user_id: str, query: str, result_count: int, ip_address: str = None):
        """记录搜索"""
        cls.log(
            action=AuditAction.SEARCH,
            user_id=user_id,
            resource_type="search",
            details={"query": query, "results": result_count},
            ip_address=ip_address,
        )
    
    @classmethod
    def log_analysis(cls, user_id: str, analysis_type: str, case_id: str = None, ip_address: str = None):
        """记录分析操作"""
        action_map = {
            "sentencing": AuditAction.ANALYSIS_SENTENCING,
            "defense": AuditAction.ANALYSIS_DEFENSE,
            "comparison": AuditAction.ANALYSIS_COMPARISON,
        }
        cls.log(
            action=action_map.get(analysis_type, AuditAction.ANALYSIS_SENTENCING),
            user_id=user_id,
            resource_type="analysis",
            resource_id=case_id,
            ip_address=ip_address,
        )
    
    @classmethod
    def log_security_event(cls, event_type: str, details: Dict, ip_address: str = None, user_id: str = None):
        """记录安全事件"""
        cls.log(
            action=AuditAction.SECURITY_ALERT,
            user_id=user_id,
            resource_type="security",
            details={"event_type": event_type, **details},
            ip_address=ip_address,
            level=AuditLevel.WARNING,
        )
    
    @classmethod
    def log_rate_limit(cls, ip_address: str, endpoint: str):
        """记录限流事件"""
        cls.log(
            action=AuditAction.RATE_LIMIT_EXCEEDED,
            ip_address=ip_address,
            resource_type="api",
            resource_id=endpoint,
            level=AuditLevel.WARNING,
            result="blocked",
        )


class AuditReporter:
    """审计报告生成器"""
    
    @classmethod
    def get_user_activity_report(cls, user_id: str, days: int = 30) -> Dict:
        """获取用户活动报告"""
        logs = db.get_operation_logs(user_id, limit=1000)
        
        # 统计
        from collections import Counter
        actions = Counter([log.get('action', '') for log in logs])
        
        return {
            "user_id": user_id,
            "period_days": days,
            "total_actions": len(logs),
            "action_breakdown": dict(actions),
            "recent_logs": logs[:20],
        }
    
    @classmethod
    def get_security_report(cls, days: int = 7) -> Dict:
        """获取安全报告"""
        logs = db.get_operation_logs(limit=5000)
        
        # 筛选安全相关事件
        security_actions = {
            AuditAction.LOGIN.value,
            AuditAction.LOGOUT.value,
            AuditAction.SECURITY_ALERT.value,
            AuditAction.RATE_LIMIT_EXCEEDED.value,
            AuditAction.INVALID_ACCESS.value,
        }
        
        security_logs = [log for log in logs if log.get('action') in security_actions]
        
        # 统计失败登录
        failed_logins = [log for log in security_logs 
                        if log.get('action') == AuditAction.LOGIN.value 
                        and log.get('result') == 'failure']
        
        return {
            "period_days": days,
            "total_security_events": len(security_logs),
            "failed_logins": len(failed_logins),
            "rate_limit_exceeded": sum(1 for log in security_logs 
                                      if log.get('action') == AuditAction.RATE_LIMIT_EXCEEDED.value),
            "recent_alerts": security_logs[:10],
        }
    
    @classmethod
    def get_compliance_report(cls, start_date: str, end_date: str) -> Dict:
        """获取合规报告"""
        logs = db.get_operation_logs(limit=10000)
        
        # 按日期分组
        from collections import defaultdict
        by_date = defaultdict(list)
        for log in logs:
            date = log.get('created_at', '')[:10]
            by_date[date].append(log)
        
        return {
            "start_date": start_date,
            "end_date": end_date,
            "total_logs": len(logs),
            "logs_by_date": {k: len(v) for k, v in sorted(by_date.items())},
        }


# 全局实例
audit_logger = AuditLogger()
audit_reporter = AuditReporter()


if __name__ == "__main__":
    print("=== 审计日志模块 ===")
    print("✅ 模块已加载")
    print("\n使用方式:")
    print("  from audit import audit_logger, audit_reporter")
    print("  audit_logger.log_login(user_id, ip_address)")
    print("  audit_logger.log_case_access(user_id, case_id)")
    print("  audit_logger.log_security_event('suspicious_login', details)")
