from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import uuid4

from .config import COLLECTIONS
from .market_memory import MarketMemory
from .store import DocumentStore, now_utc, to_iso


def demo_payload() -> dict[str, Any]:
    return {
        "provider": {
            "dataSourceId": "source-nasdaq",
            "name": "Nasdaq Data Link",
            "providerType": "market-data-api",
            "apiEndpoint": "https://data.nasdaq.com/api/v3",
        },
        "assets": [
            {
                "assetId": "asset-gm",
                "instrumentClass": "stock",
                "symbol": "GM",
                "name": "General Motors Co.",
                "region": "US",
                "description": "Onboarded equity instrument with standard daily market data.",
                "validFrom": "2026-01-01T00:00:00Z",
            },
            {
                "assetId": "asset-msft",
                "instrumentClass": "stock",
                "symbol": "MSFT",
                "name": "Microsoft Corporation",
                "region": "US",
                "description": "Technology equity instrument used for comparative analytics.",
                "validFrom": "2026-01-01T00:00:00Z",
            },
            {
                "assetId": "asset-btc",
                "instrumentClass": "crypto",
                "symbol": "BTC",
                "name": "Bitcoin",
                "region": "Global",
                "description": "Digital asset sourced from a market-data vendor.",
                "validFrom": "2026-01-01T00:00:00Z",
            },
            {
                "assetId": "asset-legacy-oil",
                "instrumentClass": "commodity-derivative",
                "symbol": "OILX",
                "name": "Legacy Oil Contract",
                "region": "US",
                "description": "Deprecated contract retained for temporal history checks.",
                "validFrom": "2026-01-01T00:00:00Z",
                "deletedFrom": "2026-02-01T00:00:00Z",
            },
        ],
        "sources": [
            {
                "dataSourceId": "source-nasdaq",
                "name": "Nasdaq Data Link",
                "providerType": "market-data-api",
                "apiEndpoint": "https://data.nasdaq.com/api/v3",
                "validFrom": "2026-01-01T00:00:00Z",
            },
            {
                "dataSourceId": "source-bloomberg",
                "name": "Bloomberg Market Data",
                "providerType": "composite-feed",
                "apiEndpoint": "https://api.bloomberg.example/market-data",
                "validFrom": "2026-01-01T00:00:00Z",
            },
        ],
        "series": [
            {
                "seriesId": "series-gm-nasdaq-daily",
                "assetId": "asset-gm",
                "dataSourceId": "source-nasdaq",
                "frequency": "1D",
                "indicators": ["openPrice", "closePrice", "highPrice", "lowPrice", "volume"],
                "validFrom": "2026-01-05T00:00:00Z",
                "points": [
                    {"pointId": "gm-p1", "timestamp": "2026-01-05T00:00:00Z", "openPrice": 32.10, "closePrice": 32.70, "highPrice": 33.12, "lowPrice": 31.90, "volume": 1520000},
                    {"pointId": "gm-p2", "timestamp": "2026-01-06T00:00:00Z", "openPrice": 32.80, "closePrice": 33.15, "highPrice": 33.40, "lowPrice": 32.40, "volume": 1640000},
                    {"pointId": "gm-p3", "timestamp": "2026-01-07T00:00:00Z", "openPrice": 33.10, "closePrice": 32.95, "highPrice": 33.25, "lowPrice": 32.60, "volume": 1410000},
                    {"pointId": "gm-p4", "timestamp": "2026-01-08T00:00:00Z", "openPrice": 33.00, "closePrice": 33.65, "highPrice": 33.80, "lowPrice": 32.85, "volume": 1730000},
                    {"pointId": "gm-p5", "timestamp": "2026-01-09T00:00:00Z", "openPrice": 33.60, "closePrice": 34.12, "highPrice": 34.28, "lowPrice": 33.40, "volume": 1810000},
                ],
            },
            {
                "seriesId": "series-msft-nasdaq-daily",
                "assetId": "asset-msft",
                "dataSourceId": "source-nasdaq",
                "frequency": "1D",
                "indicators": ["openPrice", "closePrice", "highPrice", "lowPrice", "volume", "adjustedClosePrice"],
                "validFrom": "2026-01-05T00:00:00Z",
                "points": [
                    {"pointId": "msft-p1", "timestamp": "2026-01-05T00:00:00Z", "openPrice": 377.20, "closePrice": 379.45, "highPrice": 380.10, "lowPrice": 375.80, "volume": 22400000, "adjustedClosePrice": 379.45},
                    {"pointId": "msft-p2", "timestamp": "2026-01-06T00:00:00Z", "openPrice": 379.50, "closePrice": 381.20, "highPrice": 382.40, "lowPrice": 378.60, "volume": 21900000, "adjustedClosePrice": 381.20},
                    {"pointId": "msft-p3", "timestamp": "2026-01-07T00:00:00Z", "openPrice": 381.00, "closePrice": 380.55, "highPrice": 381.90, "lowPrice": 379.80, "volume": 20800000, "adjustedClosePrice": 380.55},
                    {"pointId": "msft-p4", "timestamp": "2026-01-08T00:00:00Z", "openPrice": 380.60, "closePrice": 383.10, "highPrice": 383.40, "lowPrice": 380.20, "volume": 23200000, "adjustedClosePrice": 383.10},
                    {"pointId": "msft-p5", "timestamp": "2026-01-09T00:00:00Z", "openPrice": 383.15, "closePrice": 385.60, "highPrice": 386.10, "lowPrice": 382.90, "volume": 24500000, "adjustedClosePrice": 385.60},
                ],
            },
            {
                "seriesId": "series-btc-bloomberg-daily",
                "assetId": "asset-btc",
                "dataSourceId": "source-bloomberg",
                "frequency": "1D",
                "indicators": ["openPrice", "closePrice", "highPrice", "lowPrice", "volume", "quotedPrice"],
                "validFrom": "2026-01-05T00:00:00Z",
                "points": [
                    {"pointId": "btc-p1", "timestamp": "2026-01-05T00:00:00Z", "openPrice": 42100.0, "closePrice": 42820.0, "highPrice": 43110.0, "lowPrice": 41950.0, "volume": 3800, "quotedPrice": 42810.0},
                    {"pointId": "btc-p2", "timestamp": "2026-01-06T00:00:00Z", "openPrice": 42840.0, "closePrice": 43390.0, "highPrice": 43620.0, "lowPrice": 42630.0, "volume": 4025, "quotedPrice": 43388.0},
                    {"pointId": "btc-p3", "timestamp": "2026-01-07T00:00:00Z", "openPrice": 43380.0, "closePrice": 43020.0, "highPrice": 43490.0, "lowPrice": 42800.0, "volume": 4155, "quotedPrice": 43021.0},
                    {"pointId": "btc-p4", "timestamp": "2026-01-08T00:00:00Z", "openPrice": 43010.0, "closePrice": 43740.0, "highPrice": 43980.0, "lowPrice": 42990.0, "volume": 4478, "quotedPrice": 43742.0},
                    {"pointId": "btc-p5", "timestamp": "2026-01-09T00:00:00Z", "openPrice": 43780.0, "closePrice": 44190.0, "highPrice": 44390.0, "lowPrice": 43640.0, "volume": 4688, "quotedPrice": 44188.0},
                ],
            },
        ],
        "portfolios": [
            {
                "portfolioId": "portfolio-acme-2026",
                "ownerName": "Acme Ltd Treasury Desk",
                "creationDate": "2026-01-12",
                "validFrom": "2026-01-12T00:00:00Z",
            }
        ],
        "portfolioAssets": [
            {
                "portfolioAssetId": "portfolio-asset-gm",
                "portfolioId": "portfolio-acme-2026",
                "assetId": "asset-gm",
                "quantity": 120,
                "purchasePrice": 32.42,
                "validFrom": "2026-01-12T00:00:00Z",
            },
            {
                "portfolioAssetId": "portfolio-asset-msft",
                "portfolioId": "portfolio-acme-2026",
                "assetId": "asset-msft",
                "quantity": 40,
                "purchasePrice": 378.12,
                "validFrom": "2026-01-12T00:00:00Z",
            },
            {
                "portfolioAssetId": "portfolio-asset-btc",
                "portfolioId": "portfolio-acme-2026",
                "assetId": "asset-btc",
                "quantity": 2.5,
                "purchasePrice": 42800.00,
                "validFrom": "2026-01-12T00:00:00Z",
            },
        ],
    }


