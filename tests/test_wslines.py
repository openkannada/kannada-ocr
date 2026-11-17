# SPDX-FileCopyrightText: 2026 The Open Kannada Authors
# SPDX-License-Identifier: MIT OR Apache-2.0

import json

from kannada_ocr.wslines import LOW_RES_SHARE, held_out_books, low_res, scan_url


def test_scan_url_changes_only_the_width():
    url = "https://upload.wikimedia.org/x/thumb/d/d4/A-500px.pdf/page7-500px-A-500px.pdf.jpg"
    assert scan_url(url, 1280).endswith("/A-500px.pdf/page7-1280px-A-500px.pdf.jpg")
    assert scan_url("https://u/x/thumb/a/ab/B.png/500px-B.png", 960).endswith("/960px-B.png")


def test_benchmark_books_keep_their_split(tmp_path):
    books = [{"file": "A.djvu", "split": "dev"}, {"file": "B.pdf", "split": "test"}]
    (tmp_path / "books.json").write_text(json.dumps(books))
    assert held_out_books(tmp_path) == {"A.djvu": "dev", "B.pdf": "test"}


def test_low_res_copies_are_a_fixed_share():
    chosen = [low_res(f"ws00_{i:04d}_L01") for i in range(4000)]
    assert chosen == [low_res(f"ws00_{i:04d}_L01") for i in range(4000)]
    assert abs(sum(chosen) / len(chosen) - LOW_RES_SHARE) < 0.03


def test_a_zero_typed_for_an_anusvara_is_fixed():
    from kannada_ocr.wslines import fix_proofreading

    assert fix_proofreading("ನಿ೦ತರೇನು ಕ0ಡ") == "ನಿಂತರೇನು ಕಂಡ"
    assert fix_proofreading("೧೦ ಪುಟ ೨೦೦ ರೂ, ಸಂಖ್ಯೆ ೪೦") == "೧೦ ಪುಟ ೨೦೦ ರೂ, ಸಂಖ್ಯೆ ೪೦"
    assert fix_proofreading("ಪುಟ೦೫") == "ಪುಟ೦೫"


def test_a_box_much_taller_than_the_page_median_is_not_a_single_line():
    from kannada_ocr.wslines import single_lines

    boxes = [(0, 0, 9, 30), (0, 40, 9, 72), (0, 80, 9, 140), (0, 150, 9, 178), (0, 190, 9, 234)]
    assert single_lines(boxes) == [True, True, False, True, True]
    assert single_lines([]) == []


def test_pages_per_book_limits_training_books_only(monkeypatch):
    from kannada_ocr import wikisource, wslines

    books = {"Index:A.pdf": "A.pdf", "Index:B.pdf": "B.pdf"}
    monkeypatch.setattr(wikisource, "list_indexes", lambda client: list(books))
    monkeypatch.setattr(
        wikisource,
        "read_index",
        lambda client, title: wikisource.IndexInfo(
            title, books[title], {}, {n: 3 for n in range(1, 201)}
        ),
    )
    monkeypatch.setattr(wikisource, "file_licenses", lambda client, file: ["PD-old"])
    monkeypatch.setattr(
        wikisource,
        "read_page",
        lambda client, index, n: wikisource.ScanPage(
            f"Page:{index.file}/{n}", 3, "ಪಠ್ಯ", "u/500px-x.jpg"
        ),
    )

    class Client:
        def get(self, url):
            return b""

    pages = wslines._pages(Client(), {"B.pdf": "dev"}, lambda _: None, pages_per_book=70)
    counts = {b: sum(p["book"] == b for p in pages) for b in books.values()}
    assert counts == {"A.pdf": 70, "B.pdf": wslines.DEV_PAGES_PER_BOOK}


def test_a_failed_large_scan_falls_back_and_a_failed_page_is_skipped():
    from kannada_ocr.wslines import fetch_scan

    class Client:
        def __init__(self, broken):
            self.broken = broken

        def get(self, url):
            if any(b in url for b in self.broken):
                raise OSError("503")
            return b""

    small = "https://u/x/thumb/a/ab/B.pdf/page3-500px-B.pdf.jpg"
    assert fetch_scan(Client([]), small).endswith("page3-1280px-B.pdf.jpg")
    assert fetch_scan(Client(["1280px"]), small) == small
    assert fetch_scan(Client(["px-"]), small) is None


def test_excluded_books_give_no_pages(monkeypatch):
    from kannada_ocr import wikisource, wslines

    books = {"Index:A.pdf": "A.pdf", "Index:B.pdf": "B.pdf"}
    monkeypatch.setattr(wikisource, "excluded_books", lambda: {"B.pdf"})
    monkeypatch.setattr(wikisource, "list_indexes", lambda client: list(books))
    monkeypatch.setattr(
        wikisource,
        "read_index",
        lambda client, title: wikisource.IndexInfo(title, books[title], {}, {1: 3, 2: 3}),
    )
    monkeypatch.setattr(wikisource, "file_licenses", lambda client, file: ["PD-old"])
    monkeypatch.setattr(
        wikisource,
        "read_page",
        lambda client, index, n: wikisource.ScanPage(
            f"Page:{index.file}/{n}", 3, "ಪಠ್ಯ", "u/500px-x.jpg"
        ),
    )

    class Client:
        def get(self, url):
            return b""

    pages = wslines._pages(Client(), {}, lambda _: None)
    assert {p["book"] for p in pages} == {"A.pdf"}


def test_the_2001_book_is_excluded_and_not_in_the_training_manifest():
    from kannada_ocr.wikisource import EXCLUDED_BOOKS, excluded_books

    excluded = excluded_books()
    assert "ಸಂದೇಶದ ಕಥೆಗಳು.pdf" in excluded
    manifest = EXCLUDED_BOOKS.parent / "wikisource-training-books.json"
    listed = {book["file"] for book in json.loads(manifest.read_text(encoding="utf-8"))}
    assert not listed & excluded
