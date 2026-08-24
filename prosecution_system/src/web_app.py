# -*- coding: utf-8 -*-
"""
追诉系统 Web UI - prosecution_system/src/web_app.py
Flask Web 应用

功能：
- 案件搜索与浏览
- 报告生成
- 案件跟踪管理
- 实时状态更新

启动：python src/web_app.py
访问：http://localhost:5000
"""

import os
import re
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from logging_config import setup_logging

logger = setup_logging("web_app")

from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
import yaml

from case_loader import CaseLoader
from build_report import ReportBuilder
from wenshu_updater import CaseTracker, ManualTracker

# ---- Flask App ----

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "prosecution-system-secret-key")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max

loader = CaseLoader()
OUTPUT_DIR = Path(__file__).parent.parent / "output"
DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ---- 首页/案件列表 ----

# ---- 安全中间件 ----

@app.before_request
def security_headers() -> None:
    """注入安全响应头（预处理）"""
    pass  # 响应头在实际响应中通过 after_request 设置


@app.after_request
def add_security_headers(response):
    """追加安全响应头"""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # 移除 Server 指纹
    response.headers.pop("Server", None)
    return response


@app.route("/")
def index():
    """首页 - 案件列表"""
    status_filter = request.args.get("status", "")
    cases = loader.list_cases(status=status_filter if status_filter else None)
    statuses = ["investigating", "prosecuted", "judged", "appealed", "closed"]
    status_labels = {
        "investigating": "调查中",
        "prosecuted": "已起诉",
        "judged": "已判决",
        "appealed": "上诉中",
        "closed": "已结案",
    }
    return render_template(
        "index.html",
        cases=cases,
        statuses=statuses,
        status_labels=status_labels,
        active_status=status_filter,
    )


# ---- 案件详情 ----

@app.route("/case/<case_id>")
def case_detail(case_id):
    """案件详情页"""
    try:
        data = loader.load(case_id)
    except FileNotFoundError:
        return f"案件未找到: {case_id}", 404

    meta = data.get("meta", {})
    case_info = data.get("case_info", {})
    defendants = loader.get_defendants(case_id)
    charges = loader.get_charges(case_id)
    evidence_gaps = loader.get_evidence_gaps(case_id)
    victims = loader.get_victims(case_id)

    tracker = CaseTracker()
    tracked_cases = tracker.list_tracked()
    is_tracked = any(t["case_id"] == case_id for t in tracked_cases)
    tracker_history = tracker.get_case_history(case_id)

    warnings = loader.validate(case_id)

    return render_template(
        "case_detail.html",
        case_id=case_id,
        meta=meta,
        case_info=case_info,
        defendants=defendants,
        charges=charges,
        evidence_gaps=evidence_gaps,
        victims=victims,
        is_tracked=is_tracked,
        tracker_history=tracker_history,
        warnings=warnings,
    )


# ---- 搜索 ----

@app.route("/search")
def search():
    """全局搜索"""
    query = request.args.get("q", "").strip()
    if not query:
        return redirect(url_for("index"))

    # 搜索案件配置
    results = loader.search_cases(query)

    # 搜索案件名称
    all_cases = loader.list_cases()
    name_matches = [c for c in all_cases
                    if query.lower() in c.get("case_name", "").lower()
                    or query.lower() in c.get("case_name_full", "").lower()]

    return render_template(
        "search.html",
        query=query,
        results=results,
        name_matches=name_matches,
    )


# ---- 报告生成 ----

