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

import logging
logger = logging.getLogger(__name__)

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


CRIME_SPECIFIC_TEMPLATES = {
    # ── 财产类 ──────────────────────────────────────────────────────
    "盗窃罪": {
        "alias": "盗窃",
        "category": "财产类",
        "argument_focus": "秘密窃取 vs 公开取得、主从犯区分、犯罪未遂",
        "legal_defense": "犯罪未遂（未控制财物即被抓获）/ 部分退赃 / 初犯偶犯 / 赔偿谅解",
        "key_articles": ["《刑法》第264条", "最高法《关于办理盗窃刑事案件适用法律若干问题的解释》"],
        "sentencing_defense": [
            "犯罪金额认定异议：现有证据无法充分证明涉案金额",
            "被告人系从犯：在共同犯罪中起次要作用，应从轻或减轻处罚",
            "属犯罪未遂：尚未实际控制涉案财物即被抓获",
            "主观恶性较小：系初犯、偶犯，无前科劣迹",
            "积极退赃退赔：已全额/部分退赃，弥补被害人损失",
        ],
        "key_evidence": ["监控录像", "失窃现场勘验", "指纹/DNA鉴定", "银行转账记录"],
        "mitigation_factors": ["初犯", "偶犯", "自首", "坦白", "全部退赃", "取得谅解"],
        "aggravating_factors": ["入户盗窃", "扒窃", "惯犯", "，流窜作案"],
    },

    "诈骗罪": {
        "alias": "诈骗",
        "category": "财产类",
        "argument_focus": "非法占有目的认定、欺诈行为与民事纠纷的区分",
        "legal_defense": "民事欺诈≠刑事诈骗 / 存在真实交易背景 / 经营失败非主观故意",
        "key_articles": ["《刑法》第266条", "最高法《关于审理诈骗刑事案件具体应用法律若干问题的解释》"],
        "sentencing_defense": [
            "定性异议：被告人行为属于民事欺诈范畴，不构成刑事诈骗罪",
            "非法占有目的认定事实不清：涉案款项用于正常经营，未转移隐匿",
            "存在真实交易背景：双方曾有合作关系，纠纷源于商业争议",
            "积极退赃：被告人已退还全部/部分涉案款项",
            "认罪认罚：被告人自愿认罪认罚，态度诚恳",
        ],
        "key_evidence": ["合同文本", "银行流水", "证人证言", "被告人供述与辩解"],
        "mitigation_factors": ["全部退赃", "取得谅解", "自首", "坦白", "认罪认罚"],
        "aggravating_factors": ["诈骗老年人", "诈骗残疾人", "诈骗救灾款物", "冒充国家工作人员"],
    },

    "抢夺罪": {
        "alias": "抢夺",
        "category": "财产类",
        "argument_focus": "趁人不备 vs 有预谋、暴力程度、主从犯",
        "legal_defense": "未使用暴力 / 临时起意 / 犯罪未遂 / 分赃较少",
        "key_articles": ["《刑法》第267条", "最高法《关于抢夺罪具体应用法律若干问题的解释》"],
        "sentencing_defense": [
            "定性异议：被告人的行为更符合盗窃罪特征，非趁人不备抢夺",
            "暴力程度较低：未对被害人造成人身伤害，仅涉及财产",
            "属犯罪未遂：被当场抓获，未实际取得财物",
            "从犯：在共同犯罪中负责望风，分赃较少",
            "初犯偶犯：此前无任何违法犯罪记录",
        ],
        "key_evidence": ["被害人陈述", "监控视频", "伤情鉴定", "现场目击证人"],
        "mitigation_factors": ["初犯", "自首", "坦白", "退赃", "取得谅解"],
        "aggravating_factors": ["驾驶机动车抢夺", "抢夺老年人/未成年人", "多次抢夺", "造成伤害"],
    },

    "职务侵占罪": {
        "alias": "职务侵占",
        "category": "财产类",
        "argument_focus": "利用职务便利认定、单位知情、内部纠纷",
        "legal_defense": "公司内部民事争议 / 未利用职务便利 / 主观上无非法占有目的",
        "key_articles": ["《刑法》第271条", "最高检公安部《关于公安机关管辖的刑事案件立案追诉标准（二）》"],
        "sentencing_defense": [
            "定性异议：被告人与公司之间存在劳动争议和报酬纠纷，属于民事法律关系",
            "未利用职务便利：被告人支取款项经过了公司内部审批程序",
            "主观上无非法占有目的：涉案款项用于公司业务支出，有账目记录",
            "已返还部分款项：被告人愿意与公司进行结算",
            "公司存在过错：公司未及时足额支付劳动报酬在先",
        ],
        "key_evidence": ["劳动合同", "工资台账", "公司财务凭证", "证人证言"],
        "mitigation_factors": ["初犯", "认罪悔罪", "部分退赔", "公司谅解"],
        "aggravating_factors": ["挪用后拒不归还", "伪造财务凭证", "多次侵占"],
    },

    "敲诈勒索罪": {
        "alias": "敲诈勒索",
        "category": "财产类",
        "argument_focus": "正当权利 vs 非法占有、恐吓程度、被害人过错",
        "legal_defense": "存在真实债务纠纷 / 维权行为 / 恐吓程度轻微 / 犯罪未遂",
        "key_articles": ["《刑法》第274条", "最高法《关于敲诈勒索罪具体应用法律若干问题的解释》"],
        "sentencing_defense": [
            "定性异议：被告人系主张合法债权，不具有非法占有目的",
            "存在真实债权债务关系：被告人与被害人之间存在经济纠纷",
            "恐吓程度轻微：被告人未使用严重暴力或威胁手段",
            "被害人存在过错：被害人在先行为引发本案",
            "未遂：被害人未实际交付财物即案发",
        ],
        "key_evidence": ["借条/债务凭证", "通信记录", "证人证言", "被害人陈述"],
        "mitigation_factors": ["初犯", "自首", "坦白", "未遂", "退赃"],
        "aggravating_factors": ["冒充黑恶势力", "多次敲诈", "针对弱势群体"],
    },

    # ── 职务类 ──────────────────────────────────────────────────────
    "受贿罪": {
        "alias": "受贿",
        "category": "职务类",
        "argument_focus": "受贿金额认定、自首立功、追诉时效、赃款用途",
        "legal_defense": "自首立功 / 受贿金额扣除合法报酬 / 被索贿 / 退赃彻底",
        "key_articles": [
            "《刑法》第385条", "第388条",
            "最高法最高检《关于办理贪污贿赂刑事案件适用法律若干问题的解释》(2016)",
        ],
        "sentencing_defense": [
            "自首：被告人主动投案并如实供述犯罪事实，构成自首",
            "立功：被告人揭发他人犯罪行为并经查证属实，构成重大立功",
            "受贿金额认定异议：部分款项系被告人合法劳动报酬，应当扣除",
            "被索贿：被告人在被对方要挟的情况下被迫收受财物，应从轻处罚",
            "全部退赃：被告人已退还全部违法所得",
        ],
        "key_evidence": ["银行转账记录", "证人证言", "行受贿双方的供述", "通话记录"],
        "mitigation_factors": ["自首", "立功", "重大立功", "坦白", "全部退赃", "被索贿"],
        "aggravating_factors": ["受贿多人为他人谋利", "索贿", "为请托人谋取不正当利益", "多次受贿"],
    },

    "行贿罪": {
        "alias": "行贿",
        "category": "职务类",
        "argument_focus": "被索贿认定、不正当利益认定、自首立功",
        "legal_defense": "被索贿 / 为获取合法利益 / 自首 / 配合调查",
        "key_articles": ["《刑法》第389条", "第390条", "2016解释第7条"],
        "sentencing_defense": [
            "被索贿：被告人系在被对方明示或暗示要挟的情况下被迫行贿，应从轻或减轻处罚",
            "为谋取正当利益：被告人所追求的利益属于合法商业利益，不属于不正当利益",
            "自首：被告人主动投案并如实供述，构成自首",
            "认罪认罚：被告人自愿如实供述犯罪事实，认罪态度良好",
            "配合调查：被告人积极协助侦查机关查清案件事实",
        ],
        "key_evidence": ["银行转账记录", "证人证言", "通信记录", "项目审批文件"],
        "mitigation_factors": ["自首", "被索贿", "坦白", "认罪认罚", "配合调查", "追诉时效"],
        "aggravating_factors": ["行贿多人", "谋取不正当利益", "情节严重"],
    },

    "贪污罪": {
        "alias": "贪污",
        "category": "职务类",
        "argument_focus": "主体身份认定、贪污数额、自首立功",
        "legal_defense": "非国家工作人员 / 贪污金额扣除合法收入 / 自首立功 / 退赃",
        "key_articles": ["《刑法》第382条", "第383条", "2016解释"],
        "sentencing_defense": [
            "主体身份异议：被告人并非国家工作人员，不符合贪污罪主体要件",
            "贪污金额异议：部分款项系被告人合法绩效工资，应当扣除",
            "自首：被告人主动投案并如实供述，构成自首",
            "全部退赃：已退还全部涉案款项",
        ],
        "key_evidence": ["财务凭证", "账目记录", "银行流水", "证人证言"],
        "mitigation_factors": ["自首", "立功", "坦白", "全部退赃", "初犯"],
        "aggravating_factors": ["多次贪污", "贪污特定款物", "拒不交代赃款去向"],
    },

    # ── 经济类 ──────────────────────────────────────────────────────
    "非法经营罪": {
        "alias": "非法经营",
        "category": "经济类",
        "argument_focus": "是否违反国家规定、经营行为认定、情节严重程度",
        "legal_defense": "未经许可经营≠非法经营 / 情节轻微 / 单位犯罪从轻",
        "key_articles": ["《刑法》第225条", "最高法《关于审理非法经营罪刑事案件具体应用法律若干问题的解释》"],
        "sentencing_defense": [
            "定性异议：被告人行为不属于'经营'行为，或未经许可不等于非法经营",
            "违反国家规定异议：涉案行为未违反国家规定，不符合非法经营罪构成要件",
            "情节较轻：被告人经营时间较短，违法所得较少，社会危害性较小",
            "单位犯罪：涉案行为系公司行为，应对单位判处罚金，对直接责任人从轻处罚",
            "认罪认罚：被告人自愿认罪认罚",
        ],
        "key_evidence": ["经营账目", "银行流水", "证人证言", "行政许可证件"],
        "mitigation_factors": ["初犯", "单位犯罪", "认罪认罚", "部分退赃"],
        "aggravating_factors": ["曾被行政处罚", "造成严重后果", "规模较大"],
    },

    "虚开增值税专用发票罪": {
        "alias": "虚开发票",
        "category": "经济类",
        "argument_focus": "虚开目的、是否造成国家税款损失、单位行为",
        "legal_defense": "无骗税目的 / 未造成税款损失 / 不知是虚开 / 单位从轻",
        "key_articles": [
            "《刑法》第205条之一",
            "最高法《关于虚开增值税专用发票刑事案件定罪量刑标准的规定》",
        ],
        "sentencing_defense": [
            "主观故意异议：被告人对虚开行为不知情，主观上不具有骗税或虚开的故意",
            "未造成税款损失：受票方已按规定抵扣，但实际已缴纳税款，未造成国家税款损失",
            "有真实交易背景：被告人系基于真实货物交易而让他人代开发票",
            "单位犯罪：涉案行为系公司决策，应认定为单位犯罪",
            "从犯：被告人在共同犯罪中起次要作用",
        ],
        "key_evidence": ["发票原件", "纳税记录", "购销合同", "银行流水"],
        "mitigation_factors": ["从犯", "单位犯罪", "未造成税款损失", "坦白", "认罪认罚"],
        "aggravating_factors": ["有骗税目的", "造成税款损失", "多次虚开"],
    },

    # ── 人身类 ──────────────────────────────────────────────────────
    "故意伤害罪": {
        "alias": "故意伤害",
        "category": "人身类",
        "argument_focus": "伤情鉴定结论、正当防卫、被害人过错、邻里纠纷",
        "legal_defense": "正当防卫 / 防卫过当 / 被害人过错 / 激情犯罪 / 赔偿谅解",
        "key_articles": ["《刑法》第234条", "最高法《人体损伤程度鉴定标准》"],
        "sentencing_defense": [
            "正当防卫：被告人系为制止正在进行的不法侵害而采取的必要防卫行为",
            "防卫过当：被告人行为超过必要限度，但系因情况紧急，属于防卫过当",
            "被害人存在过错：被害人在先行为引发冲突，对损害结果负有过错",
            "邻里纠纷引发：双方因琐事发生口角，被告人系激情犯罪",
            "积极赔偿并取得谅解：被告人已赔偿被害人全部损失并取得书面谅解",
        ],
        "key_evidence": ["伤情鉴定意见", "监控视频", "证人证言", "被害人陈述"],
        "mitigation_factors": ["自首", "坦白", "赔偿谅解", "被害人过错", "防卫过当", "初犯"],
        "aggravating_factors": ["致人重伤或死亡", "使用凶器", "针对老弱病残"],
    },

    "寻衅滋事罪": {
        "alias": "寻衅滋事",
        "category": "人身类",
        "argument_focus": "情节是否严重、是否无事生非、邻里纠纷例外",
        "legal_defense": "事出有因 / 情节轻微 / 邻里纠纷 / 被害人谅解 / 犯罪未遂",
        "key_articles": ["《刑法》第293条", "最高法最高检《关于办理寻衅滋事刑事案件适用法律若干问题的解释》"],
        "sentencing_defense": [
            "定性异议：被告人行为不属于'随意'殴打他人，不符合寻衅滋事罪构成要件",
            "事出有因：被告人系因琐事与被害人发生争执，有一定起因",
            "情节较轻：殴打行为未造成严重后果，被告人及时停止",
            "邻里纠纷：双方系邻居关系，因日常矛盾引发冲突",
            "已取得被害人谅解：双方已达成和解协议",
        ],
        "key_evidence": ["监控视频", "证人证言", "伤情鉴定", "双方和解协议"],
        "mitigation_factors": ["自首", "坦白", "赔偿谅解", "初犯", "邻里纠纷"],
        "aggravating_factors": ["多次实施", "纠集他人", "造成公共场所秩序严重混乱"],
    },

    # ── 交通类 ──────────────────────────────────────────────────────
    "危险驾驶罪": {
        "alias": "醉驾",
        "category": "交通类",
        "argument_focus": "血液酒精含量检测程序、是否曾被处罚",
        "legal_defense": "酒精含量临界 / 检测程序违法 / 紧急情况 / 短距离挪车",
        "key_articles": ["《刑法》第133条之一", "最高法 最高检 公安部《关于办理醉酒驾驶机动车刑事案件适用法律若干问题的意见》"],
        "sentencing_defense": [
            "血液酒精含量认定异议：对检测机构的资质或检测程序提出合理质疑",
            "紧急情况：被告人系为将车辆移至安全位置（挪车），未实际驾驶上路",
            "行驶距离极短：被告人驾车距离极短，未造成任何实际危险",
            "认罪认罚：被告人自愿认罪认罚，态度诚恳",
            "初犯：被告人系初次实施此类行为，此前无任何违法犯罪记录",
        ],
        "key_evidence": ["血液酒精检测报告", "执法记录视频", "证人证言", "行驶轨迹"],
        "mitigation_factors": ["初犯", "认罪认罚", "未造成事故", "血液酒精含量较低", "挪车"],
        "aggravating_factors": ["血液酒精含量≥200mg/100ml", "造成事故", "无证驾驶", "曾因酒驾被处罚"],
    },

    "交通肇事罪": {
        "alias": "交通肇事",
        "category": "交通类",
        "argument_focus": "责任划分、逃逸认定、自首、赔偿谅解",
        "legal_defense": "次要责任 / 非因逃逸致人死亡 / 自首 / 积极赔偿",
        "key_articles": ["《刑法》第133条", "最高法《关于审理交通肇事刑事案件具体应用法律若干问题的解释》"],
        "sentencing_defense": [
            "责任划分异议：交警部门出具的责任认定书存在事实不清、法律依据不足的问题",
            "逃逸认定异议：被告人离开现场系因救助伤员，而非逃避法律追究",
            "自首：被告人主动投案并如实供述，构成自首",
            "积极赔偿：被告人已赔偿被害人/被害人家属全部损失",
            "取得谅解：被害人或其近亲属已出具书面谅解书",
        ],
        "key_evidence": ["交通事故认定书", "现场勘查笔录", "鉴定意见", "证人证言"],
        "mitigation_factors": ["自首", "全部赔偿", "取得谅解", "次要责任", "坦白"],
        "aggravating_factors": ["负主要或全部责任", "逃逸", "酒后驾驶", "无证驾驶", "造成死亡或重伤"],
    },

    # ── 毒品类 ──────────────────────────────────────────────────────
    "贩卖毒品罪": {
        "alias": "贩毒",
        "category": "毒品类",
        "argument_focus": "毒品数量、是否明知、特情介入、立功",
        "legal_defense": "特情引诱 / 不明知是毒品 / 毒品含量鉴定 / 犯罪未遂 / 立功",
        "key_articles": ["《刑法》第347条", "最高法《毒品犯罪座谈会纪要》(2015)"],
        "sentencing_defense": [
            "特情引诱：被告人系在公安机关特情人员引诱下实施犯罪，应当从轻处罚",
            "不明知：被告人不知道涉案物品是毒品，主观上不具有贩卖毒品的故意",
            "毒品含量异议：涉案毒品含量极低，应进行含量鉴定并据此量刑",
            "犯罪未遂：被告人尚未完成交易即被抓获",
            "重大立功：被告人揭发他人重大犯罪并经查证属实",
        ],
        "key_evidence": ["毒品鉴定意见", "通话记录", "转账记录", "证人证言"],
        "mitigation_factors": ["特情引诱", "犯罪未遂", "立功", "重大立功", "坦白", "初犯"],
        "aggravating_factors": ["毒品数量大", "向未成年人贩卖", "多次贩卖", "暴力抗拒检查"],
    },

    "非法持有毒品罪": {
        "alias": "持有毒品",
        "category": "毒品类",
        "argument_focus": "毒品数量、是否有贩卖目的",
        "legal_defense": "用于自己吸食 / 无贩卖目的 / 数量认定异议 / 毒品含量",
        "key_articles": ["《刑法》第348条"],
        "sentencing_defense": [
            "持有目的：被告人持有毒品系供自己吸食，无贩卖目的",
            "毒品数量异议：现有证据无法充分证明涉案毒品数量",
            "毒品含量较低：涉案毒品含量极低，应按纯度折算",
            "初犯：被告人系初次因毒品相关行为被查获",
        ],
        "key_evidence": ["毒品鉴定意见", "证人证言", "手机聊天记录", "被告人供述"],
        "mitigation_factors": ["初犯", "坦白", "无贩卖目的", "毒品数量接近入罪门槛"],
        "aggravating_factors": ["毒品数量大", "持有多种毒品", "曾因毒品被处罚"],
    },

    # ── 其他类 ──────────────────────────────────────────────────────
    "开设赌场罪": {
        "alias": "开设赌场",
        "category": "其他类",
        "argument_focus": "抽头渔利金额、参赌人数、是否以赌资为业",
        "legal_defense": "不知是赌场 / 规模较小 / 从犯 / 自首 / 参赌人员有限",
        "key_articles": ["《刑法》第303条", "最高法最高检《关于办理赌博刑事案件具体应用法律若干问题的解释》"],
        "sentencing_defense": [
            "定性异议：被告人仅为赌场提供场地或帮助，不明知是赌场",
            "规模较小：赌场经营时间较短，参赌人数有限，抽头渔利金额较小",
            "从犯：被告人在共同犯罪中起次要或辅助作用",
            "自首：被告人主动投案并如实供述，构成自首",
            "认罪认罚：被告人自愿认罪认罚",
        ],
        "key_evidence": ["赌资账目", "参赌人员证言", "监控视频", "银行流水"],
        "mitigation_factors": ["从犯", "自首", "坦白", "认罪认罚", "初犯"],
        "aggravating_factors": ["抽头渔利金额大", "参赌人数多", "组织未成年人参赌"],
    },

    "污染环境罪": {
        "alias": "污染环境",
        "category": "环境类",
        "argument_focus": "超标程度、是否造成实际损害、单位行为",
        "legal_defense": "排放未超标 / 意外事故 / 无主观故意 / 单位犯罪 / 已整改",
        "key_articles": ["《刑法》第338条", "两高《关于办理环境污染刑事案件适用法律若干问题的解释》"],
        "sentencing_defense": [
            "排放标准异议：被告人所在企业排放的污染物未超过国家或地方污染物排放标准",
            "因果关系异议：现有证据无法证明被害人损害与被告人的排污行为之间存在因果关系",
            "意外事故：被告人系因设备故障等意外原因导致超标排放，不具有主观故意",
            "单位犯罪：涉案行为系公司行为，应认定为单位犯罪",
            "积极整改：案发后被告人所在企业已投入资金进行设备升级和整改",
        ],
        "key_evidence": ["环境监测报告", "排污许可证", "设备运行记录", "证人证言"],
        "mitigation_factors": ["单位犯罪", "意外事故", "积极整改", "初犯", "坦白"],
        "aggravating_factors": ["超标倍数高", "造成严重后果", "多次超标排放", "隐瞒排污数据"],
    },
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

        # ── 罪名专业化辩护章节（新增）────────────────────────────────
        crime_specific = self._get_crime_template(crime)
        if crime_specific:
            sections.append(self._generate_crime_specific_section(crime, crime_specific))

        # 根据辩护类型生成相应章节
        primary_defense = self.defense_analysis.get("primary_defense") or {}
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
        primary = self.defense_analysis.get("primary_defense") or {}
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
            title="三、关于无罪辩护意见",
            content=content,
            importance=5,
        )
    
    def _generate_legal_basis_section(self) -> DefenseOpinionSection:
        """生成法律依据章节"""
        primary = self.defense_analysis.get("primary_defense") or {}
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
            title="四、法律依据与分析",
            content=content,
            importance=4,
        )
    
    # ── 罪名专业化辩护方法（新增）────────────────────────────────────

    def _get_crime_template(self, crime: str) -> Optional[Dict]:
        """根据罪名获取专业化模板，找别名匹配"""
        if crime in CRIME_SPECIFIC_TEMPLATES:
            return CRIME_SPECIFIC_TEMPLATES[crime]
        # 通过别名匹配
        for template in CRIME_SPECIFIC_TEMPLATES.values():
            if template.get("alias") == crime or crime in template.get("alias", ""):
                return template
        return None

    def _generate_crime_specific_section(self, crime: str, tmpl: Dict) -> DefenseOpinionSection:
        """生成罪名专业化辩护章节"""
        category = tmpl.get("category", "")
        argument_focus = tmpl.get("argument_focus", "")
        legal_defense = tmpl.get("legal_defense", "")
        defense_items = tmpl.get("sentencing_defense", [])
        key_articles = tmpl.get("key_articles", [])
        mitigating = tmpl.get("mitigation_factors", [])
        aggravating = tmpl.get("aggravating_factors", [])

        defense_text = "\n".join(f"（{chr(65+i)}）{item}" for i, item in enumerate(defense_items))
        articles_text = "、".join(key_articles) if key_articles else "相关法律规定"
        mitigation_text = "、".join(mitigating) if mitigating else "无"
        aggravating_text = "、".join(aggravating) if aggravating else "无"

        primary = self.defense_analysis.get("primary_defense") or {}
        defense_type = primary.get("type", "")

        content = f"""辩护人经研究本案案情，认为本案应当围绕以下专业辩护要点展开：

一、本案辩护要点分析

本案属于【{category}·{crime}】案件，辩护重点应围绕以下方面展开：

（一）本案辩护方向

{argument_focus}

（二）核心辩护策略

{legal_defense}

（三）具体辩护意见

{defense_text}

二、法律依据

本案主要涉及以下法律条文和司法解释：
{articles_text}

三、关于量刑情节

（一）从轻/减轻处罚情节
以下情节请法庭在量刑时予以充分考虑：
{mitigation_text}

（二）从重处罚情节（请法庭注意不存在以下情节）
{aggravating_text}

四、辩护结论

基于上述分析，辩护人认为：{legal_defense.split('/')[0] if '/' in legal_defense else legal_defense}。

恳请法庭在查明案件事实的基础上，依法对被告人作出公正判决。"""

        return DefenseOpinionSection(
            title=f"二、关于{crime}的专业化辩护意见",
            content=content,
            importance=5,
        )

    # ── 以下为原有方法 ───────────────────────────────────────────

    def _generate_evidence_challenge_section(self) -> DefenseOpinionSection:
        """生成证据质疑章节"""
        primary = self.defense_analysis.get("primary_defense") or {}
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
            title="三、关于证据不足的辩护意见",
            content=content,
            importance=5,
        )
    
    def _generate_sentencing_section(self) -> DefenseOpinionSection:
        """生成量刑辩护章节"""
        primary = self.defense_analysis.get("primary_defense") or {}
        secondary = self.defense_analysis.get("secondary_defenses") or []
        
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
            title="三、关于量刑的辩护意见",
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
            title="四、类案参考",
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
            title="五、量刑建议",
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
        primary = self.defense_analysis.get("primary_defense") or {}
        primary_type = primary.get("type", "")
        secondary = self.defense_analysis.get("secondary_defenses") or []
        
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
        secondary = self.defense_analysis.get("secondary_defenses") or []
        
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
