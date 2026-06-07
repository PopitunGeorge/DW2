from __future__ import annotations

from typing import Any


def _diff_fields(previous: dict[str, Any] | None, current: dict[str, Any]) -> list[str]:
    if previous is None:
        return ["created"]
    changed = []
    for key in sorted(set(previous) | set(current)):
        if previous.get(key) != current.get(key):
            changed.append(key)
    return changed or ["no material change"]


def build_asset_history_view(
    asset_id: str,
    asset_records: list[dict[str, Any]],
    series_records: list[dict[str, Any]],
    source_records: list[dict[str, Any]],
) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    previous_asset_data: dict[str, Any] | None = None

    for record in asset_records:
        data = record["data"]
        events.append(
            {
                "kind": "asset-version",
                "label": "Asset version",
                "version": record["version"],
                "validFrom": record["valid_from"],
                "isDeleted": record["is_deleted"],
                "summary": data.get("description") or data.get("name") or asset_id,
                "changes": _diff_fields(previous_asset_data, data),
                "provenance": record["provenance"],
                "recordHash": record["record_hash"],
            }
        )
        previous_asset_data = data

    for record in series_records:
        data = record["data"]
        events.append(
            {
                "kind": "series-binding",
                "label": f"Series via {data['dataSourceId']}",
                "version": record["version"],
                "validFrom": record["valid_from"],
                "isDeleted": record["is_deleted"],
                "summary": f"frequency={data.get('frequency', 'unknown')}",
                "changes": _diff_fields(None, data),
                "provenance": record["provenance"],
                "recordHash": record["record_hash"],
            }
        )

    for record in source_records:
        data = record["data"]
        events.append(
            {
                "kind": "source-version",
                "label": f"Source {data['dataSourceId']}",
                "version": record["version"],
                "validFrom": record["valid_from"],
                "isDeleted": record["is_deleted"],
                "summary": data.get("apiEndpoint", data.get("name", "source")),
                "changes": _diff_fields(None, data),
                "provenance": record["provenance"],
                "recordHash": record["record_hash"],
            }
        )

    events.sort(key=lambda event: (event["validFrom"], event["kind"], event["version"]))

    return {
        "assetId": asset_id,
        "events": events,
        "tombstones": [event for event in events if event["isDeleted"]],
        "sourceIds": sorted({record["data"]["dataSourceId"] for record in source_records}),
    }


def render_asset_history_timeline(history: dict[str, Any]) -> str:
    lines = [f"Asset timeline for {history['assetId']}", ""]
    for event in history["events"]:
        marker = "TOMBSTONE" if event["isDeleted"] else "VERSION"
        lines.append(
            f"{event['validFrom']} | {marker:<10} | {event['kind']:<15} | v{event['version']} | {event['summary']}"
        )
        if event["changes"]:
            lines.append(f"    changes: {', '.join(event['changes'])}")
    if history["tombstones"]:
        lines.append("")
        lines.append("Tombstones")
        for tombstone in history["tombstones"]:
            lines.append(f"- {tombstone['validFrom']} -> v{tombstone['version']} ({tombstone['label']})")
    if history["sourceIds"]:
        lines.append("")
        lines.append("Source changes")
        lines.append(f"- linked sources: {', '.join(history['sourceIds'])}")
    return "\n".join(lines)