@app.route("/case/<case_id>/generate", methods=["GET", "POST"])
def generate_report(case_id):
    """生成报告"""
    try:
        data = loader.load(case_id)
    except FileNotFoundError:
        return jsonify({"error": f"案件未找到: {case_id}"}), 404

    if request.method == "POST":
        fmt = request.form.get("format", "tex")
        try:
            builder = ReportBuilder(case_id, loader)
            case_slug = case_id.lower().replace("case-", "").replace("-", "")
            tex_path = OUTPUT_DIR / f"{case_slug}_report.tex"
            builder.save_tex(tex_path)

            if fmt == "pdf":
                pdf_path = builder.compile_pdf(tex_path)
                if pdf_path:
                    return jsonify({
                        "success": True,
                        "message": "PDF 报告已生成",
                        "download_url": f"/download/{case_slug}_report.pdf",
                    })
                else:
                    return jsonify({"error": "PDF 编译失败，请检查 LaTeX 安装"}), 500
            else:
                return jsonify({
                    "success": True,
                    "message": "LaTeX 报告已生成",
                    "download_url": f"/download/{case_slug}_report.tex",
                })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # GET: 显示生成选项页面
    meta = data.get("meta", {})
    return render_template(
        "generate_report.html",
        case_id=case_id,
        case_name=meta.get("case_name_full", meta.get("case_name", "")),
    )


# ---- 文件下载 ----

@app.route("/download/<filename>")
def download(filename):
    """下载生成的报告"""
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        return "文件未找到", 404
    return send_file(file_path, as_attachment=True)


# ---- 案件跟踪 ----

@app.route("/tracker/add", methods=["POST"])
def tracker_add():
    """添加案件跟踪"""
    data = request.get_json()
    case_id = data.get("case_id", "")
    case_num = data.get("case_num", "")
    court = data.get("court", "")
    status = data.get("status", "investigating")

    tracker = CaseTracker()
    tracker.add_case(case_id, case_num, court, status)
    return jsonify({"success": True, "message": f"已添加案件跟踪: {case_id}"})


@app.route("/tracker/update", methods=["POST"])
def tracker_update():
    """更新案件状态"""
    data = request.get_json()
    case_id = data.get("case_id", "")
    new_status = data.get("status", "")
    event = data.get("event", "")

    tracker = CaseTracker()
    tracker.update_status(case_id, new_status, event=event)
    return jsonify({"success": True})


@app.route("/tracker/remove", methods=["POST"])
def tracker_remove():
    """移除案件跟踪"""
    data = request.get_json()
    case_id = data.get("case_id", "")

    tracker = CaseTracker()
    tracker.remove_case(case_id)
    return jsonify({"success": True})


@app.route("/tracker")
def tracker_page():
    """跟踪管理页面"""
    tracker = CaseTracker()
    cases = tracker.list_tracked()
    return render_template("tracker.html", tracked_cases=cases)


@app.route("/tracker/log", methods=["POST"])
def tracker_log():
    """手动记录案件事件"""
    data = request.get_json()
    case_id = data.get("case_id", "")
    event = data.get("event", "")
    source = data.get("source", "")

    manual = ManualTracker()
    manual.log_event(case_id, event, source=source)
    return jsonify({"success": True})


# ---- API 接口 ----

@app.route("/api/cases")
def api_cases():
    """案件列表 API"""
    status = request.args.get("status", "")
    cases = loader.list_cases(status=status if status else None)
    return jsonify({"cases": cases, "total": len(cases)})


@app.route("/api/case/<case_id>")
def api_case(case_id):
    """案件详情 API"""
    try:
        data = loader.load(case_id)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({"error": f"案件未找到: {case_id}"}), 404


@app.route("/api/case/<case_id>/charges")
def api_charges(case_id):
    """罪名分析 API"""
    try:
        charges = loader.get_charges(case_id)
        return jsonify(charges)
    except FileNotFoundError:
        return jsonify({"error": f"案件未找到: {case_id}"}), 404


# ---- 运行 ----

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    logger.info(f"🚀 追诉系统启动: http://localhost:{port}，调试模式: {debug}，案件数量: {len(loader.list_cases())}")
    print(f"🚀 追诉系统启动: http://localhost:{port}")
    print(f"   调试模式: {debug}")
    print(f"   案件数量: {len(loader.list_cases())}")
    app.run(host="0.0.0.0", port=port, debug=debug)
