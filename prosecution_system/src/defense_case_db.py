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
    ]
    
    # 辩护类型到罪名的映射
    DEFENSE_TO_CRIMES = {
        "正当防卫": ["故意伤害罪", "故意杀人罪", "过失致人死亡罪"],
        "紧急避险": ["故意毁坏财物罪", "危害公共安全罪"],
        "自首": ["盗窃罪", "诈骗罪", "职务侵占罪", "各类犯罪"],
        "立功": ["贩卖毒品罪", "组织卖淫罪", "各类犯罪"],
        "赔偿谅解": ["交通肇事罪", "故意伤害罪", "过失致人死亡罪"],
        "情节轻微": ["危险驾驶罪", "盗窃罪", "故意伤害罪"],
        "证据不足": ["诈骗罪", "合同诈骗罪", "各类犯罪"],
        "未成年人": ["盗窃罪", "故意伤害罪", "聚众斗殴罪"],
        "精神病人": ["故意杀人罪", "故意伤害罪", "放火罪"],
        "防卫过当": ["故意伤害罪", "过失致人死亡罪"],
    }
    
    def __init__(self, custom_cases_path: Optional[Path] = None):
        """初始化案例数据库
        
        Args:
            custom_cases_path: 自定义案例JSON文件路径
        """
        self._cases: List[DefenseCase] = []
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
        self._cases_by_crime[case.crime].append(case)
        
        # 按辩护类型索引
        self._cases_by_defense[case.key_defense].append(case)
        for defense in case.supporting_defenses:
            self._cases_by_defense[defense].append(case)
    
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
            
            # 如果指定了罪名，需要匹配
            if crime and crime not in c.crime and c.crime not in crime:
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
