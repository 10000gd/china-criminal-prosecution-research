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
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from logging_config import setup_logging

logger = setup_logging("web_app")

from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, session

# 导入认证模块
from auth import create_auth_blueprint, login_required, get_current_user
from security import CSRFProtection, csrf_protect, generate_csrf_token
from admin import create_admin_blueprint
import yaml

from case_loader import CaseLoader
from build_report import ReportBuilder
from wenshu_updater import CaseTracker, ManualTracker

# ---- Flask App ----
# template_folder 指向项目根目录 (src/ 的上一层)，而不是 src/templates/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
app = Flask(__name__,
                template_folder=str(PROJECT_ROOT / "templates"),
                static_folder=str(PROJECT_ROOT / "static"),
                static_url_path="/static")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "prosecution-system-secret-key")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max

# 注册认证蓝图
auth_bp = create_auth_blueprint(app)
app.register_blueprint(auth_bp)

# 注册管理后台蓝图
admin_bp = create_admin_blueprint(app)
app.register_blueprint(admin_bp)
from api_docs import create_api_docs_blueprint
api_docs_bp = create_api_docs_blueprint(app)
app.register_blueprint(api_docs_bp)

loader = CaseLoader()
# LawRAG: 法律语义检索（惰性初始化，首次搜索时加载）
# 使用后台线程预热，不阻塞请求处理
import threading
_rag_instance = None
_rag_lock = threading.Lock()
_rag_ready = threading.Event()

def _warmup_rag():
    """后台线程：预热 LawRAG，完成后通知等待者"""
    global _rag_instance
    import io, contextlib, os
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        from law_rag import LawRAG
        _rag_instance = LawRAG(enable_vector=True)
    _rag_ready.set()

def get_rag():
    """返回 LawRAG 单例，首次调用时后台启动预热线程"""
    global _rag_instance
    if _rag_instance is None:
        with _rag_lock:
            if _rag_instance is None:
                t = threading.Thread(target=_warmup_rag, daemon=True)
                t.start()
    return _rag_instance  # 返回未完全初始化的实例用于快速返回

OUTPUT_DIR = Path(__file__).parent.parent / "output"
DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ---- 首页/案件列表 ----

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

@app.before_request
def inject_user():
    """注入当前用户信息到所有模板"""
    from flask import g
    g.current_user = get_current_user()
    g.csrf_token = CSRFProtection.set_token()
    g.user_logged_in = 'user_id' in session


@app.context_processor
def inject_template_globals():
    """注入全局模板变量"""
    from flask import session
    return {
        'current_user': get_current_user(),
        'user_logged_in': 'user_id' in session,
    }


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


@app.route("/docs")
def docs_page():
    """API文档页面 - 中文文档"""
    return render_template("docs_zh.html")


@app.route("/docs-en")
def docs_page_en():
    """API文档页面 - 英文文档"""
    return render_template("docs.html")


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

@app.route("/api/search")
def api_search():
    """全局搜索 API（案件+法律条文混合）"""
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "缺少查询参数 q"}), 400

    # 搜索案件
    case_results = loader.search_cases(query)
    all_cases = loader.list_cases()
    name_matches = [
        {"case_id": c["case_id"], "case_name": c.get("case_name", ""),
         "case_type": c.get("case_type", ""), "status": c.get("status", ""),
         "judgment_date": c.get("judgment_date", "")}
        for c in all_cases
        if query.lower() in c.get("case_name", "").lower()
        or query.lower() in c.get("case_name_full", "").lower()
    ]

    # 搜索法律条文
    try:
        rag = get_rag()
        law_results = rag.search(query, top_k=5, hybrid=True)
        law_hits = [{
            "law": h.get("law", ""),
            "article": h.get("article", ""),
            "category": h.get("category", ""),
            "score": round(h.get("score", 0), 1),
            "preview": h.get("preview", "")[:120],
        } for h in law_results]
    except Exception:
        law_hits = []

    return jsonify({
        "query": query,
        "case_results": case_results,
        "name_matches": name_matches,
        "law_results": law_hits,
        "total_cases": len(case_results),
        "total_laws": len(law_hits),
    })


@app.route("/search")
def search():
    """全局搜索"""
    query = request.args.get("q", "").strip()
    user = get_current_user()
    
    # 如果没有查询，显示搜索历史
    if not query:
        return render_template(
            "search.html",
            query="",
            results=[],
            name_matches=[],
            search_history=user.search_history[:10] if user else [],
        )

    # 保存搜索历史（如果已登录）
    if user and query:
        user_db.add_search_history(user.username, query)
    
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
        search_history=user.search_history[:10] if user else [],
    )


# ── 法律 RAG 检索 ─────────────────────────────────────────

@app.route("/law/search")
def law_search_page():
    """法律语义检索页面"""
    query = request.args.get("q", "").strip()
    mode = request.args.get("mode", "hybrid")
    top_k = request.args.get("top_k", "10")
    return render_template(
        "law_search.html",
        query=query,
        mode=mode,
        top_k=int(top_k),
    )


