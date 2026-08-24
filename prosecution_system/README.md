# 中国刑事追诉智能辅助系统

> **定位：面向检察官、刑辩律师及法学研究者的法律辅助检索工具**
> **所有输出仅供辅助参考，不构成正式法律意见。**

---

## 系统架构

```
prosecution_system/
├── src/
│   ├── legal_db.py       # 法律数据库统一接口
│   ├── china_law_db.py   # 全量法律库加载器（2,055部）
│   ├── law_rag.py        # 检索增强（BM25 + 倒排索引）
│   ├── case_loader.py    # 案件材料加载与解析
│   ├── fact_checker.py   # 案件数据真实性核查（≠罪名推理）
│   ├── build_report.py   # 报告生成（LaTeX）
│   └── web_app.py        # Web界面（Flask）
├── cases/
│   ├── legaldb/
│   │   ├── laws/                    # 2,055部法律原始文本
│   │   ├── laws_full_index.json     # 法律元数据索引
│   │   ├── 刑法条文.csv             # 402条结构化法条
│   │   ├── 刑法司法解释.csv         # 186条司法解释
│   │   ├── 标准案由表.txt           # 484个罪名
│   │   ├── 章节案由表.jsonl         # 罪名按章节分类
│   │   ├── local_regulations_index.json  # 775条地方性法规（⚠️见数据警告）
│   │   └── .rag_cache/              # RAG索引（78,240块）
│   └── *.yaml                       # 案件配置
└── docs/
    └── DATA_QUALITY.md              # 数据质量完整报告
```

---

## 核心模块说明

### LegalDB（统一接口层）

```python
from src.legal_db import LegalDB
db = LegalDB()

db.get_article(232)              # 按条文号查刑法
db.search_case_types('盗窃')      # 罪名→法条映射
db.list_laws_by_category('司法解释')  # 按分类浏览
db.fulltext_search('正当防卫')     # 关键词全文检索
db.rag_retrieve('入户盗窃转化抢劫')  # RAG检索
db.search_local_regulations('交通')  # ⚠️ 地方性法规（数据不可用）
```

### ChinaLawDatabase（全量法律库）

```python
from src.china_law_db import ChinaLawDatabase
db = ChinaLawDatabase()
db.load()
db.search('电信诈骗')
db.get_by_name('中华人民共和国刑法')
db.get_stats()
```

### LawRAG（检索增强层）

- **技术路线**：jieba 中文分词 + BM25 排序 + 倒排索引
- **索引规模**：78,240 个文本块，765,482 个索引词
- **局限性**：纯关键词检索，无向量语义能力；语义泛化场景下可能漏检
- **检索延迟**：< 50ms（P95，本地环境）

### CaseLoader（案件材料管理）

加载、解析、验证案件 YAML 配置文件，支持全文检索。

### FactChecker（数据真实性核查）

⚠️ **重要说明**：本模块的功能是**核查案件材料数据来源的真实性**（验证判决书、证据链、当事人信息的可靠性），**不是**"事实→罪名"匹配或法律推理。如需罪名推荐，使用 `LegalDB.search_case_types()`。

### BuildReport（报告生成）

将分析结果输出为 LaTeX 格式的结构化报告。

---

## 数据质量警告

### 🔴 地方性法规（UNUSABLE - 数据损坏）

| 问题 | 详情 |
|------|------|
| content 字段污染 | 源数据库将司法解释文本错误写入所有 775 条 content 字段 |
| description 字段无实质内容 | 均为模板句"《XXX法》是YYY人大的地方性法规" |
| 影响范围 | 全部 775 条，**数据不可用于任何实质性法律检索** |
| 解决方案 | 从 flk.npc.gov.cn 专项采集完整正文 |

详见：`cases/legaldb/local_regulations_index.json → data_quality`

### 🟡 全量法律库（可用，7.3% 日期损坏）

- 日期有效率：92.7%（1,905/2,055 条）
- 损坏原因：源文件元数据头中部分法律被标注为 `ff808081` 等乱码（非程序错误，为源数据问题）
- 影响：这些文件无法按时间筛选，但不影响法条内容检索

### 🟢 刑法条文（完全正确）

- 402 条（总则 107 + 分则 295）
- 含修正案一至十二（2024.3.1 施行版）
- 司法解释：186 条，核心罪名全覆盖

### 🟡 司法解释时效性

- 最新收录至 2025 年 11 期
- 2025 年以后的司法解释可能存在滞后

---

## 已知局限

| 类别 | 局限 | 优先级 |
|------|------|--------|
| 检索能力 | 纯 BM25，无向量语义检索 | 高 |
| 数据 | 地方性法规正文全文缺失（数据损坏） | 高 |
| 数据 | 司法解释时效性滞后 | 中 |
| 法律推理 | 无法律冲突检测 | 中 |
| 法律推理 | 罪名匹配基于关键词，不处理主观方面 | 中 |
| 案例 | 无裁判文书库 | 高 |
| 幻觉风险 | 无置信度/幻觉检测机制 | 高 |
| 工程 | 无单元测试、无自动更新 | 中 |
| 部署 | Flask 内置服务器（非生产级） | 低 |

---

## 版本信息

```
版本: v2.0
最新 commit: 9a9853f (2026-08-24)
依赖: Python 3.12, jieba, pandas, flask, sqlite3
```
