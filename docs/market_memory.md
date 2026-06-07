# Market-Memory Layer: Asset Change Stories

## Overview

The market-memory layer is an audit trail system that tracks **why** assets changed, not just **what** changed. Every asset version keeps a "story" explaining the reason behind changes.

**Examples of change stories:**
- "price jumped after source switch from Nasdaq to Bloomberg"
- "vendor corrected prior close after regulatory adjustment"
- "asset retired after tombstone — contract no longer offered"
- "metadata reclassified from US region to North America"
- "API endpoint upgraded from v3 to v4"

## Architecture

### Core Components

1. **MarketMemory** (`market_memory.py`)
   - Stores and retrieves change stories
   - Builds timelines with narrative context
   - Explains deltas between versions

2. **Storage Layer**
   - Stories stored in `stories.jsonl` collection
   - Each story linked to entity version
   - Contains: reason, change type, impacted fields, values

3. **Integration Points**
   - `WarehouseRepository`: Public query API
   - `IngestionService`: Automatic story recording during ingestion
   - REST API: HTTP endpoints for market-memory queries

## Data Model

### ChangeStory

```python
@dataclass
class ChangeStory:
    entity_id: str                          # "asset-gm", "source-nasdaq", etc.
    version: int                            # Version number
    timestamp: str                          # ISO 8601 when story was recorded
    reason: str                             # Human-readable explanation
    change_type: str                        # categorical type (see below)
    previous_value: Any | None = None       # Optional: previous value for comparison
    new_value: Any | None = None            # Optional: new value for comparison
    impacted_fields: list[str] | None = None  # Which fields changed
```

### Change Types

Pre-defined categorical reasons:

| Type | Description | Example |
|------|-------------|---------|
| `creation` | Initial version created | Asset onboarded to warehouse |
| `metadata_update` | Configuration/metadata changed | Name, description updated |
| `source_switch` | Changed data source or endpoint | API version upgrade, vendor switch |
| `correction` | Error correction by vendor | Prior close adjusted, region fixed |
| `retirement` | Asset deleted/tombstoned | Contract no longer available |
| `spec_change` | Specification/classification changed | Reclassified from equity to commodity |
| `reclassification` | Market classification changed | Region updated, sector changed |
| `value_change` | Data value changed | Price, volume, etc. |

## API Reference

### Query Endpoints (GET)

#### Asset Timeline
```
GET /assets/{assetId}/change-timeline
```
Returns complete timeline with stories, events, and auto-detected changes.

```json
{
  "assetId": "asset-gm",
  "timeline": [
    {
      "version": 1,
      "validFrom": "2026-01-01T00:00:00Z",
      "event": "creation",
      "data": {...},
      "story": null
    },
    {
      "version": 2,
      "validFrom": "2026-01-14T00:00:00Z",
      "event": "correction",
      "hasDataChange": true,
      "detectedChangedFields": ["region"],
      "story": {
        "reason": "Regional classification corrected from 'US' to 'North America'",
        "changeType": "correction",
        "impactedFields": ["region"]
      }
    }
  ]
}
```

#### Asset Narrative
```
GET /assets/{assetId}/change-narrative
```
Returns human-readable text narrative of all changes.

```
Change history for asset-gm:
  v1 @ 2026-01-01T00:00:00Z: CREATION
  v2 @ 2026-01-14T00:00:00Z: CORRECTION — Regional classification corrected from 'US' to 'North America' (affected: region)
```

#### Change Story
```
GET /assets/{assetId}/change-story?version=2
```
Retrieve the story for a specific version.

```json
{
  "entityId": "asset-gm",
  "version": 2,
  "timestamp": "2026-01-14T10:30:45Z",
  "reason": "Regional classification corrected from 'US' to 'North America' following vendor data governance review",
  "changeType": "correction",
  "impactedFields": ["region"]
}
```

#### Change Delta
```
GET /assets/{assetId}/change-delta?from_version=1&to_version=2
```
Compare two versions with story context.

```json
{
  "from": {
    "version": 1,
    "validFrom": "2026-01-01T00:00:00Z"
  },
  "to": {
    "version": 2,
    "validFrom": "2026-01-14T00:00:00Z"
  },
  "addedFields": [],
  "removedFields": [],
  "changedFields": {
    "region": {
      "from": "US",
      "to": "North America"
    }
  },
  "storyCount": 1,
  "stories": [
    {
      "reason": "Regional classification corrected...",
      "changeType": "correction",
      "impactedFields": ["region"]
    }
  ]
}
```

#### Source Timeline & Narrative
```
GET /sources/{sourceId}/change-timeline
GET /sources/{sourceId}/change-narrative
```
Same pattern as assets, for data sources.

---

### Record Endpoint (POST)

#### Record Change Story
```
POST /market-memory/record-story
```

Request body:
```json
{
  "assetId": "asset-gm",
  "version": 3,
  "reason": "Price adjusted after corporate split announced",
  "changeType": "correction",
  "impactedFields": ["closePrice", "openPrice"]
}
```

Response:
```json
{
  "entityId": "asset-gm",
  "version": 3,
  "timestamp": "2026-01-15T14:22:30Z",
  "reason": "Price adjusted after corporate split announced",
  "changeType": "correction"
}
```

---

## Python API Reference

### WarehouseRepository Methods

