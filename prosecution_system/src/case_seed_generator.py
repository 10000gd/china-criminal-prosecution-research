# -*- coding: utf-8 -*-
"""
案件种子数据生成器 - prosecution_system/src/case_seed_generator.py

生成真实感的模拟案件 YAML 文件，支持批量导入到 CaseLoader。
用法:
  python -m case_seed_generator --count 20 --output-dir cases/
  python -m case_seed_generator --import  # 导入到 CaseLoader
  python -m case_seed_generator --seed 50  # 生成50个案件并立即导入
"""

import argparse
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

import yaml

# ── 真实感数据字典 ──────────────────────────────────────────────

CRIME_TYPES = ["盗窃罪", "诈骗罪", "抢夺罪", "职务侵占罪", "故意伤害罪", "毒品犯罪", "开设赌场罪"]

PROVINCES = [
    "北京", "上海", "浙江", "江苏", "广东", "深圳", "天津", "重庆",
    "四川", "湖北", "湖南", "河南", "河北", "山东", "福建", "辽宁",
    "黑龙江", "吉林", "陕西", "云南", "贵州", "安徽", "江西", "山西",
    "广西", "海南", "内蒙古", "新疆", "甘肃", "青海", "宁夏", "西藏",
]

PERSON_NAMES = [
    "张三", "李四", "王五", "赵六", "孙七", "周八", "吴九", "郑十",
    "刘一", "陈二", "杨明", "黄磊", "周杰", "吴昊", "徐鹏", "孙超",
    "马超", "朱琳", "胡军", "郭靖", "林志", "何平", "高建", "罗锋",
]

COMPANY_NAMES = [
    "华盛贸易有限公司", "中金科技有限公司", "宏达物流有限公司",
    "鹏程建筑装饰工程有限公司", "天成电子科技有限公司", "龙华矿业有限公司",
    "金桥供应链管理有限公司", "瑞丰医疗器械有限公司", "恒通投资有限公司",
    "盛世电子商务有限公司", "华泰汽车销售有限公司", "中兴通讯股份有限公司",
]

PERSON_LAST_NAMES = ["张", "李", "王", "赵", "孙", "周", "吴", "郑", "刘", "陈", "杨", "黄"]
PERSON_FIRST_NAMES = ["伟", "芳", "娜", "敏", "静", "丽", "强", "磊", "军", "杰"]

# ── 金额范围配置（按罪名）───────────────────────────────────────

AMOUNT_RANGES: Dict[str, tuple] = {
    "盗窃罪":        (800, 800000),
    "诈骗罪":        (3000, 500000),
    "抢夺罪":        (500, 100000),
    "职务侵占罪":    (20000, 3000000),
    "故意伤害罪":    (0, 200000),      # 赔偿金额，非涉案金额
    "毒品犯罪":      (5, 500),          # 克数
    "开设赌场罪":    (10000, 500000),   # 赌资/抽头
}

# ── 量刑情节词库 ───────────────────────────────────────────────

AGGRAVATING = [
    "多次作案", "流窜作案", "有组织犯罪", "惯犯", "累犯",
    "拒不认罪", "毁灭证据", "威胁证人", "跨境犯罪", "涉案人数众多",
]

MITIGATING = [
    "初犯", "偶犯", "自首", "坦白", "认罪认罚", "退赃退赔",
    "取得谅解", "从犯", "胁从犯", "犯罪中止", "未成年人",
]

EVIDENCE_GAPS_TEMPLATES = [
    "现场监控录像不完整，关键时段存在盲区",
    "电子数据（微信记录/银行流水）尚未全面调取",
    "证人证言之间存在矛盾，需进一步核实",
    "涉案物品价格鉴定意见尚未作出",
    "被告人口供反复，存在合理怀疑",
    "指纹/DNA 比对结果未最终确认",
    "涉案资金流向追踪不完整，存在断点",
    "伤情鉴定结论尚未正式送达",
    "毒品含量鉴定未完成，影响量刑档次认定",
]

LEGAL_ARGUMENTS = [
    "无罪辩护：指控证据链不完整，不能排除合理怀疑",
    "罪轻辩护：被告人系从犯，应从轻或减轻处罚",
    "罪轻辩护：存在自首情节，依法可以从轻或减轻处罚",
    "量刑辩护：已全额退赃，被害人出具谅解书，请求从轻处罚",
    "程序辩护：侦查阶段存在超期羁押，程序违法",
    "定性辩护：指控罪名定性错误，应认定为较轻罪名",
    "数额辩护：涉案金额认定有误，鉴定意见存在瑕疵",
]


