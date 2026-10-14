# Docker Compose 快速部署

推荐直接使用仓库**根目录**的 [docker-compose.yml](../docker-compose.yml)，无需创建 `start.sh`，也无需本地构建镜像。Compose 默认只启动 WebUI，`automation` 工作进程可按需启用。

## 第一次部署

```bash
git clone https://github.com/lwhx/tg-signer.git
cd tg-signer
cp .env.example .env
openssl rand -hex 24
```

把生成的随机字符串填入 `.env` 中的 `TG_SIGNER_GUI_AUTHCODE`（不要直接使用示例值）。

```bash
mkdir -p data
docker compose pull
docker compose up -d
docker compose ps
```

默认通过宿主机 `127.0.0.1:8080` 访问 WebUI。若是 VPS，可在宝塔反向代理中将已设置 HTTPS 的域名代理到 `http://127.0.0.1:8080`。如需直接通过服务器 IP 访问，可设置 `WEBUI_BIND_IP=0.0.0.0`，但必须限制防火墙访问并使用安全的认证/HTTPS；不建议直接将 WebUI 暴露公网。

如需使用不同端口，修改 `.env` 中的 `WEBUI_PORT`，然后 `docker compose up -d`。

## Telegram 登录与规则

```bash
docker compose exec webui tg-signer login
docker compose exec webui tg-signer automation init my_auto
```

创建任务后，可以在 WebUI 的「Automation · 转发规则」修改规则；保存后手动启动工作进程。

编辑 `.env`：

```dotenv
TG_SIGNER_AUTOMATION_TASK=my_auto
```

启动 WebUI 和对应的 Automation 任务：

```bash
docker compose --profile automation up -d
docker compose logs -f automation
```

**注意：WebUI 是配置界面，并不负责自动执行消息监听。** 只有在任务已创建且 Automation 工作进程正在运行时，才会持续监听与转发。修改规则后，执行 `docker compose restart automation` 才能让运行中的任务重新加载配置。

当前示例的可选 Automation 容器一次运行一个任务。多个任务的进程/账号隔离需要单独配置，**不要让多个工作进程同时访问同一个 Telegram Session SQLite 文件**。

## 数据持久化与升级

两个服务共享宿主机 `./data`，映射到容器内的 `/opt/tg-signer`。该目录包含 Telegram 登录 Session、`.signer` 自动化配置、监控记录和消息转发 SQLite 去重数据。根目录 `.env` 存有 WebUI 授权码；这些文件都不应上传到公开仓库。

更新镜像：

```bash
docker compose pull
docker compose --profile automation pull
docker compose --profile automation up -d
```

只有运行 WebUI 时可以直接使用 `docker compose up -d`，无需启用自动化 profile。不要通过 `docker compose down -v` 删除匿名/命名卷，也不要手动删除 `data/` 目录。

查看状态与日志：

```bash
docker compose ps
docker compose logs --tail=100 webui
docker compose --profile automation logs --tail=100 automation
```

## 旧 Compose 的区别

`docker/docker-compose.yml` 是上游保留的旧版 CLI 示例，要求额外准备 `start.sh`，而且没有 WebUI 端口配置。

**新部署请用根目录 `docker-compose.yml`。** 已经在使用旧版目录和挂载的用户，需要先备份 Session 和 `.signer`，再调整新容器的 `./data` 位置，避免看起来像丢失登录状态。
