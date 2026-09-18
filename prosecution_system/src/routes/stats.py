# -*- coding: utf-8 -*-
"""统计路由"""
from flask import Blueprint, request, jsonify, render_template, session
from shared.singletons import loader
from shared.constants import OUTPUT_DIR
from stats_aggregator import StatsAggregator
from pathlib import Path
import re
from datetime import datetime

stats_bp = Blueprint('stats', __name__, url_prefix='/api')


def _confidence_label(score: float) -> str:
    if score >= 80: return "高置信度"
    elif score >= 60: return "中等置信度"
    elif score >= 40: return "低置信度"
    else: return "不可靠"


def _hall_label(rate: float) -> str:
    if rate < 0.1: return "优秀"
    elif rate < 0.25: return "良好"
    elif rate < 0.5: return "需关注"
    else: return "严重"


@stats_bp.route("/stats/overview")
def api_stats_overview():
    """案件统计概览"""
    cases = loader.list_cases()
    provinces = {}
    crime_types = {}
    total_amount = 0
    amount_count = 0

    for c in cases:
        cid = c.get("case_id", c) if isinstance(c, dict) else c
        info = loader.get_case_info(cid)
        charges = loader.get_charges(cid)
        if info:
            prov = info.get("province", "未知")
            provinces[prov] = provinces.get(prov, 0) + 1
            crime = info.get("crime_type") or (charges.get("primary", {}).get("name") if charges else None) or "未知"
            crime_types[crime] = crime_types.get(crime, 0) + 1
            amt = info.get("amount", 0) or 0
            if amt > 0:
                total_amount += amt
                amount_count += 1
        elif charges:
            crime = charges.get("primary", {}).get("name", "未知")
            crime_types[crime] = crime_types.get(crime, 0) + 1

    avg_amount = total_amount / amount_count if amount_count else 0

    return jsonify({
        "total_cases": len(cases),
        "total_crimes": len(crime_types),
        "provinces": dict(sorted(provinces.items(), key=lambda x: -x[1])),
        "crime_types": dict(sorted(crime_types.items(), key=lambda x: -x[1])),
        "avg_amount_wan": round(avg_amount / 10000, 2),
        "total_amount_wan": round(total_amount / 10000, 2),
    })


@stats_bp.route("/stats/hallucination")
def api_hallucination():
    """幻觉率统计"""
    agg = StatsAggregator()
    stats = agg.get_hallucination_stats()
    n = len(stats)
    return jsonify({
        "cases": [agg._stat_to_dict(s) for s in stats],
        "average_hallucination_rate": sum(s.hallucination_rate for s in stats) / n if n else 0,
        "average_confidence": sum(s.average_confidence for s in stats) / n if n else 0,
    })


@stats_bp.route("/fact-check/<case_id>")
def api_fact_check(case_id):
    """真实性核查 API"""
    from fact_checker import FactChecker
    try:
        fc = FactChecker(case_id)
        result = fc.check()
        total = result["total_fields"]
        c_count = result["grade_c"]
        d_count = result["grade_d"]
        e_count = result["grade_e"]
        hall_rate = round((c_count + d_count + e_count) / total, 4) if total else 0
        avg_conf = round((result["grade_a"] * 1.0 + result["grade_b"] * 0.7 + result["grade_c"] * 0.4 + result["grade_d"] * 0.1) / total, 2) if total else 0
        return jsonify({
            "case_id": case_id,
            "check_date": result["check_date"],
            "summary": {
                "total_fields": total,
                "grade_a": result["grade_a"],
                "grade_b": result["grade_b"],
                "grade_c": result["grade_c"],
                "grade_d": result["grade_d"],
                "grade_e": result["grade_e"],
                "hallucination_rate": hall_rate,
                "hallucination_pct": round(hall_rate * 100, 1),
                "average_confidence": avg_conf,
            },
            "fields": result["fields"],
            "issues": result["issues"],
            "average_confidence": avg_conf,
            "grade_labels": {
                "GRADE_A": "✅ 官方一手来源(可引用)",
                "GRADE_B": "🔶 可推断来源(建议注明推断依据)",
                "GRADE_C": "⚠️ 推测来源(需在报告中标注)",
                "GRADE_D": "❓ 完全未知(建议删除或标注存疑)",
                "GRADE_E": "❌ 已验证错误(必须修正)",
            },
        })
    except FileNotFoundError:
        return jsonify({"error": f"案件不存在: {case_id}"}), 404
    except Exception as e:
        return jsonify({"error": f"核查失败: {e}"}), 500


