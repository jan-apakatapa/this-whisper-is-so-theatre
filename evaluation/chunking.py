"""Разбиение текста на перекрывающиеся фрагменты для пофрагментной оценки."""

from typing import List


def split_into_chunks(
    text: str, chunk_size: int = 150, overlap: int = 20
) -> List[str]:
    """Разбивает текст на перекрывающиеся фрагменты по словам.

    Дополнительная нормализация не выполняется — предполагается, что текст
    уже нормализован. Перекрытие фрагментов обеспечивает непрерывность анализа
    на их границах.

    Аргументы:
        text: Исходный (предварительно нормализованный) текст.
        chunk_size: Число слов в одном фрагменте.
        overlap: Число перекрывающихся слов между соседними фрагментами.

    Возвращает:
        Список строк-фрагментов.
    """
    words = text.strip().split()
    chunks = []
    step = chunk_size - overlap

    i = 0
    while i < len(words):
        chunk_words = words[i:i + chunk_size]
        if chunk_words:
            chunks.append(" ".join(chunk_words))
        if i + chunk_size >= len(words):
            break
        i += step

    return chunks
