#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))  # src/ -> for intra-package imports

"""
检察机关办案系统 - 统一 CLI 工具
prosecution_system/src/cli.py

整合所有 CLI 工具的统一入口：

  python -m src.cli                          # 显示帮助
  python -m src.cli health                   # 系统健康检查
  python -m src.cli stats                    # 统计概览
  python -m src.cli list                     # 列出已加载案件
  python -m src.cli search <关键词>           # 搜索案件
  python -m src.cli report <案件ID>           # 生成案件报告
  python -m src.cli batch-report --all        # 批量生成报告
  python -m src.cli import <文件或目录>       # 导入案件数据
  python -m src.cli seed --count 20          # 生成种子数据
  python -m src.cli benchmark                 # RAG 检索 benchmark
  python -m src.cli rag-search <查询>         # 法律 RAG 检索

示例：
  python -m src.cli search 盗窃罪
  python -m src.cli report CASE-0001 --format html
  python -m src.cli batch-report --all --format pdf --output reports/
  python -m src.cli seed --count 30 --import
  python -m src.cli rag-search "盗窃罪数额较大标准" --top 5
  python -m src.cli benchmark --queries 10
"""

import argparse
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# ── 内部工具导入 ────────────────────────────────────────────────

from case_loader import CaseLoader
from stats_aggregator import StatsAggregator
from law_rag import LawRAG
from health import HealthChecker as SystemHealthChecker


# ═══════════════════════════════════════════════════════════════
# 通用工具
# ═══════════════════════════════════════════════════════════════

