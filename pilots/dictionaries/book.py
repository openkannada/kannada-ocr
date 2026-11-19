# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

"""Reads every page of a scan into text segments with boxes, for cutting into entries.

Usage: uv run python pilots/dictionaries/book.py --pages ziegler-1876/pages.tsv --tessdata DIR
       [--config kanft+latin-cols-psm6] [--head-lang Latin] [--data data] [--workers 2]

Each page is cut into its running head, 2 columns and footer (`kannada_ocr.columns`); the
footer is not read. The head is read as 1 line, each column with the configuration's model
and mode, and every line is cut into segments at wide gaps (`kannada_ocr.tesstsv`). Pages
go to <data>/pilots/dictionaries/<book>/<scan>/lines/<page>.tsv, so a stopped run resumes;
when all are read they are joined into <book>/ocr-lines.tsv next to the page list, with 1
row per segment: page, column (H for the head, L, R), line, box, mean confidence and text.
Seconds per page go to <book>/timings.tsv.
"""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import astuple, fields
from pathlib import Path

from ocr import CONFIGS
from PIL import Image

from kannada_ocr.columns import Box, ink, page_regions, split_columns
from kannada_ocr.pilot import Page, image_path, read_pages
from kannada_ocr.tesstsv import Segment, segments

HERE = Path(__file__).resolve().parent
COLUMNS = ["page", "column"] + [f.name for f in fields(Segment)]


def tesseract_tsv(image: Path, tessdata: Path, lang: str, psm: int) -> str:
    result = subprocess.run(
        ["tesseract", str(image), "stdout", "--tessdata-dir", str(tessdata), "-l", lang]
        + ["--oem", "1", "--psm", str(psm), "-c", "tessedit_create_tsv=1"],
        capture_output=True,
        text=True,
        env={**os.environ, "OMP_THREAD_LIMIT": "1"},
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"tesseract failed on {image}: {result.stderr.strip()}")
    return result.stdout


def read_page(image: Path, tessdata: Path, lang: str, psm: int, head_lang: str) -> list[list]:
    page = Image.open(image)
    mask = ink(page)
    head, body = page_regions(mask)
    parts: list[tuple[str, Box, str, int]] = []
    if head is not None:
        parts.append(("H", head, head_lang, 7))
    left, right = split_columns(mask, body)
    parts += [("L", left, lang, psm), ("R", right, lang, psm)]
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for column, box, model, mode in parts:
            crop = Path(tmp) / f"{column}.png"
            page.crop(box).save(crop)
            for seg in segments(tesseract_tsv(crop, tessdata, model, mode), box[0], box[1]):
                rows.append([column, *astuple(seg)])
    return rows


def job(root: Path, page: Page, args: argparse.Namespace, out: Path) -> str:
    config = CONFIGS[args.config]
    if not config.columns:
        raise SystemExit(f"{args.config} does not cut columns")
    start = time.monotonic()
    rows = read_page(image_path(root, page), args.tessdata, config.lang, config.psm, args.head_lang)
    seconds = time.monotonic() - start
    partial = out.with_suffix(".part")
    with partial.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerows([page.page, *row] for row in rows)
    partial.rename(out)
    return f"{page.page}\t{seconds:.1f}\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pages", required=True, help="page list, relative to this folder")
    parser.add_argument("--tessdata", type=Path, required=True)
    parser.add_argument("--config", default="kanft+latin-cols-psm6", choices=sorted(CONFIGS))
    parser.add_argument("--head-lang", default="Latin")
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--workers", type=int, default=2, choices=range(1, 5))
    args = parser.parse_args()

    pages_file = HERE / args.pages
    pages = read_pages(pages_file)
    root = args.data / "pilots" / "dictionaries"
    folder = root / pages[0].book / pages[0].scan / "lines"
    folder.mkdir(parents=True, exist_ok=True)
    timings = pages_file.parent / "timings.tsv"
    if not timings.exists():
        timings.write_text("page\tseconds\n", encoding="utf-8")
    todo = [p for p in pages if not (folder / f"{p.page}.tsv").exists()]
    with ThreadPoolExecutor(args.workers) as pool:
        work = pool.map(lambda p: job(root, p, args, folder / f"{p.page}.tsv"), todo)
        for n, row in enumerate(work):
            with timings.open("a", encoding="utf-8") as f:
                f.write(row)
            print(f"{n + 1}/{len(todo)} {row.strip()}", flush=True)
    with (pages_file.parent / "ocr-lines.tsv").open("w", encoding="utf-8", newline="") as f:
        f.write("\t".join(COLUMNS) + "\n")
        for page in pages:
            f.write((folder / f"{page.page}.tsv").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