@app.route("/api/law/search")
def api_law_search():
    """法律检索 API

    GET /api/law/search?q=查询内容&mode=hybrid|bm25&top=10
    """
    import time
    query = request.args.get("q", "").strip()
    mode = request.args.get("mode", "hybrid")
    top_k = min(int(request.args.get("top", 10)), 50)

    if not query:
        return jsonify({"error": "缺少查询参数 q"}), 400

    try:
        rag = get_rag()
        t0 = time.time()
        hits = rag.search(query, top_k=top_k, hybrid=(mode == "hybrid"))
        elapsed_ms = round((time.time() - t0) * 1000)

        results = []
        for h in hits:
            bm25_s = h.get("bm25_score", 0)
            vec_s = h.get("vector_score", 0)
            score = h.get("score", 0) or bm25_s or vec_s
            if mode == "bm25" or (mode == "hybrid" and vec_s == 0 and bm25_s > 0):
                score_type = "bm25"
            elif mode == "hybrid":
                score_type = "hybrid"
            else:
                score_type = "vector"

            results.append({
                "title": h.get("title", ""),
                "law": h.get("law", ""),
                "article": h.get("article", ""),
                "category": h.get("category", ""),
                "score": float(score),
                "score_type": score_type,
                "bm25_score": float(bm25_s) if bm25_s else 0.0,
                "vector_score": float(vec_s) if vec_s else 0.0,
                "preview": h.get("preview", ""),
                "content": h.get("content", ""),
            })

        return jsonify({
            "query": query,
            "mode": mode,
            "time_ms": elapsed_ms,
            "total": len(results),
            "results": results,
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---- 报告生成 ----

@app.route("/case/<case_id>/generate", methods=["GET", "POST"])
def generate_report(case_id):
    """生成报告 — GET/POST 均改为调用已有的辩护报告 API"""
    try:
        loader.load(case_id)
    except FileNotFoundError:
        return jsonify({"error": f"案件未找到: {case_id}"}), 404

    if request.method == "POST":
        try:
            builder = ReportBuilder(case_id, loader)
            case_slug = case_id.lower().replace("case-", "").replace("-", "")
            tex_path = OUTPUT_DIR / f"{case_slug}_report.tex"
            builder.save_tex(tex_path)
            return jsonify({
                "success": True,
                "message": "报告已生成",
                "download_url": f"/download/{case_slug}_report.tex",
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # GET: 重定向到辩护分析页（那里有完整的报告生成流程）
    from flask import redirect
    return redirect(f"/defense/{case_id}")


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


# ---- 案件对比 ----

from case_comparison import CaseComparator, compare_cases

@app.route("/compare")
def compare_page():
    """案件对比页面（支持空访问，由前端JS动态加载案件列表）"""
    case_ids = request.args.getlist("case_id")
    if len(case_ids) < 2:
        return render_template("compare.html", comparison=None, case_ids=[])  # 前端JS动态对比
    
    cases_data = []
    for case_id in case_ids:
        try:
            data = loader.load(case_id)
            cases_data.append(data)
        except FileNotFoundError:
            return f"案件不存在: {case_id}", 404
    
    comparator = CaseComparator()
    result = comparator.compare_cases(case_ids, cases_data)
    
    return render_template("compare.html", 
                         comparison=result,
                         case_ids=case_ids)

@app.route("/api/compare", methods=["POST"])
def api_compare():
    """案件对比 API"""
    data = request.get_json()
    case_ids = data.get("case_ids", [])
    
    if len(case_ids) < 2:
        return jsonify({"error": "至少需要2个案件"}), 400
    if len(case_ids) > 5:
        return jsonify({"error": "最多支持5个案件"}), 400
    
    cases_data = []
    for case_id in case_ids:
        try:
            case_data = loader.load(case_id)
            cases_data.append(case_data)
        except FileNotFoundError:
            return jsonify({"error": f"案件不存在: {case_id}"}), 404
    
    comparator = CaseComparator()
    result = comparator.compare_cases(case_ids, cases_data)
    
    return jsonify({
        "case_ids": result.case_ids,
        "summary": result.summary,
        "insights": result.insights,
        "comparison_items": [
            {
                "field": item.field,
                "label": item.label,
                "values": item.values,
                "highlight": item.highlight,
            }
            for item in result.comparison_items
        ],
    })


# ---- GET 支持（兼容 ?ids= 用法） ----

@app.route("/api/compare", methods=["GET"])
def api_compare_get():
    """案件对比 API（GET 方式，兼容 ids= 参数）"""
    ids_param = request.args.get("ids", "")
    case_ids = [x.strip() for x in ids_param.split(",") if x.strip()]
    if len(case_ids) < 2:
        return jsonify({"error": "至少需要2个案件，用逗号分隔，如 ?ids=CASE-0001,CASE-0002"}), 400
    if len(case_ids) > 5:
        return jsonify({"error": "最多支持5个案件"}), 400
    cases_data = []
    for case_id in case_ids:
        try:
            case_data = loader.load(case_id)
            cases_data.append(case_data)
        except FileNotFoundError:
            return jsonify({"error": f"案件不存在: {case_id}"}), 404
    comparator = CaseComparator()
    result = comparator.compare_cases(case_ids, cases_data)
    return jsonify({
        "case_ids": result.case_ids,
        "summary": result.summary,
        "insights": result.insights,
        "comparison_items": [
            {
                "field": item.field,
                "label": item.label,
                "values": item.values,
                "highlight": item.highlight,
            }
            for item in result.comparison_items
        ],
    })


# ---- PDF导出 ----

from pdf_exporter import PDFExporter

@app.route("/export/case/<case_id>")
@login_required
def export_case_pdf(case_id):
    """导出案件为PDF（HTML格式）"""
    try:
        case_data = loader.load(case_id)
    except FileNotFoundError:
        return f"案件不存在: {case_id}", 404
    
    exporter = PDFExporter()
    output_path = exporter.export_case_to_html(case_data)
    
    return send_file(output_path, as_attachment=True, download_name=f"{case_id}_report.html")


@app.route("/export/comparison")
@login_required
def export_comparison_pdf():
    """导出对比报告为PDF"""
    case_ids = request.args.getlist("case_id")
    if len(case_ids) < 2:
        return jsonify({"error": "至少需要2个案件"}), 400
    
    cases_data = []
    for case_id in case_ids:
        try:
            data = loader.load(case_id)
            cases_data.append(data)
        except FileNotFoundError:
            return jsonify({"error": f"案件不存在: {case_id}"}), 404
    
    comparator = CaseComparator()
    result = comparator.compare_cases(case_ids, cases_data)
    
    comparison_data = {
        "case_ids": result.case_ids,
        "summary": result.summary,
        "insights": result.insights,
        "comparison_items": [
            {
                "field": item.field,
                "label": item.label,
                "values": item.values,
                "highlight": item.highlight,
                "is_better": item.is_better,
            }
            for item in result.comparison_items
        ],
    }
    
    exporter = PDFExporter()
    output_path = exporter.export_comparison_to_html(comparison_data)
    
    return send_file(output_path, as_attachment=True, download_name="comparison_report.html")


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


@app.route("/api/cases/<case_id>")
def api_case_alias(case_id):
    """案件详情 API（兼容 /api/cases/<id> 路径）"""
    return api_case(case_id)


@app.route("/api/case/<case_id>/charges")
def api_charges(case_id):
    """罪名分析 API"""
    try:
        charges = loader.get_charges(case_id)
        return jsonify(charges)
    except FileNotFoundError:
        return jsonify({"error": f"案件未找到: {case_id}"}), 404


# ===== P3: 统计页面路由 =====

@app.route("/stats")
def stats_page():
    """统计总览页：幻觉率/置信度分布、各案件评分一览"""
    from stats_aggregator import StatsAggregator
    agg = StatsAggregator()
    stats = agg.get_all_stats()
    for c in stats.get("cases", []):
        c["hallucination_pct"] = round(c["hallucination_rate"] * 100, 1)
        c["confidence_label"] = _confidence_label(c["average_confidence"])
    overall_hall = stats.get("average_hallucination_rate", 0)
    overall_conf = stats.get("average_confidence", 0)
    return render_template(
        "stats.html",
        stats=stats,
        overall_hall=round(overall_hall * 100, 1),
        overall_conf=round(overall_conf, 1),
        confidence_label=_confidence_label(overall_conf),
        hall_label=_hall_label(overall_hall),
    )


@app.route("/output/<path:filename>")
def serve_output(filename):
    """提供 output 目录下文件的下载"""
    safe_path = Path(OUTPUT_DIR) / filename
    if not safe_path.exists() or not safe_path.is_file():
        return "文件不存在", 404
    return send_file(safe_path, as_attachment=True, download_name=filename)


@app.route("/api/reports")
def api_reports():
    """报告列表 API（JSON）"""
    reports = []
    reports_dir = Path(OUTPUT_DIR)
    for subdir in (reports_dir / "defense_reports", reports_dir):
        if not subdir.exists():
            continue
        for f in sorted(subdir.iterdir(), key=lambda x: -x.stat().st_mtime):
            if f.suffix not in (".html", ".json"):
                continue
            is_defense = subdir.name == "defense_reports" or "defense" in f.stem.lower()
            case_match = re.search(r"CASE[-\w]+", f.stem)
            if not case_match:
                case_match = re.search(r"[\w]+罪", f.stem)
            label = case_match.group() if case_match else f.stem
            reports.append({
                "type": "辩护报告" if is_defense else "量刑报告",
                "case_id": label,
                "filename": f.name,
                "path": str(f),
                "size_kb": round(f.stat().st_size / 1024, 1),
                "time": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
            })
    return jsonify({"reports": reports, "total": len(reports)})


@app.route("/reports")
def reports_page():
    """已生成报告列表页面"""
    reports = []
    reports_dir = Path(OUTPUT_DIR)
    
    # 收集辩护报告
    defense_dir = reports_dir / "defense_reports"
    if defense_dir.exists():
        for f in sorted(defense_dir.iterdir(), key=lambda x: -x.stat().st_mtime):
            if f.suffix in (".html", ".json"):
                case_match = re.search(r"CASE[-\w]+", f.stem)
                case_id = case_match.group() if case_match else f.stem
                reports.append({
                    "type": "辩护报告",
                    "case_id": case_id,
                    "filename": f.name,
                    "path": str(f),
                    "size_kb": round(f.stat().st_size / 1024, 1),
                    "time": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                })
    
    # 收集量刑报告
    if reports_dir.exists():
        for f in sorted(reports_dir.iterdir(), key=lambda x: -x.stat().st_mtime):
            if f.suffix in (".html", ".json") and "sentencing" in f.stem.lower():
                case_match = re.search(r"[\w]+罪", f.stem) or re.search(r"\w+-\d+", f.stem)
                label = case_match.group() if case_match else f.stem
                reports.append({
                    "type": "量刑报告",
                    "case_id": label,
                    "filename": f.name,
                    "path": str(f),
                    "size_kb": round(f.stat().st_size / 1024, 1),
                    "time": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                })
    
    return render_template(
        "reports.html",
        reports=reports,
        username=session.get("username"),
    )


@app.route("/api/stats/overview")
def api_stats_overview():
    """案件统计概览 — 从真实案件数据聚合"""
    cases = loader.list_cases()
    provinces = {}
    crime_types = {}
    total_amount = 0
    amount_count = 0

    for c in cases:
        cid = c.get("case_id", c) if isinstance(c, dict) else c
        info = loader.get_case_info(cid)
        charges = loader.get_charges(cid)
        if info:
            prov = info.get("province", "未知")
            provinces[prov] = provinces.get(prov, 0) + 1
            crime = info.get("crime_type") or (charges.get("primary", {}).get("name") if charges else None) or "未知"
            crime_types[crime] = crime_types.get(crime, 0) + 1
            amt = info.get("amount", 0) or 0
            if amt > 0:
                total_amount += amt
                amount_count += 1
        elif charges:
            crime = charges.get("primary", {}).get("name", "未知")
            crime_types[crime] = crime_types.get(crime, 0) + 1

    avg_amount = total_amount / amount_count if amount_count else 0

    return jsonify({
        "total_cases": len(cases),
        "total_crimes": len(crime_types),
        "provinces": dict(sorted(provinces.items(), key=lambda x: -x[1])),
        "crime_types": dict(sorted(crime_types.items(), key=lambda x: -x[1])),
        "avg_amount_wan": round(avg_amount / 10000, 2),
        "total_amount_wan": round(total_amount / 10000, 2),
    })


@app.route("/api/stats/hallucination")
def api_hallucination():
    """幻觉率统计 JSON API"""
    from stats_aggregator import StatsAggregator
    agg = StatsAggregator()
    stats = agg.get_hallucination_stats()
    n = len(stats)
    return jsonify({
        "cases": [agg._stat_to_dict(s) for s in stats],
        "average_hallucination_rate": sum(s.hallucination_rate for s in stats) / n if n else 0,
        "average_confidence": sum(s.average_confidence for s in stats) / n if n else 0,
    })


@app.route("/api/fact-check/<case_id>")
def api_fact_check(case_id):
    """
    真实性核查 API
    
    对案件 YAML 各字段逐条核查来源等级，返回：
    - GRADE_A: 官方一手来源（判决原文/最高法官网）
    - GRADE_B: 可推断来源（根据官方数据合理推断）
    - GRADE_C: 推测来源（无官方依据，需警告）
    - GRADE_D: 完全未知（无任何依据）
    - GRADE_E: 已验证错误（必须修正）
    
    幻觉率 = (grade_c + grade_d + grade_e) / total_fields
    """
    from fact_checker import FactChecker
    try:
        fc = FactChecker(case_id)
        result = fc.check()
        total = result["total_fields"]
        c_count = result["grade_c"]
        d_count = result["grade_d"]
        e_count = result["grade_e"]
        hall_rate = round((c_count + d_count + e_count) / total, 4) if total else 0
        avg_conf = round((result["grade_a"] * 1.0 + result["grade_b"] * 0.7 + result["grade_c"] * 0.4 + result["grade_d"] * 0.1) / total, 2) if total else 0
        return jsonify({
            "case_id": case_id,
            "check_date": result["check_date"],
            "summary": {
                "total_fields": total,
                "grade_a": result["grade_a"],
                "grade_b": result["grade_b"],
                "grade_c": result["grade_c"],
                "grade_d": result["grade_d"],
                "grade_e": result["grade_e"],
                "hallucination_rate": hall_rate,
                "hallucination_pct": round(hall_rate * 100, 1),
                "average_confidence": avg_conf,
            },
            "fields": result["fields"],
            "issues": result["issues"],
            "average_confidence": avg_conf,
            "grade_labels": FactChecker.__module__ and {
                "GRADE_A": "✅ 官方一手来源（可引用）",
                "GRADE_B": "🔶 可推断来源（建议注明推断依据）",
                "GRADE_C": "⚠️ 推测来源（需在报告中标注）",
                "GRADE_D": "❓ 完全未知（建议删除或标注存疑）",
                "GRADE_E": "❌ 已验证错误（必须修正）",
            },
        })
    except FileNotFoundError:
        return jsonify({"error": f"案件不存在: {case_id}"}), 404
    except Exception as e:
        return jsonify({"error": f"核查失败: {e}"}), 500


@app.route("/api/stats/provincial-diffs")
def api_provincial_diffs():
    """省级差异数据 JSON API"""
    from stats_aggregator import StatsAggregator
    return jsonify(StatsAggregator().get_provincial_diffs())


@app.route("/api/stats/company-geo")
def api_company_geo():
    """涉案公司地域分布 JSON API"""
    from stats_aggregator import StatsAggregator
    return jsonify(StatsAggregator().get_company_geo_stats())


# ===== 辅助函数 =====

def _confidence_label(score: float) -> str:
    if score >= 80: return "高置信度"
    elif score >= 60: return "中等置信度"
    elif score >= 40: return "低置信度"
    else: return "不可靠"


def _hall_label(rate: float) -> str:
    if rate < 0.1: return "优秀"
    elif rate < 0.25: return "良好"
    elif rate < 0.5: return "需关注"
    else: return "严重"


# ===== P4: 辩护增强模块路由 =====

@app.route("/defense/<case_id>")
def defense_page(case_id):
    """辩护分析页面（支持文件案件和内置辩护案例）"""
    # 优先尝试文件型案件（CASE- 前缀）
    try:
        case_data = loader.load(case_id)
    except FileNotFoundError:
        case_data = None

    if case_data:
        has_file_case = True
    elif case_id.startswith("DEF-"):
        # 内置辩护案例库
        from defense_case_db import DefenseCaseDatabase
        db = DefenseCaseDatabase()
        bd = db.get_by_id(case_id)
        if bd:
            case_data = {
                "case_id": bd.case_id,
                "case_name": bd.case_name,
                "crime": bd.crime,
                "charges": {"charge1": {"name": bd.crime, "detail": bd.key_facts}},
                "key_facts": bd.key_facts,
                "summary": f"【{bd.outcome}】{bd.reasoning}",
                "is_builtin_defense": True,
            }
            has_file_case = False
        else:
            return render_template("defense.html", error=f"案件不存在: {case_id}", case_id=case_id)
    else:
        return render_template("defense.html", error=f"案件不存在: {case_id}", case_id=case_id)

    # 执行辩护分析
    from defense_enhancer import DefenseEnhancer
    enhancer = DefenseEnhancer()
    analysis = enhancer.analyze_case(case_data)

    # 检索类似案例
    from defense_case_db import DefenseCaseDatabase
    db = DefenseCaseDatabase()

    primary_defense = analysis.primary_defense.type.value if analysis.primary_defense else None
    charges = loader.get_charges(case_id) if has_file_case else {}
    crime = (list(charges.values())[0].get("name", "") if charges else case_data.get("crime", ""))

    if primary_defense:
        similar = db.search_by_defense(primary_defense, crime, limit=5)
    else:
        similar = db.search_by_crime(crime, "innocent", limit=5)

    return render_template(
        "defense.html",
        case_id=case_id,
        case_data=case_data,
        analysis=analysis.to_dict(),
        similar_cases=[c.to_dict() for c in similar.cases],
        similar_summary=similar.summary,
    )


@app.route("/api/defense/analyze", methods=["POST"])
def api_defense_analyze():
    """辩护分析 API - 分析提交的新案件"""
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "请提供案件数据"}), 400
    
    case_id = data.get("case_id", f"CASE-{datetime.now().strftime('%Y%m%d%H%M')}")
    
    # 优先尝试从案件库加载完整数据
    case_data = None
    if case_id:
        try:
            from case_loader import CaseLoader
            loader = CaseLoader()
            full_case = loader.load(case_id)
            if full_case:
                # 解析 case_info
                case_info_raw = full_case.get("case_info", "{}")
                if isinstance(case_info_raw, str):
                    import ast
                    case_info_raw = ast.literal_eval(case_info_raw) if case_info_raw else {}
                elif not isinstance(case_info_raw, dict):
                    case_info_raw = {}
                
                # 解析 charges
                charges_raw = full_case.get("charges", "{}")
                if isinstance(charges_raw, str):
                    charges_raw = ast.literal_eval(charges_raw) if charges_raw else {}
                elif not isinstance(charges_raw, dict):
                    charges_raw = {}
                
                # 解析 defendants_person
                defendants_raw = full_case.get("defendants_person", "[]")
                if isinstance(defendants_raw, str):
                    defendants_raw = ast.literal_eval(defendants_raw) if defendants_raw else []
                elif not isinstance(defendants_raw, list):
                    defendants_raw = []
                
                # 解析 mitigating_factors
                mitigating_raw = full_case.get("mitigating_factors", "[]")
                if isinstance(mitigating_raw, str):
                    mitigating_raw = ast.literal_eval(mitigating_raw) if mitigating_raw else []
                elif not isinstance(mitigating_raw, list):
                    mitigating_raw = []
                
                # 解析 legal_arguments
                legal_args_raw = full_case.get("legal_arguments", "[]")
                if isinstance(legal_args_raw, str):
                    legal_args_raw = ast.literal_eval(legal_args_raw) if legal_args_raw else []
                elif not isinstance(legal_args_raw, list):
                    legal_args_raw = []
                
                case_data = {
                    "case_id": case_id,
                    "case_name": full_case.get("meta", {}).get("case_name", case_id) if isinstance(full_case.get("meta"), dict) else case_id,
                    "case_summary": case_info_raw.get("description", ""),
                    "facts": {
                        "description": case_info_raw.get("description", ""),
                        "detail": " ".join(str(f) for f in mitigating_raw + legal_args_raw if f),
                    },
                    "defendants": [{"name": name} for name in defendants_raw] if defendants_raw else [{"name": data.get("defendant_name", "被告")}],
                    "charges": charges_raw if isinstance(charges_raw, dict) else {},
                    "mitigating_factors": mitigating_raw,
                    "legal_arguments": legal_args_raw,
                }
        except Exception as e:
            print(f"[辩护分析] 案件加载失败: {e}")
    
    # 如果加载失败或数据不足，用请求数据兜底
    charges_val = data.get("charges")
    if isinstance(charges_val, str):
        charges_val = {"primary": {"name": charges_val}}
    elif not isinstance(charges_val, dict):
        charges_val = {"primary": {"name": data.get("crime", "未知罪名")}}

    if not case_data or not case_data.get("case_summary"):
        case_data = {
            "case_id": case_id,
            "case_summary": data.get("case_summary") or data.get("facts", ""),
            "defendants": [{"name": data.get("defendant_name", "被告")}],
            "charges": charges_val,
        }
    
    # 执行分析
    from defense_enhancer import DefenseEnhancer
    enhancer = DefenseEnhancer()
    analysis = enhancer.analyze_case(case_data)
    
    # 检索类似案例
    from defense_case_db import DefenseCaseDatabase
    db = DefenseCaseDatabase()
    charges_dict = case_data.get("charges", {})
    if isinstance(charges_dict, str):
        crime = charges_dict
    else:
        crime = (charges_dict.get("primary", {}).get("name") or
                 data.get("crime", ""))
    similar = db.search_by_defense(
        analysis.primary_defense.type.value if analysis.primary_defense else "",
        crime, limit=5
    )
    
    primary = analysis.primary_defense
    secondary = analysis.secondary_defenses
    defense_angles = ([primary] + secondary) if primary else secondary

    return jsonify({
        "analysis": analysis.to_dict(),
        "defense_angles": [a.to_dict() for a in defense_angles],
        "similar_cases": [c.to_dict() for c in similar.cases],
    })


@app.route("/api/defense/opinion", methods=["POST"])
def api_defense_opinion():
    """辩护意见生成 API - 加载完整案件后生成辩护词"""
    data = request.get_json() or {}
    case_id = data.get("case_id", "")
    
    # 从案件库加载完整数据
    case_data = None
    if case_id:
        try:
            from case_loader import CaseLoader
            loader = CaseLoader()
            full_case = loader.load(case_id)
            if full_case:
                case_info_raw = full_case.get("case_info", {})
                if not isinstance(case_info_raw, dict):
                    case_info_raw = {}
                charges_raw = full_case.get("charges", {})
                if not isinstance(charges_raw, dict):
                    charges_raw = {}
                defendants_raw = full_case.get("defendants_person", [])
                if not isinstance(defendants_raw, list):
                    defendants_raw = []
                mitigating_raw = full_case.get("mitigating_factors", [])
                if not isinstance(mitigating_raw, list):
                    mitigating_raw = []
                legal_args_raw = full_case.get("legal_arguments", [])
                if not isinstance(legal_args_raw, list):
                    legal_args_raw = []
                meta_raw = full_case.get("meta", {})
                if not isinstance(meta_raw, dict):
                    meta_raw = {}
                
                case_data = {
                    "case_id": case_id,
                    "case_name": meta_raw.get("case_name", case_id),
                    "case_summary": case_info_raw.get("description", ""),
                    "facts": {
                        "description": case_info_raw.get("description", ""),
                        "detail": " ".join(str(f) for f in mitigating_raw + legal_args_raw),
                    },
                    "defendants": [{"name": n} for n in defendants_raw] if defendants_raw else [{"name": data.get("defendant_name", "被告")}],
                    "charges": charges_raw,
                    "mitigating_factors": mitigating_raw,
                    "legal_arguments": legal_args_raw,
                }
        except Exception as e:
            print(f"[辩护意见] 案件加载失败: {e}")
    
    # 兜底：至少保留请求参数
    if not case_data or not case_data.get("case_summary"):
        case_data = {
            "case_id": case_id or "unknown",
            "case_name": data.get("case_name", "未知案件"),
            "case_summary": data.get("facts", ""),
            "defendants": [{"name": data.get("defendant_name", "被告")}],
            "charges": {"primary": {"name": data.get("crime", "未知罪名")}},
        }
    
    # 运行辩护分析（获得 analysis 和 similar_cases）
    from defense_enhancer import DefenseEnhancer
    enhancer = DefenseEnhancer()
    analysis = enhancer.analyze_case(case_data)
    
    from defense_case_db import DefenseCaseDatabase
    db = DefenseCaseDatabase()
    crime = (case_data.get("charges", {}).get("primary", {}).get("name") or
              data.get("crime", ""))
    similar = db.search_by_defense(
        analysis.primary_defense.type.value if analysis.primary_defense else "",
        crime, limit=5
    )
    
    # 生成辩护意见
    from defense_opinion_generator import DefenseOpinionGenerator
    generator = DefenseOpinionGenerator(analysis.to_dict(), [c.to_dict() for c in similar.cases])
    opinion = generator.generate_full_opinion(case_data)
    
    return jsonify({
        "opinion": opinion.to_dict(),
        "markdown": opinion.to_markdown(),
        "analysis": analysis.to_dict(),
        "similar_cases": [c.to_dict() for c in similar.cases],
    })


@app.route("/api/defense/report", methods=["POST"])
def api_defense_report():
    """辩护报告生成 API - 支持只传 case_id"""
    data = request.get_json() or {}
    case_id = data.get("case_id", "")
    
    # 如果只传了 case_id，则加载完整案件数据
    case_data = data.get("case_data")
    defense_analysis = data.get("analysis", {})
    similar_cases = data.get("similar_cases", [])
    opinion_text = data.get("opinion", "")
    
    if not case_data and case_id:
        try:
            from case_loader import CaseLoader
            loader = CaseLoader()
            full_case = loader.load(case_id)
            if full_case:
                case_info_raw = full_case.get("case_info", {})
                if not isinstance(case_info_raw, dict):
                    case_info_raw = {}
                meta_raw = full_case.get("meta", {})
                if not isinstance(meta_raw, dict):
                    meta_raw = {}
                charges_raw = full_case.get("charges", {})
                if not isinstance(charges_raw, dict):
                    charges_raw = {}
                defendants_raw = full_case.get("defendants_person", [])
                if not isinstance(defendants_raw, list):
                    defendants_raw = []
                mitigating_raw = full_case.get("mitigating_factors", [])
                if not isinstance(mitigating_raw, list):
                    mitigating_raw = []
                legal_args_raw = full_case.get("legal_arguments", [])
                if not isinstance(legal_args_raw, list):
                    legal_args_raw = []
                
                case_data = {
                    "case_id": case_id,
                    "case_name": meta_raw.get("case_name", case_id),
                    "case_summary": case_info_raw.get("description", ""),
                    "facts": {
                        "description": case_info_raw.get("description", ""),
                        "detail": " ".join(str(f) for f in mitigating_raw + legal_args_raw),
                    },
                    "charges": charges_raw,
                    "defendants": [{"name": n} for n in defendants_raw] if defendants_raw else [],
                    "mitigating_factors": mitigating_raw,
                    "legal_arguments": legal_args_raw,
                }
                
                # 如果没有传入 analysis/similar_cases/opinion，也自动生成
                if not defense_analysis:
                    from defense_enhancer import DefenseEnhancer
                    enhancer = DefenseEnhancer()
                    defense_analysis = enhancer.analyze_case(case_data).to_dict()
                
                if not similar_cases:
                    from defense_case_db import DefenseCaseDatabase
                    db = DefenseCaseDatabase()
                    crime = (case_data.get("charges", {}).get("primary", {}).get("name") or "")
                    primary_def = defense_analysis.get("primary_defense", {})
                    similar = db.search_by_defense(primary_def.get("type", "") if primary_def else "", crime, limit=5)
                    similar_cases = [c.to_dict() for c in similar.cases]
                
                if not opinion_text:
                    from defense_opinion_generator import DefenseOpinionGenerator
                    gen = DefenseOpinionGenerator(defense_analysis, similar_cases)
                    opinion_text = gen.generate_full_opinion(case_data).to_markdown()
        except Exception as e:
            print(f"[辩护报告] 案件加载失败: {e}")
    
    if not case_data:
        return jsonify({"error": "缺少案件数据"}), 400
    
    from defense_report_builder import DefenseReportBuilder
    builder = DefenseReportBuilder()
    
    report = builder.build(
        case_data=case_data,
        defense_analysis=defense_analysis,
        similar_cases=similar_cases,
        opinion=opinion_text,
    )
    
    # 保存报告
    format_type = data.get("format", "html")
    if format_type == "html":
        filepath = builder.save_html(report)
    elif format_type == "json":
        filepath = builder.save_json(report)
    elif format_type == "pdf":
        from defense_report_builder import save_defense_report_pdf
        filepath = save_defense_report_pdf(report)
    else:
        filepath = builder.save_markdown(report)
    
    return jsonify({
        "success": True,
        "report_path": str(filepath),
        "download_url": f"/download/{Path(filepath).name}",
        "content": report.get("content", "") if isinstance(report, dict) else str(report)[:2000],
    })


@app.route("/api/defense/search", methods=["GET"])
def api_defense_search():
    """辩护案例检索 API"""
    q = request.args.get("q", "").strip()
    crime = request.args.get("crime", q).strip()  # 兼容 q= 参数
    defense_type = request.args.get("defense_type", "")
    limit = int(request.args.get("limit", 10))
    
    from defense_case_db import DefenseCaseDatabase
    db = DefenseCaseDatabase()
    
    if defense_type:
        result = db.search_by_defense(defense_type, crime, limit)
    elif crime:
        result = db.search_by_crime(crime, "innocent", limit)
    else:
        return jsonify({"error": "请提供罪名或辩护类型"}), 400
    
    return jsonify({
        "cases": [c.to_dict() for c in result.cases],
        "total": result.total,
        "summary": result.summary,
    })


# ===== P5: 量刑一致性分析路由 =====

@app.route("/sentencing")
def sentencing_page():
    """量刑一致性分析页面"""
    from sentencing_consistency import SentencingConsistencyAnalyzer
    analyzer = SentencingConsistencyAnalyzer()
    report = analyzer.generate_report()
    
    # 准备图表数据
    crime_stats = []
    for crime, stats in report.get("crime_stats", {}).items():
        if stats.get("avg_sentence"):
            crime_stats.append({
                "crime": crime,
                "avg": stats["avg_sentence"],
                "median": stats.get("median_sentence"),
                "count": stats["sample_count"],
                "probation_rate": stats.get("probation_rate", 0),
                "distribution": stats.get("distribution", {}),
            })
    
    return render_template(
        "sentencing.html",
        report=report,
        crime_stats=crime_stats,
    )


@app.route("/sentencing/<crime>")
def sentencing_crime_page(crime):
    """特定罪名量刑分析页面"""
    from sentencing_consistency import SentencingConsistencyAnalyzer
    analyzer = SentencingConsistencyAnalyzer()
    
    stats = analyzer.get_stats_by_crime(crime)
    comparison = analyzer.get_provincial_comparison(crime)
    legal_comp = analyzer.get_legal_comparison(crime)
    
    # 排序省份数据
    sorted_provinces = sorted(
        comparison.items(),
        key=lambda x: x[1]["avg_sentence"]
    ) if comparison else []
    
    return render_template(
        "sentencing_crime.html",
        crime=crime,
        stats=stats,
        comparison=comparison,
        sorted_provinces=sorted_provinces,
        legal_comp=legal_comp,
    )


@app.route("/api/sentencing/report")
def api_sentencing_report():
    """量刑一致性报告 API"""
    crime = request.args.get("crime", None)
    
    from sentencing_consistency import SentencingConsistencyAnalyzer
    analyzer = SentencingConsistencyAnalyzer()
    report = analyzer.generate_report(crime)
    
    return jsonify(report)


@app.route("/api/sentencing/deviation", methods=["POST"])
def api_sentencing_deviation():
    """个案偏离度分析 API"""
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "请提供案件数据"}), 400
    
    from sentencing_consistency import SentencingConsistencyAnalyzer
    analyzer = SentencingConsistencyAnalyzer()
    result = analyzer.analyze_deviation(data)
    
    return jsonify({
        "case_id": result.case_id,
        "crime": result.crime,
        "deviation_score": result.deviation_score,
        "deviation_type": result.deviation_type,
        "expected_sentence": result.expected_sentence,
        "actual_sentence": result.actual_sentence,
        "factors": result.factors,
        "deviation_reasons": result.deviation_reasons,
        "similar_cases": result.similar_cases,
        "recommendation": result.recommendation,
    })


