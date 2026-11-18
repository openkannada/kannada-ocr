# Fine-tuning Tesseract for Kannada

This recipe fine-tunes the `kan` model from tessdata_best on a CPU with tesstrain. It costs nothing to run. Training runs in rounds and stops when the dev score stops improving, or at a wall-clock limit, and a rerun resumes after the last finished round. The defaults build `kan_ft_ofl3`, release v0.2.0. It is the `kan_ft_ofl2` recipe (release v0.1.0) without the books in `sources/excluded-training-books.json`.

## Steps

First follow the setup in the README: the `kocr-text` build, `kan.traineddata` in `data/tessdata`, the MILE clones and the 2 text dumps. Training also needs Tesseract's training tools (`lstmtraining`, `combine_tessdata`, `dawg2wordlist`). Homebrew's `tesseract` includes them; on Linux they need a Tesseract build with the training tools.

```sh
uv run kocr fonts                      # the 10 OFL font families
uv run kocr bench                      # the evaluation sets; their dev books score each round
uv run kocr corpus                     # text lines for rendering
uv run kocr synth --name synth-v0 --count 17700
uv run kocr synth --name synth-v1-ofl --seed 1 --profile-weights 0.1 0.3 0.6 --count 40000
uv run kocr wslines --fetch-only --pages-per-book 120                                 # 1 request per second
uv run kocr wslines --pages-per-book 120 --name wikisource-lines-120                  # Tesseract finds the lines
./scripts/train-tesseract.sh           # ground truth, tesstrain, training in rounds, then data/tessdata/kan_ft_ofl3.traineddata
./scripts/eval-tesseract-ft.sh kan_ft_ofl3   # dev sets next to the start model, then the test sets
uv run kocr report
```

These steps follow the `kan_ft_ofl3` recipe, and the result will be close to it, though not identical. `kan_ft_ofl3` and `kan_ft_ofl2` used the 17,608 OFL lines of a `synth-v0` of 49,581 lines rendered with `--fonts unicode`, which also needs `kocr fonts --kagapa`. `--fonts ofl`, now the default, renders every line in an OFL font, so `--count 17700` gives about as many OFL lines, in different samples, under the same license. `kocr tesstrain-gt` takes every OFL line of each synthetic set.

`train-tesseract.sh` reads these environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `MODEL` | `kan_ft_ofl3` | model name; the result is `data/tessdata/$MODEL.traineddata` |
| `LEARNING_RATE` | `stored` | `lstmtraining` learning rate, or `stored` for the rate stored in the start model |
| `ROUND_LINES` | 10000 | training lines per round; the model is scored on dev after each one |
| `MAX_ROUNDS` | 12 | most rounds to train |
| `PATIENCE` | 2 | stop after this many rounds without a dev gain of 0.1 points of CER |
| `TRAIN_SECONDS` | 21600 | wall-clock limit for 1 run of `kocr tesstune` |
| `GT_ARGS` | none | extra `kocr tesstrain-gt` options; its defaults are `--lines wikisource-lines-120 --synth synth-v0 synth-v1-ofl --kagapa 0` |
| `MAKE` | `gmake` | GNU make 4.2 or newer; `make` on most Linux systems |

The script needs GNU make 4.2 or newer: `brew install make` on macOS gives `gmake`. It clones tesstrain into `data/tools/tesstrain` and checks out commit `405346a3a67d8e4e049341d1da6a4b752e0b8351` (Apache 2.0). `kocr tesstrain-gt` downloads 3 langdata files from `tesseract-ocr/langdata_lstm` at commit `07930fd9f246622c26eb5de794d9212ceac432d3` through the polite HTTP client.

`kan_ft`'s mix needs `GT_ARGS="--lines wikisource-lines --synth synth-v0 --kagapa 6000"`, and before it `kocr fonts --kagapa`, a `synth-v0` rendered with `--fonts unicode`, `synth-v0-nudi` and the 40-page `wikisource-lines`. Its Nudi lines make a model that cannot be published.

## Retraining without excluded books

`sources/excluded-training-books.json` lists books that must not be trained on. It holds ಸಂದೇಶದ ಕಥೆಗಳು (2001), which `kan_ft_ofl2` in release v0.1.0 was trained on; its public-domain tag on Commons is probably wrong. The next release is retrained without it, with the same recipe under a new model name:

