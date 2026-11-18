# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

"""Scores every OCR configuration against the hand-transcribed lines.

Usage: uv run python pilots/dictionaries/score.py

Reads transcriptions/<book>.tsv and outputs/<book>/<scan>/<config>/<page>.txt, scores with
kocr-text, and writes results/scores.json and results/scores.md.
"""

from __future__ import annotations

import csv
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

from kannada_ocr import text
from kannada_ocr.linematch import closest_stretch, fold, headword_found, project

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
RESULTS = HERE / "results"


def references(book: str) -> list[dict[str, str]]:
    path = HERE / "transcriptions" / f"{book}.tsv"
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def rates(pairs: list[tuple[str, str, str]]) -> dict[str, float | int]:
    pairs = [p for p in pairs if p[1] or p[2]]
    summary = text.score(pairs)["summary"]
    return {
        "lines": summary["items"],
        "chars": summary["chars"]["reference"],
        "cer": round(summary["cer"], 4),
        "aer": round(summary["aer"], 4),
        "wer": round(summary["wer"], 4),
    }


def score_config(refs: list[dict[str, str]], folder: Path) -> dict[str, object]:
    full, kannada, latin, certain = [], [], [], []
    exact = loose = headwords = kannada_words = kannada_found = 0
    for i, row in enumerate(refs):
        page = (folder / f"{row['page']}.txt").read_text(encoding="utf-8")
        ref = text.normalize([row["text"]])[0]
        hyp = text.normalize([closest_stretch(ref, page)])[0]
        key = f"{row['page']}-{row['column']}-{i}"
        full.append((key, ref, hyp))
        kannada.append((key, project(ref, "kn"), project(hyp, "kn")))
        latin.append((key, project(ref, "la"), project(hyp, "la")))
        if not row["uncertain"]:
            certain.append((key, project(ref, "kn"), project(hyp, "kn")))
        if row["headword"]:
            headwords += 1
            word = text.normalize([row["headword"]])[0]
            exact += headword_found(word, hyp)
            loose += headword_found(fold(word), fold(hyp))
            if project(word, "kn"):
                kannada_words += 1
                kannada_found += headword_found(project(word, "kn"), hyp)
    return {
        "all": rates(full),
        "kannada": rates(kannada),
        "latin": rates(latin),
        "kannada_certain_lines": rates(certain),
        "headwords": headwords,
        "headword_exact": round(exact / headwords, 4) if headwords else None,
        "headword_letters": round(loose / headwords, 4) if headwords else None,
        "headword_kannada": round(kannada_found / kannada_words, 4) if kannada_words else None,
    }


def timings() -> dict[tuple[str, str, str], float]:
    seconds = defaultdict(list)
    with (OUT / "timings.tsv").open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            seconds[(row["book"], row["scan"], row["config"])].append(float(row["seconds"]))
    return {k: round(statistics.mean(v), 1) for k, v in seconds.items()}


def pct(x: float | None) -> str:
    return "" if x is None else f"{100 * x:.1f}%"


def table(results: list[dict[str, object]]) -> str:
    head = (
        "| Book | Scan | Configuration | Lines | Kannada CER | Kannada AER | Latin CER "
        "| All CER | Headword exact | Headword letters | Kannada headword | Seconds per page |\n"
        "|---|---|---|---|---|---|---|---|---|---|---|---|\n"
    )
    rows = []
    for r in results:
        rows.append(
            f"| {r['book']} | {r['scan']} | {r['config']} | {r['all']['lines']} "
            f"| {pct(r['kannada']['cer'])} | {pct(r['kannada']['aer'])} | {pct(r['latin']['cer'])} "
            f"| {pct(r['all']['cer'])} | {pct(r['headword_exact'])} | {pct(r['headword_letters'])} "
            f"| {pct(r['headword_kannada'])} | {r['seconds_per_page']} |"
        )
    return head + "\n".join(rows) + "\n"


def main() -> int:
    seconds = timings()
    results = []
    for book_dir in sorted(OUT.iterdir()):
        if not book_dir.is_dir():
            continue
        refs = references(book_dir.name)
        pages = {r["page"] for r in refs}
        for scan_dir in sorted(book_dir.iterdir()):
            for config_dir in sorted(scan_dir.iterdir()):
                done = {p.stem for p in config_dir.glob("*.txt")}
                if not pages <= done:
                    print(f"skipping {config_dir}: {len(pages - done)} pages not read")
                    continue
                result = {
                    "book": book_dir.name,
                    "scan": scan_dir.name,
                    "config": config_dir.name,
                    **score_config(refs, config_dir),
                    "seconds_per_page": seconds[(book_dir.name, scan_dir.name, config_dir.name)],
                }
                results.append(result)
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "scores.json").write_text(
        json.dumps(results, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (RESULTS / "scores.md").write_text(table(results), encoding="utf-8")
    print(table(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