def render_asset_history_html(history: dict[str, Any]) -> str:
        events_html = []
        mermaid_nodes = ["graph LR"]
        previous_node = "start"
        mermaid_nodes.append('    start([asset start])')
        for index, event in enumerate(history["events"], start=1):
                node_id = f"n{index}"
                label = (
                        f"{event['kind']} v{event['version']}\\n{event['validFrom']}"
                        if not event["isDeleted"]
                        else f"TOMBSTONE v{event['version']}\\n{event['validFrom']}"
                )
                mermaid_nodes.append(f"    {node_id}[\"{label}\"]")
                mermaid_nodes.append(f"    {previous_node} --> {node_id}")
                previous_node = node_id
                events_html.append(
                        f"""
                        <article class=\"event {('deleted' if event['isDeleted'] else 'live')}\">
                            <div class=\"event-meta\">{event['kind']} · v{event['version']} · {event['validFrom']}</div>
                            <h3>{event['label']}</h3>
                            <p>{event['summary']}</p>
                            <p class=\"event-changes\">Changes: {', '.join(event['changes'])}</p>
                            <p class=\"event-hash\">Hash: {event['recordHash']}</p>
                        </article>
                        """
                )

        source_badges = "".join(f"<span class=\"badge\">{source_id}</span>" for source_id in history["sourceIds"])
        tombstones = "".join(
                f"<li>{event['validFrom']} · v{event['version']} · {event['label']}</li>" for event in history["tombstones"]
        ) or "<li>None</li>"
        mermaid_graph = "\n".join(mermaid_nodes)
        return f"""<!doctype html>
<html lang=\"en\">
<head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Asset history — {history['assetId']}</title>
    <script src=\"https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js\"></script>
    <script>mermaid.initialize({{ startOnLoad: true, theme: 'neutral' }});</script>
    <style>
        :root {{ color-scheme: light; }}
        body {{ font-family: Arial, sans-serif; margin: 0; background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%); color: #1f2937; }}
        .wrap {{ max-width: 1100px; margin: 0 auto; padding: 32px 20px 60px; }}
        .hero {{ background: white; border: 1px solid #dbe4ff; border-radius: 20px; padding: 24px; box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08); }}
        .hero h1 {{ margin: 0 0 8px; font-size: 2rem; }}
        .muted {{ color: #64748b; }}
        .badges {{ display: flex; gap: 8px; flex-wrap: wrap; margin: 14px 0 0; }}
        .badge {{ padding: 6px 10px; border-radius: 999px; background: #e0e7ff; color: #3730a3; font-size: 0.85rem; }}
        .grid {{ display: grid; grid-template-columns: 1.2fr 1fr; gap: 20px; margin-top: 20px; }}
        .panel {{ background: white; border-radius: 18px; border: 1px solid #e2e8f0; padding: 18px; }}
        .timeline {{ display: grid; gap: 14px; margin-top: 20px; }}
        .event {{ border-left: 6px solid #6366f1; padding: 14px 16px; border-radius: 14px; background: #f8fafc; }}
        .event.deleted {{ border-left-color: #ef4444; background: #fff1f2; }}
        .event-meta {{ font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.08em; color: #64748b; }}
        .event h3 {{ margin: 6px 0 8px; }}
        .event-changes, .event-hash {{ font-size: 0.92rem; color: #475569; }}
        .section-title {{ margin: 0 0 10px; font-size: 1.1rem; }}
        .mermaid {{ background: #fff; padding: 10px; border-radius: 14px; overflow-x: auto; }}
        .history-list {{ margin: 0; padding-left: 20px; }}
        @media (max-width: 900px) {{ .grid {{ grid-template-columns: 1fr; }} }}
    </style>
</head>
<body>
    <div class=\"wrap\">
        <section class=\"hero\">
            <h1>Asset history: {history['assetId']}</h1>
            <p class=\"muted\">Append-only timeline with version changes, linked source updates, and tombstones.</p>
            <div class=\"badges\">{source_badges or '<span class="badge">No linked sources</span>'}</div>
        </section>

        <div class=\"grid\">
            <section class=\"panel\">
                <h2 class=\"section-title\">Timeline</h2>
                <div class=\"timeline\">{''.join(events_html)}</div>
            </section>

            <section class=\"panel\">
                <h2 class=\"section-title\">Diagram</h2>
                <div class=\"mermaid\">{mermaid_graph}</div>
                <h2 class=\"section-title\" style=\"margin-top:18px;\">Tombstones</h2>
                <ul class=\"history-list\">{tombstones}</ul>
            </section>
        </div>
    </div>
</body>
</html>"""
