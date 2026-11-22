# Kannada OCR

Open OCR for printed Kannada, built for the old letterpress books that stock OCR reads worst. The fine-tuned Tesseract model `kan_ft_ofl3` gets 6.0% of characters wrong on 60 pages of Kannada books printed 1868 to 1948, against 8.7% for Tesseract's stock `kan` model.

What's here:

- `kan_ft_ofl3`, the model, under Apache-2.0 ([model card](docs/model-card.md));
- a benchmark of 4 evaluation sets, scored by character, word and akshara error rate;
- a synthetic data pipeline that renders Kannada in openly licensed fonts and degrades it to look like scans and letterpress. It can also render legacy Nudi fonts through kannadi's encoder (`kocr synth --fonts legacy`); that archive has no license, so those images and the `kan_ft` model trained on them stay unpublished;
- a CPU recipe that fine-tunes Tesseract on synthetic and real Wikisource lines ([training.md](docs/training.md)).

## Quick start

```sh
mkdir -p tessdata
curl -L -o tessdata/kan_ft_ofl3.traineddata https://github.com/openkannada/kannada-ocr/releases/download/v0.2.0/kan_ft_ofl3.traineddata
shasum -a 256 tessdata/kan_ft_ofl3.traineddata   # a4fc2be41bda405b792dcdf50c9a9ec84a64f241e997a52dedf108d93ee5a922
tesseract page.png out --tessdata-dir tessdata -l kan_ft_ofl3 --oem 1 --psm 4
```

Tested with Tesseract 5.5.4. Use `--psm 4` for old 1-column books and `--psm 3` for pages set in 2 columns. If you redistribute the model, include `LICENSE-MODEL` and `NOTICE` from the release.

## Results

Character error rate on the test split, lower is better, on the samples shared by every model. Tesseract 5.5.4 throughout; dots.mocr is `mlx-community/dots.mocr-8bit`, a vision-language model.

| Set | Stock `kan` | `kan_ft_ofl3` | dots.mocr |
|---|---|---|---|
| Old print 1868 to 1948, 60 Wikisource pages, psm 4 | 8.7% | 6.0% | 7.0% |
| Degraded words from old books, 400 | 24.4% | 17.0% | 29.1% |
| Modern print, 600 MILE lines | 3.8% | 2.8% | 2.0% |
| Modern print, 30 MILE pages, psm 3 | 7.3% | 5.4% | 4.3% |

- `kan_ft_ofl3` beats stock `kan` on every set, by 1.0 to 7.4 points.
- It beats dots.mocr on old print and degraded words and reads a page about 30 times faster; dots.mocr is better on modern print, and much better on the oldest type, such as the 1868 Canarese selections (3.4% against 10.8%).
- dots.mocr answers many degraded words in Telugu or Tamil script (13.5% of outputs).

[docs/results.md](docs/results.md) has every model, every set in full, word and akshara error rates, timings, and how the sets and metrics are defined.

## Evaluation sets

| Set | What it tests | Test items |
|---|---|---|
| `wikisource-old` | proofread pages of 18 books printed 1868 to 1948, public domain on Commons | 144 pages |
| `degraded-words` | broken and faded words from old books | 1,685 words |
| `mile-lines` | modern print, 32 books, line images | 6,295 lines |
| `mile-pages` | the same scans as whole pages | 190 pages |

Splits are by book. Sources, licenses and build details are in the [data card](docs/data-card.md). The MILE sets have no stated license, so they are used for local evaluation only and nothing from them is in this repository.

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

[docs/training.md](docs/training.md) has the fine-tuning steps. The synthetic set is written as parquet shards that `datasets.load_dataset("parquet", data_dir=...)` reads with an Image feature. The evaluation sets are ImageFolder directories.

## Related

- [kannadi](https://github.com/openkannada/kannadi): text normalization and akshara segmentation used by the scorer, and conversion of legacy Nudi text.
- [kannada-ocr-benchmark](https://github.com/openkannada/kannada-ocr-benchmark): an independent benchmark of Kannada OCR systems on modern print, pre-1950 print and degraded scans.
- [kannada-test-corpus](https://github.com/openkannada/kannada-test-corpus): every Kannada test set across Open Kannada, with source and license.
- [openkannada.org/ocr](https://openkannada.org/ocr/): the model's page.

## License

Code: [MIT](LICENSE-MIT) or [Apache-2.0](LICENSE-APACHE), at your option. Copyright 2026 The Open Kannada Authors. Docs, results and source lists: CC BY 4.0. The model files `kan_ft_ofl3.traineddata` (v0.2.0) and `kan_ft_ofl2.traineddata` (v0.1.0): Apache-2.0 (`LICENSE-MODEL`, `NOTICE`); `docs/model-card.md` credits their training sources. v0.1.0 was also trained on 1 book whose public-domain tag is probably wrong, and v0.2.0 leaves it out. No image from any benchmark or training set is in this repository. `results/` holds OCR output for `degraded-words`, a set under Apache-2.0, and only scores for the other sets; `results/README.md` says why. `NOTICE` credits third-party material, the license texts are in `LICENSES/`, and `REUSE.toml` covers every file. Contributions are welcome under the [DCO](CONTRIBUTING.md). The name Open Kannada is covered by [TRADEMARKS.md](TRADEMARKS.md).

Part of [Open Kannada](https://github.com/openkannada), free and open-source tools that make Kannada work properly on computers.