def _rand(amount_range: tuple) -> float:
    return round(random.uniform(*amount_range), 2)


def _rand_int(min_v: int, max_v: int) -> int:
    return random.randint(min_v, max_v)


def _pick(lst: List[str], n: int = 1) -> List[str]:
    return random.sample(lst, min(n, len(lst)))


def _date_str(days_ago: int = 0) -> str:
    d = datetime.now() - timedelta(days=days_ago)
    return d.strftime("%Y-%m-%d")


def _uuid_short() -> str:
    return str(uuid.uuid4())[:8].upper()


def _case_id(index: int) -> str:
    return f"CASE-{index:04d}"


def _gen_theft_case(case_id: str, province: str) -> Dict:
    amount = _rand(AMOUNT_RANGES["盗窃罪"])
    thresholds = {2000: "数额较大", 30000: "数额巨大", 300000: "数额特别巨大"}
    level = next((v for k, v in thresholds.items() if amount < k), "数额特别巨大")
    return {
        "meta": {
            "case_id": case_id,
            "case_name": f"{province}市盗窃案",
            "status": random.choice(["active", "completed", "draft"]),
            "province": province,
            "created_at": _date_str(_rand_int(1, 180)),
        },
        "case_info": {
            "crime_type": "盗窃罪",
            "province": province,
            "amount": amount,
            "level": level,
            "description": f"被告人{_pick(PERSON_NAMES)[0]}在{province}市{_pick(['商场', '超市', '居民小区', '写字楼', '停车场'])[0]}内，趁无人之机秘密窃取他人财物，涉案金额{amount:.0f}元。",
            "arrest_date": _date_str(_rand_int(1, 90)),
            "prosecution_date": _date_str(_rand_int(0, 30)),
        },
        "charges": {
            "primary": {
                "article": "刑法第264条",
                "name": "盗窃罪",
                "amount": amount,
                "level": level,
                "recommended_sentence": f"{_rand_int(1, 10)}年有期徒刑" if level != "数额较大" else f"{_rand_int(3, 12)}个月拘役/有期徒刑",
            }
        },
        "defendants_person": _pick(PERSON_NAMES, _rand_int(1, 3)),
        "defendants_corp": [],
        "victims": [f"被害人{_rand_int(1, 999)}" for _ in range(_rand_int(1, 4))],
        "evidence_gaps": _pick(EVIDENCE_GAPS_TEMPLATES, _rand_int(1, 3)),
        "assets": {
            "stolen_property_value": amount,
            "recovered_value": round(amount * random.uniform(0, 1), 2),
            "recovery_rate": round(random.uniform(0, 1), 3),
        },
        "comparable_cases": {
            "reference": [
                {
                    "case_name": f"{province}中院盗窃案",
                    "amount": round(amount * random.uniform(0.8, 1.2), 0),
                    "sentence": f"{_rand_int(1, 5)}年有期徒刑",
                }
            ]
        },
        "hallucination_rate": round(random.uniform(0.05, 0.25), 3),
        "confidence_score": round(random.uniform(0.65, 0.90), 2),
        "legal_arguments": _pick(LEGAL_ARGUMENTS, _rand_int(1, 2)),
        "aggravating_factors": _pick(AGGRAVATING, _rand_int(0, 2)),
        "mitigating_factors": _pick(MITIGATING, _rand_int(0, 3)),
    }


