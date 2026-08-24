#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
法律检索增强生成(RAG)系统
基于全量中国法律数据库的向量检索
"""

import json
import jieba
import re
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

jieba.setLogLevel(20)  # 关闭jieba日志
LEGALDB_DIR = Path(__file__).parent.parent / "cases" / "legaldb"
LAWS_DIR = LEGALDB_DIR / "laws"
CACHE_DIR = LEGALDB_DIR / ".rag_cache"
CACHE_DIR.mkdir(exist_ok=True)

def tokenize(text: str) -> List[str]:
    """使用jieba分词,返回2-gram词组"""
    words = jieba.cut(text, cut_all=False)
    words = [w.strip() for w in words if len(w.strip()) >= 2]
    # 添加2-gram
    result = words[:]
    for i in range(len(words) - 1):
        ng = words[i] + words[i+1]
        if len(ng) >= 4:
            result.append(ng)
    return result


# ===== 倒排索引 =====

@dataclass
class Chunk:
    """法律文本块"""
    law_name: str
    category: str
    chunk_id: str
    content: str
    position: int  # 在法律中的字符位置
    length: int

    def to_dict(self) -> Dict:
        return {
            'law_name': self.law_name,
            'category': self.category,
            'chunk_id': self.chunk_id,
            'content': self.content,
            'position': self.position,
            'length': self.length
        }


class LawRAG:
    """
    法律检索增强生成系统

    功能:
    - 文本分块(按条文/段落)
    - 倒排索引(关键词 -> 块)
    - BM25 排序
    - 上下文窗口扩展
    """

    def __init__(self):
        self.chunks: List[Chunk] = []
        self.inverted_index: Dict[str, List[int]] = {}  # token -> chunk_ids
        self.law_index: Dict[str, Dict] = {}  # law_name -> {category, date, chunks_count}
        self._indexed = False
        self._index_file = CACHE_DIR / "rag_index.json"
        self._meta_file = CACHE_DIR / "rag_meta.json"

    def index_laws(self, force_rebuild: bool = False):
        """建立法律索引"""
        if self._indexed and not force_rebuild:
            return

        # 尝试加载缓存
        if not force_rebuild and self._index_file.exists() and self._meta_file.exists():
            print("加载索引缓存...")
            self._load_cache()
            self._indexed = True
            print(f"  已加载 {len(self.chunks)} 个文本块, {len(self.inverted_index)} 个索引词")
            return

        print("正在建立法律索引...")
        from china_law_db import ChinaLawDatabase

        db = ChinaLawDatabase(LAWS_DIR)
        db.load(verbose=False)

        self.chunks = []
        self.inverted_index = {}
        self.law_index = {}

        for entry in db._index.values():
            law_chunks = self._chunk_law(entry)
            for chunk in law_chunks:
                chunk_idx = len(self.chunks)
                self.chunks.append(chunk)

                # 索引tokens
                tokens = tokenize(chunk.content)
                for token in set(tokens):
                    if len(token) >= 2:
                        if token not in self.inverted_index:
                            self.inverted_index[token] = []
                        self.inverted_index[token].append(chunk_idx)

            self.law_index[entry.name] = {
                'category': entry.category,
                'date': entry.date,
                'chunks_count': len(law_chunks),
                'size': entry.size
            }

        self._indexed = True
        self._save_cache()
        print(f"  索引完成: {len(self.chunks)} 个文本块, {len(self.inverted_index)} 个索引词, {len(self.law_index)} 部法律")

    def _chunk_law(self, entry) -> List[Chunk]:
        """将法律文本分块"""
        chunks = []
        text = entry.text

        # 策略1: 按条文分块
        article_pattern = re.compile(r'第([一二三四五六七八九十百千零〇\\d]+)条')
        positions = []
        for m in article_pattern.finditer(text):
            positions.append((m.start(), m.group(1)))

        for i, (start, art_name) in enumerate(positions):
            end = positions[i+1][0] if i+1 < len(positions) else len(text)
            content = text[start:end].strip()

            if len(content) < 20:
                continue

            chunk_id = hashlib.md5(f"{entry.name}_{art_name}".encode()).hexdigest()[:12]

            chunk = Chunk(
                law_name=entry.name,
                category=entry.category,
                chunk_id=chunk_id,
                content=content,
                position=start,
                length=len(content)
            )
            chunks.append(chunk)

        # 如果条文分块太少,按段落分
        if len(chunks) < 3:
            paragraphs = [p.strip() for p in text.split('\n') if len(p.strip()) > 50]
            for j, para in enumerate(paragraphs):
                chunk_id = hashlib.md5(f"{entry.name}_para_{j}".encode()).hexdigest()[:12]
                chunk = Chunk(
                    law_name=entry.name,
                    category=entry.category,
                    chunk_id=chunk_id,
                    content=para,
                    position=j * 1000,
                    length=len(para)
                )
                chunks.append(chunk)

        return chunks

    def search(self, query: str, top_k: int = 10,
               category_filter: Optional[str] = None,
               law_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        检索相关法律条文

        Args:
            query: 查询文本
            top_k: 返回结果数
            category_filter: 限定分类(宪法/法律/行政法规/司法解释/监察法规)
            law_filter: 限定法律名称

        Returns:
            排序后的相关条文列表
        """
        if not self._indexed:
            self.index_laws()

        # 分词
        tokens = tokenize(query)
        query_ngrams = set(tokens)

        # 额外:对查询文本也提取2-gram(跨词边界)
        for i in range(len(query) - 1):
            ng = query[i:i+2]
            if 'a' <= ng[0] <= 'z' or 'A' <= ng[0] <= 'Z' or '0' <= ng[0] <= '9':
                continue  # 跳过英文数字混合
            query_ngrams.add(ng)

        # BM25评分
        scores: Dict[int, float] = {}
        chunk_freq: Dict[int, int] = {}  # 每个chunk包含多少查询词

        N = len(self.chunks)
        avg_len = sum(c.length for c in self.chunks) / max(N, 1)
        k1, b = 1.5, 0.75

        for token in query_ngrams:
            if len(token) < 2:
                continue
            if token not in self.inverted_index:
                continue

            chunk_ids = self.inverted_index[token]
            n = len(chunk_ids)
            # 改进的 BM25 IDF（Okapi 公式）
            idf = max(0.0, 1.0 + (N - n + 0.5) / (n + 0.5))

            for cid in chunk_ids:
                chunk = self.chunks[cid]

                # 分类过滤
                if category_filter and chunk.category != category_filter:
                    continue
                if law_filter and chunk.law_name != law_filter:
                    continue

                if cid not in scores:
                    scores[cid] = 0.0
                    chunk_freq[cid] = 0

                # BM25
                freq = chunk.content.count(token)
                score = idf * (freq * (k1 + 1)) / (freq + k1 * (1 - b + b * chunk.length / avg_len))
                scores[cid] += score
                chunk_freq[cid] += 1

        # 排序
        ranked = sorted(scores.items(), key=lambda x: (-x[1], -chunk_freq.get(x[0], 0)))

        results = []
        for chunk_id, score in ranked[:top_k]:
            chunk = self.chunks[chunk_id]
            # 找关键词上下文
            preview = self._get_preview(chunk.content, query, radius=100)

            results.append({
                'law': chunk.law_name,
                'category': chunk.category,
                'chunk_id': chunk.chunk_id,
                'score': round(score, 3),
                'match_count': chunk_freq.get(chunk_id, 0),
                'preview': preview,
                'content': chunk.content[:500],
                'length': chunk.length
            })

        return results

    def _get_preview(self, text: str, query: str, radius: int = 80) -> str:
        """获取关键词周围上下文"""
        text_lower = text.lower()
        query_lower = query.lower()

        pos = text_lower.find(query_lower[:5])
        if pos < 0:
            return text[:radius*2]

        start = max(0, pos - radius)
        end = min(len(text), pos + radius)

        preview = text[start:end]
        if start > 0:
            preview = '...' + preview
        if end < len(text):
            preview = preview + '...'

        return preview

    def rag_retrieve(self, query: str, context_window: int = 2000) -> Tuple[str, List[Dict]]:
        """
        RAG检索:获取检索结果用于增强生成

        Returns:
            (context_str, results_list)
        """
        results = self.search(query, top_k=5)

        context_parts = []
        for i, r in enumerate(results):
            context_parts.append(f"【来源{i+1}】{r['law']}({r['category']})\n{r['preview']}")

        context = '\n\n'.join(context_parts)

        if len(context) > context_window:
            context = context[:context_window] + "\n\n(已截断)"

        return context, results

    def _save_cache(self):
        """保存索引缓存"""
        chunks_data = [c.to_dict() for c in self.chunks]
        with open(self._index_file, 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, ensure_ascii=False)

        meta = {
            'inverted_index': {k: v for k, v in self.inverted_index.items()},
            'law_index': self.law_index,
            'total_chunks': len(self.chunks),
            'total_tokens': len(self.inverted_index),
        }
        with open(self._meta_file, 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False)

    def _load_cache(self):
        """加载索引缓存"""
        with open(self._index_file, 'r', encoding='utf-8') as f:
            chunks_data = json.load(f)

        self.chunks = []
        for d in chunks_data:
            # 兼容旧版本
            if 'law' in d and 'law_name' not in d:
                d['law_name'] = d.pop('law')
            self.chunks.append(Chunk(**d))

        with open(self._meta_file, 'r', encoding='utf-8') as f:
            meta = json.load(f)

        self.inverted_index = meta['inverted_index']
        self.law_index = meta['law_index']

    def get_stats(self) -> Dict[str, Any]:
        """获取RAG索引统计"""
        if not self._indexed:
            self.index_laws()

        return {
            'total_chunks': len(self.chunks),
            'total_indexed_tokens': len(self.inverted_index),
            'total_laws': len(self.law_index),
            'avg_chunk_size': sum(c.length for c in self.chunks) / max(len(self.chunks), 1),
            'by_category': {
                cat: len([c for c in self.chunks if c.category == cat])
                for cat in ['法律', '行政法规', '司法解释', '宪法', '监察法规']
            },
            'cache_file': str(self._index_file),
            'indexed': self._indexed
        }


