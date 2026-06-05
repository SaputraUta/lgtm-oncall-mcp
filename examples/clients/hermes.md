# Hermes Agent (Nous Research) — integration

[Hermes Agent](https://github.com/NousResearch/hermes-agent) is an autonomous, MCP-native agent that can receive webhooks, talk to chat platforms (Telegram, Discord, Slack), and run a continuous reasoning loop. Pairing it with `lgtm-oncall-mcp` turns it into an on-call engineer.

## Prerequisites

- Hermes `>= 0.14.0` installed (`hermes --version`).
- `hermes mcp test ...` works against any MCP server already.
- `lgtm-oncall-mcp` server running on the same box (recommended — Hermes hits loopback) or reachable over the network.

## Register the server

If Hermes and `lgtm-oncall-mcp` are on the same EC2 (recommended):

```bash
hermes mcp add lgtm-oncall --url http://127.0.0.1:8765/mcp
```

If `lgtm-oncall-mcp` has bearer-token auth:

```bash
hermes mcp add lgtm-oncall \
  --url http://127.0.0.1:8765/mcp \
  --auth header \
  --auth-header "Authorization: Bearer <YOUR_TOKEN>"
```

## Verify

```bash
hermes mcp list
hermes mcp test lgtm-oncall
```

The `test` command lists every discovered tool. Should print 17.

## Tell Hermes how to use it

Hermes uses its persona file (`~/.hermes/SOUL.md` by default) as system-prompt input. Add an on-call playbook section so it knows when to reach for which tool and — critically — how to handle destructive tools.

Minimal addition:

```markdown
## On-call playbook (lgtm-oncall MCP tools)

When an alert fires or a problem is reported:

1. **Triage** — call `get_active_alerts`. Confirm the symptom is real with
   the matching `get_*` tool (`get_error_rate`, `get_latency_p95`, etc.).
   Don't act on stale alarms.

2. **Correlate change** — `get_recent_deploys(env)`. If a tag is suspicious,
   `get_commit_diff(sha)` to read what changed.

3. **Stack trace → suspect commit** — if logs show panic at <file>:<line>,
   call `get_file_commits(<file>)` to find the most recent commit that
   touched it. Inspect that diff next.

4. **Decide ONE action path. ALL writes go through MCP tools — never via
   the hardwired `github` skill or shell.**

   - Default: rollback. If `get_recent_deploys` shows a known-good prior
     tag, call `propose_rollback(env, tag)` → surface the proposal to the
     user → wait for explicit confirmation → call `confirm_rollback(id)`.
   - Only if rollback impossible: `propose_pr_change(...)` → user confirm →
     `confirm_pr_change(id)`.

5. **Destructive tools ALWAYS require user confirmation.** The server
   enforces this via proposal_id, but you must also surface the
   proposed action clearly to the user and wait for "yes" before
   calling `confirm_*`.
```

Apply by editing the file and restarting:

```bash
$EDITOR ~/.hermes/SOUL.md
sudo systemctl restart hermes-gateway   # if installed as a service
```

## Wire a Grafana alert to Hermes

In Grafana → Alerting → Contact points → New contact point:

- **Type**: Webhook
- **URL**: `http://<hermes-host>:<webhook-port>/webhooks/grafana-alert`
- **HTTP Method**: POST

In Notification policies → set this contact point as the receiver for the alerts you want Hermes to handle (or per-alert via `notification_settings.receiver`).

When the alert fires, Hermes will receive the webhook, follow the playbook above, and post results to Telegram (or whatever platform you've wired).

## Other skills that compete with MCP

Hermes ships with built-in skills like the `github` family, `aform-triage` (if you installed it earlier), etc. These can shadow the MCP tools — Hermes may prefer to open PRs via the github skill instead of `propose_pr_change`.

Disable competing skills explicitly. In `~/.hermes/config.yaml` under `skills.disabled:`, add:

```yaml
skills:
  disabled:
    - aform-triage          # or whatever team-specific triage skill exists
    # consider also disabling the github-* family if you want strict MCP routing
```

Restart:

```bash
sudo systemctl restart hermes-gateway
```

## Troubleshooting

**Hermes calls tools but reports a 401** — bearer-token mismatch. Check `hermes mcp configure lgtm-oncall` against your server's `MCP_BEARER_TOKEN`.

**Hermes opens a PR via `github` skill instead of `propose_pr_change`** — competing skill is enabled. See the section above on disabling skills.

**Hermes triages but skips the rollback step** — playbook too weak. Make step 4 explicit ("ALWAYS use MCP tools; default to rollback if a clean prior tag exists"). See the on-call playbook section above.

**Circuit breaker opens after a tool timeout** — Hermes will mark the server unreachable for ~36s after repeated timeouts. Restart `hermes-gateway` to clear.
