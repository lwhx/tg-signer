# lwhx/tg-signer 二次开发路线

## 产品定位

**通用 Telegram 消息监控与转发平台**，不是 115 网盘专用工具。

从已登录账户有权访问的频道、群组、私聊捕获消息；按来源、发送者、关键词或正则匹配；把匹配消息以原生转发、复制、纯文本、正则提取或模板格式发送到其他频道、群组、个人或 Bot。网盘自动转存、告警、资讯聚合等都是应用模板。

基于 [amchii/tg-signer](https://github.com/amchii/tg-signer)，保留原 BSD-3-Clause 许可证、Signer 自动签到、Monitor 和 Automation 规则引擎。

## 第一阶段：通用消息转发内核

- 使用原有 Message Trigger 配置多个来源、用户过滤。
- 使用原有 Filter 支持 all / exact / contains / regex。
- 新增 `relay_message`，多个目标分别支持 forward / copy / text / extract / template。
- 新增 SQLite 去重与投递记录，策略 message / content / off。
- 默认忽略账号自己发出的消息，阻止来源 ID 与目标 ID 相同的直接转发循环。
- 兼容旧 `dispatch_link_to_bot` 入口，但不再以 115 为核心逻辑。
- 提供通用监控转发、115 转存 Bot 等示例配置。
- 镜像/包名归属更新为 lwhx，禁用原有自动 PyPI 上传；保留上游来源说明。

## 第二阶段：WebUI 规则管理（V1 已提交 PR #3）

- 账号与会话状态：登录、会话、权限与来源选择。
- [x] 可视化设置来源频道、消息匹配条件、多个目标、单条规则启停及规则增删改。
- [ ] 拖拽排序规则、快捷复制规则、批量管理任务。
- [x] 可配置匹配模式、超时受控的正则测试工具和捕获组预览。
- [x] 可视化配置 forward、copy、text、extract、template。
- [ ] 连接真实 Telegram 消息的端到端发送测试。
- SQLite 投递日志筛选（来源、目标、规则、时间、状态）、人工重投。
- [x] WebUI 非 loopback 绑定需 Auth Code，失败验证次数限制、配置文件名校验。
- [ ] 进一步增强多租户权限、细粒度会话隔离及凭据管理。

## 第三阶段：可靠性和监控

- 失败任务队列、指数退避、重试次数上限、失败告警。
- 编辑消息策略、幂等边界和反循环规则。
- 目标 Bot 异步回复和完成状态跟踪（插件化、可选，不污染通用内核）。
- Telegram FloodWait / Rate Limit 控制与吞吐监控。
- 历史消息补录、断点续扫和进度可视化。
- 配置备份/恢复、导入导出、端到端回归测试。

## 第四阶段：模板和插件生态

- 模板：115 网盘链接、普通网址、新闻关键词、频道镜像、通知归档。
- Telegram 之外的通知目标通过已有 `external_forward` 或安全的自定义 Handler 接入。
- 上游版本同步和兼容性测试；依赖、安全性持续维护。

## 开发约束

使用独立 GitHub 分支、PR、测试回归；不修改或删除现有 Signer/Monitor 功能，不把特定 Bot、资源类型或网盘逻辑写死在 `tg_signer/automation` 核心。

当前版本只实现第一阶段的基础能力，不声称已完成完整 WebUI、异步 Bot 成功确认或历史补录。GitHub Actions 没有运行结果时，不在未验证情况下宣称所有测试成功。

## 当前待验证

- PR #3 的 WebUI 代码需要在 GitHub Actions 启用后执行完整回归与 GUI 导入测试。
- V1 暂不支持自动重启运行任务。可视化编辑先同步到 JSON 编辑器，再经人工点击保存写入配置。
