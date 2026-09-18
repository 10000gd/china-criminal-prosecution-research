# -*- coding: utf-8 -*-
"""辩护路由"""
from flask import Blueprint, request, jsonify, render_template
from shared.singletons import loader
from shared.constants import OUTPUT_DIR
from auth import login_required
from defense_enhancer import DefenseEnhancer
from defense_case_db import DefenseCaseDatabase
from defense_opinion_generator import DefenseOpinionGenerator
from defense_report_builder import DefenseReportBuilder, DefenseReportBuilderPDF, DefenseReport
from defense_report_builder import _save_pdf_report as save_defense_report_pdf
from pathlib import Path
from datetime import datetime
import ast

defense_bp = Blueprint('defense', __name__, url_prefix='')


def _load_case_full(case_id: str):
    """从案件库加载完整案件数据"""
    try:
        full_case = loader.load(case_id)
        if not full_case:
            return None
        case_info_raw = full_case.get("case_info", {})
        if not isinstance(case_info_raw, dict):
            case_info_raw = {}
        meta_raw = full_case.get("meta", {})
        if not isinstance(meta_raw, dict):
            meta_raw = {}
        charges_raw = full_case.get("charges", {})
        if not isinstance(charges_raw, dict):
            charges_raw = {}
        defendants_raw = full_case.get("defendants_person", [])
        if not isinstance(defendants_raw, list):
            defendants_raw = []
        mitigating_raw = full_case.get("mitigating_factors", [])
        if not isinstance(mitigating_raw, list):
            mitigating_raw = []
        legal_args_raw = full_case.get("legal_arguments", [])
        if not isinstance(legal_args_raw, list):
            legal_args_raw = []

        return {
            "case_id": case_id,
            "case_name": meta_raw.get("case_name", case_id),
            "case_summary": case_info_raw.get("description", ""),
            "facts": {
                "description": case_info_raw.get("description", ""),
                "detail": " ".join(str(f) for f in mitigating_raw + legal_args_raw if f),
            },
            "charges": charges_raw,
            "defendants": [{"name": n} for n in defendants_raw] if defendants_raw else [],
            "mitigating_factors": mitigating_raw,
            "legal_arguments": legal_args_raw,
            "_full": full_case,
        }
    except Exception:
        return None


@defense_bp.route("/defense/<case_id>")
def defense_page(case_id):
    """辩护分析页面"""
    case_data = None
    try:
        case_data = loader.load(case_id)
    except FileNotFoundError:
        pass

    if case_data:
        has_file_case = True
    elif case_id.startswith("DEF-"):
        from defense_case_db import DefenseCaseDatabase
        db = DefenseCaseDatabase()
        bd = db.get_by_id(case_id)
        if bd:
            case_data = {
                "case_id": bd.case_id,
                "case_name": bd.case_name,
                "crime": bd.crime,
                "charges": {"charge1": {"name": bd.crime, "detail": bd.key_facts}},
                "key_facts": bd.key_facts,
                "summary": f"【{bd.outcome}】{bd.reasoning}",
                "is_builtin_defense": True,
            }
            has_file_case = False
        else:
            return render_template("defense.html", error=f"案件不存在: {case_id}", case_id=case_id)
    else:
        return render_template("defense.html", error=f"案件不存在: {case_id}", case_id=case_id)

    enhancer = DefenseEnhancer()
    analysis = enhancer.analyze_case(case_data)

    from defense_case_db import DefenseCaseDatabase
    db = DefenseCaseDatabase()
    primary_defense = analysis.primary_defense.type.value if analysis.primary_defense else None
    charges = loader.get_charges(case_id) if has_file_case else {}
    crime = (list(charges.values())[0].get("name", "") if charges else case_data.get("crime", ""))

    if primary_defense:
        similar = db.search_by_defense(primary_defense, crime, limit=5)
    else:
        similar = db.search_by_crime(crime, "innocent", limit=5)

    return render_template(
        "defense.html",
        case_id=case_id,
        case_data=case_data,
        analysis=analysis.to_dict(),
        similar_cases=[c.to_dict() for c in similar.cases],
        similar_summary=similar.summary,
    )