@app.route("/api/sentencing/provincial")
def api_sentencing_provincial():
    """省份量刑对比 API"""
    crime = request.args.get("crime", None)
    
    from sentencing_consistency import SentencingConsistencyAnalyzer
    analyzer = SentencingConsistencyAnalyzer()
    comparison = analyzer.get_provincial_comparison(crime)
    
    return jsonify(comparison)


# ── 入罪门槛 ───────────────────────────────────────────────

@app.route("/threshold")
def threshold_page():
    """入罪门槛对比页面"""
    crime = request.args.get("crime", "盗窃罪")
    from threshold_api import CRIME_THRESHOLDS, CRIME_LABELS
    thresholds = CRIME_THRESHOLDS.get(crime, {})
    rows = []
    for province, data in thresholds.items():
        threshold = data.get("low", 0)
        rows.append({
            "province": province,
            "threshold_yuan": threshold,
            "threshold_wan": round(threshold / 10000, 2),
            "standard": data.get("standard", ""),
        })
    rows.sort(key=lambda x: x["threshold_yuan"])
    return render_template(
        "threshold.html",
        crime=crime,
        crime_label=CRIME_LABELS.get(crime, crime),
        rows=rows,
        available_crimes=list(CRIME_THRESHOLDS.keys()),
    )


