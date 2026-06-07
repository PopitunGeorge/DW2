"""MongoDB adapter for the data warehouse.

This module provides integration with MongoDB for:
- Backing up/syncing local warehouse data
- Reading from MongoDB as an alternative store
- Cloud-based data persistence
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False


class MongoDBAdapter:
    """Adapter for MongoDB integration with the warehouse."""

    def __init__(self, connection_string: str | None = None, database_name: str = "aurora_vault"):
        """Initialize MongoDB adapter.
        
        Args:
            connection_string: MongoDB connection URI. If None, uses MONGODB_URI env var.
            database_name: Name of the MongoDB database to use.
        """
        if not MONGODB_AVAILABLE:
            raise ImportError("pymongo is required for MongoDB support. Install with: pip install pymongo")

        self.connection_string = connection_string or os.getenv("MONGODB_URI")
        if not self.connection_string:
            raise ValueError(
                "MongoDB connection string not provided. "
                "Pass connection_string arg or set MONGODB_URI environment variable."
            )

        self.database_name = database_name
        self.client: MongoClient | None = None
        self.db = None
        self._connect()

    def _connect(self) -> None:
        """Establish connection to MongoDB."""
        try:
            self.client = MongoClient(self.connection_string, serverSelectionTimeoutMS=5000)
            # Verify connection
            self.client.admin.command("ping")
            self.db = self.client[self.database_name]
            print(f"✅ Connected to MongoDB database: {self.database_name}")
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            raise ConnectionError(f"Failed to connect to MongoDB: {e}")

    def close(self) -> None:
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            print("❌ Disconnected from MongoDB")

    def collection_exists(self, collection_name: str) -> bool:
        """Check if a collection exists in MongoDB."""
        if not self.db:
            return False
        return collection_name in self.db.list_collection_names()

    def get_collection(self, collection_name: str) -> Any:
        """Get a MongoDB collection."""
        if not self.db:
            raise RuntimeError("Not connected to MongoDB")
        return self.db[collection_name]

    def sync_from_jsonl(self, collection_name: str, records: list[dict[str, Any]]) -> dict[str, Any]:
        """Sync JSONL records to MongoDB collection.
        
        Args:
            collection_name: Target collection name
            records: List of document dictionaries
        
        Returns:
            Summary with inserted/updated counts
        """
        if not self.db:
            raise RuntimeError("Not connected to MongoDB")

        collection = self.db[collection_name]
        inserted_count = 0
        updated_count = 0
        
        for record in records:
            # Use entity_id and version as unique key
            if "entity_id" in record and "version" in record:
                filter_query = {
                    "entity_id": record["entity_id"],
                    "version": record["version"]
                }
                result = collection.update_one(
                    filter_query,
                    {"$set": record},
                    upsert=True
                )
                if result.upserted_id:
                    inserted_count += 1
                elif result.modified_count > 0:
                    updated_count += 1
            else:
                # Fallback: insert as new document
                collection.insert_one(record)
                inserted_count += 1
        
        return {
            "collection": collection_name,
            "inserted": inserted_count,
            "updated": updated_count,
            "total": len(records),
            "synced_at": datetime.utcnow().isoformat() + "Z"
        }

    def read_collection(self, collection_name: str, limit: int | None = None) -> list[dict[str, Any]]:
        """Read documents from a MongoDB collection.
        
        Args:
            collection_name: Collection to read from
            limit: Maximum number of documents to return
        
        Returns:
            List of documents
        """
        if not self.db:
            raise RuntimeError("Not connected to MongoDB")

        collection = self.db[collection_name]
        query = collection.find({})
        
        if limit:
            query = query.limit(limit)
        
        docs = list(query)
        # Remove MongoDB's _id field for cleaner output
        for doc in docs:
            doc.pop("_id", None)
        
        return docs

    def query_entity_history(self, collection_name: str, entity_id: str) -> list[dict[str, Any]]:
        """Get version history for a specific entity.
        
        Args:
            collection_name: Collection to query
            entity_id: Entity identifier
        
        Returns:
            List of documents sorted by version
        """
        if not self.db:
            raise RuntimeError("Not connected to MongoDB")

        collection = self.db[collection_name]
        docs = list(collection.find({"entity_id": entity_id}).sort("version", 1))
        
        for doc in docs:
            doc.pop("_id", None)
        
        return docs

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the MongoDB warehouse."""
        if not self.db:
            raise RuntimeError("Not connected to MongoDB")

        stats = {
            "database": self.database_name,
            "collections": {}
        }
        
        for collection_name in self.db.list_collection_names():
            collection = self.db[collection_name]
            stats["collections"][collection_name] = {
                "document_count": collection.count_documents({}),
                "indexes": len(list(collection.list_indexes()))
            }
        
        return stats

    def create_indexes(self) -> dict[str, Any]:
        """Create indexes for better query performance."""
        if not self.db:
            raise RuntimeError("Not connected to MongoDB")

        indexes_created = {}
        collections_to_index = [
            ("instruments", [("entity_id", 1), ("version", -1)]),
            ("sources", [("entity_id", 1), ("version", -1)]),
            ("series", [("entity_id", 1), ("version", -1), ("data.assetId", 1)]),
            ("points", [("entity_id", 1), ("version", -1), ("data.seriesId", 1)]),
            ("portfolios", [("entity_id", 1), ("version", -1)]),
            ("portfolio_assets", [("entity_id", 1), ("version", -1)]),
            ("stories", [("entity_id", 1), ("version", 1)]),
        ]
        
        for collection_name, index_spec in collections_to_index:
            try:
                collection = self.db[collection_name]
                index_name = collection.create_index(index_spec)
                indexes_created[collection_name] = index_name
            except Exception as e:
                indexes_created[collection_name] = f"Error: {e}"
        
        return indexes_created

    def clear_collection(self, collection_name: str) -> dict[str, Any]:
        """Clear all documents from a collection.
        
        ⚠️ WARNING: This is destructive!
        """
        if not self.db:
            raise RuntimeError("Not connected to MongoDB")

        collection = self.db[collection_name]
        result = collection.delete_many({})
        
        return {
            "collection": collection_name,
            "deleted_count": result.deleted_count,
            "warning": "This operation cannot be undone"
        }


def get_mongodb_adapter(connection_string: str | None = None) -> MongoDBAdapter | None:
    """Factory function to get MongoDB adapter with graceful fallback.
    
    Returns None if MongoDB is not available or connection fails.
    """
    if not MONGODB_AVAILABLE:
        return None
    
    try:
        return MongoDBAdapter(connection_string)
    except (ConnectionError, ValueError):
        return None
