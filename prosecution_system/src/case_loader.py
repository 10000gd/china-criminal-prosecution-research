# -*- coding: utf-8 -*-
"""
案件加载器 - prosecution_system/src/case_loader.py
多案扩展系统核心模块

功能：
- 从 YAML 配置加载案件数据
- 验证必填字段完整性
- 提供案件列表管理
- 支持案件搜索/过滤
- 倒排索引加速搜索
"""

import os
import re
import yaml
from pathlib import Path
from typing import Optional, Dict, List
from cachetools import TTLCache
import logging

logger = logging.getLogger(__name__)

CASES_DIR = Path(__file__).parent.parent / "cases"

# TTL 缓存：每项缓存 1 小时（3600 秒），最大 200 条案件
_case_cache: TTLCache = TTLCache(maxsize=200, ttl=3600)


def _get_cache(case_id: str):
    """从模块级 TTL 缓存读取"""
    if case_id in _case_cache:
        return _case_cache[case_id]
    return None


def _set_cache(case_id: str, data: Dict):
    """写入模块级 TTL 缓存"""
    _case_cache[case_id] = data


# ---- 倒排索引 ----

class CaseSearchIndex:
    """案件倒排索引，用于快速全文搜索（替代逐文件遍历）"""

    def __init__(self, cases_dir: Path):
        self.cases_dir = cases_dir
        # 倒排索引: term -> [case_id, ...]
        self.index: Dict[str, List[str]] = {}
        # 案件元数据缓存: case_id -> meta dict
        self.case_meta: Dict[str, Dict] = {}
        self.rebuild()

    def _tokenize(self, text: str) -> List[str]:
        """简单分词：中文按单字，英文按单词（均小写）"""
        if not text:
            return []
        text = text.lower()
        # 中文字符（每个字作为一个词项）
        chinese = re.findall(r'[\u4e00-\u9fff]', text)
        # 英文单词和数字
        english = re.findall(r'[a-z0-9]+', text)
        return chinese + english

    def _index_text(self, case_id: str, text: str):
        """将文本分词后加入倒排索引"""
        if not text:
            return
        words = self._tokenize(text)
        for word in words:
            if word not in self.index:
                self.index[word] = []
            if case_id not in self.index[word]:
                self.index[word].append(case_id)

    def _build_index(self):
        """遍历所有案件文件，构建倒排索引"""
        self.index.clear()
        self.case_meta.clear()

        for f in sorted(self.cases_dir.glob("*.yaml")):
            if f.name.startswith("_"):
                continue
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    d = yaml.safe_load(fh)
                if not d:
                    continue

                meta = d.get("meta", {})
                case_id = meta.get("case_id", f.stem)

                # 索引可搜索的文本字段
                searchable_texts = [
                    str(meta),
                    str(d.get("case_info", {})),
                    str(d.get("charges", {})),
                    str(d.get("evidence_gaps", [])),
                    str(d.get("comparable_cases", {})),
                    str(d.get("assets", {})),
                    str(d.get("defendants_person", [])),
                    str(d.get("defendants_corp", [])),
                    str(d.get("victims", [])),
                ]
                for txt in searchable_texts:
                    self._index_text(case_id, txt)

                # 缓存元数据（用于结果返回）
                self.case_meta[case_id] = {
                    "case_id": case_id,
                    "case_name": meta.get("case_name", ""),
                    "status": meta.get("status", ""),
                    "matched": True,
                }
            except Exception:
                pass

    def search(self, query: str, top_n: int = 20) -> List[Dict]:
        """快速搜索：基于倒排索引，按命中词项数排序"""
        tokens = self._tokenize(query)
        if not tokens:
            return []

        # 统计每个案件的命中次数
        scores: Dict[str, int] = {}
        for token in tokens:
            if token in self.index:
                for case_id in self.index[token]:
                    scores[case_id] = scores.get(case_id, 0) + 1

        # 按命中数降序，取 top_n
        sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)[:top_n]
        return [self.case_meta[cid] for cid in sorted_ids if cid in self.case_meta]

    def rebuild(self):
        """重新构建索引（外部调用入口）"""
        self._build_index()


