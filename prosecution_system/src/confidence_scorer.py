# -*- coding: utf-8 -*-
"""
法律结论置信度评估器 - prosecution_system/src/confidence_scorer.py
为每条法律结论生成置信度评分（0-100），防止系统幻觉
"""
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

class ConfidenceLevel:
    HIGH = "HIGH"; MEDIUM = "MEDIUM"; LOW = "LOW"; UNRELIABLE = "UNRELIABLE"
    LABELS = {
        HIGH: "✅ 高置信度", MEDIUM: "🔶 中等置信度",
        LOW: "⚠️ 低置信度（需人工核查）", UNRELIABLE: "❌ 不可靠（必须人工核查）",
    }
    DESCRIPTIONS = {
        HIGH: "法条原文直接匹配，无歧义，来源可靠，可直接引用",
        MEDIUM: "基于法条和司法解释的推断，逻辑合理，但存在其他解释可能",
        LOW: "基于类比或部分匹配，存在多种解释，引用时必须标注不确定性",
        UNRELIABLE: "无法确定是否正确，系统无法保证结论准确性，必须人工核查",
    }

def _level(score: int) -> str:
    if score >= 80: return ConfidenceLevel.HIGH
    if score >= 50: return ConfidenceLevel.MEDIUM
    if score >= 20: return ConfidenceLevel.LOW
    return ConfidenceLevel.UNRELIABLE

INTERPRETATION_STATUS: Dict[str, Tuple[str, str, Optional[str]]] = {
    "最高法关于审理非法集资刑事案件具体应用法律若干问题的解释": ("ACTIVE", "现行有效", None),
    "最高法关于审理非法吸收公众存款刑事案件具体应用法律若干问题的解释": ("ACTIVE", "现行有效", None),
    "最高检公安部关于公安机关管辖的刑事案件立案追诉标准的规定（一）": ("ACTIVE", "现行有效（2022版）", None),
    "最高检公安部关于公安机关管辖的刑事案件立案追诉标准的规定（二）": ("ACTIVE", "现行有效", None),
    "最高法最高检关于办理盗窃刑事案件适用法律若干问题的解释": ("ACTIVE", "现行有效（2013）", None),
    "最高法关于审理诈骗刑事案件具体应用法律若干问题的解释": ("SUPERSEDED", "已被2022新解释替代", "2022-01-01"),
}

@dataclass
class ConfidenceScore:
    score: int; level: str; label: str; description: str
    dimensions: Dict[str, int] = field(default_factory=dict)
    uncertainty_reasons: List[str] = field(default_factory=list)
    source_statutes: List[str] = field(default_factory=list)
    recommended_action: str = ""

@dataclass
class ConfidenceReport:
    total_conclusions: int = 0; high: int = 0; medium: int = 0
    low: int = 0; unreliable: int = 0; average_score: float = 0.0
    conclusions: List[Dict[str, Any]] = field(default_factory=list)
    overall_recommendation: str = ""

