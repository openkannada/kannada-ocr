# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

import shutil

import pytest

from kannada_ocr.spelling import Hunspell, Recorder, word_list


@pytest.mark.skipif(shutil.which("hunspell") is None, reason="hunspell is not installed")
def test_hunspell_answers_from_1_batch(tmp_path):
    (tmp_path / "kn.aff").write_text("SET UTF-8\n", encoding="utf-8")
    (tmp_path / "kn.dic").write_text("2\nಬಾರದ\nಸಾಲದ\n", encoding="utf-8")
    speller = Hunspell(tmp_path / "kn")
    speller.check_many(["ಬಾರದ", "ಕೆಲಸಕ್ಕೆಬಾರದ"])
    assert speller.cache == {"ಬಾರದ": True, "ಕೆಲಸಕ್ಕೆಬಾರದ": False}
    assert speller("ಸಾಲದ") and not speller("ಸಾಲ")


def test_the_recorder_accepts_and_remembers():
    recorder = Recorder()
    assert recorder("ಬಾರದ") and recorder.words == {"ಬಾರದ"}


def test_the_word_list_is_lowercased(tmp_path):
    (tmp_path / "words").write_text("Aaron\nabandon\n\n", encoding="utf-8")
    assert word_list(tmp_path / "words") == {"aaron", "abandon"}
