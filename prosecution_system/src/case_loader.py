# -*- coding: utf-8 -*-
"""
案件加载器 - prosecution_system/src/case_loader.py
多案扩展系统核心模块

功能：
- 从 YAML 配置加载案件数据
- 验证必填字段完整性
- 提供案件列表管理
- 支持案件搜索/过滤
"""

import os
import yaml
from pathlib import Path
from typing import Optional, Dict, List, Any
from cachetools import TTLCache

CASES_DIR = Path(__file__).parent.parent / "cases"

# TTL 缓存：每项缓存 1 小时（3600 秒），最大 200 条案件
_case_cache: TTLCache = TTLCache(maxsize=200, ttl=3600)


def _get_cache(case_id: str, loader: "CaseLoader" = None):
    """从模块级 TTL 缓存读取"""
    if case_id in _case_cache:
        return _case_cache[case_id]
    return None


def _set_cache(case_id: str, data: Dict):
    """写入模块级 TTL 缓存"""
    _case_cache[case_id] = data


class CaseLoader:
    """案件加载器"""

    def __init__(self, cases_dir: Path = CASES_DIR):
        self.cases_dir = cases_dir
        self._local_cache: Dict[str, Dict] = {}  # 本地实例缓存（无 TTL）

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

    def _resolve_file(self, case_id: str) -> Optional[Path]:
        """解析案件ID到文件路径"""
        # 直接匹配
        direct = self.cases_dir / f"{case_id}.yaml"
        if direct.exists():
            return direct

        # 小写匹配（case_id不含横杠时，如 "hengda"）
        for f in self.cases_dir.glob("*.yaml"):
            if f.stem.lower() == case_id.lower():
                return f
            # 匹配 case_id 字段
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    d = yaml.safe_load(fh)
                    if d and d.get("meta", {}).get("case_id", "").lower() == case_id.lower():
                        return f
            except Exception:
                pass

        return None

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
                print(f"警告：加载案件 {f.name} 失败: {e}")
        return results

    def search_cases(self, query: str) -> List[Dict]:
        """全文搜索案件"""
        results = []
        for f in sorted(self.cases_dir.glob("*.yaml")):
            if f.name.startswith("_"):
                continue
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    content = fh.read()
                    if query.lower() in content.lower():
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
