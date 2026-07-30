#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$script_dir/.."

api_pid=""

cleanup() {
  if [ -n "$api_pid" ]; then
    kill "$api_pid" 2>/dev/null || true
    wait "$api_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT HUP INT TERM

playwright_run_id="$$"
export FORGEOPS_DATABASE_URL="sqlite+pysqlite:////tmp/forgeops-playwright-${playwright_run_id}.db"
export FORGEOPS_ENVIRONMENT="DEV"
export FORGEOPS_ACTION_ADAPTER="MOCK"

uv run alembic upgrade head >/tmp/forgeops-playwright-migration-${playwright_run_id}.log 2>&1
uv run uvicorn forgeops.api:create_app --factory --host 127.0.0.1 --port 19801 \
  >/tmp/forgeops-playwright-api-${playwright_run_id}.log 2>&1 &
api_pid=$!

FORGEOPS_API_PROXY_TARGET="http://127.0.0.1:19801" \
  pnpm --filter @forgeops/web exec vite --host 127.0.0.1 --port 19802
