#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""种子数据生成器"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from database import db
from sentencing_cases import get_sentencing_cases
import random

def create_seed_users():
    """创建种子用户"""
    users = [
        {"username": "admin", "email": "admin@example.com", "password": "admin123", "role": "admin"},
        {"username": "prosecutor1", "email": "prosecutor@example.com", "password": "prosec123", "role": "user"},
        {"username": "lawyer1", "email": "lawyer@example.com", "password": "lawyer123", "role": "user"},
        {"username": "researcher1", "email": "researcher@example.com", "password": "research123", "role": "user"},
    ]
    
    for u in users:
        try:
            db.create_user(u["username"], u["email"], u["password"], u["role"])
            print(f"✅ 创建用户: {u['username']}")
        except Exception as e:
            print(f"⚠️ 用户已存在: {u['username']}")

def create_seed_history():
    """创建搜索历史"""
    searches = ["盗窃罪", "诈骗罪", "故意伤害", "交通肇事", "危险驾驶", "职务侵占"]
    cases = get_sentencing_cases()[:10]
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users LIMIT 5")
        users = [row["user_id"] for row in cursor.fetchall()]
        
        for user_id in users:
            for _ in range(random.randint(5, 15)):
                search = random.choice(searches)
                case_id = random.choice(cases)["case_id"] if cases else None
                db.add_search_history(user_id, search)
    
    print(f"✅ 创建搜索历史完成")

def create_seed_favorites():
    """创建收藏"""
    cases = get_sentencing_cases()[:20]
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users LIMIT 5")
        users = [row["user_id"] for row in cursor.fetchall()]
        
        for user_id in users:
            for case in random.sample(cases, min(3, len(cases))):
                try:
                    db.add_favorite(user_id, case["case_id"])
                except:
                    pass
    
    print(f"✅ 创建收藏完成")

def create_seed_logs():
    """创建操作日志"""
    actions = ["login", "search", "view_case", "compare", "export"]
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users LIMIT 5")
        users = [row["user_id"] for row in cursor.fetchall()]
        
        for user_id in users:
            for i in range(random.randint(10, 30)):
                action = random.choice(actions)
                details = f"操作{i+1}"
                db.log_operation(user_id, action, details)
    
    print(f"✅ 创建操作日志完成")

def main():
    print("🌱 开始生成种子数据...\n")
    
    print("📝 创建用户...")
    create_seed_users()
    
    print("\n📝 创建搜索历史...")
    create_seed_history()
    
    print("\n📝 创建收藏...")
    create_seed_favorites()
    
    print("\n📝 创建操作日志...")
    create_seed_logs()
    
    print("\n✨ 种子数据生成完成!")
    
    stats = db.get_stats()
    print(f"\n📊 当前统计:")
    print(f"  用户数: {stats.get('total_users', 0)}")
    print(f"  收藏数: {stats.get('total_favorites', 0)}")
    print(f"  搜索数: {stats.get('total_searches', 0)}")

if __name__ == "__main__":
    main()
