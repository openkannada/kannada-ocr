# Data card

This card covers the evaluation sets, the text corpus, the fonts and the synthetic data. The benchmark and corpus were built on 2026-11-15 and 2026-11-16, and the training lines on 2026-11-16 and 2026-11-17. The pipeline logs every network request to `data/sources/requests.jsonl`. The copy committed as `sources/requests.jsonl` was taken after the benchmark build and the OFL font download, so it ends on 2026-11-15 and leaves out the KaGaPa archive and the later Wikisource fetches for training lines. None of the data files are committed; the commands in the README rebuild them.

## Evaluation sets

| Set | Level | Items | Test / dev | Groups | Reference characters | License |
|---|---|---|---|---|---|---|
| `mile-lines` | line | 8272 | 6295 / 1977 | 32 books | 397,863 | none stated |
| `mile-pages` | page | 250 | 190 / 60 | 32 books | 405,885 | none stated |
| `degraded-words` | word | 1685 | 1685 / 0 | 1 book | 15,490 | Apache-2.0 |
| `wikisource-old` | page | 176 | 144 / 32 | 22 books, 1868 to 1948 | 193,990 | tagged public domain on Commons |

Each set is a Hugging Face ImageFolder: `images/*.png` (grayscale) and `metadata.jsonl` with `file_name`, `id`, `text`, `level`, `group`, `split`, `source` and `license`. The `wikisource-old` rows also carry `year`, `quality` and `image_url`.

### Splits

Splits are by book, so no book has pages in both splits. The `assign_splits` function orders books by a SHA-256 hash of their name and puts the first 20% in `dev`. A model may be tuned on `dev`; results are reported on `test` only.

### mile-lines and mile-pages: modern print

- Source: https://github.com/MILE-IISc/Kannada-OCR-test-images-with-ground-truth, commit `53cbdf90e1c39130b663d7f4d1bb28bc0ff0d88c`, cloned and checked out at that commit.
- 250 page scans at 300 dpi from 32 books, picked by MILE (IISc) to include italics, bold, Halegannada verse, letterpress pages with detached vowel signs, English words, tables, broken and merged characters. Used in the Lipi Gnani paper (2020).
- Each page has an XML file with blocks, lines and words, and pixel boxes. Line images are cropped from the page with the line's box plus 6 pixels. About 30% of words (14,315 of 48,879) have no rows and zero columns; their lines take the columns of their block.
- **License: the repository has no LICENSE file and the README states none.** MILE's other datasets are Apache-2.0, but this one is not marked. Use it for local evaluation only until MILE confirms the terms. Do not redistribute its images or text.
- Predictions on `mile-lines` and `mile-pages` are not committed, since OCR output of these pages nearly reproduces their text. The committed summary files hold only scores.

### degraded-words: real degradation

- Source: https://github.com/MILE-IISc/DegradedWordsKannada, commit `85492e0ae0bd7ea30d7e479aca90bf9253455863`. Apache-2.0.
- 1685 word images from old books with split characters, from the NCC 2019 papers by Shiva Kumar and Ramakrishnan. All are `test`.
- The GitHub listing shows 1000 files because the web view truncates; the ground-truth file lists 1685, and all 1685 images exist.

### wikisource-old: old print

- Source: Kannada Wikisource. The builder lists every index in `Category:Index_Validated` and `Category:Index_Proofread` (56 books), keeps books whose index gives a year of 1950 or earlier (22 books, 1868 to 1948), and checks the scan's license on its Commons file page. All 22 are tagged public domain on Commons, with generic templates such as "author's life plus 70 years". The tags were not checked independently, and some look wrong: Yugaantara (V. K. Gokak), ಹಳ್ಳಿಯ ಚಿತ್ರಗಳು (Gorur Ramaswamy Iyengar), and ರಮಾನಂದ and ಸುಶೀಲೆ (Nanjanagudu Tirumalamba) are by authors who died after 1965, so they may still be in copyright in India. The set is used only for local evaluation: no image is committed, and neither is OCR output of these pages.
- From each book it takes 8 pages of quality 3 (proofread) or 4 (validated), spread evenly and skipping the first and last 5% of pages.
- The text is the visible text of the rendered page (`/wiki/ಪುಟ:...`): running header, body and footnotes. Block elements become line breaks. References markers, hidden elements and styles are dropped. Wikisource transcribers join printed lines into paragraphs, so this set is scored at page level only.
- The image is the thumbnail that the page view itself shows, from `thumb.wikimedia.org`: 1280 pixels wide for 80 pages, 960 for 46 and 500 for 50.
- The builder writes the list of books, years, authors, licenses and splits to `data/bench/wikisource-old/books.json`; a copy is committed as `sources/wikisource-books.json`.

### Access rules

- The Wikimedia robots.txt disallows `/w/` and `/api/` for general crawlers, which covers `api.php`. The builder uses only `/wiki/` page views, which robots.txt allows, and no API calls.
- Requests go at most 1 per second per host, with a user agent that names this repository, and are cached so a rebuild makes no new requests.
- `www.kagapa.in/robots.txt` returns an HTML page from a domain parking service, so there are no rules to obey there. The font archive was downloaded once. `kocr fonts` fetches it only with `--kagapa`, and checks its SHA-256 before extracting it.

