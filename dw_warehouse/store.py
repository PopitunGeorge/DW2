from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(value: datetime | str | None) -> str:
    if value is None:
        value = now_utc()
    if isinstance(value, str):
        return value.replace("+00:00", "Z") if value.endswith("Z") else value
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_iso(value: datetime | str | None) -> datetime:
    if value is None:
        return now_utc()
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_json(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


@dataclass(slots=True)
class DocumentStore:
    base_dir: Path

    def __post_init__(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _current_time(self) -> str:
        """Get current UTC time in ISO format."""
        return to_iso(now_utc())

    def collection_path(self, collection: str) -> Path:
        return self.base_dir / f"{collection}.jsonl"

    def _read_lines(self, collection: str) -> list[dict[str, Any]]:
        path = self.collection_path(collection)
        if not path.exists():
            return []
        items: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    items.append(json.loads(line))
        return items

    def append(self, collection: str, document: dict[str, Any]) -> dict[str, Any]:
        path = self.collection_path(collection)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(document, sort_keys=True, ensure_ascii=False))
            handle.write("\n")
        return document

    def read_all(self, collection: str) -> list[dict[str, Any]]:
        return self._read_lines(collection)

    def history(self, collection: str, entity_id: str) -> list[dict[str, Any]]:
        records = [record for record in self.read_all(collection) if record["entity_id"] == entity_id]
        records.sort(key=lambda record: (record["version"], record["created_at"]))
        return records

    def latest_record(
        self,
        collection: str,
        entity_id: str,
        as_of: datetime | str | None = None,
    ) -> dict[str, Any] | None:
        target_time = parse_iso(as_of)
        records = [
            record
            for record in self.read_all(collection)
            if record["entity_id"] == entity_id and parse_iso(record["valid_from"]) <= target_time
        ]
        if not records:
            return None
        records.sort(key=lambda record: (parse_iso(record["valid_from"]), record["version"], record["created_at"]))
        return records[-1]

    def latest_per_entity(
        self,
        collection: str,
        as_of: datetime | str | None = None,
        predicate: Callable[[dict[str, Any]], bool] | None = None,
    ) -> list[dict[str, Any]]:
        target_time = parse_iso(as_of)
        latest: dict[str, dict[str, Any]] = {}
        for record in self.read_all(collection):
            if parse_iso(record["valid_from"]) > target_time:
                continue
            if predicate is not None and not predicate(record):
                continue
            entity_id = record["entity_id"]
            current = latest.get(entity_id)
            if current is None:
                latest[entity_id] = record
                continue
            current_key = (parse_iso(current["valid_from"]), current["version"], current["created_at"])
            next_key = (parse_iso(record["valid_from"]), record["version"], record["created_at"])
            if next_key > current_key:
                latest[entity_id] = record
        return sorted(latest.values(), key=lambda record: record["entity_id"])

    def append_version(
        self,
        collection: str,
        entity_type: str,
        entity_id: str,
        data: dict[str, Any],
        provenance: dict[str, Any],
        valid_from: datetime | str | None = None,
        is_deleted: bool = False,
    ) -> dict[str, Any]:
        history = self.history(collection, entity_id)
        next_version = 1 if not history else history[-1]["version"] + 1
        created_at = to_iso(now_utc())
        valid_from_iso = to_iso(valid_from)
        prev_hash = history[-1]["record_hash"] if history else None
        document = {
            "collection": collection,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "version": next_version,
            "valid_from": valid_from_iso,
            "is_deleted": is_deleted,
            "data": data,
            "provenance": provenance,
            "created_at": created_at,
            "prev_hash": prev_hash,
        }
        document["record_hash"] = sha256_json(document)
        return self.append(collection, document)
