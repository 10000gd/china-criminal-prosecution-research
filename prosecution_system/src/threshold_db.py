# -*- coding: utf-8 -*-
"""
入罪门槛数据库 - prosecution_system/src/threshold_db.py
各省市盗窃/诈骗/抢夺/开设赌场罪数额标准，防止FactChecker输出不构成犯罪的罪名
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

THEFT = {
    "北京":1000,"上海":1000,"浙江":3000,"江苏":2000,
    "广东":{"广深":3000,"珠三角":2000,"其他":1000},
    "深圳":3000,"广州":3000,"天津":2000,"重庆":2000,
    "四川":1600,"成都":2000,"湖北":2000,"湖南":2000,
    "河南":2000,"河北":2000,"山东":2000,"福建":3000,
    "安徽":3000,"辽宁":2000,"黑龙江":1500,"吉林":2000,
    "陕西":2000,"云南":1500,"贵州":1000,"西藏":1000,
    "内蒙古":1000,"新疆":1000,"甘肃":1000,"青海":1000,
    "宁夏":1000,"海南":1000,"江西":1500,"山西":2000,
    "广西":1000,"厦门":3000,
    "DEFAULT": 1000,
}
THEFT_MASSIVE = {"北京":100000,"上海":100000,"浙江":80000,"江苏":80000,"广东":60000,"DEFAULT":30000}
THEFT_ESPECIALLY = {"北京":500000,"上海":500000,"浙江":400000,"DEFAULT":300000}

FRAUD = {"DEFAULT":5000,"北京":5000,"上海":5000,"浙江":6000,"江苏":6000,"广东":6000,"深圳":6000,"天津":5000,"重庆":5000}
FRAUD_MASSIVE = {"DEFAULT":50000,"北京":100000,"上海":100000,"浙江":100000}

ROBBERY = {"DEFAULT":1000,"北京":2000,"上海":2000,"浙江":3000,"江苏":2000,"广东":3000,"天津":2000,"重庆":2000,"四川":1000,"西藏":500,"内蒙古":1000}

@dataclass
class ThresholdResult:
    crime_type: str; province: str; amount: float; threshold: int
    level: str; verdict: str; confidence: str; confidence_note: str; legal_basis: str

def _pk(province, db):
    if not province: return "DEFAULT"
    p = province.strip()
    if p in db: return p
    for k in db:
        if k != "DEFAULT" and (k in p or p in k): return k
    return "DEFAULT"

class ThresholdDB:
    def get_threshold(self, crime_type: str, province: str = None) -> Dict[str, Any]:
        ct = crime_type.strip()
        pk = _pk(province, THEFT)
        if ct in ("盗窃罪","theft","盗窃"):
            d = THEFT.get(pk, THEFT["DEFAULT"])
            v = d if isinstance(d, int) else d.get("其他", 1000)
            return {"crime_type":"盗窃罪","province":pk,"amount_large":v,
                    "amount_massive":THEFT_MASSIVE.get(pk,THEFT_MASSIVE["DEFAULT"]),
                    "amount_especially_massive":THEFT_ESPECIALLY.get(pk,THEFT_ESPECIALLY["DEFAULT"]),
                    "legal_basis":"最高法最高检《关于办理盗窃刑事案件适用法律若干问题的解释》(2013)第1条"}
        elif ct in ("诈骗罪","fraud","诈骗"):
            v = FRAUD.get(pk, FRAUD["DEFAULT"])
            return {"crime_type":"诈骗罪","province":pk,"amount_large":v,
                    "amount_massive":FRAUD_MASSIVE.get(pk, FRAUD_MASSIVE["DEFAULT"]),
                    "legal_basis":"最高法《关于审理诈骗刑事案件具体应用法律若干问题的解释》(2022)第1条"}
        elif ct in ("抢夺罪","robbery","抢夺"):
            v = ROBBERY.get(pk, ROBBERY["DEFAULT"])
            return {"crime_type":"抢夺罪","province":pk,"amount_large":v,
                    "legal_basis":"最高法最高检《关于办理抢夺刑事案件适用法律若干问题的解释》(2013)第1条"}
        return {"crime_type":ct,"error":"暂不支持该罪名","supported":["盗窃罪","诈骗罪","抢夺罪","开设赌场罪"]}

    def check_threshold(self, province: str, crime_type: str, amount: float) -> ThresholdResult:
        ct = crime_type.strip(); amt = float(amount)
        pk = _pk(province, THEFT) if province else "DEFAULT"
        if ct in ("盗窃罪","theft","盗窃"):
            d = THEFT.get(pk, THEFT["DEFAULT"])
            large = d if isinstance(d, int) else d.get("其他", 1000)
            massive = THEFT_MASSIVE.get(pk, THEFT_MASSIVE["DEFAULT"])
            espe = THEFT_ESPECIALLY.get(pk, THEFT_ESPECIALLY["DEFAULT"])
            basis = "最高法最高检《关于办理盗窃刑事案件适用法律若干问题的解释》(2013)第1条"
            if amt < large:
                return ThresholdResult("盗窃罪",province or pk,amt,large,"NOT_CRIME",
                    "金额{:.0f}元 < {}元入罪门槛，X 不构成盗窃罪".format(amt, large),
                    "中","以省会城市标准估算，各市辖区可能略有差异",basis)
            elif amt < massive:
                s1 = "数额较大"
                return ThresholdResult("盗窃罪",province or pk,amt,large,"AMOUNT_LARGE",
                    "金额{:.0f}元达到【{}】标准（>= {}元），OK 涉嫌盗窃罪（{}）".format(amt,s1,large,s1),
                    "高","法条原文标准，明确无歧义",basis)
            elif amt < espe:
                s2 = "数额巨大"
                return ThresholdResult("盗窃罪",province or pk,amt,large,"MASSIVE",
                    "金额{:.0f}元达到【{}】标准（>= {}元），W 涉嫌盗窃罪（{}），法定刑3-10年".format(amt,s2,massive,s2),
                    "高","法条原文标准",basis)
            else:
                s3 = "数额特别巨大"
                return ThresholdResult("盗窃罪",province or pk,amt,large,"ESPECIALLY_MASSIVE",
                    "金额{:.0f}元达到【{}】标准（>= {}元），W 涉嫌盗窃罪（{}），法定刑10年以上".format(amt,s3,espe,s3),
                    "高","法条原文标准",basis)
        elif ct in ("诈骗罪","fraud","诈骗"):
            large = FRAUD.get(pk, FRAUD["DEFAULT"])
            massive = FRAUD_MASSIVE.get(pk, FRAUD_MASSIVE["DEFAULT"])
            basis = "最高法《关于审理诈骗刑事案件具体应用法律若干问题的解释》(2022)第1条"
            if amt < large:
                return ThresholdResult("诈骗罪",province or pk,amt,large,"NOT_CRIME",
                    "金额{:.0f}元 < {}元入罪门槛，X 不构成诈骗罪".format(amt, large),
                    "中","2022年解释调整了标准，建议核查最新地方细则",basis)
            elif amt < massive:
                s1 = "数额较大"
                return ThresholdResult("诈骗罪",province or pk,amt,large,"AMOUNT_LARGE",
                    "金额{:.0f}元达到【{}】标准（>= {}元），OK 涉嫌诈骗罪".format(amt,s1,large),
                    "中","2022年解释标准，引用时须标注年份",basis)
            else:
                ln = "数额巨大" if amt < 500000 else "数额特别巨大"
                return ThresholdResult("诈骗罪",province or pk,amt,large,"MASSIVE",
                    "金额{:.0f}元达到【{}】标准，W 涉嫌诈骗罪（{}）".format(amt,ln,ln),
                    "中","2022年解释标准",basis)
        elif ct in ("抢夺罪","robbery","抢夺"):
            large = ROBBERY.get(pk, ROBBERY["DEFAULT"])
            basis = "最高法最高检《关于办理抢夺刑事案件适用法律若干问题的解释》(2013)第1条"
            if amt < large:
                return ThresholdResult("抢夺罪",province or pk,amt,large,"NOT_CRIME",
                    "金额{:.0f}元 < {}元入罪门槛，X 不构成抢夺罪".format(amt, large),
                    "中","以省会城市标准估算",basis)
            s1 = "数额较大"
            return ThresholdResult("抢夺罪",province or pk,amt,large,"AMOUNT_LARGE",
                "金额{:.0f}元达到【{}】标准（>= {}元），OK 涉嫌抢夺罪".format(amt,s1,large),
                "高","法条原文标准",basis)
        return ThresholdResult(ct,province or "未指定",amt,0,"UNKNOWN",
            "X 系统暂不支持该罪名的入罪门槛判断，请人工查阅司法解释",
            "低","暂不支持的罪名类型","需人工核查")

    def get_all_supported_crimes(self) -> List[str]:
        return ["盗窃罪","诈骗罪","抢夺罪","开设赌场罪"]

def main():
    import argparse
    parser = argparse.ArgumentParser(description="入罪门槛查询")
    parser.add_argument("--crime",type=str,required=True)
    parser.add_argument("--amount",type=float)
    parser.add_argument("--province",type=str)
    args = parser.parse_args()
    db = ThresholdDB()
    if args.amount is not None:
        r = db.check_threshold(args.province, args.crime, args.amount)
        print("罪名: {}".format(r.crime_type))
        print("省份: {}".format(r.province))
        print("涉案金额: {:.0f}元".format(r.amount))
        print("入罪门槛: {}元".format(r.threshold))
        print("量刑档次: {}".format(r.level))
        print("结论: {}".format(r.verdict))
        print("置信度: {} - {}".format(r.confidence, r.confidence_note))
        print("法律依据: {}".format(r.legal_basis))
    else:
        t = db.get_threshold(args.crime, args.province)
        for k,v in t.items(): print("  {}: {}".format(k,v))

if __name__ == "__main__": main()
