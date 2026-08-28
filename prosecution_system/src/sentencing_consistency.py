# -*- coding: utf-8 -*-
"""
量刑一致性分析模块 - sentencing_consistency.py

分析量刑的一致性问题：
- 各省量刑差异分析
- 罪名量刑区间统计
- 个案偏离度检测
- 可视化报告生成

数据来源：sentencing_cases.py
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime
import statistics

from sentencing_cases import SENTENCING_CASES


@dataclass
class SentencingRecord:
    """量刑记录"""
    case_id: str
    case_name: str
    crime: str  # 罪名
    province: Optional[str] = None  # 省份
    city: Optional[str] = None  # 城市
    court: Optional[str] = None  # 法院
    
    # 量刑信息
    sentence_type: str = ""  # 有期徒刑/拘役/缓刑/罚金等
    sentence_years: Optional[float] = None  # 年数（浮点数）
    sentence_months: Optional[int] = None  # 月数
    fine: Optional[int] = None  # 罚金
    
    # 案件特征
    amount: Optional[float] = None  # 涉案金额
    is_累犯: bool = False
    is_自首: bool = False
    is_立功: bool = False
    is_坦白: bool = False
    is_赔偿: bool = False
    is_谅解: bool = False
    is_退赃: bool = False
    is_初犯: bool = True
    
    # 元数据
    year: Optional[int] = None
    source: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "case_id": self.case_id,
            "case_name": self.case_name,
            "crime": self.crime,
            "province": self.province,
            "sentence_display": self._sentence_display(),
            "amount": self.amount,
            "year": self.year,
        }
    
    def _sentence_display(self) -> str:
        parts = []
        if self.sentence_years:
            parts.append(f"{self.sentence_years}年")
        if self.sentence_months:
            parts.append(f"{self.sentence_months}个月")
        if self.sentence_type:
            parts.append(self.sentence_type)
        if self.fine:
            parts.append(f"罚金{self.fine}万元")
        return "".join(parts) if parts else "未知"


@dataclass
class SentencingStats:
    """量刑统计数据"""
    crime: str
    sample_count: int
    
    # 基本统计
    avg_sentence: Optional[float] = None  # 平均刑期（年）
    median_sentence: Optional[float] = None  # 中位数
    min_sentence: Optional[float] = None  # 最短
    max_sentence: Optional[float] = None  # 最大
    std_dev: Optional[float] = None  # 标准差
    
    # 区间分布
    sentence_distribution: Dict[str, int] = field(default_factory=dict)
    
    # 缓刑率
    probation_rate: float = 0.0  # 百分比
    
    # 省份分布
    province_stats: Dict[str, Dict] = field(default_factory=dict)
    
    # 特征分布
    mitigating_factors: Dict[str, int] = field(default_factory=dict)
    aggravating_factors: Dict[str, int] = field(default_factory=dict)


@dataclass
class DeviationAnalysis:
    """偏离度分析"""
    case_id: str
    crime: str
    
    # 偏离度
    deviation_score: float  # 偏离度分数（0-100，0表示无偏离）
    deviation_type: str  # "偏重" / "偏轻" / "正常"
    
    # 基准值
    expected_sentence: float  # 期望刑期
    actual_sentence: float   # 实际刑期
    
    # 影响因素
    factors: List[str] = field(default_factory=list)
    deviation_reasons: List[str] = field(default_factory=list)
    
    # 相似案例对比
    similar_cases: List[Dict] = field(default_factory=list)
    
    # 建议
    recommendation: str = ""


class SentencingConsistencyAnalyzer:
    """量刑一致性分析引擎"""
    
    # 内置典型案例数据
    BUILTIN_RECORDS = SENTENCING_CASES
    
    # 法定量刑区间（刑法规定）
    LEGAL_SENTENCING_RANGES = {
        "盗窃罪": {"min": 0.08, "max": 10, "unit": "年", "基准": "盗窃公私财物，数额较大的..."},
        "诈骗罪": {"min": 0.25, "max": 10, "unit": "年", "基准": "诈骗公私财物，数额较大的..."},
        "故意伤害罪": {"min": 0.25, "max": 10, "unit": "年", "基准": "故意伤害他人身体的..."},
        "危险驾驶罪": {"min": 1/12, "max": 0.5, "unit": "月", "基准": "在道路上醉酒驾驶机动车的..."},
        "交通肇事罪": {"min": 0.33, "max": 7, "unit": "年", "基准": "违反交通运输管理法规，因而发生重大事故..."},
        "职务侵占罪": {"min": 0.25, "max": 15, "unit": "年", "基准": "公司、企业或者其他单位的人员，利用职务上的便利..."},
        "非法吸收公众存款罪": {"min": 0.33, "max": 10, "unit": "年", "基准": "非法吸收公众存款或者变相吸收公众存款..."},
    }
    
    def __init__(self, records_path: Optional[Path] = None):
        """初始化分析器"""
        self._records: List[SentencingRecord] = []
        self._records_by_crime: Dict[str, List[SentencingRecord]] = defaultdict(list)
        self._records_by_province: Dict[str, List[SentencingRecord]] = defaultdict(list)
        
        self._load_builtin_records()
    
    def _load_builtin_records(self):
        """加载内置案例"""
        for record_data in self.BUILTIN_RECORDS:
            record = SentencingRecord(**record_data)
            self._add_record(record)
    
    def _add_record(self, record: SentencingRecord):
        """添加记录到索引"""
        self._records.append(record)
        self._records_by_crime[record.crime].append(record)
        if record.province:
            self._records_by_province[record.province].append(record)
    
    def get_stats_by_crime(self, crime: str) -> SentencingStats:
        """获取特定罪名的量刑统计"""
        records = self._records_by_crime.get(crime, [])
        
        if not records:
            return SentencingStats(crime=crime, sample_count=0)
        
        sentences = []
        for r in records:
            if r.sentence_years:
                sentences.append(r.sentence_years)
            elif r.sentence_months:
                sentences.append(r.sentence_months / 12)
        
        if not sentences:
            return SentencingStats(crime=crime, sample_count=len(records))
        
        stats = SentencingStats(
            crime=crime,
            sample_count=len(records),
            avg_sentence=statistics.mean(sentences),
            median_sentence=statistics.median(sentences),
            min_sentence=min(sentences),
            max_sentence=max(sentences),
            std_dev=statistics.stdev(sentences) if len(sentences) > 1 else 0,
        )
        
        stats.sentence_distribution = self._calculate_distribution(sentences)
        probation_count = sum(1 for s in sentences if s <= 1)
        stats.probation_rate = probation_count / len(sentences) * 100
        
        province_sentences = defaultdict(list)
        for r in records:
            if r.province and r.sentence_years:
                province_sentences[r.province].append(r.sentence_years)
        
        for province, sents in province_sentences.items():
            stats.province_stats[province] = {
                "avg": round(statistics.mean(sents), 2),
                "count": len(sents),
                "min": min(sents),
                "max": max(sents),
            }
        
        for r in records:
            if r.is_自首:
                stats.mitigating_factors["自首"] = stats.mitigating_factors.get("自首", 0) + 1
            if r.is_立功:
                stats.mitigating_factors["立功"] = stats.mitigating_factors.get("立功", 0) + 1
            if r.is_坦白:
                stats.mitigating_factors["坦白"] = stats.mitigating_factors.get("坦白", 0) + 1
            if r.is_赔偿:
                stats.mitigating_factors["赔偿"] = stats.mitigating_factors.get("赔偿", 0) + 1
            if r.is_谅解:
                stats.mitigating_factors["谅解"] = stats.mitigating_factors.get("谅解", 0) + 1
            if r.is_累犯:
                stats.aggravating_factors["累犯"] = stats.aggravating_factors.get("累犯", 0) + 1
        
        return stats
    
    def _calculate_distribution(self, sentences: List[float]) -> Dict[str, int]:
        """计算刑期区间分布"""
        distribution = {"不满1年": 0, "1-3年": 0, "3-5年": 0, "5-10年": 0, "10年以上": 0}
        for s in sentences:
            if s < 1:
                distribution["不满1年"] += 1
            elif s < 3:
                distribution["1-3年"] += 1
            elif s < 5:
                distribution["3-5年"] += 1
            elif s < 10:
                distribution["5-10年"] += 1
            else:
                distribution["10年以上"] += 1
        return distribution
    
    def get_provincial_comparison(self, crime: str = None) -> Dict:
        """获取各省量刑对比"""
        if crime:
            records = self._records_by_crime.get(crime, [])
        else:
            records = self._records
        
        province_data = defaultdict(lambda: {"sentences": [], "count": 0, "crimes": defaultdict(int)})
        
        for r in records:
            if r.province and r.sentence_years:
                province_data[r.province]["sentences"].append(r.sentence_years)
                province_data[r.province]["count"] += 1
                province_data[r.province]["crimes"][r.crime] += 1
        
        result = {}
        for province, data in province_data.items():
            sentences = data["sentences"]
            result[province] = {
                "count": data["count"],
                "avg_sentence": round(statistics.mean(sentences), 2),
                "min_sentence": min(sentences),
                "max_sentence": max(sentences),
                "std_dev": round(statistics.stdev(sentences), 2) if len(sentences) > 1 else 0,
                "crimes": dict(data["crimes"]),
            }
        
        all_sentences = []
        for data in province_data.values():
            all_sentences.extend(data["sentences"])
        
        if all_sentences:
            national_avg = statistics.mean(all_sentences)
            for province in result:
                result[province]["deviation_from_avg"] = round(
                    (result[province]["avg_sentence"] - national_avg) / national_avg * 100, 1
                )
                result[province]["deviation_type"] = (
                    "偏重" if result[province]["avg_sentence"] > national_avg else "偏轻"
                )
        
        return result
    
    def analyze_deviation(self, case_data: Dict) -> DeviationAnalysis:
        """分析个案的量刑偏离度"""
        crime = case_data.get("crime", "")
        actual_sentence = case_data.get("sentence_years", 0)
        province = case_data.get("province", "")
        
        stats = self.get_stats_by_crime(crime)
        
        if stats.sample_count == 0 or stats.avg_sentence is None:
            return DeviationAnalysis(
                case_id=case_data.get("case_id", "unknown"),
                crime=crime,
                deviation_score=50,
                deviation_type="数据不足",
                expected_sentence=0,
                actual_sentence=actual_sentence,
                recommendation="数据不足，无法进行偏离度分析"
            )
        
        expected = stats.avg_sentence
        
        if province:
            provincial_data = self.get_provincial_comparison(crime)
            if province in provincial_data:
                expected = provincial_data[province]["avg_sentence"]
        
        if expected > 0:
            deviation_ratio = abs(actual_sentence - expected) / expected
            deviation_score = min(100, deviation_ratio * 100)
        else:
            deviation_score = 50
        
        if actual_sentence > expected * 1.2:
            deviation_type = "偏重"
        elif actual_sentence < expected * 0.8:
            deviation_type = "偏轻"
        else:
            deviation_type = "正常"
        
        factors = []
        deviation_reasons = []
        
        if case_data.get("is_自首"):
            factors.append("自首")
            deviation_reasons.append("自首可以从轻或减轻处罚")
        if case_data.get("is_立功"):
            factors.append("立功")
            deviation_reasons.append("立功可以从轻或减轻处罚")
        if case_data.get("is_坦白"):
            factors.append("坦白")
            deviation_reasons.append("坦白可以从轻处罚")
        if case_data.get("is_赔偿"):
            factors.append("赔偿")
            deviation_reasons.append("积极赔偿可从轻处罚")
        if case_data.get("is_谅解"):
            factors.append("谅解")
            deviation_reasons.append("获得谅解可从轻处罚")
        if case_data.get("is_累犯"):
            factors.append("累犯")
            deviation_reasons.append("累犯应当从重处罚")
        if case_data.get("is_初犯") and not case_data.get("is_累犯"):
            factors.append("初犯")
            deviation_reasons.append("初犯可酌情从轻")
        
        similar_cases = self._find_similar_cases(crime, actual_sentence)
        
        if deviation_score > 30:
            recommendation = f"该案量刑与同类案件存在{deviation_type}，建议关注。"
        else:
            recommendation = "该案量刑在正常范围内。"
        
        if deviation_type == "偏重" and factors:
            recommendation += f" 被告人具有{', '.join(factors)}等从轻情节，可考虑进一步从宽。"
        elif deviation_type == "偏轻":
            recommendation += " 量刑已体现从宽。"
        
        return DeviationAnalysis(
            case_id=case_data.get("case_id", "unknown"),
            crime=crime,
            deviation_score=round(deviation_score, 1),
            deviation_type=deviation_type,
            expected_sentence=round(expected, 2),
            actual_sentence=actual_sentence,
            factors=factors,
            deviation_reasons=deviation_reasons,
            similar_cases=similar_cases,
            recommendation=recommendation,
        )
    
    def _find_similar_cases(self, crime: str, sentence: float, limit: int = 3) -> List[Dict]:
        """查找相似案例"""
        records = self._records_by_crime.get(crime, [])
        scored = []
        for r in records:
            if r.sentence_years:
                diff = abs(r.sentence_years - sentence)
                scored.append((diff, r))
        scored.sort(key=lambda x: x[0])
        return [r.to_dict() for _, r in scored[:limit]]
    
    def get_legal_comparison(self, crime: str) -> Dict:
        """获取法定量刑区间与实际量刑对比"""
        legal_range = self.LEGAL_SENTENCING_RANGES.get(crime, {})
        stats = self.get_stats_by_crime(crime)
        return {
            "crime": crime,
            "legal_range": legal_range,
            "actual_stats": {
                "avg": round(stats.avg_sentence, 2) if stats.avg_sentence else None,
                "median": round(stats.median_sentence, 2) if stats.median_sentence else None,
                "min": round(stats.min_sentence, 2) if stats.min_sentence else None,
                "max": round(stats.max_sentence, 2) if stats.max_sentence else None,
                "std_dev": round(stats.std_dev, 2) if stats.std_dev else 0,
            },
            "sample_count": stats.sample_count,
        }
    
    def generate_report(self, crime: str = None) -> Dict:
        """生成量刑一致性报告"""
        if crime:
            crimes = [crime]
        else:
            crimes = list(self._records_by_crime.keys())
        
        crime_stats = {}
        for c in crimes:
            stats = self.get_stats_by_crime(c)
            crime_stats[c] = {
                "sample_count": stats.sample_count,
                "avg_sentence": round(stats.avg_sentence, 2) if stats.avg_sentence else None,
                "median_sentence": round(stats.median_sentence, 2) if stats.median_sentence else None,
                "std_dev": round(stats.std_dev, 2) if stats.std_dev else 0,
                "distribution": stats.sentence_distribution,
                "probation_rate": round(stats.probation_rate, 1),
                "province_stats": stats.province_stats,
            }
        
        provincial_comparison = self.get_provincial_comparison(crime)
        
        return {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "crime": crime or "全部",
            "total_records": len(self._records),
            "crime_stats": crime_stats,
            "provincial_comparison": provincial_comparison,
            "summary": self._generate_summary(crime_stats, provincial_comparison),
        }
    
    def _generate_summary(self, crime_stats: Dict, provincial_comparison: Dict) -> str:
        """生成报告摘要"""
        summaries = []
        for crime, stats in crime_stats.items():
            if stats["avg_sentence"]:
                summaries.append(f"{crime}平均刑期{stats['avg_sentence']}年(样本{stats['sample_count']}件)")
        
        if provincial_comparison:
            provinces = list(provincial_comparison.keys())
            if len(provinces) >= 2:
                sorted_provinces = sorted(provincial_comparison.items(), key=lambda x: x[1]["avg_sentence"])
                lightest = sorted_provinces[0]
                heaviest = sorted_provinces[-1]
                diff_pct = (heaviest[1]["avg_sentence"] - lightest[1]["avg_sentence"]) / lightest[1]["avg_sentence"] * 100 if lightest[1]["avg_sentence"] > 0 else 0
                summaries.append(f"各省差异最大{diff_pct:.1f}%：{lightest[0]}最轻({lightest[1]['avg_sentence']}年) vs {heaviest[0]}最重({heaviest[1]['avg_sentence']}年)")
        
        return "；".join(summaries) if summaries else "数据不足"


def analyze_sentencing(case_data: Dict) -> Dict:
    """便捷函数：分析个案量刑偏离度"""
    analyzer = SentencingConsistencyAnalyzer()
    result = analyzer.analyze_deviation(case_data)
    return {
        "case_id": result.case_id,
        "crime": result.crime,
        "deviation_score": result.deviation_score,
        "deviation_type": result.deviation_type,
        "expected_sentence": result.expected_sentence,
        "actual_sentence": result.actual_sentence,
        "factors": result.factors,
        "similar_cases": result.similar_cases,
        "recommendation": result.recommendation,
    }


def get_sentencing_report(crime: str = None) -> Dict:
    """便捷函数：获取量刑一致性报告"""
    analyzer = SentencingConsistencyAnalyzer()
    return analyzer.generate_report(crime)


if __name__ == "__main__":
    print("=== 量刑一致性分析测试 ===\n")
    analyzer = SentencingConsistencyAnalyzer()
    
    print("1. 各罪名统计：")
    for crime in ["盗窃罪", "诈骗罪", "故意伤害罪"]:
        stats = analyzer.get_stats_by_crime(crime)
        print(f"   {crime}: {stats.sample_count}件, 平均{stats.avg_sentence:.2f}年" if stats.avg_sentence else f"   {crime}: 无数据")
    
    print("\n2. 省份对比：")
    comparison = analyzer.get_provincial_comparison("盗窃罪")
    for province, data in sorted(comparison.items(), key=lambda x: x[1]["avg_sentence"])[:5]:
        print(f"   {province}: {data['avg_sentence']}年")
    
    print("\n✅ 测试完成！")
