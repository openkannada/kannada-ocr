"""Training lines cut from proofread Kannada Wikisource scans, with proofread labels.

Books in the wikisource-old test split are skipped entirely. Its dev books give dev lines, used
to pick training checkpoints. Every other proofread book gives training lines.
Tesseract finds the printed lines on each scan; `align` labels them from the proofread text.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import statistics
import subprocess
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from functools import cache
from pathlib import Path
from typing import Any

from PIL import Image

from . import corpus, text, wikisource
from .align import align, read_tsv
from .dataset import ImageFolderWriter
from .http import Client

TRAIN_PAGES_PER_BOOK = 40
DEV_PAGES_PER_BOOK = 15
SCAN_WIDTH = 1280
LOW_RES_WIDTH = 500
"""The page width of the wikisource-old benchmark scans."""
LOW_RES_SHARE = 0.35
LINE_PAD = 6
TALL = 1.5
"""A line box this many times the page's median height holds more than 1 printed line."""
ZERO_AS_ANUSVARA = re.compile("(?<=[\u0c95-\u0cb9\u0cbe-\u0ccc])[\u0ce60](?![\u0ce6-\u0cef0-9])")
"""A zero (U+0CE6 or 0) right after a Kannada letter or vowel sign, typed for an anusvara."""
OCR_CONFIG = ("--oem", "1", "--psm", "3", "-l", "kan", "-c", "tessedit_create_tsv=1")

Log = Callable[[str], None]


def held_out_books(bench: Path) -> dict[str, str]:
    """The wikisource-old benchmark's books and their split, by file name."""
    books = json.loads((bench / "books.json").read_text(encoding="utf-8"))
    return {book["file"]: book["split"] for book in books}


def scan_url(image_url: str, width: int = SCAN_WIDTH) -> str:
    """The same scan thumbnail at another width."""
    head, _, name = image_url.rpartition("/")
    name = re.sub(r"(^|-)\d+px-", rf"\g<1>{width}px-", name, count=1)
    return f"{head}/{name}"


@cache
def _model_hash(tessdata: Path) -> str:
    return hashlib.sha256((tessdata / "kan.traineddata").read_bytes()).hexdigest()


def tesseract_tsv(image: Path, tessdata: Path, cache_dir: Path) -> str:
    """Tesseract's TSV for a scan, cached by image content, model and settings."""
    settings = (_model_hash(tessdata) + " ".join(OCR_CONFIG)).encode()
    key = hashlib.sha256(image.read_bytes() + settings).hexdigest()
    path = cache_dir / f"{key}.tsv"
    if path.exists():
        return path.read_text(encoding="utf-8")
    result = subprocess.run(
        ["tesseract", str(image), "stdout", "--tessdata-dir", str(tessdata), *OCR_CONFIG],
        capture_output=True,
        text=True,
        env={**os.environ, "OMP_THREAD_LIMIT": "1"},
        check=True,
    )
    cache_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(result.stdout, encoding="utf-8")
    return result.stdout


def fix_proofreading(label: str) -> str:
    """Puts the anusvara ಂ (U+0C82) where proofreaders typed a zero for it."""
    return ZERO_AS_ANUSVARA.sub("\u0c82", label)


def single_lines(boxes: list[tuple[int, int, int, int]]) -> list[bool]:
    """For each line box on a page, whether it is short enough to hold 1 printed line."""
    if not boxes:
        return []
    median = statistics.median(bottom - top for _, top, _, bottom in boxes)
    return [bottom - top <= TALL * median for _, top, _, bottom in boxes]


