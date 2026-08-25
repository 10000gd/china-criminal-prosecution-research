# -*- coding: utf-8 -*-
"""
法律冲突检测模块 - prosecution_system/src/law_conflict_detector.py

功能：
- 检测法律体系内的条文冲突、规范矛盾、新法旧法并存
- 支持刑法各罪名间的量刑幅度冲突检测
- 支持同一罪名不同解释间的矛盾
- 输出冲突报告，含严重等级和改进建议

冲突类型：
  TYPE_NUMERIC   — 数额/标准矛盾（同一罪名不同条文数字不一致）
  TYPE_SENTENCE  — 量刑幅度矛盾（同罪不同条刑罚悬殊）
  TYPE_JURISD    — 管辖权冲突（多部门均声称管辖）
  TYPE_TEMPORAL  — 时间效力冲突（新法旧法并存未明确废止）
  TYPE_SEMANTIC  — 语义冲突（表述相反的条款）
  TYPE_QUALIFIER — 加重/减轻情节冲突
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from pathlib import Path
import jieba

jieba.setLogLevel(20)

LEGALDB_DIR = Path(__file__).parent.parent / "cases" / "legaldb"
LAWS_DIR = LEGALDB_DIR / "laws"


# ===== 冲突类型枚举 =====

class ConflictType:
    NUMERIC = "数额/标准矛盾"
    SENTENCE = "量刑幅度矛盾"
    JURISDICTION = "管辖权冲突"
    TEMPORAL = "时间效力冲突（新旧法）"
    SEMANTIC = "语义冲突"
    QUALIFIER = "加重/减轻情节冲突"


# ===== 罪名字典（用于关联同罪名不同条文） =====

CRIME_ALIASES: Dict[str, List[str]] = {
    "盗窃罪": ["盗窃罪", "盗窃", "偷盗"],
    "诈骗罪": ["诈骗罪", "诈骗", "欺诈"],
    "抢夺罪": ["抢夺罪", "抢夺", "公然夺取"],
    "敲诈勒索罪": ["敲诈勒索罪", "敲诈勒索"],
    "非法吸收公众存款罪": ["非法吸收公众存款罪", "非法吸收", "吸存"],
    "集资诈骗罪": ["集资诈骗罪", "集资诈骗"],
    "开设赌场罪": ["开设赌场罪", "开设赌场"],
    "职务侵占罪": ["职务侵占罪", "职务侵占"],
    "挪用资金罪": ["挪用资金罪", "挪用资金"],
    "行贿罪": ["行贿罪", "行贿"],
    "受贿罪": ["受贿罪", "受贿"],
    "污染环境罪": ["污染环境罪", "污染环境"],
    "危险驾驶罪": ["危险驾驶罪", "危险驾驶", "醉驾"],
    "寻衅滋事罪": ["寻衅滋事罪", "寻衅滋事"],
    "帮助信息网络犯罪活动罪": ["帮助信息网络犯罪活动罪", "帮信罪", "帮信"],
}


@dataclass
class Conflict:
    """单条冲突"""
    type: str
    severity: str  # INFO / WARN / ERROR
    law_a: str
    law_b: str
    chunk_id_a: str
    chunk_id_b: str
    text_a: str
    text_b: str
    reason: str
    suggestion: str
    legal_basis: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "severity": self.severity,
            "law_a": self.law_a,
            "law_b": self.law_b,
            "chunk_id_a": self.chunk_id_a,
            "chunk_id_b": self.chunk_id_b,
            "text_a": self.text_a[:300],
            "text_b": self.text_b[:300],
            "reason": self.reason,
            "suggestion": self.suggestion,
            "legal_basis": self.legal_basis,
        }


# ===== 数额/量刑提取正则 =====

NUMERIC_PATTERNS = {
    "金额": [
        # 数额/涉案金额 + 阿拉伯数字 + 单位（可选）
        re.compile(r"(?:数额|涉案金额|涉案款|涉案款物)\s*(?:达)?\s*([\d]+)\s*(?:万|千|百)?元?"),
        # 达/共计/总计 + 阿拉伯数字 + 元/万
        re.compile(r"(?:达?|共计|总计)\s*([\d]+)\s*(?:万|千|百)?(?:元)?"),
        # 阿拉伯数字 + 元以上/数额较大等（无前缀单位）
        re.compile(r"([\d]+)\s*(?:元以上?|数额较大|数额巨大|数额特别巨大)"),
        # 涉案金额 + 中文数字 + 元/万
        re.compile(r"(?:数额|涉案金额|涉案款|涉案款物)\s*(?:达)?\s*([\u4e00-\u9fa5]+)\s*(?:万|千|百)?元?"),
    ],
    "刑期": [
        re.compile(r"(?:判处|处|处有期徒刑?|拘役|无期徒刑|死刑)\s*([零一二三四五六七八九十百千万〇\d]+)\s*(?:年|个月|月)"),
        re.compile(r"([零一二三四五六七八九十百千万〇\d]+)\s*(?:年|个月|月)\s*(?:以上|以下|有期徒刑)"),
        re.compile(r"(?:十年以上|七年以上|三年以上十年以下|三年以下|十年以下|无期|死刑)"),
    ],
}


def _extract_amount(text: str) -> List[float]:
    """从文本中提取金额（元）"""
    amounts = []
    seen: set = set()

    for pattern in NUMERIC_PATTERNS["金额"]:
        for m in pattern.finditer(text):
            raw = m.group(1).replace("，", "").replace(",", "").strip()
            if not raw:
                continue

            remainder = m.group(0)[len(m.group(1)):]

            if raw.isdigit():
                # 阿拉伯数字：量词在 remainder
                multiplier = 1
                if "万" in remainder:
                    multiplier = 10000
                elif "千" in remainder:
                    multiplier = 1000
                elif "百" in remainder:
                    multiplier = 100
                val = int(raw) * multiplier
            else:
                # 中文数字：量词在 raw 本身，_chinese_to_num 已自带解析
                # 直接去掉量词后传给 _chinese_to_num（避免双重乘）
                cn = raw.replace("万", "").replace("千", "").replace("百", "")
                if not cn:
                    continue
                try:
                    val = _chinese_to_num(cn)
                except (ValueError, KeyError):
                    continue

            key = round(val)
            if 0 < val < 1e12 and key not in seen:
                amounts.append(val)
                seen.add(key)

    return amounts


def _chinese_to_num(s: str) -> float:
    """中文数字转阿拉伯数字"""
    chinese_map = {
        "零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
        "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
        "〇": 0, "百": 100, "千": 1000, "万": 10000,
        "０": 0, "１": 1, "２": 2, "３": 3, "４": 4,
        "５": 5, "６": 6, "７": 7, "８": 8, "９": 9,
    }
    result = 0
    temp = 0
    for ch in s:
        if ch in ("十", "百", "千", "万"):
            v = chinese_map.get(ch, 0)
            if v >= 100:
                result += temp * v
                temp = 0
            else:
                if temp == 0:
                    temp = 1
                result += temp * v
                temp = 0
        else:
            temp = temp * 10 + chinese_map.get(ch, 0)
    return result + temp


def _extract_sentence(text: str) -> List[Tuple[int, int]]:
    """从文本中提取量刑幅度 [(min_months, max_months), ...]"""
    ranges = []
    # 匹配 "三年以上十年以下有期徒刑"
    m1 = re.search(r"([零一二三四五六七八九十百千万〇\\d]+)\s*年以上?\s*([零一二三四五六七八九十百千万〇\\d]+)\s*年以下", text)
    if m1:
        low = _chinese_to_num(m1.group(1)) * 12
        high = _chinese_to_num(m1.group(2)) * 12
        ranges.append((int(low), int(high)))
    # 匹配 "三年以下有期徒刑"
    m2 = re.search(r"([零一二三四五六七八九十百千万〇\\d]+)\s*年以下", text)
    if m2:
        high = _chinese_to_num(m2.group(1)) * 12
        ranges.append((0, int(high)))
    # 匹配 "三年有期徒刑"
    m3 = re.search(r"([零一二三四五六七八九十百千万〇\\d]+)\s*年有期徒刑", text)
    if m3:
        val = _chinese_to_num(m3.group(1)) * 12
        ranges.append((int(val), int(val)))
    return ranges


# ===== 核心检测器 =====

class LawConflictDetector:
    """
    法律冲突检测器

    用法：
        detector = LawConflictDetector()
        detector.load_laws()
        conflicts = detector.detect_all()
        # 或指定法律
        conflicts = detector.detect(law_name="刑法")
    """

    def __init__(self, laws_dir: Path = None):
        self.laws_dir = laws_dir or LAWS_DIR
        self._chunks: List[Dict[str, Any]] = []
        self._loaded = False

    def load_laws(self, force_rebuild: bool = False):
        """加载法律数据库"""
        if self._loaded and not force_rebuild:
            return

        from law_rag import LawRAG
        rag = LawRAG(enable_vector=False)  # 冲突检测不需要向量
        rag.index_laws()
        self._chunks = [c.to_dict() for c in rag.chunks]
        self._loaded = True
        print(f"  已加载 {len(self._chunks)} 条法律条文")

    def detect(self, law_name: str = None) -> List[Conflict]:
        """
        检测法律冲突

        Args:
            law_name: 指定法律名称（None = 检测全部）

        Returns:
            冲突列表
        """
        if not self._loaded:
            self.load_laws()

        chunks = self._chunks
        if law_name:
            chunks = [c for c in chunks if c.get("law_name") == law_name]

        conflicts: List[Conflict] = []
        conflicts.extend(self._detect_numeric_conflicts(chunks))
        conflicts.extend(self._detect_sentence_conflicts(chunks))
        conflicts.extend(self._detect_temporal_conflicts(chunks))
        conflicts.extend(self._detect_semantic_conflicts(chunks))
        conflicts.extend(self._detect_qualifier_conflicts(chunks))

        # 按严重程度排序
        severity_order = {"ERROR": 0, "WARN": 1, "INFO": 2}
        conflicts.sort(key=lambda x: (severity_order.get(x.severity, 3), x.type))

        return conflicts

    def detect_all(self) -> List[Conflict]:
        """检测所有法律冲突"""
        return self.detect(law_name=None)

    def _detect_numeric_conflicts(self, chunks: List[Dict[str, Any]]) -> List[Conflict]:
        """检测数额标准矛盾"""
        conflicts = []
        # 按罪名分组
        by_crime: Dict[str, List[Dict]] = {}
        for c in chunks:
            content = c.get("content", "")
            for crime, aliases in CRIME_ALIASES.items():
                if any(alias in content for alias in aliases):
                    by_crime.setdefault(crime, []).append(c)
                    break

        for crime, crime_chunks in by_crime.items():
            if len(crime_chunks) < 2:
                continue

            # 收集所有数额
            amounts_by_text: Dict[str, List[float]] = {}
            for c in crime_chunks:
                amts = _extract_amount(c.get("content", ""))
                if amts:
                    amounts_by_text[c["chunk_id"]] = amts

            # 检测矛盾：同一罪名出现不同数额标准（排除完全相同）
            seen_amounts: Dict[str, List[Tuple[str, float]]] = {}
            for chunk_id, amts in amounts_by_text.items():
                for amt in amts:
                    key = self._amount_bucket(amt)
                    seen_amounts.setdefault(key, []).append((chunk_id, amt))

            # 如果同一 bucket 有多个不同 chunk，说明存在多种标准
            for key, entries in seen_amounts.items():
                unique_chunks = set(e[0] for e in entries)
                if len(unique_chunks) >= 2:
                    chunk_ids = list(unique_chunks)
                    c1 = next((c for c in crime_chunks if c["chunk_id"] == chunk_ids[0]), {})
                    c2 = next((c for c in crime_chunks if c["chunk_id"] == chunk_ids[1]), {})
                    conflicts.append(Conflict(
                        type=ConflictType.NUMERIC,
                        severity="WARN",
                        law_a=c1.get("law_name", ""),
                        law_b=c2.get("law_name", ""),
                        chunk_id_a=chunk_ids[0],
                        chunk_id_b=chunk_ids[1],
                        text_a=c1.get("content", "")[:200],
                        text_b=c2.get("content", "")[:200],
                        reason=f"同罪名【{crime}】出现多个数额标准：{[e[1] for e in entries]}元",
                        suggestion=f"建议核查是否为特别法与一般法关系，或为不同司法解释的适用时间差异。"
                                  f"若金额差异较大（如{abs(entries[0][1]-entries[1][1]):.0f}元），"
                                  f"需确认适用的是哪部司法解释。",
                        legal_basis="最高法最高检相关罪名司法解释",
                    ))

        return conflicts

    def _amount_bucket(self, amt: float) -> str:
        """将金额映射到标准档位（用于比较是否属于同一标准）"""
        if amt < 1000:
            return "<1k"
        elif amt < 5000:
            return "1k-5k"
        elif amt < 10000:
            return "5k-1w"
        elif amt < 30000:
            return "1w-3w"
        elif amt < 100000:
            return "3w-10w"
        elif amt < 500000:
            return "10w-50w"
        else:
            return ">50w"

    def _detect_sentence_conflicts(self, chunks: List[Dict[str, Any]]) -> List[Conflict]:
        """检测量刑幅度矛盾"""
        conflicts = []
        by_crime: Dict[str, List[Dict]] = {}
        for c in chunks:
            content = c.get("content", "")
            for crime, aliases in CRIME_ALIASES.items():
                if any(alias in content for alias in aliases):
                    by_crime.setdefault(crime, []).append(c)
                    break

        for crime, crime_chunks in by_crime.items():
            ranges_by_chunk: Dict[str, Tuple[int, int]] = {}
            for c in crime_chunks:
                ranges = _extract_sentence(c.get("content", ""))
                if ranges:
                    ranges_by_chunk[c["chunk_id"]] = ranges[0]

            if len(ranges_by_chunk) >= 2:
                vals = list(ranges_by_chunk.items())
                for i in range(len(vals)):
                    for j in range(i+1, len(vals)):
                        cid1, (l1, h1) = vals[i]
                        cid2, (l2, h2) = vals[j]
                        c1 = next((c for c in crime_chunks if c["chunk_id"] == cid1), {})
                        c2 = next((c for c in crime_chunks if c["chunk_id"] == cid2), {})

                        # 严重矛盾：上限相差超过5年
                        if abs(h1 - h2) > 60 or abs(l1 - l2) > 60:
                            conflicts.append(Conflict(
                                type=ConflictType.SENTENCE,
                                severity="WARN",
                                law_a=c1.get("law_name", ""),
                                law_b=c2.get("law_name", ""),
                                chunk_id_a=cid1,
                                chunk_id_b=cid2,
                                text_a=c1.get("content", "")[:200],
                                text_b=c2.get("content", "")[:200],
                                reason=f"【{crime}】量刑幅度差异大："
                                       f"条a {l1:.0f}-{h1:.0f}月 vs 条b {l2:.0f}-{h2:.0f}月",
                                suggestion="建议核查是否为基本犯与结果加重犯的关系，或是否涉及想象竞合。"
                                          "若量刑差异无法用罪名层级解释，需确认适用的是哪条",
                                legal_basis="刑法及司法解释",
                            ))

        return conflicts

    def _detect_temporal_conflicts(self, chunks: List[Dict[str, Any]]) -> List[Conflict]:
        """检测时间效力冲突（新法旧法并存）"""
        conflicts = []
        # 找包含日期的条文
        date_pattern = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})?\s*日?")
        chunks_with_dates: List[Tuple[Dict, Tuple]] = []
        for c in chunks:
            m = date_pattern.search(c.get("content", ""))
            if m:
                year, month = int(m.group(1)), int(m.group(2))
                chunks_with_dates.append((c, (year, month)))

        # 同一法律内，检测内容相似但日期不同
        by_law: Dict[str, List[Tuple[Dict, Tuple]]] = {}
        for c, dt in chunks_with_dates:
            by_law.setdefault(c.get("law_name", ""), []).append((c, dt))

        for law_name, law_chunks in by_law.items():
            if len(law_chunks) < 2:
                continue
            for i in range(len(law_chunks)):
                for j in range(i+1, len(law_chunks)):
                    c1, dt1 = law_chunks[i]
                    c2, dt2 = law_chunks[j]
                    if dt1 == dt2:
                        continue
                    # 内容相似度检查（简单词重叠）
                    words1 = set(jieba.cut(c1.get("content", "")))
                    words2 = set(jieba.cut(c2.get("content", "")))
                    if not words1 or not words2:
                        continue
                    sim = len(words1 & words2) / min(len(words1), len(words2))
                    if sim > 0.8:
                        newer = max(dt1, dt2)
                        older = min(dt1, dt2)
                        conflicts.append(Conflict(
                            type=ConflictType.TEMPORAL,
                            severity="INFO",
                            law_a=law_name,
                            law_b=law_name,
                            chunk_id_a=c1["chunk_id"],
                            chunk_id_b=c2["chunk_id"],
                            text_a=c1.get("content", "")[:200],
                            text_b=c2.get("content", "")[:200],
                            reason=f"内容相似度{sim:.0%}，存在{newer[0]}年{newer[1]}月新法与"
                                   f"{older[0]}年{older[1]}月旧法并存问题",
                            suggestion="建议核查新法是否明确规定废止旧法相应条款。"
                                      "若未明确废止，按'从旧兼从轻'原则处理",
                            legal_basis="刑法第12条（从旧兼从轻原则）",
                        ))

        return conflicts

    def _detect_semantic_conflicts(self, chunks: List[Dict[str, Any]]) -> List[Conflict]:
        """检测语义冲突（肯定 vs 否定表述）"""
        conflicts = []
        # 语义相反词对
        opposites = [
            ("应当", "可以"),
            ("必须", "不得"),
            ("从轻", "从重"),
            ("减轻", "加重"),
            ("免除", "加重"),
            ("缓刑", "实刑"),
            ("拘役", "有期徒刑"),
            ("并处", "单处"),
            ("没收", "发还"),
        ]
        for c in chunks:
            content = c.get("content", "")
            for pos, neg in opposites:
                if pos in content and neg in content:
                    # 检查是否在同一句子中（上下文50字内）
                    pos_idx = content.find(pos)
                    neg_idx = content.find(neg)
                    if abs(pos_idx - neg_idx) < 200:
                        conflicts.append(Conflict(
                            type=ConflictType.SEMANTIC,
                            severity="INFO",
                            law_a=c.get("law_name", ""),
                            law_b=c.get("law_name", ""),
                            chunk_id_a=c["chunk_id"],
                            chunk_id_b=c["chunk_id"],
                            text_a=content[:300],
                            text_b="",
                            reason=f"同一条文同时出现'{pos}'和'{neg}'，存在语义模糊",
                            suggestion="建议明确两者的适用条件和边界，避免歧义。"
                                      "若两者针对不同情形，应加限定条件以明确区分",
                            legal_basis="立法技术规范",
                        ))
        return conflicts

    def _detect_qualifier_conflicts(self, chunks: List[Dict[str, Any]]) -> List[Conflict]:
        """检测加重/减轻情节冲突"""
        conflicts = []
        qualifiers = ["情节严重", "情节特别严重", "情节较轻", "情节轻微",
                      "造成严重后果", "造成特别严重后果", "数额巨大", "数额特别巨大"]
        for c in chunks:
            content = c.get("content", "")
            matched = [q for q in qualifiers if q in content]
            if len(matched) >= 2:
                # 检查是否矛盾
                severe = any(q in matched for q in ["情节严重", "情节特别严重",
                                                     "造成严重后果", "造成特别严重后果",
                                                     "数额巨大", "数额特别巨大"])
                light = any(q in matched for q in ["情节较轻", "情节轻微"])
                if severe and light:
                    conflicts.append(Conflict(
                        type=ConflictType.QUALIFIER,
                        severity="INFO",
                        law_a=c.get("law_name", ""),
                        law_b=c.get("law_name", ""),
                        chunk_id_a=c["chunk_id"],
                        chunk_id_b=c["chunk_id"],
                        text_a=content[:300],
                        text_b="",
                        reason=f"同一条文同时涉及加重情节和减轻情节：{matched}",
                        suggestion="建议确认是否存在情形区分（不同情形适用不同情节），"
                                  "或是否需要明确适用条件以避免歧义",
                        legal_basis="刑法总则/分则相关条文",
                    ))
        return conflicts


# ===== CLI =====

def main():
    import argparse
    parser = argparse.ArgumentParser(description="法律冲突检测")
    parser.add_argument("--law", type=str, help="指定法律名称（不指定则检测全部）")
    parser.add_argument("--output", type=str, help="输出报告路径（JSON）")
    parser.add_argument("--min-severity", type=str, default="INFO",
                        choices=["INFO", "WARN", "ERROR"],
                        help="最小严重等级（默认INFO，显示所有）")
    args = parser.parse_args()

    detector = LawConflictDetector()
    detector.load_laws()

    print(f"\n开始检测冲突..."
          + (f"（法律: {args.law}）" if args.law else "（全部法律）"))

    conflicts = detector.detect(law_name=args.law)

    # 过滤严重等级
    min_level = ["INFO", "WARN", "ERROR"].index(args.min_severity)
    level_map = {"INFO": 2, "WARN": 1, "ERROR": 0}
    conflicts = [c for c in conflicts if level_map.get(c.severity, 3) <= min_level]

    print(f"\n检测到 {len(conflicts)} 条冲突（严重等级 >= {args.min_severity}）:\n")
    for i, c in enumerate(conflicts):
        print(f"--- 冲突{i+1} [{c.type}] 严重度: {c.severity} ---")
        print(f"  法律A: {c.law_a} | 法律B: {c.law_b}")
        print(f"  原因: {c.reason}")
        print(f"  建议: {c.suggestion}")
        if c.legal_basis:
            print(f"  法律依据: {c.legal_basis}")
        print()

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump([c.to_dict() for c in conflicts], f, ensure_ascii=False, indent=2)
        print(f"✅ 报告已保存: {args.output}")


if __name__ == "__main__":
    main()
