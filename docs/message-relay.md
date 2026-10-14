# Telegram Message Relay / 通用消息监控与转发

这是 lwhx/tg-signer 的通用 Telegram 消息监控、过滤和转发功能。它不依赖任何网盘服务，也不要求目标必须是 Bot。115 转存是其中一个可选示例。

## 能做什么

- 监听指定频道、群组和私聊（使用原有 automation 的 message trigger）。
- 使用 all / exact / contains / regex 过滤；可以限定来源频道及用户。
- 一个规则将匹配消息投递给多个目标，每个目标选择不同的处理模式。
- 使用 SQLite 保存成功投递、失败、并发占用和去重状态。
- 转发的目标可以是个人、群、频道或 Bot，前提是已登录的 Telegram 账户具有相关权限。

**不实现 115 网盘上传/转存。对 Telegram Bot 发送消息成功不意味着 Bot 已成功处理消息。**

## 安装与启动

安装本仓库开发版本：

```bash
pip install -U "lwhx-tg-signer @ git+https://github.com/lwhx/tg-signer.git"
tg-signer login
tg-signer automation init message_relay
```

将 `examples/message_relay_basic.json` 复制到默认工作目录中的 `.signer/automations/message_relay/config.json`，把示例里的 SOURCE / ARCHIVE / BOT 用户名换成实际 Chat ID 或 @username。

```bash
tg-signer automation validate message_relay
tg-signer automation run message_relay
```

Docker 使用本仓库镜像 `ghcr.io/lwhx/tg-signer`，镜像需要先在本仓库 GitHub Actions 构建并发布。工作目录和 Telegram Session 必须挂载持久化存储。

## 通用 Handler：relay_message

`handlers` 中添加：

```json
{
  "handler": "relay_message",
  "params": {
    "ignore_self": true,
    "targets": [
      {
        "chat_id": "@ARCHIVE",
        "mode": "forward",
        "dedup": "message"
      },
      {
        "chat_id": "@BACKUP",
        "mode": "copy",
        "dedup": "message"
      },
      {
        "chat_id": "@LINK_BOT",
        "mode": "extract",
        "pattern": "(https?://[^\\s]+)",
        "group": 1,
        "all_matches": true,
        "dedup": "content"
      }
    ]
  }
}
```

来源聊天室由外层规则的 `triggers[*].params.chat_ids` 控制；消息匹配规则由 `filters.text_rule`、`filters.text_value` 和 `ignore_case` 控制。已有 automation 消息监听和编辑消息监听继续保留。

### 转发模式

| mode | 行为 | 适合 |
| --- | --- | --- |
| `forward` | 原生转发 Telegram 消息，通常保留原始来源信息 | 频道镜像、消息归档 |
| `copy` | 使用 Telegram copy_message 复制消息，不显示普通转发来源 | 无来源标记的频道备份 |
| `text` | 发送纯文本或媒体 caption；不发送媒体本体 | 普通文本转发 |
| `extract` | 正则提取一个捕获组后发送纯文本 | 链接、验证码、订单号、关键词 |
| `template` | 格式化文本重新发送 | 消息通知和标准化摘要 |

- `extract` 必须提供 `pattern`，`group` 可以是数字或命名组；`all_matches` 为 true 时最多处理 20 个匹配结果。
- `template` 必须提供 `template`，支持 `{text}`、`{chat_id}`、`{message_id}`、`{rule_id}`、`{sender_id}` 以及该规则 vars；如果指定 `pattern`，还可引用 `{match}`、`{group1}`、命名捕获组。
- `forward` / `copy` 包含附件、视频等消息；`text` / `extract` / `template` 只处理文字 / caption。
- 单个 Handler 支持 1 到 25 个目标，所有目标依次处理；某一目标失败不影响其他目标继续尝试。
- 默认跳过已登录账户自己发出的消息，并拒绝来源 ID 与目标 ID 完全相同的直接循环。用户名与数字 ID 指向同一会话的情况需自行避免。
- 受 Telegram 原群组权限、消息保护策略和 Bot 私聊启动状态等限制，目标必须有权接收相应内容。

### 去重与失败处理

每个目标可设置 `dedup`：

- `message`（默认）：按规则 ID + 来源 chat_id + message_id + 处理模式 + 提取结果序号防重。编辑后的同一消息默认不会重复发送同一目标。
- `content`：按最终发送文本 + 处理模式防重，不同频道的同一链接可以只发一次，适合资源链接与跨频道重复消息。
- `off`：不做去重，每次命中都发送。只在确实需要重复消息时使用。

处理状态保存在 `<workdir>/message_relay.sqlite3`，字段包含 destination、fingerprint、action、source_chat、source_message、status、attempts、created_at、updated_at、last_error。

`sending` 状态默认保留 300 秒 lease；失败后的同一资源默认冷却 600 秒。可以在目标中使用 `retry_after_seconds` / `lease_seconds` 覆盖。只有再次命中消息时才重试；当前没有后台自动重试扫描器。

`sent` 仅表示 Telegram 发送接口已成功返回，不代表目标 Bot 后续操作成功；发送成功之后、数据库更新之前崩溃时，仍可能再次投递，因此不是严格 exactly-once 语义。SQLite 存的是指纹与元数据，不存完整消息内容。

## 示例模板

- `examples/message_relay_basic.json`：通用频道镜像、链接提取到 Bot、关键词通知。
- `examples/115_long_anime.json`：仅匹配动态年份的「长时｜连载｜国漫」，从消息中提取 115 分享链接，发送到你**现有**的自动转存 Bot。

## 兼容性

保留原有 `forward`、`send_text`、`extract_regex`、`external_forward`、monitor 和签到流程。早期的 `dispatch_link_to_bot` Handler 保留为兼容快捷入口，新配置统一推荐 `relay_message`。

此阶段使用 JSON 配置；WebUI 可视化规则管理、历史消息回溯、Bot 处理结果确认、后台重试队列将安排后续开发。
