# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

from pathlib import Path

import pytest

from kannada_ocr.render import FontFace

REPO = Path(__file__).resolve().parents[1]
FONTS = REPO / "data" / "fonts"


def font_or_skip(*parts: str, weight: int | None = None) -> FontFace:
    path = FONTS.joinpath(*parts)
    if not path.exists():
        pytest.skip(f"{path} is not downloaded; run `uv run kocr fonts`")
    return FontFace(path, path.stem, weight)


@pytest.fixture
def noto() -> FontFace:
    return font_or_skip("google", "NotoSansKannada[wdth,wght].ttf", weight=400)
