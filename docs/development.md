# 开发与交付说明

首版实现记录：2026-10-29；包发布接入更新：2026-11-07。代码分别保存在独立子仓库，发布与部署流程见 [release.md](release.md)。

## 已实现

| 模块 | 交付内容 |
| --- | --- |
| 门户 | 响应式登录、目录、中文搜索、课时搜索、标签/制作人/类型筛选、分页、课程详情、章节筛选、制作人及下载资源展示 |
| 用户 | 管理员建号、独立会话、首次改密、改密后撤销会话、停用、角色调整、重置密码、最后一个管理员保护 |
| 访问控制 | 默认已登录可见、指定成员授权、未上架隔离；同一策略覆盖查询、计数、封面、课时、附件和历史版本 |
| 课程管理 | 登记 HTTPS Git 源、分支/凭据引用、启停课程源、上架/下架、推荐、更新任务及状态刷新 |
| 导入与发布 | 固定 Git 提交、仅导出提交中的白名单文件、Schema/语义/文件校验、不可变文件目录、元数据关系表与原始快照、事务切换当前版本 |
| 版本管理 | 历史列表、冲突检测、全包哈希校验后回退、版本撤销、旧版本 24 小时访问宽限、失败保留旧版本、任务幂等和 Worker 中断恢复 |
| 文件服务 | 开发环境由后端发送，生产通过 Nginx X-Accel；支持 HEAD/Range、授权校验与 private/no-store |
| 课程规范 | skill、Schema、数值课程候选清单；API 打包 Schema 并记录其 SHA-256 来源 |
| demo | 2 章、2 分组、2 个已发布课时、1 个计划课时；直线参数实验、判断题、本地封面和 CSV 下载 |
| 工程 | Python/前端锁文件、Alembic 迁移、生成的 OpenAPI/TypeScript 类型、原生本地启动、Dockerfile 与 Compose/Nginx 配置 |

门户文字使用纯文本渲染。课程 JS 仍按“受信任教师代码”处理，同源托管没有提供不受信任内容的脚本隔离。

## 工作区启动

运行根目录 `python3 scripts/dev.py setup`，安装依赖、建立本项目的原生 PostgreSQL 实例、迁移数据库、生成本地管理员并导入 demo。重复执行不会改写管理员密码；导入同一内容会复用已有版本，不自动把曾回退的版本重新激活。

执行 `python3 scripts/dev.py start` 同时启动 API、Worker、Vite。Ctrl+C 关闭这三个进程，数据库保持运行；需要停止数据库时执行 `python3 scripts/dev.py stop-db`。启动脚本不会自动结束占用端口的其他程序。

| 用途 | 地址 / 位置 |
| --- | --- |
| 开发门户 | `http://127.0.0.1:8814` |
| 开发 API | `http://127.0.0.1:8008`，通过门户代理访问以保持同源 |
| PostgreSQL | `127.0.0.1:55438`，独立 `.local/postgres` |
| 开发库 / 后端测试库 | `courseware` / `courseware_test` |
| 浏览器测试 | 前端 58174、API 58110，数据库 `courseware_e2e` |
| 本地配置和管理员信息 | `.local/settings.json`、`.local/admin.json`，权限 0600 |
| 发布文件与临时区 | `.local/storage/releases`、`.local/storage/work` |
| 浏览器截图 | `.local/screenshots/` |

开发数据库仅监听回环地址，但使用 trust 认证，因此同机进程可访问该开发实例。不要放入生产数据或在共享服务器上直接使用这个开发配置。生产使用部署说明中的独立密码与 HTTPS。

通过 frpc 访问时，将流量转发至 `127.0.0.1:8814`，前端继续代理 `/api/` 和 `/courses/`，不需要另外暴露 API 端口。在 `.local/settings.json` 中将 `CW_PUBLIC_ORIGIN` 改为浏览器实际访问的完整来源（协议、域名或 IP、非默认端口，不包含路径）。Vite 会从该配置放行对应主机，后端校验同一来源；修改后重启 `python3 scripts/dev.py start`。HTTPS 公网入口应将 `CW_SECURE_COOKIES` 设置为字符串 `"true"`，即使 frpc 到本机这一段使用 HTTP。公网纯 HTTP 入口需显式设置 `CW_ALLOW_INSECURE_HTTP="true"` 和 `CW_SECURE_COOKIES="false"`；默认不开放此例外，HTTPS 仍要求 Secure Cookie。HTTP 会明文传输密码和会话，来源校验与 CSRF 校验仍保留。切换入口后需在新地址重新登录。

`.local/`、前端依赖/构建产物和 Python 虚拟环境均已忽略。`apps/` 由 Git submodule 固定版本，业务提交分别在子仓库进行，再更新根仓库指针。

## 内容导入

