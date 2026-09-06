# -*- coding: utf-8 -*-
"""
辩护案例数据库 - defense_case_db.py

检索类似案例的无罪/轻判判决，作为辩护参考：
- 按罪名检索类似无罪/轻判案例
- 按辩护理由检索参考案例
- 量刑区间分析
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class DefenseCase:
    """辩护参考案例"""
    case_id: str
    case_name: str
    crime: str  # 罪名
    outcome: str  # 判决结果
    outcome_type: str  # innocent/mitigated/convicted
    
    # 判决理由
    reasoning: str
    key_defense: str  # 主要辩护理由
    supporting_defenses: List[str]  # 辅助辩护理由
    
    # 量刑信息
    sentence: Optional[str] = None  # 刑期
    probation: Optional[str] = None  # 缓刑
    fine: Optional[int] = None  # 罚金
    
    # 地区和时间
    province: Optional[str] = None
    year: Optional[int] = None
    
    # 关键事实（用于相似度匹配）
    key_facts: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "case_id": self.case_id,
            "case_name": self.case_name,
            "crime": self.crime,
            "outcome": self.outcome,
            "outcome_type": self.outcome_type,
            "reasoning": self.reasoning,
            "key_defense": self.key_defense,
            "supporting_defenses": self.supporting_defenses,
            "sentence": self.sentence,
            "probation": self.probation,
            "fine": self.fine,
            "province": self.province,
            "year": self.year,
            "key_facts": self.key_facts,
        }


@dataclass
class CaseSearchResult:
    """案例检索结果"""
    cases: List[DefenseCase]
    total: int
    search_params: Dict
    summary: str


class DefenseCaseDatabase:
    """辩护案例数据库
    
    内置典型无罪/轻判案例库，同时支持扩展
    """
    
    # 内置典型案例（作为种子数据）
    BUILTIN_CASES = [
        # 正当防卫案例
        {
            "case_id": "DEF-001",
            "case_name": "于欢故意伤害案",
            "crime": "故意伤害罪",
            "outcome": "认定正当防卫，改判五年有期徒刑",
            "outcome_type": "mitigated",
            "reasoning": "于欢面对正在进行的不法侵害，采取防卫行为，但其防卫行为超过必要限度造成重大损害，依法应当减轻处罚。",
            "key_defense": "正当防卫",
            "supporting_defenses": ["防卫过当", "自首", "坦白"],
            "sentence": "五年有期徒刑",
            "year": 2017,
            "province": "山东",
            "key_facts": "母亲被催债人员限制人身自由、侮辱，于欢持刀刺伤4人",
        },
        {
            "case_id": "DEF-002",
            "case_name": "涞源反杀案",
            "crime": "故意杀人罪",
            "outcome": "认定正当防卫，不负刑事责任",
            "outcome_type": "innocent",
            "reasoning": "王某某面对非法入侵住宅行凶的不法侵害，采取防卫行为造成不法侵害人伤亡，属于正当防卫。",
            "key_defense": "正当防卫",
            "supporting_defenses": ["住宅权保护"],
            "year": 2019,
            "province": "河北",
            "key_facts": "醉酒男子深夜翻墙闯入被杀害",
        },
        {
            "case_id": "DEF-003",
            "case_name": "丽江反杀案",
            "crime": "故意伤害罪",
            "outcome": "认定正当防卫，不起诉",
            "outcome_type": "innocent",
            "reasoning": "当事人面对正在进行的行凶，采取防卫行为致人死亡，不属于防卫过当。",
            "key_defense": "正当防卫",
            "supporting_defenses": ["特殊防卫"],
            "year": 2020,
            "province": "云南",
            "key_facts": "同村村民酒后滋事，持菜刀上门，被夺刀反杀",
        },
        
        # 自首案例
        {
            "case_id": "DEF-010",
            "case_name": "一般自首减轻案例",
            "crime": "盗窃罪",
            "outcome": "自首+退赃，判处缓刑",
            "outcome_type": "mitigated",
            "reasoning": "被告人自动投案，如实供述罪行，系自首，且积极退赃，取得被害人谅解，可以从轻处罚并适用缓刑。",
            "key_defense": "自首",
            "supporting_defenses": ["退赃", "谅解", "初犯"],
            "sentence": "有期徒刑一年，缓刑一年",
            "year": 2020,
            "key_facts": "盗窃现金3万元，自动投案",
        },
        
        # 未成年人案例
        {
            "case_id": "DEF-020",
            "case_name": "未成年人校园欺凌案",
            "crime": "故意伤害罪",
            "outcome": "附条件不起诉",
            "outcome_type": "innocent",
            "reasoning": "犯罪嫌疑人系未成年人，犯罪后自首并取得被害人谅解，认罪悔罪，社会调查报告显示具备帮教条件。",
            "key_defense": "未成年人",
            "supporting_defenses": ["自首", "谅解", "社会调查"],
            "year": 2021,
            "key_facts": "16岁学生打架致人轻伤",
        },
        
        # 证据不足案例
        {
            "case_id": "DEF-030",
            "case_name": "证据不足无罪案",
            "crime": "诈骗罪",
            "outcome": "证据不足，指控罪名不成立",
            "outcome_type": "innocent",
            "reasoning": "现有证据不足以证明被告人具有非法占有目的，不能排除合理怀疑，证据未达到确实充分标准。",
            "key_defense": "证据不足",
            "supporting_defenses": ["疑点利益归于被告"],
            "year": 2020,
            "key_facts": "经济纠纷被指控诈骗，民间借贷关系存疑",
        },
        
        # 情节轻微案例
        {
            "case_id": "DEF-040",
            "case_name": "醉驾情节轻微案",
            "crime": "危险驾驶罪",
            "outcome": "情节轻微，相对不起诉",
            "outcome_type": "innocent",
            "reasoning": "被告人血液酒精含量刚过追诉标准（83mg/100ml），无交通事故发生，认罪悔罪，已完成社区评估。",
            "key_defense": "情节轻微",
            "supporting_defenses": ["初犯", "认罪认罚"],
            "sentence": "相对不起诉",
            "year": 2022,
            "key_facts": "血液酒精含量83mg/100ml，行驶距离短",
        },
        
        # 赔偿谅解案例
        {
            "case_id": "DEF-050",
            "case_name": "交通肇事赔偿谅解案",
            "crime": "交通肇事罪",
            "outcome": "赔偿获谅解，判处缓刑",
            "outcome_type": "mitigated",
            "reasoning": "被告人积极赔偿被害人家属全部损失并取得谅解，自首，认罪认罚，可以从轻处罚并适用缓刑。",
            "key_defense": "赔偿谅解",
            "supporting_defenses": ["自首", "认罪认罚", "保险赔偿"],
            "sentence": "有期徒刑一年，缓刑一年六个月",
            "year": 2021,
            "key_facts": "致一人死亡，全责，已赔偿90万元",
        },
        
        # 防卫过当案例
        {
            "case_id": "DEF-060",
            "case_name": "互殴中防卫过当案",
            "crime": "故意伤害罪",
            "outcome": "认定防卫过当，减轻处罚",
            "outcome_type": "mitigated",
            "reasoning": "双方因琐事发生争执进而互殴，一方在互殴中持械致对方重伤，超过必要限度，属于防卫过当，应当减轻处罚。",
            "key_defense": "防卫过当",
            "supporting_defenses": ["被害人过错", "激情犯罪"],
            "sentence": "有期徒刑二年",
            "year": 2019,
            "key_facts": "邻里纠纷演变为互殴，一方持铁棍致对方重伤",
        },
        
        # 精神疾病案例
        {
            "case_id": "DEF-070",
            "case_name": "精神障碍无罪案",
            "crime": "故意杀人罪",
            "outcome": "不负刑事责任，强制医疗",
            "outcome_type": "innocent",
            "reasoning": "经司法鉴定，被告人案发时处于精神分裂症发病期，丧失辨认和控制能力，不负刑事责任。",
            "key_defense": "精神病人无刑事责任",
            "supporting_defenses": ["强制医疗"],
            "sentence": "强制医疗令",
            "year": 2020,
            "key_facts": "精神分裂症患者发病期间伤害家人",
        },
        
        # 罪名变更案例
        {
            "case_id": "DEF-080",
            "case_name": "定性错误变更案",
            "crime": "故意伤害罪→过失致人死亡罪",
            "outcome": "变更罪名为过失致人死亡",
            "outcome_type": "mitigated",
            "reasoning": "被告人不存在伤害故意，仅因疏忽大意致人死亡，应定性为过失致人死亡罪。",
            "key_defense": "定性错误",
            "supporting_defenses": ["主观故意存疑"],
            "sentence": "有期徒刑三年",
            "year": 2020,
            "key_facts": "民事纠纷中推搡致对方倒地死亡",
        },
        
        # 立功案例
        {
            "case_id": "DEF-090",
            "case_name": "贩毒立功案",
            "crime": "贩卖毒品罪",
            "outcome": "认定立功，从轻处罚",
            "outcome_type": "mitigated",
            "reasoning": "被告人归案后协助公安机关抓获其他犯罪嫌疑人，查证属实，构成立功，可以从轻或减轻处罚。",
            "key_defense": "立功",
            "supporting_defenses": ["自首", "坦白"],
            "sentence": "有期徒刑七年",
            "year": 2021,
            "province": "广东",
            "key_facts": "贩卖海洛因50克，归案后协助抓获同案犯",
        },
        
        # 未成年人从轻案例
        {
            "case_id": "DEF-100",
            "case_name": "未成年人盗窃案",
            "crime": "盗窃罪",
            "outcome": "附条件不起诉",
            "outcome_type": "innocent",
            "reasoning": "犯罪嫌疑人系已满十四周岁未满十八周岁的未成年人，犯罪情节较轻，有悔罪表现，家长具备监护条件。",
            "key_defense": "未成年人",
            "supporting_defenses": ["初犯", "认罪认罚", "赔偿"],
            "year": 2022,
            "province": "浙江",
            "key_facts": "16岁学生盗窃自行车两辆，价值2000元",
        },
        
        # 坦白案例
        {
            "case_id": "DEF-110",
            "case_name": "坦白从宽案",
            "crime": "诈骗罪",
            "outcome": "认定坦白，从轻处罚",
            "outcome_type": "mitigated",
            "reasoning": "被告人虽不构成自首，但到案后如实供述犯罪事实，认罪态度好，可以从轻处罚。",
            "key_defense": "坦白/认罪认罚",
            "supporting_defenses": ["初犯", "退赃"],
            "sentence": "有期徒刑三年",
            "year": 2021,
            "province": "江苏",
            "key_facts": "电信诈骗30万元，被抓获后如实供述",
        },
        
        # 老人从轻案例
        {
            "case_id": "DEF-120",
            "case_name": "老年人故意伤害案",
            "crime": "故意伤害罪",
            "outcome": "年满75周岁，从轻处罚",
            "outcome_type": "mitigated",
            "reasoning": "被告人已满七十五周岁，故意犯罪，可以从轻或减轻处罚。",
            "key_defense": "老年人",
            "supporting_defenses": ["自首", "赔偿", "谅解"],
            "sentence": "有期徒刑一年，缓刑一年",
            "year": 2022,
            "province": "北京",
            "key_facts": "77岁老人因邻里纠纷致人轻伤",
        },
        
        # 聋哑人案例
        {
            "case_id": "DEF-130",
            "case_name": "聋哑人盗窃案",
            "crime": "盗窃罪",
            "outcome": "又聋又哑，从轻处罚",
            "outcome_type": "mitigated",
            "reasoning": "被告人系又聋又哑的人，可以从轻、减轻或者免除处罚。",
            "key_defense": "聋哑人/盲人",
            "supporting_defenses": ["初犯", "自首"],
            "sentence": "拘役三个月",
            "year": 2020,
            "province": "四川",
            "key_facts": "聋哑人扒窃手机一部",
        },
        
        # 追诉时效案例
        {
            "case_id": "DEF-140",
            "case_name": "超过追诉时效案",
            "crime": "故意伤害罪",
            "outcome": "已过追诉时效，不追究刑事责任",
            "outcome_type": "innocent",
            "reasoning": "法定最高刑为三年以下有期徒刑的，经过五年不再追诉。本案已过追诉时效。",
            "key_defense": "超过追诉时效",
            "supporting_defenses": [],
            "year": 2019,
            "province": "上海",
            "key_facts": "故意伤害致人轻伤，案发后潜逃10年",
        },
        
        # 紧急避险案例
        {
            "case_id": "DEF-150",
            "case_name": "紧急避险无罪案",
            "crime": "故意毁坏财物罪",
            "outcome": "认定紧急避险，不负刑事责任",
            "outcome_type": "innocent",
            "reasoning": "被告人为了使本人的人身权利免受正在发生的危险，迫不得已采取损害另一较小合法权益的行为，属于紧急避险。",
            "key_defense": "紧急避险",
            "supporting_defenses": [],
            "year": 2021,
            "province": "浙江",
            "key_facts": "为逃避追砍砸坏他人汽车逃逸",
        },
        
        # 被害人过错案例
        {
            "case_id": "DEF-160",
            "case_name": "被害人过错从轻案",
            "crime": "故意伤害罪",
            "outcome": "认定被害人过错，从轻处罚",
            "outcome_type": "mitigated",
            "reasoning": "被害人对于矛盾激化负有直接责任，对被告人从轻处罚。",
            "key_defense": "被害人过错",
            "supporting_defenses": ["自首", "赔偿", "谅解"],
            "sentence": "有期徒刑六个月，缓刑一年",
            "year": 2021,
            "province": "福建",
            "key_facts": "因债务纠纷发生冲突，被害人先动手打人",
        },
        # ── 抢夺罪（新增4条） ────────────────────────────────
        {
            "case_id": "DEF-181",
            "case_name": "公然夺取财物被控抢夺无罪案",
            "crime": "抢夺罪",
            "outcome": "认定民事侵权，不构成抢夺罪",
            "outcome_type": "innocent",
            "reasoning": "被告人虽公然夺取财物，但系针对自身合法债权采取的私力救济行为，主观上不具有非法占有目的，不构成抢夺罪。",
            "key_defense": "无非法占有目的",
            "supporting_defenses": ["维权行为", "民事纠纷定性", "债权债务关系明确"],
            "sentence": "无罪",
            "year": 2020,
            "province": "广东",
            "key_facts": "债务人长期拖欠货款，债权人到其店铺拿走货物抵债被控抢夺",
        },
        {
            "case_id": "DEF-182",
            "case_name": "飞车抢夺老年人财物减轻案",
            "crime": "抢夺罪",
            "outcome": "认定自首、赔偿、老年人谅解，从轻处罚",
            "outcome_type": "mitigated",
            "reasoning": "被告人驾驶摩托车抢夺独行老年人财物，数额较大，但有自首情节并积极赔偿获得谅解，依法从轻处罚。",
            "key_defense": "自首",
            "supporting_defenses": ["赔偿谅解", "认罪认罚"],
            "sentence": "有期徒刑一年，缓刑一年六个月",
            "year": 2021,
            "province": "广西",
            "key_facts": "驾驶摩托车抢夺独行老人挎包，内有现金8000元及手机一部",
        },
        {
            "case_id": "DEF-183",
            "case_name": "利用精神障碍抢夺减轻案",
            "crime": "抢夺罪",
            "outcome": "认定从犯、精神障碍，全额退赃，适用缓刑",
            "outcome_type": "mitigated",
            "reasoning": "被告人在他人精神障碍状态下伙同其夺取财物，系从犯且有精神疾病，全额退赃，依法减轻处罚。",
            "key_defense": "从犯",
            "supporting_defenses": ["精神障碍", "全额退赃", "自首"],
            "sentence": "有期徒刑一年，缓刑二年",
            "year": 2022,
            "province": "贵州",
            "key_facts": "利用精神障碍人士共同夺取其家中财物，涉案金额12000元",
        },
        {
            "case_id": "DEF-184",
            "case_name": "未成年人抢夺致人轻伤减轻案",
            "crime": "抢夺罪",
            "outcome": "认定未成年、自首，适用附条件不起诉",
            "outcome_type": "mitigated",
            "reasoning": "被告人系未成年人，因网络赌博欠债结伙抢夺，数额较大，但有自首情节且认罪悔罪，依法适用附条件不起诉。",
            "key_defense": "未成年人",
            "supporting_defenses": ["自首", "认罪认罚"],
            "sentence": "附条件不起诉",
            "year": 2021,
            "province": "云南",
            "key_facts": "未成年人因网络赌博欠债，伙同他人骑摩托车抢夺独自行走女子挎包",
        },
        # ── 贩卖毒品罪（新增4条） ────────────────────────────
        {
            "case_id": "DEF-185",
            "case_name": "代购蹭吸被控贩卖毒品无罪案",
            "crime": "贩卖毒品罪",
            "outcome": "认定代购蹭吸，无贩卖故意，不构成贩卖毒品罪",
            "outcome_type": "innocent",
            "reasoning": "被告人受托为吸毒人员代购毒品并蹭吸少量，属于帮助行为而非独立贩卖，主观上不具有贩卖毒品的故意。",
            "key_defense": "无贩卖故意",
            "supporting_defenses": ["代购行为", "蹭吸非独立贩卖", "定性错误"],
            "sentence": "无罪",
            "year": 2020,
            "province": "四川",
            "key_facts": "应吸毒朋友请求代购冰毒并蹭吸少量，被以贩卖毒品罪移送审查起诉",
        },
        {
            "case_id": "DEF-186",
            "case_name": "特情介入贩卖毒品减轻案",
            "crime": "贩卖毒品罪",
            "outcome": "认定特情介入、数量引诱，从轻处罚",
            "outcome_type": "mitigated",
            "reasoning": "被告人系在特情人员数量引诱下实施贩卖毒品行为，属于特情引诱，依法从轻处罚；涉案海洛因0.8克，数量较小。",
            "key_defense": "特情引诱",
            "supporting_defenses": ["数量较小", "坦白", "认罪认罚"],
            "sentence": "有期徒刑六个月",
            "year": 2021,
            "province": "广东",
            "key_facts": "特情人员主动联系被告人要求购买海洛因，被告人从他人处购入后转卖",
        },
        {
            "case_id": "DEF-187",
            "case_name": "受雇跑腿运送毒品减轻案",
            "crime": "贩卖毒品罪",
            "outcome": "认定从犯、自首，适用缓刑",
            "outcome_type": "mitigated",
            "reasoning": "被告人受雇为他人运送毒品包裹，在犯罪中起次要作用，系从犯，且有自首情节，依法减轻处罚。",
            "key_defense": "从犯",
            "supporting_defenses": ["自首", "受雇跑腿", "认罪认罚"],
            "sentence": "有期徒刑二年，缓刑三年",
            "year": 2022,
            "province": "浙江",
            "key_facts": "受雇按指令接收和运送毒品包裹，被公安当场抓获，涉案冰毒2克",
        },
        {
            "case_id": "DEF-188",
            "case_name": "持有而非贩卖毒品免予处罚案",
            "crime": "贩卖毒品罪",
            "outcome": "认定非法持有毒品罪，改判免予刑事处罚",
            "outcome_type": "mitigated",
            "reasoning": "被告人随身携带的毒品系用于自身吸食，现有证据不足以证明其有贩卖行为，改认定非法持有毒品罪并免予处罚。",
            "key_defense": "定性错误",
            "supporting_defenses": ["仅供自吸", "无贩卖证据", "非法持有毒品罪"],
            "sentence": "免予刑事处罚",
            "year": 2021,
            "province": "湖北",
            "key_facts": "被查获随身携带冰毒3克，无法证明有贩卖行为，以贩卖毒品罪移送",
        },
        # ── 敲诈勒索罪（新增4条） ────────────────────────────────
        {
            "case_id": "DEF-161",
            "case_name": "债务纠纷敲诈勒索无罪案",
            "crime": "敲诈勒索罪",
            "outcome": "认定维权行为，不构成敲诈勒索罪",
            "outcome_type": "innocent",
            "reasoning": "被告人以索债为目的向债务人施加压力，主观上不具有非法占有目的，客观上属于私力救济，不构成敲诈勒索罪。",
            "key_defense": "维权行为",
            "supporting_defenses": ["无非法占有目的", "债权债务关系明确"],
            "sentence": "无罪",
            "year": 2020,
            "province": "广东",
            "key_facts": "多次向债务人催讨合法债务，债务人报警称被敲诈",
        },
        {
            "case_id": "DEF-162",
            "case_name": "举报后索取奖励不构成敲诈勒索案",
            "crime": "敲诈勒索罪",
            "outcome": "无罪",
            "outcome_type": "innocent",
            "reasoning": "举报违法犯罪是公民权利，索取举报奖励不属于敲诈勒索罪中的'要挟'，不具有非法占有目的。",
            "key_defense": "权利行使",
            "supporting_defenses": ["无非法占有目的", "正当权利基础"],
            "sentence": "无罪",
            "year": 2019,
            "province": "北京",
            "key_facts": "举报企业违法行为后，以向媒体曝光为筹码索取举报奖励",
        },
        {
            "case_id": "DEF-163",
            "case_name": "未成年人敲诈勒索减轻案",
            "crime": "敲诈勒索罪",
            "outcome": "认定未成年，从轻处罚，适用缓刑",
            "outcome_type": "mitigated",
            "reasoning": "被告人系未成年人，依法应当从轻或减轻处罚，且系初犯、认罪态度好。",
            "key_defense": "未成年人",
            "supporting_defenses": ["初犯", "坦白", "认罪认罚"],
            "sentence": "有期徒刑一年，缓刑一年六个月",
            "year": 2021,
            "province": "上海",
            "key_facts": "未成年人在校学生，模仿网络视频敲诈同学家长",
        },
        {
            "case_id": "DEF-164",
            "case_name": "威胁举报职务侵占索回款项轻判案",
            "crime": "敲诈勒索罪",
            "outcome": "认定自首、赔偿，从轻处罚",
            "outcome_type": "mitigated",
            "reasoning": "被告人以举报职务侵占为要挟索回本单位款项，主观恶性较小，且有自首情节并积极赔偿。",
            "key_defense": "自首",
            "supporting_defenses": ["赔偿谅解", "坦白", "认罪认罚"],
            "sentence": "有期徒刑一年，缓刑二年",
            "year": 2022,
            "province": "浙江",
            "key_facts": "以举报公司高管职务侵占为要挟，要求返还本人款项",
        },
        # ── 交通肇事罪（新增4条） ────────────────────────────────
        {
            "case_id": "DEF-165",
            "case_name": "紧急避险致交通事故无罪案",
            "crime": "交通肇事罪",
            "outcome": "认定紧急避险，不构成交通肇事罪",
            "outcome_type": "innocent",
            "reasoning": "被告人因紧急避险（躲避突然出现的行人）导致车辆失控，属正当业务行为，不构成犯罪。",
            "key_defense": "紧急避险",
            "supporting_defenses": ["正当业务行为", "意外事件"],
            "sentence": "无罪",
            "year": 2020,
            "province": "江苏",
            "key_facts": "正常驾驶时为躲避突然出现的行人紧急打方向盘导致事故",
        },
        {
            "case_id": "DEF-166",
            "case_name": "交通肇事致人死亡缓刑案",
            "crime": "交通肇事罪",
            "outcome": "认定自首、赔偿获谅解，适用缓刑",
            "outcome_type": "mitigated",
            "reasoning": "被告人负事故主要责任，但有自首情节并积极赔偿被害人家属获得谅解，可从轻处罚。",
            "key_defense": "自首",
            "supporting_defenses": ["赔偿谅解", "认罪认罚"],
            "sentence": "有期徒刑一年六个月，缓刑二年",
            "year": 2021,
            "province": "广东",
            "key_facts": "驾驶机动车将正在过马路的行人撞死，负主要责任，有自首情节",
        },
        {
            "case_id": "DEF-167",
            "case_name": "醉酒驾驶致人重伤从宽案",
            "crime": "交通肇事罪",
            "outcome": "认定坦白、积极赔偿，从轻处罚",
            "outcome_type": "mitigated",
            "reasoning": "被告人醉酒驾驶致人重伤，负全部责任，但事后积极赔偿、坦白认罪，依法从轻处罚。",
            "key_defense": "坦白",
            "supporting_defenses": ["赔偿", "认罪认罚"],
            "sentence": "有期徒刑二年",
            "year": 2022,
            "province": "四川",
            "key_facts": "醉酒驾驶机动车将两名行人撞成重伤，血液酒精含量120mg/100ml",
        },
        {
            "case_id": "DEF-168",
            "case_name": "交通肇事逃逸后自首减轻案",
            "crime": "交通肇事罪",
            "outcome": "认定自首，从轻处罚",
            "outcome_type": "mitigated",
            "reasoning": "被告人交通肇事后逃逸，但于次日自首，综合其逃逸情节和自首行为，酌情从轻处罚。",
            "key_defense": "自首",
            "supporting_defenses": ["赔偿", "认罪认罚"],
            "sentence": "有期徒刑三年",
            "year": 2021,
            "province": "湖北",
            "key_facts": "交通肇事后逃逸，次日自首，致一人死亡",
        },
        # ── 非法吸收公众存款罪（新增3条） ────────────────────────
        {
            "case_id": "DEF-169",
            "case_name": "单位犯罪直接责任人员减轻案",
            "crime": "非法吸收公众存款罪",
            "outcome": "认定从犯，自首，全部退赃，适用缓刑",
            "outcome_type": "mitigated",
            "reasoning": "被告人系单位犯罪中的直接责任人员，非单位负责人，且有自首情节、全额退赃，依法减轻处罚。",
            "key_defense": "从犯",
            "supporting_defenses": ["自首", "全额退赃", "认罪认罚"],
            "sentence": "有期徒刑二年，缓刑三年",
            "year": 2021,
            "province": "北京",
            "key_facts": "某公司部门经理，负责吸收公众存款业务，涉及金额2000万元",
        },
        {
            "case_id": "DEF-170",
            "case_name": "P2P平台技术人员减轻案",
            "crime": "非法吸收公众存款罪",
            "outcome": "认定从犯，未直接参与吸存，全额退赃，适用缓刑",
            "outcome_type": "mitigated",
            "reasoning": "被告人仅为平台技术人员，未参与吸存决策，且有自首、全额退赃情节，犯罪情节较轻。",
            "key_defense": "从犯",
            "supporting_defenses": ["自首", "全额退赃", "胁从犯"],
            "sentence": "有期徒刑一年，缓刑一年六个月",
            "year": 2022,
            "province": "上海",
            "key_facts": "P2P平台后端工程师，仅提供技术支持，未参与业务决策，涉及金额8000万元",
        },
        {
            "case_id": "DEF-171",
            "case_name": "非法吸存单位主管获轻判案",
            "crime": "非法吸收公众存款罪",
            "outcome": "认定从犯、自首、部分退赃，从轻处罚",
            "outcome_type": "mitigated",
            "reasoning": "被告人在单位犯罪中起次要作用，系从犯，且有自首情节，部分退赃，认罪认罚，依法从轻处罚。",
            "key_defense": "从犯",
            "supporting_defenses": ["自首", "认罪认罚"],
            "sentence": "有期徒刑三年",
            "year": 2020,
            "province": "浙江",
            "key_facts": "理财公司部门总监，下属团队吸收公众存款1.5亿元",
        },
        # ── 集资诈骗罪（新增3条） ────────────────────────────────
        {
            "case_id": "DEF-172",
            "case_name": "合同纠纷被控集资诈骗无罪案",
            "crime": "集资诈骗罪",
            "outcome": "认定系民事合同纠纷，不构成集资诈骗罪",
            "outcome_type": "innocent",
            "reasoning": "被告人虽有虚构项目行为，但所募集资金主要用于生产经营，且有还款意愿和能力，属于民事欺诈而非刑事诈骗。",
            "key_defense": "无非法占有目的",
            "supporting_defenses": ["主要用于生产经营", "有还款意愿", "民事纠纷定性"],
            "sentence": "无罪",
            "year": 2020,
            "province": "江苏",
            "key_facts": "企业负责人虚构项目向多人借款，后因经营不善无法还款被控集资诈骗",
        },
        {
            "case_id": "DEF-173",
            "case_name": "单位集资诈骗直接责任减轻案",
            "crime": "集资诈骗罪",
            "outcome": "认定从犯、自首，全额退赃，适用缓刑",
            "outcome_type": "mitigated",
            "reasoning": "被告人系公司财务负责人，在单位犯罪中起次要作用，有自首情节并全额退赃，依法减轻处罚。",
            "key_defense": "从犯",
            "supporting_defenses": ["自首", "全额退赃", "认罪认罚"],
            "sentence": "有期徒刑三年，缓刑四年",
            "year": 2021,
            "province": "广东",
            "key_facts": "公司财务负责人，配合公司领导实施集资诈骗，涉及金额3000万元",
        },
        {
            "case_id": "DEF-174",
            "case_name": "被诱骗参与集资诈骗减轻案",
            "crime": "集资诈骗罪",
            "outcome": "认定胁从犯、自首，全额退赃，适用缓刑",
            "outcome_type": "mitigated",
            "reasoning": "被告人被诱骗参与犯罪，主观恶性较小，且有自首情节、全额退赃，依法减轻或免除处罚。",
            "key_defense": "胁从犯",
            "supporting_defenses": ["自首", "全额退赃", "被诱骗"],
            "sentence": "有期徒刑二年，缓刑三年",
            "year": 2022,
            "province": "北京",
            "key_facts": "被朋友以高收益项目诱骗参与向社会公众吸收资金，不知真实用途",
        },
        # ── 职务侵占罪（新增3条） ────────────────────────────────
        {
            "case_id": "DEF-175",
            "case_name": "劳动关系争议被控职务侵占无罪案",
            "crime": "职务侵占罪",
            "outcome": "认定系劳动报酬争议，不构成职务侵占罪",
            "outcome_type": "innocent",
            "reasoning": "被告人占有公司款项系基于劳动关系主张工资和报销，属于民事纠纷，不具有非法占有目的。",
            "key_defense": "无非法占有目的",
            "supporting_defenses": ["劳动争议", "民事纠纷定性", "权利基础"],
            "sentence": "无罪",
            "year": 2020,
            "province": "上海",
            "key_facts": "离职员工占有公司款项称系未结清的工资和报销，公司以职务侵占报案",
        },
        {
            "case_id": "DEF-176",
            "case_name": "职务侵占自首退赃减轻案",
            "crime": "职务侵占罪",
            "outcome": "认定自首、全额退赃，从轻处罚",
            "outcome_type": "mitigated",
            "reasoning": "被告人利用职务便利侵占公司财物，但有自首情节并全额退赃，被害单位表示谅解，依法从轻处罚。",
            "key_defense": "自首",
            "supporting_defenses": ["全额退赃", "谅解", "认罪认罚"],
            "sentence": "有期徒刑一年，缓刑一年六个月",
            "year": 2021,
            "province": "广东",
            "key_facts": "公司会计利用职务便利侵占公司资金50万元，后自首并全额退赃",
        },
        {
            "case_id": "DEF-177",
            "case_name": "亲属间职务侵占和解减轻案",
            "crime": "职务侵占罪",
            "outcome": "认定自首、和解，从轻处罚",
            "outcome_type": "mitigated",
            "reasoning": "被告人与被害公司负责人系亲属关系，侵占款项已全部退还并取得谅解，有自首情节，依法从轻处罚。",
            "key_defense": "自首",
            "supporting_defenses": ["和解谅解", "退赃", "认罪认罚"],
            "sentence": "有期徒刑六个月，缓刑一年",
            "year": 2022,
            "province": "浙江",
            "key_facts": "公司股东利用职务便利将公司款项转入个人账户，后与公司达成和解",
        },
        # ── 开设赌场罪（新增3条） ────────────────────────────────
        {
            "case_id": "DEF-178",
            "case_name": "提供场所供人参赌开设赌场减轻案",
            "crime": "开设赌场罪",
            "outcome": "认定从犯、自首，情节较轻，适用缓刑",
            "outcome_type": "mitigated",
            "reasoning": "被告人仅为赌场提供场所，未参与赌资抽头，在共同犯罪中起次要作用，且有自首情节。",
            "key_defense": "从犯",
            "supporting_defenses": ["自首", "认罪认罚"],
            "sentence": "有期徒刑一年，缓刑一年六个月",
            "year": 2021,
            "province": "四川",
            "key_facts": "将自有房屋提供给赌博团伙使用，收取固定租金，未参与赌场经营",
        },
        {
            "case_id": "DEF-179",
            "case_name": "网站技术人员开设赌场减轻案",
            "crime": "开设赌场罪",
            "outcome": "认定从犯、自首，适用缓刑",
            "outcome_type": "mitigated",
            "reasoning": "被告人仅为赌博网站提供技术支持，未参与运营决策，在犯罪中作用较小，有自首情节，依法从轻处罚。",
            "key_defense": "从犯",
            "supporting_defenses": ["自首", "认罪认罚"],
            "sentence": "有期徒刑二年，缓刑三年",
            "year": 2022,
            "province": "福建",
            "key_facts": "网络技术人员受雇为境外赌博网站开发维护网站，按月收取固定报酬",
        },
        {
            "case_id": "DEF-180",
            "case_name": "聚众赌博被控开设赌场改认定赌博罪减轻案",
            "crime": "开设赌场罪",
            "outcome": "改判赌博罪，从轻处罚",
            "outcome_type": "mitigated",
            "reasoning": "被告人虽提供场所供人赌博，但系临时性、非营业性，不符合开设赌场的'持续性、稳定性'特征，改认定为赌博罪。",
            "key_defense": "定性错误",
            "supporting_defenses": ["改定性", "情节较轻", "坦白"],
            "sentence": "有期徒刑六个月",
            "year": 2020,
            "province": "云南",
            "key_facts": "农闲时期在自家开设棋牌室供村民赌博，收取少量茶水费，被控开设赌场罪",
        },
    ]
    
    # 辩护类型到罪名的映射
    DEFENSE_TO_CRIMES = {
        "正当防卫": ["故意伤害罪", "故意杀人罪", "过失致人死亡罪"],
        "紧急避险": ["故意毁坏财物罪", "危害公共安全罪", "交通肇事罪"],
        "自首": ["盗窃罪", "诈骗罪", "职务侵占罪", "敲诈勒索罪", "交通肇事罪", "非法吸收公众存款罪", "集资诈骗罪", "开设赌场罪", "各类犯罪"],
        "立功": ["贩卖毒品罪", "组织卖淫罪", "非法吸收公众存款罪", "集资诈骗罪", "各类犯罪"],
        "赔偿谅解": ["交通肇事罪", "故意伤害罪", "过失致人死亡罪", "敲诈勒索罪", "职务侵占罪"],
        "情节轻微": ["危险驾驶罪", "盗窃罪", "故意伤害罪", "开设赌场罪"],
        "证据不足": ["诈骗罪", "合同诈骗罪", "敲诈勒索罪", "集资诈骗罪", "各类犯罪"],
        "未成年人": ["盗窃罪", "故意伤害罪", "聚众斗殴罪", "敲诈勒索罪", "开设赌场罪"],
        "精神病人": ["故意杀人罪", "故意伤害罪", "放火罪"],
        "防卫过当": ["故意伤害罪", "过失致人死亡罪"],
        "无非法占有目的": ["敲诈勒索罪", "集资诈骗罪", "职务侵占罪"],
        "从犯": ["非法吸收公众存款罪", "集资诈骗罪", "开设赌场罪", "职务侵占罪"],
        "胁从犯": ["非法吸收公众存款罪", "集资诈骗罪", "开设赌场罪"],
        "和解谅解": ["职务侵占罪", "敲诈勒索罪", "交通肇事罪", "故意伤害罪"],
        "全额退赃": ["职务侵占罪", "非法吸收公众存款罪", "集资诈骗罪", "盗窃罪"],
        "被诱骗": ["非法吸收公众存款罪", "集资诈骗罪"],
        "维权行为": ["敲诈勒索罪", "非法吸收公众存款罪"],
        "民事纠纷定性": ["敲诈勒索罪", "集资诈骗罪", "职务侵占罪"],
        "正当业务行为": ["交通肇事罪"],
        "意外事件": ["交通肇事罪"],
        "无非法占有目的": ["抢夺罪"],
        "从犯": ["抢夺罪", "贩卖毒品罪"],
        "未成年人": ["抢夺罪", "贩卖毒品罪"],
        "自首": ["抢夺罪", "贩卖毒品罪"],
        "赔偿谅解": ["抢夺罪"],
        "特情引诱": ["贩卖毒品罪"],
        "无贩卖故意": ["贩卖毒品罪"],
        "定性错误": ["贩卖毒品罪", "抢夺罪"],
        "受雇跑腿": ["贩卖毒品罪"],
        "仅供自吸": ["贩卖毒品罪"],
    }
    
    def __init__(self, custom_cases_path: Optional[Path] = None):
        """初始化案例数据库
        
        Args:
            custom_cases_path: 自定义案例JSON文件路径
        """
        self._cases: List[DefenseCase] = []
        self._cases_by_id: Dict[str, DefenseCase] = {}
        self._cases_by_crime: Dict[str, List[DefenseCase]] = defaultdict(list)
        self._cases_by_defense: Dict[str, List[DefenseCase]] = defaultdict(list)
        
        # 加载内置案例
        self._load_builtin_cases()
        
        # 加载自定义案例
        if custom_cases_path and custom_cases_path.exists():
            self._load_custom_cases(custom_cases_path)
    
    def _load_builtin_cases(self):
        """加载内置案例"""
        for case_data in self.BUILTIN_CASES:
            case = DefenseCase(**case_data)
            self._add_case(case)
    
    def _load_custom_cases(self, path: Path):
        """加载自定义案例"""
        with open(path, "r", encoding="utf-8") as f:
            cases_data = json.load(f)
        
        for case_data in cases_data:
            try:
                case = DefenseCase(**case_data)
                self._add_case(case)
            except Exception as e:
                print(f"加载案例失败: {case_data.get('case_id', 'unknown')}, {e}")
    
    def _add_case(self, case: DefenseCase):
        """添加案例到索引"""
        self._cases.append(case)
        self._cases_by_id[case.case_id] = case
        self._cases_by_crime[case.crime].append(case)
        
        # 按辩护类型索引
        self._cases_by_defense[case.key_defense].append(case)
        for defense in case.supporting_defenses:
            self._cases_by_defense[defense].append(case)
    
    def get_by_id(self, case_id: str) -> Optional[DefenseCase]:
        """按 ID 获取辩护案例"""
        return self._cases_by_id.get(case_id)

    def search_by_crime(self, crime: str, 
                        outcome_type: Optional[str] = None,
                        limit: int = 10) -> CaseSearchResult:
        """按罪名检索案例
        
        Args:
            crime: 罪名（如"故意伤害罪"）
            outcome_type: 筛选结果类型（innocent/mitigated/convicted）
            limit: 返回数量限制
            
        Returns:
            CaseSearchResult: 检索结果
        """
        # 模糊匹配罪名
        matched_cases = []
        for known_crime, cases in self._cases_by_crime.items():
            if crime in known_crime or known_crime in crime:
                matched_cases.extend(cases)
        
        # 筛选结果类型
        if outcome_type:
            matched_cases = [c for c in matched_cases if c.outcome_type == outcome_type]
        
        # 去重
        matched_cases = list({c.case_id: c for c in matched_cases}.values())
        
        # 排序
        matched_cases.sort(key=lambda x: (
            0 if x.outcome_type == "innocent" else 1,
            -(x.year or 0)
        ))
        
        # 限制数量
        result_cases = matched_cases[:limit]
        
        return CaseSearchResult(
            cases=result_cases,
            total=len(matched_cases),
            search_params={"crime": crime, "outcome_type": outcome_type},
            summary=self._generate_summary(result_cases, "罪名检索", crime),
        )
    
    def search_by_defense(self, defense_type: str, 
                         crime: Optional[str] = None,
                         limit: int = 10) -> CaseSearchResult:
        """按辩护理由检索案例
        
        Args:
            defense_type: 辩护类型（如"正当防卫"）
            crime: 限定罪名（可选）
            limit: 返回数量限制
            
        Returns:
            CaseSearchResult: 检索结果
        """
        # 获取辩护类型关联的罪名
        related_crimes = self.DEFENSE_TO_CRIMES.get(defense_type, [])
        
        # 从相关罪名中筛选
        matched_cases = []
        for c in self._cases:
            # 检查辩护类型是否匹配
            if defense_type not in [c.key_defense] + c.supporting_defenses:
                continue
            
            # 如果指定了罪名，需要匹配（使用 related_crimes 映射）
            if crime:
                # 匹配逻辑：case罪名在 related_crimes 中，或 case罪名为"各类犯罪"（通用案例），
                # 或双方罪名互含（如"盗窃罪" in "盗窃罪"）
                if (c.crime not in related_crimes and
                    c.crime != "各类犯罪" and
                    crime not in c.crime and c.crime not in crime):
                    continue
            
            matched_cases.append(c)
        
        # 排序：优先无罪案例，其次按年份
        matched_cases.sort(key=lambda x: (
            0 if x.outcome_type == "innocent" else 1,
            -(x.year or 0)
        ))
        
        result_cases = matched_cases[:limit]
        
        return CaseSearchResult(
            cases=result_cases,
            total=len(matched_cases),
            search_params={"defense_type": defense_type, "crime": crime},
            summary=self._generate_summary(result_cases, "辩护检索", defense_type),
        )
    
    def search_similar_facts(self, facts: str, 
                            crime: Optional[str] = None,
                            limit: int = 5) -> CaseSearchResult:
        """基于事实相似度检索案例
        
        Args:
            facts: 案件事实描述
            crime: 限定罪名（可选）
            limit: 返回数量限制
            
        Returns:
            CaseSearchResult: 检索结果
        """
        facts_lower = facts.lower()
        fact_keywords = self._extract_keywords(facts_lower)
        
        scored_cases = []
        for case in self._cases:
            # 如果指定了罪名，优先匹配
            if crime and crime not in case.crime and case.crime not in crime:
                continue
            
            # 计算关键词匹配度
            case_keywords = self._extract_keywords(case.key_facts.lower())
            score = len(fact_keywords & case_keywords)
            
            if score > 0:
                scored_cases.append((score, case))
        
        # 按分数排序
        scored_cases.sort(key=lambda x: -x[0])
        result_cases = [c for _, c in scored_cases[:limit]]
        
        return CaseSearchResult(
            cases=result_cases,
            total=len(scored_cases),
            search_params={"facts": facts[:50], "crime": crime},
            summary=self._generate_summary(result_cases, "相似案例", ""),
        )
    
    def get_outcome_statistics(self, crime: str) -> Dict:
        """获取特定罪名的判决结果统计
        
        Returns:
            Dict: 统计信息
        """
        cases = self._cases_by_crime.get(crime, [])
        
        if not cases:
            # 尝试模糊匹配
            for known_crime, known_cases in self._cases_by_crime.items():
                if crime in known_crime or known_crime in crime:
                    cases.extend(known_cases)
        
        innocent = sum(1 for c in cases if c.outcome_type == "innocent")
        mitigated = sum(1 for c in cases if c.outcome_type == "mitigated")
        convicted = sum(1 for c in cases if c.outcome_type == "convicted")
        
        return {
            "crime": crime,
            "total_cases": len(cases),
            "innocent_count": innocent,
            "mitigated_count": mitigated,
            "convicted_count": convicted,
            "innocent_rate": f"{innocent/len(cases)*100:.1f}%" if cases else "N/A",
            "mitigation_rate": f"{mitigated/len(cases)*100:.1f}%" if cases else "N/A",
        }
    
    def get_defense_strategies(self, crime: str, 
                              outcome_type: Optional[str] = None) -> Dict:
        """获取特定罪名的辩护策略建议
        
        Args:
            crime: 罪名
            outcome_type: 筛选结果类型
            
        Returns:
            Dict: 辩护策略建议
        """
        cases = list(self._cases_by_crime.get(crime, []))
        
        if outcome_type:
            cases = [c for c in cases if c.outcome_type == outcome_type]
        
        # 统计成功的辩护理由
        defense_counts = defaultdict(int)
        for case in cases:
            if case.outcome_type in ["innocent", "mitigated"]:
                defense_counts[case.key_defense] += 1
        
        # 按成功率排序
        sorted_defenses = sorted(defense_counts.items(), key=lambda x: -x[1])
        
        return {
            "crime": crime,
            "effective_defenses": [
                {"defense": d, "success_count": c}
                for d, c in sorted_defenses[:5]
            ],
            "recommendation": self._generate_defense_recommendation(crime, sorted_defenses),
        }
    
    def _extract_keywords(self, text: str) -> set:
        """提取关键词"""
        # 移除停用词
        stopwords = {"的", "了", "是", "在", "和", "与", "或", "但", "被", "对", "于", "等"}
        
        # 简单分词
        words = re.findall(r"[\u4e00-\u9fa5]+", text)
        
        # 过滤停用词和短词
        keywords = {w for w in words if len(w) >= 2 and w not in stopwords}
        
        return keywords
    
    def _generate_summary(self, cases: List[DefenseCase], 
                         search_type: str, keyword: str) -> str:
        """生成检索摘要"""
        if not cases:
            return f"未找到{keyword}相关的{search_type}"
        
        innocent = sum(1 for c in cases if c.outcome_type == "innocent")
        mitigated = sum(1 for c in cases if c.outcome_type == "mitigated")
        
        summary = f"找到 {len(cases)} 个相关案例"
        if innocent > 0:
            summary += f"，其中 {innocent} 个无罪"
        if mitigated > 0:
            summary += f"，{mitigated} 个从宽处理"
        
        return summary
    
    def _generate_defense_recommendation(self, crime: str,
                                        defenses: List[Tuple[str, int]]) -> str:
        """生成辩护建议"""
        if not defenses:
            return f"当前数据库中{crime}的成功辩护案例较少，建议全面评估案件事实"
        
        top_defense = defenses[0][0]
        recommendations = {
            "正当防卫": "建议收集侵害正在进行、防卫必要性等相关证据",
            "自首": "确保自动投案情节被认定，准备自首材料",
            "赔偿谅解": "建议积极赔偿，争取被害人谅解",
            "情节轻微": "强调犯罪情节较轻，社会危害不大",
            "证据不足": "重点审查证据链完整性，找出合理怀疑",
            "未成年人": "申请社会调查，强调教育为主",
        }
        
        return recommendations.get(top_defense, f"建议重点关注{top_defense}情节")


def search_defense_cases(crime: str = None,
                        defense_type: str = None,
                        facts: str = None,
                        limit: int = 10) -> Dict:
    """便捷函数：检索辩护案例
    
    Args:
        crime: 罪名
        defense_type: 辩护类型
        facts: 案件事实
        limit: 返回数量
        
    Returns:
        Dict: 检索结果
    """
    db = DefenseCaseDatabase()
    
    if defense_type:
        result = db.search_by_defense(defense_type, crime, limit)
    elif facts:
        result = db.search_similar_facts(facts, crime, limit)
    elif crime:
        result = db.search_by_crime(crime, "innocent", limit)
    else:
        return {"error": "请提供罪名、辩护类型或案件事实"}
    
    return {
        "cases": [c.to_dict() for c in result.cases],
        "total": result.total,
        "summary": result.summary,
        "search_params": result.search_params,
    }


if __name__ == "__main__":
    # 测试
    print("=== 按罪名检索 ===")
    result = search_defense_cases(crime="故意伤害罪")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    print("\n=== 按辩护类型检索 ===")
    result = search_defense_cases(defense_type="正当防卫")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    print("\n=== 辩护策略建议 ===")
    db = DefenseCaseDatabase()
    strategies = db.get_defense_strategies("盗窃罪")
    print(json.dumps(strategies, ensure_ascii=False, indent=2))