class ConfidenceScorer:
    def __init__(self, db_dir: Path = None):
        if db_dir is None:
            db_dir = Path(__file__).parent.parent / "cases" / "legaldb"
        self.db_dir = db_dir; self._cache: Dict[str, str] = {}

    def assess(self, conclusion: str, matched_statutes: List[str] = None,
               matched_interpretations: List[str] = None, is_direct_quote: bool = False,
               province: str = None, crime_type: str = None) -> ConfidenceScore:
        matched_statutes = matched_statutes or []; matched_interpretations = matched_interpretations or []
        dm = {}
        dm["text_match"] = self._t_match(conclusion, matched_statutes, is_direct_quote)
        dm["currency"] = self._t_currency(matched_interpretations)
        dm["source_count"] = self._t_source(matched_statutes, matched_interpretations)
        dm["semantic"] = self._t_semantic(conclusion, crime_type)
        dm["regional"] = self._t_regional(conclusion, province, crime_type)
        score = self._compute(dm); reasons = self._reasons(dm, matched_interpretations, province, crime_type)
        lv = _level(score)
        return ConfidenceScore(score=score, level=lv, label=ConfidenceLevel.LABELS[lv],
            description=ConfidenceLevel.DESCRIPTIONS[lv], dimensions=dm,
            uncertainty_reasons=reasons, source_statutes=matched_statutes,
            recommended_action=self._action(lv, reasons))

    def assess_batch(self, conclusions: List[Dict[str, Any]]) -> ConfidenceReport:
        results = []; h = m = l = u = total = 0
        for i, c in enumerate(conclusions):
            cs = self.assess(conclusion=c.get("text",""), matched_statutes=c.get("matched_statutes",[]),
                matched_interpretations=c.get("matched_interpretations",[]),
                is_direct_quote=c.get("is_direct_quote", False),
                province=c.get("province"), crime_type=c.get("crime_type"))
            total += cs.score
            if cs.level == ConfidenceLevel.HIGH: h += 1
            elif cs.level == ConfidenceLevel.MEDIUM: m += 1
            elif cs.level == ConfidenceLevel.LOW: l += 1
            else: u += 1
            results.append({"index": i, "text": c.get("text",""), "confidence": {
                "score": cs.score, "level": cs.level, "label": cs.label,
                "dimensions": cs.dimensions, "uncertainty_reasons": cs.uncertainty_reasons,
                "recommended_action": cs.recommended_action}})
        n = len(conclusions)
        avg = round(total/n, 1) if n > 0 else 0.0
        rec = self._overall_rec(h, m, l, u, n)
        return ConfidenceReport(total_conclusions=n, high=h, medium=m, low=l,
            unreliable=u, average_score=avg, conclusions=results, overall_recommendation=rec)

    def _t_match(self, c: str, s: List[str], q: bool) -> int:
        if q and s: return 95
        if len(s) >= 2: return 85
        if s: return 75
        return 30

    def _t_currency(self, itprs: List[str]) -> int:
        if not itprs: return 100
        active_count = unknown_count = superseded_count = 0
        for i in itprs:
            st = self._status(i)
            if st == "ACTIVE": active_count += 1
            elif st == "UNKNOWN": unknown_count += 1
            else: superseded_count += 1
        if superseded_count > 0: return 15
        if unknown_count > 0: return 50
        return 90

    def _status(self, interp: str) -> str:
        if interp in self._cache: return self._cache[interp]
        for key, (st, *_) in INTERPRETATION_STATUS.items():
            if key in interp or interp in key:
                self._cache[interp] = st; return st
        self._cache[interp] = "UNKNOWN"; return "UNKNOWN"

    def _t_source(self, s: List[str], itprs: List[str]) -> int:
        n = len(s) + len(itprs)
        return 90 if n >= 3 else (75 if n == 2 else (55 if n == 1 else 25))

    def _t_semantic(self, c: str, ct: str = None) -> int:
        amb = ["可能构成","疑似","或许","有待核实","原则上","可参照","一般认为","各地不一","存在争议"]
        crit = ["构成","属于","应当","必须","认定为"]
        ac = sum(1 for p in amb if p in c); cc = sum(1 for p in crit if p in c)
        if ac >= 2: return 30
        if cc >= 2: return 40
        if ac == 1: return 55
        if cc >= 1: return 65
        return 80

    def _t_regional(self, c: str, prov: str = None, ct: str = None) -> int:
        sensitive = ["盗窃罪","诈骗罪","抢夺罪","敲诈勒索罪","开设赌场罪"]
        has_p = bool(prov); needs_p = ct in sensitive if ct else False
        if needs_p and not has_p: return 30
        if needs_p and has_p: return 70
        return 85 if has_p else 90

    def _compute(self, dm: Dict[str, int]) -> int:
        w = {"text_match":0.35,"currency":0.25,"source_count":0.15,"semantic":0.15,"regional":0.10}
        wtd = sum(dm.get(k,50)*v for k,v in w.items())
        mn = min(dm.values()) if dm else 50
        return int(wtd*0.7 + mn*0.3)

    def _reasons(self, dm: Dict[str,int], itprs, prov, ct) -> List[str]:
        r = []
        if dm.get("text_match",100) < 60: r.append("无法溯源至具体法条条文")
        if dm.get("currency",100) < 70: r.append("引用的司法解释时效性无法确认（建议核查两高官网）")
        if dm.get("source_count",100) < 50: r.append("单一来源支持，结论可能存在偏颇")
        if dm.get("semantic",100) < 50: r.append("结论表述存在歧义或不确定措辞")
        if dm.get("regional",100) < 60 and ct in ["盗窃罪","诈骗罪","抢夺罪","敲诈勒索罪"]:
            r.append("涉及省级数额标准，未指定省份时结论不可靠")
        return r

    def _action(self, lv: str, reasons: List[str]) -> str:
        if lv == ConfidenceLevel.HIGH: return "可直接引用，标注【高置信度】"
        if lv == ConfidenceLevel.MEDIUM: return "可引用，须标注【中等置信度】并注明推断依据"
        if lv == ConfidenceLevel.LOW: return "⚠️ 引用须谨慎，标注【低置信度-需人工核查】"
        return f"❌ 不得输出此结论。必须人工核查。原因：{'；'.join(reasons) or '无法确定准确性'}"

    def _overall_rec(self, h, m, l, u, n) -> str:
        if n == 0: return "无结论可评估"
        ur = u/n; lr = (l+u)/n
        if ur > 0.3: return f"⚠️ 警告：{u}条({int(ur*100)}%)不可靠，需全面人工审查"
        if lr > 0.5: return f"⚠️ 注意：{l+u}条({int(lr*100)}%)置信度低，引用前须逐一核查"
        if h/n > 0.8: return "✅ 整体置信度良好，高置信度结论占比高，可正常引用"
        return f"整体可用，但{int(lr*100)}%低置信度结论需注意，引用时务必标注等级"

