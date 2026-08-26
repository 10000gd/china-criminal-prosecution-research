# -*- coding: utf-8 -*-
"""
类案检索模块 - prosecution_system/src/legal_case_db.py

功能：
- 基于裁判文书网数据构建本地类案数据库
- 按罪名/金额/情节/被告人类型检索相似判例
- 支持类案推送报告（类似案件对比分析）
- 作为法律论证的判例支撑（注意：判例在中国不具有法律约束力）

类案匹配维度：
  罪名相似度（相同罪名/近似罪名）
  涉案金额（数量级对比）
  犯罪主体类型（个人/单位）
  法院层级（基层/中级/高级/最高法）
  判决时间（近年判例优先）

用法：
    db = LegalCaseDB()
    db.index_wenshu_cases("hengda")  # 从已下载的文书建立索引
    cases = db.search_similar("非法吸收公众存款罪", amount=50000000, top_k=5)
    report = db.generate_comparison_report(cases, current_case)
"""

import json
import hashlib
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = __import__('logging').getLogger(__name__)

LEGALDB_DIR = Path(__file__).parent.parent / "cases" / "legaldb"
CASES_DATA_DIR = LEGALDB_DIR.parent.parent / "prosecution_system" / "data"
CASES_DATA_DIR.mkdir(parents=True, exist_ok=True)


# ===== 案号解析 =====

CASE_NUM_PATTERNS = [
    # (2023)沪01刑初123号
    re.compile(r"\((\d{4})\)\s*([\u4e00-\u9fa5]{2,6})\s*(\d+)\s*刑\s*初\s*(\d+)\s*号"),
    # (2022)最高法刑辖42号
    re.compile(r"\((\d{4})\)\s*最高法\s*刑\s*辖\s*(\d+)\s*号"),
    # (2021)京02刑终234号
    re.compile(r"\((\d{4})\)\s*([\u4e00-\u9fa5]{2})\s*(\d+)\s*刑\s*终\s*(\d+)\s*号"),
]

_SENTENCE_RE_1 = re.compile(r"拘役\s*(\d+)\s*个?[月]?")
_SENTENCE_RE_2 = re.compile(r"有期徒刑\s*(\d+)\s*年\s*(\d+)\s*个?[月]?")
_SENTENCE_RE_3 = re.compile(r"有期徒刑\s*(\d+)\s*年")
_SENTENCE_RE_4 = re.compile(r"有期徒刑\s*(\d+)\s*个?[月]?")
_SENTENCE_RE_5 = re.compile(r"有期徒刑\s*(\d+)\s*年\s*缓刑\s*(\d+)")


@dataclass
class LegalCase:
    """类案记录"""
    case_id: str           # 内部 ID（案号哈希）
    case_num: str          # 案号
    court: str             # 审理法院
    judgment_date: str     # 判决日期（YYYY-MM-DD）
    crime_name: str        # 罪名
    crime_articles: List[str] = field(default_factory=list)  # 适用法条
    amount: float = 0.0    # 涉案金额（元）
    amount_level: str = "" # 数额档位（较大/巨大/特别巨大）
    sentence: str = ""     # 判决结果
    sentence_months: int = 0  # 有期徒刑月数（估算）
    is_company: bool = False  # 是否单位犯罪
    defendants: List[str] = field(default_factory=list)  # 被告人
    plaintiff: str = ""    # 原告/公诉机关
    key_facts: str = ""    # 关键事实摘要
    source: str = "裁判文书网"
    raw_data: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "case_id": self.case_id,
            "case_num": self.case_num,
            "court": self.court,
            "judgment_date": self.judgment_date,
            "crime_name": self.crime_name,
            "crime_articles": self.crime_articles,
            "amount": self.amount,
            "amount_level": self.amount_level,
            "sentence": self.sentence,
            "sentence_months": self.sentence_months,
            "is_company": self.is_company,
            "defendants": self.defendants,
            "source": self.source,
        }
        return d


@dataclass
class SimilarCaseResult:
    """类案检索结果"""
    case: LegalCase
    similarity_score: float
    match_reasons: List[str]
    amount_comparison: str  # 金额对比说明
    sentence_comparison: str  # 量刑对比说明


# ===== 金额档位判断 =====

