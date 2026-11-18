# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

import numpy as np
from PIL import Image

from kannada_ocr.columns import content_box, ink, split_columns, text_lines

LINES = 12
TOP = 230
PITCH = 24
HEIGHT = 5


def page(rule: bool = False, facing: bool = False) -> np.ndarray:
    """A 2-column page: 12 lines of dashes per column, black background on the left."""
    mask = np.zeros((700, 1000), dtype=bool)
    mask[:, :20] = True
    for i in range(LINES):
        top = TOP + PITCH * i
        shift = 5 * i % 12
        for left in [*range(60 + shift, 465, 12), *range(490 + shift, 895, 12)]:
            mask[top : top + HEIGHT, left : left + 3] = True
    if rule:
        mask[220:510, 477:480] = True
    if facing:
        mask[:, 905:940] = True
        for i in range(LINES):
            mask[TOP + PITCH * i : TOP + PITCH * i + HEIGHT, 945:995:4] = True
    return mask


def test_ink_is_the_dark_side_of_otsu():
    image = Image.fromarray(np.where(page(), 20, 230).astype(np.uint8))
    assert (ink(image) == page()).all()


def test_the_columns_part_in_the_gutter():
    left, right = split_columns(page())
    assert 464 <= left[2] == right[0] <= 490


def test_background_and_the_facing_page_stay_outside_the_printed_area():
    left, top, right, bottom = content_box(page(facing=True))
    assert 20 <= left <= 60 and 894 <= right < 945
    assert top <= TOP and bottom >= TOP + PITCH * (LINES - 1) + HEIGHT


def test_lines_are_found_one_by_one():
    left, _ = split_columns(page())
    assert len(text_lines(page(), left)) == LINES


def test_a_vertical_rule_does_not_join_the_lines():
    assert len(text_lines(page(rule=True), (470, 220, 910, 510))) == LINES


def test_lines_set_too_close_to_part_are_cut_apart():
    mask = page()
    for i in (0, 6):
        top = TOP + PITCH * i + HEIGHT + 2
        mask[top : top + HEIGHT, 60:400:4] = True
    left, _ = split_columns(mask)
    assert len(text_lines(mask, left)) == LINES + 2
