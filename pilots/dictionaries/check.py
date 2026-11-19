# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

"""Draws the hand-check sample of Ziegler entries, and scores it once checked.

Usage: uv run python pilots/dictionaries/check.py sample [--data data]
       uv run python pilots/dictionaries/check.py score

`sample` draws SIZE entries: those whose SHA-256 of the seed, scan image, column and top of
the box is smallest. The draw is random but stays the same for an entry whose first line
does not move when the parser changes elsewhere. It writes ziegler-1876/check.tsv with the OCR
fields; the reference columns of an entry already checked at the same place are kept, others
are left empty. It cuts each entry, with the line
before and after it, out of its page image into <data>/pilots/dictionaries/check/, 4 entries
to a sheet. `score` compares the filled-in reference columns with the OCR fields and writes
results/ziegler-1876-check.json and .md, overall and by confidence flag.

Reference columns, filled in by reading the scan: boundary (1 if the OCR entry is exactly 1
printed entry), headword_ref (as printed, with marks), pos_ref, glosses_ref ("; " between
glosses, as printed), and note. Glosses are compared without zero-width joiners.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from kannada_ocr import text
from kannada_ocr.linematch import fold
from kannada_ocr.pilot import image_path, read_pages

HERE = Path(__file__).resolve().parent
BOOK = HERE / "ziegler-1876"
SIZE = 200
SEED = 1876
PER_SHEET = 4
COLUMN_WIDTH = 1250
OCR_FIELDS = ["entry", "page", "image", "column", "box", "confidence", "headword", "pos", "glosses"]
REF_FIELDS = ["boundary", "headword_ref", "pos_ref", "glosses_ref", "note"]


def read_entries() -> list[dict[str, str]]:
    with (BOOK / "entries.tsv").open(encoding="utf-8", newline="") as f:
        lines = (line for line in f if not line.startswith("#"))
        return list(csv.DictReader(lines, delimiter="\t"))


def key(row: dict[str, str]) -> tuple[str, str, str]:
    """An entry's place in the scan: image, column and top of its first line."""
    return row["image"], row["column"], row["box"].split(",")[1]


def draw(row: dict[str, str]) -> str:
    return hashlib.sha256(":".join((str(SEED), *key(row))).encode()).hexdigest()


def sample(data: Path) -> int:
    rows = read_entries()
    chosen = sorted(sorted(rows, key=draw)[:SIZE], key=lambda r: int(r["entry"]))
    out = BOOK / "check.tsv"
    done: dict[tuple[str, str, str], dict[str, str]] = {}
    if out.exists():
        with out.open(encoding="utf-8", newline="") as f:
            done = {key(r): r for r in csv.DictReader(f, delimiter="\t")}
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(OCR_FIELDS + REF_FIELDS)
        for r in chosen:
            old = done.get(key(r), {})
            writer.writerow([r[k] for k in OCR_FIELDS] + [old.get(k, "") for k in REF_FIELDS])
    missing = [r["entry"] for r in chosen if key(r) not in done]
    print(f"{len(chosen) - len(missing)} entries keep their check; to check: {' '.join(missing)}")
    root = data / "pilots" / "dictionaries"
    pages = {p.page: p for p in read_pages(BOOK / "pages.tsv")}
    sheets = root / "check"
    sheets.mkdir(parents=True, exist_ok=True)
    for start in range(0, len(chosen), PER_SHEET):
        strips = []
        for r in chosen[start : start + PER_SHEET]:
            left, top, right, bottom = map(int, r["box"].split(","))
            page = Image.open(image_path(root, pages[r["image"]])).convert("RGB")
            # The line above and below show whether the entry was cut at the right place.
            # A column is about 1250 px wide; the box can be narrower than its column.
            right = max(right, left + COLUMN_WIDTH)
            strip = page.crop((left - 40, top - 130, right + 40, bottom + 130))
            label = Image.new("RGB", (strip.width, 50), "white")
            ImageDraw.Draw(label).text((10, 10), f"entry {r['entry']}", fill="red")
            strips += [label, strip]
        sheet = Image.new("RGB", (max(s.width for s in strips), sum(s.height for s in strips)))
        y = 0
        for s in strips:
            sheet.paste(s, (0, y))
            y += s.height
        sheet.save(sheets / f"{start // PER_SHEET + 1:02d}.png")
    print(f"{len(chosen)} entries, {len(range(0, len(chosen), PER_SHEET))} sheets in {sheets}")
    return 0