正式 Git 接入：在管理页面登记 slug、允许主机上的 HTTPS `.git` 地址、分支、可选凭据引用，点击同步。Worker 只读取相应分支的确定提交，不执行课程仓库脚本。成功后管理员明确上架，才能进入普通成员目录。

私有仓库在 Worker 环境设置 `CW_GIT_USERNAME_<REF>` 与 `CW_GIT_PASSWORD_<REF>`；引用转为大写，连字符转下划线。例如 `codeup-reader` 对应 `CW_GIT_PASSWORD_CODEUP_READER`。不会把凭据写入源配置、进程命令行或日志。允许的 Git 主机由 `CW_ALLOWED_GIT_HOSTS` 配置。

本地开发可在 `.local/settings.json` 设置 `CW_USE_LOCAL_GIT_CREDENTIALS="true"` 并重启，让未填写凭据引用的仓库复用本机 Git 凭据助手。该选项默认关闭；显式凭据引用优先。Worker 仅向助手读取允许主机对应的凭据，拉取过程仍使用隔离的 Git 配置，凭据不会写入数据库或日志，也不会弹出交互输入；未找到本机凭据时仍可匿名拉取公开仓库。

本地预览是显式 CLI 操作，允许导入尚未提交的可信工作树，记录 `local-preview` 来源与内容哈希，不冒充 Git commit：

```bash
python3 scripts/env-run.py apps/courseware-api uv run courseware validate ../courseware-demo
python3 scripts/env-run.py apps/courseware-api uv run courseware import-local ../courseware-demo --username admin --list
```

该入口不通过 HTTP 暴露。普通管理页面的仓库源拒绝本地路径。生产更新默认使用 Git Worker，确保来源为可追踪的提交。

`numerical-methods` 已按课程仓库提交的清单成功导入，平台不修改课程源仓库。旧 Python 服务无需迁移。

## 验证命令与实际结果

```bash
python3 scripts/dev.py test
python3 scripts/env-run.py apps/courseware-api uv run ruff check src tests
python3 scripts/env-run.py apps/courseware-api uv run alembic check
python3 scripts/dev.py types
cd apps/courseware-web
npm run test:e2e
```

本次完成：22 项后端测试通过，包含真实 Git 对象导出、拒绝未提交文件、凭据文件阻断、模拟导入失败和回退一致性；6 项浏览器测试通过，覆盖 1440×1000 桌面与 390×844 手机；登录和目录页通过 axe 的 WCAG 2 A/AA、2.1 AA 检查。已人工查看目录截图，页面无横向溢出，关键流程无未捕获的浏览器脚本异常。

前端生产构建和 TypeScript 检查通过，Alembic 检查没有未生成的模型迁移。浏览器测试使用独立数据库并清空自己的测试数据，不清空开发库。测试客户端当前有上游 Starlette/httpx 弃用提示，不影响结果。

有本机 Nginx 和 OpenSSL 时还可运行：

```bash
python3 scripts/env-run.py apps/courseware-api uv run python ../../scripts/check-gateway.py
```

该检查临时启动回环地址 HTTPS 网关与 API，并在结束后关闭。已验证生产 Nginx 配置语法、Secure/HttpOnly Cookie、X-Accel 静态文件、HEAD、Range、internal 路径隔离、后端 404 不回退成 SPA，以及登出后文件访问失效。它读取本地管理员文件；若在 UI 改过该密码，应同步本地验证凭据或自行用新账号验证。

## 首版实现与目标架构的具体差异

- 当前 API/Worker 使用扁平模块；不为了目录结构增加包装层。
- 会话空闲时间由 `last_seen_at + idle_hours` 计算；不重复存 idle_expires_at。任务租约由 heartbeat_at 判断。发布目录由 course_id/release_id 计算，不存可任意改写的服务器路径。
- 已就绪版本一次性入库；尚未完成的发布用 sync_jobs 表达，避免把空候选版本暴露给查询。
- 检索使用数据库中的规范化表及当前版本的派生 search_text，配合 pg_trgm/GIN；无外部搜索服务。统计和筛选项在首版从数据库快照计算，大规模课程库时再改为更细的 SQL 聚合。
- 每次导入执行静态契约/文件引用检查。动态 JS 的任意路径无法由静态扫描完全证明，浏览器验证目前由作者测试与平台集成测试承担；尚未给每个生产 Git 提交自动启动隔离浏览器门禁。
- 尚未自动删除历史版本或崩溃遗留的未引用目录。访问宽限与撤销已经生效，物理文件保留以避免误删；部署时需监控磁盘空间。后续清理必须保留当前版本、活动任务、宽限期和回退策略要求的文件。
- webhook、公开注册、SSO、跨设备学习进度仍不在首版范围。
- 提供了容器构建与部署配置，但本机未安装 Docker，未运行容器编排，也未验证真实私有 Codeup 凭据或外部生产部署。原生 PostgreSQL、应用及 Nginx 链路已验证。

首次包发布与安装路径见 [发布部署说明](release.md)。
