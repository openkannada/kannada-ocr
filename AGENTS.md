# Working on kannada-ocr

Instructions for anyone changing this repository, human or AI agent. Read this before writing code or docs.

## What this is

Open OCR for printed Kannada, modern and pre-1950 letterpress: an evaluation benchmark, a synthetic training-data pipeline, baseline results, a Tesseract fine-tuning recipe, and the `kan_ft_ofl2` model it produced. Text handling (normalization, aksharas, scoring) uses the kannadi crate.

## Commands

```sh
cargo build --release                 # the kocr-text binary that Python calls; it looks in $CARGO_TARGET_DIR too
cargo test
cargo fmt --all && cargo clippy --all-targets -- -D warnings
uv sync                               # add --extra vlm for the vision-model baselines
uv run pytest
uv run ruff check . && uv run ruff format --check .

uv run kocr fonts                     # download the OFL fonts, list the usable ones
uv run kocr bench                     # build the evaluation sets under data/bench
uv run kocr corpus                    # cut text lines from the Wikipedia and Wikisource dumps
uv run kocr synth --count 50000       # render and degrade line images in OFL fonts under data/synth
uv run kocr synth --fonts legacy --name synth-v0-nudi --count 20000   # legacy Nudi fonts; needs `kocr fonts --kagapa`; never publish the images
./scripts/run-baselines.sh            # every baseline on the test split
```

`kocr bench` needs the MILE repositories cloned under `data/raw/mile` (see `docs/data-card.md`). `kocr corpus` needs the 2 parquet dumps under `data/raw/text`.

## Architecture

```text
crates/kocr-text/       Rust: scoring and kannadi text tools, as a line-oriented CLI
  src/score.rs          prepare(), edit distance, CER, WER, akshara error rate
  src/cli.rs            normalize, aksharas, score commands
src/kannada_ocr/        Python
  http.py               slow cached client: robots.txt, 1 request per second, request log
  mile.py               MILE-IISc page XML and degraded-word readers
  wikisource.py         proofread Wikisource pages and their scans, through /wiki/ only
  bench.py              builds the 4 evaluation sets
  dataset.py            ImageFolder writer and book-level dev/test splits
  corpus.py             text lines for rendering, with benchmark overlap removed
  fonts.py              font inventory: shaping check, digit style, design groups
  render.py             HarfBuzz shaping plus FreeType rasterizing
  degrade.py            scan and letterpress effects
  synth.py              parallel rendering into parquet shards
  evaluate.py           runs a recognizer, resumes, scores through kocr-text
  report.py             markdown tables of the results, overall and per book
  align.py              labels a printed line with the closest stretch of proofread text
  wslines.py            cuts labeled training lines from Wikisource scans
  tesstrain.py          tesstrain ground truth and multi-page .lstmf packs
  tesstune.py           fine-tunes Tesseract in rounds with early stopping on dev
  text.py               calls the kocr-text binary
  baselines/            Tesseract and mlx-vlm recognizers
fonts.json              font sources, licenses and exclusions, as data
results/                committed scores, and predictions where the set's license allows
sources/                request log and book lists, with licenses
data/                   downloads and generated data; never committed
```

Principles:

- **Data is data.** Font sources and exclusions live in `fonts.json`; benchmark sources and licenses live in each set's metadata and in `docs/data-card.md`.
- **Scoring has 1 implementation**, in Rust on top of kannadi. Python never computes an error rate itself.
- **Labels match pixels.** If a font draws a character differently from its code point (digits in Nudi E and K fonts) or not at all, the label changes or the sample is dropped. A wrong label is worse than a missing sample.
- **The benchmark stays out of training.** Splits are by book, and corpus lines that share 20 characters with any benchmark reference are dropped.

## Code rules

- Small modules with 1 job. No abstraction before a second implementation exists.
- Comments say only what the code cannot: a code point, a non-obvious rule, why a choice was made.
- Every download goes through `http.Client`, which checks robots.txt, waits between requests and logs to `data/sources/requests.jsonl`.
- At most 2 rendering or Tesseract processes by default (`--workers` allows up to 4 on an idle machine). Generated data stays under 10 GB, and generation stops if free disk falls below 15 GB.
- Heavy steps (model runs, rendering batches, Tesseract over a set) run 1 at a time with a time limit, through `heavy` in `scripts/heavy.sh`. Set `HEAVY_SERIAL` to a lock script to share the machine with other jobs; it is called as `HEAVY_SLOTS=1 $HEAVY_SERIAL <repo dir> <command...>` and must run the command once it holds the lock.

## Tests

- Every behavior change gets a test. For each new rule, remove it, confirm a test fails, then restore it.
- Tests that need downloaded fonts skip when the fonts are missing.

## Commits

- Commits are signed. Commit messages and PR bodies carry no AI attribution lines.
- Every PR gets an independent review. Fix the findings, then merge with a squash when CI is green.
- Never commit MILE images, text or OCR output of MILE pages, images rendered with Nudi fonts, or any data whose license does not allow redistribution.

## Writing

This applies to the README, docs, comments and commit messages.

- Plain, short sentences. No hype words.
- No em dashes, no rhetorical questions, no "X, not Y" constructions.
- Digits for numbers. Sentence-case headings. American spelling.
- Say what is true and what is not done.
