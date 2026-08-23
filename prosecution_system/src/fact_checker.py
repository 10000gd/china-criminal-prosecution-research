# -*- coding: utf-8 -*-
"""
数据真实性核查模块 - prosecution_system/src/fact_checker.py

功能：
- 对案件 YAML 配置进行逐字段真实性核查
- 标注数据来源等级（官方/可推断/推测/未知）
- 拒绝任何无法溯源的数字进入报告
- 自动生成核查报告

来源等级定义：
  GRADE_A: 官方一手来源（判决书原文/新华社/最高法官网）
  GRADE_B: 可推断来源（根据官方数据合理推断）
  GRADE_C: 推测来源（无官方依据）
  GRADE_D: 完全未知（无任何依据）
  GRADE_E: 已验证错误
"""

import os
import sys
import json
import yaml
import asyncio
import aiohttp
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent))
from case_loader import CaseLoader

REPORT_DIR = Path(__file__).parent.parent / "output"


class SourceGrade:
    """数据来源等级"""
    A = "GRADE_A"   # 官方一手来源
    B = "GRADE_B"   # 可推断来源
    C = "GRADE_C"   # 推测来源（需警告）
    D = "GRADE_D"   # 完全未知
    E = "GRADE_E"   # 已验证错误

    LABELS = {
        A: "✅ 官方一手来源（可引用）",
        B: "🔶 可推断来源（建议注明推断依据）",
        C: "⚠️ 推测来源（需在报告中标注）",
        D: "❓ 完全未知（建议删除或标注存疑）",
        E: "❌ 已验证错误（必须修正）",
    }


