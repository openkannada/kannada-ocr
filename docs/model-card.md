# Model card: `kan_ft_ofl3`

`kan_ft_ofl3.traineddata` is a Tesseract 5 model for printed Kannada. It is Tesseract's `kan` model from tessdata_best, fine-tuned on real lines from Kannada Wikisource books and on synthetic lines rendered in openly licensed fonts. It reads old letterpress print and broken, faded words better than the stock model, and runs anywhere Tesseract runs.

It is release v0.2.0. It replaces `kan_ft_ofl2` (release v0.1.0), which was trained on 1 more book whose license is in doubt; "Changes from v0.1.0" below has the details.

| | |
|---|---|
| File | `kan_ft_ofl3.traineddata`, 10,683,460 bytes |
| SHA-256 | `a4fc2be41bda405b792dcdf50c9a9ec84a64f241e997a52dedf108d93ee5a922` |
| Engine | Tesseract 5 LSTM (`--oem 1`); tested with Tesseract 5.5.4 |
| Start model | `kan.traineddata` from [tesseract-ocr/tessdata_best](https://github.com/tesseract-ocr/tessdata_best), commit `9ddc24e750eec0994223a9edc3fcb434a2244f3b` |
| License | Apache-2.0 (`LICENSE-MODEL` and `NOTICE`); every training source is credited in "Training data and credits" |
| Trained | 2026-11-18, on an Apple Silicon laptop CPU, with the recipe in `docs/training.md` |
| Download | [kan_ft_ofl3.traineddata](https://github.com/openkannada/kannada-ocr/releases/download/v0.2.0/kan_ft_ofl3.traineddata), release v0.2.0 |

## Use

Download the file, check it, and point Tesseract at it:

```sh
mkdir -p tessdata
curl -L -o tessdata/kan_ft_ofl3.traineddata https://github.com/openkannada/kannada-ocr/releases/download/v0.2.0/kan_ft_ofl3.traineddata
shasum -a 256 tessdata/kan_ft_ofl3.traineddata   # or sha256sum on Linux; must match the SHA-256 above
tesseract page.png out --tessdata-dir tessdata -l kan_ft_ofl3 --oem 1 --psm 4   # old print, 1 column
tesseract page.png out --tessdata-dir tessdata -l kan_ft_ofl3 --oem 1 --psm 3   # pages with 2 columns
tesseract line.png out --tessdata-dir tessdata -l kan_ft_ofl3 --oem 1 --psm 7   # a single line
```

`--psm 4` reads a page as 1 column of text and does better on old books, where drop capitals and ornaments confuse Tesseract's layout analysis. It reads straight across 2-column pages, so use `--psm 3` for those. The model can also be copied into the system `tessdata` folder and used with `-l kan_ft_ofl3`.

## Changes from v0.1.0

- **Training data.** ಸಂದೇಶದ ಕಥೆಗಳು (2001) is left out. Its scan is tagged public domain on Commons, but a book from 2001 is very likely still under copyright, so the tag is probably wrong. v0.1.0 trained on 1659 of its lines; v0.2.0 trains on none. `sources/excluded-training-books.json` lists it, and every other source is the same as for v0.1.0.
- **Training run.** Same recipe, start model and learning rate. Early stopping kept the round at 30,000 lines, against 40,000 for v0.1.0. Mean dev CER was 6.24%, against 6.15%.
- **Accuracy.** v0.2.0 is a little less accurate than v0.1.0: 0.0 to 0.3 points of CER on the shared samples, and 0.1 to 0.7 on the full sets. Its word error rate on degraded words is lower. It still beats stock Tesseract on every set. The table below has all 3 side by side.
- **File.** The model file has a new name and SHA-256. The v0.1.0 file stays available in release v0.1.0.

## Training data

| Source | Lines | License |
|---|---|---|
| Line images cut from proofread pages of 32 Kannada Wikisource books, labeled with the Wikisource text | 93,314 | text: CC BY-SA 3.0 or 4.0 and GFDL; scans: CC BY-SA 4.0 (24 books), CC BY-SA 3.0 (4), tagged public domain on Commons (4) |
| Synthetic lines, text from Kannada Wikipedia and Wikisource, rendered in 10 Google Fonts families | 57,572 | Wikipedia text: CC BY-SA 3.0 or 4.0 and GFDL; Wikisource text: CC BY-SA 3.0 or 4.0 and GFDL, or public domain for some works; fonts: OFL-1.1 |

- **Wikisource lines.** Up to 120 proofread pages from each Kannada Wikisource book that has a license on its Commons scan, is not in the benchmark's `wikisource-old` set, and is not in `sources/excluded-training-books.json`. The books were printed from 1951 to 2019 or are undated. Tesseract found the printed lines, and each line was labeled with the closest stretch of the page's proofread text; lines that matched badly were dropped. About a quarter of the lines are copies shrunk to 500 pixels of page width. `sources/wikisource-training-books.json` lists every book with its title, author, editor, publisher, year, scan license, index page and Commons file.
- **Synthetic lines.** Text lines from the Kannada Wikipedia dump of 2023-11-01 and the Kannada Wikisource dump of 2023-12-01, from the `wikimedia/wikipedia` and `wikimedia/wikisource` datasets on Hugging Face. Each line was rendered with HarfBuzz in 1 of 10 Google Fonts families under OFL-1.1, then damaged to look like a scan or letterpress print. 39,964 of them come from a second run that gave 60% of its lines letterpress damage. `docs/data-card.md` lists the fonts and the damage. These are the same lines v0.1.0 used.
- **Left out.** No Nudi or other KaGaPa font, no page from a benchmark test book, no excluded book, and no corpus line that shares 20 characters with any benchmark reference.
- **Model selection.** After every 10,000 training lines, the model was scored on 600 `mile-lines` dev lines and on the 32 `wikisource-old` dev pages, and the best round was kept. `lstmtraining` also reported its own error on 300 MILE dev lines and 1235 Wikisource lines from the 4 dev books. These are dev books, kept apart from the test books by book. Nothing was trained on them, but they did steer which checkpoint was kept. The MILE page sets have no stated license, so they are not part of this repository.

## Results

Test split of the benchmark in this repository. `kan_ft_ofl3` was measured on 2026-11-18, `kan_ft_ofl2` on 2026-11-17 and the other models on 2026-11-16. "of" rows are a fixed sample, the same for every model: the first N items by SHA-256 of their id. Tesseract 5.5.4 read words with `--psm 8`, lines with `--psm 7` and pages with the mode shown. dots.mocr is `mlx-community/dots.mocr-8bit` (3B parameters), run on an Apple Silicon Mac with mlx-vlm, as the strongest open baseline found. Each cell is CER / WER / AER, in percent.

| Set | Items | Stock `kan` | v0.1.0 `kan_ft_ofl2` | v0.2.0 `kan_ft_ofl3` | dots.mocr |
|---|---|---|---|---|---|
| mile-lines, modern print | 600 of 6295 | 3.8 / 20.2 / 5.7 | 2.8 / 14.6 / 4.1 | 2.8 / 15.4 / 4.2 | **2.0 / 11.8 / 3.1** |
| degraded-words, broken and faded words | 400 of 1685 | 24.4 / 88.7 / 37.3 | **16.7** / 86.2 / **25.9** | 17.0 / **80.3** / 26.1 | 29.1 / 85.0 / 47.9 |
| wikisource-old, 1868 to 1948, psm 4 | 60 of 144 | 8.7 / 45.7 / 12.5 | **5.9 / 36.0 / 8.7** | 6.0 / 36.7 / 8.8 | 7.0 / 37.0 / 10.2 |
| mile-pages, modern pages, psm 3 | 30 of 190 | 7.3 / 31.0 / 10.0 | 5.4 / 24.7 / 7.4 | 5.4 / 24.9 / 7.5 | **4.3 / 13.8 / 5.1** |
| mile-lines | 6295 | 4.2 / 20.4 / 6.3 | 3.1 / 15.3 / 4.7 | 3.2 / 15.8 / 4.8 | |
| degraded-words | 1685 | 24.4 / 86.8 / 38.0 | 17.6 / 85.0 / 26.7 | 18.3 / 84.1 / 27.7 | |
| wikisource-old, psm 4 | 144 | 9.9 / 47.5 / 14.0 | 6.9 / 38.3 / 10.1 | 7.1 / 38.9 / 10.3 | |
| mile-pages, psm 3 | 190 | 7.2 / 27.9 / 9.6 | 5.6 / 22.3 / 7.5 | 5.7 / 22.8 / 7.6 | |

How the numbers are measured:

- Reference and output are both put in the canonical form of kannadi's [Kannada text normalization profile](https://github.com/openkannada/kannadi/blob/main/NORMALIZATION.md), and ZWJ, ZWNJ and the other invisible characters of its rule S2 are removed, so encoding differences that render the same are not errors.
- CER is the character edit distance summed over the set, divided by the reference length. WER is the same over whitespace-separated words, and AER over kannadi aksharas, so a wrong conjunct counts once.
- Page sets also count reading order and transcription conventions, such as a drop capital written as its own line, so line and word sets are the cleaner measure of recognition.
- The `mile-lines` and `mile-pages` sets come from MILE (IISc), `degraded-words` from MILE's DegradedWordsKannada (Apache-2.0), and `wikisource-old` from 22 books on Kannada Wikisource that are tagged public domain on Commons. `docs/data-card.md` has the sources and splits. `uv run kocr report` rebuilds this table from the files in `results/`.
- A page took about 1.2 seconds with `kan_ft_ofl3` and 39 seconds with dots.mocr on the same Mac.
- Part of the gap between v0.1.0 and v0.2.0 may be run-to-run variance, but that is not measured: the recipe was not repeated with another seed. At 30,000 lines v0.2.0 scored 6.24% on dev against 6.33% for v0.1.0; v0.1.0 then improved to 6.15% at 40,000 lines, and v0.2.0 did not.

## Limits

- **Modern print.** dots.mocr is better on modern books, on lines (2.0% against 2.8%) and on pages (4.3% against 5.4%). By book, `kan_ft_ofl3` beats it on 8 of 26 MILE line books and on 6 of 19 page books.
- **The oldest books.** On the 1868 Canarese selections it gets 10.8% against 3.4% for dots.mocr, and on ಇಂದ್ರವಜ್ರ 15.0% against 7.9%. It beats stock Tesseract on 17 of the 18 old-print test books and ties on the 18th, and beats dots.mocr on 11 of 18.
- **Similar sources.** Its Wikisource training lines share typefaces and transcription conventions with the `wikisource-old` test books, though no test book was used. Part of its old-print gain may come from that match.
- **Layout.** It has Tesseract's layout analysis. Tables, verse set in columns, marginal notes and mixed scripts are not handled well, and English words were a small part of its training.
- **Dictionaries.** Its word, number and punctuation lists are the stock `kan` lists, unchanged.

## License

The model file is released under the Apache License 2.0, the license of the `kan` model it starts from. It is a modified version of that model: the LSTM network was trained further and the character set was extended with ಋ, ಙ, ಽ and other characters seen in training. The full text is in `LICENSE-MODEL`, and `NOTICE` says what changed. Anyone who redistributes the model should include both; the release attaches them next to the model file.

The file contains no training text or images: its word, number and punctuation lists are identical to stock `kan`'s, and the rest is network weights and a character set. Training on openly licensed text and releasing the weights under a permissive license is standard practice: Tesseract's own models and BERT were trained on web and Wikipedia text and ship under Apache-2.0. Every training source is credited below with its license.

## Training data and credits

All of the material below was used as training data for the network weights of `kan_ft_ofl3` (v0.2.0), and none of it is copied into the model file. It was changed for training: scans were cut into line images, some of them downscaled; texts were normalized with kannadi and split into lines, and some lines were rendered in fonts and degraded to look like print.

| Source | License | Used for |
|---|---|---|
| Kannada Wikisource transcriptions, by its contributors | CC BY-SA 3.0 or 4.0 and GFDL | labels of the real lines; text of synthetic lines |
| Scans of 32 books on Wikimedia Commons, by their authors, publishers and uploaders | CC BY-SA 4.0 (24 books), CC BY-SA 3.0 (4), public-domain tag (4) | images of the real lines |
| Kannada Wikipedia text, by its contributors | CC BY-SA 3.0 or 4.0 and GFDL | text of synthetic lines |
| 10 font families from Google Fonts | OFL-1.1 | rendering synthetic lines |
| Tesseract `kan` model, tessdata_best | Apache-2.0 | the start model |
| Tesseract langdata_lstm: Kannada and Latin character sets, radical-stroke table | Apache-2.0 | building the character set |

- Kannada Wikisource contributors, for the proofread transcriptions, under [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) or [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) and the [GFDL](https://www.gnu.org/licenses/fdl-1.3.html).
- The authors, editors and publishers of the 32 training books, and the uploaders of their scans on Wikimedia Commons, under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) or a public-domain tag. [`sources/wikisource-training-books.json`](https://github.com/openkannada/kannada-ocr/blob/v0.2.0/sources/wikisource-training-books.json) gives each book's title, author, editor, publisher and license, and links its Commons file page, which names the uploader. 1 book, ಸಂತಾಪಕ, names no author on its index page, and ಕುಕ್ಕಿಲ ಸಂಪುಟ names its editor, M. Prabhakara Joshy.
- Kannada Wikipedia and Kannada Wikisource contributors, for text of the synthetic lines, under [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) or [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) and the [GFDL](https://www.gnu.org/licenses/fdl-1.3.html), or in the public domain for some Wikisource works.
- The Tesseract OCR project, for the `kan` start model and the langdata_lstm character sets, under [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0).
- The designers of Akaya Kanadaka, Anek Kannada, Baloo Tamma 2, Benne, Hind Mysuru, Hubballi, Noto Sans Kannada, Noto Serif Kannada, Padyakke Expanded One and Tiro Kannada, under the [SIL Open Font License 1.1](https://openfontlicense.org). The license covers the fonts; the rendered images are not font software.
- MILE Lab, IISc, for the evaluation sets the results are measured on. These were not used for training, except that dev lines and pages steered which checkpoint was kept; DegradedWordsKannada is under [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0), and the other sets state no license.

## v0.1.0: `kan_ft_ofl2`

Release v0.1.0 holds `kan_ft_ofl2.traineddata` (SHA-256 `8884bf7ddd73aaefd33510198428f01d04ab2aff1de6258ec8ace4cbba248b5d`). It was trained the same way on 33 books, including 1659 lines of ಸಂದೇಶದ ಕಥೆಗಳು (2001), whose public-domain tag is probably wrong. The [v0.1.0 copy of `sources/wikisource-training-books.json`](https://github.com/openkannada/kannada-ocr/blob/v0.1.0/sources/wikisource-training-books.json) lists its books. Use v0.2.0 for new work.

## Contact

- Bugs, wrong readings and sample pages: open a GitHub issue in this repository.
- Questions about the model, or documents you cannot share in public: support@luminik.io.
- Partnerships, such as training data or GPU grants: founders@luminik.io.
