# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

"""Runs each Tesseract configuration over the pilot pages and times every page.

Usage: uv run python pilots/dictionaries/ocr.py --tessdata DIR [--data data] [--scan BOOK/SCAN]
       [--config NAME ...] [--workers 2]

DIR holds kan, kan_ft_ofl3 and eng traineddata, and eng_best and Latin from models.tsv.
Text goes to outputs/<book>/<scan>/<config>/<page>.txt and 1 row per page to
outputs/timings.tsv. Pages already read are skipped.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from kannada_ocr.columns import ink, split_columns
from kannada_ocr.pilot import Page, image_path, read_pages

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"


@dataclass(frozen=True)
class Config:
    lang: str
    psm: int
    columns: bool = False
    """Cut the page into its 2 columns first and read each on its own."""


CONFIGS = {
    "kanft+eng-psm3": Config("kan_ft_ofl3+eng", 3),
    "kanft+eng-psm4": Config("kan_ft_ofl3+eng", 4),
    "kanft-psm3": Config("kan_ft_ofl3", 3),
    "kanft-psm4": Config("kan_ft_ofl3", 4),
    "kan+eng-psm3": Config("kan+eng", 3),
    "kan+eng-psm4": Config("kan+eng", 4),
    "kanft+eng-cols-psm4": Config("kan_ft_ofl3+eng", 4, columns=True),
    "kanft+eng-cols-psm6": Config("kan_ft_ofl3+eng", 6, columns=True),
    "kan+eng-cols-psm4": Config("kan+eng", 4, columns=True),
    "kanft+engbest-psm3": Config("kan_ft_ofl3+eng_best", 3),
    "kanft+engbest-cols-psm6": Config("kan_ft_ofl3+eng_best", 6, columns=True),
    "kanft+latin-psm3": Config("kan_ft_ofl3+Latin", 3),
    "kanft+latin-cols-psm6": Config("kan_ft_ofl3+Latin", 6, columns=True),
    "latin+kanft-cols-psm6": Config("Latin+kan_ft_ofl3", 6, columns=True),
}


def tesseract(image: Path, tessdata: Path, config: Config) -> str:
    result = subprocess.run(
        ["tesseract", str(image), "stdout", "--tessdata-dir", str(tessdata), "-l", config.lang]
        + ["--oem", "1", "--psm", str(config.psm)],
        capture_output=True,
        text=True,
        env={**os.environ, "OMP_THREAD_LIMIT": "1"},
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"tesseract failed on {image}: {result.stderr.strip()}")
    return result.stdout.replace("\f", "")


def read(image: Path, tessdata: Path, config: Config) -> str:
    if not config.columns:
        return tesseract(image, tessdata, config)
    page = Image.open(image)
    texts = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, box in enumerate(split_columns(ink(page))):
            crop = Path(tmp) / f"{i}.png"
            page.crop(box).save(crop)
            texts.append(tesseract(crop, tessdata, config))
    return "\n".join(texts)


def job(root: Path, page: Page, name: str, tessdata: Path) -> str:
    out = OUT / page.book / page.scan / name / f"{page.page}.txt"
    start = time.monotonic()
    text = read(image_path(root, page), tessdata, CONFIGS[name])
    seconds = time.monotonic() - start
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return f"{page.book}\t{page.scan}\t{name}\t{page.page}\t{seconds:.1f}\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tessdata", type=Path, required=True)
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--scan", action="append", help="BOOK/SCAN, for example kittel-1894/google")
    parser.add_argument("--config", action="append", choices=sorted(CONFIGS))
    parser.add_argument("--pages", type=int, default=0, help="only the first N pages of each scan")
    parser.add_argument("--workers", type=int, default=2, choices=range(1, 5))
    args = parser.parse_args()

    root = args.data / "pilots" / "dictionaries"
    pages = [p for p in read_pages(HERE / "pages.tsv") if p.page != "title"]
    if args.scan:
        pages = [p for p in pages if f"{p.book}/{p.scan}" in args.scan]
    if args.pages:
        seen: dict[str, int] = {}
        kept = []
        for p in pages:
            key = f"{p.book}/{p.scan}"
            seen[key] = seen.get(key, 0) + 1
            if seen[key] <= args.pages:
                kept.append(p)
        pages = kept
    todo = [
        (p, name)
        for name in args.config or CONFIGS
        for p in pages
        if not (OUT / p.book / p.scan / name / f"{p.page}.txt").exists()
    ]
    timings = OUT / "timings.tsv"
    OUT.mkdir(parents=True, exist_ok=True)
    if not timings.exists():
        timings.write_text("book\tscan\tconfig\tpage\tseconds\n", encoding="utf-8")
    with ThreadPoolExecutor(args.workers) as pool:
        for n, row in enumerate(pool.map(lambda t: job(root, t[0], t[1], args.tessdata), todo)):
            with timings.open("a", encoding="utf-8") as f:
                f.write(row)
            print(f"{n + 1}/{len(todo)} {row.strip()}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
