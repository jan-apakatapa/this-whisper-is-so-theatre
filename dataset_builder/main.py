"""Точка входа графической утилиты формирования набора данных.

Запуск из корня репозитория:

    python -m dataset_builder.main
"""

import tkinter as tk

from .main_window import MainWindow


def main() -> None:
    root = tk.Tk()
    MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
