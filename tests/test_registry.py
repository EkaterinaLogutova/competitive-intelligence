from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from competitive_intelligence.models import ExtractedItem, PageState
from competitive_intelligence.registry import RegistryError, load_sources


class RegistryTests(unittest.TestCase):
    def test_assignment_registry_contains_six_unique_sources(self) -> None:
        sources = load_sources()

        self.assertEqual(6, len(sources))
        self.assertEqual(6, len({source.id for source in sources}))
        self.assertEqual(6, len({source.url for source in sources}))

    def test_duplicate_url_is_rejected(self) -> None:
        source = {
            "id": "first",
            "url": "https://example.com/item",
            "initial_class": "example",
            "scope": "single_item",
            "notes": "test",
        }
        duplicate = {**source, "id": "second"}

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sources.json"
            path.write_text(
                json.dumps({"schema_version": 1, "sources": [source, duplicate]}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RegistryError, "duplicate source URL"):
                load_sources(path)


class ModelTests(unittest.TestCase):
    def test_empty_page_is_a_valid_observation(self) -> None:
        record = ExtractedItem(
            source_id="drive2_featured_topics",
            canonical_url="https://www.drive2.ru/featured-topics/CVQ0gEAAcHQ/",
            platform_type="automotive_social_network",
            page_type="topic_collection",
            item_type=None,
            state=PageState.EMPTY,
            title="Безопасность",
            body=None,
            author=None,
            publisher="DRIVE2",
            published_at=None,
            updated_at=None,
            collected_at="2026-10-24T00:00:00+03:00",
            language="ru",
            confidence=1.0,
            extractor_version="manual-audit/1",
        )

        self.assertEqual(PageState.EMPTY, record.state)
        self.assertIsNone(record.body)

    def test_confidence_outside_unit_interval_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "confidence"):
            ExtractedItem(
                source_id="example",
                canonical_url="https://example.com",
                platform_type="example",
                page_type="example",
                item_type=None,
                state=PageState.OK,
                title=None,
                body=None,
                author=None,
                publisher=None,
                published_at=None,
                updated_at=None,
                collected_at="2026-10-24T00:00:00+03:00",
                language=None,
                confidence=1.1,
                extractor_version="test/1",
            )


class EvidenceTests(unittest.TestCase):
    def test_sanitized_dzen_snapshot_contains_public_cards_only(self) -> None:
        path = (
            Path(__file__).resolve().parents[1]
            / "docs"
            / "dzen-news-snapshot-2026-10-24.json"
        )
        cards = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(29, len(cards))
        self.assertEqual(29, len({card["titleUrl"] for card in cards}))
        for card in cards:
            self.assertTrue(
                {"title", "titleUrl", "url", "annotation", "source", "time", "id"}
                <= card.keys()
            )
            self.assertTrue(card["titleUrl"].startswith(("http://", "https://")))

        serialized = json.dumps(cards, ensure_ascii=False)
        for private_marker in ("strongestId", "externalUid", "passportLinks", "avatar"):
            self.assertNotIn(private_marker, serialized)


if __name__ == "__main__":
    unittest.main()