AMOUNT_LEVELS = {
    "盗窃罪": [("数额较大", 1000), ("数额巨大", 30000), ("数额特别巨大", 300000)],
    "诈骗罪": [("数额较大", 3000), ("数额巨大", 100000), ("数额特别巨大", 500000)],
    "非法吸收公众存款罪": [("数额较大", 1000000), ("数额巨大", 5000000)],
    "集资诈骗罪": [("数额较大", 100000), ("数额巨大", 1000000), ("数额特别巨大", 10000000)],
    "职务侵占罪": [("数额较大", 60000), ("数额巨大", 1000000)],
    "抢夺罪": [("数额较大", 1000), ("数额巨大", 30000), ("数额特别巨大", 200000)],
    "敲诈勒索罪": [("数额较大", 2000), ("数额巨大", 30000), ("数额特别巨大", 300000)],
    "开设赌场罪": [("情节严重", 0)],  # 无具体数额，看抽头渔利
}


def _get_amount_level(crime: str, amount: float) -> str:
    """判断涉案金额属于哪一档"""
    levels = AMOUNT_LEVELS.get(crime, [])
    for label, threshold in reversed(levels):
        if amount >= threshold:
            return label
    return "未达入罪标准"


def _estimate_sentence_months(sentence_text: str) -> int:
    """从判决书文字估算刑期月数"""
    text = sentence_text.replace(" ", "")

    # 终身监禁/死缓
    if "无期" in text or "终身监禁" in text:
        return 9999
    if "死刑" in text and "缓期" in text:
        return 240  # 死缓通常按无期处理

    # 拘役：1-6个月
    m = _SENTENCE_RE_1.search(text)
    if m:
        return int(m.group(1))
    # 有期徒刑：X年Y月
    m = _SENTENCE_RE_2.search(text)
    if m:
        return int(m.group(1)) * 12 + int(m.group(2))
    m = _SENTENCE_RE_3.search(text)
    if m:
        return int(m.group(1)) * 12
    m = _SENTENCE_RE_4.search(text)
    if m:
        return int(m.group(1))
    # 有期徒刑缓刑
    m = _SENTENCE_RE_5.search(text)
    if m:
        return int(m.group(1)) * 12  # 缓刑不影响基准刑期

    return 0


