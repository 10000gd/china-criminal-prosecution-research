# -*- coding: utf-8 -*-
"""
入罪门槛数据库 - prosecution_system/src/threshold_db.py

功能：
- 提供各省市盗窃罪、诈骗罪、抢夺罪、故意伤害罪、毒品犯罪、职务侵占罪等的入罪数额标准
- 判断具体金额是否达到立案追诉门槛
- 输出省份差异提示

法律依据：
- 盗窃罪：最高法最高检《关于办理盗窃刑事案件适用法律若干问题的解释》(2013)
- 诈骗罪：最高法《关于审理诈骗刑事案件具体应用法律若干问题的解释》(2022)
- 抢夺罪：最高法最高检《关于办理抢夺刑事案件适用法律若干问题的解释》(2013)
- 开设赌场罪：最高法最高检《关于办理赌博刑事案件具体应用法律若干问题的解释》(2010)
- 故意伤害罪：刑法第234条 + 最高法《关于审理人身损害赔偿案件适用法律若干问题的解释》
- 毒品犯罪：最高法关于审理毒品犯罪案件座谈会纪要(2015) + 刑法第347条
- 职务侵占罪：最高检公安部关于公安机关管辖的刑事案件立案追诉标准的规定(二)(2022)

⚠️ 注意：以下数据基于公开司法解释，省份具体标准可能存在微调，
  使用前请以当地高院最新实施细则为准。
"""

from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass


# =============================================================================
# 盗窃罪数额标准（元）
# =============================================================================
THEFT_THRESHOLDS: Dict[str, Dict[str, Any]] = {
    "北京": {"low": 2000, "mid": 2000, "high": 2000, "standard": "2000元（统一标准）"},
    "上海": {"low": 1000, "mid": 1000, "high": 1000, "standard": "1000元"},
    "浙江": {"low": 3000, "mid": 3000, "high": 3000, "standard": "3000元（杭州、宁波等）"},
    "江苏": {"low": 2000, "mid": 2000, "high": 2000, "standard": "2000元"},
    "广东": {"low": 3000, "mid": 2000, "high": 1000, "standard": "3000/2000/1000元（分地区）"},
    "深圳": {"low": 3000, "mid": 3000, "high": 3000, "standard": "3000元"},
    "广州": {"low": 3000, "mid": 3000, "high": 3000, "standard": "3000元"},
    "天津": {"low": 2000, "mid": 2000, "high": 2000, "standard": "2000元"},
    "重庆": {"low": 2000, "mid": 2000, "high": 2000, "standard": "2000元"},
    "四川": {"low": 1600, "mid": 1600, "high": 1600, "standard": "1600元（成都2000元）"},
    "成都": {"low": 2000, "mid": 2000, "high": 2000, "standard": "2000元"},
    "湖北": {"low": 2000, "mid": 2000, "high": 2000, "standard": "2000元"},
    "湖南": {"low": 2000, "mid": 2000, "high": 2000, "standard": "2000元"},
    "河南": {"low": 2000, "mid": 2000, "high": 2000, "standard": "2000元"},
    "河北": {"low": 2000, "mid": 2000, "high": 2000, "standard": "2000元"},
    "山东": {"low": 2000, "mid": 2000, "high": 2000, "standard": "2000元"},
    "福建": {"low": 3000, "mid": 3000, "high": 3000, "standard": "3000元"},
    "厦门": {"low": 3000, "mid": 3000, "high": 3000, "standard": "3000元"},
    "安徽": {"low": 3000, "mid": 3000, "high": 3000, "standard": "3000元"},
    "辽宁": {"low": 2000, "mid": 2000, "high": 2000, "standard": "2000元"},
    "黑龙江": {"low": 1500, "mid": 1500, "high": 1500, "standard": "1500元"},
    "吉林": {"low": 2000, "mid": 2000, "high": 2000, "standard": "2000元"},
    "陕西": {"low": 2000, "mid": 2000, "high": 2000, "standard": "2000元"},
    "云南": {"low": 1500, "mid": 1500, "high": 1500, "standard": "1500元"},
    "贵州": {"low": 1000, "mid": 1000, "high": 1000, "standard": "1000元"},
    "西藏": {"low": 1000, "mid": 1000, "high": 1000, "standard": "1000元"},
    "内蒙古": {"low": 1000, "mid": 1000, "high": 1000, "standard": "1000元"},
    "新疆": {"low": 1000, "mid": 1000, "high": 1000, "standard": "1000元"},
    "甘肃": {"low": 1000, "mid": 1000, "high": 1000, "standard": "1000元"},
    "青海": {"low": 1000, "mid": 1000, "high": 1000, "standard": "1000元"},
    "宁夏": {"low": 1000, "mid": 1000, "high": 1000, "standard": "1000元"},
    "海南": {"low": 1000, "mid": 1000, "high": 1000, "standard": "1000元"},
    "江西": {"low": 1500, "mid": 1500, "high": 1500, "standard": "1500元"},
    "山西": {"low": 2000, "mid": 2000, "high": 2000, "standard": "2000元"},
    "广西": {"low": 1000, "mid": 1000, "high": 1000, "standard": "1000元"},
    "DEFAULT": {"low": 1000, "mid": 1000, "high": 1000, "standard": "1000元（全国最低标准）"},
}

