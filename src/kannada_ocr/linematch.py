# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

"""Scores page OCR against a sample of hand-transcribed lines.

Each reference line is matched to the stretch of the page's OCR text closest to it by edit
distance, so a page is scored without transcribing all of it. If the OCR reads across
both columns, the closest stretch mixes in text from the other column and scores badly,
as it should. The text of each script is then scored on its own.
"""

from __future__ import annotations

import unicodedata

from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein

JOINERS = {"\u200c", "\u200d"}
BARRED_C = str.maketrans({"\ua792": "C", "\ua793": "c"})
"""Ziegler bars a C that sounds like k. Plain print and OCR have only C."""
STRESS = "'\u2019\u2032"
PUNCTUATION = ".,;:()[]!?\"'\u2018\u2019\u201c\u201d"


def script_of(c: str) -> str | None:
    """ "kn" for the Kannada block and joiners, "la" for Latin letters, else None."""
    if "\u0c80" <= c <= "\u0cff" or c in JOINERS:
        return "kn"
    if c.isalpha() and "LATIN" in unicodedata.name(c, ""):
        return "la"
    return None


def project(text: str, script: str) -> str:
    """The words of 1 script in `text`, 1 space apart.

    A combining mark after a Latin letter belongs to it. The stress primes Ziegler prints
    inside English words are dropped without ending the word, since OCR writes them as
    U+0027, U+2019 or U+2032 at random. Everything else ends a word.
    """
    words: list[str] = []
    current: list[str] = []
    previous = None
    for c in unicodedata.normalize("NFC", text):
        if previous == "la" and c in STRESS:
            continue
        kind = script_of(c)
        if kind is None and previous == "la" and unicodedata.combining(c):
            kind = "la"
        if kind == script:
            current.append(c)
        elif current:
            words.append("".join(current))
            current = []
        previous = kind
    if current:
        words.append("".join(current))
    return " ".join(words)


def flatten(page: str) -> str:
    return " ".join(unicodedata.normalize("NFC", page).split())


def closest_stretch(reference: str, page: str) -> str:
    """The stretch of `page` with the least edit distance to `reference`.

    A fuzzy partial match finds the area, then both ends move up to a quarter of the
    reference length to the cut with the least distance.
    """
    reference = flatten(reference)
    page = flatten(page)
    if not reference or not page:
        return ""
    found = fuzz.partial_ratio_alignment(reference, page)
    if found is None:
        return ""
    reach = max(8, len(reference) // 4)
    start = page[found.dest_start : found.dest_end]
    best = (Levenshtein.distance(reference, start), start)
    for a in range(max(0, found.dest_start - reach), found.dest_start + reach + 1):
        stop = min(len(page), found.dest_end + reach)
        for b in range(max(a + 1, found.dest_end - reach), stop + 1):
            d = Levenshtein.distance(reference, page[a:b], score_cutoff=best[0])
            if d < best[0] or (d == best[0] and b - a < len(best[1])):
                best = (d, page[a:b])
    return best[1].strip()


def _tokens(text: str) -> list[str]:
    """Words without outer punctuation or joiners, with every stress prime as U+2032."""
    words = (w.strip(PUNCTUATION) for w in flatten(text).split())
    words = ("".join(c for c in w if c not in JOINERS) for w in words)
    return [w.replace("'", "\u2032").replace("\u2019", "\u2032") for w in words if w]


def headword_found(headword: str, text: str) -> bool:
    """True if the words of `headword` appear in `text` in order, exactly, punctuation aside."""
    want = _tokens(headword)
    have = _tokens(text)
    if not want:
        raise ValueError("empty headword")
    return any(have[i : i + len(want)] == want for i in range(len(have) - len(want) + 1))


def fold(text: str) -> str:
    """`text` without Latin diacritics, stress primes, syllable hyphens or barred C.

    Kannada is kept as is.
    """
    bare = unicodedata.normalize("NFD", text.translate(BARRED_C))
    kept = (c for c in bare if c not in STRESS and c != "-")
    folded = "".join(c for c in kept if script_of(c) == "kn" or not unicodedata.combining(c))
    return unicodedata.normalize("NFC", folded)
