# -*- coding: utf-8 -*-
"""管理后台"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from src.auth import login_required, admin_required, get_current_user
from src.database import db
import shutil
from datetime import datetime
from pathlib import Path

def create_admin_blueprint(app):
    bp = Blueprint("admin", __name__, url_prefix="/admin")
    
    @bp.route("/")
    @admin_required
    def index():
        stats = db.get_stats()
        return render_template("admin/index.html", system_info={
            "total_users": stats.get("total_users", 0),
            "total_favorites": stats.get("total_favorites", 0),
            "total_cases": stats.get("total_cases", 0),
            "total_searches": stats.get("total_searches", 0),
        })
    
    @bp.route("/users")
    @admin_required
    def users():
        page = request.args.get("page", 1, type=int)
        per_page = 20
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM users")
            total = cursor.fetchone()["count"]
            offset = (page - 1) * per_page
            cursor.execute("""SELECT user_id, username, email, role, created_at, last_login FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?""", (per_page, offset))
            users_list = [dict(row) for row in cursor.fetchall()]
        return render_template("admin/users.html", users=users_list, page=page, total_pages=(total + per_page - 1) // per_page, total=total)
    
    @bp.route("/users/<user_id>")
    @admin_required
    def user_detail(user_id):
        user = db.get_user_by_id(user_id)
        if not user: return "用户不存在", 404
        return render_template("admin/user_detail.html", user=user, favorites=db.get_user_favorites(user_id), history=db.get_user_history(user_id), logs=db.get_operation_logs(user_id, limit=50))
    
    @bp.route("/users/<user_id>/role", methods=["POST"])
    @admin_required
    def change_user_role(user_id):
        with db.get_connection() as conn:
            conn.execute("UPDATE users SET role = ? WHERE user_id = ?", (request.get_json().get("role", "user"), user_id))
        return jsonify({"success": True})
    
    @bp.route("/users/<user_id>/delete", methods=["POST"])
    @admin_required
    def delete_user(user_id):
        current_user = get_current_user()
        if current_user.user_id == user_id: return jsonify({"error": "不能删除自己"}), 400
        with db.get_connection() as conn:
            conn.execute("DELETE FROM favorites WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM search_history WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM operation_logs WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        return jsonify({"success": True})
    
    @bp.route("/logs")
    @admin_required
    def logs():
        page = request.args.get("page", 1, type=int)
        per_page = 50
        action = request.args.get("action", "")
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM operation_logs" + (" WHERE action = ?" if action else ""))
            total = cursor.fetchone()["count"]
            offset = (page - 1) * per_page
            cursor.execute(f"SELECT * FROM operation_logs {'WHERE action = ?' if action else ''} ORDER BY created_at DESC LIMIT ? OFFSET ?", 
                         ((action, per_page, offset) if action else (per_page, offset)))
            logs_list = [dict(row) for row in cursor.fetchall()]
            cursor.execute("SELECT DISTINCT action FROM operation_logs ORDER BY action")
            actions = [row["action"] for row in cursor.fetchall()]
        return render_template("admin/logs.html", logs=logs_list, page=page, total_pages=(total + per_page - 1) // per_page, total=total, actions=actions, current_action=action)
    
    @bp.route("/stats")
    @admin_required
    def stats():
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT role, COUNT(*) as count FROM users GROUP BY role")
            role_stats = [dict(row) for row in cursor.fetchall()]
            cursor.execute("SELECT DATE(created_at) as date, COUNT(DISTINCT user_id) as count FROM operation_logs WHERE created_at >= datetime('now', '-7 days') GROUP BY DATE(created_at) ORDER BY date")
            daily_active = [dict(row) for row in cursor.fetchall()]
            cursor.execute("SELECT query, COUNT(*) as count FROM search_history GROUP BY query ORDER BY count DESC LIMIT 10")
            popular_searches = [dict(row) for row in cursor.fetchall()]
            cursor.execute("SELECT case_id, COUNT(*) as count FROM favorites GROUP BY case_id ORDER BY count DESC LIMIT 10")
            popular_favorites = [dict(row) for row in cursor.fetchall()]
        return render_template("admin/stats.html", role_stats=role_stats, daily_active=daily_active, popular_searches=popular_searches, popular_favorites=popular_favorites)
    
    @bp.route("/dashboard")
    @admin_required
    def dashboard():
        stats = db.get_stats()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DATE(created_at) as date, COUNT(DISTINCT user_id) as count FROM operation_logs WHERE created_at >= datetime('now', '-30 days') GROUP BY DATE(created_at) ORDER BY date")
            daily_active = [dict(row) for row in cursor.fetchall()]
            cursor.execute("SELECT query, COUNT(*) as count FROM search_history GROUP BY query ORDER BY count DESC LIMIT 10")
            popular_searches = [dict(row) for row in cursor.fetchall()]
        return render_template("admin/dashboard.html", stats=stats, daily_active=daily_active, popular_searches=popular_searches)
    
    @bp.route("/backup", methods=["GET", "POST"])
    @admin_required
    def backup():
        if request.method == "POST":
            try:
                backup_dir = Path("backups"); backup_dir.mkdir(exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                shutil.copy2("data/prosecution.db", backup_dir / f"backup_{timestamp}.db")
                flash("备份成功")
            except Exception as e:
                flash(f"备份失败: {e}")
            return redirect(url_for("admin.backup"))
        backup_dir = Path("backups"); backups = []
        if backup_dir.exists():
            for f in sorted(backup_dir.glob("*.db"), reverse=True):
                backups.append({"name": f.name, "size": f.stat().st_size, "created": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")})
        return render_template("admin/backup.html", backups=backups)
    
    @bp.route("/api/stats/overview")
    @admin_required
    def api_stats_overview(): return jsonify(db.get_stats())
    
    @bp.route("/api/users/count")
    @admin_required
    def api_users_count():
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM users")
            return jsonify({"count": cursor.fetchone()["count"]})
    
    @bp.route("/export/users")
    @admin_required
    def export_users():
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, username, email, role, created_at, last_login FROM users")
            users_list = [dict(row) for row in cursor.fetchall()]
        from data_export import DataExporter
        fmt = request.args.get("format", "csv")
        if fmt == "json":
            return DataExporter.export_to_json(users_list), 200, {"Content-Type": "application/json"}
        columns = ['user_id', 'username', 'email', 'role', 'created_at', 'last_login']
        return DataExporter.export_to_csv(users_list, columns), 200, {"Content-Type": "text/csv"}
    
    @bp.route("/export/activity")
    @admin_required
    def export_activity():
        from data_export import ReportGenerator, DataExporter
        return DataExporter.export_to_json(ReportGenerator(db).generate_activity_report()), 200, {"Content-Type": "application/json"}
    
    @bp.route("/export/full-report")
    @admin_required
    def export_full_report():
        from data_export import ReportGenerator, DataExporter
        return DataExporter.export_to_json(ReportGenerator(db).generate_full_report(), pretty=True), 200, {"Content-Type": "application/json"}
    
    @bp.route("/export/audit-logs")
    @admin_required
    def export_audit_logs():
        from data_export import DataExporter
        return DataExporter.export_to_csv(db.get_operation_logs(limit=5000)), 200, {"Content-Type": "text/csv"}
    
    @bp.route("/case-import", methods=["GET", "POST"])
    @admin_required
    def case_import():
        """案件批量导入"""
        if request.method == "GET":
            return render_template("admin/case_import.html", result=None, errors=[])

        # POST: 处理文件上传
        from src.case_importer import CaseImporter
        import tempfile, os

        if "file" not in request.files:
            return render_template("admin/case_import.html", result=None, errors=["请选择要上传的文件"])

        file = request.files["file"]
        if not file.filename:
            return render_template("admin/case_import.html", result=None, errors=["未选择文件"])

        suffix = file.filename.split(".")[-1].lower()
        if suffix not in ("csv", "xlsx", "xls"):
            return render_template("admin/case_import.html", result=None,
                                  errors=[f"不支持的格式: .{suffix}，仅支持 CSV / Excel（.xlsx .xls）"])

        # 保存到临时文件
        tmp_dir = tempfile.mkdtemp(prefix="case_import_")
        tmp_path = os.path.join(tmp_dir, file.filename)
        file.save(tmp_path)

        try:
            from pathlib import Path as _Path
            importer = CaseImporter(output_dir=_Path(tmp_dir))
            result = importer.import_file(tmp_path)
        finally:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)

        # 返回结果
        return render_template("admin/case_import.html",
                               result={
                                   "success": result.success,
                                   "imported": result.imported,
                                   "failed": result.failed,
                                   "total": result.imported + result.failed,
                                   "summary": result.summary(),
                                   "warnings": result.warnings[:10],
                               },
                               errors=result.errors[:20])

    @bp.route("/case-import/template")
    @admin_required
    def case_import_template():
        """下载案件导入模板 CSV"""
        import io, csv
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["case_id", "case_name", "court", "被告人", "罪名", "涉案金额", "判决日期", "备注"])
        writer.writerow(["CASE-EXAMPLE-001", "张三盗窃案", "上海市浦东新区人民法院", "张三", "盗窃罪", "15000", "2024-06-15", "初犯、自首"])
        writer.writerow(["CASE-EXAMPLE-002", "李四诈骗案", "北京市朝阳区人民法院", "李四", "诈骗罪", "80000", "2024-05-20", "已赔偿、谅解"])
        output.seek(0)
        return output.getvalue(), 200, {
            "Content-Type": "text/csv; charset=utf-8-sig",
            "Content-Disposition": "attachment; filename=case_import_template.csv"
        }


    return bp