THEFT_MASSIVE: Dict[str, int] = {
    "DEFAULT": 30000,
    "北京": 100000, "上海": 100000, "浙江": 80000, "江苏": 80000,
    "广东": 60000, "深圳": 60000, "福建": 60000, "天津": 60000,
    "重庆": 60000, "四川": 60000, "湖北": 60000, "湖南": 60000,
    "河南": 50000, "山东": 50000, "辽宁": 50000,
}

THEFT_ESPECIALLY_MASSIVE: Dict[str, int] = {
    "DEFAULT": 300000,
    "北京": 500000, "上海": 500000, "浙江": 400000, "江苏": 400000,
    "广东": 300000, "深圳": 300000, "福建": 300000,
    "天津": 250000, "重庆": 250000, "四川": 200000,
}


# =============================================================================
# 诈骗罪数额标准（元）
# =============================================================================
FRAUD_THRESHOLDS: Dict[str, Dict[str, int]] = {
    "DEFAULT": {"amount_standard": 5000, "massive": 50000, "especially_massive": 500000},
    "北京": {"amount_standard": 5000, "massive": 100000, "especially_massive": 500000},
    "上海": {"amount_standard": 5000, "massive": 100000, "especially_massive": 500000},
    "浙江": {"amount_standard": 6000, "massive": 100000, "especially_massive": 500000},
    "广东": {"amount_standard": 6000, "massive": 50000, "especially_massive": 500000},
    "深圳": {"amount_standard": 6000, "massive": 50000, "especially_massive": 500000},
    "江苏": {"amount_standard": 6000, "massive": 50000, "especially_massive": 500000},
    "天津": {"amount_standard": 6000, "massive": 50000, "especially_massive": 500000},
    "重庆": {"amount_standard": 5000, "massive": 50000, "especially_massive": 500000},
    "四川": {"amount_standard": 5000, "massive": 50000, "especially_massive": 500000},
    "湖北": {"amount_standard": 5000, "massive": 50000, "especially_massive": 500000},
    "湖南": {"amount_standard": 5000, "massive": 50000, "especially_massive": 500000},
    "河南": {"amount_standard": 5000, "massive": 50000, "especially_massive": 500000},
    "山东": {"amount_standard": 6000, "massive": 100000, "especially_massive": 500000},
    "福建": {"amount_standard": 6000, "massive": 100000, "especially_massive": 500000},
    "辽宁": {"amount_standard": 6000, "massive": 50000, "especially_massive": 500000},
    "黑龙江": {"amount_standard": 5000, "massive": 50000, "especially_massive": 500000},
    "安徽": {"amount_standard": 5000, "massive": 50000, "especially_massive": 500000},
    "陕西": {"amount_standard": 5000, "massive": 50000, "especially_massive": 500000},
    "江西": {"amount_standard": 5000, "massive": 50000, "especially_massive": 500000},
    "云南": {"amount_standard": 5000, "massive": 50000, "especially_massive": 500000},
    "贵州": {"amount_standard": 5000, "massive": 50000, "especially_massive": 500000},
    "广西": {"amount_standard": 5000, "massive": 50000, "especially_massive": 500000},
    "海南": {"amount_standard": 5000, "massive": 50000, "especially_massive": 500000},
    "内蒙古": {"amount_standard": 5000, "massive": 50000, "especially_massive": 500000},
    "新疆": {"amount_standard": 5000, "massive": 50000, "especially_massive": 500000},
    "甘肃": {"amount_standard": 5000, "massive": 50000, "especially_massive": 500000},
    "青海": {"amount_standard": 5000, "massive": 50000, "especially_massive": 500000},
    "宁夏": {"amount_standard": 5000, "massive": 50000, "especially_massive": 500000},
    "西藏": {"amount_standard": 5000, "massive": 50000, "especially_massive": 500000},
    "吉林": {"amount_standard": 5000, "massive": 50000, "especially_massive": 500000},
    "河北": {"amount_standard": 5000, "massive": 50000, "especially_massive": 500000},
    "山西": {"amount_standard": 5000, "massive": 50000, "especially_massive": 500000},
}


