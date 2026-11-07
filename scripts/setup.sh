#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
action="${1:-help}"
service="${2:-all}"
version="${3:-}"
case "$service" in
  backend|frontend|all) ;;
  *) echo 'service: backend | frontend | all' >&2; exit 1 ;;
esac
if [[ "$service" == all ]]; then
  if [[ "$action" == stop ]]; then
    bash scripts/setup.sh "$action" frontend "$version"
    exec bash scripts/setup.sh "$action" backend "$version"
  fi
  case "$action" in
    install-dev|install-prod|upgrade|start|restart|status)
      bash scripts/setup.sh "$action" backend "$version"
      exec bash scripts/setup.sh "$action" frontend "$version" ;;
    *) echo '用法: scripts/setup.sh <install-dev|install-prod|upgrade|rollback|init|start|run|stop|restart|status> <backend|frontend|all> [version]'; exit 1 ;;
  esac
fi
if [[ "$service" == backend ]]; then
  cli=courseware-api
  package=courseware-api
else
  cli=courseware-web
  package=@farfarfun/courseware-web
fi
case "$action" in
  start|run|restart)
    if [[ "$service" == backend ]]; then
      exec "$cli" server "$action" --host "${COURSEWARE_BACKEND_HOST:-127.0.0.1}" --port "${COURSEWARE_BACKEND_PORT:-8008}"
    else
      exec "$cli" server "$action" --host "${COURSEWARE_FRONTEND_HOST:-127.0.0.1}" --port "${COURSEWARE_FRONTEND_PORT:-8817}" --backend "http://${COURSEWARE_BACKEND_HOST:-127.0.0.1}:${COURSEWARE_BACKEND_PORT:-8008}"
    fi ;;
  stop|status) exec "$cli" server "$action" ;;
  init)
    [[ "$service" == backend ]] || { echo '仅 backend 支持 init' >&2; exit 1; }
    exec "$cli" init ;;
  install-dev|install-prod|upgrade|rollback)
    [[ "$action" != rollback || -n "$version" ]] || { echo 'rollback 需要显式版本号' >&2; exit 1; }
    if [[ "$action" == install-prod && -z "$version" ]] && command -v "$cli" >/dev/null; then
      echo "$cli 已安装；更新请用 upgrade"; exit 0
    fi
    if [[ "$service" == backend ]]; then
      if [[ "$action" == install-dev ]]; then
        mkdir -p .local
        uv export --project apps/courseware-api --frozen --no-dev --no-emit-project -o .local/api-constraints.txt
        uv tool install --reinstall ./apps/courseware-api --constraint .local/api-constraints.txt
      else
        requirement="$package"; [[ -z "$version" ]] || requirement="$package==$version"
        uv tool install --reinstall "$requirement" --index 'https://farfarfun-cn-hangzhou.devops.aliyuncs.com/packages/api/protocol/pypi/funpy/'
      fi
    else
      if [[ "$action" == install-dev ]]; then
        mkdir -p .local
        (cd apps/courseware-web && npm ci && npm run build && npm pack --pack-destination ../../.local)
        archive=$(node -p "'./.local/farfarfun-courseware-web-' + require('./apps/courseware-web/package.json').version + '.tgz'")
        npm install --global "$archive"
      else
        npm install --global "$package@${version:-latest}"
      fi
    fi
    echo '安装完成；配置完成后使用 restart 启用安装的版本。' ;;
  *) echo "不支持的操作: $action" >&2; exit 1 ;;
esac
