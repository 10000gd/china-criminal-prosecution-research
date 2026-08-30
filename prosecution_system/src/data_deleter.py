# -*- coding: utf-8 -*-
"""
数据删除与匿名化模块 - prosecution_system/src/data_deleter.py

功能：
- 对案件 YAML 中的敏感字段进行匿名化/删除处理
- 支持「报告输出前自动匿名」和「彻底删除源数据」两种模式
- 保留法律分析结构，只移除个人身份信息

删除级别：
  LEVEL_ANONYMIZE — 将姓名/公司名替换为占位符（生成报告用）
  LEVEL_REDACT    — 删除所有个人身份信息字段（但保留结构）
  LEVEL_DELETE    — 彻底删除字段（不可恢复）

适用场景：
  - 对外分享报告前匿名化
  - 提交代码仓库前清理敏感数据
  - GDPR/个人信息保护合规
"""

import json
import copy
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import re


class DeletionLevel:
    ANONYMIZE = "ANONYMIZE"   # 替换为占位符（报告用）
    REDACT    = "REDACT"      # 删除内容但保留字段
    DELETE    = "DELETE"      # 彻底删除字段


# ===== 敏感字段配置 =====

SENSITIVE_FIELDS = {
    # 字段路径（dot notation）: (显示名, 匿名级别)
    "case_info.defendants": ("被告人/被告单位", "ANONYMIZE"),
    "case_info.prosecutor": ("公诉机关", "REDACT"),
    "case_info.court": ("审理法院", "KEEP"),        # 法院名称通常可保留
    "case_info.judge": ("审判人员", "REDACT"),
    "case_info.prosecutor_names": ("检察官姓名", "REDACT"),
    "case_info.lawyer": ("辩护人", "REDACT"),
    "case_info.defendant_ids": ("身份证号", "DELETE"),
    "case_info.phone": ("电话号码", "DELETE"),
    "case_info.address": ("地址", "DELETE"),
    "case_info.bank_account": ("银行账号", "DELETE"),
    "case_info.company_reg_num": ("工商注册号", "DELETE"),
    "charges.charges_judged.*.statute": ("法条引用", "KEEP"),
    "charges.charges_missed.*.statute": ("法条引用", "KEEP"),
}

# 姓名/公司名检测正则（用于通用匿名）
NAME_PATTERNS = [
    re.compile(r"[\u4e00-\u9fa5]{2,4}(公司|集团|企业|有限|股份)"),
    re.compile(r"[\u4e00-\u9fa5]{2,4}[\u4e00-\u9fa5·\s]{0,4}(有限公司|集团有限公司)"),
    re.compile(r"^[\u4e00-\u9fa5]{2,3}$"),  # 纯中文姓名
]


@dataclass
class DeletionReport:
    """删除操作报告"""
    original_keys: List[str] = field(default_factory=list)
    anonymized_keys: List[str] = field(default_factory=list)
    redacted_keys: List[str] = field(default_factory=list)
    deleted_keys: List[str] = field(default_factory=list)
    kept_keys: List[str] = field(default_factory=list)
    hash_before: str = ""
    hash_after: str = ""

    def summary(self) -> str:
        return (
            f"匿名化: {len(self.anonymized_keys)} 字段 | "
            f"删除内容: {len(self.redacted_keys)} 字段 | "
            f"彻底删除: {len(self.deleted_keys)} 字段 | "
            f"保留: {len(self.kept_keys)} 字段"
        )


