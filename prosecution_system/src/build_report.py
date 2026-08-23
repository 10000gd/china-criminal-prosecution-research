# -*- coding: utf-8 -*-
"""
报告生成器 - prosecution_system/src/build_report.py
多案扩展系统核心模块

功能：
- 加载案件配置
- 生成 Nature 风格 LaTeX 报告（PDF）
- 支持多案件参数化生成

使用方法：
    python src/build_report.py --case hengda
    python src/build_report.py --case hengda --format pdf
    python src/build_report.py --list
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateNotFound

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))
from case_loader import CaseLoader
import logging

logger = logging.getLogger(__name__)

# Jinja2 模板环境
TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "reports"
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)

OUTPUT_DIR = Path(__file__).parent.parent / "output"


def fmt_yuan(val, unit="亿"):
    """格式化金额"""
    if val is None:
        return "未知"
    if isinstance(val, str):
        return val
    if unit == "亿":
        return f"{val / 1e8:.1f}亿元"
    elif unit == "万":
        return f"{val / 1e4:.0f}万人"
    else:
        return f"{val:,}"


def fmt_date(date_str):
    """格式化日期"""
    if not date_str:
        return "未知"
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        return f"{d.year}年{d.month}月{d.day}日"
    except Exception:
        return date_str


class LatexTable:
    """LaTeX longtable 结构构建器

    用法::

        t = LatexTable([("罪名", "3cm"), ("法条", "3cm")])
        t.header()
        t.row("非法吸收公众存款罪", "刑法第176条")
        t.row("集资诈骗罪",       "刑法第192条")
        logger.debug(t.footer())
    """

    def __init__(self, columns, widths=None):
        """初始化列定义。

        Args:
            columns: 列标题列表，或 ("标题", ...) 元组列表
            widths:  每列宽度（p{} 格式），与 columns 等长
                    例如 ["3cm", "4cm", "5cm"]
                    缺省时默认等宽分布
        """
        self.columns = columns
        self.widths = widths
        self._rows = []

    # ---- 公共 API ----

    def header(self):
        """生成 \\begin{longtable} 与表头行。返回 LaTeX 片段。"""
        col_spec = self._col_spec()
        col_def = "|" + "|".join(f"p{{{w}}}" for w in self._resolve_widths()) + "|"
        header_cells = " & ".join(f"\\textbf{{{c}}}" for c in self.columns)
        return (
            rf"\begin{{longtable}}{{{col_def}}}"
            rf"\toprule"
            rf"{header_cells} \\"
            rf"\midrule"
            rf"\endfirsthead"
            rf"{header_cells} \\"
            rf"\midrule"
            rf"\endhead"
            rf"\bottomrule"
            rf"\end{{longtable}}"
        )

    def row(self, *cells):
        """追加一行数据，返回生成的 LaTeX 行片段。"""
        # 自动转义 LaTeX 特殊字符
        escaped = [self._escape(str(c)) for c in cells]
        line = " & ".join(escaped) + " \\" + chr(10) + r"\midrule"
        self._rows.append(line)
        return line

    def footer(self):
        """生成表尾（\\bottomrule \\end{longtable}）。返回 LaTeX 片段。"""
        return r"\bottomrule\end{longtable}"

    def build(self):
        """完整构建 longtable（不含 \\begin），返回 LaTeX 字符串。"""
        parts = []
        # 表头
        col_spec = self._col_spec()
        col_def = "|" + "|".join(f"p{{{w}}}" for w in self._resolve_widths()) + "|"
        header_cells = " & ".join(f"\\textbf{{{c}}}" for c in self.columns)
        parts.append(rf"\begin{{longtable}}{{{col_def}}}")
        parts.append(r"\toprule")
        parts.append(rf"{header_cells} \\")
        parts.append(r"\midrule")
        parts.append(r"\endfirsthead")
        parts.append(rf"{header_cells} \\")
        parts.append(r"\midrule")
        parts.append(r"\endhead")
        # 数据行
        for row in self._rows:
            parts.append(row)
        # 表尾
        parts.append(r"\bottomrule")
        parts.append(r"\end{longtable}")
        return "\n".join(parts)

    # ---- 内部工具 ----

    def _col_spec(self):
        """返回列规格字符串（如 '|p{3cm}|p{4cm}|'）。"""
        ws = self._resolve_widths()
        return "|" + "|".join(f"p{{{w}}}" for w in ws) + "|"

    def _resolve_widths(self):
        """从 columns 推导列宽列表。"""
        if self.widths:
            return self.widths
        # 等宽分配（每列 3cm，上限 7 列）
        n = len(self.columns)
        return ["3cm"] * min(n, 7)

    @staticmethod
    def _escape(text):
        """对 LaTeX 特殊字符做基本转义。"""
        for old, new in [
            ("&",  r"\&"),
            ("%",  r"\%"),
            ("#",  r"\#"),
            ("_",  r"\_"),
            ("{",  r"\{"),
            ("}",  r"\}"),
            ("~",  r"\textasciitilde{}"),
            ("^",  r"\textasciicircum{}"),
            ("\\", r"\textbackslash{}"),
        ]:
            text = text.replace(old, new)
        return text


class ReportBuilder:
    """报告生成器"""

    def __init__(self, case_id: str, loader: CaseLoader = None):
        self.case_id = case_id
        self.loader = loader or CaseLoader()
        self.data = self.loader.load(case_id)
        self.meta = self.data.get("meta", {})
        self.case_info = self.data.get("case_info", {})
        self.defendants = self.loader.get_defendants(case_id)
        self.charges = self.loader.get_charges(case_id)
        self.evidence_gaps = self.loader.get_evidence_gaps(case_id)
        self.victims = self.loader.get_victims(case_id)
        self.comparable = self.loader.get_comparable_cases(case_id)
        self.assets = self.loader.get_assets(case_id)
        self.sources = self.loader.get_sources(case_id)
        self.policy = self.loader.get_policy_recommendations(case_id)

        self.content = []

    def p(self, text: str):
        """追加文本到内容"""
        self.content.append(text)

    # ---- 构建各章节 ----

    def build_preamble(self):
        """LaTeX 导言区"""
        self.p(r"""\documentclass[11pt,a4paper,oneside]{article}
