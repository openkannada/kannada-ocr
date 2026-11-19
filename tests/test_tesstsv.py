# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

from kannada_ocr.tesstsv import segments

HEAD = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"


def row(level, line, word, left, width, text="", conf="90", top=10, height=40):
    return f"{level}\t1\t1\t1\t{line}\t{word}\t{left}\t{top}\t{width}\t{height}\t{conf}\t{text}\n"


def test_words_close_together_make_1_segment():
    tsv = (
        HEAD
        + row(4, 1, 0, 0, 300)
        + row(5, 1, 1, 0, 100, "In-ac′tion,", "80")
        + row(5, 1, 2, 110, 30, "s.", "60")
    )
    [seg] = segments(tsv, dx=5, dy=7)
    assert seg.text == "In-ac′tion, s."
    assert (seg.left, seg.top, seg.right, seg.bottom) == (5, 17, 145, 57)
    assert seg.conf == 70.0


def test_a_gap_wider_than_the_rule_starts_a_new_segment():
    tsv = (
        HEAD
        + row(4, 1, 0, 0, 600)
        + row(5, 1, 1, 0, 100, "ವಿಶ್ರಾಂತಿ.")
        + row(5, 1, 2, 130, 50, "[ವುಳ್ಳ.")
    )
    assert [s.text for s in segments(tsv)] == ["ವಿಶ್ರಾಂತಿ.", "[ವುಳ್ಳ."]


def test_lines_are_numbered_in_order_and_empty_words_dropped():
    tsv = HEAD + row(4, 1, 0, 0, 100) + row(5, 1, 1, 0, 50, "a") + row(4, 2, 0, 0, 100, top=60)
    tsv += row(5, 2, 1, 0, 50, " ", top=60) + row(5, 2, 2, 0, 50, "b", top=60)
    assert [(s.line, s.text) for s in segments(tsv)] == [(0, "a"), (1, "b")]
