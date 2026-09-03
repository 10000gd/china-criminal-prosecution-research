#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
法律检索增强生成(RAG)系统
基于全量中国法律数据库的向量检索

功能：
- 文本分块（按条文/段落）
- 倒排索引（关键词 -> 块）
- BM25 排序（原有）
- 向量检索（新增：sentence-transformers 轻量模型）
- 混合检索：RRF 融合 BM25 + 向量（新增）
"""

import json
import jieba
import re
import hashlib
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

jieba.setLogLevel(20)  # 关闭jieba日志

LEGALDB_DIR = Path(__file__).parent.parent / "cases" / "legaldb"
LAWS_DIR = LEGALDB_DIR / "laws"
CACHE_DIR = LEGALDB_DIR / ".rag_cache"
VECTOR_CACHE_DIR = CACHE_DIR / "vectors"
CACHE_DIR.mkdir(exist_ok=True)
VECTOR_CACHE_DIR.mkdir(exist_ok=True)

# ===== 向量模型配置 =====
# 使用多语言轻量模型，支持中文，无需微调
# 模型会在首次使用时自动下载（约 500MB）
DEFAULT_EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


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


# ===== 向量嵌入器（懒加载） =====
class LawEmbedder:
    """法律文本向量化器，使用 sentence-transformers 懒加载模型"""

    def __init__(self, model_name: str = None):
        self.model_name = model_name or os.environ.get(
            "LEGAL_EMBED_MODEL", DEFAULT_EMBED_MODEL)
        self._model = None
        self._vector_dim: Optional[int] = None

    @property
    def model(self):
        """懒加载模型，首次访问时初始化（网络错误时由调用方处理）"""
        if self._model is None:
            print(f"  [向量] 加载模型: {self.model_name} ...")
            import os
            # 限制下载超时，避免网络不可用时永久挂起
            os.environ['HF_HUB_DOWNLOAD_TIMEOUT'] = '10'
            os.environ['HF_HUB_HTTP_TIMEOUT'] = '10'
            # Patch httpx.Client 以全局设置超时
            import httpx
            _orig_init = httpx.Client.__init__
            def _patched_init(self, *args, **kwargs):
                kwargs.setdefault('timeout', httpx.Timeout(10.0, connect=5.0))
                _orig_init(self, *args, **kwargs)
            httpx.Client.__init__ = _patched_init
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            self._vector_dim = self._model.get_sentence_embedding_dimension()
            print(f"  [向量] 模型加载完成，向量维度: {self._vector_dim}")
        return self._model

    @property
    def vector_dim(self) -> int:
        """获取向量维度（触发模型加载）"""
        _ = self.model  # 触发加载
        return self._vector_dim or 384

    def encode(self, texts: List[str], batch_size: int = 64,
               show_progress: bool = False) -> List[List[float]]:
        """将文本列表编码为向量"""
        embeddings = self.model.encode(
            texts, batch_size=batch_size, show_progress_bar=show_progress,
            convert_to_numpy=True, normalize_embeddings=True
        )
        return embeddings.tolist()

    def encode_single(self, text: str) -> List[float]:
        """编码单个文本"""
        return self.encode([text])[0]


# ===== 冲突检测（依赖循环导入保护：延迟导入） =====


class LawConflictDetector:
    """法律冲突检测器"""

    def __init__(self):
        self._rules_cache: Dict[str, List[Dict]] = {}

    def detect_conflicts(self, chunks: List[Dict], law_name: str = "") -> List[Dict[str, Any]]:
        """检测法律条文间的潜在冲突"""
        conflicts = []
        texts = [c.get("content", "") for c in chunks]

        # 检测模式1：同一罪名，不同数额标准
        conflict_pairs = [
            ("数额较大", "数额巨大"),
            ("三年以下", "三年以上十年以下"),
            ("十年以下", "十年以上"),
            ("拘役", "有期徒刑"),
            ("并处", "或单处"),
            ("从轻", "从重"),
        ]

        for i, t1 in enumerate(texts):
            for j, t2 in enumerate(texts[i+1:], i+1):
                # 检查是否同一法律内的条款矛盾
                reason = self._check_contradiction(t1, t2, conflict_pairs)
                if reason:
                    conflicts.append({
                        "type": "数值/量刑矛盾",
                        "chunk_a": chunks[i].get("chunk_id", ""),
                        "chunk_b": chunks[j].get("chunk_id", ""),
                        "text_a": t1[:200],
                        "text_b": t2[:200],
                        "reason": reason,
                        "severity": "WARN",
                        "suggestion": "建议核查是否为特别法与一般法关系，或是否为时间效力问题",
                    })

        # 检测模式2：时间冲突（新法 vs 旧法）
        date_pattern = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月")
        for i, t1 in enumerate(texts):
            for j, t2 in enumerate(texts[i+1:], i+1):
                m1, m2 = date_pattern.search(t1), date_pattern.search(t2)
                if m1 and m2:
                    y1, m1_m = int(m1.group(1)), int(m1.group(2))
                    y2, m2_m = int(m2.group(1)), int(m2.group(2))
                    if (y1, m1_m) != (y2, m2_m):
                        # 检查内容相似但日期不同
                        sim = self._text_similarity(t1, t2)
                        if sim > 0.85:
                            newer = f"{y1}年{m1_m}月" if (y1, m1_m) > (y2, m2_m) else f"{y2}年{m2_m}月"
                            conflicts.append({
                                "type": "新法旧法并存",
                                "chunk_a": chunks[i].get("chunk_id", ""),
                                "chunk_b": chunks[j].get("chunk_id", ""),
                                "text_a": t1[:150],
                                "text_b": t2[:150],
                                "reason": f"内容相似度{sim:.0%}，存在{newer}后新法是否废止旧法的问题",
                                "severity": "INFO",
                                "suggestion": "建议核查新法是否明确规定废止旧法相应条款",
                            })

        return conflicts

    def _check_contradiction(self, t1: str, t2: str, patterns: List[Tuple]) -> Optional[str]:
        """检测两条文是否矛盾"""
        for pos, neg in patterns:
            has_pos = pos in t1
            has_neg = pos in t2
            if has_pos and has_neg and pos in t1 and pos in t2:
                # 同一词语在不同条文中出现，检测是否构成矛盾
                ctx1 = t1[t1.find(pos)-20:t1.find(pos)+20] if pos in t1 else ""
                ctx2 = t2[t2.find(pos)-20:t2.find(pos)+20] if pos in t2 else ""
                if ctx1 != ctx2:
                    return f"'{pos}' 在不同条文中出现，上下文不同：[{ctx1}] vs [{ctx2}]"
        return None

    def _text_similarity(self, t1: str, t2: str) -> float:
        """简单词重叠相似度"""
        words1 = set(tokenize(t1))
        words2 = set(tokenize(t2))
        if not words1 or not words2:
            return 0.0
        inter = len(words1 & words2)
        return inter / min(len(words1), len(words2))


class LawRAG:
    """
    法律检索增强生成系统

    功能:
    - 文本分块（按条文/段落）
    - 倒排索引（关键词 -> 块）
    - BM25 排序
    - 向量检索（sentence-transformers，新增）
    - 混合检索：RRF 融合（新增）
    - 上下文窗口扩展
    """

    def __init__(self, embed_model: str = None, enable_vector: bool = True):
        self.chunks: List[Chunk] = []
        self.inverted_index: Dict[str, List[int]] = {}  # token -> chunk_ids
        self.law_index: Dict[str, Dict] = {}  # law_name -> {category, date, chunks_count}
        self._indexed = False
        self._index_file = CACHE_DIR / "rag_index.json"
        self._meta_file = CACHE_DIR / "rag_meta.json"
        self._vector_index_file = VECTOR_CACHE_DIR / "vectors.npy"
        self._chunk_ids_file = VECTOR_CACHE_DIR / "chunk_ids.json"

        # 向量检索相关
        self.enable_vector = enable_vector
        self.embedder: Optional[LawEmbedder] = None
        self._vector_matrix: Optional[List[List[float]]] = None
        self._chunk_id_list: List[str] = []  # 与向量矩阵一一对应
        self._vector_loaded = False

        # TF-IDF Fallback（网络不可用时替代向量检索）
        self._tfidf_matrix: Any = None
        self._tfidf_vectorizer: Any = None
        self._use_tfidf_fallback = False

        # 自动加载索引缓存（惰性）
        self.index_laws()

    @property
    def vector_enabled(self) -> bool:
        return self.enable_vector

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

        # ===== 额外索引：刑法全文（不在 laws/ 子目录，需单独加载）=====
        criminal_law_path = LEGALDB_DIR / "中华人民共和国刑法全文.txt"
        if criminal_law_path.exists():
            from china_law_db import LawEntry
            text = criminal_law_path.read_text(encoding='utf-8')
            criminal_entry = LawEntry(
                name="中华人民共和国刑法",
                category="法律",
                date="20231229",
                path=str(criminal_law_path),
                text=text,
                size=len(text)
            )
            criminal_chunks = self._chunk_law(criminal_entry)
            for chunk in criminal_chunks:
                chunk_idx = len(self.chunks)
                self.chunks.append(chunk)
                tokens = tokenize(chunk.content)
                for token in set(tokens):
                    if len(token) >= 2:
                        if token not in self.inverted_index:
                            self.inverted_index[token] = []
                        self.inverted_index[token].append(chunk_idx)
            self.law_index[criminal_entry.name] = {
                'category': criminal_entry.category,
                'date': criminal_entry.date,
                'chunks_count': len(criminal_chunks),
                'size': criminal_entry.size
            }
            print(f"  已索引刑法全文: {len(criminal_chunks)} 个文本块")

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

    def _ensure_vector(self):
        """确保向量索引已加载（懒加载）；网络不可用时降级为 TF-IDF → BM25"""
        if not self.enable_vector:
            return
        if self._vector_loaded:
            return
        if self._use_tfidf_fallback:
            return  # 已知不可用，已切换

        # 尝试加载向量缓存（优先）
        if self._vector_index_file.exists() and self._chunk_ids_file.exists():
            print("  [向量] 加载向量缓存...")
            try:
                import numpy as np
                mat = np.load(self._vector_index_file)
                self._vector_matrix = mat.tolist()
                with open(self._chunk_ids_file, encoding="utf-8") as f:
                    self._chunk_id_list = json.load(f)
                print(f"  [向量] 已加载 {len(self._chunk_id_list)} 条向量")
                self._vector_loaded = True
                return
            except Exception as e:
                print(f"  [向量] 加载缓存失败: {e}")

        # 网络可用性预检（快速）
        import socket
        network_ok = False
        try:
            socket.setdefaulttimeout(3)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).close()
            # 尝试连接 HuggingFace 元数据服务器
            socket.create_connection(('huggingface.co', 443), timeout=3)
            network_ok = True
        except Exception:
            pass

        if not network_ok:
            print("  [向量] 网络不可达，跳过 transformer 加载，切换 TF-IDF fallback")
            self._build_tfidf_index()
            self._vector_loaded = True
            return

        # 初始化嵌入器
        if self.embedder is None:
            try:
                self.embedder = LawEmbedder()
            except Exception as e:
                print(f"  [向量] 嵌入器初始化失败: {e}，切换 TF-IDF fallback")
                self._build_tfidf_index()
                self._vector_loaded = True
                return

        # 构建向量索引（网络错误时降级 TF-IDF）
        try:
            self._build_vector_index()
        except Exception as e:
            print(f"  [向量] 向量索引构建失败: {e}")
            print(f"  [向量] 切换 TF-IDF fallback...")
            try:
                self._build_tfidf_index()
            except Exception as tfidf_err:
                print(f"  [向量] TF-IDF fallback 也失败: {tfidf_err}，降级为纯 BM25")
                self.enable_vector = False
            self._vector_loaded = True

    def _build_vector_index(self):
        """构建向量索引并缓存"""
        if not self.enable_vector:
            return
        import numpy as np

        print("  [向量] 生成文本向量...")
        self.embedder = LawEmbedder()

        # 批量编码所有chunk内容
        texts = [c.content for c in self.chunks]
        self._chunk_id_list = [c.chunk_id for c in self.chunks]

        # 分批编码，避免内存问题
        batch_size = 128
        all_vectors = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            vecs = self.embedder.encode(batch, batch_size=batch_size, show_progress=False)
            all_vectors.extend(vecs)
            print(f"  [向量] {min(i+batch_size, len(texts))}/{len(texts)}")

        self._vector_matrix = all_vectors
        self._vector_loaded = True

        # 保存缓存
        try:
            VECTOR_CACHE_DIR.mkdir(exist_ok=True)
            mat = np.array(all_vectors, dtype=np.float32)
            np.save(self._vector_index_file, mat)
            with open(self._chunk_ids_file, 'w', encoding='utf-8') as f:
                json.dump(self._chunk_id_list, f, ensure_ascii=False)
            print(f"  [向量] 缓存已保存: {self._vector_index_file}")
        except Exception as e:
            print(f"  [向量] 保存缓存失败: {e}")

    def _cosine_sim(self, a: List[float], b: List[float]) -> float:
        """计算余弦相似度（向量已归一化时即点积）"""
        return sum(x * y for x, y in zip(a, b))

    def _build_tfidf_index(self):
        """构建 TF-IDF 索引（网络不可用时的本地 fallback）"""
        from sklearn.feature_extraction.text import TfidfVectorizer
        import numpy as np

        print("  [向量] 构建 TF-IDF fallback 索引...")
        texts = [c.content for c in self.chunks]
        self._tfidf_vectorizer = TfidfVectorizer(
            max_features=10000,
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.95,
        )
        self._tfidf_matrix = self._tfidf_vectorizer.fit_transform(texts)
        self._use_tfidf_fallback = True
        print(f"  [向量] TF-IDF 索引完成: {self._tfidf_matrix.shape[0]} 文档 × {self._tfidf_matrix.shape[1]} 特征")

    def _search_vector(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """纯向量检索（top_k 结果，return [(chunk_idx, score)]）"""
        import numpy as np
        self._ensure_vector()

        # Transformer 向量模式
        if self._vector_matrix is not None:
            q_vec = self.embedder.encode_single(query)
            scores_list: List[Tuple[int, float]] = []
            for i, vec in enumerate(self._vector_matrix):
                score = self._cosine_sim(q_vec, vec)
                if score > 0:
                    scores_list.append((i, score))
        # TF-IDF fallback 模式
        elif self._use_tfidf_fallback and self._tfidf_matrix is not None:
            q_vec = self._tfidf_vectorizer.transform([query]).toarray()[0]
            nonzero = np.nonzero(q_vec)[0]
            scores_list = []
            if len(nonzero) > 0:
                doc_scores = self._tfidf_matrix[:, nonzero].toarray()
                q_norm = np.linalg.norm(q_vec)
                if q_norm > 0:
                    for doc_idx in range(doc_scores.shape[0]):
                        doc_vec = doc_scores[doc_idx]
                        doc_norm = np.linalg.norm(doc_vec)
                        if doc_norm > 0:
                            score = float(np.dot(doc_vec, q_vec) / (doc_norm * q_norm))
                            if score > 0:
                                scores_list.append((doc_idx, score))
        else:
            return []

        scores_list.sort(key=lambda x: -x[1])
        return scores_list[:top_k]

    def _rrf_fusion(self, bm25_results: List[Tuple[int, float]],
                    vector_results: List[Tuple[int, float]],
                    k: int = 60) -> List[int]:
        """
        Reciprocal Rank Fusion (RRF) 混合排序

        RRF score = Σ 1/(k+rank_i)
        k=60 为常用默认值，融合效果稳定
        """
        rrf_scores: Dict[int, float] = {}

        for rank, (chunk_idx, _) in enumerate(bm25_results):
            rrf_scores[chunk_idx] = rrf_scores.get(chunk_idx, 0) + 1.0 / (k + rank + 1)

        for rank, (chunk_idx, _) in enumerate(vector_results):
            rrf_scores[chunk_idx] = rrf_scores.get(chunk_idx, 0) + 1.0 / (k + rank + 1)

        ranked = sorted(rrf_scores.items(), key=lambda x: -x[1])
        return [idx for idx, _ in ranked]

    def search(self, query: str, top_k: int = 10,
               category_filter: Optional[str] = None,
               law_filter: Optional[str] = None,
               hybrid: bool = True,
               vector_weight: float = 0.5) -> List[Dict[str, Any]]:
        """
        检索相关法律条文

        Args:
            query: 查询文本
            top_k: 返回结果数
            category_filter: 限定分类(宪法/法律/行政法规/司法解释/监察法规)
            law_filter: 限定法律名称
            hybrid: 是否使用混合检索（True=BM25+向量融合，False=纯BM25）
            vector_weight: 向量权重（仅hybrid=True时参考，已由RRF替代）

        Returns:
            排序后的相关条文列表
        """
        if not self._indexed:
            self.index_laws()

        # ===== BM25 检索 =====
        tokens = tokenize(query)
        query_ngrams = set(tokens)

        for i in range(len(query) - 1):
            ng = query[i:i+2]
            if 'a' <= ng[0] <= 'z' or 'A' <= ng[0] <= 'Z' or '0' <= ng[0] <= '9':
                continue
            query_ngrams.add(ng)

        scores: Dict[int, float] = {}
        chunk_freq: Dict[int, int] = {}

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
            idf = max(0.0, 1.0 + (N - n + 0.5) / (n + 0.5))

            for cid in chunk_ids:
                chunk = self.chunks[cid]

                if category_filter and chunk.category != category_filter:
                    continue
                if law_filter and chunk.law_name != law_filter:
                    continue

                if cid not in scores:
                    scores[cid] = 0.0
                    chunk_freq[cid] = 0

                freq = chunk.content.count(token)
                score = idf * (freq * (k1 + 1)) / (freq + k1 * (1 - b + b * chunk.length / avg_len))
                scores[cid] += score
                chunk_freq[cid] += 1

        bm25_ranked = sorted(scores.items(), key=lambda x: (-x[1], -chunk_freq.get(x[0], 0)))

        # ===== 向量检索 =====
        use_vector = hybrid and (self.enable_vector or self._use_tfidf_fallback)
        if use_vector:
            vector_ranked = self._search_vector(query, top_k=top_k * 2)
            # RRF 融合
            fused_order = self._rrf_fusion(bm25_ranked[:top_k*3], vector_ranked)
            final_ids = fused_order[:top_k]
        else:
            final_ids = [idx for idx, _ in bm25_ranked[:top_k]]

        # ===== 构建结果 =====
        results = []
        for chunk_idx in final_ids:
            chunk = self.chunks[chunk_idx]
            bm25_score = scores.get(chunk_idx, 0)

            # 向量得分（Transformer 或 TF-IDF）
            vector_score = 0.0
            if self.enable_vector and self._vector_matrix:
                try:
                    vec_idx = self._chunk_id_list.index(chunk.chunk_id)
                    vector_score = self._cosine_sim(
                        self.embedder.encode_single(query),
                        self._vector_matrix[vec_idx]
                    )
                except (ValueError, IndexError):
                    pass
            elif self._use_tfidf_fallback and self._tfidf_matrix is not None:
                try:
                    import numpy as np
                    q_vec = self._tfidf_vectorizer.transform([query]).toarray()[0]
                    nonzero = np.nonzero(q_vec)[0]
                    if len(nonzero) > 0:
                        doc_vec = self._tfidf_matrix[chunk_idx, nonzero].toarray().flatten()
                        q_norm = np.linalg.norm(q_vec)
                        doc_norm = np.linalg.norm(doc_vec)
                        if q_norm > 0 and doc_norm > 0:
                            vector_score = float(np.dot(doc_vec, q_vec) / (doc_norm * q_norm))
                except Exception:
                    pass

            preview = self._get_preview(chunk.content, query, radius=100)
            results.append({
                'law': chunk.law_name,
                'category': chunk.category,
                'chunk_id': chunk.chunk_id,
                'bm25_score': round(bm25_score, 3),
                'vector_score': round(vector_score, 4),
                'match_count': chunk_freq.get(chunk_idx, 0),
                'preview': preview,
                'content': chunk.content[:500],
                'length': chunk.length,
                'retrieval_method': 'hybrid' if (hybrid and self.enable_vector) else 'bm25',
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

    def rag_retrieve(self, query: str, context_window: int = 2000,
                     hybrid: bool = True) -> Tuple[str, List[Dict]]:
        """
        RAG检索:获取检索结果用于增强生成

        Returns:
            (context_str, results_list)
        """
        results = self.search(query, top_k=5, hybrid=hybrid)

        context_parts = []
        for i, r in enumerate(results):
            method_tag = "🔍混合" if r.get('retrieval_method') == 'hybrid' else "📄BM25"
            context_parts.append(
                f"【来源{i+1}·{method_tag}】{r['law']}({r['category']})\n{r['preview']}"
            )

        context = '\n\n'.join(context_parts)

        if len(context) > context_window:
            context = context[:context_window] + "\n\n(已截断)"

        return context, results

    def detect_conflicts(self, law_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        检测法律冲突

        Args:
            law_name: 指定法律名称，不指定则检测所有法律

        Returns:
            冲突列表
        """
        if not self._indexed:
            self.index_laws()

        detector = LawConflictDetector()
        all_conflicts = []

        if law_name:
            law_chunks = [
                c for c in self.chunks if c.law_name == law_name
            ]
            conflicts = detector.detect_conflicts(
                [c.to_dict() for c in law_chunks], law_name
            )
            all_conflicts.extend(conflicts)
        else:
            # 按法律分组检测
            by_law: Dict[str, List[Chunk]] = {}
            for c in self.chunks:
                by_law.setdefault(c.law_name, []).append(c)

            for name, chunks in by_law.items():
                conflicts = detector.detect_conflicts(
                    [c.to_dict() for c in chunks], name
                )
                all_conflicts.extend(conflicts)

        return all_conflicts

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

        stats = {
            'total_chunks': len(self.chunks),
            'total_indexed_tokens': len(self.inverted_index),
            'total_laws': len(self.law_index),
            'avg_chunk_size': sum(c.length for c in self.chunks) / max(len(self.chunks), 1),
            'by_category': {
                cat: len([c for c in self.chunks if c.category == cat])
                for cat in ['法律', '行政法规', '司法解释', '宪法', '监察法规']
            },
            'cache_file': str(self._index_file),
            'indexed': self._indexed,
            'vector_enabled': self.enable_vector,
            'vector_loaded': self._vector_loaded,
        }
        return stats