@defense_bp.route("/api/defense/analyze", methods=["POST"])
def api_defense_analyze():
    """辩护分析 API"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "请提供案件数据"}), 400

    case_id = data.get("case_id", f"CASE-{datetime.now().strftime('%Y%m%d%H%M')}")
    case_data = None

    if case_id:
        try:
            from case_loader import CaseLoader
            cl = CaseLoader()
            full_case = cl.load(case_id)
            if full_case:
                case_info_raw = full_case.get("case_info", "{}")
                if isinstance(case_info_raw, str):
                    case_info_raw = ast.literal_eval(case_info_raw) if case_info_raw else {}
                elif not isinstance(case_info_raw, dict):
                    case_info_raw = {}
                charges_raw = full_case.get("charges", "{}")
                if isinstance(charges_raw, str):
                    charges_raw = ast.literal_eval(charges_raw) if charges_raw else {}
                elif not isinstance(charges_raw, dict):
                    charges_raw = {}
                defendants_raw = full_case.get("defendants_person", "[]")
                if isinstance(defendants_raw, str):
                    defendants_raw = ast.literal_eval(defendants_raw) if defendants_raw else []
                elif not isinstance(defendants_raw, list):
                    defendants_raw = []
                mitigating_raw = full_case.get("mitigating_factors", "[]")
                if isinstance(mitigating_raw, str):
                    mitigating_raw = ast.literal_eval(mitigating_raw) if mitigating_raw else []
                elif not isinstance(mitigating_raw, list):
                    mitigating_raw = []
                legal_args_raw = full_case.get("legal_arguments", "[]")
                if isinstance(legal_args_raw, str):
                    legal_args_raw = ast.literal_eval(legal_args_raw) if legal_args_raw else []
                elif not isinstance(legal_args_raw, list):
                    legal_args_raw = []

                meta_raw = full_case.get("meta", {}) or {}
                if not isinstance(meta_raw, dict):
                    meta_raw = {}
                case_data = {
                    "case_id": case_id,
                    "case_name": meta_raw.get("case_name", case_id),
                    "case_summary": case_info_raw.get("description", ""),
                    "facts": {
                        "description": case_info_raw.get("description", ""),
                        "detail": " ".join(str(f) for f in mitigating_raw + legal_args_raw if f),
                    },
                    "defendants": [{"name": name} for name in defendants_raw] if defendants_raw else [{"name": data.get("defendant_name", "被告")}],
                    "charges": charges_raw if isinstance(charges_raw, dict) else {},
                    "mitigating_factors": mitigating_raw,
                    "legal_arguments": legal_args_raw,
                }
        except Exception as e:
            print(f"[辩护分析] 案件加载失败: {e}")

    charges_val = data.get("charges")
    if isinstance(charges_val, str):
        charges_val = {"primary": {"name": charges_val}}
    elif not isinstance(charges_val, dict):
        charges_val = {"primary": {"name": data.get("crime", "未知罪名")}}

    if not case_data or not case_data.get("case_summary"):
        case_data = {
            "case_id": case_id,
            "case_summary": data.get("case_summary") or data.get("facts", ""),
            "defendants": [{"name": data.get("defendant_name", "被告")}],
            "charges": charges_val,
        }

    enhancer = DefenseEnhancer()
    analysis = enhancer.analyze_case(case_data)

    from defense_case_db import DefenseCaseDatabase
    db = DefenseCaseDatabase()
    charges_dict = case_data.get("charges", {})
    crime = (charges_dict.get("primary", {}).get("name") or data.get("crime", ""))
    similar = db.search_by_defense(
        analysis.primary_defense.type.value if analysis.primary_defense else "",
        crime, limit=5
    )

    primary = analysis.primary_defense
    secondary = analysis.secondary_defenses
    defense_angles = ([primary] + secondary) if primary else secondary

    return jsonify({
        "analysis": analysis.to_dict(),
        "defense_angles": [a.to_dict() for a in defense_angles],
        "similar_cases": [c.to_dict() for c in similar.cases],
    })


@defense_bp.route("/api/defense/opinion", methods=["POST"])
def api_defense_opinion():
    """辩护意见生成 API"""
    data = request.get_json() or {}
    case_id = data.get("case_id", "")

    case_data = _load_case_full(case_id) if case_id else None

    if not case_data or not case_data.get("case_summary"):
        case_data = {
            "case_id": case_id or "unknown",
            "case_name": data.get("case_name", "未知案件"),
            "case_summary": data.get("facts", ""),
            "defendants": [{"name": data.get("defendant_name", "被告")}],
            "charges": {"primary": {"name": data.get("crime", "未知罪名")}},
        }

    enhancer = DefenseEnhancer()
    analysis = enhancer.analyze_case(case_data)

    from defense_case_db import DefenseCaseDatabase
    db = DefenseCaseDatabase()
    crime = (case_data.get("charges", {}).get("primary", {}).get("name") or data.get("crime", ""))
    similar = db.search_by_defense(
        analysis.primary_defense.type.value if analysis.primary_defense else "",
        crime, limit=5
    )

    generator = DefenseOpinionGenerator(analysis.to_dict(), [c.to_dict() for c in similar.cases])
    opinion = generator.generate_full_opinion(case_data)

    return jsonify({
        "opinion": opinion.to_dict(),
        "markdown": opinion.to_markdown(),
        "analysis": analysis.to_dict(),
        "similar_cases": [c.to_dict() for c in similar.cases],
    })


@defense_bp.route("/api/defense/report", methods=["POST"])
def api_defense_report():
    """辩护报告生成 API"""
    data = request.get_json() or {}
    case_id = data.get("case_id", "")

    case_data = data.get("case_data")
    defense_analysis = data.get("analysis", {})
    similar_cases = data.get("similar_cases", [])
    opinion_text = data.get("opinion", "")

    if not case_data and case_id:
        loaded = _load_case_full(case_id)
        if loaded:
            case_data = loaded

        if case_data and not defense_analysis:
            from defense_enhancer import DefenseEnhancer
            enhancer = DefenseEnhancer()
            defense_analysis = enhancer.analyze_case(case_data).to_dict()

        if case_data and not similar_cases:
            from defense_case_db import DefenseCaseDatabase
            db = DefenseCaseDatabase()
            crime = (case_data.get("charges", {}).get("primary", {}).get("name") or "")
            primary_def = defense_analysis.get("primary_defense", {})
            similar = db.search_by_defense(primary_def.get("type", "") if primary_def else "", crime, limit=5)
            similar_cases = [c.to_dict() for c in similar.cases]

        if case_data and not opinion_text:
            from defense_opinion_generator import DefenseOpinionGenerator
            gen = DefenseOpinionGenerator(defense_analysis, similar_cases)
            opinion_text = gen.generate_full_opinion(case_data).to_markdown()

    if not case_data:
        return jsonify({"error": "缺少案件数据"}), 400

    builder = DefenseReportBuilder()
    report = builder.build(
        case_data=case_data,
        defense_analysis=defense_analysis,
        similar_cases=similar_cases,
        opinion=opinion_text,
    )

    format_type = data.get("format", "html")
    if format_type == "html":
        filepath = builder.save_html(report)
    elif format_type == "json":
        filepath = builder.save_json(report)
    elif format_type == "pdf":
        filepath = save_defense_report_pdf(report)
    else:
        filepath = builder.save_markdown(report)

    return jsonify({
        "success": True,
        "report_path": str(filepath),
        "download_url": f"/download/{Path(filepath).name}",
        "content": report.get("content", "") if isinstance(report, dict) else str(report)[:2000],
    })


@defense_bp.route("/api/defense/search", methods=["GET"])
def api_defense_search():
    """辩护案例检索 API"""
    q = request.args.get("q", "").strip()
    crime = request.args.get("crime", q).strip()
    defense_type = request.args.get("defense_type", "")
    limit = int(request.args.get("limit", 10))

    from defense_case_db import DefenseCaseDatabase
    db = DefenseCaseDatabase()

    if defense_type:
        result = db.search_by_defense(defense_type, crime, limit)
    elif crime:
        result = db.search_by_crime(crime, "innocent", limit)
    else:
        return jsonify({"error": "请提供罪名或辩护类型"}), 400

    return jsonify({
        "cases": [c.to_dict() for c in result.cases],
        "total": result.total,
        "summary": result.summary,
    })
