# -*- coding: utf-8 -*-
"""
C-CLAIM 溯源层 - prosecution_system/src/c_claim_tracer.py

功能：
- 对报告中的每条法律结论建立完整的来源链（Provenance Chain）
- C-CLAIM 框架：Claim（结论）→ Citation（引用）→ Attribution（溯源）→ Interpretation（解释）→ Methodology（方法）
- 机器可读的溯源记录，可导出为 JSON-LD 或嵌入报告附录
- 与 fact_checker 集成，为每个核查字段生成溯源链

C-CLAIM 五要素：
  Claim      — 结论是什么（罪名/量刑/情节认定）
  Citation   — 引用了哪些法条/司法解释（原文或编号）
  Attribution— 数据来源（新华社/判决原文/配置文件/分析推断）
  Interpretation — 推理过程（从法条到结论的逻辑链）
  Methodology — 使用的方法（数额比对/条文匹配/类案参考）

用法：
    tracer = CClaimTracer()
    tracer.load_from_fact_checker(fact_checker_instance)
    traces = tracer.get_all_traces()
    tracer.generate_trace_report()
"""

import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
import hashlib
import json
import re

# 预编译法条提取正则（避免在函数内重复编译）
_ARTICLE_PATTERNS = [
    re.compile(r"刑法\s*第\s*[\d零一二三四五六七八九十百千万]+条"),
    re.compile(r"最高法[院检]?\s*[司发]\s*〔\d{4}〕\s*第\s*\d+号"),
    re.compile(r"《[^》]+解释[^》]*》"),
    re.compile(r"《[^》]+意见[^》]*》"),
]


# ===== 来源等级（与 fact_checker 对齐） =====

class SourceGrade(IntEnum):
    A = 5  # 官方一手来源（判决书原文/新华社）
    B = 4  # 可推断来源（根据官方数据合理推断）
    C = 3  # 推测来源（无官方依据）
    D = 2  # 完全未知
    E = 1  # 已验证错误


@dataclass
class CClaimTrace:
    """单条溯源链"""
    trace_id: str                    # 唯一标识（内容哈希前8位）
    field_path: str                  # 对应字段路径
    claim: str                       # 结论内容

    # C-CLAIM 五要素
    citation_laws: List[str] = field(default_factory=list)   # 引用法条
    citation_keywords: List[str] = field(default_factory=list)  # 引用关键词
    attribution_source: str = ""    # 数据来源
    attribution_grade: int = 0      # 来源等级（0-5）
    interpretation_chain: List[str] = field(default_factory=list)  # 推理步骤
    methodology: str = ""           # 使用的方法

    # 元数据
    confidence_score: int = 0
    confidence_level: str = ""
    recommended_action: str = ""
    uncertainty_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["attribution_grade_name"] = SourceGrade(self.attribution_grade).name \
            if 1 <= self.attribution_grade <= 5 else "UNKNOWN"
        return d

    def to_markdown(self, max_width: int = 70) -> str:
        """渲染为可读 Markdown"""
        grade_map = {5: "A（官方）", 4: "B（可推断）", 3: "C（推测）",
                     2: "D（未知）", 1: "E（错误）"}
        grade_name = grade_map.get(self.attribution_grade, "?")
        lines = [
            f"### {self.field_path}",
            f"**结论**：{self.claim}",
            f"",
            f"| 维度 | 内容 |",
            f"|------|------|",
            f"| 来源等级 | {grade_name} |",
        ]
        if self.citation_laws:
            lines.append(f"| 引用法条 | {', '.join(self.citation_laws)} |")
        if self.citation_keywords:
            lines.append(f"| 引用关键词 | {', '.join(self.citation_keywords)} |")
        if self.attribution_source:
            lines.append(f"| 数据来源 | {self.attribution_source} |")
        if self.interpretation_chain:
            lines.append(f"| 推理链 | {' → '.join(self.interpretation_chain)} |")
        if self.methodology:
            lines.append(f"| 方法 | {self.methodology} |")
        if self.confidence_score > 0:
            lines.append(f"| 置信度 | {self.confidence_score}/100 [{self.confidence_level}] |")
        if self.recommended_action:
            lines.append(f"| 行动建议 | {self.recommended_action} |")
        if self.uncertainty_reasons:
            lines.append(f"| ⚠️ 不确定理由 | {'; '.join(self.uncertainty_reasons)} |")
        return "\n".join(lines)