def _gen_fraud_case(case_id: str, province: str) -> Dict:
    amount = _rand(AMOUNT_RANGES["诈骗罪"])
    level = "数额较大" if amount < 50000 else ("数额巨大" if amount < 500000 else "数额特别巨大")
    return {
        "meta": {
            "case_id": case_id,
            "case_name": f"{province}市电信诈骗案",
            "status": random.choice(["active", "completed", "draft"]),
            "province": province,
            "created_at": _date_str(_rand_int(1, 180)),
        },
        "case_info": {
            "crime_type": "诈骗罪",
            "province": province,
            "amount": amount,
            "level": level,
            "description": f"被告人{_pick(PERSON_NAMES)[0]}伙同他人在{province}市通过电信网络实施诈骗犯罪，虚构事实骗取被害人信任，涉案金额{amount:.0f}元。",
            "arrest_date": _date_str(_rand_int(1, 90)),
            "prosecution_date": _date_str(_rand_int(0, 30)),
        },
        "charges": {
            "primary": {
                "article": "刑法第266条",
                "name": "诈骗罪",
                "amount": amount,
                "level": level,
                "recommended_sentence": f"{_rand_int(3, 15)}年有期徒刑",
            }
        },
        "defendants_person": _pick(PERSON_NAMES, _rand_int(1, 5)),
        "defendants_corp": _pick(COMPANY_NAMES, _rand_int(0, 2)),
        "victims": [f"被害人{_rand_int(1, 999)}" for _ in range(_rand_int(1, 10))],
        "evidence_gaps": _pick(EVIDENCE_GAPS_TEMPLATES, _rand_int(1, 3)),
        "assets": {
            "defrauded_amount": amount,
            "recovered_amount": round(amount * random.uniform(0, 0.6), 2),
            "recovery_rate": round(random.uniform(0, 0.6), 3),
        },
        "comparable_cases": {
            "reference": [
                {
                    "case_name": f"{province}高院诈骗案",
                    "amount": round(amount * random.uniform(0.8, 1.2), 0),
                    "sentence": f"{_rand_int(3, 10)}年有期徒刑",
                }
            ]
        },
        "hallucination_rate": round(random.uniform(0.08, 0.30), 3),
        "confidence_score": round(random.uniform(0.60, 0.88), 2),
        "legal_arguments": _pick(LEGAL_ARGUMENTS, _rand_int(1, 2)),
        "aggravating_factors": _pick(AGGRAVATING, _rand_int(0, 3)),
        "mitigating_factors": _pick(MITIGATING, _rand_int(0, 3)),
    }


def _gen_embezzlement_case(case_id: str, province: str) -> Dict:
    amount = _rand(AMOUNT_RANGES["职务侵占罪"])
    level = "数额较大" if amount < 1000000 else "数额巨大"
    return {
        "meta": {
            "case_id": case_id,
            "case_name": f"{province}职务侵占案",
            "status": random.choice(["active", "completed", "draft"]),
            "province": province,
            "created_at": _date_str(_rand_int(1, 180)),
        },
        "case_info": {
            "crime_type": "职务侵占罪",
            "province": province,
            "amount": amount,
            "level": level,
            "description": f"被告人{_pick(PERSON_NAMES)[0]}利用在某公司担任{_pick(['财务经理', '销售总监', '采购主管', '仓库管理员', '项目经理'])[0]}的职务便利，将公司财物非法占为己有，涉案金额{amount:.0f}元。",
            "arrest_date": _date_str(_rand_int(1, 90)),
            "prosecution_date": _date_str(_rand_int(0, 30)),
        },
        "charges": {
            "primary": {
                "article": "刑法第271条",
                "name": "职务侵占罪",
                "amount": amount,
                "level": level,
                "recommended_sentence": f"{_rand_int(1, 15)}年有期徒刑",
            }
        },
        "defendants_person": _pick(PERSON_NAMES, 1),
        "defendants_corp": _pick(COMPANY_NAMES, _rand_int(1, 2)),
        "victims": [f"被害单位员工{_rand_int(1, 999)}" for _ in range(1)],
        "evidence_gaps": _pick(EVIDENCE_GAPS_TEMPLATES, _rand_int(1, 3)),
        "assets": {
            "embezzled_amount": amount,
            "recovered_amount": round(amount * random.uniform(0, 0.8), 2),
            "recovery_rate": round(random.uniform(0, 0.8), 3),
        },
        "comparable_cases": {
            "reference": [
                {
                    "case_name": f"{province}职务侵占案",
                    "amount": round(amount * random.uniform(0.8, 1.2), 0),
                    "sentence": f"{_rand_int(1, 10)}年有期徒刑",
                }
            ]
        },
        "hallucination_rate": round(random.uniform(0.05, 0.20), 3),
        "confidence_score": round(random.uniform(0.68, 0.92), 2),
        "legal_arguments": _pick(LEGAL_ARGUMENTS, _rand_int(1, 2)),
        "aggravating_factors": _pick(AGGRAVATING, _rand_int(0, 2)),
        "mitigating_factors": _pick(MITIGATING, _rand_int(0, 3)),
    }


