"""Builds the evaluation sets under `data/bench/<set>/` in ImageFolder layout."""

from __future__ import annotations

import io
import json
from collections.abc import Callable
from pathlib import Path

from PIL import Image

from . import mile, wikisource
from .dataset import ImageFolderWriter, read_jsonl
from .http import Client

MILE_PAGES_URL = "https://github.com/MILE-IISc/Kannada-OCR-test-images-with-ground-truth"
MILE_DEGRADED_URL = "https://github.com/MILE-IISc/DegradedWordsKannada"
MILE_PAGES_LICENSE = "none stated (no LICENSE file); evaluation use only until MILE confirms"
LINE_PAD = 6
OLD_PRINT_LAST_YEAR = 1950
PUBLIC_DOMAIN_MARKS = ("public domain", "pd-", "pdm", "cc0", "cc-zero")

Log = Callable[[str], None]


def build_mile_lines(repo: Path, out: Path, log: Log = print) -> int:
    """1 image per printed line, cropped from the page with the MILE line box."""
    count = 0
    with ImageFolderWriter(out) as writer:
        for page in mile.read_pages(repo):
            with Image.open(page.image) as scan:
                gray = scan.convert("L")
            for line in page.lines:
                crop = gray.crop(line.box.padded(LINE_PAD, gray.width, gray.height))
                writer.add(
                    f"{page.id}_L{line.number:03d}",
                    crop,
                    line.text,
                    level="line",
                    group=page.book,
                    source=f"{MILE_PAGES_URL}/blob/master/groundtruth/{page.id}.xml",
                    license=MILE_PAGES_LICENSE,
                )
                count += 1
    log(f"mile-lines: {count} lines")
    return count


def build_mile_pages(repo: Path, out: Path, log: Log = print) -> int:
    pages = mile.read_pages(repo)
    with ImageFolderWriter(out) as writer:
        for page in pages:
            with Image.open(page.image) as scan:
                writer.add(
                    page.id,
                    scan.convert("L"),
                    page.text,
                    level="page",
                    group=page.book,
                    source=f"{MILE_PAGES_URL}/blob/master/groundtruth/{page.id}.xml",
                    license=MILE_PAGES_LICENSE,
                )
    log(f"mile-pages: {len(pages)} pages")
    return len(pages)


def build_degraded_words(repo: Path, out: Path, log: Log = print) -> int:
    pairs = mile.read_degraded_words(repo)
    with ImageFolderWriter(out) as writer:
        for image_path, text in pairs:
            with Image.open(image_path) as im:
                writer.add(
                    image_path.stem,
                    im.convert("L"),
                    text,
                    level="word",
                    group=image_path.stem.split("_P", 1)[0],
                    split="test",
                    source=f"{MILE_DEGRADED_URL}/blob/master/TestImages/{image_path.name}",
                    license="Apache-2.0",
                )
    log(f"degraded-words: {len(pairs)} words")
    return len(pairs)


def is_public_domain(licenses: list[str]) -> bool:
    return any(mark in name.lower() for name in licenses for mark in PUBLIC_DOMAIN_MARKS)


def build_wikisource_old(
    client: Client, out: Path, pages_per_book: int = 8, log: Log = print
) -> int:
    """Proofread pages from books printed before 1951 whose scans are tagged public domain."""
    books = []
    count = 0
    with ImageFolderWriter(out) as writer:
        for title in wikisource.list_indexes(client):
            index = wikisource.read_index(client, title)
            if index.year is None or index.year > OLD_PRINT_LAST_YEAR:
                continue
            licenses = wikisource.file_licenses(client, index.file)
            if not is_public_domain(licenses):
                log(f"skip {title}: licenses {licenses}")
                continue
            numbers = wikisource.sample_pages(index, pages_per_book)
            kept = 0
            for number in numbers:
                page = wikisource.read_page(client, index, number)
                if page is None:
                    continue
                image = Image.open(io.BytesIO(client.get(page.image_url))).convert("L")
                writer.add(
                    f"ws_{len(books):02d}_{number:04d}",
                    image,
                    page.text,
                    level="page",
                    group=index.file,
                    source=wikisource.wiki_url(page.title),
                    image_url=page.image_url,
                    license=", ".join(licenses),
                    year=index.year,
                    quality=page.quality,
                )
                kept += 1
            books.append(
                {
                    "index": wikisource.wiki_url(title),
                    "file": index.file,
                    "year": index.year,
                    "author": index.fields.get("Author", ""),
                    "licenses": licenses,
                    "pages": kept,
                }
            )
            count += kept
            log(f"{title} ({index.year}): {kept} pages")
    splits = {r["group"]: r["split"] for r in read_jsonl(out / "metadata.jsonl")}
    for book in books:
        book["split"] = splits.get(book["file"])
    (out / "books.json").write_text(json.dumps(books, ensure_ascii=False, indent=1) + "\n")
    log(f"wikisource-old: {count} pages from {len(books)} books")
    return count
