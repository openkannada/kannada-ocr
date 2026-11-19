# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

import pytest

from kannada_ocr.ziegler import (
    Checks,
    Row,
    barred_c,
    column_lines,
    entries,
    fields_of,
    in_order,
    join_break,
    kannada_share,
    latin_fix,
    merge_reread,
    needs_reread,
    sort_key,
)

HEIGHT = 100


def seg(line, left, right, text, top=None, height=HEIGHT):
    top = 500 + 120 * line if top is None else top
    return Row("0231", "L", line, left, top, right, top + height, 90.0, text)


COLUMN = [
    seg(0, 170, 1300, "In-ac′tion, s. ಅನುದ್ಯೋಗ, ಆಲಸ್ಯ,"),
    seg(1, 255, 510, "ವಿಶ್ರಾಂತಿ."),
    seg(1, 1120, 1300, "[ವುಳ್ಳ."),
    seg(2, 170, 1010, "In-ac′tive, a. ಕೆಲಸವಿಲ್ಲದ,"),
    seg(2, 1100, 1300, "ಆಲಸ್ಯ"),
    seg(3, 165, 1300, "In-ad′e-quāte, a. ಕೆಲಸಕ್ಕೆ"),
    seg(4, 250, 1140, "ಬಾರದ, ಅಯೋಗ್ಯ."),
]


def test_a_turnover_moves_to_the_end_of_the_line_below():
    lines = column_lines(COLUMN)
    assert lines[1].text == "ವಿಶ್ರಾಂತಿ."
    assert lines[2].text == "In-ac′tive, a. ಕೆಲಸವಿಲ್ಲದ, ಆಲಸ್ಯವುಳ್ಳ."


def test_a_turnover_without_its_bracket_is_found_by_its_gap():
    column = [*COLUMN[:2], seg(1, 1120, 1300, "ವುಳ್ಳ."), *COLUMN[3:]]
    assert column_lines(column)[2].text.endswith("ಆಲಸ್ಯವುಳ್ಳ.")


def test_a_turnover_with_its_bracket_needs_no_wide_gap():
    column = [*COLUMN[:2], seg(1, 690, 1300, "[ವುಳ್ಳ."), *COLUMN[3:]]
    assert column_lines(column)[2].text.endswith("ಆಲಸ್ಯವುಳ್ಳ.")


def test_a_turnover_inside_the_last_segment_is_found_by_its_bracket():
    column = [*COLUMN[:1], seg(1, 255, 1300, "ವಿಶ್ರಾಂತಿ. [ವುಳ್ಳ."), *COLUMN[3:]]
    lines = column_lines(column)
    assert lines[1].text == "ವಿಶ್ರಾಂತಿ."
    assert lines[2].text.endswith("ಆಲಸ್ಯವುಳ್ಳ.")
    column = [*COLUMN[:1], seg(1, 255, 900, "ವಿಶ್ರಾಂತಿ. [ವುಳ್ಳ."), *COLUMN[3:]]
    assert column_lines(column)[1].text == "ವಿಶ್ರಾಂತಿ. [ವುಳ್ಳ."


def test_a_far_segment_with_a_label_is_not_a_turnover():
    column = [seg(0, 170, 280, "೨"), seg(0, 700, 1300, "v. a. ಬಂದುಕಟ್ಟುಮಾ"), *COLUMN[3:]]
    assert column_lines(column)[0].text == "೨ v. a. ಬಂದುಕಟ್ಟುಮಾ"
    column = [seg(0, 170, 280, "೨"), seg(0, 700, 1300, "ಕಟ್ಟು ಮಾಡು ಕೊಡು"), *COLUMN[3:]]
    assert column_lines(column)[0].text == "೨ ಕಟ್ಟು ಮಾಡು ಕೊಡು"


def test_a_wide_justified_space_is_not_a_turnover():
    lines = column_lines(COLUMN)
    assert lines[2].text.startswith("In-ac′tive, a. ಕೆಲಸವಿಲ್ಲದ,")
    assert "ಆಲಸ್ಯವುಳ್ಳ" in lines[2].text


