#!/bin/sh
# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0
# Scores a fine-tuned Tesseract model, data/tessdata/<lang>.traineddata: first on the dev
# books next to the start model, then on the test sets and fixed samples the baselines use.
# degraded-words has no dev split, so it is scored on test only.
set -eu
cd "$(dirname "$0")/.."
. ./scripts/heavy.sh
LANG_NAME=${1:-kan_ft_ofl2}
FT=tesseract@$LANG_NAME

for lang in kan "$LANG_NAME"; do
  heavy 1800 uv run kocr eval "tesseract@$lang" mile-lines --split dev --limit 600
  heavy 1800 uv run kocr eval "tesseract@$lang" wikisource-old --split dev
  heavy 1800 uv run kocr eval "tesseract-psm4@$lang" wikisource-old --split dev
done

heavy 3600 uv run kocr eval "$FT" mile-lines degraded-words wikisource-old mile-pages
heavy 1800 uv run kocr eval "tesseract-psm4@$LANG_NAME" wikisource-old mile-pages
heavy 1800 uv run kocr eval "$FT" mile-lines --limit 600
heavy 1800 uv run kocr eval "$FT" degraded-words --limit 400
heavy 1800 uv run kocr eval "$FT" wikisource-old --limit 60
heavy 1800 uv run kocr eval "$FT" mile-pages --limit 30
heavy 1800 uv run kocr eval "tesseract-psm4@$LANG_NAME" wikisource-old --limit 60
heavy 1800 uv run kocr eval "tesseract-psm4@$LANG_NAME" mile-pages --limit 30
