# -*- coding: utf-8 -*-
"""
数据库模块 - database.py

使用SQLite作为持久化存储，支持：
- 用户数据
- 案件数据
- 搜索历史
- 收藏记录
- 操作日志

迁移自文件存储，提升性能和可靠性
"""

import sqlite3
import json
import hashlib
import secrets
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from contextlib import contextmanager
from functools import wraps
import threading


@dataclass
class User:
    """用户模型"""
    user_id: str
    username: str
    email: str
    password_hash: str
    role: str = "user"
    created_at: str = ""
    last_login: str = ""
    
    def to_dict(self, safe: bool = True) -> Dict:
        data = asdict(self)
        if safe:
            data.pop("password_hash", None)
        return data


class Database:
    """SQLite数据库管理器"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, db_path: str = "data/prosecution.db"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_path: str = "data/prosecution.db"):
        if self._initialized:
            return
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = None
        self._init_db()
        self._initialized = True
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_db(self):
        """初始化数据库表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 用户表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'user',
                    created_at TEXT NOT NULL,
                    last_login TEXT
                )
            """)
            
            # 收藏表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS favorites (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    UNIQUE(user_id, case_id)
                )
            """)
            
            # 搜索历史表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    query TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # 操作日志表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS operation_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    action TEXT NOT NULL,
                    target TEXT,
                    details TEXT,
                    ip_address TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            
            # 案件数据表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cases (
                    case_id TEXT PRIMARY KEY,
                    case_data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # 量刑分析缓存表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sentencing_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cache_key TEXT UNIQUE NOT NULL,
                    result TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
            """)
            
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_favorites_user ON favorites(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_user ON search_history(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_user ON operation_logs(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_created ON operation_logs(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_key ON sentencing_cache(cache_key)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_expires ON sentencing_cache(expires_at)")
    
    # ============ 用户管理 ============
    
    def create_user(self, username: str, email: str, password: str, role: str = "user") -> Optional[User]:
        """创建用户"""
        user_id = f"user_{secrets.token_hex(8)}"
        password_hash = self._hash_password(password)
        created_at = datetime.now().isoformat()
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (user_id, username, email, password_hash, role, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, username, email, password_hash, role, created_at))
                
                return User(
                    user_id=user_id,
                    username=username,
                    email=email,
                    password_hash=password_hash,
                    role=role,
                    created_at=created_at,
                )
        except sqlite3.IntegrityError:
            return None
    
    def authenticate(self, username: str, password: str) -> Optional[User]:
        """验证登录"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            
            if row and row["password_hash"] == self._hash_password(password):
                # 更新最后登录时间
                cursor.execute("UPDATE users SET last_login = ? WHERE user_id = ?",
                             (datetime.now().isoformat(), row["user_id"]))
                
                return User(
                    user_id=row["user_id"],
                    username=row["username"],
                    email=row["email"],
                    password_hash=row["password_hash"],
                    role=row["role"],
                    created_at=row["created_at"],
                    last_login=row["last_login"],
                )
        return None
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """通过ID获取用户"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            
            if row:
                return User(
                    user_id=row["user_id"],
                    username=row["username"],
                    email=row["email"],
                    password_hash=row["password_hash"],
                    role=row["role"],
                    created_at=row["created_at"],
                    last_login=row["last_login"],
                )
        return None
    
    def get_user_favorites(self, user_id: str) -> List[str]:
        """获取用户收藏"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT case_id FROM favorites 
                WHERE user_id = ? 
                ORDER BY created_at DESC
            """, (user_id,))
            return [row["case_id"] for row in cursor.fetchall()]
    
    def add_favorite(self, user_id: str, case_id: str) -> bool:
        """添加收藏"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO favorites (user_id, case_id, created_at)
                    VALUES (?, ?, ?)
                """, (user_id, case_id, datetime.now().isoformat()))
                return True
        except Exception:
            return False
    
    def remove_favorite(self, user_id: str, case_id: str) -> bool:
        """移除收藏"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM favorites WHERE user_id = ? AND case_id = ?
            """, (user_id, case_id))
            return True
    
    def get_user_history(self, user_id: str, limit: int = 50) -> List[str]:
        """获取搜索历史"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT query FROM search_history 
                WHERE user_id = ? 
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit))
            return [row["query"] for row in cursor.fetchall()]
    
    def add_search_history(self, user_id: str, query: str) -> bool:
        """添加搜索历史"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO search_history (user_id, query, created_at)
                VALUES (?, ?, ?)
            """, (user_id, query, datetime.now().isoformat()))
            
            # 只保留最近100条
            cursor.execute("""
                DELETE FROM search_history 
                WHERE user_id = ? AND id NOT IN (
                    SELECT id FROM search_history 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC 
                    LIMIT 100
                )
            """, (user_id, user_id))
            return True
    
    def clear_search_history(self, user_id: str) -> bool:
        """清除搜索历史"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM search_history WHERE user_id = ?", (user_id,))
            return True
    
    # ============ 案件缓存 ============
    
    def save_case(self, case_id: str, case_data: Dict) -> bool:
        """保存案件数据"""
        now = datetime.now().isoformat()
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO cases (case_id, case_data, created_at, updated_at)
                    VALUES (?, ?, COALESCE((SELECT created_at FROM cases WHERE case_id = ?), ?), ?)
                """, (case_id, json.dumps(case_data, ensure_ascii=False), case_id, now, now))
                return True
        except Exception:
            return False
    
    def get_case(self, case_id: str) -> Optional[Dict]:
        """获取案件数据"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT case_data FROM cases WHERE case_id = ?", (case_id,))
            row = cursor.fetchone()
            if row:
                return json.loads(row["case_data"])
        return None
    
    # ============ 缓存管理 ============
    
    def get_cached(self, cache_key: str) -> Optional[Dict]:
        """获取缓存"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT result FROM sentencing_cache 
                WHERE cache_key = ? AND expires_at > ?
            """, (cache_key, datetime.now().isoformat()))
            row = cursor.fetchone()
            if row:
                return json.loads(row["result"])
        return None
    
    def set_cache(self, cache_key: str, result: Dict, ttl_seconds: int = 3600) -> bool:
        """设置缓存"""
        now = datetime.now()
        expires_at = (now + timedelta(seconds=ttl_seconds)).isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO sentencing_cache (cache_key, result, created_at, expires_at)
                VALUES (?, ?, ?, ?)
            """, (cache_key, json.dumps(result, ensure_ascii=False), now.isoformat(), expires_at))
            return True
    
    def cleanup_expired_cache(self) -> int:
        """清理过期缓存"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM sentencing_cache WHERE expires_at < ?
            """, (datetime.now().isoformat(),))
            return cursor.rowcount
    
    # ============ 操作日志 ============
    
    def log_operation(self, user_id: str, action: str, target: str = None, 
                     details: Dict = None, ip_address: str = None) -> bool:
        """记录操作日志"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO operation_logs (user_id, action, target, details, ip_address, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, action, target, json.dumps(details) if details else None,
                  ip_address, datetime.now().isoformat()))
            return True
    
    def get_operation_logs(self, user_id: str = None, limit: int = 100) -> List[Dict]:
        """获取操作日志"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute("""
                    SELECT * FROM operation_logs 
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (user_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM operation_logs 
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    # ============ 统计 ============
    
    def get_stats(self) -> Dict:
        """获取统计数据"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # 用户数
            cursor.execute("SELECT COUNT(*) as count FROM users")
            stats["total_users"] = cursor.fetchone()["count"]
            
            # 收藏数
            cursor.execute("SELECT COUNT(*) as count FROM favorites")
            stats["total_favorites"] = cursor.fetchone()["count"]
            
            # 案件数
            cursor.execute("SELECT COUNT(*) as count FROM cases")
            stats["total_cases"] = cursor.fetchone()["count"]
            
            # 搜索历史数
            cursor.execute("SELECT COUNT(*) as count FROM search_history")
            stats["total_searches"] = cursor.fetchone()["count"]
            
            # 今日活跃用户
            today = datetime.now().date().isoformat()
            cursor.execute("""
                SELECT COUNT(DISTINCT user_id) as count FROM operation_logs 
                WHERE created_at LIKE ?
            """, (f"{today}%",))
            stats["today_active_users"] = cursor.fetchone()["count"]
            
            return stats
    
    @staticmethod
    def _hash_password(password: str) -> str:
        """密码哈希"""
        salt = "prosecution_system_v2"
        return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


# 全局数据库实例
db = Database()


def init_database(db_path: str = "data/prosecution.db") -> Database:
    """初始化数据库"""
    return Database(db_path)


if __name__ == "__main__":
    print("=== 数据库初始化测试 ===\n")
    
    # 初始化
    database = Database("/tmp/test_prosecution.db")
    print("✅ 数据库初始化成功")
    
    # 创建测试用户
    user = database.create_user("testuser", "test@example.com", "password123", "user")
    if user:
        print(f"✅ 用户创建成功: {user.username}")
    
    # 登录测试
    user = database.authenticate("testuser", "password123")
    if user:
        print(f"✅ 登录成功: {user.username}")
    
    # 收藏测试
    database.add_favorite(user.user_id, "CASE-001")
    database.add_favorite(user.user_id, "CASE-002")
    favorites = database.get_user_favorites(user.user_id)
    print(f"📌 收藏: {favorites}")
    
    # 搜索历史测试
    database.add_search_history(user.user_id, "正当防卫")
    database.add_search_history(user.user_id, "盗窃罪")
    history = database.get_user_history(user.user_id)
    print(f"🔍 搜索历史: {history}")
    
    # 缓存测试
    database.set_cache("test_key", {"data": "test"}, ttl_seconds=60)
    cached = database.get_cached("test_key")
    print(f"💾 缓存: {cached}")
    
    # 统计
    stats = database.get_stats()
    print(f"📊 统计: {stats}")
    
    # 清理过期缓存
    deleted = database.cleanup_expired_cache()
    print(f"🧹 清理过期缓存: {deleted}条")
    
    print("\n✅ 数据库测试完成！")
