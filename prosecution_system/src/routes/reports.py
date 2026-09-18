# -*- coding: utf-8 -*-
"""报告与分析路由"""
from flask import Blueprint, request, jsonify, render_template, send_file
from shared.singletons import loader, get_report_builder, get_pdf_exporter
from shared.middleware import get_rag
from shared.constants import OUTPUT_DIR
from pathlib import Path
from datetime import datetime

reports_bp = Blueprint('reports', __name__, url_prefix='/api')


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


# ── 联合案件分析核心逻辑 ───────────────────────────────────

def _do_case_analyze(data: dict, case_full: dict = None) -> dict:
    crime = data.get("crime_type") or data.get("crime") or data.get("charges")
    if not crime:
        raise ValueError("缺少 crime_type 字段")

    def _v(key, default=None):
        return data.get(key) if data.get(key) is not None else (
            (case_full or {}).get("case_info", {}).get(key, default)
            if case_full else default
        )

    amount = float(_v("amount") or 0)
    province = _v("province", "全国")
    is_company = _v("is_company", False)
    court_level = _v("court_level", "")
    keyword = _v("keyword", "")
    sent_years = float(_v("sentencing_years") or _v("sentence_years") or 0)

    # 1. 入罪门槛
    from threshold_api import CRIME_THRESHOLDS, list_thresholds
    thresh_result = None
    if amount > 0:
        thresh_list = list_thresholds(crime=crime, amount=amount)
        if thresh_list.get("thresholds"):
            matched = [t for t in thresh_list["thresholds"]
                       if t.get("province") == province or t.get("province") == "DEFAULT"]
            thresh_result = matched[0] if matched else thresh_list["thresholds"][0]

    # 2. 量刑预测
    from sentencing_consistency import SentencingConsistencyAnalyzer
    sca = SentencingConsistencyAnalyzer()
    legal_comp = sca.get_legal_comparison(crime)
    legal_range = legal_comp.get("legal_range", {})
    actual_stats = legal_comp.get("actual_stats", {})

    # 3. 量刑偏离分析
    deviation_result = None
    if sent_years > 0 and case_full:
        dev_data = {
            "crime": crime,
            "sentence_years": sent_years,
            "province": province,
            "case_id": data.get("case_id", "unknown"),
            "is_自首": _v("自首", False),
            "is_立功": _v("立功", False),
            "is_坦白": _v("坦白", False),
            "is_赔偿": _v("赔偿", False),
            "is_谅解": _v("谅解", False),
            "is_累犯": _v("累犯", False),
            "is_初犯": _v("初犯", True),
        }
        dev = sca.analyze_deviation(dev_data)
        deviation_result = {
            "deviation_score": dev.deviation_score,
            "deviation_type": dev.deviation_type,
            "expected_sentence": dev.expected_sentence,
            "actual_sentence": dev.actual_sentence,
            "factors": dev.factors,
            "reasons": dev.deviation_reasons,
        }

    # 4. 类案搜索
    from legal_case_db import LegalCaseDB
    lcdb = LegalCaseDB()
    similar_raw = lcdb.search_similar(
        crime_name=crime,
        amount=amount,
        is_company=is_company,
        court_level=court_level,
        keyword=keyword,
        top_k=5,
    )
    similar_cases = []
    for sc in similar_raw:
        case = sc.case
        similar_cases.append({
            "case_id": case.case_id,
            "court": case.court,
            "judgment_date": case.judgment_date,
            "crime_type": case.crime_name,
            "amount": case.amount,
            "sentence": case.sentence,
            "sentence_months": case.sentence_months,
            "similarity_score": round(sc.similarity_score, 2),
            "match_reasons": sc.match_reasons,
            "amount_comparison": sc.amount_comparison,
            "sentence_comparison": sc.sentence_comparison,
            "key_facts": case.key_facts[:100],
        })

    # 5. 辩护分析
    from defense_enhancer import DefenseEnhancer
    de = DefenseEnhancer()
    if case_full:
        da = de.analyze_case(case_full)
        defense_result = {
            "primary_defense": {
                "type": da.primary_defense.type.value,
                "confidence": da.primary_defense.confidence,
                "legal_references": da.primary_defense.legal_references,
                "evidence_points": da.primary_defense.evidence_points,
                "risk_mitigation": da.primary_defense.risk_mitigation,
                "recommendation": da.primary_defense.recommendation,
            },
            "secondary_defenses": [
                {
                    "type": s.type.value,
                    "confidence": s.confidence,
                    "legal_references": s.legal_references,
                    "evidence_points": s.evidence_points,
                    "risk_mitigation": s.risk_mitigation,
                    "recommendation": s.recommendation,
                }
                for s in da.secondary_defenses
            ],
            "overall_strength": da.overall_strength,
            "recommended_strategy": da.recommended_strategy,
            "estimated_outcome": da.estimated_outcome,
        }
    else:
        factors = []
        if _v("自首", False): factors.append("自首")
        if _v("立功", False): factors.append("立功")
        if _v("坦白", False): factors.append("坦白/认罪认罚")
        if _v("赔偿", False) or _v("谅解", False): factors.append("赔偿谅解")
        if _v("初犯", False): factors.append("初犯/偶犯")
        if _v("累犯", False): factors.append("累犯(从重)")
        defense_result = {
            "primary_defense": {"type": "依参数构造", "confidence": "中",
                                "description": f"有利因素: {', '.join(factors) or '无明显有利因素'}"},
            "secondary_defenses": [],
            "overall_strength": 50 + (10 * len(factors)) if factors else 50,
            "recommended_strategy": "建议争取从轻情节,参考类似案件量刑",
            "estimated_outcome": "量刑区间内从轻处理",
        }

    # 6. 法律依据检索
    rag = get_rag()
    law_results = rag.search(crime, top_k=3) if rag else []
    legal_basis = [
        {
            "title": r.get("title", "")[:80],
            "law": r.get("law", ""),
            "article": r.get("article", ""),
            "preview": r.get("preview", "")[:120],
            "bm25_score": r.get("bm25_score", 0),
        }
        for r in law_results
    ]

    return {
        "case_id": data.get("case_id", "new"),
        "crime_type": crime,
        "amount": amount,
        "province": province,
        "is_company": is_company,
        "threshold": thresh_result,
        "sentencing_prediction": {
            "legal_range": legal_range,
            "actual_stats": actual_stats,
            "sample_count": legal_comp.get("sample_count", 0),
            "prediction_note": f"法条量刑区间 {legal_range.get('min',0)}-{legal_range.get('max',0)} "
                               f"{legal_range.get('unit','年')};类案均值 {actual_stats.get('avg','?')}年,"
                               f"中位数 {actual_stats.get('median','?')}年",
        },
        "deviation": deviation_result,
        "similar_cases": similar_cases,
        "defense": defense_result,
        "legal_basis": legal_basis,
    }


