"""Графический интерфейс ручной разметки аудиосегментов."""

import os
import threading
import tkinter as tk
from tkinter import messagebox

import sounddevice as sd
import soundfile as sf

from .exporter import export_csv
from .models import SegmentRecord

OUTPUT_CSV = "annotations.csv"


class AnnotationWindow:
    """Окно последовательной разметки сегментов.

    Оператор прослушивает каждый сегмент и вводит соответствующую ему
    текстовую транскрипцию. По завершении результат экспортируется в CSV.
    """

    def __init__(self, segments):
        """Создаёт окно разметки.

        Аргументы:
            segments: Список кортежей ``(id, путь, начало, конец)``,
                возвращаемый методом ``SpeechSegmenter.export_segments``.
        """
        self.root = tk.Toplevel()
        self.root.title("Разметка")

        self.records = [
            SegmentRecord(
                id=s[0],
                audio_path=s[1],
                text="",
                start_time=s[2],
                end_time=s[3],
            )
            for s in segments
        ]

        self.current = 0
        self.playing = False
        self.build_ui()
        self.load_segment()

    def build_ui(self) -> None:
        """Создаёт элементы интерфейса."""
        self.counter_label = tk.Label(self.root, font=("Arial", 14))
        self.counter_label.pack(pady=10)

        self.time_label = tk.Label(self.root)
        self.time_label.pack()

        self.text_box = tk.Text(self.root, height=5)
        self.text_box.pack(fill="both", expand=True, padx=10, pady=10)

        buttons = tk.Frame(self.root)
        buttons.pack()

        tk.Button(buttons, text="\u25c0", command=self.prev_segment).pack(side="left")
        tk.Button(buttons, text="\u25b6 Play", command=self.play).pack(side="left")
        tk.Button(buttons, text="\u25b6", command=self.next_segment).pack(side="left")

        tk.Button(self.root, text="Экспорт CSV", command=self.export).pack(pady=10)

    def save_current(self) -> None:
        """Сохраняет введённый текст в текущую запись."""
        self.records[self.current].text = self.text_box.get("1.0", "end").strip()

    def load_segment(self) -> None:
        """Отображает данные текущего сегмента в интерфейсе."""
        rec = self.records[self.current]

        self.counter_label.config(text=f"{self.current + 1} / {len(self.records)}")
        self.time_label.config(text=f"{rec.start_time:.2f} - {rec.end_time:.2f}")

        self.text_box.delete("1.0", "end")
        self.text_box.insert("1.0", rec.text)

    def play(self) -> None:
        """Воспроизводит аудио текущего сегмента в фоновом потоке."""
        rec = self.records[self.current]

        if not os.path.exists(rec.audio_path):
            messagebox.showerror(
                "Ошибка воспроизведения",
                f"Файл не найден:\n{rec.audio_path}",
            )
            return

        if self.playing:
            return  # воспроизведение уже идёт

        self.playing = True
        data, samplerate = sf.read(rec.audio_path, dtype="int16")

        def play_thread():
            try:
                sd.play(data, samplerate)
                sd.wait()
            except Exception as exc:  # noqa: BLE001 — показываем любую ошибку
                self.root.after(
                    0,
                    lambda: messagebox.showerror("Ошибка воспроизведения", str(exc)),
                )
            finally:
                self.playing = False

        threading.Thread(target=play_thread, daemon=True).start()

    def next_segment(self) -> None:
        """Переходит к следующему сегменту, сохранив текущий."""
        self.save_current()
        if self.current < len(self.records) - 1:
            self.current += 1
        self.load_segment()

    def prev_segment(self) -> None:
        """Переходит к предыдущему сегменту, сохранив текущий."""
        self.save_current()
        if self.current > 0:
            self.current -= 1
        self.load_segment()

    def export(self) -> None:
        """Экспортирует все размеченные записи в CSV-файл."""
        self.save_current()
        export_csv(self.records, OUTPUT_CSV)
        messagebox.showinfo("Готово", f"Файл {OUTPUT_CSV} сохранён")
