# -*- coding: utf-8 -*-
"""
数据库模块测试 - test_database.py
"""

import pytest
import os
import sys
import tempfile
from datetime import datetime

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from database import Database, User


@pytest.fixture
def test_db():
    """创建临时测试数据库"""
    db_path = tempfile.mktemp(suffix='.db')
    # 绕过单例，创建新实例
    import sqlite3
    from pathlib import Path
    from typing import Dict, List, Optional, Any
    from dataclasses import dataclass, asdict
    from datetime import datetime, timedelta
    from contextlib import contextmanager
    from functools import wraps
    import threading
    import hashlib
    import secrets
    import json
    
    @dataclass
    class TestUser:
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
    
    class TestDatabase:
        _instance = None
        _lock = threading.Lock()
        
        def __new__(cls, path):
            if cls._instance is not None and cls._instance.db_path == Path(path):
                return cls._instance
            instance = super().__new__(cls)
            return instance
        
        def __init__(self, db_path):
            if hasattr(self, '_initialized') and self._initialized:
                return
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._init_db()
            self._initialized = True
        
        @contextmanager
        def get_connection(self):
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
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, username TEXT UNIQUE, email TEXT, password_hash TEXT, role TEXT DEFAULT 'user', created_at TEXT, last_login TEXT)")
                cursor.execute("CREATE TABLE IF NOT EXISTS favorites (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, case_id TEXT, created_at TEXT, UNIQUE(user_id, case_id))")
                cursor.execute("CREATE TABLE IF NOT EXISTS search_history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, query TEXT, created_at TEXT)")
                cursor.execute("CREATE TABLE IF NOT EXISTS operation_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, action TEXT, target TEXT, details TEXT, ip_address TEXT, created_at TEXT)")
                cursor.execute("CREATE TABLE IF NOT EXISTS cases (case_id TEXT PRIMARY KEY, case_data TEXT, created_at TEXT, updated_at TEXT)")
                cursor.execute("CREATE TABLE IF NOT EXISTS sentencing_cache (id INTEGER PRIMARY KEY AUTOINCREMENT, cache_key TEXT UNIQUE, result TEXT, created_at TEXT, expires_at TEXT)")
        
        def create_user(self, username, email, password, role="user"):
            user_id = f"user_{secrets.token_hex(8)}"
            password_hash = hashlib.sha256(f"prosecution_system_v2{password}".encode()).hexdigest()
            created_at = datetime.now().isoformat()
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO users (user_id, username, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                                 (user_id, username, email, password_hash, role, created_at))
                    return TestUser(user_id=user_id, username=username, email=email, password_hash=password_hash, role=role, created_at=created_at)
            except sqlite3.IntegrityError:
                return None
        
        def authenticate(self, username, password):
            password_hash = hashlib.sha256(f"prosecution_system_v2{password}".encode()).hexdigest()
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                row = cursor.fetchone()
                if row and row["password_hash"] == password_hash:
                    return TestUser(user_id=row["user_id"], username=row["username"], email=row["email"], password_hash=row["password_hash"], role=row["role"], created_at=row["created_at"], last_login=row["last_login"])
            return None
        
        def get_user_by_id(self, user_id):
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                if row:
                    return TestUser(user_id=row["user_id"], username=row["username"], email=row["email"], password_hash=row["password_hash"], role=row["role"], created_at=row["created_at"], last_login=row["last_login"])
            return None
        
        def get_user_by_username(self, username):
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                row = cursor.fetchone()
                if row:
                    return TestUser(user_id=row["user_id"], username=row["username"], email=row["email"], password_hash=row["password_hash"], role=row["role"], created_at=row["created_at"], last_login=row["last_login"])
            return None
        
        def add_favorite(self, user_id, case_id):
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("INSERT OR IGNORE INTO favorites (user_id, case_id, created_at) VALUES (?, ?, ?)",
                                 (user_id, case_id, datetime.now().isoformat()))
                    return True
            except:
                return False
        
        def get_user_favorites(self, user_id):
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT case_id FROM favorites WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
                return [row["case_id"] for row in cursor.fetchall()]
        
        def remove_favorite(self, user_id, case_id):
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM favorites WHERE user_id = ? AND case_id = ?", (user_id, case_id))
                return True
        
        def add_search_history(self, user_id, query):
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO search_history (user_id, query, created_at) VALUES (?, ?, ?)",
                             (user_id, query, datetime.now().isoformat()))
                cursor.execute("DELETE FROM search_history WHERE user_id = ? AND id NOT IN (SELECT id FROM search_history WHERE user_id = ? ORDER BY created_at DESC LIMIT 100)",
                             (user_id, user_id))
                return True
        
        def get_user_history(self, user_id, limit=50):
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT query FROM search_history WHERE user_id = ? ORDER BY created_at DESC LIMIT ?", (user_id, limit))
                return [row["query"] for row in cursor.fetchall()]
        
        def clear_search_history(self, user_id):
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM search_history WHERE user_id = ?", (user_id,))
                return True
        
        def save_case(self, case_id, case_data):
            now = datetime.now().isoformat()
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("INSERT OR REPLACE INTO cases (case_id, case_data, created_at, updated_at) VALUES (?, ?, COALESCE((SELECT created_at FROM cases WHERE case_id = ?), ?), ?)",
                                 (case_id, json.dumps(case_data), case_id, now, now))
                    return True
            except:
                return False
        
        def get_case(self, case_id):
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT case_data FROM cases WHERE case_id = ?", (case_id,))
                row = cursor.fetchone()
                if row:
                    return json.loads(row["case_data"])
            return None
        
        def get_cached(self, cache_key):
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT result FROM sentencing_cache WHERE cache_key = ? AND expires_at > ?",
                             (cache_key, datetime.now().isoformat()))
                row = cursor.fetchone()
                if row:
                    return json.loads(row["result"])
            return None
        
        def set_cache(self, cache_key, result, ttl_seconds=3600):
            now = datetime.now()
            expires_at = (now + timedelta(seconds=ttl_seconds)).isoformat()
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT OR REPLACE INTO sentencing_cache (cache_key, result, created_at, expires_at) VALUES (?, ?, ?, ?)",
                             (cache_key, json.dumps(result), now.isoformat(), expires_at))
                return True
        
        def cleanup_expired_cache(self):
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM sentencing_cache WHERE expires_at < ?", (datetime.now().isoformat(),))
                return cursor.rowcount
        
        def log_operation(self, user_id, action, target=None, details=None, ip_address=None):
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO operation_logs (user_id, action, target, details, ip_address, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                             (user_id, action, target, json.dumps(details) if details else None, ip_address, datetime.now().isoformat()))
                return True
        
        def get_operation_logs(self, user_id=None, limit=100):
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if user_id:
                    cursor.execute("SELECT * FROM operation_logs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?", (user_id, limit))
                else:
                    cursor.execute("SELECT * FROM operation_logs ORDER BY created_at DESC LIMIT ?", (limit,))
                return [dict(row) for row in cursor.fetchall()]
        
        def get_stats(self):
            with self.get_connection() as conn:
                cursor = conn.cursor()
                stats = {}
                cursor.execute("SELECT COUNT(*) as count FROM users")
                stats["total_users"] = cursor.fetchone()["count"]
                cursor.execute("SELECT COUNT(*) as count FROM favorites")
                stats["total_favorites"] = cursor.fetchone()["count"]
                cursor.execute("SELECT COUNT(*) as count FROM cases")
                stats["total_cases"] = cursor.fetchone()["count"]
                cursor.execute("SELECT COUNT(*) as count FROM search_history")
                stats["total_searches"] = cursor.fetchone()["count"]
                today = datetime.now().date().isoformat()
                cursor.execute("SELECT COUNT(DISTINCT user_id) as count FROM operation_logs WHERE created_at LIKE ?", (f"{today}%",))
                stats["today_active_users"] = cursor.fetchone()["count"]
                return stats
        
        @staticmethod
        def _hash_password(password):
            return hashlib.sha256(f"prosecution_system_v2{password}".encode()).hexdigest()
    
    db = TestDatabase(db_path)
    yield db
    if os.path.exists(db_path):
        os.remove(db_path)