def test_a_short_last_segment_away_from_the_right_edge_stays_in_its_line():
    column = [*COLUMN[:2], seg(1, 700, 900, "[ವುಳ್ಳ."), *COLUMN[3:]]
    assert column_lines(column)[1].text == "ವಿಶ್ರಾಂತಿ. [ವುಳ್ಳ."


def test_stray_marks_are_dropped():
    column = [*COLUMN, seg(4, 870, 930, "ಬ", height=40)]
    assert column_lines(column)[4].text == "ಬಾರದ, ಅಯೋಗ್ಯ."


def test_lines_of_the_pronunciation_key_are_dropped():
    column = [*COLUMN, seg(5, 170, 1300, "dry, body; fool, book; oil; pound.")]
    assert [ln.text for ln in column_lines(column)][-1] == "ಬಾರದ, ಅಯೋಗ್ಯ."


def test_a_label_set_apart_is_kept_though_it_is_low():
    column = [seg(0, 170, 600, "Ꞓor-i-an′dĕr,"), seg(0, 680, 720, "s.", top=530, height=37)]
    column += [seg(0, 800, 1300, "ಕೊತ್ತುಂಬರಿ ಬೀಜ."), *COLUMN[3:]]
    lines = column_lines(column)
    assert lines[0].text == "Ꞓor-i-an′dĕr, s. ಕೊತ್ತುಂಬರಿ ಬೀಜ."


def test_a_narrow_mark_left_of_the_column_does_not_move_its_edge():
    column = [*COLUMN, *(seg(i, 100, 110, "|") for i in range(5))]
    lines = column_lines(column)
    assert [ln.starts for ln in lines] == [True, False, True, True, False]
    assert lines[0].text.startswith("In-ac′tion")


def test_entries_start_at_the_left_edge_and_continue_indented():
    found = entries(column_lines(COLUMN))
    assert [e.text.split(",")[0] for e in found] == ["In-ac′tion", "In-ac′tive", "In-ad′e-quāte"]
    assert found[0].text == "In-ac′tion, s. ಅನುದ್ಯೋಗ, ಆಲಸ್ಯ, ವಿಶ್ರಾಂತಿ."
    assert found[0].raw == ["In-ac′tion, s. ಅನುದ್ಯೋಗ, ಆಲಸ್ಯ,", "ವಿಶ್ರಾಂತಿ."]


def test_a_kannada_line_at_the_left_edge_continues_the_entry():
    column = [*COLUMN[:4], seg(3, 166, 600, "ವಾದ.")]
    lines = column_lines(column)
    assert not lines[-1].starts


def test_a_misread_headword_at_the_left_edge_still_starts_an_entry():
    column = [*COLUMN[:5], seg(3, 166, 1300, "ಸ, s. ಪ್ರಾಣಸಂಕಟ, ಅತಿವೇದನೆ."), *COLUMN[6:]]
    assert column_lines(column)[3].starts
    column = [*COLUMN[:5], seg(3, 166, 1300, "ಡು, ತೀರ್ಪು ಹೇಳು. v. a. ಇತ್ಯರ್ಥ"), *COLUMN[6:]]
    assert not column_lines(column)[3].starts
    column = [*COLUMN[:5], seg(3, 166, 1300, "ಸ, ಆ. ಹಲವಿಳಿಸುವ."), *COLUMN[6:]]
    assert column_lines(column)[3].starts


def test_a_line_indented_less_than_a_continuation_still_starts_an_entry():
    column = [*COLUMN[:5], seg(3, 195, 1300, "In-ad′e-quāte, a. ಕೆಲಸಕ್ಕೆ"), *COLUMN[6:]]
    assert column_lines(column)[3].starts