```sh
./scripts/train-tesseract.sh   # MODEL defaults to kan_ft_ofl3: ground truth without excluded books, then training in rounds
./scripts/eval-tesseract-ft.sh kan_ft_ofl3
uv run kocr report
```

- The new name matters. `train-tesseract.sh` reuses an existing `$MODEL-ground-truth` folder, and the `kan_ft_ofl2` one still holds the excluded book's lines.
- `kocr tesstrain-gt` drops the lines of excluded books from `wikisource-lines-120`, so the line set does not need to be rebuilt. A rebuild with `kocr wslines --pages-per-book 120 --name wikisource-lines-120` skips those books too.
- It is a heavy run with the same data needs as the steps above: ground truth, packing, then rounds of about 17 minutes each on the Mac used for `kan_ft_ofl2`. Run it when the machine is free. It was run on 2026-11-18 as `kan_ft_ofl3`, released as v0.2.0; "The `kan_ft_ofl3` run" below has the results.
- A new model needs a new release, with its own SHA-256, scores and model card entry. The v0.1.0 release asset stays as published.

## Training data

The defaults, which `kan_ft_ofl3` used. `kan_ft_ofl2` also had the excluded book's 1659 lines, for 94,973 Wikisource lines.

| Source | Lines | Use |
|---|---|---|
| `wikisource-lines-120`: Wikisource lines from books outside the benchmark, less excluded books | all, 93,314 | training |
| `synth-v0` lines in the 10 OFL font families, with scan and letterpress damage | all, 17,608 | training |
| `synth-v1-ofl`, OFL fonts, 60% letterpress damage | all, 39,964 | training |
| Wikisource lines from the benchmark's dev books | all, 1235 | checkpoint evaluation |
| `mile-lines` dev split | 300 sampled | checkpoint evaluation |

`kan_ft` also had 6000 sampled lines in KaGaPa's Unicode Nudi fonts and 6000 in legacy Nudi fonts, and the 40-page Wikisource lines.

No test-split book is used. Wikisource lines that share a 20-character window with any benchmark reference are dropped.

### Wikisource lines

`kocr wslines` takes up to 40 proofread pages (`--pages-per-book`, 120 for `kan_ft_ofl2`) from each Kannada Wikisource book outside the benchmark, and 15 from each benchmark dev book. It fetches each scan at 1280 pixels wide. Tesseract finds the printed lines, and `align.py` labels each one with the stretch of proofread text that is closest to Tesseract's reading by edit distance. Labels start and end between kannadi aksharas, because old Kannada print often breaks a word across lines without a hyphen. A line is dropped if its reading is far from the text, if its first or last characters disagree with the label, or if it ends in a hyphen.

35% of lines also get a copy shrunk to 500 pixels of page width, the narrowest of the `wikisource-old` scans, so the model sees that resolution as well.

The labels are only as good as the proofreading. In a visual check of 16 aligned dev lines, 15 had the right start and end, and 3 carried a typo that was already in the Wikisource text.

### Labels for Tesseract

Labels are normalized with kannadi, then put in the units Tesseract's Kannada unicharset can encode. A virama that is not followed by a consonant gets a ZWNJ after it (U+0CCD U+200C), which is how that unicharset writes an explicit virama; `lstmtraining` cannot encode a bare one. A ZWNJ between a virama and a consonant is dropped, since it cannot be encoded either. In a 400-line smoke test the first rule cut the skipped lines from 21% to 1.3%, mostly English loanwords that end in a consonant. Scoring removes ZWNJ, so neither change alters what is scored.

### From lines to `.lstmf`

tesstrain makes 1 `.lstmf` per line with 1 Tesseract call each, which ran at about 6 lines per second on the Mac used here: 3 hours for this data. `kocr tesstrain-pack` instead writes 400 lines at a time into a multi-page TIFF with 1 WordStr box file, in the format of tesstrain's `generate_wordstr_box.py` plus a page number, and runs Tesseract once per pack. Lines are ordered by a hash of their names, so each pack mixes the sources, and a rerun keeps finished packs. tesstrain still builds the unicharset and the proto model.

## Training

