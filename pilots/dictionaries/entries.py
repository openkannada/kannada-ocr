# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

"""Cuts the OCR of Ziegler 1876 into entries, with fields and a confidence flag.

Usage: uv run python pilots/dictionaries/entries.py --kannada-dict PATH [--data data]

Reads ziegler-1876/ocr-lines.tsv (from book.py) and writes ziegler-1876/entries.tsv.
PATH is the kn_IN Hunspell dictionary of kannada-spell (dict/kn_IN at commit
KANNADA_SPELL_COMMIT), without its extension. The English
word list is Webster's Second International (1934, public domain) as FreeBSD ships it,
downloaded once through the repository's HTTP client and checked against its SHA-256.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path

from kannada_ocr.http import Client
from kannada_ocr.linematch import fold
from kannada_ocr.pilot import sha256_file
from kannada_ocr.spelling import Hunspell, Recorder, word_list
from kannada_ocr.ziegler import (
    Checks,
    Entry,
    Line,
    Row,
    barred_c,
    column_lines,
    entries,
    fields_of,
    in_order,
    kannada_share,
    needs_reread,
    read_rows,
    sort_key,
)

HERE = Path(__file__).resolve().parent
BOOK = HERE / "ziegler-1876"
WORDS_URL = (
    "https://raw.githubusercontent.com/freebsd/freebsd-src/"
    "3ccfcdacd6ae7611dc0f2a1375713dc0111c3d5f/share/dict/web2"
)
WORDS_SHA256 = "92165d95d72a67377e80052b1b9c3d63a4ac402ccd71690c89d949e809738238"
FIRST, LAST = 17, 576
"""The scan images of dictionary pages 1 to 560; printed page = image - OFFSET. Later images
hold the additions and corrections, set differently, and are left out."""
OFFSET = 16
KANNADA_SPELL_COMMIT = "9366c23"
"""The commit of github.com/openkannada/kannada-spell whose kn_IN dictionary gave the shares."""
HEADER = """\
# Ziegler 1876 entries, from OCR, not proofread
# Source: F. Ziegler, A School-Dictionary, English and Canarese, 1st edition, Basel Mission
#   Book & Tract Depository, Mangalore, 1876. The text is in the public domain.
# Scan: Google Books 13EIAAAAQAAJ, as archive.org item
#   ziegler-a-school-dictionary-english-and-canarese; every page with its URL and SHA-256 is
#   in pages.tsv. No image is copied here.
# OCR: Tesseract 5.5.4, LSTM, kan_ft_ofl3 (kannada-ocr v0.2.0) plus tessdata_best
#   script/Latin, each column read with page segmentation mode 6.
# License: this file is CC BY 4.0, The Open Kannada Authors.
# Columns: entry number; printed page; scan image; column (L or R); box in the image
#   (left,top,right,bottom; the first column's box if the entry runs on); headword as read,
#   with marks; headword without marks; part-of-speech labels, "; " between them; Kannada
#   glosses, "; " between them; share of gloss words that the kn_IN Hunspell dictionary of
#   kannada-spell (commit {spell}) accepts; headword in the English word list (1 or 0);
#   headword sorts between its neighbors (1 or 0); confidence (high or low); entry text as
#   joined; OCR lines as read, with turnovers moved to their lines, " / " between them; a
#   Latin-only read of the first line, where the 2-script read lost the headword or label
#   and the entry took them from it ({reread} entries).
"""
FIELDS = [
    "entry",
    "page",
    "image",
    "column",
    "box",
    "headword",
    "headword_plain",
    "pos",
    "glosses",
    "kannada_share",
    "known",
    "in_order",
    "confidence",
    "text",
    "ocr_lines",
    "latin_reread",
]


def book_lines(rows: list[Row], speller) -> list[Line]:
    """The lines of the dictionary pages in reading order: page by page, left column first."""
    columns: dict[tuple[str, str], list[Row]] = {}
    for r in rows:
        if r.column in "LR" and FIRST <= int(r.page) <= LAST:
            columns.setdefault((r.page, r.column), []).append(r)
    lines = []
    for key in sorted(columns):
        lines += column_lines(columns[key], speller)
    return lines


def read_rereads(path: Path) -> dict[tuple[str, str, int], str]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as f:
        return {
            (r["page"], r["column"], int(r["line"])): r["text"]
            for r in csv.DictReader(f, delimiter="\t")
        }


def cut(rows: list[Row], rereads: dict[tuple[str, str, int], str], speller) -> list[Entry]:
    lines = book_lines(rows, speller)
    for ln in lines:
        reread = rereads.get((ln.page, ln.column, ln.line))
        if ln.starts and reread and needs_reread(ln.text):
            ln.reread = reread
    return entries(lines, speller)


def head_pages(rows: list[Row]) -> Counter:
    """How many running heads show the printed page that the image number gives."""
    seen: Counter = Counter()
    for r in rows:
        if r.column == "H" and FIRST <= int(r.page) <= LAST and re.fullmatch(r"\d+", r.text):
            seen[int(r.text) == int(r.page) - OFFSET] += 1
    return seen


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--kannada-dict", type=Path, required=True)
    parser.add_argument("--data", type=Path, default=Path("data"))
    args = parser.parse_args()

    client = Client(
        cache_dir=args.data / "cache" / "http",
        log_path=args.data / "sources" / "requests.jsonl",
    )
    words_path = client.download(WORDS_URL, args.data / "wordlists" / "web2")
    if sha256_file(words_path) != WORDS_SHA256:
        print(f"{words_path} does not match its SHA-256", file=sys.stderr)
        return 1
    english = word_list(words_path)

    rows = read_rows(BOOK / "ocr-lines.tsv")
    rereads = read_rereads(BOOK / "ocr-reread.tsv")
    recorder = Recorder()
    found = cut(rows, rereads, recorder)
    speller = Hunspell(args.kannada_dict)
    gloss_words = [w for e in found for g in fields_of(e.text).glosses for w in g.split()]
    speller.check_many([*recorder.words, *gloss_words])
    found = cut(rows, rereads, speller)

    fields = [fields_of(e.text) for e in found]
    known = english.__contains__
    for f in fields:
        f.headword = barred_c(f.headword, known)
        f.plain = fold(f.headword)
    keys = [sort_key(f.plain) for f in fields]
    knowns = [k in english for k in keys]
    order = in_order(keys, knowns)
    out = BOOK / "entries.tsv"
    high = 0
    with out.open("w", encoding="utf-8", newline="") as f:
        reread = sum(bool(e.reread) for e in found)
        f.write(HEADER.format(spell=KANNADA_SPELL_COMMIT, reread=f"{reread:,}"))
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(FIELDS)
        for n, (e, fl) in enumerate(zip(found, fields, strict=True)):
            share = kannada_share(fl.glosses, speller)
            checks = Checks(knowns[n], order[n], bool(fl.pos), bool(fl.glosses), share)
            high += checks.high
            writer.writerow(
                [
                    n + 1,
                    int(e.page) - OFFSET,
                    e.page,
                    e.column,
                    f"{e.left},{e.top},{e.right},{e.bottom}",
                    fl.headword,
                    fl.plain,
                    "; ".join(fl.pos),
                    "; ".join(fl.glosses),
                    "" if share is None else f"{share:.2f}",
                    int(checks.known),
                    int(checks.in_order),
                    "high" if checks.high else "low",
                    e.text,
                    " / ".join(e.raw),
                    e.reread,
                ]
            )
    print(f"{len(found)} entries, {high} high ({100 * high / len(found):.1f}%)")
    print(f"running heads that agree with the page offset: {dict(head_pages(rows))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