# ── 案件分析路由 ───────────────────────────────────────────

@reports_bp.route("/reasoning/charges", methods=["POST"])
def api_reasoning_charges():
    """案由推理引擎 API"""
    from case_reasoning_engine import CaseReasoningEngine
    data = request.get_json() or {}
    description = data.get("description", "").strip()
    top_k = min(int(data.get("top_k", 5)), 10)

    if len(description) < 10:
        return jsonify({"error": "案情描述过短(至少10字)"}), 400

    engine = CaseReasoningEngine()
    result = engine.reason(description, top_k=top_k)
    return jsonify(result)


@reports_bp.route("/reasoning/crimes", methods=["GET"])
def api_reasoning_crimes():
    """获取支持的罪名列表"""
    from case_reasoning_engine import CaseReasoningEngine
    engine = CaseReasoningEngine()
    return jsonify(engine.get_all_crimes())


@reports_bp.route("/case-analyze", methods=["POST"])
def api_case_analyze():
    """联合案件分析 API(POST)"""
    data = request.get_json() or {}
    crime = data.get("crime_type") or data.get("crime") or data.get("charges")
    if not crime:
        return jsonify({"error": "缺少 crime_type 字段"}), 400

    case_full = None
    if data.get("case_id"):
        try:
            case_full = loader.load(data["case_id"])
        except Exception:
            pass

    try:
        return jsonify(_do_case_analyze(data, case_full))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@reports_bp.route("/case-analyze/<case_id>")