tesstrain merges the start model's unicharset with the new characters, and builds a proto model with the start model's word, number and punctuation lists. The base `kan` model has no ಋ, ಙ or ಽ; fine-tuning adds them. `lstmtraining` continues from the `kan` LSTM with `OMP_THREAD_LIMIT=2` and `--max_image_MB 1000`, and writes a checkpoint every 100 iterations. With `LEARNING_RATE=stored`, the default, it keeps the rate stored in the start model. With a number, it is passed as `--learning_rate` together with `--reset_learning_rate`; without that flag `lstmtraining` ignores `--learning_rate` and keeps the stored rate. `kan_ft` and `kan_ft_ofl` were trained at the stored rate for that reason, and a sweep over 3 rates gave identical models, which is how this was found.

The checkpoint evaluation list holds only dev lines. `lstmtraining` keeps the checkpoint with the lowest training error, which says little about books it has not seen, so `kocr tesstune` trains in rounds instead. After each round it converts the checkpoint to a model and scores it on 600 `mile-lines` dev lines and the 32 `wikisource-old` dev pages in page mode 4. The score is the mean of the 2 CERs. Training stops after `PATIENCE` rounds without a gain, and the best round becomes the model. Rounds are recorded in `tune-stored/rounds.json`, or `tune-lr<rate>/rounds.json` for a set rate, under the model's folder, so a rerun resumes after the last finished round, and a rerun with a higher `MAX_ROUNDS` continues a run that stopped at its round limit.

`kan_ft` was trained before `kocr tesstune` existed, with 1 run of `lstmtraining` to 60,000 lines; its model is the last checkpoint.

## The `kan_ft` run

Run on 2026-11-16 with the script of that day, `MAX_ITERATIONS=60000` and the default sources: 66,661 training lines (37,053 Wikisource, 17,608 OFL, 6000 Unicode Nudi, 6000 legacy Nudi) and 1535 dev lines (1235 Wikisource, 300 MILE). Packing took 167 training and 4 dev `.lstmf` files.

- 60,000 training lines, about 0.9 of an epoch, in 97 minutes with 2 threads: about 10 lines per second.
- 0.3% to 0.9% of lines per 100 were skipped because their label could not be encoded.
- Training BCER fell from 12.6% at 100 lines to about 4.4% at the end.
- Dev BCER, which lstmtraining first reports at 13,400 lines, fell from 6.9% to 6.0%, and dev BWER from 24.7% to 23.2%. It was still falling slowly, so a longer run may help.

The checkpoints take 645 MB and the packs 1.6 GB; both stay under `data/`.

### Results

Dev books, from `uv run kocr report --split dev`, next to the start model:

| Set | Items | `kan` CER | `kan_ft` CER | `kan` WER | `kan_ft` WER |
|---|---|---|---|---|---|
| mile-lines | 600 of 1977 | 5.8% | 3.5% | 27.8% | 18.0% |
| wikisource-old, psm 3 | 32 | 12.4% | 9.8% | 48.2% | 41.6% |
| wikisource-old, psm 4 | 32 | 11.4% | 8.8% | 47.8% | 41.0% |

Test split, on the fixed samples every model shares. The full-set rows are in the README.

| Set | `kan` | `kan_ft` | dots.mocr |
|---|---|---|---|
| mile-lines, 600 lines | 3.8% | 2.8% | **2.0%** |
| degraded-words, 400 words | 24.4% | **17.4%** | 29.1% |
| wikisource-old, 60 pages, psm 4 | 8.7% | **5.8%** | 7.0% |
| mile-pages, 30 pages, psm 3 | 7.3% | 5.5% | **4.3%** |

Where it wins and where it loses:

- It is better than `kan` on every set and on 17 of the 18 old-print test books; the 18th is a tie.
- On degraded words it beats `kan` by 7 points of CER and dots.mocr by 11.7, and it never writes another script.
- On old print it beats dots.mocr on average, but by book only on 11 of 18. dots.mocr is far better on the oldest type: 3.4% against 11.1% on the 1868 Canarese selections, and 7.9% against 15.6% on ಇಂದ್ರವಜ್ರ.
- dots.mocr is still better on modern print, on lines and on pages. By book, `kan_ft` is better on 8 of 26 MILE line books and 6 of 19 MILE page books.
- Its Wikisource training lines come from later books in similar typefaces, with the same transcription conventions as `wikisource-old`, though no test book is used. Part of the old-print gain may come from that match.
- It reads about 30 times faster than dots.mocr on the same Apple Silicon Mac: 1.2 seconds per old-print page against 39.

