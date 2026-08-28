# -*- coding: utf-8 -*-
"""
用户认证模块 - auth.py

功能：
- 用户注册/登录/登出
- Session管理
- 密码加密存储
- 用户收藏管理
"""

import hashlib
import secrets
import json
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict
from datetime import datetime
from functools import wraps
from flask import session, request, jsonify, redirect, url_for, flash


@dataclass
class User:
    """用户模型"""
    user_id: str
    username: str
    email: str
    password_hash: str
    role: str = "user"  # user, admin, prosecutor, lawyer
    created_at: str = ""
    last_login: str = ""
    favorites: List[str] = None  # 收藏的案件ID列表
    search_history: List[str] = None  # 搜索历史
    
    def __post_init__(self):
        if self.favorites is None:
            self.favorites = []
        if self.search_history is None:
            self.search_history = []
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self, safe: bool = True) -> Dict:
        """转换为字典，safe=True时隐藏敏感信息"""
        data = asdict(self)
        if safe:
            data.pop("password_hash", None)
        return data


class UserDatabase:
    """用户数据库（基于文件，简单实现）"""
    
    def __init__(self, db_path: str = "users.json"):
        self.db_path = Path(db_path)
        self.users: Dict[str, User] = {}
        self._load()
    
    def _load(self):
        """加载用户数据"""
        if self.db_path.exists():
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for user_data in data.get("users", []):
                        user = User(**user_data)
                        self.users[user.username] = user
            except Exception as e:
                print(f"加载用户数据库失败: {e}")
    
    def _save(self):
        """保存用户数据"""
        data = {
            "users": [user.to_dict(safe=False) for user in self.users.values()]
        }
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def create_user(self, username: str, email: str, password: str, role: str = "user") -> Optional[User]:
        """创建新用户"""
        if username in self.users:
            return None  # 用户名已存在
        
        password_hash = self._hash_password(password)
        user = User(
            user_id=f"user_{secrets.token_hex(8)}",
            username=username,
            email=email,
            password_hash=password_hash,
            role=role,
        )
        self.users[username] = user
        self._save()
        return user
    
    def authenticate(self, username: str, password: str) -> Optional[User]:
        """验证用户登录"""
        user = self.users.get(username)
        if not user:
            return None
        
        password_hash = self._hash_password(password)
        if user.password_hash == password_hash:
            user.last_login = datetime.now().isoformat()
            self._save()
            return user
        return None
    
    def get_user(self, username: str) -> Optional[User]:
        """获取用户"""
        return self.users.get(username)
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """通过ID获取用户"""
        for user in self.users.values():
            if user.user_id == user_id:
                return user
        return None
    
    def update_user(self, username: str, updates: Dict) -> bool:
        """更新用户信息"""
        user = self.users.get(username)
        if not user:
            return False
        
        for key, value in updates.items():
            if hasattr(user, key) and key not in ["user_id", "password_hash"]:
                setattr(user, key, value)
        
        self._save()
        return True
    
    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """修改密码"""
        user = self.users.get(username)
        if not user:
            return False
        
        old_hash = self._hash_password(old_password)
        if user.password_hash != old_hash:
            return False
        
        user.password_hash = self._hash_password(new_password)
        self._save()
        return True
    
    def add_favorite(self, username: str, case_id: str) -> bool:
        """添加收藏"""
        user = self.users.get(username)
        if not user:
            return False
        
        if case_id not in user.favorites:
            user.favorites.append(case_id)
            self._save()
        return True
    
    def remove_favorite(self, username: str, case_id: str) -> bool:
        """移除收藏"""
        user = self.users.get(username)
        if not user:
            return False
        
        if case_id in user.favorites:
            user.favorites.remove(case_id)
            self._save()
        return True
    
    def add_search_history(self, username: str, query: str) -> bool:
        """添加搜索历史"""
        user = self.users.get(username)
        if not user:
            return False
        
        # 避免重复，移到最前面
        if query in user.search_history:
            user.search_history.remove(query)
        user.search_history.insert(0, query)
        
        # 最多保留50条
        user.search_history = user.search_history[:50]
        self._save()
        return True
    
    def _hash_password(self, password: str) -> str:
        """密码哈希（简单实现，生产环境建议使用bcrypt）"""
        salt = "prosecution_system_salt_v1"
        return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


