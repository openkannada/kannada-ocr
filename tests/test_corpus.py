# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

import random

import pyarrow as pa
import pyarrow.parquet as pq

from kannada_ocr import corpus
from kannada_ocr.dataset import write_jsonl


def test_chunks_are_word_aligned_and_lose_nothing():
    paragraph = " ".join(["ಕನ್ನಡ"] * 50)
    pieces = list(corpus.chunk(paragraph, random.Random(1), low=10, high=20))
    assert " ".join(pieces) == paragraph
    assert all(len(p) <= 20 for p in pieces)


def test_kannada_share_ignores_digits_and_punctuation():
    assert corpus.kannada_share("ಕನ್ನಡ 2026!") == 1.0
    assert corpus.kannada_share("ಕ abc") == 0.25
    assert corpus.kannada_share("123") == 0.0


def test_lines_overlapping_the_benchmark_are_dropped(tmp_path):
    secret = "ಈ ಸಾಲು ಪರೀಕ್ಷೆಯ ಪುಟದಲ್ಲಿ ಇರುವ ಒಂದು ಉದ್ದವಾದ ವಾಕ್ಯವಾಗಿದೆ"
    bench = tmp_path / "bench"
    write_jsonl(bench / "metadata.jsonl", [{"text": secret}])
    docs = [secret, "ಹೊಸ ಸಾಲು", "ಹೊಸ ಸಾಲು"]
    parquet = tmp_path / "wiki.parquet"
    pq.write_table(pa.table({"text": docs}), parquet)
    out = tmp_path / "lines.tsv"
    rng_seed = 3
    corpus.build_lines(
        {"wikipedia": parquet}, [bench], out, per_source=10, seed=rng_seed, log=lambda _: None
    )
    lines = [t for _, t in corpus.read_lines(out)]
    assert lines == ["ಹೊಸ ಸಾಲು"]


def test_overlap_ignores_joiners():
    assert corpus.shingles("ಕಾರ್ಯ\u200cನಿರ್ವಹಿಸುವ ಸಂಸ್ಥೆಯಲ್ಲಿ ಇದೆ") == corpus.shingles(
        "ಕಾರ್ಯನಿರ್ವಹಿಸುವ ಸಂಸ್ಥೆಯಲ್ಲಿ ಇದೆ"
    )


def test_film_song_pages_are_skipped(tmp_path):
    parquet = tmp_path / "ws.parquet"
    pq.write_table(pa.table({"text": ["ಚಿತ್ರ: ಅಭಿ\nಗಾಯನ: ಯಾರೋ\nಹಾಡು", "ಪುರಾತನ ಕೃತಿ"]}), parquet)
    assert list(corpus.documents(parquet, "wikisource")) == ["ಪುರಾತನ ಕೃತಿ"]