# ===== CLI =====

def main():
    import argparse
    parser = argparse.ArgumentParser(description="法律RAG检索系统")
    parser.add_argument("--query", type=str, help="查询文本")
    parser.add_argument("--rebuild", action="store_true", help="重建索引")
    parser.add_argument("--rebuild-vectors", action="store_true", help="重建向量索引")
    parser.add_argument("--stats", action="store_true", help="显示统计")
    parser.add_argument("--top", type=int, default=5, help="返回结果数")
    parser.add_argument("--bm25-only", action="store_true", help="仅使用BM25（禁用向量检索）")
    parser.add_argument("--detect-conflicts", type=str, metavar="LAW_NAME",
                        help="检测指定法律条文冲突（不指定则检测全部）")
    args = parser.parse_args()

    rag = LawRAG(enable_vector=not args.bm25_only)

    if args.detect_conflicts is not None:
        rag.index_laws(force_rebuild=args.rebuild)
        law_name = args.detect_conflicts if args.detect_conflicts != "" else None
        conflicts = rag.detect_conflicts(law_name=law_name)
        print(f"\n检测到 {len(conflicts)} 条潜在冲突:\n")
        for i, c in enumerate(conflicts):
            print(f"--- 冲突{i+1} [{c['type']}] 严重度: {c['severity']} ---")
            print(f"  原因: {c['reason']}")
            print(f"  建议: {c['suggestion']}")
            print()
        return

    if args.stats:
        stats = rag.get_stats()
        print("=" * 60)
        print("  法律RAG索引统计")
        print("=" * 60)
        print(f"  文本块: {stats['total_chunks']:,}")
        print(f"  索引词: {stats['total_indexed_tokens']:,}")
        print(f"  法律数: {stats['total_laws']}")
        print(f"  平均块大小: {stats['avg_chunk_size']:.0f}字符")
        print(f"  向量检索: {'已启用' if stats['vector_enabled'] else '已禁用'}")
        print(f"  向量已加载: {'是' if stats['vector_loaded'] else '否'}")
        print(f"\n  分类分布:")
        for cat, cnt in sorted(stats['by_category'].items(), key=lambda x: -x[1]):
            if cnt > 0:
                print(f"    {cat}: {cnt}")
        print(f"\n  缓存: {stats['cache_file']}")
        print("=" * 60)
        return

    if args.query:
        rag.index_laws(force_rebuild=args.rebuild)
        if args.rebuild_vectors:
            rag._vector_loaded = False
            rag._build_vector_index()

        context, results = rag.rag_retrieve(args.query, hybrid=not args.bm25_only)

        print(f"\n查询: {args.query}")
        print(f"检索到 {len(results)} 个相关条文:\n")

        for i, r in enumerate(results[:args.top]):
            method = r.get('retrieval_method', 'bm25')
            tag = "🔍混合" if method == 'hybrid' else "📄BM25"
            print(f"--- 结果{i+1} [{r['law']}] {tag} ---")
            print(f"  分类: {r['category']} | BM25: {r['bm25_score']} | 向量: {r['vector_score']}")
            print(f"  预览: {r['preview']}")
            print()
    else:
        rag.index_laws(force_rebuild=args.rebuild)
        stats = rag.get_stats()
        print(f"RAG索引就绪: {stats['total_chunks']} 块, {stats['total_laws']} 部法律, "
              f"向量检索: {'启用' if stats['vector_enabled'] else '禁用'}")


if __name__ == "__main__":
    main()
