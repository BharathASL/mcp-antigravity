from mcp.server.fastmcp import FastMCP

from .agy_runner import find_agy_binary, run_agy_command
from .auth_check import check_auth_files

mcp = FastMCP("mcp-antigravity")


def parse_timeout(timeout_str: str) -> float:
    timeout_str = timeout_str.strip().lower()
    if timeout_str.endswith("m"):
        return float(timeout_str[:-1]) * 60.0
    if timeout_str.endswith("s"):
        return float(timeout_str[:-1])
    return float(timeout_str)


def _require_auth() -> None:
    ok, err_msg = check_auth_files()
    if not ok:
        raise RuntimeError(
            f"Auth check failed: {err_msg}\n"
            "Please run `agy` interactively in your terminal to complete login."
        )


@mcp.tool()
def agy_print(
    prompt: str,
    add_dirs: list[str] | None = None,
    timeout: str = "5m",
    skip_permissions: bool = True,
    model: str | None = None,
) -> str:
    """Invokes agy --print with the given prompt.

    Pass `model` to override the model for this call (e.g. "Gemini 3.5 Flash
    (Medium)"). Use the `agy_models` tool to discover valid names. When omitted,
    agy uses its configured default.
    """
    _require_auth()

    timeout_s = min(parse_timeout(timeout), 600.0)

    args = ["--print", prompt, "--print-timeout", timeout]

    if model:
        args.extend(["--model", model])

    if add_dirs:
        for d in add_dirs:
            args.extend(["--add-dir", d])

    if skip_permissions:
        args.append("--dangerously-skip-permissions")

    return run_agy_command(args, timeout_s)


@mcp.tool()
def agy_continue(
    prompt: str,
    conversation_id: str | None = None,
    timeout: str = "5m",
    model: str | None = None,
) -> str:
    """Continues a previous agy conversation with a new prompt.

    Pass `model` to override the model for this call. Use the `agy_models` tool
    to discover valid names. When omitted, agy uses its configured default.
    """
    _require_auth()

    timeout_s = min(parse_timeout(timeout), 600.0)

    args = ["--print", prompt, "--print-timeout", timeout]

    if model:
        args.extend(["--model", model])

    if conversation_id:
        args.extend(["--conversation", conversation_id])
    else:
        args.append("-c")

    return run_agy_command(args, timeout_s)


@mcp.tool()
def agy_models(timeout: str = "30s") -> str:
    """Lists the models available to agy (wraps `agy models`).

    Note: some agy versions render this list to the terminal rather than stdout,
    in which case the call reports an empty response (see README troubleshooting).
    """
    _require_auth()

    timeout_s = min(parse_timeout(timeout), 600.0)
    return run_agy_command(["models"], timeout_s)


@mcp.tool()
def agy_health() -> dict:
    """Checks if the agy binary is available and authentication is configured."""
    health_status = {
        "binary_found": False,
        "version": "",
        "auth_present": False,
        "agy_path": "",
    }

    binary = find_agy_binary()
    if binary:
        health_status["binary_found"] = True
        health_status["agy_path"] = binary
        try:
            # Reuse the already-resolved binary to avoid a second PATH scan.
            health_status["version"] = run_agy_command(
                ["--version"], 10.0, binary=binary
            ).strip()
        except Exception:
            health_status["version"] = "unknown"

    ok, _ = check_auth_files()
    health_status["auth_present"] = ok

    return health_status


def main():
    mcp.run()


if __name__ == "__main__":
    main()