# 全局用户数据库实例
user_db = UserDatabase()


def login_required(f):
    """登录_required装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            if request.is_json:
                return jsonify({"error": "请先登录", "code": "unauthorized"}), 401
            return redirect(url_for("auth.login_page"))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """管理员_required装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            if request.is_json:
                return jsonify({"error": "请先登录", "code": "unauthorized"}), 401
            return redirect(url_for("auth.login_page"))
        
        user = user_db.get_user_by_id(session["user_id"])
        if not user or user.role != "admin":
            if request.is_json:
                return jsonify({"error": "需要管理员权限", "code": "forbidden"}), 403
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated_function


def get_current_user() -> Optional[User]:
    """获取当前登录用户"""
    if "user_id" in session:
        return user_db.get_user_by_id(session["user_id"])
    return None


# Flask Blueprint
def create_auth_blueprint(app):
    """创建认证蓝图"""
    from flask import Blueprint
    bp = Blueprint("auth", __name__, url_prefix="/auth")
    
    @bp.route("/login", methods=["GET", "POST"])
    def login():
        """登录页面/接口"""
        if request.method == "GET":
            return _render_login_page()
        
        # POST 处理
        data = request.get_json() if request.is_json else request.form
        username = data.get("username", "")
        password = data.get("password", "")
        
        if not username or not password:
            if request.is_json:
                return jsonify({"error": "请输入用户名和密码"}), 400
            flash("请输入用户名和密码")
            return redirect(url_for("auth.login"))
        
        user = user_db.authenticate(username, password)
        if user:
            session["user_id"] = user.user_id
            session["username"] = user.username
            session["role"] = user.role
            
            if request.is_json:
                return jsonify({
                    "success": True,
                    "user": user.to_dict(),
                    "message": "登录成功"
                })
            
            next_url = request.args.get("next", "/")
            return redirect(next_url)
        else:
            if request.is_json:
                return jsonify({"error": "用户名或密码错误"}), 401
            flash("用户名或密码错误")
            return redirect(url_for("auth.login"))
    
    @bp.route("/register", methods=["GET", "POST"])
    def register():
        """注册页面/接口"""
        if request.method == "GET":
            return _render_register_page()
        
        # POST 处理
        data = request.get_json() if request.is_json else request.form
        username = data.get("username", "")
        email = data.get("email", "")
        password = data.get("password", "")
        role = data.get("role", "user")
        
        # 验证
        if not username or not email or not password:
            if request.is_json:
                return jsonify({"error": "请填写所有必填项"}), 400
        
        if len(password) < 6:
            if request.is_json:
                return jsonify({"error": "密码至少6位"}), 400
            flash("密码至少6位")
            return redirect(url_for("auth.register"))
        
        user = user_db.create_user(username, email, password, role)
        if user:
            session["user_id"] = user.user_id
            session["username"] = user.username
            session["role"] = user.role
            
            if request.is_json:
                return jsonify({
                    "success": True,
                    "user": user.to_dict(),
                    "message": "注册成功"
                }), 201
            
            flash("注册成功！")
            return redirect(url_for("index"))
        else:
            if request.is_json:
                return jsonify({"error": "用户名已存在"}), 409
            flash("用户名已存在")
            return redirect(url_for("auth.register"))
    
    @bp.route("/logout")
    def logout():
        """登出"""
        session.clear()
        if request.is_json:
            return jsonify({"success": True, "message": "已退出登录"})
        return redirect(url_for("auth.login"))
    
    @bp.route("/profile")
    @login_required
    def profile():
        """用户资料页面/接口"""
        user = get_current_user()
        if request.is_json:
            return jsonify({
                "user": user.to_dict(),
                "favorites_count": len(user.favorites),
                "search_history_count": len(user.search_history),
            })
        return _render_profile_page(user)
    
    @bp.route("/favorites", methods=["GET", "POST", "DELETE"])
    @login_required
    def favorites():
        """收藏管理"""
        user = get_current_user()
        
        if request.method == "GET":
            if request.is_json:
                return jsonify({"favorites": user.favorites})
            return _render_favorites_page(user)
        
        elif request.method == "POST":
            data = request.get_json()
            case_id = data.get("case_id", "")
            if case_id:
                user_db.add_favorite(user.username, case_id)
                return jsonify({"success": True, "favorites": user.favorites})
            return jsonify({"error": "缺少case_id"}), 400
        
        elif request.method == "DELETE":
            data = request.get_json()
            case_id = data.get("case_id", "")
            if case_id:
                user_db.remove_favorite(user.username, case_id)
                return jsonify({"success": True, "favorites": user.favorites})
            return jsonify({"error": "缺少case_id"}), 400
    
    @bp.route("/search-history", methods=["GET", "DELETE"])
    @login_required
    def search_history():
        """搜索历史"""
        user = get_current_user()
        
        if request.method == "GET":
            return jsonify({"history": user.search_history})
        
        elif request.method == "DELETE":
            user.search_history = []
            user_db._save()
            return jsonify({"success": True})
    
    return bp