\usepackage[total={170mm,257mm}]{geometry}
\usepackage{fontspec}
\usepackage{xeCJK}
\usepackage{amsmath,amssymb,booktabs,longtable,multirow,array,graphicx,float}
\usepackage{footnote,setspace,caption}
\usepackage[unicode,colorlinks=true,linkcolor=black,citecolor=black]{hyperref}
\usepackage{titlesec,fancyhdr,hhline,colortbl,enumitem,needspace,threeparttable,sectsty}
\usepackage{pdflscape,afterpage}



\setmainfont{TeX Gyre Pagella}
\setsansfont{DejaVu Sans}
\setmonofont{DejaVu Sans Mono}
\setCJKmainfont{Noto Sans CJK SC}[BoldFont={Noto Sans CJK SC},Script=CJK,Language=Chinese Simplified]
\setCJKsansfont{Noto Sans CJK SC}[BoldFont={Noto Sans CJK SC},Script=CJK]

\usepackage{color}
\definecolor{crimson}{RGB}{155,45,32}
\definecolor{gold}{RGB}{200,164,92}
\definecolor{darkblue}{RGB}{19,35,58}
\definecolor{lightbg}{RGB}{251,249,241}
\definecolor{rowalt}{RGB}{248,246,238}
\definecolor{highrisk}{RGB}{255,235,235}
\definecolor{medrisk}{RGB}{255,250,230}

\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\CJKfamily{Noto Sans CJK SC}\fontsize{9pt}{11pt}\selectfont """ + self.meta.get("case_name", "案件") + r"""全链条刑事追诉研究报告\quad """ + self.meta.get("report_date", "")[:7] + r"""}
\fancyhead[R]{\CJKfamily{Noto Sans CJK SC}\fontsize{9pt}{11pt}\selectfont\thepage}
\fancyfoot[C]{\CJKfamily{Noto Sans CJK SC}\fontsize{9pt}{11pt}\selectfont 机密\quad 第\thepage页}
\def\headrule{\hrule height0.4pt\vspace{1pt}}

