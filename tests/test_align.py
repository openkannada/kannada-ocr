# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

import pytest

from kannada_ocr import text
from kannada_ocr.align import OcrLine, align, boundaries, read_tsv

REFERENCE = (
    "ಅದೆಷ್ಟೋ ಕಾಲದ ಮಾತು. ಒಂದು ದಿನ, ಸಂಜೆಯ ಹೊತ್ತಿನಲ್ಲಿ ಏಳು ವರ್ಷದ ಒಬ್ಬ ಹುಡುಗಿ "
    "ಭಾಗೀರಥಿಯ ತೀರದಲ್ಲಿ ಒಂದು ದೀಪವನ್ನು ತೇಲಿಬಿಟ್ಟಳು. ತಾಯ ಕತೆಗಳನ್ನು ಕೇಳುವರು."
)


@pytest.fixture(scope="module")
def segments():
    return text.aksharas([REFERENCE])[0]


def line(reading, top=0):
    return OcrLine((0, top, 100, top + 20), reading)


def labels(segments, readings):
    lines = [line(r, 30 * i) for i, r in enumerate(readings)]
    return [label for _, label in align(REFERENCE, segments, lines)]


def test_tsv_lines_keep_reading_order_and_skip_empty_lines():
    header = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext"
    rows = [
        "4\t1\t1\t1\t1\t0\t10\t20\t300\t30\t-1\t",
        "5\t1\t1\t1\t1\t1\t10\t20\t100\t30\t91\tಒಂದು",
        "5\t1\t1\t1\t1\t2\t120\t20\t100\t30\t88\tದಿನ",
        "4\t1\t1\t1\t2\t0\t10\t60\t300\t30\t-1\t",
        "5\t1\t1\t1\t2\t1\t10\t60\t100\t30\t-1\t ",
        "4\t1\t2\t1\t1\t0\t10\t100\t200\t30\t-1\t",
        "5\t1\t2\t1\t1\t1\t10\t100\t200\t30\t70\tಮಾತು",
    ]
    lines = read_tsv("\n".join([header, *rows]))
    assert lines == [OcrLine((10, 20, 310, 50), "ಒಂದು ದಿನ"), OcrLine((10, 100, 210, 130), "ಮಾತು")]


def test_boundaries_include_both_ends():
    assert boundaries(["ಕ್ಷ", " ", "ಮಾ"]) == [0, 3, 4, 6]


def test_labels_are_proofread_text_despite_reading_errors(segments):
    assert labels(
        segments,
        [
            "ಅದೆಷ್ಟೊ ಕಾಲದ ಮಾತು. ಒಂದು ದಿನ, ಸಂಜೆಯ ಹೊತ್ತಿನಲ್ಲ ಏಳು",
            "ವರ್ಷದ ಒಬ್ಬ ಹುಡುಗಿ ಭಾಗೀರಧಿಯ ತೀರದಲ್ಲಿ",
        ],
    ) == [
        "ಅದೆಷ್ಟೋ ಕಾಲದ ಮಾತು. ಒಂದು ದಿನ, ಸಂಜೆಯ ಹೊತ್ತಿನಲ್ಲಿ ಏಳು",
        "ವರ್ಷದ ಒಬ್ಬ ಹುಡುಗಿ ಭಾಗೀರಥಿಯ ತೀರದಲ್ಲಿ",
    ]


def test_a_word_broken_across_lines_is_cut_between_aksharas(segments):
    assert labels(
        segments,
        ["ಒಂದು ದೀಪವನ್ನು ತೇಲಿಬಿಟ್ಟಳು. ತಾಯ ಕತೆ", "ಗಳನ್ನು ಕೇಳುವರು."],
    ) == ["ಒಂದು ದೀಪವನ್ನು ತೇಲಿಬಿಟ್ಟಳು. ತಾಯ ಕತೆ", "ಗಳನ್ನು ಕೇಳುವರು."]


def test_poor_readings_short_lines_and_hyphenated_lines_are_dropped(segments):
    assert labels(
        segments,
        [
            "ಅದೆಷ್ಟೋ ಕಾಲದ ಮಾತು. ಒಂದು ದಿನ, ಸಂಜೆಯ ಹೊತ್ತಿನಲ್ಲಿ ಏಳು",
            "೧೨",
            "ಟಿಪ್ಪಣಿ ರಾಮ ಸೀತೆ ಲಕ್ಷ್ಮಣ ಭರತ ಶತ್ರುಘ್ನ",
            "ವರ್ಷದ ಒಬ್ಬ ಹುಡುಗಿ ಭಾಗೀರ-",
        ],
    ) == ["ಅದೆಷ್ಟೋ ಕಾಲದ ಮಾತು. ಒಂದು ದಿನ, ಸಂಜೆಯ ಹೊತ್ತಿನಲ್ಲಿ ಏಳು"]


