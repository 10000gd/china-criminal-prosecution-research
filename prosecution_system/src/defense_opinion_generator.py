# -*- coding: utf-8 -*-
"""
辩护意见生成器 - defense_opinion_generator.py

基于案件分析和辩护策略，生成辩护意见草稿：
- 辩护词结构生成
- 量刑辩护意见
- 无罪辩护意见
- 认罪认罚具结书
"""

import json
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class DefenseOpinionSection:
    """辩护意见的单个章节"""
    title: str
    content: str
    importance: int  # 1-5, 重要性
    
    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "content": self.content,
            "importance": self.importance,
        }


@dataclass
class DefenseOpinion:
    """完整辩护意见"""
    case_id: str
    case_name: str
    defendant_name: str
    crime: str
    
    # 各章节内容
    sections: List[DefenseOpinionSection]
    
    # 元数据
    generated_at: str
    primary_defense: str
    overall_conclusion: str
    
    def to_dict(self) -> Dict:
        return {
            "case_id": self.case_id,
            "case_name": self.case_name,
            "defendant_name": self.defendant_name,
            "crime": self.crime,
            "sections": [s.to_dict() for s in self.sections],
            "generated_at": self.generated_at,
            "primary_defense": self.primary_defense,
            "overall_conclusion": self.overall_conclusion,
        }
    
    def to_markdown(self) -> str:
        """转换为Markdown格式"""
        lines = [
            f"# {self.case_name} 辩护词",
            f"",
            f"**案号**：{self.case_id}",
            f"**被告人**：{self.defendant_name}",
            f"**涉嫌罪名**：{self.crime}",
            f"**生成时间**：{self.generated_at}",
            f"",
            f"---",
            f"",
        ]
        
        for section in self.sections:
            lines.append(f"## {section.title}")
            lines.append("")
            lines.append(section.content)
            lines.append("")
        
        lines.append("---")
        lines.append("")
        lines.append(f"## 综合结论")
        lines.append("")
        lines.append(self.overall_conclusion)
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("*本辩护意见由系统辅助生成，仅供参考使用。*")
        
        return "\n".join(lines)


