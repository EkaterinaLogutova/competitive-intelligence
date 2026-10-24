from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

from competitive_intelligence.models import SourceSpec


SOURCE_ID = re.compile(r"^[a-z][a-z0-9_]*$")
REQUIRED_FIELDS = {"id", "url", "initial_class", "scope", "notes"}


class RegistryError(ValueError):
    """Raised when the source registry does not satisfy its local contract."""


def default_registry_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "sources.json"


def load_sources(path: Path | None = None) -> list[SourceSpec]:
    registry_path = path or default_registry_path()
    payload = json.loads(registry_path.read_text(encoding="utf-8"))

    if payload.get("schema_version") != 1:
        raise RegistryError("config/sources.json: expected schema_version=1")

    raw_sources = payload.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise RegistryError("config/sources.json: sources must be a non-empty list")

    sources: list[SourceSpec] = []
    ids: set[str] = set()
    urls: set[str] = set()

    for index, raw in enumerate(raw_sources, start=1):
        if not isinstance(raw, dict):
            raise RegistryError(f"source #{index}: expected an object")

        missing = REQUIRED_FIELDS - raw.keys()
        if missing:
            fields = ", ".join(sorted(missing))
            raise RegistryError(f"source #{index}: missing fields: {fields}")

        source = SourceSpec(**{field: str(raw[field]).strip() for field in REQUIRED_FIELDS})
        parsed_url = urlparse(source.url)

        if not SOURCE_ID.fullmatch(source.id):
            raise RegistryError(f"source #{index}: invalid id {source.id!r}")
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise RegistryError(f"source {source.id}: invalid HTTP(S) URL")
        if source.id in ids:
            raise RegistryError(f"duplicate source id: {source.id}")
        if source.url in urls:
            raise RegistryError(f"duplicate source URL: {source.url}")
        if source.scope not in {"single_item", "collection"}:
            raise RegistryError(f"source {source.id}: unsupported scope {source.scope!r}")

        ids.add(source.id)
        urls.add(source.url)
        sources.append(source)

    return sources

