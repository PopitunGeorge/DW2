from __future__ import annotations

import json
import sys
from typing import Any

from .repository import WarehouseRepository


class MCPToolServer:
    def __init__(self, repository: WarehouseRepository):
        self.repository = repository

    def tool_specs(self) -> list[dict[str, Any]]:
        return [
            {"name": "list_assets", "description": "List active financial assets.", "inputSchema": {"type": "object", "properties": {"as_of": {"type": "string"}}}},
            {"name": "get_asset", "description": "Get full asset details by identifier.", "inputSchema": {"type": "object", "properties": {"asset_id": {"type": "string"}, "as_of": {"type": "string"}}, "required": ["asset_id"]}},
            {"name": "list_sources", "description": "List active data sources.", "inputSchema": {"type": "object", "properties": {"as_of": {"type": "string"}}}},
            {"name": "get_source", "description": "Get full data source details by identifier.", "inputSchema": {"type": "object", "properties": {"data_source_id": {"type": "string"}, "as_of": {"type": "string"}}, "required": ["data_source_id"]}},
            {"name": "fetch_time_series", "description": "Fetch time-series data for an asset and data source.", "inputSchema": {"type": "object", "properties": {"asset_id": {"type": "string"}, "source_id": {"type": "string"}, "as_of": {"type": "string"}}, "required": ["asset_id", "source_id"]}},
            {"name": "summarize_trends", "description": "Summarize trends and risk signals for a series.", "inputSchema": {"type": "object", "properties": {"asset_id": {"type": "string"}, "source_id": {"type": "string"}, "as_of": {"type": "string"}}, "required": ["asset_id", "source_id"]}},
            {"name": "compare_assets", "description": "Compare two assets from the same source.", "inputSchema": {"type": "object", "properties": {"left_asset_id": {"type": "string"}, "right_asset_id": {"type": "string"}, "source_id": {"type": "string"}, "as_of": {"type": "string"}}, "required": ["left_asset_id", "right_asset_id", "source_id"]}},
            {"name": "explain_change", "description": "Explain the latest movement in a series using grounded data.", "inputSchema": {"type": "object", "properties": {"asset_id": {"type": "string"}, "source_id": {"type": "string"}, "as_of": {"type": "string"}}, "required": ["asset_id", "source_id"]}},
            {"name": "show_asset_history", "description": "Show how an asset changed over time, including source changes and tombstones.", "inputSchema": {"type": "object", "properties": {"asset_id": {"type": "string"}, "as_of": {"type": "string"}}, "required": ["asset_id"]}},
        ]

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        as_of = arguments.get("as_of")
        if name == "list_assets":
            return {"items": self.repository.list_assets(as_of=as_of)}
        if name == "get_asset":
            return {"item": self.repository.get_asset(arguments["asset_id"], as_of=as_of)}
        if name == "list_sources":
            return {"items": self.repository.list_sources(as_of=as_of)}
        if name == "get_source":
            return {"item": self.repository.get_source(arguments["data_source_id"], as_of=as_of)}
        if name == "fetch_time_series":
            return {"items": self.repository.series(arguments["asset_id"], arguments["source_id"], as_of=as_of)}
        if name == "summarize_trends":
            series = self.repository.series(arguments["asset_id"], arguments["source_id"], as_of=as_of)
            return series[0] if series else {"message": "Series not found."}
        if name == "compare_assets":
            return self.repository.compare(arguments["left_asset_id"], arguments["right_asset_id"], arguments["source_id"], as_of=as_of)
        if name == "explain_change":
            return {"explanation": self.repository.explain(arguments["asset_id"], arguments["source_id"], as_of=as_of)}
        if name == "show_asset_history":
            return {"history": self.repository.asset_history(arguments["asset_id"], as_of=as_of)}
        return {"error": f"Unknown tool: {name}"}


def _make_result(result_id: Any, payload: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": result_id, "result": payload}


def _make_error(result_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": result_id, "error": {"code": code, "message": message}}


def run_stdio_server(repository: WarehouseRepository) -> None:
    server = MCPToolServer(repository)
    for raw_line in sys.stdin:
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        message = json.loads(raw_line)
        method = message.get("method")
        request_id = message.get("id")
        params = message.get("params", {})
        if method == "initialize":
            response = _make_result(request_id, {"protocolVersion": "2024-11-05", "serverInfo": {"name": "AuroraVault MCP", "version": "0.1.0"}, "capabilities": {"tools": {}}})
        elif method == "tools/list":
            response = _make_result(request_id, {"tools": server.tool_specs()})
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            payload = server.call(tool_name, arguments)
            response = _make_result(request_id, {"content": [{"type": "text", "text": json.dumps(payload, indent=2, ensure_ascii=False)}]})
        elif method == "ping":
            response = _make_result(request_id, {})
        else:
            response = _make_error(request_id, -32601, f"Unsupported method: {method}")
        sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        sys.stdout.flush()