def test_an_entry_continues_into_the_next_column():
    left = [COLUMN[0], seg(1, 255, 900, "ವಿಶ್ರಾಂ")]
    right = [
        Row("0231", "R", 0, 1500, 1000, 1700, 1100, 90.0, "ತಿ."),
        Row("0231", "R", 1, 1400, 1120, 2600, 1220, 90.0, "In-al′ien-a-ble, a. ವಂಶದ."),
        Row("0231", "R", 2, 1500, 1240, 2000, 1340, 90.0, "ಕೊಡ ಕೂಡದ."),
    ]
    found = entries(column_lines(left) + column_lines(right))
    assert [e.text for e in found] == [
        "In-ac′tion, s. ಅನುದ್ಯೋಗ, ಆಲಸ್ಯ, ವಿಶ್ರಾಂತಿ.",
        "In-al′ien-a-ble, a. ವಂಶದ. ಕೊಡ ಕೂಡದ.",
    ]
    assert (found[0].column, found[0].right, found[0].bottom) == ("L", 1300, 720)


def test_a_kannada_word_cut_by_the_line_end_is_joined():
    assert join_break("ಶೇರ ಕೂಡದ, ದು", "ರ್ಗಮವಾದ.", None) == "ಶೇರ ಕೂಡದ, ದುರ್ಗಮವಾದ."


def test_2_words_parted_by_the_line_end_keep_their_space():
    words = {"ಕೆಲಸಕ್ಕೆ", "ಬಾರದ"}
    assert join_break("a. ಕೆಲಸಕ್ಕೆ", "ಬಾರದ, ಅಯೋಗ್ಯ.", words.__contains__) == "a. ಕೆಲಸಕ್ಕೆ ಬಾರದ, ಅಯೋಗ್ಯ."


def test_a_line_ending_in_punctuation_is_joined_with_a_space():
    assert join_break("ಆಲಸ್ಯ,", "ವಿಶ್ರಾಂತಿ.", None) == "ಆಲಸ್ಯ, ವಿಶ್ರಾಂತಿ."


def test_fields_of_an_entry():
    f = fields_of("In-ad′e-quāte (-kwāt), a. ಕೆಲಸಕ್ಕೆ ಬಾರದ, ಅಯೋಗ್ಯ, ಸಾಲದ.")
    assert (f.headword, f.plain, f.pos) == ("In-ad′e-quāte", "Inadequate", ["a."])
    assert f.glosses == ["ಕೆಲಸಕ್ಕೆ ಬಾರದ", "ಅಯೋಗ್ಯ", "ಸಾಲದ"]


def test_glosses_split_on_semicolons_and_a_second_label():
    f = fields_of("Call, s. ಕರೆಯೋಣ; ಕೆಲಸ, v.a. ಕರೆ.")
    assert f.pos == ["s.", "v. a."]
    assert f.glosses == ["ಕರೆಯೋಣ", "ಕೆಲಸ", "ಕರೆ"]


def test_a_kannada_digit_is_not_where_the_glosses_start():
    f = fields_of("Call, ೮. ಕರೆ.")
    assert f.headword == "Call" and f.glosses == ["ಕರೆ"]


def test_a_cross_reference_has_a_label_and_no_glosses():
    f = fields_of("In-cāġe′, v. a. see En-cāġe′.")
    assert f.pos == ["v. a."] and f.glosses == []


def test_the_euro_sign_is_the_barred_capital_c():
    assert barred_c("€al′o-mel") == "Ꞓal′o-mel"


def test_a_euro_sign_inside_a_word_is_the_small_barred_c():
    assert latin_fix("A€′ces-sar-y, Ab-stra€t") == "A\ua793′ces-sar-y, Ab-stra\ua793t"


def test_diaeresis_caron_and_eth_are_the_breve_letters():
    assert (
        latin_fix("vër, věr, Ab-ō-li′tiðn, döve")
        == "v\u0115r, v\u0115r, Ab-ō-li′ti\u014fn, d\u014fve"
    )
    assert latin_fix("fär, Ä") == "fär, Ä"


def test_the_stress_mark_in_a_headword_is_a_prime():
    assert barred_c("Ab'bot") == "Ab\u2032bot" and barred_c("A-bet’") == "A-bet\u2032"


