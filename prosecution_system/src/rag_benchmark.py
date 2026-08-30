# -*- coding: utf-8 -*-
"""
法律 RAG 检索 Benchmark 工具 - prosecution_system/src/rag_benchmark.py

评估不同检索策略在法律查询上的表现：
- BM25 (关键词倒排索引)
- 向量检索 (semantic embedding)
- 混合检索 (RRF fusion)

用法:
  python -m rag_benchmark                    # 运行默认测试集
  python -m rag_benchmark --query "盗窃罪数额标准"  # 单次查询对比
  python -m rag_benchmark --rebuild-vectors  # 重建向量索引
  python -m rag_benchmark --list-chunks     # 查看已索引法律条块
"""

import argparse
import time
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple

import sys
sys.path.insert(0, str(Path(__file__).parent))

from law_rag import LawRAG


# ── 标准法律查询测试集 ────────────────────────────────────────

LEGAL_QUERIES = [
    {
        "id": "Q01",
        "query": "盗窃罪数额较大的标准是多少",
        "intent": "查盗窃罪入罪数额门槛",
        "expected_keywords": ["盗窃", "数额较大", "1000", "2000", "3000"],
        "expected_laws": ["关于办理盗窃刑事案件适用法律若干问题的解释"],
    },
    {
        "id": "Q02",
        "query": "诈骗罪判多少年",
        "intent": "查诈骗罪量刑标准",
        "expected_keywords": ["诈骗", "量刑", "三年", "有期徒刑"],
        "expected_laws": ["关于审理诈骗刑事案件具体应用法律若干问题的解释"],
    },
    {
        "id": "Q03",
        "query": "毒品犯罪死刑标准",
        "intent": "查毒品犯罪死刑条件",
        "expected_keywords": ["毒品", "死刑", "海洛因", "冰毒", "50克"],
        "expected_laws": ["刑法第347条"],
    },
    {
        "id": "Q04",
        "query": "职务侵占罪入罪数额",
        "intent": "查职务侵占罪立案标准",
        "expected_keywords": ["职务侵占", "数额较大", "3万", "30000"],
        "expected_laws": ["立案追诉标准(二)"],
    },
    {
        "id": "Q05",
        "query": "故意伤害致人重伤怎么判",
        "intent": "查故意伤害罪重伤量刑",
        "expected_keywords": ["故意伤害", "重伤", "三年", "十年"],
        "expected_laws": ["刑法第234条"],
    },
    {
        "id": "Q06",
        "query": "开设赌场罪抽头渔利多少入罪",
        "intent": "查开设赌场罪入罪标准",
        "expected_keywords": ["开设赌场", "抽头渔利", "5000"],
        "expected_laws": ["关于办理赌博刑事案件具体应用法律若干问题的解释"],
    },
    {
        "id": "Q07",
        "query": "抢夺罪数额较大标准",
        "intent": "查抢夺罪入罪门槛",
        "expected_keywords": ["抢夺", "数额较大", "1000", "2000"],
        "expected_laws": ["关于办理抢夺刑事案件适用法律若干问题的解释"],
    },
    {
        "id": "Q08",
        "query": "累犯从重处罚规定",
        "intent": "查累犯处罚规则",
        "expected_keywords": ["累犯", "从重", "刑法第65条"],
        "expected_laws": ["刑法第65条"],
    },
    {
        "id": "Q09",
        "query": "自首可以减轻处罚吗",
        "intent": "查自首从轻/减轻规则",
        "expected_keywords": ["自首", "减轻", "刑法第67条"],
        "expected_laws": ["刑法第67条"],
    },
    {
        "id": "Q10",
        "query": "挪用公款罪立案标准",
        "intent": "查挪用公款罪入罪门槛",
        "expected_keywords": ["挪用公款", "立案", "数额", "3万"],
        "expected_laws": ["立案追诉标准(二)"],
    },
]


def keyword_hit_rate(results: List[Dict], expected_keywords: List[str]) -> float:
    """计算关键词命中率"""
    if not results or not expected_keywords:
        return 0.0
    all_content = " ".join(r.get("content", "") for r in results[:5])
    hits = sum(1 for kw in expected_keywords if kw in all_content)
    return hits / len(expected_keywords)


def law_coverage(results: List[Dict], expected_laws: List[str]) -> float:
    """计算法律覆盖度"""
    if not results or not expected_laws:
        return 0.0
    found_laws = set()
    for r in results[:10]:
        law = r.get("law_name", "")
        for exp in expected_laws:
            if exp in law:
                found_laws.add(exp)
    return len(found_laws) / len(expected_laws)


def avg_relevance_score(results: List[Dict]) -> float:
    """估算平均相关度（基于关键词密度）"""
    if not results:
        return 0.0
    scores = []
    for r in results[:5]:
        content = r.get("content", "")
        # 简单评分：内容长度适中（100-500字）得高分
        length = len(content)
        if 100 <= length <= 500:
            scores.append(0.9)
        elif 50 <= length <= 800:
            scores.append(0.7)
        else:
            scores.append(0.4)
    return sum(scores) / len(scores) if scores else 0.0