def _gen_drug_case(case_id: str, province: str) -> Dict:
    weight = _rand(AMOUNT_RANGES["毒品犯罪"])
    drug_type = random.choice(["冰毒", "海洛因", "氯胺酮（K粉）", "大麻", "麻古"])
    level = "入罪标准" if weight < 50 else ("情节严重" if weight < 200 else "情节特别严重")
    return {
        "meta": {
            "case_id": case_id,
            "case_name": f"{province}市毒品犯罪案",
            "status": random.choice(["active", "completed", "draft"]),
            "province": province,
            "created_at": _date_str(_rand_int(1, 180)),
        },
        "case_info": {
            "crime_type": "毒品犯罪",
            "province": province,
            "drug_type": drug_type,
            "weight_grams": weight,
            "level": level,
            "description": f"被告人{_pick(PERSON_NAMES)[0]}在{province}市{_pick(['出租屋', '停车场', '酒店房间', 'KTV', '物流点'])[0]}被查获{drug_type}，重量{weight:.1f}克。",
            "arrest_date": _date_str(_rand_int(1, 90)),
            "prosecution_date": _date_str(_rand_int(0, 30)),
        },
        "charges": {
            "primary": {
                "article": "刑法第347条",
                "name": "走私/贩卖毒品罪",
                "weight_grams": weight,
                "drug_type": drug_type,
                "level": level,
                "recommended_sentence": f"{_rand_int(1, 15)}年有期徒刑至死刑",
            }
        },
        "defendants_person": _pick(PERSON_NAMES, _rand_int(1, 3)),
        "defendants_corp": [],
        "victims": [],
        "evidence_gaps": [
            "毒品含量鉴定尚未完成",
            "毒品来源尚未查清",
            "是否存在特情介入需核实",
        ],
        "assets": {
            "drug_weight": weight,
            "seized_cash": round(random.uniform(0, 50000), 2),
        },
        "comparable_cases": {
            "reference": [
                {
                    "case_name": f"{province}毒品案",
                    "weight": round(weight * random.uniform(0.8, 1.2), 1),
                    "sentence": f"{_rand_int(5, 15)}年有期徒刑",
                }
            ]
        },
        "hallucination_rate": round(random.uniform(0.03, 0.15), 3),
        "confidence_score": round(random.uniform(0.70, 0.95), 2),
        "legal_arguments": _pick(LEGAL_ARGUMENTS, _rand_int(1, 2)),
        "aggravating_factors": _pick(AGGRAVATING, _rand_int(0, 3)),
        "mitigating_factors": _pick(MITIGATING, _rand_int(0, 3)),
    }


def _gen_injury_case(case_id: str, province: str) -> Dict:
    compensation = _rand(AMOUNT_RANGES["故意伤害罪"])
    injury_level = "轻伤" if compensation < 30000 else ("重伤" if compensation < 100000 else "致死/致残")
    return {
        "meta": {
            "case_id": case_id,
            "case_name": f"{province}市故意伤害案",
            "status": random.choice(["active", "completed", "draft"]),
            "province": province,
            "created_at": _date_str(_rand_int(1, 180)),
        },
        "case_info": {
            "crime_type": "故意伤害罪",
            "province": province,
            "injury_level": injury_level,
            "compensation_demand": compensation,
            "description": f"被告人{_pick(PERSON_NAMES)[0]}因{_pick(['琐事纠纷', '债务矛盾', '情感纠葛', '生意纠纷', '邻里矛盾'])[0]}与被害人发生争执，使用{_pick(['拳脚', '菜刀', '木棍', '铁管', '砖块'])[0]}将被害人打伤，经鉴定为{injury_level}。",
            "arrest_date": _date_str(_rand_int(1, 90)),
            "prosecution_date": _date_str(_rand_int(0, 30)),
        },
        "charges": {
            "primary": {
                "article": "刑法第234条",
                "name": "故意伤害罪",
                "injury_level": injury_level,
                "recommended_sentence": f"{_rand_int(1, 15)}年有期徒刑至死刑",
            }
        },
        "defendants_person": _pick(PERSON_NAMES, 1),
        "defendants_corp": [],
        "victims": [f"被害人{_rand_int(1, 999)}"],
        "evidence_gaps": _pick(EVIDENCE_GAPS_TEMPLATES, _rand_int(1, 3)),
        "assets": {
            "compensation_demand": compensation,
            "paid_compensation": round(compensation * random.uniform(0, 0.7), 2),
        },
        "comparable_cases": {
            "reference": [
                {
                    "case_name": f"{province}故意伤害案",
                    "injury_level": injury_level,
                    "sentence": f"{_rand_int(1, 10)}年有期徒刑",
                }
            ]
        },
        "hallucination_rate": round(random.uniform(0.05, 0.20), 3),
        "confidence_score": round(random.uniform(0.65, 0.90), 2),
        "legal_arguments": _pick(LEGAL_ARGUMENTS, _rand_int(1, 2)),
        "aggravating_factors": _pick(AGGRAVATING, _rand_int(0, 2)),
        "mitigating_factors": _pick(MITIGATING, _rand_int(0, 3)),
    }


