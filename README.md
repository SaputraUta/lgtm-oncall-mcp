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

### Always required

| Var | Default | Purpose |
|---|---|---|
| `GRAFANA_URL` | — | Base URL of your Grafana |
| `GRAFANA_TOKEN` | — | Grafana service-account token (Viewer scope is enough) |
| `MIMIR_DS_UID` | — | Mimir/Prometheus datasource UID in Grafana |
| `LOKI_DS_UID` | — | Loki datasource UID in Grafana |
| `VCS_PROVIDER` | `bitbucket` | Pick one: `bitbucket` or `github` |

### Required if `VCS_PROVIDER=bitbucket`

| Var | Default | Purpose |
|---|---|---|
| `BITBUCKET_EMAIL` | — | Email associated with your Atlassian API token |
| `BITBUCKET_API_TOKEN` | — | Atlassian API token (starts with `ATAT…`) — **not** a username/password |
| `BITBUCKET_WORKSPACE` | — | e.g. `mycompany` (the `<workspace>` in `bitbucket.org/<workspace>/<repo>`) |
| `BITBUCKET_REPO_SLUG` | — | e.g. `my-app` |

Token scopes you need (Atlassian → Manage account → API tokens → Create with scopes):
- `read:repository:bitbucket`
- `read:pullrequest:bitbucket`
- `write:repository:bitbucket` *(only if you use `propose_fix_pr`)*
- `write:pullrequest:bitbucket` *(only if you use `propose_fix_pr`)*
- `read:pipeline:bitbucket`
- `write:pipeline:bitbucket` *(only if you use `rollback_deploy`)*

### Required if `VCS_PROVIDER=github`

| Var | Default | Purpose |
|---|---|---|
| `GITHUB_TOKEN` | — | Fine-grained PAT scoped to ONE repo |
| `GITHUB_OWNER` | — | e.g. `myorg` or your username |
| `GITHUB_REPO` | — | e.g. `my-app` |
| `GITHUB_DEPLOY_WORKFLOW` | `deploy.yml` | The workflow file `rollback_deploy` dispatches. Must exist at `.github/workflows/<name>` with `on: workflow_dispatch` |
| `GITHUB_API_BASE` | `https://api.github.com` | Override only for GitHub Enterprise |

PAT permissions you need (GitHub → Settings → Developer settings → Fine-grained tokens):
- **Contents**: read *(+ write only if you use `propose_fix_pr`)*
- **Pull requests**: read *(+ write only if you use `propose_fix_pr`)*
- **Actions**: read *(+ write only if you use `rollback_deploy`)*

The `GITHUB_DEPLOY_WORKFLOW` must define `workflow_dispatch` with an `env` input. Minimal skeleton:

```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  workflow_dispatch:
    inputs:
      env:
        description: 'Environment'
        required: true
        type: string
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: ./scripts/deploy.sh "${{ inputs.env }}"
```

### Optional

| Var | Default | Purpose |
|---|---|---|
| `GRAFANA_CA_CERT_PATH` | — | Pin Grafana's TLS cert to a file (recommended for self-signed) |
| `ENV_LABEL_KEY` | `env` | Label key in Mimir/Loki that identifies environment |
| `TEAM_LABEL_KEY` | `team` | Label key for team |
| `TEAM_LABEL_VALUE` | (empty) | Restrict queries to one team — leave empty to skip team filtering |
| `DEPLOY_TAG_PROD_REGEX` | `^v\d+\.\d+\.\d+$` | Regex that matches prod tags |
| `DEPLOY_TAG_NONPROD_SUFFIX_DEV` | `-dev` | Dev tag suffix |
| `DEPLOY_TAG_NONPROD_SUFFIX_STAGING` | `-stag` | Staging tag suffix |
| `MCP_HOST` | `127.0.0.1` | Bind address (use `0.0.0.0` only with `MCP_BEARER_TOKEN`) |
| `MCP_PORT` | `8765` | Port |
| `MCP_BEARER_TOKEN` | (empty) | Shared secret. If set, every request must include `Authorization: Bearer <token>`. Generate with `openssl rand -hex 32`. |

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
