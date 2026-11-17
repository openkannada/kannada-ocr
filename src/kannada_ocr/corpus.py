# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

"""Text lines for synthetic rendering, cut from the Kannada Wikipedia and Wikisource dumps.

Benchmark text is kept out: a line that shares any 20-character window with a
benchmark reference is dropped, so a model trained on these lines has not read the test pages.
"""

from __future__ import annotations

import random
import re
from collections.abc import Iterable, Iterator
from pathlib import Path

import pyarrow.parquet as pq

from . import text
from .dataset import read_jsonl

SHINGLE = 20
MIN_KANNADA_SHARE = 0.6
SONG_MARKERS = ("ಚಿತ್ರ:", "ಗಾಯನ:", "ಸಂಗೀತ:", "ಸಾಹಿತ್ಯ:")
"""Film song pages carry these header fields; their lyrics are not public domain."""

SOURCES = {
    "wikipedia": "https://huggingface.co/datasets/wikimedia/wikipedia (20231101.kn), "
    "CC BY-SA 3.0 or 4.0, and GFDL",
    "wikisource": "https://huggingface.co/datasets/wikimedia/wikisource (20231201.kn), "
    "public domain, or CC BY-SA 3.0 or 4.0 and GFDL, per work",
}


def kannada_share(line: str) -> float:
    letters = [c for c in line if c.isalpha() or "ಀ" <= c <= "೿"]
    if not letters:
        return 0.0
    return sum("ಀ" <= c <= "೿" for c in letters) / len(letters)


def chunk(paragraph: str, rng: random.Random, low: int = 12, high: int = 72) -> Iterator[str]:
    """Splits a paragraph into word-aligned pieces of printed-line length."""
    words = paragraph.split()
    target = rng.randint(low, high)
    current: list[str] = []
    size = 0
    for word in words:
        if current and size + 1 + len(word) > target:
            yield " ".join(current)
            current, size, target = [], 0, rng.randint(low, high)
        current.append(word)
        size += len(word) + (1 if size else 0)
    if current:
        yield " ".join(current)


def shingles(line: str, width: int = SHINGLE) -> set[str]:
    """Every `width`-character window of `line` without spaces, ZWJ or ZWNJ, matching
    what scoring ignores. A line shorter than `width` gives itself, which only an
    identical short reference line can match."""
    squashed = line.replace(" ", "").replace("\u200c", "").replace("\u200d", "")
    return {squashed[i : i + width] for i in range(max(1, len(squashed) - width + 1))}


def benchmark_shingles(bench_dirs: Iterable[Path]) -> set[str]:
    refs = [row["text"] for d in bench_dirs for row in read_jsonl(d / "metadata.jsonl")]
    flat = [" ".join(r.split()) for r in refs]
    found: set[str] = set()
    for line in text.normalize(flat):
        found |= shingles(line)
    return found


def documents(parquet: Path, source: str) -> Iterator[str]:
    table = pq.read_table(parquet, columns=["text"])
    for doc in table.column("text").to_pylist():
        if source == "wikisource" and any(m in doc[:300] for m in SONG_MARKERS):
            continue
        yield doc


def build_lines(
    parquets: dict[str, Path],
    bench_dirs: list[Path],
    out: Path,
    per_source: int,
    seed: int = 0,
    log=print,
) -> dict[str, int]:
    """Writes up to `per_source` distinct lines from each source to `out` as `source<TAB>text`."""
    rng = random.Random(seed)
    banned = benchmark_shingles(bench_dirs)
    counts: dict[str, int] = {}
    rows: list[str] = []
    seen: set[str] = set()
    for source, parquet in parquets.items():
        candidates = []
        for doc in documents(parquet, source):
            for paragraph in re.split(r"\n+", doc):
                for line in chunk(paragraph, rng):
                    if len(line) >= 8 and kannada_share(line) >= MIN_KANNADA_SHARE:
                        candidates.append(line)
        rng.shuffle(candidates)
        kept = 0
        dropped = 0
        for normalized in _normalize_all(candidates):
            if kept >= per_source:
                break
            if normalized in seen:
                continue
            if shingles(normalized) & banned:
                dropped += 1
                continue
            seen.add(normalized)
            rows.append(f"{source}\t{normalized}")
            kept += 1
        counts[source] = kept
        log(f"{source}: {len(candidates)} candidates, kept {kept}, {dropped} overlap the benchmark")
    rng.shuffle(rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return counts


def _normalize_all(lines: list[str], batch: int = 50_000) -> Iterator[str]:
    for i in range(0, len(lines), batch):
        yield from text.normalize(lines[i : i + batch])


def read_lines(path: Path) -> list[tuple[str, str]]:
    """(source, text) pairs from a file written by `build_lines`."""
    pairs = []
    for row in path.read_text(encoding="utf-8").splitlines():
        source, _, line = row.partition("\t")
        if line:
            pairs.append((source, line))
    return pairs