def test_a_line_whose_edges_were_misread_is_dropped(segments):
    assert labels(segments, ["ಜಿಡಿ ಒಬ್ಬ ಹುಡುಗಿ ಭಾಗೀರಥಿಯ ತೀರದಲ್ಲಿ"]) == []


def test_lines_after_several_unmatched_lines_are_still_found(segments):
    assert labels(
        segments,
        ["ಟಿಪ್ಪಣಿ ರಾಮ ಸೀತೆ ಲಕ್ಷ್ಮಣ ಭರತ", "ಟಿಪ್ಪಣಿ ಸೀತೆ ಲಕ್ಷ್ಮಣ ರಾಮ ಭರತ", "ಭಾಗೀರಥಿಯ ತೀರದಲ್ಲಿ ಒಂದು ದೀಪವನ್ನು"],
    ) == ["ಭಾಗೀರಥಿಯ ತೀರದಲ್ಲಿ ಒಂದು ದೀಪವನ್ನು"]


def test_text_is_not_matched_twice(segments):
    first = "ವರ್ಷದ ಒಬ್ಬ ಹುಡುಗಿ ಭಾಗೀರಥಿಯ ತೀರದಲ್ಲಿ"
    assert labels(segments, [first, first]) == [first]


def test_segments_must_cover_the_reference():
    with pytest.raises(ValueError):
        align(REFERENCE, ["ಅ"], [])


def test_a_reading_far_from_the_text_between_matching_edges_is_dropped(segments):
    assert labels(segments, ["ವರ್ಷದ ಜಜಜಜ ಜಜಜಜ ಜಜಜ ಜಜಜಜ ತೀರದಲ್ಲಿ"]) == []


def test_a_misread_first_word_still_starts_the_label_at_an_akshara(segments):
    found = labels(segments, ["ಏಳು ವರ್ಷದ ಒಬ್ಬ ಹುಡುಗಿ", "ಭಾಗೀರಥಿಯ ತೀರದದದಲ್ಲಿ ಒಂದು ದೀಪವನ್ನು"])
    assert found == ["ಏಳು ವರ್ಷದ ಒಬ್ಬ ಹುಡುಗಿ", "ಭಾಗೀರಥಿಯ ತೀರದಲ್ಲಿ ಒಂದು ದೀಪವನ್ನು"]


def test_the_search_reaches_past_many_unmatched_lines():
    filler = " ".join(["ಮಳೆ ಬಂತು ಕೆರೆ ತುಂಬಿತು"] * 10)
    ref = f"ಒಂದು ಊರಿನಲ್ಲಿ ಒಬ್ಬ ರಾಜನಿದ್ದನು {filler} ಅವನಿಗೆ ಏಳು ಮಕ್ಕಳು"
    readings = ["ಒಂದು ಊರಿನಲ್ಲಿ ಒಬ್ಬ ರಾಜನಿದ್ದನು"] + ["ಟಿಪ್ಪಣಿ ರಾಮ ಸೀತೆ ಲಕ್ಷ್ಮಣ ಭರತ ಶತ್ರುಘ್ನ ಹನುಮ"] * 5
    lines = [line(r, 30 * i) for i, r in enumerate([*readings, "ಅವನಿಗೆ ಏಳು ಮಕ್ಕಳು"])]
    found = [label for _, label in align(ref, text.aksharas([ref])[0], lines)]
    assert found == ["ಒಂದು ಊರಿನಲ್ಲಿ ಒಬ್ಬ ರಾಜನಿದ್ದನು", "ಅವನಿಗೆ ಏಳು ಮಕ್ಕಳು"]


def test_a_label_never_starts_inside_an_akshara(segments):
    assert labels(segments, ["ುಡುಗಿ ಭಾಗೀರಥಿಯ ತೀರದಲ್ಲಿ"]) == ["ಹುಡುಗಿ ಭಾಗೀರಥಿಯ ತೀರದಲ್ಲಿ"]