# =============================================================================
# 抢夺罪数额标准（元）
# =============================================================================
ROBBERY_THRESHOLDS: Dict[str, int] = {
    "DEFAULT": 1000,
    "北京": 2000, "上海": 2000, "浙江": 3000, "江苏": 2000,
    "广东": 3000, "天津": 2000, "重庆": 2000, "四川": 1000,
    "湖北": 2000, "湖南": 2000, "河南": 2000, "山东": 2000,
    "福建": 3000, "辽宁": 2000, "安徽": 2000, "陕西": 2000,
    "西藏": 500, "内蒙古": 1000, "新疆": 1000,
    "甘肃": 1000, "青海": 1000, "宁夏": 1000, "海南": 1000,
    "江西": 1500, "云南": 1000, "贵州": 1000, "广西": 1000,
    "黑龙江": 1000, "吉林": 1500, "河北": 1500, "山西": 1500,
}

# =============================================================================
# 职务侵占罪数额标准（元）
# 刑法第271条：数额较大（≥3万）/ 数额巨大（≥100万）
# =============================================================================
EMBEZZLEMENT_THRESHOLDS: Dict[str, Dict[str, int]] = {
    # 全国统一标准（2022年修订后）
    "DEFAULT": {"amount_standard": 30000, "massive": 1000000},
    "北京": {"amount_standard": 20000, "massive": 1000000},
    "上海": {"amount_standard": 20000, "massive": 1000000},
    "浙江": {"amount_standard": 30000, "massive": 1000000},
    "广东": {"amount_standard": 30000, "massive": 1000000},
    "深圳": {"amount_standard": 30000, "massive": 1000000},
    "江苏": {"amount_standard": 30000, "massive": 1000000},
    "天津": {"amount_standard": 30000, "massive": 1000000},
    "重庆": {"amount_standard": 30000, "massive": 1000000},
}

# =============================================================================
# 故意伤害罪入罪门槛（元）
# 刑法第234条：轻伤即可入罪，不以数额论
# 但司法实践中轻伤赔偿标准影响量刑，这里记录轻伤/重伤/致死的赔偿参考线
# =============================================================================
INJURY_THRESHOLDS: Dict[str, Dict[str, Any]] = {
    # 故意伤害罪以伤情定罪，数额仅用于量刑参考
    # level: slight=轻伤(入罪), serious=重伤, fatal=致人死亡/严重残疾
    "DEFAULT": {
        "slight_min": 1,       # 轻伤即入罪，无金额门槛
        "serious_min": 30000,  # 重伤参考赔偿起点
        "fatal_min": 100000,   # 致人死亡/严重残疾参考起点
        "note": "故意伤害罪以伤情定罪（轻伤即可入罪），赔偿数额影响量刑",
    },
    "北京": {
        "slight_min": 1,
        "serious_min": 50000,
        "fatal_min": 200000,
        "note": "北京故意伤害罪重伤/致死赔偿参考标准",
    },
    "上海": {
        "slight_min": 1,
        "serious_min": 50000,
        "fatal_min": 200000,
        "note": "上海故意伤害罪重伤/致死赔偿参考标准",
    },
    "广东": {
        "slight_min": 1,
        "serious_min": 40000,
        "fatal_min": 150000,
        "note": "广东故意伤害罪重伤/致死赔偿参考标准",
    },
    "浙江": {
        "slight_min": 1,
        "serious_min": 40000,
        "fatal_min": 150000,
        "note": "浙江故意伤害罪重伤/致死赔偿参考标准",
    },
    "江苏": {
        "slight_min": 1,
        "serious_min": 30000,
        "fatal_min": 100000,
        "note": "江苏故意伤害罪重伤/致死赔偿参考标准",
    },
}

# =============================================================================
# 毒品犯罪数量标准（克/g）
# 刑法第347条：海洛因/冰毒/甲基苯丙胺 ≥10g 入罪，≥50g 情节严重，≥200g 情节特别严重
# =============================================================================
DRUG_THRESHOLDS: Dict[str, Dict[str, float]] = {
    # 各主要毒品种类入罪/情节严重/情节特别严重标准（克）
    "海洛因": {
        "standard": 10,    # ≥10g 入罪
        "serious": 50,     # ≥50g 情节严重（可判死刑）
        "especially": 200, # ≥200g 情节特别严重（死刑）
    },
    "冰毒": {
        "standard": 10,    # ≥10g 入罪
        "serious": 50,     # ≥50g 情节严重
        "especially": 200, # ≥200g 情节特别严重
    },
    "甲基苯丙胺": {
        "standard": 10,    # 同冰毒
        "serious": 50,
        "especially": 200,
    },
    "吗啡": {
        "standard": 10,
        "serious": 50,
        "especially": 200,
    },
    "大麻": {
        "standard": 200,   # 大麻叶
        "serious": 1000,
        "especially": 5000,
    },
    "大麻脂": {
        "standard": 40,
        "serious": 200,
        "especially": 1000,
    },
    "可卡因": {
        "standard": 10,
        "serious": 50,
        "especially": 200,
    },
    "氯胺酮（K粉）": {
        "standard": 20,    # ≥20g 入罪
        "serious": 100,
        "especially": 500,
    },
    "甲卡西酮": {
        "standard": 10,
        "serious": 50,
        "especially": 200,
    },
    "麻古": {
        "standard": 10,    # 麻古为冰毒片剂
        "serious": 50,
        "especially": 200,
    },
    "罂粟壳": {
        "standard": 50,    # ≥50kg 入罪
        "serious": 200,
        "especially": 1000,
    },
    "MDMA（摇头丸）": {
        "standard": 20,
        "serious": 100,
        "especially": 500,
    },
}


