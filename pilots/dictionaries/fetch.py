# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

"""Downloads the pilot page images listed in pages.tsv and checks their SHA-256.

Usage: uv run python pilots/dictionaries/fetch.py [--pages pages.tsv] [--data data] [--record]
       [--scan BOOK/SCAN]

Images go to <data>/pilots/dictionaries/<book>/<scan>/<page>.<ext>. --pages names another
page list, relative to this folder. With --record, rows without a checksum get one written
back to the page list; without it, a missing or wrong checksum is an error.

With --zip URL, the zip at URL is downloaded in 1 request instead, and every page whose URL
points into it is taken from it; the zip is deleted afterwards. Each page keeps its own URL
and checksum, so the 2 ways give the same files.
"""

from __future__ import annotations

import argparse
import sys
import urllib.parse
from pathlib import Path

from kannada_ocr.http import Client
from kannada_ocr.pilot import (
    Page,
    extract_pages,
    image_path,
    read_pages,
    sha256_file,
    write_pages,
)

HERE = Path(__file__).resolve().parent


def unzip(client: Client, url: str, pages: list[Page], root: Path) -> None:
    archive = root / "zips" / urllib.parse.unquote(url.rsplit("/", 1)[-1])
    client.download(url, archive)
    extract_pages(archive, url, pages, root)
    archive.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pages", default="pages.tsv")
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--record", action="store_true")
    parser.add_argument("--scan", action="append", help="BOOK/SCAN to fetch")
    parser.add_argument("--zip", help="an archive.org zip that holds the pages")
    args = parser.parse_args()

    every = read_pages(HERE / args.pages)
    pages = [p for p in every if not args.scan or f"{p.book}/{p.scan}" in args.scan]
    client = Client(
        cache_dir=args.data / "cache" / "http",
        log_path=args.data / "sources" / "requests.jsonl",
    )
    root = args.data / "pilots" / "dictionaries"
    if args.zip:
        unzip(client, args.zip, pages, root)
    bad = 0
    for page in pages:
        dest = image_path(root, page)
        client.download(page.url, dest)
        digest = sha256_file(dest)
        if not page.sha256 and args.record:
            page.sha256 = digest
        elif digest != page.sha256:
            print(f"checksum mismatch: {dest} is {digest}, expected {page.sha256}", file=sys.stderr)
            bad += 1
    if args.record:
        write_pages(HERE / args.pages, every)
    print(f"{len(pages) - bad} of {len(pages)} images match {args.pages}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
