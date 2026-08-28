# -*- coding: utf-8 -*-
"""
管理员面板 - admin.py

功能：
- 用户管理
- 案件管理
- 系统统计
- 操作日志查看
- 数据备份
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from auth import login_required, admin_required, get_current_user
from database import db
import os
import shutil
from datetime import datetime
from pathlib import Path


def create_admin_blueprint(app):
    """创建管理员蓝图"""
    bp = Blueprint("admin", __name__, url_prefix="/admin")
    
    @bp.route("/")
    @admin_required
    def index():
        """管理后台首页"""
        stats = db.get_stats()
        
        # 获取系统信息
        system_info = {
            "total_users": stats.get("total_users", 0),
            "total_favorites": stats.get("total_favorites", 0),
            "total_cases": stats.get("total_cases", 0),
            "total_searches": stats.get("total_searches", 0),
            "today_active": stats.get("today_active_users", 0),
        }
        
        return render_template("admin/index.html", system_info=system_info)
    
    @bp.route("/users")
    @admin_required
    def users():
        """用户列表"""
        page = request.args.get("page", 1, type=int)
        per_page = 20
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # 获取用户总数
            cursor.execute("SELECT COUNT(*) as count FROM users")
            total = cursor.fetchone()["count"]
            
            # 获取用户列表
            offset = (page - 1) * per_page
            cursor.execute("""
                SELECT user_id, username, email, role, created_at, last_login
                FROM users
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (per_page, offset))
            
            users = [dict(row) for row in cursor.fetchall()]
        
        return render_template("admin/users.html", 
                             users=users, 
                             page=page, 
                             total_pages=(total + per_page - 1) // per_page,
                             total=total)
    
    @bp.route("/users/<user_id>")
    @admin_required
    def user_detail(user_id):
        """用户详情"""
        user = db.get_user_by_id(user_id)
        if not user:
            return "用户不存在", 404
        
        favorites = db.get_user_favorites(user_id)
        history = db.get_user_history(user_id)
        logs = db.get_operation_logs(user_id, limit=50)
        
        return render_template("admin/user_detail.html",
                             user=user,
                             favorites=favorites,
                             history=history,
                             logs=logs)
    
    @bp.route("/users/<user_id>/role", methods=["POST"])
    @admin_required
    def change_user_role(user_id):
        """修改用户角色"""
        data = request.get_json()
        new_role = data.get("role", "user")
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET role = ? WHERE user_id = ?", (new_role, user_id))
        
        return jsonify({"success": True})
    
    @bp.route("/users/<user_id>/delete", methods=["POST"])
    @admin_required
    def delete_user(user_id):
        """删除用户"""
        current_user = get_current_user()
        if current_user.user_id == user_id:
            return jsonify({"error": "不能删除自己"}), 400
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            # 删除相关数据
            cursor.execute("DELETE FROM favorites WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM search_history WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM operation_logs WHERE user_id = ?", (user_id,))
            cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        
        return jsonify({"success": True})
    
    @bp.route("/logs")
    @admin_required
    def logs():
        """操作日志"""
        page = request.args.get("page", 1, type=int)
        per_page = 50
        action = request.args.get("action", "")
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            if action:
                cursor.execute("SELECT COUNT(*) as count FROM operation_logs WHERE action = ?", (action,))
            else:
                cursor.execute("SELECT COUNT(*) as count FROM operation_logs")
            
            total = cursor.fetchone()["count"]
            
            offset = (page - 1) * per_page
            if action:
                cursor.execute("""
                    SELECT * FROM operation_logs
                    WHERE action = ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (action, per_page, offset))
            else:
                cursor.execute("""
                    SELECT * FROM operation_logs
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                """, (per_page, offset))
            
            logs = [dict(row) for row in cursor.fetchall()]
        
        # 获取所有操作类型
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT action FROM operation_logs ORDER BY action")
            actions = [row["action"] for row in cursor.fetchall()]
        
        return render_template("admin/logs.html",
                             logs=logs,
                             page=page,
                             total_pages=(total + per_page - 1) // per_page,
                             total=total,
                             actions=actions,
                             current_action=action)
    
    @bp.route("/stats")
    @admin_required
    def stats():
        """详细统计"""
        # 获取各种统计数据
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # 用户角色分布
            cursor.execute("SELECT role, COUNT(*) as count FROM users GROUP BY role")
            role_stats = [dict(row) for row in cursor.fetchall()]
            
            # 最近7天活跃用户
            cursor.execute("""
                SELECT DATE(created_at) as date, COUNT(DISTINCT user_id) as count
                FROM operation_logs
                WHERE created_at >= datetime('now', '-7 days')
                GROUP BY DATE(created_at)
                ORDER BY date
            """)
            daily_active = [dict(row) for row in cursor.fetchall()]
            
            # 热门搜索
            cursor.execute("""
                SELECT query, COUNT(*) as count
                FROM search_history
                GROUP BY query
                ORDER BY count DESC
                LIMIT 10
            """)
            popular_searches = [dict(row) for row in cursor.fetchall()]
            
            # 热门收藏
            cursor.execute("""
                SELECT case_id, COUNT(*) as count
                FROM favorites
                GROUP BY case_id
                ORDER BY count DESC
                LIMIT 10
            """)
            popular_favorites = [dict(row) for row in cursor.fetchall()]
        
        return render_template("admin/stats.html",
                             role_stats=role_stats,
                             daily_active=daily_active,
                             popular_searches=popular_searches,
                             popular_favorites=popular_favorites)
    
    @bp.route("/backup", methods=["GET", "POST"])
    @admin_required
    def backup():
        """数据备份"""
        if request.method == "POST":
            try:
                # 创建备份
                backup_dir = Path("backups")
                backup_dir.mkdir(exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = backup_dir / f"backup_{timestamp}.db"
                
                # 复制数据库
                shutil.copy2("data/prosecution.db", backup_file)
                
                flash(f"备份成功: {backup_file.name}")
            except Exception as e:
                flash(f"备份失败: {str(e)}")
            
            return redirect(url_for("admin.backup"))
        
        # 获取备份列表
        backup_dir = Path("backups")
        backups = []
        if backup_dir.exists():
            for f in sorted(backup_dir.glob("*.db"), reverse=True):
                backups.append({
                    "name": f.name,
                    "size": f.stat().st_size,
                    "created": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                })
        
        return render_template("admin/backup.html", backups=backups)
    
    @bp.route("/api/stats/overview")
    @admin_required
    def api_stats_overview():
        """API: 获取概览统计"""
        stats = db.get_stats()
        return jsonify(stats)
    
    @bp.route("/api/users/count")
    @admin_required
    def api_users_count():
        """API: 用户数量"""
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM users")
            return jsonify({"count": cursor.fetchone()["count"]})
    

    # ---- 数据导出 ----

    @bp.route("/export/users")
    @admin_required
    def export_users():
        """导出用户数据"""
        format = request.args.get("format", "csv")
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, username, email, role, created_at, last_login FROM users")
            users = [dict(row) for row in cursor.fetchall()]
        
        if format == "json":
            from data_export import DataExporter
            return DataExporter.export_to_json(users), 200, {
                "Content-Type": "application/json",
                "Content-Disposition": f"attachment; filename=users_{datetime.now().strftime('%Y%m%d')}.json"
            }
        else:
            from data_export import DataExporter
            columns = ['user_id', 'username', 'email', 'role', 'created_at', 'last_login']
            return DataExporter.export_to_csv(users, columns), 200, {
                "Content-Type": "text/csv",
                "Content-Disposition": f"attachment; filename=users_{datetime.now().strftime('%Y%m%d')}.csv"
            }
    
    @bp.route("/export/activity")
    @admin_required
    def export_activity():
        """导出活动日志"""
        from data_export import ReportGenerator
        report = ReportGenerator(db).generate_activity_report()
        
        from data_export import DataExporter
        return DataExporter.export_to_json(report), 200, {
            "Content-Type": "application/json",
            "Content-Disposition": f"attachment; filename=activity_{datetime.now().strftime('%Y%m%d')}.json"
        }
    
    @bp.route("/export/full-report")
    @admin_required
    def export_full_report():
        """导出完整报告"""
        from data_export import ReportGenerator
        report = ReportGenerator(db).generate_full_report()
        
        from data_export import DataExporter
        return DataExporter.export_to_json(report, pretty=True), 200, {
            "Content-Type": "application/json",
            "Content-Disposition": f"attachment; filename=full_report_{datetime.now().strftime('%Y%m%d')}.json"
        }
    
    @bp.route("/export/audit-logs")
    @admin_required
    def export_audit_logs():
        """导出审计日志"""
        logs = db.get_operation_logs(limit=5000)
        
        from data_export import DataExporter
        return DataExporter.export_to_csv(logs), 200, {
            "Content-Type": "text/csv",
            "Content-Disposition": f"attachment; filename=audit_logs_{datetime.now().strftime('%Y%m%d')}.csv"
        }

    return bp


# ---- 数据导出 ----

    @bp.route("/export/users")
    @admin_required
    def export_users():
        """导出用户数据"""
        format = request.args.get("format", "csv")
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, username, email, role, created_at, last_login FROM users")
            users = [dict(row) for row in cursor.fetchall()]
        
        if format == "json":
            from data_export import DataExporter
            return DataExporter.export_to_json(users), 200, {
                "Content-Type": "application/json",
                "Content-Disposition": f"attachment; filename=users_{datetime.now().strftime('%Y%m%d')}.json"
            }
        else:
            from data_export import DataExporter
            columns = ['user_id', 'username', 'email', 'role', 'created_at', 'last_login']
            return DataExporter.export_to_csv(users, columns), 200, {
                "Content-Type": "text/csv",
                "Content-Disposition": f"attachment; filename=users_{datetime.now().strftime('%Y%m%d')}.csv"
            }
    
    @bp.route("/export/activity")
    @admin_required
    def export_activity():
        """导出活动日志"""
        from data_export import ReportGenerator
        report = ReportGenerator(db).generate_activity_report()
        
        from data_export import DataExporter
        return DataExporter.export_to_json(report), 200, {
            "Content-Type": "application/json",
            "Content-Disposition": f"attachment; filename=activity_{datetime.now().strftime('%Y%m%d')}.json"
        }
    
    @bp.route("/export/full-report")
    @admin_required
    def export_full_report():
        """导出完整报告"""
        from data_export import ReportGenerator
        report = ReportGenerator(db).generate_full_report()
        
        from data_export import DataExporter
        return DataExporter.export_to_json(report, pretty=True), 200, {
            "Content-Type": "application/json",
            "Content-Disposition": f"attachment; filename=full_report_{datetime.now().strftime('%Y%m%d')}.json"
        }
    
    @bp.route("/export/audit-logs")
    @admin_required
    def export_audit_logs():
        """导出审计日志"""
        logs = db.get_operation_logs(limit=5000)
        
        from data_export import DataExporter
        return DataExporter.export_to_csv(logs), 200, {
            "Content-Type": "text/csv",
            "Content-Disposition": f"attachment; filename=audit_logs_{datetime.now().strftime('%Y%m%d')}.csv"
        }