def api_case_analyze_get(case_id):
    """联合案件分析 API(GET:从已有案件ID分析)"""
    try:
        case_full = loader.load(case_id)
    except Exception:
        return jsonify({"error": f"案件不存在: {case_id}"}), 404

    ci = (case_full or {}).get("case_info", {}) or {}
    fake_data = {
        "case_id": case_id,
        "crime_type": ci.get("crime_type", ""),
        "amount": ci.get("amount") or ci.get("涉案金额", 0),
        "province": ci.get("province", "全国"),
        "sentencing_years": ci.get("sentence_years") or ci.get("sentencing_years", 0),
        "is_company": ci.get("is_company", False),
        "自首": ci.get("is_自首", False),
        "立功": ci.get("is_立功", False),
        "坦白": ci.get("is_坦白", False),
        "赔偿": ci.get("is_赔偿", False),
        "谅解": ci.get("is_谅解", False),
        "累犯": ci.get("is_累犯", False),
        "初犯": ci.get("is_初犯", True),
    }
    return jsonify(_do_case_analyze(fake_data, case_full))


@reports_bp.route("/case-analyze/<case_id>/pdf")
def api_case_analyze_pdf(case_id):
    """从联合分析结果生成辩护 PDF"""
    try:
        case_full = loader.load(case_id)
    except Exception:
        return jsonify({"error": f"案件不存在: {case_id}"}), 404

    ci = (case_full or {}).get("case_info", {}) or {}
    fake_data = {
        "case_id": case_id,
        "crime_type": ci.get("crime_type", ""),
        "amount": ci.get("amount") or ci.get("涉案金额", 0),
        "province": ci.get("province", "全国"),
        "sentencing_years": ci.get("sentence_years") or ci.get("sentencing_years", 0),
        "is_company": ci.get("is_company", False),
        "自首": ci.get("is_自首", False),
        "立功": ci.get("is_立功", False),
        "坦白": ci.get("is_坦白", False),
        "赔偿": ci.get("is_赔偿", False),
        "谅解": ci.get("is_谅解", False),
        "累犯": ci.get("is_累犯", False),
        "初犯": ci.get("is_初犯", True),
    }
    analysis = _do_case_analyze(fake_data, case_full)

    defense_data = analysis.get("defense", {})
    primary = defense_data.get("primary_defense", {})
    secondary = defense_data.get("secondary_defenses", [])
    defense_angles = [primary] + secondary

    opinion_parts = []
    pd = primary.get("recommendation", "")
    if pd:
        opinion_parts.append(f"主要辩护策略:{pd}")
    sp = analysis.get("sentencing_prediction", {})
    if sp.get("prediction_note"):
        opinion_parts.append(f"量刑预测:{sp['prediction_note']}")
    dev = analysis.get("deviation", {})
    if dev:
        opinion_parts.append(f"量刑偏离分析:{dev.get('deviation_type','?')}(偏离分{dev.get('deviation_score','?')}),"
                             f"合理区间{dev.get('expected_sentence','?')}")
    sc_list = analysis.get("similar_cases", [])
    if sc_list:
        opinion_parts.append(f"参考类案{len(sc_list)}件,最高量刑{sc_list[0].get('sentence','?')},"
                             f"最低量刑{sc_list[-1].get('sentence','?')}。")
    opinion_text = "\n\n".join(opinion_parts)

    from defense_report_builder import DefenseReportBuilderPDF, DefenseReport
    meta = (case_full or {}).get("meta", {}) or {}
    output_dir = OUTPUT_DIR / "defense_reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    report = DefenseReport(
        case_id=case_id,
        case_name=meta.get("case_name", ci.get("case_name", case_id)),
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        analysis_summary=(
            f"罪名:{analysis['crime_type']};涉案金额:{analysis['amount']:.0f}元({analysis['province']});"
            f"入罪判定:{'已达到入罪标准' if analysis.get('threshold',{}).get('reached') else '未达入罪标准'};"
            f"辩护强度:{defense_data.get('overall_strength','?')}/100"
        ),
        defense_angles=defense_angles,
        similar_cases=sc_list,
        opinion_text=opinion_text,
        overall_strength=defense_data.get("overall_strength", 50),
        recommendation=defense_data.get("recommended_strategy", ""),
    )

    pdf_path = DefenseReportBuilderPDF(output_dir=output_dir).save_pdf(report)
    return send_file(pdf_path, as_attachment=True,
                     download_name=f"辩护意见书_{case_id}_{datetime.now().strftime('%Y%m%d')}.pdf")


