# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

import pytest

from kannada_ocr import text


def test_normalize_and_aksharas_use_kannadi():
    assert text.normalize(["ಕೀ"]) == ["ಕೀ"]
    assert text.aksharas(["ಕನ್ನಡ"]) == [["ಕ", "ನ್ನ", "ಡ"]]


def test_score_counts_akshara_errors():
    report = text.score([("a", "ಸ್ತ್ರೀ ಶಕ್ತಿ", "ಸ್ತೀ ಶಕ್ತಿ")])
    assert report["summary"]["aksharas"] == {"edits": 1, "reference": 4}
    assert report["items"][0]["id"] == "a"


def test_telugu_letters_move_to_the_parallel_kannada_ones():
    assert text.telugu_as_kannada("కన్నడ abc ಕ") == "ಕನ್ನಡ abc ಕ"


def test_other_indic_scripts_are_flagged_but_not_kannada_or_latin():
    assert text.other_indic_script("ಕನ್ನಡ నాడు")
    assert text.other_indic_script("தமிழ்")
    assert not text.other_indic_script("ಕನ್ನಡ ISO 9001 ।")


def test_multiline_items_are_rejected():
    with pytest.raises(ValueError):
        text.normalize(["ಕ\nಖ"])


def test_to_nudi_gives_glyph_codes_or_none_when_not_exact():
    assert text.to_nudi(["ಕನ್ನಡ", "ಕನ್ನಡ ISO"]) == ["PÀ£ÀßqÀ", None]
