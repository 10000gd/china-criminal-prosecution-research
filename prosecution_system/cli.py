# -*- coding: utf-8 -*-
"""
命令行工具 - prosecution_system/cli.py

提供命令行界面操作追诉系统：
- 案件管理
- 法律检索
- 辩护分析
- 量刑分析
- 报告生成

使用方法:
    python cli.py --help
    python cli.py search "盗窃罪"
    python cli.py analyze --case CASE-001
    python cli.py defense --case CASE-001
    python cli.py sentencing --crime 盗窃罪
"""

import argparse
import json
import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from case_loader import CaseLoader
from legal_db import LegalDB
from defense_enhancer import DefenseEnhancer, analyze_case_defense
from defense_case_db import search_defense_cases
from defense_opinion_generator import generate_defense_opinion
from sentencing_consistency import (
    SentencingConsistencyAnalyzer,
    analyze_sentencing,
    get_sentencing_report
)


def cmd_search(args):
    """法律检索命令"""
    db = LegalDB()
    
    results = db.fulltext_search(args.query, top_n=args.limit)
    
    if not results:
        print(f"未找到与 '{args.query}' 相关的法律条文")
        return
    
    print(f"\n🔍 找到 {len(results)} 条相关结果:\n")
    
    for i, result in enumerate(results, 1):
        title = result.get("title", result.get("article_no", ""))
        text = result.get("text", result.get("content", ""))[:200]
        print(f"{i}. 【{title}】")
        print(f"   {text}...")
        print()
    
    if args.format == "json":
        print(json.dumps(results, ensure_ascii=False, indent=2))


def cmd_case_list(args):
    """案件列表命令"""
    loader = CaseLoader()
    cases = loader.list_cases()
    
    if not cases:
        print("暂无案件数据")
        return
    
    print(f"\n📁 共有 {len(cases)} 个案件:\n")
    
    for case in cases:
        case_id = case.get("case_id", "")
        case_name = case.get("case_name", case.get("case_summary", "")[:30])
        status = case.get("status", "未知")
        print(f"  • {case_id}: {case_name} [{status}]")
    
    if args.format == "json":
        print(json.dumps(cases, ensure_ascii=False, indent=2))


def cmd_case_info(args):
    """案件详情命令"""
    loader = CaseLoader()
    case_data = loader.load(args.case_id)
    
    if not case_data:
        print(f"❌ 案件不存在: {args.case_id}")
        return
    
    print(f"\n📋 案件详情: {args.case_id}\n")
    print(f"案件名称: {case_data.get('case_name', '未知')}")
    print(f"案件类型: {case_data.get('case_type', '未知')}")
    print(f"判决日期: {case_data.get('judgment_date', '未知')}")
    print(f"来源: {case_data.get('source', '未知')}")
    
    # 被告人
    defendants = loader.get_defendants(args.case_id)
    if defendants:
        print(f"\n👤 被告人 ({len(defendants)}人):")
        for d in defendants:
            name = d.get("name", "未知")
            print(f"  - {name}")
    
    # 罪名
    charges = loader.get_charges(args.case_id)
    if charges:
        print(f"\n⚖️ 指控罪名:")
        for c in charges:
            name = c.get("name", "未知")
            article = c.get("article", "")
            print(f"  - {name} ({article})")


def cmd_analyze(args):
    """案件分析命令"""
    loader = CaseLoader()
    case_data = loader.load(args.case_id)
    
    if not case_data:
        print(f"❌ 案件不存在: {args.case_id}")
        return
    
    print(f"\n🔍 正在分析案件: {args.case_id}\n")
    
    # 辩护分析
    analysis = analyze_case_defense(case_data)
    
    primary = analysis.get("primary_defense")
    if primary:
        print(f"🛡️ 主要辩护方向: {primary.get('type', '待定')}")
        print(f"   置信度: {primary.get('confidence', 0):.0f}%")
        print(f"   法律依据: {primary.get('legal_basis', '')}")
        print(f"   风险缓解: {primary.get('risk_mitigation', '')}")
    else:
        print("🛡️ 未识别到明确的辩护方向")
    
    print(f"\n📊 整体辩护强度: {analysis.get('overall_strength', 0):.0f}/100")
    print(f"🎯 推荐策略: {analysis.get('recommended_strategy', '待定')}")
    print(f"🔮 预估结果: {analysis.get('estimated_outcome', '待定')}")
    
    # 辅助辩护
    secondary = analysis.get("secondary_defenses", [])
    if secondary:
        print(f"\n🔗 辅助辩护方向:")
        for s in secondary[:3]:
            print(f"  - {s.get('type', '')} (置信度: {s.get('confidence', 0):.0f}%)")
    
    if args.format == "json":
        print(json.dumps(analysis, ensure_ascii=False, indent=2))