@app.route("/api/threshold")
def api_threshold():
    """入罪门槛 API

    GET /api/threshold?crime=盗窃罪              → 所有省份
    GET /api/threshold?crime=盗窃罪&province=北京  → 单一省份
    GET /api/threshold?crime=盗窃罪&amount=5000   → 判断是否入罪
    """
    crime = request.args.get("crime", "盗窃罪")
    province = request.args.get("province", "").strip()
    amount = request.args.get("amount", type=float, default=0)

    from threshold_api import CRIME_THRESHOLDS, CRIME_LEGAL_BASIS
    if crime not in CRIME_THRESHOLDS:
        return jsonify({"error": f"暂不支持该罪名: {crime}（支持：盗窃罪/诈骗罪/抢夺罪/开设赌场罪）"}), 404

    thresholds = CRIME_THRESHOLDS.get(crime, {})
    legal_basis = CRIME_LEGAL_BASIS.get(crime, "")

    def _get_threshold(data: dict):
        """从数据字典中提取入罪门槛金额（新旧结构兼容）"""
        if isinstance(data, dict):
            return data.get("low") or data.get("amount_standard") or 0
        return 0

    def _is_text_data(data: dict):
        """判断是否为文字描述类数据（如交通肇事罪）"""
        if not isinstance(data, dict):
            return False
        return "death1_flee" in data or "death1_serious" in data

    if province:
        data = thresholds.get(province, {})
        if not data:
            return jsonify({"error": f"未找到省份: {province}"}), 404

        if _is_text_data(data):
            return jsonify({
                "province": province,
                "crime": crime,
                "threshold_yuan": 0,
                "is_text_based": True,
                "description": data,
                "legal_basis": legal_basis,
            })

        threshold = _get_threshold(data)
        return jsonify({
            "province": province,
            "crime": crime,
            "threshold_yuan": threshold,
            "threshold_wan": round(threshold / 10000, 2),
            "standard": data.get("standard", ""),
            "legal_basis": legal_basis,
            "reached": amount > 0 and amount >= threshold if amount else None,
        })

    rows = []
    for p, data in thresholds.items():
        if _is_text_data(data):
            rows.append({
                "province": p,
                "threshold_yuan": 0,
                "threshold_wan": 0,
                "is_text_based": True,
                "description": data,
                "legal_basis": legal_basis,
            })
            continue

        threshold = _get_threshold(data)
        reached = None
        if amount > 0:
            reached = amount >= threshold
        rows.append({
            "province": p,
            "threshold_yuan": threshold,
            "threshold_wan": round(threshold / 10000, 2),
            "standard": data.get("standard", ""),
            "reached": reached,
            "legal_basis": legal_basis,
        })

    # 数值类按门槛排序，文字类放最后
    text_rows = [r for r in rows if r.get("is_text_based")]
    num_rows = sorted([r for r in rows if not r.get("is_text_based")],
                      key=lambda x: x["threshold_yuan"])
    return jsonify({
        "crime": crime,
        "amount": amount,
        "count": len(rows),
        "rows": num_rows + text_rows,
    })