It was trained with KaGaPa Nudi fonts, whose archive has no license, so it is not published.

## The `kan_ft_ofl` run

`kan_ft_ofl` leaves out both Nudi sources (`--kagapa 0`, now the default), so every training line is Wikisource text or an OFL font, and the model can be released. It was trained like `kan_ft`, with 1 run to 60,000 lines.

| Set | `kan` | `kan_ft` | `kan_ft_ofl` | dots.mocr |
|---|---|---|---|---|
| mile-lines, 600 lines | 3.8% | 2.8% | 2.8% | **2.0%** |
| degraded-words, 400 words | 24.4% | **17.4%** | 20.3% | 29.1% |
| wikisource-old, 60 pages, psm 4 | 8.7% | **5.8%** | **5.8%** | 7.0% |

It matches `kan_ft` on lines and old pages. It loses 2.9 points on degraded words, which are the set closest to the Nudi typefaces.

## The `kan_ft_ofl2` runs

`kan_ft_ofl2` adds more of both kinds of training data and keeps the license of `kan_ft_ofl`:

- Wikisource lines from up to 120 pages per book in place of 40: 94,973 lines from 33 books outside the benchmark, plus 1235 dev lines from the 4 dev books. Labels with letters of another Indic script are dropped, since some proofread pages keep Telugu or Sinhala letters left by old OCR.
- `synth-v1-ofl`: 39,964 lines in the OFL fonts, rendered with `--seed 1 --profile-weights 0.1 0.3 0.6 --fonts ofl`, so 60% of lines get letterpress damage.
- The 17,608 `synth-v0` OFL lines, as before.

That is 152,545 training lines in 382 packs. A sweep trained 3 rounds of 10,000 lines at each learning rate. Mean dev CER, in percent:

| Learning rate | 10,000 lines | 20,000 | 30,000 | mile-lines at 30,000 | wikisource-old at 30,000 |
|---|---|---|---|---|---|
| 0.0001 | 6.86 | 6.47 | 6.39 | 3.73 | 9.06 |
| 0.0003 | 6.53 | 6.40 | 6.39 | 3.62 | 9.17 |
| 0.001 | 7.00 | 6.50 | 6.46 | 3.61 | 9.32 |
| stored in `kan` | 6.71 | 6.41 | 6.33 | 3.69 | 8.96 |

At 30,000 lines the 4 settings are within 0.13 points, about the noise of the dev set. Higher rates help modern lines a little and hurt old print a little. The stored rate was best, so the final run continued it with `LEARNING_RATE=stored`.

That run stopped after 6 rounds. Round 4, at 40,000 lines, was best, with a mean dev CER of 6.15%: 3.59% on `mile-lines` and 8.71% on `wikisource-old`. Rounds 5 and 6 scored 6.20% and 6.19%. Each round of 10,000 lines took about 17 minutes, scoring included.

Test split, on the fixed samples:

| Set | `kan` | `kan_ft` | `kan_ft_ofl` | `kan_ft_ofl2` | dots.mocr |
|---|---|---|---|---|---|
| mile-lines, 600 lines | 3.8% | 2.8% | 2.8% | 2.8% | **2.0%** |
| degraded-words, 400 words | 24.4% | 17.4% | 20.3% | **16.7%** | 29.1% |
| wikisource-old, 60 pages, psm 4 | 8.7% | **5.8%** | **5.8%** | 5.9% | 7.0% |
| mile-pages, 30 pages, psm 3 | 7.3% | 5.5% | 5.4% | 5.4% | **4.3%** |

On the full sets `kan_ft_ofl2` scores 3.1% on `mile-lines`, 17.6% on `degraded-words`, 6.9% on `wikisource-old` in page mode 4 and 5.6% on `mile-pages`.

What the extra data did:

- The letterpress lines won back the degraded words that `kan_ft_ofl` lost without the Nudi fonts, and a little more: 16.7% against 20.3% and 17.4%.
- 2.6 times as many Wikisource lines left old print where it was. On dev, `kan_ft_ofl` and `kan_ft_ofl2` both score about 6.15%. Old print seems limited by something other than the amount of matching text, such as layout or the oldest typefaces.