def split(glosses: str) -> list[str]:
    """The glosses of a cell, joiners (U+200C, U+200D) left out: print does not show them."""
    glosses = glosses.replace("\u200c", "").replace("\u200d", "")
    return [g.strip() for g in glosses.split(";") if g.strip()]


def summarize(rows: list[dict[str, str]]) -> dict[str, object]:
    """Counts over `rows`. Boundary is judged on every row; the fields only on rows that are
    printed entries (a reference headword), since a cut that is no entry has no true fields."""
    n = len(rows)
    if not n:
        return {"entries": 0}
    real = [r for r in rows if r["headword_ref"]]
    exact = sum(r["headword"] == r["headword_ref"] for r in real)
    plain = sum(fold(r["headword"]).lower() == fold(r["headword_ref"]).lower() for r in real)
    pos = sum(r["pos"] == r["pos_ref"] for r in real)
    ref_glosses = [g for r in real for g in split(r["glosses_ref"])]
    found = sum(len(set(split(r["glosses_ref"])) & set(split(r["glosses"]))) for r in real)
    pairs = [
        (r["entry"], "; ".join(split(r["glosses_ref"])), "; ".join(split(r["glosses"])))
        for r in real
        if r["glosses_ref"] or r["glosses"]
    ]
    scored = text.score(pairs)["summary"] if pairs else None
    return {
        "entries": n,
        "boundary": sum(r["boundary"] == "1" for r in rows),
        "real": len(real),
        "headword_exact": exact,
        "headword_plain": plain,
        "pos": pos,
        "glosses": len(ref_glosses),
        "glosses_exact": found,
        "gloss_cer": round(scored["cer"], 4) if scored else None,
        "gloss_chars": scored["chars"]["reference"] if scored else 0,
        "all_right": sum(
            r["boundary"] == "1"
            and r["headword"] == r["headword_ref"]
            and r["pos"] == r["pos_ref"]
            and split(r["glosses"]) == split(r["glosses_ref"])
            for r in rows
        ),
    }


def score() -> int:
    with (BOOK / "check.tsv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    if any(not r["boundary"] for r in rows):
        print("check.tsv has rows without a boundary judgment", file=sys.stderr)
        return 1
    result = {
        "all": summarize(rows),
        "high": summarize([r for r in rows if r["confidence"] == "high"]),
        "low": summarize([r for r in rows if r["confidence"] == "low"]),
    }
    results = HERE / "results"
    (results / "ziegler-1876-check.json").write_text(
        json.dumps(result, indent=1) + "\n", encoding="utf-8"
    )
    (results / "ziegler-1876-check.md").write_text(table(result), encoding="utf-8")
    print(table(result))
    return 0


def table(result: dict[str, dict]) -> str:
    def cell(s: dict, field: str, total: str = "entries") -> str:
        return f"{s[field]} of {s[total]} ({100 * s[field] / s[total]:.1f}%)" if s[total] else ""

    head = (
        "| Entries | Count | Real entry boundary | Headword exact | Headword without marks "
        "| Part of speech | Glosses exactly right | Gloss CER | Entry all right |\n"
        "|---|---|---|---|---|---|---|---|---|\n"
    )
    rows = []
    for name, s in result.items():
        if not s.get("entries"):
            continue
        cer = "" if s["gloss_cer"] is None else f"{100 * s['gloss_cer']:.1f}%"
        rows.append(
            f"| {name} | {s['entries']} | {cell(s, 'boundary')} "
            f"| {cell(s, 'headword_exact', 'real')} | {cell(s, 'headword_plain', 'real')} "
            f"| {cell(s, 'pos', 'real')} "
            f"| {cell(s, 'glosses_exact', 'glosses')} | {cer} | {cell(s, 'all_right')} |"
        )
    return head + "\n".join(rows) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("step", choices=["sample", "score"])
    parser.add_argument("--data", type=Path, default=Path("data"))
    args = parser.parse_args()
    return sample(args.data) if args.step == "sample" else score()


if __name__ == "__main__":
    sys.exit(main())