# ---- 运行 ----

if __name__ == "__main__":
    """
    生产级启动入口（优先使用 gunicorn/waitress，不建议直接运行此文件）

    推荐启动方式：
      gunicorn (Linux):  gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 'src.web_app:app'
      waitress (通用):   waitress-serve --port 5000 --threads 8 src.web_app:app
      开发调试:          python src/web_app.py

    ⚠️ 直接运行 python src/web_app.py 使用 Flask 内置服务器（不安全），仅适合开发调试。
    """
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    case_count = len(loader.list_cases())

    if not debug:
        print("=" * 60)
        print("⚠️  警告：直接运行本文件使用 Flask 内置服务器（不安全）")
        print("   生产环境请使用：")
        print(f"   gunicorn -w 4 -b 0.0.0.0:{port} --timeout 120 'src.web_app:app'")
        print(f"   或 waitress-serve --port {port} --threads 8 src.web_app:app")
        print("=" * 60)

    logger.info(f"🚀 追诉系统启动: http://localhost:{port}，调试模式: {debug}，案件数量: {case_count}")
    print(f"🚀 追诉系统启动: http://localhost:{port}")
    print(f"   调试模式: {debug}")
    print(f"   案件数量: {case_count}")
    app.run(host="0.0.0.0", port=port, debug=debug)

