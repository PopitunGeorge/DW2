#!/usr/bin/env python3
"""
MongoDB Integration Examples
============================
Demonstrates how to sync the warehouse to MongoDB and query from the cloud.
"""

from pathlib import Path
from dw_warehouse.repository import WarehouseRepository


def example_1_basic_sync():
    """Example 1: Basic MongoDB sync."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic MongoDB Sync")
    print("="*70)
    
    repo = WarehouseRepository("data/warehouse")
    
    # Connect to MongoDB (uses MONGODB_URI from .env)
    print("\n🔗 Connecting to MongoDB...")
    result = repo.connect_mongodb()
    print(f"   Status: {result['status']}")
    print(f"   Database: {result['database']}")
    
    if result['status'] != 'connected':
        print(f"   ❌ Connection failed: {result.get('message', 'Unknown error')}")
        return
    
    # Setup indexes for performance
    print("\n📊 Setting up indexes...")
    indexes = repo.mongodb_setup_indexes()
    print(f"   ✅ Created indexes on {len(indexes)} collections")
    
    # Sync all collections
    print("\n📤 Syncing all collections to MongoDB...")
    sync_result = repo.mongodb_sync_all()
    
    for collection_name, summary in sync_result['collections'].items():
        if 'error' in summary:
            print(f"   ❌ {collection_name}: {summary['error']}")
        else:
            print(f"   ✅ {collection_name}:")
            print(f"      - Inserted: {summary['inserted']}")
            print(f"      - Updated: {summary['updated']}")
            print(f"      - Total: {summary['total']}")
    
    # Cleanup
    repo.mongodb_disconnect()
    print("\n✅ MongoDB sync complete!")


def example_2_query_from_mongodb():
    """Example 2: Query data from MongoDB."""
    print("\n" + "="*70)
    print("EXAMPLE 2: Query from MongoDB")
    print("="*70)
    
    repo = WarehouseRepository("data/warehouse")
    
    # Connect
    print("\n🔗 Connecting to MongoDB...")
    result = repo.connect_mongodb()
    
    if result['status'] != 'connected':
        print(f"❌ Failed to connect: {result['message']}")
        return
    
    # Query entity history from MongoDB
    print("\n🔍 Querying asset-gm history from MongoDB...")
    history = repo.mongodb_query_entity_history("instruments", "asset-gm")
    
    if not history:
        print("   No data found for asset-gm")
    else:
        print(f"   Found {len(history)} versions:")
        for record in history:
            print(f"\n   Version {record['version']} @ {record['valid_from']}")
            print(f"   Data: {record['data']}")
    
    # Query another entity
    print("\n🔍 Querying source-nasdaq history from MongoDB...")
    sources = repo.mongodb_query_entity_history("sources", "source-nasdaq")
    print(f"   Found {len(sources)} versions")
    
    # Cleanup
    repo.mongodb_disconnect()


def example_3_sync_specific_collection():
    """Example 3: Sync a specific collection."""
    print("\n" + "="*70)
    print("EXAMPLE 3: Sync Specific Collection")
    print("="*70)
    
    repo = WarehouseRepository("data/warehouse")
    
    # Connect
    result = repo.connect_mongodb()
    if result['status'] != 'connected':
        print(f"❌ Connection failed")
        return
    
    # Sync just the instruments collection
    print("\n📤 Syncing instruments collection...")
    result = repo.mongodb_sync_collection("instruments")
    print(f"   Inserted: {result['inserted']}")
    print(f"   Updated: {result['updated']}")
    print(f"   Total: {result['total']}")
    
    # Sync another collection
    print("\n📤 Syncing sources collection...")
    result = repo.mongodb_sync_collection("sources")
    print(f"   Inserted: {result['inserted']}")
    print(f"   Updated: {result['updated']}")
    
    repo.mongodb_disconnect()


def example_4_check_status():
    """Example 4: Check MongoDB status and statistics."""
    print("\n" + "="*70)
    print("EXAMPLE 4: MongoDB Status & Statistics")
    print("="*70)
    
    repo = WarehouseRepository("data/warehouse")
    
    # Connect
    result = repo.connect_mongodb()
    if result['status'] != 'connected':
        print(f"❌ Connection failed")
        return
    
    # Get status before sync
    print("\n📊 Status after connection (before sync):")
    status = repo.mongodb_status()
    print(f"   Database: {status['database']}")
    print(f"   Collections:")
    for collection_name, info in status['stats'].get('collections', {}).items():
        print(f"      - {collection_name}: {info.get('document_count', 0)} documents")
    
    # Sync data
    print("\n📤 Syncing all data...")
    repo.mongodb_sync_all()
    
    # Get status after sync
    print("\n📊 Status after sync:")
    status = repo.mongodb_status()
    print(f"   Collections:")
    for collection_name, info in status['stats'].get('collections', {}).items():
        print(f"      - {collection_name}: {info.get('document_count', 0)} documents")
    
    repo.mongodb_disconnect()


def main():
    """Run all examples."""
    print("\n" + "🚀 "*35)
    print(" MONGODB INTEGRATION EXAMPLES ".center(70))
    print("🚀 "*35)
    
    try:
        example_1_basic_sync()
        example_2_query_from_mongodb()
        example_3_sync_specific_collection()
        example_4_check_status()
        
        print("\n" + "="*70)
        print("✅ All examples completed successfully!")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