def test_an_e_becomes_the_barred_small_c_only_if_that_makes_a_known_word():
    known = {"inaccessible", "inane"}.__contains__
    assert barred_c("In-ae-cess′i-ble", known) == "In-aꞓ-cess′i-ble"
    assert barred_c("In-āne′", known) == "In-āne′"
    assert barred_c("In-ept", known) == "In-ept"
    assert barred_c("Seat", {"seat", "scat"}.__contains__) == "Seat"


def test_sort_key_and_order():
    assert sort_key("In-ac′tion") == "inaction"
    keys = ["inaction", "inactive", "lo", "inadequate", ""]
    assert in_order(keys, [True] * 5) == [True, True, False, False, False]
    assert in_order(keys, [True, True, False, True, False]) == [True, True, False, True, False]


def test_kannada_share_counts_gloss_words():
    assert kannada_share(["ಕೆಲಸಕ್ಕೆ ಬಾರದ", "ಸಾಲದ"], {"ಬಾರದ", "ಸಾಲದ"}.__contains__) == 2 / 3
    assert kannada_share([], bool) is None


def test_high_needs_every_check():
    good = Checks(known=True, in_order=True, has_pos=True, has_glosses=True, kannada_share=0.5)
    assert good.high
    for field in ("known", "in_order", "has_pos", "has_glosses"):
        assert not Checks(**{**good.__dict__, field: False}).high
    assert not Checks(**{**good.__dict__, "kannada_share": 0.4}).high


def test_every_label_of_the_book_is_found_and_spaced():
    f = fields_of("Al-ight′, v.n. ಇಳಿ; p.a. ಇಳಿದ; s. pl. ಇಳಿತ.")
    assert f.pos == ["v. n.", "p. a.", "s.", "pl."]
    assert f.glosses == ["ಇಳಿ", "ಇಳಿದ", "ಇಳಿತ"]


def test_the_headword_runs_to_its_comma_without_its_pronunciation():
    assert fields_of("In′born (-bąrn), In′bred, a. ಹುಟ್ಟು.").headword == "In′born"
    assert fields_of("Be-numb’ (-num)’), v. a. ತಿಮರು.").headword == "Be-numb’"
    assert fields_of("Ab-j ų-rā′tiŏn, s. ವಿಸರ್ಜನೆ.").headword == "Ab-j ų-rā′tiŏn"
    assert fields_of("Ac-com-mō-dā′tiŏn ಅನುಕೂಲ.").headword == "Ac-com-mō-dā′tiŏn"
    assert fields_of("Ab-sent′ v. a. — one′s self, ಹೋಗು.").headword == "Ab-sent′"


def test_marks_before_the_headword_are_not_part_of_it():
    assert fields_of("೬ Blīthe′sŏme, a. ಉಲ್ಲಾಸವುಳ್ಳ.").headword == "Blīthe′sŏme"
    assert fields_of("` | Chal′lenġe, v. a. ಕರಿ.").headword == "Chal′lenġe"
    assert fields_of("ಸ, s. ಪ್ರಾಣಸಂಕಟ.").headword == ""


def test_an_8_in_the_label_slot_is_the_label_s():
    assert fields_of("A-ban′dŏn-ment, 8. ಬಿಟ್ಟುಬಿಡುವಿಕೆ.").pos == ["s."]
    assert fields_of("Ab′bot, 8 ಮಠಾಧಿಪತಿ.").pos == []


def test_labels_misread_as_kannada_letters_are_put_right():
    f = fields_of("A-bor′tive, ಆ. ಹಲವಿಳಿಸುವ; v. ಇ. ಹಲವಿಳಿ; v. ಆ. ಇಳಿಸು.")
    assert f.pos == ["a.", "v. n.", "v. a."]
    assert f.glosses == ["ಹಲವಿಳಿಸುವ", "ಹಲವಿಳಿ", "ಇಳಿಸು"]


