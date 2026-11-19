// SPDX-FileCopyrightText: 2026 The Open Kannada Authors
// SPDX-License-Identifier: MIT OR Apache-2.0

//! Error rates for OCR output: characters, words and aksharas.
//!
//! All 3 rates are edit distance divided by reference length, summed over a
//! whole set before dividing (micro averages), so long lines weigh more than short ones.

use serde::Serialize;

/// The characters rule S2 of the normalization profile removes: ZWNJ, ZWJ, zero width
/// space, soft hyphen, word joiner and byte order mark.
const INVISIBLE: [char; 6] = [
    '\u{200C}', '\u{200D}', '\u{200B}', '\u{00AD}', '\u{2060}', '\u{FEFF}',
];

/// Prepares text for scoring.
///
/// Puts the text in the canonical form of kannadi's Kannada text normalization
/// profile ([`kannadi::normalize`], rules C1 to C8 of its NORMALIZATION.md), removes
/// the invisible characters of its rule S2, and collapses every run of whitespace to
/// 1 space with none at either end. Joiners only choose a glyph shape, and references
/// disagree on them, so a reader cannot see a difference that scoring would count.
///
/// ```
/// assert_eq!(kocr_text::score::prepare("  ಕಿ\u{0CD5}ರ್ತಿ \n ಜೆಟ್\u{200C}ನಿ "), "ಕೀರ್ತಿ ಜೆಟ್ನಿ");
/// ```
pub fn prepare(text: &str) -> String {
    let normalized = kannadi::normalize(text);
    let mut out = String::with_capacity(normalized.len());
    for word in normalized.split_whitespace() {
        if !out.is_empty() {
            out.push(' ');
        }
        out.extend(word.chars().filter(|c| !INVISIBLE.contains(c)));
    }
    out
}

/// Levenshtein distance with unit costs for insertion, deletion and substitution.
pub fn edit_distance<T: PartialEq>(a: &[T], b: &[T]) -> usize {
    let mut prev: Vec<usize> = (0..=b.len()).collect();
    let mut cur = vec![0; b.len() + 1];
    for (i, x) in a.iter().enumerate() {
        cur[0] = i + 1;
        for (j, y) in b.iter().enumerate() {
            let substitution = prev[j] + usize::from(x != y);
            cur[j + 1] = substitution.min(prev[j + 1] + 1).min(cur[j] + 1);
        }
        std::mem::swap(&mut prev, &mut cur);
    }
    prev[b.len()]
}

/// Edits against a reference of a given length, in 1 unit.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Serialize)]
pub struct Counts {
    /// Edit distance between reference and hypothesis.
    pub edits: usize,
    /// Number of units in the reference.
    pub reference: usize,
}

impl Counts {
    fn of<T: PartialEq>(reference: &[T], hypothesis: &[T]) -> Self {
        Counts {
            edits: edit_distance(reference, hypothesis),
            reference: reference.len(),
        }
    }

    /// Edits per reference unit. An empty reference gives the edit count itself,
    /// so output for a blank image is still penalized.
    pub fn rate(&self) -> f64 {
        if self.reference == 0 {
            self.edits as f64
        } else {
            self.edits as f64 / self.reference as f64
        }
    }

    fn add(&mut self, other: Counts) {
        self.edits += other.edits;
        self.reference += other.reference;
    }
}

/// Counts for 1 reference and hypothesis pair, in each unit.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Serialize)]
pub struct Score {
    /// Unicode scalar values, spaces included.
    pub chars: Counts,
    /// Whitespace-separated tokens. Punctuation stays attached to its word.
    pub words: Counts,
    /// Segments from [`kannadi::aksharas`], spaces included.
    pub aksharas: Counts,
}

