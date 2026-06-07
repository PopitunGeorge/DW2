# MongoDB Integration Guide

## Overview

AuroraVault now supports MongoDB integration for cloud-based data persistence and backup. This guide explains how to set up and use MongoDB with your warehouse.

## Setup

### 1. Environment Configuration

The MongoDB connection string is loaded from the `.env` file in the project root:

```bash
# .env file
MONGODB_URI=mongodb+srv://alexandrupopitu0_db_user:miR25swLOnftWEDp@cluster0.u4sckpr.mongodb.net/?appName=Cluster0
MONGODB_DATABASE=aurora_vault
```

**Important:** The `.env` file is excluded from version control (see `.gitignore`). Never commit credentials!

### 2. Install MongoDB Python Driver

```bash
pip install pymongo
```

## Quick Start

### Python

```python
from dw_warehouse.repository import WarehouseRepository

# Initialize warehouse
repo = WarehouseRepository("data/warehouse")

# Connect to MongoDB
status = repo.connect_mongodb()
print(status)
# Output: {'status': 'connected', 'database': 'aurora_vault', 'message': '...'}

# Sync all local data to MongoDB
sync_result = repo.mongodb_sync_all()
print(sync_result)

# Check status
status = repo.mongodb_status()
print(status)

# Query from MongoDB
history = repo.mongodb_query_entity_history("instruments", "asset-gm")
print(history)

# Cleanup
repo.mongodb_disconnect()
```

### REST API

Start the API server:
```bash
python -m dw_warehouse.cli api --data-dir data/warehouse --port 8000
```

Then use the MongoDB endpoints:

```bash
# Connect
curl -X POST http://localhost:8000/mongodb/connect

# Sync all collections
curl -X POST http://localhost:8000/mongodb/sync-all

# Check status
curl http://localhost:8000/mongodb/status

# Query entity history
curl "http://localhost:8000/mongodb/entity-history?collection=instruments&entity_id=asset-gm"

# Disconnect
curl -X POST http://localhost:8000/mongodb/disconnect
```

## API Reference

### Methods

#### connect_mongodb(connection_string=None)
Establishes connection to MongoDB. If `connection_string` is None, uses `MONGODB_URI` from environment.

```python
repo.connect_mongodb()
# or with explicit connection string
repo.connect_mongodb("mongodb+srv://user:pass@cluster.mongodb.net/db")
```

#### mongodb_sync_all()
Syncs all local warehouse collections to MongoDB. Creates/updates documents as needed.

```python
result = repo.mongodb_sync_all()
# Returns: {'timestamp': '...', 'collections': {...}}
```

#### mongodb_sync_collection(collection_name)
Syncs a single collection to MongoDB.

```python
result = repo.mongodb_sync_collection("instruments")
# Returns: {'collection': 'instruments', 'inserted': 5, 'updated': 2, ...}
```

#### mongodb_status()
Retrieves current MongoDB connection status and statistics.

```python
status = repo.mongodb_status()
# Returns: {'status': 'connected', 'database': 'aurora_vault', 'stats': {...}}
```

#### mongodb_query_entity_history(collection_name, entity_id)
Queries MongoDB directly for entity version history.

```python
history = repo.mongodb_query_entity_history("instruments", "asset-gm")
# Returns: [{'entity_id': 'asset-gm', 'version': 1, ...}, ...]
```

#### mongodb_setup_indexes()
Creates performance indexes on all collections in MongoDB.

```python
result = repo.mongodb_setup_indexes()
# Returns: {'instruments': 'index_name', 'sources': 'index_name', ...}
```

#### mongodb_disconnect()
Closes the MongoDB connection.

```python
repo.mongodb_disconnect()
```

## Data Synchronization

### One-Way Sync (Local → MongoDB)

The `mongodb_sync_*` methods perform one-way synchronization from local JSONL files to MongoDB:

1. Read all documents from local JSONL collection
2. For each document:
   - If `(entity_id, version)` exists in MongoDB: update it
   - If not exists: insert as new document
3. Return counts of inserted/updated documents

```python
# Sync everything
result = repo.mongodb_sync_all()

# Inspect results
for collection, summary in result['collections'].items():
    print(f"{collection}: {summary['inserted']} inserted, {summary['updated']} updated")
```

### Querying from MongoDB

After syncing, you can query MongoDB directly without reading local JSONL:

```python
# Get all versions of an asset from MongoDB
history = repo.mongodb_query_entity_history("instruments", "asset-gm")

# Each version record includes all metadata
for record in history:
    print(f"v{record['version']}: {record['data']}")
```

## Performance Optimization

### Create Indexes

MongoDB queries are faster with proper indexes:

```python
# Create indexes on all collections
repo.mongodb_setup_indexes()
```

This creates compound indexes on:
- `(entity_id, version)` for efficient history queries
- `(entity_id, version, data.assetId)` for asset lookups
- etc.

