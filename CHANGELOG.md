# Changelog

All notable changes to this project are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2026-06-06

Initial public release.

### Added

- **Senses** (11 read-only tools): `ping`, `get_cpu_usage`, `get_memory_usage`,
  `get_disk_usage`, `get_error_rate`, `get_latency_p95`, `get_active_alerts`,
  `search_logs`, `get_recent_deploys`, `get_commit_diff`, `get_file_commits`.
- **Vision** (4 screenshot tools via headless Chrome): `list_dashboards`,
  `list_panels`, `capture_dashboard`, `capture_panel`.
- **Hands** (4 destructive tools, two-step propose/confirm):
  `propose_rollback` / `confirm_rollback`, `propose_pr_change` /
  `confirm_pr_change`.
- **VCS adapters**: Bitbucket Cloud and GitHub, selectable via
  `VCS_PROVIDER` env var. Common `VCSAdapter` interface for adding more.
- **Two-step approval** for every destructive tool with one-shot,
  tool-bound, TTL-expiring proposal ids. Default TTL 60s (configurable
  via `PROPOSAL_TTL_SECONDS`).
- **Audit log** of every proposal lifecycle event — written as JSONL to
  stderr (always) and optionally to a file (`AUDIT_LOG_PATH`).
- **Bearer-token auth** (`MCP_BEARER_TOKEN`) — optional, required when
  binding beyond loopback.
- **Cert pinning** (`GRAFANA_CA_CERT_PATH`) for self-signed Grafana.
- **Label templating** (`ENV_LABEL_KEY`, `TEAM_LABEL_KEY`,
  `TEAM_LABEL_VALUE`) so the server works with any team's Mimir/Loki
  labeling convention.
- **Deploy-tag rules** (`DEPLOY_TAG_PROD_REGEX`,
  `DEPLOY_TAG_NONPROD_SUFFIX_*`) so the server works with any
  org's tag naming.
- **Local dev stack** via `docker-compose.yml` (Grafana + Mimir +
  Loki + node-exporter). Lets new users try the server end-to-end
  without an AWS account.
- **Unit tests** (39, mocked via `respx`): config rules, scalar guards,
  VCS adapter contracts, proposal store contract, audit log sinks,
  destructive-tool propose/confirm flow.
- **CI** via GitHub Actions on Python 3.11 and 3.12 (lint + tests).
- Docs: README with quickstart, architecture, configuration reference,
  guardrails explanation, security notes. `SECURITY.md`,
  `CONTRIBUTING.md`, per-client integration guides in `examples/clients/`.

### Security

- Destructive tools are gated server-side. Direct calls to a destructive
  action are not possible — every action requires a fresh, unguessable,
  one-shot `proposal_id` from a separate `propose_*` call.
- Audit events for every proposal lifecycle transition.

[Unreleased]: https://github.com/SaputraUta/lgtm-oncall-mcp/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/SaputraUta/lgtm-oncall-mcp/releases/tag/v0.1.0
