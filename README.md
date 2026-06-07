# AuroraVault Financial Data Warehouse

AuroraVault is a compact, runnable data warehouse for financial markets data. It follows the lab's conceptual model and schema:

- `FinancialInstrument`
- `TimeSeries`
- `TimeSeriesPoint`
- `DataSource`
- `Portfolio`
- `PortfolioAsset`

The design is intentionally unique: it uses an append-only document store with record hashes for provenance and temporal history. Nothing is overwritten in place; new versions are appended, and deletions are represented by explicit tombstone records.

## What is included

- A local NoSQL-style warehouse built on JSONL document collections.
- A REST API for asset, source, time-series, portfolio, and analytics queries.
- An ingestion pipeline that records provenance from external-provider style payloads.
- An MCP server exposing tools for LLM clients.
- A seeded demo dataset with stocks, crypto, time series, and a portfolio.
- Tests that validate temporal behavior and API responses.

## Project layout

- `dw_warehouse/` - main package
- `scripts/seed_demo.py` - seed helper
- `tests/` - unit tests
- `docs/report.md` - short project report

## Run it

The project only uses the Python standard library.

```bash
python -m dw_warehouse.cli seed --data-dir data/warehouse
python -m dw_warehouse.cli api --data-dir data/warehouse --port 8000
```

Open these endpoints:

- `GET /health`
- `GET /assets`
- `GET /assets/{assetId}`
- `GET /sources`
- `GET /sources/{dataSourceId}`
- `GET /series?asset_id=...&source_id=...`
- `GET /analytics/summary?asset_id=...&source_id=...`
- `GET /analytics/compare?left_asset_id=...&right_asset_id=...&source_id=...`
- `GET /analytics/forecast?asset_id=...&source_id=...`
- `GET /assets/{assetId}/history`
- `GET /assets/{assetId}/history/view`
- `GET /portfolios`
- `GET /portfolios/{portfolioId}`
- `POST /ingest/provider`

## MongoDB Integration

Connect the warehouse to MongoDB Atlas for cloud backup and sync:

### Setup

1. Copy `.env.example` to `.env` and add your MongoDB connection string:

```bash
cp .env.example .env
```

```env
MONGODB_URI=mongodb+srv://user:password@cluster.u4sckpr.mongodb.net/?appName=Cluster0
MONGODB_DATABASE=aurora_vault
```

2. Install pymongo:

```bash
pip install pymongo
```

### API Endpoints

**Connect to MongoDB:**
```bash
curl -X POST http://localhost:8000/mongodb/connect \
  -H "Content-Type: application/json" \
  -d '{"connectionString": "mongodb+srv://..."}'
```

**Sync all collections to MongoDB:**
```bash
curl -X POST http://localhost:8000/mongodb/sync-all
```

**Sync specific collection:**
```bash
curl -X POST http://localhost:8000/mongodb/sync-collection \
  -H "Content-Type: application/json" \
  -d '{"collection": "instruments"}'
```

**Setup indexes for performance:**
```bash
curl -X POST http://localhost:8000/mongodb/setup-indexes
```

**Check MongoDB status:**
```bash
curl http://localhost:8000/mongodb/status
```

**Query entity history from MongoDB:**
```bash
curl "http://localhost:8000/mongodb/entity-history?collection=instruments&entity_id=asset-gm"
```

**Disconnect:**
```bash
curl -X POST http://localhost:8000/mongodb/disconnect
```

### Python Usage

```python
from dw_warehouse.repository import WarehouseRepository

repo = WarehouseRepository("data/warehouse")

# Connect to MongoDB
status = repo.connect_mongodb("mongodb+srv://...")
print(status)

# Sync all collections
result = repo.mongodb_sync_all()
print(result)

# Check status
status = repo.mongodb_status()
print(status)

# Disconnect
repo.mongodb_disconnect()
```

## MCP tools

Run the MCP server with:

```bash
python -m dw_warehouse.cli mcp --data-dir data/warehouse
```

Available tools:

- `list_assets`
- `get_asset`
- `list_sources`
- `get_source`
- `fetch_time_series`
- `summarize_trends`
- `compare_assets`
- `explain_change`
- `show_asset_history`

### Asset history view

The history endpoint and MCP tool return a compact timeline that shows:

- asset version changes,
- source changes linked to the asset's series,
- tombstones for retired assets,
- an ASCII timeline so the evolution is easy to read in a terminal or demo.
- a browser-ready HTML view with a Mermaid diagram.

## Demo flow

1. Seed the demo data.
2. Start the REST API.
3. List assets and inspect one asset.
4. Fetch a time series and compare it to another asset.
5. Ask an MCP client to call the tools above for grounded answers.

## Tests

```bash
python -m unittest discover -s tests
```

## MCP demo client

Run the end-to-end grounded MCP demo with:

```bash
python scripts/mcp_client_demo.py --data-dir data/warehouse
```

The script seeds the warehouse, starts the local MCP stdio server, lists the available tools, and calls them with real data.