class DefenseOpinionGenerator:
    """辩护意见生成器"""
    
    def __init__(self, defense_analysis: Dict = None, 
                 similar_cases: List[Dict] = None):
        """初始化生成器
        
        Args:
            defense_analysis: 辩护分析结果
            similar_cases: 类似案例
        """
        self.defense_analysis = defense_analysis or {}
        self.similar_cases = similar_cases or []
    
    def generate_full_opinion(self, case_data: Dict) -> DefenseOpinion:
        """生成完整辩护意见
        
        Args:
            case_data: 案件数据
            
        Returns:
            DefenseOpinion: 辩护意见对象
        """
        sections = []
        
        # 提取基本信息
        case_id = case_data.get("case_id", "未知")
        case_name = case_data.get("case_name", case_data.get("case_summary", "未知案件"))
        defendant_name = self._extract_defendant_name(case_data)
        crime = self._extract_crime(case_data)
        
        # 生成各章节
        sections.append(self._generate_intro(case_data))
        
        # 根据辩护类型生成相应章节
        primary_defense = self.defense_analysis.get("primary_defense", {})
        defense_type = primary_defense.get("type", "")
        
        if defense_type in ["正当防卫", "紧急避险", "精神病人无刑事责任", "不可抗力/意外事件"]:
            # 无罪辩护
            sections.append(self._generate_innocence_section(defense_type))
            sections.append(self._generate_legal_basis_section())
        elif defense_type in ["证据不足", "事实争议"]:
            # 证据辩护
            sections.append(self._generate_evidence_challenge_section())
        else:
            # 量刑辩护
            sections.append(self._generate_sentencing_section())
        
        # 附加辩护意见（如果有）
        if self.similar_cases:
            sections.append(self._generate_similar_case_section())
        
        # 量刑建议
        sections.append(self._generate_sentencing_recommendation())
        
        # 综合结论
        conclusion = self._generate_conclusion(case_data, defense_type)
        
        return DefenseOpinion(
            case_id=case_id,
            case_name=case_name,
            defendant_name=defendant_name,
            crime=crime,
            sections=sections,
            generated_at=datetime.now().strftime("%Y年%m月%d日 %H:%M"),
            primary_defense=defense_type,
            overall_conclusion=conclusion,
        )
    
    def _generate_intro(self, case_data: Dict) -> DefenseOpinionSection:
        """生成引言部分"""
        defendant_name = self._extract_defendant_name(case_data)
        crime = self._extract_crime(case_data)
        
        content = f"""辩护人依法接受本案被告人{defendant_name}的委托，担任其辩护人，参与本案诉讼活动。

经查阅案卷材料、会见被告人并了解案件情况，辩护人认为：{crime}的指控存在重大异议，理由如下：

一、关于案件基本事实

{case_data.get('case_summary', case_data.get('facts', {}).get('description', '详见案件材料'))}

二、辩护总体意见

根据本案事实和法律依据，辩护人认为应当对被告人{defendant_name}从轻、减轻处罚乃至宣告无罪。"""
        
        return DefenseOpinionSection(
            title="一、辩护意见概述",
            content=content,
            importance=5,
        )
    
    def _generate_innocence_section(self, defense_type: str) -> DefenseOpinionSection:
        """生成无罪辩护章节"""
        primary = self.defense_analysis.get("primary_defense", {})
        evidence_points = primary.get("evidence_points", [])
        legal_basis = primary.get("legal_references", [])
        
        evidence_text = "\n".join(f"- {e}" for e in evidence_points[:3]) if evidence_points else "详见案件材料"
        legal_text = "、".join(legal_basis) if legal_basis else "相关法律规定"
        
        content_map = {
            "正当防卫": f"""根据《刑法》第二十条之规定，为了使国家、公共利益、本人或者他人的人身、财产和其他权利免受正在进行的不法侵害，而采取的制止不法侵害的行为，对不法侵害人造成损害的，属于正当防卫，不负刑事责任。

经分析本案事实，辩护人认为被告人的行为完全符合正当防卫的构成要件：

（一）存在现实的不法侵害
本案中，存在对被告人不法侵害的现实危险，证据显示：
{evidence_text}

（二）防卫行为针对的是不法侵害人本人
被告人的行为完全是针对正在进行的不法侵害人本人，并未伤及无辜。

（三）防卫行为是为了保护合法权益
被告人是为保护其本人/他人的合法权益免受侵害。

（四）不法侵害正在进行
从时间上看，不法侵害处于正在进行状态，被告人的防卫行为具有紧迫性和必要性。

综上，根据{legal_text}之规定，被告人的行为应当认定为正当防卫，不负刑事责任。""",
            
            "紧急避险": f"""根据《刑法》第二十一条之规定，为了使国家、公共利益、本人或者他人的人身、财产和其他权利免受正在发生的危险，不得已采取的紧急避险行为，造成损害的，不负刑事责任。

本案中，被告人的行为符合紧急避险的构成条件，{legal_text}。

恳请法庭依法认定被告人不构成犯罪。""",
            
            "精神病人无刑事责任": """经司法鉴定（或申请鉴定），被告人案发时处于精神疾病发作期，丧失辨认和控制能力。

根据《刑法》第十八条之规定，精神病人在不能辨认或者不能控制自己行为的时候造成危害结果，经法定程序鉴定确认的，不负刑事责任。

恳请法庭依法宣告被告人无罪，并对其作出强制医疗决定。""",
            
            "不可抗力/意外事件": """经查明，被告人的行为虽然在客观上造成了损害结果，但不是出于故意或者过失，而是由于不能抗拒或者不能预见的原因所引起的。

根据《刑法》第十六条之规定，这种情况下被告人不构成犯罪。

恳请法庭依法宣告被告人无罪。""",
        }
        
        content = content_map.get(defense_type, f"根据{legal_text}之规定，被告人应当认定为无罪。")
        
        return DefenseOpinionSection(
            title="二、关于无罪辩护意见",
            content=content,
            importance=5,
        )
    
    def _generate_legal_basis_section(self) -> DefenseOpinionSection:
        """生成法律依据章节"""
        primary = self.defense_analysis.get("primary_defense", {})
        legal_basis = primary.get("legal_references", [])
        legal_text = "\n".join(f"- {ref}" for ref in legal_basis) if legal_basis else "相关法律规定"
        
        counter_args = primary.get("counter_arguments", [])
        counter_text = "\n".join(f"1. {arg}" for arg in counter_args) if counter_args else "无"
        
        content = f"""辩护人认为，本案应当适用以下法律依据：

{legal_text}

二、关于控方可能提出的反驳意见的分析

控方可能提出的反驳意见：
{counter_text}

针对上述反驳，辩护人认为：
（详见具体章节论述）

三、法律分析

基于上述法律依据和案件事实，辩护人认为被告人的行为不符合犯罪构成要件，依法不应当追究刑事责任。"""
        
        return DefenseOpinionSection(
            title="三、法律依据与分析",
            content=content,
            importance=4,
        )
    
    def _generate_evidence_challenge_section(self) -> DefenseOpinionSection:
        """生成证据质疑章节"""
        primary = self.defense_analysis.get("primary_defense", {})
        evidence_points = primary.get("evidence_points", [])
        
        content = """辩护人经审查全案证据材料，认为现有证据不足以认定被告人构成犯罪，理由如下：

一、证据不足的具体表现

1. 关于犯罪事实的证据
现有证据无法完整证明犯罪事实的全部构成要素，存在关键事实不清的问题。

2. 关于被告人主观故意的证据
现有证据不足以证明被告人具有犯罪的主观故意，不能排除合理怀疑。

3. 关于证据链闭合性
证据之间存在矛盾，未能形成完整的证据链。

二、刑事诉讼法相关要求

根据《刑事诉讼法》第五十五条之规定，认定案件事实必须以证据为依据，做到证据确实、充分。

三、辩护意见

基于上述分析，恳请法庭依据"疑点利益归于被告人"原则，宣告被告人无罪。"""
        
        return DefenseOpinionSection(
            title="二、关于证据不足的辩护意见",
            content=content,
            importance=5,
        )
    
    def _generate_sentencing_section(self) -> DefenseOpinionSection:
        """生成量刑辩护章节"""
        primary = self.defense_analysis.get("primary_defense", {})
        secondary = self.defense_analysis.get("secondary_defenses", [])
        
        primary_text = f"一、主要辩护情节：{primary.get('type', '待认定')}\n\n{primary.get('legal_basis', '')}"
        
        secondary_texts = []
        for i, s in enumerate(secondary[:3], 1):
            secondary_texts.append(f"{i}. {s.get('type', '')}：{s.get('legal_basis', '')}")
        secondary_text = "\n".join(secondary_texts) if secondary_texts else "无"
        
        overall_strength = self.defense_analysis.get("overall_strength", 50)
        
        content = f"""即使法庭认为被告人的行为构成犯罪，辩护人认为应当对被告人从轻或减轻处罚，具体理由如下：

{primary_text}

二、辅助辩护情节

{secondary_text}

三、关于量刑幅度的辩护意见

综合考虑上述情节，辩护人认为：
- 本案的整体辩护强度评分为 {overall_strength}/100
- 被告人具有从宽处理的情节
- 建议法庭在法定刑幅度内从轻或减轻处罚

四、类案参考

与本案相似的案例中，类似的辩护理由获得了法庭的采纳，建议法庭参照同类案例的处理方式。"""
        
        return DefenseOpinionSection(
            title="二、关于量刑的辩护意见",
            content=content,
            importance=4,
        )
    
    def _generate_similar_case_section(self) -> DefenseOpinionSection:
        """生成类案参考章节"""
        case_texts = []
        for i, case in enumerate(self.similar_cases[:3], 1):
            outcome = case.get("outcome", "未知")
            reasoning = case.get("reasoning", "")
            case_texts.append(
                f"{i}. **{case.get('case_name', '类案')}**：{outcome}。{reasoning}"
            )
        
        cases_text = "\n\n".join(case_texts)
        
        content = f"""辩护人检索到以下与本案案情相似的案例，供法庭参考：

{cases_text}

上述案例表明，类似情形下法庭采纳了相应的辩护意见，作出了对被告人从宽处理的判决。

恳请法庭参照上述类案的处理方式，对本案被告人作出公正判决。"""
        
        return DefenseOpinionSection(
            title="三、类案参考",
            content=content,
            importance=3,
        )
    
    def _generate_sentencing_recommendation(self) -> DefenseOpinionSection:
        """生成量刑建议章节"""
        estimated_outcome = self.defense_analysis.get("estimated_outcome", "")
        key_evidence = self.defense_analysis.get("key_evidence_needed", [])
        
        evidence_text = "\n".join(f"- {e}" for e in key_evidence[:3]) if key_evidence else "无"
        
        content = f"""综合本案事实、证据及法律适用，辩护人提出如下量刑建议：

一、关于刑罚种类和幅度的建议

{estimated_outcome}

二、关于从轻、减轻处罚情节的认定

（一）法定从轻、减轻情节
{self._get_statutory_mitigation_text()}

（二）酌定从轻情节
{self._get_discretionary_mitigation_text()}

三、关于进一步查证的建议

为准确认定案件事实，建议法庭进一步核实以下证据：
{evidence_text}

四、结语

恳请法庭采纳辩护人的上述意见，依法对被告人作出公正判决。"""
        
        return DefenseOpinionSection(
            title="四、量刑建议",
            content=content,
            importance=4,
        )
    
    def _generate_conclusion(self, case_data: Dict, defense_type: str) -> str:
        """生成综合结论"""
        defendant_name = self._extract_defendant_name(case_data)
        
        court = case_data.get('court') or '所在辖区人民法院'
        attorney = case_data.get('attorney_name') or '辩护人'
        if defense_type in ("正当防卫", "紧急避险", "精神病人无刑事责任", "不可抗力/意外事件"):
            conclusion = f"""综上所述，辩护人认为：

被告人{defendant_name}的行为依法不构成犯罪，恳请法庭依法宣告其无罪。

如法庭认为被告人的行为构成犯罪，请依据从轻、减轻处罚情节，在法定刑幅度内对其从轻或减轻处罚。

此致
{court}

{attorney}：__________
年  月  日"""
        else:
            conclusion = f"""综上所述，辩护人认为：

被告人{defendant_name}虽涉嫌犯罪，但具有多项从轻、减轻处罚情节，社会危害性较小，人身危险性较低。

恳请法庭依法对其从轻或减轻处罚，给其一个改过自新的机会。

此致
{court}

{attorney}：__________
年  月  日"""
        
        return conclusion
    
    def _extract_defendant_name(self, case_data: Dict) -> str:
        """提取被告人姓名"""
        defendants = case_data.get("defendants", [])
        if isinstance(defendants, list) and defendants:
            return defendants[0].get("name", "被告")
        if isinstance(defendants, dict):
            return defendants.get("name", "被告")
        if isinstance(defendants, str):
            return defendants
        return "被告"
    
    def _extract_crime(self, case_data: Dict) -> str:
        """提取罪名"""
        charges = case_data.get("charges", [])
        if isinstance(charges, dict):
            for c in charges.values():
                if isinstance(c, dict) and "name" in c:
                    return c.get("name", "未知罪名")
        if isinstance(charges, list) and charges:
            return charges[0].get("name", "未知罪名")
        return "未知罪名"
    
    def _get_statutory_mitigation_text(self) -> str:
        """获取法定从轻减轻情节文本（同时查 primary + secondary）"""
        primary = self.defense_analysis.get("primary_defense", {})
        primary_type = primary.get("type", "")
        secondary = self.defense_analysis.get("secondary_defenses", [])
        
        STATUTORY_MAP = {
            # 法定情节（刑法典直接依据）
            "自首": "被告人主动投案，如实供述罪行，依据《刑法》第67条，可以从轻或减轻处罚。",
            "立功": "被告人揭发他人犯罪或提供重要线索，依据《刑法》第68条，可以从轻或减轻处罚。",
            "未成年人": "被告人系未成年人，依据《刑法》第17条，应当从轻或减轻处罚。",
            "精神病人": "被告人系精神病人，依据《刑法》第18条，可以从轻或减轻处罚。",
            "聋哑人/盲人": "被告人系又聋又哑的人或盲人，依据《刑法》第19条，可以从轻、减轻或免除处罚。",
            "正当防卫": "被告人行为属于正当防卫，依据《刑法》第20条，不负刑事责任。",
            "防卫过当减免": "被告人行为属于防卫过当，依据《刑法》第20条第二款，应当减轻或免除处罚。",
            "紧急避险": "被告人行为属于紧急避险，依据《刑法》第21条，不负刑事责任。",
            # 量刑辩护（也是重要辩护角度，但放在法定情节下说明）
            "坦白/认罪认罚": "被告人认罪认罚，依据《刑法》第67条第三款及《关于适用认罪认罚从宽制度的指导意见》，可以从宽处理。",
            "赔偿谅解": "被告人积极赔偿被害人损失并取得谅解，可作为酌定从轻情节，建议法庭从轻处罚。",
            "情节轻微": "涉案数额刚过入罪门槛，犯罪情节轻微，依据《刑法》第37条，可以免予刑事处罚。",
        }
        
        found = []
        # 先查 primary
        if primary_type and primary_type in STATUTORY_MAP:
            found.append(STATUTORY_MAP[primary_type])
        # 再查 secondary（去重）
        for s in secondary:
            dtype = s.get("type", "")
            if dtype and dtype in STATUTORY_MAP and STATUTORY_MAP[dtype] not in found:
                found.append(STATUTORY_MAP[dtype])
        
        if found:
            return "\n".join(f"- {t}" for t in found)
        return "请法庭依法认定从轻、减轻情节。"
    
    def _get_discretionary_mitigation_text(self) -> str:
        """获取酌定从轻情节文本（排除已出现在法定情节中的）"""
        secondary = self.defense_analysis.get("secondary_defenses", [])
        
        # 已在法定情节中展示的，跳过避免重复
        statutory_keys = {"自首", "立功", "正当防卫", "紧急避险",
                          "防卫过当减免", "未成年人", "精神病人", "聋哑人/盲人",
                          "坦白/认罪认罚", "赔偿谅解", "情节轻微"}
        
        texts = []
        for s in secondary[:5]:
            dtype = s.get("type", "")
            if dtype and dtype not in statutory_keys:
                mitigation = s.get("risk_mitigation", "从轻处罚")
                texts.append(f"- {dtype}：{mitigation}")
        
        # 补充常见的酌定情节
        if not texts:
            texts.append("- 初犯、偶犯：社会危害性较低")
            texts.append("- 认罪态度良好：如实供述犯罪事实")
            texts.append("- 有悔罪表现：积极改正错误")
        
        return "\n".join(texts)


