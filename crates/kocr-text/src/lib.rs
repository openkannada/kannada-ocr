//! Text tools for the Kannada OCR benchmark, built on [`kannadi`].
//!
//! - [`score`]: character, word and akshara error rates.
//! - [`cli`]: the line-oriented commands behind the `kocr-text` binary.

#![forbid(unsafe_code)]
#![warn(missing_docs)]

pub mod cli;
pub mod score;
