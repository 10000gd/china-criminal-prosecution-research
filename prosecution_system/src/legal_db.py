# -*- coding: utf-8 -*-
"""
法律数据库加载器 - prosecution_system/src/legal_db.py

功能：
- 加载中国刑法条文数据库
- 加载罪名数据库
- 支持罪名搜索和法条查询

数据来源：
- C-CLAIM Dataset (CC BY-SA 4.0)
- https://github.com/Shiori-pope/c-claim
"""

import json
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional, Any

LEGALDB_DIR = Path(__file__).parent.parent / "cases" / "legaldb"


class LegalDB:
    """法律数据库加载器"""
    
    def __init__(self, db_dir: Path = LEGALDB_DIR):
        self.db_dir = db_dir
        self._laws_df: Optional[pd.DataFrame] = None
        self._case_types: Optional[List[str]] = None
        self._chapters: Optional[List[Dict]] = None
    
    @property
    def laws(self) -> pd.DataFrame:
        """获取刑法条文 DataFrame"""
        if self._laws_df is None:
            self._laws_df = pd.read_csv(self.db_dir / "刑法条文.csv")
        return self._laws_df
    
    @property
    def case_types(self) -> List[str]:
        """获取全部罪名列表"""
        if self._case_types is None:
            with open(self.db_dir / "标准案由表.txt", 'r', encoding='utf-8') as f:
                self._case_types = [line.strip() for line in f if line.strip()]
        return self._case_types
    
    @property
    def chapters(self) -> List[Dict]:
        """获取章节案由映射"""
        if self._chapters is None:
            with open(self.db_dir / "章节案由表.jsonl", 'r', encoding='utf-8') as f:
                self._chapters = [json.loads(line) for line in f if line.strip()]
        return self._chapters
    
    def get_article(self, article_no: str) -> Optional[Dict]:
        """根据条文号获取条文内容"""
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
        """获取涉及某罪名的全部条文"""
        results = []
        for _, row in self.laws.iterrows():
            if pd.notna(row['case_types']):
                try:
                    case_types = json.loads(row['case_types'])
                    if case_type in case_types:
                        results.append({
                            "chapter": row['chapter'],
                            "article_no": row['article_no'],
                            "text": row['text'][:200] + "..." if len(str(row['text'])) > 200 else row['text']
                        })
                except:
                    pass
        return results
    
    def search_case_types(self, keyword: str) -> List[str]:
        """搜索罪名"""
        keyword = keyword.lower()
        return [ct for ct in self.case_types if keyword in ct.lower()]
    
    def get_chapter_case_types(self, chapter: str) -> List[str]:
        """获取某章节的所有罪名"""
        for ch in self.chapters:
            if ch['chapter'] == chapter:
                return ch['case_types']
        return []
    
    def stats(self) -> Dict[str, Any]:
        """获取数据库统计"""
        return {
            "total_articles": len(self.laws),
            "total_case_types": len(self.case_types),
            "total_chapters": len(self.chapters),
            "total_interpretations": len(pd.read_csv(self.db_dir / "刑法司法解释.csv")),
            "total_documents": len(pd.read_csv(self.db_dir / "刑法司法文件.csv")),
        }


def main():
    """测试法律数据库"""
    db = LegalDB()
    
    print("=== 法律数据库测试 ===\n")
    
    # 统计
    stats = db.stats()
    print("数据库统计:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    
    print(f"\n罪名总数: {len(db.case_types)}")
    print(f"前10个罪名: {', '.join(db.case_types[:10])}")
    
    # 测试搜索
    print("\n搜索'诈骗'相关罪名:")
    for ct in db.search_case_types("诈骗")[:5]:
        print(f"  - {ct}")
    
    # 测试条文查询
    print("\n查询第192条 (集资诈骗罪):")
    article = db.get_article("第一百九十二条")
    if article:
        print(f"  章节: {article['chapter']}")
        print(f"  罪名: {', '.join(article['case_types'])}")


if __name__ == "__main__":
    main()
