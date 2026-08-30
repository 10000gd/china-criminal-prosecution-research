# 中国刑事追诉智能辅助系统

> **愿景：推动刑法高质量践行，服务全链条司法参与者**

面向检察官、刑辩律师、法学研究者及公众的法律辅助工具

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-green.svg)](https://www.python.org/)

---

## 🌟 核心功能

### 1. 量刑一致性分析
- **省级差异分析**：可视化各省量刑偏离度
- **罪名量刑统计**：均值/中位数/标准差/区间分布
- **个案偏离检测**：输入案件，输出偏离度报告
- **案例库**：249个案例，28种罪名

### 2. 辩护增强模块
- **辩护角度识别**：23种辩护类型自动识别
- **类案参考**：内置无罪/轻判典型案例库
- **辩护意见生成**：一键生成结构化辩护词

### 3. 案件对比
- 多案件并排对比分析
- 自动生成对比洞察和差异分析

### 4. 用户系统
- 用户注册/登录
- 收藏功能
- 搜索历史
- 个人中心

### 5. 管理后台
- 用户管理
- 操作日志
- 数据统计
- 数据备份/导出

---

## 🚀 快速开始

### 环境要求
- Python 3.11+
- 4GB+ RAM
- Linux/macOS/Windows

### 安装

```bash
# 克隆项目
git clone <repo>
cd prosecution_system

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS

# 安装依赖
pip install -r requirements.txt
```

### 启动

```bash
# 开发模式
python src/web_app.py

# 生产模式
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 'src.web_app:app'
```

访问 http://localhost:5000

### Docker部署

```bash
docker-compose up -d
```

---

## 📁 项目结构

```
prosecution_system/
├── src/
│   ├── web_app.py           # Flask主应用 (57路由)
│   ├── auth.py              # 用户认证
│   ├── database.py          # SQLite数据库
│   ├── security.py          # 安全模块(限流/验证/CSRF)
│   ├── admin.py             # 管理后台
│   ├── notifications.py     # WebSocket通知
│   ├── audit.py             # 审计日志
│   ├── data_export.py       # 数据导出
│   ├── advanced_analysis.py # 高级分析
│   ├── health.py            # 健康检查
│   ├── case_comparison.py   # 案件对比
│   ├── pdf_exporter.py      # PDF导出
│   ├── sentencing_consistency.py  # 量刑分析
│   ├── defense_enhancer.py  # 辩护增强
│   └── sentencing_cases.py  # 量刑案例库(249个)
├── templates/               # HTML模板
├── tests/                   # 测试用例(80个)
├── docker-compose.yml       # Docker编排
├── nginx.conf              # Nginx配置
└── requirements.txt
```

---

## 🔧 API参考

### Web路由

| 路由 | 功能 |
|------|------|
| `/` | 首页 |
| `/search` | 搜索 |
| `/compare` | 案件对比 |
| `/sentencing` | 量刑分析 |
| `/defense/<case_id>` | 辩护分析 |
| `/auth/login` | 登录 |
| `/auth/register` | 注册 |
| `/admin/` | 管理后台 |
| `/health` | 健康检查 |
| `/metrics` | 监控指标 |

### REST API

```bash
# 量刑API
GET  /api/sentencing/report
POST /api/sentencing/deviation

# 辩护API
POST /api/defense/analyze
POST /api/defense/opinion

# 案件API
GET  /api/compare
```

---

## 📊 数据统计

| 指标 | 数值 |
|------|------|
| 总提交 | 25个 |
| Python模块 | 37个 |
| 代码行数 | 16,655行 |
| 测试用例 | 80个 |
| Web路由 | 57个 |
| 量刑案例 | 249个 |
| 罪名种类 | 28种 |

---

## ⚠️ 免责声明

**本系统仅供辅助参考，不构成正式法律意见。**

---

## 📄 许可证

MIT License
