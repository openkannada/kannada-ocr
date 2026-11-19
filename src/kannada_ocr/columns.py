# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

"""Finds the printed area, the 2 columns and the text lines of a 2-column dictionary page.

Works on ink profiles of a binarized page. Scans of bound books show dark background, the
spine shadow and an edge of the facing page. The printed area is grown from the page center
until it meets a band, 3% of the page wide, with no print in it: blank paper, or shadow
and background, where most pixels are ink.
"""

from __future__ import annotations

import numpy as np
from PIL import Image

Box = tuple[int, int, int, int]
"""Left, top, right and bottom in pixels."""

BLANK = 0.001
DARK = 0.3
"""A row or column with less ink than BLANK, or more than DARK, has no print in it."""
MARGIN = 0.03
"""The width of a band without print that ends the printed area, as a share of the page."""
RULE = 0.35
"""A column with more ink than this inside the printed area is a vertical rule."""
FOOTER_RULE = 0.25
"""A band of rows with an unbroken run of ink this share of the printed area wide holds the
rule above a footer. Text has gaps between words, so its runs stay under 6% of the width;
rules on the Ziegler scans run 36% to 96% of it, broken or slightly skewed."""
RULE_BAND = 12
"""Rows taken together, so a rule skewed by a few pixels still makes 1 run."""


def ink(image: Image.Image) -> np.ndarray:
    """True where a pixel is darker than Otsu's threshold."""
    gray = np.asarray(image.convert("L"), dtype=np.uint8)
    hist = np.bincount(gray.ravel(), minlength=256).astype(float)
    levels = np.arange(256)
    weight = np.cumsum(hist)
    mean = np.cumsum(hist * levels)
    total = weight[-1]
    between = (mean[-1] * weight - mean * total) ** 2 / np.maximum(weight * (total - weight), 1)
    return gray <= int(np.argmax(between))


def _grow(profile: np.ndarray, center: int, run: int) -> tuple[int, int]:
    """The span around `center` that ends at the first `run` rows or columns without print."""
    empty = (profile < BLANK) | (profile > DARK)
    left = center
    gap = 0
    while left > 0 and gap < run:
        left -= 1
        gap = gap + 1 if empty[left] else 0
    right = center
    gap = 0
    while right < len(profile) - 1 and gap < run:
        right += 1
        gap = gap + 1 if empty[right] else 0
    return left, right + 1


def content_box(mask: np.ndarray) -> Box:
    """The printed area around the page center, trimmed to its ink."""
    height, width = mask.shape
    middle = mask[height // 4 : 3 * height // 4]
    left, right = _grow(middle.mean(axis=0), width // 2, int(MARGIN * width))
    top, bottom = _grow(mask[:, left:right].mean(axis=1), height // 2, int(MARGIN * height))
    region = mask[top:bottom, left:right]
    cols = np.flatnonzero((region.mean(axis=0) >= BLANK) & (region.mean(axis=0) <= DARK))
    rows = np.flatnonzero((region.mean(axis=1) >= BLANK) & (region.mean(axis=1) <= DARK))
    if len(cols) == 0 or len(rows) == 0:
        return left, top, right, bottom
    # Half a margin of padding keeps the ends of lines on a slightly skewed page.
    pad = int(MARGIN * width / 2)
    return (
        max(left, left + int(cols[0]) - pad),
        max(top, top + int(rows[0]) - pad),
        min(right, left + int(cols[-1]) + 1 + pad),
        min(bottom, top + int(rows[-1]) + 1 + pad),
    )


def gutter(mask: np.ndarray, box: Box) -> int:
    """The x of the emptiest vertical band in the middle fifth of `box`, rules ignored."""
    left, top, right, bottom = box
    profile = mask[top:bottom, left:right].mean(axis=0)
    profile = np.where(profile > RULE, 0.0, profile)
    width = right - left
    band = max(3, width // 100)
    smooth = np.convolve(profile, np.ones(band) / band, mode="same")
    lo, hi = 2 * width // 5, 3 * width // 5
    return int(left + lo + int(np.argmin(smooth[lo:hi])))


def split_columns(mask: np.ndarray, box: Box | None = None) -> tuple[Box, Box]:
    box = box or content_box(mask)
    x = gutter(mask, box)
    left, top, right, bottom = box
    return (left, top, x, bottom), (x, top, right, bottom)


def text_lines(mask: np.ndarray, box: Box, min_gap: int = 3) -> list[Box]:
    """Line boxes in `box`, from runs of rows with ink, gaps under `min_gap` rows bridged.

    Vertical rules are left out, since they would join every line. A run more than 1.7 times
    the usual line height is cut at its emptiest row, so 2 lines joined by a descender come
    apart.
    """
    left, top, right, bottom = box
    region = mask[top:bottom, left:right]
    region = region & ~(region.mean(axis=0) > RULE)
    profile = region.mean(axis=1)
    rows = profile > 0.004
    runs: list[list[int]] = []
    for y, on in enumerate(rows):
        if not on:
            continue
        if runs and y - runs[-1][1] <= min_gap:
            runs[-1][1] = y + 1
        else:
            runs.append([y, y + 1])
    runs = [r for r in runs if r[1] - r[0] >= 4]
    if not runs:
        return []
    # Many runs are 2 lines joined by a subscript, so the median would overstate a line.
    usual = float(np.percentile([b - a for a, b in runs], 25))
    split: list[tuple[int, int]] = []
    for a, b in runs:
        while b - a > 1.7 * usual:
            lo, hi = a + int(0.6 * usual), b - int(0.6 * usual)
            cut = lo + int(np.argmin(profile[lo:hi]))
            split.append((a, cut))
            a = cut
        split.append((a, b))
    boxes = []
    for a, b in split:
        cols = np.flatnonzero(region[a:b].any(axis=0))
        if len(cols):
            boxes.append((left + int(cols[0]), top + a, left + int(cols[-1]) + 1, top + b))
    return boxes


def footer_rule(mask: np.ndarray, box: Box) -> int | None:
    """The row of a horizontal rule in the lower third of `box`, if there is one.

    The first band of rows that holds the rule is found, then the row in it with the most ink.
    """
    left, top, right, bottom = box
    start = top + 2 * (bottom - top) // 3
    for y in range(start, bottom):
        band = mask[y : y + RULE_BAND, left:right]
        if longest_run(band.any(axis=0)) >= FOOTER_RULE * (right - left):
            return y + int(np.argmax(band.sum(axis=1)))
    return None


def longest_run(row: np.ndarray) -> int:
    """The length of the longest run of True in a 1-dimensional array."""
    if not row.any():
        return 0
    edges = np.flatnonzero(np.diff(np.concatenate(([0], row.astype(np.int8), [0]))))
    return int((edges[1::2] - edges[::2]).max())


def page_regions(mask: np.ndarray) -> tuple[Box | None, Box]:
    """The running head and the body of a dictionary page.

    The running head is the first text line of the printed area. The body is what lies below
    it and above the footer rule, if any; the footer (a pronunciation key) is left out.
    """
    box = content_box(mask)
    left, top, right, bottom = box
    rule = footer_rule(mask, box)
    if rule is not None:
        bottom = rule
    lines = text_lines(mask, (left, top, right, bottom))
    if len(lines) < 2:
        return None, (left, top, right, bottom)
    head = (left, lines[0][1], right, lines[0][3])
    return head, (left, lines[0][3], right, bottom)
