# -*- coding: utf-8 -*-
"""
辩护增强模块 - defense_enhancer.py

为刑事案件提供辩护视角的分析，包括：
- 辩护角度识别（正当防卫、情节轻微、证据不足等）
- 辩护法律依据检索
- 辩护强度评估
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class DefenseType(Enum):
    """辩护类型枚举"""
    # 法定无罪/免罚
    LEGITIMATE_DEFENSE = "正当防卫"           # 刑法第20条
    EMERGENCY_ESCAPE = "紧急避险"              # 刑法第21条
    INSANITY = "精神病人无刑事责任"            # 刑法第18条
    SELF_DEFENSE_MINOR = "防卫过当减免"         # 刑法第20条
    ACCIDENT = "不可抗力/意外事件"              # 刑法第16条
    
    # 程序性辩护
    PROCEDURAL_VIOLATION = "程序违法"
    ILLEGAL_EVIDENCE = "非法证据排除"
    STATUTE_OF_LIMITATIONS = "超过追诉时效"
    
    # 实体性辩护（罪轻）
    CRIMINAL_MINOR = "情节轻微"
    VOLUNTARY_SURRENDER = "自首"                # 刑法第67条
    MERITOUS_REPORTING = "立功"              # 刑法第68条
    COMPENSATION = "赔偿谅解"
    COOPERATION = "坦白/认罪认罚"               # 刑法第67条
    YOUTH = "未成年人"                         # 刑法第17条
    ELDERLY = "老年人"                          # 刑法第17条之一
    DISABILITY = "聋哑人/盲人"                  # 刑法第19条
    
    # 证据辩护
    EVIDENCE_INSUFFICIENT = "证据不足"
    FACT_DISPUTE = "事实争议"
    
    # 量刑辩护
    RECIDIVISM_NOT = "非累犯"
    HARM_MINIMAL = "危害较轻"
    INITIATIVE = "主观恶性小"
    VICTIM_FAULT = "被害人过错"
    
    # 罪名辩护
    CRIME_WRONG_CHARACTERIZATION = "定性错误"
    CRIME_REDUCED = "罪名变更"
    
    @property
    def legal_basis(self) -> str:
        """返回相关法律依据"""
        basis_map = {
            "正当防卫": "《刑法》第20条",
            "紧急避险": "《刑法》第21条",
            "精神病人无刑事责任": "《刑法》第18条",
            "防卫过当减免": "《刑法》第20条第二款",
            "不可抗力/意外事件": "《刑法》第16条",
            "程序违法": "《刑事诉讼法》相关规定",
            "非法证据排除": "《刑事诉讼法》第56条",
            "超过追诉时效": "《刑法》第87-89条",
            "情节轻微": "《刑法》第13条但书",
            "自首": "《刑法》第67条第一款",
            "立功": "《刑法》第68条",
            "赔偿谅解": "《刑事诉讼法》第288条",
            "坦白/认罪认罚": "《刑法》第67条第三款",
            "未成年人": "《刑法》第17条",
            "老年人": "《刑法》第17条之一",
            "聋哑人/盲人": "《刑法》第19条",
            "证据不足": "《刑事诉讼法》第55条",
            "事实争议": "存疑有利于被告人原则",
            "非累犯": "《刑法》第65条",
            "危害较轻": "《刑法》第61条量刑原则",
            "主观恶性小": "《刑法》第61条量刑原则",
            "定性错误": "罪刑法定原则",
            "罪名变更": "罪责刑相适应原则",
        }
        return basis_map.get(self.value, "")
    
    @property
    def severity(self) -> int:
        """辩护强度等级 1-5（5最强）"""
        level_map = {
            "正当防卫": 5,
            "紧急避险": 5,
            "精神病人无刑事责任": 5,
            "不可抗力/意外事件": 5,
            "防卫过当减免": 4,
            "超过追诉时效": 5,
            "非法证据排除": 4,
            "程序违法": 3,
            "自首": 4,
            "立功": 4,
            "赔偿谅解": 3,
            "坦白/认罪认罚": 3,
            "情节轻微": 3,
            "证据不足": 4,
            "事实争议": 3,
            "非累犯": 2,
            "危害较轻": 2,
            "主观恶性小": 2,
            "定性错误": 4,
            "罪名变更": 3,
            "未成年人": 3,
            "老年人": 2,
            "聋哑人/盲人": 2,
        }
        return level_map.get(self.value, 1)


@dataclass
class DefenseAngle:
    """单个辩护角度"""
    type: DefenseType
    confidence: float  # 0-100, 这个角度在案件中的匹配程度
    evidence_points: List[str]  # 支持这个辩护的证据点
    legal_references: List[str]  # 相关法条
    risk_mitigation: str  # 这个辩护能减轻的风险
    counter_arguments: List[str]  # 可能被反驳的点
    recommendation: str  # 建议
    
    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "type_cn": self.type.value,
            "legal_basis": self.type.legal_basis,
            "severity": self.type.severity,
            "confidence": self.confidence,
            "evidence_points": self.evidence_points,
            "legal_references": self.legal_references,
            "risk_mitigation": self.risk_mitigation,
            "counter_arguments": self.counter_arguments,
            "recommendation": self.recommendation,
        }


@dataclass
class DefenseAnalysis:
    """完整辩护分析报告"""
    case_id: str
    primary_defense: Optional[DefenseAngle]  # 主要辩护方向
    secondary_defenses: List[DefenseAngle]  # 辅助辩护方向
    overall_strength: float  # 整体辩护强度 0-100
    recommended_strategy: str  # 推荐辩护策略
    estimated_outcome: str  # 预估结果
    key_evidence_needed: List[str]  # 还需要补充的关键证据
    
    def to_dict(self) -> Dict:
        result = {
            "case_id": self.case_id,
            "primary_defense": self.primary_defense.to_dict() if self.primary_defense else None,
            "secondary_defenses": [d.to_dict() for d in self.secondary_defenses],
            "overall_strength": self.overall_strength,
            "recommended_strategy": self.recommended_strategy,
            "estimated_outcome": self.estimated_outcome,
            "key_evidence_needed": self.key_evidence_needed,
        }
        return result


class DefenseEnhancer:
    """辩护增强引擎"""
    
    # 关键词匹配模式
    DEFENSE_PATTERNS = {
        DefenseType.LEGITIMATE_DEFENSE: [
            (r"受到.*攻击", "遭受不法侵害"),
            (r"为了保护.*人身", "保护人身权利"),
            (r"制止.*侵害", "制止正在进行的不法侵害"),
            (r"防卫", "防卫行为"),
            (r"自卫", "自卫行为"),
        ],
        DefenseType.EMERGENCY_ESCAPE: [
            (r"为了避免.*危险", "紧急避险"),
            (r"迫不得已", "迫不得已的行为"),
            (r"紧急情况", "紧急状态"),
        ],
        DefenseType.SELF_DEFENSE_MINOR: [
            (r"超过必要限度", "可能构成防卫过当"),
            (r"明显超过", "防卫过当"),
        ],
        DefenseType.PROCEDURAL_VIOLATION: [
            (r"未.*告知", "未履行告知义务"),
            (r"超时.*羁押", "超期羁押"),
            (r"未.*授权", "未经授权搜查"),
        ],
        DefenseType.ILLEGAL_EVIDENCE: [
            (r"刑讯逼供", "非法取证"),
            (r"威胁.*取证", "威胁取证"),
            (r"诱供", "诱供"),
        ],
        DefenseType.VOLUNTARY_SURRENDER: [
            (r"自首", "自首情节"),
            (r"主动投案", "自首"),
            (r"自动投案", "自首"),
            (r"如实供述", "坦白"),
            (r"主动.*投案", "主动投案自首"),
            (r"投案自首", "投案自首"),
        ],
        DefenseType.MERITOUS_REPORTING: [
            (r"检举", "立功"),
            (r"揭发", "揭发犯罪"),
            (r"协助抓捕", "协助抓捕"),
        ],
        DefenseType.COMPENSATION: [
            (r"赔偿", "赔偿被害人"),
            (r"退赔", "退赃退赔"),
            (r"退赃", "退赃"),
            (r"谅解", "获得谅解"),
            (r"达成.*协议", "赔偿协议"),
            (r"赔.*被害人", "赔偿被害人"),
        ],
        DefenseType.COOPERATION: [
            (r"认罪认罚", "认罪认罚"),
            (r"认罪", "认罪"),
            (r"坦白", "坦白"),
        ],
        DefenseType.YOUTH: [
            (r"未满.*周", "未成年"),
            (r"十八周岁", "未成年人"),
        ],
        DefenseType.EVIDENCE_INSUFFICIENT: [
            (r"证据不足", "证据不充分"),
            (r"事实不清", "事实存疑"),
            (r"无法证明", "举证不能"),
            (r"证据.*瑕疵", "证据存在瑕疵"),
            (r"鉴定意见.*瑕疵", "鉴定意见存在瑕疵"),
            (r"合理怀疑", "存在合理怀疑"),
            (r"数额认定有误", "涉案数额认定有误"),
        ],
    }
    
    def __init__(self, legal_db=None):
        """初始化辩护增强器
        
        Args:
            legal_db: LegalDB实例，用于检索相关法律依据
        """
        self.legal_db = legal_db
        self._defense_cache: Dict[str, DefenseAnalysis] = {}
    
    def analyze_case(self, case_data: Dict) -> DefenseAnalysis:
        """分析案件，识别辩护角度
        
        Args:
            case_data: 案件数据，包含 facts, charges, defendants 等
            
        Returns:
            DefenseAnalysis: 完整辩护分析报告
        """
        case_id = case_data.get("case_id", "unknown")
        
        # 如果已缓存，直接返回
        if case_id in self._defense_cache:
            return self._defense_cache[case_id]
        
        # 提取案件关键信息
        facts = self._extract_facts(case_data)
        charges = self._extract_charges(case_data)
        defendants = self._extract_defendants(case_data)
        
        # 识别所有可能的辩护角度
        all_defenses = []
        all_defenses.extend(self._analyze_fact_defenses(facts))
        all_defenses.extend(self._analyze_person_defenses(defendants))
        all_defenses.extend(self._analyze_charge_defenses(charges))
        all_defenses.extend(self._analyze_procedural_defenses(case_data))
        
        # 去重并合并相似辩护
        all_defenses = self._merge_similar_defenses(all_defenses)
        
        # 按置信度排序
        all_defenses.sort(key=lambda x: x.confidence * 0.4 + x.type.severity * 10, reverse=True)
        
        # 确定主要和辅助辩护方向
        primary = all_defenses[0] if all_defenses else None
        secondary = all_defenses[1:6] if len(all_defenses) > 1 else []
        
        # 计算整体辩护强度
        overall_strength = self._calculate_overall_strength(primary, secondary)
        
        # 生成辩护策略
        strategy = self._generate_strategy(primary, secondary, overall_strength)
        
        # 预估结果
        outcome = self._estimate_outcome(primary, secondary, overall_strength)
        
        # 识别还需要的关键证据
        key_evidence = self._identify_key_evidence(primary, secondary, facts)
        
        result = DefenseAnalysis(
            case_id=case_id,
            primary_defense=primary,
            secondary_defenses=secondary,
            overall_strength=overall_strength,
            recommended_strategy=strategy,
            estimated_outcome=outcome,
            key_evidence_needed=key_evidence,
        )
        
        self._defense_cache[case_id] = result
        return result
    
    def _extract_facts(self, case_data: Dict) -> str:
        """提取案件事实"""
        fact_fields = [
            case_data.get("facts", {}).get("description", ""),
            case_data.get("facts", {}).get("detail", ""),
            case_data.get("case_summary", ""),
            case_data.get("fact_description", ""),
            # 补充：从减轻情节和法律争议中提取事实要素
            " ".join(str(f) for f in case_data.get("mitigating_factors", []) if f),
            " ".join(str(a) for a in case_data.get("legal_arguments", [])),
        ]
        return " ".join(f for f in fact_fields if f)
    
    def _extract_charges(self, case_data: Dict) -> List[Dict]:
        """提取罪名信息"""
        charges = []
        
        # 从多个可能的路径提取
        for path in ["charges", "charges_judged", "allegations"]:
            if path in case_data:
                if isinstance(case_data[path], dict):
                    charges.extend(case_data[path].values())
                elif isinstance(case_data[path], list):
                    charges.extend(case_data[path])
        
        return charges
    
    def _extract_defendants(self, case_data: Dict) -> List[Dict]:
        """提取被告人信息"""
        defendants = []
        
        for path in ["defendants", "accused", "defendant"]:
            if path in case_data:
                if isinstance(case_data[path], list):
                    defendants.extend(case_data[path])
                elif isinstance(case_data[path], dict):
                    defendants.append(case_data[path])
                elif isinstance(case_data[path], str):
                    defendants.append({"name": case_data[path]})
        
        return defendants
    
    def _analyze_fact_defenses(self, facts: str) -> List[DefenseAngle]:
        """基于事实识别辩护角度"""
        defenses = []
        facts_lower = facts.lower()
        facts_full = facts
        
        for defense_type, patterns in self.DEFENSE_PATTERNS.items():
            if defense_type in [
                DefenseType.YOUTH, DefenseType.ELDERLY, 
                DefenseType.DISABILITY, DefenseType.PROCEDURAL_VIOLATION
            ]:
                continue  # 这些是人员相关的，在别处处理
            
            matched_patterns = []
            evidence_points = []
            
            for pattern, description in patterns:
                if re.search(pattern, facts_full):
                    matched_patterns.append(description)
                    # 提取匹配上下文
                    for match in re.finditer(pattern, facts_full):
                        start = max(0, match.start() - 20)
                        end = min(len(facts_full), match.end() + 20)
                        context = facts_full[start:end]
                        evidence_points.append(f"...{context}...")
            
            if matched_patterns:
                # 计算置信度
                confidence = min(95, 60 + len(matched_patterns) * 10)
                
                # 获取法律依据
                legal_refs = self._get_legal_references(defense_type)
                
                defense = DefenseAngle(
                    type=defense_type,
                    confidence=confidence,
                    evidence_points=evidence_points[:5],  # 最多5个证据点
                    legal_references=legal_refs,
                    risk_mitigation=self._get_risk_mitigation(defense_type),
                    counter_arguments=self._get_counter_arguments(defense_type, facts),
                    recommendation=self._get_recommendation(defense_type, confidence),
                )
                defenses.append(defense)
        
        return defenses
    
    def _analyze_person_defenses(self, defendants: List[Dict]) -> List[DefenseAngle]:
        """基于人员特征识别辩护角度"""
        defenses = []
        
        for defendant in defendants:
            name = defendant.get("name", "")
            age = defendant.get("age", 0)
            disability = defendant.get("disability", "")
            mental_state = defendant.get("mental_state", "")
            
            # 未成年人
            if age and age < 18:
                defenses.append(DefenseAngle(
                    type=DefenseType.YOUTH,
                    confidence=95,
                    evidence_points=[f"被告人{name}年龄为{age}岁"],
                    legal_references=["《刑法》第17条", "《未成年人保护法》"],
                    risk_mitigation="应当从轻或减轻处罚",
                    counter_arguments=["如有前科可能影响从轻幅度"],
                    recommendation="重点强调未成年身份，申请社会调查",
                ))
            
            # 老年人
            if age and age >= 75:
                defenses.append(DefenseAngle(
                    type=DefenseType.ELDERLY,
                    confidence=95,
                    evidence_points=[f"被告人年龄{age}周岁"],
                    legal_references=["《刑法》第17条之一"],
                    risk_mitigation="故意犯罪可从轻，过失犯罪应从轻",
                    counter_arguments=["需证明年龄真实性"],
                    recommendation="申请适用老年人从宽处罚",
                ))
            
            # 精神状态
            if "精神" in mental_state or "病" in mental_state:
                defenses.append(DefenseAngle(
                    type=DefenseType.INSANITY,
                    confidence=70,
                    evidence_points=[f"精神状态：{mental_state}"],
                    legal_references=["《刑法》第18条"],
                    risk_mitigation="可能不负刑事责任",
                    counter_arguments=["需司法鉴定确认"],
                    recommendation="申请精神鉴定",
                ))
            
            # 残疾
            if disability:
                defenses.append(DefenseAngle(
                    type=DefenseType.DISABILITY,
                    confidence=90,
                    evidence_points=[f"残疾情况：{disability}"],
                    legal_references=["《刑法》第19条"],
                    risk_mitigation="可以从轻、减轻或免除处罚",
                    counter_arguments=["需证明残疾与犯罪关系"],
                    recommendation="申请残疾鉴定，强调可以从轻",
                ))
        
        return defenses
    
    def _analyze_charge_defenses(self, charges: List[Dict]) -> List[DefenseAngle]:
        """基于罪名识别辩护角度"""
        defenses = []
        
        for charge in charges:
            charge_name = charge.get("name", "")
            amount = charge.get("amount", 0)
            
            # 数额刚过门槛，考虑情节轻微
            if amount and 0 < amount < 100000:
                defenses.append(DefenseAngle(
                    type=DefenseType.CRIMINAL_MINOR,
                    confidence=65,
                    evidence_points=[f"涉案金额{amount}元，刚过入罪门槛"],
                    legal_references=["《刑法》第13条但书", "《刑法》第61条"],
                    risk_mitigation="情节轻微可不认为是犯罪，或从轻处罚",
                    counter_arguments=["需综合全案情节"],
                    recommendation="强调数额刚过门槛，争取不起诉或缓刑",
                ))
        
        return defenses
    
    def _analyze_procedural_defenses(self, case_data: Dict) -> List[DefenseAngle]:
        """识别程序性辩护角度"""
        defenses = []
        
        # 检查办案程序
        procedure = case_data.get("procedure", {})
        
        # 超期羁押
        detention_days = procedure.get("detention_days", 0)
        if detention_days > 37:  # 拘留最长37天
            defenses.append(DefenseAngle(
                type=DefenseType.PROCEDURAL_VIOLATION,
                confidence=85,
                evidence_points=[f"羁押时间已达{detention_days}天"],
                legal_references=["《刑事诉讼法》第89条", "《刑事诉讼法》第156条"],
                risk_mitigation="程序违法可能影响量刑",
                counter_arguments=["需证明超期非因客观原因"],
                recommendation="申请变更强制措施，程序违法可作为量刑参考",
            ))
        
        # 认罪认罚
        if case_data.get("confession", False) or case_data.get("plea_agreement"):
            defenses.append(DefenseAngle(
                type=DefenseType.COOPERATION,
                confidence=90,
                evidence_points=["被告人已认罪认罚"],
                legal_references=["《刑事诉讼法》第15条", "《关于适用认罪认罚从宽制度的指导意见》"],
                risk_mitigation="可以从宽处理",
                counter_arguments=["需保证认罪认罚真实性"],
                recommendation="积极适用认罪认罚从宽程序",
            ))
        
        return defenses
    
    def _merge_similar_defenses(self, defenses: List[DefenseAngle]) -> List[DefenseAngle]:
        """合并相似辩护角度"""
        # 简单的去重：按类型去重，保留置信度最高的
        seen = {}
        for d in defenses:
            if d.type not in seen or d.confidence > seen[d.type].confidence:
                seen[d.type] = d
        return list(seen.values())
    
    def _calculate_overall_strength(self, primary: Optional[DefenseAngle], 
                                    secondary: List[DefenseAngle]) -> float:
        """计算整体辩护强度"""
        if not primary:
            return 30
        
        base = primary.confidence * 0.5 + primary.type.severity * 8
        
        # 加上辅助辩护
        for s in secondary[:3]:
            base += s.confidence * 0.1 + s.type.severity * 2
        
        return min(100, max(0, base))
    
    def _generate_strategy(self, primary: Optional[DefenseAngle],
                          secondary: List[DefenseAngle],
                          overall_strength: float) -> str:
        """生成辩护策略"""
        if not primary:
            return "案件事实清楚，建议从量刑情节入手，争取从宽处理"
        
        strategies = []
        
        # 主要策略
        if primary.type == DefenseType.LEGITIMATE_DEFENSE:
            strategies.append("核心策略：无罪辩护（正当防卫）")
        elif primary.type == DefenseType.INSANITY:
            strategies.append("核心策略：无罪辩护（精神病人）")
        elif primary.type == DefenseType.VOLUNTARY_SURRENDER:
            strategies.append("核心策略：自首认定，争取从轻")
        elif primary.type == DefenseType.EVIDENCE_INSUFFICIENT:
            strategies.append("核心策略：证据不足，疑点利益归于被告")
        elif primary.type == DefenseType.CRIMINAL_MINOR:
            strategies.append("核心策略：情节轻微，争取不起诉或缓刑")
        else:
            strategies.append(f"核心策略：{primary.type.value}辩护")
        
        # 辅助策略
        if secondary:
            sec_types = [s.type.value for s in secondary[:3]]
            strategies.append(f"辅助策略：{'、'.join(sec_types)}")
        
        # 整体建议
        if overall_strength >= 80:
            strategies.append("整体强度高，建议作无罪或显著从宽辩护")
        elif overall_strength >= 60:
            strategies.append("整体强度中等，建议罪轻辩护为主")
        else:
            strategies.append("整体强度一般，建议积极配合，争取从宽")
        
        return "；".join(strategies)
    
    def _estimate_outcome(self, primary: Optional[DefenseAngle],
                         secondary: List[DefenseAngle],
                         overall_strength: float) -> str:
        """预估案件结果"""
        if not primary:
            return "可能判处有期徒刑，视情节从宽"
        
        if primary.type == DefenseType.LEGITIMATE_DEFENSE and primary.confidence > 80:
            return "无罪可能性较高"
        elif primary.type == DefenseType.INSANITY and primary.confidence > 80:
            return "不负刑事责任，但需强制医疗"
        elif primary.type == DefenseType.VOLUNTARY_SURRENDER:
            return "可减少基准刑的40%以下"
        elif primary.type == DefenseType.COMPENSATION:
            return "获谅解可减少基准刑的20-30%"
        elif primary.type == DefenseType.CRIMINAL_MINOR:
            return "情节轻微，可能不起诉或判处缓刑"
        elif overall_strength >= 70:
            return "从宽幅度较大，争取缓刑或显著减轻"
        elif overall_strength >= 50:
            return "可争取从轻处罚"
        else:
            return "从宽幅度有限"
    
    def _identify_key_evidence(self, primary: Optional[DefenseAngle],
                               secondary: List[DefenseAngle],
                               facts: str) -> List[str]:
        """识别还需要补充的关键证据"""
        evidence_needed = []
        
        if not primary:
            return evidence_needed
        
        if primary.type == DefenseType.LEGITIMATE_DEFENSE:
            evidence_needed.extend([
                "侵害正在进行的时间证据",
                "防卫行为必要性的现场证据",
                "双方力量对比的证据",
                "周围环境的证据",
            ])
        elif primary.type == DefenseType.INSANITY:
            evidence_needed.extend([
                "司法精神病鉴定",
                "病史资料",
                "案发时精神状态证据",
            ])
        elif primary.type == DefenseType.EVIDENCE_INSUFFICIENT:
            evidence_needed.extend([
                "现有证据的完整性审查",
                "关键证据的合法性审查",
                "证据链闭合性分析",
            ])
        
        return evidence_needed
    
    def _get_legal_references(self, defense_type: DefenseType) -> List[str]:
        """获取辩护类型的相关法律依据"""
        if self.legal_db:
            # 尝试从法律库检索
            try:
                search_results = self.legal_db.fulltext_search(defense_type.value)
                return [r.get("title", "") or r.get("article", "") for r in search_results[:3]]
            except:
                pass
        
        return [defense_type.legal_basis]
    
    def _get_risk_mitigation(self, defense_type: DefenseType) -> str:
        """获取辩护能减轻的风险"""
        mitigation_map = {
            DefenseType.LEGITIMATE_DEFENSE: "无罪",
            DefenseType.EMERGENCY_ESCAPE: "无罪或减轻处罚",
            DefenseType.INSANITY: "不负刑事责任",
            DefenseType.SELF_DEFENSE_MINOR: "减轻或免除处罚",
            DefenseType.ACCIDENT: "无罪",
            DefenseType.PROCEDURAL_VIOLATION: "量刑从宽",
            DefenseType.ILLEGAL_EVIDENCE: "排除非法证据",
            DefenseType.STATUTE_OF_LIMITATIONS: "不再追诉",
            DefenseType.CRIMINAL_MINOR: "不构成犯罪或从轻",
            DefenseType.VOLUNTARY_SURRENDER: "从轻或减轻处罚",
            DefenseType.MERITOUS_REPORTING: "从轻或减轻处罚",
            DefenseType.COMPENSATION: "从轻处罚",
            DefenseType.COOPERATION: "从宽处理",
            DefenseType.YOUTH: "从轻或减轻处罚",
            DefenseType.EVIDENCE_INSUFFICIENT: "无罪",
            DefenseType.RECIDIVISM_NOT: "不构成累犯",
            DefenseType.CRIME_REDUCED: "变更罪名",
        }
        return mitigation_map.get(defense_type, "从轻处罚")
    
    def _get_counter_arguments(self, defense_type: DefenseType, facts: str) -> List[str]:
        """获取可能的反驳观点"""
        counter_map = {
            DefenseType.LEGITIMATE_DEFENSE: [
                "事后防卫",
                "防卫超过必要限度",
                "不存在现实的不法侵害",
            ],
            DefenseType.EMERGENCY_ESCAPE: [
                "存在其他回避方法",
                "避险超过必要限度",
            ],
            DefenseType.VOLUNTARY_SURRENDER: [
                "被采取强制措施后交代",
                "如实供述但不构成自首",
            ],
            DefenseType.EVIDENCE_INSUFFICIENT: [
                "证据已达到确实充分标准",
                "可以排除合理怀疑",
            ],
        }
        return counter_map.get(defense_type, ["需根据案件具体情况判断"])
    
    def _get_recommendation(self, defense_type: DefenseType, confidence: float) -> str:
        """获取辩护建议"""
        if confidence >= 80:
            modifier = "强烈建议"
        elif confidence >= 60:
            modifier = "建议"
        else:
            modifier = "可考虑"
        
        rec_map = {
            DefenseType.LEGITIMATE_DEFENSE: f"{modifier}以正当防卫为核心进行无罪辩护",
            DefenseType.VOLUNTARY_SURRENDER: f"{modifier}主张自首情节，申请从轻处理",
            DefenseType.COMPENSATION: f"{modifier}积极赔偿，争取被害人谅解",
            DefenseType.CRIMINAL_MINOR: f"{modifier}强调情节轻微，申请不起诉或缓刑",
            DefenseType.EVIDENCE_INSUFFICIENT: f"{modifier}提出证据不足的辩护意见",
        }
        return rec_map.get(defense_type, f"{modifier}主张{defense_type.value}")


def analyze_case_defense(case_data: Dict, legal_db=None) -> Dict:
    """便捷函数：分析案件辩护角度
    
    Args:
        case_data: 案件数据
        legal_db: LegalDB实例
        
    Returns:
        Dict: 辩护分析结果（可JSON序列化的字典）
    """
    enhancer = DefenseEnhancer(legal_db)
    analysis = enhancer.analyze_case(case_data)
    return analysis.to_dict()


if __name__ == "__main__":
    # 测试
    test_case = {
        "case_id": "TEST-001",
        "facts": {
            "description": "被告人张某在回家途中遭遇李某持刀抢劫，张某在反抗过程中将李某刺伤。李某后经抢救无效死亡。被告人张某案发后主动投案自首。"
        },
        "defendants": [
            {"name": "张某", "age": 35}
        ],
        "charges": [
            {"name": "故意伤害罪"}
        ]
    }
    
    result = analyze_case_defense(test_case)
    print(json.dumps(result, ensure_ascii=False, indent=2))
