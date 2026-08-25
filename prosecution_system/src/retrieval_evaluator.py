# -*- coding: utf-8 -*-
"""
检索质量评估器 - prosecution_system/src/retrieval_evaluator.py

功能：
- 对 RAG 检索结果进行定量质量评估
- 支持 nDCG@k、Recall@k、MRR、Precision@k 等指标
- 内置法律领域标准测试集 + 支持自定义 query-ground_truth 对

指标说明：
  nDCG@k  — 归一化折损累计增益，衡量排序质量（0~1，越高越好）
  Recall@k — top-k 结果中相关文档的召回率（0~1，越高越好）
  MRR     — 首个相关结果的倒数排名均值（0~1，越高越好）
  Precision@k — top-k 中相关文档占比（0~1，越高越好）
"""

import json
import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path


# ===== 内置法律领域标准测试集 =====

DEFAULT_TEST_SET: List[Dict[str, Any]] = [
    {
        "query": "盗窃罪数额较大标准",
        "relevant_keywords": ["盗窃", "数额较大", "一千元", "三千元", "立案追诉"],
        "relevant_laws": ["关于办理盗窃刑事案件适用法律若干问题的解释"],
    },
    {
        "query": "诈骗罪立案标准 2022",
        "relevant_keywords": ["诈骗", "数额较大", "五千元", "五千", "诈骗罪"],
        "relevant_laws": ["关于审理诈骗刑事案件具体应用法律若干问题的解释"],
    },
    {
        "query": "非法吸收公众存款罪 量刑",
        "relevant_keywords": ["非法吸收公众存款", "量刑", "有期徒刑", "三年", "罚金"],
        "relevant_laws": ["关于审理非法吸收公众存款刑事案件具体应用法律若干问题的解释"],
    },
    {
        "query": "开设赌场罪情节严重",
        "relevant_keywords": ["开设赌场", "情节严重", "抽头渔利", "赌资", "参赌人数"],
        "relevant_laws": ["关于办理赌博刑事案件具体应用法律若干问题的解释"],
    },
    {
        "query": "职务侵占罪数额标准",
        "relevant_keywords": ["职务侵占", "数额较大", "六万元", "一百万元", "立案标准"],
        "relevant_laws": [],
    },
    {
        "query": "集资诈骗罪 重婚",
        "relevant_keywords": ["集资诈骗", "数额", "诈骗", "非法占有"],
        "relevant_laws": ["关于审理非法集资刑事案件具体应用法律若干问题的解释"],
    },
    {
        "query": "掩饰隐瞒犯罪所得收益罪",
        "relevant_keywords": ["掩饰", "隐瞒", "犯罪所得", "收益", "洗钱"],
        "relevant_laws": [],
    },
    {
        "query": "敲诈勒索罪 数额",
        "relevant_keywords": ["敲诈勒索", "数额较大", "三千元", "三千", "立案追诉"],
        "relevant_laws": [],
    },
    {
        "query": "挪用资金罪 量刑",
        "relevant_keywords": ["挪用资金", "数额较大", "营利活动", "非法活动"],
        "relevant_laws": [],
    },
    {
        "query": "行贿罪 立案标准",
        "relevant_keywords": ["行贿", "立案标准", "数额", "不正当利益", "贿赂"],
        "relevant_laws": [],
    },
    {
        "query": "污染环境罪 情节严重",
        "relevant_keywords": ["污染环境", "情节严重", "严重污染", "有害物质"],
        "relevant_laws": [],
    },
    {
        "query": "帮助信息网络犯罪活动罪",
        "relevant_keywords": ["帮助信息网络", "犯罪活动", "支付结算", "广告推广"],
        "relevant_laws": [],
    },
    {
        "query": "非法经营罪 情节特别严重",
        "relevant_keywords": ["非法经营", "情节严重", "情节特别严重", "扰乱市场秩序"],
        "relevant_laws": [],
    },
    {
        "query": "寻衅滋事罪 情节恶劣",
        "relevant_keywords": ["寻衅滋事", "情节恶劣", "强拿硬要", "任意损毁"],
        "relevant_laws": [],
    },
    {
        "query": "危险驾驶罪 醉驾",
        "relevant_keywords": ["危险驾驶", "醉驾", "血液酒精", "80毫克", "拘役"],
        "relevant_laws": [],
    },
]


