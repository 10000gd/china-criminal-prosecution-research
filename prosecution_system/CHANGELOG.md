# 更新日志

## v2.0.0 (2026-08-30)

### 新功能
- ✅ 管理后台 - 用户/日志/统计/备份
- ✅ WebSocket通知 - 实时推送
- ✅ 审计日志 - 完整操作追踪
- ✅ 数据导出 - CSV/JSON/报告
- ✅ API限流 - 令牌桶算法
- ✅ 高级分析 - 相似度/趋势/异常检测
- ✅ Docker部署 - Docker Compose + Nginx
- ✅ 健康检查 - /health端点
- ✅ 监控指标 - Prometheus格式
- ✅ API文档 - Swagger/OpenAPI
- ✅ CLI工具 - 命令行操作
- ✅ 种子数据 - 一键生成测试数据
- ✅ 快速入门 - QUICKSTART指南

### 案例库
- 249个量刑案例
- 28种罪名类型

### 测试
- 80个测试用例全部通过
- CI/CD自动化

---

## v1.0.0 (2026-08-22)

### 初始功能
- 用户认证系统
- 案件搜索与浏览
- 量刑一致性分析
- 辩护增强模块
- 案件对比功能
- PDF导出
- 移动端适配

## v2.1.0 (2026-09-07)

### 新功能
- **联合案件分析 API** `/api/case-analyze` (POST + GET)
  - 一键输出：入罪判定 + 量刑预测 + 量刑偏离 + 类案推送 + 辩护分析 + 法律依据
- **PDF 辩护意见书导出**（基于 fpdf2 + NotoSansCJK 中文支持）
  - `/api/defense/report?format=pdf`
  - `/api/case-analyze/<case_id>/pdf`

### Bug 修复
- CaseLoader.load() 支持传入 list_cases() 返回的 dict 对象
- LawRAG.search() 返回值增加 title 字段（web UI 显示兼容）
- DefenseAngle 字段映射（description → legal_references/evidence_points）
- DefenseReportBuilder output_dir 默认路径改为基于 __file__ 绝对路径

### 管理后台
- **案件批量导入** `/admin/case-import` — 上传 CSV/Excel 批量导入案件，含模板下载
