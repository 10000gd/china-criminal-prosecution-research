# -*- coding: utf-8 -*-
"""导出路由"""
from flask import Blueprint, request, jsonify, send_file
from shared.singletons import loader, get_pdf_exporter
from shared.constants import OUTPUT_DIR
from auth import login_required
from case_comparison import CaseComparator, compare_cases_standalone
from pathlib import Path

export_bp = Blueprint('export', __name__, url_prefix='')


@export_bp.route("/download/")
def download(filename):
    """下载生成的报告"""
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        return "文件未找到", 404
    return send_file(file_path, as_attachment=True)


@export_bp.route("/output/<path:filename>")
def serve_output(filename):
    """提供 output 目录下文件的下载"""
    safe_path = OUTPUT_DIR / filename
    if not safe_path.exists() or not safe_path.is_file():
        return "文件不存在", 404
    return send_file(safe_path, as_attachment=True, download_name=filename)


@export_bp.route("/export/case/<case_id>")
@login_required
def export_case_pdf(case_id):
    """导出案件为PDF(HTML格式)"""
    try:
        case_data = loader.load(case_id)
    except FileNotFoundError:
        return f"案件不存在: {case_id}", 404

    exporter = get_pdf_exporter()
    output_path = exporter.export_case_to_html(case_data)

    return send_file(output_path, as_attachment=True, download_name=f"{case_id}_report.html")


@export_bp.route("/export/comparison")
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
    result = compare_cases_standalone(case_ids, cases_data)

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

    exporter = get_pdf_exporter()
    output_path = exporter.export_comparison_to_html(comparison_data)

    return send_file(output_path, as_attachment=True, download_name="comparison_report.html")