# ===== CLI =====

def main():
    import argparse
    parser = argparse.ArgumentParser(description="法律RAG检索系统")
    parser.add_argument("--query", type=str, help="查询文本")
    parser.add_argument("--rebuild", action="store_true", help="重建索引")
    parser.add_argument("--stats", action="store_true", help="显示统计")
    parser.add_argument("--top", type=int, default=5, help="返回结果数")
    args = parser.parse_args()

    rag = LawRAG()

    if args.stats:
        stats = rag.get_stats()
        print("=" * 60)
        print("  法律RAG索引统计")
        print("=" * 60)
        print(f"  文本块: {stats['total_chunks']:,}")
        print(f"  索引词: {stats['total_indexed_tokens']:,}")
        print(f"  法律数: {stats['total_laws']}")
        print(f"  平均块大小: {stats['avg_chunk_size']:.0f}字符")
        print(f"\n  分类分布:")
        for cat, cnt in sorted(stats['by_category'].items(), key=lambda x: -x[1]):
            if cnt > 0:
                print(f"    {cat}: {cnt}")
        print(f"\n  缓存: {stats['cache_file']}")
        print("=" * 60)
        return

    if args.query:
        rag.index_laws(force_rebuild=args.rebuild)
        context, results = rag.rag_retrieve(args.query)

        print(f"\n查询: {args.query}")
        print(f"检索到 {len(results)} 个相关条文:\n")

        for i, r in enumerate(results[:args.top]):
            print(f"--- 结果{i+1} [{r['law']}] ---")
            print(f"  分类: {r['category']} | 匹配度: {r['score']} | 匹配词数: {r['match_count']}")
            print(f"  预览: {r['preview']}")
            print()
    else:
        rag.index_laws(force_rebuild=args.rebuild)
        stats = rag.get_stats()
        print(f"RAG索引就绪: {stats['total_chunks']} 块, {stats['total_laws']} 部法律")


if __name__ == "__main__":
    main()