By book, in page mode 4, `kan_ft_ofl2` is better than `kan` on 17 of the 18 old-print books and ties on the 18th. Against `kan_ft` it is better on 7, worse on 7 and level on 4. All but 1 differ by 0.6 points or less; ಸುಶೀಲೆ is 1.2 points worse. It beats dots.mocr on 11 of 18. Its worst books are the ones `kan_ft` also reads worst:

| Book | `kan` | `kan_ft` | `kan_ft_ofl2` | dots.mocr |
|---|---|---|---|---|
| ಇಂದ್ರವಜ್ರ | 22.8% | 15.6% | 15.7% | **7.9%** |
| ಕರ್ನಾಟಕ ಗತವೈಭವ | 15.6% | 15.6% | 15.6% | 25.0% |
| ಸುಶೀಲೆ | 15.1% | 11.8% | 13.0% | **8.2%** |
| Canarese selections, 1868 | 13.2% | 11.1% | 10.5% | **3.4%** |
| ಪರಂತಪ ವಿಜಯ ೨ | 12.5% | 7.8% | 8.1% | **3.9%** |

On MILE, `kan_ft_ofl2` is better than `kan` on 22 of 26 line books and 16 of 19 page books, and better than dots.mocr on 6 of 26 and 6 of 19. Its weakest MILE book is Kan_169, at 20.5% on pages against 13.0% for dots.mocr.

`kan_ft_ofl2` was released as v0.1.0: it uses no Nudi font, and on every set its CER is lower than `kan_ft`'s or within 0.1 points of it.

## The `kan_ft_ofl3` run

`kan_ft_ofl3` is `kan_ft_ofl2` without ಸಂದೇಶದ ಕಥೆಗಳು (2001), the book in `sources/excluded-training-books.json`. It ran on 2026-11-18 with `MODEL=kan_ft_ofl3 ./scripts/train-tesseract.sh` and everything else at the defaults. `synth-v1-ofl` was rebuilt first with its original arguments and came out at the same 39,964 lines.

- Training lines: 93,314 Wikisource lines from 32 books, 17,608 `synth-v0` OFL lines and 39,964 `synth-v1-ofl` lines, in 378 packs. The Wikisource lines are the 94,973 of `kan_ft_ofl2` less the excluded book's 1659.
- Mean dev CER by round: 6.73% at 10,000 lines, 6.30% at 20,000, 6.24% at 30,000 and 6.27% at 40,000. Training stopped there, and the round at 30,000 lines became the model. `kan_ft_ofl2` scored 6.33% at 30,000 lines and 6.15% at 40,000.
- The whole run, from rebuilding `synth-v1-ofl` to the last test set, took 2 hours 13 minutes.

Test split, on the fixed samples:

| Set | `kan` | `kan_ft_ofl2` | `kan_ft_ofl3` | dots.mocr |
|---|---|---|---|---|
| mile-lines, 600 lines | 3.8% | 2.8% | 2.8% | **2.0%** |
| degraded-words, 400 words | 24.4% | **16.7%** | 17.0% | 29.1% |
| wikisource-old, 60 pages, psm 4 | 8.7% | **5.9%** | 6.0% | 7.0% |
| mile-pages, 30 pages, psm 3 | 7.3% | 5.4% | 5.4% | **4.3%** |

On the full sets `kan_ft_ofl3` scores 3.2% on `mile-lines`, 18.3% on `degraded-words`, 7.1% on `wikisource-old` in page mode 4 and 5.7% on `mile-pages`, 0.1 to 0.7 points above `kan_ft_ofl2`. Its WER on degraded words is lower: 80.3% against 86.2% on the shared 400.

By book, in page mode 4, it is better than `kan` on 17 of the 18 old-print books and ties on the 18th, and better than dots.mocr on 11 of 18. Against `kan_ft_ofl2` it is better on 5, worse on 11 and level on 2. The worse ones are within 0.4 points, and ಇಂದ್ರವಜ್ರ is 0.7 points better. On MILE it is better than `kan` on 24 of 26 line books and 15 of 19 page books.

`kan_ft_ofl3` scores a little lower than `kan_ft_ofl2`. Part of the gap may be run-to-run variance: the learning-rate sweep for `kan_ft_ofl2` gave runs up to 0.13 points of dev CER apart, but the recipe was not repeated with another seed, so this is not measured. `kan_ft_ofl3` is released as v0.2.0 because its training data no longer includes a book whose license is in doubt.

