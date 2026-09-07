# -*- coding: utf-8 -*-
"""
辩护报告构建器 - defense_report_builder.py

生成完整的辩护报告：
- LaTeX格式报告
- Markdown格式报告  
- HTML格式报告
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class DefenseReport:
    """辩护报告"""
    case_id: str
    case_name: str
    generated_at: str
    
    # 各部分内容
    analysis_summary: str
    defense_angles: List[Dict]
    similar_cases: List[Dict]
    opinion_text: str
    
    # 统计
    overall_strength: float
    recommendation: str


class DefenseReportBuilder:
    """辩护报告构建器"""
    
    def __init__(self, output_dir: Path = None):
        """初始化
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir or (Path(__file__).parent.parent / "output" / "defense_reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def build(self, case_data: Dict,
              defense_analysis: Dict,
              similar_cases: List[Dict],
              opinion: str) -> DefenseReport:
        """构建辩护报告"""
        
        case_id = case_data.get("case_id", "unknown")
        case_name = case_data.get("case_name", case_data.get("case_summary", "未知案件")[:50])
        
        report = DefenseReport(
            case_id=case_id,
            case_name=case_name,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
            analysis_summary=self._generate_summary(defense_analysis),
            defense_angles=defense_analysis.get("primary_defense", {}).to_dict() if hasattr(defense_analysis.get("primary_defense", {}), 'to_dict') else defense_analysis.get("primary_defense", {}),
            similar_cases=similar_cases,
            opinion_text=opinion,
            overall_strength=defense_analysis.get("overall_strength", 50),
            recommendation=defense_analysis.get("recommended_strategy", ""),
        )
        
        return report
    
    def _generate_summary(self, defense_analysis: Dict) -> str:
        """生成分析摘要"""
        primary = defense_analysis.get("primary_defense", {})
        defense_type = primary.get("type", "待定")
        confidence = primary.get("confidence", 0)
        strength = defense_analysis.get("overall_strength", 50)
        
        return f"""
本案经系统分析，主要辩护方向为「{defense_type}」，
匹配度 {confidence:.0f}%，整体辩护强度 {strength:.0f}/100。
{ defense_analysis.get("estimated_outcome", "") }
""".strip()
    
    def save_markdown(self, report: DefenseReport, filename: str = None) -> Path:
        """保存为Markdown"""
        if not filename:
            filename = f"defense_report_{report.case_id}_{datetime.now().strftime('%Y%m%d')}.md"
        
        filepath = self.output_dir / filename
        
        content = self._build_markdown(report)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        return filepath
    
    def save_json(self, report: DefenseReport, filename: str = None) -> Path:
        """保存为JSON"""
        if not filename:
            filename = f"defense_report_{report.case_id}_{datetime.now().strftime('%Y%m%d')}.json"
        
        filepath = self.output_dir / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report.__dict__, f, ensure_ascii=False, indent=2)
        
        return filepath
    
    def save_html(self, report: DefenseReport, filename: str = None) -> Path:
        """保存为HTML"""
        if not filename:
            filename = f"defense_report_{report.case_id}_{datetime.now().strftime('%Y%m%d')}.html"
        
        filepath = self.output_dir / filename
        
        content = self._build_html(report)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        return filepath
    
    def _build_markdown(self, report: DefenseReport) -> str:
        """构建Markdown内容"""
        # 处理防御角度列表
        defense_angles_md = ""
        if report.defense_angles:
            if isinstance(report.defense_angles, list):
                for i, angle in enumerate(report.defense_angles, 1):
                    defense_angles_md += f"\n### {i}. {angle.get('type', '未知')}\n"
                    defense_angles_md += f"- **法律依据**: {angle.get('legal_basis', '待查')}\n"
                    defense_angles_md += f"- **置信度**: {angle.get('confidence', 0):.0f}%\n"
                    defense_angles_md += f"- **风险缓解**: {angle.get('risk_mitigation', '')}\n"
            else:
                defense_angles_md += f"\n### 主要防御方向\n"
                defense_angles_md += f"- **类型**: {report.defense_angles.get('type', '未知')}\n"
                defense_angles_md += f"- **法律依据**: {report.defense_angles.get('legal_basis', '待查')}\n"
        
        # 处理类似案例
        similar_cases_md = ""
        for i, case in enumerate(report.similar_cases[:5], 1):
            similar_cases_md += f"\n**{i}. {case.get('case_name', '类案')}**\n"
            similar_cases_md += f"- 罪名: {case.get('crime', '')}\n"
            similar_cases_md += f"- 结果: {case.get('outcome', '')}\n"
            similar_cases_md += f"- 辩护理由: {case.get('key_defense', '')}\n"
        
        return f"""# 辩护分析报告

## 案件信息

| 项目 | 内容 |
|------|------|
| 案号 | {report.case_id} |
| 案件名称 | {report.case_name} |
| 生成时间 | {report.generated_at} |

## 分析摘要

{report.analysis_summary}

## 整体评估

- **辩护强度**: {report.overall_strength:.0f}/100
- **推荐策略**: {report.recommendation}

## 辩护角度分析

{defense_angles_md}

## 类案参考

{similar_cases_md}

## 辩护意见摘要

{report.opinion_text}

---

*本报告由系统辅助生成，仅供参考使用。*
*生成时间: {report.generated_at}*
"""
    
    def _build_html(self, report: DefenseReport) -> str:
        """构建HTML内容"""
        # 计算强度颜色
        if report.overall_strength >= 70:
            strength_color = "#28a745"  # 绿色
        elif report.overall_strength >= 50:
            strength_color = "#ffc107"  # 黄色
        else:
            strength_color = "#dc3545"  # 红色
        
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>辩护分析报告 - {report.case_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .card {{
            background: white;
            border-radius: 8px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #007bff;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 14px;
            font-weight: 500;
        }}
        .badge-success {{
            background: #d4edda;
            color: #155724;
        }}
        .badge-warning {{
            background: #fff3cd;
            color: #856404;
        }}
        .badge-danger {{
            background: #f8d7da;
            color: #721c24;
        }}
        .strength-meter {{
            background: #e9ecef;
            border-radius: 8px;
            height: 24px;
            overflow: hidden;
            margin: 10px 0;
        }}
        .strength-bar {{
            height: 100%;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
            transition: width 0.3s ease;
        }}
        .defense-card {{
            background: #f8f9fa;
            border-left: 4px solid #007bff;
            padding: 16px;
            margin: 12px 0;
        }}
        .case-card {{
            background: #fff;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            padding: 16px;
            margin: 12px 0;
        }}
        .case-outcome {{
            font-weight: 600;
            color: #28a745;
        }}
        .opinion {{
            background: #f0f7ff;
            border-radius: 8px;
            padding: 20px;
            white-space: pre-wrap;
        }}
        .footer {{
            text-align: center;
            color: #666;
            font-size: 12px;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
        }}
    </style>
</head>
<body>
    <div class="card">
        <h1>⚖️ 辩护分析报告</h1>
        <table>
            <tr>
                <th>案号</th>
                <td>{report.case_id}</td>
            </tr>
            <tr>
                <th>案件名称</th>
                <td>{report.case_name}</td>
            </tr>
            <tr>
                <th>生成时间</th>
                <td>{report.generated_at}</td>
            </tr>
        </table>
    </div>

    <div class="card">
        <h2>📊 整体评估</h2>
        <p><strong>辩护强度评分:</strong></p>
        <div class="strength-meter">
            <div class="strength-bar" style="width: {report.overall_strength}%; background: {strength_color};">
                {report.overall_strength:.0f}/100
            </div>
        </div>
        <p><strong>推荐策略:</strong> {report.recommendation}</p>
    </div>

    <div class="card">
        <h2>🛡️ 辩护角度分析</h2>
        <div class="defense-card">
            <h3>主要辩护方向</h3>
            <p><span class="badge badge-success">{report.defense_angles.get('type', '待定') if isinstance(report.defense_angles, dict) else '待定'}</span></p>
            <p><strong>法律依据:</strong> {report.defense_angles.get('legal_basis', '待查') if isinstance(report.defense_angles, dict) else '待查'}</p>
            <p><strong>置信度:</strong> {report.defense_angles.get('confidence', 0):.0f}%</p>
            <p><strong>风险缓解:</strong> {report.defense_angles.get('risk_mitigation', '')}</p>
        </div>
    </div>

    <div class="card">
        <h2>📚 类案参考</h2>
        {"".join(f'''
        <div class="case-card">
            <h4>{case.get('case_name', '类案')}</h4>
            <p><strong>罪名:</strong> {case.get('crime', '')}</p>
            <p><strong>结果:</strong> <span class="case-outcome">{case.get('outcome', '')}</span></p>
            <p><strong>辩护理由:</strong> {case.get('key_defense', '')}</p>
        </div>''' for case in report.similar_cases[:5])}
    </div>

    <div class="card">
        <h2>📝 辩护意见摘要</h2>
        <div class="opinion">{report.opinion_text}</div>
    </div>

    <div class="footer">
        <p>本报告由系统辅助生成，仅供参考使用</p>
        <p>生成时间: {report.generated_at}</p>
    </div>
</body>
</html>
"""


def build_defense_report(case_data: Dict,
                        defense_analysis: Dict,
                        similar_cases: List[Dict],
                        opinion: str,
                        output_format: str = "markdown") -> str:
    """便捷函数：构建并保存辩护报告
    
    Args:
        case_data: 案件数据
        defense_analysis: 辩护分析结果
        similar_cases: 类似案例
        opinion: 辩护意见
        output_format: 输出格式（markdown/html/json）
        
    Returns:
        保存的文件路径
    """
    builder = DefenseReportBuilder()
    report = builder.build(case_data, defense_analysis, similar_cases, opinion)
    
    if output_format == "html":
        filepath = builder.save_html(report)
    elif output_format == "json":
        filepath = builder.save_json(report)
    else:
        filepath = builder.save_markdown(report)
    
    return str(filepath)


if __name__ == "__main__":
    # 测试
    test_data = {
        "case_id": "TEST-001",
        "case_name": "张某正当防卫案",
        "case_summary": "被告人张某在回家途中遭遇李某持刀抢劫...",
    }
    
    test_analysis = {
        "primary_defense": {
            "type": "正当防卫",
            "confidence": 85,
            "legal_basis": "《刑法》第20条",
            "risk_mitigation": "无罪",
        },
        "secondary_defenses": [
            {"type": "自首", "risk_mitigation": "从轻"},
        ],
        "overall_strength": 75,
        "recommended_strategy": "无罪辩护",
        "estimated_outcome": "无罪可能性较高",
    }
    
    test_cases = [
        {
            "case_name": "于欢案",
            "crime": "故意伤害罪",
            "outcome": "认定正当防卫，改判五年",
            "key_defense": "正当防卫",
        }
    ]
    
    test_opinion = "被告人张某的行为属于正当防卫..."
    
    filepath = build_defense_report(test_data, test_analysis, test_cases, test_opinion, "html")
    print(f"报告已生成: {filepath}")


def _escape_pdf(text: str) -> str:
    """转义 PDF 特殊字符"""
    if not text:
        return ""
    return (text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;"))

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY




class DefenseReportBuilderPDF(DefenseReportBuilder):
    """辩护报告 PDF 生成器（基于 fpdf2 + NotoSansCJK）"""

    CJK_FONT_PATH = "/root/.fonts/NotoSansCJK_1.ttf"
    CJK_FONT_NAME = "NotoSansCJK"

    def save_pdf(self, report, filename=None):
        """保存为 PDF（中文支持）"""
        if not filename:
            filename = "defense_report_{}_{}.pdf".format(
                report.case_id, datetime.now().strftime("%Y%m%d"))
        filepath = self.output_dir / filename

        try:
            from fpdf import FPDF
        except ImportError:
            return self._save_pdf_fallback(report, filename)

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)

        # 注册中文字体
        try:
            pdf.add_font(self.CJK_FONT_NAME, fname=self.CJK_FONT_PATH)
            pdf.set_font(self.CJK_FONT_NAME, size=12)
            def font(pdf, size): pdf.set_font(self.CJK_FONT_NAME, size=size)
        except Exception:
            def font(pdf, size): pdf.set_font("helvetica", size=size)

        pdf.add_page()

        # 标题
        font(pdf, 16)
        pdf.cell(0, 12, "辩护意见书（系统生成稿）", new_x="LMARGIN", new_y="NEXT", align="C")
        font(pdf, 9)
        pdf.cell(0, 6, "案件编号：{}".format(report.case_id), new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 6, "案件名称：{}".format(report.case_name), new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 6, "生成时间：{}".format(report.generated_at), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
        pdf.set_draw_color(26, 58, 92)
        pdf.set_line_width(0.5)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(6)

        def section_title(pdf, text):
            font(pdf, 13)
            pdf.set_text_color(26, 58, 92)
            pdf.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)

        def body(pdf, text, indent=0):
            font(pdf, 10)
            pdf.set_x(pdf.l_margin + indent)
            pdf.multi_cell(0, 6, text)
            pdf.ln(1)

        # 一、分析摘要
        section_title(pdf, "一、案件分析摘要")
        for line in report.analysis_summary.strip().split("\n"):
            if line.strip():
                body(pdf, line.strip())
        pdf.ln(3)

        # 二、辩护要点
        section_title(pdf, "二、辩护要点")
        angles = report.defense_angles
        if isinstance(angles, dict):
            angles = [angles]
        if angles:
            for i, angle in enumerate(angles, 1):
                atype = angle.get("type", angle.get("type_cn", "待定"))
                conf = angle.get("confidence", "?")
                rec = angle.get("recommendation", "")
                refs = angle.get("legal_references", [])
                if isinstance(refs, list):
                    refs = "；".join(str(r) for r in refs if r)
                font(pdf, 11)
                pdf.cell(0, 7, "{}. {}（匹配度 {}%）".format(i, atype, conf),
                         new_x="LMARGIN", new_y="NEXT")
                if rec:
                    body(pdf, "  建议：{}".format(rec), indent=5)
                if refs:
                    body(pdf, "  法律依据：{}".format(refs[:100]), indent=5)
                pdf.ln(1)
        else:
            body(pdf, "（无辩护要点数据）")
        pdf.ln(3)

        # 三、类案参考
        if report.similar_cases:
            section_title(pdf, "三、类案参考")
            cases = report.similar_cases[:8]
            font(pdf, 9)
            col_w = [60, 35, 30, 30, 25]
            for h, w in zip(["法院", "罪名", "金额", "量刑", "相似度"], col_w):
                pdf.cell(w, 7, h, border=1, align="C")
            pdf.ln()
            fill = False
            for sc in cases:
                if isinstance(sc, dict):
                    row = [
                        str(sc.get("court", ""))[:12],
                        str(sc.get("crime_type", ""))[:6],
                        str(sc.get("amount", "-"))[:8],
                        str(sc.get("sentence", ""))[:6],
                        "{:.1f}".format(sc.get("similarity_score", 0)),
                    ]
                else:
                    row = ["?", "?", "?", "?", "?"]
                if fill:
                    pdf.set_fill_color(240, 244, 248)
                else:
                    pdf.set_fill_color(255, 255, 255)
                for val, w in zip(row, col_w):
                    pdf.cell(w, 6, val, border=1, align="C")
                pdf.ln()
                fill = not fill
            pdf.ln(3)

        # 四、辩护意见正文
        if report.opinion_text:
            section_title(pdf, "四、辩护意见")
            for line in report.opinion_text.strip().split("\n")[:25]:
                if line.strip():
                    body(pdf, line.strip())
            pdf.ln(3)

        # 五、结论
        section_title(pdf, "五、结论与建议")
        font(pdf, 11)
        pdf.cell(0, 7, "整体辩护强度：{:.0f}/100".format(report.overall_strength),
                 new_x="LMARGIN", new_y="NEXT")
        if report.recommendation:
            body(pdf, "综合建议：{}".format(report.recommendation))

        # 页脚
        pdf.ln(10)
        pdf.set_draw_color(200, 200, 200)
        pdf.set_line_width(0.3)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(2)
        font(pdf, 8)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 5, "本报告由追诉系统辅助生成，仅供参考，不构成正式法律意见。",
                 new_x="LMARGIN", new_y="NEXT", align="C")

        pdf.output(str(filepath))
        return filepath

    def _save_pdf_fallback(self, report, filename):
        """纯文本降级方案（无中文）"""
        filepath = self.output_dir / filename
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
        doc = SimpleDocTemplate(str(filepath), pagesize=A4,
                                leftMargin=2*cm, rightMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        body = ParagraphStyle("body", parent=styles["Normal"], fontSize=10, leading=14)
        story = [
            Paragraph("Defense Opinion Report (System Generated)", styles["Title"]),
            Paragraph("Case: {} | {}".format(report.case_id, report.case_name), body),
            Paragraph("Generated: {}".format(report.generated_at), body),
            HRFlowable(width="100%", thickness=1),
            Paragraph("Summary", styles["Heading2"]),
            *[Paragraph(l, body) for l in report.analysis_summary.strip().split("\n") if l.strip()],
            Paragraph("Recommendation", styles["Heading2"]),
            Paragraph(report.recommendation or "(See system analysis)", body),
            Paragraph("Overall Strength: {:.0f}/100".format(report.overall_strength), body),
        ]
        doc.build(story)
        return filepath



def save_defense_report_pdf(report, output_dir=None):
    """便捷函数：直接生成辩护 PDF"""
    builder = DefenseReportBuilderPDF(output_dir=output_dir)
    return builder.save_pdf(report)

def save_defense_report_pdf(report: DefenseReport, output_dir: Path = None) -> Path:
    """便捷函数：直接生成辩护 PDF"""
    builder = DefenseReportBuilderPDF(output_dir=output_dir)
    return builder.save_pdf(report)

def save_defense_report_pdf(report: DefenseReport, output_dir: Path = None) -> Path:
    """便捷函数：直接生成辩护 PDF"""
    builder = DefenseReportBuilderPDF(output_dir=output_dir)
    return builder.save_pdf(report)
