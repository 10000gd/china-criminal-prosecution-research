# -*- coding: utf-8 -*-
"""
案由推理引擎 - prosecution_system/src/case_reasoning_engine.py

功能：
- 根据案情描述，自动推荐可能适用的罪名
- 对每个罪名输出：罪名名称、置信度、匹配关键词、量刑区间、法律依据

原理：
- 关键词模式匹配 + 法条关联
- 多关键词叠加提升置信度
- 覆盖常见多发犯罪类型

覆盖罪名（按章节分类）：
【财产类】盗窃罪 / 诈骗罪 / 抢夺罪 / 敲诈勒索罪 / 职务侵占罪 / 挪用资金罪
         故意毁坏财物罪 / 合同诈骗罪 / 贷款诈骗罪 / 信用卡诈骗罪
【经济类】非法经营罪 / 虚开增值税专用发票罪 / 非法吸收公众存款罪 / 集资诈骗罪
【职务类】受贿罪 / 行贿罪 / 贪污罪 / 挪用公款罪
【人身类】故意伤害罪 / 过失致人重伤罪 / 寻衅滋事罪
【毒品类】贩卖毒品罪 / 非法持有毒品罪 / 制造毒品罪
【环境类】污染环境罪
【交通类】危险驾驶罪 / 交通肇事罪
【其他类】开设赌场罪 / 拒不支付劳动报酬罪 / 非法侵入住宅罪
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import re


# =============================================================================
# 罪名模式定义
# =============================================================================

@dataclass
class CrimePattern:
    """单个罪名的推理模式"""
    name: str                              # 罪名全称
    aliases: List[str]                     # 别名/简称
    category: str                          # 分类：财产/经济/职务/人身/毒品/环境/交通/其他
    keywords: List[str]                   # 触发关键词（OR关系）
    compound_keywords: List[List[str]]     # 复合关键词（AND关系，全部出现才触发）
    exclude_keywords: List[str]           # 排除关键词（有则降低置信度）
    legal_basis: str                      # 刑法条文
    sentencing_min: str                   # 法定最低刑
    sentencing_max: str                   # 法定最高刑
    sentencing_note: str                  # 量刑说明
    notes: str = ""                       # 备注/特殊说明

    def match(self, text: str) -> Dict[str, Any]:
        """对输入文本进行匹配，返回匹配结果"""
        text_lower = text.lower()
        text_norm = text.replace(" ", "").replace("　", "")

        # 复合关键词匹配（AND）
        compound_score = 0
        compound_matched = []
        for group in self.compound_keywords:
            if all(kw in text_norm for kw in group):
                compound_score += len(group)
                compound_matched.append("+".join(group))

        # 单独关键词匹配（OR）
        keyword_score = 0
        keyword_matched = []
        for kw in self.keywords:
            if kw in text_norm:
                keyword_score += 1
                keyword_matched.append(kw)

        # 排除关键词匹配
        exclude_score = 0
        exclude_matched = []
        for kw in self.exclude_keywords:
            if kw in text_norm:
                exclude_score += 1
                exclude_matched.append(kw)

        total_score = compound_score + keyword_score
        # 有排除词则降低
        if exclude_score > 0:
            total_score = max(0, total_score - exclude_score * 2)

        # 置信度计算
        if total_score == 0:
            confidence = "低"
        elif total_score >= 3 or len(compound_matched) >= 1:
            confidence = "高"
        elif total_score >= 2:
            confidence = "中"
        else:
            confidence = "低"

        return {
            "matched": total_score > 0,
            "total_score": total_score,
            "compound_matched": compound_matched,
            "keyword_matched": keyword_matched,
            "exclude_matched": exclude_matched,
            "confidence": confidence,
        }


# =============================================================================
# 罪名模式库
# =============================================================================

CRIME_PATTERNS: List[CrimePattern] = [

    # ── 财产类 ────────────────────────────────────────────────────────────────

    CrimePattern(
        name="盗窃罪",
        aliases=["偷窃", "盗取", "窃取"],
        category="财产类",
        keywords=["盗窃", "偷", "窃取", "偷盗", "入室盗窃", "顺手牵羊", "扒窃", "偷东西", "偷钱", "偷手机", "偷电脑"],
        compound_keywords=[
            ["秘密", "窃取"], ["非法", "占有"], ["窃取", "财物"], ["盗窃", "他人"],
        ],
        exclude_keywords=["抢劫", "抢夺", "诈骗", "敲诈"],
        legal_basis="刑法第264条",
        sentencing_min="三年以下有期徒刑",
        sentencing_max="十年以上有期徒刑或无期徒刑",
        sentencing_note="数额较大≥各省标准 / 数额巨大 / 数额特别巨大",
    ),

    CrimePattern(
        name="诈骗罪",
        aliases=["欺诈", "骗取"],
        category="财产类",
        keywords=["诈骗", "欺诈", "骗取", "冒充", "假借", "虚构", "伪造", "欺骗", "电信诈骗", "网络诈骗"],
        compound_keywords=[
            ["虚构", "事实"], ["隐瞒", "真相"], ["骗取", "财物"], ["非法", "占有"],
            ["冒充", "身份"], ["伪造", "证件"], ["虚假", "宣传"],
        ],
        exclude_keywords=["合同", "贷款", "信用卡", "集资"],
        legal_basis="刑法第266条",
        sentencing_min="三年以下有期徒刑",
        sentencing_max="十年以上有期徒刑或无期徒刑",
        sentencing_note="数额较大≥5000元(2022解释) / 数额巨大≥5万 / 数额特别巨大≥50万",
    ),

    CrimePattern(
        name="抢夺罪",
        aliases=["飞车抢夺", "当街抢夺"],
        category="财产类",
        keywords=["抢夺", "夺走", "公然夺取", "趁人不备", "飞车抢夺", "当面夺走", "强抢"],
        compound_keywords=[
            ["公然", "夺取"], ["趁人", "不备"], ["夺取", "财物"],
        ],
        exclude_keywords=["抢劫", "盗窃", "诈骗"],
        legal_basis="刑法第267条",
        sentencing_min="三年以下有期徒刑",
        sentencing_max="十年以上有期徒刑或无期徒刑",
        sentencing_note="数额较大≥各省标准 / 数额巨大 / 数额特别巨大",
    ),

    CrimePattern(
        name="敲诈勒索罪",
        aliases=["恐吓", "要挟"],
        category="财产类",
        keywords=["敲诈", "勒索", "恐吓", "要挟", "威胁", "威逼", "索要", "讹诈", "黑社会性质"],
        compound_keywords=[
            ["恐吓", "威胁"], ["要挟", "索要"], ["敲诈", "勒索"], ["以暴力", "相威胁"],
            ["不给钱", "就"], ["威胁", "举报"],
        ],
        exclude_keywords=[],
        legal_basis="刑法第274条",
        sentencing_min="三年以下有期徒刑",
        sentencing_max="十年以上有期徒刑",
        sentencing_note="数额较大≥2000元(各省不同) / 数额巨大 / 数额特别巨大",
    ),

    CrimePattern(
        name="职务侵占罪",
        aliases=["侵占", "职务侵占"],
        category="财产类",
        keywords=["职务侵占", "侵占公司", "侵占公司财产", "公司高管", "财务人员", "占为己有"],
        compound_keywords=[
            ["利用职务便利", "占为己有"], ["侵占", "公司财物"], ["将本单位", "非法占为己有"],
        ],
        exclude_keywords=["挪用", "公款", "收受", "贿赂", "索取贿赂", "贪污"],
        legal_basis="刑法第271条",
        sentencing_min="三年以下有期徒刑",
        sentencing_max="十年以上有期徒刑",
        sentencing_note="数额较大≥3万 / 数额巨大≥100万(2022标准)",
    ),

    CrimePattern(
        name="挪用资金罪",
        aliases=["挪用公司资金", "挪用公款"],
        category="财产类",
        keywords=["挪用", "挪用资金", "挪用公司", "挪用款项", "私用", "挪用归个人"],
        compound_keywords=[
            ["挪用", "资金"], ["挪用", "公司款项"], ["利用职务", "挪用"],
            ["挪用", "归个人使用"],
        ],
        exclude_keywords=["贪污", "侵占", "职务侵占"],
        legal_basis="刑法第272条",
        sentencing_min="三年以下有期徒刑",
        sentencing_max="十年以上有期徒刑",
        sentencing_note="数额较大≥5万 / 数额巨大≥200万（超3个月未还）",
    ),

    CrimePattern(
        name="故意毁坏财物罪",
        aliases=["毁坏", "损坏财物"],
        category="财产类",
        keywords=["毁坏", "故意毁坏", "损坏", "破坏", "砸", "烧毁", "摔坏", "销毁"],
        compound_keywords=[
            ["故意", "毁坏"], ["损坏", "财物"], ["毁坏", "他人财产"],
        ],
        exclude_keywords=["生产", "安全事故", "交通事故"],
        legal_basis="刑法第275条",
        sentencing_min="三年以下有期徒刑、拘役或罚金",
        sentencing_max="三年以上七年以下有期徒刑",
        sentencing_note="数额较大≥5000元（各省不同）",
    ),

    CrimePattern(
        name="合同诈骗罪",
        aliases=["合同欺诈"],
        category="财产类",
        keywords=["合同诈骗", "合同欺诈", "签订合同", "收受货物", "收受货款", "骗取合同", "骗取货款", "骗取", "虚假合同"],
        compound_keywords=[
            ["合同", "诈骗"], ["签订", "虚假合同"], ["收受货物", "逃匿"], ["合同", "骗取财物"],
            ["骗取", "合同"], ["骗取", "货款"],
        ],
        exclude_keywords=[],
        legal_basis="刑法第224条",
        sentencing_min="三年以下有期徒刑",
        sentencing_max="十年以上有期徒刑或无期徒刑",
        sentencing_note="数额较大≥2万 / 数额巨大≥10万 / 数额特别巨大≥50万",
    ),

    CrimePattern(
        name="贷款诈骗罪",
        aliases=["骗取贷款"],
        category="财产类",
        keywords=["贷款诈骗", "骗取贷款", "伪造贷款", "虚假贷款", "骗贷"],
        compound_keywords=[
            ["伪造", "贷款材料"], ["骗取", "银行贷款"], ["贷款诈骗"],
        ],
        exclude_keywords=["合法", "正常贷款"],
        legal_basis="刑法第193条",
        sentencing_min="三年以下有期徒刑",
        sentencing_max="十年以上有期徒刑或无期徒刑",
        sentencing_note="数额较大≥2万 / 数额巨大≥20万 / 数额特别巨大≥100万",
    ),

    CrimePattern(
        name="信用卡诈骗罪",
        aliases=["盗刷", "信用卡诈骗"],
        category="财产类",
        keywords=["信用卡诈骗", "盗刷", "冒用信用卡", "伪造信用卡", "恶意透支", "盗取信用卡"],
        compound_keywords=[
            ["盗刷", "信用卡"], ["冒用", "他人信用卡"], ["恶意透支"],
            ["伪造", "信用卡"],
        ],
        exclude_keywords=["正常", "合法使用"],
        legal_basis="刑法第196条",
        sentencing_min="三年以下有期徒刑",
        sentencing_max="十年以上有期徒刑或无期徒刑",
        sentencing_note="数额较大≥5000元 / 数额巨大≥5万 / 数额特别巨大≥50万",
    ),

    # ── 经济类 ────────────────────────────────────────────────────────────────

    CrimePattern(
        name="非法经营罪",
        aliases=["非法经营", "无证经营"],
        category="经济类",
        keywords=["非法经营", "无证经营", "未经许可", "非法经营罪", "倒卖", "哄抬物价", "黑市"],
        compound_keywords=[
            ["未经", "许可", "经营"], ["非法", "从事", "经营活动"],
            ["倒卖", "专营"], ["哄抬", "物价"],
        ],
        exclude_keywords=["合法", "有证"],
        legal_basis="刑法第225条",
        sentencing_min="五年以下有期徒刑或拘役",
        sentencing_max="十五年有期徒刑",
        sentencing_note="情节严重 / 情节特别严重（非法经营额≥50万或所得≥10万）",
    ),

    CrimePattern(
        name="虚开增值税专用发票罪",
        aliases=["虚开发票", "虚开增值税发票"],
        category="经济类",
        keywords=["虚开发票", "虚开增值税", "虚开专票", "开具假发票", "发票犯罪", "增值税发票"],
        compound_keywords=[
            ["虚开", "增值税发票"], ["虚开", "专用发票"], ["为他人虚开", "发票"],
            ["介绍虚开", "发票"],
        ],
        exclude_keywords=["合法", "正常经营", "善意取得"],
        legal_basis="刑法第205条之一",
        sentencing_min="三年以下有期徒刑",
        sentencing_max="无期徒刑",
        sentencing_note="虚开税款数额≥5万入罪 / 数额较大 / 数额巨大 / 数额特别巨大",
    ),

    # ── 职务类 ────────────────────────────────────────────────────────────────

    CrimePattern(
        name="受贿罪",
        aliases=["收受贿赂", "索取贿赂"],
        category="职务类",
        keywords=["受贿", "收受贿赂", "索取贿赂", "收钱", "收受财物", "行贿受贿", "官员受贿", "国家工作人员", "他人财物", "行贿人"],
        compound_keywords=[
            ["国家工作人员", "受贿"], ["利用职务便利", "收受"],
            ["索取", "他人财物"], ["非法收受", "财物"],
            ["收受", "他人财物"],
        ],
        exclude_keywords=["合法收入", "正常礼尚往来", "侵占", "贪污", "挪用"],
        legal_basis="刑法第385条",
        sentencing_min="三年以下有期徒刑或拘役",
        sentencing_max="死刑",
        sentencing_note="数额较大≥3万 / 数额巨大≥20万 / 数额特别巨大≥300万（2016解释）",
    ),

    CrimePattern(
        name="行贿罪",
        aliases=["送钱", "给予财物"],
        category="职务类",
        keywords=["行贿", "向官员行贿", "送钱", "给予财物", "给予国家工作人员"],
        compound_keywords=[
            ["为谋取", "不正当利益", "给予"], ["向", "国家工作人员", "行贿"],
            ["给予", "国家工作人员", "财物"],
        ],
        exclude_keywords=["合法投标", "正常商业"],
        legal_basis="刑法第389条",
        sentencing_min="三年以下有期徒刑或拘役",
        sentencing_max="十年以上有期徒刑或无期徒刑",
        sentencing_note="为谋取不正当利益，给予国家工作人员财物 ≥3万入罪（2016解释）",
    ),

    CrimePattern(
        name="贪污罪",
        aliases=["贪污", "侵吞"],
        category="职务类",
        keywords=["贪污", "侵吞", "骗取", "克扣", "国家工作人员贪污", "挪用公款"],
        compound_keywords=[
            ["国家工作人员", "贪污"], ["利用职务便利", "侵吞"],
            ["贪污", "公款"], ["骗取", "公共财物"],
        ],
        exclude_keywords=["正常公务支出"],
        legal_basis="刑法第382条",
        sentencing_min="三年以下有期徒刑或拘役",
        sentencing_max="死刑",
        sentencing_note="数额较大≥3万 / 数额巨大≥20万 / 数额特别巨大≥300万（2016解释）",
    ),

    CrimePattern(
        name="挪用公款罪",
        aliases=["挪用公款"],
        category="职务类",
        keywords=["挪用公款", "挪用救灾款", "挪用特定款物"],
        compound_keywords=[
            ["国家工作人员", "挪用公款"], ["挪用", "公款归个人使用"],
            ["挪用", "特定款物"],
        ],
        exclude_keywords=["正常拨付", "合法使用"],
        legal_basis="刑法第384条",
        sentencing_min="五年以下有期徒刑",
        sentencing_max="无期徒刑",
        sentencing_note="挪用公款≥5万(超3月) / ≥100万(营利) / ≥200万(非法)",
    ),

    # ── 人身类 ────────────────────────────────────────────────────────────────

    CrimePattern(
        name="故意伤害罪",
        aliases=["殴打", "伤害"],
        category="人身类",
        keywords=["故意伤害", "殴打致伤", "打伤", "伤害他人", "殴打", "暴力伤害", "持刀伤人", "拳打脚踢"],
        compound_keywords=[
            ["故意", "伤害"], ["殴打", "致伤"], ["暴力", "伤害"],
            ["持刀", "伤人"], ["造成", "轻伤"],
        ],
        exclude_keywords=["正当防卫", "紧急避险"],
        legal_basis="刑法第234条",
        sentencing_min="三年以下有期徒刑或拘役",
        sentencing_max="死刑",
        sentencing_note="轻伤即可入罪 / 重伤 / 致人死亡或特别残忍手段致重伤",
    ),

    CrimePattern(
        name="寻衅滋事罪",
        aliases=["无事生非", "随意殴打"],
        category="人身类",
        keywords=["寻衅滋事", "随意殴打", "无事生非", "流氓行为", "聚众闹事", "任意毁损", "强拿硬要"],
        compound_keywords=[
            ["随意", "殴打他人"], ["无事生非", "起哄闹事"], ["强拿硬要", "公私财物"],
            ["任意", "损毁", "财物"],
        ],
        exclude_keywords=["正常纠纷", "邻里矛盾"],
        legal_basis="刑法第293条",
        sentencing_min="五年以下有期徒刑、拘役或管制",
        sentencing_max="十年有期徒刑",
        sentencing_note="多次实施 / 纠集他人 / 严重破坏社会秩序",
    ),

    # ── 毒品类 ────────────────────────────────────────────────────────────────

    CrimePattern(
        name="贩卖毒品罪",
        aliases=["贩毒", "出售毒品", "运输毒品"],
        category="毒品类",
        keywords=["贩卖毒品", "贩毒", "出售毒品", "运输毒品", "走私毒品", "制造毒品", "持有毒品"],
        compound_keywords=[
            ["贩卖", "毒品"], ["出售", "海洛因"], ["运输", "冰毒"],
            ["走私", "毒品"], ["制造", "冰毒"],
        ],
        exclude_keywords=["治病", "合法持有"],
        legal_basis="刑法第347条",
        sentencing_min="三年以下有期徒刑",
        sentencing_max="死刑",
        sentencing_note="海洛因/冰毒≥10g入罪 / ≥50g情节严重 / ≥200g可判死刑",
    ),

    CrimePattern(
        name="非法持有毒品罪",
        aliases=["持有毒品", "藏毒"],
        category="毒品类",
        keywords=["持有毒品", "非法持有", "藏毒", "随身携带毒品", "存放毒品"],
        compound_keywords=[
            ["非法持有", "毒品"], ["持有", "海洛因"], ["存放", "冰毒"],
        ],
        exclude_keywords=["贩卖", "运输", "制造"],
        legal_basis="刑法第348条",
        sentencing_min="三年以下有期徒刑",
        sentencing_max="无期徒刑",
        sentencing_note="海洛因/冰毒≥10g入罪 / ≥50g情节严重（2015纪要）",
    ),

    # ── 环境类 ────────────────────────────────────────────────────────────────

    CrimePattern(
        name="污染环境罪",
        aliases=["环境污染", "非法排放", "倾倒废物"],
        category="环境类",
        keywords=["污染环境", "非法排放", "倾倒废物", "超标排放", "非法处置", "环境污染罪"],
        compound_keywords=[
            ["违反规定", "排放"], ["非法倾倒", "废物"], ["超标排放", "污染物"],
            ["非法处置", "危险废物"],
        ],
        exclude_keywords=["正常生产", "达标排放"],
        legal_basis="刑法第338条",
        sentencing_min="三年以下有期徒刑或拘役",
        sentencing_max="七年以上有期徒刑",
        sentencing_note="严重污染环境入罪 / 后果特别严重（2023修正）",
    ),

    # ── 交通类 ────────────────────────────────────────────────────────────────

    CrimePattern(
        name="危险驾驶罪",
        aliases=["醉驾", "酒驾", "追逐竞驶"],
        category="交通类",
        keywords=["危险驾驶", "醉驾", "酒驾", "追逐竞驶", "醉被告人", "飙车", "醉驶", "醉酒驾驶"],
        compound_keywords=[
            ["醉酒驾驶", "机动车"], ["追逐竞驶", "情节恶劣"],
            ["血液酒精", "80mg"], ["醉酒", "驾驶"],
        ],
        exclude_keywords=[],
        legal_basis="刑法第133条之一",
        sentencing_min="拘役",
        sentencing_max="拘役六个月",
        sentencing_note="行为犯，醉驾入罪（血液酒精≥80mg/100ml），追逐竞驶情节恶劣入罪",
    ),

    CrimePattern(
        name="交通肇事罪",
        aliases=["交通事故", "肇事逃逸"],
        category="交通类",
        keywords=["交通肇事", "肇事逃逸", "交通事故", "撞人", "撞车", "驾车致人死亡", "超速驾驶"],
        compound_keywords=[
            ["交通肇事", "致人死亡"], ["驾车", "致人重伤"], ["肇事后", "逃逸"],
            ["交通事", "故逃逸"],
        ],
        exclude_keywords=["正当防卫", "紧急避险"],
        legal_basis="刑法第133条",
        sentencing_min="三年以下有期徒刑或拘役",
        sentencing_max="七年以上有期徒刑",
        sentencing_note="死亡1人+主责+逃逸→3-7年；死亡2人或重伤5人+逃逸→3-7年",
    ),

    # ── 其他类 ────────────────────────────────────────────────────────────────

    CrimePattern(
        name="开设赌场罪",
        aliases=["开设赌场", "聚众赌博"],
        category="其他类",
        keywords=["开设赌场", "聚众赌博", "网络赌博", "赌场", "赌博", "抽头渔利", "赌资"],
        compound_keywords=[
            ["开设赌场"], ["提供赌场"], ["聚众赌博", "抽头渔利"],
            ["组织", "网络赌博"],
        ],
        exclude_keywords=["娱乐", "正常娱乐"],
        legal_basis="刑法第303条",
        sentencing_min="五年以下有期徒刑、拘役或管制",
        sentencing_max="十年有期徒刑",
        sentencing_note="抽头渔利≥5000 / 赌资≥5万 / 参赌≥20人 / 赌具≥10台入罪",
    ),

    CrimePattern(
        name="拒不支付劳动报酬罪",
        aliases=["拖欠工资", "欠薪", "拒不支付报酬"],
        category="其他类",
        keywords=["拖欠工资", "拒不支付", "欠薪", "不支付劳动报酬", "老板跑路", "拒付工资"],
        compound_keywords=[
            ["拒不支付", "劳动报酬"], ["以转移财产", "逃匿"], ["拖欠", "员工工资"],
            ["拒不支付", "报酬"],
        ],
        exclude_keywords=["正常经营", "资金困难"],
        legal_basis="刑法第276条之一",
        sentencing_min="三年以下有期徒刑或拘役",
        sentencing_max="七年以上有期徒刑",
        sentencing_note="政府责令支付仍不支付，数额较大≥5000-10000元/人（各省标准）",
    ),

    CrimePattern(
        name="非法侵入住宅罪",
        aliases=["非法侵入", "私闯民宅", "侵入住宅"],
        category="其他类",
        keywords=["非法侵入", "私闯", "擅自进入", "破门而入", "非法侵入住宅", "闯入民宅"],
        compound_keywords=[
            ["非法侵入", "他人住宅"], ["私自", "闯入"], ["非法", "侵入"],
        ],
        exclude_keywords=["合法执行", "正当理由"],
        legal_basis="刑法第245条",
        sentencing_min="三年以下有期徒刑或拘役",
        sentencing_max="三年有期徒刑",
        sentencing_note="行为犯，非法侵入他人住宅即构成犯罪",
    ),
]


# =============================================================================
# 推理引擎核心
# =============================================================================

@dataclass
class ChargeRecommendation:
    """罪名推荐结果"""
    rank: int
    name: str
    category: str               # 分类
    confidence: str        # 高/中/低
    score: int
    matched_keywords: List[str]
    compound_matched: List[str]
    legal_basis: str
    sentencing_range: str
    sentencing_note: str
    reasoning: str


class CaseReasoningEngine:
    """案由推理引擎"""

    def __init__(self):
        self.patterns = CRIME_PATTERNS

    def reason(self, description: str, top_k: int = 5) -> Dict[str, Any]:
        """
        根据案情描述推理可能罪名

        Args:
            description: 案情描述文本
            top_k: 返回前几名推荐

        Returns:
            {
                "input_summary": "...",
                "recommendations": [ChargeRecommendation, ...],
                "categories": ["财产类", ...],
            }
        """
        if not description or len(description.strip()) < 5:
            return {
                "input_summary": description,
                "recommendations": [],
                "categories": [],
                "error": "案情描述过短，无法进行有效推理",
            }

        # 对每个罪名模式进行匹配
        results: List[Dict] = []
        for pattern in self.patterns:
            match_result = pattern.match(description)
            if match_result["matched"]:
                rec = ChargeRecommendation(
                    rank=0,
                    name=pattern.name,
                    category=pattern.category,
                    confidence=match_result["confidence"],
                    score=match_result["total_score"],
                    matched_keywords=match_result["keyword_matched"],
                    compound_matched=match_result["compound_matched"],
                    legal_basis=pattern.legal_basis,
                    sentencing_range=f"{pattern.sentencing_min} ~ {pattern.sentencing_max}",
                    sentencing_note=pattern.sentencing_note,
                    reasoning=self._build_reasoning(pattern, match_result),
                )
                results.append(rec)

        # 按置信度和分数排序
        confidence_order = {"高": 3, "中": 2, "低": 1}
        results.sort(key=lambda x: (confidence_order.get(x.confidence, 0), x.score), reverse=True)

        # 分配排名
        for i, r in enumerate(results):
            r.rank = i + 1

        # 限制返回数量
        top_results = results[:top_k]

        # 提取涉及类别
        categories = list(dict.fromkeys(r.category for r in top_results))

        return {
            "input_summary": description[:100] + "..." if len(description) > 100 else description,
            "input_length": len(description),
            "pattern_count": len(self.patterns),
            "matched_count": len(results),
            "recommendations": [
                {
                    "rank": r.rank,
                    "name": r.name,
                    "confidence": r.confidence,
                    "score": r.score,
                    "matched_keywords": r.matched_keywords,
                    "compound_keywords_matched": r.compound_matched,
                    "legal_basis": r.legal_basis,
                    "sentencing_range": r.sentencing_range,
                    "sentencing_note": r.sentencing_note,
                    "reasoning": r.reasoning,
                }
                for r in top_results
            ],
            "categories": categories,
        }

    def _build_reasoning(self, pattern: CrimePattern, match_result: Dict) -> str:
        parts = []
        if match_result["compound_matched"]:
            parts.append(f"复合关键词匹配：{' + '.join(match_result['compound_matched'])}")
        if match_result["keyword_matched"]:
            kw_list = match_result["keyword_matched"][:5]
            parts.append(f"触发关键词：{', '.join(kw_list)}")
        if match_result["exclude_matched"]:
            parts.append(f"⚠️ 存在排除词：{', '.join(match_result['exclude_matched'])}，置信度已降低")
        parts.append(f"法条依据：{pattern.legal_basis}")
        parts.append(f"量刑区间：{pattern.sentencing_min} ~ {pattern.sentencing_max}")
        return "；".join(parts)

    def get_all_crimes(self) -> Dict[str, Any]:
        """获取所有支持的罪名列表"""
        by_category: Dict[str, List[str]] = {}
        for p in self.patterns:
            if p.category not in by_category:
                by_category[p.category] = []
            by_category[p.category].append(p.name)

        return {
            "total_count": len(self.patterns),
            "by_category": by_category,
            "all_names": [p.name for p in self.patterns],
        }
