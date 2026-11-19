# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

"""Cuts the OCR of Ziegler's English and Canarese school dictionary (1876) into entries.

Ziegler sets each entry with a hanging indent: the English headword starts at the column's
left edge, and the lines after it are indented. An entry is the headword, a part-of-speech
label (s., a., v. a., ...) and Kannada glosses parted by commas and semicolons. Kannada
words are broken across lines without a hyphen. When the last syllables of a line do not
fit, they are set at the right end of the line above, after a bracket: a turnover.
"""

from __future__ import annotations

import csv
import re
import statistics
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field, replace
from pathlib import Path

from kannada_ocr.linematch import fold

INDENT = 0.05
"""A line whose left edge is within this share of the column width from the edge starts an
entry. First lines sit within 3% of the edge, indented lines 7% to 12% in."""
GARBLED = 4
"""A headword read as Kannada comes out as a run of at most this many Kannada characters."""
NOISE = 0.5
"""A segment lower than this share of the column's median segment height is a stray mark."""
NARROW = 0.3
"""A segment narrower than this share of the median segment height is a stray mark too, such
as the column rule read as | or )."""
TURN_GAP = 3.0
"""A gap this many line heights wide before the last segment of a line marks a turnover."""
EDGE = 0.03
"""A turnover ends within this share of the column width from the column's right edge."""
FOOTER_KEY = re.compile(
    r"fool, ?book|ocean, ?action|as ?in ?thou|as ?in ?get|nasal, as|f.r, fall|met, prey|tub, rude"
)
"""Phrases of the pronunciation key printed at the foot of each page, for the few pages where
the rule above it was not found."""
BRACKETS = "[({|"
PUNCT = ".,;:[](){}|"
"""A turnover opens with [ in print; OCR also reads it as (, { or |."""

LABELS = (
    "v. a.", "v. n.", "aux. v.", "p. a.", "s.", "a.", "ad.", "conj.", "int.", "prep.", "pron.",
    "pref.", "pp.", "pt.", "pl.",
)  # fmt: skip
"""The grammatical labels in Ziegler's list of abbreviations, a label that ends another first."""
_LABEL = re.compile(
    r"(?<![\w.])(" + "|".join(re.escape(x).replace(r"\ ", " ?") for x in LABELS) + r")(?= |$|[;,])"
)


Speller = Callable[[str], bool]


@dataclass(frozen=True)
class Row:
    """1 segment of the OCR, as book.py writes it."""

    page: str
    column: str
    line: int
    left: int
    top: int
    right: int
    bottom: int
    conf: float
    text: str


def read_rows(path: Path) -> list[Row]:
    with path.open(encoding="utf-8", newline="") as f:
        return [
            Row(
                r["page"],
                r["column"],
                int(r["line"]),
                int(r["left"]),
                int(r["top"]),
                int(r["right"]),
                int(r["bottom"]),
                float(r["conf"]),
                r["text"],
            )
            for r in csv.DictReader(f, delimiter="\t")
        ]


@dataclass
class Line:
    page: str
    column: str
    line: int
    """The OCR line number in its column."""
    left: int
    top: int
    right: int
    bottom: int
    text: str
    starts: bool = False
    """The line starts an entry."""
    reread: str = ""
    """A Latin-only read of the line's start, if the 2-script read lost its headword."""


@dataclass
class Entry:
    page: str
    column: str
    left: int
    top: int
    right: int
    bottom: int
    text: str
    raw: list[str] = field(default_factory=list)
    """The OCR lines of the entry, with turnovers moved to their lines."""
    reread: str = ""
    """The Latin-only read of the first line, if the entry took its headword and label from it."""


def is_kannada_letter(c: str) -> bool:
    """A Kannada letter or sign; Kannada digits are left out, since Ziegler prints none."""
    return "\u0c80" <= c <= "\u0cff" and not "\u0ce6" <= c <= "\u0cef"


