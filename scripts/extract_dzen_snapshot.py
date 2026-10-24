from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from competitive_intelligence.dzen import load_page_state, public_news_cards


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract public news-card metadata from a saved Dzen rubric page."
    )
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    cards = public_news_cards(load_page_state(args.snapshot))
    output = json.dumps(cards, ensure_ascii=False, indent=2)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
