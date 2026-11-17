# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

"""A markdown table of the summaries under `results/` for 1 split."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

SET_ORDER = ("mile-lines", "degraded-words", "wikisource-old", "mile-pages")


def table(results: Path, split: str = "test") -> str:
    summaries = [json.loads(p.read_text()) for p in sorted(results.glob("*/*.json"))]
    summaries = [s for s in summaries if s.get("split", "test") == split]
    summaries.sort(
        key=lambda s: (SET_ORDER.index(s["set"]), -s["items"], s["model"], s.get("transform") or "")
    )
    lines = [
        "| Set | Items | Model | CER | WER | AER | Wrong script | Seconds per item |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for s in (s for s in summaries if s["items"]):
        model = s["model"] + (f" ({s['transform']})" if s.get("transform") else "")
        items = f"{s['items']}" + (
            f" of {s['sampled_from']}" if s["items"] < s["sampled_from"] else ""
        )
        lines.append(
            f"| {s['set']} | {items} | {model} | {s['cer']:.1%} | {s['wer']:.1%} "
            f"| {s['aer']:.1%} | {s.get('wrong_script_items', 0) / s['items']:.1%} "
            f"| {s['seconds_per_item']:.2f} |"
        )
    return "\n".join(lines) + "\n"


def by_book(results: Path, set_name: str, split: str = "test") -> str:
    """A markdown table of CER per book for every model scored on the same items of a set.

    Models are compared on the item count most of them share, which is the fixed sample. The
    lowest CER in each row is in bold.
    """
    summaries = [json.loads(p.read_text()) for p in sorted(results.glob(f"*/{set_name}.*.json"))]
    summaries = [s for s in summaries if s.get("split", "test") == split and not s.get("transform")]
    if not summaries:
        return ""
    shared = Counter(s["items"] for s in summaries).most_common(1)[0][0]
    chosen = sorted((s for s in summaries if s["items"] == shared), key=lambda s: s["model"])
    books = sorted({book for s in chosen for book in s["cer_by_group"]})
    lines = [
        "| Book | " + " | ".join(s["model"] for s in chosen) + " |",
        "|---|" + "---|" * len(chosen),
    ]
    for book in books:
        cers = [s["cer_by_group"].get(book) for s in chosen]
        best = min(c for c in cers if c is not None)
        cells = ["" if c is None else (f"**{c:.1%}**" if c == best else f"{c:.1%}") for c in cers]
        lines.append(f"| {book} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"
