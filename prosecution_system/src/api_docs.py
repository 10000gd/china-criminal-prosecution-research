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
            "/api/sentencing/analyze": {
                "post": {
                    "tags": ["量刑分析"],
                    "summary": "分析量刑偏离度",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["crime", "amount"],
                                    "properties": {
                                        "crime": {"type": "string", "example": "盗窃罪"},
                                        "amount": {"type": "number", "example": 50000},
                                        "province": {"type": "string", "example": "北京"},
                                        "is_自首": {"type": "boolean"},
                                        "is_初犯": {"type": "boolean"},
                                        "is_赔偿": {"type": "boolean"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "成功"}}
                }
            },
            "/api/sentencing/report": {
                "get": {
                    "tags": ["量刑分析"],
                    "summary": "获取全省量刑报告",
                    "parameters": [
                        {"name": "crime", "in": "query", "schema": {"type": "string"}},
                        {"name": "province", "in": "query", "schema": {"type": "string"}}
                    ],
                    "responses": {"200": {"description": "成功"}}
                }
            },
            "/api/compare": {
                "post": {
                    "tags": ["案件对比"],
                    "summary": "对比多个案件",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "case_ids": {"type": "array", "items": {"type": "string"}}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "成功"}}
                }
            },
            "/api/defense/analyze": {
                "post": {
                    "tags": ["辩护分析"],
                    "summary": "分析辩护角度",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "crime": {"type": "string"},
                                        "case_description": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "成功"}}
                }
            },
            "/api/search": {
                "get": {
                    "tags": ["搜索"],
                    "summary": "搜索案例",
                    "parameters": [
                        {"name": "q", "in": "query", "schema": {"type": "string"}},
                        {"name": "page", "in": "query", "schema": {"type": "integer"}}
                    ],
                    "responses": {"200": {"description": "成功"}}
                }
            },
            "/health": {
                "get": {
                    "tags": ["系统"],
                    "summary": "健康检查",
                    "responses": {"200": {"description": "成功"}}
                }
            },
            "/metrics": {
                "get": {
                    "tags": ["系统"],
                    "summary": "Prometheus指标",
                    "responses": {"200": {"description": "成功"}}
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
