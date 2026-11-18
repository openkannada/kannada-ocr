# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

from kannada_ocr.linematch import closest_stretch, fold, headword_found, project

KITTEL = "ಚಳ čaḷa. 3. Mistake for ಚಿಲ, q. v."


def test_each_script_is_kept_apart():
    assert project(KITTEL, "kn") == "ಚಳ ಚಿಲ"
    assert project(KITTEL, "la") == "čaḷa Mistake for q v"


def test_stress_primes_do_not_split_or_change_a_latin_word():
    for prime in ("'", "’", "′"):
        assert project(f"Hīgh{prime}wāy, s. ಹೆದ್ದಾರಿ", "la") == "Hīghwāy s"


def test_a_combining_mark_stays_with_its_latin_letter():
    assert project("De-pos̱it, s.", "la") == "De pos̱it s"


def test_the_closest_stretch_is_cut_from_the_page():
    page = "Hig 200 Hiv\nHīgh trēa′son, s. ರಾಜ\nHint, s. ಸೂಚನೆ, ಸಂನೆ\nHip, s. ನಡುವು"
    assert closest_stretch("Hint, s. ಸೂಚನೆ, ಸನ್ನೆ", page) == "Hint, s. ಸೂಚನೆ, ಸಂನೆ"


def test_a_line_read_across_both_columns_is_not_found_clean():
    page = "Hint, s. Hip, s. ಸೂಚನೆ, ನಡುವು"
    assert closest_stretch("Hint, s. ಸೂಚನೆ,", page) != "Hint, s. ಸೂಚನೆ,"


def test_an_empty_page_has_no_stretch():
    assert closest_stretch("Hint, s.", "") == ""


def test_a_headword_must_match_exactly_up_to_punctuation_and_prime_style():
    assert headword_found("Hīgh′wāy", "Hīgh'wāy (hīwā), s. ಹೆದ್ದಾರಿ")
    assert not headword_found("Hīgh′wāy", "High'way (hīwā), s. ಹೆದ್ದಾರಿ")
    assert headword_found("ಚಳ čaḷa", "ಚಳ čaḷa. 3.")
    assert not headword_found("ಚಳ čaḷa", "ಚಳ cala. 3.")


def test_joiners_do_not_count_against_a_headword():
    assert headword_found("ಇಮ್ im", "ಇಮ್\u200c im. 2.")


def test_folding_keeps_only_the_letters_of_a_latin_headword():
    assert fold("Ꞓa̤ll, s.") == "Call, s."
    assert headword_found(fold("Hīgh′wāy"), fold("High'way (hīwā)"))
    assert headword_found(fold("Fe-lic′i-ty"), fold("Felicity, s. ಆನಂದ"))


def test_folding_leaves_kannada_alone():
    assert fold("ಇಮ್ಬು imbu") == "ಇಮ್ಬು imbu"
