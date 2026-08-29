# -*- coding: utf-8 -*-
"""
入罪门槛 API - threshold_api.py

提供各省市各罪名入罪门槛的查询和对比接口：
- GET /api/threshold?crime=盗窃罪        → 所有省份门槛
- GET /api/threshold?crime=盗窃罪&province=北京  → 单一省份详情
- GET /api/threshold?amount=5000&crime=盗窃罪  → 判断是否达到入罪标准
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from threshold_db import (
    THEFT_THRESHOLDS,
    FRAUD_THRESHOLDS,
    ROBBERY_THRESHOLDS,
    INJURY_THRESHOLDS,
    DRUG_THRESHOLDS,
    GAMBLING_THRESHOLDS,
    EMBEZZLEMENT_THRESHOLDS,
)

CRIME_THRESHOLDS = {
    "盗窃罪": THEFT_THRESHOLDS,
    "诈骗罪": FRAUD_THRESHOLDS,
    "抢夺罪": ROBBERY_THRESHOLDS,
    "故意伤害罪": INJURY_THRESHOLDS,
    "毒品犯罪": DRUG_THRESHOLDS,
    "开设赌场罪": GAMBLING_THRESHOLDS,
    "职务侵占罪": EMBEZZLEMENT_THRESHOLDS,
}

CRIME_LABELS = {
    "盗窃罪": "盗窃罪",
    "诈骗罪": "诈骗罪",
    "抢夺罪": "抢夺罪",
    "行贿罪": "行贿罪",
    "受贿罪": "受贿罪",
    "故意伤害罪": "故意伤害罪（致人重伤/死亡）",
    "毒品犯罪": "毒品犯罪",
    "开设赌场罪": "开设赌场罪",
    "职务侵占罪": "职务侵占罪",
}


def list_thresholds(crime: str = None, amount: float = None):
    """列出门槛数据

    Args:
        crime: 罪名过滤（如 "盗窃罪"）
        amount: 可选，判断该金额在哪些省份达到入罪门槛

    Returns:
        dict: {crime: str, thresholds: [...]}
    """
    crimes = [crime] if crime and crime in CRIME_THRESHOLDS else list(CRIME_THRESHOLDS.keys())
    result = {"crime": crime, "thresholds": []}

    for c in crimes:
        thresholds = CRIME_THRESHOLDS.get(c, {})
        for province, data in thresholds.items():
            threshold = data.get("low", 0)
            reached = None
            if amount is not None and amount > 0:
                reached = amount >= threshold

            result["thresholds"].append({
                "province": province,
                "crime": c,
                "crime_label": CRIME_LABELS.get(c, c),
                "threshold_yuan": threshold,
                "threshold_wan": round(threshold / 10000, 2),
                "standard": data.get("standard", ""),
                "reached": reached,
                "legal_basis": data.get("legal_basis", ""),
            })

    # 按门槛金额排序
    result["thresholds"].sort(key=lambda x: x["threshold_yuan"])
    return result


def compare_provinces(crime: str, provinces: list = None):
    """对比多个省份的同一罪名门槛差异"""
    thresholds = CRIME_THRESHOLDS.get(crime, {})
    provinces = provinces or list(thresholds.keys())
    rows = []
    for p in provinces:
        if p in thresholds:
            data = thresholds[p]
            rows.append({
                "province": p,
                "threshold_yuan": data.get("low", 0),
                "threshold_wan": round(data.get("low", 0) / 10000, 2),
                "standard": data.get("standard", ""),
                "legal_basis": data.get("legal_basis", ""),
            })
    rows.sort(key=lambda x: x["threshold_yuan"])
    return {"crime": crime, "crime_label": CRIME_LABELS.get(crime, crime), "rows": rows}


if __name__ == "__main__":
    # CLI 测试
    import json
    print(json.dumps(list_thresholds("盗窃罪"), ensure_ascii=False, indent=2))
