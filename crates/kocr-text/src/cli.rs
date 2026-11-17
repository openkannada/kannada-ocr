// SPDX-FileCopyrightText: 2026 The Open Kannada Authors
// SPDX-License-Identifier: MIT OR Apache-2.0

//! Line-oriented commands. Each reads UTF-8 from a reader and writes to a writer,
//! so the Python pipeline can call them in 1 process per batch.

use std::io::{BufRead, Write};

use serde::{Deserialize, Serialize};

use crate::score::{Counts, Score};

/// Usage text for the binary.
pub const USAGE: &str = "usage: kocr-text <command> < input
commands:
  normalize   1 line in, the kannadi-normalized line out
  aksharas    1 line in, a JSON array of its akshara segments out
  to-nudi     1 line in, {\"text\", \"clean\"} out: Nudi and Baraha ANSI glyph codes
  score       JSON lines {\"id\", \"ref\", \"hyp\"} in, 1 JSON report out";

/// A failure that names the input line it came from.
#[derive(Debug)]
pub struct Error(pub String);

impl std::fmt::Display for Error {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}

impl From<std::io::Error> for Error {
    fn from(e: std::io::Error) -> Self {
        Error(e.to_string())
    }
}

/// Runs `command`, reading `input` and writing `output`.
pub fn run(command: &str, input: impl BufRead, output: impl Write) -> Result<(), Error> {
    match command {
        "normalize" => map_lines(input, output, |line| Ok(kannadi::normalize(line))),
        "aksharas" => map_lines(input, output, |line| {
            serde_json::to_string(&kannadi::split(line)).map_err(|e| Error(e.to_string()))
        }),
        "to-nudi" => map_lines(input, output, |line| {
            let encoded = kannadi::legacy::unicode_to_nudi(line);
            let clean = encoded.is_clean();
            serde_json::to_string(&Nudi {
                text: encoded.text,
                clean,
            })
            .map_err(|e| Error(e.to_string()))
        }),
        "score" => score(input, output),
        other => Err(Error(format!("unknown command {other:?}\n{USAGE}"))),
    }
}

fn map_lines(
    input: impl BufRead,
    mut output: impl Write,
    f: impl Fn(&str) -> Result<String, Error>,
) -> Result<(), Error> {
    for line in input.lines() {
        writeln!(output, "{}", f(&line?)?)?;
    }
    Ok(())
}

/// A line in Nudi glyph codes. `clean` is false if a character had no glyph or an
/// akshara was ill formed, in which case the text does not read back as the input.
#[derive(Serialize)]
struct Nudi {
    text: String,
    clean: bool,
}

#[derive(Deserialize)]
struct Pair {
    id: String,
    #[serde(rename = "ref")]
    reference: String,
    #[serde(rename = "hyp")]
    hypothesis: String,
}

#[derive(Serialize)]
struct Rates {
    cer: f64,
    wer: f64,
    aer: f64,
}

impl From<&Score> for Rates {
    fn from(s: &Score) -> Self {
        Rates {
            cer: s.chars.rate(),
            wer: s.words.rate(),
            aer: s.aksharas.rate(),
        }
    }
}

#[derive(Serialize)]
struct Item {
    id: String,
    #[serde(flatten)]
    rates: Rates,
    ref_chars: usize,
    char_edits: usize,
}

#[derive(Serialize)]
struct Summary {
    items: usize,
    #[serde(flatten)]
    rates: Rates,
    chars: Counts,
    words: Counts,
    aksharas: Counts,
}

#[derive(Serialize)]
struct Report {
    summary: Summary,
    items: Vec<Item>,
}

fn score(input: impl BufRead, mut output: impl Write) -> Result<(), Error> {
    let mut total = Score::default();
    let mut items = Vec::new();
    for (n, line) in input.lines().enumerate() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        let pair: Pair =
            serde_json::from_str(&line).map_err(|e| Error(format!("input line {}: {e}", n + 1)))?;
        let s = Score::of(&pair.reference, &pair.hypothesis);
        total.add(s);
        items.push(Item {
            id: pair.id,
            rates: Rates::from(&s),
            ref_chars: s.chars.reference,
            char_edits: s.chars.edits,
        });
    }
    let report = Report {
        summary: Summary {
            items: items.len(),
            rates: Rates::from(&total),
            chars: total.chars,
            words: total.words,
            aksharas: total.aksharas,
        },
        items,
    };
    serde_json::to_writer(&mut output, &report).map_err(|e| Error(e.to_string()))?;
    writeln!(output)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn run_str(command: &str, input: &str) -> Result<String, Error> {
        let mut out = Vec::new();
        run(command, input.as_bytes(), &mut out)?;
        Ok(String::from_utf8(out).unwrap())
    }

    #[test]
    fn normalize_works_line_by_line() {
        assert_eq!(run_str("normalize", "ಕಿ\u{0CD5}\nಉಾ\n").unwrap(), "ಕೀ\nಊ\n");
    }

    #[test]
    fn aksharas_prints_json_arrays() {
        assert_eq!(
            run_str("aksharas", "ಕನ್ನಡ\n").unwrap(),
            "[\"ಕ\",\"ನ್ನ\",\"ಡ\"]\n"
        );
    }

    #[test]
    fn to_nudi_encodes_and_reports_unencodable_text() {
        assert_eq!(
            run_str("to-nudi", "ಕನ್ನಡ\nಕ A\n").unwrap(),
            "{\"text\":\"PÀ£ÀßqÀ\",\"clean\":true}\n{\"text\":\"PÀ A\",\"clean\":false}\n"
        );
    }

    #[test]
    fn score_reports_micro_totals_and_items() {
        let input = "{\"id\":\"a\",\"ref\":\"ಅ\",\"hyp\":\"ಆ\"}\n\n{\"id\":\"b\",\"ref\":\"ಕನ್ನಡ\",\"hyp\":\"ಕನ್ನಡ\"}\n";
        let v: serde_json::Value = serde_json::from_str(&run_str("score", input).unwrap()).unwrap();
        assert_eq!(v["summary"]["items"], 2);
        assert_eq!(v["summary"]["chars"]["edits"], 1);
        assert_eq!(v["summary"]["chars"]["reference"], 6);
        assert_eq!(v["items"][0]["cer"], 1.0);
        assert_eq!(v["items"][1]["aer"], 0.0);
        assert_eq!(v["items"][0]["char_edits"], 1);
    }

    #[test]
    fn score_names_the_bad_line() {
        let err = run_str(
            "score",
            "{\"id\":\"a\",\"ref\":\"x\",\"hyp\":\"x\"}\nnot json\n",
        )
        .unwrap_err();
        assert!(err.0.starts_with("input line 2:"), "{}", err.0);
    }

    #[test]
    fn unknown_command_is_an_error() {
        assert!(run_str("nope", "").is_err());
    }
}