def main():
    import argparse
    parser = argparse.ArgumentParser(description="法律结论置信度评估")
    parser.add_argument("--text",type=str); parser.add_argument("--statutes",type=str)
    parser.add_argument("--interpretations",type=str); parser.add_argument("--crime",type=str)
    parser.add_argument("--province",type=str); parser.add_argument("--batch",type=str)
    args = parser.parse_args()
    scorer = ConfidenceScorer()
    if args.batch:
        with open(args.batch, encoding="utf-8") as f:
            conclusions = json.load(f)
        r = scorer.assess_batch(conclusions)
        print(json.dumps({"total":r.total_conclusions,"high":r.high,"medium":r.medium,
            "low":r.low,"unreliable":r.unreliable,"average_score":r.average_score,
            "overall_recommendation":r.overall_recommendation,"conclusions":r.conclusions},
            ensure_ascii=False, indent=2)); return
    stats = [s.strip() for s in (args.statutes or "").split(",") if s.strip()]
    itprs = [i.strip() for i in (args.interpretations or "").split(",") if i.strip()]
    cs = scorer.assess(args.text or "", stats, itprs, province=args.province, crime_type=args.crime)
    dim_labels = {"text_match":"文本匹配度","currency":"时效性","source_count":"来源数量",
                  "semantic":"语义一致性","regional":"地域差异"}
    print(f"\n置信度: {cs.score}/100 [{cs.label}]  {cs.description}")
    if cs.uncertainty_reasons: print("不确定性原因: " + "; ".join(cs.uncertainty_reasons))
    print(f"建议操作: {cs.recommended_action}")
    print("\n各维度:")
    for k, v in cs.dimensions.items():
        bar = "█"*(v//5) + "░"*(20-v//5)
        print(f"  {dim_labels.get(k,k):8s}: {v:3d}/100 |{bar}|")

if __name__ == "__main__": main()
