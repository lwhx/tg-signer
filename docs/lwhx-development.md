# lwhx/tg-signer 二次开发第一阶段

本仓库源自 [amchii/tg-signer](https://github.com/amchii/tg-signer)，继续保留 BSD-3-Clause 许可证、原有签到、监控与自动化能力。

## 已完成

- 支持通过现有 Automation 的 chat_ids 监听多个来源频道。
- 根据 Python 正则过滤消息标题，仅匹配 20xx 年「长时｜连载｜国漫」并包含 115cdn 分享链接。
- 新增 dispatch_link_to_bot Handler：提取链接并以普通文本发送到**已经部署的** Telegram 自动转存 Bot。
- 增加 SQLite 持久化投递状态，按目标 Bot 和链接内容去重；失败可以在新消息再次触发时重试。
- 调整 Python 包分发名和 GitHub 项目 URL；镜像指向 ghcr.io/lwhx/tg-signer；关闭原有自动 PyPI 上传流程。

## 配置与运行

先与目标 Bot 私聊发送 /start。复制 examples/115_long_anime.json 到 .signer/automations/115_anime/config.json，替换 @SOURCE_CHANNEL_1、@SOURCE_CHANNEL_2、@YOUR_115_BOT 为实际值。

运行：

```bash
tg-signer automation validate 115_anime
tg-signer automation run 115_anime
```

机器人接收的是链接文本，不是频道消息原生转发。数据库存放在 .signer/dispatch_log.sqlite3，务必将工作目录和 Telegram Session 一并持久化。

## 明确的限制

- 状态 sent 表示消息已提交到 Telegram，不代表 Bot 已成功转存 115 网盘。
- SQLite 能减少重复发送，但在发送后、落盘前崩溃，仍可能出现重复投递；并非严格恰好一次语义。
- 失败记录仅在下一条匹配消息触发时重试，没有后台失败扫描队列。
- 本阶段去重按目标和链接原文，不归一化密码参数、URL 锚点等差异。
- 过滤器要求标题和链接格式相符；Bot 消息反馈解析、规则管理 WebUI、历史消息补录留在后续阶段。
- 不会自动创建 GitHub 的 fork 关联；本仓库仍可通过 git remote upstream 手动同步上游。

## 后续路线

1. 增加 Automation 图形化规则管理和正则测试器。
2. Bot 回复监听、状态确认、失败队列与退避重试。
3. 历史补录、批量任务与可搜索的执行日志。
4. 上游同步检测和独立版本发布规范。
