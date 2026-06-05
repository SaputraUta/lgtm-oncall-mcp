# Security policy

## Reporting a vulnerability

If you find a security issue in `lgtm-oncall-mcp`, please **do not open a public GitHub issue**. Email the maintainer at the address listed in [`pyproject.toml`](./pyproject.toml) (or open a [private security advisory](https://github.com/SaputraUta/lgtm-oncall-mcp/security/advisories/new)).

I'll acknowledge within a few days and aim to ship a fix or workaround within two weeks for confirmed issues.

## Known limitations (be aware before deploying)

1. **Destructive tools are not server-side gated.**
   `rollback_deploy` and `propose_fix_pr` will execute on any caller who can reach `/mcp`. The current safety mechanism is the agent's policy (e.g. SOUL.md telling the agent to ask for human confirmation). For higher trust, you must:
   - Set `MCP_BEARER_TOKEN` and keep it out of repos
   - Bind the server to loopback and tunnel
   - Restrict VCS token scope to the minimum your `trigger_deploy` / `open_pr` actually needs
   - Future versions will add server-side two-step approval (`propose_*` / `confirm_*` pair).

2. **Tokens live in environment variables.**
   No secrets manager integration yet. Mount `.env` securely (e.g. systemd `EnvironmentFile=` with 600 perms, or your platform's secret store).

3. **Cert pinning is opt-in.**
   If you point at a self-signed Grafana without setting `GRAFANA_CA_CERT_PATH`, the connection will fail closed (good). Do NOT add `verify=False` shortcuts.

4. **No audit log yet.**
   Tool calls are not logged to a tamper-evident store. Telegram / chat history is the only record. Roadmap.

5. **No rate limiting on tool calls.**
   A buggy or runaway agent could spam destructive tools. Run behind a reverse proxy with rate limits if exposing beyond loopback.

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
