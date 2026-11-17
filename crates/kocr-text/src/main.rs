// SPDX-FileCopyrightText: 2026 The Open Kannada Authors
// SPDX-License-Identifier: MIT OR Apache-2.0

use std::io::{stdin, stdout, BufWriter};
use std::process::ExitCode;

use kocr_text::cli::{run, USAGE};

fn main() -> ExitCode {
    let Some(command) = std::env::args().nth(1) else {
        eprintln!("{USAGE}");
        return ExitCode::from(2);
    };
    match run(&command, stdin().lock(), BufWriter::new(stdout().lock())) {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            eprintln!("kocr-text: {e}");
            ExitCode::FAILURE
        }
    }
}
