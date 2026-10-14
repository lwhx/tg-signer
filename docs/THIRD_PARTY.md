# 第三方组件

- tg-signer：amchii，BSD-3-Clause。完整许可证位于 `upstream/tg-signer/LICENSE`，源码固定于 `fc8905db2ee74e2d9afc135cce88b50be35b6212`。
- Next.js、React、Tailwind CSS、Radix UI、TanStack Table、Lucide、Zustand、Recharts：依赖版本见 `frontend/package-lock.json`，各组件许可证随 npm 包提供。
- FastAPI、SQLAlchemy、APScheduler、Kurigram/Pyrogram、PyJWT、pwdlib、cryptography 及其依赖：运行版本锁定于 `backend/constraints.txt`，许可证随已安装的发行包提供。

本项目对上游执行器采用适配和组合，未修改 vendored 上游文件。Docker 镜像中安装的 tg-signer 来源于该本地固定源码目录。
