# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

"""Word checks: a Hunspell dictionary called in batches, and a plain English word list."""

from __future__ import annotations

import subprocess
from collections.abc import Iterable
from pathlib import Path


class Hunspell:
    """Answers whether `hunspell -d <dictionary>` accepts a word, from a cache.

    `check_many` fills the cache in 1 call; a word not in it costs 1 call of its own.
    """

    def __init__(self, dictionary: Path) -> None:
        self.dictionary = dictionary
        self.cache: dict[str, bool] = {}

    def check_many(self, words: Iterable[str]) -> None:
        todo = sorted({w for w in words if w and w not in self.cache and "\n" not in w})
        if not todo:
            return
        result = subprocess.run(
            ["hunspell", "-d", str(self.dictionary), "-i", "utf-8", "-l"],
            input="\n".join(todo) + "\n",
            capture_output=True,
            text=True,
            check=True,
        )
        rejected = set(result.stdout.split())
        for w in todo:
            self.cache[w] = w not in rejected

    def __call__(self, word: str) -> bool:
        if word not in self.cache:
            self.check_many([word])
        return self.cache.get(word, False)


class Recorder:
    """A speller that accepts every word and remembers it, for a first pass that collects
    what a real speller will be asked."""

    def __init__(self) -> None:
        self.words: set[str] = set()

    def __call__(self, word: str) -> bool:
        self.words.add(word)
        return True


def word_list(path: Path) -> set[str]:
    """The lowercased words of a list with 1 word per line."""
    return {w.strip().lower() for w in path.read_text(encoding="utf-8").splitlines() if w.strip()}