@dataclass
class TraceReport:
    """整体溯源报告"""
    case_id: str
    total_traces: int = 0
    grade_a_traces: int = 0
    grade_b_traces: int = 0
    grade_c_traces: int = 0
    grade_d_traces: int = 0
    grade_e_traces: int = 0
    average_confidence: float = 0.0
    traces: List[CClaimTrace] = field(default_factory=list)

    def to_json(self, path: str = None) -> str:
        data = {
            "case_id": self.case_id,
            "total": self.total_traces,
            "grade_a": self.grade_a_traces,
            "grade_b": self.grade_b_traces,
            "grade_c": self.grade_c_traces,
            "grade_d": self.grade_d_traces,
            "grade_e": self.grade_e_traces,
            "average_confidence": round(self.average_confidence, 1),
            "traces": [t.to_dict() for t in self.traces],
        }
        s = json.dumps(data, ensure_ascii=False, indent=2)
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(s)
        return s


# ===== 溯源推理规则 =====

REASONING_RULES = {
    "数额较大": "将涉案金额与入罪门槛比较，判断是否达到'数额较大'标准",
    "数额巨大": "将涉案金额与量刑升档门槛比较，判断是否达到'数额巨大'标准",
    "单位犯罪": "核查犯罪主体是否为单位（公司/企业），判断是否适用单位犯罪条款",
    "共同犯罪": "核查是否存在多人共同故意，判断是否构成共同犯罪",
    "自首": "核查是否存在自动投案+如实供述，判断是否构成自首",
    "立功": "核查是否存在揭发他人犯罪等情形，判断是否构成立功",
    "从犯": "核查在共同犯罪中的作用，判断是否认定为从犯",
    "认罪认罚": "核查是否具结悔过+接受处罚，判断是否适用从宽情节",
    "情节严重": "核查是否存在法定加重情节（如多次犯罪、后果严重等）",
    "特别法优先": "当行为同时符合普通法和特别法时，优先适用特别法",
    "想象竞合": "一个行为触犯多个罪名，从一重罪处罚",
    "牵连犯": "手段行为与目的行为均构成犯罪，择一重罪处罚",
    "法条竞合": "一个罪名被另一罪名完全包含时，适用特殊罪名",
}