def _is_relevant(result: Dict[str, Any], test_case: Dict[str, Any]) -> float:
    """
    判断检索结果是否相关，返回相关度分数（0~1）

    相关判定规则（任一满足即相关）：
    1. 法律名称精确匹配 relevant_laws
    2. 内容关键词命中 >= 2 个（允许部分重叠）
    3. 内容关键词命中 = 1 个但有标题匹配
    """
    law = result.get("law", "")
    content = result.get("content", "")
    preview = result.get("preview", "")
    text = (content + preview).lower()

    # 规则1：法律名称匹配
    for ref_law in test_case.get("relevant_laws", []):
        if ref_law and ref_law in law:
            return 1.0

    # 规则2：关键词命中
    keywords = test_case.get("relevant_keywords", [])
    matched = sum(1 for kw in keywords if kw.lower() in text)
    if matched >= 2:
        return 1.0
    if matched == 1 and any(kw.lower() in law.lower() for kw in keywords):
        return 0.8
    if matched >= 1:
        return 0.5

    return 0.0


def _dcg(gains: List[float], k: int) -> float:
    """折损累计增益 DCG@k"""
    dcg_val = 0.0
    for i, g in enumerate(gains[:k]):
        dcg_val += g / math.log2(i + 2)  # i+2 因为从位置1开始
    return dcg_val


def _ndcg(relevances: List[List[float]], k: int) -> float:
    """平均 nDCG@k（跨查询平均）"""
    ndcg_vals = []
    for gains in relevances:
        dcg_val = _dcg(gains, k)
        ideal = sorted(gains, reverse=True)
        idcg_val = _dcg(ideal, k)
        if idcg_val > 0:
            ndcg_vals.append(dcg_val / idcg_val)
        else:
            ndcg_vals.append(0.0)
    return sum(ndcg_vals) / len(ndcg_vals) if ndcg_vals else 0.0


def _recall(gains: List[float], k: int) -> float:
    """Recall@k"""
    total_relevant = sum(gains)
    if total_relevant == 0:
        return 0.0
    return sum(gains[:k]) / total_relevant


def _mrr(gains: List[float]) -> float:
    """MRR（首个相关结果倒数排名均值）"""
    for i, g in enumerate(gains):
        if g > 0:
            return 1.0 / (i + 1)
    return 0.0


def _precision_at_k(gains: List[float], k: int) -> float:
    """Precision@k"""
    if k == 0:
        return 0.0
    return sum(gains[:k]) / k


@dataclass
class EvalResult:
    """单次评估结果"""
    query: str
    k: int
    ndcg: float
    recall: float
    mrr: float
    precision: float
    relevance_scores: List[float]
    num_results: int


@dataclass
class EvalReport:
    """整体评估报告"""
    total_queries: int
    k: int
    avg_ndcg: float
    avg_recall: float
    avg_mrr: float
    avg_precision: float
    per_query: List[EvalResult]
    test_set_source: str
    timestamp: str


