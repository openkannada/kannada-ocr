# Kannada OCR

Open OCR for printed Kannada, modern and pre-1950 letterpress:

- `kan_ft_ofl3`, a fine-tuned Tesseract model that reads old print and degraded words better than Tesseract's stock `kan` model (`docs/model-card.md`);
- a benchmark of 4 evaluation sets, with character, word and akshara error rates;
- a synthetic data pipeline that renders Kannada text in openly licensed fonts, and optionally in Nudi fonts, and degrades it to look like scans and letterpress;
- baselines for Tesseract 5 and the dots.mocr vision-language model;
- a CPU recipe that fine-tunes Tesseract's `kan` model on synthetic letterpress lines and real Wikisource lines (`docs/training.md`).

Text handling (normalization, akshara segmentation) uses the [kannadi](https://github.com/openkannada/kannadi) crate.

## The model

Download `kan_ft_ofl3.traineddata` from the [v0.2.0 release](https://github.com/openkannada/kannada-ocr/releases/tag/v0.2.0), check it, and point Tesseract at it:

```sh
mkdir -p tessdata
curl -L -o tessdata/kan_ft_ofl3.traineddata https://github.com/openkannada/kannada-ocr/releases/download/v0.2.0/kan_ft_ofl3.traineddata
shasum -a 256 tessdata/kan_ft_ofl3.traineddata   # or sha256sum; a4fc2be41bda405b792dcdf50c9a9ec84a64f241e997a52dedf108d93ee5a922
tesseract page.png out --tessdata-dir tessdata -l kan_ft_ofl3 --oem 1 --psm 4
```

It was tested with Tesseract 5.5.4. Use `--psm 4` for old 1-column books and `--psm 3` for pages set in 2 columns. `docs/model-card.md` covers its training data and their licenses, its scores, its limits and how it was measured. The model file is under Apache-2.0 (`LICENSE-MODEL` and `NOTICE`, both attached to the release; include them if you redistribute the model). The card credits every training source with its license. v0.2.0 replaces `kan_ft_ofl2` (v0.1.0), which was also trained on 1 book whose public-domain tag is probably wrong; the card says what changed.

## Evaluation sets

| Set | What it tests | Test items |
|---|---|---|
| `mile-lines` | modern print, 32 books, line images | 6295 lines |
| `mile-pages` | the same scans as whole pages | 190 pages |
| `degraded-words` | broken and faded words from old books | 1685 words |
| `wikisource-old` | proofread pages of 18 test books printed 1868 to 1948, tagged public domain on Commons (4 more books are dev) | 144 pages |

Splits are by book: 20% of books are `dev`, the rest `test`. Sources, licenses and build details are in [docs/data-card.md](docs/data-card.md). The MILE page sets have no stated license, so they are used for local evaluation only, and no image or text from them is in this repository.

## Metrics

Both texts are normalized with kannadi, ZWJ and ZWNJ are removed, and whitespace is collapsed. Then:

- **CER**: edit distance over Unicode characters, divided by reference length.
- **WER**: the same over whitespace-separated words.
- **AER**: the same over kannadi aksharas. Reading ಸ್ತ್ರೀ as ಸ್ತೀ is 2 character errors and 1 akshara error.

All rates are summed over a set before dividing. The Rust crate `crates/kocr-text` holds the only implementation.

## Results

Test split, from `uv run kocr report`, measured from 2026-11-16 to 2026-11-18. "600 of 6295" rows are a fixed sample shared by every model. Tesseract 5.5.4 uses `kan` from tessdata_best. `kan_ft`, `kan_ft_ofl`, `kan_ft_ofl2` and `kan_ft_ofl3` are that model fine-tuned with the recipe in `docs/training.md`. The `ofl` models use no Nudi fonts; `kan_ft_ofl2` is release v0.1.0, and `kan_ft_ofl3`, trained without 1 doubtful book, is release v0.2.0. dots.mocr is `mlx-community/dots.mocr-8bit`, run with mlx-vlm on an Apple Silicon Mac. "Wrong script" is the share of outputs with letters from another Indic script.

| Set | Items | Model | CER | WER | AER | Wrong script | Seconds per item |
|---|---|---|---|---|---|---|---|
| mile-lines | 6295 | tesseract-5.5.4-kan-best | 4.2% | 20.4% | 6.3% | 0.0% | 0.09 |
| mile-lines | 6295 | tesseract-5.5.4-kan_ft | 3.2% | 15.0% | 4.6% | 0.0% | 0.15 |
| mile-lines | 6295 | tesseract-5.5.4-kan_ft_ofl | 3.2% | 15.8% | 4.8% | 0.0% | 0.14 |
| mile-lines | 6295 | tesseract-5.5.4-kan_ft_ofl2 | 3.1% | 15.3% | 4.7% | 0.0% | 0.14 |
| mile-lines | 6295 | tesseract-5.5.4-kan_ft_ofl3 | 3.2% | 15.8% | 4.8% | 0.0% | 0.14 |
| mile-lines | 600 of 6295 | dots.mocr-8bit | 2.0% | 11.8% | 3.1% | 0.7% | 2.23 |
| mile-lines | 600 of 6295 | dots.mocr-8bit (telugu_as_kannada) | 2.0% | 11.8% | 3.0% | 0.5% | 2.23 |
| mile-lines | 600 of 6295 | tesseract-5.5.4-kan-best | 3.8% | 20.2% | 5.7% | 0.0% | 0.09 |
| mile-lines | 600 of 6295 | tesseract-5.5.4-kan_ft | 2.8% | 14.5% | 4.1% | 0.0% | 0.15 |
| mile-lines | 600 of 6295 | tesseract-5.5.4-kan_ft_ofl | 2.8% | 15.0% | 4.2% | 0.0% | 0.14 |
| mile-lines | 600 of 6295 | tesseract-5.5.4-kan_ft_ofl2 | 2.8% | 14.6% | 4.1% | 0.0% | 0.14 |
| mile-lines | 600 of 6295 | tesseract-5.5.4-kan_ft_ofl3 | 2.8% | 15.4% | 4.2% | 0.0% | 0.14 |
| degraded-words | 1685 | tesseract-5.5.4-kan-best | 24.4% | 86.8% | 38.0% | 0.0% | 0.05 |
| degraded-words | 1685 | tesseract-5.5.4-kan_ft | 18.3% | 82.6% | 26.8% | 0.0% | 0.10 |
| degraded-words | 1685 | tesseract-5.5.4-kan_ft_ofl | 20.7% | 91.9% | 29.5% | 0.0% | 0.10 |
| degraded-words | 1685 | tesseract-5.5.4-kan_ft_ofl2 | 17.6% | 85.0% | 26.7% | 0.0% | 0.10 |
| degraded-words | 1685 | tesseract-5.5.4-kan_ft_ofl3 | 18.3% | 84.1% | 27.7% | 0.0% | 0.10 |
| degraded-words | 400 of 1685 | dots.mocr-8bit | 29.1% | 85.0% | 47.9% | 13.5% | 0.53 |
| degraded-words | 400 of 1685 | dots.mocr-8bit (telugu_as_kannada) | 25.2% | 84.7% | 39.5% | 5.8% | 0.53 |
| degraded-words | 400 of 1685 | tesseract-5.5.4-kan-best | 24.4% | 88.7% | 37.3% | 0.0% | 0.05 |
| degraded-words | 400 of 1685 | tesseract-5.5.4-kan_ft | 17.4% | 82.0% | 25.8% | 0.0% | 0.10 |
| degraded-words | 400 of 1685 | tesseract-5.5.4-kan_ft_ofl | 20.3% | 88.7% | 28.4% | 0.0% | 0.10 |
| degraded-words | 400 of 1685 | tesseract-5.5.4-kan_ft_ofl2 | 16.7% | 86.2% | 25.9% | 0.0% | 0.10 |
| degraded-words | 400 of 1685 | tesseract-5.5.4-kan_ft_ofl3 | 17.0% | 80.3% | 26.1% | 0.0% | 0.10 |
| wikisource-old | 144 | tesseract-5.5.4-kan-best | 12.6% | 51.5% | 16.7% | 0.0% | 1.92 |
| wikisource-old | 144 | tesseract-5.5.4-kan-best-psm4 | 9.9% | 47.5% | 14.0% | 0.0% | 1.82 |
| wikisource-old | 144 | tesseract-5.5.4-kan_ft | 9.5% | 41.2% | 12.5% | 0.0% | 1.28 |
| wikisource-old | 144 | tesseract-5.5.4-kan_ft-psm4 | 7.0% | 37.5% | 10.0% | 0.0% | 1.26 |
| wikisource-old | 144 | tesseract-5.5.4-kan_ft_ofl | 9.4% | 41.6% | 12.4% | 0.0% | 1.28 |
| wikisource-old | 144 | tesseract-5.5.4-kan_ft_ofl-psm4 | 6.9% | 38.2% | 10.0% | 0.0% | 1.25 |
| wikisource-old | 144 | tesseract-5.5.4-kan_ft_ofl2 | 9.5% | 42.2% | 12.6% | 0.0% | 1.26 |
| wikisource-old | 144 | tesseract-5.5.4-kan_ft_ofl2-psm4 | 6.9% | 38.3% | 10.1% | 0.0% | 1.26 |
| wikisource-old | 144 | tesseract-5.5.4-kan_ft_ofl3 | 9.6% | 42.3% | 12.7% | 0.0% | 1.28 |
| wikisource-old | 144 | tesseract-5.5.4-kan_ft_ofl3-psm4 | 7.1% | 38.9% | 10.3% | 0.0% | 1.26 |
| wikisource-old | 60 of 144 | dots.mocr-8bit | 7.0% | 37.0% | 10.2% | 0.0% | 39.39 |
| wikisource-old | 60 of 144 | tesseract-5.5.4-kan-best | 11.4% | 50.6% | 15.7% | 0.0% | 1.87 |
| wikisource-old | 60 of 144 | tesseract-5.5.4-kan-best-psm4 | 8.7% | 45.7% | 12.5% | 0.0% | 1.66 |
| wikisource-old | 60 of 144 | tesseract-5.5.4-kan_ft | 8.3% | 39.5% | 11.1% | 0.0% | 1.23 |
| wikisource-old | 60 of 144 | tesseract-5.5.4-kan_ft-psm4 | 5.8% | 35.1% | 8.6% | 0.0% | 1.20 |
| wikisource-old | 60 of 144 | tesseract-5.5.4-kan_ft_ofl | 8.3% | 39.7% | 11.1% | 0.0% | 1.23 |
| wikisource-old | 60 of 144 | tesseract-5.5.4-kan_ft_ofl-psm4 | 5.8% | 35.7% | 8.6% | 0.0% | 1.20 |
| wikisource-old | 60 of 144 | tesseract-5.5.4-kan_ft_ofl2 | 8.4% | 40.6% | 11.4% | 0.0% | 1.21 |
| wikisource-old | 60 of 144 | tesseract-5.5.4-kan_ft_ofl2-psm4 | 5.9% | 36.0% | 8.7% | 0.0% | 1.19 |
| wikisource-old | 60 of 144 | tesseract-5.5.4-kan_ft_ofl3 | 8.4% | 40.6% | 11.3% | 0.0% | 1.24 |
| wikisource-old | 60 of 144 | tesseract-5.5.4-kan_ft_ofl3-psm4 | 6.0% | 36.7% | 8.8% | 0.0% | 1.20 |
| mile-pages | 190 | tesseract-5.5.4-kan-best | 7.2% | 27.9% | 9.6% | 0.0% | 3.04 |
| mile-pages | 190 | tesseract-5.5.4-kan-best-psm4 | 12.1% | 32.2% | 14.7% | 0.0% | 3.24 |
| mile-pages | 190 | tesseract-5.5.4-kan_ft | 5.7% | 22.2% | 7.5% | 0.0% | 2.09 |
| mile-pages | 190 | tesseract-5.5.4-kan_ft-psm4 | 10.7% | 26.8% | 12.7% | 0.0% | 2.04 |
| mile-pages | 190 | tesseract-5.5.4-kan_ft_ofl | 5.6% | 22.6% | 7.5% | 0.0% | 2.07 |
| mile-pages | 190 | tesseract-5.5.4-kan_ft_ofl-psm4 | 10.6% | 27.4% | 12.6% | 0.0% | 2.05 |
| mile-pages | 190 | tesseract-5.5.4-kan_ft_ofl2 | 5.6% | 22.3% | 7.5% | 0.0% | 2.04 |
| mile-pages | 190 | tesseract-5.5.4-kan_ft_ofl2-psm4 | 10.6% | 27.0% | 12.7% | 0.0% | 2.04 |
| mile-pages | 190 | tesseract-5.5.4-kan_ft_ofl3 | 5.7% | 22.8% | 7.6% | 0.0% | 2.07 |
| mile-pages | 190 | tesseract-5.5.4-kan_ft_ofl3-psm4 | 10.7% | 27.6% | 12.7% | 0.0% | 2.05 |
| mile-pages | 30 of 190 | dots.mocr-8bit | 4.3% | 13.8% | 5.1% | 0.0% | 83.34 |
| mile-pages | 30 of 190 | tesseract-5.5.4-kan-best | 7.3% | 31.0% | 10.0% | 0.0% | 3.26 |
| mile-pages | 30 of 190 | tesseract-5.5.4-kan-best-psm4 | 11.5% | 32.3% | 13.9% | 0.0% | 3.34 |
| mile-pages | 30 of 190 | tesseract-5.5.4-kan_ft | 5.5% | 24.5% | 7.5% | 0.0% | 2.18 |
| mile-pages | 30 of 190 | tesseract-5.5.4-kan_ft-psm4 | 9.9% | 26.5% | 11.6% | 0.0% | 2.11 |
| mile-pages | 30 of 190 | tesseract-5.5.4-kan_ft_ofl | 5.4% | 24.8% | 7.4% | 0.0% | 2.15 |
| mile-pages | 30 of 190 | tesseract-5.5.4-kan_ft_ofl-psm4 | 9.7% | 26.6% | 11.5% | 0.0% | 2.11 |
| mile-pages | 30 of 190 | tesseract-5.5.4-kan_ft_ofl2 | 5.4% | 24.7% | 7.4% | 0.0% | 2.11 |
| mile-pages | 30 of 190 | tesseract-5.5.4-kan_ft_ofl2-psm4 | 9.7% | 26.5% | 11.6% | 0.0% | 2.11 |
| mile-pages | 30 of 190 | tesseract-5.5.4-kan_ft_ofl3 | 5.4% | 24.9% | 7.5% | 0.0% | 2.15 |
| mile-pages | 30 of 190 | tesseract-5.5.4-kan_ft_ofl3-psm4 | 9.8% | 27.0% | 11.7% | 0.0% | 2.12 |

Notes:

- Tesseract's 4.2% CER on MILE lines is close to the 95.4% character accuracy that Lipi Gnani reported on the same pages with a different alignment method.
- Tesseract reads pages with automatic layout (`--psm 3`), because 3 MILE books are set in 2 columns. Mode 4 (the `-psm4` rows) reads across columns, but it handles old print better.
- dots.mocr answers some short lines and many degraded words in Telugu or Tamil script. The `telugu_as_kannada` rows rescore its output with Telugu letters moved to the parallel Kannada code points. They show how much of its error is the wrong script, and are not a fair score.
- Page-level rates also count reading order and transcription conventions, so line and word sets are the cleaner measure of recognition.
- `kan_ft_ofl3` (v0.2.0) beats stock `kan` on every set, by 1.0 to 7.4 points of CER on the shared samples. It is 0.1 to 0.7 points behind `kan_ft_ofl2` (v0.1.0), about the spread between 2 training runs, and its WER on degraded words is lower (80.3% against 86.2% on the shared 400). It beats dots.mocr on degraded words (17.0% against 29.1%) and, with `--psm 4`, on old print (6.0% against 7.0% on the shared 60 pages), and reads a page about 30 times faster. dots.mocr is better on modern print: 2.0% against 2.8% on lines and 4.3% against 5.4% on pages.
- The old-print lead is uneven. By book, `kan_ft_ofl3` is better than dots.mocr on 11 of 18, and dots.mocr is much better on the oldest type, such as the 1868 Canarese selections (3.4% against 10.8%).
- The fine-tuned models trained on Wikisource lines from later books in similar typefaces, so their old-print gain partly reflects that they have seen similar type and Wikisource's transcription conventions. No test book and no line sharing 20 characters with a benchmark reference was used.
- PaddleOCR-VL 1.5 was dropped after a 4-image spot check in which it wrote Telugu script (3 images) or repeated Tibetan characters (1 image).

## Setup

You need Rust, [uv](https://docs.astral.sh/uv/), Tesseract 5 and Python 3.12 or newer.

```sh
cargo build --release                     # the kocr-text scorer that the Python code calls
uv sync                                   # add --extra vlm on Apple Silicon for the dots.mocr baseline
mkdir -p data/tessdata
curl -L -o data/tessdata/kan.traineddata https://github.com/tesseract-ocr/tessdata_best/raw/9ddc24e750eec0994223a9edc3fcb434a2244f3b/kan.traineddata
```

The MILE sets need 2 clones under `data/raw/mile`, at the commits in the data card:

```sh
git clone https://github.com/MILE-IISc/Kannada-OCR-test-images-with-ground-truth data/raw/mile/Kannada-OCR-test-images-with-ground-truth
git -C data/raw/mile/Kannada-OCR-test-images-with-ground-truth checkout 53cbdf90e1c39130b663d7f4d1bb28bc0ff0d88c
git clone https://github.com/MILE-IISc/DegradedWordsKannada data/raw/mile/DegradedWordsKannada
git -C data/raw/mile/DegradedWordsKannada checkout 85492e0ae0bd7ea30d7e479aca90bf9253455863
```

`kocr corpus` reads the Kannada Wikipedia and Wikisource dumps as `data/raw/text/wikipedia-20231101.kn.parquet` and `data/raw/text/wikisource-20231201.kn.parquet`, from the Hugging Face datasets `wikimedia/wikipedia` (config `20231101.kn`) and `wikimedia/wikisource` (config `20231201.kn`). Save each config's train split as 1 parquet file under those names.

## Usage

```sh
uv run kocr fonts                         # the OFL fonts; --kagapa adds KaGaPa's Nudi fonts
uv run kocr bench                         # build the evaluation sets
uv run kocr corpus                        # text lines for rendering
uv run kocr synth --name synth-v0 --count 50000
VLM= ./scripts/run-baselines.sh           # Tesseract baselines; leave VLM unset on Apple Silicon to add dots.mocr
uv run kocr report
```

`docs/training.md` has the fine-tuning steps. The synthetic set is written as parquet shards that `datasets.load_dataset("parquet", data_dir=...)` reads with an Image feature. The evaluation sets are ImageFolder directories.

## Status

- Done: the benchmark, the scoring, the synthetic pipeline, and the baselines above.
- Done: legacy (ANSI) Nudi fonts, through kannadi's Unicode to Nudi encoder: `kocr synth --fonts legacy`. 108 of the 125 legacy font files pass a visual check. The KaGaPa archive has no license, so images rendered with its fonts are not published, and neither is `kan_ft`, which was trained on them.
- Done: `kan_ft_ofl2` (v0.1.0) and `kan_ft_ofl3` (v0.2.0), trained with no Nudi fonts, in rounds with early stopping on dev. `kan_ft_ofl3` also leaves out the book in `sources/excluded-training-books.json`.
- Not done: a vision-language model fine-tune, which needs a GPU.

## License

Code: [MIT](LICENSE-MIT) or [Apache-2.0](LICENSE-APACHE), at your option. Copyright 2026 The Open Kannada Authors. Docs, results and source lists: CC BY 4.0. The model file `kan_ft_ofl2.traineddata`: Apache-2.0 (`LICENSE-MODEL`, `NOTICE`); `docs/model-card.md` credits its training sources. Release v0.1.0 was trained with 1 book whose public-domain tag is probably wrong; the card says how the next release drops it. No image from any benchmark or training set is in this repository. `results/` holds OCR output for `degraded-words`, a set under Apache-2.0, and only scores for the other sets; `results/README.md` says why. `NOTICE` credits third-party material, the license texts are in `LICENSES/`, and `REUSE.toml` covers every file. Contributions are welcome under the [DCO](CONTRIBUTING.md). The name Open Kannada is covered by [TRADEMARKS.md](TRADEMARKS.md).

Part of [Open Kannada](https://github.com/openkannada), free and open-source tools that make Kannada work properly on computers.
