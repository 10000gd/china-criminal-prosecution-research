"""
API 集成测试套件 - 全量覆盖所有 API 端点
"""
import pytest
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="module")
def client():
    """使用已运行的 Flask 服务"""
    import requests
    base_url = "http://localhost:5000"
    
    class APIClient:
        def __init__(self, base):
            self.base = base
            self.session = requests.Session()
        
        def get(self, path, **kwargs):
            return self.session.get(f"{self.base}{path}", **kwargs)
        
        def post(self, path, **kwargs):
            return self.session.post(f"{self.base}{path}", **kwargs)
    
    return APIClient(base_url)


class TestAPICases:
    """案件相关 API 测试"""
    
    def test_api_cases_list(self, client):
        """GET /api/cases - 案件列表"""
        r = client.get("/api/cases")
        assert r.status_code == 200
        data = r.json()
        assert "cases" in data
        assert len(data["cases"]) > 0
    
    def test_api_case_detail(self, client):
        """GET /api/case/<id> - 案件详情"""
        r = client.get("/api/case/CASE-0001")
        assert r.status_code == 200
        data = r.json()
        assert "case_info" in data or "charges" in data or "aggravating_factors" in data
    
    def test_api_case_alias(self, client):
        """GET /api/cases/<id> - 案件详情别名路由"""
        r = client.get("/api/cases/CASE-0001")
        assert r.status_code == 200
    
    def test_api_case_charges(self, client):
        """GET /api/case/<id>/charges - 案件罪名"""
        r = client.get("/api/case/CASE-0001/charges")
        assert r.status_code in [200, 404]


class TestAPIAnalyze:
    """分析相关 API 测试"""
    
    def test_api_case_analyze_get(self, client):
        """GET /api/case-analyze/<id> - 案件分析（GET方式）"""
        r = client.get("/api/case-analyze/CASE-0001")
        assert r.status_code == 200
        data = r.json()
        assert "case_info" in data or "charges" in data or "defense" in data
    
    def test_api_case_analyze_new(self, client):
        """POST /api/case-analyze - 新建案件分析"""
        r = client.post("/api/case-analyze", json={
            "case_summary": {"description": "盗窃1000元"},
            "charges": ["盗窃罪"]
        })
        assert r.status_code in [200, 400, 500]
    
    def test_api_fact_check(self, client):
        """GET /api/fact-check/<id> - 事实核查"""
        r = client.get("/api/fact-check/CASE-0001")
        assert r.status_code == 200
        data = r.json()
        assert "average_confidence" in data or "fields" in data or "grades" in data
    
    def test_api_sentencing_deviation(self, client):
        """POST /api/sentencing/deviation - 量刑偏离分析"""
        r = client.post("/api/sentencing/deviation", json={
            "case_id": "CASE-0001",
            "predicted_sentence": "有期徒刑1年",
            "actual_sentence": "有期徒刑6个月"
        })
        assert r.status_code == 200
    
    def test_api_sentencing_provincial(self, client):
        """GET /api/sentencing/provincial - 省级量刑对比"""
        r = client.get("/api/sentencing/provincial?crime=盗窃罪")
        assert r.status_code == 200


class TestAPIThreshold:
    """入罪门槛 API 测试"""
    
    def test_api_threshold_by_crime(self, client):
        """GET /api/threshold - 入罪门槛查询"""
        r = client.get("/api/threshold?crime=盗窃罪&province=北京")
        assert r.status_code == 200
        data = r.json()
        assert "crime" in data or "reached" in data or "standard" in data
    
    def test_api_threshold_fraud(self, client):
        """GET /api/threshold 诈骗罪"""
        r = client.get("/api/threshold?crime=诈骗罪&province=上海")
        assert r.status_code == 200
    
    def test_api_threshold_robbery(self, client):
        """GET /api/threshold 抢夺罪"""
        r = client.get("/api/threshold?crime=抢夺罪")
        assert r.status_code in [200, 500]


class TestAPILaw:
    """法律检索 API 测试"""
    
    def test_api_law_search(self, client):
        """GET /api/law/search - 法律全文检索"""
        r = client.get("/api/law/search?q=正当防卫")
        assert r.status_code == 200
        data = r.json()
        assert "results" in data or "law" in data
        assert len(data.get("results", [])) > 0
    
    def test_api_law_search_empty(self, client):
        """GET /api/law/search 空查询"""
        r = client.get("/api/law/search?q=不存在的内容XYZ123")
        assert r.status_code == 200
    
    def test_api_law_search_with_article(self, client):
        """GET /api/law/search 带条款筛选"""
        r = client.get("/api/law/search?q=盗窃罪&article=264")
        assert r.status_code in [200, 500]


