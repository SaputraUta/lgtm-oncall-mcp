# Claude Desktop (GUI) — integration

Claude Desktop historically only spoke stdio-MCP. We use the [`mcp-remote`](https://github.com/geelen/mcp-remote) shim — a tiny Node tool that speaks stdio to Claude Desktop and streamable-HTTP to our server.

## Prerequisites

- Claude Desktop installed and you're logged in.
- Node.js + `npx` available on your PATH (`node -v` works).
- `lgtm-oncall-mcp` server running and reachable from your machine.

## Configure

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or the equivalent on Windows/Linux. Add or merge an `mcpServers` block at the top level:

```json
{
  "mcpServers": {
    "lgtm-oncall": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://127.0.0.1:8765/mcp"]
    }
  }
}
```

If your server has `MCP_BEARER_TOKEN` set, pass the header through `mcp-remote`:

```json
{
  "mcpServers": {
    "lgtm-oncall": {
      "command": "npx",
      "args": [
        "-y", "mcp-remote",
        "http://127.0.0.1:8765/mcp",
        "--header", "Authorization: Bearer <YOUR_TOKEN>"
      ]
    }
  }
}
```

> ⚠️ If you already have other entries under `mcpServers`, **merge — don't replace**. Validate with `python3 -m json.tool < <file>` before restarting.

## Apply

Fully quit Claude Desktop (Cmd+Q on macOS — not just close the window) and reopen. First start downloads `mcp-remote` via `npx` (~5 seconds, one-time).

## Verify

Open a new chat and ask: `what tools do you have access to from lgtm-oncall?`

Or run a tool call directly: `screenshot the error rate panel on staging, last 30 min`. The image renders inline.

## Destructive actions

Same propose/confirm flow as Claude Code (see [claude-code.md](./claude-code.md#destructive-actions)).

## Troubleshooting

**Tool list empty / "I don't have access to..."** — config not loaded. Check:
- JSON syntax: `python3 -m json.tool < ~/Library/Application\ Support/Claude/claude_desktop_config.json`
- Fully quit Claude Desktop (Cmd+Q) before reopening, not just close window.

**`mcp-remote` errors** — usually a Node version mismatch. Ensure Node 18+.

**`ECONNREFUSED localhost:8765`** — your SSM tunnel or local server is down. Restart it; Claude Desktop will auto-reconnect within ~10s.
