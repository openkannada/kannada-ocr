# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

import shutil

import pytest

from kannada_ocr.baselines.tesseract import Tesseract


def test_missing_model_is_reported(tmp_path):
    with pytest.raises(FileNotFoundError):
        Tesseract(tmp_path)


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract is not installed")
def test_page_mode_is_named_unless_default(tmp_path):
    (tmp_path / "kan.traineddata").write_bytes(b"")
    assert not Tesseract(tmp_path).name.endswith("psm3")
    assert Tesseract(tmp_path, page_mode=4).name.endswith("-best-psm4")


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract is not installed")
def test_a_fine_tuned_model_is_named_by_its_language(tmp_path):
    (tmp_path / "kan_ft.traineddata").write_bytes(b"")
    assert Tesseract(tmp_path, lang="kan_ft").name.endswith("-kan_ft")


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract is not installed")
def test_cli_model_names_pick_language_and_page_mode(tmp_path):
    from kannada_ocr.cli import _recognizer

    (tmp_path / "tessdata").mkdir()
    (tmp_path / "tessdata" / "kan_ft.traineddata").write_bytes(b"")
    recognizer = _recognizer("tesseract-psm4@kan_ft", tmp_path)
    assert (recognizer.lang, recognizer.page_mode) == ("kan_ft", 4)