## Text corpus for rendering

- Kannada Wikipedia: https://huggingface.co/datasets/wikimedia/wikipedia, config `20231101.kn`, 31,437 articles. CC BY-SA 3.0 or 4.0, and GFDL, as the dataset card lists.
- Kannada Wikisource: https://huggingface.co/datasets/wikimedia/wikisource, config `20231201.kn`, 14,980 texts. Public domain, or CC BY-SA 3.0 or 4.0 and GFDL, per work. Pages that start with film-song header fields (ಚಿತ್ರ:, ಗಾಯನ:, ಸಂಗೀತ:, ಸಾಹಿತ್ಯ:) are dropped, since their lyrics are not free.
- Paragraphs are cut at word boundaries into pieces of 12 to 72 characters. A line needs 8 characters and at least 60% Kannada letters. Lines are normalized with kannadi and deduplicated.
- A line that shares any 20-character window with a reference in any evaluation set is dropped. Spaces and the invisible characters scoring removes (ZWJ, ZWNJ, zero width space, soft hyphen, word joiner, byte order mark) are removed first. A line shorter than 20 characters is dropped only if a reference line is identical to it; common short phrases such as ಸಾಧ್ಯವಾಯಿತು stay in, since they appear in any Kannada text. In the current build this dropped 1621 Wikipedia lines and 1213 Wikisource lines.
- Result: 400,000 lines, 200,000 from each source, in `data/corpus/lines.tsv`.

## Fonts

`fonts.json` lists the sources. 75 fonts in 29 designs pass the checks below, counting each rendered weight of a variable font. 19 of them, from 13 files in 10 designs, are the OFL fonts that `kocr fonts` downloads by default; the rest come from KaGaPa's archive, which `kocr fonts --kagapa` adds.

- 10 Google Fonts families under OFL-1.1: Akaya Kanadaka, Anek Kannada, Baloo Tamma 2, Benne, Hind Mysuru, Hubballi, Noto Sans Kannada, Noto Serif Kannada, Padyakke Expanded One and Tiro Kannada. Variable fonts render at 2 or 3 weights.
- The KaGaPa Nudi archive (`Fonts.zip`, SHA-256 `e0803a03...93a5`), a free download from Kannada Ganaka Parishat with no license text. Its Unicode fonts (NUDI UNI, NudiUni, Sampige, inchara) are used. The font files are not redistributed.
- **Checks.** A font must shape ಕ + ್ + ಷ into fewer glyphs than code points, which rejects legacy fonts and Unicode fonts without OpenType tables. A sample whose text has a missing glyph, or a blank glyph for a character outside the Kannada block, is skipped.
- **Excluded by eye.** NUDI UNI 12, 17, 19 and 20 draw some letters as other letters (for example ಗ as ದ, ಕ as ಆ). See `fonts.json`.
- **Digits.** 28 Nudi "E" fonts draw Kannada digits as Latin digits, and 26 Nudi "K" fonts and inchara draw Latin digits as Kannada ones. `fonts.digit_style` detects this from the width of the digit 1, and the label is rewritten to the digits the image shows.
- **Legacy Nudi fonts.** 125 of the 191 files in the archive have no Kannada code points; they put Kannada glyphs on Latin ones. 2 more (NudiParijatha) have Kannada code points but no conjunct shaping, and are skipped. With `kocr synth --fonts legacy`, each line is converted to Nudi and Baraha ANSI glyph codes by kannadi's `unicode_to_nudi` (kannadi at commit c786820, as pinned in `crates/kocr-text/Cargo.toml`) and set in the legacy font, while the label stays the Unicode line. Lines kannadi cannot encode exactly (Latin letters, ill-formed aksharas) are never set in a legacy font. kannadi writes every digit as ASCII; "e" fonts draw Latin digits and "k" fonts Kannada ones, and the label follows. 17 files are excluded after a visual check (`legacy_exclude` in `fonts.json`): 11 use other glyph layouts, including "Nudi B Akshara", and 6 draw 1 letter like another. 108 files in 59 designs remain. **The archive has no license, so images made with these fonts are not published.**

## Synthetic data