def _render_login_page() -> str:
    return """
<!DOCTYPE html>
<html>
<head>
    <title>登录 - 刑事追诉辅助系统</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
               min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .login-box { background: white; padding: 40px; border-radius: 12px; 
                     box-shadow: 0 10px 40px rgba(0,0,0,0.3); width: 360px; }
        h1 { text-align: center; color: #1a1a2e; margin-bottom: 30px; font-size: 24px; }
        input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; 
                border-radius: 6px; box-sizing: border-box; font-size: 14px; }
        button { width: 100%; padding: 14px; background: #1a1a2e; color: white; 
                 border: none; border-radius: 6px; font-size: 16px; cursor: pointer; margin-top: 10px; }
        button:hover { background: #16213e; }
        .links { text-align: center; margin-top: 20px; }
        .links a { color: #1a1a2e; text-decoration: none; }
        .error { color: #e74c3c; text-align: center; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="login-box">
        <h1>⚖️ 刑事追诉辅助系统</h1>
        {% with messages = get_flashed_messages() %}
        {% if messages %}
        <div class="error">{{ messages[0] }}</div>
        {% endif %}
        {% endwith %}
        <form method="POST">
            <input type="text" name="username" placeholder="用户名" required>
            <input type="password" name="password" placeholder="密码" required>
            <button type="submit">登 录</button>
        </form>
        <div class="links">
            <a href="/auth/register">没有账号？立即注册</a><br>
            <a href="/">返回首页</a>
        </div>
    </div>
</body>
</html>
"""


def _render_register_page() -> str:
    return """
<!DOCTYPE html>
<html>
<head>
    <title>注册 - 刑事追诉辅助系统</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
               min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .register-box { background: white; padding: 40px; border-radius: 12px; 
                        box-shadow: 0 10px 40px rgba(0,0,0,0.3); width: 360px; }
        h1 { text-align: center; color: #1a1a2e; margin-bottom: 30px; font-size: 24px; }
        input, select { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; 
                        border-radius: 6px; box-sizing: border-box; font-size: 14px; }
        button { width: 100%; padding: 14px; background: #27ae60; color: white; 
                 border: none; border-radius: 6px; font-size: 16px; cursor: pointer; margin-top: 10px; }
        button:hover { background: #219a52; }
        .links { text-align: center; margin-top: 20px; }
        .links a { color: #1a1a2e; text-decoration: none; }
    </style>
</head>
<body>
    <div class="register-box">
        <h1>📝 用户注册</h1>
        <form method="POST">
            <input type="text" name="username" placeholder="用户名" required>
            <input type="email" name="email" placeholder="邮箱" required>
            <input type="password" name="password" placeholder="密码（至少6位）" required minlength="6">
            <select name="role">
                <option value="user">普通用户</option>
                <option value="lawyer">律师</option>
                <option value="prosecutor">检察官</option>
            </select>
            <button type="submit">注 册</button>
        </form>
        <div class="links">
            <a href="/auth/login">已有账号？立即登录</a><br>
            <a href="/">返回首页</a>
        </div>
    </div>
</body>
</html>
"""


