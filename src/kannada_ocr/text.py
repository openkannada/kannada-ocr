"""Calls the `kocr-text` Rust binary, which wraps the kannadi crate."""

from __future__ import annotations

import json
import os
import subprocess
from functools import cache
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]


@cache
def binary() -> Path:
    """The `kocr-text` binary: `$KOCR_TEXT`, else the release build in `$CARGO_TARGET_DIR`
    or in this repo."""
    target = Path(os.environ.get("CARGO_TARGET_DIR", REPO / "target"))
    path = Path(os.environ.get("KOCR_TEXT", target / "release" / "kocr-text"))
    if not path.exists():
        raise FileNotFoundError(f"{path} is missing; run `cargo build --release` first")
    return path


def _run(command: str, stdin: str) -> str:
    result = subprocess.run(
        [binary(), command], input=stdin, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(f"kocr-text {command}: {result.stderr.strip()}")
    return result.stdout


def _one_per_line(lines: list[str]) -> str:
    if any("\n" in line or "\r" in line for line in lines):
        raise ValueError("each item must be a single line")
    return "".join(line + "\n" for line in lines)


TELUGU_TO_KANNADA = {c: c + 0x80 for c in range(0x0C00, 0x0C80)}
"""Unicode lays out Telugu (U+0C00) and Kannada (U+0C80) in parallel, 0x80 apart."""


def telugu_as_kannada(hypothesis: str) -> str:
    """Moves Telugu code points to the parallel Kannada ones.

    A diagnostic: it shows how much of a model's error is writing the wrong script.
    """
    return hypothesis.translate(TELUGU_TO_KANNADA)


def other_indic_script(hypothesis: str) -> bool:
    """True if the text has a letter from an Indic block other than Kannada (U+0900 to U+0DFF)."""
    return any(
        "\u0900" <= c <= "\u0dff" and not "\u0c80" <= c <= "\u0cff" and c.isalpha()
        for c in hypothesis
    )


def normalize(lines: list[str]) -> list[str]:
    """kannadi normalization for each single-line string."""
    return _run("normalize", _one_per_line(lines)).splitlines()


def aksharas(lines: list[str]) -> list[list[str]]:
    """kannadi akshara segments for each single-line string."""
    return [json.loads(row) for row in _run("aksharas", _one_per_line(lines)).splitlines()]


def to_nudi(lines: list[str]) -> list[str | None]:
    """Each line in Nudi and Baraha ANSI glyph codes, or None if kannadi cannot encode it
    exactly (a Latin letter, or an ill-formed akshara)."""
    rows = [json.loads(row) for row in _run("to-nudi", _one_per_line(lines)).splitlines()]
    return [row["text"] if row["clean"] else None for row in rows]


def score(pairs: list[tuple[str, str, str]]) -> dict[str, Any]:
    """CER, WER and akshara error rate for (id, reference, hypothesis) triples."""
    stdin = "".join(
        json.dumps({"id": i, "ref": r, "hyp": h}, ensure_ascii=False) + "\n" for i, r, h in pairs
    )
    return json.loads(_run("score", stdin))
