# Model card: `kan_ft_ofl2`

`kan_ft_ofl2.traineddata` is a Tesseract 5 model for printed Kannada. It is Tesseract's `kan` model from tessdata_best, fine-tuned on real lines from Kannada Wikisource books and on synthetic lines rendered in openly licensed fonts. It reads old letterpress print and broken, faded words better than the stock model, and runs anywhere Tesseract runs.

| | |
|---|---|
| File | `kan_ft_ofl2.traineddata`, 10,683,460 bytes |
| SHA-256 | `8884bf7ddd73aaefd33510198428f01d04ab2aff1de6258ec8ace4cbba248b5d` |
| Engine | Tesseract 5 LSTM (`--oem 1`); tested with Tesseract 5.5.4 |
| Start model | `kan.traineddata` from [tesseract-ocr/tessdata_best](https://github.com/tesseract-ocr/tessdata_best), commit `9ddc24e750eec0994223a9edc3fcb434a2244f3b` |
| License | Apache-2.0 (`LICENSE-MODEL` and `NOTICE`); every training source is credited in "Training data and credits" |
| Trained | 2026-11-17, on an Apple Silicon laptop CPU, with the recipe in `docs/training.md` |
| Download | [kan_ft_ofl2.traineddata](https://github.com/openkannada/kannada-ocr/releases/download/v0.1.0/kan_ft_ofl2.traineddata), release v0.1.0 |

## Use

Download the file, check it, and point Tesseract at it:

```sh
mkdir -p tessdata
curl -L -o tessdata/kan_ft_ofl2.traineddata https://github.com/openkannada/kannada-ocr/releases/download/v0.1.0/kan_ft_ofl2.traineddata
shasum -a 256 tessdata/kan_ft_ofl2.traineddata   # or sha256sum on Linux; must match the SHA-256 above
tesseract page.png out --tessdata-dir tessdata -l kan_ft_ofl2 --oem 1 --psm 4   # old print, 1 column
tesseract page.png out --tessdata-dir tessdata -l kan_ft_ofl2 --oem 1 --psm 3   # pages with 2 columns
tesseract line.png out --tessdata-dir tessdata -l kan_ft_ofl2 --oem 1 --psm 7   # a single line
```

`--psm 4` reads a page as 1 column of text and does better on old books, where drop capitals and ornaments confuse Tesseract's layout analysis. It reads straight across 2-column pages, so use `--psm 3` for those. The model can also be copied into the system `tessdata` folder and used with `-l kan_ft_ofl2`.

## Training data

| Source | Lines | License |
|---|---|---|
| Line images cut from proofread pages of 33 Kannada Wikisource books, labeled with the Wikisource text | 94,973 | text: CC BY-SA 3.0 or 4.0 and GFDL; scans: CC BY-SA 4.0 (24 books), CC BY-SA 3.0 (4), tagged public domain on Commons (5) |
| Synthetic lines, text from Kannada Wikipedia and Wikisource, rendered in 10 Google Fonts families | 57,572 | Wikipedia text: CC BY-SA 3.0 or 4.0 and GFDL; Wikisource text: CC BY-SA 3.0 or 4.0 and GFDL, or public domain for some works; fonts: OFL-1.1 |

- **Wikisource lines.** Up to 120 proofread pages from each Kannada Wikisource book that has a license on its Commons scan and is not in the benchmark's `wikisource-old` set. The books were printed from 1951 to 2019 or are undated. Tesseract found the printed lines, and each line was labeled with the closest stretch of the page's proofread text; lines that matched badly were dropped. 24,640 of the lines are copies shrunk to 500 pixels of page width. The v0.1.0 copy of [`sources/wikisource-training-books.json`](https://github.com/openkannada/kannada-ocr/blob/v0.1.0/sources/wikisource-training-books.json) lists every book with its title, author, year, scan license, index page and Commons file. 1 of the 5 books tagged public domain, ಸಂದೇಶದ ಕಥೆಗಳು, was published in 2001, so its tag is probably wrong. It gave 1659 lines, about 1% of the training lines. See "The 2001 book" below.
- **Synthetic lines.** Text lines from the Kannada Wikipedia dump of 2023-11-01 and the Kannada Wikisource dump of 2023-12-01, from the `wikimedia/wikipedia` and `wikimedia/wikisource` datasets on Hugging Face. Each line was rendered with HarfBuzz in 1 of 10 Google Fonts families under OFL-1.1, then damaged to look like a scan or letterpress print. 39,964 of them come from a second run that gave 60% of its lines letterpress damage. `docs/data-card.md` lists the fonts and the damage.
- **Left out.** No Nudi or other KaGaPa font, no page from a benchmark test book, and no corpus line that shares 20 characters with any benchmark reference.
- **Model selection.** After every 10,000 training lines, the model was scored on 600 `mile-lines` dev lines and on the 32 `wikisource-old` dev pages, and the best round was kept. `lstmtraining` also reported its own error on 300 MILE dev lines and 1235 Wikisource lines from the 4 dev books. These are dev books, kept apart from the test books by book. Nothing was trained on them, but they did steer which checkpoint was kept. The MILE page sets have no stated license, so they are not part of this repository.

## Results

Test split of the benchmark in this repository. `kan_ft_ofl2` was measured on 2026-11-17, the other models on 2026-11-16. "of" rows are a fixed sample, the same for every model: the first N items by SHA-256 of their id. Tesseract 5.5.4 read words with `--psm 8`, lines with `--psm 7` and pages with the mode shown. dots.mocr is `mlx-community/dots.mocr-8bit` (3B parameters), run on an Apple Silicon Mac with mlx-vlm, as the strongest open baseline found. Each cell is CER / WER / AER.

| Set | Items | Stock `kan` | `kan_ft_ofl2` | dots.mocr |
|---|---|---|---|---|
| mile-lines, modern print | 600 of 6295 | 3.8 / 20.2 / 5.7 | 2.8 / 14.6 / 4.1 | **2.0 / 11.8 / 3.1** |
| degraded-words, broken and faded words | 400 of 1685 | 24.4 / 88.7 / 37.3 | **16.7** / 86.2 / **25.9** | 29.1 / **85.0** / 47.9 |
| wikisource-old, 1868 to 1948, psm 4 | 60 of 144 | 8.7 / 45.7 / 12.5 | **5.9** / **36.0** / **8.7** | 7.0 / 37.0 / 10.2 |
| mile-pages, modern pages, psm 3 | 30 of 190 | 7.3 / 31.0 / 10.0 | 5.4 / 24.7 / 7.4 | **4.3 / 13.8 / 5.1** |
| mile-lines | 6295 | 4.2 / 20.4 / 6.3 | 3.1 / 15.3 / 4.7 | |
| degraded-words | 1685 | 24.4 / 86.8 / 38.0 | 17.6 / 85.0 / 26.7 | |
| wikisource-old, psm 4 | 144 | 9.9 / 47.5 / 14.0 | 6.9 / 38.3 / 10.1 | |
| mile-pages, psm 3 | 190 | 7.2 / 27.9 / 9.6 | 5.6 / 22.3 / 7.5 | |

How the numbers are measured:

- Reference and output are both normalized with [kannadi](https://github.com/openkannada/kannadi), and ZWJ and ZWNJ are removed, so encoding differences that render the same are not errors.
- CER is the character edit distance summed over the set, divided by the reference length. WER is the same over whitespace-separated words, and AER over kannadi aksharas, so a wrong conjunct counts once.
- Page sets also count reading order and transcription conventions, such as a drop capital written as its own line, so line and word sets are the cleaner measure of recognition.
- The `mile-lines` and `mile-pages` sets come from MILE (IISc), `degraded-words` from MILE's DegradedWordsKannada (Apache-2.0), and `wikisource-old` from 22 books on Kannada Wikisource that are tagged public domain on Commons. `docs/data-card.md` has the sources and splits. `uv run kocr report` rebuilds this table from the files in `results/`.
- A page took about 1.2 seconds with `kan_ft_ofl2` and 39 seconds with dots.mocr on the same Mac.

## Limits

- **Modern print.** dots.mocr is better on modern books, on lines (2.0% against 2.8%) and on pages (4.3% against 5.4%). By book, `kan_ft_ofl2` beats it on 6 of 26 MILE line books.
- **The oldest books.** On the 1868 Canarese selections it gets 10.5% against 3.4% for dots.mocr, and on ಇಂದ್ರವಜ್ರ 15.7% against 7.9%. It beats stock Tesseract on 17 of the 18 old-print test books and ties on the 18th, and beats dots.mocr on 11 of 18.
- **Similar sources.** Its Wikisource training lines share typefaces and transcription conventions with the `wikisource-old` test books, though no test book was used. Part of its old-print gain may come from that match.
- **Layout.** It has Tesseract's layout analysis. Tables, verse set in columns, marginal notes and mixed scripts are not handled well, and English words were a small part of its training.
- **Dictionaries.** Its word, number and punctuation lists are the stock `kan` lists, unchanged.

## License

The model file is released under the Apache License 2.0, the license of the `kan` model it starts from. It is a modified version of that model: the LSTM network was trained further and the character set was extended with ಋ, ಙ, ಽ and other characters seen in training. The full text is in `LICENSE-MODEL`, and `NOTICE` says what changed. Anyone who redistributes the model should include both; the release attaches them next to the model file.

The file contains no training text or images: its word, number and punctuation lists are identical to stock `kan`'s, and the rest is network weights and a character set. Training on openly licensed text and releasing the weights under a permissive license is standard practice: Tesseract's own models and BERT were trained on web and Wikipedia text and ship under Apache-2.0. Every training source is credited below with its license.

## The 2001 book

Release v0.1.0 includes 1659 training lines from ಸಂದೇಶದ ಕಥೆಗಳು by ಶ್ರೀನಿವಾಸ ವರಖೇಡಿ, published in 2001. Its scan is tagged public domain on Commons, but a book from 2001 is very likely still under copyright, so the tag is probably wrong. The next release drops it:

- `sources/excluded-training-books.json` lists the book. `kocr wslines` skips it, and `kocr tesstrain-gt` leaves out its lines even from a line set built before the exclusion.
- `sources/wikisource-training-books.json` on `main` lists the 32 books a new run trains on. The v0.1.0 copy lists the 33 that `kan_ft_ofl2` used.
- The retrain command is in `docs/training.md`, under "Retraining without excluded books". It has not been run yet. Until it is, the v0.1.0 model file stays as released.

## Training data and credits

All of the material below was used as training data for the network weights of `kan_ft_ofl2` (v0.1.0), and none of it is copied into the model file. It was changed for training: scans were cut into line images, some of them downscaled; texts were normalized with kannadi and split into lines, and some lines were rendered in fonts and degraded to look like print.

| Source | License | Used for |
|---|---|---|
| Kannada Wikisource transcriptions, by its contributors | CC BY-SA 3.0 or 4.0 and GFDL | labels of the real lines; text of synthetic lines |
| Scans of 33 books on Wikimedia Commons, by their authors, publishers and uploaders | CC BY-SA 4.0 (24 books), CC BY-SA 3.0 (4), public-domain tag (5) | images of the real lines |
| Kannada Wikipedia text, by its contributors | CC BY-SA 3.0 or 4.0 and GFDL | text of synthetic lines |
| 10 font families from Google Fonts | OFL-1.1 | rendering synthetic lines |
| Tesseract `kan` model, tessdata_best | Apache-2.0 | the start model |
| Tesseract langdata_lstm: Kannada and Latin character sets, radical-stroke table | Apache-2.0 | building the character set |


- Kannada Wikisource contributors, for the proofread transcriptions, under [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) or [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) and the [GFDL](https://www.gnu.org/licenses/fdl-1.3.html).
- The authors, editors and publishers of the 33 training books, and the uploaders of their scans on Wikimedia Commons, under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) or a public-domain tag. The [v0.1.0 copy of `sources/wikisource-training-books.json`](https://github.com/openkannada/kannada-ocr/blob/v0.1.0/sources/wikisource-training-books.json) gives each book's title, author, editor, publisher and license, and links its Commons file page, which names the uploader. 1 book, ಸಂತಾಪಕ, names no author on its index page.
- Kannada Wikipedia and Kannada Wikisource contributors, for text of the synthetic lines, under [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) or [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) and the [GFDL](https://www.gnu.org/licenses/fdl-1.3.html), or in the public domain for some Wikisource works.
- The Tesseract OCR project, for the `kan` start model and the langdata_lstm character sets, under [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0).
- The designers of Akaya Kanadaka, Anek Kannada, Baloo Tamma 2, Benne, Hind Mysuru, Hubballi, Noto Sans Kannada, Noto Serif Kannada, Padyakke Expanded One and Tiro Kannada, under the [SIL Open Font License 1.1](https://openfontlicense.org). The license covers the fonts; the rendered images are not font software.
- MILE Lab, IISc, for the evaluation sets the results are measured on. These were not used for training, except that dev lines and pages steered which checkpoint was kept; DegradedWordsKannada is under [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0), and the other sets state no license.

## Contact

- Bugs, wrong readings and sample pages: open a GitHub issue in this repository.
- Questions about the model, or documents you cannot share in public: support@luminik.io.
- Partnerships, such as training data or GPU grants: founders@luminik.io.
