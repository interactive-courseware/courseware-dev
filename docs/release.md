# Courseware 包发布与部署

Courseware 按 funfluid 的多仓库模式交付：根工作区固定子仓库提交，共享版本写在 `scripts/funbuild.toml`。后端发布 `courseware-api` 到 funpy，前端发布 `@farfarfun/courseware-web` 到 funnpm。课程规范与 demo 是 Git 子模块，不作为 Python/npm 包发布。

## 发布

安装 `funbuild`、uv、Node.js，并配置本机 `~/.pypirc` 的 `funpy` 和 npm 的 `@farfarfun` registry 凭据。凭据不进入仓库。

```bash
git submodule update --init --recursive
funbuild build --dry-run --version 0.1.0
bash scripts/build.sh --version 0.1.0 'feat: release courseware 0.1.0'
```

脚本先跑后端、前端构建、CLI 与浏览器检查，再调用 funbuild 发布。funbuild 会拉取、更新版本、构建、发布包、提交推送并创建版本标签。只使用尚未发布的版本号；不要重跑已经成功发布的包版本。部分失败时检查制品库和远端标签，使用 `--apps` 限定尚未完成的应用，禁止覆盖已发布内容。发布后从制品库安装并验证版本、迁移、API/Worker 和前端代理，记录准确提交与产物哈希。

## 安装与初始化

```bash
uv tool install courseware-api --index https://farfarfun-cn-hangzhou.devops.aliyuncs.com/packages/api/protocol/pypi/funpy/
npm install --global @farfarfun/courseware-web
courseware-api init
```

第一次 `init` 只生成 `~/.farfarfun/courseware/backend/config.json`（0600），不覆盖现有配置。编辑其中的 PostgreSQL 连接、公开入口、存储目录及 Cookie 设置后再执行：

```bash
courseware-api init
courseware-api create-admin admin
courseware-api server start
courseware-web server start
```

后端依赖外部 PostgreSQL；命令不会自动安装数据库或清空已有数据。数据库迁移随 wheel 发布，离开源码目录也能初始化。后端 supervisor 同时管理 API 和 Worker，任一退出都会停止整组，防止同步进程失效却显示服务正常。

新安装的默认入口为 `http://127.0.0.1:8817`，API 为 `127.0.0.1:8008`。开发 Vite 仍使用 8814。前端 CLI 运行构建后的静态文件，代理 `/api`、`/courses`、`/health`；课程文件授权仍由 API 完成。`/version.json` 返回实际运行的前端包版本。

配置路径可由 `CW_CONFIG_FILE`、`CW_WEB_CONFIG_FILE` 或 CLI `--config` 覆盖。前端首次启动生成 `~/.farfarfun/courseware/frontend/config.json`；`--host`、`--port`、`--backend` 可覆盖监听和代理地址。后端 `CW_*` 环境变量优先于配置文件。日志和进程控制信息保存在配置文件旁，升级不会覆盖配置、课程文件或数据库。

原有 frpc 入口保持 `http://8.130.133.114:18814`、本机前端 8814：设置前端配置 `port=8814`，后端 `CW_PUBLIC_ORIGIN` 为公网地址，并显式设置 `CW_ALLOW_INSECURE_HTTP=true`、`CW_SECURE_COOKIES=false`。HTTP 会明文传输会话；HTTPS 入口使用 Secure Cookie。本机私有 Git 凭据复用需显式开启 `CW_USE_LOCAL_GIT_CREDENTIALS=true`，服务器可改用只读凭据引用。

## fundeploy

包含 Courseware 声明的 fundeploy 版本支持：

```bash
fundeploy service courseware install 0.1.0
# 首次安装按上述流程配置数据库、迁移、建号
fundeploy service courseware start
fundeploy service courseware status
fundeploy service courseware stop
```

该声明按顺序启动后端与前端，前端自动获得 API 地址。可用 `COURSEWARE_BACKEND_PORT`、`COURSEWARE_FRONTEND_PORT` 调整端口。已有 8814/frpc 环境使用：

```bash
COURSEWARE_FRONTEND_PORT=8814 fundeploy service courseware start
COURSEWARE_FRONTEND_PORT=8814 fundeploy service courseware status
```

fundeploy 的默认前端端口 8817 避开现有 funlesson 的 8814。原服务占用时不要强制释放它的端口。也可用根脚本 `scripts/setup.sh <action> <backend|frontend|all> [version]` 管理已安装包；`install-dev` 从源码构建真实包，`install-prod` 从制品库安装，`upgrade`/`rollback` 换包后需显式重启。固定版本回退必须同时考虑数据库迁移兼容性。

## 备份与回退

换包前暂停写入，同批备份 PostgreSQL、课程存储目录和配置文件；确认备份完成后再迁移或启动新包。包回退不会回退数据库。首版无上一版已发布包，回退点为部署前备份及保留的开发启动入口。Docker/Nginx 是另一条可选部署路径，见 `deploy/README.md`，本次包发布不代表 Docker 已验证。