# ---- 案件加载器 ----

class CaseLoader:
    """案件加载器"""

    def __init__(self, cases_dir: Path = CASES_DIR):
        self.cases_dir = cases_dir
        self._local_cache: Dict[str, Dict] = {}  # 本地实例缓存（无 TTL）
        self._search_index: Optional[CaseSearchIndex] = None  # 倒排索引（惰性初始化）
        self._lowercase_map: Optional[Dict[str, Path]] = None  # case_id→文件路径映射（惰性缓存）

    # ---- 搜索索引（惰性初始化）----

    @property
    def search_index(self) -> CaseSearchIndex:
        """获取搜索索引（首次访问时构建）"""
        if self._search_index is None:
            self._search_index = CaseSearchIndex(self.cases_dir)
        return self._search_index

    def rebuild_search_index(self):
        """重建搜索索引"""
        self._search_index = CaseSearchIndex(self.cases_dir)

    # ---- 基础加载 ----

    def load(self, case_id: str, use_cache: bool = True) -> Dict:
        """
        加载指定案件配置
        case_id: 案件编号，如 "CASE-001" 或 "hengda"
        """
        # 优先从模块级 TTL 缓存读取
        if use_cache:
            cached = _get_cache(case_id)
            if cached is not None:
                return cached
            if case_id in self._local_cache:
                return self._local_cache[case_id]

        # 尝试多种匹配方式
        yaml_file = self._resolve_file(case_id)
        if yaml_file is None:
            raise FileNotFoundError(f"案件配置文件未找到: {case_id}")

        with open(yaml_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if data is None:
            raise ValueError(f"案件配置文件为空或格式错误: {yaml_file}")

        # 同时写入模块级 TTL 缓存和本地缓存
        _set_cache(case_id, data)
        self._local_cache[case_id] = data
        return data

    def _build_lowercase_map(self) -> Dict[str, Path]:
        """惰性构建 case_id → 文件路径映射（一次性扫描，全局缓存）"""
        m: Dict[str, Path] = {}
        for f in self.cases_dir.glob("*.yaml"):
            stem = f.stem.lower()
            m[stem] = f          # CASE-0001.yaml → case-0001
            if stem not in m:
                m[stem] = f
        return m

    def _resolve_file(self, case_id: str) -> Optional[Path]:
        """解析案件ID到文件路径"""
        # 去掉 .yaml 后缀（如果有）
        key = case_id.lower().removesuffix(".yaml")

        # 直接匹配
        direct = self.cases_dir / f"{key}.yaml"
        if direct.exists():
            return direct

        # 惰性加载映射表
        if self._lowercase_map is None:
            self._lowercase_map = self._build_lowercase_map()

        return self._lowercase_map.get(key)

    # ---- 批量操作 ----

    def list_cases(self, status: Optional[str] = None) -> List[Dict]:
        """列出所有案件，可按状态过滤"""
        results = []
        for f in sorted(self.cases_dir.glob("*.yaml")):
            if f.name.startswith("_"):
                continue
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    d = yaml.safe_load(fh)
                    if d:
                        meta = d.get("meta", {})
                        cid = meta.get("case_id", f.stem)
                        if status is None or meta.get("status") == status:
                            results.append({
                                "case_id": cid,
                                "case_name": meta.get("case_name", ""),
                                "case_name_full": meta.get("case_name_full", ""),
                                "case_type": meta.get("case_type", ""),
                                "status": meta.get("status", ""),
                                "report_date": meta.get("report_date", ""),
                                "confidentiality": meta.get("confidentiality", ""),
                            })
            except Exception as e:
                logger.warning(f"加载案件 {f.name} 失败: {e}")
        return results

    def search_cases(self, query: str) -> List[Dict]:
        """
        全文搜索案件（优先使用倒排索引，索引未就绪时回退到逐文件扫描）
        """
        try:
            return self.search_index.search(query)
        except Exception:
            # 索引异常时回退到原始逐文件搜索
            return self._search_cases_fallback(query)

    def _search_cases_fallback(self, query: str) -> List[Dict]:
        """逐文件扫描搜索（search_cases 的兜底实现）"""
        results = []
        for f in sorted(self.cases_dir.glob("*.yaml")):
            if f.name.startswith("_"):
                continue
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    content = fh.read()
                    if query.lower() in content.lower():
                        fh.seek(0)
                        d = yaml.safe_load(fh)
                        if d:
                            meta = d.get("meta", {})
                            results.append({
                                "case_id": meta.get("case_id", f.stem),
                                "case_name": meta.get("case_name", ""),
                                "status": meta.get("status", ""),
                                "matched": True,
                            })
            except Exception:
                pass
        return results

    # ---- 数据访问便捷方法 ----

    def get_meta(self, case_id: str) -> Dict:
        """获取案件元数据"""
        data = self.load(case_id)
        return data.get("meta", {})

    def get_case_info(self, case_id: str) -> Dict:
        """获取案件基本信息"""
        data = self.load(case_id)
        return data.get("case_info", {})

    def get_defendants(self, case_id: str) -> Dict:
        """获取被告人信息"""
        data = self.load(case_id)
        return {
            "corp": data.get("defendants_corp", []),
            "person": data.get("defendants_person", []),
        }

    def get_charges(self, case_id: str) -> Dict:
        """获取罪名信息"""
        data = self.load(case_id)
        return data.get("charges", {})

    def get_evidence_gaps(self, case_id: str) -> List[Dict]:
        """获取证据断裂点"""
        data = self.load(case_id)
        return data.get("evidence_gaps", [])

    def get_victims(self, case_id: str) -> List[Dict]:
        """获取受害者信息"""
        data = self.load(case_id)
        return data.get("victims", [])

    def get_comparable_cases(self, case_id: str) -> Dict:
        """获取类案信息"""
        data = self.load(case_id)
        return data.get("comparable_cases", {})

    def get_assets(self, case_id: str) -> Dict:
        """获取资产信息"""
        data = self.load(case_id)
        return data.get("assets", {})

    def get_sources(self, case_id: str) -> List[Dict]:
        """获取数据来源"""
        data = self.load(case_id)
        return data.get("sources", [])

    def get_policy_recommendations(self, case_id: str) -> List[Dict]:
        """获取政策建议"""
        data = self.load(case_id)
        return data.get("policy_recommendations", [])

    # ---- 验证 ----

    def validate(self, case_id: str) -> List[str]:
        """验证案件配置完整性，返回警告列表"""
        data = self.load(case_id)
        warnings = []
        required_meta = ["case_id", "case_name", "case_name_full", "status"]
        for field in required_meta:
            if not data.get("meta", {}).get(field):
                warnings.append(f"缺少必填字段: meta.{field}")

        if not data.get("case_info", {}).get("court"):
            warnings.append("缺少必填字段: case_info.court")
        return warnings


# ---- CLI 入口 ----

def main():
    import argparse
    parser = argparse.ArgumentParser(description="案件配置加载器")
    parser.add_argument("--list", action="store_true", help="列出所有案件")
    parser.add_argument("--case", type=str, help="案件ID")
    parser.add_argument("--search", type=str, help="搜索关键词")
    parser.add_argument("--validate", action="store_true", help="验证配置")
    args = parser.parse_args()

    loader = CaseLoader()

    if args.list:
        for c in loader.list_cases():
            print(f"[{c['case_id']}] {c['case_name']} | {c['status']} | {c.get('case_type', '')}")

    elif args.case:
        data = loader.load(args.case)
        import json
        print(json.dumps(data, ensure_ascii=False, indent=2))

    elif args.search:
        for c in loader.search_cases(args.search):
            print(f"[{c['case_id']}] {c['case_name']} | {c['status']}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
