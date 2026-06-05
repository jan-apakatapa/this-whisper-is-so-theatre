"""Экспорт размеченных сегментов в табличный формат CSV."""

import pandas as pd


def export_csv(records, output_file: str) -> None:
    """Сохраняет список записей сегментов в CSV-файл.

    Итоговая таблица содержит поля ``id``, ``audio_path``, ``text``,
    ``start_time`` и ``end_time`` и пригодна для загрузки при дообучении
    моделей семейства Whisper.

    Аргументы:
        records: Список объектов :class:`~dataset_builder.models.SegmentRecord`.
        output_file: Путь к выходному CSV-файлу.
    """
    rows = [
        {
            "id": r.id,
            "audio_path": r.audio_path,
            "text": r.text,
            "start_time": r.start_time,
            "end_time": r.end_time,
        }
        for r in records
    ]

    pd.DataFrame(rows).to_csv(output_file, index=False)
