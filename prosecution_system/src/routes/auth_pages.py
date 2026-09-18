# -*- coding: utf-8 -*-
"""认证相关页面"""
from flask import Blueprint, request, render_template, session

auth_pages_bp = Blueprint('auth_pages', __name__)


@auth_pages_bp.route("/")
def index():
    """首页 - 案件列表"""
    from shared.singletons import loader
    loader_instance = loader  # 使用模块级单例
    status_filter = request.args.get("status", "")
    cases = loader_instance.list_cases(status=status_filter if status_filter else None)
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


@auth_pages_bp.route("/docs")
def docs_page():
    """API文档页面 - 中文文档"""
    return render_template("docs_zh.html")


@auth_pages_bp.route("/docs-en")
def docs_page_en():
    """API文档页面 - 英文文档"""
    return render_template("docs.html")
