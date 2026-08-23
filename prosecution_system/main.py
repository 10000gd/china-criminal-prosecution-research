#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
追诉系统主入口 - prosecution_system/main.py

用法：
    python main.py                  # 交互式菜单
    python main.py serve             # 启动Web服务
    python main.py list             # 列出所有案件
    python main.py report hengda    # 生成报告
    python main.py track add ...     # 跟踪管理
    python main.py search 恒大       # 搜索案件
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import argparse
from case_loader import CaseLoader
from build_report import ReportBuilder
from wenshu_updater import CaseTracker, ManualTracker
from logging_config import setup_logging

OUTPUT_DIR = Path(__file__).parent / "output"
logger = setup_logging("main")


def cmd_list() -> None:
    """列出所有案件"""
    loader: CaseLoader = CaseLoader()
    cases = loader.list_cases()
    status_labels = {
        "investigating": "调查中",
        "prosecuted": "已起诉",
        "judged": "已判决",
        "appealed": "上诉中",
        "closed": "已结案",
    }
    logger.info(f"查询案件列表，共 {len(cases)} 个案件")
    print(f"\n{'='*60}")
    print(f" 追诉系统 · 案件数据库 ({len(cases)} 个案件)")
    print(f"{'='*60}")
    for c in cases:
        label = status_labels.get(c["status"], c["status"])
        print(f"\n  [{c['case_id']}] {c['case_name_full'] or c['case_name']}")
        print(f"    类型: {c.get('case_type', '')} | 状态: {label} | 密级: {c.get('confidentiality', '')}")
    print(f"\n{'='*60}\n")


def cmd_report(case_id: str, fmt: str = "tex") -> None:
    """生成报告"""
    loader: CaseLoader = CaseLoader()
    try:
        data = loader.load(case_id)
        case_name = data["meta"]["case_name_full"]
        logger.info(f"正在生成报告: {case_name}")
    except FileNotFoundError:
        logger.error(f"案件未找到: {case_id}")
        return

    builder = ReportBuilder(case_id, loader)
    case_slug = case_id.lower().replace("case-", "").replace("-", "")
    tex_path = OUTPUT_DIR / f"{case_slug}_report.tex"
    builder.save_tex(tex_path)

    if fmt == "pdf":
        logger.info("正在编译 PDF…（xelatex，可能需要30-60秒）")
        pdf_path = builder.compile_pdf(tex_path)
        if pdf_path:
            print(f"\n✅ PDF已生成: {pdf_path}")
    else:
        print(f"\n✅ LaTeX已生成: {tex_path}")


def cmd_search(query: str) -> None:
    """搜索案件"""
    loader: CaseLoader = CaseLoader()
    results = loader.search_cases(query)
    all_cases = loader.list_cases()
    name_matches = [c for c in all_cases
                    if query.lower() in (c.get("case_name", "") + c.get("case_name_full", "")).lower()]

    logger.info(f"搜索「{query}」: 名称匹配 {len(name_matches)} 个，全文匹配 {len(results)} 个")
    print(f"\n搜索「{query}」:")
    if name_matches:
        print(f"  按名称匹配: {len(name_matches)} 个")
        for c in name_matches:
            print(f"    [{c['case_id']}] {c['case_name_full'] or c['case_name']}")
    if results:
        print(f"  全文匹配: {len(results)} 个")
        for r in results:
            print(f"    [{r['case_id']}]")
    if not name_matches and not results:
        print("  未找到匹配结果")


def cmd_tracker(args) -> None:
    """跟踪管理"""
    tracker: CaseTracker = CaseTracker()
    action = args.tracker_action

    if not action:
        # 交互模式
        cases = tracker.list_tracked()
        if not cases:
            logger.info("暂无跟踪案件")
            print("暂无跟踪案件")
        else:
            for c in cases:
                print(f"  [{c['case_id']}] {c['case_num']} | {c['court']} | {c['status']}")
        return

    if action == "add":
        tracker.add_case(args.case_id, case_num=args.case_num or "",
                         court=args.court or "", status=args.status or "investigating")
    elif action == "list":
        for c in tracker.list_tracked():
            print(f"  [{c['case_id']}] {c['case_num']} | {c['court']} | {c['status']}")
    elif action == "update":
        tracker.update_status(args.case_id, args.new_status, event=args.event or "")
    elif action == "log":
        manual = ManualTracker()
        manual.log_event(args.case_id, args.event, source=args.source or "")
    elif action == "remove":
        tracker.remove_case(args.case_id)


def cmd_serve() -> None:
    """启动Web服务"""
    from web_app import app
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    logger.info(f"🚀 追诉系统启动: http://localhost:{port}，调试模式: {debug}")
    print(f"🚀 追诉系统启动中… http://localhost:{port}")
    print(f"   调试模式: {debug}")
    app.run(host="0.0.0.0", port=port, debug=debug)


def cmd_interactive() -> None:
    """交互式菜单"""
    loader: CaseLoader = CaseLoader()
    print(f"""
╔══════════════════════════════════════╗
║   追诉系统 · 全链条刑事追诉研究平台    ║
╚══════════════════════════════════════╝

  1. 列出所有案件
  2. 搜索案件
  3. 生成报告
  4. 案件跟踪管理
  5. 启动Web界面
  0. 退出
""")
    choice = input("请选择操作: ").strip()
    if choice == "1":
        cmd_list()
    elif choice == "2":
        q = input("输入搜索关键词: ").strip()
        if q:
            cmd_search(q)
    elif choice == "3":
        cases = loader.list_cases()
        if cases:
            print("可用案件:")
            for c in cases:
                print(f"  {c['case_id']}: {c['case_name']}")
        case_id = input("输入案件ID: ").strip()
        if case_id:
            cmd_report(case_id, "tex")
    elif choice == "4":
        print("跟踪管理：请使用 --tracker 参数")
    elif choice == "5":
        cmd_serve()


# ---- 主入口 ----

def main():
    parser = argparse.ArgumentParser(description="追诉系统 · 多案扩展架构",
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(dest="command")

    # serve
    subparsers.add_parser("serve", help="启动Web服务")

    # list
    subparsers.add_parser("list", help="列出所有案件")

    # search
    sp = subparsers.add_parser("search", help="搜索案件")
    sp.add_argument("query", help="搜索关键词")

    # report
    sp = subparsers.add_parser("report", help="生成报告")
    sp.add_argument("case_id", help="案件ID")
    sp.add_argument("--format", "-f", default="tex", choices=["tex", "pdf"], help="输出格式")

    # tracker
    tp = subparsers.add_parser("track", help="案件跟踪")
    tp.add_argument("tracker_action", nargs='?', choices=["add", "list", "update", "log", "remove"],
                    help="操作 (add/list/update/log/remove)")
    tp.add_argument("--case-id", dest="case_id", help="案件ID")
    tp.add_argument("--case-num", dest="case_num", help="案号")
    tp.add_argument("--court", help="审理法院")
    tp.add_argument("--status", default="investigating", help="案件状态")
    tp.add_argument("--new-status", dest="new_status", help="新状态")
    tp.add_argument("--event", help="事件描述")
    tp.add_argument("--source", help="事件来源")

    args = parser.parse_args()

    if args.command == "serve":
        cmd_serve()
    elif args.command == "list":
        cmd_list()
    elif args.command == "search":
        cmd_search(args.query)
    elif args.command == "report":
        cmd_report(args.case_id, args.format)
    elif args.command == "track":
        cmd_tracker(args)
    elif args.command is None:
        cmd_interactive()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