```python
# Get timeline with stories
timeline = repo.asset_change_timeline("asset-gm")

# Get human-readable narrative
narrative = repo.asset_change_narrative("asset-gm")

# Get story for specific version
story = repo.asset_change_story("asset-gm", version=2)

# Compare versions with story context
delta = repo.asset_change_delta("asset-gm", from_version=1, to_version=2)

# Similar methods for sources
timeline = repo.source_change_timeline("source-nasdaq")
narrative = repo.source_change_narrative("source-nasdaq")

# Record new change story
result = repo.record_asset_change_story(
    asset_id="asset-gm",
    version=3,
    reason="Price adjusted after corporate split",
    change_type="correction",
    impacted_fields=["closePrice", "openPrice"]
)
```

### MarketMemory Class

Direct usage (for custom integrations):

```python
from dw_warehouse.market_memory import MarketMemory
from dw_warehouse.store import DocumentStore

store = DocumentStore("/path/to/data")
memory = MarketMemory(store)

# Record a story
story = memory.record_change_story(
    collection="instruments",
    entity_id="asset-gm",
    version=2,
    reason="Regional classification corrected...",
    change_type="correction",
    impacted_fields=["region"]
)

# Retrieve story
retrieved = memory.get_change_story("instruments", "asset-gm", 2)

# Build timeline
timeline = memory.get_entity_timeline("instruments", "asset-gm")

# Generate narrative
narrative = memory.build_change_narrative("instruments", "asset-gm")

# Explain delta
delta = memory.explain_version_delta("instruments", "asset-gm", 1, 2)
```

---

## Ingestion with Stories

### Bulk Ingestion with Change Stories

```python
from dw_warehouse.ingest import IngestionService

service = IngestionService(store)

payload = {
    "provider": {...},
    "assets": [...],
    "series": [...],
    # ... standard payload
}

stories = {
    "asset-gm": [
        {
            "version": 2,
            "reason": "Price adjusted for stock split announced",
            "changeType": "correction",
            "impactedFields": ["closePrice", "openPrice"]
        }
    ],
    "source-nasdaq": [
        {
            "collection": "sources",
            "version": 2,
            "reason": "Upgraded API endpoint from v3 to v4",
            "changeType": "source_switch",
            "impactedFields": ["apiEndpoint"]
        }
    ]
}

result = service.ingest_payload_with_stories(payload, stories)
# result["storiesRecorded"] == 2
```

---

## Real-World Examples

### Example 1: Source Migration

```python
# A vendor switches their API endpoint

repo.record_asset_change_story(
    asset_id="source-bloomberg",
    version=3,
    reason="API endpoint migrated from https://old.bloomberg.com to https://new.bloomberg.com for improved latency",
    change_type="source_switch",
    impacted_fields=["apiEndpoint"]
)
```

### Example 2: Data Correction

```python
# Vendor corrects a prior close price due to regulatory issue

repo.record_asset_change_story(
    asset_id="asset-msft",
    version=4,
    reason="Prior close price corrected from 381.20 to 380.95 after SEC adjustment for dividend accounting",
    change_type="correction",
    impacted_fields=["closePrice"],
    previous_value=381.20,
    new_value=380.95
)
```

### Example 3: Asset Reclassification

```python
# Asset reclassified from equity to different category

repo.record_asset_change_story(
    asset_id="asset-xyz",
    version=2,
    reason="Reclassified from 'equity' to 'commodity-derivative' based on updated market data standards",
    change_type="reclassification",
    impacted_fields=["instrumentClass"]
)
```

### Example 4: Retirement/Tombstone

```python
# Asset is retired from the warehouse

repo.record_asset_change_story(
    asset_id="asset-legacy-oil",
    version=2,
    reason="Asset retired. Legacy oil contract OILX no longer offered by vendor after 2026-02-01",
    change_type="retirement",
    impacted_fields=["deletedReason"]
)
```

---

## Auto-Detection Features

The market-memory layer automatically detects:

1. **Field-level changes** — Compares previous vs. current data
2. **Event types** — Creation, updates, retirement
3. **Change narrative** — Suggests "CREATION", "UPDATE", "RETIREMENT" events
4. **Timeline context** — Sorts and sequences all changes chronologically

---

## Storage

Stories are persisted in the `stories.jsonl` collection:

```jsonl
{"collection":"instruments","entity_id":"asset-gm","version":2,"reason":"Regional classification corrected...","change_type":"correction","impacted_fields":["region"],"recorded_at":"2026-01-14T10:30:45Z"}
{"collection":"sources","entity_id":"source-nasdaq","version":2,"reason":"API endpoint upgraded...","change_type":"source_switch","impacted_fields":["apiEndpoint"],"recorded_at":"2026-01-18T12:45:10Z"}
```

---

## Testing

The market-memory layer includes comprehensive tests:

```bash
pytest tests/test_warehouse.py::WarehouseTests::test_asset_change_timeline -v
pytest tests/test_warehouse.py::WarehouseTests::test_asset_change_story_retrieval -v
pytest tests/test_warehouse.py::WarehouseTests::test_asset_change_delta -v
pytest tests/test_warehouse.py::WarehouseTests::test_market_memory_narrative_for_deleted_asset -v
```

---

## Summary

The market-memory layer transforms the data warehouse from a simple **"what changed"** system into a **"why it changed"** system:

- ✅ Explicit change stories attached to every version
- ✅ Categorical change types for structured analysis
- ✅ Field-level impact tracking
- ✅ Human-readable narratives for non-technical users
- ✅ REST API for external integration
- ✅ Temporal queries with story context
- ✅ Retirement/tombstone tracking with explanation
- ✅ Audit trail for compliance and debugging
