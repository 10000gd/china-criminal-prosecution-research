#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全量中国法律数据库加载器
数据来源：
  - github.com/lawtext/law-flk-vol1 (主数据源，2055部法律法规)
  - github.com/Shiori-pope/c-claim (刑法罪名映射，484个罪名)
  - 华律网66law.cn (刑法全文原始文本)
版本：2023-2025年最新版
"""

import json
import os
import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# 路径配置
LEGALDB_DIR = Path(__file__).parent.parent / "cases" / "legaldb"
LAWS_DIR = LEGALDB_DIR / "laws"


@dataclass
class LawEntry:
    """单个法律条目"""
    name: str           # 法律名称
    category: str       # 分类：宪法/法律/行政法规/司法解释/监察法规
    date: str           # 发布日期 YYYYMMDD
    path: str           # 文件路径
    text: str           # 全文文本
    size: int           # 字符数


class ChinaLawDatabase:
    """
    全量中国法律数据库
    
    覆盖范围（2,055部）：
    - 宪法及相关：7部（宪法+6个修正案）
    - 基本法律：602部
    - 行政法规：698部
    - 司法解释：746部（最高法/最高检）
    - 监察法规：2部
    总计：2,055部法律法规
    """

    def __init__(self, laws_dir: Path = LAWS_DIR):
        self.laws_dir = laws_dir
        self._index: Dict[str, LawEntry] = {}
        self._names_index: Dict[str, List[str]] = {}
        self._loaded = False

    def load(self, verbose=True):
        """加载法律数据库"""
        if self._loaded:
            return
        
        if verbose:
            print("正在加载全量中国法律数据库...")
        
        txt_files = list(self.laws_dir.glob("*.txt"))
        
        for fpath in txt_files:
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # 解析头部元信息
                meta = {'category': '未知', 'date': '', 'path': str(fpath)}
                name_set = False
                text_lines = []
                
                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith('#'):
                        if not name_set and '分类' not in stripped and '发布' not in stripped and '来源' not in stripped:
                            meta['name'] = stripped[1:].strip()
                            name_set = True
                        elif '分类' in stripped:
                            parts = stripped.split(':', 1)
                            if len(parts) == 2:
                                meta['category'] = parts[1].strip()
                        elif '发布' in stripped:
                            parts = stripped.split(':', 1)
                            if len(parts) == 2:
                                date_val = parts[1].strip().split('_')[0]
                                meta['date'] = date_val
                        elif '来源' in stripped:
                            parts = stripped.split(':', 1)
                            if len(parts) == 2:
                                meta['path'] = stripped  # 来源行不需要解析
                    elif line.startswith('='):
                        continue
                    else:
                        text_lines.append(line.rstrip())
                
                name = meta.get('name', fpath.stem)
                text = '\n'.join(text_lines).strip()
                
                if len(text) > 50 and name:
                    entry = LawEntry(
                        name=name,
                        category=meta['category'],
                        date=meta['date'],
                        path=str(fpath),
                        text=text,
                        size=len(text)
                    )
                    self._index[name] = entry
                    
                    # 构建名称索引（支持模糊搜索）
                    name_key = name.replace('中华人民共和国', '')
                    if name_key not in self._names_index:
                        self._names_index[name_key] = []
                    if name not in self._names_index[name_key]:
                        self._names_index[name_key].append(name)
            
            except Exception as e:
                if verbose:
                    print(f"  加载失败: {fpath.name}: {e}")
        
        self._loaded = True
        
        if verbose:
            print(f"  加载完成: {len(self._index)} 部法律")
            cats = {}
            for entry in self._index.values():
                cats[entry.category] = cats.get(entry.category, 0) + 1
            for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
                print(f"    {cat}: {count} 部")

    def search(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """搜索法律（按名称）"""
        if not self._loaded:
            self.load(verbose=False)
        
        results = []
        kw_lower = keyword.lower()
        
        for name, entry in self._index.items():
            if kw_lower in name.lower():
                results.append({
                    'name': entry.name,
                    'category': entry.category,
                    'date': entry.date,
                    'size': entry.size,
                    'preview': entry.text[:200]
                })
        
        results.sort(key=lambda x: -x['size'])
        return results[:limit]

    def search_fulltext(self, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
        """全文搜索法律"""
        if not self._loaded:
            self.load(verbose=False)
        
        results = []
        kw_lower = keyword.lower()
        
        for name, entry in self._index.items():
            if kw_lower in entry.text.lower():
                # 找到关键词位置
                pos = entry.text.lower().find(kw_lower)
                start = max(0, pos - 50)
                end = min(len(entry.text), pos + len(keyword) + 50)
                snippet = entry.text[start:end]
                
                results.append({
                    'name': entry.name,
                    'category': entry.category,
                    'date': entry.date,
                    'size': entry.size,
                    'snippet': snippet
                })
        
        return results[:limit]

    def get_by_name(self, name: str) -> Optional[LawEntry]:
        """按名称获取法律"""
        if not self._loaded:
            self.load(verbose=False)
        
        # 精确匹配
        if name in self._index:
            return self._index[name]
        
        # 模糊匹配
        name_key = name.replace('中华人民共和国', '')
        for key, names in self._names_index.items():
            if name_key in key or key in name_key:
                if names:
                    return self._index[names[0]]
        
        return None

    def get_text(self, name: str) -> Optional[str]:
        """获取法律全文"""
        entry = self.get_by_name(name)
        return entry.text if entry else None

    def list_by_category(self, category: str) -> List[LawEntry]:
        """按分类列出法律"""
        if not self._loaded:
            self.load(verbose=False)
        
        return [e for e in self._index.values() if e.category == category]

    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计"""
        if not self._loaded:
            self.load(verbose=False)
        
        cats = {}
        total_size = 0
        for entry in self._index.values():
            cats[entry.category] = cats.get(entry.category, 0) + 1
            total_size += entry.size
        
        return {
            'total_laws': len(self._index),
            'total_size_chars': total_size,
            'total_size_mb': total_size / 1024 / 1024,
            'by_category': cats,
            'source': 'github.com/lawtext/law-flk-vol1',
            'total_in_repository': 2055,
            'downloaded_coverage': f"{len(self._index)/2055*100:.1f}%"
        }


