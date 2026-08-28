# -*- coding: utf-8 -*-
"""
案例对比模块 - case_comparison.py

功能：
- 多案件并排对比
- 案件特征差异高亮
- 量刑差异分析
- 对比报告生成
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import statistics


@dataclass
class ComparisonItem:
    """对比项"""
    field: str  # 字段名
    label: str  # 显示标签
    values: Dict[str, str]  # {case_id: value}
    highlight: bool  # 是否高亮差异
    is_better: str  # "case1" / "case2" / "both" / "none"


@dataclass
class ComparisonResult:
    """对比结果"""
    case_ids: List[str]
    cases_data: List[Dict]
    comparison_items: List[ComparisonItem]
    summary: str
    insights: List[str]


class CaseComparator:
    """案件对比器"""
    
    # 对比字段定义
    COMPARABLE_FIELDS = {
        "case_id": ("案件ID", "id"),
        "case_name": ("案件名称", "text"),
        "court": ("法院", "text"),
        "judgment_date": ("判决日期", "date"),
        "crime": ("罪名", "text"),
        "sentence_years": ("刑期(年)", "number"),
        "sentence_months": ("刑期(月)", "number"),
        "amount": ("涉案金额", "money"),
        "is_累犯": ("累犯", "boolean"),
        "is_自首": ("自首", "boolean"),
        "is_立功": ("立功", "boolean"),
        "is_坦白": ("坦白", "boolean"),
        "is_赔偿": ("赔偿", "boolean"),
        "is_谅解": ("谅解", "boolean"),
        "is_初犯": ("初犯", "boolean"),
    }
    
    def __init__(self):
        pass
    
    def compare_cases(self, case_ids: List[str], cases_data: List[Dict]) -> ComparisonResult:
        """对比多个案件
        
        Args:
            case_ids: 案件ID列表
            cases_data: 案件数据列表
            
        Returns:
            ComparisonResult: 对比结果
        """
        if len(case_ids) < 2:
            raise ValueError("至少需要2个案件进行对比")
        
        if len(case_ids) > 5:
            raise ValueError("最多支持5个案件对比")
        
        if len(case_ids) != len(cases_data):
            raise ValueError("案件ID数量与数据数量不匹配")
        
        comparison_items = []
        insights = []
        
        # 对每个字段进行对比
        for field, (label, field_type) in self.COMPARABLE_FIELDS.items():
            values = {}
            all_values = []
            
            for case_id, case_data in zip(case_ids, cases_data):
                value = self._extract_field_value(case_data, field)
                values[case_id] = self._format_value(value, field_type)
                if value is not None:
                    all_values.append(value)
            
            # 检查是否所有值都相同
            unique_values = set(str(v) for v in all_values if v is not None)
            highlight = len(unique_values) > 1
            
            # 判断哪个更好（对于量刑，越短越好）
            is_better = self._determine_better(field, all_values, case_ids, cases_data)
            
            comparison_items.append(ComparisonItem(
                field=field,
                label=label,
                values=values,
                highlight=highlight,
                is_better=is_better,
            ))
        
        # 生成洞察
        insights = self._generate_insights(case_ids, cases_data)
        
        # 生成摘要
        summary = self._generate_summary(case_ids, cases_data, insights)
        
        return ComparisonResult(
            case_ids=case_ids,
            cases_data=cases_data,
            comparison_items=comparison_items,
            summary=summary,
            insights=insights,
        )
    
    def _extract_field_value(self, case_data: Dict, field: str):
        """提取字段值"""
        # 直接字段
        if field in case_data:
            return case_data[field]
        
        # 嵌套字段
        if field == "court":
            return case_data.get("meta", {}).get("court", "")
        
        if field == "case_name":
            return case_data.get("meta", {}).get("name", case_data.get("case_id", ""))
        
        if field == "judgment_date":
            dates = case_data.get("procedure", {})
            return dates.get("judgment_date", dates.get("trial_date", ""))
        
        if field in ["sentence_years", "sentence_months"]:
            charges = case_data.get("charges", {}).get("charges_judged", {})
            for charge in charges.values():
                if field == "sentence_years":
                    return charge.get("sentence_years")
                else:
                    return charge.get("sentence_months")
        
        if field == "amount":
            charges = case_data.get("charges", {}).get("charges_judged", {})
            for charge in charges.values():
                amount = charge.get("amount")
                if amount:
                    return amount
        
        if field == "crime":
            charges = case_data.get("charges", {}).get("charges_judged", {})
            crimes = [c.get("name", "") for c in charges.values()]
            return ", ".join(crimes) if crimes else ""
        
        # 量刑情节
        if field.startswith("is_"):
            return case_data.get(field, False)
        
        return None
    
    def _format_value(self, value, field_type: str) -> str:
        """格式化字段值"""
        if value is None:
            return "-"
        
        if field_type == "boolean":
            return "✓" if value else "✗"
        
        if field_type == "money":
            if isinstance(value, (int, float)):
                if value >= 10000:
                    return f"{value/10000:.1f}万"
                return f"{value:.0f}"
            return str(value)
        
        if field_type == "number":
            if isinstance(value, (int, float)):
                return f"{value:.2f}"
            return str(value)
        
        return str(value)
    
    def _determine_better(self, field: str, values: List, case_ids: List, cases_data: List) -> str:
        """判断哪个案件在该字段上更好"""
        if not values or len(values) < 2:
            return "none"
        
        # 刑期越短越好
        if field in ["sentence_years", "sentence_months"]:
            min_val = min(v for v in values if v is not None)
            if min_val is not None:
                for i, (case_id, case_data) in enumerate(zip(case_ids, cases_data)):
                    extracted = self._extract_field_value(case_data, field)
                    if extracted == min_val:
                        return case_id
            return "none"
        
        # 从轻情节越多越好
        if field in ["is_自首", "is_立功", "is_坦白", "is_赔偿", "is_谅解", "is_初犯"]:
            true_count = sum(1 for v in values if v)
            if true_count == len(values):
                return "both"
            elif true_count == 0:
                return "none"
            else:
                # 找出有该情节的案件
                better_cases = []
                for case_id, case_data in zip(case_ids, cases_data):
                    if self._extract_field_value(case_data, field):
                        better_cases.append(case_id)
                return better_cases[0] if len(better_cases) == 1 else "both"
        
        # 累犯越少越好
        if field == "is_累犯":
            false_count = sum(1 for v in values if not v)
            if false_count == len(values):
                return "both"
            elif false_count == 0:
                return "none"
            else:
                for case_id, case_data in zip(case_ids, cases_data):
                    if not self._extract_field_value(case_data, field):
                        return case_id
                return "none"
        
        return "none"
    
    def _generate_insights(self, case_ids: List[str], cases_data: List[Dict]) -> List[str]:
        """生成对比洞察"""
        insights = []
        
        # 1. 量刑对比
        sentences = []
        for case_id, case_data in zip(case_ids, cases_data):
            years = self._extract_field_value(case_data, "sentence_years")
            months = self._extract_field_value(case_data, "sentence_months")
            if years:
                total_months = years * 12
            elif months:
                total_months = months
            else:
                total_months = None
            
            if total_months is not None:
                sentences.append((case_id, total_months))
        
        if len(sentences) >= 2:
            sentences.sort(key=lambda x: x[1])
            min_case, min_sentence = sentences[0]
            max_case, max_sentence = sentences[-1]
            diff = max_sentence - min_sentence
            
            if diff > 0:
                insights.append(f"📊 量刑差异: {min_case}最轻({min_sentence:.0f}月) vs {max_case}最重({max_sentence:.0f}月)，相差{diff:.0f}个月")
        
        # 2. 从轻情节对比
        mitigating_factors = ["is_自首", "is_立功", "is_坦白", "is_赔偿", "is_谅解", "is_初犯"]
        factor_counts = {}
        
        for case_id, case_data in zip(case_ids, cases_data):
            count = sum(1 for f in mitigating_factors if self._extract_field_value(case_data, f))
            factor_counts[case_id] = count
        
        if factor_counts:
            max_factors = max(factor_counts.values())
            min_factors = min(factor_counts.values())
            if max_factors != min_factors:
                max_cases = [c for c, n in factor_counts.items() if n == max_factors]
                insights.append(f"⚖️ 从轻情节: {', '.join(max_cases)}最多({max_factors}个)，{min(factor_counts.items(), key=lambda x: x[1])[0]}最少({min_factors}个)")
        
        # 3. 金额对比
        amounts = []
        for case_id, case_data in zip(case_ids, cases_data):
            amount = self._extract_field_value(case_data, "amount")
            if amount:
                amounts.append((case_id, amount))
        
        if len(amounts) >= 2:
            amounts.sort(key=lambda x: x[1])
            min_case, min_amount = amounts[0]
            max_case, max_amount = amounts[-1]
            insights.append(f"💰 涉案金额: {min_case}最低({min_amount:.0f}元) vs {max_case}最高({max_amount:.0f}元)")
        
        return insights
    
    def _generate_summary(self, case_ids: List[str], cases_data: List[Dict], insights: List[str]) -> str:
        """生成摘要"""
        if not insights:
            return "这些案件在主要特征上较为相似"
        
        return f"对比了{len(case_ids)}个案件: " + "; ".join(insights[:2])
    
    def generate_comparison_html(self, result: ComparisonResult) -> str:
        """生成对比HTML"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>案件对比 - {' vs '.join(result.case_ids)}</title>
    <style>
        body {{ font-family: -apple-system, 'PingFang SC', sans-serif; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #1a1a2e; margin-bottom: 10px; }}
        .summary {{ background: #e8f4fd; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
        .insights {{ background: #fff3cd; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
        .insights li {{ margin: 5px 0; }}
        table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #1a1a2e; color: white; }}
        tr:hover {{ background: #f8f9fa; }}
        .highlight {{ background: #fff3cd !important; }}
        .better {{ color: #27ae60; font-weight: bold; }}
        .worse {{ color: #e74c3c; }}
        .back {{ display: inline-block; padding: 10px 20px; background: #1a1a2e; color: white; text-decoration: none; border-radius: 6px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>⚖️ 案件对比分析</h1>
        
        <div class="summary">
            <strong>摘要:</strong> {result.summary}
        </div>
        
        <div class="insights">
            <strong>📊 对比洞察:</strong>
            <ul>
                {"".join(f"<li>{insight}</li>" for insight in result.insights)}
            </ul>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>对比项</th>
                    {"".join(f"<th>{case_id}</th>" for case_id in result.case_ids)}
                </tr>
            </thead>
            <tbody>
"""
        
        for item in result.comparison_items:
            row_class = 'class="highlight"' if item.highlight else ""
            html += f"""
                <tr {row_class}>
                    <td><strong>{item.label}</strong></td>
"""
            for case_id in result.case_ids:
                value = item.values.get(case_id, "-")
                cell_class = ""
                if item.highlight:
                    if item.is_better == case_id:
                        cell_class = 'class="better"'
                    elif item.is_better not in ["both", "none"] and item.is_better != case_id:
                        cell_class = 'class="worse"'
                html += f"""                    <td {cell_class}>{value}</td>
"""
            html += """                </tr>
"""
        
        html += """            </tbody>
        </table>
        
        <a href="/" class="back">← 返回案件列表</a>
    </div>
</body>
</html>"""
        
        return html


def compare_cases(case_ids: List[str], cases_data: List[Dict]) -> ComparisonResult:
    """便捷函数：对比案件"""
    comparator = CaseComparator()
    return comparator.compare_cases(case_ids, cases_data)


if __name__ == "__main__":
    print("=== 案例对比模块测试 ===\n")
    
    # 模拟案件数据
    case1 = {
        "case_id": "CASE-001",
        "case_name": "盗窃案A",
        "court": "北京市朝阳区法院",
        "judgment_date": "2024-01-15",
        "charges": {"charges_judged": {"c1": {"name": "盗窃罪", "amount": 50000, "sentence_years": 1.5}}},
        "is_自首": True,
        "is_初犯": True,
        "is_累犯": False,
        "is_赔偿": True,
        "is_谅解": True,
    }
    
    case2 = {
        "case_id": "CASE-002",
        "case_name": "盗窃案B",
        "court": "上海市浦东新区法院",
        "judgment_date": "2024-02-20",
        "charges": {"charges_judged": {"c1": {"name": "盗窃罪", "amount": 80000, "sentence_years": 2.5}}},
        "is_自首": False,
        "is_初犯": True,
        "is_累犯": True,
        "is_赔偿": False,
        "is_谅解": False,
    }
    
    comparator = CaseComparator()
    result = comparator.compare_cases(["CASE-001", "CASE-002"], [case1, case2])
    
    print(f"对比案件: {result.case_ids}")
    print(f"\n摘要: {result.summary}")
    print(f"\n洞察:")
    for insight in result.insights:
        print(f"  - {insight}")
    
    print(f"\n对比项数量: {len(result.comparison_items)}")
    
    # 生成HTML
    html = comparator.generate_comparison_html(result)
    with open("/tmp/comparison.html", "w") as f:
        f.write(html)
    print("\n✅ HTML报告已生成: /tmp/comparison.html")
