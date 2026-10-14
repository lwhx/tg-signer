import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "tg-signer · 自动化控制台",
  description: "Telegram 账号、签到与自动化任务管理",
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(() => { try { const stored = localStorage.getItem("tg-signer-theme"); const dark = stored ? stored === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches; document.documentElement.classList.toggle("dark", dark); } catch (_) {} })();`,
          }}
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