@stats_bp.route("/stats/provincial-diffs")
def api_provincial_diffs():
    """省级差异数据"""
    return jsonify(StatsAggregator().get_provincial_diffs())


@stats_bp.route("/stats/company-geo")
def api_company_geo():
    """涉案公司地域分布"""
    return jsonify(StatsAggregator().get_company_geo_stats())


# ---- 页面路由 ----

stats_page_bp = Blueprint('stats_page', __name__, url_prefix='')


@stats_page_bp.route("/stats")
def stats_page():
    """统计总览页"""
    agg = StatsAggregator()
    stats = agg.get_all_stats()
    for c in stats.get("cases", []):
        c["hallucination_pct"] = round(c["hallucination_rate"] * 100, 1)
        c["confidence_label"] = _confidence_label(c["average_confidence"])
    overall_hall = stats.get("average_hallucination_rate", 0)
    overall_conf = stats.get("average_confidence", 0)
    return render_template(
        "stats.html",
        stats=stats,
        overall_hall=round(overall_hall * 100, 1),
        overall_conf=round(overall_conf, 1),
        confidence_label=_confidence_label(overall_conf),
        hall_label=_hall_label(overall_hall),
    )


@stats_page_bp.route("/api/reports")
def api_reports():
    """报告列表 API"""
    reports = []
    reports_dir = Path(OUTPUT_DIR)
    for subdir in (reports_dir / "defense_reports", reports_dir):
        if not subdir.exists():
            continue
        for f in sorted(subdir.iterdir(), key=lambda x: -x.stat().st_mtime):
            if f.suffix not in (".html", ".json"):
                continue
            is_defense = subdir.name == "defense_reports" or "defense" in f.stem.lower()
            case_match = re.search(r"CASE[-\w]+", f.stem)
            if not case_match:
                case_match = re.search(r"[\w]+罪", f.stem)
            label = case_match.group() if case_match else f.stem
            reports.append({
                "type": "辩护报告" if is_defense else "量刑报告",
                "case_id": label,
                "filename": f.name,
                "path": str(f),
                "size_kb": round(f.stat().st_size / 1024, 1),
                "time": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
            })
    return jsonify({"reports": reports, "total": len(reports)})


@stats_page_bp.route("/reports")
def reports_page():
    """已生成报告列表页面"""
    reports = []
    reports_dir = Path(OUTPUT_DIR)

    defense_dir = reports_dir / "defense_reports"
    if defense_dir.exists():
        for f in sorted(defense_dir.iterdir(), key=lambda x: -x.stat().st_mtime):
            if f.suffix in (".html", ".json"):
                case_match = re.search(r"CASE[-\w]+", f.stem)
                case_id = case_match.group() if case_match else f.stem
                reports.append({
                    "type": "辩护报告",
                    "case_id": case_id,
                    "filename": f.name,
                    "path": str(f),
                    "size_kb": round(f.stat().st_size / 1024, 1),
                    "time": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                })

    if reports_dir.exists():
        for f in sorted(reports_dir.iterdir(), key=lambda x: -x.stat().st_mtime):
            if f.suffix in (".html", ".json") and "sentencing" in f.stem.lower():
                case_match = re.search(r"[\w]+罪", f.stem) or re.search(r"\w+-\d+", f.stem)
                label = case_match.group() if case_match else f.stem
                reports.append({
                    "type": "量刑报告",
                    "case_id": label,
                    "filename": f.name,
                    "path": str(f),
                    "size_kb": round(f.stat().st_size / 1024, 1),
                    "time": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
                })

    return render_template(
        "reports.html",
        reports=reports,
        username=session.get("username"),
    )
