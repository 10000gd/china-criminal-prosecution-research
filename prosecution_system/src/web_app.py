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
app = Flask(__name__, template_folder=str(PROJECT_ROOT / "templates"))
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
_rag_instance = None

def get_rag():
    global _rag_instance
    if _rag_instance is None:
        from law_rag import LawRAG
        _rag_instance = LawRAG(enable_vector=True)
    return _rag_instance

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
    """API文档页面"""
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


# ---- 案件对比 ----

from case_comparison import CaseComparator, compare_cases

@app.route("/compare")
def compare_page():
    """案件对比页面"""
    case_ids = request.args.getlist("case_id")
    if len(case_ids) < 2:
        return render_template("compare.html", error="请选择至少2个案件进行对比", cases=[])
    
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
@login_required
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
    """辩护分析页面"""
    case_data = loader.load(case_id)
    if not case_data:
        return render_template("defense.html", error=f"案件不存在: {case_id}", case_id=case_id)
    
    # 执行辩护分析
    from defense_enhancer import DefenseEnhancer
    enhancer = DefenseEnhancer()
    analysis = enhancer.analyze_case(case_data)
    
    # 检索类似案例
    from defense_case_db import DefenseCaseDatabase
    db = DefenseCaseDatabase()
    
    # 获取主要辩护类型和罪名
    primary_defense = analysis.primary_defense.type.value if analysis.primary_defense else None
    charges = loader.get_charges(case_id)
    crime = (list(charges.values())[0].get("name", "") if charges else "")
    
    # 检索类似案例
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
    if not case_data or not case_data.get("case_summary"):
        case_data = {
            "case_id": case_id,
            "case_summary": data.get("facts", ""),
            "defendants": [{"name": data.get("defendant_name", "被告")}],
            "charges": {"primary": {"name": data.get("crime", "未知罪名")}},
        }
    
    # 执行分析
    from defense_enhancer import DefenseEnhancer
    enhancer = DefenseEnhancer()
    analysis = enhancer.analyze_case(case_data)
    
    # 检索类似案例
    from defense_case_db import DefenseCaseDatabase
    db = DefenseCaseDatabase()
    crime = (case_data.get("charges", {}).get("primary", {}).get("name") or 
             data.get("crime", ""))
    similar = db.search_by_defense(
        analysis.primary_defense.type.value if analysis.primary_defense else "", 
        crime, limit=5
    )
    
    return jsonify({
        "analysis": analysis.to_dict(),
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
    else:
        filepath = builder.save_markdown(report)
    
    return jsonify({
        "success": True,
        "report_path": str(filepath),
        "download_url": f"/download/{Path(filepath).name}",
    })


@app.route("/api/defense/search", methods=["GET"])
def api_defense_search():
    """辩护案例检索 API"""
    crime = request.args.get("crime", "")
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
    thresholds = CRIME_THRESHOLDS.get(crime, {})
    legal_basis = CRIME_LEGAL_BASIS.get(crime, "")

    if province:
        data = thresholds.get(province, {})
        if not data:
            return jsonify({"error": f"未找到省份: {province}"}), 404
        threshold = data.get("low", 0)
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
        threshold = data.get("low", 0)
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
    rows.sort(key=lambda x: x["threshold_yuan"])
    return jsonify({
        "crime": crime,
        "amount": amount,
        "count": len(rows),
        "rows": rows,
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