impl Score {
    /// Scores `hypothesis` against `reference` after [`prepare`] on both.
    ///
    /// ```
    /// let s = kocr_text::score::Score::of("ಕನ್ನಡ ನಾಡು", "ಕನ್ನಡ ನಾಡು");
    /// assert_eq!(s.chars.edits, 0);
    /// assert_eq!(s.aksharas.reference, 6);
    /// ```
    pub fn of(reference: &str, hypothesis: &str) -> Self {
        let r = prepare(reference);
        let h = prepare(hypothesis);
        let rc: Vec<char> = r.chars().collect();
        let hc: Vec<char> = h.chars().collect();
        let rw: Vec<&str> = r.split(' ').filter(|w| !w.is_empty()).collect();
        let hw: Vec<&str> = h.split(' ').filter(|w| !w.is_empty()).collect();
        Score {
            chars: Counts::of(&rc, &hc),
            words: Counts::of(&rw, &hw),
            aksharas: Counts::of(&kannadi::split(&r), &kannadi::split(&h)),
        }
    }

    /// Adds another score's counts to this one.
    pub fn add(&mut self, other: Score) {
        self.chars.add(other.chars);
        self.words.add(other.words);
        self.aksharas.add(other.aksharas);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn edit_distance_counts_each_operation_once() {
        let d = |a: &str, b: &str| {
            edit_distance(
                &a.chars().collect::<Vec<_>>(),
                &b.chars().collect::<Vec<_>>(),
            )
        };
        assert_eq!(d("", ""), 0);
        assert_eq!(d("abc", ""), 3);
        assert_eq!(d("", "ab"), 2);
        assert_eq!(d("kitten", "sitting"), 3);
        assert_eq!(d("ಕನ್ನಡ", "ಕನ್ನಡ"), 0);
    }

    #[test]
    fn one_wrong_conjunct_is_one_akshara_error_and_several_char_errors() {
        // ಸ್ತ್ರೀ read as ಸ್ತೀ: 2 code points lost, 1 akshara wrong.
        let s = Score::of("ಸ್ತ್ರೀ", "ಸ್ತೀ");
        assert_eq!(s.chars.edits, 2);
        assert_eq!(s.aksharas.edits, 1);
        assert_eq!(s.aksharas.reference, 1);
        assert_eq!(s.words.edits, 1);
    }

    #[test]
    fn scoring_ignores_spacing_and_joiners_but_not_letters() {
        assert_eq!(Score::of("ಜೆಟ್\u{200C}ನಿ  ಹೋಗು", " ಜೆಟ್ನಿ\nಹೋಗು").chars.edits, 0);
        assert_eq!(Score::of("ಕನ್ನಡ", "ಕನ್ನಡಾ").chars.edits, 1);
    }

    #[test]
    fn scoring_uses_the_canonical_form_and_drops_invisible_characters() {
        // Nukta typed after the vowel sign, and a zero width space inside a word.
        assert_eq!(Score::of("ಜ\u{0CBC}ೀರೋ", "ಜೀ\u{0CBC}ರೋ").chars.edits, 0);
        assert_eq!(Score::of("ಕನ್ನಡ", "ಕನ್ನ\u{200B}ಡ").chars.edits, 0);
        assert_eq!(Score::of("ಔ", "ಒೌ").chars.edits, 0);
        assert_eq!(
            Score::of("ಕನ್ನಡ", "ಕ\u{00AD}ನ್\u{2060}ನ\u{FEFF}ಡ")
                .chars
                .edits,
            0
        );
    }

    #[test]
    fn scoring_normalizes_two_part_vowel_signs() {
        assert_eq!(Score::of("ಕೀ", "ಕಿ\u{0CD5}").chars.edits, 0);
    }

    #[test]
    fn empty_reference_rate_is_the_edit_count() {
        let s = Score::of("", "ಕಕ");
        assert_eq!(s.chars.rate(), 2.0);
        assert_eq!(Score::of("", "").chars.rate(), 0.0);
    }

    #[test]
    fn totals_are_micro_averages() {
        let mut total = Score::default();
        total.add(Score::of("ಅ", "ಆ"));
        total.add(Score::of("ಕನ್ನಡನಾಡು", "ಕನ್ನಡನಾಡು"));
        assert_eq!(total.chars.edits, 1);
        assert_eq!(total.chars.reference, 1 + 9);
    }
}