def column_lines(rows: list[Row], speller: Speller | None = None) -> list[Line]:
    """The lines of 1 column, stray marks dropped and turnovers moved to the line below."""
    if not rows:
        return []
    usual = statistics.median(r.bottom - r.top for r in rows)
    # An italic label such as s. is only x-height tall, as low as a stray mark.
    rows = [
        r
        for r in rows
        if _LABEL.fullmatch(r.text.strip())
        or (r.bottom - r.top >= NOISE * usual and r.right - r.left >= NARROW * usual)
    ]
    if not rows:
        return []
    by_line: dict[int, list[Row]] = {}
    for r in rows:
        by_line.setdefault(r.line, []).append(r)
    right_edge = max(r.right for r in rows)
    width = right_edge - min(r.left for r in rows)
    lines: list[Line] = []
    turnovers: list[str | None] = []
    for segs in by_line.values():
        segs.sort(key=lambda r: r.left)
        turn = None
        if len(segs) > 1 and _is_turnover(segs[-2], segs[-1], right_edge, width):
            turn = segs.pop().text.lstrip(BRACKETS).strip()
        elif segs[-1].right >= right_edge - EDGE * width and " [" in segs[-1].text:
            # A turnover set close to the text before it stays in its segment; [ still marks it.
            head, _, tail = segs[-1].text.rpartition(" [")
            segs[-1] = replace(segs[-1], text=head)
            turn = tail.strip()
        lines.append(
            Line(
                page=segs[0].page,
                column=segs[0].column,
                line=segs[0].line,
                left=segs[0].left,
                top=min(r.top for r in segs),
                right=max(r.right for r in segs),
                bottom=max(r.bottom for r in segs),
                text=" ".join(r.text for r in segs),
            )
        )
        turnovers.append(turn)
    kept = [i for i, ln in enumerate(lines) if not FOOTER_KEY.search(ln.text)]
    lines, turnovers = [lines[i] for i in kept], [turnovers[i] for i in kept]
    if not lines:
        return []
    for i, turn in enumerate(turnovers):
        if turn and i + 1 < len(lines):
            lines[i + 1].text = join_break(lines[i + 1].text, turn, speller)
        elif turn:
            lines[i].text = f"{lines[i].text} {turn}"
    lefts = [ln.left for ln in lines]
    edge = statistics.quantiles(lefts, n=10, method="inclusive")[0] if len(lines) > 1 else lefts[0]
    for ln in lines:
        first = ln.text.lstrip(BRACKETS + " ")[:1]
        kannada = bool(first) and is_kannada_letter(first)
        ln.starts = ln.left <= edge + INDENT * width and (not kannada or garbled_head(ln.text))
    return lines


def garbled_head(text: str) -> bool:
    """A line that opens with Kannada but is an entry's first line whose headword was misread:
    a label follows, and every Kannada run before it is short."""
    text = misread_labels(text)
    label = _LABEL.search(_without_kannada_keep_length(text))
    if not label:
        return False
    runs = re.findall(r"[\u0c80-\u0cff\u200c\u200d]+", text[: label.start()])
    return all(len(r) <= GARBLED for r in runs)


def _is_turnover(before: Row, last: Row, right_edge: int, width: int) -> bool:
    if last.right < right_edge - EDGE * width:
        return False
    if last.text[:1] in BRACKETS:
        return True
    # Without its bracket, a turnover is 1 or 2 syllable groups and never holds a label.
    short = len(last.text.split()) <= 2 and not _LABEL.search(last.text)
    return short and last.left - before.right >= TURN_GAP * (last.bottom - last.top)


def join_break(a: str, b: str, speller: Speller | None) -> str:
    """Joins 2 lines of 1 entry.

    A Kannada word cut by the line end is joined without a space. Where both pieces are words
    by themselves and the joined form is not, the break was between words.
    """
    if not a:
        return b
    if not b:
        return a
    if not (is_kannada_letter(a[-1]) and is_kannada_letter(b[0])):
        return f"{a} {b}"
    head = a.split()[-1].strip(PUNCT)
    tail = b.split()[0].strip(PUNCT)
    if speller and speller(head) and speller(tail) and not speller(head + tail):
        return f"{a} {b}"
    return a + b


