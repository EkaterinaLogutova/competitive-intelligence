from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class PageState(StrEnum):
    """Observed retrieval state; empty content is distinct from a failed fetch."""

    OK = "ok"
    EMPTY = "empty"
    BLOCKED = "blocked"
    NOT_FOUND = "not_found"
    PARSE_ERROR = "parse_error"


@dataclass(frozen=True, slots=True)
class SourceSpec:
    """A source from the assignment with a provisional taxonomy label."""

    id: str
    url: str
    initial_class: str
    scope: str
    notes: str


@dataclass(frozen=True, slots=True)
class ExtractedItem:
    """Normalized record produced by a future source-specific extractor."""

    source_id: str
    canonical_url: str
    platform_type: str
    page_type: str
    item_type: str | None
    state: PageState
    title: str | None
    body: str | None
    author: str | None
    publisher: str | None
    published_at: str | None
    updated_at: str | None
    collected_at: str
    language: str | None
    confidence: float
    extractor_version: str
    raw_reference: str | None = None
    parent_url: str | None = None
    external_id: str | None = None
    observed_time_text: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

