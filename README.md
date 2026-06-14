# mcp-antigravity

An MCP (Model Context Protocol) server that securely proxies requests to Google's Antigravity CLI (`agy`).

## Why this exists
AI tools running in sandboxes (like Claude Code) cannot natively access your local authentication credentials (`~/.antigravitycli/` and `~/.gemini/oauth_creds.json`). Direct invocations of `agy` within these sandboxes will silently hang or fail. `mcp-antigravity` runs as an MCP server in your normal user environment, ensuring commands inherit your permissions and auth state safely.

## Prerequisites
- The Antigravity CLI (`agy`) must be installed.
- You must have run `agy` interactively at least once to complete Google OAuth.

## Install

Use `pipx` for a global installation:
```bash
pipx install mcp-antigravity
```

Alternatively, you can run it via `uvx` without installing:
```bash
uvx mcp-antigravity
```

## Configuration

Add the following to your AI tool's MCP configuration file (e.g., Claude Code's `mcp.json`):

```json
{
  "mcpServers": {
    "antigravity": {
      "command": "uvx",
      "args": ["mcp-antigravity"]
    }
  }
}
```

*(If you installed via `pipx`, use `mcp-antigravity` as the command instead)*

## Tools

- `agy_print(prompt, add_dirs, timeout, skip_permissions)`: Runs `agy --print` to perform tasks. `skip_permissions` defaults to true.
- `agy_continue(prompt, conversation_id, timeout)`: Continues a recent `agy` conversation using `-c` or `--conversation`.
- `agy_health()`: Diagnostic tool to verify `agy` binary and auth files are available.

## Troubleshooting
If `agy` authentication becomes stuck, delete the `~/.antigravitycli/` and `~/.gemini/oauth_creds.json` files and re-run `agy` interactively in your terminal to log in again.

**Tools return an "empty response" even though `agy_health` is green.** The MCP
server captures `agy`'s stdout over a pipe. Some `agy` versions render the model
response straight to the terminal (a "typewriter" animation) instead of writing
it to stdout, so nothing is captured when the CLI is run non-interactively. Run
`agy update` to pick up a version that supports non-interactive `--print` output,
and verify with `agy --print "hi" > out.txt` — if `out.txt` is empty, your `agy`
build does not yet emit print-mode output to stdout.

## Contribution
PRs are welcome! Before submitting, ensure all tests pass:
```bash
uv run pytest
uv run ruff check
```

## License
MIT License
