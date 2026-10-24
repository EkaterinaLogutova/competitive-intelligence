from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from competitive_intelligence.dzen import extract_records, write_jsonl
from competitive_intelligence.registry import RegistryError, load_sources


SUBMISSION_FILES = ("task-1.md", "task-2.md", "task-3.md")


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def validate_repository() -> list[str]:
    errors: list[str] = []
    source_ids: set[str] = set()

    try:
        sources = load_sources()
        source_ids = {source.id for source in sources}
        if len(sources) != 6:
            errors.append(f"ожидалось 6 источников, найдено {len(sources)}")
    except (OSError, json.JSONDecodeError, RegistryError) as exc:
        errors.append(str(exc))

    submission_dir = repository_root() / "submission"
    for name in SUBMISSION_FILES:
        path = submission_dir / name
        if not path.is_file():
            errors.append(f"нет файла ответа: {path.relative_to(repository_root())}")
        elif not path.read_text(encoding="utf-8").strip():
            errors.append(f"файл ответа пуст: {path.relative_to(repository_root())}")

    inventory_path = repository_root() / "data" / "curated" / "source_inventory.csv"
    try:
        with inventory_path.open(encoding="utf-8", newline="") as source:
            inventory_ids = {row["source_id"] for row in csv.DictReader(source)}
        if source_ids and inventory_ids != source_ids:
            missing = sorted(source_ids - inventory_ids)
            extra = sorted(inventory_ids - source_ids)
            errors.append(
                f"реестр и паспорт выборки не совпадают: "
                f"пропущены={missing or '-'}, лишние={extra or '-'}"
            )
    except (OSError, KeyError, csv.Error) as exc:
        errors.append(f"ошибка в паспорте выборки: {exc}")

    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="competitive-intelligence",
        description="Команды для проверки тестового задания.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list-sources", help="показать шесть источников")
    subparsers.add_parser("validate", help="проверить данные и файлы ответа")
    extract_dzen = subparsers.add_parser(
        "extract-dzen",
        help="извлечь публичные карточки из сохраненной страницы Дзена",
    )
    extract_dzen.add_argument("snapshot", type=Path)
    extract_dzen.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)

    if args.command == "list-sources":
        for source in load_sources():
            print(f"{source.id}\t{source.initial_class}\t{source.url}")
        return 0

    if args.command == "validate":
        errors = validate_repository()
        if errors:
            for error in errors:
                print(f"ОШИБКА: {error}", file=sys.stderr)
            return 1
        print(
            "Проверка пройдена: 6 источников, паспорт выборки совпадает с реестром, "
            "3 файла ответа на месте."
        )
        return 0

    if args.command == "extract-dzen":
        try:
            records = extract_records(args.snapshot)
            write_jsonl(records, args.output)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"ОШИБКА: {exc}", file=sys.stderr)
            return 2
        print(f"Извлечено записей: {len(records)}. Результат: {args.output}.")
        return 0

    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())

