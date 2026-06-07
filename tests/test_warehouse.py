from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import urlopen

from dw_warehouse.api import build_server
from dw_warehouse.repository import WarehouseRepository


class WarehouseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = WarehouseRepository(Path(self.tempdir.name))
        self.repo.seed_demo()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_temporal_asset_history(self) -> None:
        current = self.repo.get_asset("asset-gm")
        historical = self.repo.get_asset("asset-gm", as_of="2026-01-03T00:00:00Z")
        self.assertEqual(current["data"]["symbol"], "GM")
        self.assertEqual(historical["data"]["symbol"], "GM")
        self.assertEqual(current["state"], "active")

    def test_deleted_asset_is_retired(self) -> None:
        asset = self.repo.get_asset("asset-legacy-oil")
        self.assertTrue(asset["isDeleted"])
        active_assets = self.repo.list_assets()
        asset_ids = {item["assetId"] for item in active_assets}
        self.assertNotIn("asset-legacy-oil", asset_ids)

    def test_series_summary_and_forecast(self) -> None:
        series = self.repo.series("asset-gm", "source-nasdaq")
        self.assertEqual(len(series), 1)
        summary = series[0]["summary"]
        self.assertGreater(summary["count"], 0)
        self.assertIn("nextCloseForecast", summary)

    def test_api_endpoints(self) -> None:
        server = build_server(self.tempdir.name, host="127.0.0.1", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        host, port = server.server_address
        try:
            with urlopen(f"http://{host}:{port}/health") as response:
                payload = json.loads(response.read().decode("utf-8"))
            self.assertEqual(payload["status"], "ok")

            with urlopen(f"http://{host}:{port}/assets") as response:
                payload = json.loads(response.read().decode("utf-8"))
            self.assertGreaterEqual(len(payload["items"]), 2)
        finally:
            server.shutdown()
            server.server_close()

    def test_portfolio_projection(self) -> None:
        portfolio = self.repo.portfolio("portfolio-acme-2026")
        self.assertEqual(portfolio["portfolioId"], "portfolio-acme-2026")
        self.assertGreaterEqual(len(portfolio["assets"]), 3)

    def test_asset_history_view(self) -> None:
        history = self.repo.asset_history("asset-gm")
        self.assertIsNotNone(history)
        self.assertGreaterEqual(len(history["events"]), 3)
        rendered = history["rendered"]
        self.assertIn("TOMBSTONE", self.repo.asset_history("asset-legacy-oil")["rendered"])
        self.assertIn("Source changes", rendered)
        self.assertIn("asset-gm", rendered)

    def test_asset_history_html(self) -> None:
        html = self.repo.asset_history_html("asset-gm")
        self.assertIsNotNone(html)
        self.assertIn("mermaid", html)
        self.assertIn("Asset history: asset-gm", html)

    def test_asset_change_timeline(self) -> None:
        """Test market-memory: asset change timeline with stories."""
        timeline = self.repo.asset_change_timeline("asset-gm")
        self.assertGreaterEqual(len(timeline), 1)
        # First version should be creation
        self.assertEqual(timeline[0]["version"], 1)
        self.assertEqual(timeline[0]["event"], "creation")
        # Check that later versions have events
        if len(timeline) > 1:
            self.assertIn("event", timeline[1])

    def test_asset_change_narrative(self) -> None:
        """Test market-memory: human-readable change narrative."""
        narrative = self.repo.asset_change_narrative("asset-gm")
        self.assertIsNotNone(narrative)
        self.assertIn("asset-gm", narrative)
        self.assertIn("history", narrative.lower())

    def test_asset_change_story_retrieval(self) -> None:
        """Test market-memory: retrieve specific change story."""
        # Asset-gm version 2 has a correction story
        story = self.repo.asset_change_story("asset-gm", 2)
        self.assertIsNotNone(story)
        self.assertEqual(story["changeType"], "correction")
        self.assertIn("Regional classification", story["reason"])
        self.assertEqual(story["impactedFields"], ["region"])

    def test_asset_change_delta(self) -> None:
        """Test market-memory: explain differences between versions."""
        delta = self.repo.asset_change_delta("asset-gm", 1, 2)
        self.assertIsNotNone(delta)
        self.assertEqual(delta["from"]["version"], 1)
        self.assertEqual(delta["to"]["version"], 2)
        self.assertIn("changedFields", delta)
        self.assertIn("stories", delta)

    def test_retired_asset_change_story(self) -> None:
        """Test market-memory: retirement story for deleted asset."""
        story = self.repo.asset_change_story("asset-legacy-oil", 2)
        self.assertIsNotNone(story)
        self.assertEqual(story["changeType"], "retirement")
        self.assertIn("retired", story["reason"].lower())

    def test_source_change_timeline(self) -> None:
        """Test market-memory: data source change timeline."""
        timeline = self.repo.source_change_timeline("source-nasdaq")
        self.assertGreaterEqual(len(timeline), 1)
        # Should have creation and potentially an upgrade
        if len(timeline) > 1:
            self.assertEqual(timeline[0]["event"], "creation")

    def test_source_change_story(self) -> None:
        """Test market-memory: data source change story."""
        # source-nasdaq version 2 has an API endpoint upgrade
        timeline = self.repo.source_change_timeline("source-nasdaq")
        if len(timeline) > 1:
            v2 = timeline[1]
            self.assertIn("story", v2)
            self.assertEqual(v2["story"]["changeType"], "source_switch")
            self.assertIn("API endpoint", v2["story"]["reason"])

    def test_market_memory_narrative_for_deleted_asset(self) -> None:
        """Test market-memory: narrative for asset with tombstone."""
        narrative = self.repo.asset_change_narrative("asset-legacy-oil")
        self.assertIsNotNone(narrative)
        self.assertIn("asset-legacy-oil", narrative)
        # Should mention the retirement event
        self.assertTrue(
            "RETIREMENT" in narrative or "retirement" in narrative or "TOMBSTONE" in narrative,
            f"Narrative should mention retirement: {narrative}"
        )


if __name__ == "__main__":
    unittest.main()