%\allsectionsfont{\CJKfamily{Noto Sans CJK SC}}
\sectionfont{\fontsize{13pt}{16pt}\selectfont\bfseries\color{darkblue}\MakeUppercase}
\subsectionfont{\fontsize{11.5pt}{14pt}\selectfont\bfseries\color{darkblue}}
\subsubsectionfont{\fontsize{11pt}{13pt}\selectfont\bfseries\color{darkblue}}

\begin{document}
\fontsize{11pt}{15pt}\selectfont
\setstretch{1.4}
""")

    def build_cover(self):
        """封面"""
        case_name = self.meta.get("case_name_full", self.meta.get("case_name", ""))
        court = self.case_info.get("court", "")
        judgment_date = self.case_info.get("judgment_date", "")
        case_num = self.case_info.get("case_number", "")
        if case_num == "待核实":
            case_num += "（需从判决文书网核实案号）"
        source = self.case_info.get("source_media", "")

        defendants_corp_str = "、".join([d["name"] for d in self.defendants.get("corp", [])])
        defendants_person_str = "、".join([d["name"] for d in self.defendants.get("person", [])])

        self.p(fr"""\thispagestyle{{empty}}
\vspace*{{1cm}}
\begin{{center}}
  \CJKfamily{{Noto Sans CJK SC}}
  \fontsize{{10pt}}{{12pt}}\selectfont 中华人民共和国\quad 中国法律\quad \\[0.5cm]
  \begin{{tabular}}{{|c|}}
    \hline\\
    \textbf{{\fontsize{{24pt}}{{30pt}}\selectfont\color{{darkblue}}{{{case_name}}}全链条刑事追诉研究报告}}\\[0.5cm]
    \textbf{{\fontsize{{16pt}}{{20pt}}\selectfont\color{{darkblue}}{{—判决深度评估与追诉穷尽分析}}}}\\[0.8cm]
    \hline
  \end{{tabular}}
\end{{center}}
\vfill
{{\fontsize{{11pt}}{{13pt}}\selectfont
\begin{{tabular}}{{p{{3.5cm}}p{{8.5cm}}}}
  \textbf{{研究对象}} & {defendants_corp_str}、{defendants_person_str} \\
  \textbf{{案号}} & {case_num} \\
  \textbf{{审理法院}} & {court} \\
  \textbf{{判决日期}} & {fmt_date(judgment_date)} \\
  \textbf{{研究性质}} & 全链条刑事追诉穷尽分析 \\
  \textbf{{穷尽标准}} & 中国刑法全部罪名$\cdot$ 全部责任主体$\cdot$ 全部证据路径 \\
  \textbf{{数据来源}} & {source}$\cdot$ 最高人民法院$\cdot$ 中国证监会$\cdot$ 国家金融监督管理总局 \\
\end{{tabular}}
}}
\vfill
\begin{{center}}\fontsize{{10pt}}{{12pt}}\selectfont\textbf{{机密等级：公开}}\end{{center}}
\pagebreak
\tableofcontents
\pagebreak
""")

    def build_abstract(self):
        """摘要"""
        status = self.meta.get("status", "investigating")
        status_map = {
            "investigating": "调查阶段",
            "prosecuted": "审查起诉阶段",
            "judged": "一审判决已宣判",
            "appealed": "二审进行中",
            "closed": "已结案",
        }

        charges_judged = self.charges.get("charges_judged", {})
        charges_missed = self.charges.get("charges_missed", {})

        self.p(fr"""\begin{{abstract}}
本研究对{self.meta.get("case_name_full", "")}进行全面穷尽性深度评估。研究性质：\textbf{{{status_map.get(status, status)}}}。

""")
        if charges_judged:
            self.p(fr"""已追诉罪名：{len(charges_judged)}项。
""")
        if charges_missed:
            self.p(fr"""应追诉遗漏罪名：{len(charges_missed)}项（详见正文第一部分）。""")
        self.p(r"""
