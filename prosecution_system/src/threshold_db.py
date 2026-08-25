# -*- coding: utf-8 -*-
"""
入罪门槛数据库 - prosecution_system/src/threshold_db.py

功能：
- 提供各省市盗窃罪、诈骗罪等罪名的入罪数额标准
- 判断具体金额是否达到立案追诉门槛
- 输出省份差异提示

法律依据：
- 盗窃罪：最高法最高检《关于办理盗窃刑事案件适用法律若干问题的解释》(2013)
- 诈骗罪：最高法《关于审理诈骗刑事案件具体应用法律若干问题的解释》(2022)
- 抢夺罪：最高法最高检《关于办理抢夺刑事案件适用法律若干问题的解释》(2013)
- 开设赌场罪：最高法最高检《关于办理赌博刑事案件具体应用法律若干问题的解释》(2010)

⚠️ 注意：以下数据基于公开司法解释，省份具体标准可能存在微调，
  使用前请以当地高院最新实施细则为准。
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass


# ---- 各省市盗窃罪数额标准（元）----
# 2013年解释第1条：盗窃公私财物价值一千元至三万元以上为"数额较大"
# 各省可在上述幅度内确定本地标准（通常分三类地区）

THEFT_THRESHOLDS: Dict[str, Dict[str, int]] = {
    # 省份 -> {low: 一类地区（经济发达）, mid: 二类地区, high: 三类地区（经济欠发达）}
    "北京": {"low": 2000, "mid": 2000, "high": 2000, "standard": "2000元"},
    "上海": {"low": 1000, "mid": 1000, "high": 1000, "standard": "1000元"},
    "浙江": {"low": 3000, "mid": 3000, "high": 3000, "standard": "3000元（杭州、宁波）"},
    "江苏": {"low": 2000, "mid": 2000, "high": 2000, "standard": "2000元"},
    "广东": {"low": 3000, "mid": 2000, "high": 1000, "standard": "3000/2000/1000元（分地区）"},
    "深圳": {"low": 3000, "mid": 3000, "high": 3000, "standard": "3000元"},
    "广州": {"low": 3000, "mid": 3000, "high": 3000, "standard": "3000元"},
    "天津": {"low": 2000, "mid": 2000, "high": 2000, "standard": "2000元"},
    "重庆": {"low": 2000, "mid": 2000, "high": 2000, "standard": "2000元"},
    "四川": {"low": 1600, "mid": 1600, "high": 1600, "standard": "1600元"},
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

# 盗窃罪"数额巨大"标准（元）
THEFT_MASSIVE: Dict[str, int] = {
    "DEFAULT": 30000,
    "北京": 100000, "上海": 100000, "浙江": 80000, "江苏": 80000,
    "广东": 60000, "深圳": 60000, "福建": 60000, "天津": 60000,
    "重庆": 60000, "四川": 60000, "湖北": 60000, "湖南": 60000,
}

# 盗窃罪"数额特别巨大"标准（元）
THEFT_ESPECIALLY_MASSIVE: Dict[str, int] = {
    "DEFAULT": 300000,
    "北京": 500000, "上海": 500000, "浙江": 400000, "江苏": 400000,
    "广东": 300000, "深圳": 300000, "福建": 300000,
}

# 诈骗罪数额标准（元）
FRAUD_THRESHOLDS: Dict[str, Dict[str, int]] = {
    "DEFAULT": {"amount_standard": 5000, "massive": 50000, "especially_massive": 500000},
    "北京": {"amount_standard": 5000, "massive": 100000, "especially_massive": 500000},
    "上海": {"amount_standard": 5000, "massive": 100000, "especially_massive": 500000},
    "浙江": {"amount_standard": 6000, "massive": 100000, "especially_massive": 500000},
    "广东": {"amount_standard": 6000, "massive": 50000, "especially_massive": 500000},
    "江苏": {"amount_standard": 6000, "massive": 50000, "especially_massive": 500000},
    "深圳": {"amount_standard": 6000, "massive": 50000, "especially_massive": 500000},
}

# 抢夺罪数额标准（元）
ROBBERY_THRESHOLDS: Dict[str, int] = {
    "DEFAULT": 1000,
    "北京": 2000, "上海": 2000, "浙江": 3000, "江苏": 2000,
    "广东": 3000, "天津": 2000, "重庆": 2000, "四川": 1000,
    "西藏": 500, "内蒙古": 1000, "新疆": 1000,
}

# 开设赌场罪"情节严重"标准
GAMBLING_THRESHOLDS = {
    "DEFAULT": {"regular": "抽头渔利5000元以上/赌资50000元以上/参赌人数20人以上"},
}


@dataclass
class ThresholdResult:
    crime_type: str
    province: str
    amount: float
    threshold: int
    level: str  # NOT_CRIME / AMOUNT_LARGE / MASSIVE / ESPECIALLY_MASSIVE
    verdict: str  # 结论描述
    confidence: str  # 高/中/低
    confidence_note: str  # 置信度说明
    legal_basis: str  # 法律依据


def _get_province_key(province: str, db: Dict[str, Any]) -> str:
    """匹配省份名称到数据库key"""
    if not province:
        return "DEFAULT"
    province = province.strip()
    if province in db:
        return province
    # 模糊匹配
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
                "legal_basis": "最高法最高检《关于办理盗窃刑事案件适用法律若干问题的解释》第1条",
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
                "legal_basis": "最高法最高检《关于办理抢夺刑事案件适用法律若干问题的解释》第1条",
            }
        elif ct in ("开设赌场罪", "gambling", "开设赌场"):
            return {
                "crime_type": "开设赌场罪",
                "province": pk if pk != "DEFAULT" else "（全国默认）",
                "threshold_note": self.gambling_thresholds["DEFAULT"]["regular"],
                "legal_basis": "最高法最高检《关于办理赌博刑事案件具体应用法律若干问题的解释》第1条",
            }
        else:
            return {
                "crime_type": ct,
                "province": province or "（未指定）",
                "error": "暂不支持该罪名的门槛查询",
                "supported": ["盗窃罪", "诈骗罪", "抢夺罪", "开设赌场罪"],
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

        if ct in ("盗窃罪", "theft", "盗窃"):
            data = self.theft_thresholds.get(pk, self.theft_thresholds["DEFAULT"])
            large = data.get("low", 1000)
            massive = THEFT_MASSIVE.get(pk, THEFT_MASSIVE["DEFAULT"])
            espe = THEFT_ESPECIALLY_MASSIVE.get(pk, THEFT_ESPECIALLY_MASSIVE["DEFAULT"])
            basis = "最高法最高检《关于办理盗窃刑事案件适用法律若干问题的解释》第1条"

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
                return ThresholdResult(
                    crime_type="诈骗罪", province=province or pk,
                    amount=amt, threshold=large,
                    level="MASSIVE" if amt < espe else "ESPECIALLY_MASSIVE",
                    verdict=f"金额{amt:.0f}元，达到'{level_name}'标准，⚠️ 涉嫌诈骗罪（{level_name}）",
                    confidence="中", confidence_note="2022年解释标准",
                    legal_basis=basis,
                )

        elif ct in ("抢夺罪", "robbery", "抢夺"):
            large = self.robbery_thresholds.get(pk, self.robbery_thresholds["DEFAULT"])
            basis = "最高法最高检《关于办理抢夺刑事案件适用法律若干问题的解释》第1条"
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

        return ThresholdResult(
            crime_type=ct, province=province or "未指定",
            amount=amt, threshold=0,
            level="UNKNOWN",
            verdict="❌ 系统暂不支持该罪名的入罪门槛判断，请人工查阅司法解释",
            confidence="低", confidence_note="暂不支持的罪名类型",
            legal_basis="需人工核查",
        )

    def get_all_supported_crimes(self) -> List[str]:
        return ["盗窃罪", "诈骗罪", "抢夺罪", "开设赌场罪"]


def main():
    import argparse
    parser = argparse.ArgumentParser(description="入罪门槛查询")
    parser.add_argument("--crime", type=str, required=True, help="罪名类型")
    parser.add_argument("--amount", type=float, help="涉案金额（元）")
    parser.add_argument("--province", type=str, help="省份")
    args = parser.parse_args()

    db = ThresholdDB()
    if args.amount is not None:
        r = db.check_threshold(args.province, args.crime, args.amount)
        print(f"罪名: {r.crime_type}")
        print(f"省份: {r.province}")
        print(f"涉案金额: {r.amount:.0f}元")
        print(f"入罪门槛: {r.threshold}元")
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
