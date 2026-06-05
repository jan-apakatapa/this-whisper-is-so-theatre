"""Детектирование речевых сегментов на основе WebRTC VAD.

Модуль разбивает аудиозапись на отдельные речевые фрагменты, пригодные для
последующей ручной разметки и обучения модели распознавания речи.
"""

import os
import wave

import soundfile as sf
import webrtcvad


class SpeechSegmenter:
    """Выделяет речевые сегменты из WAV-файла с помощью WebRTC VAD.

    Алгоритм работы:
        1. Аудиопоток разбивается на фреймы фиксированной длительности, каждый
           из которых классифицируется детектором как речь либо не речь.
        2. Смежные речевые фреймы объединяются в первичные сегменты.
        3. Сегменты, разделённые короткой паузой, сливаются в один.
        4. Слишком короткие сегменты отбрасываются, слишком длинные — делятся
           на части допустимой длительности.
    """

    def __init__(
        self,
        aggressiveness: int = 2,
        frame_ms: int = 30,
        min_duration: float = 1.0,
        max_duration: float = 15.0,
        silence_split: float = 0.7,
    ):
        """Инициализирует сегментатор.

        Аргументы:
            aggressiveness: Агрессивность VAD (0–3); чем выше, тем строже
                детектор относит фрейм к речи.
            frame_ms: Длительность одного фрейма анализа, мс (10, 20 или 30).
            min_duration: Минимальная длительность сегмента, с. Более короткие
                сегменты отбрасываются.
            max_duration: Максимальная длительность сегмента, с. Более длинные
                принудительно делятся на части.
            silence_split: Порог паузы между сегментами, с. Если пауза меньше,
                соседние сегменты объединяются.
        """
        self.vad = webrtcvad.Vad(aggressiveness)
        self.frame_ms = frame_ms
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.silence_split = silence_split

    def read_wav(self, path: str):
        """Считывает PCM-данные и частоту дискретизации из WAV-файла."""
        with wave.open(path, "rb") as wf:
            sample_rate = wf.getframerate()
            pcm = wf.readframes(wf.getnframes())
        return pcm, sample_rate

    def detect(self, wav_path: str):
        """Возвращает список речевых сегментов в виде пар (начало, конец), с."""
        pcm, sample_rate = self.read_wav(wav_path)

        frame_size = int(sample_rate * self.frame_ms / 1000)
        byte_size = frame_size * 2  # 16-битный звук: 2 байта на отсчёт

        # Шаг 1. Классификация каждого фрейма как речь / не речь.
        speech_flags = []
        for i in range(0, len(pcm), byte_size):
            frame = pcm[i:i + byte_size]
            if len(frame) != byte_size:
                continue  # неполный завершающий фрейм пропускаем
            speech_flags.append(self.vad.is_speech(frame, sample_rate))

        # Шаг 2. Формирование первичных сегментов из последовательностей речи.
        segments = []
        start = None
        for idx, is_speech in enumerate(speech_flags):
            t = idx * self.frame_ms / 1000
            if is_speech and start is None:
                start = t
            elif not is_speech and start is not None:
                end = t
                if end - start > 0.2:  # отбрасываем совсем короткие всплески
                    segments.append((start, end))
                start = None

        # Шаг 3. Слияние сегментов, разделённых короткой паузой.
        merged = []
        for seg in segments:
            if not merged:
                merged.append(seg)
                continue
            prev_start, prev_end = merged[-1]
            if seg[0] - prev_end < self.silence_split:
                merged[-1] = (prev_start, seg[1])
            else:
                merged.append(seg)

        # Шаг 4. Фильтрация по длительности и деление длинных сегментов.
        final = []
        for start, end in merged:
            duration = end - start
            if duration < self.min_duration:
                continue
            if duration > self.max_duration:
                cur = start
                while cur < end:
                    part_end = min(cur + self.max_duration, end)
                    final.append((cur, part_end))
                    cur = part_end
            else:
                final.append((start, end))

        return final

    def export_segments(self, wav_path: str, output_dir: str, segments):
        """Сохраняет сегменты в отдельные WAV-файлы.

        Каждому сегменту присваивается четырёхзначный идентификатор
        (``0001.wav``, ``0002.wav`` и т. д.). Файлы записываются в формате
        PCM 16-bit для совместимости с библиотеками воспроизведения.

        Аргументы:
            wav_path: Путь к исходному WAV-файлу.
            output_dir: Каталог для сохранения сегментов.
            segments: Список пар (начало, конец) в секундах.

        Возвращает:
            Список кортежей ``(id, путь, начало, конец)`` для каждого сегмента.
        """
        audio, sr = sf.read(wav_path)
        os.makedirs(output_dir, exist_ok=True)

        files = []
        for idx, (start, end) in enumerate(segments):
            chunk = audio[int(start * sr):int(end * sr)]
            seg_id = f"{idx + 1:04d}"
            out_file = os.path.join(output_dir, f"{seg_id}.wav")

            # subtype='PCM_16' задаётся явно для совместимости с
            # библиотеками воспроизведения на разных платформах.
            sf.write(out_file, chunk, sr, subtype="PCM_16")

            files.append((seg_id, out_file, start, end))

        return files
