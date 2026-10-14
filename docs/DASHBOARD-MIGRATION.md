# 从 dongbo501/TG-SIGNER Dashboard 迁移

本仓库的**运行基础是原 Dashboard**，而不是原 amchii 项目的 NiceGUI。后端 FastAPI、前端 Next.js、SQLite 表结构、面板密码、账号加密密钥和任务调度均基于 [dongbo501/TG-SIGNER](https://github.com/dongbo501/TG-SIGNER)。在执行器层接入了 lwhx 维护的 `relay_message` 通用转发 Handler，并增加对应前端设置和正则测试工具。

## 部署前检查

1. **先在当前原 Dashboard 部署目录完成备份**：停止 Dashboard 容器（避免备份时 SQLite WAL 仍在写入），复制完整的 `data/` 以及配置文件。
2. 至少确认备份包含 `data/dashboard.sqlite3`、`data/encryption.key`、`data/jwt.key`、`data/upstream/` 和其他原有文件；若存在 WAL/SHM 文件，不要只拷贝单个数据库文件。
3. 不要删除原 `data/`，不要把账号 Session、Cookie、原始数据库上传至公开仓库。
4. 若从原来的 `ghcr.io/lwhx/tg-signer:latest-webui`（NiceGUI）切换，此旧容器请先停止；不能让多个 Telegram 工作进程同时消费相同任务。
5. 检查容器内路径：**原 Dashboard 与新 Dashboard 都是 `./data:/data`**。NiceGUI 版本使用的 `/opt/tg-signer` 数据格式不应当作 Dashboard 数据库。

安全备份示例（在原 Dashboard 的 Compose 目录）：

```bash
docker compose stop dashboard
mkdir -p backups
tar -czf "backups/tg-dashboard-before-migration-$(date +%Y%m%d-%H%M%S).tar.gz" data
```

备份包可能包含账号 Session、加密密钥和任务数据，建议仅保存在你信任的本机存储并限制访问权限。

## 切换到自己的 GHCR Dashboard 镜像

部署仍在**原来的宿主机目录**，以确保 `./data` 指向旧文件夹：

```bash
# 备份原 docker-compose.yml 后，替换为本仓库根目录的版本
cp .env.example .env  # 若原有 .env，请先备份，勿覆盖
```

`.env` 例子：

```dotenv
WEBUI_BIND_IP=127.0.0.1
WEBUI_PORT=8999
COOKIE_SECURE=true
TZ=Asia/Shanghai
ADMIN_PASSWORD=
```

`COOKIE_SECURE=true` 需要从**HTTPS 域名**访问；如果只通过 HTTP 测试，设为 `false`，并限制仅本机访问。

如果 `data/dashboard.sqlite3` 中已有管理员密码，后端沿用数据库中保存的密码哈希，`ADMIN_PASSWORD` **仅在首次初始化时生效**。如果 `dashboard.sqlite3` 不存在，留空会在 `data/initial-password.txt` 生成新密码；请及时妥善保存。

```bash
docker compose pull dashboard
docker compose up -d dashboard
docker compose ps
docker compose logs --tail=100 dashboard
```

请先在网页检查旧 Telegram 账号、签到任务、自动化规则、监控任务和历史记录，再尝试启动新的通用转发任务。若账号或密码异常，应立即停止新容器、保留数据备份并回滚，不要随意重置 `encryption.key`。

## 增强的通用消息转发

进入原 Dashboard 的「自动化规则」创建或编辑任务，使用：

- **触发器**：收到消息时；可以填写多个来源频道/群组或数字 Chat ID
- **消息筛选**：全部、包含、精确、正则；提供正则测试预览
- **执行动作 → 通用多目标消息转发**：对每个目标选择 `forward` / `copy` / `text` / `extract` / `template`
- **去重**：`message` / `content` / `off`，独立于每个目标设置
- **115 Bot**：使用「115 链接转存 Bot 示例」模板，仅转发指定链接给已有 Bot，不重复实现网盘 API

转发状态保存在 `data/upstream/message_relay.sqlite3`。仅表明 Telegram 发送结果，**并不代表外部 Bot 完成转存**。真正需要消息监听时必须启用 Automation 任务，而不只是打开 Dashboard。

## 回滚

若新版本出现兼容问题，先停止新 Dashboard 容器，将 Compose 镜像临时改回原作者的已知可用版本；如果程序曾修改数据库，再使用停机时创建的备份恢复**整个** `data/`（不仅是 SQLite 文件）。两版本不得同时写入同一数据库或 Session。不要在生产数据上直接验证结构迁移。

## GitHub 分支与历史

重建前的旧 NiceGUI + CLI 代码完整保存在本仓库的 `archive/pre-dashboard-rebuild-20261014` 分支。重建后仓库 `main` 将以原 Dashboard 为基础，Docker 镜像另行发布为 `ghcr.io/lwhx/tg-signer:latest-dashboard`，不会覆盖旧 `latest` 镜像标签。
