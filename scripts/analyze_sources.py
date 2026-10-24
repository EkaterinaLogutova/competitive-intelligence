from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


FIELD_COLUMNS = (
    "has_title",
    "has_body",
    "has_author",
    "has_published_at",
    "has_publisher",
    "has_metrics",
    "has_original_url",
)

FIELD_NAMES = {
    "has_title": "заголовок",
    "has_body": "текст",
    "has_author": "автор",
    "has_published_at": "дата публикации",
    "has_publisher": "издание",
    "has_metrics": "счетчики",
    "has_original_url": "ссылка на оригинал",
}

PAGE_TYPE_NAMES = {
    "review_collection": "отзывы об одном объекте",
    "publisher_blog_feed": "редакционная лента",
    "news_aggregator_rubric": "новостная рубрика-агрегатор",
    "forum_section_index": "раздел форума",
    "review_catalog": "каталог объектов с отзывами",
    "topic_collection": "тематическая подборка",
}

STATE_NAMES = {
    "populated": "есть материалы",
    "empty": "пустая страница",
}

ACCESS_NAMES = {
    "browser": "браузер",
    "direct_http": "обычный запрос",
    "saved_html": "сохраненная страница",
}


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    def render(row: list[object]) -> str:
        values = [str(value).replace("|", "\\|") for value in row]
        return "| " + " | ".join(values) + " |"

    separator = ["---"] * len(headers)
    return "\n".join([render(headers), render(separator), *(render(row) for row in rows)])


def build_report(inventory_path: Path, dzen_path: Path) -> str:
    inventory = pd.read_csv(inventory_path)
    dzen_cards = pd.DataFrame(json.loads(dzen_path.read_text(encoding="utf-8")))
    populated = inventory.loc[inventory["collection_state"] == "populated"]

    coverage_rows: list[list[object]] = []
    for field in FIELD_COLUMNS:
        all_sources = float(np.mean(inventory[field])) * 100
        populated_sources = float(np.mean(populated[field])) * 100
        coverage_rows.append(
            [FIELD_NAMES[field], f"{all_sources:.0f}%", f"{populated_sources:.0f}%"]
        )

    access_counts = (
        inventory.groupby("access_method", dropna=False)
        .size()
        .sort_values(ascending=False)
    )
    access_rows = [[ACCESS_NAMES.get(name, name), int(count)] for name, count in access_counts.items()]

    publisher_counts = dzen_cards["source"].value_counts()
    publisher_rows = [[publisher, int(count)] for publisher, count in publisher_counts.items()]

    class_rows = [
        [
            row.source_name,
            PAGE_TYPE_NAMES.get(row.page_type, row.page_type),
            STATE_NAMES.get(row.collection_state, row.collection_state),
            ACCESS_NAMES.get(row.access_method, row.access_method),
        ]
        for row in inventory.itertuples()
    ]

    lines = [
        "# Аудит исследовательской выборки",
        "",
        "Отчет строится из `data/curated/source_inventory.csv` и обезличенного снимка Дзена.",
        "Он описывает текущую выборку, а не генеральную совокупность сайтов.",
        "",
        "## Состав выборки",
        "",
        f"Источников: {len(inventory)}. Типов страниц: {inventory['page_type'].nunique()}.",
        f"Заполненных коллекций: {len(populated)}; пустых: {len(inventory) - len(populated)}.",
        "",
        markdown_table(
            ["Источник", "Тип страницы", "Состояние", "Доступ"], class_rows
        ),
        "",
        "## Полнота наблюдаемых полей",
        "",
        markdown_table(
            ["Поле", "Все источники", "Только заполненные"], coverage_rows
        ),
        "",
        "Нулевая полнота поля не всегда означает ошибку. Например, у каталога объектов",
        "может не быть автора или даты публикации на индексной странице.",
        "",
        "## Способы доступа",
        "",
        markdown_table(["Способ", "Источников"], access_rows),
        "",
        "## Издания в снимке Дзена",
        "",
        f"Карточек: {len(dzen_cards)}; уникальных изданий: {dzen_cards['source'].nunique()}.",
        "",
        markdown_table(["Издание", "Карточек"], publisher_rows),
        "",
        "## Ограничение интерпретации",
        "",
        "Выборка целевая и малая. Проценты полноты нужны для проектирования схемы и",
        "следующей разметки; их нельзя переносить на весь веб или использовать как",
        "оценку качества будущей модели.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Собрать отчет по исследуемым источникам.")
    parser.add_argument(
        "--inventory",
        type=Path,
        default=Path("data/curated/source_inventory.csv"),
    )
    parser.add_argument(
        "--dzen",
        type=Path,
        default=Path("docs/dzen-news-snapshot-2026-10-24.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/source-audit.md"),
    )
    args = parser.parse_args()

    report = build_report(args.inventory, args.dzen)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8", newline="\n")
    print(f"Отчет сохранен в {args.output}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
