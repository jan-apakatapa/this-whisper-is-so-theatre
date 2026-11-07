# Theatre ASR Toolkit

[Русская версия](README.ru.md)

Tools for studying automatic speech recognition (ASR) of Russian theatrical speech with OpenAI's [Whisper](https://arxiv.org/abs/2212.04356) models. The goal is accessible theatre: automatic captions for deaf and hard-of-hearing audiences.

Most ASR benchmarks use clean studio recordings. Theatre audio is different: background music, overlapping lines, emotionally charged delivery and unstable acoustics. This repository covers the full research cycle — building an annotated dataset from real performance recordings, draft transcription, fine-tuning compact Whisper models (`tiny`, `small`), and evaluating recognition quality with WER and CER.

![Data processing pipeline](imgs/pipeline.png)

## Research question

What does Whisper learn when it is fine-tuned on a recording of one theatre production, and can the play script give the same gain without training?

## Corpus

Four annotated productions, with a fifth (Bulgakov's *Flight*) currently being annotated:

| Production | Type | Test set used below |
| --- | --- | --- |
| *Masquerade* (Lermontov), Alexandrinsky Theatre | verse drama | whole recording, 206 segments, 38.1 min |
| *Dream of Autumn* (Fosse), Lensovet Theatre | play with long silences | whole recording, 57 segments, 6.3 min |
| "Show", student theatre Svoy Variant | play about a reality show | final 20%, 151 segments, 14.0 min |
| "Play", student theatre Svoy Variant | contemporary play | final 20%, 196 segments, 17.6 min |

Labels are produced semi-automatically: Whisper large-v3 output is aligned with the play script, and segments that do not match are checked by ear. On *Masquerade* these labels reach 11.5% WER against a fully manual reference, compared with 18.3% for raw Whisper large-v3. A random listening check of 64 segments found 2–4% WER in the labels.

## Protocol

Each training production is split by time: the first 70% for training, 70–80% for validation (the checkpoint is chosen by validation loss), the final 20% for testing. The encoder is frozen and only the decoder is trained (150 steps, learning rate 1e-5, batch 8). Output length is capped by segment duration, and every result is reported as overall WER, median per-segment WER and the number of repetition loops; loops are not mentioned below because whisper-small produced none.

## Results

### Fine-tuning helps only on the same production

Overall WER (%) of whisper-small:

| Model | "Play" (final 20%) | "Show" (final 20%) | *Masquerade* |
| --- | --- | --- | --- |
| no fine-tuning | 17.6 | 19.8 | 24.7 |
| fine-tuned on "Show" | 18.2 | **15.6** | 23.8 |
| fine-tuned on "Play" | **16.0** | 19.6 | 23.7 |

Fine-tuning lowers WER on later scenes of the same production and gives no gain on the neighbouring production of the same theatre, which shares some of the actors (±0.6 points). Words that occur only in the training play make up a 2.1–2.4 times larger share of the words fixed by fine-tuning than of all test words: the model mainly learns character names and plot vocabulary. whisper-tiny also improves on its own production but gets worse on *Masquerade*, mostly through repetition loops.

### A prompt from the play script helps only with names

whisper-small without fine-tuning was given a prompt with the characters' names and up to 25 key words selected from the script ("own"), the prompt of a paired production ("foreign"), or none. Overall WER (%):

| Test set | none | own | foreign |
| --- | --- | --- | --- |
| "Play" | 17.6 | 18.5 | 18.3 |
| "Show" | 19.8 | **17.9** | 19.9 |
| *Masquerade* | 24.7 | 27.8 | 27.6 |
| *Dream of Autumn* | 30.7 | 39.4 | 39.1 |

Paired bootstrap (10,000 resamples, 95% CI, no correction for multiple comparisons):

- "Show": own prompt −1.87 points [−3.11; −0.71], about 45% of the fine-tuning gain on this test; the foreign prompt has no effect.
- "Play" and *Masquerade*: no difference from zero, including a prompt built from Lermontov's original text.
- *Dream of Autumn*: any prompt makes WER worse, +8.7 points [1.75; 17.51] for the own prompt.
- Character names recognised correctly with the own prompt: 37% → 83% on "Show", 53% → 77% on "Play"; key words are recognised as before.

### What changed since the course paper

An earlier version of this README reported that fine-tuning on *Masquerade* increased WER and called it overfitting. Those results came from a random train/test split inside one production, a checkpoint chosen on the test set and audio files that no longer matched their labels. They are withdrawn; the results above use the corrected data and protocol.

## Code status

The components below are the toolkit from the course paper. The thesis code (script alignment, the fine-tuning matrix and the prompt experiment, currently run on Kaggle and Google Colab) is being prepared for release in this repository.

## Components

| Component | Purpose | Stack |
| --- | --- | --- |
| [`dataset_builder`](dataset_builder) | Dataset creation: speech segment detection and manual annotation | WebRTC VAD, Tkinter, ffmpeg |
| [`evaluation`](evaluation) | Evaluation: metrics, error analysis, visualisation | Streamlit, jiwer, Plotly |
| [`scripts/transcribe.py`](scripts/transcribe.py) | Draft transcription of video recordings | faster-whisper, PyTorch |
| [`scripts/normalize_text.py`](scripts/normalize_text.py) | Text normalisation before comparison | Tkinter |
| [`scripts/merge_datasets.py`](scripts/merge_datasets.py) | Merging datasets | pandas, Tkinter |
| [`notebooks/whisper_finetune.ipynb`](notebooks/whisper_finetune.ipynb) | Fine-tuning Whisper | Hugging Face Transformers, Google Colab |

## Getting started

Requires Python 3.9+ and [ffmpeg](https://ffmpeg.org/) installed on your system.

```bash
git clone https://github.com/jan-apakatapa/this-whisper-is-so-theatre.git
cd this-whisper-is-so-theatre

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

Typical workflow:

1. **Build a dataset** from a performance recording:

   ```bash
   python -m dataset_builder.main
   ```

   The tool extracts audio, detects speech segments automatically and opens a manual annotation window. Annotations are saved to `annotations.csv`, segments to `data/segments`.

2. **(Optional) Get a draft transcription** to speed up annotation:

   ```bash
   python scripts/transcribe.py
   ```

3. **Remove empty annotations**:

   ```bash
   python -m dataset_builder.clean_annotations annotations.csv
   ```

4. **Fine-tune the model** with [`notebooks/whisper_finetune.ipynb`](notebooks/whisper_finetune.ipynb) (designed for Google Colab with a GPU).

5. **Evaluate recognition quality**:

   ```bash
   streamlit run evaluation/app.py
   ```

   The app takes three transcriptions (reference, Whisper tiny, Whisper small) and reports WER and CER, error breakdown, hallucination rate and segment-by-segment comparison.

## Project structure

```
this-whisper-is-so-theatre/
├── dataset_builder/             # Dataset creation tool
│   ├── main.py                  #   entry point (GUI)
│   ├── main_window.py           #   main window
│   ├── audio_utils.py           #   audio extraction (ffmpeg)
│   ├── segmenter.py             #   speech segment detection (VAD)
│   ├── annotation_window.py     #   manual segment annotation
│   ├── exporter.py              #   CSV export
│   ├── clean_annotations.py     #   empty annotation cleanup
│   └── models.py                #   data structures
├── evaluation/                  # Evaluation tool (Streamlit)
│   ├── app.py                   #   web app
│   ├── chunking.py              #   text chunking
│   ├── metrics.py               #   WER, CER, error analysis
│   ├── visualization.py         #   result visualisation
│   └── utils.py                 #   helpers
├── scripts/                     # Standalone utilities
│   ├── transcribe.py            #   draft transcription (faster-whisper)
│   ├── normalize_text.py        #   text normalisation
│   └── merge_datasets.py        #   dataset merging
├── notebooks/
│   └── whisper_finetune.ipynb   # Whisper fine-tuning (Google Colab)
├── imgs/
├── requirements.txt
├── LICENSE
└── README.md
```

## Metrics

- **WER (Word Error Rate)** — substitutions, insertions and deletions divided by the number of words in the reference.
- **CER (Character Error Rate)** — the same at character level; more informative for inflected languages such as Russian.

The evaluation tool also reports a detailed error breakdown and the model's **hallucination rate**: the share of generated words that are absent from the audio.

## About the project

Developed as undergraduate research at HSE University, St Petersburg (2026): *Developing an automatic captioning system for theatre performances based on neural speech recognition models*. The work continues as a bachelor's thesis (in progress, defence in spring 2027): *A framework for automatic captioning of theatre performances grounded in the dramatic text and the features of theatrical speech*.

**Author:** Eva Borodaenko
**Supervisor:** Victoria Firsanova, Senior Lecturer, Department of Philology, HSE University

Parts of the code were written with the help of AI coding assistants (GitHub Copilot, Claude Haiku 4.5, GPT-4.1).

## License

See [LICENSE](LICENSE).