def _print_header(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def _load_system():
    """加载系统核心组件"""
    print("正在初始化系统...")
    t0 = time.time()
    loader = CaseLoader()
    stats = StatsAggregator()
    t1 = time.time()
    print(f"✅ 系统就绪（{t1-t0:.1f}s）")
    return loader, stats


# ═══════════════════════════════════════════════════════════════
# 命令实现
# ═══════════════════════════════════════════════════════════════

def cmd_health(args):
    """系统健康检查"""
    _print_header("系统健康检查")
    result = SystemHealthChecker.check()
    checks = result.get("checks", {})
    ok = sum(1 for v in checks.values() if v.get("status") == "ok")
    total = len(checks)
    print(f"\n{'状态':<8} {'检查项':<30} {'详情'}")
    print("-" * 70)
    for name, info in checks.items():
        icon = {"ok": "✅", "warn": "⚠️", "error": "❌", "healthy": "✅"}.get(info.get("status", ""), "?")
        msg = info.get("message", str(info))[:40]
        print(f"{icon} {name:<30} {msg}")
    print(f"\n通过: {ok}/{total}  |  时间: {result.get('timestamp', '')}")
    return 0 if ok == total else 1


def cmd_stats(args):
    """统计概览"""
    loader, stats = _load_system()
    _print_header("统计概览")
    all_stats = stats.get_all_stats()
    print(f"\n📊 案件统计")
    print(f"  总案件数: {all_stats.get('total_cases', 0)}")
    print(f"  省份数:   {all_stats.get('provinces_count', 0)}")
    print(f"  罪名类型: {all_stats.get('crime_types_count', 0)}")
    if "hallucination" in all_stats:
        h = all_stats["hallucination"]
        print(f"\n🧠 幻觉率统计")
        print(f"  平均幻觉率:   {h.get('avg_hallucination_rate', 0):.1%}")
        print(f"  平均置信度:   {h.get('avg_confidence', 0):.1f}/100")
        print(f"  高置信案件:   {h.get('high_confidence_count', 0)}")
    if "provincial_diffs" in all_stats:
        pd = all_stats["provincial_diffs"]
        print(f"\n📍 省级差异（{len(pd)} 省份）")
        for p in list(pd)[:5]:
            print(f"  {p['province']}: {p.get('crime_type', '?')} 门槛 {p.get('threshold_display', '?')}")
    return 0


def cmd_list(args):
    """列出已加载案件"""
    loader, _ = _load_system()
    _print_header(f"已加载案件（共 {len(loader.list_cases())} 个）")
    cases = loader.list_cases()
    if not cases:
        print("  （无案件）")
        return 0
    fmt = args.format
    if fmt == "table":
        print(f"{'案件ID':<20} {'案件名称':<20} {'状态'}")
        print("-" * 50)
        for c in cases:
            cid = c.get("case_id", "?") if isinstance(c, dict) else c
            cname = c.get("case_name", "") if isinstance(c, dict) else ""
            status = c.get("status", "") if isinstance(c, dict) else ""
            print(f"{cid:<20} {cname:<20} {status}")
    else:
        for c in cases:
            cid = c.get("case_id", "?") if isinstance(c, dict) else c
            print(f"  • {cid}")
    return 0


def cmd_search(args):
    """搜索案件"""
    loader, _ = _load_system()
    _print_header(f"搜索结果：{args.query!r}")
    results = loader.search_cases(args.query)[:args.top]
    if not results:
        print("  （无结果）")
        return 0
    print(f"找到 {len(results)} 个相关案件：\n")
    for r in results:
        cid = r.get("case_id", "?")
        score = r.get("score", 0)
        preview = r.get("preview", "")[:60]
        print(f"  [{score:.2f}] {cid}")
        if preview:
            print(f"         {preview}...")
        print()
    return 0


def cmd_report(args):
    """生成案件报告"""
    loader, stats = _load_system()
    case_id = args.case_id
    meta = loader.get_meta(case_id)
    if not meta:
        print(f"❌ 案件不存在: {case_id}")
        return 1
    info = loader.get_case_info(case_id)
    charges = loader.get_charges(case_id)
    output = Path(args.output or f"report_{case_id}.{args.format}")
    _print_header(f"报告生成：{case_id}")
    print(f"  格式: {args.format}")
    print(f"  输出: {output}")
    # 简单文本报告
    content = [
        f"# 案件报告：{case_id}",
        f"",
        f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"",
        f"## 案件概要",
        f"- 省份: {info.get('province', '未知') if info else '未知'}",
        f"- 案号: {info.get('case_number', '未知') if info else '未知'}",
        f"- 涉案金额: {info.get('case_amount', 0)/10000:.1f}万元" if info and info.get("case_amount") else "- 涉案金额: 未知",
        f"",
        f"## 罪名信息",
    ]
    if charges:
        for c in charges.get("charges", []):
            content.append(f"- **{c.get('name', '?')}**")
            if c.get("amount"):
                content.append(f"  涉案金额: {c['amount']/10000:.1f}万元")
            if c.get("sentencing_recommendation"):
                content.append(f"  量刑建议: {c['sentencing_recommendation']}")
    content.extend([
        f"",
        f"## 证据缺口",
    ])
    gaps = loader.get_evidence_gaps(case_id)
    if gaps:
        for g in gaps:
            content.append(f"- {g.get('description', g) if isinstance(g, dict) else g}")
    else:
        content.append("  （无记录）")
    content.extend([
        f"",
        f"## 幻觉率: {meta.get('hallucination_rate', 'N/A')}",
        f"## 置信度: {meta.get('confidence_score', 'N/A')}",
    ])
    output.write_text("\n".join(content), encoding="utf-8")
    print(f"✅ 报告已保存: {output}")
    return 0


def cmd_batch_report(args):
    """批量生成报告"""
    loader, _ = _load_system()
    output_dir = Path(args.output or "reports")
    output_dir.mkdir(exist_ok=True)
    _print_header("批量报告生成")
    all_cases = loader.list_cases()
    cases_to_report = all_cases if args.all else all_cases[:args.limit]
    print(f"  目标: {len(cases_to_report)} 个案件")
    print(f"  输出: {output_dir}")
    print(f"  格式: {args.format}")
    ok, fail = 0, []
    for cid in cases_to_report:
        try:
            meta = loader.get_meta(cid)
            info = loader.get_case_info(cid)
            content = [f"# {cid}", f"生成: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ""]
            if info:
                content.append(f"**省份**: {info.get('province','?')}")
                content.append(f"**案号**: {info.get('case_number','?')}")
                content.append(f"**涉案金额**: {info.get('case_amount',0)/10000:.1f}万元" if info.get("case_amount") else "**涉案金额**: N/A")
            charges = loader.get_charges(cid)
            if charges:
                content.append("**罪名**: " + ", ".join(c.get("name","?") for c in charges.get("charges", [])))
            if meta:
                content.append(f"**幻觉率**: {meta.get('hallucination_rate','N/A')}")
                content.append(f"**置信度**: {meta.get('confidence_score','N/A')}")
            (output_dir / f"{cid}.md").write_text("\n".join(content), encoding="utf-8")
            ok += 1
        except Exception as e:
            fail.append((cid, str(e)))
    print(f"\n✅ 成功: {ok}  |  ❌ 失败: {len(fail)}")
    if fail:
        print("失败列表:")
        for cid, err in fail:
            print(f"  {cid}: {err}")
    return 0 if not fail else 1


def cmd_import(args):
    """导入案件数据"""
    loader, _ = _load_system()
    path = Path(args.path)
    _print_header(f"导入案件: {path}")
    if path.is_file():
        result = _import_single(loader, path)
        if result:
            print(f"✅ 导入成功: {result}")
        else:
            print(f"❌ 导入失败")
            return 1
    elif path.is_dir():
        files = list(path.glob("*.yaml")) + list(path.glob("*.yml")) + \
                list(path.glob("*.json"))
        print(f"  找到 {len(files)} 个文件")
        ok, fail = 0, []
        for f in files:
            r = _import_single(loader, f)
            if r:
                ok += 1
            else:
                fail.append(f.name)
        print(f"✅ 成功: {ok}  |  ❌ 失败: {len(fail)}")
        if fail:
            print(f"  失败文件: {', '.join(fail)}")
    else:
        print(f"❌ 路径不存在: {path}")
        return 1
    return 0


def _import_single(loader, path):
    """导入单个文件"""
    import yaml, json
    try:
        if path.suffix in (".yaml", ".yml"):
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        elif path.suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
        else:
            return None
        case_id = data.get("meta", {}).get("case_id") or data.get("case_id") or path.stem
        loader.cases_dir  # ensure writable
        dest = Path(loader.cases_dir) / f"{case_id}.yaml"
        with open(dest, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        loader.rebuild_search_index()
        return case_id
    except Exception as e:
        print(f"  ⚠️ {path.name}: {e}")
        return None


def cmd_seed(args):
    """生成种子数据"""
    try:
        from case_seed_generator import CaseSeedGenerator
    except ImportError:
        print("❌ case_seed_generator 未安装")
        return 1
    _print_header(f"种子数据生成")
    print(f"  数量: {args.count}")
    print(f"  导入: {'是' if args.import_data else '否'}")
    gen = CaseSeedGenerator()
    cases = gen.generate_cases(count=args.count)
    print(f"  已生成 {len(cases)} 个案件")
    if args.import_data:
        from case_loader import CaseLoader
        loader = CaseLoader()
        for case_id, data in cases:
            loader.save_case_data(case_id, data)
        loader.rebuild_search_index()
        print(f"  ✅ 已导入 CaseLoader")
    return 0


def cmd_rag_search(args):
    """法律 RAG 检索"""
    print(f"正在初始化法律数据库（78,240 个文本块）...")
    t0 = time.time()
    rag = LawRAG(enable_vector=True)
    print(f"✅ 加载完成（{time.time()-t0:.1f}s）\n")
    results = rag.search(args.query, top_k=args.top, hybrid=args.hybrid)
    _print_header(f"RAG 检索：{args.query!r}")
    mode = "🔍 混合检索（BM25 + TF-IDF）" if args.hybrid else "📄 BM25 检索"
    print(f"  模式: {mode}")
    print(f"  命中: {len(results)} 个\n")
    for i, r in enumerate(results, 1):
        law = r.get("law", "?")
        cat = r.get("category", "")
        preview = r.get("preview", "")[:120]
        score = r.get("score", r.get("bm25_score", 0))
        print(f"  [{i}] {law}（{cat}）")
        print(f"      得分: {score:.3f} | {preview}...")
        print()
    return 0


def cmd_benchmark(args):
    """RAG benchmark"""
    from rag_benchmark import run_benchmark, LEGAL_QUERIES
    print("正在初始化 LawRAG（加载 78,240 个文本块）...")
    rag = LawRAG(enable_vector=True)
    queries = LEGAL_QUERIES[:args.queries]
    results = run_benchmark(rag, queries=queries, top_n=5)
    return 0


# ═══════════════════════════════════════════════════════════════
# CLI 主入口
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="检察机关办案系统 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例命令:
  %(prog)s health              # 系统健康检查
  %(prog)s stats               # 统计概览
  %(prog)s list                # 列出所有案件
  %(prog)s search 盗窃罪       # 搜索案件
  %(prog)s report CASE-0001    # 生成案件报告
  %(prog)s batch-report --all  # 批量生成报告
  %(prog)s import ./cases/     # 导入案件
  %(prog)s seed --count 20    # 生成种子数据
  %(prog)s rag-search "盗窃罪数额"  # 法律检索
  %(prog)s benchmark           # RAG benchmark
        """
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # health
    p = sub.add_parser("health", help="系统健康检查")

    # stats
    p = sub.add_parser("stats", help="统计概览")

    # list
    p = sub.add_parser("list", help="列出所有案件")
    p.add_argument("--format", default="table", choices=["table", "simple"], help="输出格式")

    # search
    p = sub.add_parser("search", help="搜索案件")
    p.add_argument("query", help="搜索关键词")
    p.add_argument("--top", type=int, default=10, help="返回数量（默认10）")

    # report
    p = sub.add_parser("report", help="生成案件报告")
    p.add_argument("case_id", help="案件ID")
    p.add_argument("--format", default="md", choices=["md", "html", "pdf"], help="报告格式")
    p.add_argument("--output", help="输出文件路径")

    # batch-report
    p = sub.add_parser("batch-report", help="批量生成报告")
    p.add_argument("--all", action="store_true", help="所有案件")
    p.add_argument("--limit", type=int, default=50, help="限制数量")
    p.add_argument("--format", default="md", choices=["md", "html"], help="报告格式")
    p.add_argument("--output", default="reports/", help="输出目录")

    # import
    p = sub.add_parser("import", help="导入案件数据")
    p.add_argument("path", help="文件或目录路径")

    # seed
    p = sub.add_parser("seed", help="生成种子数据")
    p.add_argument("--count", type=int, default=10, help="生成数量")
    p.add_argument("--import", dest="import_data", action="store_true", help="同时导入CaseLoader")

    # rag-search
    p = sub.add_parser("rag-search", help="法律 RAG 检索")
    p.add_argument("query", help="检索查询")
    p.add_argument("--top", type=int, default=5, help="返回数量")
    p.add_argument("--hybrid", action="store_true", help="使用混合检索（默认BM25）")

    # benchmark
    p = sub.add_parser("benchmark", help="RAG 检索 benchmark")
    p.add_argument("--queries", type=int, default=10, help="测试查询数")

    args = parser.parse_args()

    # 命令路由
    commands = {
        "health": cmd_health,
        "stats": cmd_stats,
        "list": cmd_list,
        "search": cmd_search,
        "report": cmd_report,
        "batch-report": cmd_batch_report,
        "import": cmd_import,
        "seed": cmd_seed,
        "rag-search": cmd_rag_search,
        "benchmark": cmd_benchmark,
    }
    fn = commands.get(args.command)
    if fn:
        sys.exit(fn(args))


if __name__ == "__main__":
    main()
