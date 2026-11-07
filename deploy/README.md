# 生产部署

Docker Compose 负责 PostgreSQL、一次性迁移、API、Worker 与 Nginx 前端。只有 Nginx 的 80/443 端口对外开放；发布目录通过 API 授权后由 internal location 发送。

## 准备与启动

1. 在根工作区检出四个独立仓库，固定需要部署的 web/API 提交。构建使用各自锁文件。
2. 复制 `deploy/env.example` 到根 `.env`，填写 HTTPS 域名、TLS 证书目录、数据库密码和会话密钥。证书目录包含 `fullchain.pem` 与 `privkey.pem`。可用 `openssl rand -hex 32` 分别生成两个独立密钥；数据库密码使用 URL 安全值。
3. 私有课程仓库的只读凭据放在 `.env` 的 Worker 专用 `CW_GIT_*` 变量中，平台数据库只存引用名称。
4. 执行：

```bash
docker compose --env-file .env -f deploy/compose.yml config --quiet
docker compose --env-file .env -f deploy/compose.yml up -d --build
docker compose --env-file .env -f deploy/compose.yml exec api courseware create-admin admin
```

最后一个命令交互式输入管理员密码，不使用默认密码。迁移服务先创建并分配存储目录权限、执行 Alembic，API 和 Worker 再启动。API 只读挂载课程卷；Worker 可写，Nginx 只读。

登录后登记课程仓库、同步、检查版本，然后上架。首次部署不自动拉取私有课程或公开本地 preview。

容器内 Git 操作关闭隐式凭据 helper 和 HTTP 重定向，只允许配置的 HTTPS 主机。课程程序不会在服务器执行；本版只接入可信教师的 JavaScript 内容。

## 更新

先备份，再检出经过集成测试的应用提交，重新执行 `up -d --build`。检查 `/health/ready` 和 Worker 日志。记录部署使用的提交与镜像摘要；不要把主分支名称当作可恢复版本。

课程更新使用后台的“同步”，与应用部署独立。状态到“更新完成”才代表发布成功；失败保留原版本。更新同一已存在内容不会强行激活曾经回退的版本。

## 备份与恢复

必须同时备份 PostgreSQL 和发布文件卷，单独备份一项不足以恢复课程。以下在维护窗口执行，停止新写入后保存一致备份：

```bash
mkdir -p .local/backups
docker compose --env-file .env -f deploy/compose.yml stop web api worker
docker compose --env-file .env -f deploy/compose.yml exec -T db pg_dump -U courseware -d courseware -Fc > .local/backups/courseware.dump
docker compose --env-file .env -f deploy/compose.yml run --rm --no-deps --entrypoint tar worker -C /srv/courseware -czf - releases > .local/backups/releases.tgz
docker compose --env-file .env -f deploy/compose.yml up -d
```

备份成功后把两个文件作为同一批次保存到服务器外。环境密钥和只读凭据使用独立的受保护备份，不混入课程发布包。

恢复应先在新环境演练：建立空数据库/发布卷，导入匹配的数据库备份、解包 releases 并设置 Worker 用户 10001 的权限；核对当前版本的文件校验和，再启动服务。对已有环境使用 `pg_restore --clean` 会删除现有数据库对象，因此恢复前保留现场备份并确认目标环境。数据库结构升级后，不要只回滚应用镜像而忽略迁移兼容性。

## 运维边界

发布前有文件数、包大小、Git 拉取时长/大小和磁盘剩余空间限制；网络拉取大小通过运行时监测限制，严格的磁盘配额可在宿主机/容器层额外设置。失败发布可能留下未引用的版本目录，首版保守保留，不自动删除。监控数据库、磁盘、同步失败和 Worker 心跳。

当前已通过本机原生 Nginx/TLS/X-Accel 集成验证；Docker 编排和远程服务器部署尚未执行。这些配置需要在目标环境验证证书、DNS、卷权限和真实仓库凭据。