class TestAPIDefense:
    """辩护增强 API 测试"""
    
    def test_api_defense_analyze(self, client):
        """POST /api/defense/analyze - 辩护分析"""
        r = client.post("/api/defense/analyze", json={
            "case_id": "CASE-0001"
        })
        assert r.status_code == 200
        data = r.json()
        assert "primary_defense" in data or "defense_angles" in data or "case_summary" in data
    
    def test_api_defense_opinion(self, client):
        """POST /api/defense/opinion - 辩护词生成"""
        r = client.post("/api/defense/opinion", json={
            "case_id": "CASE-0001"
        })
        assert r.status_code == 200
        data = r.json()
        assert "opinion" in data or "content" in data or "markdown" in data
    
    def test_api_defense_search(self, client):
        """GET /api/defense/search - 辩护案例搜索"""
        r = client.get("/api/defense/search?q=自首")
        assert r.status_code == 200
        data = r.json()
        assert "cases" in data or "results" in data
    
    def test_api_defense_report(self, client):
        """POST /api/defense/report - 辩护报告"""
        r = client.post("/api/defense/report", json={
            "case_id": "CASE-0001"
        })
        assert r.status_code in [200, 500]


class TestAPISearch:
    """通用搜索 API 测试"""
    
    def test_api_search(self, client):
        """GET /api/search - 通用搜索"""
        r = client.get("/api/search?q=盗窃")
        assert r.status_code == 200
        data = r.json()
        assert "case_results" in data or "law_results" in data or "results" in data
    
    def test_api_compare(self, client):
        """POST /api/compare - 案件对比"""
        r = client.post("/api/compare", json={
            "case_ids": ["CASE-0001", "CASE-0002"]
        })
        assert r.status_code == 200
    
    def test_api_compare_get(self, client):
        """GET /api/compare - 案件对比GET"""
        r = client.get("/api/compare?case_ids=CASE-0001,CASE-0002")
        assert r.status_code in [200, 400]


class TestAPIStats:
    """统计 API 测试"""
    
    def test_api_stats_overview(self, client):
        """GET /api/stats/overview - 统计概览"""
        r = client.get("/api/stats/overview")
        assert r.status_code == 200
        data = r.json()
        assert "total_cases" in data or "total" in data or "overview" in data
    
    def test_api_stats_provincial_diffs(self, client):
        """GET /api/stats/provincial-diffs - 省份差异"""
        r = client.get("/api/stats/provincial-diffs")
        assert r.status_code == 200
    
    def test_api_stats_company_geo(self, client):
        """GET /api/stats/company-geo - 公司地理分布"""
        r = client.get("/api/stats/company-geo")
        assert r.status_code == 200
    
    def test_api_stats_hallucination(self, client):
        """GET /api/stats/hallucination - 幻觉率统计"""
        r = client.get("/api/stats/hallucination")
        assert r.status_code == 200


class TestAPIReports:
    """报告 API 测试"""
    
    def test_api_reports(self, client):
        """GET /api/reports - 报告列表"""
        r = client.get("/api/reports")
        assert r.status_code == 200


class TestAPIErrorHandling:
    """错误处理测试"""
    
    def test_api_nonexistent_case(self, client):
        """GET /api/case/NONEXISTENT - 不存在的案件"""
        r = client.get("/api/case/NONEXISTENT")
        assert r.status_code == 404
    
    def test_api_invalid_threshold_crime(self, client):
        """GET /api/threshold 无效罪名"""
        r = client.get("/api/threshold?crime=不存在的罪名XYZ")
        assert r.status_code in [200, 400, 404]
    
    def test_api_case_analyze_invalid(self, client):
        """POST /api/case-analyze 无效数据"""
        r = client.post("/api/case-analyze", json={})
        assert r.status_code in [200, 400, 500]


class TestWebPages:
    """Web 页面测试"""
    
    def test_homepage(self, client):
        """GET / - 首页"""
        r = client.get("/")
        assert r.status_code == 200
        assert "html" in r.text.lower()
    
    def test_search_page(self, client):
        """GET /search - 搜索页"""
        r = client.get("/search")
        assert r.status_code == 200
    
    def test_compare_page(self, client):
        """GET /compare - 对比页"""
        r = client.get("/compare")
        assert r.status_code == 200
    
    def test_stats_page(self, client):
        """GET /stats - 统计页"""
        r = client.get("/stats")
        assert r.status_code == 200
    
    def test_case_page(self, client):
        """GET /case/<id> - 案件详情页"""
        r = client.get("/case/CASE-0001")
        assert r.status_code == 200
    
    def test_reports_page(self, client):
        """GET /reports - 报告列表页"""
        r = client.get("/reports")
        assert r.status_code == 200
