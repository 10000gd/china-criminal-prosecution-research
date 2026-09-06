# -*- coding: utf-8 -*-
"""API文档生成器"""
from flask import Blueprint, jsonify, render_template

def create_api_docs_blueprint(app):
    bp = Blueprint("api_docs", __name__, url_prefix="/api/docs")
    
    API_SPEC = {
        "openapi": "3.0.0",
        "info": {
            "title": "刑事追诉智能辅助系统 API",
            "version": "2.0.0",
            "description": "面向检察官、刑辩律师、法学研究者的法律辅助工具"
        },
        "servers": [{"url": "/", "description": "本地服务器"}],
        "paths": {
            # ── 入罪门槛 ──────────────────────────────────────────
            "/api/threshold": {
                "get": {
                    "tags": ["入罪门槛"],
                    "summary": "查询入罪数额标准",
                    "parameters": [
                        {"name": "crime", "in": "query", "required": True, "schema": {"type": "string", "example": "盗窃罪"}},
                        {"name": "amount", "in": "query", "schema": {"type": "number", "example": 5000}},
                        {"name": "province", "in": "query", "schema": {"type": "string", "example": "广东"}},
                    ],
                    "responses": {"200": {"description": "返回入罪门槛结果（含是否达到数额较大/巨大/特别巨大）"}}
                }
            },
            # ── 案件管理 ──────────────────────────────────────────
            "/api/cases": {
                "get": {
                    "tags": ["案件管理"],
                    "summary": "列出所有案件",
                    "parameters": [
                        {"name": "province", "in": "query", "schema": {"type": "string"}},
                        {"name": "crime", "in": "query", "schema": {"type": "string"}},
                    ],
                    "responses": {"200": {"description": "案件列表"}}
                }
            },
            "/api/case/{case_id}": {
                "get": {
                    "tags": ["案件管理"],
                    "summary": "获取案件详情",
                    "parameters": [{"name": "case_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "案件数据"}, "404": {"description": "案件不存在"}}
                }
            },
            "/api/case/{case_id}/charges": {
                "get": {
                    "tags": ["案件管理"],
                    "summary": "获取案件罪名信息",
                    "parameters": [{"name": "case_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "罪名数据"}}
                }
            },
            # ── 真实性核查 ─────────────────────────────────────────
            "/api/fact-check/{case_id}": {
                "get": {
                    "tags": ["真实性核查"],
                    "summary": "核查案件数据来源真实性",
                    "description": "对案件各字段核查来源等级：GRADE_A=官方一手，GRADE_B=可推断，GRADE_C=推测，GRADE_D=未知，GRADE_E=错误。幻觉率=(C+D+E)/总字段数",
                    "parameters": [{"name": "case_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {
                        "200": {"description": "核查结果（summary/fields/issues三级结构）"},
                        "404": {"description": "案件不存在"}
                    }
                }
            },
            # ── 案件对比 ──────────────────────────────────────────
            "/api/compare": {
                "post": {
                    "tags": ["案件对比"],
                    "summary": "对比多个案件",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["case_ids"],
                                    "properties": {
                                        "case_ids": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 5, "example": ["CASE-0001", "CASE-0003"]}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "对比结果（comparison_items/insights/summary）"}, "400": {"description": "参数错误"}}
                }
            },
            # ── 辩护分析 ──────────────────────────────────────────
            "/api/defense/analyze": {
                "post": {
                    "tags": ["辩护分析"],
                    "summary": "分析辩护角度与策略",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "case_id": {"type": "string", "example": "CASE-0001"},
                                        "crime": {"type": "string", "example": "盗窃罪"},
                                        "case_description": {"type": "string"},
                                    }
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "辩护分析结果"}}
                }
            },
            "/api/defense/opinion": {
                "post": {
                    "tags": ["辩护分析"],
                    "summary": "生成辩护意见书",
                    "requestBody": {
                        "content": {"application/json": {"schema": {"type": "object", "properties": {"case_id": {"type": "string"}, "crime": {"type": "string"}}}}}
                    },
                    "responses": {"200": {"description": "辩护意见书文本"}}
                }
            },
            "/api/defense/report": {
                "post": {
                    "tags": ["辩护分析"],
                    "summary": "生成完整辩护报告",
                    "requestBody": {
                        "content": {"application/json": {"schema": {"type": "object", "properties": {"case_id": {"type": "string"}}}}}
                    },
                    "responses": {"200": {"description": "完整辩护报告HTML"}}
                }
            },
            "/api/defense/search": {
                "get": {
                    "tags": ["辩护分析"],
                    "summary": "搜索类似辩护案例",
                    "parameters": [
                        {"name": "q", "in": "query", "schema": {"type": "string", "example": "盗窃罪 自首"}},
                        {"name": "crime", "in": "query", "schema": {"type": "string"}},
                    ],
                    "responses": {"200": {"description": "辩护案例列表"}}
                }
            },
            # ── 量刑分析 ──────────────────────────────────────────
            "/api/sentencing/report": {
                "get": {
                    "tags": ["量刑分析"],
                    "summary": "获取全省量刑偏离度报告",
                    "parameters": [
                        {"name": "crime", "in": "query", "schema": {"type": "string"}},
                        {"name": "province", "in": "query", "schema": {"type": "string"}},
                    ],
                    "responses": {"200": {"description": "量刑报告"}}
                }
            },
            "/api/sentencing/deviation": {
                "post": {
                    "tags": ["量刑分析"],
                    "summary": "分析量刑偏离度",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["crime", "amount"],
                                    "properties": {
                                        "crime": {"type": "string", "example": "盗窃罪"},
                                        "amount": {"type": "number", "example": 50000},
                                        "province": {"type": "string", "example": "广东"},
                                        "is_自首": {"type": "boolean"},
                                        "is_初犯": {"type": "boolean"},
                                        "is_赔偿": {"type": "boolean"},
                                    }
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "偏离度分析结果"}}
                }
            },
            "/api/sentencing/provincial": {
                "get": {
                    "tags": ["量刑分析"],
                    "summary": "省级量刑差异分析",
                    "parameters": [
                        {"name": "crime", "in": "query", "schema": {"type": "string"}},
                    ],
                    "responses": {"200": {"description": "省级差异数据"}}
                }
            },
            # ── 法律搜索 ──────────────────────────────────────────
            "/api/law/search": {
                "get": {
                    "tags": ["法律搜索"],
                    "summary": "全文搜索法律法规",
                    "parameters": [
                        {"name": "q", "in": "query", "required": True, "schema": {"type": "string", "example": "正当防卫"}},
                        {"name": "top_k", "in": "query", "schema": {"type": "integer", "default": 5}},
                        {"name": "category", "in": "query", "schema": {"type": "string", "enum": ["法律", "行政法规", "司法解释", "监察法规"]}},
                    ],
                    "responses": {"200": {"description": "法律条文列表"}}
                }
            },
            # ── 统计分析 ──────────────────────────────────────────
            "/api/stats/overview": {
                "get": {
                    "tags": ["统计分析"],
                    "summary": "全量统计概览",
                    "responses": {"200": {"description": "统计概览（案件数/罪名分布/省份分布/金额统计）"}}
                }
            },
            "/api/stats/hallucination": {
                "get": {
                    "tags": ["统计分析"],
                    "summary": "真实性核查统计",
                    "description": "返回所有案例的来源等级分布。幻觉率=(grade_c+grade_d+grade_e)/总字段，平均置信度加权计算",
                    "responses": {"200": {"description": "逐案例GRADE分布与聚合统计"}}
                }
            },
            "/api/stats/provincial-diffs": {
                "get": {
                    "tags": ["统计分析"],
                    "summary": "省级入罪门槛差异",
                    "description": "返回盗窃罪/诈骗罪/抢夺罪/职务侵占罪在全国各省的入罪数额标准",
                    "responses": {"200": {"description": "省级差异数据（crime_types/provinces/data/max_amount）"}}
                }
            },
            "/api/stats/company-geo": {
                "get": {
                    "tags": ["统计分析"],
                    "summary": "涉案公司地域分布",
                    "responses": {"200": {"description": "公司地域分布统计"}}
                }
            },
            # ── 系统 ──────────────────────────────────────────
            "/health": {
                "get": {
                    "tags": ["系统"],
                    "summary": "健康检查",
                    "responses": {"200": {"description": "系统健康状态"}}
                }
            },
            "/metrics": {
                "get": {
                    "tags": ["系统"],
                    "summary": "Prometheus监控指标",
                    "responses": {"200": {"description": "指标数据"}}
                }
            }
        },
        "components": {
            "schemas": {
                "Error": {
                    "type": "object",
                    "properties": {
                        "error": {"type": "string"},
                        "code": {"type": "integer"}
                    }
                }
            }
        }
    }
    
    @bp.route("/")
    def index():
        return render_template("api_docs.html", spec=API_SPEC)
    
    @bp.route("/spec.json")
    def spec_json():
        return jsonify(API_SPEC)
    
    @bp.route("/swagger-ui")
    def swagger_ui():
        return render_template("swagger_ui.html")
    
    return bp
