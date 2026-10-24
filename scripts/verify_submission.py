from __future__ import annotations

import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "submission" / "final"
GITHUB_URL = "https://github.com/EkaterinaLogutova/competitive-intelligence"
AUTHOR = "Екатерина Логутова"
TEAM = (
    "Команда исследований технологий управления интеллектуальной собственности "
    "на основе ИИ и аналитики"
)

EXPECTED_NAMES = [
    (
        "Логутова Е. Команда исследований технологий управления интеллектуальной "
        f"собственностью на основе ИИ и аналитики. Задание {number}.docx"
    )
    for number in (1, 2, 3)
]

TASK_REQUIREMENTS = {
    1: [
        "https://irecommend.ru/content/sait-ozontravel-0",
        "https://5koleso.livejournal.com",
        "https://dzen.ru/news/rubric/computers",
        "https://4pda.to/forum/index.php?showforum=320",
        "https://otzovik.com/money_systems/banks/",
        "https://www.drive2.ru/featured-topics/CVQ0gEAAcHQ/",
        "автор",
        "дата",
        "тип страницы",
        "единица материала",
    ],
    2: ["10 источников", "100 источников", "1 000 источников", "10 000 источников"],
    3: [
        "3.1 Автоматизация сбора",
        "3.2 Классификация источников и извлечение полей",
        "3.3 Что можно построить для медиамониторинга",
        "неизвестный тип",
        "RAG",
    ],
}


def read_docx(path: Path) -> tuple[str, str]:
    with zipfile.ZipFile(path) as archive:
        document_xml = archive.read("word/document.xml")
        relationships = archive.read("word/_rels/document.xml.rels").decode("utf-8")

    root = ElementTree.fromstring(document_xml)
    text = " ".join(node.text or "" for node in root.iter() if node.tag.endswith("}t"))
    return text, relationships


def main() -> int:
    errors: list[str] = []
    actual_names = sorted(path.name for path in OUTPUT_DIR.glob("*.docx"))
    if actual_names != sorted(EXPECTED_NAMES):
        errors.append("В submission/final должен находиться ровно ожидаемый набор из трех DOCX.")

    for number, name in enumerate(EXPECTED_NAMES, start=1):
        path = OUTPUT_DIR / name
        if not path.exists():
            errors.append(f"Нет файла: {name}")
            continue

        text, relationships = read_docx(path)
        common_requirements = [AUTHOR, TEAM, f"Задание {number}"]
        for fragment in common_requirements + TASK_REQUIREMENTS[number]:
            if fragment.casefold() not in text.casefold():
                errors.append(f"{name}: не найдено обязательное содержание: {fragment}")

        if GITHUB_URL not in text or GITHUB_URL not in relationships:
            errors.append(f"{name}: ссылка на GitHub отсутствует или не является гиперссылкой.")

        if "—" in text or "–" in text:
            errors.append(f"{name}: найдено длинное или среднее тире.")
        if ", а не" in text.casefold():
            errors.append(f"{name}: найден оборот ', а не'.")

    if errors:
        print("Проверка не пройдена:")
        print(*(f"- {error}" for error in errors), sep="\n")
        return 1

    print("Проверка пройдена: 3 DOCX, имена, содержание и гиперссылки соответствуют ТЗ.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
