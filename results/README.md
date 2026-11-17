# Results

1 folder per model, from `kocr eval`. `<set>.<split>[.n<sample>].json` holds the scores: CER, WER and AER over the set, the edit counts behind them, and CER per book.

`<set>.predictions.jsonl` holds each item's OCR output. Only the `degraded-words` predictions are committed, since that set is Apache-2.0 (MILE DegradedWordsKannada). OCR output of the other sets nearly reproduces their text: the MILE page sets have no stated license, and some `wikisource-old` books are tagged public domain on Commons on grounds this project could not confirm. Their predictions stay local, and `.gitignore` keeps them out.