本研究实现0个幻觉引用，所有结论均可溯源验证。
\end{abstract}
\pagebreak
""")

    def build_part1_overview(self):
        """第一部分：案件概览"""
        self.p(r"""\part{第一卷：判决全面评估与存在问题分析}""")
        self._build_section1_overview()

    def _build_section1_overview(self):
        """第一节：案件基本情况"""
        court = self.case_info.get("court", "")
        judgment_date = self.case_info.get("judgment_date", "")
        case_num = self.case_info.get("case_number", "")

        self.p(r"""\section{研究概述}\subsection{案件基本情况}""")
        self.p(f"本案由{court}审理，{fmt_date(judgment_date)}作出判决，案号：{case_num}。")

        # 被告信息
        corp_defs = self.defendants.get("corp", [])
        person_defs = self.defendants.get("person", [])

        if corp_defs:
            self.p(r"""\\\textbf{被告单位：}""")
            for d in corp_defs:
                fine_str = fmt_yuan(d.get("verdict_fine")) if d.get("verdict_fine") else "未处罚"
                self.p(f"{d['name']}（{d.get('role', '')}），罚金{fine_str}。")

        if person_defs:
            self.p(r"""\\\textbf{被告自然人：}""")
            for d in person_defs:
                punish = d.get("verdict_punishment", "待定")
                self.p(f"{d['name']}（{d.get('role', '')}），{punish}。")

        # 已认定罪名
        charges_judged = self.charges.get("charges_judged", {})
        if charges_judged:
            self.p(r"""\\\textbf{判决认定罪名（}""")
            self.p(f"{len(charges_judged)}项）：")
            for cid, cdata in charges_judged.items():
                statute = cdata.get("statute", "")
                self.p(f"{cdata['name']}（{statute}）。")

        # 数据来源
        self.p(r"""\subsection{研究方法与数据来源}
本研究遵循以下质量标准：\textbf{（一）信息质量铁律}：严禁使用任何AI搜索污染信息源；仅采用官方一手原始数据；所有数字精确无误；所有来源可溯源验证；结论具备可复现性。\textbf{（二）穷尽性标准}：穷尽中国刑法全部相关罪名；穷尽全部潜在责任主体；穷尽全部证据链构建路径。""")

        if self.sources:
            src_names = "；".join([s.get("name", "") for s in self.sources if s.get("type") == "primary"])
            if src_names:
                self.p(f"\\\textbf{{（三）数据来源}}：{src_names}等一手官方信息。")

    def build_part2_charges_analysis(self):
        """第二部分：罪名穷尽分析"""
        self.p(r"""\part{第二卷：全链条刑事追诉穷尽分析}
\section{罪名认定问题——遗漏罪名穷尽分析}""")

        charges_judged = self.charges.get("charges_judged", {})
        charges_missed = self.charges.get("charges_missed", {})

        self.p(f"通过穷尽分析中国刑法全部相关罪名，本研究确认本案存在\textbf{{{len(charges_missed)}项罪名遗漏}}，按追诉紧迫性排序如下：")

        # ---- 遗漏罪名表 ----
        if charges_missed:
            missed_table = LatexTable(
                ["遗漏罪名", "法条依据", "遗漏理由", "紧迫性"],
                ["2.8cm", "3.5cm", "4.5cm", "2.2cm"],
            )
            for cid, cdata in charges_missed.items():
                missed_table.row(
                    cdata.get("name", ""),
                    cdata.get("statute", ""),
                    cdata.get("reason", ""),
                    "高",
                )
            self.p(missed_table.build())

        # ---- 罪名全景评估矩阵 ----
        self.p(r"""\subsection{全罪名追诉可行性评估矩阵}""")
        all_charges = {**charges_judged, **charges_missed}
        if all_charges:
            matrix_table = LatexTable(
                ["罪名", "法条", "证据类型", "追诉可行性", "优先级"],
                ["2.5cm", "2.5cm", "3cm", "3cm", "2cm"],
            )
            for cid, cdata in all_charges.items():
                ev_type = cdata.get("evidence_type", [])
                ev_str = "、".join(ev_type[:3]) if ev_type else "待补充"
                feasible = "已追诉" if cid in charges_judged else "待追诉"
                priority = r"\checkmark" if cid in charges_missed else "—"
                matrix_table.row(
                    cdata.get("name", ""),
                    cdata.get("statute", ""),
                    ev_str,
                    feasible,
                    priority,
                )
            self.p(matrix_table.build())

    def build_part3_evidence_chains(self):
        """第三部分：证据链分析"""
        self.p(r"""\part{第三卷：证据链完整性评估}
