#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/dev.py test
python3 scripts/env-run.py apps/courseware-api uv run ruff check src tests
(cd apps/courseware-web && npm run test:cli && npm run test:e2e)