def _render_profile_page(user: User) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>个人中心</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; 
               background: #f5f5f5; min-height: 100vh; }}
        .container {{ max-width: 800px; margin: 40px auto; padding: 20px; }}
        .card {{ background: white; border-radius: 12px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #1a1a2e; margin-bottom: 20px; }}
        .info {{ margin: 15px 0; }}
        .info-label {{ color: #666; font-size: 14px; }}
        .info-value {{ color: #1a1a2e; font-size: 16px; margin-top: 5px; }}
        .stats {{ display: flex; gap: 20px; margin-top: 20px; }}
        .stat {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; flex: 1; }}
        .stat-value {{ font-size: 32px; font-weight: bold; color: #1a1a2e; }}
        .stat-label {{ color: #666; font-size: 14px; margin-top: 5px; }}
        .btn {{ display: inline-block; padding: 10px 20px; background: #1a1a2e; color: white; 
                text-decoration: none; border-radius: 6px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>👤 个人中心</h1>
            <div class="info">
                <div class="info-label">用户名</div>
                <div class="info-value">{user.username}</div>
            </div>
            <div class="info">
                <div class="info-label">邮箱</div>
                <div class="info-value">{user.email}</div>
            </div>
            <div class="info">
                <div class="info-label">角色</div>
                <div class="info-value">{user.role}</div>
            </div>
            <div class="info">
                <div class="info-label">注册时间</div>
                <div class="info-value">{user.created_at[:10]}</div>
            </div>
            <div class="stats">
                <div class="stat">
                    <div class="stat-value">{len(user.favorites)}</div>
                    <div class="stat-label">收藏案件</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{len(user.search_history)}</div>
                    <div class="stat-label">搜索记录</div>
                </div>
            </div>
            <a href="/auth/logout" class="btn">退出登录</a>
            <a href="/" class="btn" style="background: #666;">返回首页</a>
        </div>
    </div>
</body>
</html>
"""


def _render_favorites_page(user: User) -> str:
    favorites_html = ""
    if user.favorites:
        for case_id in user.favorites:
            favorites_html += f'<li><a href="/case/{case_id}">{case_id}</a></li>'
    else:
        favorites_html = "<li>暂无收藏</li>"
    
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>我的收藏</title>
    <style>
        body {{ font-family: -apple-system, sans-serif; background: #f5f5f5; }}
        .container {{ max-width: 800px; margin: 40px auto; padding: 20px; }}
        .card {{ background: white; border-radius: 12px; padding: 30px; }}
        ul {{ list-style: none; padding: 0; }}
        li {{ padding: 15px; border-bottom: 1px solid #eee; }}
        li:last-child {{ border-bottom: none; }}
        a {{ color: #1a1a2e; text-decoration: none; }}
        a:hover {{ color: #3498db; }}
        .btn {{ display: inline-block; padding: 8px 16px; background: #e74c3c; color: white; 
                text-decoration: none; border-radius: 4px; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>⭐ 我的收藏</h1>
            <ul>{favorites_html}</ul>
            <a href="/auth/profile">返回个人中心</a>
        </div>
    </div>
</body>
</html>
"""


if __name__ == "__main__":
    # 测试用户数据库
    print("=== 用户系统测试 ===\n")
    
    # 创建测试用户
    user = user_db.create_user("testuser", "test@example.com", "password123")
    if user:
        print(f"✅ 用户创建成功: {user.username}")
    else:
        print("⚠️ 用户已存在")
    
    # 登录测试
    user = user_db.authenticate("testuser", "password123")
    if user:
        print(f"✅ 登录成功: {user.username} ({user.role})")
    else:
        print("❌ 登录失败")
    
    # 收藏测试
    user_db.add_favorite("testuser", "CASE-001")
    user_db.add_favorite("testuser", "CASE-002")
    user = user_db.get_user("testuser")
    print(f"📌 收藏列表: {user.favorites}")
    
    # 搜索历史测试
    user_db.add_search_history("testuser", "正当防卫")
    user_db.add_search_history("testuser", "盗窃罪")
    user = user_db.get_user("testuser")
    print(f"🔍 搜索历史: {user.search_history}")
    
    print("\n✅ 用户系统测试完成！")
