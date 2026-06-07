"""MongoDB synchronization service for the warehouse.

Syncs local JSONL data with MongoDB for cloud backup and remote queries.
"""

from __future__ import annotations

from typing import Any

from .mongodb_adapter import MongoDBAdapter
from .repository import WarehouseRepository
from .store import DocumentStore
from .config import COLLECTIONS


class MongoDBSyncService:
    """Service to sync warehouse data with MongoDB."""

    def __init__(self, repository: WarehouseRepository, mongodb_adapter: MongoDBAdapter):
        """Initialize sync service.
        
        Args:
            repository: Local WarehouseRepository instance
            mongodb_adapter: Connected MongoDBAdapter instance
        """
        self.repository = repository
        self.adapter = mongodb_adapter
        self.store = repository.store

    def sync_all_collections(self) -> dict[str, Any]:
        """Sync all local collections to MongoDB.
        
        Returns:
            Summary of sync operation
        """
        summary = {
            "timestamp": self.store._current_time(),
            "collections": {}
        }
        
        for collection_name in COLLECTIONS.values():
            try:
                records = self.store.read_all(collection_name)
                result = self.adapter.sync_from_jsonl(collection_name, records)
                summary["collections"][collection_name] = result
            except Exception as e:
                summary["collections"][collection_name] = {"error": str(e)}
        
        return summary

    def sync_collection(self, collection_name: str) -> dict[str, Any]:
        """Sync a single collection to MongoDB.
        
        Args:
            collection_name: Name of collection to sync
        
        Returns:
            Sync operation summary
        """
        records = self.store.read_all(collection_name)
        return self.adapter.sync_from_jsonl(collection_name, records)

    def get_mongodb_status(self) -> dict[str, Any]:
        """Get status of MongoDB connection and collections."""
        try:
            stats = self.adapter.get_stats()
            return {
                "status": "connected",
                "database": self.adapter.database_name,
                "stats": stats
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    def restore_from_mongodb(self, collection_name: str, target_dir: str | None = None) -> dict[str, Any]:
        """Restore a collection from MongoDB to local JSONL.
        
        Args:
            collection_name: MongoDB collection to restore
            target_dir: Target directory (uses repository's data_dir if None)
        
        Returns:
            Restoration summary
        """
        records = self.adapter.read_collection(collection_name)
        
        if target_dir is None:
            store = DocumentStore(self.store.base_dir)
        else:
            from pathlib import Path
            store = DocumentStore(Path(target_dir))
        
        # Append all records to local store
        for record in records:
            store.append(collection_name, record)
        
        return {
            "collection": collection_name,
            "restored_count": len(records),
            "target_directory": str(store.base_dir)
        }

    def setup_indexes(self) -> dict[str, Any]:
        """Create MongoDB indexes for optimal performance."""
        return self.adapter.create_indexes()