class LegalCaseDB:
    """
    类案数据库

    用法：
        db = LegalCaseDB()
        db.load_from_file("data/wenshu_cases.json")  # 加载本地数据
        cases = db.search_similar("非法吸收公众存款罪", amount=50000000, top_k=5)
        report = db.generate_comparison_report(cases, current_case_data)
    """

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or CASES_DATA_DIR / "legal_case_db.json"
        self._cases: Dict[str, LegalCase] = {}
        self._by_crime: Dict[str, List[LegalCase]] = {}
        self._loaded = False

    def load(self):
        """加载本地类案库"""
        if self._loaded:
            return
        if self.db_path.exists():
            with open(self.db_path, encoding="utf-8") as f:
                data = json.load(f)
            for item in data.get("cases", []):
                case = self._dict_to_case(item)
                if case:
                    self._cases[case.case_id] = case
                    self._by_crime.setdefault(case.crime_name, []).append(case)
            logger.info(f"已加载 {len(self._cases)} 条类案")
            print(f"  已加载 {len(self._cases)} 条类案")
        self._loaded = True

    def save(self):
        """保存到本地"""
        data = {
            "updated_at": datetime.now().isoformat(),
            "cases": [c.to_dict() for c in self._cases.values()],
        }
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"已保存 {len(self._cases)} 条类案到 {self.db_path}")

    def add_case(self, case_data: Dict[str, Any]) -> Optional[LegalCase]:
        """添加一条类案记录"""
        case = self._parse_case_data(case_data)
        if not case:
            return None
        self._cases[case.case_id] = case
        self._by_crime.setdefault(case.crime_name, []).append(case)
        return case

    def _parse_case_data(self, data: Dict[str, Any]) -> Optional[LegalCase]:
        """解析原始案件数据为 LegalCase"""
        case_num = data.get("case_num", "")
        if not case_num:
            # 从案号提取或生成 ID
            case_id = hashlib.md5(str(data).encode()).hexdigest()[:12]
        else:
            case_id = hashlib.md5(case_num.encode()).hexdigest()[:12]

        crime = data.get("crime_name", data.get("crime", ""))
        amount = float(data.get("amount", data.get("涉案金额", 0)))
        amount_level = _get_amount_level(crime, amount)

        sentence_text = data.get("sentence", data.get("判决结果", ""))
        sentence_months = _estimate_sentence_months(sentence_text)

        return LegalCase(
            case_id=case_id,
            case_num=case_num,
            court=data.get("court", ""),
            judgment_date=data.get("judgment_date", data.get("判决日期", "")),
            crime_name=crime,
            crime_articles=data.get("crime_articles", []),
            amount=amount,
            amount_level=amount_level,
            sentence=sentence_text,
            sentence_months=sentence_months,
            is_company=data.get("is_company", False),
            defendants=data.get("defendants", []),
            plaintiff=data.get("plaintiff", ""),
            key_facts=data.get("key_facts", ""),
            source=data.get("source", "裁判文书网"),
            raw_data=data,
        )

    def _dict_to_case(self, d: Dict) -> Optional[LegalCase]:
        try:
            return LegalCase(
                case_id=d["case_id"],
                case_num=d.get("case_num", ""),
                court=d.get("court", ""),
                judgment_date=d.get("judgment_date", ""),
                crime_name=d.get("crime_name", ""),
                crime_articles=d.get("crime_articles", []),
                amount=d.get("amount", 0.0),
                amount_level=d.get("amount_level", ""),
                sentence=d.get("sentence", ""),
                sentence_months=d.get("sentence_months", 0),
                is_company=d.get("is_company", False),
                defendants=d.get("defendants", []),
                raw_data=d,
            )
        except Exception:
            return None

    def search_similar(
        self,
        crime_name: str = None,
        amount: float = 0,
        is_company: bool = None,
        court_level: str = None,  # "基层" / "中级" / "高级" / "最高法"
        year_from: int = None,
        year_to: int = None,
        keyword: str = "",
        top_k: int = 5,
    ) -> List[SimilarCaseResult]:
        """
        检索相似判例

        Args:
            crime_name: 目标罪名
            amount: 涉案金额（元）
            is_company: 是否单位犯罪
            court_level: 法院层级
            year_from/year_to: 年份范围
            keyword: 关键词（用于全文搜索）
            top_k: 返回数量

        Returns:
            SimilarCaseResult 列表（按相似度降序）
        """
        self.load()

        # 筛选候选集
        candidates = list(self._cases.values())

        if crime_name:
            # 精确优先，其次模糊
            exact = self._by_crime.get(crime_name, [])
            fuzzy = [c for c in candidates if c.crime_name != crime_name and
                     any(kw in c.crime_name for kw in [crime_name, crime_name.replace("罪", "")])]
            candidates = exact + fuzzy

        if year_from:
            candidates = [c for c in candidates if c.judgment_date >= str(year_from)]
        if year_to:
            candidates = [c for c in candidates if c.judgment_date <= str(year_to)]

        if is_company is not None:
            candidates = [c for c in candidates if c.is_company == is_company]

        if keyword:
            kw = keyword.lower()
            candidates = [c for c in candidates
                          if kw in c.crime_name.lower()
                          or kw in c.court.lower()
                          or kw in c.sentence.lower()
                          or kw in c.key_facts.lower()]

        # 计算相似度
        scored: List[SimilarCaseResult] = []
        for case in candidates:
            score, reasons, amt_cmp, sent_cmp = self._compute_similarity(
                case, crime_name, amount, is_company, court_level
            )
            if score > 0:
                scored.append(SimilarCaseResult(
                    case=case,
                    similarity_score=score,
                    match_reasons=reasons,
                    amount_comparison=amt_cmp,
                    sentence_comparison=sent_cmp,
                ))

        # 排序并截取 top_k
        scored.sort(key=lambda x: x.similarity_score, reverse=True)
        return scored[:top_k]

    def _compute_similarity(
        self,
        case: LegalCase,
        crime_name: str,
        amount: float,
        is_company: bool,
        court_level: str,
    ) -> Tuple[float, List[str], str, str]:
        """计算相似度评分（0-100）"""
        score = 0.0
        reasons = []
        amt_cmp = ""
        sent_cmp = ""

        # 1. 罪名匹配（40分）
        if crime_name and case.crime_name == crime_name:
            score += 40
            reasons.append(f"罪名相同：{crime_name}")
        elif crime_name and crime_name.replace("罪", "") in case.crime_name:
            score += 20
            reasons.append(f"罪名近似：{case.crime_name}")

        # 2. 金额匹配（30分）- 同一档位给满分，相差一档给部分分
        if amount > 0 and case.amount > 0:
            level_score = self._amount_level_score(crime_name, amount, case.amount)
            score += level_score * 0.3
            if level_score == 1.0:
                reasons.append(f"金额同档：{case.amount_level}")
                amt_cmp = f"案例金额 {case.amount/1e4:.0f} 万元，本案约 {amount/1e4:.0f} 万元"
            elif level_score > 0:
                ratio = min(amount, case.amount) / max(amount, case.amount)
                amt_cmp = f"案例金额 {case.amount/1e4:.0f} 万元，本案约 {amount/1e4:.0f} 万元（比例 {ratio:.1%}）"

        # 3. 主体类型匹配（15分）
        if is_company is not None and case.is_company == is_company:
            score += 15
            reasons.append("主体类型相同（单位/个人）")

        # 4. 时间新鲜度（15分）- 5年内满分，5年外线性衰减
        if case.judgment_date:
            try:
                year = int(case.jredgment_date[:4])
                current_year = datetime.now().year
                age = current_year - year
                time_score = max(0, 15 * (1 - age / 15))
                score += time_score
                if age <= 3:
                    reasons.append(f"近年判例（{year}年）")
            except (ValueError, IndexError):
                pass

        return score, reasons, amt_cmp, sent_cmp

    def _amount_level_score(self, crime: str, amount_a: float, amount_b: float) -> float:
        """同一数额档位返回1.0，相差一档返回0.5，相差两档返回0.2"""
        level_a = _get_amount_level(crime, amount_a)
        level_b = _get_amount_level(crime, amount_b)
        if level_a == level_b:
            return 1.0
        level_order = ["未达入罪标准", "数额较大", "数额巨大", "数额特别巨大",
                       "情节严重", "情节特别严重", "情节较轻"]
        try:
            dist = abs(level_order.index(level_a) - level_order.index(level_b))
            return max(0, 1.0 - dist * 0.4)
        except ValueError:
            return 0.5

    def generate_comparison_report(
        self,
        similar_results: List[SimilarCaseResult],
        current_case: Dict[str, Any],
    ) -> str:
        """生成类案对比报告"""
        lines = [
            "## 类案对比分析",
            "",
            "**说明**：中国并非判例法国家，以下类案仅供法律论证参考，不具有法律约束力。",
            "",
        ]

        if not similar_results:
            lines.append("*（当前类案库为空，建议通过 WenshuAPI 补充类案数据）*")
            return "\n".join(lines)

        current_crime = current_case.get("primary_charge", "")
        current_amount = float(current_case.get("total_amount", 0))
        current_level = _get_amount_level(current_crime, current_amount)

        lines.append(f"**本案**：{current_crime} | 金额 {current_amount/1e4:.0f} 万元 | "
                     f"档位：{current_level}")
        lines.append("")
        lines.append(f"共检索到 {len(similar_results)} 个类案：")
        lines.append("")

        for i, result in enumerate(similar_results, 1):
            c = result.case
            lines.append(f"### 类案{i}：{c.case_num or c.case_id}")
            lines.append(f"")
            lines.append(f"| 项目 | 内容 |")
            lines.append(f"|------|------|")
            lines.append(f"| 审理法院 | {c.court} |")
            lines.append(f"| 判决日期 | {c.judgment_date} |")
            lines.append(f"| 罪名 | {c.crime_name} |")
            lines.append(f"| 涉案金额 | {c.amount/1e4:.0f} 万元（{c.amount_level}） |")
            lines.append(f"| 判决结果 | {c.sentence} |")
            lines.append(f"| 相似度 | {result.similarity_score:.0f}/100 |")
            if result.match_reasons:
                lines.append(f"| 匹配理由 | {'；'.join(result.match_reasons)} |")
            if result.amount_comparison:
                lines.append(f"| 金额对比 | {result.amount_comparison} |")
            if result.sentence_comparison:
                lines.append(f"| 量刑对比 | {result.sentence_comparison} |")
            if c.crime_articles:
                lines.append(f"| 适用法条 | {', '.join(c.crime_articles)} |")
            lines.append("")
            lines.append(f"📌 **法律论证参考**：")
            if result.similarity_score >= 60:
                lines.append(f"本案与上述类案在罪名、金额档位等方面具有高度相似性，"
                             f"可参考其量刑结果。量刑 {c.sentence}。"
                             f"建议本案量刑幅度参照类案，结合本案具体情节综合确定。")
            else:
                lines.append(f"上述类案与本案存在一定差异，量刑结论仅供参考，"
                             f"需结合本案具体情节独立判断。")
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def get_statistics(self) -> Dict[str, Any]:
        """获取类案库统计"""
        self.load()
        all_cases = list(self._cases.values())
        if not all_cases:
            return {"total": 0}

        by_crime = {}
        for c in all_cases:
            by_crime.setdefault(c.crime_name, []).append(c)

        return {
            "total": len(all_cases),
            "by_crime": {crime: len(cases) for crime, cases in by_crime.items()},
            "by_court_level": self._count_by_court_level(all_cases),
            "year_range": (
                min((c.judgment_date for c in all_cases if c.judgment_date), default="")[:4],
                max((c.judgment_date for c in all_cases if c.judgment_date), default="")[:4],
            ),
        }

    def _count_by_court_level(self, cases: List[LegalCase]) -> Dict[str, int]:
        counts = {"基层法院": 0, "中级法院": 0, "高级法院": 0, "最高法": 0}
        for c in cases:
            court = c.court
            if "最高法" in court or "最高人民法院" in court:
                counts["最高法"] += 1
            elif "高级法院" in court or "高级人民法院" in court:
                counts["高级法院"] += 1
            elif "中级法院" in court or "中级人民法院" in court:
                counts["中级法院"] += 1
            elif any(x in court for x in ["区法院", "县法院", "市法院"]):
                counts["基层法院"] += 1
            else:
                counts["基层法院"] += 1
        return counts