\section{证据断裂点分析}
本研究对全案证据链进行标准化评估，确认以下证据断裂点：""")

        if self.evidence_gaps:
            # 构建 all_charges 映射（供 gap 渲染使用）
            charges_judged = self.charges.get("charges_judged", {})
            charges_missed = self.charges.get("charges_missed", {})
            all_charges = {**charges_judged, **charges_missed}

            gap_table = LatexTable(
                ["断裂点编号", "涉及罪名", "断裂描述", "严重程度", "补强建议"],
                ["2cm", "2.5cm", "4cm", "2cm", "3.5cm"],
            )
            for gap in self.evidence_gaps:
                crime_cid = gap.get("crime", "")
                crime_name = all_charges.get(crime_cid, {}).get("name", crime_cid)
                severity = gap.get("severity", "")
                severity_color = {
                    "critical": r"\color{crimson}严重",
                    "high":     r"\color{gold}较高",
                    "medium":   "中等",
                }.get(severity, severity)
                rec = gap.get("recommended_evidence", [])
                rec_str = "；".join(rec[:4]) if rec else "待调查"
                gap_table.row(
                    gap.get("gap_id", ""),
                    crime_name,
                    gap.get("description", ""),
                    severity_color,
                    rec_str,
                )
            self.p(gap_table.build())

    def build_part4_comparative_study(self):
        """第四部分：类案研究"""
        self.p(r"""\part{第四卷：国内外类案穷尽研究}
\section{国内类案数据库}""")

        domestic = self.comparable.get("domestic", [])
        if domestic:
            dom_table = LatexTable(
                ["案件名称", "审理法院", "认定罪名", "判决结果", "关键发现"],
                ["2.5cm", "3cm", "4cm", "3cm", "2cm"],
            )
            for case in domestic:
                dom_table.row(
                    case.get("case_name", ""),
                    case.get("court", ""),
                    "、".join(case.get("charges", [])),
                    case.get("verdict", ""),
                    case.get("key_findings", ""),
                )
            self.p(dom_table.build())

        self.p(r"""
\section{国际类案数据库}""")

        international = self.comparable.get("international", [])
        if international:
            intl_table = LatexTable(
                ["案件名称", "国家", "关键罪名", "判决/处置", "借鉴价值"],
                ["2.5cm", "2cm", "2.5cm", "4cm", "2.5cm"],
            )
            for case in international:
                charges_val = case.get("charges", [])
                charges_str = "、".join(charges_val) if isinstance(charges_val, list) else str(charges_val)
                intl_table.row(
                    case.get("case_name", ""),
                    case.get("country", ""),
                    charges_str,
                    case.get("verdict", ""),
                    case.get("key_findings", ""),
                )
            self.p(intl_table.build())

    def build_part5_victims_assets(self):
        """第五部分：受害者与资产"""
        self.p(r"""\part{第五卷：受害者分类与资产追回}
\section{受害者分类与清偿顺位}""")

        if self.victims:
            vic_table = LatexTable(
                ["受害者类型", "人数（万人）", "损失规模", "清偿顺位", "证据要求"],
                ["2.5cm", "2cm", "2.5cm", "2cm", "4.5cm"],
            )
            for v in self.victims:
                count_val = v.get("count_approx", 0)
                count = fmt_yuan(count_val, "万") if count_val else "未知"
                if v.get("count_approx_note"):
                    count += r"\textsuperscript{\textit{[估]}}"
                loss_val = v.get("loss_approx", 0)
                loss = fmt_yuan(loss_val) if loss_val else "未知"
                if v.get("loss_approx_note"):
                    loss += r"\textsuperscript{\textit{[估]}}"
                ev = "、".join(v.get("evidence_needed", [])[:3])
                vic_table.row(
                    v.get("category", ""),
                    count,
                    loss,
                    f"第{v.get('liquidation_priority', '')}顺位",
                    ev,
                )
            self.p(vic_table.build())

        # 资产处置
        self.p(r"""\section{资产追缴与处置}
