# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

"""Downloads the Tesseract models listed in models.tsv and checks their SHA-256.

Usage: uv run python pilots/dictionaries/fetch_models.py --tessdata DIR [--data data] [--record]

Each model is saved as DIR/<name>.traineddata, so `-l <name>` selects it. With --record, rows
without a checksum get one written back to models.tsv.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from kannada_ocr.http import Client
from kannada_ocr.pilot import sha256_file

HERE = Path(__file__).resolve().parent
FIELDS = ["name", "url", "sha256", "license"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tessdata", type=Path, required=True)
    parser.add_argument("--data", type=Path, default=Path("data"))
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()

    path = HERE / "models.tsv"
    with path.open(encoding="utf-8", newline="") as f:
        models = list(csv.DictReader(f, delimiter="\t"))
    client = Client(
        cache_dir=args.data / "cache" / "http",
        log_path=args.data / "sources" / "requests.jsonl",
    )
    bad = 0
    for model in models:
        dest = client.download(model["url"], args.tessdata / f"{model['name']}.traineddata")
        digest = sha256_file(dest)
        if not model["sha256"] and args.record:
            model["sha256"] = digest
        elif digest != model["sha256"]:
            print(f"checksum mismatch: {dest} is {digest}", file=sys.stderr)
            bad += 1
    if args.record:
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, FIELDS, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(models)
    print(f"{len(models) - bad} of {len(models)} models match models.tsv")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
