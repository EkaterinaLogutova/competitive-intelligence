from __future__ import annotations

import json
import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from competitive_intelligence.models import ExtractedItem, PageState


MARKER = "window.Ya.Neo="
EXTRACTOR_VERSION = "dzen-saved-page/1"
DZEN_RUBRIC_URL = "https://dzen.ru/news/rubric/computers"
MOSCOW_TIMEZONE = timezone(timedelta(hours=3))

PUBLIC_FIELDS = (
    "title",
    "titleUrl",
    "url",
    "annotation",
    "text",
    "source",
    "sourceName",
    "sourceUrl",
    "publicationTime",
    "publishedAt",
    "datetime",
    "date",
    "time",
    "timestamp",
    "storyId",
    "id",
)

RUSSIAN_MONTHS = {
    "января": 1,
    "февраля": 2,
    "марта": 3,
    "апреля": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "августа": 8,
    "сентября": 9,
    "октября": 10,
    "ноября": 11,
    "декабря": 12,
}


def load_page_state(path: Path) -> Mapping[str, Any]:
    """Read the embedded Dzen server state from a browser-saved HTML page."""

    html = path.read_text(encoding="utf-8")
    assignment_marker = MARKER + "{"
    marker_index = html.find(assignment_marker)
    if marker_index < 0:
        raise ValueError(f"{assignment_marker!r} was not found in the saved page")

    payload_start = marker_index + len(MARKER)
    payload, _ = json.JSONDecoder().raw_decode(html[payload_start:].lstrip())
    if not isinstance(payload, dict):
        raise ValueError("Dzen page state must be a JSON object")
    return payload


def walk(value: Any) -> Iterator[Mapping[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def public_news_cards(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return unique public card fields without copying account/session state."""

    cards: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for candidate in walk(state):
        title = candidate.get("title")
        title_url = candidate.get("titleUrl")
        if not isinstance(title, str) or not isinstance(title_url, str):
            continue
        if not title.strip() or not title_url.startswith(("http://", "https://")):
            continue

        key = (title.strip(), title_url)
        if key in seen:
            continue
        seen.add(key)

        public = {
            field: candidate[field]
            for field in PUBLIC_FIELDS
            if field in candidate
            and isinstance(candidate[field], (str, int, float, bool, type(None)))
        }
        public["available_fields"] = sorted(candidate.keys())
        cards.append(public)

    return cards


def collected_at_from_state(state: Mapping[str, Any]) -> datetime:
    try:
        timestamp_ms = state["dataSource"]["neo"]["timestamp"]
    except (KeyError, TypeError) as exc:
        raise ValueError("Dzen page state has no collection timestamp") from exc

    if not isinstance(timestamp_ms, (int, float)):
        raise ValueError("Dzen collection timestamp must be numeric")
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).astimezone(
        MOSCOW_TIMEZONE
    )


def normalize_display_time(
    display_time: str | None, collected_at: datetime
) -> tuple[str | None, bool]:
    """Normalize Dzen's Russian display time and flag approximate relative values."""

    if not display_time:
        return None, False

    value = " ".join(display_time.replace("\u00a0", " ").split()).lower()
    clock_pattern = r"(\d{1,2}):(\d{2})"

    match = re.fullmatch(rf"сегодня в {clock_pattern}", value)
    if match:
        hour, minute = map(int, match.groups())
        return collected_at.replace(hour=hour, minute=minute, second=0).isoformat(), False

    match = re.fullmatch(rf"вчера в {clock_pattern}", value)
    if match:
        hour, minute = map(int, match.groups())
        day = collected_at - timedelta(days=1)
        return day.replace(hour=hour, minute=minute, second=0).isoformat(), False

    match = re.fullmatch(
        r"(\d+) (минута|минуты|минут|час|часа|часов) назад", value
    )
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        delta = timedelta(minutes=amount) if unit.startswith("минут") else timedelta(hours=amount)
        return (collected_at - delta).replace(second=0, microsecond=0).isoformat(), True

    months = "|".join(RUSSIAN_MONTHS)
    match = re.fullmatch(rf"(\d{{1,2}}) ({months}) в {clock_pattern}", value)
    if match:
        day, month_name, hour, minute = match.groups()
        published = datetime(
            collected_at.year,
            RUSSIAN_MONTHS[month_name],
            int(day),
            int(hour),
            int(minute),
            tzinfo=collected_at.tzinfo,
        )
        if published > collected_at + timedelta(days=1):
            published = published.replace(year=published.year - 1)
        return published.isoformat(), False

    return None, False


def normalize_card(card: Mapping[str, Any], collected_at: datetime) -> ExtractedItem:
    title_url = str(card["titleUrl"])
    display_time = card.get("time")
    observed_time = display_time if isinstance(display_time, str) else None
    published_at, approximate = normalize_display_time(observed_time, collected_at)
    publisher = card.get("source")
    annotation = card.get("annotation")
    story_url = card.get("url")

    return ExtractedItem(
        source_id="dzen_computers_news",
        canonical_url=title_url,
        platform_type="news_platform",
        page_type="news_aggregator_rubric",
        item_type="news_card",
        state=PageState.OK,
        title=str(card["title"]).strip(),
        body=annotation.strip() if isinstance(annotation, str) else None,
        author=None,
        publisher=publisher.strip() if isinstance(publisher, str) else None,
        published_at=published_at,
        updated_at=None,
        collected_at=collected_at.isoformat(),
        language="ru",
        confidence=1.0,
        extractor_version=EXTRACTOR_VERSION,
        raw_reference=story_url if isinstance(story_url, str) else None,
        parent_url=DZEN_RUBRIC_URL,
        external_id=str(card["id"]) if card.get("id") is not None else None,
        observed_time_text=observed_time,
        metadata={"published_at_is_approximate": approximate},
    )


def extract_records(path: Path) -> list[ExtractedItem]:
    state = load_page_state(path)
    collected_at = collected_at_from_state(state)
    return [normalize_card(card, collected_at) for card in public_news_cards(state)]


def record_as_dict(record: ExtractedItem) -> dict[str, Any]:
    payload = asdict(record)
    payload["state"] = record.state.value
    return payload


def write_jsonl(records: Sequence[ExtractedItem], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as output:
        for record in records:
            output.write(json.dumps(record_as_dict(record), ensure_ascii=False) + "\n")
