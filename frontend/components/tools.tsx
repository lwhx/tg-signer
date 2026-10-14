"use client";
import { useEffect, useState } from "react";
import {
  Code2,
  Database,
  Download,
  Play,
  Save,
  Trash2,
  Wrench,
} from "lucide-react";
import { Account, api, post } from "@/lib/api";
import { download } from "@/lib/utils";
import { parseSchedule, scheduleCron } from "@/lib/schedule";
import { SchedulePicker } from "./schedule-picker";
import { ActionButton, Field } from "./common";
import { Button } from "./ui/button";
const operations = [
  ["dialogs", "最近对话 / Folder 发现"],
  ["folders", "列出 Telegram 文件夹"],
  ["topics", "群组话题 ID"],
  ["members", "查询群组 / 频道成员"],
  ["send_text", "发送文本消息"],
  ["send_dice", "发送骰子"],
  ["schedule", "批量添加 Telegram 定时消息"],
  ["scheduled", "查看 Telegram 定时消息"],
  ["delete_scheduled", "删除 Telegram 定时消息"],
  ["logout", "撤销 Telegram Session"],
];
export function Tools({ accounts }: { accounts: Account[] }) {
  const [schedule, setSchedule] = useState(() => parseSchedule("0 8 * * *"));
  const [form, setForm] = useState<any>({
    account_id: accounts[0]?.id || 0,
    operation: "dialogs",
    chat_id: "",
    text: "",
    folder: "",
    message_thread_id: null,
    delete_after: null,
    limit: 50,
    admin: false,
    query: "",
    cron: "0 8 * * *",
    next_times: 3,
    random_seconds: 0,
    message_ids: [],
  });
  const [result, setResult] = useState("");
  const [tab, setTab] = useState("telegram");
  const [plugins, setPlugins] = useState<any[]>([]);
  const [plugin, setPlugin] = useState({
    name: "custom.py",
    code: 'async def echo(event, ctx, params):\n    await ctx.worker.send_message(event.chat_id, params.get("text", "hello"))\n    return "continue"\n\nHANDLERS = {"echo": echo}\n',
  });
  const [legacyUser, setLegacyUser] = useState("");
  const change = (k: string, v: any) =>
    setForm((old: any) => ({ ...old, [k]: v }));
  const loadPlugins = () => api("/plugins").then(setPlugins);
  useEffect(() => {
    if (tab === "plugins") loadPlugins().catch((e) => setResult(e.message));
  }, [tab]);
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-2">
        {[
          ["telegram", "Telegram 工具", Wrench],
          ["records", "历史记录迁移", Database],
          ["plugins", "Python 插件", Code2],
        ].map(([id, label, Icon]: any) => (
          <Button
            key={id}
            variant={tab === id ? "default" : "outline"}
            onClick={() => {
              setTab(id);
              setResult("");
            }}
          >
            <Icon size={15} />
            {label}
          </Button>
        ))}
      </div>
      {tab === "telegram" ? (
        <div className="grid gap-6 xl:grid-cols-2">
          <section className="card space-y-5 p-6">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="执行账号">
                <select
                  value={form.account_id}
                  onChange={(e) => change("account_id", Number(e.target.value))}
                >
                  {!accounts.length && <option value={0}>请先添加账号</option>}
                  {accounts.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="操作">
                <select
                  value={form.operation}
                  onChange={(e) => change("operation", e.target.value)}
                >
                  {operations.map(([v, l]) => (
                    <option key={v} value={v}>
                      {l}
                    </option>
                  ))}
                </select>
              </Field>
            </div>
            {!["folders", "dialogs", "logout"].includes(form.operation) && (
              <Field label="Chat ID / @username">
                <input
                  value={form.chat_id}
                  onChange={(e) => change("chat_id", e.target.value)}
                  placeholder="@YourBot / -100…"
                />
              </Field>
            )}
            {form.operation === "dialogs" && (
              <Field label="Folder 名称或 ID（可选）">
                <input
                  value={form.folder}
                  onChange={(e) => change("folder", e.target.value)}
                  placeholder="留空获取最近对话"
                />
              </Field>
            )}
            {["dialogs", "members", "topics"].includes(form.operation) && (
              <Field label="结果数量">
                <input
                  type="number"
                  min={1}
                  max={500}
                  value={form.limit}
                  onChange={(e) => change("limit", Number(e.target.value))}
                />
              </Field>
            )}
            {form.operation === "members" && (
              <>
                <Field label="搜索关键词">
                  <input
                    value={form.query}
                    onChange={(e) => change("query", e.target.value)}
                  />
                </Field>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={form.admin}
                    onChange={(e) => change("admin", e.target.checked)}
                  />
                  仅管理员
                </label>
              </>
            )}
            {["send_text", "send_dice", "schedule"].includes(
              form.operation,
            ) && (
              <>
                <Field
                  label={
                    form.operation === "send_dice" ? "骰子 Emoji" : "消息文本"
                  }
                >
                  <textarea
                    rows={3}
                    value={form.text}
                    onChange={(e) => change("text", e.target.value)}
                    placeholder={
                      form.operation === "send_dice"
                        ? "🎲"
                        : "请输入要发送的消息"
                    }
                  />
                </Field>
                <div className="grid grid-cols-2 gap-4">
                  <Field label="话题 ID（可选）">
                    <input
                      type="number"
                      value={form.message_thread_id ?? ""}
                      onChange={(e) =>
                        change(
                          "message_thread_id",
                          e.target.value ? Number(e.target.value) : null,
                        )
                      }
                    />
                  </Field>
                  {form.operation !== "schedule" && (
                    <Field label="延时删除（秒，可选）">
                      <input
                        type="number"
                        value={form.delete_after ?? ""}
                        onChange={(e) =>
                          change(
                            "delete_after",
                            e.target.value ? Number(e.target.value) : null,
                          )
                        }
                      />
                    </Field>
                  )}
                </div>
              </>
            )}
            {form.operation === "schedule" && (
              <>
                <SchedulePicker value={schedule} onChange={setSchedule} />
                <div className="grid grid-cols-2 gap-4">
                  <Field label="未来发送次数">
                    <input
                      type="number"
                      min={1}
                      max={100}
                      value={form.next_times}
                      onChange={(e) =>
                        change("next_times", Number(e.target.value))
                      }
                    />
                  </Field>
                  <Field label="随机延迟上限（秒）">
                    <input
                      type="number"
                      value={form.random_seconds}
                      onChange={(e) =>
                        change("random_seconds", Number(e.target.value))
                      }
                    />
                  </Field>
                </div>
                <p className="text-xs leading-6 text-muted">
                  由 Telegram
                  服务器保存定时消息，面板关闭后仍会发送。调度时区使用容器 TZ。
                </p>
              </>
            )}
            {form.operation === "delete_scheduled" && (
              <Field label="消息 ID（逗号分隔）">
                <input
                  onChange={(e) =>
                    change(
                      "message_ids",
                      e.target.value.split(",").map(Number).filter(Boolean),
                    )
                  }
                />
              </Field>
            )}
            {form.operation === "logout" && (
              <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
                这将撤销 Telegram
                授权并禁用该账号的全部任务。再次使用需要重新登录。
              </p>
            )}
            <ActionButton
              disabled={!form.account_id}
              action={async () => {
                if (
                  form.operation === "logout" &&
                  !confirm("确定撤销此 Telegram Session？")
                )
                  return;
                const data = await post("/tools", {
                  ...form,
                  ...(form.operation === "schedule"
                    ? { cron: scheduleCron(schedule) }
                    : {}),
                });
                setResult(JSON.stringify(data.result, null, 2));
              }}
            >
              <Play size={15} />
              执行操作
            </ActionButton>
          </section>
          <Result value={result} />
        </div>
      ) : tab === "records" ? (
        <div className="grid gap-6 xl:grid-cols-2">
          <section className="card space-y-5 p-6">
            <h2 className="font-semibold">兼容 tg-signer 历史记录</h2>
            <p className="text-sm leading-7 text-muted">
              将旧工作目录放入数据卷的 upstream 目录。迁移会扫描 signs 下的
              sign_record.json，写入 SQLite
              并保留原文件。迁移记录只包含执行日期，不会伪造成功匹配结果。
            </p>
            <Field label="旧版记录 User ID（可选）">
              <input
                value={legacyUser}
                onChange={(e) => setLegacyUser(e.target.value)}
                placeholder="仅无用户子目录的旧记录需要"
              />
            </Field>
            <div className="flex flex-wrap gap-3">
              <ActionButton
                action={async () =>
                  setResult(
                    JSON.stringify(
                      await post(
                        "/records/migrate" +
                          (legacyUser
                            ? "?legacy_user_id=" +
                              encodeURIComponent(legacyUser)
                            : ""),
                      ),
                      null,
                      2,
                    ),
                  )
                }
              >
                <Database size={15} />
                迁移历史记录
              </ActionButton>
              <ActionButton
                variant="outline"
                action={async () =>
                  setResult(
                    JSON.stringify(await api("/records/upstream"), null, 2),
                  )
                }
              >
                读取上游记录
              </ActionButton>
            </div>
          </section>
          <Result value={result} />
        </div>
      ) : (
        <div className="grid gap-6 xl:grid-cols-[230px_1fr]">
          <section className="card p-5">
            <h2 className="mb-4 font-semibold">自定义 Handler</h2>
            <p className="mb-5 text-xs leading-6 text-muted">
              仅安装您信任的 Python
              代码。插件以容器用户权限执行，保存后重新启动自动化任务。
            </p>
            {plugins.map((p) => (
              <button
                key={p.name}
                onClick={() => setPlugin(p)}
                className="mb-2 block w-full rounded-lg bg-slate-50 px-3 py-2 text-left font-mono text-xs"
              >
                {p.name}
              </button>
            ))}
          </section>
          <section className="card space-y-4 p-6">
            <Field label="文件名">
              <input
                value={plugin.name}
                onChange={(e) => setPlugin({ ...plugin, name: e.target.value })}
              />
            </Field>
            <Field label="Python 代码">
              <textarea
                className="code-editor min-h-72"
                value={plugin.code}
                onChange={(e) => setPlugin({ ...plugin, code: e.target.value })}
                spellCheck={false}
              />
            </Field>
            <div className="flex gap-3">
              <ActionButton
                action={async () => {
                  await api("/plugins", {
                    method: "PUT",
                    body: JSON.stringify(plugin),
                  });
                  await loadPlugins();
                }}
                success="插件已保存"
              >
                <Save size={15} />
                保存插件
              </ActionButton>
              <ActionButton
                variant="destructive"
                action={async () => {
                  if (!confirm("删除此插件文件？")) return;
                  await api("/plugins/" + encodeURIComponent(plugin.name), {
                    method: "DELETE",
                  });
                  await loadPlugins();
                }}
              >
                <Trash2 size={15} />
                删除
              </ActionButton>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
function Result({ value }: { value: string }) {
  return (
    <section className="card overflow-hidden">
      <div className="flex items-center justify-between border-b border-line px-5 py-4">
        <h2 className="text-sm font-semibold">执行结果</h2>
        <Button
          variant="ghost"
          size="sm"
          disabled={!value}
          onClick={() => download("telegram-result.json", value)}
        >
          <Download size={14} />
          导出
        </Button>
      </div>
      <pre className="max-h-[600px] min-h-64 overflow-auto whitespace-pre-wrap break-all p-5 font-mono text-xs leading-6 text-muted">
        {value || "等待执行操作…"}
      </pre>
    </section>
  );
}
