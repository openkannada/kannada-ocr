# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

"""Hugging Face ImageFolder layout: `images/` plus a `metadata.jsonl` with 1 row per image.

`datasets.load_dataset("imagefolder", data_dir=...)` reads this layout directly.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image


def assign_splits(groups: set[str], dev_fraction: float = 0.2) -> dict[str, str]:
    """A stable `dev` or `test` split per group, such as a book.

    Groups are ordered by a hash of their name and the first `dev_fraction` of them,
    at least 1, go to `dev`. Whole books go to 1 split, so a model tuned on `dev`
    never sees a `test` book's typeface.
    """
    ordered = sorted(groups, key=lambda g: hashlib.sha256(g.encode()).hexdigest())
    dev = max(1, round(len(ordered) * dev_fraction)) if ordered else 0
    return {g: ("dev" if i < dev else "test") for i, g in enumerate(ordered)}


class ImageFolderWriter:
    """Writes images and their metadata rows. Use as a context manager.

    Rows given a `group` and no `split` get 1 from `assign_splits` on exit.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.images = root / "images"
        self.rows: list[dict[str, Any]] = []

    def __enter__(self) -> ImageFolderWriter:
        self.images.mkdir(parents=True, exist_ok=True)
        return self

    def add(self, item_id: str, image: Image.Image, text: str, **fields: Any) -> None:
        file_name = f"images/{item_id}.png"
        image.save(self.root / file_name, optimize=True)
        self.rows.append({"file_name": file_name, "id": item_id, "text": text, **fields})

    def __exit__(self, *exc: object) -> None:
        if exc[0] is not None:
            return
        splits = assign_splits({r["group"] for r in self.rows if "split" not in r})
        for row in self.rows:
            row.setdefault("split", splits.get(row.get("group", "")))
        write_jsonl(self.root / "metadata.jsonl", self.rows)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: Path, allow_torn_tail: bool = False) -> list[dict[str, Any]]:
    """Rows of a JSON-lines file. With `allow_torn_tail`, a last line cut off by a
    killed writer is dropped instead of raising."""
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = []
    for i, line in enumerate(lines):
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            if not (allow_torn_tail and i == len(lines) - 1):
                raise
    return rows
