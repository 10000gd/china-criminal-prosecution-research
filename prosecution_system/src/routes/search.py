# -*- coding: utf-8 -*-
"""搜索路由"""
from flask import Blueprint, request, jsonify, render_template, session
from shared.middleware import rate_limit, get_rag
from shared.singletons import loader
from auth import get_current_user
from database import db as user_db
from datetime import datetime

search_bp = Blueprint('search', __name__, url_prefix='/api')


@search_bp.route("/search")
def api_search():
    """全局搜索 API(案件+法律条文混合)"""
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "缺少查询参数 q"}), 400

    # 搜索案件
    case_results = loader.search_cases(query)
    all_cases = loader.list_cases()
    name_matches = [
        {"case_id": c["case_id"], "case_name": c.get("case_name", ""),
         "case_type": c.get("case_type", ""), "status": c.get("status", ""),
         "judgment_date": c.get("judgment_date", "")}
        for c in all_cases
        if query.lower() in c.get("case_name", "").lower()
        or query.lower() in c.get("case_name_full", "").lower()
    ]

    # 搜索法律条文
    law_results = []
    try:
        rag = get_rag()
        if rag:
            law_results = rag.search(query, top_k=5, hybrid=True)
        law_hits = [{
            "law": h.get("law", ""),
            "article": h.get("article", ""),
            "category": h.get("category", ""),
            "score": round(h.get("score", 0), 1),
            "preview": h.get("preview", "")[:120],
        } for h in law_results]
    except Exception:
        law_hits = []

    return jsonify({
        "query": query,
        "case_results": case_results,
        "name_matches": name_matches,
        "law_results": law_hits,
        "total_cases": len(case_results),
        "total_laws": len(law_hits),
    })


@search_bp.route("/law/search")
def api_law_search():
    """法律检索 API

    GET /api/law/search?q=查询内容&mode=hybrid|bm25&top=10
    """
    import time
    query = request.args.get("q", "").strip()
    mode = request.args.get("mode", "hybrid")
    top_k = min(int(request.args.get("top", 10)), 50)

    if not query:
        return jsonify({"error": "缺少查询参数 q"}), 400

    try:
        rag = get_rag()
        t0 = time.time()
        hits = rag.search(query, top_k=top_k, hybrid=(mode == "hybrid"))
        elapsed_ms = round((time.time() - t0) * 1000)

        results = []
        for h in hits:
            bm25_s = h.get("bm25_score", 0)
            vec_s = h.get("vector_score", 0)
            score = h.get("score", 0) or bm25_s or vec_s
            if mode == "bm25" or (mode == "hybrid" and vec_s == 0 and bm25_s > 0):
                score_type = "bm25"
            elif mode == "hybrid":
                score_type = "hybrid"
            else:
                score_type = "vector"

            results.append({
                "title": h.get("title", ""),
                "law": h.get("law", ""),
                "article": h.get("article", ""),
                "category": h.get("category", ""),
                "score": float(score),
                "score_type": score_type,
                "bm25_score": float(bm25_s) if bm25_s else 0.0,
                "vector_score": float(vec_s) if vec_s else 0.0,
                "preview": h.get("preview", ""),
                "content": h.get("content", ""),
            })

        return jsonify({
            "query": query,
            "mode": mode,
            "time_ms": elapsed_ms,
            "total": len(results),
            "results": results,
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---- 页面路由(无 /api 前缀) ----

search_bp_page = Blueprint('search_page', __name__, url_prefix='')


@search_bp_page.route("/search")
def search():
    """全局搜索页面"""
    query = request.args.get("q", "").strip()
    user = get_current_user()

    if not query:
        return render_template(
            "search.html",
            query="",
            results=[],
            name_matches=[],
            search_history=user.search_history[:10] if user else [],
        )

    if user and query:
        user_db.add_search_history(user.username, query)

    results = loader.search_cases(query)
    all_cases = loader.list_cases()
    name_matches = [c for c in all_cases
                    if query.lower() in c.get("case_name", "").lower()
                    or query.lower() in c.get("case_name_full", "").lower()]

    return render_template(
        "search.html",
        query=query,
        results=results,
        name_matches=name_matches,
        search_history=user.search_history[:10] if user else [],
    )


@search_bp_page.route("/law/search")
def law_search_page():
    """法律语义检索页面"""
    query = request.args.get("q", "").strip()
    mode = request.args.get("mode", "hybrid")
    top_k = request.args.get("top_k", "10")
    return render_template(
        "law_search.html",
        query=query,
        mode=mode,
        top_k=int(top_k),
    )
