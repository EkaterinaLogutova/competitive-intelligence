from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from competitive_intelligence.cli import main
from competitive_intelligence.dzen import (
    collected_at_from_state,
    extract_records,
    normalize_display_time,
    public_news_cards,
)


COLLECTED_AT = datetime(2026, 10, 24, 10, 52, 8, tzinfo=timezone(timedelta(hours=3)))


def saved_page(cards: list[dict[str, object]]) -> str:
    state = {
        "dataSource": {"neo": {"timestamp": 1792828328000}},
        "news": {"rubric": {"items": cards}},
    }
    return (
        "<!doctype html><script>"
        "window.Ya.Neo=window.Ya.Neo||{};"
        f"window.Ya.Neo={json.dumps(state, ensure_ascii=False)};"
        "</script>"
    )


class DzenExtractionTests(unittest.TestCase):
    def test_public_cards_are_deduplicated_and_account_data_is_ignored(self) -> None:
        card = {
            "id": 7,
            "title": "Новость",
            "titleUrl": "https://media.example/news/7",
            "url": "https://dzen.ru/news/story/7",
            "source": "Издание",
            "annotation": "Краткое описание.",
            "time": "Вчера в 21:48",
        }
        state = {
            "user": {"name": "Private User", "avatar": "private"},
            "items": [card, card],
        }

        cards = public_news_cards(state)

        self.assertEqual(1, len(cards))
        serialized = json.dumps(cards, ensure_ascii=False)
        self.assertNotIn("Private User", serialized)
        self.assertNotIn("avatar", serialized)

    def test_display_times_are_normalized_against_collection_time(self) -> None:
        self.assertEqual(
            ("2026-10-23T21:48:00+03:00", False),
            normalize_display_time("Вчера в 21:48", COLLECTED_AT),
        )
        self.assertEqual(
            ("2026-10-24T08:52:00+03:00", True),
            normalize_display_time("2 часа назад", COLLECTED_AT),
        )
        self.assertEqual(
            ("2026-10-22T15:37:00+03:00", False),
            normalize_display_time("22 октября в 15:37", COLLECTED_AT),
        )

    def test_snapshot_is_normalized_to_jsonl_through_cli(self) -> None:
        cards = [
            {
                "id": 7,
                "title": "Новость",
                "titleUrl": "https://media.example/news/7",
                "url": "https://dzen.ru/news/story/7",
                "source": "Издание",
                "annotation": "Краткое описание.",
                "time": "Вчера в 21:48",
            }
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot = Path(temp_dir) / "snapshot.html"
            output = Path(temp_dir) / "records.jsonl"
            snapshot.write_text(saved_page(cards), encoding="utf-8")

            exit_code = main(["extract-dzen", str(snapshot), "--output", str(output)])
            record = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(0, exit_code)
        self.assertEqual("news_aggregator_rubric", record["page_type"])
        self.assertEqual("Издание", record["publisher"])
        self.assertEqual("2026-10-23T21:48:00+03:00", record["published_at"])
        self.assertEqual("ok", record["state"])

    def test_real_sanitized_snapshot_matches_raw_snapshot_contract(self) -> None:
        evidence_path = (
            Path(__file__).resolve().parents[1]
            / "docs"
            / "dzen-news-snapshot-2026-10-24.json"
        )
        cards = json.loads(evidence_path.read_text(encoding="utf-8"))
        state = {"dataSource": {"neo": {"timestamp": 1792828328000}}}

        self.assertEqual(COLLECTED_AT, collected_at_from_state(state))
        self.assertEqual(29, len(cards))

        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot = Path(temp_dir) / "snapshot.html"
            snapshot.write_text(saved_page(cards), encoding="utf-8")
            records = extract_records(snapshot)

        self.assertEqual(29, len(records))
        self.assertEqual(29, len({record.canonical_url for record in records}))
        self.assertTrue(all(record.publisher for record in records))


if __name__ == "__main__":
    unittest.main()
