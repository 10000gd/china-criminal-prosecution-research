# -*- coding: utf-8 -*-
"""
数据聚合统计模块 - prosecution_system/src/stats_aggregator.py

功能：
- 跨案件聚合幻觉率/置信度统计
- 省级数额差异数据聚合
- 涉案公司地域分布统计
- 为 Web 页面提供 JSON API 数据

API 端点（供 web_app 调用）：
  get_hallucination_stats()       — 幻觉率统计
  get_provincial_diffs()          — 省级差异数据
  get_company_geo_stats()         — 公司地域分布
  get_confidence_trend(case_id)   — 置信度趋势
  get_all_stats()                 — 全量统计摘要
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
from functools import lru_cache
import re

from case_loader import CaseLoader
from confidence_scorer import ConfidenceScorer, ConfidenceLevel
from threshold_db import ThresholdDB
from legal_case_db import LegalCaseDB


@dataclass
class HallucinationStat:
    """幻觉率统计"""
    case_id: str
    total_fields: int = 0
    grade_a: int = 0
    grade_b: int = 0
    grade_c: int = 0
    grade_d: int = 0
    grade_e: int = 0
    high_confidence: int = 0
    medium_confidence: int = 0
    low_confidence: int = 0
    unreliable_confidence: int = 0
    average_confidence: float = 0.0
    hallucination_rate: float = 0.0   # (grade_c + grade_d + grade_e) / total
    unreliability_rate: float = 0.0   # (low + unreliable) / total
    timestamp: str = ""


@dataclass
class ProvincialDiff:
    """省级差异数据"""
    crime_type: str
    province: str
    amount_standard: int
    category: str  # 一类/二类/三类地区
    is_default: bool = False


@dataclass
class CompanyGeoStat:
    """涉案公司地域统计"""
    company_name: str
    province: str
    city: str = ""
    case_count: int = 1
    primary_charge: str = ""
    amount: float = 0.0


class StatsAggregator:
    """
    数据聚合统计器

    用法：
        agg = StatsAggregator()
        stats = agg.get_hallucination_stats()
        provincial = agg.get_provincial_diffs()
        geo = agg.get_company_geo_stats()
    """

    def __init__(self):
        self.loader = CaseLoader()
        self.scorer = ConfidenceScorer()
        self.threshold_db = ThresholdDB()
        self._hallucination_cache: Dict[str, HallucinationStat] = {}

    # ===== 幻觉率统计 =====

    def get_hallucination_stats(self, force_recompute: bool = False) -> List[HallucinationStat]:
        """
        获取所有案件的幻觉率统计

        幻觉率 = (grade_c + grade_d + grade_e) / total_fields
        不可靠率 = (low_confidence + unreliable_confidence) / total
        """
        cases = self.loader.list_cases()
        results = []

        for case_meta in cases:
            case_id = case_meta.get("case_id", "")
            if not case_id or not force_recompute:
                # 尝试用缓存
                if case_id in self._hallucination_cache and not force_recompute:
                    results.append(self._hallucination_cache[case_id])
                    continue

            try:
                stat = self._compute_case_stat(case_id)
                if stat:
                    self._hallucination_cache[case_id] = stat
                    results.append(stat)
            except Exception:
                continue

        return results

    def _compute_case_stat(self, case_id: str) -> Optional[HallucinationStat]:
        """计算单个案件的统计"""
        data = self.loader.load(case_id)
        if not data:
            return None

        charges = data.get("charges", {})
        judged = charges.get("charges_judged", {})
        missed = charges.get("charges_missed", {})

        total = len(judged) + len(missed)
        if total == 0:
            return None

        # 各置信度级别计数
        grade_a = grade_b = grade_c = grade_d = grade_e = 0
        high = medium = low = unreliable = 0
        scores = []

        for cid, cdata in judged.items():
            cs = self.scorer.assess(
                conclusion=f"构成{cdata.get('name','')}",
                matched_statutes=[cdata.get("statute", "")] if cdata.get("statute") else [],
                crime_type=cdata.get("name", ""),
            )
            scores.append(cs.score)
            if cs.level == "HIGH":
                high += 1
            elif cs.level == "MEDIUM":
                medium += 1
            elif cs.level == "LOW":
                low += 1
            else:
                unreliable += 1
            # 来源等级分布（从 fact_checker grade 映射）
            # grade_a~e 需从 fact_checker 结果中提取，此处用置信度推断
            if cs.score >= 80:
                grade_a += 1
            elif cs.score >= 60:
                grade_b += 1
            elif cs.score >= 40:
                grade_c += 1
            elif cs.score >= 20:
                grade_d += 1
            else:
                grade_e += 1

        for cid, cdata in missed.items():
            cs = self.scorer.assess(
                conclusion=f"遗漏{cdata.get('name','')}",
                matched_statutes=[],
                crime_type=cdata.get("name", ""),
            )
            scores.append(cs.score)
            if cs.level == "HIGH":
                high += 1
            elif cs.level == "MEDIUM":
                medium += 1
            elif cs.level == "LOW":
                low += 1
            else:
                unreliable += 1
            if cs.score >= 80:
                grade_a += 1
            elif cs.score >= 60:
                grade_b += 1
            elif cs.score >= 40:
                grade_c += 1
            elif cs.score >= 20:
                grade_d += 1
            else:
                grade_e += 1

        avg_score = sum(scores) / len(scores) if scores else 0

        return HallucinationStat(
            case_id=case_id,
            total_fields=total,
            grade_a=grade_a,
            grade_b=grade_b,
            grade_c=grade_c,
            grade_d=grade_d,
            grade_e=grade_e,
            high_confidence=high,
            medium_confidence=medium,
            low_confidence=low,
            unreliable_confidence=unreliable,
            average_confidence=round(avg_score, 1),
            hallucination_rate=round((low + unreliable) / total, 3),
            unreliability_rate=round((low + unreliable) / total, 3),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )

    def get_all_stats(self) -> Dict[str, Any]:
        """全量统计摘要（用于首页仪表板）"""
        hall_stats = self.get_hallucination_stats()
        total_cases = len(hall_stats)
        total_fields = sum(s.total_fields for s in hall_stats)
        avg_hall_rate = (sum(s.hallucination_rate for s in hall_stats) / total_cases
                         if total_cases else 0)
        avg_confidence = (sum(s.average_confidence for s in hall_stats) / total_cases
                          if total_cases else 0)

        return {
            "total_cases": total_cases,
            "total_charge_fields": total_fields,
            "average_hallucination_rate": round(avg_hall_rate, 3),
            "average_confidence": round(avg_confidence, 1),
            "hallucination_rate_trend": [s.hallucination_rate for s in hall_stats],
            "cases": [self._stat_to_dict(s) for s in hall_stats],
        }

    def _stat_to_dict(self, s: HallucinationStat) -> Dict:
        return {
            "case_id": s.case_id,
            "total_fields": s.total_fields,
            "high": s.high_confidence,
            "medium": s.medium_confidence,
            "low": s.low_confidence,
            "unreliable": s.unreliable_confidence,
            "average_confidence": s.average_confidence,
            "hallucination_rate": s.hallucination_rate,
            "timestamp": s.timestamp,
        }

    # ===== 省级差异数据 =====

    def get_provincial_diffs(self) -> Dict[str, Any]:
        """
        聚合省级数额差异数据（用于可视化）

        返回格式：
        {
          "crime_types": ["盗窃罪", "诈骗罪", ...],
          "provinces": [...],
          "data": {
            "盗窃罪": {
              "北京": {"standard": 2000, "category": "统一标准"},
              "广东": {"standard": 3000, "category": "三类地区"},
              ...
            },
            ...
          },
          "max_amount": 100000,  # 用于图表纵轴
        }
        """
        # 省级标准（已在模块级预计算，避免重复 regex）
        theft_provinces, fraud_provinces, robbery_provinces = _build_provincial_stats(
            self.threshold_db
        )

        all_amounts = (
            [v["amount"] for v in theft_provinces.values()] +
            [v["amount"] for v in fraud_provinces.values()] +
            [v["amount"] for v in robbery_provinces.values()]
        )

        return {
            "crime_types": ["盗窃罪", "诈骗罪", "抢夺罪"],
            "provinces": sorted(set(
                list(theft_provinces.keys()) +
                list(fraud_provinces.keys()) +
                list(robbery_provinces.keys())
            )),
            "data": {
                "盗窃罪": theft_provinces,
                "诈骗罪": fraud_provinces,
                "抢夺罪": robbery_provinces,
            },
            "max_amount": max(all_amounts) if all_amounts else 100000,
        }

    # ===== 涉案公司地域分布 =====

    def get_company_geo_stats(self) -> Dict[str, Any]:
        """
        聚合涉案公司地域分布

        从所有案件 YAML 中提取公司名称和地域信息
        """
        companies: Dict[str, CompanyGeoStat] = {}
        cases = self.loader.list_cases()

        for case_meta in cases:
            case_id = case_meta.get("case_id", "")
            if not case_id:
                continue
            try:
                data = self.loader.load(case_id)
                if not data:
                    continue

                # 提取涉案公司
                case_info = data.get("case_info", {})
                defendants = case_info.get("defendants", [])

                for d in defendants:
                    if isinstance(d, str):
                        name = d
                        province = self._extract_province(name) or case_info.get("province", "未知")
                    elif isinstance(d, dict):
                        name = d.get("name", "")
                        province = d.get("province", case_info.get("province", "未知"))
                    else:
                        continue

                    if not name:
                        continue

                    if name in companies:
                        companies[name].case_count += 1
                    else:
                        charge = self._primary_charge(data)
                        amount = self._case_amount(data)
                        companies[name] = CompanyGeoStat(
                            company_name=name,
                            province=province,
                            city="",
                            case_count=1,
                            primary_charge=charge,
                            amount=amount,
                        )
            except Exception:
                continue

        # 统计
        company_list = [c for c in companies.values()]
        by_province: Dict[str, int] = defaultdict(int)
        for c in company_list:
            by_province[c.province] += 1

        return {
            "total_companies": len(company_list),
            "companies": [
                {
                    "name": c.company_name,
                    "province": c.province,
                    "case_count": c.case_count,
                    "primary_charge": c.primary_charge,
                    "amount": c.amount,
                }
                for c in sorted(company_list, key=lambda x: x.case_count, reverse=True)
            ],
            "by_province": dict(sorted(by_province.items(), key=lambda x: -x[1])),
            "top_provinces": sorted(by_province.items(), key=lambda x: -x[1])[:10],
        }

    def _extract_province(self, company_name: str) -> Optional[str]:
        """从公司名推断省份"""
        import re
        province_keywords = {
            "北京": ["北京"], "上海": ["上海"], "广东": ["广东", "广州", "深圳"],
            "浙江": ["浙江", "杭州"], "江苏": ["江苏", "南京", "苏州"],
            "四川": ["四川", "成都"], "湖北": ["湖北", "武汉"],
            "山东": ["山东", "济南"], "福建": ["福建", "福州", "厦门"],
            "天津": ["天津"], "重庆": ["重庆"], "河南": ["河南", "郑州"],
            "辽宁": ["辽宁", "沈阳"], "湖南": ["湖南", "长沙"],
            "安徽": ["安徽", "合肥"], "陕西": ["陕西", "西安"],
            "河北": ["河北", "石家庄"], "江西": ["江西", "南昌"],
            "云南": ["云南", "昆明"], "贵州": ["贵州", "贵阳"],
            "广西": ["广西", "南宁"], "海南": ["海南", "海口"],
        }
        for prov, keywords in province_keywords.items():
            if any(kw in company_name for kw in keywords):
                return prov
        return None

    def _primary_charge(self, data: Dict) -> str:
        charges = data.get("charges", {})
        judged = charges.get("charges_judged", {})
        if judged:
            first = list(judged.values())[0]
            return first.get("name", "")
        return ""

    def _case_amount(self, data: Dict) -> float:
        fi = data.get("financial_info", {})
        return float(fi.get("total_amount", fi.get("amount", 0)))

PROVINCE_TIER1 = frozenset({"北京", "上海", "江苏", "浙江", "广东", "深圳"})
PROVINCE_TIER2 = frozenset({"天津", "重庆", "福建", "山东", "四川", "湖北", "湖南", "河南",
                             "辽宁", "陕西", "安徽", "河北"})
_NUM_PATTERN = re.compile(r"\d+")


def _province_category(province: str) -> str:
    if province in PROVINCE_TIER1:
        return "一类地区（经济发达）"
    elif province in PROVINCE_TIER2:
        return "二类地区（中等发达）"
    return "三类地区（欠发达）"


@lru_cache(maxsize=1)
def _build_provincial_stats(tdb) -> tuple:
    """构建省级标准（缓存避免重复计算，缓存键基于 tdb 对象id）"""
    theft = {}
    for prov, data in tdb.theft_thresholds.items():
        if prov == "DEFAULT":
            continue
        std = data.get("standard", "")
        nums = _NUM_PATTERN.findall(std)
        amount = int(nums[0]) if nums else 0
        theft[prov] = {"standard": std, "amount": amount, "category": _province_category(prov)}

    fraud = {}
    for prov, data in tdb.fraud_thresholds.items():
        if prov == "DEFAULT":
            continue
        std = data.get("standard", "")
        nums = _NUM_PATTERN.findall(std)
        amount = int(nums[0]) if nums else 0
        fraud[prov] = {"standard": std, "amount": amount, "category": _province_category(prov)}

    robbery = {}
    for prov, data in tdb.robbery_thresholds.items():
        if prov == "DEFAULT":
            continue
        amount = data if isinstance(data, int) else (
            data.get("standard", 0) if isinstance(data, dict) else 0)
        std = f"{amount}元（数额较大）" if amount else ""
        robbery[prov] = {"standard": std, "amount": amount, "category": _province_category(prov)}

    return theft, fraud, robbery

# ===== CLI =====

def main():
    import argparse
    parser = argparse.ArgumentParser(description="数据聚合统计")
    parser.add_argument("--hallucination", action="store_true", help="幻觉率统计")
    parser.add_argument("--provincial", action="store_true", help="省级差异数据")
    parser.add_argument("--geo", action="store_true", help="公司地域分布")
    parser.add_argument("--all", action="store_true", help="全量统计")
    parser.add_argument("--json", type=str, help="输出JSON文件")
    args = parser.parse_args()

    agg = StatsAggregator()

    if args.hallucination:
        stats = agg.get_hallucination_stats()
        data = {"cases": [agg._stat_to_dict(s) for s in stats]}
        s = json.dumps(data, ensure_ascii=False, indent=2)
        print(s if not args.json else "")
        if args.json:
            with open(args.json, 'w') as f:
                f.write(s)
            print(f"✅ 已保存: {args.json}")

    elif args.provincial:
        data = agg.get_provincial_diffs()
        s = json.dumps(data, ensure_ascii=False, indent=2)
        print(s if not args.json else "")
        if args.json:
            with open(args.json, 'w') as f:
                f.write(s)
            print(f"✅ 已保存: {args.json}")

    elif args.geo:
        data = agg.get_company_geo_stats()
        s = json.dumps(data, ensure_ascii=False, indent=2)
        print(s if not args.json else "")
        if args.json:
            with open(args.json, 'w') as f:
                f.write(s)
            print(f"✅ 已保存: {args.json}")

    elif args.all:
        data = agg.get_all_stats()
        print(json.dumps(data, ensure_ascii=False, indent=2))

    else:
        print("用法: --hallucination | --provincial | --geo | --all [--json 文件]")


if __name__ == "__main__":
    main()
