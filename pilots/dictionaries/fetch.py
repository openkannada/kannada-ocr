# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

"""Downloads the pilot page images listed in pages.tsv and checks their SHA-256.

Usage: uv run python pilots/dictionaries/fetch.py [--data data] [--record]

Images go to <data>/pilots/dictionaries/<book>/<scan>/<page>.<ext>. With --record, rows
without a checksum get one written back to pages.tsv; without it, a missing or wrong
checksum is an error.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from kannada_ocr.http import Client
from kannada_ocr.pilot import image_path, read_pages, sha256_file, write_pages

HERE = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()

    pages = read_pages(HERE / "pages.tsv")
    client = Client(
        cache_dir=args.data / "cache" / "http",
        log_path=args.data / "sources" / "requests.jsonl",
    )
    root = args.data / "pilots" / "dictionaries"
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
        write_pages(HERE / "pages.tsv", pages)
    print(f"{len(pages) - bad} of {len(pages)} images match pages.tsv")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