@reports_bp.route("/case-analyze/new/pdf")
def api_case_analyze_new_pdf():
    """对新建案件直接生成辩护 PDF(GET 参数)"""
    crime_type = request.args.get("crime_type", "")
    amount = float(request.args.get("amount") or 0)
    province = request.args.get("province", "全国")
    court_level = request.args.get("court_level") or None
    keyword = request.args.get("keyword") or None

    case_data = {
        "case_id": "NEW-" + datetime.now().strftime("%Y%m%d%H%M"),
        "crime_type": crime_type,
        "amount": amount,
        "province": province,
        "court_level": court_level,
        "keyword": keyword,
        "is_company": False,
        "自首": False, "立功": False, "坦白": False,
        "赔偿": False, "谅解": False, "累犯": False, "初犯": True,
    }
    for k in ["自首", "立功", "坦白", "赔偿", "谅解", "认罪认罚", "累犯", "初犯", "从犯", "预备"]:
        v = request.args.get(k)
        if v is not None:
            case_data[k] = str(v).lower() in ("1", "true", "yes")

    actual = request.args.get("sentencing_years") or request.args.get("actual_sentencing")
    if actual:
        case_data["sentencing_years"] = float(actual)

    analysis = _do_case_analyze(case_data, None)

    from defense_report_builder import DefenseReportBuilderPDF, DefenseReport
    defense_data = analysis.get("defense", {})
    primary = defense_data.get("primary_defense", {})
    secondary = defense_data.get("secondary_defenses", []) or []
    defense_angles = [primary] + secondary
    sc_list = list(analysis.get("similar_cases", [])[:8])

    opinion_lines = []
    if primary:
        conf = primary.get("confidence", "?")
        opinion_lines.append("主要辩护策略:" + (primary.get("type", "待定")) + "(匹配度 " + str(conf) + "%)")
        if primary.get("recommendation"):
            opinion_lines.append("具体建议:" + primary["recommendation"])
    for d in secondary:
        opinion_lines.append("次要策略:" + (d.get("type", "待定")) + "(匹配度 " + str(d.get("confidence", "?")) + "%)")
    opinion_text = "\n".join(opinion_lines)

    output_dir = OUTPUT_DIR / "defense_reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    reached = analysis.get("threshold", {}).get("reached")
    verdict = "已达到入罪标准" if reached else "未达入罪标准"
    strength = defense_data.get("overall_strength", "?")
    summary = ("罪名:" + crime_type + ";涉案金额:" + str(int(amount)) + "元(" + province + ");"
               + "入罪判定:" + verdict + ";辩护强度:" + str(strength) + "/100")
    report = DefenseReport(
        case_id=case_data["case_id"],
        case_name=province + " " + crime_type + "(新建)",
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        analysis_summary=summary,
        defense_angles=defense_angles,
        similar_cases=sc_list,
        opinion_text=opinion_text,
        overall_strength=strength if isinstance(strength, (int, float)) else 50,
        recommendation=defense_data.get("recommended_strategy", ""),
    )
    pdf_path = DefenseReportBuilderPDF(output_dir=output_dir).save_pdf(report)
    return send_file(pdf_path, as_attachment=True,
                     download_name="辩护意见书_" + crime_type + "_" + datetime.now().strftime("%Y%m%d") + ".pdf")


# ── 量刑分析路由 ───────────────────────────────────────────

@reports_bp.route("/sentencing/report")
def api_sentencing_report():
    """量刑一致性报告 API"""
    crime = request.args.get("crime", None)
    from sentencing_consistency import SentencingConsistencyAnalyzer
    analyzer = SentencingConsistencyAnalyzer()
    report = analyzer.generate_report(crime)
    return jsonify(report)


