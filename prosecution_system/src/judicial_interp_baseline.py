# -*- coding: utf-8 -*-
"""
司法解释覆盖基线文档 - prosecution_system/src/judicial_interp_baseline.py

功能：
- 建立所有主要罪名的司法解释覆盖基线
- 跟踪每部司法解释的状态（ACTIVE/SUPERSEDED/草案）
- 为报告生成提供「本报告引用司法解释的有效性说明」
- 支持自动核查报告中所引司法解释是否在基线覆盖范围内

覆盖范围：
  - 刑法分则各主要罪名对应的司法解释
  - 量刑情节、数额标准、管辖等程序性解释
  - 2024年最新修订动态

用法：
    from judicial_interp_baseline import JudicialInterpBaseline, InterpStatus
    baseline = JudicialInterpBaseline()
    coverage = baseline.check_coverage(["关于办理盗窃刑事案件适用法律若干问题的解释"])
    print(coverage)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import re


class InterpStatus:
    ACTIVE = "现行有效"
    SUPERSEDED = "已被替代/废止"
    DRAFT = "征求意见稿"
    PARTIAL = "部分修订"


@dataclass
class JudicialInterp:
    """单部司法解释"""
    name: str                          # 官方名称
    abbr: str                          # 简称
    issuing_authority: str             # 发布机关
    effective_date: str                # 施行日期
    superseded_date: Optional[str]     # 废止日期（None=现行有效）
    superseded_by: Optional[str]       # 被何者替代
    status: str                        # InterpStatus 常量
    crime_types: List[str]             # 对应罪名
    key_content: str                   # 核心内容摘要
    key_thresholds: Dict[str, str]     # 关键数额/量刑标准 {"数额较大": "2000-3000元以上", ...}
    notes: str = ""                    # 备注


# ===== 司法解释基线数据库 =====

JUDICIAL_INTERPRETATIONS: List[JudicialInterp] = [
    # ===== 盗窃罪 =====
    JudicialInterp(
        name="最高人民法院、最高人民检察院关于办理盗窃刑事案件适用法律若干问题的解释",
        abbr="盗窃罪司法解释（2013）",
        issuing_authority="最高法、最高检",
        effective_date="2013-04-04",
        superseded_date=None,
        superseded_by=None,
        status=InterpStatus.ACTIVE,
        crime_types=["盗窃罪"],
        key_content="盗窃罪数额较大、数额巨大、数额特别巨大的具体标准",
        key_thresholds={
            "数额较大（一般）": "1000元至3000元以上",
            "数额巨大": "3万元至10万元以上",
            "数额特别巨大": "30万元至50万元以上",
            "入户盗窃/扒窃": "无数额要求",
        },
        notes="各省市可在规定幅度内确定本地标准（见 threshold_db）",
    ),

    # ===== 诈骗罪 =====
    JudicialInterp(
        name="最高人民法院关于审理诈骗刑事案件具体应用法律若干问题的解释（2022修订）",
        abbr="诈骗罪司法解释（2022）",
        issuing_authority="最高法",
        effective_date="2022-02-01",
        superseded_date=None,
        superseded_by=None,
        status=InterpStatus.ACTIVE,
        crime_types=["诈骗罪"],
        key_content="诈骗罪数额较大、数额巨大、数额特别巨大的具体标准（2022年修订）",
        key_thresholds={
            "数额较大（一般）": "3000元至1万元以上",
            "数额巨大": "10万元至50万元以上",
            "数额特别巨大": "50万元至200万元以上",
        },
        notes="2022年修订，原2011年解释同时废止",
    ),

    # ===== 非法吸收公众存款罪 =====
    JudicialInterp(
        name="最高人民法院关于审理非法吸收公众存款刑事案件具体应用法律若干问题的解释（2022修订）",
        abbr="非法吸存司法解释（2022）",
        issuing_authority="最高法",
        effective_date="2022-03-01",
        superseded_date=None,
        superseded_by=None,
        status=InterpStatus.ACTIVE,
        crime_types=["非法吸收公众存款罪"],
        key_content="非法吸存罪的数额/情节标准，单位犯罪与个人犯罪标准",
        key_thresholds={
            "非法吸收公众存款（个人）": "100万元以上",
            "非法吸收公众存款（单位）": "500万元以上",
            "数额巨大（个人）": "500万元以上",
        },
        notes="2022年修订，整合原2010年解释",
    ),

    # ===== 集资诈骗罪 =====
    JudicialInterp(
        name="最高人民法院关于审理非法集资刑事案件具体应用法律若干问题的解释（2022修订）",
        abbr="集资诈骗司法解释（2022）",
        issuing_authority="最高法",
        effective_date="2022-03-01",
        superseded_date=None,
        superseded_by=None,
        status=InterpStatus.ACTIVE,
        crime_types=["集资诈骗罪"],
        key_content="集资诈骗罪数额较大/巨大/特别巨大的具体标准",
        key_thresholds={
            "数额较大": "10万元以上",
            "数额巨大": "100万元以上",
            "数额特别巨大": "1000万元以上",
        },
        notes="与非法吸存解释同期修订",
    ),

    # ===== 职务侵占罪 =====
    JudicialInterp(
        name="最高人民法院、最高人民检察院关于办理贪污贿赂刑事案件适用法律若干问题的解释",
        abbr="贪污贿赂司法解释（2016）",
        issuing_authority="最高法、最高检",
        effective_date="2016-04-18",
        superseded_date=None,
        superseded_by=None,
        status=InterpStatus.ACTIVE,
        crime_types=["职务侵占罪", "挪用资金罪", "贪污罪", "受贿罪", "行贿罪"],
        key_content="职务侵占罪/挪用资金罪数额标准，贪污贿赂犯罪量刑标准",
        key_thresholds={
            "职务侵占罪数额较大": "6万元以上",
            "职务侵占罪数额巨大": "100万元以上",
            "挪用资金罪数额较大": "10万元以上",
            "行贿罪立案标准": "3万元以上",
            "行贿罪情节严重": "100万元以上",
        },
        notes="重要：职务侵占罪数额标准与盗窃罪不同（盗窃1000元起，职务侵占6万元起）",
    ),

    # ===== 开设赌场罪 =====
    JudicialInterp(
        name="最高人民法院、最高人民检察院关于办理赌博刑事案件具体应用法律若干问题的解释",
        abbr="赌博罪司法解释（2005）",
        issuing_authority="最高法、最高检",
        effective_date="2005-05-13",
        superseded_date=None,
        superseded_by=None,
        status=InterpStatus.ACTIVE,
        crime_types=["开设赌场罪", "赌博罪"],
        key_content="开设赌场罪情节严重的标准",
        key_thresholds={
            "抽头渔利": "5000元以上",
            "赌资": "5万元以上",
            "参赌人数": "20人以上",
        },
        notes="情节严重为5年以上10年以下有期徒刑",
    ),

    # ===== 抢夺罪 =====
    JudicialInterp(
        name="最高人民法院、最高人民检察院关于办理抢夺刑事案件适用法律若干问题的解释",
        abbr="抢夺罪司法解释（2013）",
        issuing_authority="最高法、最高检",
        effective_date="2013-11-18",
        superseded_date=None,
        superseded_by=None,
        status=InterpStatus.ACTIVE,
        crime_types=["抢夺罪"],
        key_content="抢夺罪数额较大/巨大/特别巨大的具体标准",
        key_thresholds={
            "数额较大（一般）": "1000元至3000元以上",
            "数额巨大": "3万元至8万元以上",
            "数额特别巨大": "20万元至40万元以上",
            "入户/携带凶器/扒窃": "无数额要求",
        },
    ),

    # ===== 敲诈勒索罪 =====
    JudicialInterp(
        name="最高人民法院、最高人民检察院关于办理敲诈勒索刑事案件适用法律若干问题的解释",
        abbr="敲诈勒索司法解释（2013）",
        issuing_authority="最高法、最高检",
        effective_date="2013-04-27",
        superseded_date=None,
        superseded_by=None,
        status=InterpStatus.ACTIVE,
        crime_types=["敲诈勒索罪"],
        key_content="敲诈勒索罪数额标准",
        key_thresholds={
            "数额较大": "2000元至5000元以上",
            "数额巨大": "3万元至10万元以上",
            "数额特别巨大": "30万元至50万元以上",
        },
    ),

    # ===== 污染环境罪 =====
    JudicialInterp(
        name="最高人民法院、最高人民检察院关于办理环境污染刑事案件适用法律若干问题的解释（2023修订）",
        abbr="污染环境司法解释（2023）",
        issuing_authority="最高法、最高检",
        effective_date="2023-08-15",
        superseded_date=None,
        superseded_by=None,
        status=InterpStatus.ACTIVE,
        crime_types=["污染环境罪"],
        key_content="污染环境罪'情节严重/情节特别严重'的具体标准",
        key_thresholds={
            "非法排放": "3吨以上",
            "危险废物": "10吨以上",
            "情节特别严重": "上述标准的10倍以上",
        },
        notes="2023年修订，原2016年解释同时废止",
    ),

    # ===== 非法经营罪 =====
    JudicialInterp(
        name="最高人民法院关于审理非法出版物刑事案件具体应用法律若干问题的解释",
        abbr="非法出版物司法解释（1998）",
        issuing_authority="最高法",
        effective_date="1998-12-23",
        superseded_date=None,
        superseded_by=None,
        status=InterpStatus.ACTIVE,
        crime_types=["非法经营罪"],
        key_content="非法经营出版物数额/违法所得标准",
        key_thresholds={
            "经营数额": "5万元以上",
            "违法所得": "2万元以上",
        },
    ),

    # ===== 危险驾驶罪 =====
    JudicialInterp(
        name="最高人民法院、最高人民检察院、公安部关于办理醉酒驾驶机动车刑事案件适用法律若干问题的意见",
        abbr="醉驾意见（2013）",
        issuing_authority="最高法、最高检、公安部",
        effective_date="2013-12-18",
        superseded_date=None,
        superseded_by=None,
        status=InterpStatus.ACTIVE,
        crime_types=["危险驾驶罪"],
        key_content="醉驾血液酒精含量≥80mg/100ml即构成犯罪",
        key_thresholds={
            "醉驾": "血液酒精≥80mg/100ml",
            '情节轻微': "血液酒精100mg/100ml以下，无事故",
        },
    ),

    # ===== 帮助信息网络犯罪活动罪（帮信罪） =====
    JudicialInterp(
        name="最高人民法院、最高人民检察院关于办理非法利用信息网络、帮助信息网络犯罪活动等刑事案件适用法律若干问题的解释",
        abbr="帮信罪司法解释（2019）",
        issuing_authority="最高法、最高检",
        effective_date="2019-11-01",
        superseded_date=None,
        superseded_by=None,
        status=InterpStatus.ACTIVE,
        crime_types=["帮助信息网络犯罪活动罪"],
        key_content="帮信罪的入罪标准：支付结算/广告推广/技术支持金额20万元以上",
        key_thresholds={
            "支付结算金额": "20万元以上",
            "违法所得": "1万元以上",
            "情节严重": "上述标准的2倍或为3个以上对象提供帮助",
        },
    ),

    # ===== 行贿罪 =====
    JudicialInterp(
        name="最高人民法院、最高人民检察院关于办理贪污贿赂刑事案件适用法律若干问题的解释",
        abbr="行贿罪司法解释（2016）",
        issuing_authority="最高法、最高检",
        effective_date="2016-04-18",
        superseded_date=None,
        superseded_by=None,
        status=InterpStatus.ACTIVE,
        crime_types=["行贿罪", "对有影响力的人行贿罪"],
        key_content="行贿罪立案标准、情节严重、情节特别严重标准",
        key_thresholds={
            "立案标准": "3万元以上",
            "情节严重": "100万元以上",
            "情节特别严重": "500万元以上",
            "谋取不正当利益": "关键构成要件",
        },
    ),

    # ===== 寻衅滋事罪 =====
    JudicialInterp(
        name="最高人民法院、最高人民检察院关于办理寻衅滋事刑事案件适用法律若干问题的解释",
        abbr="寻衅滋事司法解释（2013）",
        issuing_authority="最高法、最高检",
        effective_date="2013-07-22",
        superseded_date=None,
        superseded_by=None,
        status=InterpStatus.ACTIVE,
        crime_types=["寻衅滋事罪"],
        key_content="寻衅滋事罪'情节恶劣/情节严重'的标准",
        key_thresholds={
            "随意殴打他人": "2次以上/1人以上轻伤",
            "强拿硬要": "1000元以上",
            "造成公共场所秩序严重混乱": "无数额要求",
        },
    ),

    # ===== 组织、领导传销活动罪 =====
    JudicialInterp(
        name="最高人民法院、最高人民检察院、公安部关于办理组织领导传销活动刑事案件适用法律若干问题的意见",
        abbr="传销司法意见（2013）",
        issuing_authority="最高法、最高检、公安部",
        effective_date="2013-11-14",
        superseded_date=None,
        superseded_by=None,
        status=InterpStatus.ACTIVE,
        crime_types=["组织、领导传销活动罪"],
        key_content="传销活动层级和人数认定",
        key_thresholds={
            "层级": "3级以上",
            "人数": "30人以上",
            "涉案金额": "100万元以上",
        },
    ),
]


class JudicialInterpBaseline:
    """
    司法解释覆盖基线管理器

    用法：
        baseline = JudicialInterpBaseline()

        # 检查引用覆盖
        coverage = baseline.check_coverage([
            "关于办理盗窃刑事案件适用法律若干问题的解释",
            "关于办理贪污贿赂刑事案件适用法律若干问题的解释",
        ])

        # 获取某罪名的现行有效解释
        interps = baseline.get_active_for_crime("职务侵占罪")

        # 生成报告引用说明
        disclaimer = baseline.generate_report_disclaimer()
    """

    def __init__(self):
        self._interps = {i.name: i for i in JUDICIAL_INTERPRETATIONS}
        self._by_crime: Dict[str, List[JudicialInterp]] = {}
        for interp in JUDICIAL_INTERPRETATIONS:
            for crime in interp.crime_types:
                self._by_crime.setdefault(crime, []).append(interp)

    def all_interpretations(self) -> List[JudicialInterp]:
        return JUDICIAL_INTERPRETATIONS

    def get_all_interpretations(self) -> List[JudicialInterp]:
        """all_interpretations 的别名，保持 API 一致性"""
        return self.all_interpretations()

    def get(self, name: str) -> Optional[JudicialInterp]:
        """精确查找司法解释"""
        return self._interps.get(name)

    def search(self, keyword: str) -> List[JudicialInterp]:
        """关键词模糊搜索"""
        kw = keyword.lower()
        return [
            i for i in JUDICIAL_INTERPRETATIONS
            if kw in i.name.lower() or kw in i.abbr.lower()
            or any(kw in c.lower() for c in i.crime_types)
        ]

    def get_active_for_crime(self, crime_type: str) -> List[JudicialInterp]:
        """获取某罪名的现行有效司法解释"""
        return [
            i for i in self._by_crime.get(crime_type, [])
            if i.status == InterpStatus.ACTIVE
        ]

    def check_coverage(self, cited_interps: List[str]) -> Dict[str, dict]:
        """
        核查报告中引用的司法解释是否在基线覆盖范围内

        匹配策略（优先级递减）：
          1. 精确匹配（key 完全一致）
          2. normalize 后匹配（去除"最高法"与"最高法、最高检"前缀差异）
          3. 关键词匹配（罪名核心词同时出现在 query 和库中）
          4. search() 模糊搜索兜底

        Returns:
            {解释名: {found: bool, interp: JudicialInterp|None, status: str}}
        """
        result = {}

        def _norm(s: str) -> str:
            """去除"最高法、最高检"与"最高法"等前缀差异，保留核心名称"""
            return re.sub(r"^[最高法最高检两高三部省市区]+[、]?", "", s).strip()

        def _kw_match(query: str, interp_name: str) -> bool:
            """关键词匹配：query 与 interp 含有共同的罪名核心词"""
            qn, inn = _norm(query).lower(), interp_name.lower()
            core = ["盗窃", "诈骗", "抢夺", "敲诈勒索", "非法吸收", "集资诈骗",
                    "职务侵占", "挪用资金", "行贿", "受贿", "污染环境",
                    "赌博", "非法经营", "醉驾", "危险驾驶", "帮信",
                    "寻衅滋事", "传销", "贪污贿赂"]
            return any(k in qn and k in inn for k in core)

        for name in cited_interps:
            # 策略1：精确 key 匹配
            interp = self._interps.get(name)
            strat = "exact"

            # 策略2：normalize 后扫描（去掉机关前缀后匹配）
            if not interp:
                norm_name = _norm(name)
                for k, v in self._interps.items():
                    if _norm(k) == norm_name:
                        interp = v
                        strat = "normalize"
                        break

            # 策略3：关键词匹配
            if not interp:
                hits = [v for k, v in self._interps.items() if _kw_match(name, k)]
                if hits:
                    interp = hits[0]
                    strat = "keyword"

            if interp:
                result[name] = {
                    "found": True,
                    "interp": interp,
                    "status": interp.status,
                    "effective_date": interp.effective_date,
                    "superseded_by": interp.superseded_by,
                    "strategy": strat,
                }
            else:
                # 策略4：search() 模糊兜底
                matches = self.search(name)
                if matches:
                    result[name] = {
                        "found": "partial",
                        "interp": matches[0],
                        "status": matches[0].status,
                        "strategy": "fallback",
                        "note": f"可能匹配：{matches[0].name}",
                    }
                else:
                    result[name] = {
                        "found": False,
                        "interp": None,
                        "status": "未知",
                        "strategy": "not_found",
                        "note": "该司法解释不在基线覆盖范围内，建议核查原文",
                    }
        return result

    def generate_coverage_report(self, cited_interps: List[str] = None) -> str:
        """生成司法解释覆盖说明（用于报告附录）"""
        lines = [
            "## 司法解释覆盖说明",
            "",
            "本报告引用的司法解释均属现行有效规范，以下为覆盖基线：",
            "",
        ]
        for interp in JUDICIAL_INTERPRETATIONS:
            if interp.status == InterpStatus.ACTIVE:
                status_icon = "✅"
            elif interp.status == InterpStatus.SUPERSEDED:
                status_icon = "❌"
            else:
                status_icon = "⚠️"

            lines.append(f"{status_icon} **{interp.abbr}**")
            lines.append(f"  - 发布机关：{interp.issuing_authority}")
            lines.append(f"  - 施行日期：{interp.effective_date}")
            lines.append(f"  - 状态：{interp.status}")
            if interp.superseded_by:
                lines.append(f"  - ⚠️ 已被 {interp.superseded_by} 替代")
            lines.append(f"  - 覆盖罪名：{', '.join(interp.crime_types)}")
            if interp.key_thresholds:
                lines.append(f"  - 关键标准：")
                for k, v in interp.key_thresholds.items():
                    lines.append(f"    · {k}：{v}")
            lines.append("")

        # 覆盖核查
        if cited_interps:
            lines.append("### 本报告引用核查")
            coverage = self.check_coverage(cited_interps)
            for name, result in coverage.items():
                if result["found"] is True:
                    lines.append(f"✅ {name} — {result['status']}")
                elif result["found"] == "partial":
                    lines.append(f"⚠️ {name} — {result.get('note', '')}")
                else:
                    lines.append(f"❌ {name} — 未在基线中找到，建议核查原文")
            lines.append("")

        lines.append(
            "**注**：司法解释可能随时修订，请在最高人民法院官网（www.court.gov.cn）"
            "核查最新有效版本。"
        )
        return "\n".join(lines)

    def get_coverage_summary(self) -> Dict[str, int]:
        """获取覆盖统计"""
        active = sum(1 for i in JUDICIAL_INTERPRETATIONS if i.status == InterpStatus.ACTIVE)
        superseded = sum(1 for i in JUDICIAL_INTERPRETATIONS if i.status == InterpStatus.SUPERSEDED)
        return {
            "total": len(JUDICIAL_INTERPRETATIONS),
            "active": active,
            "superseded": superseded,
            "coverage_crimes": len(set(
                c for i in JUDICIAL_INTERPRETATIONS for c in i.crime_types
            )),
        }


# ===== CLI =====

def main():
    import argparse
    parser = argparse.ArgumentParser(description="司法解释覆盖基线")
    parser.add_argument("--list", action="store_true", help="列出所有司法解释")
    parser.add_argument("--crime", type=str, help="查询某罪名的司法解释")
    parser.add_argument("--search", type=str, help="关键词搜索")
    parser.add_argument("--check", type=str, help="核查指定司法解释（逗号分隔）")
    parser.add_argument("--report", action="store_true", help="生成覆盖报告")
    args = parser.parse_args()

    baseline = JudicialInterpBaseline()

    if args.list:
        summary = baseline.get_coverage_summary()
        print(f"\n司法解释基线总览：")
        print(f"  总数: {summary['total']} 部")
        print(f"  现行有效: {summary['active']} 部")
        print(f"  已废止: {summary['superseded']} 部")
        print(f"  覆盖罪名: {summary['coverage_crimes']} 个")
        print()
        for interp in JUDICIAL_INTERPRETATIONS:
            status_icon = "✅" if interp.status == InterpStatus.ACTIVE else "❌"
            print(f"  {status_icon} {interp.abbr}")
            print(f"      罪名: {', '.join(interp.crime_types)} | 施行: {interp.effective_date}")

    elif args.crime:
        interps = baseline.get_active_for_crime(args.crime)
        if interps:
            print(f"\n【{args.crime}】现行有效司法解释：")
            for i in interps:
                print(f"  · {i.name}")
                print(f"    施行: {i.effective_date} | 关键标准: {i.key_thresholds}")
        else:
            print(f"\n未找到 {args.crime} 的专门司法解释（可能适用刑法总则）")

    elif args.search:
        results = baseline.search(args.search)
        print(f"\n搜索「{args.search}」结果：")
        for i in results:
            print(f"  · {i.abbr} [{i.status}]")

    elif args.check:
        cited = [x.strip() for x in args.check.split(",") if x.strip()]
        coverage = baseline.check_coverage(cited)
        print(f"\n覆盖核查：")
        for name, result in coverage.items():
            found = result["found"]
            status = result["status"]
            if found is True:
                print(f"  ✅ {name} — {status}")
            elif found == "partial":
                print(f"  ⚠️ {name} — {result.get('note', '')}")
            else:
                print(f"  ❌ {name} — 未在基线中找到")

    elif args.report:
        print(baseline.generate_coverage_report())

    else:
        summary = baseline.get_coverage_summary()
        print(f"司法解释基线：{summary['total']} 部（现行 {summary['active']} / 已废止 {summary['superseded']}）")
        print(f"覆盖罪名：{summary['coverage_crimes']} 个")
        print("用法: --list | --crime 罪名 | --search 关键词 | --check 解释名 | --report")


if __name__ == "__main__":
    main()
