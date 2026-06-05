"""Вспомогательные функции интерфейса: загрузка, выгрузка, выравнивание."""

import json
from difflib import SequenceMatcher
from typing import Optional, Tuple

import pandas as pd
import streamlit as st

# Цвета подсветки расхождений при выравнивании текстов.
COLOR_SUBSTITUTION = "#fdd"  # подстановка
COLOR_DELETION = "#faa"      # удаление (есть в эталоне, нет в гипотезе)
COLOR_INSERTION = "#afa"     # вставка (есть в гипотезе, нет в эталоне)


def file_uploader(label: str, input_key: str) -> Optional[str]:
    """Виджет загрузки текстового файла. Возвращает его содержимое либо None."""
    uploaded_file = st.file_uploader(label, type=["txt"], key=input_key)
    if uploaded_file is None:
        return None
    try:
        return uploaded_file.read().decode("utf-8")
    except Exception:  # noqa: BLE001 — некорректная кодировка и т. п.
        st.error("Не удалось прочитать файл (проверьте кодировку).")
        return None


def download_button(data, filename: str, label: str, as_json: bool = False) -> None:
    """Виджет выгрузки данных в формате CSV или JSON."""
    if as_json:
        mime = "application/json"
        filedata = json.dumps(data, indent=2, ensure_ascii=False)
    else:
        mime = "text/csv"
        filedata = (
            data.to_csv(index=False)
            if isinstance(data, pd.DataFrame)
            else str(data)
        )
    st.download_button(label=label, data=filedata, file_name=filename, mime=mime)


def highlight_alignment(ref: str, hyp: str) -> Tuple[str, str]:
    """Выравнивает два текста и выделяет расхождения цветом.

    Используется алгоритм поиска наибольшей общей подпоследовательности
    (:class:`difflib.SequenceMatcher`). Подстановки, удаления и вставки
    выделяются разными цветами.

    Возвращает:
        Кортеж ``(html_эталона, html_гипотезы)`` с HTML-разметкой.
    """
    ref_words = ref.split()
    hyp_words = hyp.split()
    matcher = SequenceMatcher(a=ref_words, b=hyp_words)

    ref_out, hyp_out = [], []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            ref_out.extend(ref_words[i1:i2])
            hyp_out.extend(hyp_words[j1:j2])
        elif tag == "replace":
            ref_out.append(_span(COLOR_SUBSTITUTION, ref_words[i1:i2]))
            hyp_out.append(_span(COLOR_SUBSTITUTION, hyp_words[j1:j2]))
        elif tag == "delete":
            ref_out.append(_span(COLOR_DELETION, ref_words[i1:i2]))
        elif tag == "insert":
            hyp_out.append(_span(COLOR_INSERTION, hyp_words[j1:j2]))

    return " ".join(ref_out), " ".join(hyp_out)


def _span(color: str, words) -> str:
    """Оборачивает слова в цветной HTML-фрагмент."""
    return f"<span style='background:{color};'>{' '.join(words)}</span>"
