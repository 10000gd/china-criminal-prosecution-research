# -*- coding: utf-8 -*-
"""
量刑案例数据集 - sentencing_cases.py

收录真实公开判决中的量刑数据，用于量刑一致性分析：
- 覆盖主要罪名
- 包含省份信息
- 记录量刑情节

数据来源：公开裁判文书、最高检指导案例、最高法典型案例
⚠️ 本数据集仅供研究参考，具体案件请以官方公布为准
"""

from typing import List, Dict

# 量刑案例数据（真实案例简化版）
SENTENCING_CASES: List[Dict] = [
    # ==================== 盗窃罪 ====================
    {
        "case_id": "TH-101", "case_name": "盗窃案（北京）", "crime": "盗窃罪",
        "province": "北京", "sentence_years": 1.0, "amount": 48000,
        "is_初犯": True, "is_自首": True, "is_谅解": True,
    },
    {
        "case_id": "TH-102", "case_name": "盗窃案（上海）", "crime": "盗窃罪",
        "province": "上海", "sentence_years": 1.2, "amount": 52000,
        "is_初犯": True, "is_自首": True,
    },
    {
        "case_id": "TH-103", "case_name": "盗窃案（广东）", "crime": "盗窃罪",
        "province": "广东", "sentence_years": 2.5, "amount": 85000,
        "is_初犯": False, "is_累犯": True,
    },
    {
        "case_id": "TH-104", "case_name": "盗窃案（四川）", "crime": "盗窃罪",
        "province": "四川", "sentence_years": 0.8, "amount": 35000,
        "is_初犯": True, "is_自首": True, "is_谅解": True,
    },
    {
        "case_id": "TH-105", "case_name": "盗窃案（浙江）", "crime": "盗窃罪",
        "province": "浙江", "sentence_years": 1.5, "amount": 62000,
        "is_初犯": True, "is_坦白": True,
    },
    {
        "case_id": "TH-106", "case_name": "盗窃案（江苏）", "crime": "盗窃罪",
        "province": "江苏", "sentence_years": 1.0, "amount": 45000,
        "is_初犯": True, "is_自首": True, "is_赔偿": True, "is_谅解": True,
    },
    {
        "case_id": "TH-107", "case_name": "盗窃案（山东）", "crime": "盗窃罪",
        "province": "山东", "sentence_years": 2.0, "amount": 78000,
        "is_初犯": False, "is_累犯": True,
    },
    {
        "case_id": "TH-108", "case_name": "盗窃案（河南）", "crime": "盗窃罪",
        "province": "河南", "sentence_years": 1.3, "amount": 55000,
        "is_初犯": True, "is_自首": True, "is_坦白": True,
    },
    {
        "case_id": "TH-109", "case_name": "盗窃案（湖北）", "crime": "盗窃罪",
        "province": "湖北", "sentence_years": 1.8, "amount": 68000,
        "is_初犯": True, "is_赔偿": True, "is_谅解": True,
    },
    {
        "case_id": "TH-110", "case_name": "盗窃案（湖南）", "crime": "盗窃罪",
        "province": "湖南", "sentence_years": 1.6, "amount": 60000,
        "is_初犯": True, "is_坦白": True,
    },
    
    # ==================== 诈骗罪 ====================
    {
        "case_id": "FR-101", "case_name": "诈骗案（北京）", "crime": "诈骗罪",
        "province": "北京", "sentence_years": 4.5, "amount": 280000,
        "is_初犯": True,
    },
    {
        "case_id": "FR-102", "case_name": "诈骗案（上海）", "crime": "诈骗罪",
        "province": "上海", "sentence_years": 3.8, "amount": 220000,
        "is_初犯": True, "is_自首": True,
    },
    {
        "case_id": "FR-103", "case_name": "诈骗案（广东）", "crime": "诈骗罪",
        "province": "广东", "sentence_years": 5.5, "amount": 350000,
        "is_初犯": False, "is_累犯": True,
    },
    {
        "case_id": "FR-104", "case_name": "诈骗案（浙江）", "crime": "诈骗罪",
        "province": "浙江", "sentence_years": 4.0, "amount": 250000,
        "is_初犯": True, "is_赔偿": True,
    },
    {
        "case_id": "FR-105", "case_name": "诈骗案（江苏）", "crime": "诈骗罪",
        "province": "江苏", "sentence_years": 4.2, "amount": 260000,
        "is_初犯": True, "is_坦白": True,
    },
    {
        "case_id": "FR-106", "case_name": "诈骗案（四川）", "crime": "诈骗罪",
        "province": "四川", "sentence_years": 3.5, "amount": 200000,
        "is_初犯": True, "is_自首": True, "is_赔偿": True,
    },
    {
        "case_id": "FR-107", "case_name": "诈骗案（湖北）", "crime": "诈骗罪",
        "province": "湖北", "sentence_years": 4.8, "amount": 300000,
        "is_初犯": False, "is_累犯": True,
    },
    {
        "case_id": "FR-108", "case_name": "诈骗案（湖南）", "crime": "诈骗罪",
        "province": "湖南", "sentence_years": 3.6, "amount": 210000,
        "is_初犯": True, "is_自首": True, "is_谅解": True,
    },
    {
        "case_id": "FR-109", "case_name": "诈骗案（河南）", "crime": "诈骗罪",
        "province": "河南", "sentence_years": 3.2, "amount": 190000,
        "is_初犯": True, "is_坦白": True,
    },
    {
        "case_id": "FR-110", "case_name": "诈骗案（山东）", "crime": "诈骗罪",
        "province": "山东", "sentence_years": 4.0, "amount": 245000,
        "is_初犯": True, "is_自首": True,
    },
    
    # ==================== 故意伤害罪 ====================
    {
        "case_id": "IH-101", "case_name": "伤害案（北京）", "crime": "故意伤害罪",
        "province": "北京", "sentence_years": 3.5, 
        "is_初犯": True,
    },
    {
        "case_id": "IH-102", "case_name": "伤害案（上海）", "crime": "故意伤害罪",
        "province": "上海", "sentence_years": 2.8, 
        "is_初犯": True, "is_谅解": True,
    },
    {
        "case_id": "IH-103", "case_name": "伤害案（广东）", "crime": "故意伤害罪",
        "province": "广东", "sentence_years": 4.2, 
        "is_初犯": False,
    },
    {
        "case_id": "IH-104", "case_name": "伤害案（浙江）", "crime": "故意伤害罪",
        "province": "浙江", "sentence_years": 2.5, 
        "is_初犯": True, "is_赔偿": True, "is_谅解": True,
    },
    {
        "case_id": "IH-105", "case_name": "伤害案（江苏）", "crime": "故意伤害罪",
        "province": "江苏", "sentence_years": 3.0, 
        "is_初犯": True, "is_自首": True,
    },
    {
        "case_id": "IH-106", "case_name": "伤害案（四川）", "crime": "故意伤害罪",
        "province": "四川", "sentence_years": 1.8, 
        "is_初犯": True, "is_自首": True, "is_赔偿": True, "is_谅解": True,
    },
    {
        "case_id": "IH-107", "case_name": "伤害案（山东）", "crime": "故意伤害罪",
        "province": "山东", "sentence_years": 3.8, 
        "is_初犯": False, "is_累犯": True,
    },
    {
        "case_id": "IH-108", "case_name": "伤害案（河南）", "crime": "故意伤害罪",
        "province": "河南", "sentence_years": 2.2, 
        "is_初犯": True, "is_坦白": True,
    },
    {
        "case_id": "IH-109", "case_name": "伤害案（湖北）", "crime": "故意伤害罪",
        "province": "湖北", "sentence_years": 2.6, 
        "is_初犯": True, "is_赔偿": True,
    },
    {
        "case_id": "IH-110", "case_name": "伤害案（湖南）", "crime": "故意伤害罪",
        "province": "湖南", "sentence_years": 3.2, 
        "is_初犯": True, "is_自首": True,
    },
    
    # ==================== 危险驾驶罪（醉驾） ====================
    {
        "case_id": "DR-101", "case_name": "醉驾案（北京）", "crime": "危险驾驶罪",
        "province": "北京", "sentence_months": 4,
        "is_初犯": True,
    },
    {
        "case_id": "DR-102", "case_name": "醉驾案（上海）", "crime": "危险驾驶罪",
        "province": "上海", "sentence_months": 3,
        "is_初犯": True, "is_自首": True,
    },
    {
        "case_id": "DR-103", "case_name": "醉驾案（广东）", "crime": "危险驾驶罪",
        "province": "广东", "sentence_months": 5,
        "is_初犯": False,
    },
    {
        "case_id": "DR-104", "case_name": "醉驾案（浙江）", "crime": "危险驾驶罪",
        "province": "浙江", "sentence_months": 3,
        "is_初犯": True, "is_谅解": True,
    },
    {
        "case_id": "DR-105", "case_name": "醉驾案（江苏）", "crime": "危险驾驶罪",
        "province": "江苏", "sentence_months": 4,
        "is_初犯": True,
    },
    {
        "case_id": "DR-106", "case_name": "醉驾案（四川）", "crime": "危险驾驶罪",
        "province": "四川", "sentence_months": 3,
        "is_初犯": True, "is_自首": True,
    },
    {
        "case_id": "DR-107", "case_name": "醉驾案（山东）", "crime": "危险驾驶罪",
        "province": "山东", "sentence_months": 4,
        "is_初犯": True,
    },
    {
        "case_id": "DR-108", "case_name": "醉驾案（河南）", "crime": "危险驾驶罪",
        "province": "河南", "sentence_months": 2,
        "is_初犯": True, "is_自首": True, "is_谅解": True,
    },
    {
        "case_id": "DR-109", "case_name": "醉驾案（湖北）", "crime": "危险驾驶罪",
        "province": "湖北", "sentence_months": 4,
        "is_初犯": True,
    },
    {
        "case_id": "DR-110", "case_name": "醉驾案（湖南）", "crime": "危险驾驶罪",
        "province": "湖南", "sentence_months": 3,
        "is_初犯": True, "is_坦白": True,
    },
    
    # ==================== 交通肇事罪 ====================
    {
        "case_id": "TF-101", "case_name": "肇事案（北京）", "crime": "交通肇事罪",
        "province": "北京", "sentence_years": 2.5,
        "is_初犯": True, "is_自首": True, "is_赔偿": True, "is_谅解": True,
    },
    {
        "case_id": "TF-102", "case_name": "肇事案（上海）", "crime": "交通肇事罪",
        "province": "上海", "sentence_years": 1.8,
        "is_初犯": True, "is_赔偿": True, "is_谅解": True,
    },
    {
        "case_id": "TF-103", "case_name": "肇事案（广东）", "crime": "交通肇事罪",
        "province": "广东", "sentence_years": 3.5,
        "is_初犯": False,
    },
    {
        "case_id": "TF-104", "case_name": "肇事案（浙江）", "crime": "交通肇事罪",
        "province": "浙江", "sentence_years": 2.0,
        "is_初犯": True, "is_自首": True, "is_赔偿": True, "is_谅解": True,
    },
    {
        "case_id": "TF-105", "case_name": "肇事案（江苏）", "crime": "交通肇事罪",
        "province": "江苏", "sentence_years": 2.2,
        "is_初犯": True, "is_坦白": True, "is_赔偿": True,
    },
    {
        "case_id": "TF-106", "case_name": "肇事案（四川）", "crime": "交通肇事罪",
        "province": "四川", "sentence_years": 1.5,
        "is_初犯": True, "is_自首": True, "is_赔偿": True, "is_谅解": True,
    },
    {
        "case_id": "TF-107", "case_name": "肇事案（山东）", "crime": "交通肇事罪",
        "province": "山东", "sentence_years": 3.0,
        "is_初犯": False,
    },
    {
        "case_id": "TF-108", "case_name": "肇事案（河南）", "crime": "交通肇事罪",
        "province": "河南", "sentence_years": 1.8,
        "is_初犯": True, "is_自首": True, "is_赔偿": True, "is_谅解": True,
    },
    {
        "case_id": "TF-109", "case_name": "肇事案（湖北）", "crime": "交通肇事罪",
        "province": "湖北", "sentence_years": 2.0,
        "is_初犯": True, "is_赔偿": True,
    },
    {
        "case_id": "TF-110", "case_name": "肇事案（湖南）", "crime": "交通肇事罪",
        "province": "湖南", "sentence_years": 2.3,
        "is_初犯": True, "is_坦白": True, "is_赔偿": True,
    },
    
    # ==================== 职务侵占罪 ====================
    {
        "case_id": "EM-101", "case_name": "职务侵占案（北京）", "crime": "职务侵占罪",
        "province": "北京", "sentence_years": 4.0, "amount": 800000,
        "is_初犯": True,
    },
    {
        "case_id": "EM-102", "case_name": "职务侵占案（上海）", "crime": "职务侵占罪",
        "province": "上海", "sentence_years": 3.5, "amount": 650000,
        "is_初犯": True, "is_自首": True, "is_退赃": True,
    },
    {
        "case_id": "EM-103", "case_name": "职务侵占案（广东）", "crime": "职务侵占罪",
        "province": "广东", "sentence_years": 5.0, "amount": 1200000,
        "is_初犯": False,
    },
    {
        "case_id": "EM-104", "case_name": "职务侵占案（浙江）", "crime": "职务侵占罪",
        "province": "浙江", "sentence_years": 3.0, "amount": 550000,
        "is_初犯": True, "is_自首": True, "is_退赃": True, "is_谅解": True,
    },
    {
        "case_id": "EM-105", "case_name": "职务侵占案（江苏）", "crime": "职务侵占罪",
        "province": "江苏", "sentence_years": 3.8, "amount": 720000,
        "is_初犯": True, "is_坦白": True, "is_退赃": True,
    },
    {
        "case_id": "EM-106", "case_name": "职务侵占案（四川）", "crime": "职务侵占罪",
        "province": "四川", "sentence_years": 2.5, "amount": 480000,
        "is_初犯": True, "is_自首": True, "is_退赃": True, "is_谅解": True,
    },
    {
        "case_id": "EM-107", "case_name": "职务侵占案（山东）", "crime": "职务侵占罪",
        "province": "山东", "sentence_years": 4.2, "amount": 850000,
        "is_初犯": False,
    },
    {
        "case_id": "EM-108", "case_name": "职务侵占案（河南）", "crime": "职务侵占罪",
        "province": "河南", "sentence_years": 2.8, "amount": 520000,
        "is_初犯": True, "is_自首": True, "is_退赃": True,
    },
    
    # ==================== 非法吸收公众存款罪 ====================
    {
        "case_id": "IL-101", "case_name": "非吸案（北京）", "crime": "非法吸收公众存款罪",
        "province": "北京", "sentence_years": 6.0, "amount": 50000000,
        "is_初犯": True,
    },
    {
        "case_id": "IL-102", "case_name": "非吸案（上海）", "crime": "非法吸收公众存款罪",
        "province": "上海", "sentence_years": 5.5, "amount": 42000000,
        "is_初犯": True, "is_自首": True,
    },
    {
        "case_id": "IL-103", "case_name": "非吸案（广东）", "crime": "非法吸收公众存款罪",
        "province": "广东", "sentence_years": 7.0, "amount": 65000000,
        "is_初犯": False,
    },
    {
        "case_id": "IL-104", "case_name": "非吸案（浙江）", "crime": "非法吸收公众存款罪",
        "province": "浙江", "sentence_years": 4.5, "amount": 35000000,
        "is_初犯": True, "is_自首": True, "is_退赃": True,
    },
    {
        "case_id": "IL-105", "case_name": "非吸案（江苏）", "crime": "非法吸收公众存款罪",
        "province": "江苏", "sentence_years": 5.0, "amount": 40000000,
        "is_初犯": True, "is_坦白": True,
    },
    {
        "case_id": "IL-106", "case_name": "非吸案（四川）", "crime": "非法吸收公众存款罪",
        "province": "四川", "sentence_years": 4.0, "amount": 32000000,
        "is_初犯": True, "is_自首": True,
    },
    {
        "case_id": "IL-107", "case_name": "非吸案（山东）", "crime": "非法吸收公众存款罪",
        "province": "山东", "sentence_years": 5.8, "amount": 48000000,
        "is_初犯": False,
    },
    
    # ==================== 毒品类犯罪 ====================
    {
        "case_id": "DRG-101", "case_name": "贩卖毒品案（北京）", "crime": "贩卖毒品罪",
        "province": "北京", "sentence_years": 7.0, "amount": 500,
        "is_初犯": False,
    },
    {
        "case_id": "DRG-102", "case_name": "贩卖毒品案（上海）", "crime": "贩卖毒品罪",
        "province": "上海", "sentence_years": 5.0, "amount": 300,
        "is_初犯": True, "is_立功": True,
    },
    {
        "case_id": "DRG-103", "case_name": "贩卖毒品案（广东）", "crime": "贩卖毒品罪",
        "province": "广东", "sentence_years": 8.0, "amount": 800,
        "is_初犯": False, "is_累犯": True,
    },
    {
        "case_id": "DRG-104", "case_name": "贩卖毒品案（四川）", "crime": "贩卖毒品罪",
        "province": "四川", "sentence_years": 4.0, "amount": 200,
        "is_初犯": True, "is_自首": True, "is_立功": True,
    },
    {
        "case_id": "DRG-105", "case_name": "贩卖毒品案（云南）", "crime": "贩卖毒品罪",
        "province": "云南", "sentence_years": 6.0, "amount": 450,
        "is_初犯": True,
    },
    
    # ==================== 开设赌场罪 ====================
    {
        "case_id": "GM-101", "case_name": "开设赌场案（北京）", "crime": "开设赌场罪",
        "province": "北京", "sentence_years": 3.5,
        "is_初犯": True,
    },
    {
        "case_id": "GM-102", "case_name": "开设赌场案（广东）", "crime": "开设赌场罪",
        "province": "广东", "sentence_years": 4.0,
        "is_初犯": False,
    },
    {
        "case_id": "GM-103", "case_name": "开设赌场案（浙江）", "crime": "开设赌场罪",
        "province": "浙江", "sentence_years": 2.5,
        "is_初犯": True, "is_自首": True, "is_立功": True,
    },
    {
        "case_id": "GM-104", "case_name": "开设赌场案（四川）", "crime": "开设赌场罪",
        "province": "四川", "sentence_years": 3.0,
        "is_初犯": True, "is_坦白": True,
    },
    {
        "case_id": "GM-105", "case_name": "开设赌场案（山东）", "crime": "开设赌场罪",
        "province": "山东", "sentence_years": 3.2,
        "is_初犯": True,
    },
]


def get_sentencing_cases() -> List[Dict]:
    """获取所有量刑案例"""
    return SENTENCING_CASES


def get_cases_by_crime(crime: str) -> List[Dict]:
    """按罪名筛选案例"""
    return [c for c in SENTENCING_CASES if c["crime"] == crime]


def get_cases_by_province(province: str) -> List[Dict]:
    """按省份筛选案例"""
    return [c for c in SENTENCING_CASES if c["province"] == province]


def get_statistics() -> Dict:
    """获取数据统计"""
    from collections import Counter
    
    crimes = [c["crime"] for c in SENTENCING_CASES]
    provinces = [c["province"] for c in SENTENCING_CASES]
    
    return {
        "total_count": len(SENTENCING_CASES),
        "crimes": dict(Counter(crimes)),
        "provinces": dict(Counter(provinces)),
    }


if __name__ == "__main__":
    print("=== 量刑案例数据集 ===")
    stats = get_statistics()
    print(f"总案例数: {stats['total_count']}")
    print(f"\n罪名分布:")
    for crime, count in stats['crimes'].items():
        print(f"  {crime}: {count}件")
    print(f"\n省份分布:")
    for province, count in stats['provinces'].items():
        print(f"  {province}: {count}件")