def cmd_defense_search(args):
    """辩护案例检索命令"""
    result = search_defense_cases(
        crime=args.crime,
        defense_type=args.defense_type,
        limit=args.limit
    )
    
    print(f"\n📚 找到 {result['total']} 个相关案例:")
    print(f"   {result['summary']}\n")
    
    for case in result["cases"]:
        print(f"  • {case['case_name']}")
        print(f"    罪名: {case['crime']}")
        print(f"    结果: {case['outcome']}")
        print(f"    辩护: {case['key_defense']}")
        print()
    
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_defense_opinion(args):
    """辩护意见生成命令"""
    loader = CaseLoader()
    
    if args.case_id:
        case_data = loader.load(args.case_id)
        if not case_data:
            print(f"❌ 案件不存在: {args.case_id}")
            return
        analysis = analyze_case_defense(case_data)
        similar = search_defense_cases(
            defense_type=analysis.get("primary_defense", {}).get("type"),
            crime=analysis.get("primary_defense", {}).get("type"),
            limit=5
        )["cases"]
    else:
        # 从命令行参数构建案件
        case_data = {
            "case_id": "cli-input",
            "case_name": args.case_name or "命令行输入案件",
            "case_summary": args.facts or "",
            "defendants": [{"name": args.defendant or "被告"}],
            "charges": [{"name": args.crime or "未知罪名"}],
        }
        analysis = {"primary_defense": None, "secondary_defenses": [], "overall_strength": 0}
        similar = []
    
    opinion = generate_defense_opinion(case_data, analysis, similar, output_format="markdown")
    
    print(f"\n📝 辩护意见:\n")
    print(opinion)


def cmd_sentencing_stats(args):
    """量刑统计命令"""
    report = get_sentencing_report(args.crime)
    
    print(f"\n⚖️ 量刑一致性报告")
    print(f"   生成时间: {report['generated_at']}")
    print(f"   样本总数: {report['total_records']}")
    print(f"\n📊 {report['summary']}\n")
    
    # 详细统计
    if args.crime and args.crime in report["crime_stats"]:
        stats = report["crime_stats"][args.crime]
        print(f"【{args.crime}】详细统计:")
        print(f"  样本数: {stats['sample_count']}")
        print(f"  平均刑期: {stats.get('avg_sentence', 'N/A')}年")
        print(f"  中位数: {stats.get('median_sentence', 'N/A')}年")
        print(f"  标准差: {stats.get('std_dev', 0)}")
        print(f"  缓刑率: {stats.get('probation_rate', 0)}%")
        print(f"  区间分布: {stats.get('distribution', {})}")
    
    # 省份对比
    if args.province:
        comparison = report["provincial_comparison"]
        if args.province in comparison:
            data = comparison[args.province]
            print(f"\n【{args.province}】量刑数据:")
            print(f"  平均刑期: {data['avg_sentence']}年")
            print(f"  案例数: {data['count']}")
            print(f"  偏离类型: {data['deviation_type']}")
    
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))


