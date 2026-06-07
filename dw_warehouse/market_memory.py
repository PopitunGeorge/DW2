from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .store import DocumentStore, parse_iso


@dataclass(slots=True)
class ChangeStory:
    """A change story records why an asset version changed."""

    entity_id: str
    version: int
    timestamp: str
    reason: str
    change_type: str  # "value_change", "metadata_update", "source_switch", "correction", "retirement", etc.
    previous_value: Any | None = None
    new_value: Any | None = None
    impacted_fields: list[str] | None = None


class MarketMemory:
    """Market-memory layer: tracks the 'story' of why assets changed.
    
    Instead of just recording value changes, we track the narrative reasons:
    - "price jumped after source switch"
    - "vendor corrected prior close"
    - "asset retired after tombstone"
    - etc.
    """

    def __init__(self, store: DocumentStore):
        self.store = store

    def record_change_story(
        self,
        collection: str,
        entity_id: str,
        version: int,
        reason: str,
        change_type: str,
        previous_value: Any | None = None,
        new_value: Any | None = None,
        impacted_fields: list[str] | None = None,
    ) -> ChangeStory:
        """Record a change story for an entity version.
        
        Args:
            collection: The collection name (e.g., "instruments", "points")
            entity_id: The entity identifier
            version: The version number
            reason: Human-readable reason for the change
            change_type: Categorical reason (source_switch, correction, retirement, etc.)
            previous_value: The previous value(s) for comparison
            new_value: The new value(s)
            impacted_fields: List of field names that changed
        
        Returns:
            ChangeStory object
        """
        story = ChangeStory(
            entity_id=entity_id,
            version=version,
            timestamp=self.store._current_time(),
            reason=reason,
            change_type=change_type,
            previous_value=previous_value,
            new_value=new_value,
            impacted_fields=impacted_fields or [],
        )
        
        # Store the story as metadata in a "stories" collection
        story_doc = {
            "collection": collection,
            "entity_id": entity_id,
            "version": version,
            "reason": reason,
            "change_type": change_type,
            "previous_value": previous_value,
            "new_value": new_value,
            "impacted_fields": impacted_fields or [],
            "recorded_at": story.timestamp,
        }
        
        self.store.append("stories", story_doc)
        return story

    def get_change_story(self, collection: str, entity_id: str, version: int) -> ChangeStory | None:
        """Retrieve the change story for a specific version."""
        stories = self.store.read_all("stories")
        for story_doc in stories:
            if (story_doc["collection"] == collection 
                and story_doc["entity_id"] == entity_id 
                and story_doc["version"] == version):
                return ChangeStory(
                    entity_id=story_doc["entity_id"],
                    version=story_doc["version"],
                    timestamp=story_doc["recorded_at"],
                    reason=story_doc["reason"],
                    change_type=story_doc["change_type"],
                    previous_value=story_doc.get("previous_value"),
                    new_value=story_doc.get("new_value"),
                    impacted_fields=story_doc.get("impacted_fields"),
                )
        return None

    def get_entity_timeline(self, collection: str, entity_id: str) -> list[dict[str, Any]]:
        """Get the full timeline of changes for an entity with stories.
        
        Returns a list of versions with their change stories and context.
        """
        records = self.store.history(collection, entity_id)
        stories_by_version = {}
        
        all_stories = self.store.read_all("stories")
        for story_doc in all_stories:
            if story_doc["collection"] == collection and story_doc["entity_id"] == entity_id:
                stories_by_version[story_doc["version"]] = story_doc
        
        timeline = []
        for i, record in enumerate(records):
            version = record["version"]
            story = stories_by_version.get(version)
            
            entry = {
                "version": version,
                "validFrom": record["valid_from"],
                "isDeleted": record["is_deleted"],
                "data": record["data"],
                "provenance": record["provenance"],
                "recordHash": record["record_hash"],
                "prevHash": record["prev_hash"],
            }
            
            if story:
                entry["story"] = {
                    "reason": story["reason"],
                    "changeType": story["change_type"],
                    "impactedFields": story.get("impacted_fields", []),
                    "previousValue": story.get("previous_value"),
                    "newValue": story.get("new_value"),
                    "recordedAt": story["recorded_at"],
                }
            
            # Add contextual info about the change
            if i > 0:
                prev_record = records[i - 1]
                if prev_record["data"] != record["data"]:
                    entry["hasDataChange"] = True
                    # Auto-detect field changes
                    changed_fields = [
                        key for key in record["data"]
                        if prev_record["data"].get(key) != record["data"].get(key)
                    ]
                    entry["detectedChangedFields"] = changed_fields
            
            if record["is_deleted"]:
                entry["event"] = "retirement"
            elif i == 0:
                entry["event"] = "creation"
            elif story:
                entry["event"] = story["change_type"]
            else:
                entry["event"] = "update"
            
            timeline.append(entry)
        
        return timeline

    def build_change_narrative(self, collection: str, entity_id: str) -> str:
        """Build a human-readable narrative of all changes."""
        timeline = self.get_entity_timeline(collection, entity_id)
        
        if not timeline:
            return f"No history found for {entity_id}."
        
        lines = [f"Change history for {entity_id}:"]
        
        for entry in timeline:
            version = entry["version"]
            valid_from = entry["validFrom"]
            event = entry.get("event", "update").upper()
            
            line = f"  v{version} @ {valid_from}: {event}"
            
            if "story" in entry:
                story = entry["story"]
                line += f" — {story['reason']}"
                if story.get("impactedFields"):
                    line += f" (affected: {', '.join(story['impactedFields'])})"
            elif "detectedChangedFields" in entry:
                changed = entry["detectedChangedFields"]
                line += f" (detected changes: {', '.join(changed)})"
            
            lines.append(line)
        
        return "\n".join(lines)

    def explain_version_delta(
        self,
        collection: str,
        entity_id: str,
        from_version: int,
        to_version: int,
    ) -> dict[str, Any]:
        """Explain what changed between two versions with stories."""
        records = self.store.history(collection, entity_id)
        records_by_version = {r["version"]: r for r in records}
        
        from_record = records_by_version.get(from_version)
        to_record = records_by_version.get(to_version)
        
        if not from_record or not to_record:
            return {"error": "One or both versions not found"}
        
        from_data = from_record["data"]
        to_data = to_record["data"]
        
        # Detect field-level changes
        added_fields = set(to_data.keys()) - set(from_data.keys())
        removed_fields = set(from_data.keys()) - set(to_data.keys())
        changed_fields = {
            key: {"from": from_data[key], "to": to_data[key]}
            for key in set(from_data.keys()) & set(to_data.keys())
            if from_data[key] != to_data[key]
        }
        
        # Look up stories for this version range
        stories = []
        all_stories = self.store.read_all("stories")
        for story_doc in all_stories:
            if (story_doc["collection"] == collection 
                and story_doc["entity_id"] == entity_id 
                and from_version < story_doc["version"] <= to_version):
                stories.append(story_doc)
        
        stories.sort(key=lambda s: s["version"])
        
        return {
            "from": {"version": from_version, "validFrom": from_record["valid_from"]},
            "to": {"version": to_version, "validFrom": to_record["valid_from"]},
            "addedFields": list(added_fields),
            "removedFields": list(removed_fields),
            "changedFields": changed_fields,
            "storyCount": len(stories),
            "stories": stories,
        }