def generate_defense_opinion(case_data: Dict,
                            defense_analysis: Dict = None,
                            similar_cases: List[Dict] = None,
                            output_format: str = "dict") -> Dict:
    """便捷函数：生成辩护意见
    
    Args:
        case_data: 案件数据
        defense_analysis: 辩护分析结果
        similar_cases: 类似案例
        output_format: 输出格式（dict/markdown）
        
    Returns:
        辩护意见（dict或markdown字符串）
    """
    generator = DefenseOpinionGenerator(defense_analysis, similar_cases)
    opinion = generator.generate_full_opinion(case_data)
    
    if output_format == "markdown":
        return opinion.to_markdown()
    return opinion.to_dict()


if __name__ == "__main__":
    # 测试
    test_case = {
        "case_id": "TEST-001",
        "case_name": "张某故意伤害案",
        "defendant": "张某",
        "defendants": [{"name": "张某", "age": 35}],
        "charges": [{"name": "故意伤害罪"}],
        "case_summary": "被告人张某在回家途中遭遇李某持刀抢劫，张某在反抗过程中将李某刺伤。李某后经抢救无效死亡。被告人张某案发后主动投案自首。",
        "court": "北京市第一中级人民法院",
    }
    
    test_analysis = {
        "primary_defense": {
            "type": "正当防卫",
            "confidence": 85,
            "legal_basis": "《刑法》第20条",
            "evidence_points": ["遭遇持刀抢劫", "正在进行的不法侵害", "防卫行为"],
            "risk_mitigation": "无罪",
        },
        "secondary_defenses": [
            {"type": "自首", "risk_mitigation": "从轻或减轻处罚"},
        ],
        "overall_strength": 75,
        "estimated_outcome": "无罪可能性较高",
    }
    
    opinion = generate_defense_opinion(test_case, test_analysis, output_format="markdown")
    print(opinion)
