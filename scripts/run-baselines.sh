#!/bin/sh
# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0
# Runs every baseline on the test split, 1 heavy step at a time, each with a time limit.
# The vision model runs on fixed samples, and Tesseract is scored on the same samples and on
# the full sets. The vision model needs mlx on Apple Silicon; VLM= skips it.
set -eu
cd "$(dirname "$0")/.."
. ./scripts/heavy.sh
MODEL=${VLM-mlx-community/dots.mocr-8bit}

eval_on_samples() {
  heavy 1800 uv run kocr eval "$1" mile-lines --limit 600
  heavy 1800 uv run kocr eval "$1" degraded-words --limit 400
  heavy 3600 uv run kocr eval "$1" wikisource-old --limit 60
  heavy 3600 uv run kocr eval "$1" mile-pages --limit 30
}

heavy 1800 cargo build --release --quiet
heavy 1800 uv run kocr eval tesseract mile-lines degraded-words wikisource-old mile-pages
eval_on_samples tesseract
heavy 1800 uv run kocr eval tesseract-psm4 wikisource-old mile-pages
heavy 600 uv run kocr eval tesseract-psm4 wikisource-old --limit 60
heavy 600 uv run kocr eval tesseract-psm4 mile-pages --limit 30
if [ -n "$MODEL" ]; then
  eval_on_samples "$MODEL"
fi
