#!/bin/sh
set -eu

api_pid=""
web_pid=""

cleanup() {
  if [ -n "$web_pid" ]; then
    kill "$web_pid" 2>/dev/null || true
    wait "$web_pid" 2>/dev/null || true
  fi
  if [ -n "$api_pid" ]; then
    kill "$api_pid" 2>/dev/null || true
    wait "$api_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT HUP INT TERM

export FORGEOPS_DATABASE_URL="sqlite+pysqlite:///./.local/web-smoke.db"
export FORGEOPS_ENVIRONMENT="DEV"
export FORGEOPS_ACTION_ADAPTER="MOCK"

uv run alembic upgrade head
uv run uvicorn forgeops.api:create_app --factory --host 127.0.0.1 --port 18731 \
  >.local/web-smoke-api.log 2>&1 &
api_pid=$!
FORGEOPS_API_PROXY_TARGET="http://127.0.0.1:18731" \
  pnpm --filter @forgeops/web exec vite preview --host 127.0.0.1 --port 14731 \
  >.local/web-smoke-preview.log 2>&1 &
web_pid=$!

attempt=0
until curl --fail --silent http://127.0.0.1:14731/health/ready >/dev/null; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 50 ]; then
    echo "web/API preview did not become ready" >&2
    exit 1
  fi
  sleep 0.1
done

curl --fail --silent --show-error http://127.0.0.1:14731/ | grep 'id="root"' >/dev/null
curl --fail --silent --show-error \
  -H 'X-ForgeOps-Actor: local-web-smoke' \
  -H 'X-Trace-ID: standalone-web-smoke-trace' \
  http://127.0.0.1:14731/v1/platform/status >.local/web-smoke-status.json

uv run python - <<'PY'
import json
from pathlib import Path

status = json.loads(Path('.local/web-smoke-status.json').read_text())
assert status['scope'] == 'LOCAL_SYNTHETIC_ENGINEERING'
assert status['advisoryMode'] is True
assert status['dataMode'] == 'SYNTHETIC_ONLY'
assert status['externalModelEnabled'] is False
assert status['enterpriseApproval'] == 'NOT_GRANTED'
print(json.dumps({
    'testId': 'TEST-OPS-WEB-SMOKE-001',
    'requirementIds': ['REQ-OPS-001', 'REQ-UIX-001'],
    'scope': status['scope'],
    'previewProxiedRealApiState': True,
    'enterpriseApproval': status['enterpriseApproval'],
    'passed': True,
}, indent=2))
PY
