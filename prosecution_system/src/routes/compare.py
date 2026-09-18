# -*- coding: utf-8 -*-
"""对比路由"""
from flask import Blueprint, request, jsonify, render_template
from shared.singletons import loader, get_pdf_exporter
from case_comparison import CaseComparator, compare_cases_standalone

compare_bp = Blueprint('compare', __name__, url_prefix='/api')


@compare_bp.route("/compare", methods=["POST"])
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
    result = compare_cases_standalone(case_ids, cases_data)

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


@compare_bp.route("/compare", methods=["GET"])
def api_compare_get():
    """案件对比 API(GET 方式,兼容 ids= 参数)"""
    ids_param = request.args.get("ids", "")
    case_ids = [x.strip() for x in ids_param.split(",") if x.strip()]
    if len(case_ids) < 2:
        return jsonify({"error": "至少需要2个案件,用逗号分隔,如 ?ids=CASE-0001,CASE-0002"}), 400
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
    result = compare_cases_standalone(case_ids, cases_data)
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


# ---- 页面路由 ----

compare_page_bp = Blueprint('compare_page', __name__, url_prefix='')


@compare_page_bp.route("/compare")
def compare_page():
    """案件对比页面"""
    case_ids = request.args.getlist("case_id")
    if len(case_ids) < 2:
        return render_template("compare.html", comparison=None, case_ids=[])

    cases_data = []
    for case_id in case_ids:
        try:
            data = loader.load(case_id)
            cases_data.append(data)
        except FileNotFoundError:
            return f"案件不存在: {case_id}", 404

    comparator = CaseComparator()
    result = compare_cases_standalone(case_ids, cases_data)

    return render_template("compare.html",
                           comparison=result,
                           case_ids=case_ids)
