"""Извлечение и подготовка аудиодорожки средствами ffmpeg."""

import subprocess

# Параметры, требуемые моделью Whisper на входе.
TARGET_SAMPLE_RATE = 16000  # Гц
TARGET_CHANNELS = 1  # моно


def extract_audio(input_path: str, output_wav: str) -> None:
    """Извлекает аудиодорожку из медиафайла и приводит её к формату Whisper.

    Выходной файл записывается как одноканальный (моно) WAV с частотой
    дискретизации 16 кГц.

    Аргументы:
        input_path: Путь к исходному медиафайлу (видео или аудио).
        output_wav: Путь, по которому будет сохранён результат.

    Вызывает:
        subprocess.CalledProcessError: если вызов ffmpeg завершился ошибкой.
    """
    cmd = [
        "ffmpeg",
        "-y",  # перезаписывать выходной файл без запроса
        "-i", input_path,
        "-ac", str(TARGET_CHANNELS),
        "-ar", str(TARGET_SAMPLE_RATE),
        "-vn",  # отбросить видеопоток
        output_wav,
    ]

    subprocess.run(
        cmd,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