- Layout: `data/synth/<name>/data/train-NNNNN-of-NNNNN.parquet`, 2000 rows per shard, zstd. Columns: `image` ({bytes, path}, grayscale PNG), `text`, `font`, `design`, `font_license`, `size`, `text_source`, `degradation` (JSON of every parameter). This is the layout the Hugging Face Hub and `datasets` read as an Image feature.
- Each sample picks a text line, a design uniformly (then a file in it), an em size of 24 to 63 pixels, and a profile: `clean` 20%, `print` 40%, `letterpress` 40%.
- `print`: paper tone, skew up to 1 degree, blur, optional downsampling, noise, optional JPEG.
- `letterpress`: ink spread or thinning, broken strokes, uneven ink, darker paper with grain and stains, mirrored bleed-through of another line, skew up to 2.5 degrees, stronger blur and noise, and binarization 15% of the time. If ink wear, including the uneven-density step, would remove more than 40% of the ink, the weight change and breaks are skipped.
- Seeds: sample `i` uses `numpy.random.default_rng([seed, i])`, so any sample can be rebuilt alone.
- `synth-v0`: 50,000 requested, seed 0, 2 processes, `--fonts unicode` (the OFL fonts and KaGaPa's Unicode Nudi fonts, the default at the time), 17,608 of them in OFL fonts: 49,581 lines, 1.34 GB. See `data/synth/synth-v0/stats.json` for counts per profile, design and source.
- `synth-v0-nudi`: 20,000 requested, seed 0, legacy fonts only (`--fonts legacy`): 18,185 lines, 438 MB. 1815 were skipped because kannadi could not encode the line exactly. Not published, as no image made with Nudi fonts is.
- `synth-v1-ofl`: 40,000 requested, seed 1, OFL fonts only (`--fonts ofl`), profile weights 0.1 clean, 0.3 print and 0.6 letterpress: 39,964 lines. It was deleted after packing for `kan_ft_ofl2`, rebuilt from those arguments for `kan_ft_ofl3` with the same 39,964 lines, and deleted again.
- The `font_encoding` column says whether a sample was set in Unicode or in Nudi glyph codes.
- Limits: generation refuses to write into a run directory that has shards, checks free disk before each shard and stops below 15 GB, and stops when everything under `data/synth` reaches 10 GB.

## Training lines from Wikisource

`kocr wslines` builds `data/train/wikisource-lines` (ImageFolder layout). The line images are not published. See `docs/training.md` for the method.

- **Books.** Every proofread Kannada Wikisource book outside the `wikisource-old` test split whose scan has a license on Commons: 33 training books (15 printed 1951 to 2019, 18 undated) and the 4 benchmark dev books. 1 book (ಬೆಳಗಿದ ದೀಪಗಳು) was skipped because no license was found. Each line's row records its page URL, scan URL, license and year.
- **Pages.** Up to 40 proofread pages per training book and 15 per dev book, spread through each book: 1355 pages, fetched through `/wiki/` page views and 1280-pixel scan thumbnails at about 1 request per second per host.
- **Lines.** 27,425 training lines and 936 dev lines, plus 9628 and 299 copies shrunk to 500 pixels of page width, the narrowest of the benchmark scans. Tesseract found 35,640 lines of 8 or more characters; 82% were labeled before the filters below.
- **Filters.** Lines whose reading is far from the proofread text, whose first or last characters disagree, or that end in a hyphen are dropped. So are boxes over 1.5 times their page's median line height (they hold 2 printed lines) and lines sharing 20 characters with any benchmark reference.
- **Fixes.** A zero right after a Kannada letter or vowel sign (598 of 29,283 labels) is a proofreader's stand-in for the anusvara and becomes ಂ.
- **More pages.** `kocr wslines --pages-per-book 120 --name wikisource-lines-120` takes up to 120 pages per training book: 3221 training pages, 70,440 training lines plus 24,640 low-resolution copies, and the same 936 dev lines and 299 copies. 107 labels with letters of another Indic script are dropped when the lines are exported for Tesseract. `kan_ft_ofl2` trained on this set. `kan_ft_ofl3` trained on it without the excluded book in `sources/excluded-training-books.json`: 32 books, 3153 pages, 69,212 lines plus 24,209 copies, and 93,314 lines after the same filter. `sources/wikisource-training-books.json` lists those 32 books with title, author, editor, publisher, year, scan license, page count and line count; the v0.1.0 copy lists the 33 of `kan_ft_ofl2`. Both were written from the cached index pages after the build.
- **Excluded books.** `sources/excluded-training-books.json` lists books never to train on, with the reason. `kocr wslines` skips them and `kocr tesstrain-gt` drops their lines. It holds ಸಂದೇಶದ ಕಥೆಗಳು (2001), whose public-domain tag on Commons is probably wrong, so the list on `main` has 32 books.
- **Noise.** Labels inherit proofreading errors. In 2 visual checks (16 dev lines, 14 training lines), 29 of 30 had the right end points. 5 labels differed from the print by a typo in the Wikisource text, 1 of them a zero for an anusvara, which is now fixed. 1 crop held 2 printed lines, which the height filter now drops.
- **Selection bias.** A line is kept only if Tesseract's start model reads it well enough to align, so the hardest lines are underrepresented.

## Known gaps

- No handwriting and no page layout data. The real training lines come from books printed after 1950 or undated; the only pre-1950 lines are in the 4 dev books, which stay out of training. The 18 old test books have about 1600 more proofread pages that would make good training data only if `wikisource-old` moved to other books.
- Modern digital fonts do not look like pre-1950 metal type. Degradation narrows the gap but does not close it; real old-print lines are needed for training.
- The `wikisource-old` references follow Wikisource conventions (for example a drop capital is a separate line), so page-level error rates include some layout noise.