class CClaimTracer:
    """
    C-CLAIM 溯源层

    用法：
        # 从 fact_checker 加载
        tracer = CClaimTracer()
        tracer.load_from_fact_checker(fc)
        traces = tracer.get_all_traces()

        # 导出
        report = tracer.generate_report("hengda")
        print(report.to_json("traces.json"))

        # 嵌入报告附录
        md = tracer.generate_markdown_report()
    """

    def __init__(self):
        self._traces: List[CClaimTrace] = []

    def load_from_fact_checker(self, fc) -> int:
        """
        从 FactChecker 实例加载溯源数据

        Returns:
            加载的溯源条数
        """
        from confidence_scorer import ConfidenceScorer

        self._traces = []
        results = fc.results
        fields = results.get("fields", [])

        for f in fields:
            path = f.get("field_path", "")
            value = f.get("value", "")
            grade = f.get("grade", SourceGrade.D)
            source = f.get("source", "")
            notes = f.get("notes", "")

            # 构建 C-CLAIM 溯源链
            trace = self._build_trace(path, value, grade, source, notes, results)
            self._traces.append(trace)

        return len(self._traces)

    def _build_trace(
        self,
        field_path: str,
        value: Any,
        grade: SourceGrade,
        source: str,
        notes: str,
        results: Dict,
    ) -> CClaimTrace:
        """为单个字段构建溯源链"""
        claim = str(value) if value else ""

        # 从 confidence_scorer 获取置信度
        scorer: Optional[ConfidenceScorer] = results.get("_scorer")
        cs = None
        if scorer:
            cs = scorer.assess(
                conclusion=claim,
                matched_statutes=[],
                crime_type=self._infer_crime_type(field_path),
            )

        # 解析 field_path 构建 citation
        citations = self._extract_citations(field_path, value)

        # 推理链
        interp_chain = self._build_interpretation_chain(field_path, value, source, notes)

        # 方法论
        method = self._infer_methodology(field_path, value)

        # 生成 trace_id
        trace_id = hashlib.md5(
            f"{field_path}:{claim}".encode()
        ).hexdigest()[:8]

        return CClaimTrace(
            trace_id=trace_id,
            field_path=field_path,
            claim=claim,
            citation_laws=citations["laws"],
            citation_keywords=citations["keywords"],
            attribution_source=source or "未标注",
            attribution_grade=grade.value if isinstance(grade, SourceGrade) else grade,
            interpretation_chain=interp_chain,
            methodology=method,
            confidence_score=cs.score if cs else 0,
            confidence_level=cs.level if cs else "",
            recommended_action=cs.recommended_action if cs else "",
            uncertainty_reasons=cs.uncertainty_reasons if cs else [],
        )

    def _extract_citations(self, field_path: str, value: Any) -> Dict[str, List[str]]:
        """从字段路径和值中提取引用"""
        laws = []
        keywords = []
        value_str = str(value)

        # 从 field_path 推断
        if "charges_judged" in field_path:
            laws.append("刑法分则相应条款")
            keywords.append("罪名认定")
        if "charges_missed" in field_path:
            laws.append("刑法分则")
            keywords.append("遗漏罪名")
        if "amount" in field_path or "fine" in field_path or "金额" in value_str:
            keywords.extend(["数额较大", "数额巨大", "入罪门槛"])
        if "victim" in field_path:
            keywords.append("被害人")
        if "court" in field_path:
            keywords.append("管辖法院")

        for pattern in _ARTICLE_PATTERNS:
            for m in re.finditer(pattern, value_str):
                laws.append(m.group(0))

        return {"laws": list(dict.fromkeys(laws)), "keywords": list(dict.fromkeys(keywords))}

    def _build_interpretation_chain(
        self,
        field_path: str,
        value: Any,
        source: str,
        notes: str,
    ) -> List[str]:
        """构建推理链"""
        chain = []
        if "charges_judged" in field_path:
            chain.append("核查判决书中记载的罪名名称")
            chain.append("对照新华社原文验证罪名准确性")
            if source == "新华社判决原文":
                chain.append("来源确认为官方一手（GRADE_A）")
            else:
                chain.append("来源为分析推断（GRADE_B），需进一步核实")
        elif "charges_missed" in field_path:
            chain.append("基于刑法分则条文分析遗漏罪名")
            chain.append("评估证据充分性")
            chain.append("给出置信度评估")
        elif "amount" in field_path or "fine" in field_path:
            chain.append("提取涉案金额")
            chain.append("对照司法解释入罪门槛")
            chain.append("判断是否达到追诉标准")
        elif "victim" in field_path:
            chain.append("核查受害者类型和人数")
            chain.append("对照相应罪名被害人要件")
        else:
            chain.append("一般核查字段")

        if notes:
            chain.append(f"备注：{notes[:50]}")
        return chain

    def _infer_methodology(self, field_path: str, value: Any) -> str:
        """推断所使用方法"""
        if "charges_judged" in field_path:
            return "罪名认定：法条对照 + 来源验证"
        if "charges_missed" in field_path:
            return "遗漏罪名分析：要件比对 + 证据充分性评估"
        if "amount" in field_path or "fine" in field_path:
            return "数额判断：入罪门槛比对 + 数额档位分析"
        if "victim" in field_path:
            return "被害人核查：类型分类 + 人数统计"
        return "一般字段核查"

    def _infer_crime_type(self, field_path: str) -> str:
        """从字段路径推断罪名类型"""
        if "charges_judged" in field_path or "charges_missed" in field_path:
            m = re.search(r"charges_[jm]udged\.([\w]+)\.", field_path)
            return m.group(1) if m else ""
        return ""

    def get_all_traces(self) -> List[CClaimTrace]:
        return self._traces

    def get_low_confidence_traces(self, threshold: int = 50) -> List[CClaimTrace]:
        return [t for t in self._traces if t.confidence_score < threshold]

    def get_grade_d_traces(self) -> List[CClaimTrace]:
        return [t for t in self._traces if t.attribution_grade <= 2]

    def generate_report(self, case_id: str) -> TraceReport:
        """生成整体溯源报告"""
        n = len(self._traces)
        grades = [t.attribution_grade for t in self._traces]
        confidences = [t.confidence_score for t in self._traces if t.confidence_score > 0]

        report = TraceReport(
            case_id=case_id,
            total_traces=n,
            grade_a_traces=sum(1 for g in grades if g == 5),
            grade_b_traces=sum(1 for g in grades if g == 4),
            grade_c_traces=sum(1 for g in grades if g == 3),
            grade_d_traces=sum(1 for g in grades if g == 2),
            grade_e_traces=sum(1 for g in grades if g == 1),
            average_confidence=sum(confidences) / len(confidences) if confidences else 0,
            traces=self._traces,
        )
        return report

    def generate_markdown_report(self) -> str:
        """生成 Markdown 格式的溯源报告（用于报告附录）"""
        lines = [
            "# C-CLAIM 溯源报告",
            "",
            "本附录追踪报告中每条法律结论的来源链，确保可验证性和透明度。",
            "",
        ]

        # 统计摘要
        report = self.generate_report("query")
        lines.append("## 溯源统计")
        lines.append(f"- 总溯源条目：{report.total_traces}")
        lines.append(f"- GRADE_A（官方一手）：{report.grade_a_traces}")
        lines.append(f"- GRADE_B（可推断）：{report.grade_b_traces}")
        lines.append(f"- GRADE_C（推测）：{report.grade_c_traces}")
        lines.append(f"- GRADE_D（未知）：{report.grade_d_traces}")
        lines.append(f"- 平均置信度：{report.average_confidence:.1f}/100")
        lines.append("")

        # 低置信度条目
        low_conf = self.get_low_confidence_traces(50)
        if low_conf:
            lines.append(f"## ⚠️ 低置信度结论（< 50/100）")
            for t in low_conf:
                lines.append(f"- **{t.field_path}**：{t.claim}（置信度 {t.confidence_score}/100）")
                if t.uncertainty_reasons:
                    lines.append(f"  原因：{'；'.join(t.uncertainty_reasons)}")
            lines.append("")

        # 详细溯源链（按字段路径排序）
        lines.append("## 详细溯源链")
        for trace in sorted(self._traces, key=lambda t: t.field_path):
            lines.append(trace.to_markdown())
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)


