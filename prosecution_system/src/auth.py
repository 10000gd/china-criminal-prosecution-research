# -*- coding: utf-8 -*-
"""
用户认证模块 - auth.py

功能：
- 用户注册/登录/登出
- Session管理
- 密码加密存储
- 用户收藏管理

使用 SQLite 数据库 (database.py)
"""

from functools import wraps
from flask import session, request, jsonify, redirect, url_for, flash, g
from database import db, Database, User


def login_required(f):
    """登录_required装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            if request.is_json:
                return jsonify({"error": "请先登录", "code": "unauthorized"}), 401
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """管理员_required装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            if request.is_json:
                return jsonify({"error": "请先登录", "code": "unauthorized"}), 401
            return redirect(url_for("auth.login"))
        
        user = get_current_user()
        if not user or user.role != "admin":
            if request.is_json:
                return jsonify({"error": "需要管理员权限", "code": "forbidden"}), 403
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated_function


def get_current_user() -> User:
    """获取当前登录用户"""
    if "user_id" in session:
        return db.get_user_by_id(session["user_id"])
    return None


def get_user_favorites(user_id: str) -> list:
    """获取用户收藏"""
    return db.get_user_favorites(user_id)


def get_user_history(user_id: str) -> list:
    """获取用户搜索历史"""
    return db.get_user_history(user_id, limit=20)


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
        
        data = request.get_json() if request.is_json else request.form
        username = data.get("username", "")
        password = data.get("password", "")
        
        if not username or not password:
            if request.is_json:
                return jsonify({"error": "请输入用户名和密码"}), 400
            flash("请输入用户名和密码")
            return redirect(url_for("auth.login"))
        
        user = db.authenticate(username, password)
        if user:
            session["user_id"] = user.user_id
            session["username"] = user.username
            session["role"] = user.role
            
            # 记录登录日志
            db.log_operation(user.user_id, "login", ip_address=request.remote_addr)
            
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
        
        data = request.get_json() if request.is_json else request.form
        username = data.get("username", "")
        email = data.get("email", "")
        password = data.get("password", "")
        role = data.get("role", "user")
        
        if not username or not email or not password:
            if request.is_json:
                return jsonify({"error": "请填写所有必填项"}), 400
        
        if len(password) < 6:
            if request.is_json:
                return jsonify({"error": "密码至少6位"}), 400
            flash("密码至少6位")
            return redirect(url_for("auth.register"))
        
        user = db.create_user(username, email, password, role)
        if user:
            session["user_id"] = user.user_id
            session["username"] = user.username
            session["role"] = user.role
            
            # 记录注册日志
            db.log_operation(user.user_id, "register", ip_address=request.remote_addr)
            
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
        if "user_id" in session:
            db.log_operation(session["user_id"], "logout", ip_address=request.remote_addr)
        session.clear()
        if request.is_json:
            return jsonify({"success": True, "message": "已退出登录"})
        return redirect(url_for("auth.login"))
    
    @bp.route("/profile")
    @login_required
    def profile():
        """用户资料页面/接口"""
        user = get_current_user()
        favorites = get_user_favorites(user.user_id)
        history = get_user_history(user.user_id)
        
        if request.is_json:
            return jsonify({
                "user": user.to_dict(),
                "favorites": favorites,
                "search_history": history,
            })
        return _render_profile_page(user, favorites, history)
    
    @bp.route("/favorites", methods=["GET", "POST", "DELETE"])
    @login_required
    def favorites():
        """收藏管理"""
        user = get_current_user()
        
        if request.method == "GET":
            favs = get_user_favorites(user.user_id)
            if request.is_json:
                return jsonify({"favorites": favs})
            return _render_favorites_page(user, favs)
        
        elif request.method == "POST":
            data = request.get_json()
            case_id = data.get("case_id", "")
            if case_id:
                db.add_favorite(user.user_id, case_id)
                db.log_operation(user.user_id, "add_favorite", case_id)
                return jsonify({"success": True, "favorites": get_user_favorites(user.user_id)})
            return jsonify({"error": "缺少case_id"}), 400
        
        elif request.method == "DELETE":
            data = request.get_json()
            case_id = data.get("case_id", "")
            if case_id:
                db.remove_favorite(user.user_id, case_id)
                db.log_operation(user.user_id, "remove_favorite", case_id)
                return jsonify({"success": True, "favorites": get_user_favorites(user.user_id)})
            return jsonify({"error": "缺少case_id"}), 400
    
    @bp.route("/search-history", methods=["GET", "DELETE"])
    @login_required
    def search_history():
        """搜索历史"""
        user = get_current_user()
        
        if request.method == "GET":
            return jsonify({"history": get_user_history(user.user_id)})
        
        elif request.method == "DELETE":
            db.clear_search_history(user.user_id)
            db.log_operation(user.user_id, "clear_history")
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


def _render_profile_page(user: User, favorites: list, history: list) -> str:
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
                    <div class="stat-value">{len(favorites)}</div>
                    <div class="stat-label">收藏案件</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{len(history)}</div>
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


def _render_favorites_page(user: User, favorites: list) -> str:
    favorites_html = ""
    if favorites:
        for case_id in favorites:
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
    print("=== 用户系统测试 ===\n")
    
    # 创建测试用户
    user = db.create_user("testuser", "test@example.com", "password123")
    if user:
        print(f"✅ 用户创建成功: {user.username}")
    else:
        print("⚠️ 用户已存在")
    
    # 登录测试
    user = db.authenticate("testuser", "password123")
    if user:
        print(f"✅ 登录成功: {user.username} ({user.role})")
    else:
        print("❌ 登录失败")
    
    # 收藏测试
    db.add_favorite(user.user_id, "CASE-001")
    db.add_favorite(user.user_id, "CASE-002")
    favorites = db.get_user_favorites(user.user_id)
    print(f"📌 收藏列表: {favorites}")
    
    # 搜索历史测试
    db.add_search_history(user.user_id, "正当防卫")
    db.add_search_history(user.user_id, "盗窃罪")
    history = db.get_user_history(user.user_id)
    print(f"🔍 搜索历史: {history}")
    
    print("\n✅ 用户系统测试完成！")
