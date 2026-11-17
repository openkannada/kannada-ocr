from pathlib import Path

from kannada_ocr import mile

FIXTURE = Path(__file__).parent / "fixtures" / "mile_page.xml"


def test_page_lines_join_words_and_drop_empty_lines():
    page = mile.parse_page(FIXTURE, Path("images"))
    assert page.id == "mile_page"
    assert [line.text for line in page.lines] == ["ಮನೆಯ ಬಾಗಿಲು", "ತೆರೆದಿದೆಯೇ ?"]
    assert page.text == "ಮನೆಯ ಬಾಗಿಲು\nತೆರೆದಿದೆಯೇ ?"


def test_line_box_comes_from_words_when_they_have_boxes():
    box = mile.parse_page(FIXTURE, Path("images")).lines[0].box
    assert box == mile.Box(top=104, bottom=143, left=870, right=1133)


def test_line_box_falls_back_to_block_columns_for_boxless_words():
    box = mile.parse_page(FIXTURE, Path("images")).lines[1].box
    assert box == mile.Box(top=150, bottom=190, left=50, right=900)


def test_padded_box_is_clipped_to_the_image():
    assert mile.Box(2, 10, 3, 20).padded(5, width=22, height=12) == (0, 0, 22, 12)


def test_degraded_word_list_skips_header_and_blank_rows(tmp_path):
    (tmp_path / "GroundTruthUnicode.txt").write_text(
        "﻿Image_Name: Unicode_Text\na.tif : ಹುಟ್ಟು,\nb.tif :\n", encoding="utf-8"
    )
    assert mile.read_degraded_words(tmp_path) == [(tmp_path / "TestImages" / "a.tif", "ಹುಟ್ಟು,")]
