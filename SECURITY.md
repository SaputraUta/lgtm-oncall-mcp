# Security policy

## Reporting a vulnerability

If you find a security issue in `lgtm-oncall-mcp`, please **do not open a public GitHub issue**. Email the maintainer at the address listed in [`pyproject.toml`](./pyproject.toml) (or open a [private security advisory](https://github.com/SaputraUta/lgtm-oncall-mcp/security/advisories/new)).

I'll acknowledge within a few days and aim to ship a fix or workaround within two weeks for confirmed issues.

## Built-in guardrails

1. **Two-step approval for destructive tools.**
   `rollback_deploy` and `propose_fix_pr` are not directly callable. They're split into `propose_*` / `confirm_*` pairs. `propose_*` validates inputs and returns a one-shot `proposal_id` that expires (default 60s). `confirm_*` requires that id. See the [Guardrails section in README](./README.md#guardrails) for the full flow.

2. **Audit log.**
   Every destructive action emits a structured JSON event to stderr (and optionally to `AUDIT_LOG_PATH`). Events cover `proposal_created`, `proposal_consumed`, `action_executed`, `action_failed`, `proposal_rejected`.

3. **Tool binding on confirm.**
   A `proposal_id` from `propose_rollback` cannot execute `confirm_pr_change`. The store verifies the tool name on every consume.

4. **One-shot proposals.**
   Once `confirm_*` succeeds, the proposal is gone. No replays.

## Known limitations (be aware before deploying)

1. **Agent-side confirmation is still recommended.**
   The server-side guard prevents accidental approval but doesn't replace agent policy. SOUL.md / system prompts should still tell the agent to surface the proposal to the user and wait for explicit confirmation before calling `confirm_*`.

2. **No allowed-target list yet.**
   `rollback_deploy` will roll back to ANY existing tag that matches the env naming convention. A curated "known-good" tag list is on the roadmap.

3. **No cool-down / rate-limit between destructive actions.**
   A buggy agent could open many proposals + confirms in quick succession. Run behind a reverse proxy with rate limits if exposing beyond loopback.

4. **Tokens live in environment variables.**
   No secrets manager integration yet. Mount `.env` securely (e.g. systemd `EnvironmentFile=` with 600 perms, or your platform's secret store).

5. **Cert pinning is opt-in.**
   If you point at a self-signed Grafana without setting `GRAFANA_CA_CERT_PATH`, the connection will fail closed (good). Do NOT add `verify=False` shortcuts.

6. **Proposals are in-memory.**
   Server restart wipes all open proposals. This is intentional — restarts are rare and "forgetting" pending destructive actions is the safe default.

## Token scope recommendations

**Bitbucket Cloud (Atlassian API token):**
- `read:repository:bitbucket`
- `write:repository:bitbucket` (only if you use `propose_fix_pr`)
- `read:pullrequest:bitbucket`
- `write:pullrequest:bitbucket` (only if you use `propose_fix_pr`)
- `read:pipeline:bitbucket`
- `write:pipeline:bitbucket` (only if you use `rollback_deploy`)

**GitHub (fine-grained PAT, scoped to the one repo):**
- Contents: read (+ write only for `propose_fix_pr`)
- Pull requests: read (+ write only for `propose_fix_pr`)
- Actions: read (+ write only for `rollback_deploy`)

**Grafana service account:**
- Viewer is enough for sense tools (CPU, memory, error rate, logs, alerts, dashboards)
- Editor only if you intend to mutate dashboards/alerts (no tool does this today)