@pytest.mark.parametrize(
    ("read", "label"),
    [("ಆ", "a."), ("ಇ", "a."), ("4", "a."), ("«", "a."), ("e", "a."), ("8", "s."), ("೯", "s.")],
)
def test_every_slot_misread_is_the_label_it_stands_for(read, label):
    assert fields_of(f"Ab′bot, {read}. ಮಠಾಧಿಪತಿ.").pos == [label]


@pytest.mark.parametrize(
    ("read", "label"), [("ಆ", "v. a."), ("ಇ", "v. n."), ("z", "v. n."), ("7", "v. n.")]
)
def test_every_verb_misread_is_the_label_it_stands_for(read, label):
    assert fields_of(f"A-bide′, v. {read}. ನೆಲೆಯಾಗಿರು.").pos == [label]


def test_a_kannada_letter_after_the_glosses_start_is_not_a_label():
    assert fields_of("Ass, s. ಕತ್ತೆ, ಆ. ದಡ್ಡ.").pos == ["s."]


def test_a_lost_headword_and_label_come_from_the_latin_read():
    assert merge_reread("೬ v. a. ತಗ್ಗಿಸು; ಮಾನ", "A-bāse′, v. a. sA N") == "A-bāse′, v. a. ತಗ್ಗಿಸು; ಮಾನ"
    assert (
        merge_reread("A-bor′tive, ಆ. ಹಲವಿಳಿಸುವ.", "A-bor′tive, a. BOD") == "A-bor′tive, a. ಹಲವಿಳಿಸುವ."
    )
    assert merge_reread("A-bound′ ಹೆಚ್ಚಾಗಿರು.", "A-bound′, v. n. S A") == "A-bound′, v. n. ಹೆಚ್ಚಾಗಿರು."
    assert (
        merge_reread("A-ban′dŏn-ment, ಅ. ಬಿಟ್ಟು.", "A-ban′dŏn-ment, 8. O")
        == "A-ban′dŏn-ment, s. ಬಿಟ್ಟು."
    )


def test_a_label_read_with_a_comma_in_the_latin_read_still_counts():
    assert merge_reread("೨ a. ಸೂತ್ರಮಯವಾದ,", "Sen-ten′tiŏus, a, SA3,") == "Sen-ten′tiŏus, a. ಸೂತ್ರಮಯವಾದ,"


def test_a_latin_read_without_a_label_or_a_headword_changes_nothing():
    assert merge_reread("೬ v. a. ತಗ್ಗಿಸು.", "A-bāse′ sA N") == "೬ v. a. ತಗ್ಗಿಸು."
    assert merge_reread("೬ v. a. ತಗ್ಗಿಸು.", "3, v. a. x") == "೬ v. a. ತಗ್ಗಿಸು."


def test_a_line_needs_a_reread_if_its_headword_has_no_latin_letter_or_it_has_no_label():
    assert needs_reread("1-802, s. ವಿಸರ್ಜನೆ.")
    assert needs_reread("A-bound′ ಹೆಚ್ಚಾಗಿರು.")
    assert not needs_reread("A-bor′tive, ಆ. ಹಲವಿಳಿಸುವ.")
    assert not needs_reread("Ab′bot, s. ಮಠಾಧಿಪತಿ.")


def test_a_reread_line_starts_its_entry_with_the_latin_headword():
    lines = column_lines(COLUMN)
    lines[0].text = "೬ s. ಅನುದ್ಯೋಗ, ಆಲಸ್ಯ,"
    lines[0].reread = "In-ac′tion, s. Ws"
    found = entries(lines)
    assert found[0].text.startswith("In-ac′tion, s. ಅನುದ್ಯೋಗ")
    assert found[0].raw[0] == "೬ s. ಅನುದ್ಯೋಗ, ಆಲಸ್ಯ,"
    assert found[0].reread == "In-ac′tion, s. Ws"


def test_a_latin_read_the_entry_did_not_use_is_not_kept():
    lines = column_lines(COLUMN)
    lines[0].text = "೬ s. ಅನುದ್ಯೋಗ, ಆಲಸ್ಯ,"
    lines[0].reread = "3, Ws"
    assert entries(lines)[0].reread == ""