# ---- 健康检查与监控 ----

@app.route("/health")
def health_check():
    """健康检查端点"""
    from health import HealthChecker, MetricsCollector
    health = HealthChecker.check()
    metrics = MetricsCollector.get_metrics()
    return jsonify({
        "health": health,
        "metrics": metrics,
    })

@app.route("/health/live")
def health_live():
    """存活探针"""
    return jsonify({"status": "alive"})

@app.route("/health/ready")
def health_ready():
    """就绪探针"""
    from health import HealthChecker
    health = HealthChecker.check()
    if health['checks']['database']['status'] == 'ok':
        return jsonify({"status": "ready"})
    return jsonify({"status": "not ready", "reason": "database unavailable"}), 503

@app.route("/metrics")
def metrics():
    """Prometheus格式指标"""
    from health import MetricsCollector
    m = MetricsCollector.get_metrics()
    lines = [
        "# HELP prosecution_requests_total Total requests",
        "# TYPE prosecution_requests_total counter",
        f"prosecution_requests_total {m['total_requests']}",
        "# HELP prosecution_errors_total Total errors",
        "# TYPE prosecution_errors_total counter",
        f"prosecution_errors_total {m['total_errors']}",
        "# HELP prosecution_response_time_seconds Average response time",
        "# TYPE prosecution_response_time_seconds gauge",
        f"prosecution_response_time_seconds {m['avg_response_time']:.3f}",
        "# HELP prosecution_uptime_seconds Uptime in seconds",
        "# TYPE prosecution_uptime_seconds counter",
        f"prosecution_uptime_seconds {m['uptime_seconds']}",
    ]
    return '\n'.join(lines), 200, {"Content-Type": "text/plain"}

