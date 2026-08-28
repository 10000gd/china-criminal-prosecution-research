# 🚀 快速入门指南

## 5分钟快速启动

### 方式1: Docker (推荐)

```bash
# 克隆项目
git clone <repo-url>
cd prosecution_system

# 一键启动
docker-compose up -d

# 访问 http://localhost:5000
# 登录: admin / admin123
```

### 方式2: 本地运行

```bash
# 克隆项目
git clone <repo-url>
cd prosecution_system

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 生成测试数据 (可选)
python seed_data.py

# 启动
python src/web_app.py

# 访问 http://localhost:5000
# 登录: admin / admin123
```

### 方式3: 一键脚本

```bash
./start.sh dev
```

---

## 默认账号

| 账号 | 密码 | 角色 |
|------|------|------|
| admin | admin123 | 管理员 |
| prosecutor1 | prosec123 | 用户 |
| lawyer1 | lawyer123 | 用户 |
| researcher1 | research123 | 用户 |

---

## CLI工具

```bash
# 统计信息
python cli_tools.py stats

# 搜索案例
python cli_tools.py search 盗窃

# 查找相似案例
python cli_tools.py similar TH-101

# 检测异常
python cli_tools.py anomaly

# 导出数据
python cli_tools.py export --format csv
```

---

## API端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/metrics` | GET | Prometheus指标 |
| `/api/sentencing/analyze` | POST | 量刑分析 |
| `/api/compare` | POST | 案件对比 |
| `/api/defense/analyze` | POST | 辩护分析 |

---

## 项目结构

```
prosecution_system/
├── src/              # Python源码
├── templates/         # HTML模板
├── tests/            # 测试用例
├── data/             # 数据库
├── docker-compose.yml # Docker配置
├── start.sh          # 启动脚本
└── Makefile         # 管理命令
```

---

## 常用命令

```bash
# 开发模式
make dev

# 生产模式
make prod

# 运行测试
make test

# 备份数据库
make backup

# 查看日志
make logs
```
