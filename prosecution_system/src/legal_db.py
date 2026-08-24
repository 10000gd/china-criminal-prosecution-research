# -*- coding: utf-8 -*-
"""
法律数据库加载器 - prosecution_system/src/legal_db.py

功能：
- 加载中国刑法条文数据库（追诉系统专用）
- 加载全量中国法律数据库（2,055部）
- 支持罪名搜索和法条查询
- 支持法律RAG检索

数据来源：
- C-CLAIM Dataset (CC BY-SA 4.0) - https://github.com/Shiori-pope/c-claim
- lawtext/law-flk-vol1 (2,055部法律法规)
"""

import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional, Any

LEGALDB_DIR = Path(__file__).parent.parent / "cases" / "legaldb"
LOCAL_REG_INDEX = LEGALDB_DIR / "local_regulations_index.json"


class LocalRegulationDB:
    """地方性法规数据库（补充层）"""

    def __init__(self, index_path: Path = LOCAL_REG_INDEX):
        self.index_path = index_path
        self._data: Optional[Dict] = None

    def _load(self):
        if self._data is None:
            if self.index_path.exists():
                with open(self.index_path, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
            else:
                self._data = {'total': 0, 'records': [], 'by_province': {}}

    @property
    def records(self) -> List[Dict]:
        self._load()
        return self._data.get('records', [])

    @property
    def total(self) -> int:
        self._load()
        return self._data.get('total', 0)

    @property
    def by_province(self) -> Dict[str, int]:
        self._load()
        return self._data.get('by_province', {})

    def search(self, keyword: str = '', province: str = '',
               top_k: int = 20) -> List[Dict]:
        """搜索地方性法规
        
        Args:
            keyword: 关键词（匹配标题和摘要）
            province: 省份名称
            top_k: 返回数量
        """
        results = self.records
        if province:
            results = [r for r in results if province in r.get('province', '') or province in r.get('issuing_authority', '')]
        if keyword:
            kw = keyword.lower()
            results = [r for r in results if kw in r.get('name', '').lower() or kw in r.get('summary', '').lower()]
        return results[:top_k]

    def get_by_province(self, province: str) -> List[Dict]:
        return [r for r in self.records if province in r.get('province', '') or province in r.get('issuing_authority', '')]

    def get_stats(self) -> Dict[str, Any]:
        self._load()
        return {
            'total': self.total,
            'by_province': self.by_province,
            'note': '仅含摘要预览，全文需专项采集（flk.npc.gov.cn）'
        }


class LegalDB:
    """法律数据库加载器（追诉系统专用）"""

    def __init__(self, db_dir: Path = LEGALDB_DIR):
        self.db_dir = db_dir
        self._laws_df: Optional[pd.DataFrame] = None
        self._case_types: Optional[List[str]] = None
        self._chapters: Optional[List[Dict]] = None
        self._china_law_db = None
        self._law_rag = None
        self._local_reg = None

    # ===== 地方性法规（补充层）=====

    @property
    def local_reg_db(self) -> LocalRegulationDB:
        if self._local_reg is None:
            self._local_reg = LocalRegulationDB()
        return self._local_reg

    def search_local_regulations(self, keyword: str = '', province: str = '',
                                  top_k: int = 20) -> List[Dict]:
        """搜索地方性法规（需专项采集全文）"""
        return self.local_reg_db.search(keyword=keyword, province=province, top_k=top_k)

    def list_local_regulations_by_province(self, province: str) -> List[Dict]:
        return self.local_reg_db.get_by_province(province)

    # ===== 追诉系统专用（刑法） =====

    @property
    def laws(self) -> pd.DataFrame:
        if self._laws_df is None:
            self._laws_df = pd.read_csv(self.db_dir / "刑法条文.csv")
        return self._laws_df

    @property
    def case_types(self) -> List[str]:
        if self._case_types is None:
            with open(self.db_dir / "标准案由表.txt", 'r', encoding='utf-8') as f:
                self._case_types = [line.strip() for line in f if line.strip()]
        return self._case_types

    @property
    def chapters(self) -> List[Dict]:
        if self._chapters is None:
            with open(self.db_dir / "章节案由表.jsonl", 'r', encoding='utf-8') as f:
                self._chapters = [json.loads(line) for line in f if line.strip()]
        return self._chapters

    def get_article(self, article_no: str) -> Optional[Dict]:
        df = self.laws
        row = df[df['article_no'] == article_no]
        if len(row) > 0:
            r = row.iloc[0]
            return {
                "chapter": r['chapter'],
                "article_no": r['article_no'],
                "text": r['text'],
                "category": r['category'],
                "case_types": json.loads(r['case_types']) if pd.notna(r['case_types']) else []
            }
        return None

    def get_case_type_articles(self, case_type: str) -> List[Dict]:
        results = []
        for _, row in self.laws.iterrows():
            if pd.notna(row['case_types']):
                try:
                    cts = json.loads(row['case_types'])
                    if case_type in cts:
                        results.append({
                            "chapter": row['chapter'],
                            "article_no": row['article_no'],
                            "text": row['text'][:200] + "..." if len(str(row['text'])) > 200 else row['text']
                        })
                except Exception:
                    pass
        return results

    def search_case_types(self, keyword: str) -> List[str]:
        keyword = keyword.lower()
        return [ct for ct in self.case_types if keyword in ct.lower()]

    def get_chapter_case_types(self, chapter: str) -> List[str]:
        for ch in self.chapters:
            if ch['chapter'] == chapter:
                return ch['case_types']
        return []

    # ===== 全量中国法律库 =====

    @property
    def china_law_db(self):
        if self._china_law_db is None:
            from china_law_db import ChinaLawDatabase
            self._china_law_db = ChinaLawDatabase(self.db_dir / "laws")
            self._china_law_db.load(verbose=False)
        return self._china_law_db

    def search_laws(self, keyword: str, category: Optional[str] = None) -> List[Dict]:
        results = self.china_law_db.search(keyword)
        if category:
            results = [r for r in results if r.get('category') == category]
        return results

    def get_law_fulltext(self, law_name: str) -> Optional[Any]:
        return self.china_law_db.get_by_name(law_name)

    def list_laws_by_category(self, category: str) -> List[str]:
        return self.china_law_db.list_by_category(category)

    def fulltext_search(self, keyword: str, top_k: int = 10) -> List[Dict]:
        return self.china_law_db.search_fulltext(keyword, top_k=top_k)

    # ===== RAG 检索 =====

    @property
    def law_rag(self):
        if self._law_rag is None:
            from law_rag import LawRAG
            self._law_rag = LawRAG()
            self._law_rag.index_laws()
        return self._law_rag

    def rag_search(self, query: str, top_k: int = 5,
                   category_filter: Optional[str] = None) -> List[Dict]:
        return self.law_rag.search(query, top_k=top_k, category_filter=category_filter)

    def rag_retrieve(self, query: str, context_window: int = 2000) -> tuple:
        return self.law_rag.rag_retrieve(query, context_window=context_window)

    # ===== 统计 =====

    def stats(self) -> Dict[str, Any]:
        stats = {
            "total_articles": len(self.laws),
            "total_case_types": len(self.case_types),
            "total_chapters": len(self.chapters),
        }
        try:
            stats["total_interpretations"] = len(pd.read_csv(self.db_dir / "刑法司法解释.csv"))
        except Exception:
            pass
        try:
            law_stats = self.china_law_db.get_stats()
            stats["china_law_total"] = law_stats["total_laws"]
            stats["china_law_chars"] = law_stats["total_size_chars"]
            stats["china_law_by_category"] = law_stats["by_category"]
        except Exception:
            pass
        try:
            rag = self.law_rag
            rs = rag.get_stats()
            stats["rag_chunks"] = rs["total_chunks"]
            stats["rag_indexed_tokens"] = rs["total_indexed_tokens"]
        except Exception:
            pass
        try:
            lr = self.local_reg_db
            lr_stats = lr.get_stats()
            stats["local_regulations"] = lr_stats["total"]
            stats["local_reg_by_province"] = lr_stats["by_province"]
            stats["local_reg_note"] = lr_stats["note"]
        except Exception:
            pass
        return stats


def main():
    db = LegalDB()
    print("=== 法律数据库测试 ===\n")
    stats = db.stats()
    for k, v in stats.items():
        if isinstance(v, dict):
            print(f"  {k}:")
            for kk, vv in v.items():
                print(f"    {kk}: {vv}")
        else:
            print(f"  {k}: {v}")

    print(f"\n罪名总数: {len(db.case_types)}")
    print(f"前5个罪名: {', '.join(db.case_types[:5])}")

    print("\n全量法律库搜索'贪污':")
    for r in db.search_laws("贪污")[:3]:
        print(f"  - {r['name']} ({r['category']})")

    print("\nRAG检索'挪用公款罪构成要件':")
    for r in db.rag_search("挪用公款罪构成要件", top_k=3):
        print(f"  - [{r['law']}] 匹配度:{r['score']} | {r['preview'][:60]}...")

    print("\n地方性法规搜索'交通安全'（省级）:")
    for r in db.search_local_regulations(keyword='交通', top_k=5):
        print(f"  - [{r['province']}] {r['name']} | {r['issue_date']} | {r['content_length']}字")

    print("\n地方性法规 - 西藏:")
    tibet = db.list_local_regulations_by_province('西藏')
    print(f"  共 {len(tibet)} 部")
    for r in tibet[:3]:
        print(f"  - {r['name']} | {r['content_length']}字")


if __name__ == "__main__":
    main()