# =============================================================================
# 开设赌场罪标准
# =============================================================================
GAMBLING_THRESHOLDS = {
    "DEFAULT": {
        "regular": "抽头渔利5000元以上/赌资50000元以上/参赌人数20人以上/赌具数量10台以上",
    },
}


@dataclass
class ThresholdResult:
    crime_type: str
    province: str
    amount: float
    threshold: int
    level: str  # NOT_CRIME / AMOUNT_LARGE / MASSIVE / ESPECIALLY_MASSIVE / INJURY_SLIGHT / INJURY_SERIOUS / INJURY_FATAL / DRUG_STANDARD / DRUG_SERIOUS / DRUG_ESPECIALLY
    verdict: str  # 结论描述
    confidence: str  # 高/中/低
    confidence_note: str  # 置信度说明
    legal_basis: str  # 法律依据


def _get_province_key(province: str, db: Dict) -> str:
    """匹配省份名称到数据库key"""
    if not province:
        return "DEFAULT"
    province = province.strip()
    if province in db:
        return province
    for key in db:
        if key != "DEFAULT" and (key in province or province in key):
            return key
    return "DEFAULT"


class ThresholdDB:
    """入罪门槛数据库"""

    def __init__(self):
        self.theft_thresholds = THEFT_THRESHOLDS
        self.fraud_thresholds = FRAUD_THRESHOLDS
        self.robbery_thresholds = ROBBERY_THRESHOLDS
        self.gambling_thresholds = GAMBLING_THRESHOLDS
        self.embezzlement_thresholds = EMBEZZLEMENT_THRESHOLDS
        self.injury_thresholds = INJURY_THRESHOLDS
        self.drug_thresholds = DRUG_THRESHOLDS

    def get_threshold(self, crime_type: str, province: str = None) -> Dict[str, Any]:
        """获取某省份某罪名的入罪门槛"""
        ct = crime_type.strip()
        pk = _get_province_key(province, self.theft_thresholds)

        if ct in ("盗窃罪", "theft", "盗窃"):
            data = self.theft_thresholds.get(pk, self.theft_thresholds["DEFAULT"])
            return {
                "crime_type": "盗窃罪",
                "province": pk if pk != "DEFAULT" else "（全国默认）",
                "amount_large": data.get("low", 1000),
                "amount_massive": THEFT_MASSIVE.get(pk, THEFT_MASSIVE["DEFAULT"]),
                "amount_especially_massive": THEFT_ESPECIALLY_MASSIVE.get(pk, THEFT_ESPECIALLY_MASSIVE["DEFAULT"]),
                "standard_note": data.get("standard", ""),
                "legal_basis": "最高法最高检《关于办理盗窃刑事案件适用法律若干问题的解释》(2013) 第1条",
            }

        elif ct in ("诈骗罪", "fraud", "诈骗"):
            data = self.fraud_thresholds.get(pk, self.fraud_thresholds["DEFAULT"])
            return {
                "crime_type": "诈骗罪",
                "province": pk if pk != "DEFAULT" else "（全国默认）",
                "amount_large": data.get("amount_standard", 5000),
                "amount_massive": data.get("massive", 50000),
                "amount_especially_massive": data.get("especially_massive", 500000),
                "standard_note": "",
                "legal_basis": "最高法《关于审理诈骗刑事案件具体应用法律若干问题的解释》(2022) 第1条",
            }

        elif ct in ("抢夺罪", "robbery", "抢夺"):
            amt = self.robbery_thresholds.get(pk, self.robbery_thresholds["DEFAULT"])
            return {
                "crime_type": "抢夺罪",
                "province": pk if pk != "DEFAULT" else "（全国默认）",
                "amount_large": amt,
                "standard_note": "",
                "legal_basis": "最高法最高检《关于办理抢夺刑事案件适用法律若干问题的解释》(2013) 第1条",
            }

        elif ct in ("开设赌场罪", "gambling", "开设赌场"):
            return {
                "crime_type": "开设赌场罪",
                "province": pk if pk != "DEFAULT" else "（全国默认）",
                "threshold_note": self.gambling_thresholds["DEFAULT"]["regular"],
                "legal_basis": "最高法最高检《关于办理赌博刑事案件具体应用法律若干问题的解释》(2010) 第1条",
            }

        elif ct in ("职务侵占罪", "embezzlement", "职务侵占"):
            data = self.embezzlement_thresholds.get(pk, self.embezzlement_thresholds["DEFAULT"])
            return {
                "crime_type": "职务侵占罪",
                "province": pk if pk != "DEFAULT" else "（全国默认）",
                "amount_large": data.get("amount_standard", 30000),
                "amount_massive": data.get("massive", 1000000),
                "standard_note": "数额较大≥3万，数额巨大≥100万",
                "legal_basis": "最高检公安部《立案追诉标准(二)》(2022修订) 第76条",
            }

        elif ct in ("故意伤害罪", "injury", "故意伤害"):
            data = self.injury_thresholds.get(pk, self.injury_thresholds["DEFAULT"])
            return {
                "crime_type": "故意伤害罪",
                "province": pk if pk != "DEFAULT" else "（全国默认）",
                "threshold_note": "以伤情定罪，轻伤即可入罪（无金额门槛）",
                "serious_min": data.get("serious_min", 30000),
                "fatal_min": data.get("fatal_min", 100000),
                "standard_note": data.get("note", ""),
                "legal_basis": "《刑法》第234条 + 最高法《人身损害赔偿司法解释》(2022)",
            }

        elif ct in ("毒品犯罪", "drug", "贩毒", "走私毒品", "制造毒品", "运输毒品"):
            return {
                "crime_type": "毒品犯罪",
                "province": "（全国统一标准）",
                "drug_types": list(self.drug_thresholds.keys()),
                "standard_note": "以毒品重量（克）计，不以金额计",
                "legal_basis": "《刑法》第347条 + 最高法《毒品犯罪座谈会纪要》(2015)",
            }

        else:
            return {
                "crime_type": ct,
                "province": province or "（未指定）",
                "error": "暂不支持该罪名的门槛查询",
                "supported": self.get_all_supported_crimes(),
            }

    def check_threshold(
        self,
        province: str,
        crime_type: str,
        amount: float,
    ) -> ThresholdResult:
        """判断给定金额是否达到入罪门槛，返回结构化结果"""
        ct = crime_type.strip()
        amt = float(amount)
        pk = _get_province_key(province, self.theft_thresholds) if province else "DEFAULT"

        # ── 盗窃罪 ──────────────────────────────────────────────
        if ct in ("盗窃罪", "theft", "盗窃"):
            data = self.theft_thresholds.get(pk, self.theft_thresholds["DEFAULT"])
            large = data.get("low", 1000)
            massive = THEFT_MASSIVE.get(pk, THEFT_MASSIVE["DEFAULT"])
            espe = THEFT_ESPECIALLY_MASSIVE.get(pk, THEFT_ESPECIALLY_MASSIVE["DEFAULT"])
            basis = "最高法最高检《关于办理盗窃刑事案件适用法律若干问题的解释》(2013) 第1条"

            if amt < large:
                return ThresholdResult(
                    crime_type="盗窃罪", province=province or pk,
                    amount=amt, threshold=large,
                    level="NOT_CRIME",
                    verdict=f"金额{amt:.0f}元 < {large}元入罪门槛，❌ 不构成盗窃罪（需达到{large}元）",
                    confidence="中", confidence_note="以省会城市标准估算，各市辖区可能略有差异",
                    legal_basis=basis,
                )
            elif amt < massive:
                return ThresholdResult(
                    crime_type="盗窃罪", province=province or pk,
                    amount=amt, threshold=large,
                    level="AMOUNT_LARGE",
                    verdict=f"金额{amt:.0f}元，达到'数额较大'标准（≥{large}元），✅ 涉嫌盗窃罪（数额较大）",
                    confidence="高", confidence_note="法条原文标准，明确无歧义",
                    legal_basis=basis,
                )
            elif amt < espe:
                return ThresholdResult(
                    crime_type="盗窃罪", province=province or pk,
                    amount=amt, threshold=large,
                    level="MASSIVE",
                    verdict=f"金额{amt:.0f}元，达到'数额巨大'标准（≥{massive}元），⚠️ 涉嫌盗窃罪（数额巨大），法定刑3-10年",
                    confidence="高", confidence_note="法条原文标准，明确无歧义",
                    legal_basis=basis,
                )
            else:
                return ThresholdResult(
                    crime_type="盗窃罪", province=province or pk,
                    amount=amt, threshold=large,
                    level="ESPECIALLY_MASSIVE",
                    verdict=f"金额{amt:.0f}元，达到'数额特别巨大'标准（≥{espe}元），⚠️ 涉嫌盗窃罪（数额特别巨大），法定刑10年以上",
                    confidence="高", confidence_note="法条原文标准，明确无歧义",
                    legal_basis=basis,
                )

        # ── 诈骗罪 ──────────────────────────────────────────────
        elif ct in ("诈骗罪", "fraud", "诈骗"):
            data = self.fraud_thresholds.get(pk, self.fraud_thresholds["DEFAULT"])
            large = data.get("amount_standard", 5000)
            massive = data.get("massive", 50000)
            espe = data.get("especially_massive", 500000)
            basis = "最高法《关于审理诈骗刑事案件具体应用法律若干问题的解释》(2022) 第1条"

            if amt < large:
                return ThresholdResult(
                    crime_type="诈骗罪", province=province or pk,
                    amount=amt, threshold=large,
                    level="NOT_CRIME",
                    verdict=f"金额{amt:.0f}元 < {large}元入罪门槛，❌ 不构成诈骗罪",
                    confidence="中", confidence_note="2022年解释调整了标准，建议核查最新地方细则",
                    legal_basis=basis,
                )
            elif amt < massive:
                return ThresholdResult(
                    crime_type="诈骗罪", province=province or pk,
                    amount=amt, threshold=large,
                    level="AMOUNT_LARGE",
                    verdict=f"金额{amt:.0f}元，达到'数额较大'标准（≥{large}元），✅ 涉嫌诈骗罪",
                    confidence="中", confidence_note="2022年解释标准，引用时须标注年份",
                    legal_basis=basis,
                )
            else:
                level_name = "数额巨大" if amt < espe else "数额特别巨大"
                lvl = "MASSIVE" if amt < espe else "ESPECIALLY_MASSIVE"
                return ThresholdResult(
                    crime_type="诈骗罪", province=province or pk,
                    amount=amt, threshold=large,
                    level=lvl,
                    verdict=f"金额{amt:.0f}元，达到'{level_name}'标准，⚠️ 涉嫌诈骗罪（{level_name}）",
                    confidence="中", confidence_note="2022年解释标准",
                    legal_basis=basis,
                )

        # ── 抢夺罪 ──────────────────────────────────────────────
        elif ct in ("抢夺罪", "robbery", "抢夺"):
            large = self.robbery_thresholds.get(pk, self.robbery_thresholds["DEFAULT"])
            basis = "最高法最高检《关于办理抢夺刑事案件适用法律若干问题的解释》(2013) 第1条"
            if amt < large:
                return ThresholdResult(
                    crime_type="抢夺罪", province=province or pk,
                    amount=amt, threshold=large,
                    level="NOT_CRIME",
                    verdict=f"金额{amt:.0f}元 < {large}元入罪门槛，❌ 不构成抢夺罪",
                    confidence="中", confidence_note="以省会城市标准估算",
                    legal_basis=basis,
                )
            return ThresholdResult(
                crime_type="抢夺罪", province=province or pk,
                amount=amt, threshold=large,
                level="AMOUNT_LARGE",
                verdict=f"金额{amt:.0f}元，达到'数额较大'标准（≥{large}元），✅ 涉嫌抢夺罪",
                confidence="高", confidence_note="法条原文标准，明确无歧义",
                legal_basis=basis,
            )

        # ── 职务侵占罪 ──────────────────────────────────────────
        elif ct in ("职务侵占罪", "embezzlement", "职务侵占"):
            data = self.embezzlement_thresholds.get(pk, self.embezzlement_thresholds["DEFAULT"])
            large = data.get("amount_standard", 30000)
            massive = data.get("massive", 1000000)
            basis = "最高检公安部《立案追诉标准(二)》(2022修订) 第76条"

            if amt < large:
                return ThresholdResult(
                    crime_type="职务侵占罪", province=province or pk,
                    amount=amt, threshold=large,
                    level="NOT_CRIME",
                    verdict=f"金额{amt:.0f}元 < {large}元入罪门槛，❌ 不构成职务侵占罪",
                    confidence="高", confidence_note="2022年修订后标准",
                    legal_basis=basis,
                )
            elif amt < massive:
                return ThresholdResult(
                    crime_type="职务侵占罪", province=province or pk,
                    amount=amt, threshold=large,
                    level="AMOUNT_LARGE",
                    verdict=f"金额{amt:.0f}元，达到'数额较大'标准（≥{large}元），✅ 涉嫌职务侵占罪",
                    confidence="高", confidence_note="法条原文标准，明确无歧义",
                    legal_basis=basis,
                )
            else:
                return ThresholdResult(
                    crime_type="职务侵占罪", province=province or pk,
                    amount=amt, threshold=large,
                    level="MASSIVE",
                    verdict=f"金额{amt:.0f}元，达到'数额巨大'标准（≥{massive}元），⚠️ 涉嫌职务侵占罪（数额巨大），法定刑3年以上",
                    confidence="高", confidence_note="法条原文标准",
                    legal_basis=basis,
                )

        # ── 毒品犯罪 ────────────────────────────────────────────
        elif ct in ("毒品犯罪", "drug", "贩毒", "走私毒品", "制造毒品", "运输毒品"):
            # amount 参数在这里是毒品重量（克），不是金额
            weight = amt  # 克
            # 默认为冰毒/海洛因标准
            drug_data = self.drug_thresholds.get("冰毒", self.drug_thresholds.get("海洛因"))
            if not drug_data:
                drug_data = {"standard": 10, "serious": 50, "especially": 200}

            std = drug_data["standard"]
            serious = drug_data["serious"]
            espe = drug_data["especially"]
            basis = "《刑法》第347条 + 最高法《毒品犯罪座谈会纪要》(2015)"

            if weight < std:
                return ThresholdResult(
                    crime_type="毒品犯罪", province="（全国统一标准）",
                    amount=weight, threshold=std,
                    level="NOT_CRIME",
                    verdict=f"毒品重量{weight:.1f}g < {std}g入罪门槛，❌ 不构成毒品犯罪",
                    confidence="高", confidence_note="全国统一标准",
                    legal_basis=basis,
                )
            elif weight < serious:
                return ThresholdResult(
                    crime_type="毒品犯罪", province="（全国统一标准）",
                    amount=weight, threshold=std,
                    level="DRUG_STANDARD",
                    verdict=f"毒品重量{weight:.1f}g，达到入罪标准（≥{std}g），✅ 涉嫌毒品犯罪",
                    confidence="高", confidence_note="全国统一标准",
                    legal_basis=basis,
                )
            elif weight < espe:
                return ThresholdResult(
                    crime_type="毒品犯罪", province="（全国统一标准）",
                    amount=weight, threshold=std,
                    level="DRUG_SERIOUS",
                    verdict=f"毒品重量{weight:.1f}g，达到'情节严重'标准（≥{serious}g），⚠️ 法定刑15年以上/死刑",
                    confidence="高", confidence_note="全国统一标准",
                    legal_basis=basis,
                )
            else:
                return ThresholdResult(
                    crime_type="毒品犯罪", province="（全国统一标准）",
                    amount=weight, threshold=std,
                    level="DRUG_ESPECIALLY",
                    verdict=f"毒品重量{weight:.1f}g，达到'情节特别严重'标准（≥{espe}g），⚠️ 法定刑死刑",
                    confidence="高", confidence_note="全国统一标准",
                    legal_basis=basis,
                )

        # ── 故意伤害罪（以伤情参考赔偿金额判断量刑档次）─────────
        elif ct in ("故意伤害罪", "injury", "故意伤害"):
            # 故意伤害罪不以金额入罪，但可按赔偿金额估算量刑档次
            data = self.injury_thresholds.get(pk, self.injury_thresholds["DEFAULT"])
            serious_min = data.get("serious_min", 30000)
            fatal_min = data.get("fatal_min", 100000)
            basis = "《刑法》第234条"

            if amt < 1:
                return ThresholdResult(
                    crime_type="故意伤害罪", province=province or pk,
                    amount=amt, threshold=0,
                    level="INJURY_SLIGHT",
                    verdict=f"❌ 金额{amt:.0f}元不足判断伤情，故意伤害罪以伤情定罪（非金额）",
                    confidence="中", confidence_note="轻伤即入罪，赔偿金额仅用于量刑参考",
                    legal_basis=basis,
                )
            elif amt < serious_min:
                return ThresholdResult(
                    crime_type="故意伤害罪", province=province or pk,
                    amount=amt, threshold=0,
                    level="INJURY_SLIGHT",
                    verdict=f"赔偿金额{amt:.0f}元，参考轻伤档次，✅ 涉嫌故意伤害罪（轻伤），法定刑3年以下",
                    confidence="中", confidence_note=f"赔偿金额<{serious_min}元，推定轻伤",
                    legal_basis=basis,
                )
            elif amt < fatal_min:
                return ThresholdResult(
                    crime_type="故意伤害罪", province=province or pk,
                    amount=amt, threshold=0,
                    level="INJURY_SERIOUS",
                    verdict=f"赔偿金额{amt:.0f}元，参考重伤档次，⚠️ 涉嫌故意伤害罪（重伤），法定刑3-10年",
                    confidence="中", confidence_note=f"赔偿金额{serious_min}-{fatal_min}元，推定重伤",
                    legal_basis=basis,
                )
            else:
                return ThresholdResult(
                    crime_type="故意伤害罪", province=province or pk,
                    amount=amt, threshold=0,
                    level="INJURY_FATAL",
                    verdict=f"赔偿金额{amt:.0f}元，参考致人死亡/严重残疾档次，⚠️ 涉嫌故意伤害罪（致死/致残），法定刑10年以上/死刑",
                    confidence="中", confidence_note=f"赔偿金额≥{fatal_min}元，推定致人死亡/严重残疾",
                    legal_basis=basis,
                )

        # ── 不支持的罪名 ────────────────────────────────────────
        return ThresholdResult(
            crime_type=ct, province=province or "未指定",
            amount=amt, threshold=0,
            level="UNKNOWN",
            verdict="❌ 系统暂不支持该罪名的入罪门槛判断，请人工查阅司法解释",
            confidence="低", confidence_note="暂不支持的罪名类型",
            legal_basis="需人工核查",
        )

    def get_all_supported_crimes(self) -> List[str]:
        return [
            "盗窃罪", "诈骗罪", "抢夺罪", "职务侵占罪",
            "故意伤害罪", "毒品犯罪", "开设赌场罪",
        ]

    def get_drug_types(self) -> List[str]:
        """获取支持的毒品种类"""
        return list(self.drug_thresholds.keys())

    def check_drug_threshold(self, drug_name: str, weight_grams: float) -> ThresholdResult:
        """专门检查毒品犯罪的入罪门槛"""
        # 模糊匹配毒品种类
        drug_name = drug_name.strip()
        matched_key = None
        for key in self.drug_thresholds:
            if drug_name in key or key in drug_name:
                matched_key = key
                break
        if not matched_key:
            # 默认用冰毒
            matched_key = "冰毒"

        data = self.drug_thresholds[matched_key]
        std = data["standard"]
        serious = data["serious"]
        espe = data["especially"]

        if weight_grams < std:
            return ThresholdResult(
                crime_type="毒品犯罪", province="（全国统一标准）",
                amount=weight_grams, threshold=std,
                level="NOT_CRIME",
                verdict=f"[{matched_key}] 重量{weight_grams:.1f}g < {std}g入罪门槛，❌ 不构成毒品犯罪",
                confidence="高", confidence_note=f"以{matched_key}标准计",
                legal_basis="《刑法》第347条",
            )
        elif weight_grams < serious:
            return ThresholdResult(
                crime_type="毒品犯罪", province="（全国统一标准）",
                amount=weight_grams, threshold=std,
                level="DRUG_STANDARD",
                verdict=f"[{matched_key}] 重量{weight_grams:.1f}g，达到入罪标准（≥{std}g），✅ 涉嫌毒品犯罪",
                confidence="高", confidence_note=f"以{matched_key}标准计",
                legal_basis="《刑法》第347条",
            )
        elif weight_grams < espe:
            return ThresholdResult(
                crime_type="毒品犯罪", province="（全国统一标准）",
                amount=weight_grams, threshold=std,
                level="DRUG_SERIOUS",
                verdict=f"[{matched_key}] 重量{weight_grams:.1f}g，≥{serious}g，⚠️ 情节严重，法定刑15年以上/死刑",
                confidence="高", confidence_note=f"以{matched_key}标准计",
                legal_basis="《刑法》第347条",
            )
        else:
            return ThresholdResult(
                crime_type="毒品犯罪", province="（全国统一标准）",
                amount=weight_grams, threshold=std,
                level="DRUG_ESPECIALLY",
                verdict=f"[{matched_key}] 重量{weight_grams:.1f}g，≥{espe}g，⚠️ 情节特别严重，法定刑死刑",
                confidence="高", confidence_note=f"以{matched_key}标准计",
                legal_basis="《刑法》第347条",
            )


