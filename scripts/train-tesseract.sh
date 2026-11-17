#!/bin/sh
# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0
# Fine-tunes Tesseract's tessdata_best `kan` model with tesstrain, on the CPU. The defaults
# follow the kan_ft_ofl2 recipe; docs/training.md lists the data it needs first. Heavy steps run 1 at a
# time with a time limit. `kocr tesstune` trains in rounds and stops when the dev score stops
# improving; a rerun resumes after the last round.
set -eu
cd "$(dirname "$0")/.."
REPO=$PWD
MODEL=${MODEL:-kan_ft_ofl2}
LEARNING_RATE=${LEARNING_RATE:-stored}
ROUND_LINES=${ROUND_LINES:-10000}
MAX_ROUNDS=${MAX_ROUNDS:-12}
PATIENCE=${PATIENCE:-2}
TRAIN_SECONDS=${TRAIN_SECONDS:-21600}
GT_ARGS=${GT_ARGS:-}
MAKE=${MAKE:-gmake}
TESSTRAIN_COMMIT=405346a3a67d8e4e049341d1da6a4b752e0b8351
TOOL=$REPO/data/tools/tesstrain
DATA=${TESSTRAIN_DATA:-$REPO/data/train/tesstrain/data}
TESSDATA=$REPO/data/tessdata
OUT=$DATA/$MODEL
LOG=$OUT/training.log
export OMP_THREAD_LIMIT=2 PYTHONUNBUFFERED=1

. ./scripts/heavy.sh

LANGDATA="$DATA/langdata/radical-stroke.txt $DATA/langdata/Kannada.unicharset $DATA/langdata/Latin.unicharset"

# tesstrain <seconds> <model name> <make target>; only the unicharset and proto model come from
# tesstrain, since its 1 Tesseract call per line is slow; `kocr tesstrain-pack` writes the .lstmf.
tesstrain() {
  heavy "$1" "$MAKE" -C "$TOOL" -j2 MODEL_NAME="$2" START_MODEL=kan TESSDATA="$TESSDATA" \
    DATA_DIR="$DATA" LANG_TYPE=Indic PY_CMD="$REPO/.venv/bin/python" \
    TESSERACT_LANGDATA="$LANGDATA" "$3"
}

if [ ! -d "$TOOL" ]; then
  git clone --quiet https://github.com/tesseract-ocr/tesstrain.git "$TOOL"
fi
git -C "$TOOL" checkout --quiet "$TESSTRAIN_COMMIT"

if [ ! -d "$DATA/$MODEL-ground-truth" ]; then
  # shellcheck disable=SC2086
  heavy 3600 uv run kocr tesstrain-gt --model "$MODEL" --out "$DATA" $GT_ARGS
fi

# The start model's dictionaries, so the fine-tuned model keeps them.
mkdir -p "$OUT/start"
if [ ! -f "$OUT/$MODEL.wordlist" ]; then
  combine_tessdata -u "$TESSDATA/kan.traineddata" "$OUT/start/kan." > /dev/null
  dawg2wordlist "$OUT/start/kan.lstm-unicharset" "$OUT/start/kan.lstm-word-dawg" "$OUT/$MODEL.wordlist"
  dawg2wordlist "$OUT/start/kan.lstm-unicharset" "$OUT/start/kan.lstm-number-dawg" "$OUT/$MODEL.numbers"
  dawg2wordlist "$OUT/start/kan.lstm-unicharset" "$OUT/start/kan.lstm-punc-dawg" "$OUT/$MODEL.punc"
fi

if [ ! -f "$OUT/$MODEL.traineddata" ]; then
  tesstrain 1800 "$MODEL" proto-model
fi
# Train on every training line; checkpoints are scored on the dev books, never on test.
heavy 7200 uv run kocr tesstrain-pack --model "$MODEL" --out "$DATA"

status=0
heavy "$TRAIN_SECONDS" uv run kocr tesstune --model "$MODEL" --out "$DATA" \
  --learning-rate "$LEARNING_RATE" --round-lines "$ROUND_LINES" \
  --max-rounds "$MAX_ROUNDS" --patience "$PATIENCE" \
  >> "$LOG" 2>&1 || status=$?
case $status in
  0) tail -n 1 "$LOG" ;;
  142) echo "training reached its time limit; rerun to resume after the last finished round" ;;
  *) echo "training failed with status $status; see $LOG" >&2; exit "$status" ;;
esac
