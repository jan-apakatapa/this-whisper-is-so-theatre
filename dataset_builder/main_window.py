"""Главное окно утилиты формирования набора данных."""

import os
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .annotation_window import AnnotationWindow
from .audio_utils import (
    TARGET_CHANNELS,
    TARGET_SAMPLE_RATE,
    extract_audio,
)
from .segmenter import SpeechSegmenter

DATA_DIR = "data"
WAV_FILE = os.path.join(DATA_DIR, "audio.wav")
SEGMENTS_DIR = os.path.join(DATA_DIR, "segments")


class MainWindow:
    """Главное окно: выбор медиафайла и запуск конвейера обработки.

    Конвейер выполняет извлечение аудио, детектирование речевых сегментов и
    их экспорт, после чего открывает окно ручной разметки. Тяжёлые операции
    выполняются в фоновом потоке, чтобы не блокировать интерфейс.
    """

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("TTS Dataset Creator")
        self.root.geometry("700x300")
        self.file_path = ""
        self.build_ui()

    def build_ui(self) -> None:
        """Создаёт элементы интерфейса."""
        title = tk.Label(
            self.root,
            text="Создание датасета TTS / ASR",
            font=("Arial", 16, "bold"),
        )
        title.pack(pady=10)

        frame = tk.Frame(self.root)
        frame.pack(fill="x", padx=15)

        self.path_var = tk.StringVar()
        tk.Entry(frame, textvariable=self.path_var).pack(
            side="left", fill="x", expand=True
        )
        tk.Button(frame, text="Выбрать файл", command=self.select_file).pack(
            side="left", padx=5
        )

        self.progress = ttk.Progressbar(self.root, mode="indeterminate")
        self.progress.pack(fill="x", padx=15, pady=20)

        self.status = tk.Label(self.root, text="Ожидание файла")
        self.status.pack()

        tk.Button(
            self.root,
            text="Начать обработку",
            height=2,
            command=self.start_processing,
        ).pack(pady=15)

    def select_file(self) -> None:
        """Открывает диалог выбора медиафайла."""
        path = filedialog.askopenfilename(
            filetypes=[("Media files", "*.mp4 *.wav *.mp3 *.m4a")]
        )
        if path:
            self.file_path = path
            self.path_var.set(path)

    def start_processing(self) -> None:
        """Запускает обработку выбранного файла в фоновом потоке."""
        if not self.file_path:
            messagebox.showerror("Ошибка", "Выберите файл")
            return

        self.progress.start()
        threading.Thread(target=self.process_file, daemon=True).start()

    def process_file(self) -> None:
        """Выполняет полный конвейер обработки медиафайла."""
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            ext = os.path.splitext(self.file_path)[1].lower()

            self.set_status("Извлечение аудио...")
            if ext == ".mp4":
                extract_audio(self.file_path, WAV_FILE)
            else:
                # Для прочих форматов конвертируем напрямую через ffmpeg.
                subprocess.run(
                    [
                        "ffmpeg", "-y", "-i", self.file_path,
                        "-ac", str(TARGET_CHANNELS),
                        "-ar", str(TARGET_SAMPLE_RATE),
                        WAV_FILE,
                    ],
                    check=True,
                )

            self.set_status("Поиск речи...")
            segmenter = SpeechSegmenter()
            segments = segmenter.detect(WAV_FILE)
            self.set_status(f"Найдено сегментов: {len(segments)}")

            exported = segmenter.export_segments(WAV_FILE, SEGMENTS_DIR, segments)
            self.progress.stop()
            self.root.after(0, lambda: self.open_annotation(exported))

        except Exception as exc:  # noqa: BLE001 — показываем любую ошибку
            self.progress.stop()
            self.root.after(0, lambda: messagebox.showerror("Ошибка", str(exc)))

    def set_status(self, text: str) -> None:
        """Обновляет строку состояния из любого потока."""
        self.root.after(0, lambda: self.status.config(text=text))

    def open_annotation(self, exported) -> None:
        """Открывает окно ручной разметки полученных сегментов."""
        self.status.config(text="Сегментация завершена")
        messagebox.showinfo("Готово", f"Создано {len(exported)} сегментов")
        AnnotationWindow(exported)