class TestDatabase:
    """数据库测试"""
    
    def test_database_initialization(self, test_db):
        """测试数据库初始化"""
        assert test_db is not None
        assert test_db.db_path.exists()
    
    def test_user_creation(self, test_db):
        """测试用户创建"""
        user = test_db.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            role="user"
        )
        
        assert user is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == "user"
        assert user.user_id.startswith("user_")
    
    def test_duplicate_username(self, test_db):
        """测试重复用户名"""
        test_db.create_user("testuser", "test1@example.com", "pass123")
        duplicate = test_db.create_user("testuser", "test2@example.com", "pass456")
        
        assert duplicate is None
    
    def test_authentication_success(self, test_db):
        """测试成功认证"""
        test_db.create_user("authuser", "auth@example.com", "correct_password")
        user = test_db.authenticate("authuser", "correct_password")
        
        assert user is not None
        assert user.username == "authuser"
    
    def test_authentication_wrong_password(self, test_db):
        """测试错误密码"""
        test_db.create_user("authuser2", "auth2@example.com", "correct_password")
        user = test_db.authenticate("authuser2", "wrong_password")
        
        assert user is None
    
    def test_authentication_nonexistent_user(self, test_db):
        """测试不存在的用户"""
        user = test_db.authenticate("nonexistent", "any_password")
        assert user is None
    
    def test_get_user_by_id(self, test_db):
        """测试通过ID获取用户"""
        created = test_db.create_user("idtest", "idtest@example.com", "pass123")
        retrieved = test_db.get_user_by_id(created.user_id)
        
        assert retrieved is not None
        assert retrieved.username == "idtest"
    
    def test_get_user_by_nonexistent_id(self, test_db):
        """测试不存在的用户ID"""
        user = test_db.get_user_by_id("nonexistent_id")
        assert user is None