@reports_bp.route("/sentencing/deviation", methods=["POST"])
def api_sentencing_deviation():
    """个案偏离度分析 API"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "请提供案件数据"}), 400

    from sentencing_consistency import SentencingConsistencyAnalyzer
    analyzer = SentencingConsistencyAnalyzer()
    result = analyzer.analyze_deviation(data)

    return jsonify({
        "case_id": result.case_id,
        "crime": result.crime,
        "deviation_score": result.deviation_score,
        "deviation_type": result.deviation_type,
        "expected_sentence": result.expected_sentence,
        "actual_sentence": result.actual_sentence,
        "factors": result.factors,
        "deviation_reasons": result.deviation_reasons,
        "similar_cases": result.similar_cases,
        "recommendation": result.recommendation,
    })


@reports_bp.route("/sentencing/provincial")
def api_sentencing_provincial():
    """省份量刑对比 API"""
    crime = request.args.get("crime", None)
    from sentencing_consistency import SentencingConsistencyAnalyzer
    analyzer = SentencingConsistencyAnalyzer()
    comparison = analyzer.get_provincial_comparison(crime)
    return jsonify(comparison)


@reports_bp.route("/sentencing/deviation/chart", methods=["POST"])
def api_sentencing_deviation_chart():
    """量刑偏离度可视化 API"""
    data = request.get_json() or {}
    if not data.get("crime"):
        return jsonify({"error": "缺少 crime 字段"}), 400

    from sentencing_consistency import (
        SentencingConsistencyAnalyzer, get_echarts_deviation_chart,
    )
    analyzer = SentencingConsistencyAnalyzer()
    charts = get_echarts_deviation_chart(analyzer, data)
    return jsonify({"charts": charts})


@reports_bp.route("/sentencing/distribution")
def api_sentencing_distribution():
    """罪名量刑分布可视化 API"""
    crime = request.args.get("crime", "盗窃罪")
    province = request.args.get("province", None)
    from sentencing_consistency import SentencingConsistencyAnalyzer, get_echarts_crime_distribution
    analyzer = SentencingConsistencyAnalyzer()
    result = get_echarts_crime_distribution(analyzer, crime, province)
    if "error" in result:
        return jsonify(result), 404
    return jsonify(result)


@reports_bp.route("/sentencing/provincial/chart")
def api_sentencing_provincial_chart():
    """省份量刑对比可视化 API"""
    crime = request.args.get("crime", "盗窃罪")
    top_n = min(int(request.args.get("top_n", 10)), 20)
    from sentencing_consistency import SentencingConsistencyAnalyzer, get_echarts_provincial_comparison
    analyzer = SentencingConsistencyAnalyzer()
    result = get_echarts_provincial_comparison(analyzer, crime, top_n)
    if "error" in result:
        return jsonify(result), 404
    return jsonify(result)


# ── 入罪门槛 ───────────────────────────────────────────────

@reports_bp.route("/threshold")
def api_threshold():
    """入罪门槛 API"""
    crime = request.args.get("crime", "盗窃罪").strip()
    province = request.args.get("province", "北京").strip()
    amount = request.args.get("amount", type=float, default=0)

    from threshold_db import ThresholdDB
    db = ThresholdDB()

    non_amount_crimes = {
        "污染环境罪", "危险驾驶罪", "拒不支付劳动报酬罪",
        "非法侵入住宅罪", "寻衅滋事罪",
    }

    t = db.get_threshold(crime, province)
    if "error" in t:
        return jsonify({
            "error": t["error"],
            "supported": db.get_all_supported_crimes(),
        }), 404

    if amount > 0:
        result = db.check_threshold(province, crime, amount)
        return jsonify({
            "crime": crime,
            "province": province,
            "amount": amount,
            "threshold": t,
            "reached": result.verdict,
            "level": result.level,
            "confidence": result.confidence,
            "legal_basis": result.legal_basis,
        })

    is_non_amount = crime in non_amount_crimes
    threshold_yuan = t.get("amount_standard", 0)

    return jsonify({
        "crime": crime,
        "province": province,
        "is_behavior_based": is_non_amount,
        "threshold_yuan": threshold_yuan,
        "threshold_wan": round(threshold_yuan / 10000, 2) if threshold_yuan else None,
        "standard_note": t.get("standard_note") or t.get("threshold_note", ""),
        "legal_basis": t.get("legal_basis", ""),
        "amount_massive": t.get("amount_massive"),
        "amount_especially_massive": t.get("amount_especially_massive"),
    })


# ── 健康检查与监控 ─────────────────────────────────────────

@reports_bp.route("/monitor/stats")
def api_monitor_stats():
    """性能统计 API"""
    from src.performance_monitor import monitor
    return jsonify(monitor.get_stats())


@reports_bp.route("/monitor/system")
def api_monitor_system():
    """系统资源 API"""
    from src.performance_monitor import monitor
    return jsonify(monitor.get_system_stats())


@reports_bp.route("/monitor/errors")
def api_monitor_errors():
    """最近错误 API"""
    from src.performance_monitor import monitor
    limit = request.args.get('limit', 10, type=int)
    return jsonify({"errors": monitor.get_recent_errors(limit)})


@reports_bp.route("/monitor/slow")
def api_monitor_slow():
    """慢请求 API"""
    from src.performance_monitor import monitor
    limit = request.args.get('limit', 10, type=int)
    return jsonify({"slow_requests": monitor.get_slow_requests(limit)})


# ---- 页面路由 ----

reports_page_bp = Blueprint('reports_page', __name__, url_prefix='')


@reports_page_bp.route("/case-analyze")
def case_analyze_page():
    """联合案件分析前端页面"""
    return render_template("case_analyze.html")


@reports_page_bp.route("/sentencing")
def sentencing_page():
    """量刑一致性分析页面"""
    from sentencing_consistency import SentencingConsistencyAnalyzer
    analyzer = SentencingConsistencyAnalyzer()
    report = analyzer.generate_report()

    crime_stats = []
    for crime, stats in report.get("crime_stats", {}).items():
        if stats.get("avg_sentence"):
            crime_stats.append({
                "crime": crime,
                "avg": stats["avg_sentence"],
                "median": stats.get("median_sentence"),
                "count": stats["sample_count"],
                "probation_rate": stats.get("probation_rate", 0),
                "distribution": stats.get("distribution", {}),
            })

    return render_template(
        "sentencing.html",
        report=report,
        crime_stats=crime_stats,
    )


@reports_page_bp.route("/sentencing/<crime>")
def sentencing_crime_page(crime):
    """特定罪名量刑分析页面"""
    from sentencing_consistency import SentencingConsistencyAnalyzer
    analyzer = SentencingConsistencyAnalyzer()

    stats = analyzer.get_stats_by_crime(crime)
    comparison = analyzer.get_provincial_comparison(crime)
    legal_comp = analyzer.get_legal_comparison(crime)

    sorted_provinces = sorted(
        comparison.items(),
        key=lambda x: x[1]["avg_sentence"]
    ) if comparison else []

    return render_template(
        "sentencing_crime.html",
        crime=crime,
        stats=stats,
        comparison=comparison,
        sorted_provinces=sorted_provinces,
        legal_comp=legal_comp,
    )


@reports_page_bp.route("/health")
def health_check():
    """健康检查"""
    from health import HealthChecker, MetricsCollector
    health = HealthChecker.check()
    metrics = MetricsCollector.get_metrics()
    return jsonify({"health": health, "metrics": metrics})


@reports_page_bp.route("/health/live")
def health_live():
    """存活探针"""
    return jsonify({"status": "alive"})


@reports_page_bp.route("/health/ready")
def health_ready():
    """就绪探针"""
    from health import HealthChecker
    health = HealthChecker.check()
    if health['checks']['database']['status'] == 'ok':
        return jsonify({"status": "ready"})
    return jsonify({"status": "not ready", "reason": "database unavailable"}), 503


@reports_page_bp.route("/metrics")
def metrics():
    """Prometheus格式指标"""
    from health import MetricsCollector
    m = MetricsCollector.get_metrics()
    lines = [
        "# HELP prosecution_requests_total Total requests",
        "# TYPE prosecution_requests_total counter",
        f"prosecution_requests_total {m['total_requests']}",
        "# HELP prosecution_errors_total Total errors",
        "# TYPE prosecution_errors_total counter",
        f"prosecution_errors_total {m['total_errors']}",
        "# HELP prosecution_response_time_seconds Average response time",
        "# TYPE prosecution_response_time_seconds gauge",
        f"prosecution_response_time_seconds {m['avg_response_time']:.3f}",
        "# HELP prosecution_uptime_seconds Uptime in seconds",
        "# TYPE prosecution_uptime_seconds counter",
        f"prosecution_uptime_seconds {m['uptime_seconds']}",
    ]
    return '\n'.join(lines), 200, {"Content-Type": "text/plain"}
