"""Matches the printed lines Tesseract finds on a scan to the proofread text of the page.

Wikisource keeps the proofread text of each page, often without its printed line breaks, and
old Kannada print breaks words across lines without a hyphen. Tesseract finds each printed
line and reads it with errors. A line's label is the stretch of proofread text, cut at akshara
boundaries, that is closest to its reading by edit distance. Lines whose reading is far from
every stretch, or whose first or last aksharas differ, are dropped, so a label is never a guess.
"""

from __future__ import annotations

import bisect
from collections.abc import Sequence
from dataclasses import dataclass

from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein

MIN_SIMILARITY = 0.7
EDGE = 4
"""Characters compared at each end of a line."""
EDGE_SIMILARITY = 0.5
MIN_CHARS = 8
SLACK = 40
"""Characters searched past where a line's text is expected to end."""
REACH = 12
"""How far a label's ends may move from the rough match while searching for the closest cut."""


@dataclass(frozen=True)
class OcrLine:
    box: tuple[int, int, int, int]
    """Left, top, right and bottom in pixels."""
    text: str


def read_tsv(tsv: str) -> list[OcrLine]:
    """Printed lines from Tesseract's TSV output, in reading order, with their words."""
    boxes: dict[tuple[str, ...], tuple[int, int, int, int]] = {}
    words: dict[tuple[str, ...], list[str]] = {}
    for row in tsv.splitlines()[1:]:
        cols = row.split("\t")
        if len(cols) < 12:
            continue
        level, key = cols[0], tuple(cols[1:5])
        left, top, width, height = (int(c) for c in cols[6:10])
        if level == "4":
            boxes[key] = (left, top, left + width, top + height)
            words.setdefault(key, [])
        elif level == "5" and cols[11].strip():
            words.setdefault(key, []).append(cols[11].strip())
    return [OcrLine(boxes[k], " ".join(words[k])) for k in boxes if words.get(k)]


def boundaries(segments: Sequence[str]) -> list[int]:
    """Character offsets between akshara segments, including both ends."""
    offsets = [0]
    for segment in segments:
        offsets.append(offsets[-1] + len(segment))
    return offsets


def similarity(a: str, b: str) -> float:
    return Levenshtein.normalized_similarity(a, b)


def _near(cuts: list[int], center: int, low: int) -> list[int]:
    lo = bisect.bisect_left(cuts, max(low, center - REACH))
    hi = bisect.bisect_right(cuts, center + REACH)
    return cuts[lo:hi]


def _closest(reading: str, ref: str, starts: list[int], ends: list[int]) -> tuple[int, str]:
    best = (-1.0, 0, "")
    for a in starts:
        for b in ends:
            label = ref[a:b].strip()
            if len(label) >= MIN_CHARS:
                score = similarity(reading, label)
                if score > best[0]:
                    best = (score, b, label)
    return best[1], best[2]


def _edges_match(reading: str, label: str) -> bool:
    return (
        similarity(reading[:EDGE], label[:EDGE]) >= EDGE_SIMILARITY
        and similarity(reading[-EDGE:], label[-EDGE:]) >= EDGE_SIMILARITY
    )


def align(
    ref: str,
    segments: Sequence[str],
    lines: list[OcrLine],
    min_similarity: float = MIN_SIMILARITY,
) -> list[tuple[OcrLine, str]]:
    """Each line that matches a stretch of `ref` closely, with that stretch as its label.

    `segments` are the aksharas of `ref`, spaces included; labels start and end between them.
    Lines are matched in order, each after the previous match, so no text is used twice. The
    first match may be anywhere, since Tesseract can miss a heading or the page's first lines.
    A line that ends in a hyphen is dropped, since the proofread text joins the word.
    """
    cuts = boundaries(segments)
    if cuts[-1] != len(ref):
        raise ValueError("segments do not cover ref")
    cursor = 0
    skipped = 0  # text read on unmatched lines since the last match, so the search reaches past it
    matched = []
    for line in lines:
        reading = " ".join(line.text.split())
        if len(reading.replace(" ", "")) < MIN_CHARS or reading.endswith(("-", "\u2010")):
            continue
        end = cursor + skipped + 2 * len(reading) + SLACK if matched else len(ref)
        window = ref[cursor:end]
        skipped += len(reading) + 1
        if len(window) < len(reading):
            continue
        hit = fuzz.partial_ratio_alignment(reading, window)
        if hit is None:
            continue
        starts = _near(cuts, cursor + hit.dest_start, cursor)
        ends = _near(cuts, cursor + hit.dest_end, cursor)
        end, label = _closest(reading, ref, starts, ends)
        if label and similarity(reading, label) >= min_similarity and _edges_match(reading, label):
            matched.append((line, label))
            cursor, skipped = end, 0
    return matched