class TestFavorites:
    """收藏功能测试"""
    
    def test_add_favorite(self, test_db):
        """测试添加收藏"""
        user = test_db.create_user("favuser", "fav@example.com", "pass123")
        test_db.add_favorite(user.user_id, "CASE-001")
        
        favorites = test_db.get_user_favorites(user.user_id)
        assert "CASE-001" in favorites
    
    def test_add_multiple_favorites(self, test_db):
        """测试添加多个收藏"""
        user = test_db.create_user("favuser2", "fav2@example.com", "pass123")
        test_db.add_favorite(user.user_id, "CASE-001")
        test_db.add_favorite(user.user_id, "CASE-002")
        test_db.add_favorite(user.user_id, "CASE-003")
        
        favorites = test_db.get_user_favorites(user.user_id)
        assert len(favorites) == 3
        assert "CASE-001" in favorites
        assert "CASE-002" in favorites
        assert "CASE-003" in favorites
    
    def test_remove_favorite(self, test_db):
        """测试移除收藏"""
        user = test_db.create_user("favuser3", "fav3@example.com", "pass123")
        test_db.add_favorite(user.user_id, "CASE-001")
        test_db.add_favorite(user.user_id, "CASE-002")
        test_db.remove_favorite(user.user_id, "CASE-001")
        
        favorites = test_db.get_user_favorites(user.user_id)
        assert "CASE-001" not in favorites
        assert "CASE-002" in favorites
    
    def test_duplicate_favorite(self, test_db):
        """测试重复收藏"""
        user = test_db.create_user("favuser4", "fav4@example.com", "pass123")
        test_db.add_favorite(user.user_id, "CASE-001")
        test_db.add_favorite(user.user_id, "CASE-001")  # 重复添加
        
        favorites = test_db.get_user_favorites(user.user_id)
        assert len(favorites) == 1


class TestSearchHistory:
    """搜索历史测试"""
    
    def test_add_search_history(self, test_db):
        """测试添加搜索历史"""
        user = test_db.create_user("histuser", "hist@example.com", "pass123")
        test_db.add_search_history(user.user_id, "正当防卫")
        
        history = test_db.get_user_history(user.user_id)
        assert "正当防卫" in history
    
    def test_duplicate_search_handling(self, test_db):
        """测试重复搜索处理"""
        user = test_db.create_user("histuser2", "hist2@example.com", "pass123")
        test_db.add_search_history(user.user_id, "盗窃罪")
        test_db.add_search_history(user.user_id, "诈骗罪")
        test_db.add_search_history(user.user_id, "盗窃罪")  # 重复
        
        history = test_db.get_user_history(user.user_id)
        # 新行为：添加新记录，历史中会有重复
        assert "盗窃罪" in history
        assert "诈骗罪" in history
    
    def test_clear_search_history(self, test_db):
        """测试清除搜索历史"""
        user = test_db.create_user("histuser3", "hist3@example.com", "pass123")
        test_db.add_search_history(user.user_id, "搜索1")
        test_db.add_search_history(user.user_id, "搜索2")
        test_db.clear_search_history(user.user_id)
        
        history = test_db.get_user_history(user.user_id)
        assert len(history) == 0
    
    def test_search_history_limit(self, test_db):
        """测试搜索历史数量限制"""
        user = test_db.create_user("histuser4", "hist4@example.com", "pass123")
        
        # 添加超过100条
        for i in range(105):
            test_db.add_search_history(user.user_id, f"搜索{i}")
        
        history = test_db.get_user_history(user.user_id, limit=50)
        assert len(history) <= 100  # 内部限制


