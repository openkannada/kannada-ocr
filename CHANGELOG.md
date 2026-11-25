# Changelog

## [Unreleased]

### Changed

- The README leads with the result on old print and a 4-line quick start; the full results table moved to `docs/results.md`.

## [0.2.0] - 2026-11-18

### Changed

- New model `kan_ft_ofl3`, trained without 1 book whose public-domain tag is probably wrong (`sources/excluded-training-books.json`). Character error rate on the shared samples: 6.0% on old print with `--psm 4`, 17.0% on degraded words, 2.8% on modern lines and 5.4% on modern pages.

## [0.1.0] - 2026-11-17

### Added

- `kan_ft_ofl2`, a Tesseract 5 model fine-tuned from `kan` on Wikisource lines and synthetic lines in openly licensed fonts, under Apache-2.0.
- The benchmark: 4 evaluation sets, character, word and akshara error rates, and baselines for stock Tesseract and dots.mocr.
- The synthetic data pipeline and the CPU fine-tuning recipe.

[Unreleased]: https://github.com/openkannada/kannada-ocr/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/openkannada/kannada-ocr/releases/tag/v0.2.0
[0.1.0]: https://github.com/openkannada/kannada-ocr/releases/tag/v0.1.0
