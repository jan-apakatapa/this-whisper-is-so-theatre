"""Графическая утилита нормализации текста транскрипций.

Приводит текст к единообразному виду перед сравнением расшифровок: удаляет
слова в верхнем регистре (ремарки, имена действующих лиц), знаки препинания,
приводит к нижнему регистру и убирает лишние пробелы. Та же нормализация
применяется как к эталону, так и к выводу модели, что исключает влияние
оформления на метрики качества.
"""

import os
import re
import string
import tkinter as tk
from tkinter import filedialog, messagebox

FILENAME_PREFIX = "norm_"


def remove_uppercase_words(text: str) -> str:
    """Удаляет слова, состоящие исключительно из заглавных букв.

    В исходных текстах таким образом оформляются ремарки и имена действующих
    лиц, не относящиеся к звучащей речи.
    """
    words = text.split()
    filtered = [w for w in words if not (w.isupper() and w.isalpha())]
    return " ".join(filtered)


def normalize_text(text: str) -> str:
    """Приводит текст к нормализованному виду.

    Удаляет знаки препинания, переводит символы в нижний регистр и сворачивает
    последовательности пробельных символов в одиночные пробелы.
    """
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize(text: str) -> str:
    """Выполняет полную нормализацию: удаление капса и базовая нормализация."""
    return normalize_text(remove_uppercase_words(text))


class NormalizerApp:
    """Окно нормализации текста."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Нормализатор текста")
        self.root.geometry("700x650")
        self.build_ui()

    def build_ui(self) -> None:
        """Создаёт элементы интерфейса."""
        button_frame = tk.Frame(self.root)
        button_frame.pack(padx=8, pady=8, fill="x")
        tk.Button(
            button_frame, text="Загрузить файл", command=self.load_file, width=20
        ).pack(side="left", padx=5)
        tk.Button(
            button_frame, text="Сохранить результат", command=self.save_file, width=20
        ).pack(side="left", padx=5)

        self.status_label = tk.Label(self.root, text="Готово к работе", fg="gray")
        self.status_label.pack(anchor="w", padx=8)

        tk.Label(self.root, text="Исходный текст:").pack(anchor="w", padx=8, pady=2)
        self.text_input = tk.Text(self.root, height=10, width=60)
        self.text_input.pack(padx=8, pady=2)

        tk.Button(self.root, text="Нормализовать", command=self.on_normalize).pack(
            pady=5
        )

        tk.Label(self.root, text="Результат:").pack(anchor="w", padx=8, pady=2)
        self.text_output = tk.Text(self.root, height=10, width=60)
        self.text_output.pack(padx=8, pady=2)

    def load_file(self) -> None:
        """Загружает текст из файла в поле ввода."""
        file_path = filedialog.askopenfilename(
            title="Выберите файл",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not file_path:
            return
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
            self.text_input.delete("1.0", tk.END)
            self.text_input.insert(tk.END, content)
            self.status_label.config(text=f"Загружен: {os.path.basename(file_path)}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Ошибка", f"Не удалось загрузить файл: {exc}")

    def save_file(self) -> None:
        """Сохраняет результат нормализации в файл с префиксом ``norm_``."""
        result_text = self.text_output.get("1.0", tk.END)
        if not result_text.strip():
            messagebox.showwarning("Внимание", "Результат пуст")
            return

        file_path = filedialog.asksaveasfilename(
            title="Сохранить файл",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not file_path:
            return

        base_name = os.path.basename(file_path)
        if FILENAME_PREFIX not in base_name:
            file_path = os.path.join(
                os.path.dirname(file_path), f"{FILENAME_PREFIX}{base_name}"
            )

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(result_text)
            self.status_label.config(text=f"Сохранён: {os.path.basename(file_path)}")
            messagebox.showinfo("Готово", f"Файл сохранён: {os.path.basename(file_path)}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {exc}")

    def on_normalize(self) -> None:
        """Нормализует текст из поля ввода и выводит результат."""
        result = normalize(self.text_input.get("1.0", tk.END))
        self.text_output.delete("1.0", tk.END)
        self.text_output.insert(tk.END, result)


def main() -> None:
    root = tk.Tk()
    NormalizerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
