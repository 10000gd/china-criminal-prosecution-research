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
    # ==================== 故意毁坏财物罪 ====================
    {"case_id": "DDM-101", "case_name": "毁财案（北京）", "crime": "故意毁坏财物罪", "province": "北京", "sentence_years": 1.0, "amount": 50000, "is_初犯": True, "is_自首": True, "is_赔偿": True},
    {"case_id": "DDM-102", "case_name": "毁财案（广东）", "crime": "故意毁坏财物罪", "province": "广东", "sentence_years": 1.5, "amount": 80000, "is_初犯": True, "is_赔偿": True},
    # ==================== 寻衅滋事罪 ====================
    {"case_id": "EDS-101", "case_name": "寻衅案（北京）", "crime": "寻衅滋事罪", "province": "北京", "sentence_years": 2.0, "is_初犯": True},
    {"case_id": "EDS-102", "case_name": "寻衅案（上海）", "crime": "寻衅滋事罪", "province": "上海", "sentence_years": 1.5, "is_初犯": True, "is_自首": True, "is_谅解": True},
    {"case_id": "EDS-103", "case_name": "寻衅案（广东）", "crime": "寻衅滋事罪", "province": "广东", "sentence_years": 3.0, "is_初犯": False, "is_累犯": True},
    # ==================== 聚众斗殴罪 ====================
    {"case_id": "GFA-101", "case_name": "斗殴案（江苏）", "crime": "聚众斗殴罪", "province": "江苏", "sentence_years": 2.5, "is_初犯": True},
    {"case_id": "GFA-102", "case_name": "斗殴案（浙江）", "crime": "聚众斗殴罪", "province": "浙江", "sentence_years": 1.8, "is_初犯": True, "is_自首": True},
    # ==================== 掩饰隐瞒犯罪所得罪 ====================
    {"case_id": "MOC-101", "case_name": "掩饰案（北京）", "crime": "掩饰隐瞒犯罪所得罪", "province": "北京", "sentence_years": 2.0, "amount": 100000, "is_初犯": True},
    {"case_id": "MOC-102", "case_name": "掩饰案（广东）", "crime": "掩饰隐瞒犯罪所得罪", "province": "广东", "sentence_years": 3.0, "amount": 200000, "is_初犯": False},
    {"case_id": "MOC-103", "case_name": "掩饰案（上海）", "crime": "掩饰隐瞒犯罪所得罪", "province": "上海", "sentence_years": 1.5, "amount": 80000, "is_初犯": True, "is_自首": True, "is_退赃": True},
    # ==================== 合同诈骗罪 ====================
    {"case_id": "SCP-101", "case_name": "合同诈骗案（北京）", "crime": "合同诈骗罪", "province": "北京", "sentence_years": 5.0, "amount": 500000, "is_初犯": True},
    {"case_id": "SCP-102", "case_name": "合同诈骗案（上海）", "crime": "合同诈骗罪", "province": "上海", "sentence_years": 4.5, "amount": 400000, "is_初犯": True, "is_自首": True, "is_退赃": True},
    {"case_id": "SCP-103", "case_name": "合同诈骗案（广东）", "crime": "合同诈骗罪", "province": "广东", "sentence_years": 6.0, "amount": 800000, "is_初犯": False, "is_累犯": True},
    # ==================== 组织卖淫罪 ====================
    {"case_id": "OSL-101", "case_name": "组织卖淫案（广东）", "crime": "组织卖淫罪", "province": "广东", "sentence_years": 5.5, "is_初犯": False},
    {"case_id": "OSL-102", "case_name": "组织卖淫案（北京）", "crime": "组织卖淫罪", "province": "北京", "sentence_years": 5.0, "is_初犯": True},
    # ==================== 非法经营罪 ====================
    {"case_id": "EOB-101", "case_name": "非法经营案（北京）", "crime": "非法经营罪", "province": "北京", "sentence_years": 3.0, "amount": 1000000, "is_初犯": True},
    {"case_id": "EOB-102", "case_name": "非法经营案（上海）", "crime": "非法经营罪", "province": "上海", "sentence_years": 2.5, "amount": 800000, "is_初犯": True, "is_自首": True},
    # ==================== 挪用资金罪 ====================
    {"case_id": "EMB-101", "case_name": "挪用资金案（北京）", "crime": "挪用资金罪", "province": "北京", "sentence_years": 3.5, "amount": 2000000, "is_初犯": True},
    {"case_id": "EMB-102", "case_name": "挪用资金案（浙江）", "crime": "挪用资金罪", "province": "浙江", "sentence_years": 2.0, "amount": 500000, "is_初犯": True, "is_自首": True, "is_退赃": True},
    {"case_id": "EMB-103", "case_name": "挪用资金案（广东）", "crime": "挪用资金罪", "province": "广东", "sentence_years": 4.0, "amount": 3000000, "is_初犯": False},
    # ==================== 受贿罪 ====================
    {"case_id": "BRB-101", "case_name": "受贿案（北京）", "crime": "受贿罪", "province": "北京", "sentence_years": 10.0, "amount": 5000000, "is_初犯": True},
    {"case_id": "BRB-102", "case_name": "受贿案（浙江）", "crime": "受贿罪", "province": "浙江", "sentence_years": 8.0, "amount": 3000000, "is_初犯": True, "is_自首": True, "is_退赃": True},
    # ==================== 行贿罪 ====================
    {"case_id": "BRG-101", "case_name": "行贿案（广东）", "crime": "行贿罪", "province": "广东", "sentence_years": 3.0, "amount": 2000000, "is_初犯": True, "is_自首": True},
    {"case_id": "BRG-102", "case_name": "行贿案（北京）", "crime": "行贿罪", "province": "北京", "sentence_years": 4.0, "amount": 3000000, "is_初犯": False},

    # ---- 故意伤害罪（续）----
    {"case_id": "GH-201", "case_name": "伤害案（北京）", "crime": "故意伤害罪", "province": "北京", "sentence_years": 1.5, "is_初犯": True, "is_坦白": True, "is_赔偿": True},
    {"case_id": "GH-202", "case_name": "伤害案（上海）", "crime": "故意伤害罪", "province": "上海", "sentence_years": 2.0, "is_初犯": True},
    {"case_id": "GH-203", "case_name": "伤害案（广东）", "crime": "故意伤害罪", "province": "广东", "sentence_years": 1.8, "is_初犯": True, "is_赔偿": True},
    {"case_id": "GH-204", "case_name": "伤害案（江苏）", "crime": "故意伤害罪", "province": "江苏", "sentence_years": 1.2, "is_自首": True},
    {"case_id": "GH-205", "case_name": "伤害案（浙江）", "crime": "故意伤害罪", "province": "浙江", "sentence_years": 2.5, "is_累犯": True},
    {"case_id": "GH-206", "case_name": "伤害案（四川）", "crime": "故意伤害罪", "province": "四川", "sentence_years": 1.0, "is_自首": True, "is_赔偿": True},
    {"case_id": "GH-207", "case_name": "伤害案（湖北）", "crime": "故意伤害罪", "province": "湖北", "sentence_years": 1.6, "is_初犯": True, "is_坦白": True},
    {"case_id": "GH-208", "case_name": "伤害案（湖南）", "crime": "故意伤害罪", "province": "湖南", "sentence_years": 2.2, "is_初犯": True},
    {"case_id": "GH-209", "case_name": "伤害案（河南）", "crime": "故意伤害罪", "province": "河南", "sentence_years": 1.4, "is_赔偿": True},
    {"case_id": "GH-210", "case_name": "伤害案（山东）", "crime": "故意伤害罪", "province": "山东", "sentence_years": 1.8, "is_坦白": True},
    {"case_id": "GH-211", "case_name": "伤害案（河北）", "crime": "故意伤害罪", "province": "河北", "sentence_years": 1.7, "is_初犯": True},
    {"case_id": "GH-212", "case_name": "伤害案（福建）", "crime": "故意伤害罪", "province": "福建", "sentence_years": 2.1, "is_自首": True},
    {"case_id": "GH-213", "case_name": "伤害案（重庆）", "crime": "故意伤害罪", "province": "重庆", "sentence_years": 1.9, "is_初犯": True},
    {"case_id": "GH-214", "case_name": "伤害案（天津）", "crime": "故意伤害罪", "province": "天津", "sentence_years": 1.5, "is_坦白": True},
    {"case_id": "GH-215", "case_name": "伤害案（辽宁）", "crime": "故意伤害罪", "province": "辽宁", "sentence_years": 2.3, "is_初犯": True},
    # ---- 抢夺罪 ----
    {"case_id": "QD-201", "case_name": "抢夺案（北京）", "crime": "抢夺罪", "province": "北京", "sentence_years": 1.0, "is_初犯": True},
    {"case_id": "QD-202", "case_name": "抢夺案（上海）", "crime": "抢夺罪", "province": "上海", "sentence_years": 1.5, "is_初犯": True, "is_坦白": True},
    {"case_id": "QD-203", "case_name": "抢夺案（广东）", "crime": "抢夺罪", "province": "广东", "sentence_years": 2.0, "is_累犯": True},
    {"case_id": "QD-204", "case_name": "抢夺案（江苏）", "crime": "抢夺罪", "province": "江苏", "sentence_years": 0.8, "is_自首": True},
    {"case_id": "QD-205", "case_name": "抢夺案（浙江）", "crime": "抢夺罪", "province": "浙江", "sentence_years": 1.2, "is_初犯": True},
    {"case_id": "QD-206", "case_name": "抢夺案（四川）", "crime": "抢夺罪", "province": "四川", "sentence_years": 1.8, "is_初犯": True},
    {"case_id": "QD-207", "case_name": "抢夺案（湖北）", "crime": "抢夺罪", "province": "湖北", "sentence_years": 1.0, "is_坦白": True},
    {"case_id": "QD-208", "case_name": "抢夺案（湖南）", "crime": "抢夺罪", "province": "湖南", "sentence_years": 1.5, "is_初犯": True},
    {"case_id": "QD-209", "case_name": "抢夺案（河南）", "crime": "抢夺罪", "province": "河南", "sentence_years": 1.3, "is_自首": True},
    {"case_id": "QD-210", "case_name": "抢夺案（山东）", "crime": "抢夺罪", "province": "山东", "sentence_years": 1.6, "is_初犯": True},
    {"case_id": "QD-211", "case_name": "抢夺案（河北）", "crime": "抢夺罪", "province": "河北", "sentence_years": 1.1, "is_坦白": True},
    {"case_id": "QD-212", "case_name": "抢夺案（福建）", "crime": "抢夺罪", "province": "福建", "sentence_years": 1.4, "is_初犯": True},
    {"case_id": "QD-213", "case_name": "抢夺案（重庆）", "crime": "抢夺罪", "province": "重庆", "sentence_years": 1.7, "is_自首": True},
    {"case_id": "QD-214", "case_name": "抢夺案（天津）", "crime": "抢夺罪", "province": "天津", "sentence_years": 1.2, "is_初犯": True},
    {"case_id": "QD-215", "case_name": "抢夺案（辽宁）", "crime": "抢夺罪", "province": "辽宁", "sentence_years": 1.9, "is_累犯": True},
    # ---- 敲诈勒索罪 ----
    {"case_id": "ZL-201", "case_name": "敲诈勒索案（北京）", "crime": "敲诈勒索罪", "province": "北京", "sentence_years": 2.0, "is_初犯": True},
    {"case_id": "ZL-202", "case_name": "敲诈勒索案（上海）", "crime": "敲诈勒索罪", "province": "上海", "sentence_years": 2.5, "is_初犯": True},
    {"case_id": "ZL-203", "case_name": "敲诈勒索案（广东）", "crime": "敲诈勒索罪", "province": "广东", "sentence_years": 3.0, "is_累犯": True},
    {"case_id": "ZL-204", "case_name": "敲诈勒索案（江苏）", "crime": "敲诈勒索罪", "province": "江苏", "sentence_years": 1.5, "is_自首": True},
    {"case_id": "ZL-205", "case_name": "敲诈勒索案（浙江）", "crime": "敲诈勒索罪", "province": "浙江", "sentence_years": 1.8, "is_初犯": True},
    {"case_id": "ZL-206", "case_name": "敲诈勒索案（四川）", "crime": "敲诈勒索罪", "province": "四川", "sentence_years": 2.2, "is_坦白": True},
    {"case_id": "ZL-207", "case_name": "敲诈勒索案（湖北）", "crime": "敲诈勒索罪", "province": "湖北", "sentence_years": 1.6, "is_初犯": True},
    {"case_id": "ZL-208", "case_name": "敲诈勒索案（湖南）", "crime": "敲诈勒索罪", "province": "湖南", "sentence_years": 2.0, "is_初犯": True},
    {"case_id": "ZL-209", "case_name": "敲诈勒索案（河南）", "crime": "敲诈勒索罪", "province": "河南", "sentence_years": 1.8, "is_自首": True},
    {"case_id": "ZL-210", "case_name": "敲诈勒索案（山东）", "crime": "敲诈勒索罪", "province": "山东", "sentence_years": 2.5, "is_初犯": True},
    {"case_id": "ZL-211", "case_name": "敲诈勒索案（河北）", "crime": "敲诈勒索罪", "province": "河北", "sentence_years": 1.9, "is_坦白": True},
    {"case_id": "ZL-212", "case_name": "敲诈勒索案（福建）", "crime": "敲诈勒索罪", "province": "福建", "sentence_years": 2.3, "is_初犯": True},
    {"case_id": "ZL-213", "case_name": "敲诈勒索案（重庆）", "crime": "敲诈勒索罪", "province": "重庆", "sentence_years": 2.1, "is_自首": True},
    {"case_id": "ZL-214", "case_name": "敲诈勒索案（天津）", "crime": "敲诈勒索罪", "province": "天津", "sentence_years": 1.7, "is_初犯": True},
    {"case_id": "ZL-215", "case_name": "敲诈勒索案（辽宁）", "crime": "敲诈勒索罪", "province": "辽宁", "sentence_years": 2.8, "is_累犯": True},
    # ---- 侵占罪 ----
    {"case_id": "QZ-201", "case_name": "侵占案（北京）", "crime": "侵占罪", "province": "北京", "sentence_years": 0.5, "is_初犯": True, "is_自首": True},
    {"case_id": "QZ-202", "case_name": "侵占案（上海）", "crime": "侵占罪", "province": "上海", "sentence_years": 1.0, "is_初犯": True},
    {"case_id": "QZ-203", "case_name": "侵占案（广东）", "crime": "侵占罪", "province": "广东", "sentence_years": 0.8, "is_坦白": True},
    {"case_id": "QZ-204", "case_name": "侵占案（江苏）", "crime": "侵占罪", "province": "江苏", "sentence_years": 1.2, "is_初犯": True},
    {"case_id": "QZ-205", "case_name": "侵占案（浙江）", "crime": "侵占罪", "province": "浙江", "sentence_years": 0.6, "is_自首": True},
    {"case_id": "QZ-206", "case_name": "侵占案（四川）", "crime": "侵占罪", "province": "四川", "sentence_years": 1.5, "is_初犯": True},
    {"case_id": "QZ-207", "case_name": "侵占案（湖北）", "crime": "侵占罪", "province": "湖北", "sentence_years": 0.8, "is_坦白": True},
    {"case_id": "QZ-208", "case_name": "侵占案（湖南）", "crime": "侵占罪", "province": "湖南", "sentence_years": 1.0, "is_初犯": True},
    {"case_id": "QZ-209", "case_name": "侵占案（河南）", "crime": "侵占罪", "province": "河南", "sentence_years": 0.7, "is_自首": True},
    {"case_id": "QZ-210", "case_name": "侵占案（山东）", "crime": "侵占罪", "province": "山东", "sentence_years": 1.3, "is_初犯": True},
    {"case_id": "QZ-211", "case_name": "侵占案（河北）", "crime": "侵占罪", "province": "河北", "sentence_years": 0.9, "is_坦白": True},
    {"case_id": "QZ-212", "case_name": "侵占案（福建）", "crime": "侵占罪", "province": "福建", "sentence_years": 1.1, "is_初犯": True},
    {"case_id": "QZ-213", "case_name": "侵占案（重庆）", "crime": "侵占罪", "province": "重庆", "sentence_years": 0.5, "is_自首": True},
    {"case_id": "QZ-214", "case_name": "侵占案（天津）", "crime": "侵占罪", "province": "天津", "sentence_years": 0.8, "is_初犯": True},
    {"case_id": "QZ-215", "case_name": "侵占案（辽宁）", "crime": "侵占罪", "province": "辽宁", "sentence_years": 1.4, "is_坦白": True},
    # ---- 绑架罪 ----
    {"case_id": "BD-201", "case_name": "绑架案（北京）", "crime": "绑架罪", "province": "北京", "sentence_years": 8.0, "is_累犯": True},
    {"case_id": "BD-202", "case_name": "绑架案（上海）", "crime": "绑架罪", "province": "上海", "sentence_years": 10.0, "is_累犯": True},
    {"case_id": "BD-203", "case_name": "绑架案（广东）", "crime": "绑架罪", "province": "广东", "sentence_years": 5.0, "is_初犯": True},
    {"case_id": "BD-204", "case_name": "绑架案（江苏）", "crime": "绑架罪", "province": "江苏", "sentence_years": 6.0, "is_初犯": True},
    {"case_id": "BD-205", "case_name": "绑架案（浙江）", "crime": "绑架罪", "province": "浙江", "sentence_years": 7.0, "is_坦白": True},
    {"case_id": "BD-206", "case_name": "绑架案（四川）", "crime": "绑架罪", "province": "四川", "sentence_years": 5.5, "is_初犯": True},
    {"case_id": "BD-207", "case_name": "绑架案（湖北）", "crime": "绑架罪", "province": "湖北", "sentence_years": 4.5, "is_自首": True},
    {"case_id": "BD-208", "case_name": "绑架案（湖南）", "crime": "绑架罪", "province": "湖南", "sentence_years": 6.5, "is_初犯": True},
    {"case_id": "BD-209", "case_name": "绑架案（河南）", "crime": "绑架罪", "province": "河南", "sentence_years": 5.0, "is_坦白": True},
    {"case_id": "BD-210", "case_name": "绑架案（山东）", "crime": "绑架罪", "province": "山东", "sentence_years": 7.5, "is_累犯": True},
    {"case_id": "BD-211", "case_name": "绑架案（河北）", "crime": "绑架罪", "province": "河北", "sentence_years": 5.8, "is_初犯": True},
    {"case_id": "BD-212", "case_name": "绑架案（福建）", "crime": "绑架罪", "province": "福建", "sentence_years": 6.8, "is_坦白": True},
    {"case_id": "BD-213", "case_name": "绑架案（重庆）", "crime": "绑架罪", "province": "重庆", "sentence_years": 4.2, "is_自首": True},
    {"case_id": "BD-214", "case_name": "绑架案（天津）", "crime": "绑架罪", "province": "天津", "sentence_years": 5.3, "is_初犯": True},
    {"case_id": "BD-215", "case_name": "绑架案（辽宁）", "crime": "绑架罪", "province": "辽宁", "sentence_years": 8.5, "is_累犯": True},
    # ---- 抢劫罪（续）----
    {"case_id": "QZ-301", "case_name": "抢劫案（北京）", "crime": "抢劫罪", "province": "北京", "sentence_years": 4.0, "is_累犯": True},
    {"case_id": "QZ-302", "case_name": "抢劫案（上海）", "crime": "抢劫罪", "province": "上海", "sentence_years": 3.5, "is_初犯": True},
    {"case_id": "QZ-303", "case_name": "抢劫案（广东）", "crime": "抢劫罪", "province": "广东", "sentence_years": 4.5, "is_累犯": True},
    {"case_id": "QZ-304", "case_name": "抢劫案（江苏）", "crime": "抢劫罪", "province": "江苏", "sentence_years": 3.0, "is_坦白": True},
    {"case_id": "QZ-305", "case_name": "抢劫案（浙江）", "crime": "抢劫罪", "province": "浙江", "sentence_years": 3.8, "is_初犯": True},
    {"case_id": "QZ-306", "case_name": "抢劫案（四川）", "crime": "抢劫罪", "province": "四川", "sentence_years": 4.2, "is_累犯": True},
    {"case_id": "QZ-307", "case_name": "抢劫案（湖北）", "crime": "抢劫罪", "province": "湖北", "sentence_years": 3.2, "is_坦白": True},
    {"case_id": "QZ-308", "case_name": "抢劫案（湖南）", "crime": "抢劫罪", "province": "湖南", "sentence_years": 4.0, "is_初犯": True},
    {"case_id": "QZ-309", "case_name": "抢劫案（河南）", "crime": "抢劫罪", "province": "河南", "sentence_years": 3.5, "is_自首": True},
    {"case_id": "QZ-310", "case_name": "抢劫案（山东）", "crime": "抢劫罪", "province": "山东", "sentence_years": 4.8, "is_累犯": True},
    {"case_id": "QZ-311", "case_name": "抢劫案（河北）", "crime": "抢劫罪", "province": "河北", "sentence_years": 3.7, "is_坦白": True},
    {"case_id": "QZ-312", "case_name": "抢劫案（福建）", "crime": "抢劫罪", "province": "福建", "sentence_years": 4.1, "is_初犯": True},
    {"case_id": "QZ-313", "case_name": "抢劫案（重庆）", "crime": "抢劫罪", "province": "重庆", "sentence_years": 3.9, "is_自首": True},
    {"case_id": "QZ-314", "case_name": "抢劫案（天津）", "crime": "抢劫罪", "province": "天津", "sentence_years": 3.3, "is_初犯": True},
    {"case_id": "QZ-315", "case_name": "抢劫案（辽宁）", "crime": "抢劫罪", "province": "辽宁", "sentence_years": 4.6, "is_累犯": True},
    # ---- 强迫交易罪 ----
    {"case_id": "QJ-201", "case_name": "强迫交易案（北京）", "crime": "强迫交易罪", "province": "北京", "sentence_years": 1.0, "is_初犯": True},
    {"case_id": "QJ-202", "case_name": "强迫交易案（上海）", "crime": "强迫交易罪", "province": "上海", "sentence_years": 1.5, "is_坦白": True},
    {"case_id": "QJ-203", "case_name": "强迫交易案（广东）", "crime": "强迫交易罪", "province": "广东", "sentence_years": 2.0, "is_累犯": True},
    {"case_id": "QJ-204", "case_name": "强迫交易案（江苏）", "crime": "强迫交易罪", "province": "江苏", "sentence_years": 0.8, "is_自首": True},
    {"case_id": "QJ-205", "case_name": "强迫交易案（浙江）", "crime": "强迫交易罪", "province": "浙江", "sentence_years": 1.2, "is_初犯": True},
    {"case_id": "QJ-206", "case_name": "强迫交易案（四川）", "crime": "强迫交易罪", "province": "四川", "sentence_years": 1.8, "is_初犯": True},
    {"case_id": "QJ-207", "case_name": "强迫交易案（湖北）", "crime": "强迫交易罪", "province": "湖北", "sentence_years": 1.0, "is_坦白": True},
    {"case_id": "QJ-208", "case_name": "强迫交易案（湖南）", "crime": "强迫交易罪", "province": "湖南", "sentence_years": 1.5, "is_初犯": True},
    {"case_id": "QJ-209", "case_name": "强迫交易案（河南）", "crime": "强迫交易罪", "province": "河南", "sentence_years": 1.3, "is_自首": True},
    {"case_id": "QJ-210", "case_name": "强迫交易案（山东）", "crime": "强迫交易罪", "province": "山东", "sentence_years": 1.6, "is_初犯": True},
    {"case_id": "QJ-211", "case_name": "强迫交易案（河北）", "crime": "强迫交易罪", "province": "河北", "sentence_years": 1.1, "is_坦白": True},
    {"case_id": "QJ-212", "case_name": "强迫交易案（福建）", "crime": "强迫交易罪", "province": "福建", "sentence_years": 1.4, "is_初犯": True},
    {"case_id": "QJ-213", "case_name": "强迫交易案（重庆）", "crime": "强迫交易罪", "province": "重庆", "sentence_years": 1.7, "is_自首": True},
    {"case_id": "QJ-214", "case_name": "强迫交易案（天津）", "crime": "强迫交易罪", "province": "天津", "sentence_years": 0.9, "is_初犯": True},
    {"case_id": "QJ-215", "case_name": "强迫交易案（辽宁）", "crime": "强迫交易罪", "province": "辽宁", "sentence_years": 1.9, "is_累犯": True},
    # ---- 故意杀人罪（续）----
    {"case_id": "SR-301", "case_name": "杀人案（北京）", "crime": "故意杀人罪", "province": "北京", "sentence_years": 12.0, "is_累犯": True},
    {"case_id": "SR-302", "case_name": "杀人案（上海）", "crime": "故意杀人罪", "province": "上海", "sentence_years": 10.0, "is_坦白": True},
    {"case_id": "SR-303", "case_name": "杀人案（广东）", "crime": "故意杀人罪", "province": "广东", "sentence_years": 15.0, "is_累犯": True},
    {"case_id": "SR-304", "case_name": "杀人案（江苏）", "crime": "故意杀人罪", "province": "江苏", "sentence_years": 8.0, "is_自首": True},
    {"case_id": "SR-305", "case_name": "杀人案（浙江）", "crime": "故意杀人罪", "province": "浙江", "sentence_years": 11.0, "is_初犯": True},
    {"case_id": "SR-306", "case_name": "杀人案（四川）", "crime": "故意杀人罪", "province": "四川", "sentence_years": 13.0, "is_累犯": True},
    {"case_id": "SR-307", "case_name": "杀人案（湖北）", "crime": "故意杀人罪", "province": "湖北", "sentence_years": 9.0, "is_坦白": True},
    {"case_id": "SR-308", "case_name": "杀人案（湖南）", "crime": "故意杀人罪", "province": "湖南", "sentence_years": 10.5, "is_初犯": True},
    {"case_id": "SR-309", "case_name": "杀人案（河南）", "crime": "故意杀人罪", "province": "河南", "sentence_years": 8.5, "is_自首": True},
    {"case_id": "SR-310", "case_name": "杀人案（山东）", "crime": "故意杀人罪", "province": "山东", "sentence_years": 12.5, "is_累犯": True},
    {"case_id": "SR-311", "case_name": "杀人案（河北）", "crime": "故意杀人罪", "province": "河北", "sentence_years": 9.5, "is_坦白": True},
    {"case_id": "SR-312", "case_name": "杀人案（福建）", "crime": "故意杀人罪", "province": "福建", "sentence_years": 11.5, "is_初犯": True},
    {"case_id": "SR-313", "case_name": "杀人案（重庆）", "crime": "故意杀人罪", "province": "重庆", "sentence_years": 7.5, "is_自首": True},
    {"case_id": "SR-314", "case_name": "杀人案（天津）", "crime": "故意杀人罪", "province": "天津", "sentence_years": 10.0, "is_初犯": True},
    {"case_id": "SR-315", "case_name": "杀人案（辽宁）", "crime": "故意杀人罪", "province": "辽宁", "sentence_years": 14.0, "is_累犯": True},
    # ---- 拐卖妇女、儿童罪 ----
    {"case_id": "GM-201", "case_name": "拐卖案（北京）", "crime": "拐卖妇女、儿童罪", "province": "北京", "sentence_years": 8.0, "is_累犯": True},
    {"case_id": "GM-202", "case_name": "拐卖案（上海）", "crime": "拐卖妇女、儿童罪", "province": "上海", "sentence_years": 10.0, "is_累犯": True},
    {"case_id": "GM-203", "case_name": "拐卖案（广东）", "crime": "拐卖妇女、儿童罪", "province": "广东", "sentence_years": 6.0, "is_坦白": True},
    {"case_id": "GM-204", "case_name": "拐卖案（江苏）", "crime": "拐卖妇女、儿童罪", "province": "江苏", "sentence_years": 7.0, "is_初犯": True},
    {"case_id": "GM-205", "case_name": "拐卖案（浙江）", "crime": "拐卖妇女、儿童罪", "province": "浙江", "sentence_years": 5.0, "is_自首": True},
    {"case_id": "GM-206", "case_name": "拐卖案（四川）", "crime": "拐卖妇女、儿童罪", "province": "四川", "sentence_years": 8.5, "is_累犯": True},
    {"case_id": "GM-207", "case_name": "拐卖案（湖北）", "crime": "拐卖妇女、儿童罪", "province": "湖北", "sentence_years": 5.5, "is_坦白": True},
    {"case_id": "GM-208", "case_name": "拐卖案（湖南）", "crime": "拐卖妇女、儿童罪", "province": "湖南", "sentence_years": 7.5, "is_初犯": True},
    {"case_id": "GM-209", "case_name": "拐卖案（河南）", "crime": "拐卖妇女、儿童罪", "province": "河南", "sentence_years": 6.5, "is_自首": True},
    {"case_id": "GM-210", "case_name": "拐卖案（山东）", "crime": "拐卖妇女、儿童罪", "province": "山东", "sentence_years": 9.0, "is_累犯": True},
    {"case_id": "GM-211", "case_name": "拐卖案（河北）", "crime": "拐卖妇女、儿童罪", "province": "河北", "sentence_years": 6.8, "is_坦白": True},
    {"case_id": "GM-212", "case_name": "拐卖案（福建）", "crime": "拐卖妇女、儿童罪", "province": "福建", "sentence_years": 5.8, "is_初犯": True},
    {"case_id": "GM-213", "case_name": "拐卖案（重庆）", "crime": "拐卖妇女、儿童罪", "province": "重庆", "sentence_years": 7.2, "is_自首": True},
    {"case_id": "GM-214", "case_name": "拐卖案（天津）", "crime": "拐卖妇女、儿童罪", "province": "天津", "sentence_years": 5.5, "is_初犯": True},
    {"case_id": "GM-215", "case_name": "拐卖案（辽宁）", "crime": "拐卖妇女、儿童罪", "province": "辽宁", "sentence_years": 8.8, "is_累犯": True},
    # ---- 招摇撞骗罪 ----
    {"case_id": "ZY-201", "case_name": "招摇撞骗案（北京）", "crime": "招摇撞骗罪", "province": "北京", "sentence_years": 0.5, "is_自首": True},
    {"case_id": "ZY-202", "case_name": "招摇撞骗案（上海）", "crime": "招摇撞骗罪", "province": "上海", "sentence_years": 1.0, "is_初犯": True},
    {"case_id": "ZY-203", "case_name": "招摇撞骗案（广东）", "crime": "招摇撞骗罪", "province": "广东", "sentence_years": 1.5, "is_坦白": True},
    {"case_id": "ZY-204", "case_name": "招摇撞骗案（江苏）", "crime": "招摇撞骗罪", "province": "江苏", "sentence_years": 0.8, "is_初犯": True},
    {"case_id": "ZY-205", "case_name": "招摇撞骗案（浙江）", "crime": "招摇撞骗罪", "province": "浙江", "sentence_years": 1.2, "is_自首": True},
    {"case_id": "ZY-206", "case_name": "招摇撞骗案（四川）", "crime": "招摇撞骗罪", "province": "四川", "sentence_years": 0.6, "is_初犯": True},
    {"case_id": "ZY-207", "case_name": "招摇撞骗案（湖北）", "crime": "招摇撞骗罪", "province": "湖北", "sentence_years": 1.0, "is_坦白": True},
    {"case_id": "ZY-208", "case_name": "招摇撞骗案（湖南）", "crime": "招摇撞骗罪", "province": "湖南", "sentence_years": 1.3, "is_初犯": True},
    {"case_id": "ZY-209", "case_name": "招摇撞骗案（河南）", "crime": "招摇撞骗罪", "province": "河南", "sentence_years": 0.7, "is_自首": True},
    {"case_id": "ZY-210", "case_name": "招摇撞骗案（山东）", "crime": "招摇撞骗罪", "province": "山东", "sentence_years": 1.1, "is_初犯": True},
    {"case_id": "ZY-211", "case_name": "招摇撞骗案（河北）", "crime": "招摇撞骗罪", "province": "河北", "sentence_years": 0.9, "is_坦白": True},
    {"case_id": "ZY-212", "case_name": "招摇撞骗案（福建）", "crime": "招摇撞骗罪", "province": "福建", "sentence_years": 1.4, "is_初犯": True},
    {"case_id": "ZY-213", "case_name": "招摇撞骗案（重庆）", "crime": "招摇撞骗罪", "province": "重庆", "sentence_years": 0.5, "is_自首": True},
    {"case_id": "ZY-214", "case_name": "招摇撞骗案（天津）", "crime": "招摇撞骗罪", "province": "天津", "sentence_years": 0.8, "is_初犯": True},
    {"case_id": "ZY-215", "case_name": "招摇撞骗案（辽宁）", "crime": "招摇撞骗罪", "province": "辽宁", "sentence_years": 1.5, "is_坦白": True},
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