# ===== CLI =====

def main():
    import argparse
    parser = argparse.ArgumentParser(description="C-CLAIM 溯源追踪")
    parser.add_argument("--case", type=str, help="案件ID")
    parser.add_argument("--fact-checker-result", type=str, help="fact_checker 结果 JSON 文件")
    parser.add_argument("--output", type=str, help="输出 JSON 文件路径")
    parser.add_argument("--markdown", action="store_true", help="输出 Markdown 格式")
    parser.add_argument("--low-confidence", action="store_true", help="仅显示低置信度条目")
    args = parser.parse_args()

    tracer = CClaimTracer()

    if args.case:
        # 从案件加载并运行 fact_checker
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from fact_checker import FactChecker
        from case_loader import CaseLoader

        loader = CaseLoader()
        fc = FactChecker(args.case, loader)
        fc.check_all()
        tracer.load_from_fact_checker(fc)
        case_id = args.case
    else:
        case_id = "unknown"

    if args.low_confidence:
        low = tracer.get_low_confidence_traces()
        print(f"\n低置信度条目（< 50/100）：{len(low)} 条")
        for t in low:
            print(f"\n  [{t.field_path}]")
            print(f"  结论：{t.claim}")
            print(f"  置信度：{t.confidence_score}/100 [{t.confidence_level}]")
            print(f"  不确定理由：{'；'.join(t.uncertainty_reasons)}")
    elif args.markdown:
        print(tracer.generate_markdown_report())
    else:
        report = tracer.generate_report(case_id)
        s = report.to_json(args.output)
        print(f"\n溯源报告（案件：{case_id}）")
        print(f"  总条目：{report.total_traces}")
        print(f"  GRADE_A：{report.grade_a_traces} | GRADE_B：{report.grade_b_traces} "
              f"| GRADE_C：{report.grade_c_traces} | GRADE_D：{report.grade_d_traces}")
        print(f"  平均置信度：{report.average_confidence:.1f}/100")
        if args.output:
            print(f"\n✅ 已保存: {args.output}")
        else:
            print(f"\n{s[:500]}...")


if __name__ == "__main__":
    main()
