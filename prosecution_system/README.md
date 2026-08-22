# 追诉系统 · 多案扩展架构

全链条刑事追诉研究平台，支持多案件参数化报告生成、实时跟踪和 Web 界面。

## 目录结构

```
prosecution_system/
├── cases/                    # 案件数据库（YAML配置）
│   ├── hengda.yaml          # 恒大案（样例）
│   └── _template.yaml       # 新案模板
├── templates/                # Flask HTML模板
├── src/
│   ├── case_loader.py       # 案件加载器
│   ├── build_report.py      # 报告生成器（LaTeX/PDF）
│   ├── wenshu_updater.py    # 判决文书网实时更新
│   └── web_app.py           # Flask Web应用
├── data/                     # 跟踪数据
├── output/                   # 生成的报告
└── README.md
```

## 快速开始

### 1. 案件加载
```bash
python src/case_loader.py --list       # 列出所有案件
python src/case_loader.py --case hengda  # 加载指定案件
python src/case_loader.py --validate      # 验证配置完整性
```

### 2. 生成报告
```bash
# 生成 LaTeX 源文件
python src/build_report.py --case hengda

# 生成 PDF 报告
python src/build_report.py --case hengda --format pdf
```

### 3. 启动 Web UI
```bash
python src/web_app.py
# 访问 http://localhost:5000
```

### 4. 案件跟踪
```bash
# 添加跟踪
python src/wenshu_updater.py --add CASE-001 --case-num "(2026)粤03刑初XXX号" --court "深圳市中级人民法院"

# 记录事件
python src/wenshu_updater.py --log CASE-001 "二审开庭" "新华社"

# 检查更新（需 WENSHU_TOKEN）
export WENSHU_TOKEN=your_token_here
python src/wenshu_updater.py --check-updates
```

## 添加新案件

1. 复制模板：
   ```bash
   cp cases/_template.yaml cases/my_case.yaml
   ```

2. 修改 `cases/my_case.yaml` 中的案件参数

3. 验证：
   ```bash
   python src/case_loader.py --case my_case --validate
   ```

4. 生成报告：
   ```bash
   python src/build_report.py --case my_case --format pdf
   ```

## 架构设计

### 多案扩展原理

**关键洞察**：所有报告的结构相同，变的只是内容。

- **案件数据** → YAML 配置文件（`cases/*.yaml`）
- **报告框架** → 参数化 `ReportBuilder`（`src/build_report.py`）
- **案件加载** → `CaseLoader`（`src/case_loader.py`）
- **模板引擎** → 直接拼接（无需 Jinja2，保持 LaTeX 控制）

```
案件YAML → CaseLoader → ReportBuilder → LaTeX → PDF
                            ↓
                    多案共用同一框架
```

### 实时更新方案

| 方案 | 条件 | 可靠性 |
|------|------|--------|
| Wenshu API | 需向 court.gov.cn 申请 Token | 高（需机构认证） |
| Web Scraper | 无需 Token | 中（反爬限制） |
| Manual Tracker | 无需任何配置 | 100%可用 |

推荐：使用 Manual Tracker 记录事件 + 申请 Wenshu API Token 进行自动更新。

## Web UI 功能

- 📋 案件列表（按状态过滤）
- 🔍 全局搜索（案件名/案号/当事人）
- 📄 报告生成（LaTeX/PDF）
- 📡 案件跟踪（状态变更历史）
- 📝 手动记录事件

## 数据来源

所有信息严格来自：
- 新华社等官方媒体
- 最高人民法院官网
- 中国证监会官网
- 国家金融监督管理总局官网
- 中国裁判文书网（wenshu.court.gov.cn）

**零幻觉引用保证**：所有数字精确、无模糊表述、所有来源可溯源验证。