### Indexes Created

| Collection | Index |
|-----------|-------|
| instruments | (entity_id, version) |
| sources | (entity_id, version) |
| series | (entity_id, version, data.assetId) |
| points | (entity_id, version, data.seriesId) |
| portfolios | (entity_id, version) |
| portfolio_assets | (entity_id, version) |
| stories | (entity_id, version) |

## Example Workflow

```python
from dw_warehouse.repository import WarehouseRepository

# 1. Create local warehouse with demo data
repo = WarehouseRepository("data/warehouse")
repo.seed_demo()

# 2. Connect to MongoDB Atlas
result = repo.connect_mongodb()
if result['status'] != 'connected':
    print(f"Connection failed: {result}")
    exit(1)

# 3. Set up indexes for performance
indexes = repo.mongodb_setup_indexes()
print(f"Created indexes: {indexes}")

# 4. Sync all local data to cloud
sync_result = repo.mongodb_sync_all()
for collection, summary in sync_result['collections'].items():
    print(f"Synced {collection}: {summary['inserted']} new, {summary['updated']} updated")

# 5. Query from MongoDB to verify
gm_history = repo.mongodb_query_entity_history("instruments", "asset-gm")
print(f"Found {len(gm_history)} versions of asset-gm in MongoDB")

# 6. Check overall status
status = repo.mongodb_status()
print(f"MongoDB database stats: {status['stats']}")

# 7. Cleanup
repo.mongodb_disconnect()
```

## Troubleshooting

### Connection Failures

**Error**: `ConnectionFailure: connection refused`

**Solutions:**
1. Check MongoDB connection string in `.env`
2. Verify MongoDB Atlas cluster is running
3. Check network access (IP whitelist in MongoDB Atlas)
4. Verify credentials (username, password, cluster name)

### "pymongo is required"

**Error**: `ImportError: pymongo is required for MongoDB support`

**Solution**: Install pymongo
```bash
pip install pymongo
```

### Duplicate Key Errors

**Error**: `pymongo.errors.DuplicateKeyError`

**Cause**: Trying to insert documents with duplicate `(entity_id, version)` combinations

**Solution**: The sync service uses `upsert=True`, so duplicates are handled gracefully by updating existing documents

### Connection Timeout

**Error**: `ServerSelectionTimeoutError`

**Solutions:**
1. Verify MongoDB Atlas cluster is active
2. Check internet connection
3. Increase timeout: `MongoClient(..., serverSelectionTimeoutMS=10000)`

## Architecture

### Components

```
┌─────────────────────────────────────┐
│    WarehouseRepository              │
│  (connect_mongodb, sync_all, etc)   │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│    MongoDBSyncService               │
│  (Orchestrates syncing)             │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│    MongoDBAdapter                   │
│  (Low-level MongoDB operations)     │
└──────────────┬──────────────────────┘
               │
        MongoDB Atlas
```

### Data Flow: Sync

```
Local JSONL Files
      │
      └─▶ DocumentStore.read_all()
           │
           └─▶ MongoDBSyncService.sync_from_jsonl()
                │
                └─▶ MongoDBAdapter.sync_from_jsonl()
                     │
                     └─▶ collection.update_one(..., upsert=True)
                          │
                          └─▶ MongoDB Atlas
```

### Data Flow: Query

```
MongoDB Atlas
      │
      └─▶ MongoDBAdapter.query_entity_history()
           │
           └─▶ collection.find({"entity_id": ...})
                │
                └─▶ WarehouseRepository.mongodb_query_entity_history()
                     │
                     └─▶ Client Application
```

## Security Best Practices

1. **Never commit `.env`**: It's in `.gitignore` for a reason
2. **Use strong passwords**: MongoDB Atlas enforces this
3. **IP Whitelist**: Restrict access to your app servers only
4. **Database Users**: Use dedicated MongoDB users with minimal permissions
5. **Environment Variables**: In production, use proper secrets management (AWS Secrets Manager, Vault, etc.)

## FAQ

**Q: Can I sync back from MongoDB to local?**
A: Not yet. Current implementation is one-way (local → MongoDB). See `mongodb_sync.py` for extension points.

**Q: How often should I sync?**
A: As needed. You might sync:
- After ingesting new data
- Periodically (daily/weekly) for backup
- Before important analysis

**Q: Can I use this with MongoDB Community Edition?**
A: Yes! Just provide the connection string to your MongoDB instance instead of Atlas.

**Q: What about data deletion?**
A: Synced documents are never automatically deleted. To clear MongoDB, use the admin API or MongoDB Atlas console.

## Next Steps

- [View Market-Memory documentation](market_memory.md)
- [Review API endpoints](../README.md#mongodb-integration)
- [Run examples](../scripts/market_memory_examples.py)