def low_res(item_id: str) -> bool:
    """A fixed share of lines also gets a copy at the benchmark's scan resolution."""
    return int(hashlib.sha256(item_id.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF < LOW_RES_SHARE


def fetch_scan(client: Client, image_url: str) -> str | None:
    """The URL of the page's scan at SCAN_WIDTH, fetched and cached, or of its own thumbnail
    if the large one fails; None if both fail, so 1 bad scan does not stop a long fetch."""
    for url in (scan_url(image_url), image_url):
        try:
            client.get(url)
            return url
        except Exception:  # noqa: BLE001 - thumbnail errors vary: 404, 429, 503, timeouts
            continue
    return None


def _pages(
    client: Client, held: dict[str, str], log: Log, pages_per_book: int = TRAIN_PAGES_PER_BOOK
) -> list[dict[str, Any]]:
    """Every page to cut lines from, with its book's details. Fetches and caches the scans."""
    pages = []
    for title in wikisource.list_indexes(client):
        index = wikisource.read_index(client, title)
        split = held.get(index.file, "train")
        if split == "test":
            continue
        licenses = wikisource.file_licenses(client, index.file)
        if not licenses:
            log(f"skip {title}: no license found")
            continue
        count = DEV_PAGES_PER_BOOK if split == "dev" else pages_per_book
        kept = 0
        for number in wikisource.sample_pages(index, count):
            page = wikisource.read_page(client, index, number)
            if page is None:
                continue
            url = fetch_scan(client, page.image_url)
            if url is None:
                log(f"skip {page.title}: no scan could be fetched")
                continue
            pages.append(
                {
                    "book": index.file,
                    "number": number,
                    "split": split,
                    "text": page.text,
                    "image_url": url,
                    "source": wikisource.wiki_url(page.title),
                    "license": ", ".join(licenses),
                    "year": index.year,
                }
            )
            kept += 1
        log(f"{title} ({index.year}, {split}): {kept} pages")
    return pages


def fetch(
    client: Client, bench: Path, pages_per_book: int = TRAIN_PAGES_PER_BOOK, log: Log = print
) -> int:
    """Downloads and caches every page and scan `build` needs, with no OCR."""
    return len(_pages(client, held_out_books(bench), log, pages_per_book))


def build(
    client: Client,
    out: Path,
    bench: Path,
    tessdata: Path,
    benchmark_sets: list[Path],
    workers: int = 2,
    pages_per_book: int = TRAIN_PAGES_PER_BOOK,
    log: Log = print,
) -> int:
    """Writes line images and labels under `out` in ImageFolder layout."""
    pages = _pages(client, held_out_books(bench), log, pages_per_book)
    books = sorted({p["book"] for p in pages})
    banned = corpus.benchmark_shingles(benchmark_sets)
    scratch = out / "scans"
    scratch.mkdir(parents=True, exist_ok=True)

    def cut(page: dict[str, Any]) -> tuple[float, list[tuple[str, Image.Image, str]]]:
        scan = Image.open(io.BytesIO(client.get(page["image_url"]))).convert("L")
        path = scratch / f"{hashlib.sha256(page['image_url'].encode()).hexdigest()[:16]}.png"
        scan.save(path)
        ref = text.normalize([" ".join(page["text"].split())])[0]
        tsv = tesseract_tsv(path, tessdata, out.parent / "ocr")
        path.unlink()
        lines = align(ref, text.aksharas([ref])[0], read_tsv(tsv))
        prefix = f"ws{books.index(page['book']):02d}_{page['number']:04d}"
        crops = []
        single = single_lines([line.box for line, _ in lines])
        for i, ((line, label), ok) in enumerate(zip(lines, single, strict=True)):
            label = fix_proofreading(label)
            if not ok or corpus.shingles(label) & banned:
                continue
            left, top, right, bottom = line.box
            box = (
                max(0, left - LINE_PAD),
                max(0, top - LINE_PAD),
                min(scan.width, right + LINE_PAD),
                min(scan.height, bottom + LINE_PAD),
            )
            crops.append((f"{prefix}_L{i:02d}", scan.crop(box), label))
        return LOW_RES_WIDTH / scan.width, crops

    count = 0
    with ImageFolderWriter(out) as writer, ThreadPoolExecutor(workers) as pool:
        for page, (scale, crops) in zip(pages, pool.map(cut, pages), strict=True):
            fields = {"level": "line", "group": page["book"]}
            fields |= {k: page[k] for k in ("split", "source", "image_url", "license", "year")}
            for item_id, crop, label in crops:
                writer.add(item_id, crop, label, **fields)
                count += 1
                if low_res(item_id) and scale < 1:
                    size = (max(1, round(crop.width * scale)), max(1, round(crop.height * scale)))
                    writer.add(
                        f"{item_id}_lr",
                        crop.resize(size, Image.Resampling.LANCZOS),
                        label,
                        **fields,
                    )
                    count += 1
    scratch.rmdir()
    log(f"wikisource-lines: {count} lines from {len(books)} books")
    return count
