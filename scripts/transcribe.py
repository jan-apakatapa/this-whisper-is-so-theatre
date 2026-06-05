"""Графическая утилита черновой расшифровки видеофайлов через faster-whisper.

Утилита последовательно распознаёт речь в видеофайлах выбранного каталога и
сохраняет объединённый результат в текстовый файл. Полученная черновая
расшифровка используется в качестве вспомогательного материала при ручной
разметке набора данных.
"""

import os
import re
import threading
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor, as_completed
from tkinter import messagebox

import torch
from deep_translator import GoogleTranslator
from faster_whisper import WhisperModel

VIDEO_EXTENSIONS = (".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv")
OUTPUT_FILE = "result.txt"
MAX_WORKERS = 2  # ограничение параллельной обработки


class WhisperApp:
    """Окно пакетной расшифровки видеофайлов."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Faster Whisper")
        self.root.geometry("400x280")

        self.folder_path = ""
        self.model_name = tk.StringVar(value="tiny")
        self.model = None
        self.translator = None
        self.output_file = None
        self.lock = threading.Lock()

        self.build_ui()

    def build_ui(self) -> None:
        """Создаёт элементы интерфейса."""
        tk.Label(
            self.root,
            text="Расшифровка видео (Whisper)",
            font=("Arial", 14, "bold"),
        ).pack(pady=10)

        tk.Button(self.root, text="Выбрать папку", command=self.select_folder).pack(
            pady=10
        )
        self.folder_label = tk.Label(self.root, text="Папка не выбрана", fg="gray")
        self.folder_label.pack()

        tk.Label(self.root, text="Модель:", font=("Arial", 10)).pack(pady=5)
        tk.Radiobutton(
            self.root, text="tiny (39 МБ, быстро)",
            variable=self.model_name, value="tiny",
        ).pack()
        tk.Radiobutton(
            self.root, text="small (461 МБ, точнее)",
            variable=self.model_name, value="small",
        ).pack()

        tk.Button(
            self.root, text="Начать расшифровку",
            command=self.start, font=("Arial", 11),
        ).pack(pady=15)

        self.progress_label = tk.Label(self.root, text="", font=("Arial", 10))
        self.progress_label.pack()

    def select_folder(self) -> None:
        """Открывает диалог выбора каталога с видеофайлами."""
        from tkinter import filedialog

        self.folder_path = filedialog.askdirectory()
        if self.folder_path:
            self.folder_label.config(text=self.folder_path, fg="green")

    @staticmethod
    def _extract_number(filename: str) -> float:
        """Извлекает числовой суффикс из имени файла для сортировки."""
        match = re.search(r"_(\d+)\.\w+$", filename)
        return int(match.group(1)) if match else float("inf")

    def get_sorted_files(self):
        """Возвращает список видеофайлов каталога, упорядоченный по номеру."""
        files = [
            f for f in os.listdir(self.folder_path)
            if f.lower().endswith(VIDEO_EXTENSIONS)
        ]
        files.sort(key=self._extract_number)
        return files

    @staticmethod
    def _has_english_chars(text: str) -> bool:
        """Проверяет наличие латинских буквенных последовательностей."""
        return bool(re.search(r"[A-Za-z]{3,}", text))

    def _translate_if_english(self, text: str) -> str:
        """Переводит фрагмент на русский, если в нём обнаружена латиница.

        Whisper иногда «галлюцинирует» англоязычным текстом; такие фрагменты
        переводятся обратно на русский.
        """
        if not self._has_english_chars(text):
            return text
        if self.translator is None:
            try:
                self.translator = GoogleTranslator(source="en", target="ru")
            except Exception:  # noqa: BLE001 — при сбое возвращаем исходный текст
                return text
        try:
            return self.translator.translate(text)
        except Exception:  # noqa: BLE001
            return text

    def _write_atomic(self, text: str) -> None:
        """Дописывает фрагмент в выходной файл с принудительным сбросом буфера."""
        with open(self.output_file, "a", encoding="utf-8") as f:
            f.write(text + " ")
            f.flush()
            os.fsync(f.fileno())

    def _select_device(self):
        """Выбирает устройство и тип вычислений (GPU при наличии CUDA)."""
        if torch.cuda.is_available():
            return "cuda", "float16"
        return "cpu", "int8"

    def transcribe(self) -> None:
        """Выполняет пакетную расшифровку всех видеофайлов каталога."""
        try:
            files = self.get_sorted_files()
            if not files:
                messagebox.showerror("Ошибка", "Видеофайлы не найдены")
                return

            self.progress_label.config(text="Загрузка модели...")
            self.root.update()

            device, compute_type = self._select_device()
            self.model = WhisperModel(
                self.model_name.get(), device=device, compute_type=compute_type
            )

            self.output_file = os.path.join(self.folder_path, OUTPUT_FILE)
            open(self.output_file, "w", encoding="utf-8").close()

            # Результаты буферизуются и записываются строго по порядку файлов,
            # несмотря на параллельную обработку.
            results_buffer = {}
            next_index_to_write = [0]

            def worker(file_idx: int, filename: str):
                filepath = os.path.join(self.folder_path, filename)
                self.progress_label.config(text=f"Обработка: {filename}")
                self.root.update()

                segments_list = []
                try:
                    segments, _ = self.model.transcribe(filepath, language="ru")
                    for segment in segments:
                        text = segment.text.strip()
                        if text:
                            segments_list.append(self._translate_if_english(text))
                except Exception as exc:  # noqa: BLE001
                    segments_list.append(f"[ОШИБКА] {exc}")

                with self.lock:
                    results_buffer[file_idx] = segments_list
                    while next_index_to_write[0] in results_buffer:
                        for fragment in results_buffer[next_index_to_write[0]]:
                            self._write_atomic(fragment)
                        del results_buffer[next_index_to_write[0]]
                        next_index_to_write[0] += 1

            workers = min(MAX_WORKERS, len(files))
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [
                    executor.submit(worker, i, f) for i, f in enumerate(files)
                ]
                done = 0
                for _ in as_completed(futures):
                    done += 1
                    self.progress_label.config(text=f"Готово: {done}/{len(files)}")
                    self.root.update()

            messagebox.showinfo("Готово", f"Результат сохранён:\n{self.output_file}")

        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Ошибка", str(exc))
        finally:
            self.model = None
            self.translator = None

    def start(self) -> None:
        """Запускает расшифровку в фоновом потоке."""
        if not self.folder_path:
            messagebox.showerror("Ошибка", "Выберите папку")
            return
        threading.Thread(target=self.transcribe, daemon=True).start()


def main() -> None:
    root = tk.Tk()
    WhisperApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
