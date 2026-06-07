from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .config import DEFAULT_API_PORT, DEFAULT_HOST
from .ingest import IngestionService, seed_demo_warehouse
from .repository import WarehouseRepository
from .store import parse_iso


def _json_default(value: Any) -> Any:
    if isinstance(value, set):
        return sorted(value)
    raise TypeError(f"Cannot serialize {type(value)!r}")


class WarehouseHTTPRequestHandler(BaseHTTPRequestHandler):
    repository: WarehouseRepository

    def _send_html(self, status: int, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, default=_json_default, indent=2, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            return {}
        raw = self.rfile.read(content_length).decode("utf-8")
        return json.loads(raw) if raw.strip() else {}

    def _query_time(self, params: dict[str, list[str]]) -> Any:
        value = params.get("as_of", [None])[0]
        return parse_iso(value) if value else None

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        as_of = self._query_time(params)
        path = parsed.path.rstrip("/") or "/"
        if path == "/health":
            self._send_json(200, {"status": "ok", "service": "AuroraVault DWH"})
            return
        if path == "/assets":
            self._send_json(200, {"items": self.repository.list_assets(as_of=as_of)})
            return
        if path.startswith("/assets/") and path.endswith("/history"):
            asset_id = path.split("/")[2]
            history = self.repository.asset_history(asset_id, as_of=as_of)
            self._send_json(200 if history else 404, {"item": history} if history else {"error": "Asset history not found"})
            return
        if path.startswith("/assets/") and path.endswith("/history/view"):
            asset_id = path.split("/")[2]
            html = self.repository.asset_history_html(asset_id, as_of=as_of)
            self._send_html(200 if html else 404, html or "<h1>Asset history not found</h1>")
            return
        if path.startswith("/assets/") and path.endswith("/change-timeline"):
            asset_id = path.split("/")[2]
            timeline = self.repository.asset_change_timeline(asset_id)
            self._send_json(200, {"assetId": asset_id, "timeline": timeline})
            return
        if path.startswith("/assets/") and path.endswith("/change-narrative"):
            asset_id = path.split("/")[2]
            narrative = self.repository.asset_change_narrative(asset_id)
            self._send_json(200, {"assetId": asset_id, "narrative": narrative})
            return
        if path.startswith("/assets/") and path.endswith("/change-story"):
            asset_id = path.split("/")[2]
            version = params.get("version", [None])[0]
            if not version:
                self._send_json(400, {"error": "version parameter is required"})
                return
            story = self.repository.asset_change_story(asset_id, int(version))
            self._send_json(200 if story else 404, {"story": story} if story else {"error": "Story not found"})
            return
        if path.startswith("/assets/") and path.endswith("/change-delta"):
            asset_id = path.split("/")[2]
            from_version = params.get("from_version", [None])[0]
            to_version = params.get("to_version", [None])[0]
            if not from_version or not to_version:
                self._send_json(400, {"error": "from_version and to_version parameters are required"})
                return
            delta = self.repository.asset_change_delta(asset_id, int(from_version), int(to_version))
            self._send_json(200, {"assetId": asset_id, "delta": delta})
            return
        if path.startswith("/assets/"):
            asset_id = path.split("/", 2)[2]
            asset = self.repository.get_asset(asset_id, as_of=as_of)
            self._send_json(200 if asset else 404, {"item": asset} if asset else {"error": "Asset not found"})
            return
        if path == "/sources":
            self._send_json(200, {"items": self.repository.list_sources(as_of=as_of)})
            return
        if path.startswith("/sources/") and path.endswith("/change-timeline"):
            source_id = path.split("/")[2]
            timeline = self.repository.source_change_timeline(source_id)
            self._send_json(200, {"sourceId": source_id, "timeline": timeline})
            return
        if path.startswith("/sources/") and path.endswith("/change-narrative"):
            source_id = path.split("/")[2]
            narrative = self.repository.source_change_narrative(source_id)
            self._send_json(200, {"sourceId": source_id, "narrative": narrative})
            return
        if path.startswith("/sources/"):
            source_id = path.split("/", 2)[2]
            source = self.repository.get_source(source_id, as_of=as_of)
            self._send_json(200 if source else 404, {"item": source} if source else {"error": "Source not found"})
            return
        if path == "/series":
            asset_id = params.get("asset_id", [None])[0]
            source_id = params.get("source_id", [None])[0]
            if not asset_id or not source_id:
                self._send_json(400, {"error": "asset_id and source_id are required"})
                return
            self._send_json(200, {"items": self.repository.series(asset_id, source_id, as_of=as_of)})
            return
        if path == "/analytics/summary":
            asset_id = params.get("asset_id", [None])[0]
            source_id = params.get("source_id", [None])[0]
            if not asset_id or not source_id:
                self._send_json(400, {"error": "asset_id and source_id are required"})
                return
            series = self.repository.series(asset_id, source_id, as_of=as_of)
            if not series:
                self._send_json(404, {"error": "Series not found"})
                return
            self._send_json(200, {"seriesId": series[0]["seriesId"], "summary": series[0]["summary"]})
            return
        if path == "/analytics/compare":
            left_asset_id = params.get("left_asset_id", [None])[0]
            right_asset_id = params.get("right_asset_id", [None])[0]
            source_id = params.get("source_id", [None])[0]
            if not left_asset_id or not right_asset_id or not source_id:
                self._send_json(400, {"error": "left_asset_id, right_asset_id and source_id are required"})
                return
            self._send_json(200, self.repository.compare(left_asset_id, right_asset_id, source_id, as_of=as_of))
            return
        if path == "/analytics/forecast":
            asset_id = params.get("asset_id", [None])[0]
            source_id = params.get("source_id", [None])[0]
            if not asset_id or not source_id:
                self._send_json(400, {"error": "asset_id and source_id are required"})
                return
            self._send_json(200, self.repository.forecast(asset_id, source_id, as_of=as_of))
            return
        if path == "/portfolios":
            self._send_json(200, {"items": self.repository.portfolios(as_of=as_of)})
            return
        if path.startswith("/portfolios/") and path.endswith("/assets"):
            portfolio_id = path.split("/")[2]
            self._send_json(200, {"items": self.repository.portfolio_assets(portfolio_id, as_of=as_of)})
            return
        if path.startswith("/portfolios/"):
            portfolio_id = path.split("/")[2]
            portfolio = self.repository.portfolio(portfolio_id, as_of=as_of)
            self._send_json(200 if portfolio else 404, {"item": portfolio} if portfolio else {"error": "Portfolio not found"})
            return
        # MongoDB integration endpoints
        if path == "/mongodb/status":
            status = self.repository.mongodb_status()
            self._send_json(200, status)
            return
        if path == "/mongodb/entity-history":
            collection_name = params.get("collection", [None])[0]
            entity_id = params.get("entity_id", [None])[0]
            if not collection_name or not entity_id:
                self._send_json(400, {"error": "collection and entity_id parameters are required"})
                return
            history = self.repository.mongodb_query_entity_history(collection_name, entity_id)
            self._send_json(200, {"collection": collection_name, "entity_id": entity_id, "history": history})
            return
        self._send_json(404, {"error": "Route not found"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path == "/admin/seed-demo":
            payload = seed_demo_warehouse(self.repository.store)
            self._send_json(200, payload)
            return
        if path == "/ingest/provider":
            body = self._read_body()
            result = IngestionService(self.repository.store).ingest_payload(body)
            self._send_json(201, result)
            return
        if path == "/market-memory/record-story":
            body = self._read_body()
            required = ["assetId", "version", "reason", "changeType"]
            if not all(key in body for key in required):
                self._send_json(400, {"error": f"Required fields: {', '.join(required)}"})
                return
            result = self.repository.record_asset_change_story(
                asset_id=body["assetId"],
                version=body["version"],
                reason=body["reason"],
                change_type=body["changeType"],
                impacted_fields=body.get("impactedFields"),
            )
            self._send_json(201, result)
            return
        # MongoDB integration endpoints
        if path == "/mongodb/connect":
            body = self._read_body()
            connection_string = body.get("connectionString")
            result = self.repository.connect_mongodb(connection_string)
            self._send_json(200, result)
            return
        if path == "/mongodb/sync-all":
            result = self.repository.mongodb_sync_all()
            self._send_json(200, result)
            return
        if path == "/mongodb/sync-collection":
            body = self._read_body()
            collection_name = body.get("collection")
            if not collection_name:
                self._send_json(400, {"error": "collection parameter is required"})
                return
            result = self.repository.mongodb_sync_collection(collection_name)
            self._send_json(200, result)
            return
        if path == "/mongodb/setup-indexes":
            result = self.repository.mongodb_setup_indexes()
            self._send_json(200, result)
            return
        if path == "/mongodb/disconnect":
            result = self.repository.mongodb_disconnect()
            self._send_json(200, result)
            return
        self._send_json(404, {"error": "Route not found"})

    def log_message(self, format: str, *args: Any) -> None:
        return


def build_server(data_dir: str | Path, host: str = DEFAULT_HOST, port: int = DEFAULT_API_PORT) -> ThreadingHTTPServer:
    repository = WarehouseRepository(data_dir)
    handler = type("ConfiguredWarehouseHTTPRequestHandler", (WarehouseHTTPRequestHandler,), {"repository": repository})
    return ThreadingHTTPServer((host, port), handler)
