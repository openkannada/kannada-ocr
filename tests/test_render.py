# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

import numpy as np
from conftest import FONTS, font_or_skip

from kannada_ocr.fonts import design_key, digit_style
from kannada_ocr.render import render, shape, shapes_kannada


def test_conjuncts_shape_to_fewer_glyphs(noto):
    ids, _ = shape(noto, "ಕ್ಷ")
    assert len(ids) < 3 and all(ids)
    assert shapes_kannada(noto)


def test_render_gives_cropped_ink_in_unit_range(noto):
    ink = render(noto, "ಕನ್ನಡ ನಾಡು", 40)
    assert ink is not None and ink.dtype == np.float32
    assert ink.min() >= 0.0 and ink.max() <= 1.0 and ink.max() > 0.9
    assert ink.shape[0] < 4 * 40 and ink.shape[1] > ink.shape[0]


def test_render_refuses_text_the_font_cannot_draw(noto):
    assert render(noto, "ಕನ್ನಡ 漢", 40) is None


def test_render_refuses_a_blank_drawn_latin_character(noto, monkeypatch):
    import kannada_ocr.render as r

    real = r._glyph

    def blank_for_question_mark(loaded, glyph_id):
        bitmap, left, top = real(loaded, glyph_id)
        if glyph_id == shape(noto, "?")[0][0]:
            return np.zeros_like(bitmap), left, top
        return bitmap, left, top

    monkeypatch.setattr(r, "_glyph", blank_for_question_mark)
    assert render(noto, "ಕನ್ನಡ?", 40) is None
    assert render(noto, "ಕನ್ನಡ", 40) is not None


def test_legacy_nudi_font_fails_the_kannada_check():
    assert not shapes_kannada(font_or_skip("nudi", "Nudi 01 e.ttf"))


def test_unicode_font_without_conjuncts_fails_the_kannada_check():
    assert not shapes_kannada(font_or_skip("nudi", "NudiParijatha.ttf"))


def test_shared_digit_glyphs_are_detected_with_their_style(noto):
    assert digit_style(font_or_skip("nudi", "NUDI UNI 01E.ttf")) == "latin"
    assert digit_style(font_or_skip("nudi", "NUDI UNI 01K.ttf")) == "kannada"
    assert digit_style(noto) is None
    assert digit_style(font_or_skip("google", "PadyakkeExpandedOne-Regular.ttf")) is None


def test_design_key_groups_variants_of_one_design():
    assert design_key("NUDI UNI 01E BOLD") == design_key("NudiUni01e") == "nudiuni01"
    assert design_key("NotoSansKannada[wdth,wght]") == "notosanskannada"


def test_a_glyph_off_the_canvas_drops_the_sample(noto, monkeypatch):
    import kannada_ocr.render as r

    real = r._glyph

    def far_left(loaded, glyph_id):
        bitmap, left, top = real(loaded, glyph_id)
        return bitmap, left - 10_000, top

    monkeypatch.setattr(r, "_glyph", far_left)
    assert render(noto, "ಕನ್ನಡ", 40) is None


def test_legacy_inventory_keeps_nudi_layouts_and_drops_excluded_files():
    from kannada_ocr.fonts import legacy_inventory

    font_or_skip("nudi", "Nudi 01 e.ttf")
    names = {f.face.family: f for f in legacy_inventory(FONTS, log=lambda _: None)}
    assert names["Nudi 01 e"].encoding == "nudi"
    assert names["Nudi 01 e"].digit_style == "latin"
    assert names["Nudi 01 k"].digit_style == "kannada"
    assert "Nudi B Akshara-1" not in names and "Nudi 17 e" not in names
    assert "NUDI UNI 01E" not in names
    assert "NudiParijatha" not in names, "a Unicode font with Latin-1 glyphs is not legacy"
