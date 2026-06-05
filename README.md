# lgtm-oncall-mcp

[![CI](https://github.com/SaputraUta/lgtm-oncall-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/SaputraUta/lgtm-oncall-mcp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

> An MCP server that gives an LLM agent a typed, auditable on-call surface on top of the LGTM stack (**L**oki · **G**rafana · **T**empo · **M**imir) plus your VCS (Bitbucket Cloud or GitHub).

Replaces broad shell-and-SSH agent power with narrow, schema-checked tools. Same toolbox works for autonomous on-call agents (e.g. Hermes responding to Grafana webhooks via Telegram) and interactive copilots (Claude Code, Claude Desktop, Cursor, …).

> Status: **alpha**. The core flow works end-to-end. Interfaces may still shift.

---

## What it gives the agent

Three groups, 16 tools total:

**Senses** (read-only, query Mimir / Loki / Grafana / your VCS):
- `ping`
- `get_cpu_usage(env)`
- `get_memory_usage(env)`
- `get_disk_usage(env)`
- `get_error_rate(env)`
- `get_latency_p95(env)`
- `get_active_alerts()`
- `search_logs(env, contains, minutes, limit)`
- `get_recent_deploys(env, limit)`
- `get_commit_diff(sha, max_chars)`
- `get_file_commits(path, limit)`

**Vision** (Grafana screenshots via headless Chrome):
- `list_dashboards()`
- `list_panels(dashboard_uid)`
- `capture_dashboard(uid, env, minutes)`
- `capture_panel(dashboard_uid, panel_id, env, minutes)`

**Hands** (destructive — the agent must confirm with the user before calling):
- `rollback_deploy(env, target_tag)` — reruns the deploy pipeline for an existing tag
- `propose_fix_pr(branch, file_path, new_content, title, body, base_branch)` — opens a PR with a single-file fix

---

## Quickstart

Requires Python 3.11+ and a running LGTM stack you can reach.

```bash
# 1. Install
pip install lgtm-oncall-mcp
python -m playwright install chromium

# 2. Configure
cp .env.example .env
$EDITOR .env      # fill in GRAFANA_URL, GRAFANA_TOKEN, MIMIR_DS_UID, LOKI_DS_UID, VCS_*

# 3. Run
set -a; source .env; set +a
lgtm-oncall-mcp
# → MCP server listening on http://127.0.0.1:8765/mcp
```

Smoke test from another shell:

```bash
curl -s http://127.0.0.1:8765/mcp -X POST \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"smoke","version":"1"}}}'
```

You should get a JSON response listing capabilities.

---

## Connecting MCP clients

### Claude Code (CLI)

```bash
claude mcp add lgtm-oncall --transport http http://localhost:8765/mcp
claude mcp list   # should print "✓ Connected"
```

### Claude Desktop (GUI)

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "lgtm-oncall": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://localhost:8765/mcp"]
    }
  }
}
```

Fully quit Claude Desktop (Cmd+Q) and reopen.

### Generic / other clients

Any MCP client that speaks streamable HTTP can connect to `http://<host>:8765/mcp`. If you set `MCP_BEARER_TOKEN`, the client must send `Authorization: Bearer <token>`.

### Autonomous on-call agent (e.g. Hermes by Nous Research)

```bash
hermes mcp add lgtm-oncall --url http://127.0.0.1:8765/mcp
hermes mcp test lgtm-oncall   # lists all tools
```

Wire your Grafana alert contact point to the agent's webhook, and the agent will pick up the alert and decide which tools to call.

---

## Configuration reference

All configuration is environment-driven. Copy `.env.example` to `.env` to start.