# ===== CLI =====

def main():
    import argparse
    parser = argparse.ArgumentParser(description="类案检索")
    parser.add_argument("--crime", type=str, help="罪名")
    parser.add_argument("--amount", type=float, help="涉案金额（元）")
    parser.add_argument("--company", action="store_true", help="单位犯罪")
    parser.add_argument("--year-from", type=int, help="最早年份")
    parser.add_argument("--year-to", type=int, help="最晚年份")
    parser.add_argument("--top-k", type=int, default=5, help="返回数量（默认5）")
    parser.add_argument("--stats", action="store_true", help="显示类案库统计")
    parser.add_argument("--add", type=str, help="添加类案（JSON文件路径）")
    args = parser.parse_args()

    db = LegalCaseDB()

    if args.stats:
        stats = db.get_statistics()
        print(f"\n类案库统计：")
        print(f"  总案件：{stats['total']}")
        if stats['total'] > 0:
            print(f"  年份范围：{stats['year_range'][0]} - {stats['year_range'][1]}")
            print(f"  按罪名：")
            for crime, cnt in sorted(stats['by_crime'].items(), key=lambda x: -x[1]):
                print(f"    {crime}: {cnt} 条")
            print(f"  按法院层级：")
            for level, cnt in stats['by_court_level'].items():
                if cnt > 0:
                    print(f"    {level}: {cnt}")

    elif args.add:
        with open(args.add, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            for item in data:
                db.add_case(item)
        else:
            db.add_case(data)
        db.save()
        print(f"✅ 已添加类案")

    elif args.crime or args.amount:
        results = db.search_similar(
            crime_name=args.crime,
            amount=args.amount or 0,
            is_company=args.company if args.company else None,
            year_from=args.year_from,
            year_to=args.year_to,
            top_k=args.top_k,
        )
        if not results:
            print("未找到相似判例")
            return

        print(f"\n找到 {len(results)} 个类案：\n")
        for i, r in enumerate(results, 1):
            c = r.case
            print(f"【类案{i}】{c.case_num or c.case_id}")
            print(f"  法院：{c.court} | 日期：{c.judgment_date}")
            print(f"  罪名：{c.crime_name} | 金额：{c.amount/1e4:.0f} 万元（{c.amount_level}）")
            print(f"  判决：{c.sentence}")
            print(f"  相似度：{r.similarity_score:.0f}/100 | {', '.join(r.match_reasons)}")
            print()
    else:
        print("用法：--crime 罪名 --amount 金额 --stats --add JSON文件")


if __name__ == "__main__":
    main()