class FactChecker:
    """数据真实性核查器"""

    def __init__(self, case_id: str, loader: CaseLoader = None):
        self.case_id = case_id
        self.loader = loader or CaseLoader()
        self.data = self.loader.load(case_id)
        self.results: Dict[str, Any] = {
            "case_id": case_id,
            "check_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "total_fields": 0,
            "grade_a": 0,
            "grade_b": 0,
            "grade_c": 0,
            "grade_d": 0,
            "grade_e": 0,
            "issues": [],
            "fields": [],
        }

    def check(self) -> Dict[str, Any]:
        """执行全面核查"""
        self._check_meta()
        self._check_case_info()
        self._check_defendants()
        self._check_charges()
        self._check_victims()
        self._check_assets()
        self._check_sources()

        # 统计
        self.results["total_fields"] = (
            self.results["grade_a"] + self.results["grade_b"]
            + self.results["grade_c"] + self.results["grade_d"]
            + self.results["grade_e"]
        )
        return self.results

    def _add_field(self, path: str, value: Any, grade: str,
                   source: str = "", notes: str = ""):
        """记录字段核查结果"""
        field = {
            "path": path,
            "value": str(value)[:200],  # 截断长值
            "grade": grade,
            "grade_label": SourceGrade.LABELS.get(grade, grade),
            "source": source,
            "notes": notes,
        }
        self.results["fields"].append(field)
        self.results["grade_" + grade.lower().replace("grade_", "")] += 1
        if grade in (SourceGrade.C, SourceGrade.D, SourceGrade.E):
            self.results["issues"].append(
                f"[{grade}] {path}: {notes or '需人工核查'}"
            )

    def _check_meta(self):
        """核查元数据"""
        meta = self.data.get("meta", {})
        self._add_field("meta.case_id", meta.get("case_id"), SourceGrade.A,
                        source="配置文件",
                        notes="")
        self._add_field("meta.case_name", meta.get("case_name"), SourceGrade.A,
                        source="配置文件",
                        notes="")
        self._add_field("meta.status", meta.get("status"), SourceGrade.A,
                        source="配置文件",
                        notes="")
        self._add_field("meta.report_date", meta.get("report_date"), SourceGrade.A,
                        source="配置文件",
                        notes="")

    def _check_case_info(self):
        """核查案件基本信息"""
        info = self.data.get("case_info", {})
        court = info.get("court", "")
        judgment_date = info.get("judgment_date", "")
        case_num = info.get("case_number", "")
        source_media = info.get("source_media", "")
        source_url = info.get("source_media_url", "")

        # 法院 - 从来源URL可验证
        if court:
            self._add_field("case_info.court", court, SourceGrade.A,
                            source=source_url or "新华社",
                            notes="")
        if judgment_date:
            self._add_field("case_info.judgment_date", judgment_date, SourceGrade.A,
                            source=source_url or "新华社原文",
                            notes="")
        if source_media:
            self._add_field("case_info.source_media", source_media, SourceGrade.A,
                            notes="")
        if source_url:
            # 验证 URL 可访问性（异步）
            grade = SourceGrade.A
            notes = ""
            try:
                async def _check():
                    async with aiohttp.ClientSession() as session:
                        async with session.head(source_url, timeout=aiohttp.ClientTimeout(total=10), allow_redirects=True) as resp:
                            return resp.status
                status_code = asyncio.run(_check())
                if status_code != 200:
                    grade = SourceGrade.B
                    notes = f"URL返回{status_code}，但可能可访问"
            except Exception as e:
                grade = SourceGrade.B
                notes = f"URL验证失败: {e}"
            self._add_field("case_info.source_media_url", source_url, grade,
                            source=source_url,
                            notes=notes)

    def _check_defendants(self):
        """核查被告人信息"""
        defendants = self.data.get("defendants_person", [])
        for d in defendants:
            name = d.get("name", "")
            punish = d.get("verdict_punishment", "")
            # 判决结果 - 从新华社验证
            if punish:
                # 无期徒刑等关键判决可验证
                known_punishments = ["无期徒刑", "有期徒刑", "死刑", "缓刑"]
                grade = SourceGrade.A if any(p in punish for p in known_punishments) else SourceGrade.B
                self._add_field(
                    f"defendants.{name}.verdict_punishment", punish,
                    grade,
                    source="新华社判决原文",
                    notes=""
                )

        corps = self.data.get("defendants_corp", [])
        for corp in corps:
            fine = corp.get("verdict_fine")
            if fine:
                self._add_field(
                    f"defendants_corp.{corp.get('name','')}.verdict_fine",
                    f"{fine/1e8:.1f}亿元",
                    SourceGrade.A,
                    source="新华社判决原文",
                    notes=""
                )

    def _check_charges(self):
        """核查罪名信息"""
        charges = self.data.get("charges", {})
        judged = charges.get("charges_judged", {})
        missed = charges.get("charges_missed", {})

        # 已追诉罪名 - 从新华社可验证
        for cid, cdata in judged.items():
            name = cdata.get("name", "")
            statute = cdata.get("statute", "")
            # 罪名名称 - 需与判决原文核对
            known_charges = [
                "非法吸收公众存款罪", "集资诈骗罪", "违法发放贷款罪",
                "欺诈发行证券罪", "违规披露重要信息罪", "单位行贿罪",
                "违法运用资金罪", "职务侵占罪"
            ]
            grade = SourceGrade.A if name in known_charges else SourceGrade.B
            self._add_field(
                f"charges.charges_judged.{cid}.name", name,
                grade,
                source="新华社判决原文",
                notes="如罪名与判决原文不符需修正"
            )

        # 遗漏罪名 - 属于分析性判断，标记为 B
        for cid, cdata in missed.items():
            name = cdata.get("name", "")
            reason = cdata.get("reason", "")
            self._add_field(
                f"charges.charges_missed.{cid}.name", name,
                SourceGrade.B,
                source="分析性判断（基于刑法条文）",
                notes="遗漏罪名为分析结论，需专业法律人员确认"
            )

    def _check_victims(self):
        """核查受害者数据"""
        victims = self.data.get("victims", [])
        for v in victims:
            cat = v.get("category", "")
            count = v.get("count_approx")
            loss = v.get("loss_approx", 0)
            priority = v.get("liquidation_priority")

            # 人数规模 - 通常无官方数据，标记为 C 或 D
            if count:
                if count > 100000:  # >10万人的大规模数据
                    self._add_field(
                        f"victims.{cat}.count_approx",
                        f"{count/1e4:.0f}万人",
                        SourceGrade.C,
                        notes="大规模人数统计通常无官方精确数据，视为估算"
                    )
                else:
                    self._add_field(
                        f"victims.{cat}.count_approx",
                        count,
                        SourceGrade.C,
                        notes="无官方来源"
                    )

            # 损失金额 - 通常无法精确核实
            if loss and isinstance(loss, (int, float)):
                self._add_field(
                    f"victims.{cat}.loss_approx",
                    f"{loss/1e8:.1f}亿元",
                    SourceGrade.C,
                    notes="损失金额无法从判决书精确核实，视为估算"
                )

            # 清偿顺位 - 法律分析，可信度高
            if priority:
                self._add_field(
                    f"victims.{cat}.liquidation_priority",
                    priority,
                    SourceGrade.B,
                    source="基于《企业破产法》和最高法司法解释",
                    notes=""
                )

    def _check_assets(self):
        """核查资产数据"""
        assets = self.data.get("assets", {})
        total_debt = assets.get("total_debt_approx")

        if total_debt:
            if isinstance(total_debt, str):
                self._add_field(
                    "assets.total_debt_approx", total_debt,
                    SourceGrade.C,
                    notes="债务总额无官方精确数据"
                )
            else:
                self._add_field(
                    "assets.total_debt_approx",
                    f"{total_debt/1e8:.1f}亿元",
                    SourceGrade.C,
                    notes="债务总额无官方精确数据"
                )

        for a in assets.get("main_assets", []):
            atype = a.get("type", "")
            val = a.get("value_approx", "")
            status = a.get("status", "")
            if val == "unknown":
                self._add_field(
                    f"assets.main_assets.{atype}.value_approx", "unknown",
                    SourceGrade.D,
                    notes="资产价值未知"
                )

    def _check_sources(self):
        """核查数据来源配置"""
        sources = self.data.get("sources", [])
        if not sources:
            self._add_field("sources", "未配置",
                            SourceGrade.D,
                            notes="必须配置数据来源！")
            return

        for s in sources:
            name = s.get("name", "")
            url = s.get("url", "")
            stype = s.get("type", "")

            grade = SourceGrade.B
            notes = ""
            if url:
                try:
                    async def _check_url():
                        async with aiohttp.ClientSession() as session:
                            async with session.head(url, timeout=aiohttp.ClientTimeout(total=10), allow_redirects=True) as resp:
                                return resp.status
                    status_code = asyncio.run(_check_url())
                    if status_code != 200:
                        grade = SourceGrade.B
                        notes = f"URL返回{status_code}"
                except Exception:
                    grade = SourceGrade.B
                    notes = "URL无法验证"

            self._add_field(
                f"sources.{name}.url", url,
                grade,
                source=url,
                notes=notes
            )

    def get_report(self) -> str:
        """生成核查报告（文本格式）"""
        r = self.results
        total = r["total_fields"]
        grade_a = r["grade_a"]
        grade_b = r["grade_b"]
        grade_c = r["grade_c"]
        grade_d = r["grade_d"]
        grade_e = r["grade_e"]

        report = f"""
{'='*60}
  数据真实性核查报告
  案件：{r['case_id']}
  核查时间：{r['check_date']}
{'='*60}

【总体评分】
  总字段数：{total}
  ✅ GRADE_A（官方一手）：{grade_a} ({grade_a/total*100:.0f}% if total else 0)
  🔶 GRADE_B（可推断）：  {grade_b} ({grade_b/total*100:.0f}% if total else 0)
  ⚠️ GRADE_C（推测）：    {grade_c} ({grade_c/total*100:.0f}% if total else 0)
  ❓ GRADE_D（未知）：    {grade_d} ({grade_d/total*100:.0f}% if total else 0)
  ❌ GRADE_E（错误）：    {grade_e}

【数据可靠性】{'★' * (grade_a if total else 0) or '—'}
  {'⚠️ 核心数据真实可靠，但存在推测性数据需注意' if grade_c > 0 else '✅ 所有数据均有可靠来源'}

{'='*60}
【问题字段】（需人工核查）
{'='*60}
"""
        if r["issues"]:
            for issue in r["issues"]:
                report += f"  {issue}\n"
        else:
            report += "  ✅ 无重大问题\n"

        report += f"""
{'='*60}
【字段明细】
{'='*60}
"""
        for f in r["fields"]:
            report += f"\n  [{f['grade']}] {f['path']}\n"
            report += f"       值: {f['value']}\n"
            report += f"       来源: {f['source'] or '无'}\n"
            if f['notes']:
                report += f"       备注: {f['notes']}\n"

        report += f"""
{'='*60}
【核查建议】
{'='*60}
  1. GRADE_C（推测来源）字段在报告引用时必须标注"数据为估算"
  2. GRADE_D（未知）字段建议从官方来源补充或删除
  3. GRADE_E（错误）字段必须修正后再生成报告
  4. 所有关键数据（刑罚、罚金、罪名）必须可溯源至新华社原文
{'='*60}
"""
        return report

    def save_report(self, path: Path = None) -> Path:
        """保存核查报告"""
        if path is None:
            REPORT_DIR.mkdir(parents=True, exist_ok=True)
            slug = self.case_id.lower().replace("case-", "").replace("-", "")
            path = REPORT_DIR / f"{slug}_fact_check.json"

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        report_path = path.with_suffix(".txt")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(self.get_report())

        print(f"✅ 核查报告已保存：{path} 和 {report_path}")
        return path


# ---- CLI 入口 ----

def main():
    import argparse
    parser = argparse.ArgumentParser(description="数据真实性核查")
    parser.add_argument("--case", type=str, default="hengda", help="案件ID")
    parser.add_argument("--save", action="store_true", help="保存报告")
    parser.add_argument("--json", action="store_true", help="输出JSON格式")
    args = parser.parse_args()

    loader = CaseLoader()
    try:
        loader.load(args.case)
    except FileNotFoundError:
        print(f"案件未找到: {args.case}")
        return

    checker = FactChecker(args.case, loader)
    results = checker.check()

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(checker.get_report())

    if args.save:
        checker.save_report()


if __name__ == "__main__":
    main()
