# Courseware Dev

多门交互式课程的统一入口。这个工作区负责课程目录、访问控制和发布流程；每门课程的页面、图片、程序与测试仍由自己的仓库维护。

> 当前状态：首版应用已实现并完成本地验证。项目名称为 `courseware-dev`；本地工作目录可与仓库名称不同。

## 本地运行

需要 Python 3.12+、uv、Node.js 22.12+ 和 PostgreSQL 18（`initdb`、`pg_ctl`、`psql` 在 PATH 中），并先在 `apps/` 下分别检出四个子仓库。

```bash
python3 scripts/dev.py setup
python3 scripts/dev.py start
```

打开 **http://127.0.0.1:8814**。`setup` 创建本项目独立的 PostgreSQL 实例（55438 端口）、数据库、随机管理员密码，并导入示范课程。不会使用或清空系统默认数据库。

本地账号信息保存在未跟踪的 `.local/admin.json`，可以通过 `python3 scripts/dev.py credentials` 查看。密码不内置在源码中；`setup` 再次执行不会重置已有账号密码。本地数据库使用仅监听回环地址的开发认证配置，不用于生产部署。

```bash
python3 scripts/dev.py test                 # 独立测试数据库 + 前端生产构建
python3 scripts/dev.py types                # 导出 OpenAPI 并更新前端类型
cd apps/courseware-web
npm run test:e2e                            # 独立数据库/端口，桌面与手机浏览器测试
```

浏览器测试默认使用本机 Chrome。详情见[开发与交付说明](docs/development.md)，生产配置见[部署说明](deploy/README.md)。

## 包发布与服务安装

采用 funfluid 的 Python/npm 包发布模式，提供 `courseware-api`、`courseware-web` 服务命令，以及 `scripts/setup.sh` 编排入口。发布流程、数据库初始化、frpc 配置和 fundeploy 接入见[发布部署说明](docs/release.md)。

## 设计文档

以下文档细化并更新了原始草案，以这些约定作为后续开发依据：

- [整体架构](docs/architecture.md)：前后端、数据库、多用户登录、检索、同步发布、部署及实施阶段。
- [课程仓库标准 v1](apps/courseware-skill/references/course-repository-standard.md)：目录、相对链接、元数据、制作人、章节与课时、发布白名单。
- [数据与 API 约定](docs/data-and-api.md)：数据表、统计口径、访问权限及接口边界。
- [首门课程接入评估](docs/numerical-methods-assessment.md)：实际案例检查结果、需要迁移的内容和验收标准。
- [course.json Schema](apps/courseware-skill/schemas/course.schema.json) 与 [数值计算方法清单示例](apps/courseware-skill/examples/numerical-methods.course.json)：可校验的课程元数据契约及接入参考。

已采用 Vue 3 + TypeScript + Vite 前端、FastAPI 后端、PostgreSQL 数据库、独立更新 Worker、Nginx 静态资源服务。依赖版本由各应用的锁文件固定。

本仓库是开发统筹仓库，`apps/` 下通过 Git submodule 固定各独立仓库的提交。首次检出执行 `git submodule update --init --recursive`；业务提交分别在对应仓库进行，根仓库记录版本组合。

## 仓库分工

| 仓库 | 负责内容 |
| --- | --- |
| `courseware-dev` | 整体架构、跨仓库接口、开发编排、集成验收与部署 |
| `apps/courseware-web` | 门户与管理前端 |
| `apps/courseware-api` | API、课程数据库、账号会话、检索、导入 Worker 与发布工具 |
| `apps/courseware-skill` | 课程制作 skill、课程仓库标准、JSON Schema 与参考清单 |
| `apps/courseware-demo` | 标准示范课程，验证新课程制作与门户接入流程 |
| 每门课程仓库 | 本课程的 Web 页面、资源、源程序、测试和课程说明 |

当前本地已接入 `courseware-demo` 和 `numerical-methods`。数值计算方法课程位于 Codeup：

```text
https://farfarfun-cn-hangzhou.devops.aliyuncs.com/codeup/interactive-courseware/numerical-methods.git
```

入口仓库位于 GitHub，课程仓库位于 Codeup；发布程序通过各课程配置中的仓库地址获取内容，不要求它们使用同一个 Git 平台。

## 访问方式

总网站展示课程列表，课程入口使用稳定路径：

```text
/
/courses/numerical-methods/
/courses/numerical-methods/web/index.html
```

课程稳定入口跳转到当前版本的 `web/index.html`，实际文件位于 `/courses/<slug>/releases/<release_id>/` 下，保留仓库内部相对目录。旧的无版本文件路径兼容跳转到当前版本，避免发布过程中 HTML 与资源混用不同版本。发布文件由 `course.json` 中的精确白名单决定，不开放整个课程仓库；详见课程仓库标准。

统一登录应由总网站的服务端处理，并覆盖课程目录、每门课程页面及其静态资源。直接下载并打开 HTML 文件不会经过网站验证，所以需要保护的课程仓库和发布包也应限制访问。这个入口仓库是公开仓库，账号密码、Git 凭据及会话密钥不能提交到这里，应由部署环境提供。

## 课程配置

门户数据库维护仓库接入配置；以下展示配置字段，不是 `course.json` 内容：

```json
{
  "slug": "numerical-methods",
  "repo": "https://farfarfun-cn-hangzhou.devops.aliyuncs.com/codeup/interactive-courseware/numerical-methods.git",
  "branch": "master",
  "manifest_path": "course.json",
  "credential_ref": "codeup-course-reader"
}
```

`slug` 用于生成稳定链接；仓库地址、分支和凭据引用由服务端更新程序使用。课程名、简介、封面、制作人、章节和课时必须来自课程仓库根目录的 `course.json`，同步进入数据库，用于检索与展示。凭据值由部署环境提供，不存入课程清单或源码。

## 更新与发布

1. 教师在课程仓库中修改内容、运行该课程的测试并推送。
2. 总网站的更新程序在服务器上获取指定分支，检查仓库与入口文件是否有效。
3. 将通过检查的版本发布到该课程的独立目录，再切换线上指向；失败时继续提供旧版本。
4. 记录课程名、提交号、更新时间和结果，便于核对及回退。

首版支持管理员命令和管理页面的同步操作；按钮只向服务端提交更新任务，由独立 Worker 执行。仓库推送后自动触发留待后续实现。访客浏览页面时不执行 `git pull`，不同课程可以独立更新。

## 实施顺序

1. 评审并确定课程标准、数据模型和前后端接口。
2. 建立前后端、数据库及多用户登录骨架，默认所有课程数据和文件需要授权访问。
3. 接入 `numerical-methods`，完成校验、元数据入库、版本发布、检索与展示。
4. 完成失败恢复、回退及部署验收，再按同一标准接入第二门课程。

现有 `numerical-methods` 仓库的密码验证只作用于它自己的 Python 服务。迁入总网站后，应由总网站统一验证访问，并避免同时公开一个可绕过总网站的课程服务地址。