# ── 联合案件分析 API ────────────────────────────────────────

def _do_case_analyze(data: dict, case_full: dict = None) -> dict:
    """
    联合案件分析核心逻辑（供 POST 和 GET 共同调用）
    """
    crime = data.get("crime_type") or data.get("crime") or data.get("charges")
    if not crime:
        raise ValueError("缺少 crime_type 字段")

    # 合并：外部参数优先，其次从完整案件提取
    def _v(key, default=None):
        return data.get(key) if data.get(key) is not None else (
            (case_full or {}).get("case_info", {}).get(key, default)
            if case_full else default
        )

    amount = float(_v("amount") or 0)
    province = _v("province", "全国")
    is_company = _v("is_company", False)
    court_level = _v("court_level", "")
    keyword = _v("keyword", "")
    sent_years = float(_v("sentencing_years") or _v("sentence_years") or 0)

    # 1. 入罪门槛判定
    from threshold_api import list_thresholds
    thresh_result = None
    if amount > 0:
        thresh_list = list_thresholds(crime=crime, amount=amount)
        if thresh_list.get("thresholds"):
            matched = [t for t in thresh_list["thresholds"]
                       if t.get("province") == province or t.get("province") == "DEFAULT"]
            thresh_result = matched[0] if matched else thresh_list["thresholds"][0]

    # 2. 量刑预测（基于类案统计）
    from sentencing_consistency import SentencingConsistencyAnalyzer
    sca = SentencingConsistencyAnalyzer()
    legal_comp = sca.get_legal_comparison(crime)
    legal_range = legal_comp.get("legal_range", {})
    actual_stats = legal_comp.get("actual_stats", {})

    # 3. 量刑偏离分析（若提供了实际量刑）
    deviation_result = None
    if sent_years > 0 and case_full:
        dev_data = {
            "crime": crime,
            "sentence_years": sent_years,
            "province": province,
            "case_id": data.get("case_id", "unknown"),
            "is_自首": _v("自首", False),
            "is_立功": _v("立功", False),
            "is_坦白": _v("坦白", False),
            "is_赔偿": _v("赔偿", False),
            "is_谅解": _v("谅解", False),
            "is_累犯": _v("累犯", False),
            "is_初犯": _v("初犯", True),
        }
        dev = sca.analyze_deviation(dev_data)
        deviation_result = {
            "deviation_score": dev.deviation_score,
            "deviation_type": dev.deviation_type,
            "expected_sentence": dev.expected_sentence,
            "actual_sentence": dev.actual_sentence,
            "factors": dev.factors,
            "reasons": dev.deviation_reasons,
        }

    # 4. 类案搜索
    from legal_case_db import LegalCaseDB
    lcdb = LegalCaseDB()
    similar_raw = lcdb.search_similar(
        crime_name=crime,
        amount=amount,
        is_company=is_company,
        court_level=court_level,
        keyword=keyword,
        top_k=5,
    )
    similar_cases = []
    for sc in similar_raw:
        case = sc.case
        similar_cases.append({
            "case_id": case.case_id,
            "court": case.court,
            "judgment_date": case.judgment_date,
            "crime_type": case.crime_name,
            "amount": case.amount,
            "sentence": case.sentence,
            "sentence_months": case.sentence_months,
            "similarity_score": round(sc.similarity_score, 2),
            "match_reasons": sc.match_reasons,
            "amount_comparison": sc.amount_comparison,
            "sentence_comparison": sc.sentence_comparison,
            "key_facts": case.key_facts[:100],
        })

    # 5. 辩护分析
    from defense_enhancer import DefenseEnhancer
    de = DefenseEnhancer()
    defense_result = None
    if case_full:
        da = de.analyze_case(case_full)
        defense_result = {
            "primary_defense": {
                "type": da.primary_defense.type.value,
                "confidence": da.primary_defense.confidence,
                "legal_references": da.primary_defense.legal_references,
                "evidence_points": da.primary_defense.evidence_points,
                "risk_mitigation": da.primary_defense.risk_mitigation,
                "recommendation": da.primary_defense.recommendation,
            },
            "secondary_defenses": [
                {
                    "type": s.type.value,
                    "confidence": s.confidence,
                    "legal_references": s.legal_references,
                    "evidence_points": s.evidence_points,
                    "risk_mitigation": s.risk_mitigation,
                    "recommendation": s.recommendation,
                }
                for s in da.secondary_defenses
            ],
            "overall_strength": da.overall_strength,
            "recommended_strategy": da.recommended_strategy,
            "estimated_outcome": da.estimated_outcome,
        }
    else:
        factors = []
        if _v("自首", False): factors.append("自首")
        if _v("立功", False): factors.append("立功")
        if _v("坦白", False): factors.append("坦白/认罪认罚")
        if _v("赔偿", False) or _v("谅解", False): factors.append("赔偿谅解")
        if _v("初犯", False): factors.append("初犯/偶犯")
        if _v("累犯", False): factors.append("累犯（从重）")
        defense_result = {
            "primary_defense": {"type": "依参数构造", "confidence": "中",
                                "description": f"有利因素: {', '.join(factors) or '无明显有利因素'}"},
            "secondary_defenses": [],
            "overall_strength": 50 + (10 * len(factors)) if factors else 50,
            "recommended_strategy": "建议争取从轻情节，参考类似案件量刑",
            "estimated_outcome": "量刑区间内从轻处理",
        }

    # 6. 法律依据检索
    rag = get_rag()
    law_results = rag.search(crime, top_k=3)
    legal_basis = [
        {
            "title": r.get("title", "")[:80],
            "law": r.get("law", ""),
            "article": r.get("article", ""),
            "preview": r.get("preview", "")[:120],
            "bm25_score": r.get("bm25_score", 0),
        }
        for r in law_results
    ]

    return {
        "case_id": data.get("case_id", "new"),
        "crime_type": crime,
        "amount": amount,
        "province": province,
        "is_company": is_company,
        "threshold": thresh_result,
        "sentencing_prediction": {
            "legal_range": legal_range,
            "actual_stats": actual_stats,
            "sample_count": legal_comp.get("sample_count", 0),
            "prediction_note": f"法条量刑区间 {legal_range.get('min',0)}-{legal_range.get('max',0)} "
                               f"{legal_range.get('unit','年')}；类案均值 {actual_stats.get('avg','?')}年，"
                               f"中位数 {actual_stats.get('median','?')}年",
        },
        "deviation": deviation_result,
        "similar_cases": similar_cases,
        "defense": defense_result,
        "legal_basis": legal_basis,
    }


@app.route("/api/case-analyze", methods=["POST"])
def api_case_analyze():
    """联合案件分析 API（POST 方式）"""
    data = request.get_json() or {}
    crime = data.get("crime_type") or data.get("crime") or data.get("charges")
    if not crime:
        return jsonify({"error": "缺少 crime_type 字段"}), 400

    loader = CaseLoader()
    case_full = None
    if data.get("case_id"):
        try:
            case_full = loader.load(data["case_id"])
        except Exception:
            pass

    try:
        return jsonify(_do_case_analyze(data, case_full))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/case-analyze")
def case_analyze_page():
    """联合案件分析前端页面"""
    return render_template("case_analyze.html")