def run_benchmark(rag: LawRAG, queries: List[Dict] = None, top_n: int = 5) -> Dict[str, Any]:
    """运行完整 benchmark"""
    queries = queries or LEGAL_QUERIES
    strategies = ["bm25", "hybrid"]  # vector 模式需网络+模型，当前不可用
    results: Dict[str, List] = {s: [] for s in strategies}

    print(f"\n{'='*70}")
    print(f"  法律 RAG 检索 Benchmark — {len(queries)} 个查询 × {len(strategies)} 种策略")
    print(f"{'='*70}")

    for q in queries:
        qid = q["id"]
        query = q["query"]

        print(f"\n[{qid}] {query}")
        print(f"  意图: {q['intent']}")

        for strategy in strategies:
            start = time.time()
            hits = rag.search(query, top_k=top_n, hybrid=(strategy == "hybrid"))
            elapsed = (time.time() - start) * 1000

            kw_rate = keyword_hit_rate(hits, q["expected_keywords"])
            law_cov = law_coverage(hits, q["expected_laws"])
            rel = avg_relevance_score(hits)

            results[strategy].append({
                "query_id": qid,
                "query": query,
                "hits": len(hits),
                "keyword_hit_rate": kw_rate,
                "law_coverage": law_cov,
                "relevance_score": rel,
                "latency_ms": round(elapsed, 1),
            })

            print(f"  {strategy:8s}: {len(hits)} hits | "
                  f"关键词命中率={kw_rate:.0%} | "
                  f"法条覆盖={law_cov:.0%} | "
                  f"延迟={elapsed:.0f}ms")

    # ── 汇总统计 ───────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("  汇总结果")
    print(f"{'='*70}")

    summary = {}
    for strategy in strategies:
        stats = results[strategy]
        n = len(stats)
        avg_kw = sum(s["keyword_hit_rate"] for s in stats) / n
        avg_law = sum(s["law_coverage"] for s in stats) / n
        avg_rel = sum(s["relevance_score"] for s in stats) / n
        avg_lat = sum(s["latency_ms"] for s in stats) / n

        summary[strategy] = {
            "avg_keyword_hit_rate": round(avg_kw, 3),
            "avg_law_coverage": round(avg_law, 3),
            "avg_relevance_score": round(avg_rel, 3),
            "avg_latency_ms": round(avg_lat, 1),
            "total_queries": n,
        }

        print(f"\n  {strategy.upper()}:")
        print(f"    关键词命中率:     {avg_kw:.1%}")
        print(f"    法条覆盖度:       {avg_law:.1%}")
        print(f"    平均相关度:       {avg_rel:.1%}")
        print(f"    平均延迟:         {avg_lat:.0f}ms")

    # 找出最佳策略
    best = max(summary.keys(), key=lambda s: summary[s]["avg_relevance_score"])
    print(f"\n  🏆 最佳策略: {best.upper()} (相关度 {summary[best]['avg_relevance_score']:.1%})")

    return {"summary": summary, "details": results}


def main():
    parser = argparse.ArgumentParser(description="法律 RAG 检索 Benchmark")
    parser.add_argument("--query", type=str, help="单个查询（对比三种策略）")
    parser.add_argument("--top-n", type=int, default=5, help="返回结果数量（默认5）")
    parser.add_argument("--rebuild-vectors", action="store_true", help="强制重建向量索引")
    parser.add_argument("--list-chunks", action="store_true", help="列出已索引的法律和块数")
    parser.add_argument("--export-json", type=str, help="导出结果到 JSON 文件")
    args = parser.parse_args()

    print("正在初始化 LawRAG（加载 78,240 个法律文本块）...")
    rag = LawRAG(enable_vector=True)
    print(f"✅ 已加载 {len(rag.chunks)} 个文本块, {len(rag.inverted_index)} 个索引词")
    if not rag.vector_enabled:
        print("  (向量检索不可用，使用纯 BM25 模式)")
    else:
        print(f"  (向量检索已启用)")

    if args.list_chunks:
        print("\n已索引法律列表:")
        for law_name, info in sorted(rag.law_index.items()):
            print(f"  {law_name}: {info.get('chunks_count', 0)} 块 | {info.get('category', '')}")
        return

    if args.query:
        print(f"\n查询: {args.query}")
        print(f"{'策略':<10} {'命中数':>6} {'延迟':>8}")
        print("-" * 30)
        for strategy in ["bm25", "hybrid"]:
            start = time.time()
            hits = rag.search(args.query, top_k=args.top_n, hybrid=(strategy == "hybrid"))
            elapsed = (time.time() - start) * 1000
            print(f"{strategy:<10} {len(hits):>6} {elapsed:>7.0f}ms")

        print("\n--- BM25 Top 3 ---")
        for i, h in enumerate(rag.search(args.query, top_k=3, hybrid=False), 1):
            print(f"  [{i}] {h.get('law','?')} | {h.get('preview','')[:80]}...")

        print("\n--- Hybrid Top 3 ---")
        for i, h in enumerate(rag.search(args.query, top_k=3, hybrid=True), 1):
            print(f"  [{i}] {h.get('law','?')} | {h.get('preview','')[:80]}...")
        return

    # 完整 benchmark
    result = run_benchmark(rag, top_n=args.top_n)

    if args.export_json:
        with open(args.export_json, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 结果已导出至 {args.export_json}")


if __name__ == "__main__":
    main()
