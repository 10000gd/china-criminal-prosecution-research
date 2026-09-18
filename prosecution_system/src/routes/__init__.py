# -*- coding: utf-8 -*-
"""所有路由蓝图导出"""
from .auth_pages import auth_pages_bp
from .cases import cases_bp
from .search import search_bp, search_bp_page
from .stats import stats_bp, stats_page_bp
from .compare import compare_bp, compare_page_bp
from .tracker import tracker_bp
from .export import export_bp
from .defense import defense_bp
from .reports import reports_bp, reports_page_bp

__all__ = [
    'auth_pages_bp',
    'cases_bp',
    'search_bp',
    'search_bp_page',
    'stats_bp',
    'stats_page_bp',
    'compare_bp',
    'compare_page_bp',
    'tracker_bp',
    'export_bp',
    'defense_bp',
    'reports_bp',
    'reports_page_bp',
]