GENERATORS = {
    "盗窃罪": _gen_theft_case,
    "诈骗罪": _gen_fraud_case,
    "职务侵占罪": _gen_embezzlement_case,
    "毒品犯罪": _gen_drug_case,
    "故意伤害罪": _gen_injury_case,
    # 抢夺罪/开设赌场罪 用盗窃案结构
    "抢夺罪": _gen_theft_case,
    "开设赌场罪": _gen_theft_case,
}


def generate_case(case_id: str, province: str = None) -> Dict:
    """生成单个随机案件"""
    province = province or random.choice(PROVINCES)
    crime = random.choice(list(GENERATORS.keys()))
    return GENERATORS[crime](case_id, province)


def generate_batch(count: int, provinces: List[str] = None) -> List[Dict]:
    """生成批量案件"""
    provinces = provinces or PROVINCES
    cases = []
    for i in range(1, count + 1):
        province = provinces[i % len(provinces)]
        cases.append(generate_case(_case_id(i), province))
    return cases


def save_case(case: Dict, output_dir: Path) -> Path:
    """保存案件到 YAML 文件"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    case_id = case["meta"]["case_id"]
    filepath = output_dir / f"{case_id}.yaml"
    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(
            case,
            f,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            indent=2,
        )
    return filepath


def save_batch(cases: List[Dict], output_dir: Path) -> List[Path]:
    """批量保存案件文件"""
    return [save_case(c, output_dir) for c in cases]


# ── 导入到 CaseLoader ─────────────────────────────────────────

def import_to_case_loader(cases_dir: Path = None) -> dict:
    """将 cases_dir 下的 YAML 文件注册/导入到 CaseLoader"""
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from case_loader import CaseLoader

    cases_dir = cases_dir or Path(__file__).parent.parent / "cases"
    loader = CaseLoader(cases_dir)
    loader.rebuild_search_index()
    cases = loader.list_cases()
    return {
        "total_cases": len(cases),
        "cases_dir": str(cases_dir),
        "case_ids": [c["case_id"] for c in cases],
    }


def seed_and_import(count: int, output_dir: Path = None) -> dict:
    """生成案件 + 导入到 CaseLoader"""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    output_dir = output_dir or Path(__file__).parent.parent / "cases"
    print(f"正在生成 {count} 个案件...")
    cases = generate_batch(count)
    paths = save_batch(cases, output_dir)
    print(f"已保存 {len(paths)} 个案件文件到 {output_dir}")
    print("正在导入到 CaseLoader...")
    result = import_to_case_loader(output_dir)
    return result


# ── CLI ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="案件种子数据生成器")
    parser.add_argument("--count", type=int, default=0, help="生成案件数量（与 --seed 互斥）")
    parser.add_argument("--output-dir", type=str, help="输出目录")
    parser.add_argument("--seed", type=int, metavar="N", help="生成 N 个案件并立即导入 CaseLoader")
    parser.add_argument("--import-only", action="store_true", help="仅重建 CaseLoader 索引")
    parser.add_argument("--list", action="store_true", help="列出当前已加载的案件")
    args = parser.parse_args()

    random.seed(42)  # 可复现

    if args.import_only:
        result = import_to_case_loader()
        print(f"✅ 已导入 {result['total_cases']} 个案件")
        for cid in result["case_ids"]:
            print(f"  - {cid}")
        return

    if args.list:
        result = import_to_case_loader()
        print(f"已加载案件 ({result['total_cases']}):")
        for cid in result["case_ids"]:
            print(f"  {cid}")
        return

    if args.seed:
        result = seed_and_import(args.seed)
        print(f"✅ 完成！共导入 {result['total_cases']} 个案件")
        return

    if args.count:
        output_dir = Path(args.output_dir) if args.output_dir else Path(__file__).parent.parent / "cases"
        cases = generate_batch(args.count)
        paths = save_batch(cases, output_dir)
        print(f"✅ 已生成 {len(paths)} 个案件，保存至 {output_dir}:")
        for p in paths[:5]:
            print(f"  {p.name}")
        if len(paths) > 5:
            print(f"  ... 及其他 {len(paths)-5} 个文件")
        return

    # 无参数：默认生成 10 个并显示
    parser.print_help()


if __name__ == "__main__":
    main()