| Var | Required | Default | Purpose |
|---|---|---|---|
| `GRAFANA_URL` | yes | — | Base URL of your Grafana |
| `GRAFANA_TOKEN` | yes | — | Service-account token |
| `MIMIR_DS_UID` | yes | — | Mimir/Prometheus datasource UID |
| `LOKI_DS_UID` | yes | — | Loki datasource UID |
| `GRAFANA_CA_CERT_PATH` | no | — | Path to pinned cert (recommended for self-signed) |
| `ENV_LABEL_KEY` | no | `env` | Label key for environment |
| `TEAM_LABEL_KEY` | no | `team` | Label key for team |
| `TEAM_LABEL_VALUE` | no | (empty) | Restrict queries to one team |
| `VCS_PROVIDER` | no | `bitbucket` | `bitbucket` or `github` |
| `BITBUCKET_EMAIL` | bb | — | Email for Atlassian API token Basic auth |
| `BITBUCKET_API_TOKEN` | bb | — | Atlassian API token (ATAT…) |
| `BITBUCKET_WORKSPACE` | bb | — | e.g. `mycompany` |
| `BITBUCKET_REPO_SLUG` | bb | — | e.g. `my-app` |
| `GITHUB_TOKEN` | gh | — | Fine-grained PAT |
| `GITHUB_OWNER` | gh | — | e.g. `myorg` |
| `GITHUB_REPO` | gh | — | e.g. `my-app` |
| `GITHUB_DEPLOY_WORKFLOW` | gh | `deploy.yml` | Workflow file for `rollback_deploy` |
| `GITHUB_API_BASE` | no | `https://api.github.com` | For GitHub Enterprise |
| `DEPLOY_TAG_PROD_REGEX` | no | `^v\d+\.\d+\.\d+$` | Tags that match → prod |
| `DEPLOY_TAG_NONPROD_SUFFIX_DEV` | no | `-dev` | Dev tag suffix |
| `DEPLOY_TAG_NONPROD_SUFFIX_STAGING` | no | `-stag` | Staging tag suffix |
| `MCP_HOST` | no | `127.0.0.1` | Bind address |
| `MCP_PORT` | no | `8765` | Port |
| `MCP_BEARER_TOKEN` | no | (empty) | If set, required in `Authorization` header |

---

## Architecture

```
        ┌──────────┐   ┌──────────┐   ┌─────────────┐
        │  Claude  │   │  Claude  │   │  Autonomous │
        │   Code   │   │ Desktop  │   │  agent      │
        │  (CLI)   │   │  (GUI)   │   │ (Hermes, …) │
        └────┬─────┘   └────┬─────┘   └──────┬──────┘
             └─────────────┬┴────────────────┘
                           ▼
              ┌─────────────────────────┐
              │  lgtm-oncall-mcp        │
              │  FastMCP HTTP · 16 tools │
              │  (senses · vision · hands)│
              └────┬──────────┬─────────┘
                   │          │
              ┌────▼─────┐  ┌─▼──────────┐
              │ Grafana  │  │ Bitbucket  │
              │  + Mimir │  │   Cloud    │
              │  + Loki  │  │  OR GitHub │
              └──────────┘  └────────────┘
```

The server is stateless. Run it close to your LGTM stack (in the same VPC if Mimir/Loki are private). Agents can be anywhere as long as they reach the server.

---

## Security notes

- **Destructive tools are gated by the agent's policy**, not by the server. Today, `rollback_deploy` and `propose_fix_pr` are MCP-callable by anyone who can reach the server. Use SOUL.md / system-prompt instructions on the agent side to require user confirmation. *(Server-side approval gates are on the roadmap.)*
- **Bearer-token auth** (`MCP_BEARER_TOKEN`) is supported but optional. If your transport isn't loopback or SSH-tunneled, **set the token**.
- **Cert pinning** (`GRAFANA_CA_CERT_PATH`) is supported for self-signed Grafana setups. Prefer pinning over `verify=False`.
- **No secrets are written to disk** by the server. Tokens live only in environment variables.

---

## Development

```bash
git clone https://github.com/SaputraUta/lgtm-oncall-mcp.git
cd lgtm-oncall-mcp
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m playwright install chromium

pytest      # tests
ruff check  # lint
```

### Try it without an AWS account

A local docker-compose brings up Grafana + Mimir + Loki + a node-exporter so the sense tools have real data:

```bash
docker compose up -d
open http://localhost:3000        # Grafana — anonymous Admin

# In another shell:
set -a; source .env.docker; set +a
python -m lgtm_oncall_mcp
# → MCP server listening, ready for any client
```

See `examples/docker/` for the Mimir + Grafana config files used by the stack.

---

## Why this exists

If you give a generic agent shell + SSH, it's effective. It's also terrifying to imagine running unattended at 3am.

The LGTM stack already has all the data an on-call human would look at. The deploy pipeline already has the actions a human would take. What's missing is a **typed, auditable surface** the agent can use without inheriting full root.

That's this server: senses + vision + hands as concrete tools, defined once, consumed by any MCP client.

---

## License

MIT — see [LICENSE](./LICENSE).