class RetrievalEvaluator:
    """
    检索质量评估器

    用法：
        evaluator = RetrievalEvaluator()
        report = evaluator.evaluate(rag_system, test_set=None, k=5)
        print(report)
    """

    def __init__(self):
        self._test_set = DEFAULT_TEST_SET

    @property
    def test_set(self) -> List[Dict[str, Any]]:
        return self._test_set

    def add_test_case(self, query: str, relevant_keywords: List[str],
                      relevant_laws: List[str] = None):
        """添加自定义测试用例"""
        self._test_set.append({
            "query": query,
            "relevant_keywords": relevant_keywords,
            "relevant_laws": relevant_laws or [],
        })

    def load_test_set(self, path: str):
        """从 JSON 文件加载测试集"""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            self._test_set = data
        else:
            self._test_set = data.get("test_cases", data.get("cases", []))

    def evaluate(
        self,
        rag_system,
        test_set: List[Dict[str, Any]] = None,
        k: int = 5,
        verbose: bool = True,
    ) -> EvalReport:
        """
        对 RAG 系统进行质量评估

        Args:
            rag_system: LawRAG 实例
            test_set: 测试用例列表（None 则使用内置测试集）
            k: 评估截断深度
            verbose: 是否打印详细结果

        Returns:
            EvalReport
        """
        from datetime import datetime
        cases = test_set or self._test_set
        results: List[EvalResult] = []

        for case in cases:
            query = case["query"]
            # 调用 RAG 检索
            try:
                search_results = rag_system.search(query, top_k=k * 2, hybrid=True)
            except Exception as e:
                if verbose:
                    print(f"  ⚠️ 检索失败 [{query}]: {e}")
                continue

            # 计算相关度分数
            rel_scores = [_is_relevant(r, case) for r in search_results[:k]]

            # 填充到 k 长度（无结果视为 0）
            while len(rel_scores) < k:
                rel_scores.append(0.0)

            # 各指标
            ndcg = _ndcg([rel_scores], k)
            rec = _recall(rel_scores, k)
            mrr = _mrr(rel_scores)
            prec = _precision_at_k(rel_scores, k)

            results.append(EvalResult(
                query=query,
                k=k,
                ndcg=round(ndcg, 4),
                recall=round(rec, 4),
                mrr=round(mrr, 4),
                precision=round(prec, 4),
                relevance_scores=rel_scores,
                num_results=len(search_results),
            ))

        # 汇总
        n = len(results)
        avg_ndcg = sum(r.ndcg for r in results) / n if n else 0
        avg_recall = sum(r.recall for r in results) / n if n else 0
        avg_mrr = sum(r.mrr for r in results) / n if n else 0
        avg_prec = sum(r.precision for r in results) / n if n else 0

        report = EvalReport(
            total_queries=n,
            k=k,
            avg_ndcg=round(avg_ndcg, 4),
            avg_recall=round(avg_recall, 4),
            avg_mrr=round(avg_mrr, 4),
            avg_precision=round(avg_prec, 4),
            per_query=results,
            test_set_source="builtin" if test_set is None else "custom",
            timestamp=datetime.now().isoformat(),
        )

        if verbose:
            self._print_report(report)

        return report

    def _print_report(self, report: EvalReport):
        """打印评估报告"""
        print("\n" + "=" * 60)
        print("  检索质量评估报告")
        print("=" * 60)
        print(f"  测试集: {report.test_set_source}")
        print(f"  查询数量: {report.total_queries}")
        print(f"  评估深度 k: {report.k}")
        print()
        print(f"  📊 整体得分:")
        print(f"    nDCG@{report.k}    : {report.avg_ndcg:.4f}  "
              f"({'优秀' if report.avg_ndcg > 0.7 else '良好' if report.avg_ndcg > 0.5 else '需改进'})")
        print(f"    Recall@{report.k}  : {report.avg_recall:.4f}")
        print(f"    MRR               : {report.avg_mrr:.4f}")
        print(f"    Precision@{report.k}: {report.avg_precision:.4f}")
        print()
        print(f"  📋 各查询详情:")
        print(f"  {'查询':<30s} {'nDCG':>6s} {'Recall':>7s} {'MRR':>5s} {'P@K':>5s}")
        print(f"  {'-'*30} {'-'*6} {'-'*7} {'-'*5} {'-'*5}")
        for r in report.per_query:
            print(f"  {r.query:<30s} {r.ndcg:>6.4f} {r.recall:>7.4f} {r.mrr:>5.4f} {r.precision:>5.4f}")

        # 给出改进建议
        print()
        print(f"  💡 改进建议:")
        if report.avg_ndcg < 0.5:
            print("    · nDCG 偏低，建议检查向量模型与法律文本的匹配度")
            print("    · 考虑使用更大/更专业的法律嵌入模型")
        if report.avg_recall < 0.6:
            print("    · Recall 偏低，BM25 可能遗漏语义相关内容")
            print("    · 考虑扩大 top_k 或调整混合检索权重")
        if report.avg_mrr < 0.5:
            print("    · MRR 偏低，相关结果排名靠后")
            print("    · 建议优先优化召回阶段（提高相关结果进入 top-5 的概率）")
        if report.avg_ndcg >= 0.7:
            print("    · 整体表现良好，继续保持")

        print("=" * 60)

    def to_json(self, report: EvalReport) -> str:
        """导出为 JSON 字符串"""
        data = {
            "total_queries": report.total_queries,
            "k": report.k,
            "avg_ndcg": report.avg_ndcg,
            "avg_recall": report.avg_recall,
            "avg_mrr": report.avg_mrr,
            "avg_precision": report.avg_precision,
            "test_set_source": report.test_set_source,
            "timestamp": report.timestamp,
            "per_query": [
                {
                    "query": r.query,
                    "ndcg": r.ndcg,
                    "recall": r.recall,
                    "mrr": r.mrr,
                    "precision": r.precision,
                    "relevance_scores": r.relevance_scores,
                    "num_results": r.num_results,
                }
                for r in report.per_query
            ],
        }
        return json.dumps(data, ensure_ascii=False, indent=2)


# ===== CLI =====

def main():
    import argparse
    parser = argparse.ArgumentParser(description="检索质量评估")
    parser.add_argument("--test-set", type=str, help="测试集 JSON 文件路径")
    parser.add_argument("--k", type=int, default=5, help="评估截断深度（默认5）")
    parser.add_argument("--output", type=str, help="评估报告输出路径（JSON）")
    parser.add_argument("--quiet", action="store_true", help="静默模式（仅输出JSON）")
    args = parser.parse_args()

    from law_rag import LawRAG

    evaluator = RetrievalEvaluator()
    if args.test_set:
        evaluator.load_test_set(args.test_set)

    rag = LawRAG(enable_vector=True)
    rag.index_laws()

    report = evaluator.evaluate(rag, k=args.k, verbose=not args.quiet)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(evaluator.to_json(report))
        print(f"\n✅ 报告已保存: {args.output}")


if __name__ == "__main__":
    main()
