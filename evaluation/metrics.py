"""Метрики оценки качества распознавания речи (WER, CER и др.)."""

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from jiwer import cer, wer
from jiwer.measures import process_words


def global_metrics(ref: str, pred: str) -> Dict[str, float]:
    """Вычисляет WER и CER для пары «эталон — гипотеза»."""
    return {"wer": wer(ref, pred), "cer": cer(ref, pred)}


def jiwer_detailed(ref: str, pred: str) -> Dict[str, float]:
    """Возвращает детализированную статистику ошибок.

    Включает число подстановок, вставок, удалений и совпадений, а также
    производные метрики WER, MER, WIL и WIP.
    """
    result = process_words(ref, pred)
    return {
        "substitutions": result.substitutions,
        "insertions": result.insertions,
        "deletions": result.deletions,
        "hits": result.hits,
        "wer": result.wer,
        "mer": result.mer,
        "wil": result.wil,
        "wip": result.wip,
    }


def hallucination_rate(ref: str, pred: str) -> Tuple[int, float]:
    """Оценивает частоту галлюцинаций модели.

    Галлюцinations измеряются как доля вставленных слов (отсутствующих в
    эталоне) от общего числа слов в гипотезе.

    Возвращает:
        Кортеж ``(число_вставок, доля_вставок)``.
    """
    result = process_words(ref, pred)
    insertions = result.insertions
    total = len(pred.split())
    return insertions, (insertions / total if total > 0 else 0.0)


def chunk_metrics(
    reference_chunks: List[str],
    tiny_chunks: List[str],
    small_chunks: List[str],
) -> pd.DataFrame:
    """Вычисляет WER и CER по каждому фрагменту для обеих моделей."""
    rows = []
    for idx, (ref, tiny, small) in enumerate(
        zip(reference_chunks, tiny_chunks, small_chunks)
    ):
        tiny_m = global_metrics(ref, tiny)
        small_m = global_metrics(ref, small)
        rows.append(
            {
                "Chunk ID": idx + 1,
                "Tiny WER": tiny_m["wer"],
                "Small WER": small_m["wer"],
                "Tiny CER": tiny_m["cer"],
                "Small CER": small_m["cer"],
            }
        )
    return pd.DataFrame(rows)


def chunk_error_stats(
    reference_chunks: List[str], pred_chunks: List[str]
) -> List[Dict[str, float]]:
    """Возвращает детализированную статистику ошибок по каждому фрагменту."""
    return [
        jiwer_detailed(ref, pred)
        for ref, pred in zip(reference_chunks, pred_chunks)
    ]


def chunk_hallucinations(
    reference_chunks: List[str], pred_chunks: List[str]
) -> List[Dict[str, float]]:
    """Возвращает показатели галлюцинаций по каждому фрагменту."""
    result = []
    for ref, pred in zip(reference_chunks, pred_chunks):
        insertions, rate = hallucination_rate(ref, pred)
        result.append({"insertions": insertions, "hallucination_rate": rate})
    return result


def aggregate_metrics(chunk_df: pd.DataFrame, column: str) -> Dict[str, float]:
    """Вычисляет сводную статистику по столбцу метрик (среднее, медиана и т. д.)."""
    values = chunk_df[column].values
    return {
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "std": float(np.std(values)),
    }
