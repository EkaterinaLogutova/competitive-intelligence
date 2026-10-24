from __future__ import annotations

import csv
import unittest
from pathlib import Path


class ResearchDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        path = (
            Path(__file__).resolve().parents[1]
            / "data"
            / "curated"
            / "source_inventory.csv"
        )
        with path.open(encoding="utf-8", newline="") as source:
            cls.rows = list(csv.DictReader(source))

    def test_inventory_has_six_unique_sources_and_page_types(self) -> None:
        self.assertEqual(6, len(self.rows))
        self.assertEqual(6, len({row["source_id"] for row in self.rows}))
        self.assertEqual(6, len({row["page_type"] for row in self.rows}))

    def test_boolean_features_use_binary_values(self) -> None:
        boolean_fields = [field for field in self.rows[0] if field.startswith("has_")]
        for row in self.rows:
            for field in boolean_fields:
                self.assertIn(row[field], {"0", "1"})

    def test_empty_collection_has_zero_observed_items(self) -> None:
        drive2 = next(
            row for row in self.rows if row["source_id"] == "drive2_featured_topics"
        )
        self.assertEqual("empty", drive2["collection_state"])
        self.assertEqual("0", drive2["items_on_snapshot"])


if __name__ == "__main__":
    unittest.main()