def entries(lines: Iterable[Line], speller: Speller | None = None) -> list[Entry]:
    """Entries from lines in reading order. A line that does not start an entry continues
    the one before it, across columns and pages."""
    out: list[Entry] = []
    for ln in lines:
        if ln.starts or not out:
            text = merge_reread(ln.text, ln.reread) if ln.reread else ln.text
            out.append(Entry(ln.page, ln.column, ln.left, ln.top, ln.right, ln.bottom, text))
            out[-1].raw.append(ln.text)
            if text != ln.text:
                out[-1].reread = ln.reread
            continue
        e = out[-1]
        e.text = join_break(e.text, ln.text, speller)
        e.raw.append(ln.text)
        if (ln.page, ln.column) == (e.page, e.column):
            e.left, e.right = min(e.left, ln.left), max(e.right, ln.right)
            e.bottom = max(e.bottom, ln.bottom)
    return out


MARKS = str.maketrans(
    {"\u00eb": "\u0115", "\u011b": "\u0115", "\u00f6": "\u014f", "\u00f0": "\u014f"}
)
"""Ziegler prints e and o with a breve (U+0115, U+014F) but never with a diaeresis or caron,
nor an eth. The Latin model has no breve letters and writes those instead."""
PRIME = str.maketrans({"'": "\u2032", "\u2019": "\u2032"})
"""Ziegler's stress mark in a headword is a prime (U+2032); OCR writes an apostrophe."""


def latin_fix(text: str) -> str:
    """Ziegler's letters where the Latin model writes others: barred C and breves.

    The model reads the barred C as the euro sign: a capital (U+A792) at the start of a word,
    a small one (U+A793) inside it.
    """
    text = re.sub(r"(?<=[A-Za-z\u00c0-\u024f\-\u2032'])\u20ac", "\ua793", text)
    return text.replace("\u20ac", "\ua792").translate(MARKS)


def barred_c(headword: str, known: Callable[[str], bool] | None = None) -> str:
    """The headword with `latin_fix`, primes for apostrophes, and a small barred c where OCR
    wrote e.

    An e becomes the barred c only if the headword is not a known word and becomes one
    with c in its place.
    """
    word = latin_fix(headword).translate(PRIME)
    if known is None or known(fold(word).lower()):
        return word
    for i, c in enumerate(word):
        if c == "e":
            trial = word[:i] + "\ua793" + word[i + 1 :]
            if known(fold(trial).lower()):
                return trial
    return word


@dataclass
class Fields:
    headword: str
    plain: str
    """The headword without marks: diacritics, stress primes, syllable hyphens, bars."""
    pos: list[str]
    glosses: list[str]


_JUNK = re.compile(r"^(?:[^\sA-Za-z\u00c0-\u024f\ua792\ua793\u0c80-\u0ce5\u0cf0-\u0cff]+\s+)+")
"""Tokens without a letter before the headword: marks read as digits, bars or quotes."""


def fields_of(text: str) -> Fields:
    """Headword, part-of-speech labels and Kannada glosses of 1 entry's text."""
    text = misread_labels(_JUNK.sub("", text))
    first = next((i for i, c in enumerate(text) if is_kannada_letter(c)), len(text))
    label = _LABEL.search(_without_kannada_keep_length(text))
    end = min(first, label.start()) if label else first
    headword = re.sub(r"\([^)]*\)?", "", text[:end].split(",")[0])
    headword = " ".join(t for t in headword.split() if any(c.isalpha() for c in t)).strip(" .;:")
    pos = [_normal_label(m.group(1)) for m in _LABEL.finditer(_without_kannada(text))]
    glosses = []
    for part in re.split(r"[,;.]", _LABEL.sub(",", text[first:])):
        part = part.strip(" []()|")
        if any(is_kannada_letter(c) for c in part):
            glosses.append(" ".join(part.split()))
    return Fields(headword, fold(headword), pos, glosses)


VERB_MISREADS = {"\u0c86": "a", "\u0c87": "n", "z": "n", "7": "n"}
"""The italic a or n of v. a. and v. n. as OCR reads it: Kannada aa, Kannada i, z, 7."""
SLOT_MISREADS = {
    "\u0c86": "a", "\u0c87": "a", "4": "a", "\u00ab": "a", "e": "a",
    "8": "s", "\u0cef": "s",
}  # fmt: skip
"""The italic label right after the headword's comma as OCR reads it, by what the Latin-only
read of the same lines gives in the Ziegler run: Kannada aa or i, 4, << or e for a.; 8 or
Kannada 9 for s."""


