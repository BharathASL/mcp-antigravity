# Changelog

## [Unreleased]
### Fixed
- **Server failed to start.** The server was built on the low-level `Server` API
  but registered tools with `@server.tool()`, which only exists on `FastMCP`.
  This raised `AttributeError` on import, so the process crashed immediately and
  any MCP client launching it would hang on the initialization handshake.
  Migrated to `FastMCP`.
- `agy_health` resolved the `agy` binary twice (once directly, once again inside
  `run_agy_command`), doubling the PATH scan on every health check. It now
  resolves once and reuses the result.
- Clarified the empty-response error: an empty stdout does not necessarily mean
  the auth token expired; some `agy` versions render the response to the terminal
  instead of stdout, so it is lost when captured non-interactively.

### Tests
- Fixed a stale `stdin` assertion (`DEVNULL`, not `None`) and a regex that did
  not span newlines.
- Added coverage for empty responses, supplied-binary reuse, missing binaries,
  tool registration, `parse_timeout`, and the `agy_health` single-scan guarantee.

## [0.1.0] - Initial Release
- Initial implementation of the mcp-antigravity server.
- Supported tools: `agy_print`, `agy_continue`, and `agy_health`.
- Included cross-platform binary discovery for `agy` (Windows, macOS, Linux).
- Graceful error handling for missing authentication and binary files.
