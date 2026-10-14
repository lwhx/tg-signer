"use client";
import { useEffect, useRef, useState } from "react";
import {
  ArrowDownToLine,
  ChevronLeft,
  ChevronRight,
  Download,
  Pause,
  Play,
  Search,
  Terminal,
  Trash2,
} from "lucide-react";
import { Account, api, Run, Task } from "@/lib/api";
import { cn, date, download } from "@/lib/utils";
import { Status } from "./common";
import { Button } from "./ui/button";
import { Dialog, DialogContent } from "./ui/dialog";
export function Logs({
  accounts,
  tasks,
}: {
  accounts: Account[];
  tasks: Task[];
}) {
  const [entries, setEntries] = useState<any[]>([]);
  const [connected, setConnected] = useState(false);
  const [transport, setTransport] = useState("WebSocket");
  const [paused, setPaused] = useState(false);
  const pause = useRef(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const bottom = useRef<HTMLDivElement>(null);
  const [filter, setFilter] = useState({
    account_id: "",
    task_id: "",
    status: "",
    q: "",
  });
  const [page, setPage] = useState(1);
  const [data, setData] = useState<{ items: Run[]; total: number }>({
    items: [],
    total: 0,
  });
  const [selected, setSelected] = useState<Run | null>(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("live");
  const [keyword, setKeyword] = useState("");
  useEffect(() => {
    let alive = true;
    let socket: WebSocket;
    let source: EventSource | null = null;
    let timer: ReturnType<typeof setTimeout>;
    const message = (event: MessageEvent) => {
      if (!alive || pause.current) return;
      const value = JSON.parse(event.data);
      if (value.type === "history") setEntries(value.items);
      else if (value.type === "log")
        setEntries((old) => [...old, value.item].slice(-1000));
    };
    const fallback = () => {
      if (source || !alive) return;
      source = new EventSource("/api/logs/stream");
      source.onmessage = message;
      source.onopen = () => {
        setTransport("EventSource");
        setConnected(true);
      };
      source.onerror = () => setConnected(false);
    };
    const connect = () => {
      socket = new WebSocket(
        `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/logs`,
      );
      socket.onopen = () => {
        source?.close();
        source = null;
        setTransport("WebSocket");
        setConnected(true);
      };
      socket.onmessage = message;
      socket.onclose = (e) => {
        if (!alive) return;
        if (!source) setConnected(false);
        if (alive && e.code !== 4401) {
          fallback();
          timer = setTimeout(connect, 5000);
        }
      };
      socket.onerror = () => socket.close();
    };
    connect();
    return () => {
      alive = false;
      clearTimeout(timer);
      socket?.close();
      source?.close();
    };
  }, []);
  useEffect(() => {
    if (autoScroll) bottom.current?.scrollIntoView({ block: "nearest" });
  }, [entries, autoScroll]);
  useEffect(() => {
    let alive = true;
    const load = () => {
      const query = new URLSearchParams({
        page: String(page),
        size: "25",
        ...Object.fromEntries(Object.entries(filter).filter(([, v]) => v)),
      });
      api("/logs?" + query)
        .then((v) => {
          if (alive) {
            setData(v);
            setError("");
          }
        })
        .catch((e) => {
          if (alive) setError(e.message);
        });
    };
    const debounce = setTimeout(load, 250);
    const timer = setInterval(load, 10000);
    return () => {
      alive = false;
      clearTimeout(debounce);
      clearInterval(timer);
    };
  }, [filter, page]);
  const filtered = entries.filter(
    (e) =>
      (!filter.account_id || String(e.account_id) === filter.account_id) &&
      (!filter.task_id || String(e.task_id) === filter.task_id) &&
      (!keyword || e.message.toLowerCase().includes(keyword.toLowerCase())),
  );
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-2">
          <Button
            variant={tab === "live" ? "default" : "outline"}
            onClick={() => setTab("live")}
          >
            <Terminal size={15} />
            实时终端
          </Button>
          <Button
            variant={tab === "history" ? "default" : "outline"}
            onClick={() => setTab("history")}
          >
            执行历史
          </Button>
        </div>
        <div className="flex flex-wrap gap-2">
          <select
            aria-label="按账号筛选"
            className="!w-40"
            value={filter.account_id}
            onChange={(e) => {
              setFilter({ ...filter, account_id: e.target.value });
              setPage(1);
            }}
          >
            <option value="">全部账号</option>
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>
          <select
            aria-label="按任务筛选"
            className="!w-40"
            value={filter.task_id}
            onChange={(e) => {
              setFilter({ ...filter, task_id: e.target.value });
              setPage(1);
            }}
          >
            <option value="">全部任务</option>
            {tasks.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </div>
      </div>
      {tab === "live" ? (
        <section className="overflow-hidden rounded-xl border border-slate-700 bg-[#111f29]">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 px-5 py-4">
            <div className="flex items-center gap-3">
              <div className="flex gap-1.5">
                <i className="h-2.5 w-2.5 rounded-full bg-red-400" />
                <i className="h-2.5 w-2.5 rounded-full bg-amber-300" />
                <i className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
              </div>
              <span className="font-mono text-xs text-slate-400">
                tg-signer / console
              </span>
              <span
                className={cn(
                  "rounded px-2 py-0.5 text-[10px]",
                  connected
                    ? "bg-emerald-400/10 text-emerald-300"
                    : "bg-amber-400/10 text-amber-300",
                )}
              >
                {connected ? "LIVE" : "RECONNECTING"}
              </span>
            </div>
            <div className="flex gap-1">
              <Button
                variant="ghost"
                size="icon"
                className="text-slate-400 hover:bg-white/10 hover:text-white"
                aria-label={paused ? "恢复日志" : "暂停日志"}
                onClick={() => {
                  pause.current = !paused;
                  setPaused(!paused);
                }}
              >
                {paused ? <Play size={15} /> : <Pause size={15} />}
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className={cn(
                  "text-slate-400 hover:bg-white/10 hover:text-white",
                  autoScroll && "text-emerald-300",
                )}
                aria-label="自动滚动"
                onClick={() => setAutoScroll(!autoScroll)}
              >
                <ArrowDownToLine size={15} />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="text-slate-400 hover:bg-white/10 hover:text-white"
                aria-label="清空本地终端"
                onClick={() => setEntries([])}
              >
                <Trash2 size={15} />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="text-slate-400 hover:bg-white/10 hover:text-white"
                aria-label="导出终端日志"
                onClick={() =>
                  download(
                    "tg-signer-console.log",
                    filtered
                      .map((e) => `${e.time} [${e.level}] ${e.message}`)
                      .join("\n"),
                  )
                }
              >
                <Download size={15} />
              </Button>
            </div>
          </div>
          <div className="border-b border-white/5 px-5 py-3">
            <input
              aria-label="搜索实时日志"
              className="!border-white/10 !bg-white/5 !py-2 !text-xs !text-slate-300"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              placeholder="搜索终端输出…"
            />
          </div>
          <div className="h-[500px] overflow-y-auto p-5 font-mono text-xs leading-7">
            {!filtered.length && (
              <p className="text-slate-500">等待任务日志…</p>
            )}
            {filtered.map((e, i) => (
              <div key={i} className="flex gap-3">
                <span className="shrink-0 text-slate-500">
                  {new Date(e.time).toLocaleTimeString("zh-CN", {
                    hour12: false,
                  })}
                </span>
                <span
                  className={cn(
                    "w-14 shrink-0",
                    e.level === "ERROR"
                      ? "text-red-400"
                      : e.level === "WARNING"
                        ? "text-amber-300"
                        : "text-emerald-400",
                  )}
                >
                  {e.level}
                </span>
                <span className="whitespace-pre-wrap break-all text-slate-300">
                  {e.task_id ? `[任务 ${e.task_id}] ` : ""}
                  {e.message}
                </span>
              </div>
            ))}
            <div ref={bottom} />
          </div>
          <div className="flex justify-between border-t border-white/10 px-5 py-3 text-[11px] text-slate-500">
            <span>{paused ? "已暂停接收显示" : `${transport} 实时日志流`}</span>
            <span>最近 {entries.length} 条 · 最多保留 1,000 条</span>
          </div>
        </section>
      ) : (
        <section className="card overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-3 p-5">
            <div className="flex flex-wrap gap-3">
              <div className="relative">
                <Search
                  size={15}
                  className="absolute left-3 top-3 text-muted"
                />
                <input
                  aria-label="搜索历史记录"
                  className="!pl-9"
                  placeholder="搜索任务、回复或结果…"
                  value={filter.q}
                  onChange={(e) => {
                    setFilter({ ...filter, q: e.target.value });
                    setPage(1);
                  }}
                />
              </div>
              <select
                aria-label="按结果筛选"
                className="!w-32"
                value={filter.status}
                onChange={(e) => {
                  setFilter({ ...filter, status: e.target.value });
                  setPage(1);
                }}
              >
                <option value="">全部结果</option>
                {[
                  ["success", "成功"],
                  ["failed", "失败"],
                  ["completed", "已执行"],
                  ["running", "运行中"],
                  ["cancelled", "已停止"],
                  ["interrupted", "已中断"],
                ].map(([v, l]) => (
                  <option key={v} value={v}>
                    {l}
                  </option>
                ))}
              </select>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                download(
                  "execution-history-page.json",
                  JSON.stringify(data.items, null, 2),
                )
              }
            >
              <Download size={14} />
              导出本页
            </Button>
          </div>
          {error && <p className="p-5 text-sm text-red-600">{error}</p>}
          <div className="overflow-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-y border-line bg-slate-50 text-xs text-muted">
                <tr>
                  {["执行时间", "任务 / 账号", "状态", "结果摘要", "详情"].map(
                    (t) => (
                      <th
                        key={t}
                        className="whitespace-nowrap px-5 py-3 font-medium"
                      >
                        {t}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {data.items.map((r) => (
                  <tr key={r.id} className="border-b border-line">
                    <td className="whitespace-nowrap px-5 py-4 text-xs text-muted">
                      {date(r.started_at)}
                    </td>
                    <td className="px-5 py-4">
                      <p className="font-medium">{r.task_name}</p>
                      <p className="mt-1 text-xs text-muted">
                        {r.account_name}
                      </p>
                    </td>
                    <td className="px-5 py-4">
                      <Status value={r.status} />
                    </td>
                    <td className="max-w-xs truncate px-5 py-4 text-xs text-muted">
                      {r.summary || "执行中…"}
                    </td>
                    <td className="px-5 py-4">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelected(r)}
                      >
                        查看回复
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!data.items.length && (
              <p className="p-12 text-center text-sm text-muted">
                当前筛选下没有执行记录。
              </p>
            )}
          </div>
          <div className="flex items-center justify-between p-4 text-xs text-muted">
            <span>
              共 {data.total} 条 · 第 {page} 页
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="icon"
                aria-label="上一页记录"
                disabled={page === 1}
                onClick={() => setPage(page - 1)}
              >
                <ChevronLeft size={15} />
              </Button>
              <Button
                variant="outline"
                size="icon"
                aria-label="下一页记录"
                disabled={page * 25 >= data.total}
                onClick={() => setPage(page + 1)}
              >
                <ChevronRight size={15} />
              </Button>
            </div>
          </div>
        </section>
      )}
      <Dialog open={!!selected} onOpenChange={(v) => !v && setSelected(null)}>
        <DialogContent
          title={selected?.task_name || "执行详情"}
          description={
            selected
              ? `${selected.account_name} · ${date(selected.started_at)}`
              : ""
          }
        >
          <Status value={selected?.status || "pending"} />
          <p className="my-4 text-sm leading-6">{selected?.summary}</p>
          <h3 className="mb-2 text-xs font-medium text-muted">
            Telegram 原始回复
          </h3>
          <pre className="max-h-96 overflow-auto whitespace-pre-wrap break-all rounded-lg bg-slate-50 p-4 text-xs leading-6">
            {selected?.response || "没有记录到回复消息。"}
          </pre>
        </DialogContent>
      </Dialog>
    </div>
  );
}
