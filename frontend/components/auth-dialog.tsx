"use client";
import { useEffect, useReducer, useState } from "react";
import {
  ArrowRight,
  Check,
  KeyRound,
  Loader2,
  LockKeyhole,
  Send,
  ShieldCheck,
  Upload,
} from "lucide-react";
import { toast } from "sonner";
import { api, post } from "@/lib/api";
import { useUI } from "@/lib/store";
import { cn } from "@/lib/utils";
import { Button } from "./ui/button";
import { Dialog, DialogContent } from "./ui/dialog";
import { Field } from "./common";
type State = {
  step: "PARAMETERS" | "CODE_SENT" | "2FA_REQUIRED" | "AUTHORIZED";
  flow_id: string;
  phone_code_hash: string;
  retryAt: number;
};
type Event =
  | { type: "RESET" }
  | {
      type: "SENT";
      flow_id: string;
      phone_code_hash: string;
      resend_after: number;
    }
  | { type: "2FA" }
  | { type: "DONE" };
const initial: State = {
  step: "PARAMETERS",
  flow_id: "",
  phone_code_hash: "",
  retryAt: 0,
};
function reducer(state: State, event: Event): State {
  switch (event.type) {
    case "RESET":
      return initial;
    case "SENT":
      if (state.step !== "PARAMETERS" && state.step !== "CODE_SENT")
        return state;
      return {
        step: "CODE_SENT",
        flow_id: event.flow_id,
        phone_code_hash: event.phone_code_hash,
        retryAt: Date.now() + event.resend_after * 1000,
      };
    case "2FA":
      return state.step === "CODE_SENT"
        ? { ...state, step: "2FA_REQUIRED" }
        : state;
    case "DONE":
      return { ...state, step: "AUTHORIZED" };
  }
}
export function AuthDialog() {
  const { authOpen, setAuthOpen, refresh } = useUI();
  const [state, dispatch] = useReducer(reducer, initial);
  const [mode, setMode] = useState<"phone" | "import">("phone");
  const [custom, setCustom] = useState(false);
  const [phone, setPhone] = useState("");
  const [name, setName] = useState("");
  const [apiId, setApiId] = useState("");
  const [apiHash, setApiHash] = useState("");
  const [proxy, setProxy] = useState("");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [session, setSession] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [clock, setClock] = useState(Date.now());
  useEffect(() => {
    const timer = setInterval(() => setClock(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  const reset = () => {
    dispatch({ type: "RESET" });
    setCode("");
    setPassword("");
    setSession("");
    setFile(null);
    setApiHash("");
    setError("");
    setMode("phone");
  };
  const close = async () => {
    if (busy) return;
    if (state.flow_id && state.step !== "AUTHORIZED")
      await api("/auth/flows/" + state.flow_id, { method: "DELETE" }).catch(
        () => {},
      );
    setAuthOpen(false);
    reset();
  };
  const spec = () => ({
    phone,
    name,
    proxy,
    ...(custom ? { api_id: Number(apiId), api_hash: apiHash } : {}),
  });
  const run = async (action: () => Promise<any>) => {
    setBusy(true);
    setError("");
    try {
      const result = await action();
      if (result?.status === "AUTHORIZED") {
        dispatch({ type: "DONE" });
        setPassword("");
        setCode("");
        setSession("");
        refresh();
        toast.success("Telegram 账号已绑定");
      }
      return result;
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const send = async () => {
    const result = await run(() =>
      post("/auth/send-code", {
        ...spec(),
        ...(state.flow_id ? { flow_id: state.flow_id } : {}),
      }),
    );
    if (result) dispatch({ type: "SENT", ...result });
  };
  const verify = () =>
    run(async () => {
      const result = await post("/auth/sign-in", {
        flow_id: state.flow_id,
        phone_code_hash: state.phone_code_hash,
        code,
      });
      if (result.status === "2FA_REQUIRED") {
        dispatch({ type: "2FA" });
        setCode("");
      }
      return result;
    });
  const importSession = () =>
    run(() => {
      const form = new FormData();
      form.set("name", name);
      form.set("proxy", proxy);
      if (custom) {
        form.set("api_id", apiId);
        form.set("api_hash", apiHash);
      }
      if (file) form.set("file", file);
      else form.set("session_string", session);
      return api("/accounts/import", { method: "POST", body: form });
    });
  const remaining = Math.max(0, Math.ceil((state.retryAt - clock) / 1000));
  const steps = ["账号信息", "验证码", "安全验证"];
  const index =
    state.step === "PARAMETERS" ? 0 : state.step === "CODE_SENT" ? 1 : 2;
  return (
    <Dialog
      open={authOpen}
      onOpenChange={(open) => {
        if (!open) void close();
      }}
    >
      <DialogContent
        title="连接 Telegram 账号"
        description="为您的自动化任务添加一个执行账号。"
      >
        <div className="mb-6 flex items-center justify-between">
          {steps.map((s, i) => (
            <div
              key={s}
              className={cn(
                "flex items-center gap-2 text-xs",
                i <= index ? "text-primary" : "text-slate-400",
              )}
            >
              <span
                className={cn(
                  "flex h-6 w-6 items-center justify-center rounded-full",
                  i <= index ? "bg-emerald-100" : "bg-slate-100",
                )}
              >
                {i < index ? <Check size={13} /> : i + 1}
              </span>
              {s}
            </div>
          ))}
        </div>
        {state.step === "AUTHORIZED" ? (
          <div className="py-8 text-center">
            <ShieldCheck className="mx-auto mb-4 text-primary" size={48} />
            <h3 className="text-xl font-semibold">连接成功</h3>
            <p className="my-3 text-sm text-muted">
              账号已保存，可以开始创建签到任务了。
            </p>
            <Button className="mt-4 w-full" onClick={() => void close()}>
              完成
            </Button>
          </div>
        ) : (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (mode === "import") void importSession();
              else if (state.step === "PARAMETERS") void send();
              else if (state.step === "CODE_SENT") void verify();
              else
                void run(() =>
                  post("/auth/check-2fa", { flow_id: state.flow_id, password }),
                );
            }}
            className="space-y-5"
          >
            {state.step === "PARAMETERS" && (
              <>
                <div className="flex rounded-lg bg-slate-100 p-1">
                  {(["phone", "import"] as const).map((v) => (
                    <button
                      type="button"
                      key={v}
                      onClick={() => {
                        setMode(v);
                        setError("");
                      }}
                      className={cn(
                        "flex-1 rounded-md py-2 text-sm",
                        mode === v
                          ? "bg-white font-medium text-ink shadow-sm"
                          : "text-muted",
                      )}
                    >
                      {v === "phone" ? "手机号登录" : "导入 Session"}
                    </button>
                  ))}
                </div>
                <Field label="账号备注">
                  <input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="例如：主账号"
                    maxLength={100}
                  />
                </Field>
                {mode === "phone" ? (
                  <Field
                    label="手机号码"
                    hint="请包含国家区号，验证码通常发送至 Telegram 客户端。"
                  >
                    <input
                      type="tel"
                      required
                      pattern="\+[1-9][0-9]{6,14}"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      placeholder="+86 138…"
                      autoComplete="tel"
                    />
                  </Field>
                ) : (
                  <>
                    <Field
                      label="Session String"
                      hint="支持 Pyrogram / Kurigram 格式，与 tg-signer 保持兼容。"
                    >
                      <textarea
                        rows={3}
                        className="code-editor"
                        value={session}
                        onChange={(e) => {
                          setSession(e.target.value);
                          setFile(null);
                        }}
                        placeholder="粘贴您的 Session String"
                        disabled={!!file}
                      />
                    </Field>
                    <Field label="或上传 .session 文件">
                      <input
                        type="file"
                        accept=".session"
                        onChange={(e) => setFile(e.target.files?.[0] || null)}
                        className="text-xs text-muted"
                      />
                    </Field>
                  </>
                )}
                <Field label="Telegram API 配置">
                  <select
                    value={custom ? "custom" : "default"}
                    onChange={(e) => setCustom(e.target.value === "custom")}
                  >
                    <option value="default">使用 tg-signer 默认 API</option>
                    <option value="custom">使用自定义 API_ID / API_HASH</option>
                  </select>
                </Field>
                {custom && (
                  <div className="grid grid-cols-3 gap-3">
                    <Field label="API_ID">
                      <input
                        type="number"
                        required
                        value={apiId}
                        onChange={(e) => setApiId(e.target.value)}
                      />
                    </Field>
                    <Field label="API_HASH" className="col-span-2">
                      <input
                        type="password"
                        required
                        value={apiHash}
                        onChange={(e) => setApiHash(e.target.value)}
                        autoComplete="off"
                      />
                    </Field>
                  </div>
                )}
                <Field
                  label="独立代理（可选）"
                  hint="留空使用全局代理，支持 SOCKS5 / HTTP。"
                >
                  <input
                    value={proxy}
                    onChange={(e) => setProxy(e.target.value)}
                    placeholder="socks5://user:pass@host:1080"
                    autoComplete="off"
                  />
                </Field>
              </>
            )}
            {state.step === "CODE_SENT" && (
              <>
                <div className="rounded-xl bg-emerald-50 p-4 text-sm leading-6 text-emerald-800">
                  <Send size={18} className="mb-2" />
                  验证码已发送至 {phone}，请查看 Telegram 客户端或短信。
                </div>
                <Field label="登录验证码">
                  <input
                    required
                    autoFocus
                    inputMode="numeric"
                    pattern="[0-9]{4,8}"
                    autoComplete="one-time-code"
                    value={code}
                    onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                    className="text-center !text-2xl tracking-[.5em]"
                    placeholder="· · · · ·"
                  />
                </Field>
                <button
                  type="button"
                  disabled={remaining > 0 || busy}
                  onClick={() => void send()}
                  className="text-sm text-primary disabled:text-muted"
                >
                  {remaining > 0
                    ? `${remaining} 秒后可重新发送`
                    : "重新发送验证码"}
                </button>
              </>
            )}
            {state.step === "2FA_REQUIRED" && (
              <>
                <div className="rounded-xl bg-amber-50 p-4 text-sm leading-6 text-amber-800">
                  <LockKeyhole size={20} className="mb-2" />
                  此账号已开启二步验证，请输入 Telegram 云密码。
                </div>
                <Field label="二步验证密码">
                  <input
                    type="password"
                    required
                    autoFocus
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </Field>
              </>
            )}
            {error && (
              <p
                role="alert"
                className="rounded-lg bg-red-50 p-3 text-sm leading-6 text-red-600"
              >
                {error}
              </p>
            )}
            <Button
              type="submit"
              className="w-full"
              disabled={busy || (mode === "import" && !session && !file)}
            >
              {busy ? (
                <Loader2 size={16} className="animate-spin" />
              ) : mode === "import" ? (
                <Upload size={16} />
              ) : state.step === "2FA_REQUIRED" ? (
                <KeyRound size={16} />
              ) : (
                <ArrowRight size={16} />
              )}{" "}
              {busy
                ? "正在连接 Telegram…"
                : mode === "import"
                  ? "导入并验证"
                  : state.step === "PARAMETERS"
                    ? "发送验证码"
                    : state.step === "CODE_SENT"
                      ? "验证并继续"
                      : "验证密码"}
            </Button>
            <p className="flex items-center justify-center gap-1.5 text-xs text-muted">
              <ShieldCheck size={13} /> Session 加密存储 · 验证码和密码不落盘
            </p>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
