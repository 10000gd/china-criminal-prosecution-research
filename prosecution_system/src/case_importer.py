# -*- coding: utf-8 -*-
"""
案件数据导入器 - case_importer.py

支持多种格式的案件数据导入：
- YAML格式（系统原生）
- JSON格式
- CSV格式（表格导入）
- Excel格式（xlsx）
- 裁判文书JSON格式

使用方法:
    from case_importer import CaseImporter
    importer = CaseImporter()
    result = importer.import_file("案件数据.xlsx")
    result = importer.import_directory("cases/custom/")
"""

import json
import csv
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import re


@dataclass
class ImportResult:
    """导入结果"""
    success: bool
    imported: int
    failed: int
    errors: List[str]
    warnings: List[str]
    imported_ids: List[str]
    
    def summary(self) -> str:
        status = "✅ 成功" if self.success else "❌ 失败"
        return f"{status}: 导入 {self.imported}/{self.imported + self.failed} 个案件"


class CaseImporter:
    """案件数据导入器"""
    
    # 支持的文件格式
    SUPPORTED_FORMATS = {
        ".yaml": "yaml",
        ".yml": "yaml",
        ".json": "json",
        ".csv": "csv",
        ".xlsx": "xlsx",
        ".xls": "xls",
    }
    
    def __init__(self, output_dir: Path = None):
        """初始化导入器
        
        Args:
            output_dir: 案件输出目录
        """
        self.output_dir = output_dir or Path("cases")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.imported_ids: List[str] = []
    
    def import_file(self, file_path: str) -> ImportResult:
        """导入单个文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            ImportResult: 导入结果
        """
        path = Path(file_path)
        
        if not path.exists():
            return ImportResult(
                success=False,
                imported=0,
                failed=1,
                errors=[f"文件不存在: {file_path}"],
                warnings=[],
                imported_ids=[]
            )
        
        suffix = path.suffix.lower()
        if suffix not in self.SUPPORTED_FORMATS:
            return ImportResult(
                success=False,
                imported=0,
                failed=1,
                errors=[f"不支持的文件格式: {suffix}"],
                warnings=[],
                imported_ids=[]
            )
        
        format_type = self.SUPPORTED_FORMATS[suffix]
        self.errors = []
        self.warnings = []
        self.imported_ids = []
        
        try:
            if format_type == "yaml":
                return self._import_yaml(path)
            elif format_type == "json":
                return self._import_json(path)
            elif format_type == "csv":
                return self._import_csv(path)
            elif format_type in ["xlsx", "xls"]:
                return self._import_excel(path)
        except Exception as e:
            self.errors.append(f"导入失败: {str(e)}")
        
        return ImportResult(
            success=len(self.errors) == 0,
            imported=len(self.imported_ids),
            failed=len(self.errors),
            errors=self.errors,
            warnings=self.warnings,
            imported_ids=self.imported_ids
        )
    
    def import_directory(self, dir_path: str) -> ImportResult:
        """导入目录下所有支持的文件
        
        Args:
            dir_path: 目录路径
            
        Returns:
            ImportResult: 汇总导入结果
        """
        path = Path(dir_path)
        
        all_errors = []
        all_warnings = []
        all_imported_ids = []
        total_imported = 0
        total_failed = 0
        
        for file_path in path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_FORMATS:
                result = self.import_file(str(file_path))
                total_imported += result.imported
                total_failed += result.failed
                all_errors.extend(result.errors)
                all_warnings.extend(result.warnings)
                all_imported_ids.extend(result.imported_ids)
        
        return ImportResult(
            success=total_failed == 0,
            imported=total_imported,
            failed=total_failed,
            errors=all_errors,
            warnings=all_warnings,
            imported_ids=all_imported_ids
        )
    
    def _import_yaml(self, path: Path) -> ImportResult:
        """导入YAML文件"""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        if isinstance(data, list):
            # 批量案件
            for item in data:
                self._save_case(item)
        else:
            # 单个案件
            self._save_case(data)
        
        return ImportResult(
            success=len(self.errors) == 0,
            imported=len(self.imported_ids),
            failed=len(self.errors),
            errors=self.errors,
            warnings=self.warnings,
            imported_ids=self.imported_ids
        )
    
    def _import_json(self, path: Path) -> ImportResult:
        """导入JSON文件"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 支持裁判文书JSON格式
        if isinstance(data, dict) and "caseInfo" in data:
            data = self._convert_wenshu_format(data)
        
        if isinstance(data, list):
            for item in data:
                self._save_case(item)
        else:
            self._save_case(data)
        
        return ImportResult(
            success=len(self.errors) == 0,
            imported=len(self.imported_ids),
            failed=len(self.errors),
            errors=self.errors,
            warnings=self.warnings,
            imported_ids=self.imported_ids
        )
    
    def _import_csv(self, path: Path) -> ImportResult:
        """导入CSV文件"""
        cases = []
        
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                case = self._csv_row_to_case(row)
                if case:
                    cases.append(case)
        
        for case in cases:
            self._save_case(case)
        
        return ImportResult(
            success=len(self.errors) == 0,
            imported=len(self.imported_ids),
            failed=len(self.errors),
            errors=self.errors,
            warnings=self.warnings,
            imported_ids=self.imported_ids
        )
    
    def _import_excel(self, path: Path) -> ImportResult:
        """导入Excel文件"""
        try:
            import pandas as pd
        except ImportError:
            self.errors.append("需要安装 pandas 和 openpyxl: pip install pandas openpyxl")
            return ImportResult(
                success=False,
                imported=0,
                failed=1,
                errors=self.errors,
                warnings=[],
                imported_ids=[]
            )
        
        df = pd.read_excel(path)
        cases = []
        
        for _, row in df.iterrows():
            case = self._dataframe_row_to_case(row)
            if case:
                cases.append(case)
        
        for case in cases:
            self._save_case(case)
        
        return ImportResult(
            success=len(self.errors) == 0,
            imported=len(self.imported_ids),
            failed=len(self.errors),
            errors=self.errors,
            warnings=self.warnings,
            imported_ids=self.imported_ids
        )
    
    def _convert_wenshu_format(self, wenshu_data: Dict) -> Dict:
        """转换裁判文书JSON格式到系统格式"""
        case_info = wenshu_data.get("caseInfo", {})
        
        # 提取基本信息
        case = {
            "case_id": case_info.get("caseId", f"WENSHU-{datetime.now().strftime('%Y%m%d%H%M%S')}"),
            "case_name": case_info.get("caseName", "未知案件"),
            "case_type": case_info.get("caseType", "刑事案件"),
            "judgment_date": case_info.get("judgmentDate", ""),
            "court": case_info.get("courtName", ""),
            "case_number": case_info.get("caseNo", ""),
        }
        
        # 提取被告人
        parties = wenshu_data.get("parties", [])
        defendants = []
        for party in parties:
            if party.get("role") in ["被告", "被告人", "被告单位"]:
                defendants.append({
                    "name": party.get("name", "未知"),
                    "gender": party.get("gender", ""),
                    "age": party.get("age", None),
                })
        if defendants:
            case["defendants"] = defendants
        
        # 提取罪名和判决
        judgments = wenshu_data.get("judgments", [])
        charges_judged = {}
        
        for i, judgment in enumerate(judgments):
            crime = judgment.get("crime", "未知罪名")
            article = judgment.get("article", "")
            sentence = judgment.get("sentence", "")
            
            charges_judged[f"c{i+1}"] = {
                "name": crime,
                "article": article,
                "sentence": sentence,
                "is_accurate": True,
            }
        
        if charges_judged:
            case["charges"] = {"charges_judged": charges_judged}
        
        return case
    
    def _csv_row_to_case(self, row: Dict) -> Optional[Dict]:
        """CSV行转换为案件格式"""
        try:
            case_id = row.get("case_id", row.get("案号", ""))
            if not case_id:
                return None
            
            case = {
                "case_id": str(case_id),
                "case_name": row.get("case_name", row.get("案件名称", "未知")),
                "case_type": row.get("case_type", row.get("案件类型", "刑事")),
                "judgment_date": row.get("judgment_date", row.get("判决日期", "")),
                "court": row.get("court", row.get("法院", "")),
            }
            
            # 被告人
            defendant = row.get("defendant", row.get("被告人", ""))
            if defendant:
                case["defendants"] = [defendant]
            
            # 罪名
            crime = row.get("crime", row.get("罪名", ""))
            if crime:
                case["charges"] = {
                    "charges_judged": {
                        "c1": {
                            "name": crime,
                            "is_accurate": True,
                        }
                    }
                }
            
            # 涉案金额
            amount = row.get("amount", row.get("涉案金额", ""))
            if amount:
                try:
                    case["charges"]["charges_judged"]["c1"]["amount"] = float(amount)
                except ValueError:
                    pass
            
            return case
            
        except Exception as e:
            self.errors.append(f"CSV行转换失败: {e}")
            return None
    
    def _dataframe_row_to_case(self, row) -> Optional[Dict]:
        """DataFrame行转换为案件格式"""
        try:
            case_id = str(row.get("case_id", row.get("案号", "")))
            if not case_id or case_id == "nan":
                return None
            
            case = {
                "case_id": case_id,
                "case_name": str(row.get("case_name", row.get("案件名称", "未知"))),
            }
            
            return case
            
        except Exception as e:
            self.errors.append(f"Excel行转换失败: {e}")
            return None
    
    def _save_case(self, case_data: Dict) -> bool:
        """保存案件数据"""
        try:
            # 验证必填字段
            if not case_data.get("case_id"):
                case_data["case_id"] = f"CASE-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
            
            case_id = case_data["case_id"]
            
            # 检查是否已存在
            existing_path = self.output_dir / f"{case_id}.yaml"
            if existing_path.exists():
                self.warnings.append(f"案件已存在，将覆盖: {case_id}")
            
            # 写入文件
            output_path = self.output_dir / f"{case_id}.yaml"
            with open(output_path, "w", encoding="utf-8") as f:
                yaml.dump(case_data, f, allow_unicode=True, default_flow_style=False)
            
            self.imported_ids.append(case_id)
            return True
            
        except Exception as e:
            self.errors.append(f"保存案件失败: {case_data.get('case_id', 'unknown')} - {e}")
            return False
    
    def validate_case(self, case_data: Dict) -> List[str]:
        """验证案件数据的完整性
        
        Args:
            case_data: 案件数据
            
        Returns:
            List[str]: 验证错误列表
        """
        errors = []
        
        # 必填字段检查
        if not case_data.get("case_id"):
            errors.append("缺少案件ID")
        
        # 被告人检查
        defendants = case_data.get("defendants", [])
        if not defendants:
            errors.append("缺少被告人信息")
        
        # 罪名检查
        charges = case_data.get("charges", {})
        if not charges:
            errors.append("缺少罪名信息")
        
        return errors
    
    def export_to_template(self, output_path: str = "case_template.yaml"):
        """导出案件模板
        
        Args:
            output_path: 输出路径
        """
        template = {
            "case_id": "CASE-EXAMPLE-001",
            "case_name": "示例案件",
            "case_type": "刑事案件",
            "judgment_date": "2024-01-01",
            "source": "示例来源",
            "court": "示例法院",
            "case_summary": "案件事实简述...",
            "defendants": [
                {
                    "name": "张三",
                    "gender": "男",
                    "age": 35,
                }
            ],
            "charges": {
                "charges_judged": {
                    "c1": {
                        "name": "盗窃罪",
                        "article": "刑法第264条",
                        "statute": "盗窃公私财物，数额较大的，处三年以下有期徒刑、拘役或者管制，并处或者单处罚金",
                        "amount": 50000,
                        "is_accurate": True,
                    }
                },
                "charges_missed": {}
            },
            # 可选字段
            "procedure": {
                "detention_date": "2024-01-01",
                "arrest_date": "2024-01-15",
                "prosecution_date": "2024-03-01",
                "trial_date": "2024-04-01",
            },
            "victims": [],
            "evidence": [],
            "notes": "备注信息",
        }
        
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(template, f, allow_unicode=True, default_flow_style=False)
        
        print(f"✅ 模板已导出: {output_path}")


def import_cases(file_path: str, output_dir: str = None) -> ImportResult:
    """便捷函数：导入案件
    
    Args:
        file_path: 文件或目录路径
        output_dir: 输出目录
        
    Returns:
        ImportResult: 导入结果
    """
    importer = CaseImporter(Path(output_dir) if output_dir else None)
    return importer.import_file(file_path)


if __name__ == "__main__":
    # 测试导入器
    print("=== 案件导入器测试 ===\n")
    
    importer = CaseImporter()
    
    # 导出模板
    importer.export_to_template("case_template.yaml")
    print()
    
    # 测试验证
    test_case = {
        "case_id": "TEST-001",
        "case_name": "测试案件",
        "defendants": [{"name": "测试被告"}],
        "charges": {
            "charges_judged": {
                "c1": {"name": "盗窃罪"}
            }
        }
    }
    
    errors = importer.validate_case(test_case)
    if errors:
        print(f"验证错误: {errors}")
    else:
        print("✅ 案件验证通过")
    
    print("\n=== 支持的文件格式 ===")
    for ext, fmt in importer.SUPPORTED_FORMATS.items():
        print(f"  {ext}: {fmt}")
