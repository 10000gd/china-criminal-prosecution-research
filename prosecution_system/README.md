# 中国刑事追诉智能辅助系统

> **愿景：推动刑法高质量践行，服务全链条司法参与者**
> 
> 面向检察官、刑辩律师、法学研究者及公众的法律辅助工具

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-green.svg)](https://www.python.org/)

---

## 🌟 核心功能

### 1. 法律智能检索
- **全文检索**：2,055部法律法规，402条刑法条文，186条司法解释
- **RAG增强检索**：BM25 + 倒排索引，78,240个知识块
- **罪名映射**：484个标准罪名→法条关联

### 2. 辩护增强模块（新增🆕）
- **辩护角度识别**：23种辩护类型自动识别
- **类案参考**：内置无罪/轻判典型案例库
- **辩护意见生成**：一键生成结构化辩护词
- **Web界面**：`/defense/<case_id>`

### 3. 量刑一致性分析（新增🆕）
- **省级差异分析**：可视化各省量刑偏离度
- **罪名量刑统计**：均值/中位数/标准差/区间分布
- **个案偏离检测**：输入案件，输出偏离度报告
- **Web界面**：`/sentencing`

### 4. 案件管理
- YAML格式案件配置
- 全文检索案件库
- 置信度评估
- 法律冲突检测
- LaTeX报告生成

---

## 🚀 快速开始

### 环境要求
- Python 3.11+
- 4GB+ RAM
- Linux/macOS/Windows

### 安装

```bash
# 克隆项目
git clone https://github.com/your-repo/prosecution_system.git
cd prosecution_system

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt
```

### 启动 Web 服务

```bash
# 开发模式
python src/web_app.py

# 生产模式（推荐）
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 'src.web_app:app'
```

访问 http://localhost:5000

### Docker 部署

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止
docker-compose down
```

---

## 💻 命令行工具

```bash
# 法律检索
python cli.py search "正当防卫"
python cli.py search "盗窃罪 入户" --limit 20

# 案件管理
python cli.py cases                    # 列出所有案件
python cli.py case CASE-001           # 查看案件详情

# 辩护分析
python cli.py analyze --case CASE-001              # 分析案件辩护角度
python cli.py defense-search --defense-type 正当防卫  # 检索辩护案例
python cli.py defense-opinion --case-id CASE-001  # 生成辩护意见

# 量刑分析
python cli.py sentencing                          # 量刑统计总览
python cli.py sentencing --crime 盗窃罪           # 特定罪名统计
python cli.py sentencing-deviation --crime 盗窃罪 --sentence 2.5 --zishou  # 偏离度检测

# 法律查询
python cli.py lookup --article 第20条             # 查询条文
python cli.py lookup --crime 盗窃罪               # 查询罪名相关法条

# 输出JSON格式
python cli.py search "正当防卫" --format json
```

---

## 📁 项目结构

```
prosecution_system/
├── src/
│   ├── legal_db.py              # 法律数据库统一接口
│   ├── china_law_db.py         # 全量法律库（2,055部）
│   ├── law_rag.py              # BM25检索增强
│   ├── case_loader.py           # 案件加载器
│   ├── confidence_scorer.py    # 置信度评估
│   ├── threshold_db.py          # 入罪门槛（各省标准）
│   ├── law_conflict_detector.py # 法律冲突检测
│   ├── fact_checker.py          # 数据真实性核查
│   ├── build_report.py          # LaTeX报告生成
│   ├── stats_aggregator.py      # 统计仪表盘
│   │                           # ─── 新增模块 ───
│   ├── defense_enhancer.py      # 辩护角度识别引擎
│   ├── defense_case_db.py       # 辩护案例数据库
│   ├── defense_opinion_generator.py  # 辩护意见生成器
│   ├── defense_report_builder.py     # 辩护报告构建器
│   └── sentencing_consistency.py     # 量刑一致性分析
│   │
│   └── web_app.py              # Flask Web应用
│
├── cases/
│   └── legaldb/
│       ├── laws/                # 2,055部法律原文
│       ├── 刑法条文.csv         # 402条结构化法条
│       ├── 刑法司法解释.csv     # 186条司法解释
│       ├── 标准案由表.txt       # 484个罪名
│       └── .rag_cache/         # RAG索引
│
├── templates/                  # Web页面模板
│   ├── index.html
│   ├── defense.html            # 🆕 辩护分析页
│   └── sentencing.html         # 🆕 量刑分析页
│
├── tests/                      # 测试套件
├── cli.py                      # 🆕 命令行工具
├── Dockerfile                  # 🆕 Docker配置
├── docker-compose.yml          # 🆕 Docker编排
└── requirements.txt
```

---

## 🔧 API 参考

### Web 界面

| 路由 | 功能 |
|------|------|
| `/` | 案件列表首页 |
| `/case/<case_id>` | 案件详情页 |
| `/search` | 法律检索页 |
| `/stats` | 统计仪表盘 |
| `/defense/<case_id>` | 🆕 辩护分析页 |
| `/sentencing` | 🆕 量刑一致性总览 |
| `/sentencing/<crime>` | 🆕 特定罪名分析 |

### REST API

```bash
# 案件API
GET /api/cases
GET /api/case/<case_id>
GET /api/case/<case_id>/charges

# 辩护API (🆕)
POST /api/defense/analyze
POST /api/defense/opinion
POST /api/defense/report
GET  /api/defense/search?crime=盗窃罪&defense_type=正当防卫

# 量刑API (🆕)
GET  /api/sentencing/report
POST /api/sentencing/deviation
GET  /api/sentencing/provincial

# 统计API
GET /api/stats/hallucination
GET /api/stats/provincial-diffs
GET /api/stats/company-geo
```

---

## 🎯 使用场景

### 检察官
- 快速检索相关法条和司法解释
- 生成量刑建议参考报告
- 检测法律冲突
- 分析辩护角度，提前准备应对

### 刑辩律师
- 识别潜在辩护角度
- 检索无罪/轻判类案
- 生成辩护意见草稿
- 分析量刑偏离度

### 法学研究者
- 分析量刑一致性
- 研究地区差异
- 追踪法律演变
- 辅助学术研究

### 公众
- 了解法律知识
- 查询相关法条
- 理解量刑标准

---

## ⚠️ 免责声明

**本系统仅供辅助参考，不构成正式法律意见。**

- 所有分析结果应经过专业人士审核
- 法律适用需结合具体案件情况
- 系统不保证检索结果的完整性和准确性

---

## 📊 数据质量

| 数据类型 | 状态 | 说明 |
|---------|------|------|
| 刑法条文 | 🟢 优秀 | 402条，完全正确 |
| 司法解释 | 🟡 良好 | 186条，时效性需关注 |
| 全量法律库 | 🟡 可用 | 2,055部，7.3%日期损坏 |
| 地方性法规 | 🔴 不可用 | 数据损坏，待修复 |
| RAG索引 | 🟢 良好 | 78,240块 |

详见：[docs/DATA_QUALITY.md](docs/DATA_QUALITY.md)

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 🙏 致谢

- 中国法律开放数据
- 最高人民法院司法解释
- 所有开源贡献者
