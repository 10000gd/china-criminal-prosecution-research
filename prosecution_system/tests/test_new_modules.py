# -*- coding: utf-8 -*-
"""
新模块测试 - tests/test_new_modules.py

测试新增的模块：
- case_importer
- sentencing_cases
- sentencing_consistency
- defense_case_db (扩展部分)
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from case_importer import CaseImporter, CaseImporter as Importer
from sentencing_cases import get_sentencing_cases, get_cases_by_crime, get_statistics
from sentencing_consistency import (
    SentencingConsistencyAnalyzer,
    analyze_sentencing,
    get_sentencing_report
)
from defense_case_db import DefenseCaseDatabase


class TestCaseImporter:
    """案件导入器测试"""
    
    def test_importer_initializes(self):
        importer = Importer()
        assert importer is not None
        assert len(importer.SUPPORTED_FORMATS) >= 4
    
    def test_supported_formats(self):
        importer = Importer()
        assert ".yaml" in importer.SUPPORTED_FORMATS
        assert ".json" in importer.SUPPORTED_FORMATS
        assert ".csv" in importer.SUPPORTED_FORMATS
    
    def test_validate_case_valid(self):
        importer = Importer()
        case = {
            "case_id": "TEST-001",
            "defendants": [{"name": "张三"}],
            "charges": {"charges_judged": {"c1": {"name": "盗窃罪"}}}
        }
        errors = importer.validate_case(case)
        assert len(errors) == 0
    
    def test_validate_case_missing_fields(self):
        importer = Importer()
        case = {"case_name": "测试"}
        errors = importer.validate_case(case)
        assert len(errors) > 0
    
    def test_import_nonexistent_file(self):
        importer = Importer()
        result = importer.import_file("/nonexistent/file.yaml")
        assert result.success is False
        assert result.failed >= 1


class TestSentencingCases:
    """量刑案例库测试"""
    
    def test_get_all_cases(self):
        cases = get_sentencing_cases()
        assert len(cases) >= 50  # 至少50个案例
    
    def test_get_cases_by_crime(self):
        theft_cases = get_cases_by_crime("盗窃罪")
        assert len(theft_cases) >= 5
        assert all(c["crime"] == "盗窃罪" for c in theft_cases)
    
    def test_get_statistics(self):
        stats = get_statistics()
        assert stats["total_count"] >= 50
        assert "crimes" in stats
        assert "provinces" in stats
        assert len(stats["crimes"]) >= 5  # 至少5种罪名
    
    def test_cases_have_required_fields(self):
        cases = get_sentencing_cases()
        for case in cases[:5]:
            assert "case_id" in case
            assert "crime" in case
            assert "province" in case
            assert "sentence_years" in case or "sentence_months" in case


class TestSentencingConsistency:
    """量刑一致性分析测试"""
    
    def test_analyzer_initializes(self):
        analyzer = SentencingConsistencyAnalyzer()
        assert analyzer is not None
        assert len(analyzer._records) >= 50
    
    def test_get_stats_by_crime(self):
        analyzer = SentencingConsistencyAnalyzer()
        stats = analyzer.get_stats_by_crime("盗窃罪")
        assert stats.sample_count >= 5
        assert stats.avg_sentence is not None
        assert stats.avg_sentence > 0
    
    def test_get_provincial_comparison(self):
        analyzer = SentencingConsistencyAnalyzer()
        comparison = analyzer.get_provincial_comparison("盗窃罪")
        assert len(comparison) >= 5
        for province, data in comparison.items():
            assert "avg_sentence" in data
            assert "deviation_type" in data
    
    def test_analyze_deviation(self):
        case_data = {
            "case_id": "TEST-001",
            "crime": "盗窃罪",
            "sentence_years": 2.0,
            "province": "北京",
            "is_自首": True,
        }
        result = analyze_sentencing(case_data)
        assert "deviation_score" in result
        assert "deviation_type" in result
        assert result["deviation_type"] in ["偏重", "偏轻", "正常"]
    
    def test_generate_report(self):
        report = get_sentencing_report()
        assert "generated_at" in report
        assert "crime_stats" in report
        assert "provincial_comparison" in report
        assert "summary" in report
    
    def test_legal_comparison(self):
        analyzer = SentencingConsistencyAnalyzer()
        comparison = analyzer.get_legal_comparison("盗窃罪")
        assert "legal_range" in comparison
        assert "actual_stats" in comparison


class TestDefenseCaseDatabase:
    """辩护案例库测试（扩展部分）"""
    
    def test_database_initializes(self):
        db = DefenseCaseDatabase()
        assert db is not None
        assert len(db._cases) >= 15  # 扩充后至少15个
    
    def test_search_by_defense(self):
        db = DefenseCaseDatabase()
        result = db.search_by_defense("正当防卫", limit=5)
        assert result.total >= 2
        assert all("正当防卫" in c.key_defense for c in result.cases)
    
    def test_search_by_crime(self):
        db = DefenseCaseDatabase()
        result = db.search_by_crime("盗窃罪", "innocent", limit=5)
        assert result.total >= 1
    
    def test_get_defense_strategies(self):
        db = DefenseCaseDatabase()
        strategies = db.get_defense_strategies("盗窃罪")
        assert strategies is not None
    
    def test_case_outcome_types(self):
        """验证案例结果类型分布"""
        db = DefenseCaseDatabase()
        outcome_types = set(c.outcome_type for c in db._cases)
        assert "innocent" in outcome_types or "mitigated" in outcome_types


class TestIntegration:
    """集成测试"""
    
    def test_full_sentencing_workflow(self):
        """完整量刑分析工作流"""
        # 1. 获取统计
        stats = get_statistics()
        assert stats["total_count"] >= 50
        
        # 2. 分析器初始化
        analyzer = SentencingConsistencyAnalyzer()
        assert len(analyzer._records) >= 50
        
        # 3. 生成报告
        report = get_sentencing_report()
        assert len(report["summary"]) > 0
        
        # 4. 分析偏离度
        deviation = analyze_sentencing({
            "case_id": "TEST-001",
            "crime": "盗窃罪",
            "sentence_years": 1.5,
            "is_自首": True,
        })
        assert deviation["deviation_score"] >= 0
    
    def test_full_defense_workflow(self):
        """完整辩护分析工作流"""
        # 1. 搜索辩护案例
        db = DefenseCaseDatabase()
        result = db.search_by_defense("正当防卫")
        assert result.total >= 1
        
        # 2. 获取辩护策略
        strategies = db.get_defense_strategies("盗窃罪")
        assert strategies is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
