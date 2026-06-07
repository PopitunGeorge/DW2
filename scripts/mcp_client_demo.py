from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dw_warehouse.repository import WarehouseRepository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run an end-to-end MCP client demo against AuroraVault")
    parser.add_argument("--data-dir", default=str(Path("data") / "warehouse"), help="Warehouse data directory")
    return parser


def send_message(process: subprocess.Popen[str], payload: dict) -> dict:
    assert process.stdin is not None
    assert process.stdout is not None
    process.stdin.write(json.dumps(payload) + "\n")
    process.stdin.flush()
    raw = process.stdout.readline()
    if not raw:
        raise RuntimeError("MCP server closed the stream unexpectedly")
    return json.loads(raw)


def call_tool(process: subprocess.Popen[str], request_id: int, name: str, arguments: dict) -> dict:
    response = send_message(
        process,
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
    )
    if "error" in response:
        raise RuntimeError(response["error"])
    content = response["result"]["content"][0]["text"]
    return json.loads(content)


def main() -> int:
    args = build_parser().parse_args()
    repo = WarehouseRepository(Path(args.data_dir))
    repo.seed_demo()

    process = subprocess.Popen(
        [sys.executable, "-m", "dw_warehouse.cli", "mcp", "--data-dir", args.data_dir],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        initialize = send_message(
            process,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "clientInfo": {"name": "AuroraVault Demo", "version": "0.1.0"}},
            },
        )
        print("Initialize response:")
        print(json.dumps(initialize, indent=2))

        tools = send_message(process, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        print("\nAvailable tools:")
        print(json.dumps(tools, indent=2))

        print("\nGrounded tool calls:")
        print(json.dumps(call_tool(process, 3, "list_assets", {}), indent=2))
        print(json.dumps(call_tool(process, 4, "fetch_time_series", {"asset_id": "asset-gm", "source_id": "source-nasdaq"}), indent=2))
        print(json.dumps(call_tool(process, 5, "summarize_trends", {"asset_id": "asset-gm", "source_id": "source-nasdaq"}), indent=2))
        print(json.dumps(call_tool(process, 6, "compare_assets", {"left_asset_id": "asset-gm", "right_asset_id": "asset-msft", "source_id": "source-nasdaq"}), indent=2))
        print(json.dumps(call_tool(process, 7, "explain_change", {"asset_id": "asset-btc", "source_id": "source-bloomberg"}), indent=2))
        return 0
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