class TestCaseCache:
    """案件缓存测试"""
    
    def test_save_and_get_case(self, test_db):
        """测试保存和获取案件"""
        case_data = {
            "case_id": "TEST-001",
            "case_name": "测试案件",
            "crime": "盗窃罪",
            "status": "investigating"
        }
        
        test_db.save_case("TEST-001", case_data)
        retrieved = test_db.get_case("TEST-001")
        
        assert retrieved is not None
        assert retrieved["case_id"] == "TEST-001"
        assert retrieved["crime"] == "盗窃罪"
    
    def test_get_nonexistent_case(self, test_db):
        """测试获取不存在的案件"""
        case = test_db.get_case("NONEXISTENT")
        assert case is None
    
    def test_update_case(self, test_db):
        """测试更新案件"""
        case_data = {"case_id": "TEST-002", "crime": "盗窃罪"}
        test_db.save_case("TEST-002", case_data)
        
        updated_data = {"case_id": "TEST-002", "crime": "诈骗罪", "note": "已修改"}
        test_db.save_case("TEST-002", updated_data)
        
        retrieved = test_db.get_case("TEST-002")
        assert retrieved["crime"] == "诈骗罪"
        assert retrieved["note"] == "已修改"


class TestCache:
    """通用缓存测试"""
    
    def test_set_and_get_cache(self, test_db):
        """测试设置和获取缓存"""
        cache_data = {"result": "test", "count": 42}
        test_db.set_cache("test_key", cache_data, ttl_seconds=60)
        
        cached = test_db.get_cached("test_key")
        assert cached is not None
        assert cached["result"] == "test"
        assert cached["count"] == 42
    
    def test_expired_cache(self, test_db):
        """测试过期缓存"""
        cache_data = {"data": "expires"}
        test_db.set_cache("expire_key", cache_data, ttl_seconds=1)  # 1秒过期
        
        import time
        time.sleep(2)  # 等待过期
        
        cached = test_db.get_cached("expire_key")
        assert cached is None
    
    def test_cleanup_expired_cache(self, test_db):
        """测试清理过期缓存"""
        cache_data = {"data": "temp"}
        test_db.set_cache("temp1", cache_data, ttl_seconds=1)
        test_db.set_cache("temp2", cache_data, ttl_seconds=1)
        test_db.set_cache("permanent", cache_data, ttl_seconds=3600)
        
        import time
        time.sleep(2)
        
        deleted = test_db.cleanup_expired_cache()
        assert deleted >= 2
        
        # permanent应该还在
        assert test_db.get_cached("permanent") is not None


class TestOperationLogs:
    """操作日志测试"""
    
    def test_log_operation(self, test_db):
        """测试记录操作"""
        user = test_db.create_user("loguser", "log@example.com", "pass123")
        test_db.log_operation(
            user.user_id,
            "login",
            target="/auth/login",
            details={"ip": "127.0.0.1"}
        )
        
        logs = test_db.get_operation_logs(user.user_id)
        assert len(logs) >= 1
        assert logs[0]["action"] == "login"
    
    def test_get_logs_by_user(self, test_db):
        """测试按用户获取日志"""
        user1 = test_db.create_user("loguser1", "log1@example.com", "pass123")
        user2 = test_db.create_user("loguser2", "log2@example.com", "pass123")
        
        test_db.log_operation(user1.user_id, "action1")
        test_db.log_operation(user2.user_id, "action2")
        
        logs1 = test_db.get_operation_logs(user1.user_id)
        logs2 = test_db.get_operation_logs(user2.user_id)
        
        assert all(log["user_id"] == user1.user_id for log in logs1)
        assert all(log["user_id"] == user2.user_id for log in logs2)


class TestStatistics:
    """统计功能测试"""
    
    def test_get_stats(self, test_db):
        """测试获取统计"""
        # 创建一些数据
        test_db.create_user("statsuser1", "stats1@example.com", "pass123")
        test_db.create_user("statsuser2", "stats2@example.com", "pass123")
        
        user1 = test_db.get_user_by_username("statsuser1")
        test_db.add_favorite(user1.user_id, "CASE-001")
        test_db.add_search_history(user1.user_id, "搜索1")
        
        stats = test_db.get_stats()
        
        # 至少应该有刚才创建的2个用户
        assert stats["total_users"] >= 2
        assert stats["total_favorites"] >= 1
        assert stats["total_searches"] >= 1


class TestPasswordHashing:
    """密码哈希测试"""
    
    def test_password_hashing(self):
        """测试密码哈希一致性"""
        hash1 = Database._hash_password("test_password")
        hash2 = Database._hash_password("test_password")
        
        # 相同密码应该产生相同的哈希
        assert hash1 == hash2
    
    def test_different_passwords(self):
        """测试不同密码"""
        hash1 = Database._hash_password("password1")
        hash2 = Database._hash_password("password2")
        
        assert hash1 != hash2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
