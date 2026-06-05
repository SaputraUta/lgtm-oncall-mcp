#!/usr/bin/env bash
# Smoke test — exercises every tool category against a running MCP server.
#
# Usage:
#   ./scripts/smoke.sh [ENV]
#
# ENV defaults to "staging". Set MCP_URL if not http://127.0.0.1:8765/mcp.
# Set MCP_BEARER_TOKEN if your server requires auth.
#
# What it does:
#   1. initialize handshake
#   2. tools/list — confirm all 17 tools are registered
#   3. one call per category (senses, vision-list, vcs-list-tags)
#   4. propose_rollback (no execute) — confirms guardrails wire
#
# Does NOT call confirm_rollback or confirm_pr_change — that would actually
# deploy something. Read-only smoke.

set -euo pipefail

ENV="${1:-staging}"
URL="${MCP_URL:-http://127.0.0.1:8765/mcp}"
AUTH_HEADER=()
if [[ -n "${MCP_BEARER_TOKEN:-}" ]]; then
  AUTH_HEADER=(-H "Authorization: Bearer ${MCP_BEARER_TOKEN}")
fi

REQ_ID=0
call() {
  local method="$1"
  local params="$2"
  REQ_ID=$((REQ_ID + 1))
  curl -sk -X POST "$URL" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    "${AUTH_HEADER[@]}" \
    -d "{\"jsonrpc\":\"2.0\",\"id\":${REQ_ID},\"method\":\"${method}\",\"params\":${params}}"
}

tool() {
  local name="$1"
  local args="$2"
  echo
  echo "=== ${name} ==="
  call "tools/call" "{\"name\":\"${name}\",\"arguments\":${args}}" | sed -E 's/("token"|"api_token"|"secret")"[^"]*"/\1:"<redacted>"/g'
}

echo "=== initialize ==="
call "initialize" '{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"smoke","version":"0"}}' \
  | head -200

echo
echo "=== tools/list (expect 17 tools) ==="
call "tools/list" '{}' | python3 -c 'import sys,json,re
raw = sys.stdin.read()
# strip SSE prefix if any
m = re.search(r"\{.*\}", raw, re.S)
if not m:
    print("no json found"); sys.exit(1)
data = json.loads(m.group(0))
tools = [t["name"] for t in data["result"]["tools"]]
print(f"{len(tools)} tools:")
for t in sorted(tools):
    print(f"  - {t}")'

tool ping '{}'
tool get_cpu_usage "{\"env\":\"${ENV}\"}"
tool get_memory_usage "{\"env\":\"${ENV}\"}"
tool get_disk_usage "{\"env\":\"${ENV}\"}"
tool get_error_rate "{\"env\":\"${ENV}\"}"
tool get_latency_p95 "{\"env\":\"${ENV}\"}"
tool get_active_alerts '{}'
tool search_logs "{\"env\":\"${ENV}\",\"contains\":\"error\",\"minutes\":60,\"limit\":3}"
tool get_recent_deploys "{\"env\":\"${ENV}\",\"limit\":3}"
tool list_dashboards '{}'
# get_commit_diff + get_file_commits need real shas/paths; skip in generic smoke.

# Guardrails wire — propose only, do NOT confirm
tool propose_rollback "{\"env\":\"${ENV}\",\"target_tag\":\"DUMMY-WILL-FAIL-VALIDATION\"}" || true

echo
echo "=== done. Review output above. ==="
echo "If every call returned valid JSON (no '\"error\"' top-level), tools are wired."
