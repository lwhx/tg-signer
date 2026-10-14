# Docker Compose 快速部署

推荐直接使用仓库**根目录**的 [docker-compose.yml](../docker-compose.yml)，无需创建 `start.sh`，也无需本地构建镜像。Compose 默认只启动 WebUI，`automation` 工作进程可按需启用。默认启用基础容器安全限制，`read_only` 可通过可选覆盖文件单独开启。

## 第一次部署

```bash
git clone https://github.com/lwhx/tg-signer.git
cd tg-signer
cp .env.example .env
openssl rand -hex 24
```

把生成的随机字符串填入 `.env` 中的 `TG_SIGNER_GUI_AUTHCODE`（不要直接使用示例值）。建议执行 `chmod 600 .env` 限制其他本机用户读取授权码。

WebUI 默认使用该随机 Auth Code 作为稳定的 NiceGUI cookie 签名密钥，避免重启后反复要求登录。若希望将登录授权码与会话签名密钥分开，额外设置 `TG_SIGNER_GUI_STORAGE_SECRET`（请独立生成随机值）；两者都不要写进 Git。

```bash
mkdir -p data
docker compose pull
docker compose up -d
docker compose ps
```

默认通过宿主机 `127.0.0.1:8080` 访问 WebUI。若是 VPS，可在宝塔反向代理中将已设置 HTTPS 的域名代理到 `http://127.0.0.1:8080`。如需直接通过服务器 IP 访问，可设置 `WEBUI_BIND_IP=0.0.0.0`，但必须限制防火墙访问并使用安全的认证/HTTPS；不建议直接将 WebUI 暴露公网。

如需使用不同端口，修改 `.env` 中的 `WEBUI_PORT`，然后 `docker compose up -d`。

## 容器安全配置（默认启用）

仓库根目录 Compose 保留 `127.0.0.1` 绑定、明确的 WebUI 授权码、数据目录挂载和日志轮转，并对 WebUI 与 Automation 工作进程统一设置：

| Docker Compose 参数 | 作用 |
| --- | --- |
| `init: true` | 处理子进程及容器停止信号 |
| `security_opt: [no-new-privileges:true]` | 禁止进程在运行时获取额外权限 |
| `cap_drop: [ALL]` | 移除容器默认 Linux capabilities |
| `tmpfs: /tmp:size=128m,mode=1777` | 为临时文件提供容量受限的内存目录 |
| `stop_grace_period: 40s` | 给 Telegram/SQLite 提供退出清理时间 |
| `logging` | 日志单文件最多 10 MB，保留 3 份 |

上述加固不会更改你已发布的 `ghcr.io/lwhx/tg-signer` 镜像，也不在服务器本地重新构建。

**数据目录所有权（重要）：** 当前镜像默认以容器 UID 0 运行，但由于 `cap_drop: ALL`，它不再能越权写入其他 UID 所拥有、权限为 0755 的目录。新部署时应确保宿主机 `./data` 对容器 UID 0 可写。在常规 rootful Docker 的 root 用户部署中，可使用：

```bash
mkdir -p data
sudo chown root:root data
sudo chmod 700 data
```

上述命令仅为**新建空目录**示例。已有 Telegram Session、`.signer` 或其他数据时，**先备份并检查文件所有者**，不要不加核对地递归修改权限或删除数据。若使用 rootless Docker / userns-remap，容器 UID 0 对应的宿主机 UID 可能不同，须按实际用户映射调整，而不是直接照搬 root:root。若出现 `PermissionError: logs`，优先检查宿主机目录权限及用户映射。

### 额外开启只读根文件系统

考虑到 NiceGUI、Telegram Session 和 SQLite 的运行时写入需求，默认不强制只读根目录；可以通过 [docker-compose.readonly.yml](../docker-compose.readonly.yml) **显式启用**：

```bash
# 首次启用前先备份 ./data 和 .env
docker compose -f docker-compose.yml -f docker-compose.readonly.yml \
  config --quiet
docker compose -f docker-compose.yml -f docker-compose.readonly.yml \
  up -d
docker compose -f docker-compose.yml -f docker-compose.readonly.yml \
  ps
```

启用该模式后，容器内的根文件系统变成只读，但 `./data:/opt/tg-signer` 仍然可写，`/tmp` 仍然是可写的 tmpfs。覆盖文件还会禁止生成 Python 字节码，并将常见缓存写入位置指向 `/tmp/.cache`。

如果已启用 Automation 工作进程，请在上面两条 `up/ps` 命令中追加 `--profile automation`（位于 `-f` 参数之后）。

**如果某个第三方库因为根文件系统只读而无法启动**，可先回退到基础 Compose：

```bash
docker compose -f docker-compose.yml up -d --force-recreate
docker compose logs --tail=100 webui
```

以上仅验证镜像中 WebUI 的启动及数据目录可写，不代表所有 Telegram 工作流及第三方插件都支持只读模式。生产环境建议先让基础配置稳定运行，再开启只读模式。

### 与原 Dashboard Compose 的区别

- 原 `tg-signer-dashboard:local` 要求 `build: .`，本仓库直接从 GHCR 拉取已发布镜像，**不需要 build**。
- 原 Dashboard 容器使用 8999 端口；本仓库 WebUI 内部端口是 **8080**。若你希望宿主机沿用原端口，在 `.env` 设置 `WEBUI_PORT=8999`，即映射为 `127.0.0.1:8999:8080`。
- `ADMIN_PASSWORD` 和 `COOKIE_SECURE` 是原 Dashboard 的配置项，不能直接应用到本项目。请使用 `TG_SIGNER_GUI_AUTHCODE`，并通过宝塔 HTTPS 反向代理确保浏览器安全访问。
- 默认没有改变基础镜像的 root 运行身份。若需要非 root 运行，必须另外检查 Session 目录权限和第三方库兼容性。

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
