#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""API客户端示例"""
import requests
import json

BASE_URL = "http://localhost:5000"

def login(username: str, password: str) -> str:
    """登录获取session"""
    resp = requests.post(f"{BASE_URL}/auth/login", data={
        "username": username,
        "password": password
    }, allow_redirects=False)
    return resp.cookies.get("session")

def analyze_sentencing(case_data: dict, cookie: str = None):
    """量刑分析"""
    resp = requests.post(
        f"{BASE_URL}/api/sentencing/analyze",
        json=case_data,
        cookies={"session": cookie} if cookie else None
    )
    return resp.json()

def search_cases(query: str, cookie: str = None):
    """搜索案例"""
    resp = requests.get(
        f"{BASE_URL}/api/search",
        params={"q": query},
        cookies={"session": cookie} if cookie else None
    )
    return resp.json()

def get_health():
    """健康检查"""
    resp = requests.get(f"{BASE_URL}/health")
    return resp.json()

if __name__ == "__main__":
    # 示例: 健康检查
    print("健康检查:", get_health()["status"])
    
    # 示例: 量刑分析
    result = analyze_sentencing({
        "crime": "盗窃罪",
        "amount": 50000,
        "province": "北京",
        "is_初犯": True
    })
    print("\n量刑分析结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
