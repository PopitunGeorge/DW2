from __future__ import annotations

import argparse
from pathlib import Path

# Load environment variables from .env file
from .env_config import load_env_file
load_env_file()

from .api import build_server
from .config import DEFAULT_API_PORT, DEFAULT_DATA_DIR, DEFAULT_HOST
from .ingest import seed_demo_warehouse
from .mcp_server import run_stdio_server
from .repository import WarehouseRepository


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR), help="Path to the warehouse data directory")

    parser = argparse.ArgumentParser(prog="aurora-dw", description="AuroraVault financial data warehouse", parents=[common])
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("seed", help="Seed the demo warehouse", parents=[common])

    api_parser = subparsers.add_parser("api", help="Run the REST API server", parents=[common])
    api_parser.add_argument("--host", default=DEFAULT_HOST)
    api_parser.add_argument("--port", default=DEFAULT_API_PORT, type=int)

    mcp_parser = subparsers.add_parser("mcp", help="Run the MCP stdio server", parents=[common])
    mcp_parser.add_argument("--seed", action="store_true", help="Seed before serving")

    subparsers.add_parser("demo", help="Print a short demo summary", parents=[common])
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repository = WarehouseRepository(Path(args.data_dir))

    if args.command == "seed":
        result = seed_demo_warehouse(repository.store)
        print(result)
        return 0
    if args.command == "api":
        server = build_server(args.data_dir, host=args.host, port=args.port)
        print(f"AuroraVault API running on http://{args.host}:{args.port}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            return 0
    if args.command == "mcp":
        if args.seed:
            seed_demo_warehouse(repository.store)
        run_stdio_server(repository)
        return 0
    if args.command == "demo":
        repository.seed_demo()
        print({"assets": repository.list_assets(), "sources": repository.list_sources(), "portfolios": repository.portfolios()})
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
