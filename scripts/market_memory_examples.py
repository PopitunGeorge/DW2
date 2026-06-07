#!/usr/bin/env python3
"""
Market-Memory Examples
======================
Demonstrates how to use the market-memory layer to track and query asset change stories.
"""

from pathlib import Path
from dw_warehouse.repository import WarehouseRepository
from dw_warehouse.ingest import IngestionService


def example_1_explore_change_history():
    """Example 1: Explore asset change history with stories."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Explore Asset Change History")
    print("="*70)
    
    repo = WarehouseRepository("data/warehouse")
    
    # Get the full timeline with change stories
    print("\n📅 Asset Timeline (with stories):")
    timeline = repo.asset_change_timeline("asset-gm")
    for entry in timeline:
        version = entry["version"]
        event = entry.get("event", "update").upper()
        valid_from = entry["validFrom"]
        print(f"\n  Version {version} @ {valid_from}: {event}")
        
        if "story" in entry:
            story = entry["story"]
            print(f"    📖 Reason: {story['reason']}")
            print(f"    🏷️  Type: {story['changeType']}")
            if story.get("impactedFields"):
                print(f"    🎯 Fields: {', '.join(story['impactedFields'])}")


def example_2_human_narrative():
    """Example 2: Get human-readable change narrative."""
    print("\n" + "="*70)
    print("EXAMPLE 2: Human-Readable Change Narrative")
    print("="*70)
    
    repo = WarehouseRepository("data/warehouse")
    
    # Get narrative for asset
    print("\n📖 Asset Narrative:")
    narrative = repo.asset_change_narrative("asset-gm")
    print(narrative)
    
    # Get narrative for retired asset
    print("\n📖 Retired Asset Narrative (asset-legacy-oil):")
    narrative = repo.asset_change_narrative("asset-legacy-oil")
    print(narrative)


def example_3_compare_versions():
    """Example 3: Compare two versions with story context."""
    print("\n" + "="*70)
    print("EXAMPLE 3: Compare Versions with Story Context")
    print("="*70)
    
    repo = WarehouseRepository("data/warehouse")
    
    # Get delta between versions (asset-gm has v1 only, so check asset-legacy-oil)
    print("\n🔄 Delta between v1 and v2 (asset-legacy-oil):")
    delta = repo.asset_change_delta("asset-legacy-oil", 1, 2)
    
    if delta.get("error"):
        print(f"  ⚠️  {delta['error']}")
        print("  (This is expected if only v1 exists)")
    else:
        print(f"  From: v{delta['from']['version']} @ {delta['from']['validFrom']}")
        print(f"  To:   v{delta['to']['version']} @ {delta['to']['validFrom']}")
        
        if delta.get("changedFields"):
            print("\n  Changed fields:")
            for field, change in delta["changedFields"].items():
                print(f"    {field}: {change['from']} → {change['to']}")
        
        if delta.get("stories"):
            print(f"\n  {len(delta['stories'])} story/stories explaining changes:")
            for story in delta["stories"]:
                print(f"    • {story['reason']}")
                print(f"      Type: {story['change_type']}")


def example_4_query_specific_story():
    """Example 4: Query a specific change story."""
    print("\n" + "="*70)
    print("EXAMPLE 4: Query Specific Change Story")
    print("="*70)
    
    repo = WarehouseRepository("data/warehouse")
    
    # Get story for specific version (asset-legacy-oil v2 has retirement story)
    print("\n🎯 Change story for asset-legacy-oil v2:")
    story = repo.asset_change_story("asset-legacy-oil", 2)
    
    if story:
        print(f"  Entity: {story['entityId']}")
        print(f"  Version: {story['version']}")
        print(f"  Reason: {story['reason']}")
        print(f"  Type: {story['changeType']}")
        print(f"  Impacted fields: {', '.join(story['impactedFields']) if story['impactedFields'] else 'None'}")
    else:
        print("  ⚠️  No story found for this version")
        # Try asset-gm v2 if available
        print("\n🎯 Change story for asset-gm v2:")
        story = repo.asset_change_story("asset-gm", 2)
        if story:
            print(f"  Entity: {story['entityId']}")
            print(f"  Version: {story['version']}")
            print(f"  Reason: {story['reason']}")
            print(f"  Type: {story['changeType']}")
        else:
            print("  ⚠️  No story found (asset-gm may only have 1 version)")


def example_5_data_source_changes():
    """Example 5: Track data source configuration changes."""
    print("\n" + "="*70)
    print("EXAMPLE 5: Data Source Configuration Changes")
    print("="*70)
    
    repo = WarehouseRepository("data/warehouse")
    
    # Get source timeline
    print("\n📊 Data source timeline (source-nasdaq):")
    timeline = repo.source_change_timeline("source-nasdaq")
    
    for entry in timeline:
        version = entry["version"]
        valid_from = entry["validFrom"]
        print(f"\n  Version {version} @ {valid_from}")
        
        if "story" in entry:
            story = entry["story"]
            print(f"    📖 {story['reason']}")
            print(f"    🏷️  {story['changeType']}")


def example_6_record_new_story():
    """Example 6: Record a new change story manually."""
    print("\n" + "="*70)
    print("EXAMPLE 6: Record New Change Story")
    print("="*70)
    
    repo = WarehouseRepository("data/warehouse")
    
    # Simulate recording a new change
    print("\n📝 Recording new change story...")
    result = repo.record_asset_change_story(
        asset_id="asset-msft",
        version=3,  # hypothetical future version
        reason="Price adjusted after corporate dividend payment on 2026-01-20",
        change_type="correction",
        impacted_fields=["adjustedClosePrice", "closePrice"]
    )
    
    print(f"  ✅ Story recorded:")
    print(f"     Entity: {result['entityId']}")
    print(f"     Version: {result['version']}")
    print(f"     Reason: {result['reason']}")
    print(f"     Type: {result['changeType']}")


def example_7_ingestion_with_stories():
    """Example 7: Ingest data with change stories."""
    print("\n" + "="*70)
    print("EXAMPLE 7: Ingest with Automatic Change Stories")
    print("="*70)
    
    from dw_warehouse.store import DocumentStore
    
    # Create temporary store for demo
    temp_repo = WarehouseRepository("data/warehouse")
    service = IngestionService(temp_repo.store)
    
    # Example: ingesting with stories attached
    payload = {
        "provider": {
            "dataSourceId": "source-demo",
            "name": "Demo Provider",
            "providerType": "api",
            "apiEndpoint": "https://api.example.com/v1",
        },
        "sources": [],
        "assets": [],
        "series": [],
    }
    
    stories = {
        "asset-example": [
            {
                "version": 1,
                "reason": "Initial onboarding of demo asset",
                "changeType": "creation",
                "impactedFields": []
            }
        ]
    }
    
    print("\n📦 Ingesting payload with stories...")
    result = service.ingest_payload_with_stories(payload, stories)
    
    print(f"  Stories recorded: {result.get('storiesRecorded', 0)}")
    print(f"  Provider: {result['provenance']['provider']}")
    print(f"  Batch ID: {result['provenance']['batchId']}")


def main():
    """Run all examples."""
    print("\n" + "🎯 "*35)
    print(" MARKET-MEMORY LAYER EXAMPLES ".center(70))
    print("🎯 "*35)
    
    try:
        example_1_explore_change_history()
        example_2_human_narrative()
        example_3_compare_versions()
        example_4_query_specific_story()
        example_5_data_source_changes()
        example_6_record_new_story()
        example_7_ingestion_with_stories()
        
        print("\n" + "="*70)
        print("✅ All examples completed successfully!")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
