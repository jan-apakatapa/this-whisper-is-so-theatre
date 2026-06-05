"""Очистка набора данных от пустых аннотаций.

Удаляет записи без транскрипции и соответствующие им аудиофайлы, чтобы в
обучающую выборку не попадали неразмеченные сегменты.
"""

import argparse
import os

import pandas as pd


def _detect_separator(path: str) -> str:
    """Определяет разделитель CSV-файла по его первой строке."""
    with open(path, encoding="utf-8") as f:
        first_line = f.readline()
    return "\t" if "\t" in first_line else ","


def clean_annotations(annotations_path: str) -> int:
    """Удаляет из набора данных записи с пустой транскрипцией.

    Записи без текста (или содержащие лишь пробельные символы) исключаются из
    таблицы, а связанные с ними аудиофайлы удаляются с диска. Очищенная
    таблица перезаписывается на место исходной.

    Аргументы:
        annotations_path: Путь к CSV-файлу с аннотациями.

    Возвращает:
        Число удалённых записей.
    """
    sep = _detect_separator(annotations_path)
    df = pd.read_csv(annotations_path, sep=sep)

    is_empty = df["text"].isnull() | (df["text"].astype(str).str.strip() == "")
    to_remove = df[is_empty]

    for audio_path in to_remove["audio_path"]:
        if os.path.exists(audio_path):
            os.remove(audio_path)

    df_clean = df[~is_empty]
    df_clean.to_csv(annotations_path, sep=sep, index=False)

    return len(to_remove)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Удаление пустых аннотаций из набора данных."
    )
    parser.add_argument(
        "annotations",
        nargs="?",
        default="annotations.csv",
        help="Путь к CSV-файлу с аннотациями (по умолчанию annotations.csv).",
    )
    args = parser.parse_args()

    removed = clean_annotations(args.annotations)
    print(f"Удалено записей: {removed}")
    print(f"Файл сохранён: {args.annotations}")


if __name__ == "__main__":
    main()
