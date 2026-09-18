# -*- coding: utf-8 -*-
"""案件路由"""
from flask import Blueprint, request, jsonify, render_template, session, g, send_file, redirect, url_for
from shared.middleware import rate_limit, csrf_protect, get_rag
from shared.singletons import loader, get_report_builder, get_pdf_exporter
from shared.constants import OUTPUT_DIR, DATA_DIR
from auth import login_required, get_current_user
from wenshu_updater import CaseTracker
from datetime import datetime
import re

cases_bp = Blueprint('cases', __name__, url_prefix='')


@cases_bp.route("/case/<case_id>")
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


# ---- API 接口 ----

@cases_bp.route("/api/cases")
def api_cases():
    """案件列表 API"""
    status = request.args.get("status", "")
    cases = loader.list_cases(status=status if status else None)
    return jsonify({"cases": cases, "total": len(cases)})


@cases_bp.route("/api/case/<case_id>")
def api_case(case_id):
    """案件详情 API"""
    try:
        data = loader.load(case_id)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({"error": f"案件未找到: {case_id}"}), 404


@cases_bp.route("/api/cases/<case_id>")
def api_case_alias(case_id):
    """案件详情 API(兼容 /api/cases/<id> 路径)"""
    return api_case(case_id)


@cases_bp.route("/api/case/<case_id>/charges")
def api_charges(case_id):
    """罪名分析 API"""
    try:
        charges = loader.get_charges(case_id)
        return jsonify(charges)
    except FileNotFoundError:
        return jsonify({"error": f"案件未找到: {case_id}"}), 404


# ---- 报告生成 ----

@cases_bp.route("/case/<case_id>/generate", methods=["GET", "POST"])
def generate_report(case_id):
    """生成报告 - GET/POST"""
    try:
        loader.load(case_id)
    except FileNotFoundError:
        return jsonify({"error": f"案件未找到: {case_id}"}), 404

    if request.method == "POST":
        try:
            builder = get_report_builder()
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

    # GET: 重定向到辩护分析页
    return redirect(f"/defense/{case_id}")