@app.route("/api/case-analyze/<case_id>")
def api_case_analyze_get(case_id):
    """联合案件分析 API（GET 方式：从已有案件 ID 分析）"""
    try:
        loader = CaseLoader()
        case_full = loader.load(case_id)
    except Exception:
        return jsonify({"error": f"案件不存在: {case_id}"}), 404

    ci = (case_full or {}).get("case_info", {}) or {}
    fake_data = {
        "case_id": case_id,
        "crime_type": ci.get("crime_type", ""),
        "amount": ci.get("amount") or ci.get("涉案金额", 0),
        "province": ci.get("province", "全国"),
        "sentencing_years": ci.get("sentence_years") or ci.get("sentencing_years", 0),
        "is_company": ci.get("is_company", False),
        "自首": ci.get("is_自首", False),
        "立功": ci.get("is_立功", False),
        "坦白": ci.get("is_坦白", False),
        "赔偿": ci.get("is_赔偿", False),
        "谅解": ci.get("is_谅解", False),
        "累犯": ci.get("is_累犯", False),
        "初犯": ci.get("is_初犯", True),
    }
    return jsonify(_do_case_analyze(fake_data, case_full))


# ── PDF 辩护意见书导出 ──────────────────────────────────────

@app.route("/api/case-analyze/<case_id>/pdf")
def api_case_analyze_pdf(case_id):
    """从联合分析结果直接生成辩护 PDF"""
    # 先执行联合分析
    try:
        loader = CaseLoader()
        case_full = loader.load(case_id)
    except Exception:
        return jsonify({"error": f"案件不存在: {case_id}"}), 404

    ci = (case_full or {}).get("case_info", {}) or {}
    fake_data = {
        "case_id": case_id,
        "crime_type": ci.get("crime_type", ""),
        "amount": ci.get("amount") or ci.get("涉案金额", 0),
        "province": ci.get("province", "全国"),
        "sentencing_years": ci.get("sentence_years") or ci.get("sentencing_years", 0),
        "is_company": ci.get("is_company", False),
        "自首": ci.get("is_自首", False),
        "立功": ci.get("is_立功", False),
        "坦白": ci.get("is_坦白", False),
        "赔偿": ci.get("is_赔偿", False),
        "谅解": ci.get("is_谅解", False),
        "累犯": ci.get("is_累犯", False),
        "初犯": ci.get("is_初犯", True),
    }
    analysis = _do_case_analyze(fake_data, case_full)

    # 生成辩护角度 dict（用于 DefenseReportBuilder）
    defense_data = analysis.get("defense", {})
    primary = defense_data.get("primary_defense", {})
    secondary = defense_data.get("secondary_defenses", [])
    defense_angles = [primary] + secondary

    # 生成意见文本
    opinion_parts = []
    pd = primary.get("recommendation", "")
    if pd:
        opinion_parts.append(f"主要辩护策略：{pd}")
    sp = analysis.get("sentencing_prediction", {})
    if sp.get("prediction_note"):
        opinion_parts.append(f"量刑预测：{sp['prediction_note']}")
    dev = analysis.get("deviation", {})
    if dev:
        opinion_parts.append(f"量刑偏离分析：{dev.get('deviation_type','?')}（偏离分{dev.get('deviation_score','?')}），"
                             f"合理区间{dev.get('expected_sentence','?')}")
    sc_list = analysis.get("similar_cases", [])
    if sc_list:
        opinion_parts.append(f"参考类案{len(sc_list)}件，最高量刑{sc_list[0].get('sentence','?')}，"
                             f"最低量刑{sc_list[-1].get('sentence','?')}。")
    opinion_text = "\n\n".join(opinion_parts)

    # 构建 report
    from defense_report_builder import DefenseReportBuilderPDF, DefenseReport
    meta = (case_full or {}).get("meta", {}) or {}
    output_dir = Path(__file__).parent.parent / "output" / "defense_reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    report = DefenseReport(
        case_id=case_id,
        case_name=meta.get("case_name", ci.get("case_name", case_id)),
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        analysis_summary=(
            f"罪名：{analysis['crime_type']}；涉案金额：{analysis['amount']:.0f}元（{analysis['province']}）；"
            f"入罪判定：{'已达到入罪标准' if analysis.get('threshold',{}).get('reached') else '未达入罪标准'}；"
            f"辩护强度：{defense_data.get('overall_strength','?')}/100"
        ),
        defense_angles=defense_angles,
        similar_cases=sc_list,
        opinion_text=opinion_text,
        overall_strength=defense_data.get("overall_strength", 50),
        recommendation=defense_data.get("recommended_strategy", ""),
    )

    pdf_path = DefenseReportBuilderPDF(output_dir=output_dir).save_pdf(report)
    return send_file(pdf_path, as_attachment=True,
                     download_name=f"辩护意见书_{case_id}_{datetime.now().strftime('%Y%m%d')}.pdf")

@app.route("/api/case-analyze/new/pdf")
def api_case_analyze_new_pdf():
    """
    对新建案件直接生成辩护 PDF（GET 参数）
    ?crime_type=盗窃罪&amount=15000&province=上海
    """
    crime_type = request.args.get("crime_type", "")
    amount = float(request.args.get("amount") or 0)
    province = request.args.get("province", "全国")
    court_level = request.args.get("court_level") or None
    keyword = request.args.get("keyword") or None

    case_data = {
        "case_id": "NEW-" + datetime.now().strftime("%Y%m%d%H%M"),
        "crime_type": crime_type,
        "amount": amount,
        "province": province,
        "court_level": court_level,
        "keyword": keyword,
        "is_company": False,
        "自首": False, "立功": False, "坦白": False,
        "赔偿": False, "谅解": False, "累犯": False, "初犯": True,
    }
    for k in ["自首","立功","坦白","赔偿","谅解","认罪认罚","累犯","初犯","从犯","预备"]:
        v = request.args.get(k)
        if v is not None:
            case_data[k] = str(v).lower() in ("1","true","yes")

    actual = request.args.get("sentencing_years") or request.args.get("actual_sentencing")
    if actual:
        case_data["sentencing_years"] = float(actual)

    analysis = _do_case_analyze(case_data, None)

    from defense_report_builder import DefenseReportBuilderPDF, DefenseReport

    defense_data = analysis.get("defense", {})
    primary = defense_data.get("primary_defense", {})
    secondary = defense_data.get("secondary_defenses", []) or []
    defense_angles = [primary] + secondary

    sc_list = list(analysis.get("similar_cases", [])[:8])

    opinion_lines = []
    if primary:
        conf = primary.get("confidence", "?")
        opinion_lines.append("主要辩护策略：" + (primary.get("type","待定")) + "（匹配度 " + str(conf) + "%）")
        if primary.get("recommendation"):
            opinion_lines.append("具体建议：" + primary["recommendation"])
    for d in secondary:
        opinion_lines.append("次要策略：" + (d.get("type","待定")) + "（匹配度 " + str(d.get("confidence","?")) + "%）")
    opinion_text = "\n".join(opinion_lines)

    output_dir = Path(__file__).parent.parent / "output" / "defense_reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    reached = analysis.get("threshold", {}).get("reached")
    verdict = "已达到入罪标准" if reached else "未达入罪标准"
    strength = defense_data.get("overall_strength", "?")
    summary = ("罪名：" + crime_type + "；涉案金额：" + str(int(amount)) + "元（" + province + "）；"
               + "入罪判定：" + verdict + "；辩护强度：" + str(strength) + "/100")
    report = DefenseReport(
        case_id=case_data["case_id"],
        case_name=province + " " + crime_type + "（新建）",
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        analysis_summary=summary,
        defense_angles=defense_angles,
        similar_cases=sc_list,
        opinion_text=opinion_text,
        overall_strength=strength if isinstance(strength, (int,float)) else 50,
        recommendation=defense_data.get("recommended_strategy", ""),
    )
    pdf_path = DefenseReportBuilderPDF(output_dir=output_dir).save_pdf(report)
    return send_file(pdf_path, as_attachment=True,
                     download_name="辩护意见书_" + crime_type + "_" + datetime.now().strftime("%Y%m%d") + ".pdf")