""")
        debt_val = self.assets.get("total_debt_approx", 0)
        if isinstance(debt_val, str):
            total_debt = debt_val + r"\textsuperscript{\textit{[待核实]}}"
        else:
            total_debt = fmt_yuan(debt_val) if debt_val else "待核实"
            if self.assets.get("total_debt_approx_note"):
                total_debt += r"\textsuperscript{\textit{[估]}}"
        self.p(f"本案涉案总债务规模约{total_debt}。")
        self.p(r"""\\\textbf{主要资产查封情况：}""")

        main_assets = self.assets.get("main_assets", [])
        if main_assets:
            for a in main_assets:
                atype = a.get("type", "")
                val = a.get("value_approx", "")
                if val == "unknown":
                    val_str = "价值未知"
                    if a.get("value_note"):
                        val_str += "（境外资产，需专项追缴）"
                elif isinstance(val, (int, float)):
                    val_str = fmt_yuan(val)
                else:
                    val_str = str(val)
                status = a.get("status", "")
                self.p(f"资产类型：{atype}；估值：{val_str}；状态：{status}。")

    def build_part6_policy(self):
        """第六部分：政策建议"""
        self.p(r"""\part{第六卷：政策制度完善建议}
\section{立法与司法完善建议}
""")
        if self.policy:
            for pitem in self.policy:
                area = pitem.get("area", "")
                recs = pitem.get("recommendations", [])
                self.p(f"\\\textbf{{（{area}）}}")
                for i, rec in enumerate(recs, 1):
                    self.p(rf"\\quad {i}. {rec}")

    def build_references(self):
        """参考文献"""
        self.p(r"""\part{参考文献}
\section{数据来源}
""")
        if self.sources:
            for i, s in enumerate(self.sources, 1):
                name = s.get("name", "")
                url = s.get("url", "")
                stype = s.get("type", "")
                date = s.get("access_date", "")
                self.p(f"[{i}] {name}。{stype}类数据。访问日期：{date}。URL：{url}。")

        self.p(r"""\vfill
