"""Веб-приложение для оценки качества распознавания театральной речи.

Сравнивает расшифровки моделей Whisper Tiny и Small с эталонной транскрипцией
и выводит набор метрик (WER, CER, статистику ошибок, частоту галлюцинаций),
а также визуализации и инструменты пофрагментного анализа.

Запуск:

    streamlit run evaluation/app.py
"""

import chunking
import metrics
import utils
import visualization
import streamlit as st

st.set_page_config(
    page_title="Оценка качества распознавания театральной речи",
    layout="wide",
)

st.title("Оценка качества распознавания театральной речи")
st.write(
    "Сравнение расшифровок Whisper Tiny и Small с эталонной транскрипцией "
    "аудиозаписи театральной постановки."
)

# --- Ввод данных ---
with st.sidebar:
    st.header("Исходные транскрипции")
    ref_txt = st.text_area("Эталонная транскрипция", height=200, key="ref_text")
    tiny_txt = st.text_area("Расшифровка Whisper Tiny", height=200, key="tiny_text")
    small_txt = st.text_area("Расшифровка Whisper Small", height=200, key="small_text")
    st.markdown("---")
    ref_file = utils.file_uploader("Или загрузите эталон (.txt)", "file_ref")
    tiny_file = utils.file_uploader("Или загрузите Tiny (.txt)", "file_tiny")
    small_file = utils.file_uploader("Или загрузите Small (.txt)", "file_small")

    # Загруженный файл имеет приоритет над введённым вручную текстом.
    reference = ref_file or ref_txt
    tiny_pred = tiny_file or tiny_txt
    small_pred = small_file or small_txt

if not (reference and tiny_pred and small_pred):
    st.warning("Укажите все три транскрипции (текстом или файлом) для начала оценки.")
    st.stop()

if st.button("Запустить оценку", use_container_width=True):
    st.success("Результаты оценки")

    # --- Разбиение на фрагменты ---
    ref_chunks = chunking.split_into_chunks(reference)
    tiny_chunks = chunking.split_into_chunks(tiny_pred)
    small_chunks = chunking.split_into_chunks(small_pred)

    # Выравнивание числа фрагментов по минимальному.
    min_len = min(len(ref_chunks), len(tiny_chunks), len(small_chunks))
    ref_chunks = ref_chunks[:min_len]
    tiny_chunks = tiny_chunks[:min_len]
    small_chunks = small_chunks[:min_len]

    # --- Глобальные метрики ---
    global_results = {
        "tiny": metrics.global_metrics(reference, tiny_pred),
        "small": metrics.global_metrics(reference, small_pred),
    }
    visualization.summary_cards(global_results)
    visualization.plot_global_bar(global_results)

    # --- Пофрагментные метрики ---
    chunk_df = metrics.chunk_metrics(ref_chunks, tiny_chunks, small_chunks)
    visualization.plot_chunk_line(chunk_df)
    st.write("Таблица WER / CER по фрагментам:")
    st.dataframe(chunk_df, use_container_width=True, height=350)

    # --- Галлюцинации ---
    chunk_halluc_tiny = metrics.chunk_hallucinations(ref_chunks, tiny_chunks)
    chunk_halluc_small = metrics.chunk_hallucinations(ref_chunks, small_chunks)
    halluc_tiny = metrics.hallucination_rate(reference, tiny_pred)
    halluc_small = metrics.hallucination_rate(reference, small_pred)
    visualization.plot_hallucination(chunk_halluc_tiny, chunk_halluc_small, chunk_df)
    st.markdown(
        f"**Вставки Tiny:** {halluc_tiny[0]} (доля: {halluc_tiny[1]:.2%})  |  "
        f"**Вставки Small:** {halluc_small[0]} (доля: {halluc_small[1]:.2%})"
    )

    # --- Анализ ошибок ---
    error_stats = {
        "tiny": metrics.jiwer_detailed(reference, tiny_pred),
        "small": metrics.jiwer_detailed(reference, small_pred),
    }
    st.subheader("Анализ ошибок")
    st.write(f"**Tiny:** {error_stats['tiny']}")
    st.write(f"**Small:** {error_stats['small']}")
    visualization.plot_error_distribution(error_stats)

    # --- Обзор фрагментов ---
    st.subheader("Обзор фрагментов")
    with st.expander("Фрагменты, отсортированные по убыванию WER (Tiny)"):
        worst = chunk_df.sort_values(by="Tiny WER", ascending=False)
        st.dataframe(worst.head(10), use_container_width=True, height=300)
        st.write("Лучшие фрагменты:")
        st.dataframe(
            chunk_df.sort_values(by="Tiny WER").head(5), use_container_width=True
        )
        st.write("Фрагменты с наибольшим расхождением Tiny и Small:")
        chunk_df["WER Diff"] = abs(chunk_df["Tiny WER"] - chunk_df["Small WER"])
        st.dataframe(
            chunk_df.sort_values(by="WER Diff", ascending=False).head(5),
            use_container_width=True,
        )

    # --- Выравнивание текстов ---
    st.subheader("Выравнивание транскрипций")
    chunk_ix = st.number_input(
        "Номер фрагмента для выравнивания",
        min_value=1, max_value=len(ref_chunks), value=1,
    )
    ref_html, tiny_html = utils.highlight_alignment(
        ref_chunks[chunk_ix - 1], tiny_chunks[chunk_ix - 1]
    )
    _, small_html = utils.highlight_alignment(
        ref_chunks[chunk_ix - 1], small_chunks[chunk_ix - 1]
    )

    st.markdown("**Эталон и Tiny:**", unsafe_allow_html=True)
    st.markdown(ref_html, unsafe_allow_html=True)
    st.markdown(tiny_html, unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("**Эталон и Small:**", unsafe_allow_html=True)
    st.markdown(ref_html, unsafe_allow_html=True)
    st.markdown(small_html, unsafe_allow_html=True)

    # --- Выгрузка отчётов ---
    st.subheader("Выгрузка отчётов")
    json_report = {
        "global_metrics": global_results,
        "chunk_metrics": chunk_df.to_dict(orient="records"),
        "error_statistics": error_stats,
        "hallucination_metrics": {
            "tiny": {
                "insertions": halluc_tiny[0],
                "hallucination_rate": halluc_tiny[1],
            },
            "small": {
                "insertions": halluc_small[0],
                "hallucination_rate": halluc_small[1],
            },
            "chunks": {"tiny": chunk_halluc_tiny, "small": chunk_halluc_small},
        },
    }
    utils.download_button(chunk_df, "chunk_metrics.csv", "Скачать метрики (CSV)")
    utils.download_button(
        json_report, "full_report.json", "Скачать полный отчёт (JSON)", as_json=True
    )
