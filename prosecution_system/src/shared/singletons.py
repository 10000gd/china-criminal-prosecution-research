# -*- coding: utf-8 -*-
"""共享单例对象"""
from case_loader import CaseLoader
from build_report import ReportBuilder
from pdf_exporter import PDFExporter

# CaseLoader 是无状态工具，直接模块级单例
loader = CaseLoader()

# ReportBuilder 延迟初始化
_report_builder = None


def get_report_builder():
    global _report_builder
    if _report_builder is None:
        _report_builder = ReportBuilder()
    return _report_builder


# PDFExporter 延迟初始化
_pdf_exporter = None


def get_pdf_exporter():
    global _pdf_exporter
    if _pdf_exporter is None:
        _pdf_exporter = PDFExporter()
    return _pdf_exporter