def misread_labels(text: str) -> str:
    """`text` with the label misreads of VERB_MISREADS and SLOT_MISREADS put right."""
    verb = "".join(VERB_MISREADS)
    text = re.sub(
        rf"(?<![\w.])v\. ?([{verb}])\.(?=\s|$)", lambda m: f"v. {VERB_MISREADS[m[1]]}.", text
    )
    slot = "".join(SLOT_MISREADS)
    return re.sub(
        rf"^([^,]*,\s*)([{slot}])\.(?=\s|$)", lambda m: f"{m[1]}{SLOT_MISREADS[m[2]]}.", text
    )


def _normal_label(label: str) -> str:
    """OCR often drops the space inside a 2-part label, as in v.a."""
    return re.sub(r"\.(?=\w)", ". ", label)


def _without_kannada(text: str) -> str:
    """Kannada words become commas, so a label after a gloss is still found."""
    return re.sub(r"[\u0c80-\u0cff\u200c\u200d]+", ",", text)


HIGH_SHARE = 0.5
"""A high-confidence entry has at least this share of gloss words that the Kannada speller
accepts. Ziegler's 1876 spelling is not always the modern one, so the bar is low."""


@dataclass
class Checks:
    known: bool
    """The headword without marks is in the English word list."""
    in_order: bool
    """The headword sorts between its neighbors."""
    has_pos: bool
    has_glosses: bool
    kannada_share: float | None
    """The share of gloss words that the Kannada speller accepts."""

    @property
    def high(self) -> bool:
        return (
            self.known
            and self.in_order
            and self.has_pos
            and self.has_glosses
            and (self.kannada_share or 0.0) >= HIGH_SHARE
        )


def sort_key(plain: str) -> str:
    """The headword as the book sorts it: letters only, lowercased."""
    return "".join(c for c in plain.lower() if c.isalpha())


def in_order(keys: list[str], anchors: list[bool]) -> list[bool]:
    """True for each key that sorts between its nearest anchors, before and after.

    Anchors are the keys that can be trusted as neighbors, for example those of known words,
    so 1 garbled headword does not put the entries around it out of order.
    """
    out = []
    for i, key in enumerate(keys):
        before = next((keys[j] for j in range(i - 1, -1, -1) if anchors[j]), "")
        after = next((keys[j] for j in range(i + 1, len(keys)) if anchors[j]), None)
        out.append(bool(key) and before <= key and (after is None or key <= after))
    return out


def kannada_share(glosses: list[str], speller: Speller) -> float | None:
    words = [w.strip("[]()|") for g in glosses for w in g.split()]
    words = [w for w in words if w and all(is_kannada_letter(c) or c in "\u200c\u200d" for c in w)]
    if not words:
        return None
    return sum(speller(w) for w in words) / len(words)


def latin_letters(text: str) -> bool:
    return any(c.isalpha() and c.isascii() for c in text)


def needs_reread(text: str) -> bool:
    """An entry's first line whose headword or label the 2-script read lost.

    Bold headwords and italic labels are sometimes read as digits or Kannada letters.
    """
    f = fields_of(text)
    return not latin_letters(f.headword) or not f.pos


def merge_reread(text: str, reread: str) -> str:
    """The first line of an entry, with headword and label from a Latin-only read.

    The Latin read gives everything up to and including its first label. The 2-script read
    keeps what follows its own label, or, without one, what follows its first Kannada letter;
    then a Kannada token of 1 or 2 characters right there is the lost label and is dropped.
    """
    # The Latin model sometimes reads the label's full stop as a comma.
    reread = misread_labels(re.sub(r"^([^,]*,\s*)(s|a|ad),(?=\s|$)", r"\1\2.", reread))
    text = misread_labels(text)
    label = _LABEL.search(reread)
    if not label or not latin_letters(reread[: label.start()]):
        return text
    own = _LABEL.search(_without_kannada_keep_length(text))
    if own:
        rest = text[own.end() :]
    else:
        first = next((i for i, c in enumerate(text) if is_kannada_letter(c)), len(text))
        rest = re.sub(r"^[\u0c80-\u0cff]{1,2}[.,]?(?=\s|$)", "", text[first:])
    return f"{reread[: label.end()]} {rest.strip()}".strip()


def _without_kannada_keep_length(text: str) -> str:
    return re.sub(r"[\u0c80-\u0cff\u200c\u200d]", ",", text)