class DataDeleter:
    """
    数据删除与匿名化处理器

    用法：
        deleter = DataDeleter()
        clean_data, report = deleter.process(data, level="ANONYMIZE")
        print(report.summary())
    """

    def __init__(self):
        self._report: Optional[DeletionReport] = None

    def process(
        self,
        data: Dict[str, Any],
        level: str = "ANONYMIZE",
        preserve_structure: bool = True,
    ) -> Tuple[Dict[str, Any], DeletionReport]:
        """
        处理数据，返回清理后的副本

        Args:
            data: 案件数据字典
            level: ANONYMIZE / REDACT / DELETE
            preserve_structure: 是否保留字段结构（False=彻底删除字段）

        Returns:
            (清理后数据, 删除报告)
        """
        report = DeletionReport()
        result = copy.deepcopy(data)

        report.hash_before = self._hash_data(data)

        # 遍历敏感字段配置
        for field_path, (label, default_level) in SENSITIVE_FIELDS.items():
            self._process_field(result, field_path, level, default_level, report, preserve_structure)

        # 通用检测：遍历所有字符串字段，匿名化姓名/公司名
        if level in ("ANONYMIZE", "REDACT"):
            self._anonymize_strings(result, report, level)

        report.hash_after = self._hash_data(result)

        self._report = report
        return result, report

    def _process_field(
        self,
        data: Dict[str, Any],
        field_path: str,
        effective_level: str,
        default_level: str,
        report: DeletionReport,
        preserve_structure: bool,
    ):
        """处理单个字段路径"""
        parts = field_path.split(".")
        current = data

        # 导航到父级
        for part in parts[:-1]:
            if isinstance(current, dict):
                if part not in current:
                    return
                current = current[part]
            elif isinstance(current, list):
                try:
                    idx = int(part)
                    if idx < 0 or idx >= len(current):
                        return
                    current = current[idx]
                except ValueError:
                    # 通配符处理（如 charges_judged.*.statute）
                    if part == "*":
                        for item in current:
                            if isinstance(item, dict):
                                self._process_field(item, ".".join(parts[parts.index(part)+1:]),
                                                    effective_level, default_level, report, preserve_structure)
                        return
                    return
            else:
                return

        key = parts[-1]
        if not isinstance(current, dict) or key not in current:
            return

        # 判断实际处理级别
        action_level = effective_level if effective_level != "ANONYMIZE" else default_level

        if action_level == "KEEP":
            report.kept_keys.append(field_path)
            return

        value = current[key]
        report.original_keys.append(field_path)

        if action_level == "DELETE":
            if preserve_structure:
                current[key] = None
            else:
                del current[key]
            report.deleted_keys.append(field_path)

        elif action_level == "REDACT":
            current[key] = self._redact_value(value)
            report.redacted_keys.append(field_path)

        elif action_level == "ANONYMIZE":
            current[key] = self._anonymize_value(value, field_path)
            report.anonymized_keys.append(field_path)

    def _anonymize_value(self, value: Any, field_path: str) -> Any:
        """生成匿名化值"""
        if value is None:
            return None
        if isinstance(value, str):
            # 生成哈希前缀以保持唯一性
            h = hashlib.md5(value.encode()).hexdigest()[:4]
            if "defendants" in field_path or "公司" in value or "集团" in value:
                return f"[被告单位_{h}]" if "公司" in value or "集团" in value else f"[当事人_{h}]"
            if "prosecutor" in field_path:
                return f"[公诉机关_{h}]"
            if "court" in field_path:
                return f"[审理法院_{h}]"
            if "judge" in field_path or "lawyer" in field_path:
                return f"[法律职业者_{h}]"
            return f"[已匿名_{h}]"
        if isinstance(value, list):
            return [self._anonymize_value(v, field_path) for v in value]
        if isinstance(value, dict):
            return {k: self._anonymize_value(v, field_path) for k, v in value.items()}
        return value

    def _redact_value(self, value: Any) -> str:
        """彻底删除内容，只保留类型标记"""
        if value is None:
            return None
        if isinstance(value, str):
            return "[已删除]"
        if isinstance(value, list):
            return ["[已删除]"] * len(value)
        if isinstance(value, dict):
            return {k: "[已删除]" for k in value}
        return "[已删除]"

    def _anonymize_strings(self, data: Dict, report: DeletionReport, level: str):
        """通用字符串匿名化（兜底）"""
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, str) and self._looks_like_name(v):
                    report.anonymized_keys.append(f"<auto>:{k}")
                    data[k] = self._anonymize_value(v, k)
                elif isinstance(v, (dict, list)):
                    self._anonymize_strings(v, report, level)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, (dict, list)):
                    self._anonymize_strings(item, report, level)

    def _looks_like_name(self, text: str) -> bool:
        """判断字符串是否像人名或公司名"""
        if not text or len(text) > 50:
            return False
        # 中文姓名特征
        if re.match(r"^[\u4e00-\u9fa5]{2,4}$", text):
            return True
        # 公司名特征
        for p in NAME_PATTERNS:
            if p.match(text):
                return True
        return False

    def _hash_data(self, data: Dict) -> str:
        """计算数据指纹（用于变更检测）"""
        return hashlib.sha256(
            json.dumps(data, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()[:16]

    def verify_anonymity(self, data: Dict[str, Any]) -> List[str]:
        """
        验证数据是否已完全匿名化，返回残留敏感词列表
        """
        violations: List[str] = []
        raw = json.dumps(data, ensure_ascii=False)

        # 检测残留姓名/公司名
        name_patterns = [
            (r"[\u4e00-\u9fa5]{2,4}(公司|集团|企业|有限|股份)", "公司名"),
            (r"^[\u4e00-\u9fa5]{2,3}$", "疑似人名"),
            (r"\d{15,18}", "身份证号"),
            (r"1[3-9]\d{9}", "手机号"),
            (r"\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}", "银行卡号"),
        ]
        for pattern, label in name_patterns:
            matches = re.findall(pattern, raw)
            violations.extend([f"{label}: {m}" for m in matches if "[已" not in m])

        return violations


# ===== CLI =====

def main():
    import argparse, yaml
    parser = argparse.ArgumentParser(description="数据删除与匿名化")
    parser.add_argument("--case", type=str, help="案件ID（从 cases/ 目录读取）")
    parser.add_argument("--input", type=str, help="输入 YAML/JSON 文件路径")
    parser.add_argument("--output", type=str, help="输出文件路径")
    parser.add_argument("--level", type=str, default="ANONYMIZE",
                        choices=["ANONYMIZE", "REDACT", "DELETE"],
                        help="删除级别（默认ANONYMIZE）")
    parser.add_argument("--verify", action="store_true", help="验证匿名化效果")
    args = parser.parse_args()

    # 加载数据
    if args.case:
        from case_loader import CaseLoader
        loader = CaseLoader()
        data = loader.load(args.case)
    elif args.input:
        with open(args.input, encoding="utf-8") as f:
            data = yaml.safe_load(f) if args.input.endswith((".yaml", ".yml")) else json.load(f)
    else:
        print("❌ 请指定 --case 或 --input")
        return

    deleter = DataDeleter()
    clean_data, report = deleter.process(data, level=args.level)

    print(f"\n{'='*50}")
    print(f"  数据删除报告（级别: {args.level}）")
    print(f"{'='*50}")
    print(f"  {report.summary()}")
    print(f"  数据指纹: {report.hash_before} → {report.hash_after}")

    if report.anonymized_keys:
        print(f"\n  匿名化字段 ({len(report.anonymized_keys)}):")
        for k in report.anonymized_keys[:10]:
            print(f"    · {k}")
        if len(report.anonymized_keys) > 10:
            print(f"    ... 等 {len(report.anonymized_keys)} 个")

    if report.redacted_keys:
        print(f"\n  删除内容字段 ({len(report.redacted_keys)}):")
        for k in report.redacted_keys:
            print(f"    · {k}")

    if report.deleted_keys:
        print(f"\n  彻底删除字段 ({len(report.deleted_keys)}):")
        for k in report.deleted_keys:
            print(f"    · {k}")

    if args.verify:
        violations = deleter.verify_anonymity(clean_data)
        if violations:
            print(f"\n  ⚠️ 匿名化验证失败，残留敏感信息:")
            for v in violations[:10]:
                print(f"    · {v}")
        else:
            print(f"\n  ✅ 匿名化验证通过，无残留敏感信息")

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            if args.output.endswith((".yaml", ".yml")):
                yaml.dump(clean_data, f, allow_unicode=True, default_flow_style=False)
            else:
                json.dump(clean_data, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 已保存: {args.output}")


if __name__ == "__main__":
    main()
