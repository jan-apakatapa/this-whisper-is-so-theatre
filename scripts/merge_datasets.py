"""Графическая утилита объединения двух наборов данных в один.

Объединяет два независимо собранных набора (каждый содержит каталог
``segments`` и CSV-файл аннотаций), устраняя конфликты числовых
идентификаторов: все аудиофайлы переименовываются в единую сквозную
последовательность, а пути в аннотациях обновляются автоматически.
"""

import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import pandas as pd


class MergeDatasetApp:
    """Окно объединения двух наборов данных."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Объединение наборов данных")
        self.root.geometry("700x500")

        self.dataset1_path = tk.StringVar()
        self.dataset2_path = tk.StringVar()
        self.output_path = tk.StringVar()

        self.build_ui()

    def build_ui(self) -> None:
        """Создаёт элементы интерфейса."""
        tk.Label(
            self.root,
            text="Объединение наборов данных",
            font=("Arial", 16, "bold"),
        ).pack(pady=10)

        self._folder_row("Набор данных 1:", self.dataset1_path)
        self._folder_row("Набор данных 2:", self.dataset2_path)
        self._folder_row("Каталог результата:", self.output_path)

        self.progress = ttk.Progressbar(self.root, mode="indeterminate")
        self.progress.pack(fill="x", padx=15, pady=10)

        self.status = tk.Label(
            self.root, text="Готово к работе", wraplength=650, justify="left"
        )
        self.status.pack(padx=15, pady=5, fill="both", expand=True)

        tk.Button(
            self.root,
            text="Объединить",
            command=self.merge,
            height=2,
        ).pack(pady=15)

    def _folder_row(self, label: str, var: tk.StringVar) -> None:
        """Создаёт строку «подпись + поле пути + кнопка выбора»."""
        frame = tk.Frame(self.root)
        frame.pack(fill="x", padx=15, pady=5)
        tk.Label(frame, text=label, font=("Arial", 10)).pack(side="left")
        tk.Entry(frame, textvariable=var, width=50).pack(
            side="left", fill="x", expand=True, padx=5
        )
        tk.Button(
            frame, text="Обзор", command=lambda: self.select_folder(var)
        ).pack(side="left")

    def select_folder(self, var: tk.StringVar) -> None:
        """Открывает диалог выбора каталога."""
        folder = filedialog.askdirectory()
        if folder:
            var.set(folder)

    def set_status(self, text: str) -> None:
        """Обновляет строку состояния."""
        self.status.config(text=text)
        self.root.update()

    def find_dataset_files(self, folder: str):
        """Находит CSV-файл и каталог ``segments`` внутри набора данных."""
        csv_file = None
        segments_folder = None
        for item in os.listdir(folder):
            full = os.path.join(folder, item)
            if item.endswith(".csv"):
                csv_file = full
            if item == "segments" and os.path.isdir(full):
                segments_folder = full
        return csv_file, segments_folder

    def _copy_segments(self, segments_dir: str, out_segs: str, start_counter: int):
        """Копирует и сквозным образом переименовывает WAV-файлы набора.

        Аргументы:
            segments_dir: Каталог с исходными WAV-файлами.
            out_segs: Каталог назначения.
            start_counter: Начальное значение сквозного счётчика.

        Возвращает:
            Кортеж ``(отображение_id, следующий_счётчик)``, где отображение
            связывает старые числовые идентификаторы с новыми.
        """
        mapping = {}
        counter = start_counter
        for filename in sorted(os.listdir(segments_dir)):
            if not filename.endswith(".wav"):
                continue
            shutil.copy(
                os.path.join(segments_dir, filename),
                os.path.join(out_segs, f"{counter:04d}.wav"),
            )
            try:
                old_id = int(filename.split(".")[0])
                mapping[old_id] = counter
            except ValueError:
                mapping[counter] = counter
            counter += 1
        return mapping, counter

    def merge(self) -> None:
        """Выполняет объединение наборов данных."""
        d1 = self.dataset1_path.get()
        d2 = self.dataset2_path.get()
        out = self.output_path.get()

        if not d1 or not d2 or not out:
            messagebox.showerror("Ошибка", "Укажите все три каталога")
            return
        if not os.path.exists(d1) or not os.path.exists(d2):
            messagebox.showerror("Ошибка", "Один из наборов данных не найден")
            return

        self.progress.start()
        try:
            self.set_status("Анализ наборов данных...")
            csv1, segs1 = self.find_dataset_files(d1)
            csv2, segs2 = self.find_dataset_files(d2)
            if not all([csv1, segs1, csv2, segs2]):
                raise FileNotFoundError(
                    "В одном из наборов не найден CSV-файл или каталог segments"
                )

            out_segs = os.path.join(out, "segments")
            os.makedirs(out_segs, exist_ok=True)

            self.set_status("Копирование и переименование сегментов...")
            df1, df2 = pd.read_csv(csv1), pd.read_csv(csv2)
            mapping1, counter = self._copy_segments(segs1, out_segs, 1)
            mapping2, counter = self._copy_segments(segs2, out_segs, counter)

            self.set_status("Объединение аннотаций...")
            df1 = df1.copy()
            df1["id"] = df1["id"].map(mapping1)
            df2 = df2.copy()
            df2["id"] = df2["id"].map(mapping2)

            df_merged = pd.concat([df1, df2], ignore_index=True)
            df_merged["audio_path"] = df_merged["id"].apply(
                lambda x: os.path.join("segments", f"{int(x):04d}.wav")
            )
            df_merged = df_merged[["id", "audio_path", "text"]]
            df_merged.to_csv(os.path.join(out, "annotations.csv"), index=False)

            self.progress.stop()
            total = counter - 1
            self.set_status(f"Готово. Всего сегментов: {total}\nРезультат: {out}")
            messagebox.showinfo("Готово", f"Объединено сегментов: {total}")

        except Exception as exc:  # noqa: BLE001 — показываем любую ошибку
            self.progress.stop()
            self.set_status(f"Ошибка: {exc}")
            messagebox.showerror("Ошибка", str(exc))


def main() -> None:
    root = tk.Tk()
    MergeDatasetApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
