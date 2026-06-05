# Contributing

Thanks for considering a contribution. The project is small — a few hundred lines of Python — and intentionally aims to stay narrow.

## Quick start for contributors

```bash
git clone https://github.com/SaputraUta/lgtm-oncall-mcp.git
cd lgtm-oncall-mcp
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m playwright install chromium

pytest         # tests
ruff check .   # lint
```

## What's in scope

- New tools that fit the senses / vision / hands split
- Additional VCS backends (GitLab, Gitea, …)
- Better resilience around Mimir / Loki / Grafana quirks
- Docs, examples, integration guides
- Test coverage

## What's out of scope (for now)

- Bundling Grafana / Mimir / Loki themselves
- Replacing the agent's reasoning (this is just the toolbox)
- Cloud-specific deploy tools (k8s rollouts, etc.) — open a discussion first if you want to add these

## Pull requests

- One concern per PR
- Add or update tests
- `ruff check .` must pass
- Update README/`.env.example` if you add a config var

## Filing a bug

Include:
- What you ran, what happened, what you expected
- MCP server version + Python version
- Relevant logs (strip tokens first)

## Code style

- Type hints everywhere
- Prefer small, readable modules over clever ones
- One purpose per module under `src/lgtm_oncall_mcp/`

## Security disclosure

See [`SECURITY.md`](./SECURITY.md). Don't open public issues for security bugs.
