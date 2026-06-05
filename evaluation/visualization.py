"""Визуализация результатов оценки качества распознавания."""

import pandas as pd
import plotly.express as px
import streamlit as st


def summary_cards(global_results: dict) -> None:
    """Выводит сводные карточки с глобальными значениями WER и CER."""
    cols = st.columns(4)
    cols[0].metric("WER Tiny", f"{global_results['tiny']['wer'] * 100:.2f}%")
    cols[1].metric("WER Small", f"{global_results['small']['wer'] * 100:.2f}%")
    cols[2].metric("CER Tiny", f"{global_results['tiny']['cer'] * 100:.2f}%")
    cols[3].metric("CER Small", f"{global_results['small']['cer'] * 100:.2f}%")


def plot_global_bar(global_results: dict) -> None:
    """Строит столбчатую диаграмму сравнения WER и CER для обеих моделей."""
    df = pd.DataFrame(
        [
            {
                "Модель": "Whisper Tiny",
                "WER": global_results["tiny"]["wer"],
                "CER": global_results["tiny"]["cer"],
            },
            {
                "Модель": "Whisper Small",
                "WER": global_results["small"]["wer"],
                "CER": global_results["small"]["cer"],
            },
        ]
    )
    st.subheader("Глобальные метрики")
    fig = px.bar(
        df, x="Модель", y=["WER", "CER"], barmode="group",
        title="Сравнение WER / CER",
    )
    st.plotly_chart(fig, use_container_width=True)


def plot_chunk_line(chunk_df: pd.DataFrame) -> None:
    """Строит графики динамики WER и CER по фрагментам."""
    st.subheader("WER / CER по фрагментам")
    fig_wer = px.line(
        chunk_df, x="Chunk ID", y=["Tiny WER", "Small WER"],
        title="Динамика WER по фрагментам",
    )
    st.plotly_chart(fig_wer, use_container_width=True)

    fig_cer = px.line(
        chunk_df, x="Chunk ID", y=["Tiny CER", "Small CER"],
        title="Динамика CER по фрагментам",
    )
    st.plotly_chart(fig_cer, use_container_width=True)


def plot_error_distribution(error_stats: dict) -> None:
    """Строит распределение ошибок по типам (подстановки, вставки, удаления)."""
    err_types = ["substitutions", "insertions", "deletions"]
    data = [
        {"Модель": "Tiny", **{k: error_stats["tiny"][k] for k in err_types}},
        {"Модель": "Small", **{k: error_stats["small"][k] for k in err_types}},
    ]
    df = pd.DataFrame(data)
    fig = px.bar(
        df.set_index("Модель"), barmode="group",
        title="Распределение ошибок по типам",
    )
    st.plotly_chart(fig, use_container_width=True)


def plot_hallucination(
    chunk_hallucinations_tiny, chunk_hallucinations_small, chunk_df
) -> None:
    """Строит график частоты галлюцинаций по фрагментам."""
    df = pd.DataFrame(
        {
            "Chunk ID": chunk_df["Chunk ID"],
            "Tiny Hallucination Rate": [
                h["hallucination_rate"] for h in chunk_hallucinations_tiny
            ],
            "Small Hallucination Rate": [
                h["hallucination_rate"] for h in chunk_hallucinations_small
            ],
        }
    )
    fig = px.line(
        df,
        x="Chunk ID",
        y=["Tiny Hallucination Rate", "Small Hallucination Rate"],
        title="Частота галлюцинаций по фрагментам",
    )
    st.plotly_chart(fig, use_container_width=True)
