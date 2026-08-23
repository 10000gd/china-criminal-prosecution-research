#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
官方全量法律文本加载器
数据来源：全国人大官网 / 华律网66law
用途：提供完整官方原始法条文本（无中间处理）
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

# 路径配置
LEGALDB_DIR = Path(__file__).parent.parent / "cases" / "legaldb"


def cn2num(cn: str) -> int:
    """中文数字转阿拉伯数字"""
    if not cn:
        return 0
    if cn.isdigit():
        return int(cn)
    m = {'零': 0, '〇': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
         '六': 6, '七': 7, '八': 8, '九': 9, '十': 10, '百': 100, '千': 1000, '万': 10000}
    result, current = 0, 0
    for c in cn:
        val = m.get(c, 0)
        if c == '万':
            result += current * 10000
            current = 0
        elif c == '千':
            result += current * 1000
            current = 0
        elif c == '百':
            result += current * 100
            current = 0
        elif c == '十':
            if current == 0:
                current = 10
            else:
                result += current * 10
                current = 0
        else:
            current += val
    return result + current


class OfficialLawLoader:
    """
    官方全量法律文本加载器
    
    提供完整官方原始法条文本，包括：
    - 刑法全文（第1-452条，2023刑法修正案十二版）
    - 完整章节结构
    - 原始条文标题和正文
    """

    def __init__(self, db_dir: Path = LEGALDB_DIR):
        self.db_dir = db_dir
        self._articles: List[Dict] = []
        self._articles_by_num: Dict[int, Dict] = {}
        self._loaded = False

    def _load(self):
        """加载官方全量文本"""
        if self._loaded:
            return

        json_path = self.db_dir / "中华人民共和国刑法（结构化）.json"
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                self._articles = json.load(f)
            self._articles_by_num = {a['article_num']: a for a in self._articles}
        else:
            # 备选：从txt原始文件解析
            txt_path = self.db_dir / "中华人民共和国刑法（官方原始文本）.txt"
            if txt_path.exists():
                self._parse_txt(txt_path)

        self._loaded = True

    def _parse_txt(self, txt_path: Path):
        """从txt文件解析"""
        import re
        with open(txt_path, 'r', encoding='utf-8') as f:
            text = f.read()

        # 找到正文开始
        start_idx = text.find('第一条　【立法宗旨】')
        if start_idx == -1:
            start_idx = 0
        law_text = text[start_idx:]

        pattern = r'第([一二三四五六七八九十百\d零〇]+)条　【([^】]+)】'
        for m in re.finditer(pattern, law_text):
            num = cn2num(m.group(1))
            self._articles.append({
                "article_no": f"第{m.group(1)}条",
                "article_num": num,
                "title": m.group(2),
                "text": law_text[m.end():].split('第')[0].strip() if m else ""
            })

    @property
    def articles(self) -> List[Dict]:
        """获取所有条文"""
        self._load()
        return self._articles

    def get_article(self, article_num: int) -> Optional[Dict]:
        """获取指定条文号的法律条文"""
        self._load()
        return self._articles_by_num.get(article_num)

    def get_article_text(self, article_num: int) -> Optional[str]:
        """获取指定条文号的原始文本"""
        article = self.get_article(article_num)
        return article['text'] if article else None

    def search_articles(self, keyword: str) -> List[Dict]:
        """搜索包含关键词的条文"""
        self._load()
        results = []
        for a in self._articles:
            if keyword in a['text'] or keyword in a['title']:
                results.append(a)
        return results

    def get_chapter_articles(self, chapter_name: str) -> List[Dict]:
        """获取指定章节的所有条文"""
        self._load()
        results = []
        for a in self._articles:
            if chapter_name in a.get('chapter', ''):
                results.append(a)
        return results

    def get_stats(self) -> Dict[str, Any]:
        """获取统计数据"""
        self._load()
        return {
            "total_articles": len(self._articles),
            "article_range": (
                min(a['article_num'] for a in self._articles) if self._articles else 0,
                max(a['article_num'] for a in self._articles) if self._articles else 0
            ),
            "missing_articles": self._get_missing(),
            "source": "全国人大官网 / 华律网66law",
            "version": "2023刑法修正案十二版"
        }

    def _get_missing(self) -> List[int]:
        """获取缺失的条文号"""
        self._load()
        all_expected = set(range(1, 453))
        found = set(a['article_num'] for a in self._articles)
        return sorted(all_expected - found)

    def verify_article(self, article_num: int) -> Dict[str, Any]:
        """验证条文存在并返回详情"""
        article = self.get_article(article_num)
        if article:
            return {
                "exists": True,
                "article_no": article['article_no'],
                "title": article['title'],
                "text_length": len(article['text']),
                "text_preview": article['text'][:100]
            }
        return {
            "exists": False,
            "article_num": article_num,
            "note": "该条文号在2023刑法修正案十二版中不存在"
        }


# ---- CLI ----

def main():
    import argparse
    parser = argparse.ArgumentParser(description="官方全量法律文本加载器")
    parser.add_argument("--list", action="store_true", help="列出所有条文")
    parser.add_argument("--article", type=int, help="查询指定条文号")
    parser.add_argument("--search", type=str, help="搜索关键词")
    parser.add_argument("--stats", action="store_true", help="显示统计")
    parser.add_argument("--verify", action="store_true", help="验证条文完整性")
    args = parser.parse_args()

    loader = OfficialLawLoader()

    if args.stats:
        stats = loader.get_stats()
        print("=" * 60)
        print("中华人民共和国刑法 - 官方全量原始文本")
        print("=" * 60)
        print(f"  总条文数: {stats['total_articles']} 条")
        print(f"  条文范围: 第{stats['article_range'][0]}条 → 第{stats['article_range'][1]}条")
        print(f"  缺失条文: {stats['missing_articles']}")
        print(f"  数据来源: {stats['source']}")
        print(f"  版本: {stats['version']}")
        print("=" * 60)

    elif args.article:
        article = loader.get_article(args.article)
        if article:
            print(f"第{article['article_num']}条【{article['title']}】")
            print(f"{'='*60}")
            print(article['text'])
        else:
            print(f"第{args.article}条不存在")

    elif args.search:
        results = loader.search_articles(args.search)
        print(f"找到 {len(results)} 条相关条文:")
        for a in results[:10]:
            print(f"  第{a['article_no']}【{a['title']}】")
            print(f"    {a['text'][:80]}...")

    elif args.list:
        for a in loader.articles[:20]:
            print(f"第{a['article_no']}【{a['title']}】")
        print(f"... (共 {len(loader.articles)} 条)")

    elif args.verify:
        key_nums = [1, 13, 17, 37, 48, 63, 67, 78, 87, 101,
                    102, 192, 225, 264, 382, 385, 397, 452]
        print("关键条文验证:")
        for num in key_nums:
            v = loader.verify_article(num)
            status = "✅" if v['exists'] else "❌"
            if v['exists']:
                print(f"  {status} 第{num}条【{v['title']}】: {v['text_length']}字符")
            else:
                print(f"  {status} 第{num}条: 不存在")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
