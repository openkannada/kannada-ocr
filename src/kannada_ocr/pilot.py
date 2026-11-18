# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

"""The page list of an OCR pilot: which scan pages, from where, with which checksum."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass, fields
from pathlib import Path


@dataclass
class Page:
    book: str
    scan: str
    page: str
    """The printed page number, or "title" for the title page."""
    url: str
    sha256: str


def read_pages(path: Path) -> list[Page]:
    with path.open(encoding="utf-8", newline="") as f:
        return [Page(**row) for row in csv.DictReader(f, delimiter="\t")]


def write_pages(path: Path, pages: list[Page]) -> None:
    names = [f.name for f in fields(Page)]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(names)
        for page in pages:
            writer.writerow([getattr(page, n) for n in names])


def image_path(root: Path, page: Page) -> Path:
    suffix = Path(page.url.rsplit("%2F", 1)[-1]).suffix or ".jpg"
    return root / page.book / page.scan / f"{page.page}{suffix}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()
