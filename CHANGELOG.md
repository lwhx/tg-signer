# Changelog

## 1.1.0 — 2026-09-25

- 发布可复现的单容器 Docker 部署包，支持 Linux amd64 VPS 离线导入镜像后启动。
- 签到任务列表支持 20/50/100 条分页、跨页搜索、排序和删除后的页码修正。
- 搜索覆盖任务名称、Bot 用户名、保存的目标名称和数字或字符串 Chat ID。
- 保留 Telegram 登录、签到、Automation、Monitor、实时日志、配置导入导出和通知功能。
- 补充源码部署、备份恢复、发布包安装和验证文档。

## 1.0.0 — 2026-09-19

- 首次发布 tg-signer Dashboard 单容器控制台。
- 提供 Next.js 静态前端、FastAPI API、SQLite WAL 数据库和加密凭据存储。
- 集成固定版本的 `amchii/tg-signer` 上游源码，并提供 Docker Compose 部署。
