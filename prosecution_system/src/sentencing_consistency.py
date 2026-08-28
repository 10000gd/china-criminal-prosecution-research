# -*- coding: utf-8 -*-
"""
量刑一致性分析模块 - sentencing_consistency.py

分析量刑的一致性问题：
- 各省量刑差异分析
- 罪名量刑区间统计
- 个案偏离度检测
- 可视化报告生成
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime
import statistics


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
    # 如 {"0-1年": 10, "1-3年": 25, "3-5年": 15, "5-10年": 5}
    
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
    
    # 内置典型案例数据（作为种子）
    BUILTIN_RECORDS = [
        # 盗窃罪 - 各省案例
        {"case_id": "TH-001", "case_name": "盗窃案A", "crime": "盗窃罪", "province": "北京", "sentence_years": 1.5, "amount": 50000, "is_初犯": True},
        {"case_id": "TH-002", "case_name": "盗窃案B", "crime": "盗窃罪", "province": "上海", "sentence_years": 1.0, "amount": 48000, "is_初犯": True},
        {"case_id": "TH-003", "case_name": "盗窃案C", "crime": "盗窃罪", "province": "广东", "sentence_years": 2.0, "amount": 52000, "is_初犯": False},
        {"case_id": "TH-004", "case_name": "盗窃案D", "crime": "盗窃罪", "province": "四川", "sentence_years": 1.2, "amount": 51000, "is_初犯": True, "is_自首": True},
        {"case_id": "TH-005", "case_name": "盗窃案E", "crime": "盗窃罪", "province": "浙江", "sentence_years": 1.8, "amount": 55000, "is_初犯": True},
        {"case_id": "TH-006", "case_name": "盗窃案F", "crime": "盗窃罪", "province": "江苏", "sentence_years": 1.3, "amount": 49000, "is_初犯": True, "is_谅解": True},
        {"case_id": "TH-007", "case_name": "盗窃案G", "crime": "盗窃罪", "province": "山东", "sentence_years": 2.2, "amount": 60000, "is_初犯": False, "is_累犯": True},
        {"case_id": "TH-008", "case_name": "盗窃案H", "crime": "盗窃罪", "province": "河南", "sentence_years": 1.0, "amount": 45000, "is_初犯": True, "is_自首": True},
        
        # 诈骗罪 - 各省案例
        {"case_id": "FR-001", "case_name": "诈骗案A", "crime": "诈骗罪", "province": "北京", "sentence_years": 4.0, "amount": 200000, "is_初犯": True},
        {"case_id": "FR-002", "case_name": "诈骗案B", "crime": "诈骗罪", "province": "上海", "sentence_years": 3.5, "amount": 190000, "is_初犯": True},
        {"case_id": "FR-003", "case_name": "诈骗案C", "crime": "诈骗罪", "province": "广东", "sentence_years": 5.0, "amount": 210000, "is_初犯": False},
        {"case_id": "FR-004", "case_name": "诈骗案D", "crime": "诈骗罪", "province": "浙江", "sentence_years": 3.8, "amount": 195000, "is_初犯": True, "is_赔偿": True},
        {"case_id": "FR-005", "case_name": "诈骗案E", "crime": "诈骗罪", "province": "江苏", "sentence_years": 4.5, "amount": 220000, "is_初犯": True, "is_坦白": True},
        {"case_id": "FR-006", "case_name": "诈骗案F", "crime": "诈骗罪", "province": "四川", "sentence_years": 3.2, "amount": 180000, "is_初犯": True, "is_自首": True},
        {"case_id": "FR-007", "case_name": "诈骗案G", "crime": "诈骗罪", "province": "湖北", "sentence_years": 4.2, "amount": 205000, "is_初犯": False, "is_累犯": True},
        {"case_id": "FR-008", "case_name": "诈骗案H", "crime": "诈骗罪", "province": "湖南", "sentence_years": 3.6, "amount": 188000, "is_初犯": True, "is_谅解": True},
        
        # 故意伤害罪 - 各省案例
        {"case_id": "IH-001", "case_name": "伤害案A", "crime": "故意伤害罪", "province": "北京", "sentence_years": 3.0, "is_初犯": True},
        {"case_id": "IH-002", "case_name": "伤害案B", "crime": "故意伤害罪", "province": "上海", "sentence_years": 2.5, "is_初犯": True, "is_谅解": True},
        {"case_id": "IH-003", "case_name": "伤害案C", "crime": "故意伤害罪", "province": "广东", "sentence_years": 4.0, "is_初犯": False},
        {"case_id": "IH-004", "case_name": "伤害案D", "crime": "故意伤害罪", "province": "浙江", "sentence_years": 2.8, "is_初犯": True, "is_赔偿": True, "is_谅解": True},
        {"case_id": "IH-005", "case_name": "伤害案E", "crime": "故意伤害罪", "province": "江苏", "sentence_years": 3.5, "is_初犯": True, "is_自首": True},
        {"case_id": "IH-006", "case_name": "伤害案F", "crime": "故意伤害罪", "province": "四川", "sentence_years": 2.0, "is_初犯": True, "is_自首": True, "is_赔偿": True},
        {"case_id": "IH-007", "case_name": "伤害案G", "crime": "故意伤害罪", "province": "山东", "sentence_years": 3.8, "is_初犯": False, "is_累犯": True},
        {"case_id": "IH-008", "case_name": "伤害案H", "crime": "故意伤害罪", "province": "河南", "sentence_years": 2.6, "is_初犯": True, "is_坦白": True},
        
        # 醉驾（危险驾驶罪）
        {"case_id": "DR-001", "case_name": "醉驾案A", "crime": "危险驾驶罪", "province": "北京", "sentence_months": 4, "is_初犯": True},
        {"case_id": "DR-002", "case_name": "醉驾案B", "crime": "危险驾驶罪", "province": "上海", "sentence_months": 3, "is_初犯": True, "is_自首": True},
        {"case_id": "DR-003", "case_name": "醉驾案C", "crime": "危险驾驶罪", "province": "广东", "sentence_months": 5, "is_初犯": False},
        {"case_id": "DR-004", "case_name": "醉驾案D", "crime": "危险驾驶罪", "province": "浙江", "sentence_months": 3, "is_初犯": True, "is_谅解": True},
        {"case_id": "DR-005", "case_name": "醉驾案E", "crime": "危险驾驶罪", "province": "江苏", "sentence_months": 4, "is_初犯": True},
        
        # 交通肇事罪
        {"case_id": "TF-001", "case_name": "肇事案A", "crime": "交通肇事罪", "province": "北京", "sentence_years": 2.0, "is_初犯": True, "is_赔偿": True, "is_谅解": True},
        {"case_id": "TF-002", "case_name": "肇事案B", "crime": "交通肇事罪", "province": "上海", "sentence_years": 1.5, "is_初犯": True, "is_赔偿": True, "is_谅解": True, "is_自首": True},
        {"case_id": "TF-003", "case_name": "肇事案C", "crime": "交通肇事罪", "province": "广东", "sentence_years": 3.0, "is_初犯": False},
        {"case_id": "TF-004", "case_name": "肇事案D", "crime": "交通肇事罪", "province": "浙江", "sentence_years": 1.8, "is_初犯": True, "is_赔偿": True, "is_谅解": True},
        {"case_id": "TF-005", "case_name": "肇事案E", "crime": "交通肇事罪", "province": "江苏", "sentence_years": 2.5, "is_初犯": True, "is_坦白": True},
    ]
    
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
        """初始化分析器
        
        Args:
            records_path: 自定义量刑记录JSON文件
        """
        self._records: List[SentencingRecord] = []
        self._records_by_crime: Dict[str, List[SentencingRecord]] = defaultdict(list)
        self._records_by_province: Dict[str, List[SentencingRecord]] = defaultdict(list)
        
        # 加载内置数据
        self._load_builtin_records()
        
        # 加载自定义数据
        if records_path and records_path.exists():
            self._load_custom_records(records_path)
    
    def _load_builtin_records(self):
        """加载内置案例"""
        for record_data in self.BUILTIN_RECORDS:
            record = SentencingRecord(**record_data)
            self._add_record(record)
    
    def _load_custom_records(self, path: Path):
        """加载自定义案例"""
        with open(path, "r", encoding="utf-8") as f:
            records_data = json.load(f)
        
        for record_data in records_data:
            try:
                record = SentencingRecord(**record_data)
                self._add_record(record)
            except Exception as e:
                print(f"加载量刑记录失败: {record_data.get('case_id', 'unknown')}, {e}")
    
    def _add_record(self, record: SentencingRecord):
        """添加记录到索引"""
        self._records.append(record)
        self._records_by_crime[record.crime].append(record)
        if record.province:
            self._records_by_province[record.province].append(record)
    
    def add_record(self, case_id: str, crime: str, sentence_years: float,
                   province: str = None, **kwargs) -> SentencingRecord:
        """添加新量刑记录"""
        record = SentencingRecord(
            case_id=case_id,
            case_name=kwargs.get("case_name", case_id),
            crime=crime,
            province=province,
            sentence_years=sentence_years,
            **kwargs
        )
        self._add_record(record)
        return record
    
    def get_stats_by_crime(self, crime: str) -> SentencingStats:
        """获取特定罪名的量刑统计
        
        Args:
            crime: 罪名
            
        Returns:
            SentencingStats: 统计结果
        """
        records = self._records_by_crime.get(crime, [])
        
        if not records:
            return SentencingStats(crime=crime, sample_count=0)
        
        # 提取刑期数据
        sentences = []
        for r in records:
            if r.sentence_years:
                sentences.append(r.sentence_years)
            elif r.sentence_months:
                sentences.append(r.sentence_months / 12)
        
        if not sentences:
            return SentencingStats(crime=crime, sample_count=len(records))
        
        # 计算基本统计
        stats = SentencingStats(
            crime=crime,
            sample_count=len(records),
            avg_sentence=statistics.mean(sentences),
            median_sentence=statistics.median(sentences),
            min_sentence=min(sentences),
            max_sentence=max(sentences),
            std_dev=statistics.stdev(sentences) if len(sentences) > 1 else 0,
        )
        
        # 区间分布
        stats.sentence_distribution = self._calculate_distribution(sentences)
        
        # 缓刑率（简化判断：1年以下）
        probation_count = sum(1 for s in sentences if s <= 1)
        stats.probation_rate = probation_count / len(sentences) * 100
        
        # 省份统计
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
        
        # 特征统计
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
        distribution = {
            "不满1年": 0,
            "1-3年": 0,
            "3-5年": 0,
            "5-10年": 0,
            "10年以上": 0,
        }
        
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
        """获取各省量刑对比
        
        Args:
            crime: 罪名（可选，筛选特定罪名）
            
        Returns:
            Dict: 各省对比数据
        """
        if crime:
            records = self._records_by_crime.get(crime, [])
        else:
            records = self._records
        
        # 按省份汇总
        province_data = defaultdict(lambda: {"sentences": [], "count": 0, "crimes": defaultdict(int)})
        
        for r in records:
            if r.province and r.sentence_years:
                province = r.province
                province_data[province]["sentences"].append(r.sentence_years)
                province_data[province]["count"] += 1
                province_data[province]["crimes"][r.crime] += 1
        
        # 计算统计数据
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
        
        # 计算全国平均值作为基准
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
        """分析个案的量刑偏离度
        
        Args:
            case_data: 案件数据
            
        Returns:
            DeviationAnalysis: 偏离度分析结果
        """
        crime = case_data.get("crime", "")
        actual_sentence = case_data.get("sentence_years", 0)
        province = case_data.get("province", "")
        
        # 获取该罪名的统计数据
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
        
        # 计算偏离度
        expected = stats.avg_sentence
        
        # 考虑省份因素
        if province:
            provincial_data = self.get_provincial_comparison(crime)
            if province in provincial_data:
                expected = provincial_data[province]["avg_sentence"]
        
        # 计算偏离度分数（0-100）
        if expected > 0:
            deviation_ratio = abs(actual_sentence - expected) / expected
            deviation_score = min(100, deviation_ratio * 100)
        else:
            deviation_score = 50
        
        # 判断偏离类型
        if actual_sentence > expected * 1.2:
            deviation_type = "偏重"
        elif actual_sentence < expected * 0.8:
            deviation_type = "偏轻"
        else:
            deviation_type = "正常"
        
        # 分析影响因素
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
        
        # 查找相似案例
        similar_cases = self._find_similar_cases(crime, actual_sentence)
        
        # 生成建议
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
        
        # 按刑期相似度排序
        scored = []
        for r in records:
            if r.sentence_years:
                diff = abs(r.sentence_years - sentence)
                scored.append((diff, r))
        
        scored.sort(key=lambda x: x[0])
        
        return [r.to_dict() for _, r in scored[:limit]]
    
    def get_legal_comparison(self, crime: str) -> Dict:
        """获取法定量刑区间与实际量刑对比
        
        Args:
            crime: 罪名
            
        Returns:
            Dict: 对比数据
        """
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
            "is_within_legal": (
                stats.min_sentence >= legal_range.get("min", 0) and
                stats.max_sentence <= legal_range.get("max", 999)
            ) if legal_range else None,
        }
    
    def generate_report(self, crime: str = None) -> Dict:
        """生成量刑一致性报告
        
        Args:
            crime: 罪名（可选）
            
        Returns:
            Dict: 报告数据
        """
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
        
        # 各罪名统计摘要
        for crime, stats in crime_stats.items():
            if stats["avg_sentence"]:
                summaries.append(
                    f"{crime}平均刑期{stats['avg_sentence']}年"
                    f"(样本{stats['sample_count']}件)"
                )
        
        # 省份差异摘要
        if provincial_comparison:
            provinces = list(provincial_comparison.keys())
            if len(provinces) >= 2:
                sorted_provinces = sorted(
                    provincial_comparison.items(),
                    key=lambda x: x[1]["avg_sentence"]
                )
                lightest = sorted_provinces[0]
                heaviest = sorted_provinces[-1]
                
                diff_pct = (
                    (heaviest[1]["avg_sentence"] - lightest[1]["avg_sentence"])
                    / lightest[1]["avg_sentence"] * 100
                ) if lightest[1]["avg_sentence"] > 0 else 0
                
                summaries.append(
                    f"各省差异最大{diff_pct:.1f}%："
                    f"{lightest[0]}最轻({lightest[1]['avg_sentence']}年) vs "
                    f"{heaviest[0]}最重({heaviest[1]['avg_sentence']}年)"
                )
        
        return "；".join(summaries) if summaries else "数据不足"


def analyze_sentencing(case_data: Dict) -> Dict:
    """便捷函数：分析个案量刑偏离度
    
    Args:
        case_data: 案件数据
        
    Returns:
        Dict: 偏离度分析结果
    """
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
    """便捷函数：获取量刑一致性报告
    
    Args:
        crime: 罪名（可选）
        
    Returns:
        Dict: 报告数据
    """
    analyzer = SentencingConsistencyAnalyzer()
    return analyzer.generate_report(crime)


if __name__ == "__main__":
    # 测试
    print("=== 量刑一致性分析测试 ===\n")
    
    analyzer = SentencingConsistencyAnalyzer()
    
    # 测试1：获取盗窃罪统计
    print("1. 盗窃罪量刑统计：")
    stats = analyzer.get_stats_by_crime("盗窃罪")
    print(f"   样本数: {stats.sample_count}")
    print(f"   平均刑期: {stats.avg_sentence:.2f}年")
    print(f"   中位数: {stats.median_sentence:.2f}年")
    print(f"   区间分布: {stats.sentence_distribution}")
    print(f"   缓刑率: {stats.probation_rate:.1f}%")
    
    # 测试2：省份对比
    print("\n2. 各省量刑对比（盗窃罪）：")
    comparison = analyzer.get_provincial_comparison("盗窃罪")
    for province, data in sorted(comparison.items(), key=lambda x: x[1]["avg_sentence"]):
        print(f"   {province}: 平均{data['avg_sentence']:.2f}年 ({data['deviation_type']})")
    
    # 测试3：偏离度分析
    print("\n3. 个案偏离度分析：")
    test_case = {
        "case_id": "TEST-001",
        "crime": "盗窃罪",
        "sentence_years": 3.0,  # 某被告人被判3年
        "province": "北京",
        "is_自首": True,
        "is_初犯": True,
    }
    deviation = analyzer.analyze_deviation(test_case)
    print(f"   偏离度: {deviation.deviation_score:.1f}")
    print(f"   偏离类型: {deviation.deviation_type}")
    print(f"   期望刑期: {deviation.expected_sentence:.2f}年")
    print(f"   实际刑期: {deviation.actual_sentence:.2f}年")
    print(f"   影响因素: {', '.join(deviation.factors)}")
    print(f"   建议: {deviation.recommendation}")
    
    # 测试4：生成报告
    print("\n4. 生成量刑一致性报告：")
    report = analyzer.generate_report()
    print(f"   摘要: {report['summary']}")
    
    print("\n✅ 测试完成！")
