from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .analytics import build_derived_series, compare_series, correlation_matrix, explain_change, summarize_points
from .config import COLLECTIONS
from .history import build_asset_history_view, render_asset_history_html, render_asset_history_timeline
from .market_memory import MarketMemory
from .store import DocumentStore, parse_iso


class WarehouseRepository:
    def __init__(self, data_dir: str | Path):
        self.store = DocumentStore(Path(data_dir))
        self.market_memory = MarketMemory(self.store)

    def seed_demo(self) -> dict[str, Any]:
        from .ingest import seed_demo_warehouse

        return seed_demo_warehouse(self.store)

    def _asset_records(self, asset_id: str, as_of: datetime | str | None = None) -> list[dict[str, Any]]:
        records = self.store.history(COLLECTIONS["instruments"], asset_id)
        if as_of is None:
            return records
        target_time = parse_iso(as_of)
        return [record for record in records if parse_iso(record["valid_from"]) <= target_time]

    def ingest_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        from .ingest import IngestionService

        return IngestionService(self.store).ingest_payload(payload)

    def _asset_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return {
            "assetId": record["entity_id"],
            "version": record["version"],
            "validFrom": record["valid_from"],
            "isDeleted": record["is_deleted"],
            "data": record["data"],
            "provenance": record["provenance"],
            "recordHash": record["record_hash"],
            "prevHash": record["prev_hash"],
            "state": "retired" if record["is_deleted"] else "active",
        }

    def _source_record(self, record: dict[str, Any]) -> dict[str, Any]:
        payload = self._asset_record(record)
        payload["dataSourceId"] = payload.pop("assetId")
        return payload

    def _series_record(self, record: dict[str, Any], as_of: datetime | str | None = None) -> dict[str, Any]:
        series_id = record["entity_id"]
        points = self.series_points(series_id, as_of=as_of)
        return {
            "seriesId": series_id,
            "version": record["version"],
            "validFrom": record["valid_from"],
            "isDeleted": record["is_deleted"],
            "data": record["data"],
            "provenance": record["provenance"],
            "recordHash": record["record_hash"],
            "prevHash": record["prev_hash"],
            "state": "retired" if record["is_deleted"] else "active",
            "points": points,
            "summary": summarize_points(points),
        }

    def _portfolio_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return {
            "portfolioId": record["entity_id"],
            "version": record["version"],
            "validFrom": record["valid_from"],
            "isDeleted": record["is_deleted"],
            "data": record["data"],
            "provenance": record["provenance"],
            "recordHash": record["record_hash"],
            "prevHash": record["prev_hash"],
            "state": "retired" if record["is_deleted"] else "active",
        }

    def _portfolio_asset_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return {
            "portfolioAssetId": record["entity_id"],
            "version": record["version"],
            "validFrom": record["valid_from"],
            "isDeleted": record["is_deleted"],
            "data": record["data"],
            "provenance": record["provenance"],
            "recordHash": record["record_hash"],
            "prevHash": record["prev_hash"],
            "state": "retired" if record["is_deleted"] else "active",
        }

    def list_assets(self, as_of: datetime | str | None = None) -> list[dict[str, Any]]:
        records = self.store.latest_per_entity(COLLECTIONS["instruments"], as_of=as_of)
        return [self._asset_summary(record) for record in records if not record["is_deleted"]]

    def _asset_summary(self, record: dict[str, Any]) -> dict[str, Any]:
        data = record["data"]
        return {
            "assetId": record["entity_id"],
            "symbol": data["symbol"],
            "instrumentClass": data["instrumentClass"],
            "name": data["name"],
            "region": data["region"],
            "validFrom": record["valid_from"],
            "state": "retired" if record["is_deleted"] else "active",
        }

    def get_asset(self, asset_id: str, as_of: datetime | str | None = None) -> dict[str, Any] | None:
        record = self.store.latest_record(COLLECTIONS["instruments"], asset_id, as_of=as_of)
        return None if record is None else self._asset_record(record)

    def asset_history(self, asset_id: str, as_of: datetime | str | None = None) -> dict[str, Any] | None:
        asset_records = self._asset_records(asset_id, as_of=as_of)
        if not asset_records:
            return None
        series_records = [
            record
            for record in self.store.read_all(COLLECTIONS["series"])
            if record["data"]["assetId"] == asset_id
            and (as_of is None or parse_iso(record["valid_from"]) <= parse_iso(as_of))
        ]
        source_ids = sorted({record["data"]["dataSourceId"] for record in series_records})
        source_records = []
        for source_id in source_ids:
            source_records.extend(self.store.history(COLLECTIONS["sources"], source_id))
        history = build_asset_history_view(asset_id, asset_records, series_records, source_records)
        history["asset"] = self._asset_record(asset_records[-1])
        history["rendered"] = render_asset_history_timeline(history)
        history["seriesIds"] = sorted({record["entity_id"] for record in series_records})
        return history

    def asset_history_html(self, asset_id: str, as_of: datetime | str | None = None) -> str | None:
        history = self.asset_history(asset_id, as_of=as_of)
        return None if history is None else render_asset_history_html(history)

    def list_sources(self, as_of: datetime | str | None = None) -> list[dict[str, Any]]:
        records = self.store.latest_per_entity(COLLECTIONS["sources"], as_of=as_of)
        return [self._source_summary(record) for record in records if not record["is_deleted"]]

    def _source_summary(self, record: dict[str, Any]) -> dict[str, Any]:
        data = record["data"]
        return {
            "dataSourceId": record["entity_id"],
            "name": data["name"],
            "providerType": data["providerType"],
            "apiEndpoint": data["apiEndpoint"],
            "validFrom": record["valid_from"],
            "state": "retired" if record["is_deleted"] else "active",
        }

    def get_source(self, data_source_id: str, as_of: datetime | str | None = None) -> dict[str, Any] | None:
        record = self.store.latest_record(COLLECTIONS["sources"], data_source_id, as_of=as_of)
        return None if record is None else self._source_record(record)

    def series(self, asset_id: str, source_id: str, as_of: datetime | str | None = None) -> list[dict[str, Any]]:
        series_records = self.store.latest_per_entity(
            COLLECTIONS["series"],
            as_of=as_of,
            predicate=lambda record: record["data"]["assetId"] == asset_id and record["data"]["dataSourceId"] == source_id,
        )
        return [self._series_record(record, as_of=as_of) for record in series_records if not record["is_deleted"]]

    def series_points(self, series_id: str, as_of: datetime | str | None = None) -> list[dict[str, Any]]:
        records = self.store.latest_per_entity(
            COLLECTIONS["points"],
            as_of=as_of,
            predicate=lambda record: record["data"]["seriesId"] == series_id,
        )
        points = []
        for record in records:
            if record["is_deleted"]:
                continue
            point = {"pointId": record["entity_id"], "validFrom": record["valid_from"], "data": record["data"]}
            points.append(point)
        points.sort(key=lambda point: point["data"]["timestamp"])
        return points

    def derived_series(self, asset_id: str, source_id: str, as_of: datetime | str | None = None) -> dict[str, Any] | None:
        series = self.series(asset_id, source_id, as_of=as_of)
        if not series:
            return None
        base = series[0]
        derived = build_derived_series(base["points"])
        return {
            "assetId": asset_id,
            "sourceId": source_id,
            "seriesId": base["seriesId"],
            "generatedAt": base["provenance"]["importedAt"],
            "baseSummary": base["summary"],
            "derived": derived,
        }

    def correlation_view(self, source_id: str, as_of: datetime | str | None = None) -> dict[str, Any]:
        series_records = self.store.latest_per_entity(
            COLLECTIONS["series"],
            as_of=as_of,
            predicate=lambda record: record["data"]["dataSourceId"] == source_id,
        )
        series_points: dict[str, list[dict[str, Any]]] = {}
        for record in series_records:
            if record["is_deleted"]:
                continue
            series_id = record["entity_id"]
            series_points[series_id] = self.series_points(series_id, as_of=as_of)
        return {
            "sourceId": source_id,
            "matrix": correlation_matrix(series_points),
        }

    def portfolio(self, portfolio_id: str, as_of: datetime | str | None = None) -> dict[str, Any] | None:
        record = self.store.latest_record(COLLECTIONS["portfolios"], portfolio_id, as_of=as_of)
        if record is None:
            return None
        payload = self._portfolio_record(record)
        payload["assets"] = self.portfolio_assets(portfolio_id, as_of=as_of)
        return payload

    def portfolios(self, as_of: datetime | str | None = None) -> list[dict[str, Any]]:
        records = self.store.latest_per_entity(COLLECTIONS["portfolios"], as_of=as_of)
        return [self.portfolio(record["entity_id"], as_of=as_of) for record in records if not record["is_deleted"]]

    def portfolio_assets(self, portfolio_id: str, as_of: datetime | str | None = None) -> list[dict[str, Any]]:
        records = self.store.latest_per_entity(
            COLLECTIONS["portfolio_assets"],
            as_of=as_of,
            predicate=lambda record: record["data"]["portfolioId"] == portfolio_id,
        )
        assets = []
        for record in records:
            if record["is_deleted"]:
                continue
            payload = self._portfolio_asset_record(record)
            asset_id = payload["data"]["assetId"]
            asset = self.get_asset(asset_id, as_of=as_of)
            payload["asset"] = asset
            assets.append(payload)
        return assets

    def compare(self, left_asset_id: str, right_asset_id: str, source_id: str, as_of: datetime | str | None = None) -> dict[str, Any]:
        left = self.series(left_asset_id, source_id, as_of=as_of)
        right = self.series(right_asset_id, source_id, as_of=as_of)
        if not left or not right:
            return {"message": "One or both series were not found."}
        return compare_series(left[0], right[0])

    def forecast(self, asset_id: str, source_id: str, as_of: datetime | str | None = None) -> dict[str, Any]:
        series = self.series(asset_id, source_id, as_of=as_of)
        if not series:
            return {"message": "Series not found."}
        summary = series[0]["summary"]
        return {
            "seriesId": series[0]["seriesId"],
            "forecastNextClose": summary["nextCloseForecast"],
            "signal": summary["riskSignal"],
            "trend": summary["momentum"],
        }

    def explain(self, asset_id: str, source_id: str, as_of: datetime | str | None = None) -> str:
        series = self.series(asset_id, source_id, as_of=as_of)
        if not series:
            return "Series not found."
        return explain_change(series[0])

    # Market-memory layer: change history and narratives

    def asset_change_timeline(self, asset_id: str) -> list[dict[str, Any]]:
        """Get the timeline of changes for an asset with their stories."""
        return self.market_memory.get_entity_timeline(COLLECTIONS["instruments"], asset_id)

    def asset_change_narrative(self, asset_id: str) -> str:
        """Build a human-readable narrative of why an asset changed."""
        return self.market_memory.build_change_narrative(COLLECTIONS["instruments"], asset_id)

    def asset_change_story(self, asset_id: str, version: int) -> dict[str, Any] | None:
        """Get the change story for a specific asset version."""
        story = self.market_memory.get_change_story(COLLECTIONS["instruments"], asset_id, version)
        if story is None:
            return None
        return {
            "entityId": story.entity_id,
            "version": story.version,
            "timestamp": story.timestamp,
            "reason": story.reason,
            "changeType": story.change_type,
            "impactedFields": story.impacted_fields,
            "previousValue": story.previous_value,
            "newValue": story.new_value,
        }

    def asset_change_delta(self, asset_id: str, from_version: int, to_version: int) -> dict[str, Any]:
        """Explain what changed between two asset versions."""
        return self.market_memory.explain_version_delta(
            COLLECTIONS["instruments"], asset_id, from_version, to_version
        )

    def source_change_timeline(self, source_id: str) -> list[dict[str, Any]]:
        """Get the timeline of changes for a data source."""
        return self.market_memory.get_entity_timeline(COLLECTIONS["sources"], source_id)

    def source_change_narrative(self, source_id: str) -> str:
        """Build a human-readable narrative of source configuration changes."""
        return self.market_memory.build_change_narrative(COLLECTIONS["sources"], source_id)

    def series_change_timeline(self, series_id: str) -> list[dict[str, Any]]:
        """Get the timeline of changes for a time series."""
        return self.market_memory.get_entity_timeline(COLLECTIONS["series"], series_id)

    def series_change_narrative(self, series_id: str) -> str:
        """Build a human-readable narrative of series changes."""
        return self.market_memory.build_change_narrative(COLLECTIONS["series"], series_id)

    def record_asset_change_story(
        self,
        asset_id: str,
        version: int,
        reason: str,
        change_type: str,
        impacted_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Record a change story for an asset version.
        
        Change types: 'creation', 'metadata_update', 'source_switch', 'correction', 
                      'retirement', 'spec_change', 'reclassification', etc.
        """
        story = self.market_memory.record_change_story(
            COLLECTIONS["instruments"],
            asset_id,
            version,
            reason,
            change_type,
            impacted_fields=impacted_fields,
        )
        return {
            "entityId": story.entity_id,
            "version": story.version,
            "timestamp": story.timestamp,
            "reason": story.reason,
            "changeType": story.change_type,
        }

    # MongoDB integration: cloud persistence and sync

    def connect_mongodb(self, connection_string: str | None = None) -> dict[str, Any]:
        """Connect to MongoDB for cloud backup and sync.
        
        Args:
            connection_string: MongoDB URI. If None, uses MONGODB_URI env var.
        
        Returns:
            Connection status and metadata
        """
        from .mongodb_adapter import get_mongodb_adapter
        from .mongodb_sync import MongoDBSyncService

        adapter = get_mongodb_adapter(connection_string)
        if adapter is None:
            return {
                "status": "error",
                "message": "Failed to connect to MongoDB. Check connection string and network.",
                "hint": "Set MONGODB_URI environment variable or pass connection_string parameter"
            }

        self.mongodb_adapter = adapter
        self.mongodb_sync = MongoDBSyncService(self, adapter)
        
        return {
            "status": "connected",
            "database": adapter.database_name,
            "message": "MongoDB connection established"
        }

    def mongodb_sync_all(self) -> dict[str, Any]:
        """Sync all local collections to MongoDB.
        
        Returns:
            Sync operation summary with per-collection results
        """
        if not hasattr(self, "mongodb_sync"):
            return {"error": "MongoDB not connected. Call connect_mongodb() first."}
        
        return self.mongodb_sync.sync_all_collections()

    def mongodb_sync_collection(self, collection_name: str) -> dict[str, Any]:
        """Sync a specific collection to MongoDB.
        
        Args:
            collection_name: Name of collection to sync
        
        Returns:
            Sync operation result
        """
        if not hasattr(self, "mongodb_sync"):
            return {"error": "MongoDB not connected. Call connect_mongodb() first."}
        
        return self.mongodb_sync.sync_collection(collection_name)

    def mongodb_status(self) -> dict[str, Any]:
        """Get MongoDB connection and data status.
        
        Returns:
            Status including database name and collection statistics
        """
        if not hasattr(self, "mongodb_adapter"):
            return {"status": "disconnected"}
        
        return self.mongodb_sync.get_mongodb_status()

    def mongodb_query_entity_history(self, collection_name: str, entity_id: str) -> list[dict[str, Any]]:
        """Query entity history directly from MongoDB.
        
        Args:
            collection_name: Collection to query
            entity_id: Entity ID to retrieve
        
        Returns:
            Version history for the entity
        """
        if not hasattr(self, "mongodb_adapter"):
            return []
        
        return self.mongodb_adapter.query_entity_history(collection_name, entity_id)

    def mongodb_setup_indexes(self) -> dict[str, Any]:
        """Create indexes on MongoDB collections for performance.
        
        Returns:
            Index creation results
        """
        if not hasattr(self, "mongodb_sync"):
            return {"error": "MongoDB not connected."}
        
        return self.mongodb_sync.setup_indexes()

    def mongodb_disconnect(self) -> dict[str, Any]:
        """Disconnect from MongoDB.
        
        Returns:
            Disconnection status
        """
        if not hasattr(self, "mongodb_adapter"):
            return {"status": "not connected"}
        
        self.mongodb_adapter.close()
        if hasattr(self, "mongodb_sync"):
            delattr(self, "mongodb_sync")
        if hasattr(self, "mongodb_adapter"):
            delattr(self, "mongodb_adapter")
        
        return {"status": "disconnected"}
