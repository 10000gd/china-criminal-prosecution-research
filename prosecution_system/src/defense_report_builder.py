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
        self.output_dir = output_dir or Path("output/defense_reports")
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
