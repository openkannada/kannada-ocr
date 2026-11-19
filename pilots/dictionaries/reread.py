# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

"""Reads the start of an entry again with the Latin model alone, where the 2-script read
lost its headword or label.

Usage: uv run python pilots/dictionaries/reread.py --tessdata DIR [--lang Latin] [--data data]
       [--workers 2]

The 2-script read sometimes turns a bold headword into digits or an italic label into a
Kannada letter. For every first line of an entry where `kannada_ocr.ziegler.needs_reread`
says so, the left SHARE of the line is read as 1 line (page segmentation mode 7). The reads
go to ziegler-1876/ocr-reread.tsv; entries.py takes the headword and label from them.
"""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from entries import BOOK, book_lines
from PIL import Image

from kannada_ocr.pilot import image_path, read_pages
from kannada_ocr.ziegler import Line, needs_reread, read_rows

SHARE = 0.7
"""Headword and label fit in the left 70% of a line; Kannada after them only adds noise."""


def tesseract_line(image: Path, tessdata: Path, lang: str) -> str:
    result = subprocess.run(
        ["tesseract", str(image), "stdout", "--tessdata-dir", str(tessdata), "-l", lang]
        + ["--oem", "1", "--psm", "7"],
        capture_output=True,
        text=True,
        env={**os.environ, "OMP_THREAD_LIMIT": "1"},
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"tesseract failed on {image}: {result.stderr.strip()}")
    return " ".join(result.stdout.split())


def reread_page(image: Path, lines: list[Line], right: dict[str, int], args) -> list[list]:
    page = Image.open(image)
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        for ln in lines:
            stop = min(right[ln.column], ln.left + int(SHARE * (right[ln.column] - ln.left)))
            crop = Path(tmp) / "line.png"
            page.crop((ln.left - 15, ln.top - 10, stop, ln.bottom + 10)).save(crop)
            text = tesseract_line(crop, args.tessdata, args.lang)
            out.append([ln.page, ln.column, ln.line, text])
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tessdata", type=Path, required=True)
    parser.add_argument("--lang", default="Latin")
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--workers", type=int, default=2, choices=range(1, 5))
    args = parser.parse_args()

    rows = read_rows(BOOK / "ocr-lines.tsv")
    right: dict[str, dict[str, int]] = {}
    for r in rows:
        if r.column in "LR":
            edges = right.setdefault(r.page, {})
            edges[r.column] = max(edges.get(r.column, 0), r.right)
    todo: dict[str, list[Line]] = {}
    for ln in book_lines(rows, None):
        if ln.starts and needs_reread(ln.text):
            todo.setdefault(ln.page, []).append(ln)
    pages = {p.page: p for p in read_pages(BOOK / "pages.tsv")}
    root = args.data / "pilots" / "dictionaries"

    def job(page: str) -> list[list]:
        return reread_page(image_path(root, pages[page]), todo[page], right[page], args)

    with ThreadPoolExecutor(args.workers) as pool:
        results = list(pool.map(job, sorted(todo)))
    with (BOOK / "ocr-reread.tsv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(["page", "column", "line", "text"])
        for rows_of_page in results:
            writer.writerows(rows_of_page)
    print(f"{sum(len(v) for v in todo.values())} lines read again on {len(todo)} pages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
