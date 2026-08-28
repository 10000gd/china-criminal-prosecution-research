# -*- coding: utf-8 -*-
"""
PDF导出模块 - pdf_exporter.py

支持多种导出方式：
- HTML模板（浏览器打印为PDF）
- Markdown（可转换为PDF）
- 纯文本报告

由于服务器环境限制，优先使用HTML导出，用户可通过浏览器打印为PDF。
如需服务器端PDF生成，建议安装：
- reportlab: pip install reportlab
- wkhtmltopdf: sudo apt install wkhtmltopdf
- weasyprint: pip install weasyprint
"""

import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from io import StringIO


class PDFExporter:
    """PDF导出器（基于HTML模板）"""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export_case_to_html(self, case_data: Dict, output_path: str = None) -> str:
        """导出案件为HTML（可打印为PDF）"""
        if output_path is None:
            output_path = self.output_dir / f"case_{case_data.get('case_id', 'unknown')}.html"
        else:
            output_path = Path(output_path)
        
        html = self._generate_case_html(case_data)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        
        return str(output_path)
    
    def export_comparison_to_html(self, comparison_data: Dict, output_path: str = None) -> str:
        """导出对比结果为HTML"""
        if output_path is None:
            output_path = self.output_dir / "comparison_report.html"
        
        html = self._generate_comparison_html(comparison_data)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        
        return str(output_path)
    
    def export_defense_to_markdown(self, case_data: Dict, defense_analysis: Dict, output_path: str = None) -> str:
        """导出辩护意见为Markdown"""
        if output_path is None:
            output_path = self.output_dir / f"defense_{case_data.get('case_id', 'unknown')}.md"
        else:
            output_path = Path(output_path)
        
        md = self._generate_defense_markdown(case_data, defense_analysis)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md)
        
        return str(output_path)
    
    def export_sentencing_report_to_html(self, report_data: Dict, output_path: str = None) -> str:
        """导出量刑报告为HTML"""
        if output_path is None:
            output_path = self.output_dir / "sentencing_report.html"
        
        html = self._generate_sentencing_html(report_data)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        
        return str(output_path)
    
    def _generate_case_html(self, case_data: Dict) -> str:
        """生成案件HTML"""
        meta = case_data.get("meta", {})
        case_info = case_data.get("case_info", {})
        charges = case_data.get("charges", {})
        
        defendants = case_data.get("defendants", [])
        defendants_html = ""
        for d in defendants:
            defendants_html += f"<tr><td>{d.get('name', '')}</td><td>{d.get('gender', '')}</td><td>{d.get('age', '')}</td></tr>"
        
        charges_html = ""
        for cid, charge in charges.get("charges_judged", {}).items():
            charges_html += f"""
            <tr>
                <td>{charge.get('name', '')}</td>
                <td>{charge.get('article', '')}</td>
                <td>{charge.get('amount', '')}</td>
                <td>{charge.get('sentence', '')}</td>
            </tr>
            """
        
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>案件报告 - {case_data.get('case_id', '')}</title>
    <style>
        @media print {{
            .no-print {{ display: none; }}
            body {{ padding: 20px; }}
        }}
        body {{ font-family: 'SimSun', '宋体', serif; font-size: 14px; line-height: 1.8; max-width: 800px; margin: 0 auto; padding: 40px; }}
        h1 {{ text-align: center; font-size: 24px; border-bottom: 2px solid #333; padding-bottom: 10px; }}
        h2 {{ font-size: 18px; margin-top: 24px; border-left: 4px solid #1e3a5f; padding-left: 10px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
        th {{ background: #f5f5f5; }}
        .meta {{ color: #666; font-size: 12px; text-align: right; margin-top: 20px; }}
        .print-btn {{ 
            background: #1e3a5f; color: white; border: none; padding: 12px 24px; 
            border-radius: 6px; cursor: pointer; font-size: 14px; margin: 20px 0;
        }}
        .print-btn:hover {{ background: #2d5a8f; }}
    </style>
</head>
<body>
    <button class="print-btn no-print" onclick="window.print()">🖨️ 打印为PDF</button>
    
    <h1>刑事案件报告</h1>
    
    <table>
        <tr><th style="width: 100px;">案件编号</th><td>{case_data.get('case_id', '')}</td></tr>
        <tr><th>案件名称</th><td>{meta.get('name', case_data.get('case_id', ''))}</td></tr>
        <tr><th>案件类型</th><td>{case_data.get('case_type', '刑事案件')}</td></tr>
        <tr><th>审理法院</th><td>{meta.get('court', '')}</td></tr>
    </table>
    
    <h2>一、被告人信息</h2>
    <table>
        <thead><tr><th>姓名</th><th>性别</th><th>年龄</th></tr></thead>
        <tbody>{defendants_html}</tbody>
    </table>
    
    <h2>二、案件事实</h2>
    <p>{case_data.get('case_summary', case_info.get('summary', '（详见判决书）'))}</p>
    
    <h2>三、指控罪名</h2>
    <table>
        <thead><tr><th>罪名</th><th>法条</th><th>涉案金额</th><th>量刑建议</th></tr></thead>
        <tbody>{charges_html}</tbody>
    </table>
    
    <h2>四、程序信息</h2>
    <table>
        <tr><th style="width: 120px;">拘留日期</th><td>{case_data.get('procedure', {}).get('detention_date', '')}</td></tr>
        <tr><th>逮捕日期</th><td>{case_data.get('procedure', {}).get('arrest_date', '')}</td></tr>
        <tr><th>起诉日期</th><td>{case_data.get('procedure', {}).get('prosecution_date', '')}</td></tr>
        <tr><th>审判日期</th><td>{case_data.get('procedure', {}).get('trial_date', '')}</td></tr>
    </table>
    
    <div class="meta">
        报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
        刑事追诉智能辅助系统 · 仅供参考
    </div>
</body>
</html>"""
    
    def _generate_comparison_html(self, comparison_data: Dict) -> str:
        """生成对比报告HTML"""
        case_ids = comparison_data.get("case_ids", [])
        summary = comparison_data.get("summary", "")
        insights = comparison_data.get("insights", [])
        items = comparison_data.get("comparison_items", [])
        
        rows_html = ""
        for item in items:
            rows_html += f"<tr><td>{item.get('label', '')}</td>"
            for case_id in case_ids:
                value = item.get("values", {}).get(case_id, "-")
                highlight = item.get("highlight", False)
                better = item.get("is_better", "none")
                style = ""
                if highlight:
                    if better == case_id:
                        style = 'style="background: #d1fae5;"'
                    elif better not in ["both", "none"]:
                        style = 'style="background: #fee2e2;"'
                rows_html += f"<td {style}>{value}</td>"
            rows_html += "</tr>"
        
        insights_html = "".join(f"<li>{i}</li>" for i in insights)
        
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>案件对比报告</title>
    <style>
        @media print {{ body {{ padding: 20px; }} }}
        body {{ font-family: 'SimSun', serif; font-size: 14px; line-height: 1.8; max-width: 1000px; margin: 0 auto; padding: 40px; }}
        h1 {{ text-align: center; font-size: 24px; }}
        .summary {{ background: #f0f9ff; padding: 16px; border-radius: 8px; margin: 20px 0; }}
        .insights {{ background: #fffbeb; padding: 16px; border-radius: 8px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background: #1e3a5f; color: white; }}
    </style>
</head>
<body>
    <h1>⚖️ 案件对比报告</h1>
    
    <div class="summary">
        <strong>摘要：</strong>{summary}
    </div>
    
    <div class="insights">
        <strong>对比洞察：</strong>
        <ul>{insights_html}</ul>
    </div>
    
    <table>
        <thead><tr><th>对比项</th>{"".join(f"<th>{cid}</th>" for cid in case_ids)}</tr></thead>
        <tbody>{rows_html}</tbody>
    </table>
    
    <div style="text-align: right; color: #666; font-size: 12px; margin-top: 20px;">
        报告生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </div>
</body>
</html>"""
    
    def _generate_defense_markdown(self, case_data: Dict, defense_analysis: Dict) -> str:
        """生成辩护意见Markdown"""
        case_id = case_data.get("case_id", "")
        defendant_name = case_data.get("defendants", [{}])[0].get("name", "被告")
        
        primary = defense_analysis.get("primary_defense", "")
        secondary = defense_analysis.get("secondary_defenses", [])
        strength = defense_analysis.get("overall_strength", 0)
        
        arguments = defense_analysis.get("arguments", [])
        similar_cases = defense_analysis.get("similar_cases", [])
        
        md = f"""# 辩护意见书

**案件编号：** {case_id}  
**被告人：** {defendant_name}  
**生成时间：** {datetime.now().strftime('%Y-%m-%d')}

---

## 一、核心辩护观点

### 主要辩护方向：{primary}

**辩护强度评估：** {"⭐" * int(strength / 20)} ({strength}%)

### 辅助辩护方向

{"".join(f"- {s}" for s in secondary)}

---

## 二、辩护理由

{"".join(f"### {i+1}. {arg.get('title', '')}\n\n{arg.get('content', '')}\n\n" for i, arg in enumerate(arguments))}

---

## 三、类案参考

| 案件 | 结果 | 关键辩护点 |
|------|------|-----------|
{"".join(f"| {c.get('case_name', '')} | {c.get('outcome', '')} | {c.get('key_defense', '')} |" for c in similar_cases[:5])}

---

## 四、法律依据

{"".join(f"- {law}\n" for law in defense_analysis.get("legal_basis", []))}

---

## 五、结论与建议

{defense_analysis.get("conclusion", "建议法庭充分考虑上述辩护意见，依法作出公正判决。")}

---

*本辩护意见由刑事追诉智能辅助系统生成，仅供参考。*  
*最终法律意见请咨询专业律师。*
"""
        return md
    
    def _generate_sentencing_html(self, report_data: Dict) -> str:
        """生成量刑报告HTML"""
        generated_at = report_data.get("generated_at", "")
        summary = report_data.get("summary", "")
        crime_stats = report_data.get("crime_stats", {})
        provincial = report_data.get("provincial_comparison", {})
        
        stats_rows = ""
        for crime, stats in crime_stats.items():
            stats_rows += f"""<tr>
                <td>{crime}</td>
                <td>{stats.get('sample_count', 0)}</td>
                <td>{stats.get('avg_sentence', 'N/A')}</td>
                <td>{stats.get('median_sentence', 'N/A')}</td>
                <td>{stats.get('probation_rate', 0)}%</td>
            </tr>"""
        
        province_rows = ""
        for province, data in sorted(provincial.items(), key=lambda x: x[1].get("avg_sentence", 0)):
            deviation = data.get("deviation_type", "")
            color = "#d1fae5" if deviation == "偏轻" else "#fee2e2" if deviation == "偏重" else "#f3f4f6"
            province_rows += f"""<tr style="background: {color};">
                <td>{province}</td>
                <td>{data.get('count', 0)}</td>
                <td>{data.get('avg_sentence', 'N/A')}</td>
                <td>{deviation}</td>
            </tr>"""
        
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>量刑一致性报告</title>
    <style>
        @media print {{ body {{ padding: 20px; }} }}
        body {{ font-family: 'SimSun', serif; font-size: 14px; line-height: 1.8; max-width: 900px; margin: 0 auto; padding: 40px; }}
        h1 {{ text-align: center; font-size: 24px; }}
        h2 {{ font-size: 18px; margin-top: 30px; border-left: 4px solid #1e3a5f; padding-left: 10px; }}
        .summary {{ background: #f0f9ff; padding: 16px; border-radius: 8px; margin: 20px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
        th {{ background: #f5f5f5; }}
    </style>
</head>
<body>
    <h1>⚖️ 量刑一致性分析报告</h1>
    
    <p style="text-align: right; color: #666;">生成时间：{generated_at}</p>
    
    <div class="summary">
        <strong>报告摘要：</strong>{summary}
    </div>
    
    <h2>一、罪名量刑统计</h2>
    <table>
        <thead><tr><th>罪名</th><th>样本数</th><th>平均刑期(年)</th><th>中位数(年)</th><th>缓刑率</th></tr></thead>
        <tbody>{stats_rows}</tbody>
    </table>
    
    <h2>二、省份量刑对比</h2>
    <table>
        <thead><tr><th>省份</th><th>案例数</th><th>平均刑期(年)</th><th>偏离类型</th></tr></thead>
        <tbody>{province_rows}</tbody>
    </table>
    
    <p style="margin-top: 40px; color: #666; font-size: 12px;">
        * 本报告基于历史案例数据分析，仅供参考。具体量刑应由法院根据案件具体情况判定。
    </p>
</body>
</html>"""


def export_case_pdf(case_data: Dict, output_dir: str = "output") -> str:
    """便捷函数：导出案件为PDF（HTML格式）"""
    exporter = PDFExporter(output_dir)
    return exporter.export_case_to_html(case_data)


def export_comparison_pdf(comparison_data: Dict, output_dir: str = "output") -> str:
    """便捷函数：导出对比报告为PDF"""
    exporter = PDFExporter(output_dir)
    return exporter.export_comparison_to_html(comparison_data)


if __name__ == "__main__":
    print("=== PDF导出模块测试 ===\n")
    
    # 测试数据
    test_case = {
        "case_id": "TEST-001",
        "case_name": "测试案件",
        "case_type": "刑事案件",
        "meta": {"court": "北京市朝阳区法院", "name": "盗窃案"},
        "defendants": [{"name": "张三", "gender": "男", "age": 35}],
        "charges": {
            "charges_judged": {
                "c1": {"name": "盗窃罪", "article": "刑法第264条", "amount": 50000, "sentence": "有期徒刑1年"}
            }
        },
        "procedure": {
            "detention_date": "2024-01-01",
            "arrest_date": "2024-01-15",
            "prosecution_date": "2024-03-01",
            "trial_date": "2024-04-01",
        },
        "case_summary": "被告人张三于2024年1月1日在某商场盗窃商品，价值共计50000元。",
    }
    
    exporter = PDFExporter("/tmp")
    
    # 导出案件HTML
    path = exporter.export_case_to_html(test_case, "/tmp/test_case.html")
    print(f"✅ 案件HTML已导出: {path}")
    
    # 导出对比HTML
    comparison_data = {
        "case_ids": ["CASE-001", "CASE-002"],
        "summary": "两个盗窃案件对比分析",
        "insights": ["量刑差异20%", "从轻情节不同"],
        "comparison_items": [
            {"label": "刑期", "values": {"CASE-001": "1年", "CASE-002": "2年"}, "highlight": True, "is_better": "CASE-001"}
        ]
    }
    path = exporter.export_comparison_to_html(comparison_data, "/tmp/test_comparison.html")
    print(f"✅ 对比HTML已导出: {path}")
    
    print("\n✅ PDF导出模块测试完成！")
    print("💡 提示：在浏览器中打开HTML文件，使用Ctrl+P可打印为PDF")