class IngestionService:
    def __init__(self, store: DocumentStore):
        self.store = store
        self.market_memory = MarketMemory(store)

    def ingest_payload(self, payload: dict[str, Any], provider_override: dict[str, Any] | None = None) -> dict[str, Any]:
        imported_at = to_iso(now_utc())
        provider = provider_override or payload["provider"]
        provenance = {
            "provider": provider["name"],
            "providerType": provider.get("providerType"),
            "apiEndpoint": provider.get("apiEndpoint"),
            "importedAt": imported_at,
            "batchId": payload.get("batchId", f"batch-{uuid4().hex[:10]}"),
        }
        summary = {
            "assets": 0,
            "sources": 0,
            "series": 0,
            "points": 0,
            "portfolios": 0,
            "portfolioAssets": 0,
        }
        for source in payload.get("sources", []):
            self.store.append_version(
                COLLECTIONS["sources"],
                "DataSource",
                source["dataSourceId"],
                {
                    "dataSourceId": source["dataSourceId"],
                    "name": source["name"],
                    "providerType": source["providerType"],
                    "apiEndpoint": source["apiEndpoint"],
                },
                provenance,
                valid_from=source.get("validFrom"),
            )
            summary["sources"] += 1
        for asset in payload.get("assets", []):
            deleted_from = asset.get("deletedFrom")
            self.store.append_version(
                COLLECTIONS["instruments"],
                "FinancialInstrument",
                asset["assetId"],
                {
                    "assetId": asset["assetId"],
                    "instrumentClass": asset["instrumentClass"],
                    "symbol": asset["symbol"],
                    "name": asset["name"],
                    "region": asset["region"],
                    "description": asset["description"],
                },
                provenance,
                valid_from=asset.get("validFrom"),
            )
            summary["assets"] += 1
            if deleted_from is not None:
                self.store.append_version(
                    COLLECTIONS["instruments"],
                    "FinancialInstrument",
                    asset["assetId"],
                    {
                        "assetId": asset["assetId"],
                        "instrumentClass": asset["instrumentClass"],
                        "symbol": asset["symbol"],
                        "name": asset["name"],
                        "region": asset["region"],
                        "description": asset["description"],
                        "deletedReason": "retired from market data warehouse",
                    },
                    provenance,
                    valid_from=deleted_from,
                    is_deleted=True,
                )
                summary["assets"] += 1
        for series in payload.get("series", []):
            self.store.append_version(
                COLLECTIONS["series"],
                "TimeSeries",
                series["seriesId"],
                {
                    "seriesId": series["seriesId"],
                    "assetId": series["assetId"],
                    "dataSourceId": series["dataSourceId"],
                    "frequency": series["frequency"],
                    "indicators": series.get("indicators", []),
                },
                provenance,
                valid_from=series.get("validFrom"),
            )
            summary["series"] += 1
            for point in series.get("points", []):
                point_payload = {key: value for key, value in point.items() if key != "pointId"}
                point_payload["seriesId"] = series["seriesId"]
                self.store.append_version(
                    COLLECTIONS["points"],
                    "TimeSeriesPoint",
                    point["pointId"],
                    point_payload,
                    provenance,
                    valid_from=point["timestamp"],
                )
                summary["points"] += 1
        for portfolio in payload.get("portfolios", []):
            self.store.append_version(
                COLLECTIONS["portfolios"],
                "Portfolio",
                portfolio["portfolioId"],
                {
                    "portfolioId": portfolio["portfolioId"],
                    "ownerName": portfolio["ownerName"],
                    "creationDate": portfolio["creationDate"],
                },
                provenance,
                valid_from=portfolio.get("validFrom"),
            )
            summary["portfolios"] += 1
        for link in payload.get("portfolioAssets", []):
            self.store.append_version(
                COLLECTIONS["portfolio_assets"],
                "PortfolioAsset",
                link["portfolioAssetId"],
                {
                    "portfolioAssetId": link["portfolioAssetId"],
                    "portfolioId": link["portfolioId"],
                    "assetId": link["assetId"],
                    "quantity": link["quantity"],
                    "purchasePrice": link["purchasePrice"],
                },
                provenance,
                valid_from=link.get("validFrom"),
            )
            summary["portfolioAssets"] += 1
        return {"provenance": provenance, "summary": summary}

    def ingest_payload_with_stories(
        self,
        payload: dict[str, Any],
        stories: dict[str, list[dict[str, Any]]] | None = None,
        provider_override: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Ingest payload and record change stories.
        
        Args:
            payload: Standard ingestion payload
            stories: Dict mapping entity IDs to their change stories.
                     Example: {
                         "asset-gm": [
                             {
                                 "version": 2,
                                 "reason": "price jumped after source switch from nasdaq to bloomberg",
                                 "changeType": "source_switch",
                                 "impactedFields": ["closePrice", "volume"]
                             }
                         ]
                     }
            provider_override: Override provider info
        
        Returns:
            Same as ingest_payload plus recorded stories
        """
        result = self.ingest_payload(payload, provider_override)
        
        if stories:
            for entity_id, entity_stories in stories.items():
                for story_info in entity_stories:
                    self.market_memory.record_change_story(
                        collection=story_info.get("collection", COLLECTIONS["instruments"]),
                        entity_id=entity_id,
                        version=story_info["version"],
                        reason=story_info["reason"],
                        change_type=story_info["changeType"],
                        impacted_fields=story_info.get("impactedFields"),
                    )
            result["storiesRecorded"] = sum(len(s) for s in stories.values())
        
        return result


def seed_demo_warehouse(store: DocumentStore) -> dict[str, Any]:
    if store.read_all(COLLECTIONS["instruments"]):
        return {"status": "already-seeded"}
    service = IngestionService(store)
    result = service.ingest_payload(deepcopy(demo_payload()))

    provenance = {
        "provider": "Nasdaq Data Link",
        "providerType": "market-data-api",
        "apiEndpoint": "https://data.nasdaq.com/api/v3",
        "importedAt": to_iso(now_utc()),
        "batchId": f"batch-{uuid4().hex[:10]}",
    }
    store.append_version(
        COLLECTIONS["instruments"],
        "FinancialInstrument",
        "asset-gm",
        {
            "assetId": "asset-gm",
            "instrumentClass": "stock",
            "symbol": "GM",
            "name": "General Motors Co.",
            "region": "North America",
            "description": "Corrected regional classification after vendor review.",
        },
        provenance,
        valid_from="2026-01-14T00:00:00Z",
    )
    store.append_version(
        COLLECTIONS["sources"],
        "DataSource",
        "source-nasdaq",
        {
            "dataSourceId": "source-nasdaq",
            "name": "Nasdaq Data Link",
            "providerType": "market-data-api",
            "apiEndpoint": "https://data.nasdaq.com/api/v4",
        },
        provenance,
        valid_from="2026-01-18T00:00:00Z",
    )
    result["summary"]["assets"] += 1
    result["summary"]["sources"] += 1
    
    # Record market-memory stories explaining the changes
    memory = MarketMemory(store)
    
    # Story for asset-gm version 2 (regional reclassification)
    memory.record_change_story(
        collection=COLLECTIONS["instruments"],
        entity_id="asset-gm",
        version=2,
        reason="Regional classification corrected from 'US' to 'North America' following vendor data governance review",
        change_type="correction",
        impacted_fields=["region"],
    )
    
    # Story for asset-legacy-oil version 2 (retirement)
    memory.record_change_story(
        collection=COLLECTIONS["instruments"],
        entity_id="asset-legacy-oil",
        version=2,
        reason="Asset retired from active tracking. Legacy oil contract OILX no longer offered by vendor after 2026-02-01.",
        change_type="retirement",
        impacted_fields=["deletedReason"],
    )
    
    # Story for source-nasdaq version 2 (API endpoint update)
    memory.record_change_story(
        collection=COLLECTIONS["sources"],
        entity_id="source-nasdaq",
        version=2,
        reason="API endpoint upgraded from v3 to v4 to access new market data indicators and improved latency",
        change_type="source_switch",
        impacted_fields=["apiEndpoint"],
    )
    
    result["storiesRecorded"] = 3
    return result