def main():
    import argparse
    parser = argparse.ArgumentParser(description="入罪门槛查询")
    parser.add_argument("--crime", type=str, required=True, help="罪名类型")
    parser.add_argument("--amount", type=float, help="涉案金额（元）或毒品重量（克）")
    parser.add_argument("--province", type=str, help="省份")
    parser.add_argument("--list-crimes", action="store_true", help="列出所有支持的罪名")
    parser.add_argument("--list-drugs", action="store_true", help="列出所有毒品种类")
    args = parser.parse_args()

    db = ThresholdDB()

    if args.list_crimes:
        print("支持的罪名：")
        for c in db.get_all_supported_crimes():
            t = db.get_threshold(c, "北京")
            note = t.get("standard_note", t.get("threshold_note", ""))
            print(f"  • {c} — {note}")
        return

    if args.list_drugs:
        print("支持的毒品种类及入罪标准（克）：")
        for drug, data in db.drug_thresholds.items():
            print(f"  • {drug}: 入罪≥{data['standard']}g, 情节严重≥{data['serious']}g, 情节特别严重≥{data['especially']}g")
        return

    if args.amount is not None:
        r = db.check_threshold(args.province, args.crime, args.amount)
        print(f"罪名: {r.crime_type}")
        print(f"省份: {r.province}")
        print(f"涉案金额: {r.amount:.0f}{'g（毒品重量）' if 'drug' in r.crime_type.lower() or '毒品' in r.crime_type else '元'}")
        print(f"入罪门槛: {r.threshold}{'g' if r.threshold and r.threshold > 0 and 'drug' in r.crime_type.lower() or '毒品' in r.crime_type else '元'}")
        print(f"量刑档次: {r.level}")
        print(f"结论: {r.verdict}")
        print(f"置信度: {r.confidence} — {r.confidence_note}")
        print(f"法律依据: {r.legal_basis}")
    else:
        t = db.get_threshold(args.crime, args.province)
        print(f"罪名: {t.get('crime_type', args.crime)}")
        print(f"省份: {t.get('province', args.province)}")
        for k, v in t.items():
            if k not in ("crime_type", "province"):
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
