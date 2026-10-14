# Automation 通用转发 WebUI

本阶段将通用消息监控与转发规则纳入 WebUI，**不要求 Telegram Bot 或任何网盘接口**；已有 115 自动转存 Bot 只是一个目标示例。

## 功能

在 WebUI 的「配置管理 → Automation · 转发规则」中：

- 选择已有任务或新建任务。
- 点击「可视化消息转发」添加/编辑/删除普通消息转发规则。
- 每条规则可指定多个来源频道或群组（@username / 数字 Chat ID）、可选发送者、all/contains/exact/regex 匹配、忽略大小写和忽略自身消息。
- 每条规则可有多个目标，分别选择 forward、copy、text、extract、template 模式，设置 message/content/off 去重方式。
- 在「正则匹配测试」粘贴真实消息，检查是否命中、命中范围、普通捕获组和命名捕获组。
- 完成可视化编辑后，**必须点击配置页面最下方的「保存」**，任务配置才会写入磁盘。此操作不会启动、停止或重启正在运行的 Automation 任务。

复杂规则（定时/启动触发、混合 Handler、未知字段）仍可通过 JSON 编辑器管理。可视化编辑器只显示自己可安全处理的 `message → relay_message` 规则，编辑时不会删掉其他高级规则。

## 启动 WebUI

安装该仓库自己的 GitHub 版本：

```bash
pip install -U "lwhx-tg-signer[gui] @ git+https://github.com/lwhx/tg-signer.git"
tg-signer webgui --host 127.0.0.1 --port 8080
```

打开服务器本地地址 `http://127.0.0.1:8080`。

如果需要从其他电脑通过公网或 LAN 访问，需要设置 `TG_SIGNER_GUI_AUTHCODE`，同时推荐用 HTTPS 反向代理 / Tailscale / WireGuard 限制访问。没有 Auth Code 时不允许启动非 loopback 监听：

```bash
export TG_SIGNER_GUI_AUTHCODE="替换为长度足够的随机授权码"
tg-signer webgui --host 0.0.0.0 --port 8080
```

WebUI 验证失败会触发服务端共享的短期尝试次数限制，防止无限重试。**WebUI 不是多租户权限系统，不应直接裸露公网或与不可信用户共享授权码。**

## 操作流程

1. 登录 Telegram 会话：`tg-signer login`。确认账号已经加入来源频道/群组，且拥有发消息到目标的权限。
2. 进入「配置管理 → Automation · 转发规则」；在「保存为/新建名称」输入例如 `monitor_news`，或从已有配置下拉框选择现有任务。
3. 在可视化编辑器中填写规则 ID（例如 `news_links`）、来源聊天室、过滤条件。
4. 添加多个目标：例如将原消息 forward 到备份频道，同时对目标 Bot 以 extract 模式发送正则捕获的链接；每个目标可设置不同的去重方式。
5. 使用正则测试器验证真实 TG 消息，查看普通/命名捕获组，然后点击「应用到 JSON 编辑器」。
6. 最后在配置管理界面点击「保存」；启动 Automation：

```bash
tg-signer automation validate monitor_news
tg-signer automation run monitor_news
```

WebUI 修改运行中的配置不会实时生效。确认保存后，请使用你自己的进程管理器/Docker 手动重启相应 Automation 进程。

## 匹配注意事项

- `contains`：只要消息包含关键词即可；`exact`：整条消息完全一致；`regex`：Python 正则 `re.search()`。
- 正则表达式最长 2048 字符，测试样本最长 8000 字符。WebUI 正则测试运行在有 1 秒超时的子进程中，避免灾难性回溯卡住界面。**实际 Telegram 监听引擎仍使用 Python re.search；请避免在运行规则中使用回溯风险高的表达式。**
- `extract`：必须填写捕获正则和存在的捕获组（数字或命名）。
- `template`：支持 `{text}`、`{chat_id}`、`{message_id}`、`{sender_id}`、`{rule_id}` 等模板变量；可以选填正则。
- `dedup=message` 会按来源消息及规则区分；`dedup=content` 会按内容去重；`off` 关闭去重。
- 转发目标也可填写 `me`，将消息发到当前 Telegram 账号的「收藏消息（Saved Messages）」。
- 禁止来源和目标填写完全相同的 ID/用户名，但无法自动识别「@username 与对应数字 ID 其实属于同一聊天室」的间接循环，请谨慎配置。
- 纯媒体消息可以通过 forward/copy 转发；text/extract/template 只处理文本或媒体 caption。
- 仅转发/发送成功不等于外部 Bot 已成功处理相关内容。

## 本阶段交付与边界

新增 `tg_signer/webui/automation_editor.py`、`automation_form.py`、`regex_preview.py`。扩展原数据层以管理原生 Automation 的 `config.json`。原有 Signer、Monitor、Automation CLI 保持不变。

**尚未实现：** 自动启停任务、浏览器端历史扫描、对目标 Bot 的异步处理结果确认、复杂规则可视化和多用户权限管理。第二轮继续完善运行状态与投递日志看板。
