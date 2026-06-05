# Claude Code (CLI) — integration

[Claude Code](https://docs.claude.com/en/docs/claude-code/overview) is Anthropic's terminal-based coding agent. It speaks streamable-HTTP MCP natively.

## Prerequisites

- `claude` CLI installed and you can run `claude` once successfully.
- `lgtm-oncall-mcp` server running and reachable from your machine.
  - Either locally (`python -m lgtm_oncall_mcp` → `http://127.0.0.1:8765/mcp`)
  - Or remote (e.g. via `aws ssm start-session ... AWS-StartPortForwardingSession`).

## Register the server

```bash
claude mcp add lgtm-oncall \
  --transport http \
  http://127.0.0.1:8765/mcp
```

If the server has `MCP_BEARER_TOKEN` set:

```bash
claude mcp add lgtm-oncall \
  --transport http \
  http://127.0.0.1:8765/mcp \
  --header "Authorization: Bearer <YOUR_TOKEN>"
```

## Verify

```bash
claude mcp list
```

You should see:

```
lgtm-oncall: http://127.0.0.1:8765/mcp (HTTP) - ✓ Connected
```

## Try it

Open a Claude Code session and ask, in any phrasing:

- `get cpu usage on staging`
- `what's the error rate on prod right now?`
- `show me the last 5 deploys for staging`
- `screenshot the error rate panel on staging, last 15 min`

Claude will discover the 17 tools and call them as needed.

## Destructive actions

`propose_rollback` and `propose_pr_change` are callable, but `confirm_*` requires the `proposal_id` returned by the propose step. A typical flow looks like:

```
You:      rollback staging to v0.0.36-stag
Claude:   [calls propose_rollback] → got proposal_id abc123, expires in 60s.
          Confirm rollback of staging to v0.0.36-stag?
You:      yes
Claude:   [calls confirm_rollback(abc123)] → pipeline triggered (build 266).
```

If you don't confirm within `PROPOSAL_TTL_SECONDS` (default 60s), the proposal expires and Claude will have to re-propose.

## Troubleshooting

**`Connection refused`** — the server isn't running, or your SSM tunnel dropped. Restart both.

**`401 Unauthorized`** — server has `MCP_BEARER_TOKEN` set but you didn't include the `--header` flag. Re-register with the header.

**Claude doesn't seem to know about the tools** — tools are discovered on each session start. Restart Claude Code.

## Remove

```bash
claude mcp remove lgtm-oncall
```