def cmd_sentencing_deviation(args):
    """偏离度检测命令"""
    case_data = {
        "case_id": args.case_id or "cli-input",
        "crime": args.crime,
        "sentence_years": args.sentence,
        "province": args.province or None,
        "is_自首": args.zishou,
        "is_立功": args.ligong,
        "is_坦白": args.tanbai,
        "is_赔偿": args.peichang,
        "is_谅解": args.liangjie,
        "is_累犯": args.leifan,
    }
    
    result = analyze_sentencing(case_data)
    
    print(f"\n🔍 量刑偏离度分析")
    print(f"   罪名: {result['crime']}")
    print(f"   实际刑期: {result['actual_sentence']}年")
    print(f"   期望刑期: {result['expected_sentence']}年")
    print(f"   偏离度: {result['deviation_score']:.1f}")
    print(f"   偏离类型: {result['deviation_type']}")
    
    if result["factors"]:
        print(f"   影响因素: {', '.join(result['factors'])}")
    
    print(f"\n💡 {result['recommendation']}")
    
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_legal_lookup(args):
    """法律条文查询命令"""
    db = LegalDB()
    
    if args.article:
        # 按条文号查询
        result = db.get_article(int(args.article[3:]) if args.article.startswith("第") else args.article)
        if result:
            print(f"\n📜 {result.get('article_no', '')} {result.get('title', '')}")
            print(f"   {result.get('text', '')}")
        else:
            print(f"未找到条文: {args.article}")
    elif args.crime:
        # 按罪名查询
        results = db.search_case_types(args.crime)
        if results:
            print(f"\n⚖️ {args.crime} 相关法条:")
            for r in results[:10]:
                print(f"  - {r}")
        else:
            print(f"未找到罪名: {args.crime}")
    elif args.category:
        # 按分类浏览
        results = db.list_laws_by_category(args.category)
        if results:
            print(f"\n📚 {args.category} 分类下共 {len(results)} 部法律:")
            for r in results[:20]:
                name = r.get("name", r.get("title", ""))
                count = r.get("article_count", "")
                print(f"  - {name} ({count}条)")
        else:
            print(f"未找到该分类: {args.category}")


def cmd_import(args):
    """案件导入命令"""
    from case_importer import CaseImporter
    
    importer = CaseImporter(Path(args.output) if args.output else None)
    
    # 导出模板
    if args.template:
        importer.export_to_template(args.template)
        return
    
    # 导入文件
    result = importer.import_file(args.file)
    
    print(f"\n📥 导入结果:")
    print(result.summary())
    
    if result.errors:
        print(f"\n❌ 错误:")
        for err in result.errors:
            print(f"  - {err}")
    
    if result.warnings:
        print(f"\n⚠️ 警告:")
        for warn in result.warnings:
            print(f"  - {warn}")
    
    if result.imported_ids:
        print(f"\n✅ 已导入案件:")
        for case_id in result.imported_ids[:10]:
            print(f"  - {case_id}")
        if len(result.imported_ids) > 10:
            print(f"  ... 共 {len(result.imported_ids)} 个")


def cmd_stats(args):
    """数据集统计命令"""
    from sentencing_cases import get_statistics
    from defense_case_db import DefenseCaseDatabase
    
    print("\n📊 数据集统计\n")
    
    # 量刑案例统计
    print("【量刑案例库】")
    sentencing_stats = get_statistics()
    print(f"  总计: {sentencing_stats['total_count']} 个案例")
    print(f"  罪名: {len(sentencing_stats['crimes'])} 种")
    print(f"  省份: {len(sentencing_stats['provinces'])} 个")
    
    # 辩护案例统计
    print("\n【辩护案例库】")
    db = DefenseCaseDatabase()
    print(f"  总计: {len(db._cases)} 个案例")
    
    # 罪名统计
    crime_counts = {}
    for case in db._cases:
        crime = case.crime
        crime_counts[crime] = crime_counts.get(crime, 0) + 1
    
    print("  罪名分布:")
    for crime, count in sorted(crime_counts.items(), key=lambda x: -x[1])[:5]:
        print(f"    - {crime}: {count}个")
    
    # 辩护类型统计
    defense_counts = {}
    for case in db._cases:
        defense = case.key_defense
        defense_counts[defense] = defense_counts.get(defense, 0) + 1
    
    print("  辩护类型分布:")
    for defense, count in sorted(defense_counts.items(), key=lambda x: -x[1]):
        print(f"    - {defense}: {count}个")