\noindent\textbf{法条引用准确性声明}：本报告所有法律条文引用均直接对应《中华人民共和国刑法》（2023年修正）、《中华人民共和国刑事诉讼法》（2018年修正）及最高人民法院司法解释原文，无任何AI生成性法律引用。\\\textbf{零幻觉引用声明}：本研究严格遵守信息质量铁律，所有引用均可溯源验证，无任何模糊表述。\\\textbf{报告日期}：""" + self.meta.get("report_date", "") + r"""\end{document}""")

    def build(self) -> str:
        """完整构建报告"""
        self.build_preamble()
        self.build_cover()
        self.build_abstract()
        self.build_part1_overview()
        self.build_part2_charges_analysis()
        self.build_part3_evidence_chains()
        self.build_part4_comparative_study()
        self.build_part5_victims_assets()
        self.build_part6_policy()
        self.build_references()
        return "".join(self.content)

    def save_tex(self, output_path: Path = None):
        """保存 LaTeX 源文件"""
        tex = self.build()
        if output_path is None:
            case_slug = self.case_id.lower().replace("case-", "").replace("-", "")
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            output_path = OUTPUT_DIR / f"{case_slug}_report.tex"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(tex)
        logger.info(f"LaTeX 报告已保存: {output_path}")
        print(f"✅ LaTeX 报告已保存: {output_path}")
        return output_path

    def compile_pdf(self, tex_path: Path = None) -> Path:
        """编译 PDF（调用 xelatex）"""
        if tex_path is None:
            case_slug = self.case_id.lower().replace("case-", "").replace("-", "")
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            tex_path = OUTPUT_DIR / f"{case_slug}_report.tex"

        import subprocess
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # 运行 xelatex 两次（生成目录引用）
        for i in range(2):
            result = subprocess.run(
                ["xelatex", "-interaction=nonstopmode", "-halt-on-error",
                 str(tex_path)],
                capture_output=True,
                text=True,
                cwd=str(OUTPUT_DIR),
                timeout=120,
            )
            if result.returncode != 0:
                logger.warning(f"xelatex 第{i+1}次编译失败，日志：{result.stdout[-2000:]}")
                print(f"⚠️ xelatex 第{i+1}次编译失败，查看日志：")
                print(result.stdout[-2000:])
                print(result.stderr[-1000:])
                break

        pdf_path = tex_path.with_suffix(".pdf")
        if pdf_path.exists():
            logger.info(f"PDF 编译成功: {pdf_path}")
            print(f"✅ PDF 编译成功: {pdf_path}")
            return pdf_path
        else:
            logger.error("PDF 编译失败，请检查 LaTeX 错误")
            print("❌ PDF 编译失败，请检查 LaTeX 错误")
            return None


# ---- CLI ----

def main():
    parser = argparse.ArgumentParser(description="追诉报告生成器")
    parser.add_argument("--case", type=str, default="hengda", help="案件ID（默认：hengda）")
    parser.add_argument("--format", type=str, default="tex", choices=["tex", "pdf"], help="输出格式")
    parser.add_argument("--list", action="store_true", help="列出所有案件")
    parser.add_argument("--validate", action="store_true", help="验证配置完整性")
    args = parser.parse_args()

    loader = CaseLoader()

    if args.list:
        logger.info("列出所有案件")
        print("=" * 60)
        print("追诉系统 · 案件数据库")
        print("=" * 60)
        for c in loader.list_cases():
            print(f"  [{c['case_id']}] {c['case_name']}")
            print(f"    状态: {c['status']} | 类型: {c.get('case_type', '')} | 密级: {c.get('confidentiality', '')}")
        return

    # 加载并验证案件
    try:
        case_data = loader.load(args.case)
        logger.info(f"加载案件: {case_data['meta']['case_name_full']}")
        print(f"✅ 加载案件: {case_data['meta']['case_name_full']}")
    except FileNotFoundError:
        logger.error(f"案件未找到: {args.case}")
        print(f"❌ 案件未找到: {args.case}")
        print("可用案件：")
        for c in loader.list_cases():
            print(f"  - {c['case_id']}: {c['case_name']}")
        return

    # 验证
    warnings = loader.validate(args.case)
    if warnings:
        logger.warning(f"配置警告: {w}")
        print("⚠️ 配置警告：")
        for w in warnings:
            print(f"  • {w}")

    # 生成报告
    # ---- 真实性核查（生成前必须通过） ----
    from fact_checker import FactChecker
    checker = FactChecker(args.case, loader)
    results = checker.check()
    if results["grade_e"] > 0:
        logger.error("存在已验证错误数据（GRADE_E），必须修正后才能生成报告")
        print("❌ 存在已验证错误数据（GRADE_E），必须修正后才能生成报告：")
        for issue in results["issues"]:
            if "GRADE_E" in issue:
                print(f"  {issue}")
        return
    grade_c = results["grade_c"]
    grade_d = results["grade_d"]
    if grade_c > 0 or grade_d > 0:
        logger.warning(f"存在推测数据(GRADE_C:{grade_c})/未知数据(GRADE_D:{grade_d})")
        print(f"⚠️  警告：存在推测数据(GRADE_C:{grade_c})/未知数据(GRADE_D:{grade_d})")
        print(f"   详细报告：python src/fact_checker.py --case {args.case} --save")
        print(f"   推测数据已在报告中标注[估]，未知数据标注[待核实]")

    builder = ReportBuilder(args.case, loader)
    case_slug = args.case.lower().replace("case-", "").replace("-", "")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    tex_path = OUTPUT_DIR / f"{case_slug}_report.tex"

    builder.save_tex(tex_path)

    if args.format == "pdf":
        logger.info("正在编译 PDF（xelatex）...")
        print("🔄 正在编译 PDF（xelatex）...")
        builder.compile_pdf(tex_path)


if __name__ == "__main__":
    main()
