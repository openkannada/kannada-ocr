# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

"""Picks the hand-checked lines of each pilot page and cuts them out for transcribing.

Usage: uv run python pilots/dictionaries/sample.py BOOK SCAN [--data data]

From each page it takes 3 lines: the first entry at or below 25% of the left column, the
first entry at or below 50% of the right column, and the line at 80% of a column that
alternates from page to page, starting with the right one. An entry is a line that starts at the
column's left edge; continuation lines are indented. A box taller than a line is cut to its
first line. Crops go to <data>/pilots/dictionaries/crops/, 3 lines to an image.
transcriptions/BOOK.tsv gets 1 row per line with an empty text column, unless it exists.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from kannada_ocr.columns import Box, ink, split_columns, text_lines
from kannada_ocr.pilot import image_path, read_pages

HERE = Path(__file__).resolve().parent
PICKS = (("L", 0.25, True), ("R", 0.50, True), ("odd", 0.80, False))
INDENT = 0.015
"""A line whose left edge is within this share of the column width from the edge starts an entry."""
SCALE = 1.6


def pick(lines: list[Box], column: Box, at: float, entry: bool) -> int:
    top, bottom = column[1], column[3]
    edge = float(np.percentile([b[0] for b in lines], 10))
    width = column[2] - column[0]
    target = top + at * (bottom - top)
    for i, b in enumerate(lines):
        if b[1] >= target and (not entry or b[0] <= edge + INDENT * width):
            return i
    return len(lines) - 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("book")
    parser.add_argument("scan")
    parser.add_argument("--data", type=Path, default=Path("data"))
    args = parser.parse_args()

    root = args.data / "pilots" / "dictionaries"
    crops = root / "crops" / args.book
    crops.mkdir(parents=True, exist_ok=True)
    pages = [
        p
        for p in read_pages(HERE / "pages.tsv")
        if p.book == args.book and p.scan == args.scan and p.page != "title"
    ]
    rows = []
    for n, page in enumerate(sorted(pages, key=lambda p: int(p.page))):
        image = Image.open(image_path(root, page)).convert("RGB")
        mask = ink(image)
        columns = dict(zip("LR", split_columns(mask), strict=True))
        lines = {k: text_lines(mask, box) for k, box in columns.items()}
        strips = []
        for side, at, entry in PICKS:
            if side == "odd":
                side = "L" if n % 2 else "R"
            i = pick(lines[side], columns[side], at, entry)
            left, top, right, bottom = lines[side][i]
            usual = float(np.median([b[3] - b[1] for b in lines[side]]))
            # A box the line finder could not split is cut to its first line.
            bottom = min(bottom, top + int(1.3 * usual))
            box = (columns[side][0], top - 6, columns[side][2], bottom + 6)
            rows.append([page.page, side, i, ",".join(map(str, box)), "", "", ""])
            strip = image.crop(box)
            strips.append(strip.resize((int(strip.width * SCALE), int(strip.height * SCALE))))
        size = (max(s.width for s in strips) + 60, sum(s.height + 20 for s in strips))
        sheet = Image.new("RGB", size, "white")
        y = 0
        draw = ImageDraw.Draw(sheet)
        for k, strip in enumerate(strips):
            draw.text((5, y + strip.height // 2), str(k + 1), fill="red")
            sheet.paste(strip, (60, y))
            y += strip.height + 20
        sheet.save(crops / f"{page.page}.png")
    out = HERE / "transcriptions" / f"{args.book}.tsv"
    if out.exists():
        print(f"{out} exists; not overwritten")
        return 0
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(["page", "column", "line", "box", "headword", "text", "uncertain"])
        writer.writerows(rows)
    print(f"{len(rows)} lines from {len(pages)} pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