def main():
    parser = argparse.ArgumentParser(
        description="中国刑事追诉智能辅助系统 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  法律检索:
    python cli.py search "正当防卫"
    python cli.py search "盗窃罪 入户" --limit 20

  案件管理:
    python cli.py cases
    python cli.py case CASE-001
    python cli.py case CASE-001 --info

  辩护分析:
    python cli.py analyze --case CASE-001
    python cli.py defense-search --defense-type 正当防卫
    python cli.py defense-opinion --case-id CASE-001

  量刑分析:
    python cli.py sentencing
    python cli.py sentencing --crime 盗窃罪
    python cli.py sentencing-deviation --crime 盗窃罪 --sentence 2.5 --province 北京 --zishou

  法律查询:
    python cli.py lookup --article 第20条
    python cli.py lookup --crime 盗窃罪
    python cli.py lookup --category 刑法

输出格式:
  默认输出为人类可读格式
  添加 --format json 输出JSON格式
        """
    )
    
    parser.add_argument("--format", choices=["text", "json"], default="text",
                       help="输出格式 (默认: text)")
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # search 命令
    p_search = subparsers.add_parser("search", help="法律检索")
    p_search.add_argument("query", help="搜索关键词")
    p_search.add_argument("--limit", type=int, default=10, help="返回结果数量")
    
    # cases 命令
    p_cases = subparsers.add_parser("cases", help="案件列表")
    
    # case 命令
    p_case = subparsers.add_parser("case", help="案件详情")
    p_case.add_argument("case_id", help="案件ID")
    p_case.add_argument("--info", action="store_true", help="显示详细信息")
    
    # analyze 命令
    p_analyze = subparsers.add_parser("analyze", help="案件辩护分析")
    p_analyze.add_argument("--case", dest="case_id", required=True, help="案件ID")
    
    # defense-search 命令
    p_defense_search = subparsers.add_parser("defense-search", help="辩护案例检索")
    p_defense_search.add_argument("--crime", help="罪名")
    p_defense_search.add_argument("--defense-type", help="辩护类型")
    p_defense_search.add_argument("--limit", type=int, default=10, help="返回数量")
    
    # defense-opinion 命令
    p_defense_opinion = subparsers.add_parser("defense-opinion", help="生成辩护意见")
    p_defense_opinion.add_argument("--case-id", help="案件ID")
    p_defense_opinion.add_argument("--case-name", help="案件名称")
    p_defense_opinion.add_argument("--defendant", help="被告人")
    p_defense_opinion.add_argument("--crime", help="罪名")
    p_defense_opinion.add_argument("--facts", help="案件事实")
    
    # sentencing 命令
    p_sentencing = subparsers.add_parser("sentencing", help="量刑统计")
    p_sentencing.add_argument("--crime", help="罪名")
    p_sentencing.add_argument("--province", help="省份")
    
    # sentencing-deviation 命令
    p_deviation = subparsers.add_parser("sentencing-deviation", help="偏离度检测")
    p_deviation.add_argument("--crime", required=True, help="罪名")
    p_deviation.add_argument("--sentence", type=float, required=True, help="实际刑期（年）")
    p_deviation.add_argument("--province", help="省份")
    p_deviation.add_argument("--case-id", help="案件ID")
    p_deviation.add_argument("--zishou", action="store_true", help="自首")
    p_deviation.add_argument("--ligong", action="store_true", help="立功")
    p_deviation.add_argument("--tanbai", action="store_true", help="坦白")
    p_deviation.add_argument("--peichang", action="store_true", help="赔偿")
    p_deviation.add_argument("--liangjie", action="store_true", help="谅解")
    p_deviation.add_argument("--leifan", action="store_true", help="累犯")
    
    # lookup 命令
    p_lookup = subparsers.add_parser("lookup", help="法律条文查询")
    p_lookup.add_argument("--article", help="条文号（如：第20条）")
    p_lookup.add_argument("--crime", help="罪名")
    p_lookup.add_argument("--category", help="法律分类")
    
    # import 命令
    p_import = subparsers.add_parser("import", help="导入案件数据")
    p_import.add_argument("file", help="文件或目录路径")
    p_import.add_argument("--output", "-o", help="输出目录")
    p_import.add_argument("--template", "-t", help="导出模板文件路径")
    
    # stats 命令
    p_stats = subparsers.add_parser("stats", help="数据集统计")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # 执行命令
    commands = {
        "search": cmd_search,
        "cases": cmd_case_list,
        "case": cmd_case_info,
        "analyze": cmd_analyze,
        "defense-search": cmd_defense_search,
        "defense-opinion": cmd_defense_opinion,
        "sentencing": cmd_sentencing_stats,
        "sentencing-deviation": cmd_sentencing_deviation,
        "lookup": cmd_legal_lookup,
        "import": cmd_import,
        "stats": cmd_stats,
    }
    
    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
