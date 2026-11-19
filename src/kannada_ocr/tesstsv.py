# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

"""Text lines with boxes from Tesseract's TSV output, cut into segments at wide gaps.

A dictionary line can hold 2 pieces of text far apart: the end of the line, and a turnover
(the last syllables of the line below, set at the right). A gap wider than GAP times the
line height ends a segment, so a later step can tell the pieces apart.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass

GAP = 0.6


@dataclass(frozen=True)
class Segment:
    line: int
    """The line's number in the TSV, counted across Tesseract's blocks, from 0."""
    left: int
    top: int
    right: int
    bottom: int
    conf: float
    """The mean word confidence, 0 to 100."""
    text: str


def segments(tsv: str, dx: int = 0, dy: int = 0) -> list[Segment]:
    """The segments of every line in `tsv`, in reading order, boxes moved by (dx, dy)."""
    lines: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    heights: dict[tuple[str, str, str], int] = {}
    for row in csv.DictReader(io.StringIO(tsv), delimiter="\t", quoting=csv.QUOTE_NONE):
        key = (row["block_num"], row["par_num"], row["line_num"])
        if row["level"] == "4":
            heights[key] = int(row["height"])
        elif row["level"] == "5" and row["text"].strip():
            lines.setdefault(key, []).append(row)
    out: list[Segment] = []
    for n, (key, words) in enumerate(lines.items()):
        gap = GAP * heights.get(key, max(int(w["height"]) for w in words))
        run: list[dict[str, str]] = []
        for word in words:
            if run and int(word["left"]) - _right(run[-1]) > gap:
                out.append(_segment(n, run, dx, dy))
                run = []
            run.append(word)
        out.append(_segment(n, run, dx, dy))
    return out


def _right(word: dict[str, str]) -> int:
    return int(word["left"]) + int(word["width"])


def _segment(line: int, words: list[dict[str, str]], dx: int, dy: int) -> Segment:
    return Segment(
        line=line,
        left=dx + min(int(w["left"]) for w in words),
        top=dy + min(int(w["top"]) for w in words),
        right=dx + max(_right(w) for w in words),
        bottom=dy + max(int(w["top"]) + int(w["height"]) for w in words),
        conf=round(sum(float(w["conf"]) for w in words) / len(words), 1),
        text=" ".join(w["text"].strip() for w in words),
    )
