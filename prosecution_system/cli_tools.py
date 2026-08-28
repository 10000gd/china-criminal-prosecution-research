#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI增强工具 - 命令行界面"""
import argparse
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sentencing_cases import get_sentencing_cases
CASES = get_sentencing_cases()
from advanced_analysis import SimilarityAnalyzer, StatisticsEngine, AnomalyDetector

def cmd_stats():
    """显示统计信息"""
    stats = StatisticsEngine.analyze(CASES)
    print("\n📊 案例库统计")
    print("=" * 40)
    print(f"总案例数: {stats['total']}")
    print(f"罪名种类: {stats['crimes']}")
    print(f"平均刑期: {stats['sentencing']['avg']:.2f} 年")
    print(f"最高刑期: {stats['sentencing']['max']} 年")
    print(f"最低刑期: {stats['sentencing']['min']} 年")
    print("\n📌 罪名分布 (Top 10)")
    for crime, count in stats['crime_dist'].items():
        print(f"  {crime}: {count}")
    print("\n📍 省份分布 (Top 10)")
    for prov, count in stats['province_dist'].items():
        print(f"  {prov}: {count}")

def cmd_search(query):
    """搜索案例"""
    results = [c for c in CASES if query.lower() in str(c).lower()]
    print(f"\n🔍 搜索 '{query}': 找到 {len(results)} 条结果\n")
    for case in results[:10]:
        print(f"  [{case['case_id']}] {case['case_name']}")
        print(f"    罪名: {case['crime']}, 刑期: {case.get('sentence_years', 'N/A')}年")
        print(f"    省份: {case.get('province', 'N/A')}")
        print()

def cmd_similar(case_id):
    """查找相似案例"""
    target = next((c for c in CASES if c['case_id'] == case_id), None)
    if not target:
        print(f"❌ 未找到案例: {case_id}")
        return
    similar = SimilarityAnalyzer.find_similar(target, CASES, n=5)
    print(f"\n🔗 与 [{case_id}] 相似的案例:\n")
    for case, score in similar:
        print(f"  [{case['case_id']}] {case['case_name']} (相似度: {score:.2%})")
        print(f"    刑期: {case.get('sentence_years', 'N/A')}年")

def cmd_anomaly():
    """检测异常"""
    anomalies = AnomalyDetector.detect(CASES, threshold=2.0)
    print(f"\n⚠️ 检测到 {len(anomalies)} 个异常案例:\n")
    for item in anomalies[:10]:
        case = item['case']
        print(f"  [{case['case_id']}] {case['case_name']}")
        print(f"    偏离度: {item['deviation']:.2f}年 (Z-score: {item['z_score']})")

def cmd_export(format='json'):
    """导出数据"""
    if format == 'json':
        output = Path('cases_export.json')
        output.write_text(json.dumps(CASES, ensure_ascii=False, indent=2))
        print(f"✅ 导出到 {output}")
    elif format == 'csv':
        import csv
        output = Path('cases_export.csv')
        with output.open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CASES[0].keys())
            writer.writeheader()
            writer.writerows(CASES)
        print(f"✅ 导出到 {output}")

def main():
    parser = argparse.ArgumentParser(description='刑事追诉系统 CLI工具')
    subparsers = parser.add_subparsers(dest='cmd', help='命令')
    
    subparsers.add_parser('stats', help='显示统计信息')
    subparsers.add_parser('anomaly', help='检测异常案例')
    
    p_search = subparsers.add_parser('search', help='搜索案例')
    p_search.add_argument('query', help='搜索关键词')
    
    p_similar = subparsers.add_parser('similar', help='查找相似案例')
    p_similar.add_argument('case_id', help='案例ID')
    
    p_export = subparsers.add_parser('export', help='导出数据')
    p_export.add_argument('--format', choices=['json', 'csv'], default='json', help='导出格式')
    
    args = parser.parse_args()
    
    if args.cmd == 'stats':
        cmd_stats()
    elif args.cmd == 'search':
        cmd_search(args.query)
    elif args.cmd == 'similar':
        cmd_similar(args.case_id)
    elif args.cmd == 'anomaly':
        cmd_anomaly()
    elif args.cmd == 'export':
        cmd_export(args.format)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