# ---- CLI ----

def main():
    import argparse
    parser = argparse.ArgumentParser(description="全量中国法律数据库")
    parser.add_argument("--stats", action="store_true", help="显示统计")
    parser.add_argument("--list", action="store_true", help="列出所有法律")
    parser.add_argument("--search", type=str, help="搜索法律")
    parser.add_argument("--grep", type=str, help="全文搜索")
    parser.add_argument("--show", type=str, help="显示法律全文")
    parser.add_argument("--category", type=str, help="按分类列出")
    args = parser.parse_args()

    db = ChinaLawDatabase()

    if args.stats:
        stats = db.get_stats()
        print("=" * 60)
        print("全量中国法律数据库")
        print("=" * 60)
        print(f"  已下载法律: {stats['total_laws']} 部")
        print(f"  总字符数: {stats['total_size_chars']:,}")
        print(f"  总大小: {stats['total_size_mb']:.1f} MB")
        print(f"  仓库总计: {stats['total_in_repository']} 部")
        print(f"  下载覆盖率: {stats['downloaded_coverage']}")
        print(f"  数据来源: {stats['source']}")
        print("\n分类统计:")
        for cat, count in sorted(stats['by_category'].items(), key=lambda x: -x[1]):
            print(f"  {cat}: {count} 部")
        print("=" * 60)

    elif args.search:
        results = db.search(args.search)
        print(f"搜索 \"{args.search}\": {len(results)} 个结果\n")
        for r in results[:20]:
            print(f"  📜 {r['name']} ({r['category']}, {r['date']})")
            print(f"     {r['preview'][:80]}...")
            print()

    elif args.grep:
        results = db.search_fulltext(args.grep)
        print(f"全文搜索 \"{args.grep}\": {len(results)} 个结果\n")
        for r in results[:20]:
            print(f"  📜 {r['name']} ({r['category']}, {r['date']})")
            print(f"     ...{r['snippet']}...")
            print()

    elif args.show:
        entry = db.get_by_name(args.show)
        if entry:
            print(f"# {entry.name}")
            print(f"分类: {entry.category} | 日期: {entry.date}")
            print(f"字符数: {entry.size}")
            print("=" * 60)
            print(entry.text[:5000])
            if len(entry.text) > 5000:
                print(f"\n... (共 {entry.size} 字符，显示前5000)")
        else:
            print(f"未找到: {args.show}")

    elif args.category:
        entries = db.list_by_category(args.category)
        print(f"分类 \"{args.category}\": {len(entries)} 部法律\n")
        for e in sorted(entries, key=lambda x: x.name):
            print(f"  {e.name} ({e.date}) - {e.size}字符")

    elif args.list:
        stats = db.get_stats()
        print(f"所有法律 ({stats['total_laws']} 部):\n")
        for name, entry in sorted(db._index.items()):
            print(f"  {entry.category}: {name} ({entry.date})")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
